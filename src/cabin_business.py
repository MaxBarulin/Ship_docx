"""Каюта категории «business». Планировка — lib.cabin, размеры — lib.ship."""

from cadgen import glb, step

from lib.cabin import build


@step(out="../STEP/cabin_business.step")
@glb(out="../GLB/cabin_business.glb")
def cabin_business():
    return build("business")


if __name__ == "__main__":
    cabin_business()
