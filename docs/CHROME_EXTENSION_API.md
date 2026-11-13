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

## Load the starter extension

The minimal Manifest V3 popup is in `extension/`. It only reads page text after
the user selects text and presses **Use page selection**. Load it using
`chrome://extensions` → **Developer mode** → **Load unpacked**, then select that
folder. Copy its displayed extension ID and add the matching
`chrome-extension://ID` origin to the backend's `CORS_ALLOWED_ORIGINS` before
starting Uvicorn. The popup sends selected text to the local JSON endpoint; it
does not contain provider credentials. Batch file upload is available through
the documented batch endpoint for a future extension file picker.
