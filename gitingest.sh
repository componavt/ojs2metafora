#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

mkdir -p output/ai_concat

gitingest . \
  --include-pattern "README.md" \
  --include-pattern "requirements.txt" \
  --include-pattern "schemas/*.xsd" \
  --include-pattern "src/*.py" \
  --include-pattern "src/*.sh" \
  --exclude-pattern "output/*" \
  -o output/ai_concat/concat_01.txt
