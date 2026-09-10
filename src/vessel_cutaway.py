"""Судно в продольном разрезе: видна начинка палуб.

Правый борт отброшен целиком, поэтому в кадре остаются каюты, коридоры,
центральный блок с трапами и отсеки нижних палуб — то, ради чего разрез
и делается.
"""

from cadgen import glb, step

from lib.vessel import build


@step(out="../STEP/vessel_cutaway.step")
@glb(out="../GLB/vessel_cutaway.glb")
def vessel_cutaway():
    return build(interior=True, half=True)


if __name__ == "__main__":
    vessel_cutaway()
