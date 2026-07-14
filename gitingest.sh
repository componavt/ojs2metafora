#!/bin/sh
# run from repository root folder
gitingest . \
  --include-pattern "README.md" \
  --include-pattern "requirements.txt" \
  --include-pattern "schemas/*.xsd" \
  --include-pattern "src/*.py" \
  --include-pattern "src/*.sh" \
  --exclude-pattern "output/*" \
  --output out_gitingest/concat_03.txt
