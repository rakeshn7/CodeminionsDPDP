# DPDP Privacy Gateway backend

FastAPI service that detects Indian identifiers locally, masks detections with
request-scoped placeholders, verifies the exact serialized LLM request before
transmission, and restores returned placeholders locally. The original-to-token
mapping is held only in the backend process and is never part of API responses,
LLM requests, or ordinary audit records.

## Requirements and setup

Python 3.11 or newer is required. From this directory:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
Copy-Item .env.example .env
```

The only configured LLM provider is Groq, using its `/openai/v1/chat/completions`
endpoint.
Set `GROQ_API_KEY` and `AUDIT_API_KEY` in the process environment or local
`.env` file. The default model is `openai/gpt-oss-20b`, Groq's recommended
replacement for the retired Llama 3.1 8B Instant model. Configure `GROQ_MODEL`
and `GROQ_BASE_URL` as needed. The application loads `.env` from its working
directory; no credentials are stored in source.

To run from this directory:

```powershell
$env:GROQ_API_KEY = "your-rotated-key"
$env:AUDIT_API_KEY = "a-long-random-secret"
uvicorn app.main:app --reload
```

Do not paste API keys into source code, commits, or chat. If a key has been
shared, revoke it and configure a newly generated key locally.

Interactive API documentation is at `http://127.0.0.1:8000/docs`. `GET /health`
reports whether Presidio's configured spaCy model and GLiNER are ready. GLiNER
loads lazily and may download its configured model on the first detection call.
If either local model is unavailable, the health and detection responses state
that explicitly. Indian identity regex detection remains available, but PERSON
and model-based ADDRESS coverage is degraded until the models are installed.

## API

- `POST /api/process`: detect, mask, verify, call configured provider, and restore.
- `POST /api/detect`: local detection; returns offsets and detection status.
- `POST /api/mask`: local masking; stores the mapping in the backend's short-lived
  process-local vault and returns a request ID.
- `POST /api/reinsert`: restores known placeholders for a request ID.
- `GET /api/audit/{request_id}` and `GET /api/audit`: audit data. Both require
  `Authorization: Bearer $env:AUDIT_API_KEY` in PowerShell; they return `503`
  until the key is configured.
- `GET /api/metrics` and `GET /health`.

Process requests accept `summarize` or `extract`. Input size is limited by
`MAX_INPUT_CHARS` (default 100,000 characters). The audit database is SQLite at
`DATABASE_URL` (default `./data/audit.db`). Audit records contain entity types
and counts, sanitized outbound payloads, verification status, provider/model,
latency, restoration status, and security events—not source text or mappings.
Blocked payloads are deliberately not persisted because they may contain raw
data.

## Run tests

```powershell
python -m pytest -q
```

The test suite uses a provider stub for deterministic testing; production uses
the configured real external provider and does not fabricate a response on API
failure.

## Privacy and operational limitations

The outbound firewall checks every detected original value as an exact,
case-insensitive, token-boundary-aware value in the final serialized request.
It cannot guarantee detection of PII missed by all local recognizers. Validate
model coverage for your documents before production use. Request mappings are
process-local and expire after one hour (and are lost on restart); run a single
backend worker if the separate mask/reinsert endpoints are used. The demo audit
key is a shared bearer secret, not a substitute for production identity,
authorization, TLS, key rotation, or deployment hardening.

Aadhaar checks enforce the 12-digit format, valid leading digit range, and
reject degenerate repeated-digit values; they do not prove that a number was
issued by UIDAI. The API only masks detections, and is not an identity
verification service.

## Document review coverage

The upload path extracts selectable text from PDF, DOCX, TXT, CSV, XLSX,
PPTX, Markdown, JSON, and HTML files, and OCRs JPG, JPEG, PNG, WEBP, BMP, and
TIFF images and scanned PDF pages when Tesseract is available. Mixed PDFs are
handled page by page so scanned pages are not skipped just because another
page contains selectable text. Legacy DOC/XLS/PPT and DOCX/PPTX embedded-image
text are not currently extracted; embedded images are reported as a limitation.

Local language and PII coverage is validated for English, Hindi (Devanagari),
and Kannada. Other detected writing systems remain available for local text
review, but external review is skipped because sending text with unvalidated
PII detection could expose personal information. Latin-script language
identification is heuristic and cannot reliably distinguish every language.
OCR accuracy depends on installed Tesseract language packs. Always verify
extracted text, especially scanned pages and tables. This demo cannot guarantee
correct extraction, classification, or conclusions for every document,
language, or layout; the provider is instructed to use only document evidence
and state uncertainty.
