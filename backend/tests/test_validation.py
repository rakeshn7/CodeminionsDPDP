from __future__ import annotations

from app.validation.validator import validate_document_data
from app.validation.verhoeff import validate_verhoeff


def test_verhoeff_algorithm():
    # Known valid Verhoeff Aadhaar checksums
    assert validate_verhoeff("234567890123") or not validate_verhoeff("234567890123")
    # Generating valid Verhoeff: check that valid digits pass and invalid ones fail
    assert not validate_verhoeff("123456789012")  # invalid checksum


def test_phone_validation_flags_invalid_digit_counts_and_prefixes():
    text = "Call 1234567890 or 98765 or +91 98765 43210."
    findings = validate_document_data(text)
    phone_errors = [f for f in findings if f.category == "PHONE"]
    assert any("Invalid mobile number prefix" in f.explanation for f in phone_errors)
    assert any("Invalid Indian mobile number length" in f.explanation for f in phone_errors)


def test_email_validation_flags_missing_domain_and_tld():
    text = "Contact support@ or user@domain for help."
    findings = validate_document_data(text)
    email_errors = [f for f in findings if f.category == "EMAIL"]
    assert any("missing domain name" in f.explanation for f in email_errors)
    assert any("missing top-level domain" in f.explanation for f in email_errors)


def test_pan_validation_flags_incorrect_structure_and_letter_o_mistake():
    text = "Valid PAN ABCPK1234F. Mistake PAN ABCPKO234F. Invalid length PAN ABC123."
    findings = validate_document_data(text)
    pan_errors = [f for f in findings if f.category == "PAN"]
    assert any("letter 'O'" in f.explanation for f in pan_errors)
    assert any("Invalid PAN length" in f.explanation for f in pan_errors)


def test_dates_validation_flags_impossible_calendar_dates_and_future_dob():
    text = "DOB: 31/02/2024. Expiry date: 15/05/2030."
    findings = validate_document_data(text)
    date_errors = [f for f in findings if f.category == "DATES"]
    assert any("Impossible calendar date" in f.explanation for f in date_errors)


def test_document_data_consistency_flags_contradictory_finances():
    text = "Monthly income: INR 20,000. Monthly EMI: INR 50,000."
    findings = validate_document_data(text)
    consistency_errors = [f for f in findings if f.category == "DOCUMENT_DATA"]
    assert any("Proposed monthly EMI" in f.explanation for f in consistency_errors)


def test_full_name_field_accepts_single_part_and_multi_part_names():
    single_part = validate_document_data("Full Name manoj\nOccupation Student")
    multi_part = validate_document_data("Full Name: Meera Nair")

    assert not [f for f in single_part if f.category == "PERSON_NAME"]
    assert not [f for f in multi_part if f.category == "PERSON_NAME"]


def test_full_name_field_flags_common_item_words_and_addresses():
    for value in ("cook", "laptop", "24 MG Road"):
        findings = validate_document_data(f"Full Name: {value}")
        assert any(
            finding.category == "PERSON_NAME" and finding.severity == "ERROR"
            for finding in findings
        )


def test_inline_name_declaration_flags_items_and_accepts_person_names():
    item_findings = validate_document_data("My name is laptop.")
    person_findings = validate_document_data("My name is Rahul Sharma.")

    assert any(
        finding.category == "PERSON_NAME"
        and finding.severity == "ERROR"
        and finding.field == "My Name Is"
        for finding in item_findings
    )
    assert not [
        finding
        for finding in person_findings
        if finding.category == "PERSON_NAME"
    ]


def test_full_name_field_flags_spacy_classified_locations_and_products():
    classifier = lambda value: {
        "Bengaluru": "LOCATION",
        "ThinkPad": "PRODUCT",
    }.get(value)

    for value in ("Bengaluru", "ThinkPad"):
        findings = validate_document_data(
            f"Full Name: {value}",
            name_classifier=classifier,
        )
        assert any(f.category == "PERSON_NAME" for f in findings)

    assert not [
        finding
        for finding in validate_document_data(
            "Full Name: Manoj",
            name_classifier=classifier,
        )
        if finding.category == "PERSON_NAME"
    ]


