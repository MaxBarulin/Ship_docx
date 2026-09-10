#!/usr/bin/env python
"""Обход судна с уровня глаз: камера ставится точкой, а не пресетом.

Пресеты камеры кадрируют всю сборку — 141-метровое судно в кадре
превращает любой вид от первого лица в общий план. Поэтому виды задаются
парой «глаз — куда смотрит» в координатах судна: снимок так и снимается,
из середины модели, ничего не вырезая.

Глаз на высоте 1690 мм над палубой — это мужчина ростом 1800 мм. Рядом
на палубах стоят фигуры того же и большего роста (lib/people.py): без
них по картинке не понять, парапет это или стеклянная стена.

    python scripts/walkthrough.py [имя вида ...]
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from lib import people, ship  # noqa: E402

CADGEN = ROOT / ".venv" / "bin" / "cadgen"
STEP = ROOT / "STEP" / "vessel_walk.step"
OUT = ROOT / "renders" / "walk"

EYE = people.EYE  # 1690 мм над настилом


def view(deck, at, look, drop=0):
    """Глаз в точке at, взгляд в точку look — обе в плане, палуба задаёт высоту.

    drop — насколько цель ниже глаза: горизонтальный взгляд оставляет
    полкадра неба, а человек в проходе смотрит немного вниз.
    """
    level = ship.DECK_LEVELS[deck]
    return {"position": [at[0], at[1], level + EYE],
            "target": [look[0], look[1], level + EYE - drop],
            "up": [0, 0, 1]}


VIEWS = {
    # солнечная палуба: ограждение, бассейн, площадка, смотровая в носу
    "солнечная_у_борта": view("солнечная", (30_000, -1_000),
                              (34_000, 5_400), drop=500),
    "солнечная_спорт": view("солнечная", (42_000, 3_600), (54_000, 1_200),
                            drop=700),
    "солнечная_бассейн": view("солнечная", (56_500, 4_600),
                              (70_000, 3_000), drop=900),
    "солнечная_нос": view("солнечная", (93_500, 1_500), (104_000, 0),
                          drop=900),
    # верхняя: панорамный бар с носа зала и коридор кают люкс
    "верхняя_бар": view("верхняя", (32_000, 0), (19_000, 0), drop=700),
    "верхняя_коридор": view("верхняя", (57_000, 2_200),
                            (75_000, 2_200), drop=900),
    # шлюпочная: кафе
    "шлюпочная_кафе": view("шлюпочная", (14_200, 900), (24_000, 300),
                           drop=600),
    # средняя: коридор кают и трап центрального блока
    "средняя_коридор": view("средняя", (40_000, 2_200),
                            (70_000, 2_200), drop=1_200),
    "средняя_трап": view("средняя", (72_600, 1_000), (76_000, -500),
                         drop=400),
    # главная: ресторан, вестибюль, открытый променад
    "главная_ресторан": view("главная", (16_000, 0), (34_000, 0), drop=900),
    "главная_вестибюль": view("главная", (52_000, 3_000), (60_000, 1_500),
                              drop=600),
    "главная_променад": view("главная", (56_000, 7_300),
                             (85_000, 7_100), drop=1_500),
}


def render(names):
    OUT.mkdir(parents=True, exist_ok=True)
    outputs = [{"path": str((OUT / f"{name}.png").relative_to(ROOT)),
                "camera": VIEWS[name]} for name in names]
    job = {"input": str(STEP.relative_to(ROOT)), "mode": "view",
           "outputs": outputs,
           "render": {"sizeProfile": "presentation"}}
    path = ROOT / "tmp" / "walkthrough.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(job, ensure_ascii=False, indent=2))
    done = subprocess.run([str(CADGEN), "step", "snapshot", "--job", str(path)],
                          cwd=ROOT, text=True)
    return done.returncode


def main():
    if not STEP.exists():
        raise SystemExit(f"нет {STEP.name} — сначала: python src/vessel_walk.py")
    names = sys.argv[1:] or list(VIEWS)
    unknown = [name for name in names if name not in VIEWS]
    if unknown:
        raise SystemExit(f"нет такого вида: {', '.join(unknown)}\n"
                         f"есть: {', '.join(VIEWS)}")
    return render(names)


if __name__ == "__main__":
    raise SystemExit(main())
