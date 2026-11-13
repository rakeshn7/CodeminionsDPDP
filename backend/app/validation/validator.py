from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any, Callable

from app.validation.verhoeff import validate_verhoeff


@dataclass
class ValidationFinding:
    category: str  # "PHONE", "EMAIL", "PAN", "AADHAAR", "DATES", "DOCUMENT_DATA"
    severity: str  # "ERROR", "WARNING", "INFO"
    location: str  # "Page 1", "Line 4", etc.
    field: str  # "Phone Number", "Email Address", "PAN", "Aadhaar", etc.
    masked_value: str
    explanation: str
    suggestion: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Masking helpers for validation findings
def mask_phone(val: str) -> str:
    digits = re.sub(r"\D", "", val)
    if len(digits) >= 6:
        return f"{digits[:2]}{'X' * (len(digits) - 4)}{digits[-2:]}"
    return "XX" * len(val)


def mask_email(val: str) -> str:
    if "@" in val:
        user, domain = val.split("@", 1)
        user_m = f"{user[0]}***{user[-1]}" if len(user) > 2 else "***"
        dom_parts = domain.split(".", 1)
        dom_name = dom_parts[0]
        ext = dom_parts[1] if len(dom_parts) > 1 else "com"
        dom_m = f"{dom_name[0]}***{dom_name[-1]}" if len(dom_name) > 2 else "***"
        return f"{user_m}@{dom_m}.{ext}"
    return "***@***"


def mask_pan(val: str) -> str:
    compact = re.sub(r"[ -]", "", val).upper()
    if len(compact) >= 5:
        return f"{compact[:2]}{'X' * (len(compact) - 4)}{compact[-2:]}"
    return "XXXXX"


def mask_aadhaar(val: str) -> str:
    digits = re.sub(r"\D", "", val)
    if len(digits) == 12:
        return f"{digits[:2]}XX-XXXX-XX{digits[-2:]}"
    return "XXXX-XXXX-XXXX"


def _determine_location(text: str, offset: int, pages: list[dict[str, Any]] | None = None) -> str:
    if pages:
        current_offset = 0
        for p in pages:
            p_len = p.get("char_count", len(p.get("text", "")))
            if current_offset <= offset <= current_offset + p_len:
                # Find line within page
                sub = p.get("text", "")[: max(0, offset - current_offset)]
                line_no = sub.count("\n") + 1
                return f"Page {p.get('page_number', 1)}, Line {line_no}"
            current_offset += p_len + 2

    # Fallback to line number in full text
    sub = text[:offset]
    line_no = sub.count("\n") + 1
    return f"Line {line_no}"


# --- Validators ---

def _validate_phones(text: str, pages: list[dict[str, Any]] | None) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    # 1. Matches with phone labels or keywords
    phone_context = re.compile(
        r"(?i)\b(?:phone|mobile|cell|contact|tel|mob|call|फोन|ಮೊಬೈಲ್)\s*[:\-]?\s*(?P<val>\+?[0-9][0-9 \-]{3,16}[0-9])"
    )
    # 2. Standalone potential Indian phone numbers
    standalone_numbers = re.compile(
        r"(?<!\d)(?:\+?91[ -]?)?[0-9]{5,13}(?!\d)"
    )

    found_spans = set()
    candidates = []

    for match in phone_context.finditer(text):
        span = match.span("val")
        found_spans.add(span)
        candidates.append((match.group("val"), span[0]))

    for match in standalone_numbers.finditer(text):
        span = match.span(0)
        # Avoid overlapping with already found context matches or standard IDs
        if not any(s[0] <= span[0] < s[1] for s in found_spans):
            val = match.group(0)
            # Only consider standalone numbers if length between 5 and 13 digits
            digits = re.sub(r"\D", "", val)
            if 5 <= len(digits) <= 13:
                candidates.append((val, span[0]))

    for raw_val, start_pos in candidates:
        digits = re.sub(r"\D", "", raw_val)
        if not digits:
            continue
        # Skip if looks like a date (e.g. 20240515) or PIN code (6 digits starting with 1-9 without phone context)
        if len(digits) == 6 and digits[0] in "12345678" and not any(k in text[max(0, start_pos - 15):start_pos].lower() for k in ["phone", "mobile", "tel", "call"]):
            continue

        loc = _determine_location(text, start_pos, pages)
        masked = mask_phone(raw_val)

        if digits.startswith("91") and len(digits) in (12, 13):
            digits = digits[2:]
        elif digits.startswith("0") and len(digits) == 11:
            digits = digits[1:]

        if len(digits) < 10 or len(digits) > 10:
            if 5 <= len(digits) <= 9 or len(digits) in (11, 12):
                findings.append(
                    ValidationFinding(
                        category="PHONE",
                        severity="ERROR",
                        location=loc,
                        field="Phone Number",
                        masked_value=masked,
                        explanation=f"Invalid Indian mobile number length ({len(digits)} digits found). Valid mobile numbers require 10 digits.",
                        suggestion="Verify that the mobile number contains exactly 10 digits excluding country code.",
                        confidence=0.98,
                    )
                )
        elif digits[0] not in "6789":
            findings.append(
                ValidationFinding(
                    category="PHONE",
                    severity="ERROR",
                    location=loc,
                    field="Phone Number",
                    masked_value=masked,
                    explanation=f"Invalid mobile number prefix '{digits[0]}'. Indian mobile numbers must start with 6, 7, 8, or 9.",
                    suggestion="Ensure the mobile number starts with an authorized Indian telecom prefix (6, 7, 8, or 9).",
                    confidence=0.96,
                )
            )
        elif len(set(digits)) == 1:
            findings.append(
                ValidationFinding(
                    category="PHONE",
                    severity="WARNING",
                    location=loc,
                    field="Phone Number",
                    masked_value=masked,
                    explanation="Suspicious dummy phone number consisting of a single repeating digit.",
                    suggestion="Confirm whether this is a placeholder or a legitimate subscriber contact.",
                    confidence=0.95,
                )
            )

    return findings


