from __future__ import annotations

import pytest

from app.detection.india_recognizers import (
    build_presidio_recognizers,
    detect_india_patterns,
)
from app.detection.ner_engine import GlinerEngine
from app.detection.presidio_engine import EntitySpan, PresidioDetectionEngine
from app.privacy.outbound_guard import verify_outbound
from app.privacy.reinsertion import reinsert
from app.privacy.token_manager import TokenManager


def test_detects_all_indian_identifier_patterns_and_address():
    aadhaar = "234567890123"
    text = (
        f"Aadhaar {aadhaar}, PAN ABCPK1234F, GSTIN 27ABCPK1234F1Z5, "
        "voter ABC1234567, passport N1234567, phone +91 98765 43210, "
        "PIN 560001, address: 12 MG Road, Pune"
    )
    detected = detect_india_patterns(text)
    assert {item.entity_type for item in detected} == {
        "AADHAAR",
        "PAN",
        "GSTIN",
        "VOTER_ID",
        "PASSPORT",
        "PHONE_NUMBER",
        "PIN_CODE",
        "ADDRESS",
    }
    assert any(item.entity_type == "AADHAAR" for item in detected)
    assert not detect_india_patterns("Aadhaar 1234-5678-9012")


def test_pan_recognizer_accepts_valid_category_and_rejects_invalid_formats():
    recognizer = build_presidio_recognizers()[0]
    valid_text = "PAN ABCPK1234F"
    results = recognizer.analyze(valid_text, ["PAN"])
    assert [
        (result.entity_type, valid_text[result.start : result.end], result.score)
        for result in results
    ] == [("PAN", "ABCPK1234F", 0.93)]

    for invalid in ("ABCDE1234F", "ABCDP1234F", "ABCP1234F", "ABCPK12345"):
        assert not recognizer.analyze(f"PAN {invalid}", ["PAN"]), invalid


def test_pan_is_registered_and_executed_by_presidio_analyzer():
    spacy = pytest.importorskip("spacy")
    if not spacy.util.is_package("en_core_web_sm"):
        pytest.skip("en_core_web_sm is not installed")
    detector = PresidioDetectionEngine(
        "en_core_web_sm", GlinerEngine("urchade/gliner_small-v2.1", enabled=False)
    )
    assert detector.status()["presidio"]["state"] == "ready"
    text = "Valid PAN ABCPK1234F; invalid PAN ABCDP1234F."
    detected = detector.detect(text)
    matches = [
        text[item.start : item.end]
        for item in detected
        if item.entity_type == "PAN"
    ]
    assert matches == ["ABCPK1234F"]
    assert not any(
        item.entity_type == "PERSON" and text[item.start : item.end] == "PAN"
        for item in detected
    )


def test_indian_mobile_and_pin_rules_reject_malformed_numbers():
    valid_text = "Call +91 98765 43210 or 9876543210; PIN 560001."
    matches = detect_india_patterns(valid_text)
    assert [
        valid_text[item.start : item.end]
        for item in matches
        if item.entity_type == "PHONE_NUMBER"
    ] == ["+91 98765 43210", "9876543210"]
    assert [
        valid_text[item.start : item.end]
        for item in matches
        if item.entity_type == "PIN_CODE"
    ] == ["560001"]
    invalid_text = "Call 1234567890; invalid PIN 012345."
    assert not detect_india_patterns(invalid_text)


def test_identifiers_keep_exact_unicode_safe_offsets():
    text = "ß PAN ABCPK1234F"
    match = next(item for item in detect_india_patterns(text) if item.entity_type == "PAN")
    assert text[match.start : match.end] == "ABCPK1234F"


def test_masks_repeated_names_and_identity_values_consistently():
    text = "Rahul Sharma has PAN ABCPD1234F; Rahul Sharma used PAN ABCPD1234F."
    entities = [
        EntitySpan("PERSON", 0, 12, 0.9, "test"),
        EntitySpan("PAN", 21, 31, 0.9, "test"),
        EntitySpan("PERSON", 33, 45, 0.9, "test"),
        EntitySpan("PAN", 55, 65, 0.9, "test"),
    ]
    manager = TokenManager()
    masked, public = manager.mask(text, entities)
    assert masked == (
        "<PERSON_1> has PAN <PAN_1>; <PERSON_1> used PAN <PAN_1>."
    )
    assert manager.mapping == {
        "<PERSON_1>": "Rahul Sharma",
        "<PAN_1>": "ABCPD1234F",
    }
    assert "Rahul Sharma" not in masked
    assert len(public) == 4


def test_distinct_people_receive_distinct_tokens():
    text = "Asha met Ravi."
    entities = [
        EntitySpan("PERSON", 0, 4, 0.9, "gliner"),
        EntitySpan("PERSON", 9, 13, 0.9, "gliner"),
    ]
    masked, public = TokenManager().mask(text, entities)
    assert masked == "<PERSON_1> met <PERSON_2>."
    assert public[0]["placeholder"] != public[1]["placeholder"]


