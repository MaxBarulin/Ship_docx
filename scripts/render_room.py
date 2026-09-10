#!/usr/bin/env python
"""Интерьерные виды общественного помещения.

Ближняя к камере переборка снимается по ИМЕНИ, а не по номеру occurrence:
номера съезжают при первой правке расстановки, имена — нет. Тот же приём,
что и в render_cabins.py, только зал длиннее каюты, поэтому кроме общего
вида снимается ещё вид вдоль зала — по нему читается шаг посадки.

    python scripts/render_room.py [модель ...]
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CADGEN = ROOT / ".venv" / "bin" / "cadgen"
OUT = ROOT / "renders"

ROOMS = {"room_restaurant": "ресторан"}

VIEWS = {
    "интерьер": ("168:16", ["подволок", "фриз борта"]),
    "вдоль": ("196:9", ["подволок", "фриз борта", "цоколь борта",
                        "остекление"]),
}


def refs_by_name(step):
    raw = subprocess.run(
        [str(CADGEN), "step", "inspect", "refs", str(step), "#o1",
         "--format", "json"],
        capture_output=True, text=True, cwd=ROOT).stdout
    found: dict[str, list[str]] = {}
    for item in json.loads(raw)["tokens"][0]["selections"]:
        ref = item["normalizedSelector"]
        if ref.count(".") != 1:
            continue
        name = item["summary"]
        try:
            name = name.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
        found.setdefault(name, []).append("#" + ref)
    return found


def render(model, title):
    step = ROOT / "STEP" / f"{model}.step"
    if not step.exists():
        raise SystemExit(f"нет {step.name} — сначала: python src/{model}.py")
    refs = refs_by_name(step)
    OUT.mkdir(exist_ok=True)

    for view, (camera, drop) in VIEWS.items():
        path = OUT / f"{title}_{view}.png"
        args = [str(CADGEN), "step", "snapshot", str(step), str(path),
                "--camera", camera, "--width", "2200", "--height", "1200"]
        for name in drop:
            for ref in refs.get(name, []):
                args += ["--hide", ref]
        done = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
        print(f"  {view:9} -> {path.relative_to(ROOT)}" if done.returncode == 0
              else f"  {view}: {done.stderr.strip()[:140]}")


def main():
    wanted = sys.argv[1:] or list(ROOMS)
    for model in wanted:
        print(f"{model}:")
        render(model, ROOMS.get(model, model))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
