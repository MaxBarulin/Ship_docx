"""Надстройка, палубы и судовое оборудование.

Ленты остекления строятся НАКЛАДНЫМИ простенками поверх сплошного стекла,
а не вычитанием сотни проёмов из стенки: на трёх палубах в два борта проёмов
под две сотни, и булев вычет каждого превращает сборку судна из секунд
в минуты, а на каждой правке компоновки это повторяется заново.
"""

from cadgen import build123d as bd
from cadgen import srgb

from . import ship
from .furniture import _part, block

# --- Отделка судна ---------------------------------------------------------

HULL_UNDERWATER = srgb("#9C4436")  # сурик ниже КВЛ
HULL_TOPSIDE = srgb("#48607A")
SUPERSTRUCTURE = srgb("#EFEDE6")
DECK_TEAK = srgb("#A88A5E")
DECK_PAINT = srgb("#8E9490")
GLAZING = srgb("#8FB6CE", 0.38)
GLASS_RAIL = srgb("#AFC9DA", 0.30)
RAIL = srgb("#C8CCCE")
DARK = srgb("#3A4048")
SOLAR = srgb("#22304A")
ACCENT = srgb("#B03A2E")

MAT_PAINT = {"roughness": 0.55, "metalness": 0.0, "clearcoat": 0.4}
MAT_GLASS = {"roughness": 0.05, "metalness": 0.0}
MAT_METAL = {"roughness": 0.3, "metalness": 0.85}
MAT_TEAK = {"roughness": 0.6, "metalness": 0.0}


def deck_slab(level, x0, length, width, color=None, label="палуба"):
    """Палубная плита толщиной 120 мм, симметрично относительно ДП."""
    return _part(length, width, 120, (x0, -width / 2, level - 120),
                 color or DECK_PAINT, MAT_TEAK, label)


