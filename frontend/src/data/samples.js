export const sampleDocuments = [
  {
    id: 'loan-1',
    title: 'Loan Application – Rahul Verma',
    category: 'Loan applications',
    text: 'Loan application for Rahul Verma, mobile 9876543210. PAN ABCDE1234F, Aadhaar 1234 5678 9012. Current address: 15, MG Road, Bengaluru, Karnataka 560001. Requested amount: INR 7,50,000.',
  },
  {
    id: 'kyc-1',
    title: 'KYC Verification – Priya Nair',
    category: 'KYC documents',
    text: 'KYC verification record for Priya Nair. Voter ID: ABC1234567. Aadhaar 9876 5432 1098. Address: 42, 3rd Cross, Jayanagar, Bengaluru 560041. Customer wants account upgrade.',
  },
  {
    id: 'support-1',
    title: 'Customer Support Ticket – Ananya Iyer',
    category: 'Customer support tickets',
    text: 'Support ticket raised by Ananya Iyer regarding delayed payment. Passport number: Z9876543. PAN: LMNOP6789Q. Email support is available at ananya.iyer@example.com. Customer resides in Koramangala, Bengaluru.',
  },
  {
    id: 'insurance-1',
    title: 'Insurance Claim – Sandeep Rao',
    category: 'Insurance claims',
    text: 'Insurance claim for Sandeep Rao. GSTIN: 29ABCDE1234F1Z5. Aadhaar 4321 9876 5432. Address: 8-2-293, Road No. 4, Banjara Hills, Hyderabad 500034. Claim amount: INR 2,40,000.',
  },
  {
    id: 'multi-person-1',
    title: 'Multiple People in same document',
    category: 'KYC documents',
    text: 'KYC review for Rahul Sharma and Meera Singh. Rahul PAN ABCDE1234F and Mera Aadhaar 1111 2222 3333. Meera passport K1234567. Both residents of 64, Residency Road, Pune 411001.',
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

export const defaultMetrics = {
  totalRequests: 1874,
  piiEntitiesDetected: 3452,
  outboundLeakageIncidents: 18,
  avgLatencyMs: 214,
  reinsertionAccuracy: 96.4,
  requestTrend: [
    { day: 'Mon', requests: 180 },
    { day: 'Tue', requests: 210 },
    { day: 'Wed', requests: 195 },
    { day: 'Thu', requests: 260 },
    { day: 'Fri', requests: 290 },
    { day: 'Sat', requests: 245 },
    { day: 'Sun', requests: 320 },
  ],
  piiByCategory: [
    { name: 'PERSON', value: 920 },
    { name: 'AADHAAR', value: 610 },
    { name: 'PAN', value: 480 },
    { name: 'ADDRESS', value: 690 },
    { name: 'GSTIN', value: 240 },
    { name: 'PASSPORT', value: 150 },
  ],
}

export const defaultAuditData = [
  {
    request_id: 'REQ-1001',
    timestamp: '2026-11-12T08:10:00Z',
    external_model: 'gpt-4.1-mini',
    entity_types: ['PERSON', 'AADHAAR', 'PAN'],
    sanitized_payload: 'Customer Rahul Sharma requested a loan. <PERSON_1> is eligible. PAN <PAN_1> verified.',
    leakage_status: 'safe',
    latency_ms: 175,
    restoration_status: 'restored',
  },
  {
    request_id: 'REQ-1002',
    timestamp: '2026-11-12T08:25:00Z',
    external_model: 'claude-3.5-sonnet',
    entity_types: ['ADDRESS', 'GSTIN'],
    sanitized_payload: 'Address <ADDRESS_1> and GSTIN <GSTIN_1> were redacted before outbound transmission.',
    leakage_status: 'blocked',
    latency_ms: 221,
    restoration_status: 'partial',
  },
]
