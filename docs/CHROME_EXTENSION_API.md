# Chrome extension API integration

The local API is served at `http://127.0.0.1:8000`. Keep all provider credentials
on the backend; an extension must never include a Groq key.

## Send selected webpage text

`POST /api/documents/analyze` accepts JSON:

```json
{
  "text": "Selected webpage text to inspect",
  "filename": "selected-page.txt",
  "run_llm": true,
  "provider": "configured_provider"
}
```

The response follows the existing single-document analysis schema, including the
detected languages, extracted text, sanitized text, findings, validation alerts,
and AI analysis. Only sanitized text is sent to the configured provider.

## Send multiple files

`POST /api/documents/analyze-batch` accepts `multipart/form-data`. Append each
file under the repeated `files` field. Optional fields are `provider` and
`run_llm`.

```javascript
const form = new FormData()
for (const file of selectedFiles) form.append('files', file)
form.append('provider', 'configured_provider')
form.append('run_llm', 'true')

const response = await fetch('http://127.0.0.1:8000/api/documents/analyze-batch', {
  method: 'POST',
  body: form,
})
const result = await response.json()
```

The response keeps each document independent:

```json
{
  "success": true,
  "total_files": 2,
  "successful_files": 1,
  "failed_files": 1,
  "results": [
    {
      "document_id": "per-upload UUID",
      "filename": "application.pdf",
      "status": "success",
      "detected_languages": ["English"],
      "pages": [{"page_number": 1, "text": "...", "char_count": 12}],
      "entities": [{"type": "PERSON", "placeholder": "<PERSON_1>", "start": 0, "end": 10, "score": 0.9, "source": "local"}],
      "validation_findings": [],
      "llm_analysis": {"status": "success", "summary": "...", "findings": []}
    },
    {
      "document_id": "another UUID",
      "filename": "unsupported.exe",
      "status": "error",
      "error": "Unsupported file format ..."
    }
  ]
}
```

Within one batch, exact normalized PII values of the same type reuse placeholders.
The batch token registry is request-scoped and cleared at completion; document
text, local mappings, and AI prompts are not shared. A failed file is reported
individually and does not prevent other files from being analyzed.

Supported formats include PDF, DOCX, PPTX, TXT, CSV, XLSX, Markdown, JSON, HTML,
and raster images (including PNG, JPG, and JPEG). The batch limit is 10 files,
25 MB per file, and 100 MB combined. Extraction retains PDF page and spreadsheet
sheet/row references where available.

## Errors and CORS

Invalid multipart bodies return HTTP 400, an empty file list returns HTTP 422,
and request/file/count limits return HTTP 413. Per-file extraction or analysis
failures appear as `status: "error"` in that document's result while the request
can still return HTTP 200.

Example request-level errors are JSON:

```json
{"detail": "Provide at least one file in the 'files' field."}
```

This is returned with HTTP 422 when the `files` field is missing or empty. HTTP
413 responses use the same `{"detail":"..."}` shape for file-count, individual
file-size, and total-size limits; malformed multipart requests return HTTP 400.

The backend permits the local Vite origins by default. For an installed
extension, set `CORS_ALLOWED_ORIGINS` on the backend to a comma-separated list
of explicit origins, including `chrome-extension://<your-extension-id>`, then
restart FastAPI. Do not use wildcard origins for a privacy-sensitive deployment.

## Install and configure the Manifest V3 extension

1. Start the backend from `D:\DpdpCM\CodeminionsDPDP\backend`:

   ```powershell
   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

2. In Chrome, open `chrome://extensions` and enable **Developer mode**.
3. Choose **Load unpacked** and select
   `D:\DpdpCM\CodeminionsDPDP\extension`.
4. Copy the extension ID shown on its extension card. Do not copy the `chrome-extension://`
   prefix into the ID field; the backend origin needs the complete origin.
5. Configure `CORS_ALLOWED_ORIGINS` in the backend process environment or in
   `backend/.env`. Include the exact extension origin and preserve local frontend
   origins if you still use the frontend:

   ```dotenv
   CORS_ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173,chrome-extension://YOUR_EXTENSION_ID
   ```

   Replace `YOUR_EXTENSION_ID` with the ID from `chrome://extensions`, with no
   trailing slash. This is an allowlist; do not use `*`.
6. Restart Uvicorn after changing the environment. Reload the extension from
   `chrome://extensions` if its files change.
7. Click the extension icon. Paste text and select **Analyze**, or first select
   text on a regular webpage and explicitly click **Use selected page text**.
   The extension reads only the current selection; it never reads the full page
   or sends anything until **Analyze** is pressed. AI review is optional and
   unchecked by default. **Clear** removes the text and displayed results.

The extension uses only `activeTab` and `scripting` permissions, plus a host
permission for the local backend. It does not declare storage permissions or
save page text. It renders the sanitized text and masked PII placeholders
returned by the existing `/api/documents/analyze` endpoint. When AI review
succeeds, it also displays the provider's masked summary, the backend's
locally-restored summary, findings, and placeholder restoration notes when
available. Restored values are displayed only in the popup from the local
backend response; the backend remains responsible for PII detection/masking
and holds any provider credentials. No Groq key belongs in extension files.

To check the backend, open `http://127.0.0.1:8000/health` and confirm it returns
`{"status":"ok", ...}`. Then analyze a short test sentence containing a fake
name and inspect **Detected PII** and **Sanitized text**. If the popup reports
that it cannot reach the backend, confirm Uvicorn is running at the specified
address. If the request is blocked by CORS, confirm the extension ID origin in
`CORS_ALLOWED_ORIGINS` is exact and restart the backend. Provider failures are
shown in the AI panel; local extraction, detection, and validation are still
shown when available.

This extension has not been browser-tested unless explicitly noted in the
project's verification report. Browser restrictions may prevent injecting into
Chrome internal pages or other protected pages; select text on a regular
webpage instead.
