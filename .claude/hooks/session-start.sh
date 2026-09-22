#!/bin/bash
# Ставит зависимости скриптов проекта (requirements.txt) в облачной сессии
# Claude Code, чтобы планы, чертежи DXF, сводка и модель узла запускались
# сразу. Локально ничего не делает: там свой Python, PyCharm и Blender.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"
python3 -m pip install --quiet --disable-pip-version-check --root-user-action=ignore \
  -r requirements.txt
