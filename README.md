# DPDP-Ready Privacy Gateway for Enterprise LLMs

> **Enterprise AI Privacy & Compliance Console**  
> Built for Indian Enterprise LLM adoption in compliance with the **Digital Personal Data Protection (DPDP) Act, 2023** and **DPDP Rules, 2025**.

---

## 1. Project Overview

The **DPDP-Ready Privacy Gateway** is an enterprise cybersecurity solution that intercepts prompt payloads sent to third-party Large Language Models (LLMs), detects and redacts Indian Personally Identifiable Information (PII), transmits sanitized payloads with indexed placeholders (`<PERSON_1>`, `<AADHAAR_1>`, `<PAN_1>`), and locally reinserts the original sensitive data into the final AI response before presenting it to the end-user.

This repository contains the **Enterprise Frontend Dashboard**, **Synthetic Evaluation Dataset**, and **Evaluation Engine** developed for Person 2's role.

---

## 2. Technology Stack

- **Frontend Core**: React 19, Vite, Tailwind CSS
- **Icons & Visuals**: Lucide React
- **Charts & Graphs**: Recharts
- **HTTP Client**: Axios
- **Dataset & Evaluation**: Python 3, JSON, CSV
- **Code Quality**: Oxlint

---

## 3. Architecture & Project Layout

```text
CodeminionsDPDP/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx          # Top enterprise navigation bar
│   │   │   ├── Sidebar.jsx         # Collapsible sidebar with navigation routes
│   │   │   ├── StatCard.jsx        # Standardized telemetry KPI card
│   │   │   ├── OriginalInput.jsx   # Panel A: Original document input & upload
│   │   │   ├── SanitizedOutput.jsx # Panel B: Outbound payload with placeholder highlights
│   │   │   ├── FinalResponse.jsx   # Panel C: Reinserted AI response & restoration status
│   │   │   ├── EntityTable.jsx     # Detected entity map (colored badges, no raw PII)
│   │   │   ├── AuditTable.jsx      # Historical request audit table with expandable payload inspection
│   │   │   └── MetricCharts.jsx    # Recharts visualizations (trend, category pie, precision/recall)
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx       # Executive dashboard with KPIs & trend visualizations
│   │   │   ├── PrivacyGateway.jsx  # 3-panel secure processing workspace (Core demo)
│   │   │   ├── AuditLogs.jsx       # Request audit history, leak verification & search
│   │   │   ├── Evaluation.jsx      # Benchmark evaluation results on 50 synthetic documents
│   │   │   └── Settings.jsx        # Purpose-based privacy policies (Mask / Block / Allow)
│   │   ├── services/
│   │   │   └── api.js              # Axios service integrating with FastAPI backend
│   │   ├── data/
│   │   │   └── samples.js          # Synthetic enterprise document presets
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── public/
│   │   └── evaluation-results.json # Verified benchmark results for dashboard consumption
│   └── package.json
│
├── dataset/
│   ├── generate_dataset.py         # Synthetic document generation & span offset validator
│   ├── synthetic_documents.json    # 50 synthetic Indian enterprise documents
│   ├── synthetic_documents.csv     # Flattened CSV format
│   ├── ground_truth.json           # Labeled ground truth with verified offsets
│   └── README.md
│
├── evaluation/
│   ├── metrics.py                  # Exact span matching, precision, recall, F1, leakage, reinsertion
│   ├── evaluate.py                 # Automated benchmark evaluator against API contract
│   ├── results.json                # Benchmark output metrics
│   └── README.md
│
└── README.md
```

---

## 4. Key Pages & Features

### 1. Privacy Gateway (Core Demonstration Page)
- **Panel A: ORIGINAL DOCUMENT**: Large text input, sample preset selector (Loan, KYC, Support, Insurance), character counter, and clear button.
- **Panel B: SANITIZED OUTBOUND PAYLOAD**: Displays exact sanitized text with indexed placeholders highlighted (`<PERSON_1>`, `<PAN_1>`), detected entity count, and outbound leakage status.
- **Panel C: FINAL AI RESPONSE**: Shows the LLM response after local reinsertion, lists restored items, and indicates restoration status.
- **PII Entity Table**: Formats detected entities with type, placeholder, and detection status. Raw PII values are strictly omitted to maintain zero-trust security.
- **Execution Modes**:
  - *Live API Mode* (default): Interacts directly with Person 1's FastAPI server (`POST /api/process`).
  - *Gateway Simulator Mode*: Demonstrates client-side DPDP sanitization and local reinsertion when running offline.

### 2. Executive Dashboard
- Summary cards: Total requests, PII entities detected, Outbound leakage incidents, Average gateway latency, Reinsertion accuracy.
- Recharts visualizations: Requests processed over time, PII entities by category, Detection precision vs recall, and Safe vs Blocked outbound requests.

### 3. Audit Logs
- Integrates with `GET /api/audit` and `GET /api/audit/{request_id}`.
- Search by Request ID, filter by security status (Safe, Blocked, Partial), and sort by timestamp.
- Expandable drawer displays the sanitized outbound payload and status summary without revealing original sensitive values.

### 4. Evaluation & Metrics
- Displays precision, recall, and F1-score across all 7 Indian PII categories.
- Measures confirmed outbound PII leakage, placeholder reinsertion accuracy, and gateway processing latency.

### 5. Privacy Policies / Settings
- Configurable purpose-based processing: *Loan processing*, *Marketing*, *KYC verification*, *Customer support*, and *Insurance claims*.
- Action matrix allowing *Mask*, *Block*, or *Allow* for each PII category.
- Clearly indicates whether policy enforcement is live or frontend-configured.

---

## 5. API Integration Contract

The frontend connects to Person 1's FastAPI backend via `VITE_API_URL` (default: `http://localhost:8000`):

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/process` | Processes and sanitizes text, sends to external LLM, and locally reinserts values |
| `GET` | `/api/audit` | Retrieves historical audit logs |
| `GET` | `/api/audit/{id}` | Retrieves details for a specific request ID |
| `GET` | `/api/metrics` | Retrieves live aggregated gateway metrics |
| `GET` | `/health` | Gateway health check |

---

## 6. Setup & Running Instructions

### Prerequisites
- Node.js (v18+ recommended)
- Python 3.9+

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
The React console will be accessible at `http://localhost:5173`.

To build for production:
```bash
npm run build
```

To run lint checks:
```bash
npm run lint
```

### Dataset & Evaluation
```bash
# 1. Regenerate 50 synthetic Indian benchmark documents
python dataset/generate_dataset.py

# 2. Run automated benchmark evaluation
python evaluation/evaluate.py
```
Evaluation metrics will automatically update in `evaluation/results.json` and sync with `frontend/public/evaluation-results.json` for live dashboard rendering.
