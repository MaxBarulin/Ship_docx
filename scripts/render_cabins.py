#!/usr/bin/env python
"""Пересобрать рендеры всех кают одной командой.

Ближняя к камере переборка всегда закрывает интерьер, поэтому для каждого
ракурса она снимается. Снимаются переборки ПО ИМЕНИ, а не по номеру
occurrence: номера поедут при первой же правке планировки, имена — нет.

    python scripts/render_cabins.py [категория ...]
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CADGEN = ROOT / ".venv" / "bin" / "cadgen"
PYTHON = ROOT / ".venv" / "bin" / "python"
OUT = ROOT / "renders"

CATEGORIES = ["econom", "standard", "business", "lux"]

# подпись и главный ракурс категории. Главный — тот, где не мешает санблок:
# в тесном экономе он загораживает всё, кроме взгляда со стороны борта.
TITLES = {
    "econom": ("ЭКОНОМ", "window"),
    "standard": ("СТАНДАРТ", "interior"),
    "business": ("БИЗНЕС", "interior"),
    "lux": ("ЛЮКС", "interior"),
}

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ракурс -> (камера, какие части снять, подпись)
VIEWS = {
    "plan": ("top", ["подволок"], "план"),
    "interior": ("165:28", ["подволок", "переборка коридора", "дверь"],
                 "интерьер от входа"),
    "window": ("20:25", ["подволок", "борт", "остекление", "ограждение"],
               "интерьер со стороны борта"),
}


def run(args: list[str]) -> str:
    done = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
    if done.returncode != 0:
        raise SystemExit(f"не отработало: {' '.join(args)}\n{done.stderr}")
    return done.stdout


def top_level_refs(step: Path) -> dict[str, list[str]]:
    """Имя части -> её occurrence refs верхнего уровня."""
    raw = run([str(CADGEN), "step", "inspect", "refs", str(step), "#o1",
               "--format", "json"])
    found: dict[str, list[str]] = {}
    for item in json.loads(raw)["tokens"][0]["selections"]:
        ref = item["normalizedSelector"]
        if ref.count(".") != 1:  # только верхний уровень сборки
            continue
        found.setdefault(item["summary"], []).append("#" + ref)
    return found


def render(category: str) -> list[Path]:
    step = ROOT / "STEP" / f"cabin_{category}.step"
    if not step.exists():
        raise SystemExit(f"нет {step} — сначала соберите: python src/cabin_{category}.py")
    refs = top_level_refs(step)
    OUT.mkdir(exist_ok=True)

    written = []
    for view, (camera, drop, _) in VIEWS.items():
        path = OUT / f"{category}_{view}.png"
        args = [str(CADGEN), "step", "snapshot", str(step), str(path),
                "--camera", camera, "--width", "1800", "--height", "1250"]
        for name in drop:
            for ref in refs.get(name, []):
                args += ["--hide", ref]
        run(args)
        written.append(path)
        print(f"  {view:9} -> {path.relative_to(ROOT)}")
    return written


def sheet(categories: list[str], view_of: dict[str, str], out: Path,
          cols=2, width=900):
    """Свести главные ракурсы в подписанный лист — его и показывают команде."""
    from PIL import Image, ImageDraw, ImageFont

    sys.path.insert(0, str(ROOT / "src"))
    from lib import ship

    font = ImageFont.truetype(FONT, 21)
    band = 52
    tiles = []
    for category in categories:
        im = Image.open(OUT / f"{category}_{view_of[category]}.png").convert("RGB")
        scale = width / im.width
        tiles.append(im.resize((width, int(im.height * scale)), Image.LANCZOS))

    h = tiles[0].height
    rows = (len(tiles) + cols - 1) // cols
    board = Image.new("RGB", (width * cols, (h + band) * rows), "white")
    draw = ImageDraw.Draw(board)
    for i, (tile, category) in enumerate(zip(tiles, categories)):
        x, y = (i % cols) * width, (i // cols) * (h + band)
        board.paste(tile, (x, y))
        draw.rectangle([x, y + h, x + width, y + h + band], fill="#1a1c1b")
        caption = (f"{TITLES[category][0]}   ·   {ship.clear_area(category):.2f} м²"
                   f"   ·   {ship.MODULES[category]} модуля по "
                   f"{ship.MODULE / 1000:.2f} м")
        draw.text((x + 18, y + h + 15), caption, fill="white", font=font)
    board.save(out)
    print(f"лист: {out.relative_to(ROOT)}")


def main() -> int:
    wanted = sys.argv[1:] or CATEGORIES
    for category in wanted:
        print(f"{category}:")
        render(category)
    if len(wanted) > 1:
        sheet(wanted, {c: TITLES[c][1] for c in wanted}, OUT / "каюты_виды.png")
        sheet(wanted, {c: "plan" for c in wanted}, OUT / "каюты_планы.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
