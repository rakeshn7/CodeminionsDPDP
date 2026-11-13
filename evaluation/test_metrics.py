from evaluation.metrics import check_reinsertion_accuracy, evaluate_entity_spans
from evaluation.evaluate import run_reference_gateway


def test_dropped_placeholder_is_not_counted_as_reinserted():
    score = check_reinsertion_accuracy(
        'Contact <PERSON_1> and <PAN_1>.',
        'Contact.',
        {'restored': [], 'missing': ['<PERSON_1>', '<PAN_1>']},
    )

    assert score == 0.0


def test_reinsertion_requires_backend_report_and_removed_placeholder():
    score = check_reinsertion_accuracy(
        'Applicant <PERSON_1>.',
        'Applicant Priya Nair.',
        {'restored': ['<PERSON_1>']},
    )

    assert score == 1.0


def test_placeholder_left_in_response_is_not_counted_as_reinserted():
    score = check_reinsertion_accuracy(
        'Applicant <PERSON_1>.',
        'Applicant <PERSON_1>.',
        {'restored': ['<PERSON_1>']},
    )

    assert score == 0.0


def test_exact_span_metrics_preserve_duplicate_predictions():
    entity = {'type': 'PERSON', 'start': 0, 'end': 5}
    counts = evaluate_entity_spans([entity, entity], [entity])

    assert counts['PERSON'] == {'tp': 1, 'fp': 0, 'fn': 1}


def test_reference_simulator_reuses_placeholders_without_sending_raw_values():
    text = 'Priya Nair called. Priya Nair will follow up.'
    first_start = text.index('Priya Nair')
    second_start = text.index('Priya Nair', first_start + 1)
    result = run_reference_gateway({
        'text': text,
        'entities': [
            {
                'type': 'PERSON',
                'value': 'Priya Nair',
                'start': first_start,
                'end': first_start + len('Priya Nair'),
            },
            {
                'type': 'PERSON',
                'value': 'Priya Nair',
                'start': second_start,
                'end': second_start + len('Priya Nair'),
            },
        ],
    })

    assert result['sanitized_text'].count('<PERSON_1>') == 2
    assert 'Priya Nair' not in result['llm_response']
    assert result['final_response'] == 'Reference simulation summary for Priya Nair.'
    assert result['restoration']['restored'] == ['<PERSON_1>']
