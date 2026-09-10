"""Каюта категории «econom». Планировка — lib.cabin, размеры — lib.ship."""

from cadgen import glb, step

from lib.cabin import build


@step(out="../STEP/cabin_econom.step")
@glb(out="../GLB/cabin_econom.glb")
def cabin_econom():
    return build("econom")


if __name__ == "__main__":
    cabin_econom()
