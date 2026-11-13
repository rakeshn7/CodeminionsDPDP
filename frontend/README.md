# DPDP Privacy Gateway frontend

React and Vite dashboard for the existing FastAPI + Groq backend.

## Requirements

- Node.js `^20.19.0` or `>=22.12.0` (required by the versions in
  `package-lock.json`)
- Python 3.11+ for the backend

## Local development

Start the backend in a separate terminal from `backend/`:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Configure backend credentials in the backend process environment or its local
`.env` file. Never put Groq or audit credentials in frontend variables.

Start the frontend:

```powershell
cd frontend
npm ci
npm run dev
```

The Vite server binds to `127.0.0.1` and proxies `/api` and `/health` to
`http://127.0.0.1:8000`. Browser requests use relative paths. This proxy and
its optional audit-header injection are for local development only; they are
not production authentication or a production reverse proxy.

For local audit access, set `AUDIT_API_KEY` in the shell that starts Vite, then
restart Vite. The development proxy reads it server-side and adds a bearer
header only to `/api/audit` requests. It is not a `VITE_` variable and is never
sent to browser JavaScript. If the variable is missing or the backend has no
audit key configured, the protected audit page reports that access is
unavailable; backend authentication remains enabled.

Useful frontend checks:

```powershell
npm run build
npm run lint
```

The gateway page displays results only from the real backend. Evaluation pages
load the existing JSON result; opening the page does not run evaluation.
Reference evaluation is an offline simulation, not a live detector benchmark.
Live evaluation requires an explicit document limit and confirmation; see
`../evaluation/README.md`.
