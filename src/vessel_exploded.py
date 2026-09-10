"""Взрыв-схема судна: те же палубы, раздвинутые по вертикали.

Требование блока дизайн-проекта. Собирается из той же геометрии, что и
vessel.py, поэтому расходиться со сборкой не может по построению.
"""

from cadgen import glb, step

from lib.vessel import build


@step(out="../STEP/vessel_exploded.step")
@glb(out="../GLB/vessel_exploded.glb")
def vessel_exploded():
    return build(explode=7_000)


if __name__ == "__main__":
    vessel_exploded()