def _validate_emails(text: str, pages: list[dict[str, Any]] | None) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    # Match potential email attempts (including missing domain e.g. "support@" or missing TLD)
    email_candidates = re.compile(
        r"(?i)\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]*"
    )
    for match in email_candidates.finditer(text):
        val = match.group(0).strip(" ,;:")
        loc = _determine_location(text, match.start(), pages)
        masked = mask_email(val)

        if val.endswith("@") or "@" not in val or not val.split("@")[-1].strip():
            findings.append(
                ValidationFinding(
                    category="EMAIL",
                    severity="ERROR",
                    location=loc,
                    field="Email Address",
                    masked_value=masked,
                    explanation="Incomplete email address: missing domain name after '@'.",
                    suggestion="Provide the complete domain name (e.g. @domain.com).",
                    confidence=0.99,
                )
            )
        elif "." not in val.split("@")[-1] or val.endswith("."):
            findings.append(
                ValidationFinding(
                    category="EMAIL",
                    severity="ERROR",
                    location=loc,
                    field="Email Address",
                    masked_value=masked,
                    explanation="Invalid email domain formatting: missing top-level domain (TLD) extension.",
                    suggestion="Ensure domain has a valid extension (e.g. .com, .in, .org).",
                    confidence=0.97,
                )
            )

    return findings


# Comprehensive geographic locations (Indian cities, states, UTs, world capitals/countries, IT hubs/localities)
_COMMON_LOCATIONS = frozenset([
    # Major Indian Cities & Towns
    "bengaluru", "bangalore", "mumbai", "delhi", "new delhi", "kolkata", "calcutta", "chennai", "madras",
    "hyderabad", "pune", "ahmedabad", "jaipur", "surat", "lucknow", "kanpur", "nagpur", "indore", "thane",
    "bhopal", "visakhapatnam", "patna", "vadodara", "ghaziabad", "ludhiana", "agra", "nashik", "faridabad",
    "meerut", "rajkot", "varanasi", "srinagar", "aurangabad", "dhanbad", "amritsar", "navi mumbai", "allahabad",
    "prayagraj", "ranchi", "howrah", "coimbatore", "jabalpur", "gwalior", "vijayawada", "jodhpur", "madurai",
    "raipur", "kota", "guwahati", "chandigarh", "solapur", "hubballi", "hubli", "dharwad", "mysuru", "mysore",
    "tiruchirappalli", "bareilly", "aligarh", "tiruppur", "moradabad", "jalandhar", "bhubaneswar", "salem",
    "warangal", "guntur", "bhiwandi", "saharanpur", "gorakhpur", "bikaner", "amravati", "noida", "jamshedpur",
    "bhilai", "cuttack", "firozabad", "kochi", "cochin", "nellore", "bhavnagar", "dehradun", "durgapur",
    "asansol", "rourkela", "nanded", "kolhapur", "ajmer", "akola", "gulbarga", "kalaburagi", "jamnagar",
    "ujjain", "loni", "siliguri", "jhansi", "ulhasnagar", "jammu", "sangli", "mangaluru", "mangalore",
    "erode", "belagavi", "belgaum", "ambattur", "tirunelveli", "malegaon", "gaya", "udaipur", "kakinada",
    "davanagere", "kozhikode", "calicut", "bellary", "ballari", "shimoga", "shivamogga", "tumkur", "tumakuru",
    "bidar", "bijapur", "vijayapura", "raichur", "bagalkot", "hospet", "hosapete", "karwar", "udupi",
    "panaji", "margao", "vasco da gama", "gandhinagar", "anand", "morbi", "surendranagar", "bharuch",
    # Indian States & Union Territories
    "karnataka", "maharashtra", "tamil nadu", "kerala", "andhra pradesh", "telangana", "uttar pradesh",
    "madhya pradesh", "gujarat", "rajasthan", "west bengal", "bihar", "punjab", "haryana", "odisha",
    "assam", "jharkhand", "chhattisgarh", "uttarakhand", "himachal pradesh", "goa", "tripura", "meghalaya",
    "manipur", "nagaland", "arunachal pradesh", "mizoram", "sikkim", "ladakh", "puducherry", "pondicherry",
    "andaman and nicobar", "dadra and nagar haveli", "daman and diu", "lakshadweep",
    # Prominent Localities / Neighborhoods
    "indiranagar", "koramangala", "whitefield", "jayanagar", "malleshwaram", "marathahalli", "bellandur",
    "electronic city", "hebbal", "rajajinagar", "banashankari", "btm layout", "hsr layout", "sarjapur",
    "bandra", "andheri", "juhu", "colaba", "borivali", "dadar", "powai", "worli", "chembur", "kurla",
    "connaught place", "karol bagh", "chandni chowk", "saket", "hauz khas", "dwarka", "rohini",
    # Countries & Global Capitals
    "india", "usa", "united states", "uk", "united kingdom", "canada", "australia", "germany", "france",
    "japan", "china", "singapore", "dubai", "london", "new york", "paris", "tokyo", "sydney", "toronto",
    "berlin", "san francisco", "chicago", "texas", "california", "florida", "washington", "russia", "brazil",
])

