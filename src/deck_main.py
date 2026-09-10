"""Главная палуба отдельной моделью: ресторан, вестибюль, конференц-зал.

На ней стоит вся общественная мебель, поэтому именно она показывает, что
зоны не просто подписаны, а заняты и на сколько человек.
"""

from cadgen import glb, step

from lib import interior, ship, vessel


@step(out="../STEP/deck_main.step")
@glb(out="../GLB/deck_main.glb")
def deck_main():
    from cadgen import build123d as bd

    parts = vessel.deck_shell("главная", sill=350, window=2_000, cabins=False)
    parts += interior.deck_interior("главная", ship.MAIN_DECK)
    return bd.Compound(children=parts, label="главная палуба")


if __name__ == "__main__":
    deck_main()
