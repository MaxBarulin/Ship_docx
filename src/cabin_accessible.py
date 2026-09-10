"""Каюта для маломобильных пассажиров. Требование КЗ, отдельная категория."""

from cadgen import glb, step

from lib.cabin import build


@step(out="../STEP/cabin_accessible.step")
@glb(out="../GLB/cabin_accessible.glb")
def cabin_accessible():
    return build("accessible")


if __name__ == "__main__":
    cabin_accessible()
