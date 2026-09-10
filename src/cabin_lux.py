"""Каюта категории «lux». Планировка — lib.cabin, размеры — lib.ship."""

from cadgen import glb, step

from lib.cabin import build


@step(out="../STEP/cabin_lux.step")
@glb(out="../GLB/cabin_lux.glb")
def cabin_lux():
    return build("lux")


if __name__ == "__main__":
    cabin_lux()
