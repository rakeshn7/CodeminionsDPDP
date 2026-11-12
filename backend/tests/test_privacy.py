from __future__ import annotations

from app.detection.india_recognizers import detect_india_patterns
from app.detection.presidio_engine import EntitySpan, PresidioDetectionEngine
from app.privacy.outbound_guard import verify_outbound
from app.privacy.reinsertion import reinsert
from app.privacy.token_manager import TokenManager


def test_detects_all_indian_identifier_patterns_and_address():
    aadhaar = "234567890123"
    text = (
        f"Aadhaar {aadhaar}, PAN ABCPD1234F, GSTIN 27ABCPD1234F1Z5, "
        "voter ABC1234567, passport N1234567, address: 12 MG Road, Pune"
    )
    detected = detect_india_patterns(text)
    assert {item.entity_type for item in detected} == {
        "AADHAAR",
        "PAN",
        "GSTIN",
        "VOTER_ID",
        "PASSPORT",
        "ADDRESS",
    }
    assert any(item.entity_type == "AADHAAR" for item in detected)
    assert not detect_india_patterns("Aadhaar 1234-5678-9012")


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
    assert verify_outbound('{"content":"not in this text"}', ["IN"]).allowed


def test_code_mixed_context_still_detects_identifiers():
    text = "Rahul ka Aadhaar number hai 2345-6789-0123, please verify karo."
    assert any(item.entity_type == "AADHAAR" for item in detect_india_patterns(text))


def test_identifier_offsets_remain_correct_after_unicode_expansion_character():
    text = "ß PAN ABCPD1234F"
    match = next(item for item in detect_india_patterns(text) if item.entity_type == "PAN")
    assert text[match.start : match.end] == "ABCPD1234F"
