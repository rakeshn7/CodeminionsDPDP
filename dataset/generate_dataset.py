import csv
import json
import random
import re
from pathlib import Path

random.seed(42)

NAMES = [
    'Rahul Sharma', 'Priya Nair', 'Ananya Iyer', 'Sandeep Rao', 'Meera Singh', 'Arjun Patel',
    'Nisha Reddy', 'Karan Mehta', 'Kavya Reddy', 'Vikram Joshi', 'Ritika Gupta', 'Aman Khanna',
    'Divya Sethi', 'Neha Kulkarni', 'Harsh Vyas', 'Pooja Menon', 'Aditya Iyer', 'Shreya Nair',
    'Ishaan Kapoor', 'Tanvi Shah', 'Gaurav Bansal', 'Aisha Khan', 'Rohan Srivastava', 'Mitali Das'
]

CITIES = ['Bengaluru', 'Hyderabad', 'Pune', 'Mumbai', 'Chennai', 'Delhi', 'Kochi', 'Jaipur', 'Ahmedabad', 'Lucknow']
STREETS = ['MG Road', 'Jayanagar', 'Koramangala', 'Banjara Hills', 'Residency Road', 'Old Airport Road', 'Cubbon Park Road', 'Whitefield']


def generate_aadhaar():
    return ' '.join(f'{random.randint(1000, 9999)}' for _ in range(3))


def generate_pan():
    letters = ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(5))
    return f'{letters}{random.randint(1000, 9999)}{random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}'


def generate_gstin():
    return f'{random.randint(11, 99)}ABCDE{random.randint(1000, 9999)}F{random.randint(1, 9)}Z{random.randint(1, 9)}'


def generate_voter_id():
    return f'ABC{random.randint(1000000, 9999999)}'


def generate_passport():
    return random.choice(['Z', 'N', 'K', 'P']) + str(random.randint(1000000, 9999999))


def generate_address():
    house = random.randint(1, 999)
    city = random.choice(CITIES)
    street = random.choice(STREETS)
    return f'{house}, {street}, {city} {random.randint(110001, 560068)}'


def add_entity(entities, entity_type, value, start, end):
    entities.append({
        'type': entity_type,
        'value': value,
        'start': start,
        'end': end,
    })


