#!/usr/bin/env bash
# Static validation for the finsetter_crm addon: XML well-formedness +
# Python syntax. Safe to run any time, no Docker/Odoo required.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== XML well-formedness =="
fail=0
while IFS= read -r -d '' f; do
  if ! python3 -c "import xml.etree.ElementTree as ET; ET.parse('$f')" 2>/tmp/xmlerr; then
    echo "FAIL: $f"; cat /tmp/xmlerr; fail=1
  fi
done < <(find addons/finsetter_crm -name "*.xml" -print0)
[ "$fail" -eq 0 ] && echo "OK - all XML files are well-formed"

echo
echo "== Python syntax =="
find addons/finsetter_crm -name "*.py" -print0 | xargs -0 -n1 python3 -m py_compile
echo "OK - all Python files compile"

echo
echo "== Manifest sanity =="
python3 - <<'EOF'
import ast
with open("addons/finsetter_crm/__manifest__.py") as f:
    data = ast.literal_eval(f.read())
required = ["name", "version", "depends", "data"]
missing = [k for k in required if k not in data]
assert not missing, f"manifest missing keys: {missing}"
print("OK - manifest has required keys:", ", ".join(required))
EOF

echo
echo "All static checks passed."