# Comprehensive common objects, products, appliances, tools, food, furniture, and vehicles
_COMMON_ITEMS_AND_PRODUCTS = frozenset([
    # Household & Furniture
    "cook", "chair", "table", "desk", "bed", "sofa", "couch", "bench", "stool", "cabinet", "shelf",
    "cupboard", "wardrobe", "drawer", "pillow", "blanket", "cushion", "mat", "carpet", "curtain", "door",
    "window", "mirror", "clock", "lamp", "fan", "light", "bulb", "switch", "dining table", "office chair",
    # Electronics, Gadgets & Peripherals
    "laptop", "computer", "pc", "desktop", "mobile", "phone", "smartphone", "cellphone", "tablet", "ipad",
    "charger", "cable", "mouse", "keyboard", "monitor", "screen", "printer", "scanner", "camera", "headphone",
    "headphones", "earphone", "earphones", "earbuds", "speaker", "speakers", "microphone", "mic",
    "projector", "television", "tv", "remote", "battery", "router", "modem", "pendrive", "usb",
    "smart phone", "wrist watch", "wall clock", "air conditioner", "ac", "refrigerator", "fridge",
    # Kitchenware, Utensils & Food
    "spoon", "fork", "knife", "plate", "bowl", "cup", "mug", "glass", "bottle", "water bottle", "jug",
    "pan", "pot", "cooker", "stove", "oven", "microwave", "blender", "mixer", "grinder", "kettle", "toaster",
    "dish", "utensil", "utensils", "coffee mug", "tea cup", "water heater", "washing machine",
    "apple", "banana", "mango", "orange", "grape", "lemon", "potato", "tomato", "onion", "rice", "wheat",
    "bread", "butter", "cheese", "milk", "tea", "coffee", "water", "juice", "oil", "salt", "sugar",
    "egg", "meat", "fish", "soup", "salad", "cake", "biscuit", "cookie", "pizza", "burger", "sandwich",
    "noodle", "noodles", "pasta",
    # Stationery, School & Office Items
    "book", "notebook", "pen", "pencil", "eraser", "sharpener", "ruler", "scale", "marker", "highlighter",
    "paper", "sheet", "envelope", "folder", "file", "stapler", "scissors", "tape", "glue", "chalk",
    "duster", "board", "whiteboard", "blackboard", "calculator", "diary", "calendar",
    # Bags, Clothing & Accessories
    "bag", "backpack", "handbag", "purse", "wallet", "suitcase", "box", "carton", "packet", "shirt",
    "t-shirt", "pant", "pants", "trousers", "jeans", "shorts", "dress", "skirt", "jacket", "coat",
    "sweater", "hoodie", "cap", "hat", "helmet", "shoe", "shoes", "boot", "boots", "sandal", "sandals",
    "slipper", "slippers", "sock", "socks", "glove", "gloves", "belt", "tie", "watch", "ring", "necklace",
    "bracelet", "glasses", "sunglasses", "mask", "umbrella",
    # Vehicles & Transportation
    "car", "bus", "train", "flight", "plane", "airplane", "aeroplane", "bike", "bicycle", "cycle",
    "motorcycle", "scooter", "auto", "rickshaw", "truck", "lorry", "van", "jeep", "boat", "ship",
    "metro", "tram", "helicopter", "tractor", "ambulance", "taxi", "cab",
    # Tools & Hardware
    "hammer", "wrench", "screwdriver", "pliers", "saw", "drill", "nail", "screw", "nut", "bolt",
    "pipe", "wire", "rope", "chain", "lock", "key", "ladder", "bucket", "broom", "mop", "brush",
    "sponge", "soap", "towel", "shampoo", "paste", "toothbrush", "drill machine",
    # Animals / Pets
    "dog", "cat", "cow", "goat", "sheep", "horse", "donkey", "monkey", "elephant", "tiger", "lion",
    "bear", "deer", "rabbit", "rat", "bird", "pigeon", "crow", "sparrow", "parrot", "peacock", "snake",
    "duck", "hen", "chicken",
])

