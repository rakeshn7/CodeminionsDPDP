import csv
import json
import random
from pathlib import Path

random.seed(42)

FIRST_NAMES = [
    'Rahul', 'Priya', 'Ananya', 'Sandeep', 'Meera', 'Arjun',
    'Nisha', 'Karan', 'Kavya', 'Vikram', 'Ritika', 'Aman',
    'Divya', 'Neha', 'Harsh', 'Pooja', 'Aditya', 'Shreya',
    'Ishaan', 'Tanvi', 'Gaurav', 'Aisha', 'Rohan', 'Mitali',
    'Suresh', 'Deepika', 'Rajesh', 'Sunita', 'Venkat', 'Lakshmi'
]

LAST_NAMES = [
    'Sharma', 'Nair', 'Iyer', 'Rao', 'Singh', 'Patel',
    'Reddy', 'Mehta', 'Joshi', 'Gupta', 'Khanna', 'Sethi',
    'Kulkarni', 'Vyas', 'Menon', 'Kapoor', 'Shah', 'Bansal',
    'Khan', 'Srivastava', 'Das', 'Kumar', 'Verma', 'Pillai'
]

CITIES_PINCODES = [
    ('Bengaluru', '560001'), ('Bengaluru', '560034'), ('Bengaluru', '560041'),
    ('Hyderabad', '500034'), ('Hyderabad', '500081'),
    ('Pune', '411001'), ('Pune', '411014'),
    ('Mumbai', '400001'), ('Mumbai', '400050'),
    ('Chennai', '600001'), ('Chennai', '600028'),
    ('Delhi', '110001'), ('Delhi', '110025'),
    ('Kochi', '682001'), ('Jaipur', '302001'),
    ('Ahmedabad', '380001'), ('Lucknow', '226001')
]

STREETS = [
    'MG Road', '100 Feet Road, Indiranagar', '3rd Cross, Jayanagar',
    'Road No. 12, Banjara Hills', 'Hitech City Main Road',
    'Residency Road', 'Old Airport Road', 'Whitefield Main Road',
    'FC Road, Shivaji Nagar', 'Linking Road, Bandra', 'Anna Salai',
    'Connaught Place, Barakhamba Road', 'Marine Drive'
]


def generate_name(exclude=None):
    for _ in range(50):
        name = f'{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}'
        if name != exclude:
            return name
    return 'Rahul Sharma'


def generate_aadhaar():
    return f'{random.randint(2000, 9999)} {random.randint(1000, 9999)} {random.randint(1000, 9999)}'


def generate_pan():
    letters = ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(3))
    entity_type = random.choice(['P', 'C', 'H', 'F', 'A', 'T'])
    surname_initial = random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    digits = f'{random.randint(1000, 9999)}'
    checksum = random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    return f'{letters}{entity_type}{surname_initial}{digits}{checksum}'


def generate_gstin(pan_val=None):
    state_code = f'{random.randint(10, 37):02d}'
    pan_part = pan_val if pan_val else generate_pan()
    entity_num = random.randint(1, 9)
    return f'{state_code}{pan_part}{entity_num}Z{random.randint(1, 9)}'


def generate_voter_id():
    prefix = ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(3))
    return f'{prefix}{random.randint(1000000, 9999999)}'


def generate_passport():
    prefix = random.choice(['Z', 'N', 'K', 'P', 'L', 'M'])
    return f'{prefix}{random.randint(1000000, 9999999)}'


def generate_address():
    house_num = random.randint(1, 999)
    street = random.choice(STREETS)
    city, pin = random.choice(CITIES_PINCODES)
    return f'{house_num}, {street}, {city} {pin}'


class DocumentBuilder:
    def __init__(self):
        self.text = ''
        self.entities = []

    def add_plain(self, text):
        self.text += text
        return self

    def add_entity(self, entity_type, value):
        start = len(self.text)
        self.text += value
        end = len(self.text)
        self.entities.append({
            'type': entity_type,
            'value': value,
            'start': start,
            'end': end,
        })
        return self


