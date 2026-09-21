# -*- coding: utf-8 -*-
"""Расчётная модель «с ярусами»: объединение корпуса, надстройки и рубки.

Запускается внутри Blender (булево объединение делает его точный решатель):

    blender -b --python scripts/blender_расчётные_модели.py

Результат — одно замкнутое тело в CAD/ВГ-2026_корпус_с_ярусами.stl и .obj
"""
import bpy, bmesh, sys, os

ROOT = r"E:\Ship_docx"
sys.path.insert(0, os.path.join(ROOT, "src"))
for m in [k for k in list(sys.modules) if k.startswith("lib")]:
    del sys.modules[m]
from lib import gorizont_mesh as M

OUT = os.path.join(ROOT, "CAD")


def make(name, verts, faces):
    verts, faces = M.weld(verts, faces)
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.validate()
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def stats(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    oe = sum(1 for e in bm.edges if len(e.link_faces) < 2)
    nm = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    n = (len(bm.verts), len(bm.faces), oe, nm)
    bm.free()
    return n


def build_union():
    hull = make("_расч_корпус", *M.build(tiers=False))
    sup = make("_расч_надстройка", *M.super_solid())
    whl = make("_расч_рубка", *M.wheel_solid())
    bpy.context.view_layer.objects.active = hull
    for other in (sup, whl):
        md = hull.modifiers.new("union", "BOOLEAN")
        md.operation = 'UNION'
        md.solver = 'EXACT'
        md.object = other
        bpy.ops.object.modifier_apply(modifier=md.name)
    for other in (sup, whl):
        bpy.data.objects.remove(other, do_unlink=True)
    bm = bmesh.new(); bm.from_mesh(hull.data)
    bmesh.ops.dissolve_limit(bm, angle_limit=0.0017, verts=bm.verts, edges=bm.edges)
    bm.to_mesh(hull.data); bm.free()
    return hull


def export(o, name):
    verts = [(v.co.x * 1000.0, v.co.y * 1000.0, v.co.z * 1000.0) for v in o.data.vertices]
    faces = [tuple(p.vertices) for p in o.data.polygons]
    n1 = M.write_stl(os.path.join(OUT, name + ".stl"), verts, faces, name)
    M.write_obj(os.path.join(OUT, name + ".obj"), verts, faces, name)
    return n1


if __name__ == "__main__":
    for o in list(bpy.data.objects):
        if o.name.startswith("_расч_"):
            bpy.data.objects.remove(o, do_unlink=True)
    h = build_union()
    v, f, oe, nm = stats(h)
    print("СВОДКА: вершин %d граней %d открытых рёбер %d неманифолд %d"
          % (v, f, oe, nm))
    print("треугольников:", export(h, "ВГ-2026_корпус_с_ярусами"))
    bpy.data.objects.remove(h, do_unlink=True)
