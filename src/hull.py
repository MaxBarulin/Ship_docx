"""Корпус судна. Обводы — таблица шпангоутов в lib.ship, лофт — lib.hull."""

from cadgen import glb, step, srgb

from lib.hull import hull_solid


@step(out="../STEP/hull.step")
@glb(out="../GLB/hull.glb")
def hull():
    body = hull_solid()
    body.color = srgb("#2E3B47")
    body.label = "корпус"
    return body


if __name__ == "__main__":
    hull()