def build_loan_application(doc_id, index):
    primary_name = generate_name()
    pan = generate_pan()
    aadhaar = generate_aadhaar()
    address = generate_address()
    builder = DocumentBuilder()

    if index % 3 == 0:
        # Multi-person with co-borrower
        co_borrower = generate_name(exclude=primary_name)
        co_pan = generate_pan()
        builder.add_plain('Housing loan application for primary applicant ')
        builder.add_entity('PERSON', primary_name)
        builder.add_plain(' (PAN: ')
        builder.add_entity('PAN', pan)
        builder.add_plain(', Aadhaar: ')
        builder.add_entity('AADHAAR', aadhaar)
        builder.add_plain(') and co-applicant ')
        builder.add_entity('PERSON', co_borrower)
        builder.add_plain(' (PAN: ')
        builder.add_entity('PAN', co_pan)
        builder.add_plain('). Residential address: ')
        builder.add_entity('ADDRESS', address)
        builder.add_plain(f'. Requested sanction amount is INR {random.randint(25, 85)},00,000 for property purchase.')
    elif index % 3 == 1:
        # Repeated name and code-mixed phrasing
        builder.add_plain('Retail personal loan form. Applicant name: ')
        builder.add_entity('PERSON', primary_name)
        builder.add_plain('. Permanent Account Number: ')
        builder.add_entity('PAN', pan)
        builder.add_plain('. Current residential address: ')
        builder.add_entity('ADDRESS', address)
        builder.add_plain('. Aadhaar verification number: ')
        builder.add_entity('AADHAAR', aadhaar)
        builder.add_plain(f'. Monthly net salary INR {random.randint(65000, 185000)}. Kindly verify ')
        builder.add_entity('PERSON', primary_name)
        builder.add_plain(' bank statements. Kripya loan eligibility jaldi check karein.')
    else:
        # Standard commercial vehicle / MSME loan
        builder.add_plain('Commercial vehicle credit proposal submitted by ')
        builder.add_entity('PERSON', primary_name)
        builder.add_plain('. Identification details: Aadhaar: ')
        builder.add_entity('AADHAAR', aadhaar)
        builder.add_plain(', Tax ID PAN: ')
        builder.add_entity('PAN', pan)
        builder.add_plain('. Registered correspondence address: ')
        builder.add_entity('ADDRESS', address)
        builder.add_plain('. CIBIL score is 785. Disbursal requested to HDFC Bank account.')

    return {
        'document_id': doc_id,
        'category': 'Loan applications',
        'text': builder.text,
        'entities': builder.entities,
    }


def build_kyc_document(doc_id, index):
    primary_name = generate_name()
    aadhaar = generate_aadhaar()
    address = generate_address()
    voter_id = generate_voter_id()
    builder = DocumentBuilder()

    if index % 3 == 0:
        # Multiple people (joint KYC account holder)
        nominee_name = generate_name(exclude=primary_name)
        builder.add_plain('Periodic KYC re-verification record for account holder ')
        builder.add_entity('PERSON', primary_name)
        builder.add_plain('. Aadhaar card number: ')
        builder.add_entity('AADHAAR', aadhaar)
        builder.add_plain(', Voter ID card: ')
        builder.add_entity('VOTER_ID', voter_id)
        builder.add_plain('. Present address: ')
        builder.add_entity('ADDRESS', address)
        builder.add_plain('. Designated account nominee: ')
        builder.add_entity('PERSON', nominee_name)
        builder.add_plain('. Form 60 submitted and biometric verification complete.')
    elif index % 3 == 1:
        # Code-mixed Hindi / English
        builder.add_plain('Customer onboarding KYC docket. Name of customer: ')
        builder.add_entity('PERSON', primary_name)
        builder.add_plain('. Official identity proof: Voter Identity ')
        builder.add_entity('VOTER_ID', voter_id)
        builder.add_plain(' and UIDAI Aadhaar ')
        builder.add_entity('AADHAAR', aadhaar)
        builder.add_plain('. Residential domicile: ')
        builder.add_entity('ADDRESS', address)
        builder.add_plain('. Dastavej check ho gaye hain, kripya approval finalize karein.')
    else:
        # Repeated entity mention
        builder.add_plain('Mutual fund video-KYC compliance sheet. Verified citizen: ')
        builder.add_entity('PERSON', primary_name)
        builder.add_plain('. Aadhaar: ')
        builder.add_entity('AADHAAR', aadhaar)
        builder.add_plain('. Election commission EPIC: ')
        builder.add_entity('VOTER_ID', voter_id)
        builder.add_plain('. Permanent residence: ')
        builder.add_entity('ADDRESS', address)
        builder.add_plain('. Live geo-tagging matches address. Contact customer ')
        builder.add_entity('PERSON', primary_name)
        builder.add_plain(' for final OTP verification.')

    return {
        'document_id': doc_id,
        'category': 'KYC documents',
        'text': builder.text,
        'entities': builder.entities,
    }


