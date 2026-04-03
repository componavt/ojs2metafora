#!/usr/bin/env bash
# Developer test script — run manually to verify everything works.
# Note: set -e is intentionally NOT used so all steps run even on errors.

echo "=== Step 1: Check schemas directory ==="
ls -la ../schemas/ 2>/dev/null || ls -la schemas/ 2>/dev/null || \
  echo "WARNING: schemas/ not found — create it and copy journal3.xsd there"

echo "=== Step 2: Smoke test — single article (article_id=2099) ==="
python3 - <<'PYEOF'
import sys; sys.path.insert(0, '.')
from fetch_article import fetch_article_metadata
from xml_generator import build_article_element
from lxml import etree
data = fetch_article_metadata(2099)
if data is None:
    print("ERROR: article 2099 not found"); sys.exit(1)
el = build_article_element(data)
if el is None:
    print("ERROR: build_article_element returned None"); sys.exit(1)
xml_str = etree.tostring(el, pretty_print=True, encoding='unicode')
print("SUCCESS: article element built")
print(xml_str[:6000])
PYEOF

echo "=== Step 3: Generate single issue XML (issue_id=151, no validation) ==="
python3 main.py 151 --verbose 2>&1

echo "=== Step 4: Generate with XSD validation ==="
python3 main.py 151 --validate --verbose 2>&1

echo "=== Step 5: List generated file ==="
find output/ -name "*.xml" | sort | xargs ls -lh 2>/dev/null

echo "=== Step 6: Dry run for all mathem issues ==="
python3 generate_all.py --journal-path mathem --dry-run

echo "=== All steps complete ==="
