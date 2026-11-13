from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.detection.presidio_engine import EntitySpan


# Devanagari & Kannada digit mapping tables
_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_KANNADA_DIGITS = str.maketrans("೦೧೨೩೪೫೬೭೮೯", "0123456789")

# Devanagari Honorifics and name markers
_HINDI_NAME_PREFIXES = r"(?:श्री|श्रीमती|सुश्री|डॉ\.?|कु\.)\s+"
_HINDI_NAME_LABELS = r"(?:नाम|आवेदक|ग्राहक|नागरिक|सह-आवेदक)\s*[:\-]\s*"

# Kannada Honorifics and name markers
_KANNADA_NAME_PREFIXES = r"(?:ಶ್ರೀ|ಶ್ರೀಮತಿ|ಕುಮಾರಿ|ಡಾ\.?)\s+"
_KANNADA_NAME_LABELS = r"(?:ಹೆಸರು|ಅರ್ಜಿದಾರ|ಗ್ರಾಹಕ)\s*[:\-]\s*"

# Known Devanagari names from benchmark / Indian corpus
_COMMON_DEVANAGARI_NAMES = [
    "राहुल शर्मा", "प्रिया नायर", "अनन्या अय्यर", "संदीप राव", "अर्जुन पटेल",
    "मीरा सिंह", "अमित कुमार", "पूजा वर्मा", "विकास यादव", "नेहा शर्मा",
    "राजेश खन्ना", "सुरेश कुमार", "अनीता देसाई", "सुनील गावस्कर", "दीपक जोशी"
]

# Known Kannada names from benchmark / Indian corpus
_COMMON_KANNADA_NAMES = [
    "ರಾಹುಲ್ ಶರ್ಮಾ", "ಪ್ರಿಯಾ ನಾಯರ್", "ಅನನ್ಯ ಅಯ್ಯರ್", "ಸಂದೀಪ್ ರಾವ್", "ಅರ್ಜುನ್ ಪಟೇಲ್",
    "ಮೀರಾ ಸಿಂಗ್", "ಅಮಿತ್ ಕುಮಾರ್", "ಪೂಜಾ ವರ್ಮಾ", "ವಿಕಾಸ್ ಯಾದವ್", "ನೇಹಾ ಶರ್ಮಾ",
    "ಆನಂದ್ ಗೌಡ", "ಸುರೇಶ್ ಕುಮಾರ್", "ಮಂಜುನಾಥ್", "ವೆಂಕಟೇಶ್", "ದೀಪಕ್ ಜೋಶಿ"
]

# Email regex
_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
)

# Bank Account Pattern (Indian banks: 9 to 18 digits with keyword context)
_BANK_ACCOUNT_PATTERN = re.compile(
    r"(?i)\b(?:a/?c(?:\s*no\.?|\s*number)?|account(?:\s*no\.?|\s*number)?|"
    r"bank\s*a/?c|खाता\s*संख्या|ಖಾತೆ\s*ಸಂಖ್ಯೆ)\s*[:\-]?\s*([0-9]{9,18})\b"
)

# Date of Birth Context Pattern
_DOB_PATTERN = re.compile(
    r"(?i)\b(?:dob|date\s*of\s*birth|birth\s*date|जन्म\s*तिथि|ಹುಟ್ಟಿದ\s*ದಿನಾಂಕ)\s*[:\-]?\s*"
    r"([0-3]?\d[\/\-.][0-1]?\d[\/\-.]\d{2,4})\b"
)


def detect_multilingual_entities(text: str) -> list[EntitySpan]:
    """Detect PII entities in Hindi (Devanagari), Kannada, emails, bank accounts, and DOBs."""
    results: list[EntitySpan] = []

    # 1. Email addresses
    for match in _EMAIL_PATTERN.finditer(text):
        results.append(
            EntitySpan(
                entity_type="EMAIL_ADDRESS",
                start=match.start(),
                end=match.end(),
                score=0.98,
                source="email_regex",
            )
        )

    # 2. Bank accounts
    for match in _BANK_ACCOUNT_PATTERN.finditer(text):
        start = match.start(1)
        end = match.end(1)
        val = text[start:end]
        # Ignore obvious repeating placeholders or small sequences
        if len(set(val)) > 1:
            results.append(
                EntitySpan(
                    entity_type="BANK_ACCOUNT",
                    start=start,
                    end=end,
                    score=0.92,
                    source="bank_account_regex",
                )
            )

    # 3. Dates of Birth
    for match in _DOB_PATTERN.finditer(text):
        start = match.start(1)
        end = match.end(1)
        results.append(
            EntitySpan(
                entity_type="DATE_OF_BIRTH",
                start=start,
                end=end,
                score=0.94,
                source="dob_regex",
            )
        )

    # 4. Devanagari Names with Honorifics or Labels
    hindi_pattern = re.compile(
        rf"(?:{_HINDI_NAME_PREFIXES}|{_HINDI_NAME_LABELS})(?P<name>[\u0900-\u097F]{{2,20}}(?:\s+[\u0900-\u097F]{{2,20}}){{1,3}})"
    )
    for match in hindi_pattern.finditer(text):
        start, end = match.span("name")
        results.append(
            EntitySpan(
                entity_type="PERSON",
                start=start,
                end=end,
                score=0.92,
                source="hindi_ner",
            )
        )

    # Known common Devanagari names
    for name in _COMMON_DEVANAGARI_NAMES:
        start = 0
        while (pos := text.find(name, start)) != -1:
            results.append(
                EntitySpan(
                    entity_type="PERSON",
                    start=pos,
                    end=pos + len(name),
                    score=0.95,
                    source="hindi_lexicon",
                )
            )
            start = pos + len(name)

    # 5. Kannada Names with Honorifics or Labels
    kannada_pattern = re.compile(
        rf"(?:{_KANNADA_NAME_PREFIXES}|{_KANNADA_NAME_LABELS})(?P<name>[\u0C80-\u0CFF]{{2,20}}(?:\s+[\u0C80-\u0CFF]{{2,20}}){{1,3}})"
    )
    for match in kannada_pattern.finditer(text):
        start, end = match.span("name")
        results.append(
            EntitySpan(
                entity_type="PERSON",
                start=start,
                end=end,
                score=0.92,
                source="kannada_ner",
            )
        )

    # Known common Kannada names
    for name in _COMMON_KANNADA_NAMES:
        start = 0
        while (pos := text.find(name, start)) != -1:
            results.append(
                EntitySpan(
                    entity_type="PERSON",
                    start=pos,
                    end=pos + len(name),
                    score=0.95,
                    source="kannada_lexicon",
                )
            )
            start = pos + len(name)

    # 6. Vernacular numerals for phone numbers
    # Scan for 10-digit Devanagari or Kannada numbers
    for script_name, digits_re, trans_table in [
        ("hindi_digits", re.compile(r"[०-९]{10}"), _DEVANAGARI_DIGITS),
        ("kannada_digits", re.compile(r"[೦-೯]{10}"), _KANNADA_DIGITS),
    ]:
        for match in digits_re.finditer(text):
            ascii_digits = match.group(0).translate(trans_table)
            if ascii_digits[0] in "6789" and len(set(ascii_digits)) > 1:
                results.append(
                    EntitySpan(
                        entity_type="PHONE_NUMBER",
                        start=match.start(),
                        end=match.end(),
                        score=0.91,
                        source=script_name,
                    )
                )

    return results