# Occupations & roles when mistakenly entered into the personal name field
_COMMON_OCCUPATIONS = frozenset([
    "student", "teacher", "professor", "doctor", "nurse", "engineer", "driver", "farmer", "lawyer",
    "advocate", "police", "officer", "clerk", "manager", "director", "worker", "laborer", "mechanic",
    "electrician", "plumber", "carpenter", "tailor", "barber", "security", "guard", "chef", "waiter",
    "accountant", "developer", "programmer", "architect", "designer", "pilot", "soldier", "cashier",
])

# Placeholders and test values
_PLACEHOLDER_NAMES = frozenset([
    "test", "demo", "sample", "unknown", "none", "null", "undefined", "n/a", "na", "admin", "administrator",
    "user", "guest", "anonymous", "dummy", "placeholder", "xxx", "xyz", "asdf", "qwerty", "temp", "fake",
    "testing", "example",
])

# Common person names (single mononyms or first names) that must always be accepted without false positives
_KNOWN_PERSON_NAMES = frozenset([
    "rahul", "priya", "manoj", "suresh", "rajesh", "arjun", "ananya", "ramesh", "deepa", "vikram",
    "kavya", "amitabh", "sachin", "raghu", "rohit", "virat", "deepika", "sundar", "satya", "aarav",
    "sneha", "rohan", "pooja", "mohan", "swati", "naveen", "lakshmi", "syed", "harpreet", "gurpreet",
    "karan", "sunita", "anita", "divya", "neha", "vikas", "ajay", "vijay", "deepak", "sanjay", "anil",
    "sunil", "shweta", "kavita", "rekha", "ritu", "meena", "geeta", "seema", "asha", "usha", "shanti",
    "meera", "john", "david", "alice", "robert", "emily", "michael", "james", "sarah", "mary", "william",
    "anand", "prakash", "chetan", "prashant", "kiran", "shankar", "venkat", "santosh", "ashok", "ravi",
])

_ADDRESS_INDICATORS = re.compile(
    r"(?i)(?:"
    r"^\s*(?:#|no\.?|plot|flat|door|survey|house|building|bldg)\s*\d+|"
    r"^\s*\d+[/,-]\s*\d*|"
    r"\b\d+[A-Za-z]?\s+(?:cross|main|road|street|layout|nagar|block|sector|stage|phase)\b|"
    r"\b(?:road|street|avenue|lane|layout|nagar|colony|district|taluk|village|sector|"
    r"highway|cross|main\s+road|block|floor|flat|apartment|apartments|apt|building|house|"
    r"plot|door|phase|stage|extension|halli|pura|puram|pete|galli|chowk|marg|bazaar|society|"
    r"vihar|enclave|gardens|park|towers|residency|heights|estate|circle|rd|st|ave|ln)\b|"
    r"\b\d{6}\b"
    r")"
)

_NAME_FIELD_EXTRACTOR = re.compile(
    r"(?im)^\s*(?P<field>full\s*name|applicant(?:\s*name)?|customer(?:\s*name)?|"
    r"candidate(?:\s*name)?|employee(?:\s*name)?|patient(?:\s*name)?|person(?:\s*name)?|"
    r"user(?:\s*name)?|student\s*name|client(?:\s*name)?|beneficiary(?:\s*name)?|"
    r"account\s*holder(?:\s*name)?|name\s*of\s*(?:applicant|customer|candidate|person)|"
    r"name|नाम|पूरा\s*नाम|ಹೆಸರು|ಪೂರ್ಣ\s*ಹೆಸರು)"
    r"\s*(?:[:\-=\t|,]|\s{2,}|\s(?=[A-Za-z0-9#\u0900-\u097F\u0C80-\u0CFF]))\s*(?P<value>[^\r\n;]+)"
)


