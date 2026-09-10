"""Панорамный ресторан отдельной моделью — для интерьерного рендера.

Берётся фрагмент главной палубы по границам зоны: борт с остеклением,
настил, подволок и вся обстановка. Отдельная модель нужна потому, что на
палубе целиком зал занимает пятую часть кадра и мебель в нём не читается.
"""

from cadgen import build123d as bd
from cadgen import glb, srgb, step

from lib import arrangement as ar
from lib import deckhouse as dh
from lib import interior, lines, ship, vessel
from lib.furniture import _part

ZONE = "Панорамный ресторан"
DECK = "главная"

CEILING = srgb("#F1EFEA")


def _zone():
    for zone in ar.place(DECK):
        if zone.name == ZONE:
            return zone
    raise SystemExit(f"зона «{ZONE}» не найдена в раскладке")


@step(out="../STEP/room_restaurant.step")
@glb(out="../GLB/room_restaurant.glb")
def room_restaurant():
    zone = _zone()
    level = ship.MAIN_DECK
    x0, x1 = zone.x0, zone.x0 + zone.length

    # Обвод палубы, вырезанный по длине зоны. Борта берутся по отдельности
    # и сшиваются поперечными отрезками: если просто отфильтровать полный
    # контур по x, замыкание пойдёт от правого борта к левому через нос, и
    # вместо зала получится клин.
    full = vessel.deck_contour(DECK)
    right = sorted((p for p in full if p[1] > 0 and x0 - 200 <= p[0] <= x1),
                   key=lambda p: p[0])
    left = sorted((p for p in full if p[1] < 0 and x0 - 200 <= p[0] <= x1),
                  key=lambda p: -p[0])
    contour = right + left
    if len(contour) < 4:
        raise SystemExit("контур зоны вырожден")

    parts = [
        lines.deck_slab(contour, level, 120, dh.DECK_TEAK, dh.MAT_TEAK,
                        "настил зала"),
        lines.deck_slab(contour, level + ship.DECK_PITCH, 120, CEILING,
                        dh.MAT_PAINT, "подволок"),
    ]
    parts += lines.band(contour, level, 350, 110, dh.SUPERSTRUCTURE,
                        dh.MAT_PAINT, "цоколь борта")
    parts += lines.band(contour, level + 350, 2_000, 60, dh.GLAZING,
                        dh.MAT_GLASS, "остекление")
    parts += lines.band(contour, level + 2_350, ship.DECK_PITCH - 2_350, 110,
                        dh.SUPERSTRUCTURE, dh.MAT_PAINT, "фриз борта")
    parts.append(_part(160, 2 * ship.SUPERSTRUCTURE_HALF, ship.DECK_PITCH,
                       (x1, -ship.SUPERSTRUCTURE_HALF, level),
                       dh.SUPERSTRUCTURE, dh.MAT_PAINT, "переборка зала"))

    half_at = interior._zone_half_beam(DECK)
    parts += interior.zone_floors(DECK, level)[:1]
    parts += interior.furnish_zone(zone, DECK, level, half_at)

    return bd.Compound(children=parts, label="панорамный ресторан")


if __name__ == "__main__":
    room_restaurant()
