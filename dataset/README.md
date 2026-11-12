# DPDP Synthetic Benchmark Dataset

This directory contains 50 synthetic Indian enterprise documents designed and generated for benchmarking the **DPDP-Ready Privacy Gateway for Enterprise LLMs**.

## Dataset Distribution

In accordance with hackathon requirements, the dataset contains exactly **50 synthetic documents** across four enterprise compliance workflows:

| Workflow Category | Document Count | Synthetic PII Entities Included |
|---|---:|---|
| **Loan applications** | 15 | Primary applicant & co-borrower names, PAN, Aadhaar, residential addresses, sanction amounts |
| **KYC documents** | 15 | Citizen names, UIDAI Aadhaar, Election Commission Voter ID (EPIC), residential addresses, joint nominee names |
| **Customer support tickets** | 10 | Customer names, Indian passport numbers, linked PAN cards, delivery addresses, Kannada & Hindi code-mixed escalation notes |
| **Insurance claims** | 10 | Corporate health & commercial fire claimants, corporate GSTIN, PAN, Aadhaar, hospital & business premises addresses |
| **Total** | **50** | **182 ground-truth entity spans across 7 PII types** |

## Supported Indian PII Categories

1. **PERSON**: Multi-regional Indian personal names (primary applicants, co-borrowers, nominees, claimants).
2. **AADHAAR**: 12-digit UIDAI identifiers formatted in 4-digit groups (e.g. `9876 5432 1098`).
3. **PAN**: 10-character Permanent Account Number matching IT department format (`[A-Z]{5}[0-9]{4}[A-Z]`).
4. **GSTIN**: 15-character Goods and Services Tax Identification Number (`[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]`).
5. **VOTER_ID**: 10-character Election Commission EPIC identifier (`[A-Z]{3}[0-9]{7}`).
6. **PASSPORT**: Indian travel passport number (`[A-Z][0-9]{7}`).
7. **ADDRESS**: Multi-component Indian addresses including house numbers, streets/roads, localities, cities, and 6-digit postal pincodes.

## Synthetic & Privacy Safety Guarantee

> [!IMPORTANT]
> All personal names, addresses, identification numbers, and contact records are **100% fictional and synthetically generated**. No real personal data or active government identifiers are used.

## Exact Offset Verification

All entity annotations contain precise character start and end offsets `[start, end]` such that:
$$\text{document.text}[\text{start}:\text{end}] == \text{entity.value}$$
Verification passes with **0 offset mismatches across all 50 documents**.

## Files in this Directory

- `generate_dataset.py`: Python generation script that builds and validates the 50 documents.
- `synthetic_documents.json`: Complete JSON array of all 50 synthetic documents with embedded entity annotations.
- `synthetic_documents.csv`: Flattened tabular representation of all documents and entity lists.
- `ground_truth.json`: Structured ground truth specification used directly by `evaluation/evaluate.py`.

## Regenerating the Dataset

```bash
python dataset/generate_dataset.py
```