def build_document(doc_id, category):
    name = random.choice(NAMES)
    aadhaar = generate_aadhaar()
    pan = generate_pan()
    gstin = generate_gstin()
    voter_id = generate_voter_id()
    passport = generate_passport()
    address = generate_address()

    text_components = []
    entities = []

    def append_text(value):
        start = len(''.join(text_components))
        text_components.append(value)
        return start, start + len(value)

    if category == 'Loan applications':
        phrase = f'Loan application for {name}. '
        start, end = append_text(phrase)
        person_start = start + len('Loan application for ')
        person_end = person_start + len(name)
        add_entity(entities, 'PERSON', name, person_start, person_end)

        text_components.append(f'PAN {pan}. Aadhaar {aadhaar}. ')
        pan_start = len(''.join(text_components)) - len(f'PAN {pan}. Aadhaar {aadhaar}. ') + len('PAN ')
        add_entity(entities, 'PAN', pan, pan_start, pan_start + len(pan))
        aadhaar_start = len(''.join(text_components)) - len(f'Aadhaar {aadhaar}. ') + len('Aadhaar ')
        add_entity(entities, 'AADHAAR', aadhaar, aadhaar_start, aadhaar_start + len(aadhaar))

        addr_text = f'Address: {address}. Requested amount: INR {random.randint(150000, 950000)}.'
        start, end = append_text(addr_text)
        add_entity(entities, 'ADDRESS', address, start + len('Address: '), start + len('Address: ') + len(address))
        text = ''.join(text_components)

    elif category == 'KYC documents':
        prefix = f'KYC verification record for {name}. '
        text_components.append(prefix)
        person_start = len(prefix) - len(name)
        add_entity(entities, 'PERSON', name, person_start, person_start + len(name))

        voter = f'Voter ID: {voter_id}. '
        text_components.append(voter)
        add_entity(entities, 'VOTER_ID', voter_id, len(''.join(text_components)) - len(voter) + len('Voter ID: '), len(''.join(text_components)) - len(voter) + len('Voter ID: ') + len(voter_id))

        aadhaar_text = f'Aadhaar {aadhaar}. '
        text_components.append(aadhaar_text)
        add_entity(entities, 'AADHAAR', aadhaar, len(''.join(text_components)) - len(aadhaar_text) + len('Aadhaar '), len(''.join(text_components)) - len(aadhaar_text) + len('Aadhaar ') + len(aadhaar))

        addr_text = f'Address: {address}. Please verify resident status.'
        text_components.append(addr_text)
        add_entity(entities, 'ADDRESS', address, len(''.join(text_components)) - len(addr_text) + len('Address: '), len(''.join(text_components)) - len(addr_text) + len('Address: ') + len(address))
        text = ''.join(text_components)

    elif category == 'Customer support tickets':
        text_components.append(f'Support ticket raised by {name}. ')
        add_entity(entities, 'PERSON', name, len('Support ticket raised by ') + 0, len('Support ticket raised by ') + len(name))
        text_components.append(f'Passport number: {passport}. ') 
        add_entity(entities, 'PASSPORT', passport, len(''.join(text_components)) - len(f'Passport number: {passport}. ') + len('Passport number: '), len(''.join(text_components)) - len(f'Passport number: {passport}. ') + len('Passport number: ') + len(passport))
        text_components.append(f'PAN: {pan}. Customer address {address}. Helpful in Kannada: "namma customer ge help maadbeku".')
        add_entity(entities, 'PAN', pan, len(''.join(text_components)) - len(f'PAN: {pan}. Customer address {address}. Helpful in Kannada: "namma customer ge help maadbeku".') + len('PAN: '), len(''.join(text_components)) - len(f'PAN: {pan}. Customer address {address}. Helpful in Kannada: "namma customer ge help maadbeku".') + len('PAN: ') + len(pan))
        add_entity(entities, 'ADDRESS', address, len(''.join(text_components)) - len(f'Customer address {address}. Helpful in Kannada: "namma customer ge help maadbeku".') + len('Customer address '), len(''.join(text_components)) - len(f'Customer address {address}. Helpful in Kannada: "namma customer ge help maadbeku".') + len('Customer address ') + len(address))
        text = ''.join(text_components)

    else:
        text_components.append(f'Insurance claim for {name}. ')
        add_entity(entities, 'PERSON', name, len('Insurance claim for '), len('Insurance claim for ') + len(name))
        text_components.append(f'GSTIN: {gstin}. ') 
        add_entity(entities, 'GSTIN', gstin, len(''.join(text_components)) - len(f'GSTIN: {gstin}. ') + len('GSTIN: '), len(''.join(text_components)) - len(f'GSTIN: {gstin}. ') + len('GSTIN: ') + len(gstin))
        text_components.append(f'Aadhaar {aadhaar}. Policy cover requested for {address}.')
        add_entity(entities, 'AADHAAR', aadhaar, len(''.join(text_components)) - len(f'Aadhaar {aadhaar}. Policy cover requested for {address}.') + len('Aadhaar '), len(''.join(text_components)) - len(f'Aadhaar {aadhaar}. Policy cover requested for {address}.') + len('Aadhaar ') + len(aadhaar))
        add_entity(entities, 'ADDRESS', address, len(''.join(text_components)) - len(f'Policy cover requested for {address}.') + len('Policy cover requested for '), len(''.join(text_components)) - len(f'Policy cover requested for {address}.') + len('Policy cover requested for ') + len(address))
        text = ''.join(text_components)

    doc = {
        'document_id': doc_id,
        'category': category,
        'text': text,
        'entities': entities,
    }
    return doc


def make_dataset():
    categories = {
        'Loan applications': 15,
        'KYC documents': 15,
        'Customer support tickets': 10,
        'Insurance claims': 10,
    }

    documents = []
    for category, count in categories.items():
        for idx in range(count):
            doc_id = f'{category.lower().replace(" ", "-")}-{idx + 1:02d}'
            documents.append(build_document(doc_id, category))

    return documents


def save_outputs(documents):
    output_dir = Path(__file__).resolve().parent
    json_path = output_dir / 'synthetic_documents.json'
    csv_path = output_dir / 'synthetic_documents.csv'
    ground_truth_path = output_dir / 'ground_truth.json'

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
    documents = make_dataset()
    save_outputs(documents)
    print(f'Generated {len(documents)} synthetic documents in dataset/')
