# Dataset status

No organizer-provided annotated PII corpus has been supplied to this workspace.

The provided references are not evaluation documents:

- The MeitY DPDP Rules page is a policy reference and was not readable by the inspection fetcher (HTTP 403).
- The Gazette PDF is a commencement-date notification.
- The Presidio supported-entities Markdown page describes recognizer types. Its India section lists `IN_PAN`, `IN_AADHAAR`, `IN_VEHICLE_REGISTRATION`, `IN_VOTER`, `IN_PASSPORT`, and `IN_GSTIN`; `PERSON` and `LOCATION` are listed globally.

These references contain no document-level ground-truth entity spans or labeled values suitable for detection evaluation. Do not treat them as corpus records. The Presidio naming differs from the dashboard's expected `VOTER_ID` label, and the reference does not list an India-specific address entity; do not silently map these categories without agreeing on the organizer/backend taxonomy.

The existing `synthetic_documents.json`, `synthetic_documents.csv`, and `ground_truth.json` files are earlier generated demo fixtures. Their format is JSON objects with `document_id`, `category`, `text`, and `entities` entries (`type`, `value`, `start`, `end`) and CSV rows with text and flattened entity fields. They are not organizer data and must not be used to report organizer-corpus metrics.

Once organizers provide the actual corpus, inspect its format, fields, labels, offsets, licensing, and privacy constraints before adapting any importer or evaluator. Keep the original unchanged and out of Git unless distribution is explicitly permitted.
