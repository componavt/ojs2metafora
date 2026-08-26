# ojs2metafora

> *Because manually copy-pasting journal metadata is a crime against humanity.*

Extracts article metadata from **OJS 2.4** and **OJS 3.1** MySQL databases,
transforms it into `journal3.xsd`-compliant XML, and uploads it to the
[Metafora](https://metafora.rcsi.science/) indexing system (RCSI, Russia) via REST API.

Current source profiles:

- `karrc` — OJS 2.4, «Труды КарНЦ РАН»
- `mgta` — OJS 3.1, *Mathematical Game Theory and Applications*

Also supports generating a second XML target for **journals.rcsi.science / RCSI elibrary**
from already-generated Metafora XML and a prepared issue directory.

## What it does

1. **Reads** issue metadata, articles, authors, abstracts, keywords, DOI,
   and citations directly from OJS MySQL databases through source-specific adapters:
   OJS 2.4 for `karrc` and OJS 3.1 for `mgta`.
2. **Generates** a `journal3.xsd`-compliant XML file ready for Metafora.
3. **Uploads** the XML to Metafora via REST API, polls for processing status,
   and optionally signs all publications in one go.

## Project layout

### Two database profiles

The system supports two database backends (OJS versions) with source-isolated configuration
and output paths:

| `--source` | OJS version | Purpose |
|---|---|---|
| `karrc` | OJS 2.4 | Труды КарНЦ РАН |
| `mgta` | OJS 3.1 | Mathematical Game Theory and Applications |

### Source-namespaced output directories

Each source has its own output namespace. Generated XML files go to:
```
output/<source output_namespace>/<year>/<journal>_n<number>.xml
```

Upload logs are also source-isolated:
```
output/<source output_namespace>/upload_log.json
```

For example:

- `output/karrc/2025/mathem_n4.xml` and `output/karrc/upload_log.json`
- `output/mgta/2022/mgta_n1.xml` and `output/mgta/upload_log.json`

`output/mgta/upload_log.json` is created automatically after the first successful MGTA upload.

```
ojs2metafora/
├── .env                    # Secrets: Metafora API key + DB credentials
├── .env.example            # Template for .env (committed to git)
├── schemas/
│   └── journal3.xsd        # Metafora XSD schema (copy here manually once)
├── src/
│   ├── adapters/
│   │   ├── __init__.py     # Adapter factory selected by source profile
│   │   ├── base.py         # Normalized metadata contract
│   │   ├── ojs24.py        # OJS 2.4 / KarRC adapter
│   │   └── ojs31.py        # OJS 3.1 / MGTA adapter
│   ├── main.py             # Entry point: generate XML for a given issue
│   ├── issue_builder.py    # Assembles the full issue XML tree
│   ├── xml_generator.py    # Converts article_data dict → <article> XML element
│   ├── fetch_article.py    # Fetches all metadata for a single article from the DB
│   ├── db_connector.py     # MySQL connection helper for selected source profile
│   ├── output_paths.py     # Source-namespaced output and upload-log paths
│   ├── validator.py        # Validates generated XML against journal3.xsd
│   ├── metafora_client.py  # CLI client for the Metafora REST API
│   ├── explore_db.py       # Interactive DB explorer / sanity checker
│   ├── generate_all.py     # Batch XML generation for all issues
│   ├── xml2elibrary.py     # Convert Metafora XML → RCSI elibrary XML
│   └── run_test.sh         # Developer smoke-test script
└── output/
    ├── karrc/
    │   ├── upload_log.json
    │   └── 2025/
    │       └── mathem_n4.xml
    └── mgta/
        ├── upload_log.json # Created after the first successful MGTA upload
        └── 2022/
            └── mgta_n1.xml
```

## Setup

### 1. Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Create `.env` in the project root

```bash
cp .env.example .env
```

```ini
# OJS 2.4 (karrc) database
OJS24_DBHOST=localhost
OJS24_DBUSER=ojs_user
OJS24_DBPASSWORD=
OJS24_DBNAME=ojs
OJS24_DBCHARSET=utf8mb4

# OJS 3.1 (mgta) database
MGTA_DBHOST=localhost
MGTA_DBUSER=mgta_user
MGTA_DBPASSWORD=
MGTA_DBNAME=mgta
MGTA_DBCHARSET=utf8mb4

# Metafora API
METAFORA_API_KEY=your_api_key_here
METAFORA_API_BASE=https://metafora.rcsi.science/api/v2
```

### 3. Copy the XSD schema

```bash
mkdir -p schemas
cp /path/to/journal3.xsd schemas/
```

## Finding the issue_id

`issue_id` is the numeric primary key of a row in the OJS `issues` table.
You can find it in the OJS admin URL, or just ask the database directly:

```sql
SELECT issue_id, volume, number, year
FROM issues
ORDER BY year DESC, number DESC
LIMIT 20;
```

> Example: *Mathematics & Mechanics*, issue No. 4, 2025 → `issue_id = 151`.

---

## The workflow: from OJS to Metafora

All commands are run from the **project root** (`ojs2metafora/`).

---

### Mode A — Initial bulk export (one-time, all historical issues)

**Step A1 — Generate XML for all issues**

```bash
# All journal series at once (recommended for first-time export)
python3 src/generate_all.py --all-journals --validate

# Only one series, with optional year filter
python3 src/generate_all.py --journal-path mathem --validate
python3 src/generate_all.py --journal-path mathem --year-from 2020 --validate

# Preview list of issues without generating files
python3 src/generate_all.py --all-journals --dry-run
```

Output: `output/<source>/<year>/<series>_n<number>.xml`

**Step A2 — Upload all generated XML files**

```bash
# Upload all files for a specific source (recommended with --sign)
python3 src/metafora_client.py upload-all 2025 --source karrc --sign
python3 src/metafora_client.py upload-all 2022 --source mgta --sign

# Upload only one journal series
python3 src/metafora_client.py upload-all 2025 --source karrc --journal mathem --sign
python3 src/metafora_client.py upload-all 2022 --source mgta --sign

# Preview which files would be uploaded (no actual upload)
python3 src/metafora_client.py upload-all 2025 --source karrc --dry-run
python3 src/metafora_client.py upload-all 2022 --source mgta --dry-run

# Optional: allow more time for a large batch if Metafora is slow
python3 src/metafora_client.py upload-all 2025 --source karrc --sign --max-wait 600 --poll-interval 10
```

### Example: upload new 2026 Biogeography issues

From the project root:

```bash
# Generate or refresh XML files for all 2026 Biogeography issues.
python3 src/generate_all.py --source karrc --journal-path biogeo --year-from 2026 --year-to 2026 --validate

# Upload all 2026 KarRC XML files and sign their publications.
python3 src/metafora_client.py upload-all 2026 --source karrc --sign
```

The upload command processes every XML file in `output/karrc/2026`. Files already processed by Metafora are skipped, so it is safe to run the command again.

The default waiting settings are suitable for normal use; the `--max-wait`/`--poll-interval` form is only for unusually slow processing.

If processing is interrupted or Metafora needs longer than expected, use the file UID printed by the program:

```bash
python3 src/metafora_client.py status FILE_UID
python3 src/metafora_client.py sign FILE_UID
```

When Metafora returns `XML_ALREADY_EXISTS`, the client uses the server-provided file UID and continues safely.

**Step A3 — Sign uploaded articles (if `--sign` was omitted in Step A2)**

```bash
# Sign all articles for all files in a year
python3 src/metafora_client.py sign-all 2025 --source karrc
python3 src/metafora_client.py sign-all 2022 --source mgta

# Sign only one journal series
python3 src/metafora_client.py sign-all 2025 --source karrc --journal mathem
python3 src/metafora_client.py sign-all 2022 --source mgta
```

> `sign-all` is idempotent: already-signed articles return HTTP 409,
> which is treated as success. Safe to re-run.

---

### Note on `YEAR_OR_DIRECTORY` behavior

For batch commands (`upload-all`, `sign-all`), `YEAR_OR_DIRECTORY` behaves as follows:

- If an existing directory is provided, it is used literally.
- Otherwise, the value is treated as a year and resolved under the selected source namespace:
  - `2025 --source karrc` → `output/karrc/2025/`
  - `2022 --source mgta` → `output/mgta/2022/`

---

### Mode B — Periodic update (single new issue)

**Step B1 — Generate XML**

```bash
python3 src/main.py --source karrc 151 --validate
python3 src/main.py --source karrc 151 --titleid 38962 --validate
python3 src/main.py --source karrc 151 --validate --verbose

python3 src/main.py --source mgta 11 --validate
python3 src/main.py --source mgta 11 --titleid 12345 --validate
python3 src/main.py --source mgta 11 --validate --verbose
```

> `151` or `11` is the `issue_id` from the OJS `issues` table.
> Find it with:
> ```sql
> SELECT issue_id, number, year FROM issues
> ORDER BY year DESC, number DESC LIMIT 10;
> ```

> ⚠️ **WARNING: Missing `<pages>`** — fill in page ranges in OJS,
> then re-run the same command. No cache; always reads fresh from DB.

**Step B2 — Upload to Metafora**

```bash
# Upload, wait for processing, then sign automatically
python3 src/metafora_client.py upload output/karrc/2025/mathem_n4.xml --source karrc --sign

# Upload with full HTTP logging
python3 src/metafora_client.py upload output/mgta/2022/mgta_n1.xml --source mgta --verbose
```

> 🚫 **HTTP 422** — Metafora rejected the XML (e.g. missing `<artType>`
> or `<pages>`). Read the error list, fix in OJS, regenerate, re-upload.

**Step B3 — Sign (if `--sign` was omitted in Step B2)**

```bash
python3 src/metafora_client.py sign output/karrc/2025/mathem_n4.xml --source karrc
python3 src/metafora_client.py sign output/mgta/2022/mgta_n1.xml --source mgta
```

### First upload for a new source or issue

For the first XML from a new source, upload one issue **without** `--sign`,
wait for processing, review the issue in the Metafora web interface, and only
then sign its publications.

Example: MGTA, volume 17, issue 3, 2025:

```bash
# 1. Validate the already generated XML locally.
python3 - <<'PY'
from src.validator import validate_xml
raise SystemExit(
    0 if validate_xml(
        "output/mgta/2025/mgta_n3.xml",
        "schemas/journal3.xsd",
    ) else 1
)
PY

# 2. Upload XML, wait until Metafora processes it, but do not sign yet.
python3 src/metafora_client.py \
    upload output/mgta/2025/mgta_n3.xml \
    --source mgta \
    --verbose

# 3. Confirm server-side processing and article count.
python3 src/metafora_client.py \
    status output/mgta/2025/mgta_n3.xml \
    --source mgta

# 4. Review the issue in the Metafora web interface.

# 5. Sign only after the review is satisfactory.
python3 src/metafora_client.py \
    sign output/mgta/2025/mgta_n3.xml \
    --source mgta \
    --verbose
```

After a successful upload, the client writes the server file UID, processing
status, and article UIDs to `output/mgta/upload_log.json`.

---

### Notes for `upload` and `upload-all`

- `upload-all YEAR --source <karrc|mgta> --sign` uploads each XML file, waits for Metafora processing, and signs the resulting publications.
- Files already processed by Metafora are skipped, so rerunning the command is safe.
- If Metafora reports `XML_ALREADY_EXISTS`, the client uses the existing server file UID and continues.
- If processing is interrupted or takes too long, use the file UID printed by the program:

  ```bash
  python3 src/metafora_client.py status FILE_UID
  python3 src/metafora_client.py sign FILE_UID
  ```

---

### Mode C — Generate RCSI elibrary XML from existing Metafora XML

This mode converts an already-generated Metafora issue XML into the RCSI elibrary-compatible
format. It requires a **prepared issue directory** that contains article PDFs (named with
numeric prefixes like `01 Article.pdf`), the combined `PDF all.pdf`, and optionally a cover
image. The script generates only the XML — it does not modify or move any files.

**Step C1 — Generate the elibrary XML**

```bash
python3 src/xml2elibrary.py \
    output/karrc/2025/precambrian_n5.xml \
    output/journals.rcsi.science/2025/1997-3217_2025_5 \
    --output output/journals.rcsi.science/2025/1997-3217_2025_5/1997-3217_2025_5.xml \
    --validate --verbose
```

Parameters:

| Parameter | Description |
|---|---|
| `source_xml` (positional) | Path to the existing Metafora XML file |
| `issue_dir` (positional) | Path to the prepared issue directory containing PDFs |
| `--output`, `-o` | Output XML file path. If omitted, auto-generated from ISSN/year/number |
| `--validate` | Validate the output against `schemas/journal3.xsd` |
| `--xsd-path` | Custom path to the XSD schema (default: `schemas/journal3.xsd`) |
| `--verbose`, `-v` | Enable debug logging |

What the script does:

1. Parses the source Metafora XML.
2. Scans the issue directory for article PDFs with numeric prefixes (e.g. `01 Author.pdf`).
3. Matches PDFs to articles by position and page order.
4. Converts language codes from 2-letter (`ru`, `en`) to 3-letter RCSI style (`RUS`, `ENG`).
5. Adds `<files>` elements with PDF filenames to each `<article>`.
6. Writes the elibrary XML to the specified output path.

Notes:

- `PDF all.pdf` and cover JPEGs are **excluded** from the XML.
- If PDF-to-article matching is imperfect, the script logs warnings but still writes the output.
- Language codes are converted in `<langPubl>`, `lang` attributes on `<journalInfo>`,
  `<secTitle>`, `<individInfo>`, `<artTitle>`, `<kwdGroup>`, and `<file>` elements.

---

### Status, sign, delete: source-aware and raw UID support

Upload, sign, and delete commands support both XML file paths and raw file UIDs.

**With file path** (requires `--source` to select the upload log):

```bash
python3 src/metafora_client.py status output/karrc/2025/mathem_n4.xml --source karrc
python3 src/metafora_client.py sign output/mgta/2022/mgta_n1.xml --source mgta
python3 src/metafora_client.py delete output/karrc/2025/mathem_n4.xml --source karrc
```

**With raw file UID** (bypasses local upload log, no `--source` required):

```bash
python3 src/metafora_client.py status xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
python3 src/metafora_client.py sign xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
python3 src/metafora_client.py delete xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

This recovery mechanism is useful when you have only the Metafora file UID (e.g., from a previous incomplete operation).

**Check DOI** (source-independent, does not accept `--source`):

```bash
python3 src/metafora_client.py check-doi 10.17076/mat2099
python3 src/metafora_client.py check-doi 10.17076/mgta_2022_1_42
```

---

---

## Known quirks 🐛

### Bilingual authors (the "double author" convention)

OJS 2.4 does not support per-locale author names — you can only store a name in one
language per record. The journal editors work around this by creating **two author
records per real author**: one with the Russian name, one with the English name.

The generator detects this automatically by looking for Cyrillic characters in the
surname, then pairs Russian and English records by position and emits a single
`<author>` element with both `<individInfo lang="ru">` and `<individInfo lang="en">`.
No deduplication by email is performed — both names are intentional and are kept.

### Article type `<artType>`

OJS has no native article-type field, so the generator infers `<artType>` from the
section name stored in the database:

| Section keywords | `<artType>` |
|---|---|
| «Памяти», «Obituary», «In memoriam» | `OBT` |
| «Обзор», «Review» | `REV` |
| «Краткое сообщение», «Short report» | `SHR` |
| «От редакции», «Editorial» | `EDI` |
| *(everything else)* | `RAR` *(Research Article — default)* |

### Missing `<pages>`

Metafora **requires** a page range for every article. If `articles.pages` is `NULL`
in OJS, the generator logs a WARNING and omits the `<pages>` element — Metafora will
then reject that article with a 422 error. Fix: fill in the page range in OJS and
regenerate the XML.

---

## Output path rules

When `--output-dir` is omitted, generated XML goes to:
```
output/<source output_namespace>/<year>/
```

When `--output-dir` is provided explicitly, it is used literally. The source namespace is not appended.

Examples:

```bash
python3 src/main.py --source karrc 151 --validate
# output/karrc/2025/mathem_n4.xml

python3 src/main.py --source mgta 11 --validate
# output/mgta/2022/mgta_n1.xml

python3 src/main.py --source mgta 11 --output-dir /tmp/mgta-check --validate
# /tmp/mgta-check/2022/mgta_n1.xml
```

## Source-specific upload logs

Each source has its own isolated upload log:

- `output/karrc/upload_log.json`
- `output/mgta/upload_log.json`

Keys in these logs are normalized absolute XML file paths. Successful uploads record the Metafora file UID, processing status, and article UIDs.

The `status`, `sign`, and `delete` commands use this information automatically when an XML file path is supplied.

If Metafora reports `XML_ALREADY_EXISTS`, the client uses the existing server file UID and continues safely. If processing is interrupted or takes too long, use the file UID printed by the program:

```bash
python3 src/metafora_client.py status FILE_UID
python3 src/metafora_client.py sign FILE_UID
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `lxml` | XML generation and XSD validation |
| `pymysql` | MySQL connection to OJS database |
| `requests` | HTTP calls to the Metafora REST API |
| `python-dotenv` | Loading secrets from `.env` |
| `tabulate` | Pretty-printing DB reports in `explore_db.py` |

---

## Status

⚙️ The project is in active use for exporting journal issues to Metafora.
The core architecture is stable; minor details may still change.

## Disclaimer

This is not an official tool of OJS, RCSI, or any institution. Provided "as is",
without warranty of any kind. Use at your own risk — and maybe buy the maintainer
a coffee. ☕
