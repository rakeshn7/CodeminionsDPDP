from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass


@dataclass
class LanguageProfile:
    primary_language: str
    detected_languages: list[str]
    is_mixed: bool
    scripts: dict[str, float]
    confidence: float
    notes: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


_LATIN_CHARS = re.compile(r"[A-Za-z]")
_SCRIPT_RANGES = (
    ("Devanagari", "Hindi", 0x0900, 0x097F),
    ("Bengali", "Bengali", 0x0980, 0x09FF),
    ("Gurmukhi", "Punjabi", 0x0A00, 0x0A7F),
    ("Gujarati", "Gujarati", 0x0A80, 0x0AFF),
    ("Odia", "Odia", 0x0B00, 0x0B7F),
    ("Tamil", "Tamil", 0x0B80, 0x0BFF),
    ("Telugu", "Telugu", 0x0C00, 0x0C7F),
    ("Kannada", "Kannada", 0x0C80, 0x0CFF),
    ("Malayalam", "Malayalam", 0x0D00, 0x0D7F),
    ("Sinhala", "Sinhala", 0x0D80, 0x0DFF),
    ("Thai", "Thai", 0x0E00, 0x0E7F),
    ("Lao", "Lao", 0x0E80, 0x0EFF),
    ("Tibetan", "Tibetan", 0x0F00, 0x0FFF),
    ("Myanmar", "Myanmar", 0x1000, 0x109F),
    ("Khmer", "Khmer", 0x1780, 0x17FF),
    ("Arabic", "Arabic-script", 0x0600, 0x06FF),
    ("Hebrew", "Hebrew", 0x0590, 0x05FF),
    ("Greek", "Greek", 0x0370, 0x03FF),
    ("Cyrillic", "Cyrillic", 0x0400, 0x052F),
    ("Hiragana", "Japanese", 0x3040, 0x309F),
    ("Katakana", "Japanese", 0x30A0, 0x30FF),
    ("Han", "Chinese/Japanese", 0x4E00, 0x9FFF),
)


def _script_name(character: str) -> str | None:
    codepoint = ord(character)
    if _LATIN_CHARS.fullmatch(character) or (
        unicodedata.category(character).startswith("L")
        and "LATIN" in unicodedata.name(character, "")
    ):
        return "Latin"
    for script, _, start, end in _SCRIPT_RANGES:
        if start <= codepoint <= end:
            return script
    return None

# Common Hindi vocabulary written in Latin script (Hinglish indicators)
_HINGLISH_WORDS = {
    "kripya", "dastavej", "naam", "pata", "aadhar", "aavedan", "karein", "hai", "hain",
    "karo", "nahi", "bhi", "yeh", "woh", "ke", "ki", "ka", "ko", "se", "aur", "dossier",
    "shikayat", "prathmik", "khata", "sankhya"
}

# Common Kannada vocabulary written in Latin script (Kanglish indicators)
_KANGLISH_WORDS = {
    "namma", "maadbeku", "ge", "inda", "illa", "beku", "hesaru", "vivaara", "dhaakhalegalu",
    "kodi", "maadi", "avara", "kelasa", "sahayata", "ondhu", "eradu"
}


def detect_document_language(text: str) -> LanguageProfile:
    """Analyze script frequencies and vocabulary to detect document languages and code-mixing."""
    if not text or not text.strip():
        return LanguageProfile(
            primary_language="English",
            detected_languages=["English"],
            is_mixed=False,
            scripts={"Latin": 1.0},
            confidence=0.5,
            notes="Empty or whitespace-only document default.",
        )

    clean_text = text.strip()
    script_counts: dict[str, int] = {}
    for character in clean_text:
        if not unicodedata.category(character).startswith("L"):
            continue
        script = _script_name(character)
        if script:
            script_counts[script] = script_counts.get(script, 0) + 1

    letter_total = sum(script_counts.values())
    if letter_total == 0:
        return LanguageProfile(
            primary_language="English",
            detected_languages=["English"],
            is_mixed=False,
            scripts={"Latin": 1.0},
            confidence=0.5,
            notes="Document contains no alphabetic scripts.",
        )

    scripts = {
        script: round(count / letter_total, 3)
        for script, count in script_counts.items()
    }
    script_languages = {
        script: language
        for script, language, _, _ in _SCRIPT_RANGES
    }

    detected_langs: list[str] = []
    is_mixed = False
    notes: list[str] = []

    if script_counts.get("Latin", 0) / letter_total >= 0.05:
        detected_langs.append("English")
        notes.append(
            "Latin script detected; script alone cannot reliably distinguish English "
            "from every other Latin-script language."
        )
    for script, count in script_counts.items():
        if script != "Latin" and count / letter_total >= 0.05:
            language = script_languages.get(script, script)
            if language not in detected_langs:
                detected_langs.append(language)

    unsupported_scripts = sorted(
        script
        for script, count in script_counts.items()
        if count / letter_total >= 0.05
        and script not in {"Latin", "Devanagari", "Kannada"}
    )
    if unsupported_scripts:
        notes.append(
            "Script detected, but local PII recognition is not validated for: "
            + ", ".join(unsupported_scripts)
            + "."
        )

    # Check for code-mixed romanized words
    lower_words = set(re.findall(r"\b[a-z]{2,15}\b", clean_text.lower()))
    hinglish_matches = lower_words.intersection(_HINGLISH_WORDS)
    kanglish_matches = lower_words.intersection(_KANGLISH_WORDS)

    if hinglish_matches and "Hindi" not in detected_langs:
        detected_langs.append("Hindi")
        notes.append(f"Romanized Hindi (Hinglish) keywords detected: {', '.join(sorted(hinglish_matches)[:4])}")
    if kanglish_matches and "Kannada" not in detected_langs:
        detected_langs.append("Kannada")
        notes.append(f"Romanized Kannada (Kanglish) keywords detected: {', '.join(sorted(kanglish_matches)[:4])}")

    # Determine primary language
    if not detected_langs:
        detected_langs = ["English"]

    if len(detected_langs) > 1:
        is_mixed = True

    if scripts.get("Kannada", 0) > 0.40:
        primary = "Kannada" if not is_mixed else f"Kannada + {'/'.join(l for l in detected_langs if l != 'Kannada')}"
    elif scripts.get("Devanagari", 0) > 0.40:
        primary = "Hindi" if not is_mixed else f"Hindi + {'/'.join(l for l in detected_langs if l != 'Hindi')}"
    elif len(scripts) == 1 and "Latin" not in scripts:
        primary = detected_langs[0]
    elif is_mixed:
        primary = f"English + {'/'.join(l for l in detected_langs if l != 'English')}"
    else:
        primary = detected_langs[0]

    confidence = (0.90 if letter_total > 50 else 0.75) if not unsupported_scripts else 0.55

    return LanguageProfile(
        primary_language=primary,
        detected_languages=detected_langs,
        is_mixed=is_mixed,
        scripts=scripts,
        confidence=confidence,
        notes="; ".join(notes) if notes else None,
    )
