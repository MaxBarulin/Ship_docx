"""Судно в сборе. Все размеры — lib.ship, состав — lib.vessel."""

from cadgen import glb, step

from lib.vessel import build


@step(out="../STEP/vessel.step")
@glb(out="../GLB/vessel.glb")
def vessel():
    return build()


if __name__ == "__main__":
    vessel()
