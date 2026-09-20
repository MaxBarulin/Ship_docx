# -*- coding: utf-8 -*-
r"""Материалы интерьера: дерево, ткань, кожа, камень, металл.

Прежние материалы были плоскими: один цвет и одна шероховатость на весь
предмет. На рендере это читается как пластик, а каюта люкс должна выглядеть
дорого. Здесь у каждого материала появляется то, из-за чего вещь кажется
настоящей:

* у дерева — текстура волокна и лаковый слой (Coat), блик идёт по волокну;
* у тканей — ворс (Sheen): бархат светлеет на скользящем взгляде;
* у кожи — мелкая мерея и слабый лак;
* у камня — прожилки и полировка;
* у металла — анизотропная шлифовка, отдельно латунь для деталей;
* у ковролина — крупный ворс и глубокий цвет.

Всё процедурное: ни одной внешней карты, файл остаётся самодостаточным.

    exec(open(r"E:\Ship_docx\scripts\blender_материалы_интерьера.py", encoding="utf-8").read())
    rebuild_materials()
"""
import bpy


def _mat(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.location = (260, 0)
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    return m, nt, b


def _set(b, **kw):
    names = {"base": "Base Color", "metallic": "Metallic",
             "rough": "Roughness", "ior": "IOR", "sheen": "Sheen Weight",
             "sheen_r": "Sheen Roughness", "sheen_c": "Sheen Tint",
             "coat": "Coat Weight", "coat_r": "Coat Roughness",
             "aniso": "Anisotropic", "aniso_r": "Anisotropic Rotation",
             "spec": "Specular IOR Level", "trans": "Transmission Weight",
             "emit": "Emission Strength", "emit_c": "Emission Color"}
    for k, v in kw.items():
        n = names.get(k, k)
        if n in b.inputs:
            b.inputs[n].default_value = v


def _tex(nt, kind, scale, detail=2.0, dist=0.0, loc=(-700, 0)):
    n = nt.nodes.new("ShaderNodeTexNoise" if kind == "noise"
                     else "ShaderNodeTexWave" if kind == "wave"
                     else "ShaderNodeTexVoronoi")
    n.location = loc
    if "Scale" in n.inputs:
        n.inputs["Scale"].default_value = scale
    if kind == "noise":
        n.inputs["Detail"].default_value = detail
        if "Roughness" in n.inputs:
            n.inputs["Roughness"].default_value = 0.55
    if kind == "wave":
        n.bands_direction = "X"
        n.wave_profile = "SIN"
        n.inputs["Distortion"].default_value = dist
        n.inputs["Detail"].default_value = detail
    return n


def _ramp(nt, stops, loc=(-460, 0)):
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.location = loc
    el = r.color_ramp.elements
    while len(el) > 1:
        el.remove(el[-1])
    el[0].position, el[0].color = stops[0]
    for pos, col in stops[1:]:
        e = el.new(pos)
        e.color = col
    return r


def _bump(nt, src, strength, dist, b, loc=(60, -260)):
    bp = nt.nodes.new("ShaderNodeBump")
    bp.location = loc
    bp.inputs["Strength"].default_value = strength
    bp.inputs["Distance"].default_value = dist
    nt.links.new(src, bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return bp


def wood(name, c_dark, c_light, scale=6.0, coat=0.35, rough=0.30):
    """Шпон: волокно волной с искажением, лак поверх."""
    m, nt, b = _mat(name)
    w = _tex(nt, "wave", scale, detail=6.0, dist=6.0, loc=(-820, 40))
    r = _ramp(nt, [(0.38, c_dark), (0.62, c_light)], loc=(-560, 40))
    nt.links.new(w.outputs["Fac"], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    n = _tex(nt, "noise", 240.0, detail=4.0, loc=(-820, -260))
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.location = (-560, -220)
    rr.inputs["To Min"].default_value = rough - 0.06
    rr.inputs["To Max"].default_value = rough + 0.06
    nt.links.new(n.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    _bump(nt, w.outputs["Fac"], 0.10, 0.0012, b)
    _set(b, metallic=0.0, coat=coat, coat_r=0.07, spec=0.55)
    return m


def fabric(name, col, sheen=0.62, rough=0.92, scale=520.0, bump=0.22):
    """Ткань с ворсом: бархат светлеет на скользящем взгляде."""
    m, nt, b = _mat(name)
    n = _tex(nt, "noise", scale, detail=3.0, loc=(-760, -160))
    _bump(nt, n.outputs["Fac"], bump, 0.0006, b)
    _set(b, base=col, metallic=0.0, rough=rough, sheen=sheen, sheen_r=0.28,
         sheen_c=(1.0, 1.0, 1.0, 1.0), spec=0.35)
    return m


def leather(name, col):
    m, nt, b = _mat(name)
    v = _tex(nt, "voronoi", 180.0, loc=(-760, -160))
    _bump(nt, v.outputs["Distance"], 0.32, 0.0009, b)
    _set(b, base=col, metallic=0.0, rough=0.46, sheen=0.18, sheen_r=0.4,
         coat=0.12, coat_r=0.28, spec=0.5)
    return m


def stone(name, c_base, c_vein, scale=2.4, rough=0.12, coat=0.5):
    m, nt, b = _mat(name)
    n = _tex(nt, "noise", scale, detail=8.0, loc=(-820, 40))
    r = _ramp(nt, [(0.42, c_base), (0.52, c_vein), (0.60, c_base)],
              loc=(-560, 40))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    _bump(nt, n.outputs["Fac"], 0.06, 0.0004, b)
    _set(b, metallic=0.0, rough=rough, coat=coat, coat_r=0.05, spec=0.6)
    return m


def metal(name, col, rough=0.22, aniso=0.45):
    m, nt, b = _mat(name)
    n = _tex(nt, "noise", 900.0, detail=2.0, loc=(-760, -160))
    _bump(nt, n.outputs["Fac"], 0.08, 0.0002, b)
    _set(b, base=col, metallic=1.0, rough=rough, aniso=aniso, aniso_r=0.0)
    return m


def carpet(name, col):
    """Ковролин и ковёр. Ворс (Sheen) берём слабый и в цвет ворса, иначе
    белая вуаль сверху съедает цвет: тёмно-красный ковёр на рендере
    выходил белым пятном."""
    m, nt, b = _mat(name)
    n = _tex(nt, "noise", 380.0, detail=6.0, loc=(-760, -160))
    _bump(nt, n.outputs["Fac"], 0.55, 0.0022, b)
    _set(b, base=col, metallic=0.0, rough=0.97, sheen=0.12, sheen_r=0.6,
         sheen_c=tuple(min(1.0, c * 1.5) for c in col[:3]) + (1.0,),
         spec=0.25)
    return m


def plain(name, col, rough=0.62, sheen=0.0, coat=0.0, bump_scale=0.0,
          bump=0.0):
    m, nt, b = _mat(name)
    if bump_scale:
        n = _tex(nt, "noise", bump_scale, detail=3.0, loc=(-760, -160))
        _bump(nt, n.outputs["Fac"], bump, 0.0005, b)
    _set(b, base=col, metallic=0.0, rough=rough, sheen=sheen, sheen_r=0.4,
         coat=coat, coat_r=0.1)
    return m


PALETTE = {
    "орех":       ((0.108, 0.048, 0.022, 1.0), (0.235, 0.118, 0.055, 1.0)),
    "дуб":        ((0.330, 0.232, 0.140, 1.0), (0.520, 0.395, 0.255, 1.0)),
    "изумруд":    (0.055, 0.180, 0.150, 1.0),
    "бирюза":     (0.075, 0.215, 0.250, 1.0),
    "терракота":  (0.360, 0.150, 0.085, 1.0),
    "охра":       (0.430, 0.300, 0.110, 1.0),
    "бордо":      (0.230, 0.030, 0.045, 1.0),
    "коньяк":     (0.300, 0.140, 0.070, 1.0),
    "латунь":     (0.780, 0.580, 0.280, 1.0),
    "сталь":      (0.660, 0.672, 0.690, 1.0),
    "мрамор":     (0.780, 0.760, 0.730, 1.0),
    "прожилка":   (0.400, 0.380, 0.360, 1.0),
    "песок":      (0.700, 0.640, 0.560, 1.0),
    "слоновая":   (0.930, 0.905, 0.860, 1.0),
    "графит":     (0.115, 0.125, 0.140, 1.0),
}


def rebuild_materials(verbose=True):
    P = PALETTE
    made = []
    made.append(wood("гор_дерево", *P["орех"], scale=34.0, coat=0.40,
                     rough=0.26))
    made.append(wood("гор_дерево_светлое", *P["дуб"], scale=42.0, coat=0.28,
                     rough=0.34))
    made.append(fabric("гор_текстиль", P["изумруд"], sheen=0.28, rough=0.86))
    made.append(fabric("гор_текстиль_тёплый", P["терракота"], sheen=0.30,
                       rough=0.86))
    made.append(fabric("гор_бельё", P["слоновая"], sheen=0.22, rough=0.70,
                       scale=900.0, bump=0.12))
    made.append(leather("гор_кожа", P["коньяк"]))
    made.append(stone("гор_плитка", P["мрамор"], P["прожилка"], scale=2.8,
                      rough=0.10))
    made.append(stone("гор_гранит", (0.16, 0.16, 0.17, 1.0),
                      (0.34, 0.33, 0.31, 1.0), scale=9.0, rough=0.18,
                      coat=0.35))
    made.append(metal("гор_металл", P["сталь"], rough=0.24, aniso=0.5))
    made.append(metal("гор_акцент_латунь", P["латунь"], rough=0.16,
                      aniso=0.35))
    made.append(carpet("гор_ковролин", (0.170, 0.128, 0.105, 1.0)))
    made.append(carpet("гор_ковёр", (0.300, 0.140, 0.120, 1.0)))
    made.append(plain("гор_стекло_каюты", (0.75, 0.82, 0.88, 1.0), rough=0.03))
    gl = made[-1]
    for n in gl.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            n.inputs["Transmission Weight"].default_value = 1.0
            n.inputs["IOR"].default_value = 1.46
    made.append(plain("гор_картина", (0.42, 0.38, 0.34, 1.0), rough=0.45,
                      coat=0.25))
    # зеркало и экран телевизора — разные вещи: одно отражает, другое гасит
    made.append(metal("гор_зеркало", (0.93, 0.94, 0.95, 1.0), rough=0.02,
                      aniso=0.0))
    made.append(plain("гор_экран", (0.035, 0.038, 0.042, 1.0), rough=0.22,
                      coat=0.4))
    made.append(plain("гор_фарфор", (0.965, 0.960, 0.950, 1.0), rough=0.12,
                      coat=0.45))
    made.append(plain("гор_цветы", (0.62, 0.12, 0.22, 1.0), rough=0.55))
    made.append(plain("гор_подволок", (0.960, 0.950, 0.935, 1.0), rough=0.88,
                      bump_scale=60.0, bump=0.05))
    made.append(plain("гор_переборка", P["песок"], rough=0.58, sheen=0.10,
                      coat=0.10, bump_scale=90.0, bump=0.07))
    made.append(plain("гор_простенок", (0.800, 0.755, 0.700, 1.0), rough=0.55,
                      coat=0.10))
    made.append(plain("гор_акцент", P["бордо"], rough=0.30, coat=0.30))
    made.append(plain("гор_зелень", (0.085, 0.230, 0.090, 1.0), rough=0.62,
                      bump_scale=160.0, bump=0.25))
    # светильники: тёплый свет, иначе каюта уходит в синеву
    lamp = plain("гор_щит", (0.960, 0.930, 0.870, 1.0), rough=0.35)
    made.append(lamp)
    for n in lamp.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            n.inputs["Emission Color"].default_value = (1.0, 0.90, 0.74, 1.0)
            n.inputs["Emission Strength"].default_value = 3.2
    if verbose:
        print("материалов пересобрано: %d" % len(made))
    return [m.name for m in made]
