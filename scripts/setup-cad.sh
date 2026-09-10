#!/usr/bin/env bash
# Restore the text-to-cad toolchain in a fresh checkout or a fresh container.
# Idempotent: safe to run on every session start.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

venv="${CAD_VENV:-$root/.venv}"
python_bin="$venv/bin/python"

if [ ! -x "$python_bin" ]; then
  echo "[setup-cad] creating $venv"
  "${PYTHON:-python3}" -m venv "$venv"
  "$python_bin" -m pip install --quiet --upgrade pip
fi

# The skills themselves are committed under .agents/skills; only restore them
# from upstream if the tree is missing (e.g. a partial checkout).
if [ ! -d "$root/.agents/skills/cad" ]; then
  echo "[setup-cad] restoring skills from earthtojake/text-to-cad"
  npx --yes skills add earthtojake/text-to-cad
fi

echo "[setup-cad] installing python runtime"
"$python_bin" -m pip install --quiet -r "$root/requirements-cad.txt"

"$python_bin" "$root/scripts/ensure_chromium.py" || true

"$venv/bin/cadgen" doctor "$root/.agents/skills/cad"