def _classify_name_field_candidate(
    value: str,
    name_classifier: Callable[[str], str | None] | None = None,
) -> tuple[bool, str, str, str]:
    """Classify whether a name candidate is an address, location, item, occupation, or valid personal name.

    Returns:
        (is_error, error_type, explanation, suggestion)
    """
    clean_val = value.strip(" \t.:,\"'")
    if not clean_val:
        return False, "", "", ""

    norm = re.sub(r"\s+", " ", clean_val.casefold())
    words = norm.split()

    # 1. Check for numerical digits in name (unless it's an address)
    has_digits = bool(re.search(r"\d", clean_val))
    is_address_pattern = bool(_ADDRESS_INDICATORS.search(clean_val))

    if is_address_pattern:
        return (
            True,
            "ADDRESS",
            f"The Full Name field contains an address or street ('{clean_val}'), not a valid person's name.",
            f"Enter the person's full legal name in this field. Move '{clean_val}' to the Address field.",
        )

    if has_digits:
        return (
            True,
            "INVALID",
            f"The Full Name field contains numerical digits ('{clean_val}'), which is invalid for a person's name.",
            "Ensure personal names contain only alphabetic characters and standard name prefixes.",
        )

    # 2. Check for explicit placeholder / test values
    if norm in _PLACEHOLDER_NAMES:
        return (
            True,
            "PLACEHOLDER",
            f"The Full Name field contains placeholder or test text ('{clean_val}'), not a valid person's name.",
            "Provide the actual legal name of the person or applicant.",
        )

    # 3. External classifier (Presidio / spaCy entity check if supplied)
    classifier_result = name_classifier(clean_val) if name_classifier else None

    # 4. Check for geographical locations (cities, states, countries)
    if norm in _COMMON_LOCATIONS or (len(words) == 1 and words[0] in _COMMON_LOCATIONS) or classifier_result == "LOCATION":
        return (
            True,
            "LOCATION",
            f"The Full Name field contains a location or geographical place name ('{clean_val}'), not a valid person's name.",
            f"Enter the person's legal name here. Place cities or regions ('{clean_val}') in the City or State field.",
        )

    # 5. Check for occupations / roles
    if norm in _COMMON_OCCUPATIONS or (len(words) == 1 and words[0] in _COMMON_OCCUPATIONS):
        return (
            True,
            "OCCUPATION",
            f"The Full Name field contains an occupation or role ('{clean_val}'), not a person's name.",
            "Enter a valid person's name (e.g., Rahul Sharma). Place professions in the Occupation field.",
        )

    # 6. Check for physical items, objects, appliances, tools, products, vehicles, food
    if (
        norm in _COMMON_ITEMS_AND_PRODUCTS
        or (len(words) == 1 and words[0] in _COMMON_ITEMS_AND_PRODUCTS)
        or classifier_result in {"PRODUCT", "FACILITY", "ORG"}
    ):
        return (
            True,
            "ITEM",
            f"The Full Name field contains an item or non-person object ('{clean_val}'), not a valid person's name.",
            "Enter a valid personal name (e.g., Rahul Sharma). Physical items or objects must not be entered in the name field.",
        )

    # 7. Check if known personal name or multi-part legitimate person name
    if norm in _KNOWN_PERSON_NAMES or (len(words) >= 2 and all(len(w) >= 2 for w in words)):
        # Valid personal name accepted!
        return False, "", "", ""

    # 8. Single token sanity check: if very short (1 char) or repeated characters (e.g. 'zzzzz')
    if len(clean_val) < 2:
        return (
            True,
            "INVALID",
            f"The Full Name field contains an invalid or too short name value ('{clean_val}').",
            "Provide the complete legal name of the person.",
        )
    if len(set(clean_val.casefold())) == 1 and len(clean_val) >= 3:
        return (
            True,
            "INVALID",
            f"The Full Name field contains repeated characters ('{clean_val}'), which is invalid for a person's name.",
            "Enter a legitimate human name.",
        )

    # If it reached here without matching any item/location/address/invalid rule, accept as valid name!
    return False, "", "", ""


