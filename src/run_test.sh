#!/usr/bin/env bash
set -u
set -o pipefail

# Resolve script directory and repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# Parse --source argument
SOURCE_KEY="karrc"
while [[ $# -gt 0 ]]; do
    case $1 in
        --source)
            if [[ -z "$2" || "$2" == --* ]]; then
                echo "Error: --source requires a value" >&2
                exit 1
            fi
            SOURCE_KEY="$2"
            shift 2
            ;;
        *)
            echo "Error: Unknown argument: $1" >&2
            echo "Usage: $0 [--source karrc|mgta]" >&2
            exit 1
            ;;
    esac
done

# Validate source key
if [[ "$SOURCE_KEY" != "karrc" && "$SOURCE_KEY" != "mgta" ]]; then
    echo "Error: Unknown source key '$SOURCE_KEY'" >&2
    echo "Usage: $0 [--source karrc|mgta]" >&2
    exit 1
fi

echo "=== Step 1: Check schemas directory ==="
if [[ ! -f "schemas/journal3.xsd" ]]; then
    echo "ERROR: schemas/journal3.xsd not found" >&2
    exit 1
fi
echo "schemas/journal3.xsd found"

echo "=== Step 2: Run unit tests ==="
python3 -m unittest discover -s tests -v
TEST_RESULT=$?
if [[ $TEST_RESULT -ne 0 ]]; then
    echo "ERROR: Unit tests failed" >&2
    exit $TEST_RESULT
fi
echo "Unit tests passed"

echo "=== Step 3: Database connection diagnostic (both profiles) ==="
DIAG_SCRIPT=$(cat << 'DIAGET'
import sys
sys.path.insert(0, '.')
from src.db_connector import get_connection

profiles = [
    ("karrc", "ojs"),
    ("mgta", "mgta"),
]

failures = []

for source_key, expected_db in profiles:
    conn = None
    try:
        conn = get_connection(source_key)
        with conn.cursor() as cursor:
            cursor.execute("SELECT DATABASE() AS db_name, COUNT(*) AS journal_count FROM journals")
            result = cursor.fetchone()
            db_name = result['db_name']
            journal_count = result['journal_count']
            print(f"{source_key} -> database {db_name}, journal_count {journal_count}")
    except Exception as e:
        print(f"{source_key} -> ERROR: {e}", file=sys.stderr)
        failures.append(source_key)
    finally:
        if conn:
            conn.close()

if failures:
    raise SystemExit(1)
DIAGET
)

python3 -c "$DIAG_SCRIPT"

echo "=== Step 4: Source-specific smoke test ==="

if [[ "$SOURCE_KEY" == "karrc" ]]; then
    echo "--- Running OJS24 smoke tests for karrc ---"
    
    echo "4a. fetch_article.py (article_id=2099, json format)"
    python3 src/fetch_article.py --source karrc 2099 --format json
    if [[ $? -ne 0 ]]; then
        echo "ERROR: fetch_article.py failed" >&2
        exit 1
    fi
    
    echo "4b. main.py (issue_id=151, validate, verbose)"
    python3 src/main.py --source karrc 151 --validate --verbose
    if [[ $? -ne 0 ]]; then
        echo "ERROR: main.py failed" >&2
        exit 1
    fi
    
    echo "4c. generate_all.py (dry-run for mathem journal)"
    python3 src/generate_all.py --source karrc --journal-path mathem --dry-run
    if [[ $? -ne 0 ]]; then
        echo "ERROR: generate_all.py failed" >&2
        exit 1
    fi
    
    echo "4d. explore_db.py"
    python3 src/explore_db.py --source karrc
    if [[ $? -ne 0 ]]; then
        echo "ERROR: explore_db.py failed" >&2
        exit 1
    fi
    
    echo "4e. Package import smoke test for article XML construction"
    python3 - <<'PYEOF'
import sys
sys.path.insert(0, '.')
from src.fetch_article import fetch_article_metadata
from src.xml_generator import build_article_element
from lxml import etree

data = fetch_article_metadata(2099, source_key="karrc")
if data is None:
    print("ERROR: article 2099 not found")
    sys.exit(1)
el = build_article_element(data)
if el is None:
    print("ERROR: build_article_element returned None")
    sys.exit(1)
xml_str = etree.tostring(el, encoding='unicode')
print("SUCCESS: article element built")
print(xml_str[:1000])
PYEOF
    if [[ $? -ne 0 ]]; then
        echo "ERROR: Package import smoke test failed" >&2
        exit 1
    fi
    
else
    echo "--- Running OJS24-compatible diagnostic for mgta ---"
    echo "5a. generate_all.py dry-run for mgta journal"
    python3 src/generate_all.py --source mgta --journal-path mgta --dry-run
    
    if [[ $? -ne 0 ]]; then
        echo "ERROR: MGTA dry-run failed" >&2
        exit 1
    fi
    
    echo ""
    echo "MGTA connection and published-issue discovery succeeded."
    echo "OJS 3.1 metadata adapter is not implemented yet."
    echo "Skipping article/XML OJS24 smoke tests for mgta."
fi

echo "=== All steps complete ==="
exit 0
