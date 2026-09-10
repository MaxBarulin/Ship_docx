"""Палитра и отделочные материалы интерьера.

Цвет задаётся ТОЛЬКО через srgb(): каналы build123d линейные, и подстановка
hex напрямую даёт выцветшую картинку. cad_material отвечает за то, как
поверхность откликается на свет — им ткань отличается от лака и от металла.

Категория читается по отделке, а не по подписи под картинкой: эконом —
светлый пластик и ковролин, люкс — тёмное дерево, латунь и камень.
"""

from cadgen import srgb

# --- Отделка помещения -----------------------------------------------------

CEILING = srgb("#F4F2EE")
WALL_LIGHT = srgb("#E8E2D8")  # зашивка эконом/стандарт
WALL_WARM = srgb("#DCD2C4")  # бизнес
WALL_DARK = srgb("#4A4038")  # акцентная переборка люкса
FLOOR_CARPET = srgb("#6E6055")
FLOOR_CARPET_RICH = srgb("#5A4038")
FLOOR_WOOD = srgb("#9A7248")
FLOOR_TILE = srgb("#CFCAC2")

# --- Мебель ----------------------------------------------------------------

WOOD_LIGHT = srgb("#B08A5E")
WOOD_DARK = srgb("#6B4A32")
LAMINATE = srgb("#D8D2C8")
METAL = srgb("#AFB4B8")
BRASS = srgb("#B8924A")

# --- Текстиль --------------------------------------------------------------

LINEN = srgb("#EFEDE7")  # постельное бельё
TEXTILE_BLUE = srgb("#33566B")
TEXTILE_TEAL = srgb("#2F6156")
TEXTILE_WINE = srgb("#6E2B36")
TEXTILE_SAND = srgb("#C2A883")

# --- Санблок ---------------------------------------------------------------

SANITARY = srgb("#F2F2F0")  # фаянс
STONE = srgb("#8C8880")

# --- Остекление ------------------------------------------------------------

GLASS = srgb("#A8C6D8", 0.30)
GLASS_SHOWER = srgb("#C4D8E0", 0.22)

# --- Как поверхность откликается на свет -----------------------------------

MAT_TEXTILE = {"roughness": 0.95, "metalness": 0.0}
MAT_WOOD = {"roughness": 0.45, "metalness": 0.0, "clearcoat": 0.35}
MAT_LACQUER = {"roughness": 0.18, "metalness": 0.0, "clearcoat": 0.8}
MAT_METAL = {"roughness": 0.28, "metalness": 0.9}
MAT_BRASS = {"roughness": 0.22, "metalness": 0.95}
MAT_GLASS = {"roughness": 0.05, "metalness": 0.0}
MAT_CERAMIC = {"roughness": 0.12, "metalness": 0.0, "clearcoat": 0.9}
MAT_CARPET = {"roughness": 1.0, "metalness": 0.0}
MAT_PAINT = {"roughness": 0.7, "metalness": 0.0}


def finish(shape, color, material=None, label=None):
    """Покрасить лист дерева сборки. Цвет на группе в модель не попадает."""
    shape.color = color
    if material is not None:
        shape.cad_material = dict(material)
    if label is not None:
        shape.label = label
    return shape
