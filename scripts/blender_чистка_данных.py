# -*- coding: utf-8 -*-
r"""Чистка блок-данных: дубли материалов и сеток, мусор без пользователей.

Копирование объектов и загрузка из резервного файла плодят дубли вида
«гор_палуба_сталь.001». Они одинаковы по содержанию, но ломают единый
вид: часть объектов рисуется одним материалом, часть — его копией,
которую потом никто не правит.

Скрипт сливает такие дубли обратно в исходный материал по имени до точки
и убирает всё, чем никто не пользуется.

    exec(open(r"E:\Ship_docx\scripts\blender_чистка_данных.py", encoding="utf-8").read())
    cleanup()
"""
import bpy, re

SUFFIX = re.compile(r"\.\d{3}$")


def merge_materials(verbose=True):
    """Слить материалы-дубли в оригинал."""
    merged = []
    for m in list(bpy.data.materials):
        if not SUFFIX.search(m.name):
            continue
        base = bpy.data.materials.get(SUFFIX.sub("", m.name))
        if base is None or base is m:
            continue
        m.user_remap(base)
        merged.append(m.name)
    for n in merged:
        m = bpy.data.materials.get(n)
        if m and m.users == 0:
            bpy.data.materials.remove(m)
    if verbose and merged:
        print("слито материалов:", len(merged))
    return merged


def merge_meshes(verbose=True):
    """Слить одинаковые по имени сетки-дубли."""
    merged = []
    for me in list(bpy.data.meshes):
        if not SUFFIX.search(me.name):
            continue
        base = bpy.data.meshes.get(SUFFIX.sub("", me.name))
        if base is None or base is me:
            continue
        if len(base.vertices) != len(me.vertices):
            continue
        me.user_remap(base)
        merged.append(me.name)
    for n in merged:
        me = bpy.data.meshes.get(n)
        if me and me.users == 0:
            bpy.data.meshes.remove(me)
    if verbose and merged:
        print("слито сеток:", len(merged))
    return merged


def purge(verbose=True):
    """Убрать блок-данные без пользователей."""
    n = 0
    for _ in range(4):
        k = bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True,
                                   do_recursive=True)
        n += k
        if not k:
            break
    if verbose:
        print("вычищено блоков:", n)
    return n


def cleanup(verbose=True):
    rep = {"материалы": merge_materials(verbose),
           "сетки": merge_meshes(verbose),
           "вычищено": purge(verbose)}
    rep["итого"] = {"материалов": len(bpy.data.materials),
                    "сеток": len(bpy.data.meshes),
                    "объектов": len(bpy.data.objects),
                    "изображений": len(bpy.data.images)}
    if verbose:
        print(rep["итого"])
    return rep