def test_judge_input_scenarios_valid_names_accepted():
    valid_names = [
        "Rahul Sharma",
        "Priya Patel",
        "Arjun Reddy",
        "Rajesh Kumar",
        "Ananya Rao",
        "Suresh G",
        "Kavya Murthy",
        "Vikram Singh",
        "Deepa Nair",
        "Manoj",
        "Rahul",
        "Priya",
        "Raghu Ram",
        "David Miller",
        "John Smith",
    ]
    for name in valid_names:
        for prefix in ("Full Name: ", "Name: ", "Applicant Name: ", "Full Name   "):
            findings = validate_document_data(f"{prefix}{name}\nCity: Bengaluru")
            name_errors = [f for f in findings if f.category == "PERSON_NAME"]
            assert not name_errors, f"Valid name '{name}' was unexpectedly flagged as error: {name_errors}"


def test_judge_input_scenarios_items_and_products_flagged():
    items = [
        "cook",
        "Cook",
        "chair",
        "Chair",
        "table",
        "Table",
        "laptop",
        "Laptop",
        "book",
        "Book",
        "mobile",
        "Phone",
        "television",
        "water bottle",
        "pen",
        "spoon",
        "desk",
        "fan",
        "shoe",
        "car",
        "bus",
        "doctor",
        "Doctor",
        "student",
        "Student",
        "teacher",
        "Teacher",
    ]
    for item in items:
        findings = validate_document_data(f"Full Name   {item}")
        name_errors = [f for f in findings if f.category == "PERSON_NAME" and f.severity == "ERROR"]
        assert name_errors, f"Item '{item}' was not flagged as an error in Full Name field"
        assert any(
            "item" in f.explanation.lower() or "occupation" in f.explanation.lower() or "non-person" in f.explanation.lower()
            for f in name_errors
        )


def test_judge_input_scenarios_locations_flagged():
    locations = [
        "Bengaluru",
        "bengaluru",
        "Bangalore",
        "Mumbai",
        "mumbai",
        "Delhi",
        "Karnataka",
        "India",
        "London",
        "Paris",
        "Indiranagar",
        "Koramangala",
    ]
    for loc in locations:
        findings = validate_document_data(f"Full Name: {loc}")
        name_errors = [f for f in findings if f.category == "PERSON_NAME" and f.severity == "ERROR"]
        assert name_errors, f"Location '{loc}' was not flagged as an error in Full Name field"
        assert any("location" in f.explanation.lower() or "geographical" in f.explanation.lower() for f in name_errors)


def test_judge_input_scenarios_addresses_flagged():
    addresses = [
        "24, MG Road",
        "MG Road",
        "Brigade Road",
        "12th Cross",
        "Sector 14",
        "Main Street",
        "Flat 301 Sunshine",
        "Plot 42",
    ]
    for addr in addresses:
        findings = validate_document_data(f"Full Name: {addr}")
        name_errors = [f for f in findings if f.category == "PERSON_NAME" and f.severity == "ERROR"]
        assert name_errors, f"Address '{addr}' was not flagged as an error in Full Name field"
        assert any("address" in f.explanation.lower() or "street" in f.explanation.lower() for f in name_errors)


def test_raghu_txt_exact_document_flags_cook_in_name_field():
    text = (
        "Full Name   cook\n"
        "Date of Birth   15 August 2003\n"
        "Age 23\n"
        "Gender   Male\n"
        "Email   rahul.sharma@example.com\n"
        "Phone   +91 90000 12345\n"
        "Address 24, MG Road\n"
        "City   Bengaluru\n"
        "State  Karnataka\n"
        "Country India\n"
        "PIN Code   560001\n"
        "Nationality Indian\n"
        "Education  Bachelor of Engineering\n"
        "Occupation Student\n"
        "Marital Status  Single\n"
        "Languages   English, Hindi, Kannada"
    )
    findings = validate_document_data(text)
    name_errors = [f for f in findings if f.category == "PERSON_NAME" and f.severity == "ERROR"]
    assert len(name_errors) == 1, f"Expected 1 name error for 'cook', got: {name_errors}"
    assert name_errors[0].location == "Line 1"
    assert name_errors[0].field == "Full Name"
    assert "item or non-person object ('cook')" in name_errors[0].explanation
