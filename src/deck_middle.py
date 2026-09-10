"""Палуба отдельной моделью: оболочка и вся начинка, без подволока.

Нужна, чтобы увидеть расстановку сверху — на разрезе судна поперечные
переборки кают стоят в глубине и не читаются.
"""

from cadgen import glb, step

from lib import interior, ship, vessel


@step(out="../STEP/deck_middle.step")
@glb(out="../GLB/deck_middle.glb")
def deck_middle():
    from cadgen import build123d as bd

    parts = vessel.deck_shell("средняя")
    parts += interior.deck_interior("средняя", ship.CABIN_DECK_1)
    return bd.Compound(children=parts, label="средняя палуба")


if __name__ == "__main__":
    deck_middle()