def build_support_ticket(doc_id, index):
    customer_name = generate_name()
    passport = generate_passport()
    pan = generate_pan()
    address = generate_address()
    builder = DocumentBuilder()

    if index % 2 == 0:
        # Kannada code-mixed support ticket
        builder.add_plain('Customer grievance ticket #IN-')
        builder.add_plain(f'{random.randint(10000, 99999)}')
        builder.add_plain('. Escalation logged by customer ')
        builder.add_entity('PERSON', customer_name)
        builder.add_plain('. Registered PAN on file is ')
        builder.add_entity('PAN', pan)
        builder.add_plain(', Passport ID: ')
        builder.add_entity('PASSPORT', passport)
        builder.add_plain('. Billing delivery address: ')
        builder.add_entity('ADDRESS', address)
        builder.add_plain('. Issue: International payment declined during forex transaction. Internal note: Namma customer ge urgent help maadbeku, priority support required.')
    else:
        # Repeated name and Hindi code-mixed
        builder.add_plain('Priority CRM support request. User: ')
        builder.add_entity('PERSON', customer_name)
        builder.add_plain('. International passport identification: ')
        builder.add_entity('PASSPORT', passport)
        builder.add_plain('. Linked PAN card: ')
        builder.add_entity('PAN', pan)
        builder.add_plain('. Dispatch address: ')
        builder.add_entity('ADDRESS', address)
        builder.add_plain('. Client ')
        builder.add_entity('PERSON', customer_name)
        builder.add_plain(' reported unauthorized debit of INR 14,200. Turant card block kar diya gaya hai.')

    return {
        'document_id': doc_id,
        'category': 'Customer support tickets',
        'text': builder.text,
        'entities': builder.entities,
    }


def build_insurance_claim(doc_id, index):
    claimant_name = generate_name()
    pan = generate_pan()
    gstin = generate_gstin(pan)
    aadhaar = generate_aadhaar()
    address = generate_address()
    builder = DocumentBuilder()

    if index % 2 == 0:
        # Business health / group insurance claim with GSTIN and PAN
        builder.add_plain('Corporate health insurance reimbursement claim. Insured employee: ')
        builder.add_entity('PERSON', claimant_name)
        builder.add_plain('. Employer GSTIN: ')
        builder.add_entity('GSTIN', gstin)
        builder.add_plain(', PAN: ')
        builder.add_entity('PAN', pan)
        builder.add_plain(', Aadhaar: ')
        builder.add_entity('AADHAAR', aadhaar)
        builder.add_plain('. Hospitalization location & patient residence: ')
        builder.add_entity('ADDRESS', address)
        builder.add_plain(f'. Total hospitalization expenses INR {random.randint(80000, 450000)}. All hospital bills verified.')
    else:
        # Commercial property insurance claim
        builder.add_plain('Commercial fire and transit insurance claim dossier. Claimant: ')
        builder.add_entity('PERSON', claimant_name)
        builder.add_plain('. Corporate GSTIN: ')
        builder.add_entity('GSTIN', gstin)
        builder.add_plain('. Policyholder Aadhaar: ')
        builder.add_entity('AADHAAR', aadhaar)
        builder.add_plain('. Insured business premises address: ')
        builder.add_entity('ADDRESS', address)
        builder.add_plain(f'. Surveyor assessed loss at INR {random.randint(300000, 1800000)}. Final settlement note dispatched to ')
        builder.add_entity('PERSON', claimant_name)
        builder.add_plain('.')

    return {
        'document_id': doc_id,
        'category': 'Insurance claims',
        'text': builder.text,
        'entities': builder.entities,
    }


def make_dataset():
    distribution = [
        ('Loan applications', 15, build_loan_application),
        ('KYC documents', 15, build_kyc_document),
        ('Customer support tickets', 10, build_support_ticket),
        ('Insurance claims', 10, build_insurance_claim),
    ]

    documents = []
    for category_name, count, builder_fn in distribution:
        slug = category_name.lower().replace(' ', '-')
        for idx in range(count):
            doc_id = f'{slug}-{idx + 1:02d}'
            documents.append(builder_fn(doc_id, idx))

    return documents


def save_outputs(documents):
    output_dir = Path(__file__).resolve().parent
    json_path = output_dir / 'synthetic_documents.json'
    csv_path = output_dir / 'synthetic_documents.csv'
    ground_truth_path = output_dir / 'ground_truth.json'

    # Validate all offsets before writing
    mismatches = 0
    for doc in documents:
        text = doc['text']
        for ent in doc['entities']:
            actual = text[ent['start']:ent['end']]
            if actual != ent['value']:
                mismatches += 1
                print(f"ERROR: Offset mismatch in {doc['document_id']} for {ent['type']}: expected {ent['value']!r}, got {actual!r}")

    if mismatches > 0:
        raise ValueError(f'Validation failed with {mismatches} offset errors!')

    with json_path.open('w', encoding='utf-8') as handle:
        json.dump(documents, handle, ensure_ascii=False, indent=2)

    with csv_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=['document_id', 'category', 'original_text', 'entity_types', 'entity_values'])
        writer.writeheader()
        for doc in documents:
            writer.writerow({
                'document_id': doc['document_id'],
                'category': doc['category'],
                'original_text': doc['text'],
                'entity_types': '; '.join(entity['type'] for entity in doc['entities']),
                'entity_values': '; '.join(entity['value'] for entity in doc['entities']),
            })

    with ground_truth_path.open('w', encoding='utf-8') as handle:
        json.dump({
            'document_count': len(documents),
            'documents': documents,
        }, handle, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    docs = make_dataset()
    save_outputs(docs)
    print(f'Successfully generated and validated {len(docs)} synthetic documents in dataset/')