def window_band(x0, length, z, height, width, pitch=1_300, pier=180,
                label="лента остекления"):
    """Сплошное стекло по обоим бортам плюс накладные простенки по шагу сетки.

    pitch по умолчанию равен модулю каюты: простенок приходится ровно на
    переборку между каютами, поэтому снаружи видно, где какая каюта.
    """
    parts = []
    for side in (-1, 1):
        y = side * width / 2
        parts.append(_part(length, 40, height, (x0, y - 20, z),
                           GLAZING, MAT_GLASS, "остекление"))
        n = int(length // pitch)
        for i in range(n + 1):
            parts.append(_part(pier, 70, height, (x0 + i * pitch - pier / 2,
                                                  y - 35, z),
                               SUPERSTRUCTURE, MAT_PAINT, "простенок"))
    return parts


def railing(x0, length, z, width, label="леер"):
    """Стойки и два поручня по обоим бортам."""
    parts = []
    for side in (-1, 1):
        y = side * width / 2
        for rail_z in (500, 1_060):
            parts.append(_part(length, 60, 60, (x0, y - 30, z + rail_z),
                               RAIL, MAT_METAL, "поручень"))
        for i in range(int(length // 2_000) + 1):
            parts.append(_part(60, 60, 1_100, (x0 + i * 2_000, y - 30, z),
                               RAIL, MAT_METAL, "стойка леера"))
    return parts


def wheelhouse(x_center, level):
    """Рулевая рубка: остеклённый пояс с наклоном и крыша."""
    w, d, h = 9_000, 5_200, 2_600
    x0, y0 = x_center - w / 2, -d / 2
    parts = [
        _part(w, d, 300, (x0, y0, level), SUPERSTRUCTURE, MAT_PAINT, "основание рубки"),
        _part(w, d, h - 400, (x0, y0, level + 300), GLAZING, MAT_GLASS, "остекление рубки"),
        _part(w + 600, d + 600, 200, (x0 - 300, y0 - 300, level + h - 100),
              SUPERSTRUCTURE, MAT_PAINT, "крыша рубки"),
        _part(1_400, 400, 900, (x_center - 700, y0 + d, level + h + 100),
              DARK, MAT_METAL, "антенный пост"),
    ]
    for side in (-1, 1):  # крылья мостика — на них выходят при шлюзовании
        y = side * (ship.SUPERSTRUCTURE_BEAM / 2)
        parts.append(_part(3_000, 1_800, 200,
                           (x_center - 1_500, y - 900 if side > 0 else y - 900, level),
                           SUPERSTRUCTURE, MAT_PAINT, "крыло мостика"))
    return parts


def funnel(x_center, level):
    """Труба гибридной установки, с наклоном по потоку."""
    w, d, h = 2_600, 4_200, 3_400
    x0 = x_center - w / 2
    return [
        _part(w, d, h, (x0, -d / 2, level), DARK, MAT_PAINT, "труба"),
        _part(w + 300, d + 300, 260, (x0 - 150, -d / 2 - 150, level + h - 260),
              ACCENT, MAT_PAINT, "пояс трубы"),
    ]


def mast(x_center, level, height=2_800):
    """Заваливающаяся мачта — на ЕГС иначе не пройти под мостами."""
    return [
        _part(400, 400, height, (x_center - 200, -200, level),
              RAIL, MAT_METAL, "мачта заваливающаяся"),
        _part(3_200, 200, 160, (x_center - 1_600, -100, level + height - 700),
              RAIL, MAT_METAL, "рей"),
    ]


def lifeboat(x_center, side, level):
    """Спасательная шлюпка на кильблоках под шлюпбалками."""
    y = side * (ship.SUPERSTRUCTURE_BEAM / 2 + 250)
    body = _part(8_200, 2_600, 2_200, (x_center - 4_100, y - 1_300, level + 900),
                 ACCENT, MAT_PAINT, "спасательная шлюпка")
    # шлюпбалка выше шлюпки: она её несёт, а не стоит рядом
    davits = []
    for dx in (-3_400, 3_100):
        davits.append(_part(300, 300, 4_200, (x_center + dx, y - 150, level),
                            RAIL, MAT_METAL, "шлюпбалка"))
        davits.append(_part(300, 1_400, 300,
                            (x_center + dx, y - 150 - 1_100, level + 3_900),
                            RAIL, MAT_METAL, "нок шлюпбалки"))
    return [body, *davits]


def solar_array(x0, length, level, width):
    """Солнечные панели на солнечной палубе.

    Требование КЗ: снижение расхода топлива средствами, не связанными с ДВС.
    Панели — самая наглядная его часть, поэтому они на виду сверху.
    """
    parts = []
    panel_w, panel_d, gap = 2_000, 3_400, 400
    n = int(length // (panel_w + gap))
    for i in range(n):
        x = x0 + i * (panel_w + gap)
        for side in (-1, 1):
            y = side * (width / 4) - panel_d / 2
            parts.append(_part(panel_w, panel_d, 90, (x, y, level + 900),
                               SOLAR, {"roughness": 0.15, "metalness": 0.35},
                               "солнечная панель"))
            for dx in (150, panel_w - 300):
                parts.append(_part(120, 120, 900, (x + dx, y + panel_d / 2, level),
                                   RAIL, MAT_METAL, "опора панели"))
    return parts


def gangway(x_center, side, level):
    """Телескопический трап для высадки на необорудованный берег.

    Дополнительное требование КЗ. Показан в убранном положении: три секции,
    вложенные одна в другую, на поворотном основании у борта.
    """
    y = side * (ship.SUPERSTRUCTURE_BEAM / 2 + 400)
    parts = [
        _part(1_600, 1_600, 500, (x_center - 800, y - 800, level),
              DARK, MAT_METAL, "основание трапа"),
    ]
    for i, (length, width, dz) in enumerate(
            [(11_000, 1_400, 500), (9_500, 1_150, 780), (8_000, 900, 1_020)]):
        parts.append(_part(length, width, 260,
                           (x_center - 800, y - width / 2, level + dz),
                           RAIL if i else DARK, MAT_METAL,
                           f"секция трапа {i + 1}"))
    return parts


def balcony(x0, length, side, level, depth=1_800):
    """Балконы люксов на верхней палубе кают, на ширине променада."""
    y = side * 6_200
    y0 = y if side > 0 else y - depth
    return [
        _part(length, depth, 100, (x0, y0, level - 100), DECK_TEAK, MAT_TEAK,
              "палуба балкона"),
        _part(length, 40, 1_000, (x0, y0 + (depth - 40 if side > 0 else 0), level),
              GLAZING, MAT_GLASS, "ограждение балкона"),
    ]
