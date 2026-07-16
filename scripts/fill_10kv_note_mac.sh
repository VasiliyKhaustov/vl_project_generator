#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DWG_DIR="$ROOT/output/result/dwg"
DWG="$DWG_DIR/note_result.dwg"
LISP="$DWG_DIR/apply_10kv_replacements.lsp"

ACAD_APP=""
for candidate in \
  "/Applications/Autodesk/AutoCAD 2027/AutoCAD 2027.app" \
  "/Applications/Autodesk/AutoCAD 2026/AutoCAD 2026.app" \
  "/Applications/Autodesk/AutoCAD 2025/AutoCAD 2025.app"
do
  if [[ -d "$candidate" ]]; then
    ACAD_APP="$candidate"
    break
  fi
done

if [[ -z "$ACAD_APP" ]]; then
  echo "AutoCAD для Mac не найден." >&2
  exit 1
fi
if [[ ! -f "$DWG" || ! -f "$LISP" ]]; then
  echo "Сначала запустите генерацию проекта 10 кВ на сайте." >&2
  exit 1
fi

SIZE=$(stat -f%z "$DWG" 2>/dev/null || stat -c%s "$DWG")
if [[ "$SIZE" -lt 3100000 ]]; then
  echo "note_result.dwg повреждён ($SIZE байт). Перезапустите генерацию проекта." >&2
  exit 1
fi

echo "Открываю note_result.dwg в AutoCAD (без batch-скрипта)..."
echo ""
echo "После открытия выполните в AutoCAD:"
echo "  1. APPLOAD → apply_10kv_replacements.lsp"
echo "  2. APPLY10KVREPLACEMENTS"
echo "  3. Ctrl+S"
echo ""
echo "НЕ открывайте файл apply_10kv_replacements.scr двойным щелчком."
open -a "$ACAD_APP" "$DWG"
