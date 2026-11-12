# DPDP-Ready Privacy Gateway Evaluation

This directory contains the automated evaluation framework and benchmark metrics for the **DPDP-Ready Privacy Gateway for Enterprise LLMs**.

## Evaluation Methodology

The evaluation engine tests the gateway's ability to protect sensitive Indian Personally Identifiable Information (PII) before transmission to external LLMs, and correctly restore placeholders upon response receipt.

### Ground Truth Benchmark
- **Benchmark Corpus**: 50 synthetic Indian enterprise documents spanning 4 high-compliance domains:
  - 15 Loan applications (multi-borrowers, income slips, property addresses)
  - 15 KYC records (joint accounts, biometrics, EPIC voter IDs, UIDAI Aadhaar)
  - 10 Customer support tickets (passport queries, code-mixed Kannada/Hindi CRM logs)
  - 10 Insurance claims (corporate GSTIN, hospital bills, commercial policy claims)
- **Entity Types Tested**:
  - `PERSON`: Indian individual names across multiple states
  - `AADHAAR`: 12-digit UIDAI identifiers (4-digit grouped format)
  - `PAN`: 10-character Permanent Account Number format (`[A-Z]{5}[0-9]{4}[A-Z]`)
  - `GSTIN`: 15-character Goods and Services Tax Identification Number
  - `VOTER_ID`: 10-character Election Commission EPIC ID (`[A-Z]{3}[0-9]{7}`)
  - `PASSPORT`: Indian passport numbers (`[A-Z][0-9]{7}`)
  - `ADDRESS`: Indian residential and corporate addresses (localities, cities, pincodes)

### Metrics Formulae
1. **Precision**:
   $$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}$$
2. **Recall**:
   $$\text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}}$$
3. **F1-Score**:
   $$\text{F1} = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$
4. **Matching Mode**:
   Exact entity span & type matching: A detection is considered a True Positive (TP) if and only if both the predicted `type` and the exact character span `(start, end)` match the ground truth.
5. **Raw PII Leakage Count**:
   Verification of whether raw ground-truth PII entity strings appear in outbound sanitized payloads without being masked by placeholders `<ENTITY_TYPE_INDEX>`.
6. **Placeholder Reinsertion Accuracy**:
   Percentage of outbound placeholders `<ENTITY_X>` successfully replaced back with original local values in the final LLM response.
7. **Gateway Processing Latency**:
   End-to-end gateway overhead in milliseconds (min, average, max).

## How to Run Evaluation

```bash
# Generate the 50 synthetic documents
python dataset/generate_dataset.py

# Run benchmark evaluation
python evaluation/evaluate.py
```

Results are saved to:
- `evaluation/results.json`
- `frontend/public/evaluation-results.json` (consumed directly by the React dashboard)
