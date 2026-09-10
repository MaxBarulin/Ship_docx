"""Каюта категории «standard». Планировка — lib.cabin, размеры — lib.ship."""

from cadgen import glb, step

from lib.cabin import build


@step(out="../STEP/cabin_standard.step")
@glb(out="../GLB/cabin_standard.glb")
def cabin_standard():
    return build("standard")


if __name__ == "__main__":
    cabin_standard()