def _validate_full_names(
    text: str,
    pages: list[dict[str, Any]] | None,
    name_classifier: Callable[[str], str | None] | None,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    for match in _NAME_FIELD_EXTRACTOR.finditer(text):
        raw_val = match.group("value").strip(" \t.:,\"'")
        if not raw_val:
            continue

        field_label = match.group("field").strip().title()
        is_error, error_type, explanation, suggestion = _classify_name_field_candidate(
            raw_val, name_classifier=name_classifier
        )

        if is_error:
            masked = f"{raw_val[0]}***{raw_val[-1]}" if len(raw_val) >= 3 else "***"
            findings.append(
                ValidationFinding(
                    category="PERSON_NAME",
                    severity="ERROR",
                    location=_determine_location(text, match.start("value"), pages),
                    field=field_label,
                    masked_value=masked,
                    explanation=explanation,
                    suggestion=suggestion,
                    confidence=0.97,
                )
            )

    return findings


def _validate_pans(text: str, pages: list[dict[str, Any]] | None) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    # Match PAN mentions and sequences
    pan_context = re.compile(
        r"(?i)\b(?:pan(?:\s*card|\s*number|\s*no\.?)?)\s*[:\-]?\s*(?P<val>[A-Za-z0-9]{5,12})\b"
    )
    for match in pan_context.finditer(text):
        val = match.group("val").upper()
        loc = _determine_location(text, match.start("val"), pages)
        masked = mask_pan(val)

        if len(val) != 10:
            findings.append(
                ValidationFinding(
                    category="PAN",
                    severity="ERROR",
                    location=loc,
                    field="PAN",
                    masked_value=masked,
                    explanation=f"Invalid PAN length ({len(val)} characters). Indian Permanent Account Number must be exactly 10 characters.",
                    suggestion="Verify that the PAN consists of 5 alphabetic characters, 4 digits, and 1 trailing letter.",
                    confidence=0.98,
                )
            )
        elif not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", val):
            # Check for common OCR or data-entry mistake: letter 'O' instead of digit '0'
            if re.fullmatch(r"[A-Z]{3}[A-Z][A-Z][0-9O]{4}[A-Z]", val) and "O" in val[5:9]:
                findings.append(
                    ValidationFinding(
                        category="PAN",
                        severity="ERROR",
                        location=loc,
                        field="PAN",
                        masked_value=masked,
                        explanation="Potential data-entry mistake: letter 'O' detected in the 4-digit numeric section of the PAN.",
                        suggestion="Replace letter 'O' with digit '0' in the numeric portion.",
                        confidence=0.95,
                    )
                )
            else:
                findings.append(
                    ValidationFinding(
                        category="PAN",
                        severity="ERROR",
                        location=loc,
                        field="PAN",
                        masked_value=masked,
                        explanation="Incorrect PAN structure. Expected format: 5 uppercase letters, 4 numbers, 1 uppercase letter.",
                        suggestion="Check the format against the official Income Tax Department card.",
                        confidence=0.97,
                    )
                )
        else:
            # 4th letter is the holder category
            status_char = val[3]
            valid_statuses = {"P": "Individual", "C": "Company", "H": "HUF", "F": "Firm", "A": "AOP",
                              "T": "Trust", "B": "Body of Individuals", "L": "Local Authority",
                              "J": "Artificial Juridical Person", "G": "Government"}
            if status_char not in valid_statuses:
                findings.append(
                    ValidationFinding(
                        category="PAN",
                        severity="WARNING",
                        location=loc,
                        field="PAN",
                        masked_value=masked,
                        explanation=f"PAN 4th character '{status_char}' is not a standard entity status code.",
                        suggestion="Verify whether this PAN was issued to an Individual (P), Company (C), or Firm (F).",
                        confidence=0.91,
                    )
                )

    return findings


def _validate_aadhaars(text: str, pages: list[dict[str, Any]] | None) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    aadhaar_context = re.compile(
        r"(?i)\b(?:aadhaar|aadhar|uidai|uid)\s*[:\-]?\s*(?P<val>[0-9]{4}[ -]?[0-9]{4}[ -]?[0-9]{4}|[0-9]{10,14})\b"
    )
    for match in aadhaar_context.finditer(text):
        raw = match.group("val")
        digits = re.sub(r"\D", "", raw)
        loc = _determine_location(text, match.start("val"), pages)
        masked = mask_aadhaar(raw)

        if len(digits) != 12:
            findings.append(
                ValidationFinding(
                    category="AADHAAR",
                    severity="ERROR",
                    location=loc,
                    field="Aadhaar Number",
                    masked_value=masked,
                    explanation=f"Invalid Aadhaar length ({len(digits)} digits). UIDAI Aadhaar must have exactly 12 digits.",
                    suggestion="Verify the 12-digit number against the official Aadhaar letter or e-Aadhaar.",
                    confidence=0.99,
                )
            )
        elif digits[0] in "01":
            findings.append(
                ValidationFinding(
                    category="AADHAAR",
                    severity="ERROR",
                    location=loc,
                    field="Aadhaar Number",
                    masked_value=masked,
                    explanation=f"Invalid Aadhaar start digit '{digits[0]}'. UIDAI numbers never begin with 0 or 1.",
                    suggestion="Check for leading zero or omitted initial digits.",
                    confidence=0.98,
                )
            )
        elif len(set(digits)) == 1:
            findings.append(
                ValidationFinding(
                    category="AADHAAR",
                    severity="WARNING",
                    location=loc,
                    field="Aadhaar Number",
                    masked_value=masked,
                    explanation="Suspicious dummy Aadhaar composed of repeating digits.",
                    suggestion="Ensure real UIDAI Aadhaar number is provided for compliance.",
                    confidence=0.97,
                )
            )
        else:
            # Check Verhoeff checksum algorithm
            if not validate_verhoeff(digits):
                findings.append(
                    ValidationFinding(
                        category="AADHAAR",
                        severity="WARNING",
                        location=loc,
                        field="Aadhaar Number",
                        masked_value=masked,
                        explanation="Aadhaar checksum failed the standard Verhoeff algorithm. (Format check only; does not query UIDAI).",
                        suggestion="Verify the exact digits of the Aadhaar number to avoid typographical errors.",
                        confidence=0.94,
                    )
                )
            else:
                findings.append(
                    ValidationFinding(
                        category="AADHAAR",
                        severity="INFO",
                        location=loc,
                        field="Aadhaar Number",
                        masked_value=masked,
                        explanation="Aadhaar format and Verhoeff checksum valid. (Format check only; does not claim identity verification).",
                        suggestion="No action needed.",
                        confidence=0.99,
                    )
                )

    return findings


def _validate_dates(text: str, pages: list[dict[str, Any]] | None) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    today = date.today()

    date_pattern = re.compile(
        r"(?i)\b(?:dob|date\s*of\s*birth|issue\s*date|expiry\s*date|valid\s*till|date)\s*[:\-]?\s*"
        r"(?P<val>(?P<d>\d{1,2})[\/\-.](?P<m>\d{1,2})[\/\-.](?P<y>\d{4}))\b"
    )

    for match in date_pattern.finditer(text):
        raw_val = match.group("val")
        loc = _determine_location(text, match.start("val"), pages)
        day_val = int(match.group("d"))
        month_val = int(match.group("m"))
        year_val = int(match.group("y"))

        # Check calendar validity
        try:
            parsed_date = date(year_val, month_val, day_val)
        except ValueError as exc:
            findings.append(
                ValidationFinding(
                    category="DATES",
                    severity="ERROR",
                    location=loc,
                    field="Calendar Date",
                    masked_value=raw_val,
                    explanation=f"Impossible calendar date: {raw_val} ({str(exc)}).",
                    suggestion="Verify day and month values against standard calendar limits.",
                    confidence=0.99,
                )
            )
            continue

        # Check future DOB
        context_window = text[max(0, match.start() - 25) : match.start()].lower()
        if "dob" in context_window or "birth" in context_window or "जन्म" in context_window:
            if parsed_date > today:
                findings.append(
                    ValidationFinding(
                        category="DATES",
                        severity="ERROR",
                        location=loc,
                        field="Date of Birth",
                        masked_value=raw_val,
                        explanation=f"Impossible future Date of Birth: {raw_val} cannot be in the future.",
                        suggestion="Verify and enter the correct birth year.",
                        confidence=0.98,
                    )
                )
            elif parsed_date.year < 1900:
                findings.append(
                    ValidationFinding(
                        category="DATES",
                        severity="WARNING",
                        location=loc,
                        field="Date of Birth",
                        masked_value=raw_val,
                        explanation=f"Suspicious birth year ({parsed_date.year}) earlier than 1900.",
                        suggestion="Verify whether a two-digit year was improperly expanded.",
                        confidence=0.92,
                    )
                )

    # Check for Issue Date > Expiry Date inconsistency
    issue_match = re.search(r"(?i)issue\s*date\s*[:\-]?\s*(\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{4})", text)
    expiry_match = re.search(r"(?i)expiry\s*date\s*[:\-]?\s*(\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{4})", text)
    if issue_match and expiry_match:
        try:
            id_parts = [int(p) for p in re.split(r"[\/\-.]", issue_match.group(1))]
            ed_parts = [int(p) for p in re.split(r"[\/\-.]", expiry_match.group(1))]
            i_date = date(id_parts[2], id_parts[1], id_parts[0])
            e_date = date(ed_parts[2], ed_parts[1], ed_parts[0])
            if i_date > e_date:
                findings.append(
                    ValidationFinding(
                        category="DATES",
                        severity="ERROR",
                        location="Document Dates",
                        field="Validity Dates",
                        masked_value=f"{issue_match.group(1)} > {expiry_match.group(1)}",
                        explanation=f"Contradictory dates: Issue Date ({issue_match.group(1)}) is after Expiry Date ({expiry_match.group(1)}).",
                        suggestion="Check document issue and expiration dates.",
                        confidence=0.96,
                    )
                )
        except Exception:
            pass

    return findings


def _validate_document_consistency(text: str, pages: list[dict[str, Any]] | None) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    # 1. Duplicate PAN or Aadhaar across distinct entities
    pan_matches = re.findall(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text)
    if len(pan_matches) > 1 and len(set(pan_matches)) == 1:
        # Check if multiple names exist
        names = re.findall(r"(?i)(?:primary applicant|co-applicant|nominee|claimant)\s*[:\-]?\s*([A-Za-z ]{3,30})", text)
        if len(names) >= 2 and names[0].strip().lower() != names[1].strip().lower():
            findings.append(
                ValidationFinding(
                    category="DOCUMENT_DATA",
                    severity="WARNING",
                    location="Document Body",
                    field="Identification Data",
                    masked_value=mask_pan(pan_matches[0]),
                    explanation="Duplicate PAN identifier detected across multiple distinct named individuals.",
                    suggestion="Verify that each applicant or nominee has provided their own unique PAN card.",
                    confidence=0.90,
                )
            )

    # 2. Financial contradiction: Stated monthly income vs requested EMI
    income_match = re.search(r"(?i)(?:monthly\s*income|salary)\s*[:\-]?\s*(?:inr|rs\.?)?\s*([0-9,]+)", text)
    emi_match = re.search(r"(?i)(?:monthly\s*emi|emi|installment)\s*[:\-]?\s*(?:inr|rs\.?)?\s*([0-9,]+)", text)
    if income_match and emi_match:
        try:
            inc = float(income_match.group(1).replace(",", ""))
            emi = float(emi_match.group(1).replace(",", ""))
            if emi > inc and inc > 0:
                findings.append(
                    ValidationFinding(
                        category="DOCUMENT_DATA",
                        severity="WARNING",
                        location="Financial Details",
                        field="Loan Application Data",
                        masked_value=f"Income: INR {int(inc)} vs EMI: INR {int(emi)}",
                        explanation=f"Contradictory financial values: Proposed monthly EMI (INR {int(emi):,}) exceeds reported monthly income (INR {int(inc):,}).",
                        suggestion="Confirm applicant financial solvency or co-borrower income pool.",
                        confidence=0.91,
                    )
                )
        except Exception:
            pass

    # 3. Blank required fields
    blank_field_pattern = re.compile(
        r"(?i)\b(?P<field>pan|aadhaar|address|contact|email|phone)\s*[:\-]\s*(?:\[blank\]|nil|n/?a|none|\s*(?=\n|$))"
    )
    for match in blank_field_pattern.finditer(text):
        field_name = match.group("field").capitalize()
        loc = _determine_location(text, match.start(), pages)
        findings.append(
            ValidationFinding(
                category="DOCUMENT_DATA",
                severity="INFO",
                location=loc,
                field=field_name,
                masked_value="[BLANK]",
                explanation=f"Explicit empty or missing value detected for field '{field_name}'.",
                suggestion=f"Confirm whether '{field_name}' is required for this enterprise workflow.",
                confidence=0.88,
            )
        )

    return findings


def validate_document_data(
    text: str,
    pages: list[dict[str, Any]] | None = None,
    name_classifier: Callable[[str], str | None] | None = None,
) -> list[ValidationFinding]:
    """Execute deterministic validation checks across phone, email, PAN, Aadhaar, dates, and document structure."""
    if not text:
        return []

    findings: list[ValidationFinding] = []
    findings.extend(_validate_phones(text, pages))
    findings.extend(_validate_emails(text, pages))
    findings.extend(_validate_full_names(text, pages, name_classifier))
    findings.extend(_validate_pans(text, pages))
    findings.extend(_validate_aadhaars(text, pages))
    findings.extend(_validate_dates(text, pages))
    findings.extend(_validate_document_consistency(text, pages))

    # Sort findings by severity: ERROR > WARNING > INFO
    severity_order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
    findings.sort(key=lambda f: (severity_order.get(f.severity, 3), f.category, f.location))
    return findings
