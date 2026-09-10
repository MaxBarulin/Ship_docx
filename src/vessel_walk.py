"""Судно с людьми на борту — модель для видов с уровня глаз.

Отличается от vessel.py ровно одним: на палубах стоят масштабные фигуры.
Держать их в основной модели нельзя — они попадут в состав деталей и в
проверку пересечений, — а без них вид от первого лица нечем мерить.

Камеры к этой модели: scripts/walkthrough.py.
"""

from cadgen import glb, step

from lib.vessel import build


@step(out="../STEP/vessel_walk.step")
@glb(out="../GLB/vessel_walk.glb")
def vessel_walk():
    return build(figures=True)


if __name__ == "__main__":
    vessel_walk()
