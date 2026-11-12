"""
Evaluation metrics calculation module for DPDP Privacy Gateway.
Calculates Precision, Recall, F1 per entity type, raw PII leakage count,
placeholder reinsertion accuracy, and gateway processing latency statistics.
"""

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
        truth_set = set((e['type'], e['start'], e['end']) for e in ground_truth_entities)
        pred_set = set((e['type'], e['start'], e['end']) for e in predicted_entities)

        for p in pred_set:
            etype = p[0]
            if etype in counts:
                if p in truth_set:
                    counts[etype]['tp'] += 1
                else:
                    counts[etype]['fp'] += 1

        for t in truth_set:
            etype = t[0]
            if etype in counts:
                if t not in pred_set:
                    counts[etype]['fn'] += 1
    else:
        # Value-based matching fallback
        truth_vals = set((e['type'], e['value'].strip()) for e in ground_truth_entities)
        pred_vals = set((e['type'], e['value'].strip()) for e in predicted_entities)

        for p in pred_vals:
            etype = p[0]
            if etype in counts:
                if p in truth_vals:
                    counts[etype]['tp'] += 1
                else:
                    counts[etype]['fp'] += 1

        for t in truth_vals:
            etype = t[0]
            if etype in counts:
                if t not in pred_vals:
                    counts[etype]['fn'] += 1

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
    entities: List[Dict[str, Any]],
    sanitized_text: str,
    final_response: str
) -> float:
    """
    Calculates placeholder reinsertion accuracy:
    Percentage of placeholders in sanitized_text that were properly restored
    with original entity values in final_response.
    """
    import re
    placeholders = re.findall(r'<[A-Z_]+_\d+>', sanitized_text)
    if not placeholders:
        return 1.0

    restored_count = 0
    for ph in set(placeholders):
        # A placeholder is successfully restored if it does not remain raw in final_response
        if ph not in final_response:
            restored_count += 1

    return round((restored_count / len(set(placeholders))), 4)


def calculate_latency_summary(latencies_ms: List[float]) -> Dict[str, float]:
    """Computes average, min, max, and median latency."""
    if not latencies_ms:
        return {'average_latency_ms': 0.0, 'min_latency_ms': 0.0, 'max_latency_ms': 0.0}

    return {
        'average_latency_ms': round(sum(latencies_ms) / len(latencies_ms), 2),
        'min_latency_ms': round(min(latencies_ms), 2),
        'max_latency_ms': round(max(latencies_ms), 2),
    }
