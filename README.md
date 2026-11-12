# DPDP-Ready Privacy Gateway

This repository contains the frontend dashboard, synthetic dataset, and evaluation scripts for the DPDP-Ready Privacy Gateway project.

## Project structure

- `frontend/` — React + Vite dashboard and privacy gateway interface
- `dataset/` — synthetic Indian document generator and saved outputs
- `evaluation/` — Python evaluation engine and results JSON

## Frontend setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev -- --host 0.0.0.0
```

The app reads the backend URL from the `VITE_API_URL` environment variable and defaults to `http://localhost:8000`.

## Dataset generation

```bash
python dataset/generate_dataset.py
```

This creates:

- `dataset/synthetic_documents.json`
- `dataset/synthetic_documents.csv`
- `dataset/ground_truth.json`

## Evaluation

```bash
python evaluation/evaluate.py
```

This generates:

- `evaluation/results.json`

The React dashboard also loads `frontend/public/evaluation-results.json` during demo mode.

## Backend contract

The dashboard expects the backend to expose:

- `POST /api/process`
- `GET /api/audit`
- `GET /api/audit/{request_id}`
- `GET /api/metrics`
- `GET /health`

If the backend is not running yet, the UI falls back to demo data and clearly labels it as non-live.

## Notes

- The dataset uses synthetic Indian identities and fictional values only.
- The dashboard clearly distinguishes live and demo metrics.
- Privacy policies are configurable in the frontend and labelled as frontend-only until backend enforcement is confirmed.
