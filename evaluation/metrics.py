"""
Evaluation metrics calculation module for DPDP Privacy Gateway.
Calculates Precision, Recall, F1 per entity type, raw PII leakage count,
placeholder reinsertion accuracy, and gateway processing latency statistics.
"""

import re
from collections import Counter
from typing import Dict, List, Tuple, Any


ENTITY_TYPES = ['PERSON', 'AADHAAR', 'PAN', 'GSTIN', 'VOTER_ID', 'PASSPORT', 'ADDRESS']


def calculate_precision(tp: int, fp: int) -> float:
    """Calculate precision: TP / (TP + FP)"""
    return tp / (tp + fp) if (tp + fp) > 0 else 0.0


def calculate_recall(tp: int, fn: int) -> float:
    """Calculate recall: TP / (TP + FN)"""
    return tp / (tp + fn) if (tp + fn) > 0 else 0.0


def calculate_f1(precision: float, recall: float) -> float:
    """Calculate F1 score: 2 * (Precision * Recall) / (Precision + Recall)"""
    return (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0


def evaluate_entity_spans(
    ground_truth_entities: List[Dict[str, Any]],
    predicted_entities: List[Dict[str, Any]],
    matching_mode: str = 'exact'
) -> Dict[str, Dict[str, int]]:
    """
    Evaluates detection using exact (type, start, end) matching or value-based matching.
    Returns per-entity counts of TP, FP, FN.
    """
    counts = {e_type: {'tp': 0, 'fp': 0, 'fn': 0} for e_type in ENTITY_TYPES}

    if matching_mode == 'exact':
        truth_items = [
            (e['type'], e['start'], e['end']) for e in ground_truth_entities
        ]
        predicted_items = [
            (e['type'], e['start'], e['end']) for e in predicted_entities
        ]
    else:
        truth_items = [
            (e['type'], e['value'].strip()) for e in ground_truth_entities
        ]
        predicted_items = [
            (e['type'], e['value'].strip()) for e in predicted_entities
        ]

    truth_counts = Counter(truth_items)
    predicted_counts = Counter(predicted_items)
    for item in truth_counts.keys() | predicted_counts.keys():
        etype = item[0]
        if etype not in counts:
            continue
        truth_count = truth_counts[item]
        predicted_count = predicted_counts[item]
        counts[etype]['tp'] += min(truth_count, predicted_count)
        counts[etype]['fp'] += max(predicted_count - truth_count, 0)
        counts[etype]['fn'] += max(truth_count - predicted_count, 0)

    return counts


def calculate_per_entity_metrics(counts: Dict[str, Dict[str, int]]) -> List[Dict[str, Any]]:
    """
    Computes Precision, Recall, and F1 for each entity type.
    """
    results = []
    for etype in ENTITY_TYPES:
        c = counts.get(etype, {'tp': 0, 'fp': 0, 'fn': 0})
        tp, fp, fn = c['tp'], c['fp'], c['fn']
        prec = calculate_precision(tp, fp)
        rec = calculate_recall(tp, fn)
        f1 = calculate_f1(prec, rec)
        results.append({
            'name': etype,
            'tp': tp,
            'fp': fp,
            'fn': fn,
            'precision': round(prec, 4),
            'recall': round(rec, 4),
            'f1': round(f1, 4),
        })
    return results


def check_outbound_leakage(entities: List[Dict[str, Any]], sanitized_text: str) -> Tuple[bool, List[str]]:
    """
    Verifies that raw ground-truth PII values do not leak in outbound sanitized text.
    Returns (leakage_detected, list_of_leaked_values).
    """
    leaked = []
    for ent in entities:
        val = ent.get('value', '').strip()
        # Only check significant strings (> 3 characters) to avoid false positives on short numbers
        if len(val) >= 4 and val in sanitized_text:
            leaked.append(val)
    return (len(leaked) > 0, leaked)


def check_reinsertion_accuracy(
    sanitized_text: str,
    final_response: str,
    restoration: Dict[str, Any],
) -> float:
    """
    Measures placeholders reported as restored that no longer appear in the final response.
    """
    placeholders = set(re.findall(r'<[A-Z_]+_\d+>', sanitized_text))
    if not placeholders:
        return 1.0

    restored = set(restoration.get('restored', []))
    restored_count = sum(
        placeholder in restored and placeholder not in final_response
        for placeholder in placeholders
    )
    return round(restored_count / len(placeholders), 4)


def calculate_latency_summary(latencies_ms: List[float]) -> Dict[str, float]:
    """Computes average, min, max, and median latency."""
    if not latencies_ms:
        return {'average_latency_ms': 0.0, 'min_latency_ms': 0.0, 'max_latency_ms': 0.0}

    return {
        'average_latency_ms': round(sum(latencies_ms) / len(latencies_ms), 2),
        'min_latency_ms': round(min(latencies_ms), 2),
        'max_latency_ms': round(max(latencies_ms), 2),
    }