def test_mask_rejects_invalid_or_overlapping_spans_instead_of_corrupting_text():
    text = "Asha"
    manager = TokenManager()
    with pytest.raises(ValueError, match="valid and non-overlapping"):
        manager.mask(
            text,
            [
                EntitySpan("PERSON", 0, 4, 0.9, "test"),
                EntitySpan("ADDRESS", 1, 4, 0.8, "test"),
            ],
        )
    with pytest.raises(ValueError, match="valid and non-overlapping"):
        manager.mask(text, [EntitySpan("PERSON", -1, 4, 0.9, "test")])


def test_overlap_prefers_complete_indian_identifier():
    text = "27ABCDE1234F1Z5"
    candidates = [
        EntitySpan("PAN", 2, 12, 0.93, "regex"),
        EntitySpan("GSTIN", 0, 15, 0.94, "regex"),
    ]
    result = PresidioDetectionEngine._resolve_overlaps(candidates, len(text))
    assert [(item.entity_type, item.start, item.end) for item in result] == [
        ("GSTIN", 0, 15)
    ]


def test_adjacent_gliner_address_spans_merge_but_unrelated_addresses_do_not():
    text = (
        "24 MG Road, Bengaluru, Karnataka. At office: 10 Park Street. "
        "Home: 15 Lake Road."
    )
    address_parts = (
        "24 MG Road",
        "Bengaluru, Karnataka",
        "10 Park Street",
        "15 Lake Road",
    )
    starts = [text.index(part) for part in address_parts]
    spans = [
        EntitySpan("ADDRESS", starts[0], starts[0] + len(address_parts[0]), 0.96, "gliner"),
        EntitySpan("ADDRESS", starts[1], starts[1] + len(address_parts[1]), 0.91, "gliner"),
        EntitySpan("ADDRESS", starts[2], starts[2] + len(address_parts[2]), 0.94, "gliner"),
        EntitySpan("ADDRESS", starts[3], starts[3] + len(address_parts[3]), 0.89, "gliner"),
    ]
    resolved = PresidioDetectionEngine._resolve_overlaps(spans, len(text), text)
    assert [(text[item.start : item.end], item.source) for item in resolved] == [
        ("24 MG Road, Bengaluru, Karnataka", "gliner"),
        ("10 Park Street", "gliner"),
        ("15 Lake Road", "gliner"),
    ]


def test_context_address_keeps_state_and_pin_as_separate_nonoverlapping_spans():
    text = "I live at 24 MG Road, Bengaluru, Karnataka 560001."
    address_start = text.index("24 MG Road")
    pin_start = text.index("560001")
    candidates = [
        EntitySpan("ADDRESS", address_start, pin_start + 6, 0.78, "india_regex"),
        EntitySpan("ADDRESS", address_start, text.index(", Karnataka"), 0.91, "gliner"),
        EntitySpan("PIN_CODE", pin_start, pin_start + 6, 0.90, "india_regex"),
    ]
    resolved = PresidioDetectionEngine._resolve_overlaps(
        candidates, len(text), text
    )
    assert [
        (item.entity_type, text[item.start : item.end]) for item in resolved
    ] == [
        ("ADDRESS", "24 MG Road, Bengaluru, Karnataka"),
        ("PIN_CODE", "560001"),
    ]


def test_reinsertion_reports_reordered_repeated_missing_and_unknown():
    mapping = {"<PERSON_1>": "Asha", "<PAN_1>": "ABCDE1234F"}
    outcome = reinsert(
        "PAN <PAN_1>; applicant <PERSON_1>, again <PERSON_1>; unknown <PERSON_9>",
        mapping,
    )
    assert outcome.text.count("Asha") == 2
    assert "ABCDE1234F" in outcome.text
    assert outcome.restored == ["<PAN_1>", "<PERSON_1>"]
    assert outcome.missing == []
    assert outcome.unknown == ["<PERSON_9>"]

    missing = reinsert("No placeholder was returned.", mapping)
    assert missing.missing == ["<PERSON_1>", "<PAN_1>"]
    assert missing.text == "No placeholder was returned."

    malformed = reinsert("Applicant <PERSON_1 has PAN <PAN_1", mapping)
    assert malformed.unknown == []
    assert malformed.malformed == ["<PERSON_1", "<PAN_1"]
    assert malformed.text == "Applicant <PERSON_1 has PAN <PAN_1"


def test_outbound_guard_blocks_known_raw_pii_and_allows_clean_payload():
    known_pii = "ABCDE1234F"
    assert not verify_outbound(
        '{"content":"PAN ABCDE1234F"}', [known_pii]
    ).allowed
    assert verify_outbound(
        '{"content":"PAN <PAN_1>"}', [known_pii]
    ).allowed
    assert not verify_outbound('{"content":"the person is IN"}', ["IN"]).allowed
    assert verify_outbound('{"content":"inside"}', ["IN"]).allowed


def test_code_mixed_context_still_detects_identifiers():
    text = "Rahul ka Aadhaar number hai 2345-6789-0123, please verify karo."
    assert any(item.entity_type == "AADHAAR" for item in detect_india_patterns(text))


def test_identifier_offsets_remain_correct_after_unicode_expansion_character():
    text = "ß PAN ABCPD1234F"
    match = next(item for item in detect_india_patterns(text) if item.entity_type == "PAN")
    assert text[match.start : match.end] == "ABCPD1234F"
