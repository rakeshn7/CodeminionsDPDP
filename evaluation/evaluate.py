"""
Evaluate the synthetic corpus against either a reference simulator or the live API.
Live evaluation is opt-in and requires an explicit document limit and confirmation.
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import (
    calculate_latency_summary,
    calculate_per_entity_metrics,
    check_outbound_leakage,
    check_reinsertion_accuracy,
    evaluate_entity_spans,
)

ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / 'dataset' / 'synthetic_documents.json'
RESULTS_PATH = ROOT / 'evaluation' / 'results.json'
FRONTEND_RESULTS_PATH = ROOT / 'frontend' / 'public' / 'evaluation-results.json'
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://127.0.0.1:8000').rstrip('/')
REFERENCE_SOURCE = 'Reference simulation — not live backend measurements'
LIVE_SOURCE = f'Live FastAPI backend ({BACKEND_URL})'

RECOGNIZERS = {
    'AADHAAR': re.compile(r'\b[2-9]\d{3}\s\d{4}\s\d{4}\b'),
    'PAN': re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b'),
    'GSTIN': re.compile(r'\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b'),
    'VOTER_ID': re.compile(r'\b[A-Z]{3}\d{7}\b'),
    'PASSPORT': re.compile(r'\b[A-Z]\d{7}\b'),
}


def load_synthetic_dataset() -> list[dict[str, Any]]:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f'Synthetic dataset not found at {DATASET_PATH}. '
            'Run dataset/generate_dataset.py first.'
        )
    with DATASET_PATH.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def check_backend_available() -> bool:
    request = Request(f'{BACKEND_URL}/health', headers={'User-Agent': 'EvaluationEngine'})
    try:
        with urlopen(request, timeout=3) as response:
            return response.status == 200
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def call_live_backend(text: str) -> dict[str, Any]:
    payload = json.dumps({
        'text': text,
        'task': 'summarize',
        'provider': 'configured_provider',
    }).encode('utf-8')
    request = Request(
        f'{BACKEND_URL}/api/process',
        data=payload,
        headers={'Content-Type': 'application/json'},
    )
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode('utf-8'))


def run_reference_gateway(doc: dict[str, Any]) -> dict[str, Any]:
    """Run a deterministic demonstration; PERSON and ADDRESS use ground-truth spans."""
    text = doc['text']
    detected_entities = []

    for entity_type, pattern in RECOGNIZERS.items():
        for match in pattern.finditer(text):
            detected_entities.append({
                'type': entity_type,
                'value': match.group(),
                'start': match.start(),
                'end': match.end(),
            })

    for entity in doc['entities']:
        if entity['type'] in ('PERSON', 'ADDRESS'):
            detected_entities.append({
                'type': entity['type'],
                'value': entity['value'],
                'start': entity['start'],
                'end': entity['end'],
            })

    detected_entities.sort(key=lambda entity: (entity['start'], -entity['end']))
    filtered = []
    last_end = -1
    for entity in detected_entities:
        if entity['start'] >= last_end:
            filtered.append(entity)
            last_end = entity['end']

    placeholder_map = {}
    value_placeholders = {}
    type_counts = {}
    for entity in filtered:
        entity_type = entity['type']
        value_key = (entity_type, entity['value'])
        placeholder = value_placeholders.get(value_key)
        if placeholder is None:
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
            placeholder = f'<{entity_type}_{type_counts[entity_type]}>'
            value_placeholders[value_key] = placeholder
            placeholder_map[placeholder] = entity['value']
        entity['placeholder'] = placeholder

    sanitized = text
    for entity in sorted(filtered, key=lambda item: item['start'], reverse=True):
        placeholder = entity['placeholder']
        sanitized = sanitized[:entity['start']] + placeholder + sanitized[entity['end']:]

    person_placeholder = next(
        (entity['placeholder'] for entity in filtered if entity['type'] == 'PERSON'),
        'the applicant',
    )
    llm_response = (
        'Reference simulation summary for '
        f'{person_placeholder}.'
    )
    final_response = llm_response
    restored = []
    for placeholder, original_value in placeholder_map.items():
        if placeholder in final_response:
            final_response = final_response.replace(placeholder, original_value)
            restored.append(placeholder)

    return {
        'status': 'success',
        'sanitized_text': sanitized,
        'entities': filtered,
        'llm_response': llm_response,
        'final_response': final_response,
        'leakage_detected': False,
        'restoration': {
            'restored': restored,
            'missing': [item for item in placeholder_map if item not in restored],
            'unknown': [],
            'malformed': [],
        },
    }


def evaluate(mode: str = 'reference', limit: int | None = None) -> dict[str, Any]:
    documents = load_synthetic_dataset()
    if limit is not None:
        if limit < 1 or limit > len(documents):
            raise ValueError(f'--limit must be between 1 and {len(documents)}.')
        documents = documents[:limit]

    if mode == 'live' and not check_backend_available():
        raise RuntimeError('The backend health check failed; no live evaluation was run.')

    source = LIVE_SOURCE if mode == 'live' else REFERENCE_SOURCE
    print(f'Evaluating {len(documents)} documents in {mode} mode.')
    print(f'Source: {source}')
    if mode == 'reference':
        print('Reference PERSON and ADDRESS detections use ground-truth spans.')

    all_ground_truth = []
    all_predicted = []
    latencies = []
    reinsertion_scores = []
    document_results = []
    category_counts = {}
    total_leakages = 0
    successful_count = 0
    failed_documents = []

    for document in documents:
        ground_truth = document['entities']
        all_ground_truth.extend(ground_truth)
        for entity in ground_truth:
            category_counts[entity['type']] = category_counts.get(entity['type'], 0) + 1

        try:
            result = (
                call_live_backend(document['text'])
                if mode == 'live'
                else run_reference_gateway(document)
            )
            if result.get('status') != 'success':
                raise ValueError('The backend did not return a successful process result.')
            if not isinstance(result.get('sanitized_text'), str):
                raise ValueError('The process response did not include sanitized text.')
            if not isinstance(result.get('entities'), list):
                raise ValueError('The process response did not include an entity list.')
            if not isinstance(result.get('restoration'), dict):
                raise ValueError('The process response did not include restoration status.')
        except Exception as error:
            failed_documents.append({
                'document_id': document['document_id'],
                'error': f'Request failed ({type(error).__name__}); details omitted.',
            })
            document_results.append({
                'document_id': document['document_id'],
                'status': 'failed',
            })
            print(f"Failed {document['document_id']}; no reference fallback was used.")
            continue

        successful_count += 1
        predicted = result['entities']
        all_predicted.extend(predicted)
        sanitized = result['sanitized_text']
        leakage_detected, _ = check_outbound_leakage(ground_truth, sanitized)
        leakage_detected = leakage_detected or bool(result.get('leakage_detected'))
        total_leakages += int(leakage_detected)
        restoration_score = check_reinsertion_accuracy(
            sanitized,
            result.get('final_response', ''),
            result['restoration'],
        )
        reinsertion_scores.append(restoration_score)
        if mode == 'live':
            latency = result.get('metrics', {}).get('processing_latency_ms')
            if isinstance(latency, (int, float)):
                latencies.append(float(latency))

        document_results.append({
            'document_id': document['document_id'],
            'status': 'success',
            'raw_pii_leakage_detected': leakage_detected,
            'placeholder_reinsertion_accuracy': restoration_score,
        })

    span_counts = evaluate_entity_spans(
        all_ground_truth,
        all_predicted,
        matching_mode='exact',
    )
    entity_metrics = calculate_per_entity_metrics(span_counts)
    overall_tp = sum(metric['tp'] for metric in entity_metrics)
    overall_fp = sum(metric['fp'] for metric in entity_metrics)
    overall_fn = sum(metric['fn'] for metric in entity_metrics)
    precision = overall_tp / (overall_tp + overall_fp) if overall_tp + overall_fp else 0.0
    recall = overall_tp / (overall_tp + overall_fn) if overall_tp + overall_fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    reinsertion_accuracy = (
        round(sum(reinsertion_scores) / len(reinsertion_scores) * 100, 2)
        if reinsertion_scores else None
    )
    latency = calculate_latency_summary(latencies) if latencies else None

    summary = {
        'total_documents_tested': len(documents),
        'documents_succeeded': successful_count,
        'documents_failed': len(failed_documents),
        'ground_truth_entities': len(all_ground_truth),
        'detected_entities': len(all_predicted),
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'f1': round(f1, 4),
        'raw_pii_leakage_count': total_leakages,
        'reinsertion_accuracy': reinsertion_accuracy,
        'average_latency_ms': latency['average_latency_ms'] if latency else None,
        'min_latency_ms': latency['min_latency_ms'] if latency else None,
        'max_latency_ms': latency['max_latency_ms'] if latency else None,
    }
    payload = {
        'status': 'completed' if not failed_documents else 'failed',
        'evaluation_mode': 'live_backend' if mode == 'live' else 'reference_simulation',
        'source': source,
        'matching_method': 'Exact Entity Span & Type (type, start, end)',
        'limitations': [
            'Reference PERSON and ADDRESS spans are copied from ground truth; '
            'reference detection scores do not measure backend NER accuracy.'
        ] if mode == 'reference' else [],
        'summary': summary,
        'entity_metrics': entity_metrics,
        'privacy_metrics': {
            'raw_pii_leakage_count': total_leakages,
            'placeholder_reinsertion_accuracy': reinsertion_accuracy,
        },
        'pii_by_category': [
            {'name': name, 'value': count}
            for name, count in category_counts.items()
        ],
        'document_results': document_results,
        'failed_documents': failed_documents,
    }

    for output_path in (RESULTS_PATH, FRONTEND_RESULTS_PATH):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('w', encoding='utf-8') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    print(
        f"Finished: {successful_count}/{len(documents)} succeeded; "
        f"{len(failed_documents)} failed."
    )
    print(f'Results saved to {RESULTS_PATH} and {FRONTEND_RESULTS_PATH}.')
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Evaluate the synthetic privacy gateway corpus.')
    parser.add_argument(
        '--mode',
        choices=('reference', 'live'),
        default='reference',
        help='Reference mode is offline simulation; live mode calls the backend.',
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of documents to process. Required for live mode.',
    )
    parser.add_argument(
        '--confirm-live',
        action='store_true',
        help='Required confirmation before live mode can make provider requests.',
    )
    args = parser.parse_args(argv)
    if args.mode == 'live':
        if not args.confirm_live:
            parser.error('live mode requires --confirm-live.')
        if args.limit is None:
            parser.error('live mode requires an explicit --limit.')
    elif args.confirm_live:
        parser.error('--confirm-live is only valid with --mode live.')
    return args


if __name__ == '__main__':
    arguments = parse_args()
    try:
        evaluate(arguments.mode, arguments.limit)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f'Evaluation stopped: {error}', file=sys.stderr)
        raise SystemExit(1) from error
