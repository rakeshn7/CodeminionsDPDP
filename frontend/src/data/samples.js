export const sampleDocuments = [
  {
    id: 'loan-1',
    title: 'Loan Application – Rahul Verma (Co-applicant & PII)',
    category: 'Loan applications',
    text: 'Housing loan application for primary applicant Rahul Sharma (PAN: ABCDE1234F, Aadhaar: 9876 5432 1098) and co-applicant Meera Singh (PAN: FGHIJ5678K). Residential address: 15, MG Road, Bengaluru 560001. Requested sanction amount is INR 45,00,000 for property purchase.',
  },
  {
    id: 'kyc-1',
    title: 'KYC Verification – Priya Nair (Voter ID & UIDAI)',
    category: 'KYC documents',
    text: 'Customer onboarding KYC docket. Name of customer: Priya Nair. Official identity proof: Voter Identity ABC1234567 and UIDAI Aadhaar 4321 9876 5432. Residential domicile: 42, 3rd Cross, Jayanagar, Bengaluru 560041. Dastavej check ho gaye hain, kripya approval finalize karein.',
  },
  {
    id: 'support-1',
    title: 'Support Grievance – Ananya Iyer (Code-mixed Kannada)',
    category: 'Customer support tickets',
    text: 'Customer grievance ticket #IN-84219. Escalation logged by customer Ananya Iyer. Registered PAN on file is LMNOP6789Q, Passport ID: Z9876543. Billing delivery address: 8-2-293, Road No. 12, Banjara Hills, Hyderabad 500034. Issue: International payment declined during forex transaction. Internal note: Namma customer ge urgent help maadbeku, priority support required.',
  },
  {
    id: 'insurance-1',
    title: 'Corporate Health Claim – Sandeep Rao (GSTIN & Hospital)',
    category: 'Insurance claims',
    text: 'Corporate health insurance reimbursement claim. Insured employee: Sandeep Rao. Employer GSTIN: 29ABCDE1234F1Z5, PAN: ABCDE1234F, Aadhaar: 1234 5678 9012. Hospitalization location & patient residence: 64, Residency Road, Pune 411001. Total hospitalization expenses INR 1,85,000. All hospital bills verified.',
  },
  {
    id: 'multi-person-1',
    title: 'Commercial Property & Multiple Entities',
    category: 'Insurance claims',
    text: 'Commercial fire and transit insurance claim dossier. Claimant: Arjun Patel. Corporate GSTIN: 27XYZAB9876C1Z3. Policyholder Aadhaar: 8765 4321 2109. Insured business premises address: 100 Feet Road, Indiranagar, Bengaluru 560038. Surveyor assessed loss at INR 6,50,000. Final settlement note dispatched to Arjun Patel.',
  },
]

export const defaultPolicy = {
  purpose: 'KYC verification',
  active: false,
  rules: {
    PERSON: 'Mask',
    AADHAAR: 'Mask',
    PAN: 'Mask',
    GSTIN: 'Block',
    VOTER_ID: 'Mask',
    PASSPORT: 'Block',
    ADDRESS: 'Mask',
  },
}

export const defaultAuditData = [
  {
    request_id: 'REQ-1001',
    timestamp: '2026-11-12T08:10:00Z',
    external_model: 'gpt-4o-mini',
    entity_types: ['PERSON', 'AADHAAR', 'PAN'],
    sanitized_payload: 'Housing loan proposal for primary applicant <PERSON_1> (PAN: <PAN_1>, Aadhaar: <AADHAAR_1>). Outbound safe.',
    leakage_status: 'safe',
    latency_ms: 115,
    restoration_status: 'restored',
  },
  {
    request_id: 'REQ-1002',
    timestamp: '2026-11-12T08:25:00Z',
    external_model: 'claude-3-5-sonnet',
    entity_types: ['ADDRESS', 'GSTIN'],
    sanitized_payload: 'Corporate health insurance claim. Employer GSTIN: <GSTIN_1>, Hospital address: <ADDRESS_1>.',
    leakage_status: 'safe',
    latency_ms: 132,
    restoration_status: 'restored',
  },
  {
    request_id: 'REQ-1003',
    timestamp: '2026-11-12T08:42:00Z',
    external_model: 'gpt-4o',
    entity_types: ['PERSON', 'PASSPORT', 'PAN'],
    sanitized_payload: 'Customer escalation for <PERSON_1>. Passport <PASSPORT_1> and PAN <PAN_1> verified.',
    leakage_status: 'safe',
    latency_ms: 98,
    restoration_status: 'restored',
  },
]
