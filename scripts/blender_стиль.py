# -*- coding: utf-8 -*-
r"""Материалы сцены из дизайн-системы проекта.

Цвет живёт в `src/lib/gorizont_style.py` и больше нигде. Этот скрипт
переносит его в Blender: создаёт материалы по описанию, а если они уже
есть — обновляет, не плодя дублей вида «Корпус_графит.001».

Две грабли, на которых тут легко навернуться:

  * Principled BSDF принимает ЛИНЕЙНЫЙ RGB. Если положить туда sRGB прямо
    из палитры, графит выйдет мышиным, а красный розовым. Перевод делает
    `gorizont_style.linear()`, поэтому цвета берутся только через него;
  * узлы ищутся по типу, а не по имени. На нерусском... точнее, на любом
    локализованном интерфейсе `nodes["Principled BSDF"]` вернёт None,
    потому что узел там называется иначе.

Запуск внутри Blender:
    exec(open(r"<путь>/scripts/blender_стиль.py", encoding="utf-8").read())
    построить()
"""
import bpy, os, sys


def _корень():
    """Корень репозитория: от файла скрипта, от переменной среды или от .blend."""
    for кандидат in (
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if "__file__" in globals() else None,
        os.environ.get("GORIZONT_ROOT"),
        os.path.dirname(os.path.dirname(bpy.data.filepath)) if bpy.data.filepath else None,
    ):
        if кандидат and os.path.isdir(os.path.join(кандидат, "src", "lib")):
            return кандидат
    raise RuntimeError(
        "Не найден корень репозитория. Задайте переменную среды GORIZONT_ROOT "
        "или сохраните .blend внутри репозитория."
    )


ROOT = _корень()
if os.path.join(ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "src"))

from lib import gorizont_style as S


def _principled(mat):
    """Узел Principled BSDF по типу: по имени его на локализованном UI нет."""
    return next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)


def _вход(узел, *имена):
    """Вход узла по любому из имён: они менялись между версиями Blender."""
    for имя in имена:
        вход = узел.inputs.get(имя)
        if вход is not None:
            return вход
    return None


def материал(имя):
    """Создать или обновить материал по описанию из дизайн-системы."""
    оп = S.материал(имя)
    mat = bpy.data.materials.get(имя) or bpy.data.materials.new(имя)
    mat.use_nodes = True
    bsdf = _principled(mat)
    if bsdf is None:
        return mat
    _вход(bsdf, "Base Color", "Базовый цвет").default_value = оп["base_color"]
    _вход(bsdf, "Roughness", "Шероховатость").default_value = оп["roughness"]
    _вход(bsdf, "Metallic", "Металличность").default_value = оп["metallic"]
    прозр = _вход(bsdf, "Transmission Weight", "Transmission")
    if прозр is not None:
        прозр.default_value = оп["transmission"]
    if оп["transmission"] > 0.0:
        mat.blend_method = "BLEND" if hasattr(mat, "blend_method") else mat.blend_method
    # Цвет вьюпорта — чтобы сцена читалась и без рендера
    mat.diffuse_color = оп["base_color"]
    return mat


def построить():
    """Все материалы дизайн-системы разом."""
    сделано = [материал(имя) for имя in S.МАТЕРИАЛЫ]
    print("Материалов создано или обновлено: %d" % len(сделано))
    for m in сделано:
        print("   %s" % m.name)
    return сделано


def назначить(объект, имя_материала):
    """Повесить материал на объект, заменив слоты."""
    mat = bpy.data.materials.get(имя_материала) or материал(имя_материала)
    объект.data.materials.clear()
    объект.data.materials.append(mat)
    return mat


if __name__ == "__main__":
    построить()
