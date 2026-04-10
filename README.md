# ojs2metafora

> *Because manually copy-pasting journal metadata is a crime against humanity.*

📚 Extracts article metadata from an **OJS 2.4** MySQL database, transforms it into
`journal3.xsd`-compliant XML, and ships it to the
[Metafora](https://metafora.rcsi.science/) indexing system (RCSI, Russia) via REST API.

## What it does

1. **Reads** issue metadata (articles, authors, abstracts, keywords, citations) directly
   from the OJS 2.4 MySQL database.
2. **Generates** a `journal3.xsd`-compliant XML file ready for Metafora.
3. **Uploads** the XML to Metafora via REST API, polls for processing status,
   and optionally signs all publications in one go.

## Project layout

```
ojs2metafora/
├── .env                    # Secrets: Metafora API key + DB credentials
├── schemas/
│   └── journal3.xsd        # Metafora XSD schema (copy here manually once)
├── src/
│   ├── main.py             # Entry point: generate XML for a given issue
│   ├── issue_builder.py    # Assembles the full issue XML tree
│   ├── xml_generator.py    # Converts article_data dict → <article> XML element
│   ├── fetch_article.py    # Fetches all metadata for a single article from the DB
│   ├── db_connector.py     # MySQL connection helper (reads .env)
│   ├── validator.py        # Validates generated XML against journal3.xsd
│   ├── metafora_client.py  # CLI client for the Metafora REST API
│   ├── explore_db.py       # Interactive DB explorer / sanity checker
│   └── generate_all.py     # Batch XML generation for all issues
└── output/
    └── 2025/
        └── mathem_n4.xml   # Example generated file (year / series_nNUMBER.xml)
```

## Setup

### 1. Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Create `.env` in the project root

```ini
# OJS database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=ojs_db
DB_USER=ojs_user
DB_PASS=secret

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

All commands are run from the **project root** directory (`ojs2metafora/`).

---

### Mode A — Initial bulk export (one-time, all historical issues)

Use this when loading the entire archive into Metafora for the first time.

**Step A1 — Generate XML for all issues of one journal series**

```bash
# Generate XML for all published issues of the "mathem" journal series
python3 src/generate_all.py --journal-path mathem --validate

# With year filter (e.g. only 2020–2025)
python3 src/generate_all.py --journal-path mathem --year-from 2020 --year-to 2025 --validate

# Preview issue list without generating files
python3 src/generate_all.py --journal-path mathem --dry-run

# Generate for ALL journal series at once
python3 src/generate_all.py --all-journals --validate
```

Output is saved to `output/<year>/<series>_n<number>.xml`.

**Step A2 — Upload all generated XML files for a given year**

```bash
# Upload all XML files in output/2025/ (skips already-processed files)
python3 src/metafora_client.py upload-all 2025

# Upload, then automatically sign all articles
python3 src/metafora_client.py upload-all 2025 --sign

# Upload only the "mathem" series
python3 src/metafora_client.py upload-all 2025 --journal mathem --sign

# Preview what would be uploaded (no actual upload)
python3 src/metafora_client.py upload-all 2025 --dry-run
```

---

### Mode B — Periodic update (new issue)

Use this when a new issue has been published in OJS and needs to be exported.

**Step B1 — Generate XML for a single issue**

```bash
# Basic generation → output/<year>/<series>_n<number>.xml
python3 src/main.py 151

# Recommended: generate + validate against journal3.xsd
python3 src/main.py 151 --validate

# With DEBUG-level logging
python3 src/main.py 151 --validate --verbose

# Explicitly set the Metafora titleid (journal identifier in Metafora)
python3 src/main.py 151 --titleid 38962 --validate
```

> `151` is the `issue_id` from the OJS database (see the `issues` table).
> Find it in the OJS admin URL or with:
> ```sql
> SELECT issue_id, number, year FROM issues ORDER BY year DESC, number DESC LIMIT 10;
> ```

> ⚠️ If you see **WARNING: Missing `<pages>`** — the `pages` field is empty in OJS.
> Fill in the page ranges in OJS, then **re-run the same command**.
> The script reads fresh data from the database every time; there is no cache.

**Step B2 — Upload to Metafora**

```bash
# Upload and wait for server processing, then sign all articles
python3 src/metafora_client.py upload output/2025/mathem_n4.xml --sign

# Upload without automatic signing (sign manually in Step B3)
python3 src/metafora_client.py upload output/2025/mathem_n4.xml

# Upload with full HTTP request/response logging
python3 src/metafora_client.py upload output/2025/mathem_n4.xml --verbose
```

> 🚫 **HTTP 422** means Metafora rejected the XML (e.g. missing `<artType>` or
> `<pages>`). Read the error list, fix the data in OJS, regenerate, and re-upload.

**Step B3 — Sign publications (if not done automatically)**

```bash
python3 src/metafora_client.py sign output/2025/mathem_n4.xml
```

---

### Other useful commands

```bash
# Check processing status (by file path or raw UUID)
python3 src/metafora_client.py status output/2025/mathem_n4.xml
python3 src/metafora_client.py status xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Delete a file from Metafora (e.g. to re-upload a corrected version)
python3 src/metafora_client.py delete output/2025/mathem_n4.xml

# Check whether a DOI is already registered in Metafora
python3 src/metafora_client.py check-doi 10.14529/mmph250101
```

---

### Mode A — Initial bulk export (one-time, all historical issues)

Use this when loading the entire archive into Metafora for the first time.

**Step A1 — Generate XML for all issues of one journal series**

```bash
# Generate XML for all published issues of the "mathem" journal series
python3 src/generate_all.py --journal-path mathem --validate

# With year filter (e.g. only 2020–2025)
python3 src/generate_all.py --journal-path mathem --year-from 2020 --year-to 2025 --validate

# Preview issue list without generating files
python3 src/generate_all.py --journal-path mathem --dry-run

# Generate for ALL journal series at once
python3 src/generate_all.py --all-journals --validate
```

Output is saved to `output/<year>/<series>_n<number>.xml`.

**Step A2 — Upload all generated XML files for a given year**

```bash
# Upload all XML files in output/2025/ (skips already-processed files)
python3 src/metafora_client.py upload-all 2025

# Upload, then automatically sign all articles
python3 src/metafora_client.py upload-all 2025 --sign

# Upload only the "mathem" series
python3 src/metafora_client.py upload-all 2025 --journal mathem --sign

# Preview what would be uploaded (no actual upload)
python3 src/metafora_client.py upload-all 2025 --dry-run
```

---

### Mode B — Periodic update (new issue)

Use this when a new issue has been published in OJS and needs to be exported.

**Step B1 — Generate XML for a single issue**

```bash
# Basic generation → output/<year>/<series>_n<number>.xml
python3 src/main.py 151

# Recommended: generate + validate against journal3.xsd
python3 src/main.py 151 --validate

# With DEBUG-level logging
python3 src/main.py 151 --validate --verbose

# Explicitly set the Metafora titleid (journal identifier in Metafora)
python3 src/main.py 151 --titleid 38962 --validate
```

> `151` is the `issue_id` from the OJS database (see the `issues` table).
> Find it in the OJS admin URL or with:
> ```sql
> SELECT issue_id, number, year FROM issues ORDER BY year DESC, number DESC LIMIT 10;
> ```

> ⚠️ If you see **WARNING: Missing `<pages>`** — the `pages` field is empty in OJS.
> Fill in the page ranges in OJS, then **re-run the same command**.
> The script reads fresh data from the database every time; there is no cache.

**Step B2 — Upload to Metafora**

```bash
# Upload and wait for server processing, then sign all articles
python3 src/metafora_client.py upload output/2025/mathem_n4.xml --sign

# Upload without automatic signing (sign manually in Step B3)
python3 src/metafora_client.py upload output/2025/mathem_n4.xml

# Upload with full HTTP request/response logging
python3 src/metafora_client.py upload output/2025/mathem_n4.xml --verbose
```

> 🚫 **HTTP 422** means Metafora rejected the XML (e.g. missing `<artType>` or
> `<pages>`). Read the error list, fix the data in OJS, regenerate, and re-upload.

**Step B3 — Sign publications (if not done automatically)**

```bash
python3 src/metafora_client.py sign output/2025/mathem_n4.xml
```

---

### Other useful commands

```bash
# Check processing status (by file path or raw UUID)
python3 src/metafora_client.py status output/2025/mathem_n4.xml
python3 src/metafora_client.py status xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Delete a file from Metafora (e.g. to re-upload a corrected version)
python3 src/metafora_client.py delete output/2025/mathem_n4.xml

# Check whether a DOI is already registered in Metafora
python3 src/metafora_client.py check-doi 10.14529/mmph250101
```

---

### Mode A — Initial bulk export (one-time, all historical issues)

Use this when loading the entire archive into Metafora for the first time.

**Step A1 — Generate XML for all issues of one journal series**

```bash
# Generate XML for all published issues of the "mathem" journal series
python3 src/generate_all.py --journal-path mathem --validate

# With year filter (e.g. only 2020–2025)
python3 src/generate_all.py --journal-path mathem --year-from 2020 --year-to 2025 --validate

# Preview issue list without generating files
python3 src/generate_all.py --journal-path mathem --dry-run

# Generate for ALL journal series at once
python3 src/generate_all.py --all-journals --validate
```

Output is saved to `output/<year>/<series>_n<number>.xml`.

**Step A2 — Upload all generated XML files for a given year**

```bash
# Upload all XML files in output/2025/ (skips already-processed files)
python3 src/metafora_client.py upload-all 2025

# Upload, then automatically sign all articles
python3 src/metafora_client.py upload-all 2025 --sign

# Upload only the "mathem" series
python3 src/metafora_client.py upload-all 2025 --journal mathem --sign

# Preview what would be uploaded (no actual upload)
python3 src/metafora_client.py upload-all 2025 --dry-run
```

---

### Mode B — Periodic update (new issue)

Use this when a new issue has been published in OJS and needs to be exported.

**Step B1 — Generate XML for a single issue**

```bash
# Basic generation → output/<year>/<series>_n<number>.xml
python3 src/main.py 151

# Recommended: generate + validate against journal3.xsd
python3 src/main.py 151 --validate

# With DEBUG-level logging
python3 src/main.py 151 --validate --verbose

# Explicitly set the Metafora titleid (journal identifier in Metafora)
python3 src/main.py 151 --titleid 38962 --validate
```

> `151` is the `issue_id` from the OJS database (see the `issues` table).
> Find it in the OJS admin URL or with:
> ```sql
> SELECT issue_id, number, year FROM issues ORDER BY year DESC, number DESC LIMIT 10;
> ```

> ⚠️ If you see **WARNING: Missing `<pages>`** — the `pages` field is empty in OJS.
> Fill in the page ranges in OJS, then **re-run the same command**.
> The script reads fresh data from the database every time; there is no cache.

**Step B2 — Upload to Metafora**

```bash
# Upload and wait for server processing, then sign all articles
python3 src/metafora_client.py upload output/2025/mathem_n4.xml --sign

# Upload without automatic signing (sign manually in Step B3)
python3 src/metafora_client.py upload output/2025/mathem_n4.xml

# Upload with full HTTP request/response logging
python3 src/metafora_client.py upload output/2025/mathem_n4.xml --verbose
```

> 🚫 **HTTP 422** means Metafora rejected the XML (e.g. missing `<artType>` or
> `<pages>`). Read the error list, fix the data in OJS, regenerate, and re-upload.

**Step B3 — Sign publications (if not done automatically)**

```bash
python3 src/metafora_client.py sign output/2025/mathem_n4.xml
```

---

### Other useful commands

```bash
# Check processing status (by file path or raw UUID)
python3 src/metafora_client.py status output/2025/mathem_n4.xml
python3 src/metafora_client.py status xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Delete a file from Metafora (e.g. to re-upload a corrected version)
python3 src/metafora_client.py delete output/2025/mathem_n4.xml

# Check whether a DOI is already registered in Metafora
python3 src/metafora_client.py check-doi 10.14529/mmph250101
```

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

## Upload log

Every successful upload is recorded in `output/upload_log.json` with the `file_uid`,
upload timestamp, processing status, and the list of `article_uid` values returned by
Metafora. The log is read automatically by `status`, `sign`, and `delete` commands so
you don't have to track UUIDs by hand.

---

## Dependencies

| Package | Purpose |
|---|---|
| `lxml` | XML generation and XSD validation |
| `pymysql` | MySQL connection to OJS database |
| `requests` | HTTP calls to the Metafora REST API |
| `python-dotenv` | Loading secrets from `.env` |
| `tabulate` | Pretty-printing reports in `fetch_article.py` |

---

## Status

⚙️ The project is in active use for exporting journal issues to Metafora.
The core architecture is stable; minor details may still change.

## Disclaimer

This is not an official tool of OJS, RCSI, or any institution. Provided "as is",
without warranty of any kind. Use at your own risk — and maybe buy the maintainer
a coffee. ☕
