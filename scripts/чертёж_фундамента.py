# -*- coding: utf-8 -*-
"""Чертежи узла ВГ-2026.46.00 «Фундамент-замок модуля (твистлок «ласточкин хвост»)» - DXF и PNG из 3D.

    python scripts/чертёж_фундамента.py

Виды - проекции тел 3D-модели узла с удалением невидимых линий, разрезы - те же тела, рассечённые
плоскостью, со штриховкой сечений. Тела - CAD/src/twistlock.py: корпус - модель конструктора (STEP)
как есть, остальное по lib.gorizont_twistlock. Размеры, допуски и технические требования - из библиотеки
узла. Листы (CAD/узел/, растр - renders/горизонт_2026/чертежи_dxf/):

* ВГ-2026.46.00 СБ          - сборочный чертёж: ступенчатый разрез А-А, разрез Б-Б, вид сверху с положениями
                              рукоятки, позиции, шов корпуса с платиком, техническая характеристика, ТТ;
* ВГ-2026.46.01             - корпус: вид спереди, вид сверху, разрез по отверстию, разрез по полости рукоятки;
* ВГ-2026.46.02 … 46.05     - стержень, элемент запирающий, платик, шайба разрезная;
* ВГ-2026.46.01 ЛФ          - отливка в форме: разъём, припуски, прибыли, стержни, литниковая система;
* ВГ-2026.46.01-МД          - модель корпуса со знаками стержней;
* ВГ-2026.46.01-СЯ1, -СЯ2   - ящики стержневые: стержень отверстия и стержень полости рукоятки.

Для листов модульного решения (scripts/модульное_решение.py, МР-02) - Лист, разрез_АА(L), план_узла(), Z_НАСТИЛ.
"""
import os, sys, math, importlib
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _п in (os.path.join(ROOT, "src"), os.path.join(ROOT, "scripts"), os.path.join(ROOT, "CAD", "src")):
    if _п not in sys.path:
        sys.path.insert(0, _п)
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA
from ezdxf import bbox as EB
from shapely.geometry import Polygon, MultiPolygon, LineString, box, Point
from shapely.ops import unary_union
from shapely import affinity
import build123d as bd
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE
from build123d.topology.shape_core import downcast
from OCP.BRepLib import BRepLib
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GeomAbs import GeomAbs_Line
from lib import gorizont_twistlock as T
import twistlock as TW
D = importlib.import_module("чертежи_dxf")
PNG = importlib.import_module("чертежи_png")

OUT = os.path.join(ROOT, "CAD", "узел")
os.makedirs(OUT, exist_ok=True)
for _ф, _р in (("A2", (594, 420)), ("A3", (420, 297)), ("A4", (210, 297))):
    D.SHEETS.setdefault(_ф, _р)

K, З, С, П, Ш, О, Б = T.КОРПУС, T.ЗАПОР, T.СТЕРЖЕНЬ, T.ПЛАТИК, T.ШАЙБА, T.ОПОРА, T.БОЛТ
Z_ПЛЕЧО = K["плечо_z"]                     # плечо под фитинг, начало узла
Z_ПЛ, Z_ПЛ_НИЗ, Z_ПР = TW.Z_ПЛ, TW.Z_ПЛ_НИЗ, TW.Z_ПР
Z_НАСТИЛ, Z_НАСТ_НИЗ = TW.Z_ЛИСТ, TW.Z_НАСТ    # верх и низ настила
Z_ГОЛОВА = З["z_вала"][1] + З["голова"][2] + З["голова"][3]
ЦЕЛЫЕ = ("pos.3 ", "pos.10 ", "pos.11 ", "pos.12 ")    # не рассекаются в продольном разрезе (ГОСТ 2.305, 2.315)


def ф(x, nd=0):
    return (("%." + str(nd) + "f") % x).replace(".", ",")


# ------------------------------------------------------------------ проекции 3D → лист
#: вид: (направление к наблюдателю, верх листа)
ВИД = {"спереди": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)), "сзади": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
       "сверху": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)), "снизу": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
       "слева": ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)), "справа": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0))}


def _вектор(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def на_вид(вид):
    """Точка модели (x, y, z) → точка вида (по листу вправо, вверх) - как у проекции HLR."""
    d, u = ВИД[вид]
    r = _вектор(tuple(-c for c in d), u)
    return lambda p: (p[0] * r[0] + p[1] * r[1] + p[2] * r[2], p[0] * u[0] + p[1] * u[1] + p[2] * u[2])


def _кривые(comp):
    out = []
    if comp is None or comp.IsNull():
        return out
    ex = TopExp_Explorer(comp, TopAbs_EDGE)
    while ex.More():
        e = downcast(ex.Current())
        BRepLib.BuildCurves3d_s(e, 1e-5)
        c = BRepAdaptor_Curve(e)
        t0, t1 = c.FirstParameter(), c.LastParameter()
        if c.GetType() == GeomAbs_Line:
            n = 1
        else:
            грубо = [c.Value(t0 + (t1 - t0) * i / 8.0) for i in range(9)]
            длина = sum(грубо[i].Distance(грубо[i + 1]) for i in range(8))
            n = max(6, int(длина / 0.8))
        pts = [(c.Value(t0 + (t1 - t0) * i / n).X(), c.Value(t0 + (t1 - t0) * i / n).Y()) for i in range(n + 1)]
        if sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)) > 0.05:
            out.append(pts)
        ex.Next()
    return out


def hlr(тела, вид, скрытые=False):
    """Видимые (и невидимые) линии тел на виде - списки точек в координатах вида."""
    d, u = ВИД[вид]
    algo = HLRBRep_Algo()
    for s in тела:
        for q in (s if isinstance(s, (list, tuple)) or type(s).__name__ == "ShapeList" else [s]):
            algo.Add(q.wrapped)
    ax = gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*d))
    ax.SetYDirection(gp_Dir(*u))
    algo.Projector(HLRAlgo_Projector(ax))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    видимые = _кривые(h.VCompound()) + _кривые(h.OutLineVCompound())
    невидимые = (_кривые(h.HCompound()) + _кривые(h.OutLineHCompound())) if скрытые else []
    return видимые, невидимые


_ОСИ = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}


def сечение(тело, ось, c, вид):
    """Сечение тела плоскостью «ось = c» в координатах вида (shapely)."""
    n = _ОСИ[ось]
    pl = bd.Plane(origin=tuple(c * k for k in n), z_dir=n)
    try:
        r = тело.intersect(bd.Face.make_rect(4000, 4000, pl))
    except Exception:
        return Polygon()
    if r is None:
        return Polygon()
    м = на_вид(вид)

    def pts(w):
        k = max(24, int(w.length / 0.4))
        return [м(tuple(w.position_at(i / k))) for i in range(k)]
    части = []
    for f in r.faces():
        части.append(Polygon(pts(f.outer_wire()), [pts(w) for w in f.inner_wires()]).buffer(0))
    return unary_union(части) if части else Polygon()


def _полупространство(ось, c, знак, R=4000.0):
    """Тело «ось < c» (знак -1) или «ось > c» (знак +1)."""
    k = "xyz".index(ось)
    ц = [0.0, 0.0, 0.0]
    ц[k] = c + знак * R / 2.0
    return bd.Pos(*ц) * bd.Box(R, R, R)


def разрез(детали, зоны, вид, целые=ЦЕЛЫЕ):
    """Разрез (ступенчатый - несколько зон). Зона - (ось, c, призмы или None): в зоне снимается всё, что между
    наблюдателем и плоскостью «ось = c». Призмы - [(x0, x1, y0, y1)] по плану, ограничивают зону. Возвращает
    (тела для HLR, [(метка, сечение)])."""
    d, _ = ВИД[вид]
    снять = None
    for ось, c, обл in зоны:
        s = d["xyz".index(ось)]
        тело = _полупространство(ось, c, 1.0 if s > 0 else -1.0)
        if обл is not None:                      # зона ограничена по другой оси - пересечь с призмами области
            пр = None
            for b in обл:
                q = призма(*b)
                пр = q if пр is None else пр + q
            тело = тело & пр
        снять = тело if снять is None else снять + тело
    тела, сеч = [], []
    for sh in детали:
        метка = getattr(sh, "label", "") or ""
        if метка.startswith(целые):
            # целая деталь в разрезе: снимается, только если вся перед плоскостями
            ост = sh - снять
            if ост is not None and ост.volume > 1e-3:
                тела.append(sh)
            continue
        ост = sh - снять
        if ост is None or ост.volume < 1e-3:
            continue
        тела.append(ост)
        if ост.volume < sh.volume - 1e-3:
            g = []
            for ось, c, обл in зоны:
                сч = сечение(sh, ось, c, вид)
                if обл is not None:
                    сч = сч.intersection(unary_union([_обл2(b, вид) for b in обл]))
                g.append(сч)
            сеч.append((метка, unary_union(g)))
    return тела, сеч


def _обл2(b, вид):
    """Призма зоны (x0, x1, y0, y1) на виде - прямоугольник."""
    м = на_вид(вид)
    x0, x1, y0, y1 = b
    a, c = м((x0, y0, -2000.0)), м((x1, y1, 2000.0))
    return box(min(a[0], c[0]), min(a[1], c[1]), max(a[0], c[0]), max(a[1], c[1]))


def призма(x0, x1, y0, y1, z0=-2000.0, z1=2000.0):
    return bd.Pos((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0) * bd.Box(x1 - x0, y1 - y0, z1 - z0)


#: штриховка сечений: угол, шаг, узор. Соседние детали - встречным наклоном или другим шагом (ГОСТ 2.306),
#: неметаллы (стеклотекстолит) - клеткой
ШТРИХ = {"pos.1 ": (45.0, 1.0, "ANSI31"), "pos.2 ": (135.0, 0.5, "ANSI31"), "pos.4 ": (135.0, 1.0, "ANSI31"),
         "pos.5 ": (135.0, 0.45, "ANSI31"), "pos.6 ": (45.0, 0.35, "ANSI37"), "pos.7 ": (45.0, 0.3, "ANSI37"),
         "pos.8 ": (45.0, 0.3, "ANSI37"), "pos.9 ": (45.0, 0.6, "ANSI31"), "deck": (135.0, 0.6, "ANSI31")}


def _штрих(метка):
    return next((v for k, v in ШТРИХ.items() if метка.startswith(k)), (45.0, 1.0, "ANSI31"))


# ------------------------------------------------------------------ лист
СЛОИ = [("20_ВИДИМЫЕ", 7, "CONTINUOUS", 50), ("21_НЕВИДИМЫЕ", 7, "DASHED", 25), ("22_ТОНКИЕ", 7, "CONTINUOUS", 18),
        ("23_ШТРИХОВКА", 7, "CONTINUOUS", 18), ("24_ФАНТОМ", 7, "PHANTOM", 18), ("25_ЛИТЬЁ", 7, "CONTINUOUS", 35),
        ("26_РАЗЪЁМ", 7, "DASHDOT", 35), ("07_ОСИ", 7, "CENTER", 18)]


class Лист(object):
    """Лист DXF в масштабе 1 : sc. Координаты - миллиметры модели, начало текущего вида - вид(ox, oy)."""

    def __init__(self, sc, формат="A1"):
        self.sc, self.формат = sc, формат
        W, H = D.SHEETS[формат]
        self.W, self.H = W * sc, H * sc
        self.o = (0.0, 0.0)
        self.doc = D.newdoc()
        self.msp = self.doc.modelspace()
        for nm, col, lt, lw in СЛОИ:
            if nm not in self.doc.layers:
                self.doc.layers.add(name=nm, color=col, linetype=lt)
            self.doc.layers.get(nm).dxf.lineweight = lw
        for nm in ("08_ТЕКСТ", "09_РАЗМЕРЫ", "00_РАМКА"):
            self.doc.layers.get(nm).color = 7
        self.doc.header["$LTSCALE"] = 0.35 * sc
        ds = self.doc.dimstyles.new("ГОСТ") if "ГОСТ" not in self.doc.dimstyles else self.doc.dimstyles.get("ГОСТ")
        ds.dxf.dimtxt, ds.dxf.dimasz, ds.dxf.dimexe, ds.dxf.dimexo, ds.dxf.dimgap = 3.5, 3.0, 2.0, 0.0, 1.0
        ds.dxf.dimscale, ds.dxf.dimtad, ds.dxf.dimdec, ds.dxf.dimzin = sc, 1, 1, 8
        ds.dxf.dimtih, ds.dxf.dimtoh, ds.dxf.dimtxsty = 0, 0, "ГОСТ"
        ds.dxf.dimdsep = ord(",")
        ds.dxf.dimclrd, ds.dxf.dimclre, ds.dxf.dimclrt = 7, 7, 7

    def вид(self, ox, oy):
        self.o = (ox, oy)

    def _p(self, p):
        return (p[0] + self.o[0], p[1] + self.o[1])

    def pl(self, pts, layer="20_ВИДИМЫЕ", close=False):
        if len(pts) > 1:
            self.msp.add_lwpolyline([self._p(p) for p in pts], close=close, dxfattribs={"layer": layer})

    def line(self, a, b, layer="20_ВИДИМЫЕ"):
        self.msp.add_line(self._p(a), self._p(b), dxfattribs={"layer": layer})

    def rect(self, x0, y0, x1, y1, layer="20_ВИДИМЫЕ"):
        self.pl([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer, True)

    def circle(self, c, r, layer="20_ВИДИМЫЕ"):
        self.msp.add_circle(self._p(c), r, dxfattribs={"layer": layer})

    def axis(self, a, b):
        self.line(a, b, "07_ОСИ")

    def cross(self, c, r):
        self.axis((c[0] - r, c[1]), (c[0] + r, c[1]))
        self.axis((c[0], c[1] - r), (c[0], c[1] + r))

    def geom(self, g, layer="20_ВИДИМЫЕ"):
        for p in (g.geoms if hasattr(g, "geoms") else [g]):
            if p.is_empty or not hasattr(p, "exterior"):
                continue
            self.pl(list(p.exterior.coords), layer, True)
            for i in p.interiors:
                self.pl(list(i.coords), layer, True)

    def линии(self, кривые, layer="20_ВИДИМЫЕ", dx=0.0, dy=0.0, k=1.0, без=None):
        """Полилинии проекции. без - область (shapely), внутри которой линии не рисуются."""
        for pts in кривые:
            pts = [(dx + k * x, dy + k * y) for x, y in pts]
            if без is not None:
                ln = LineString(pts).difference(без) if len(pts) > 1 else None
                if ln is None or ln.is_empty:
                    continue
                for g in (ln.geoms if hasattr(ln, "geoms") else [ln]):
                    if g.length > 0.2:
                        self.pl(list(g.coords), layer)
                continue
            self.pl(pts, layer)

    def hatch(self, g, angle=45.0, step=1.0, pattern="ANSI31"):
        for p in (g.geoms if hasattr(g, "geoms") else [g]):
            if p.is_empty or not hasattr(p, "exterior") or p.area < 0.5:
                continue
            h = self.msp.add_hatch(color=7, dxfattribs={"layer": "23_ШТРИХОВКА"})
            if pattern == "SOLID":
                h.set_solid_fill(color=7)
            else:
                h.set_pattern_fill(pattern, scale=0.5 * self.sc * step, angle=angle - 45.0)
            h.paths.add_polyline_path([self._p(c) for c in list(p.exterior.coords)[:-1]], is_closed=True,
                                      flags=ezdxf.const.BOUNDARY_PATH_EXTERNAL)
            for i in p.interiors:
                h.paths.add_polyline_path([self._p(c) for c in list(i.coords)[:-1]], is_closed=True)
            self.geom(p)

    def text(self, x, y, s, h=3.5, al=TA.MIDDLE_CENTER, layer="08_ТЕКСТ", rot=0.0):
        x, y = self._p((x, y))
        return D.text(self.msp, x, y, s, h, self.sc, layer, al, rot)

    def dim(self, p1, p2, base, angle=0.0, text=None):
        d = self.msp.add_linear_dim(base=self._p(base), p1=self._p(p1), p2=self._p(p2), angle=angle, dimstyle="ГОСТ",
                                    override={"dimtxsty": "ГОСТ"}, dxfattribs={"layer": "09_РАЗМЕРЫ"},
                                    **({"text": text} if text is not None else {}))
        d.render()

    def dimh(self, x0, x1, y_obj, y_dim, text=None, y_obj1=None):
        self.dim((x0, y_obj), (x1, y_obj if y_obj1 is None else y_obj1), (0.5 * (x0 + x1), y_dim), 0.0, text)

    def dimv(self, y0, y1, x_obj, x_dim, text=None, x_obj1=None):
        self.dim((x_obj, y0), (x_obj if x_obj1 is None else x_obj1, y1), (x_dim, 0.5 * (y0 + y1)), 90.0, text)

    def dim_угол(self, c, r, a0, a1, text=None):
        d = self.msp.add_angular_dim_cra(center=self._p(c), radius=r, start_angle=a0, end_angle=a1, distance=2.0 * self.sc,
                                         dimstyle="ГОСТ", override={"dimtxsty": "ГОСТ", "dimaunit": 0, "dimadec": 0},
                                         dxfattribs={"layer": "09_РАЗМЕРЫ"}, **({"text": text} if text else {}))
        d.render()

    def dim_радиус(self, c, r, a, text=None):
        d = self.msp.add_radius_dim(center=self._p(c), radius=r, angle=a, dimstyle="ГОСТ", override={"dimtxsty": "ГОСТ"},
                                    dxfattribs={"layer": "09_РАЗМЕРЫ"}, **({"text": text} if text else {}))
        d.render()

    def полка(self, pt, колено, s, h=3.0, стрелка=False):
        """Линия-выноска с полкой и надписью над полкой (ГОСТ 2.316). Полка - по длине надписи."""
        self.line(pt, колено, "09_РАЗМЕРЫ")
        if стрелка:
            self._стрелка(pt, колено)
        sgn = 1.0 if колено[0] >= pt[0] else -1.0
        e = self.text(колено[0] + sgn * 1.0 * self.sc, колено[1] + 1.0 * self.sc, s, h,
                      TA.BOTTOM_LEFT if sgn > 0 else TA.BOTTOM_RIGHT)
        bb = EB.extents([e], fast=False)
        w = (bb.extmax.x - bb.extmin.x) + 2.0 * self.sc
        self.line(колено, (колено[0] + sgn * w, колено[1]), "09_РАЗМЕРЫ")

    def _стрелка(self, pt, от):
        s = self.sc
        a = math.atan2(от[1] - pt[1], от[0] - pt[0])
        L, W = 3.5 * s, 1.0 * s
        b1 = (pt[0] + L * math.cos(a) - W * math.sin(a), pt[1] + L * math.sin(a) + W * math.cos(a))
        b2 = (pt[0] + L * math.cos(a) + W * math.sin(a), pt[1] + L * math.sin(a) - W * math.cos(a))
        h = self.msp.add_hatch(color=7, dxfattribs={"layer": "09_РАЗМЕРЫ"})
        h.paths.add_polyline_path([self._p(pt), self._p(b1), self._p(b2)], is_closed=True)

    def pos(self, pt, shelf, n):
        """Позиция (ГОСТ 2.109) - точка на детали, выноска, номер над полкой."""
        s = self.sc
        self.msp.add_circle(self._p(pt), 0.8 * s, dxfattribs={"layer": "09_РАЗМЕРЫ"})
        h = self.msp.add_hatch(color=7, dxfattribs={"layer": "09_РАЗМЕРЫ"})
        h.paths.add_edge_path().add_arc(self._p(pt), 0.8 * s, 0, 360)
        self.line(pt, shelf, "09_РАЗМЕРЫ")
        w = 10.0 * s
        sgn = 1.0 if shelf[0] >= pt[0] else -1.0
        self.line(shelf, (shelf[0] + sgn * w, shelf[1]), "09_РАЗМЕРЫ")
        self.text(shelf[0] + sgn * w / 2.0, shelf[1] + 1.0 * s, str(n), 5.0, TA.BOTTOM_CENTER)

    def позиции(self, пункты, x_лев, x_прав, xc, шаг=11.0):
        """Номера позиций столбцами слева и справа от вида. Порядок полок по высоте - как у точек, выноски не
        пересекаются. пункты - [(номер, точка)]."""
        шаг = шаг * self.sc
        for сторона, x in ((-1, x_лев), (1, x_прав)):
            гр = sorted([p for p in пункты if (p[1][0] < xc) == (сторона < 0)], key=lambda p: -p[1][1])
            ys = []
            for n, (px, py) in гр:
                y = py + 3.0 * self.sc
                if ys and y > ys[-1] - шаг:
                    y = ys[-1] - шаг
                ys.append(y)
            for (n, pt), y in zip(гр, ys):
                self.pos(pt, (x, y), n)

    def rough(self, x, y, val, up=True):
        """Знак шероховатости (ГОСТ 2.309) - вершиной на поверхности, значение над полкой."""
        s = self.sc
        k = 1.0 if up else -1.0
        a, b, c = (x - 2.5 * s, y + k * 4.3 * s), (x, y), (x + 5.0 * s, y + k * 8.6 * s)
        self.pl([a, b, c], "09_РАЗМЕРЫ")
        self.line(c, (c[0] + 12.0 * s, c[1]), "09_РАЗМЕРЫ")
        self.text(c[0] + 6.0 * s, c[1] + k * 1.0 * s, val, 2.5, TA.BOTTOM_CENTER if up else TA.TOP_CENTER)

    def rough_угол(self, val):
        """Шероховатость остальных поверхностей - в правом верхнем углу листа: знак, значение, (√)."""
        s = self.sc
        x, y = self.W - 5.0 * s - 60.0 * s, self.H - 5.0 * s - 14.0 * s
        o = self.o
        self.o = (0.0, 0.0)
        self.text(x, y + 3.0 * s, val, 3.5, TA.BOTTOM_LEFT)
        x2 = x + 22.0 * s
        self.pl([(x2, y + 7.0 * s), (x2 + 2.5 * s, y + 2.7 * s), (x2 + 7.5 * s, y + 11.3 * s)], "09_РАЗМЕРЫ")
        self.text(x2 + 11.0 * s, y + 3.0 * s, "(", 3.5, TA.BOTTOM_LEFT)
        x3 = x2 + 14.0 * s
        self.pl([(x3, y + 7.0 * s), (x3 + 2.5 * s, y + 2.7 * s), (x3 + 7.5 * s, y + 11.3 * s)], "09_РАЗМЕРЫ")
        self.text(x3 + 9.0 * s, y + 3.0 * s, ")", 3.5, TA.BOTTOM_LEFT)
        self.o = o

    def cut(self, a, b, letter, look):
        """След секущей плоскости - разомкнутые штрихи, стрелки направления взгляда, буквы."""
        s = self.sc
        ux, uy = b[0] - a[0], b[1] - a[1]
        L_ = math.hypot(ux, uy)
        ux, uy = ux / L_, uy / L_
        for p, sg in ((a, 1.0), (b, -1.0)):
            q = (p[0] + sg * ux * 10 * s, p[1] + sg * uy * 10 * s)
            self.msp.add_lwpolyline([self._p(p), self._p(q)], dxfattribs={"layer": "20_ВИДИМЫЕ", "const_width": 1.0 * s})
            tip = (p[0] + look[0] * 10 * s, p[1] + look[1] * 10 * s)
            self.line(p, tip, "20_ВИДИМЫЕ")
            nx, ny = look
            h = self.msp.add_hatch(color=7, dxfattribs={"layer": "20_ВИДИМЫЕ"})
            h.paths.add_polyline_path([self._p((tip[0] - nx * 4 * s - ny * 1.2 * s, tip[1] - ny * 4 * s + nx * 1.2 * s)), self._p(tip),
                                       self._p((tip[0] - nx * 4 * s + ny * 1.2 * s, tip[1] - ny * 4 * s - nx * 1.2 * s))], is_closed=True)
            self.text(tip[0] + look[0] * 2 * s - sg * ux * 5 * s, tip[1] + look[1] * 2 * s - sg * uy * 5 * s, letter, 5.0)

    def излом(self, pts):
        """Ступенчатый след: перегибы - утолщёнными штрихами."""
        s = self.sc
        for i in range(1, len(pts) - 1):
            p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]
            for pa in (p0, p2):
                dx, dy = pa[0] - p1[0], pa[1] - p1[1]
                L_ = math.hypot(dx, dy)
                q = (p1[0] + dx / L_ * 6 * s, p1[1] + dy / L_ * 6 * s)
                self.msp.add_lwpolyline([self._p(p1), self._p(q)], dxfattribs={"layer": "20_ВИДИМЫЕ", "const_width": 1.0 * s})

    def title(self, x, y, s, h=5.0):
        return self.text(x, y, s, h, TA.BOTTOM_CENTER)

    def обрыв(self, x, z0, z1):
        s = self.sc
        zm = 0.5 * (z0 + z1)
        self.pl([(x, z0), (x, zm - 3 * s), (x - 2.5 * s, zm - 1 * s), (x + 2.5 * s, zm + 1 * s), (x, zm + 3 * s), (x, z1)], "22_ТОНКИЕ")

    def обрыв_г(self, z, x0, x1):
        s = self.sc
        xm = 0.5 * (x0 + x1)
        self.pl([(x0, z), (xm - 3 * s, z), (xm - 1 * s, z - 2.5 * s), (xm + 1 * s, z + 2.5 * s), (xm + 3 * s, z), (x1, z)], "22_ТОНКИЕ")

    def шов(self, pt, колено, катет, гост, тип, способ, h=3.5):
        """Обозначение шва (ГОСТ 2.312): выноска с односторонней стрелкой, окружность на изломе - шов по замкнутой
        линии, над полкой - стандарт, тип соединения, способ сварки, знак катета ⊿ и катет."""
        s = self.sc
        self.line(pt, колено, "09_РАЗМЕРЫ")
        self._стрелка(pt, колено)
        self.circle(колено, 2.0 * s, "09_РАЗМЕРЫ")
        y0 = колено[1] + 1.0 * s
        e = self.text(0.0, y0, "%s-%s-%s-" % (гост, тип, способ), h, TA.BOTTOM_LEFT)
        e2 = self.text(0.0, y0, ф(катет), h, TA.BOTTOM_LEFT)
        w1 = EB.extents([e], fast=False).size.x
        w2 = EB.extents([e2], fast=False).size.x
        t = h * s * 0.9
        W = w1 + 0.8 * s + t + 0.8 * s + w2
        x0 = колено[0] + 2.0 * s if колено[0] >= pt[0] else колено[0] - 2.0 * s - W
        e.set_placement(self._p((x0, y0)), align=TA.BOTTOM_LEFT)
        xa = x0 + w1 + 0.8 * s
        self.pl([(xa, y0), (xa + t, y0), (xa, y0 + t), (xa, y0)], "09_РАЗМЕРЫ")
        e2.set_placement(self._p((xa + t + 0.8 * s, y0)), align=TA.BOTTOM_LEFT)
        x1 = x0 + W + 1.5 * s if колено[0] >= pt[0] else x0 - 1.5 * s
        self.line(колено, (x1, колено[1]), "09_РАЗМЕРЫ")

    def след(self, pts, letter, look):
        """След секущей плоскости (ГОСТ 2.305): разомкнутые штрихи на концах и на перегибах ступенчатого разреза,
        стрелки направления взгляда и буквы у концов."""
        s = self.sc
        for p, q in ((pts[0], pts[1]), (pts[-1], pts[-2])):
            dx, dy = q[0] - p[0], q[1] - p[1]
            L_ = math.hypot(dx, dy)
            u = (dx / L_, dy / L_)
            self.msp.add_lwpolyline([self._p(p), self._p((p[0] + u[0] * 10 * s, p[1] + u[1] * 10 * s))],
                                    dxfattribs={"layer": "20_ВИДИМЫЕ", "const_width": 1.0 * s})
            a = (p[0] - u[0] * 2 * s, p[1] - u[1] * 2 * s)
            tip = (a[0] + look[0] * 10 * s, a[1] + look[1] * 10 * s)
            self.line(a, tip, "20_ВИДИМЫЕ")
            nx, ny = look
            h = self.msp.add_hatch(color=7, dxfattribs={"layer": "20_ВИДИМЫЕ"})
            h.paths.add_polyline_path([self._p((tip[0] - nx * 4 * s - ny * 1.2 * s, tip[1] - ny * 4 * s + nx * 1.2 * s)), self._p(tip),
                                       self._p((tip[0] - nx * 4 * s + ny * 1.2 * s, tip[1] - ny * 4 * s - nx * 1.2 * s))], is_closed=True)
            self.text(tip[0] + look[0] * 3 * s - u[0] * 5 * s, tip[1] + look[1] * 3 * s - u[1] * 5 * s, letter, 5.0)
        self.излом(pts)

    def save(self, name, mark, title, subtitle, notes, material, wrap=None):
        self.o = (0.0, 0.0)
        D.frame(self.msp, self.формат, self.sc, (0.0, 0.0, self.W, self.H), mark, title, subtitle, notes,
                material=material, wrap=wrap)
        p = os.path.join(OUT, name + ".dxf")
        tmp = p + ".tmp.dxf"
        self.doc.saveas(tmp)
        os.replace(tmp, p)
        png = os.path.join(PNG.OUT, name + ".png")
        w, h = PNG.растр(p, png)
        print("%-52s %4d КБ  PNG %d × %d" % (os.path.relpath(p, ROOT), os.path.getsize(p) // 1024, w, h))
        return p


def _точка(g):
    """Точка внутри сечения детали - для позиции."""
    if g.is_empty:
        return None
    части = sorted(g.geoms, key=lambda q: -q.area) if hasattr(g, "geoms") else [g]
    q = части[0].representative_point()
    return (q.x, q.y)


def контур(тела, вид):
    """Силуэт тел на виде - объединение сечений на нескольких уровнях по глубине (для обрезки фантома)."""
    d, _ = ВИД[вид]
    k = next(i for i in range(3) if abs(d[i]) > 0.5)
    ось = "xyz"[k]
    out = []
    for т in тела:
        bb = т.bounding_box()
        lo, hi = (bb.min.X, bb.min.Y, bb.min.Z)[k], (bb.max.X, bb.max.Y, bb.max.Z)[k]
        for i in range(1, 12):
            out.append(сечение(т, ось, lo + (hi - lo) * i / 12.0, вид))
    return unary_union(out)


# ------------------------------------------------------------------ СБ
def детали_узла(угол=TW.ЗАКРЫТО):
    return TW.сборка(угол, с_настилом=True)


def разрез_АА(L, детали=None, для_мр=False):
    """Ступенчатый разрез А-А: по оси узла (Y = 0) в пределах корпуса и по оси болтов (Y = +95) снаружи. Вид спереди,
    начало вида - ось узла на плече корпуса. Возвращает сечения деталей (для позиций)."""
    детали = детали or детали_узла()
    xb = 0.5 * (K["габарит"][0] + (2 * П["болт_x"] - П["овал"][1])) / 2.0 + 10.0        # граница ступени между корпусом и болтами
    зоны = [("y", 0.0, [(-xb, xb, -2000, 2000)]), ("y", П["болт_y"], [(-2000, -xb, -2000, 2000), (xb, 2000, -2000, 2000)])]
    тела, сеч = разрез(детали, зоны, "спереди")
    vis, _ = hlr(тела, "спереди")
    # переход ступени (x = ±xb) по ГОСТ 2.305 не показывают
    vis = [p for p in vis if not (len(p) == 2 and abs(abs(p[0][0]) - xb) < 0.05 and abs(abs(p[1][0]) - xb) < 0.05)]
    L.линии(vis)
    for метка, g in сеч:
        a, st, pat = _штрих(метка)
        L.hatch(g, a, st, pat)
    ш = швы(unary_union([g for м_, g in сеч if м_.startswith("pos.1 ")]))
    L.hatch(ш, pattern="SOLID")
    for x in (-TW.НАСТИЛ[0] / 2.0, TW.НАСТИЛ[0] / 2.0):
        L.обрыв(x, Z_НАСТ_НИЗ - 6, Z_НАСТИЛ + 6)
    L.axis((0, Z_НАСТ_НИЗ - 60), (0, Z_ГОЛОВА + 15))
    for x in (-П["болт_x"], П["болт_x"]):
        L.axis((x, Z_ПЛ + 25), (x, Z_НАСТ_НИЗ - 55))
    if not для_мр:
        фитинг(L)
    return сеч, xb, ш


def швы(корпус_сеч):
    """Сечение шва Т1 у наружных кромок опорных полос на разрезе по оси: треугольник с катетом по платику и по корпусу,
    под свесом «ласточкина хвоста» - до его поверхности."""
    x1, k = K["полоса"]["x"][1], T.ШОВ["катет"]
    out = []
    for sg in (-1.0, 1.0):
        tri = Polygon([(sg * x1, Z_ПЛ), (sg * (x1 + k), Z_ПЛ), (sg * x1, Z_ПЛ + k)])
        out.append(tri.difference(корпус_сеч))
    return unary_union(out)


def фитинг(L):
    """Угловой фитинг ISO 1161 контейнера - фантом: днище на плече корпуса, центратор в отверстии."""
    М = T._M().КОНТЕЙНЕР
    fl, fw, fh = М["фитинг_мм"]
    al, aw = М["отверстие_мм"]
    a0, a1, h = -73.0, 89.0, aw
    дно = T.ФИТИНГ_ДНО
    L.pl([(a0, 0), (-h / 2, 0), (-h / 2, дно), (a0 + 12, дно), (a0 + 12, fh - 12), (a1 - 12, fh - 12), (a1 - 12, дно),
          (h / 2, дно), (h / 2, 0), (a1, 0), (a1, fh), (a0, fh), (a0, 0)], "24_ФАНТОМ")


def разрез_ББ(L, детали=None):
    """Разрез Б-Б по оси узла поперёк (X = 0), вид слева: полость рукоятки со стержнем."""
    детали = детали or детали_узла()
    тела, сеч = разрез(детали, [("x", 0.0, None)], "слева", целые=ЦЕЛЫЕ + ("pos.2 ",))
    vis, _ = hlr(тела, "слева")
    L.линии(vis)
    for метка, g in сеч:
        a, st, pat = _штрих(метка)
        L.hatch(g, a, st, pat)
    for x in (-TW.НАСТИЛ[1] / 2.0, TW.НАСТИЛ[1] / 2.0):
        L.обрыв(x, Z_НАСТ_НИЗ - 6, Z_НАСТИЛ + 6)
    L.axis((0, Z_НАСТ_НИЗ - 30), (0, Z_ГОЛОВА + 15))
    return сеч


def план_узла(угол=TW.ЗАКРЫТО, с_настилом=False):
    """Вид сверху на узел - видимые линии (для МР-02)."""
    тела = [t for t in TW.сборка(угол, с_настилом=с_настилом)]
    vis, _ = hlr(тела, "сверху")
    return vis


def сб():
    sc = 2
    L = Лист(sc, "A1")
    н, м = T.нагрузки(), T.массы()
    детали = детали_узла()
    # --- А-А
    AX, AY = 560.0, 830.0
    L.вид(AX, AY)
    # стержень лежит перед плоскостью разреза - снят
    сеч, xb, шов = разрез_АА(L, [d for d in детали if not d.label.startswith("pos.2 ")])
    L.title(0, 175, "А-А")
    L.dimh(-П["L"] / 2, П["L"] / 2, Z_ПЛ_НИЗ, Z_НАСТ_НИЗ - 80)
    L.dimh(-П["болт_x"], П["болт_x"], Z_НАСТ_НИЗ - 40, Z_НАСТ_НИЗ - 105)
    L.dimv(Z_НАСТИЛ, Z_ПЛЕЧО, K["габарит"][0] / 2, 290, ф(-Z_НАСТИЛ))
    L.dimv(Z_НАСТИЛ, Z_ГОЛОВА, З["голова"][0] / 2, 330, "%s*" % ф(Z_ГОЛОВА - Z_НАСТИЛ))
    L.dimv(Z_ПЛЕЧО, Z_ГОЛОВА, З["голова"][0] / 2, 250, "%s*" % ф(Z_ГОЛОВА))
    по_метке = {}
    for метка, g in сеч:
        if not метка.startswith("pos."):
            continue
        n = int(метка.split()[0].split(".")[1])
        if n not in по_метке and not g.is_empty:
            по_метке[n] = g
    пункты = []
    for n in (1, 4, 5, 6, 9, 7, 8):
        if n in по_метке:
            g = по_метке[n]
            if n in (7, 8):          # втулка и шайба изолирующие - у болта справа
                g = g.intersection(box(0, -2000, 2000, 2000))
            t = _точка(g)
            if t:
                пункты.append((n, t))
    пункты += [(3, (-25.0, Z_ГОЛОВА - 12.0)), (10, (П["болт_x"] + 8.0, Z_ПЛ + 8.0)),
               (12, (П["болт_x"] + 20.0, Z_НАСТ_НИЗ - Б["шайба_изол"][2] - 2.5)), (11, (П["болт_x"] + 12.0, Z_НАСТ_НИЗ - 20.0))]
    L.позиции(пункты, -300.0, 300.0, 0.0)
    # выносной элемент I - шов корпуса с платиком
    ц_I = (K["полоса"]["x"][1] + 3.0, Z_ПЛ + 2.0)
    L.circle(ц_I, 12.0, "22_ТОНКИЕ")
    L.полка((ц_I[0] + 8.5, ц_I[1] + 8.5), (130.0, 22.0), "I", 5.0)
    # --- I (2 : 1)
    L.вид(1080.0, 420.0)
    k, R = 4.0, 30.0
    окно = Point(ц_I).buffer(R, 128)

    def увел(g):
        return affinity.scale(affinity.translate(g, -ц_I[0], -ц_I[1]), k, k, origin=(0, 0))
    for метка, g in сеч:
        gg = g.intersection(окно)
        if not gg.is_empty:
            a, st, pat = _штрих(метка)
            L.hatch(увел(gg), a, st, pat)
    шI = увел(шов.intersection(окно))
    L.hatch(шI, pattern="SOLID")
    L.circle((0.0, 0.0), R * k, "22_ТОНКИЕ")
    L.title(0.0, R * k + 10.0, "I (2 : 1)")
    ц = шI.centroid
    L.шов((ц.x - 2.0, ц.y + 2.0), (-95.0, 150.0), T.ШОВ["катет"], T.ШОВ["гост"], T.ШОВ["тип"], "ИУП")
    # --- Б-Б
    BX, BY = 1230.0, 830.0
    L.вид(BX, BY)
    сеч_б = разрез_ББ(L, детали)
    L.title(0, 175, "Б-Б")
    L.dimh(-П["B"] / 2, П["B"] / 2, Z_ПЛ_НИЗ, Z_НАСТ_НИЗ - 80)
    L.dimh(-П["болт_y"], П["болт_y"], Z_НАСТ_НИЗ - 40, Z_НАСТ_НИЗ - 105, None)
    L.dimh(-О["лист"][1] / 2, О["лист"][1] / 2, Z_ПР, Z_НАСТ_НИЗ - 130)
    ст = TW.стержень(TW.ЗАКРЫТО)
    bb = ст.bounding_box()
    мв = на_вид("слева")
    p2 = мв(((bb.min.X + bb.max.X) / 2.0 + 20.0, bb.min.Y + 20.0, З["z_отв"]))
    L.позиции([(2, p2)], -260.0, 260.0, 0.0)
    # --- вид сверху
    TX, TY = 560.0, 345.0
    L.вид(TX, TY)
    vis, _ = hlr(детали, "сверху")
    L.линии(vis)
    тело = контур([TW.корпус(), TW.платик()], "сверху")
    L.линии(hlr([TW.стержень(TW.ОТКРЫТО)], "сверху")[0], "24_ФАНТОМ", без=тело.buffer(0.3))
    голова = hlr([TW.запор(TW.ОТКРЫТО).intersect(призма(-200, 200, -200, 200, З["z_вала"][1], 200))], "сверху")[0]
    L.линии(голова, "24_ФАНТОМ")
    L.cross((0, 0), 80)
    for x in (-П["болт_x"], П["болт_x"]):
        for y in (-П["болт_y"], П["болт_y"]):
            L.cross((x, y), 22)
    r = С["r_конца"]
    ao, az = math.radians(TW.ОТКРЫТО), math.radians(TW.ЗАКРЫТО)
    L.dim_угол((0, 0), r - 25.0, TW.ОТКРЫТО, TW.ЗАКРЫТО, "%s°" % ф(T.ПОВОРОТ))
    L.полка((r * math.cos(ao), r * math.sin(ao)), (-190.0, -215.0), "открыто", 3.5)
    L.полка((r * math.cos(az), r * math.sin(az)), (190.0, -215.0), "закрыто", 3.5)
    yb = П["болт_y"]
    L.след([(-265.0, yb), (-xb, yb), (-xb, 0.0), (xb, 0.0), (xb, yb), (265.0, yb)], "А", (0, 1))
    L.след([(0.0, 222.0), (0.0, -222.0)], "Б", (1, 0))
    L.dimh(-TW.НАСТИЛ[0] / 2, TW.НАСТИЛ[0] / 2, -TW.НАСТИЛ[1] / 2, -TW.НАСТИЛ[1] / 2 - 62, "%s (вырезка настила)" % ф(TW.НАСТИЛ[0]))
    L.dimh(-О["лист"][0] / 2, О["лист"][0] / 2, О["лист"][1] / 2, TW.НАСТИЛ[1] / 2 + 45)
    L.dimv(-П["болт_y"], П["болт_y"], П["болт_x"], 275, None)
    L.полка((П["болт_x"] + 16, -П["болт_y"] - 12), (300.0, -150.0), "4 отв. ⌀%s в листе и настиле" % ф(Б["втулка"][0] + 0.6, 1), 3.0)
    # --- характеристика и ТТ
    L.вид(0.0, 0.0)
    S = н["SWL"]
    пр = н["предельный"]
    rows = [["Рабочая нагрузка на опору (SWL) - отрыв, сжатие, сдвиг", "%s, %s, %s кН" % (ф(S["отрыв"]), ф(S["сжатие"]), ф(S["сдвиг"]))],
            ["Предельная расчётная - отрыв, сжатие, сдвиг", "%s, %s, %s кН" % (ф(пр["отрыв"], 1), ф(пр["сжатие"], 1), ф(пр["сдвиг"], 1))],
            ["Расчётный модуль", "%s %s т, только в ряду ДП" % (н["модуль"][0], ф(н["модуль"][1], 1))],
            ["Высота опоры над настилом", "%s мм" % ф(T.высота_опоры() * 1000)],
            ["Поворот рукоятки «открыто» - «закрыто»", "%s°" % ф(T.ПОВОРОТ)],
            ["Масса узла без листа поз. 9, с листом", "%s кг, %s кг" % (ф(м["узел"], 1), ф(м["узел_с_листом"], 1))],
            ["Фундаментов на судно", "%d" % T.программа()["на_судно"]]]
    D.table(L.msp, 1302.0, 560.0, sc, ["Техническая характеристика", "Значение"], rows, [118, 67], h_row=7.0)
    ш = T.ШОВ
    notes = ("*Размеры для справок.",
             "Корпус поз. 1 приварить к платику поз. 4 швом %s по замкнутому контуру корпуса, катет %s мм, "
             "проволока %s в смеси газов (%s). Контроль шва ВИК 100 %%." % (ш["тип"], ф(ш["катет"]), ш["проволока"], ш["газ"]),
             "Покрытие сварного корпуса и запора поз. 3 - грунтовка ГФ-021 в два слоя, эмаль ПФ-115. Отверстие ⌀30, вал "
             "поз. 3 и резьбу М14×1,5 не окрашивать.",
             "Вал поз. 3 смазать Литол-24 ГОСТ 21150-2017 и вставить в корпус сверху. Шайбу поз. 5 завести снизу через окно "
             "платика в проточку вала.",
             "Стержень поз. 2 ввернуть через прорезь корпуса в резьбу вала на анаэробном фиксаторе резьбы средней прочности.",
             "Поворот запора от выреза до выреза корпуса %s° без заеданий, в положениях «открыто» и «закрыто» стержень входит "
             "в вырез." % ф(T.ПОВОРОТ),
             "Лист поз. 9 приварить к настилу над подпалубной балкой %s при постройке судна. Отверстия в листе и настиле "
             "сверлить по платику на месте." % T.балка()["обозначение"],
             "Прокладку поз. 6 и втулки поз. 7 ставить на герметике У-30МЭС-5 ГОСТ 13489-79.",
             "Болты поз. 10 затянуть крест-накрест моментом %d Н·м." % T.момент_затяжки(),
             "Рабочую нагрузку (SWL) и номер фундамента нанести на платик краской.",
             "Испытания - по программе %s ПМ." % T.MARK)
    return L.save(T.MARK.replace(".", "_") + "_СБ", T.MARK + " СБ", T.NAME,
                  "Сборочный чертёж. %d шт. на судно, фитинг ISO 1161 - тонкой штрихпунктирной" % T.программа()["на_судно"],
                  notes, "Масса %s кг" % ф(м["узел"], 1), wrap=82)


# ------------------------------------------------------------------ детали
def _вид_тела(L, тело, вид, скрытые=False):
    vis, hid = hlr([тело], вид, скрытые)
    L.линии(vis)
    if скрытые:
        L.линии(hid, "21_НЕВИДИМЫЕ")


def _разрез_тела(L, тело, ось, c, вид, метка="pos.1 "):
    тела, сеч = разрез([тело], [(ось, c, None)], вид, целые=())
    L.линии(hlr(тела, вид)[0])
    for _, g in сеч:
        a, st, pat = _штрих(метка)
        L.hatch(g, a, st, pat)
    return unary_union([g for _, g in сеч])


def корпус_лист():
    L = Лист(1, "A1")
    м = T.массы()
    b = TW.корпус()
    x1, x0 = K["полоса"]["x"][1], K["полоса"]["x"][0]
    zb, zt = K["z"]
    # --- главный вид (спереди)
    L.вид(190.0, 440.0)
    _вид_тела(L, b, "спереди")
    L.axis((0, zb - 12), (0, zt + 12))
    L.dimh(-K["кромка"], K["кромка"], -40.0, zb - 34, ф(K["габарит"][0]))
    L.dimh(-x1, x1, zb, zb - 16)
    L.dimh(-K["центратор"][0] / 2, K["центратор"][0] / 2, zt, zt + 14)
    L.dimh(-72.56, 72.56, Z_ПЛЕЧО, zt + 30, "%s" % ф(2 * 72.56, 1))
    L.dimv(zb, zt, -K["кромка"], -K["кромка"] - 34, ф(K["габарит"][2]))
    L.dimv(zb, Z_ПЛЕЧО, -x1, -K["кромка"] - 18)
    L.dimv(Z_ПЛЕЧО, zt, K["центратор"][0] / 2, 100)
    L.rough(50.0, Z_ПЛЕЧО, "12,5")
    L.rough(70.0, zb, "12,5", up=False)
    zc = sum(K["полость"]["z"]) / 2.0
    L.след([(-142.0, zc), (122.0, zc)], "Б", (0, -1))
    # --- вид сверху
    L.вид(190.0, 190.0)
    _вид_тела(L, b, "сверху")
    L.cross((0, 0), 100)
    L.dimv(-80.0, 80.0, K["кромка"], 118, ф(K["габарит"][1]))
    L.dimv(-K["центратор"][1] / 2, K["центратор"][1] / 2, -K["центратор"][0] / 2, -112, ф(K["центратор"][1]))
    L.полка((K["d_отв"] / 2 * 0.7, K["d_отв"] / 2 * 0.7), (60.0, 100.0), "⌀%sH9 сквозное, Ra 3,2" % ф(K["d_отв"]), 3.0)
    L.след([(0.0, 98.0), (0.0, -98.0)], "А", (1, 0))
    # --- А-А (x = 0, вид слева)
    L.вид(470.0, 440.0)
    _разрез_тела(L, b, "x", 0.0, "слева")
    L.title(0, zt + 42, "А-А")
    L.axis((0, zb - 12), (0, zt + 12))
    L.dimh(-K["d_отв"] / 2, K["d_отв"] / 2, zt, zt + 16, "⌀%sH9" % ф(K["d_отв"]))
    п = K["полость"]
    L.dimv(п["z"][0], п["z"][1], 40.0, 98.0, ф(п["z"][1] - п["z"][0]))
    L.dimv(п["z"][1], Z_ПЛЕЧО, 40.0, 116.0, ф(-п["z"][1]))
    L.dimv(zb, K["низ_z"], -20.0, -100.0, ф(K["низ_z"] - zb))
    L.dimh(-80.0, 80.0, zb, zb - 18, ф(K["габарит"][1]))
    L.полка((58.0, zc), (120.0, zc - 45.0), "полость рукоятки", 3.0)
    # --- Б-Б (z = середина полости, вид сверху)
    L.вид(470.0, 190.0)
    _разрез_тела(L, b, "z", zc, "сверху")
    L.title(0, 95, "Б-Б")
    L.cross((0, 0), 90)
    r = 58.0
    for a in (TW.ОТКРЫТО, TW.ЗАКРЫТО):
        L.axis((0, 0), (r * math.cos(math.radians(a)), r * math.sin(math.radians(a))))
    L.dim_угол((0, 0), 48.0, TW.ОТКРЫТО, TW.ЗАКРЫТО, "%s°" % ф(T.ПОВОРОТ))
    L.полка((0.0, -40.0), (95.0, -112.0), "положения рукоятки", 3.0)
    L.rough_угол("Rz 320")
    o = T.отливка()
    notes = ("Отливка - сталь 20ГСЛ ГОСТ 977-88, группа 2. %s." % T.ТОЧНОСТЬ,
             "Неуказанные размеры, литейные радиусы и уклоны - по электронной модели детали. Грани «ласточкина хвоста» - "
             "под %s° к вертикали." % ф(K["хвост_угол"]),
             "Термообработка - %s. Твёрдость не более 187 НВ." % T.МАТЕРИАЛЫ["20ГСЛ"]["термо"],
             "Механические свойства на образцах от плавки - σт не менее %s МПа, σв не менее %s МПа, δ не менее %s %%, "
             "KCU не менее %s кДж/м²." % (ф(T.МАТЕРИАЛЫ["20ГСЛ"]["σт"]), ф(T.МАТЕРИАЛЫ["20ГСЛ"]["σв"]),
                                         T.МАТЕРИАЛЫ["20ГСЛ"]["δ"], T.МАТЕРИАЛЫ["20ГСЛ"]["KCU"]),
             "Раковины, трещины и засоры на опорных полосах, плече и центраторе не допускаются. Исправление дефектов "
             "заваркой - по ГОСТ 977-88, на плече и центраторе - с разрешения конструктора.",
             "Отверстие ⌀%sH9 льётся ⌀%s под сверление и развёртывание, опорные полосы и плечо зачистить в размер." % (
                 ф(K["d_отв"]), ф(K["d_отв"] - 2 * T.ПРИПУСКИ["отверстие"])),
             "Неуказанные предельные отклонения размеров обработанных поверхностей - H14, h14, ±IT14/2.",
             "Маркировать литыми знаками «ВГ-46» и номером плавки, клеймо ОТК ударным способом.")
    return L.save("ВГ-2026_46_01_корпус", "ВГ-2026.46.01", "Корпус",
                  "Деталь поз. 1 узла %s. Отливка %s кг, деталь %s кг" % (T.MARK, ф(o["масса_отливки"], 2), ф(м["корпус"], 2)),
                  notes, "Сталь 20ГСЛ ГОСТ 977-88, масса %s кг" % ф(м["корпус"], 2), wrap=86)


def стержень_лист():
    L = Лист(1, "A4")
    d, l = С["d"], С["l"]
    рез, lр = С["резьба"]
    L.вид(40.0, 205.0)
    f = 1.0
    L.pl([(f, -d / 2), (l - f, -d / 2), (l, -d / 2 + f), (l, d / 2 - f), (l - f, d / 2), (f, d / 2), (0, d / 2 - f),
          (0, -d / 2 + f)], close=True)
    for x in (f, l - f):
        L.line((x, -d / 2), (x, d / 2))
    d1 = d - 1.227 * 1.5
    L.line((0.0, d1 / 2), (lр, d1 / 2), "22_ТОНКИЕ")
    L.line((0.0, -d1 / 2), (lр, -d1 / 2), "22_ТОНКИЕ")
    L.line((lр, -d / 2), (lр, d / 2))
    L.axis((-8.0, 0.0), (l + 8.0, 0.0))
    L.dimh(0.0, l, -d / 2, -30.0)
    L.dimh(0.0, lр, d / 2, 20.0)
    L.dimv(-d / 2, d / 2, 70.0, 70.0 + 0.0, "⌀%sh11" % ф(d))
    L.полка((6.0, d1 / 2 + 0.5), (38.0, 44.0), рез + "-6g", 3.0)
    L.полка((l - 0.5, d / 2 - 0.5), (l - 10.0, 34.0), "2 фаски 1×45°", 3.0)
    L.rough_угол("Ra 6,3")
    notes = ("Круг 16 ГОСТ 2590-2006 из стали 40Х ГОСТ 4543-2016, улучшение 235…277 НВ.",
             "Неуказанные предельные отклонения размеров h14, ±IT14/2.",
             "Покрытие - грунтовка ГФ-021, эмаль ПФ-115. Резьбу не окрашивать.")
    return L.save("ВГ-2026_46_02_стержень", "ВГ-2026.46.02", "Стержень",
                  "Деталь поз. 2 узла %s, рукоятка запора" % T.MARK, notes,
                  "Круг 40Х ГОСТ 2590-2006, масса %s кг" % ф(T.массы()["стержень"], 2))


def запор_лист():
    L = Лист(1, "A3")
    угол = 0.0                                              # резьбовое отверстие - вдоль X
    з = TW.запор(угол)
    ах = TW._head_угол(угол) % 180.0                       # длинная ось головы в плане
    z0, z1 = З["z_вала"]
    длина, ширина, прямая, конус, (дл_в, шир_в) = З["голова"]
    # --- А-А по оси резьбового отверстия
    L.вид(95.0, 170.0)
    _разрез_тела(L, з, "y", 0.0, "спереди", "pos.3 ")
    L.axis((0, z0 - 10), (0, Z_ГОЛОВА + 10))
    L.axis((-26.0, З["z_отв"]), (26.0, З["z_отв"]))
    L.title(-40.0, Z_ГОЛОВА + 18, "А-А")
    L.dimh(-З["вал"] / 2, З["вал"] / 2, 5.0, 5.0, "⌀%sf9" % ф(З["вал"]))
    пр = З["проточка"]
    L.dimh(-пр["d"] / 2, пр["d"] / 2, sum(пр["z"]) / 2, sum(пр["z"]) / 2, "⌀%s" % ф(пр["d"]))
    L.dimv(z0, Z_ГОЛОВА, -26.0, -62.0, ф(Z_ГОЛОВА - z0, 1))
    L.dimv(z0, z1, -15.0, -46.0, ф(z1 - z0, 1))
    L.dimv(пр["z"][0], пр["z"][1], 15.0, 36.0, ф(пр["z"][1] - пр["z"][0], 1))
    L.dimv(z0, пр["z"][0], 15.0, 36.0, ф(пр["z"][0] - z0, 1))
    L.dimv(z0, З["z_отв"], 15.0, 52.0, ф(З["z_отв"] - z0, 1))
    L.dimv(z1, z1 + прямая, 30.0, 62.0, ф(прямая))
    L.dimv(z1 + прямая, Z_ГОЛОВА, 30.0, 62.0, ф(конус))
    L.полка((-6.0, З["z_отв"] - 3.0), (-44.0, z0 - 12.0), "М14×1,5-6Н", 3.0)
    L.line((0.0, Z_ГОЛОВА + 45.0), (0.0, Z_ГОЛОВА + 31.0))
    L._стрелка((0.0, Z_ГОЛОВА + 27.0), (0.0, Z_ГОЛОВА + 31.0))
    L.text(6.0, Z_ГОЛОВА + 40.0, "Б", 5.0)
    # --- вид Б (сверху)
    L.вид(250.0, 175.0)
    _вид_тела(L, з, "сверху")
    L.title(0, 70, "Б")
    L.cross((0, 0), 40)
    ca, sa = math.cos(math.radians(ах)), math.sin(math.radians(ах))
    L.axis((-62 * ca, -62 * sa), (62 * ca, 62 * sa))
    L.dim((-длина / 2 * ca, -длина / 2 * sa), (длина / 2 * ca, длина / 2 * sa),
          (-sa * 45.0, ca * 45.0), ах)
    L.dim((sa * ширина / 2, -ca * ширина / 2), (-sa * ширина / 2, ca * ширина / 2), (ca * 72.0, sa * 72.0), ах + 90.0)
    L.dim_угол((0, 0), 34.0, 0.0, ах, "%s°" % ф(ах))
    L.полка((дл_в / 2 * ca * 0.8, дл_в / 2 * sa * 0.8), (70.0, -48.0), "верх головы %s × %s" % (ф(дл_в), ф(шир_в)), 3.0)
    # след А-А на виде Б и стрелка вида Б на разрезе
    L.след([(-66.0, 0.0), (66.0, 0.0)], "А", (0, 1))
    L.rough_угол("Ra 12,5")
    notes = ("Поковка группы IV ГОСТ 8479-70, КП 590, сталь 40Х ГОСТ 4543-2016, 235…277 НВ.",
             "Резьба М14×1,5-6Н сквозная, ось перпендикулярна оси вала, под %s° к длинной оси головы." % ф(ах),
             "Шероховатость вала ⌀%sf9 - Ra 1,6. Неуказанные радиусы R2, неуказанные предельные отклонения размеров H14, h14, ±IT14/2." % ф(З["вал"]),
             "Покрытие головки - грунтовка ГФ-021, эмаль ПФ-115. Вал ⌀%sf9, проточку и резьбу не окрашивать." % ф(З["вал"]))
    return L.save("ВГ-2026_46_03_запор", "ВГ-2026.46.03", "Элемент запирающий",
                  "Деталь поз. 3 узла %s, поковка по кооперации" % T.MARK, notes,
                  "Сталь 40Х ГОСТ 4543-2016, масса %s кг" % ф(T.массы()["запор"], 2))


def платик_лист():
    L = Лист(2, "A3")
    p = TW.платик()
    Lп, Bп, t = П["L"], П["B"], П["t"]
    L.вид(270.0, 400.0)
    _вид_тела(L, p, "сверху")
    L.cross((0, 0), Lп / 2 + 15)
    for sx in (-1, 1):
        for sy in (-1, 1):
            L.cross((sx * П["болт_x"], sy * П["болт_y"]), 30)
    L.dimh(-Lп / 2, Lп / 2, -Bп / 2, -Bп / 2 - 30)
    L.dimh(-П["болт_x"], П["болт_x"], П["болт_y"], Bп / 2 + 25)
    L.dimv(-Bп / 2, Bп / 2, Lп / 2, Lп / 2 + 40)
    L.dimv(-П["болт_y"], П["болт_y"], П["болт_x"], Lп / 2 + 75)
    L.dimh(-П["окно"][0] / 2, П["окно"][0] / 2, П["окно"][1] / 2, П["окно"][1] / 2 + 30)
    L.dimv(-П["окно"][1] / 2, П["окно"][1] / 2, -П["окно"][0] / 2 + 20, -П["окно"][0] / 2 - 30)
    ox, oy = -П["болт_x"], -П["болт_y"]
    L.полка((ox + 8.0, oy + П["овал"][0] / 2 - 1.0), (-60.0, -48.0), "4 паза %s × %s" % (ф(П["овал"][0]), ф(П["овал"][1])), 3.0)
    L.след([(-Lп / 2 - 14, 0.0), (Lп / 2 + 14, 0.0)], "А", (0, 1))
    # --- А-А
    L.вид(270.0, 170.0 - Z_ПЛ)
    _разрез_тела(L, p, "y", 0.0, "спереди", "pos.4 ")
    L.title(0, Z_ПЛ + 22, "А-А")
    L.dimv(Z_ПЛ_НИЗ, Z_ПЛ, -Lп / 2, -Lп / 2 - 20, ф(t))
    L.rough_угол("Rz 80")
    notes = ("Лист 20 09Г2С-325 ГОСТ 19281-2014. Резка плазменная, неуказанные предельные отклонения ±1 мм.",
             "Концы пазов калибровать сверлом ⌀%s по кондуктору." % ф(П["овал"][0]),
             "Грат и окалину удалить, острые кромки притупить.")
    return L.save("ВГ-2026_46_04_платик", "ВГ-2026.46.04", "Платик",
                  "Деталь поз. 4 узла %s" % T.MARK, notes,
                  "Лист 09Г2С ГОСТ 19281-2014, масса %s кг" % ф(T.массы()["платик"], 2))


def шайба_лист():
    L = Лист(1, "A4")
    ш = TW.шайба()
    Dш, dш, t, разрез_ = Ш["D"], Ш["d"], Ш["t"], Ш["разрез"]
    L.вид(65.0, 215.0)
    _вид_тела(L, ш, "сверху")
    L.cross((0, 0), 34)
    L.dimv(-разрез_ / 2, разрез_ / 2, Dш / 2, Dш / 2 + 24, ф(разрез_, 1))
    L.полка((Dш / 2 * 0.7, Dш / 2 * 0.7), (30.0, 40.0), "⌀%s" % ф(Dш), 3.0)
    L.полка((-dш / 2 * 0.7, -dш / 2 * 0.7), (24.0, -40.0), "⌀%s" % ф(dш, 1), 3.0)
    L.след([(-Dш / 2 - 8, 0.0), (Dш / 2 + 8, 0.0)], "А", (0, 1))
    L.вид(160.0, 215.0 - Ш["z"][0])
    _разрез_тела(L, ш, "y", 0.0, "спереди", "pos.5 ")
    L.title(0, Ш["z"][1] + 12, "А-А")
    L.dimv(Ш["z"][0], Ш["z"][1], Dш / 2, Dш / 2 + 12, ф(t))
    L.rough_угол("Rz 80")
    notes = ("Лист 12 09Г2С-325 ГОСТ 19281-2014. Резка плазменная, неуказанные предельные отклонения ±0,5 мм.",
             "Опорные торцы плоские, отклонение от плоскостности не более 0,2 мм. Грат удалить.")
    return L.save("ВГ-2026_46_05_шайба", "ВГ-2026.46.05", "Шайба разрезная",
                  "Деталь поз. 5 узла %s" % T.MARK, notes,
                  "Лист 09Г2С ГОСТ 19281-2014, масса %s кг" % ф(T.массы()["шайба"], 2))


# ------------------------------------------------------------------ литьё и оснастка
def _разъём(L, x0, x1, z):
    """Линия разъёма формы и модели (ГОСТ 3.1125-88): штрихпунктирная, стрелки «В» и «Н», знак «МФ»."""
    s = L.sc
    L.line((x0, z), (x1, z), "26_РАЗЪЁМ")
    L.line((x1, z), (x1, z + 14 * s), "20_ВИДИМЫЕ")
    L.line((x1, z), (x1, z - 14 * s), "20_ВИДИМЫЕ")
    L.text(x1 + 5 * s, z + 9 * s, "В", 3.5)
    L.text(x1 + 5 * s, z - 9 * s, "Н", 3.5)
    L.text(x1 - 12 * s, z + 4 * s, "МФ", 3.5)


def литьё_лист():
    L = Лист(1, "A1")
    о, л = T.отливка(), T.ЛИТЬЁ
    отл, дет = TW.отливка(), TW.корпус()
    ст1, ст2 = TW.стержень_1(), TW.стержень_2()
    Lf, Bf, Hв, Hн = л["опока"]
    zр = K["z"][0]
    Wr, Lr, Hr = о["прибыль"]
    # --- А-А по прибылям (y = 10)
    yr = 10.0
    L.вид(210.0, 390.0)
    g = сечение(отл, "y", yr, "спереди")
    L.hatch(g, 45.0, 1.0)
    L.geom(сечение(дет, "y", yr, "спереди"), "22_ТОНКИЕ")
    L.hatch(сечение(ст1, "y", yr, "спереди"), 45.0, 0.6, "ANSI37")
    L.rect(-150.0, zр - Hн, 150.0, zр + Hв, "22_ТОНКИЕ")
    for x in (-150.0, 150.0):
        L.обрыв(x, zр - Hн - 4, zр + Hв + 4)
    _разъём(L, -170.0, 175.0, zр)
    L.title(0, zр + Hв + 14, "А-А")
    L.text(0.0, 14.0, "Ст. 1", 3.5)
    xc = (K["центратор"][0] / 2.0 + 72.56) / 2.0 + 2.0
    L.dimv(Z_ПЛЕЧО, Z_ПЛЕЧО + Hr, xc + Wr / 2, 110.0, ф(Hr))
    L.dimh(xc - Wr / 2, xc + Wr / 2, Z_ПЛЕЧО + Hr, Z_ПЛЕЧО + Hr + 14.0, ф(Wr))
    L.dimv(zр - Hн, zр, -150.0, -165.0, ф(Hн))
    L.dimv(zр, zр + Hв, -150.0, -165.0, ф(Hв))
    L.полка((xc, Z_ПЛЕЧО + Hr - 12.0), (60.0, 100.0), "прибыль открытая", 3.0)
    L.полка((-40.0, -44.0), (-110.0, -95.0), "припуск %s" % ф(T.ПРИПУСКИ["полосы"]), 3.0)
    # --- Б-Б по оси (x = 0)
    L.вид(530.0, 390.0)
    L.hatch(сечение(отл, "x", 0.0, "слева"), 45.0, 1.0)
    L.geom(сечение(дет, "x", 0.0, "слева"), "22_ТОНКИЕ")
    L.hatch(сечение(ст1, "x", 0.0, "слева"), 45.0, 0.6, "ANSI37")
    L.hatch(сечение(ст2, "x", 0.0, "слева"), 45.0, 0.6, "ANSI37")
    L.rect(-110.0, zр - Hн, 110.0, zр + Hв, "22_ТОНКИЕ")
    for x in (-110.0, 110.0):
        L.обрыв(x, zр - Hн - 4, zр + Hв + 4)
    _разъём(L, -125.0, 120.0, zр)
    L.title(0, zр + Hв + 14, "Б-Б")
    L.полка((0.0, 40.0), (-70.0, 80.0), "Ст. 1", 3.0)
    L.полка((70.0, -30.0), (40.0, -110.0), "Ст. 2, знак до разъёма", 3.0)
    L.dimh(-K["d_отв"] / 2 + T.ПРИПУСКИ["отверстие"], K["d_отв"] / 2 - T.ПРИПУСКИ["отверстие"], K["z"][1] + TW.ЗНАК_СТ1,
           K["z"][1] + TW.ЗНАК_СТ1 + 12.0, "⌀%s" % ф(K["d_отв"] - 2 * T.ПРИПУСКИ["отверстие"]))
    L.dimv(K["z"][1], K["z"][1] + TW.ЗНАК_СТ1, 13.0, 40.0, ф(TW.ЗНАК_СТ1))
    # --- план формы, М 1 : 4 (верхняя полуформа снята)
    k = 0.25
    L.вид(330.0, 125.0)
    L.rect(-Lf / 2 * k, -Bf / 2 * k, Lf / 2 * k, Bf / 2 * k)
    план = hlr([отл], "сверху")[0]
    for sx in (-1.0, 1.0):
        L.линии(план, dx=sx * Lf / 4 * k, k=k)
    r_ст = о["d_стояка"] / 2.0
    L.circle((0, 0), r_ст * k)
    L.circle((0, 0), (r_ст + 8.0) * k, "22_ТОНКИЕ")
    x_к = Lf / 4 - K["кромка"] - 25.0
    L.rect(-x_к * k, -10.0 * k, x_к * k, 10.0 * k)
    for sx in (-1.0, 1.0):
        for y in (-40.0, 40.0):
            xa, xb_ = sx * x_к, sx * (Lf / 4 - K["полоса"]["x"][1])
            L.rect(min(xa, xb_) * k, (y - 8.0) * k, max(xa, xb_) * k, (y + 8.0) * k)
        L.rect((sx * x_к - 6.0) * k, -48.0 * k, (sx * x_к + 6.0) * k, 48.0 * k)
    L.title(0, Bf / 2 * k + 8.0, "План формы, М 1 : 4 (верхняя полуформа снята)")
    L.dimh(-Lf / 2 * k, Lf / 2 * k, -Bf / 2 * k, -Bf / 2 * k - 14.0, ф(Lf))
    L.dimv(-Bf / 2 * k, Bf / 2 * k, Lf / 2 * k, Lf / 2 * k + 14.0, ф(Bf))
    L.полка((0.0, 0.0), (-100.0, 55.0), "стояк ⌀%s" % ф(о["d_стояка"]), 3.0)
    L.полка((-x_к * k + 5.0, 0.0), (-110.0, -70.0), "коллектор", 3.0)
    L.полка(((x_к + 8.0) * k, 40.0 * k), (100.0, 62.0), "питатели, %d шт." % о["питателей"], 3.0)
    # --- таблица
    L.вид(0.0, 0.0)
    rows = [["Форма", "ХТС, опоки %s × %s × %s/%s" % tuple(ф(v) for v in л["опока"])],
            ["Отливок в форме, металла на форму", "%d, %s кг" % (л["отливок_в_форме"], ф(о["металл_на_форму"], 1))],
            ["Масса детали, отливки, прибылей на отливку", "%s, %s, %s кг" % (ф(о["масса_детали"], 2), ф(о["масса_отливки"], 2),
                                                                            ф(о["масса_прибылей"], 2))],
            ["Выход годного", "%s %%" % ф(о["выход_годного"], 1)],
            ["Модуль отливки, теплового узла, прибыли", "%s, %s, %s мм" % (ф(о["модуль_отливки"], 1), ф(о["модуль_узла"], 1),
                                                                         ф(о["модуль_прибыли"], 1))],
            ["Питание нужно, даёт прибыль", "%s, %s кг" % (ф(о["питание_нужно_кг"], 2), ф(о["питание_отдаёт_кг"], 2))],
            ["Заливка τ = S√G", "%s с" % ф(о["τ_с"], 1)],
            ["Расчётный напор", "%s мм" % ф(о["H_р_мм"])],
            ["Fст, Fкол, Fпит", "%s, %s, %s см²" % (ф(о["F_ст"], 2), ф(о["F_шл"], 2), ф(о["F_пит"], 2))],
            ["Температура заливки", "%d…%d °С" % л["t_заливки"]],
            ["Смесь на форму, смола", "%s т, %s кг" % (ф(о["смесь_на_форму_т"], 3), ф(о["смола_кг"], 2))],
            ["Стержни Ст. 1 и Ст. 2 на отливку", "%s кг смеси" % ф(о["стержни_кг"], 2)],
            ["Груз на форму", "%d кг" % T.груз_на_форму()["груз_кг"]]]
    D.table(L.msp, 651.0, 560.0, 1, ["Литейная технология", "Значение"], rows, [100, 85], h_row=6.2)
    notes = ("Элементы литейной формы - по ГОСТ 3.1125-88. Отливка в верхней полуформе, разъём по опорным полосам.",
             "Форма и стержни - ХТС на щелочной фенольной смоле %s %% от песка, отвердитель %s %% от смолы, песок %s." % (
                 ф(л["смесь"]["смола"], 1), ф(л["смесь"]["отвердитель"]), л["смесь"]["песок"]),
             "Форму и стержни окрасить - краска %s." % л["краска"],
             "Знак стержня Ст. 2 выведен через лицевую грань и опущен до разъёма. Ст. 2 ставить на нижнюю полуформу, Ст. 1 - "
             "в знаки обеих полуформ.",
             "Припуск на литое отверстие %s мм на сторону, на опорные полосы и плечо %s мм." % (ф(T.ПРИПУСКИ["отверстие"]),
                                                                                           ф(T.ПРИПУСКИ["полосы"])),
             "Прибыли открытые %s × %s × %s, зеркало засыпать утепляющей смесью сразу после заливки." % (ф(Lr), ф(Wr), ф(Hr)),
             "Выдержка отливок в форме не менее %s ч, прибыли отрезать после термообработки." % ф(л["охлаждение_ч"]))
    return L.save("ВГ-2026_46_01_ЛФ_отливка", "ВГ-2026.46.01 ЛФ", "Корпус. Отливка",
                  "Элементы литейной формы. Разъём, припуски, прибыли, стержни, литники", notes,
                  "Сталь 20ГСЛ ГОСТ 977-88, отливка %s кг" % ф(о["масса_отливки"], 2), wrap=86)


def модель_лист():
    L = Лист(1, "A1")
    м_ = TW.модель()
    kу = 1.0 + T.УСАДКА / 100.0
    bb = м_.bounding_box()
    L.вид(200.0, 430.0)
    _вид_тела(L, м_, "спереди")
    L.axis((0, bb.min.Z - 12), (0, bb.max.Z + 12))
    _разъём(L, -130.0, 130.0, K["z"][0] * kу)
    L.dimh(bb.min.X, bb.max.X, K["z"][0] * kу, bb.min.Z - 40.0, ф(bb.max.X - bb.min.X, 1))
    L.dimv(K["z"][0] * kу, bb.max.Z, bb.min.X, bb.min.X - 25.0, ф(bb.max.Z - K["z"][0] * kу, 1))
    L.dimv(bb.min.Z, K["z"][0] * kу, bb.min.X, bb.min.X - 25.0, ф(K["z"][0] * kу - bb.min.Z, 1))
    L.полка((0.0, bb.max.Z - 5.0), (70.0, bb.max.Z + 25.0), "знак Ст. 1", 3.0)
    L.полка((0.0, bb.min.Z + 5.0), (60.0, bb.min.Z - 22.0), "знак Ст. 1", 3.0)
    L.вид(200.0, 190.0)
    _вид_тела(L, м_, "сверху")
    L.cross((0, 0), 100)
    L.dimv(bb.min.Y, bb.max.Y, bb.max.X, bb.max.X + 25.0, ф(bb.max.Y - bb.min.Y, 1))
    L.полка((0.0, bb.min.Y + 8.0), (-110.0, bb.min.Y - 12.0), "знак Ст. 2", 3.0)
    L.вид(500.0, 430.0)
    _вид_тела(L, м_, "слева")
    L.axis((0, bb.min.Z - 12), (0, bb.max.Z + 12))
    _разъём(L, -110.0, 110.0, K["z"][0] * kу)
    L.dimh(-bb.max.Y, -bb.min.Y, K["z"][0] * kу, bb.min.Z - 40.0, ф(bb.max.Y - bb.min.Y, 1))
    o = T.отливка()
    notes = ("Модель деревянная, сосна ГОСТ 8486-86, влажность не более 12 %%. Размеры - с усадкой стали %s %%, "
             "модель больше детали в %s раза." % (ф(T.УСАДКА, 1), ф(kу, 2)),
             "Формовочные уклоны %s." % T.УКЛОН,
             "Модель окрасить - поверхности отливки красным, знаки стержней чёрным, линию разъёма и прибыли - по ГОСТ 3.1125-88.",
             "Прибыли %s × %s × %s - съёмные, на шипах." % tuple(ф(v) for v in (o["прибыль"][1], o["прибыль"][0], o["прибыль"][2])),
             "Две модели на плите с литниковой системой - по листу ВГ-2026.46.01 ЛФ. Стойкость комплекта - не менее %d съёмов." %
             (T.программа()["всего"] // 2 + 20),
             "Неуказанные размеры - по электронной модели отливки со знаками стержней.")
    return L.save("ВГ-2026_46_01-МД_модель", "ВГ-2026.46.01-МД", "Модель корпуса",
                  "Оснастка - модель отливки ВГ-2026.46.01 со знаками стержней Ст. 1 и Ст. 2", notes,
                  "Сосна ГОСТ 8486-86", wrap=86)


def ящик_1_лист():
    L = Лист(1, "A3")
    kу = 1.0 + T.УСАДКА / 100.0
    d = (K["d_отв"] - 2 * T.ПРИПУСКИ["отверстие"]) * kу
    lс = (K["z"][1] - K["низ_z"] + 2 * TW.ЗНАК_СТ1) * kу
    ст, hs = 25.0, 30.0
    Lb, Bb = lс + ст, d + 2 * ст
    # --- план нижней половины (засыпка с открытого торца)
    L.вид(120.0, 188.0)
    L.rect(0.0, -Bb / 2, Lb, Bb / 2)
    L.rect(0.0, -d / 2, lс, d / 2)
    L.axis((-8.0, 0.0), (Lb + 8.0, 0.0))
    for x in (ст, Lb - ст):
        L.circle((x, Bb / 2 - 10.0), 4.0)
        L.circle((x, -Bb / 2 + 10.0), 4.0)
        L.cross((x, Bb / 2 - 10.0), 7.0)
        L.cross((x, -Bb / 2 + 10.0), 7.0)
    L.dimh(0.0, Lb, -Bb / 2, -Bb / 2 - 26.0)
    L.dimh(0.0, lс, d / 2, Bb / 2 + 26.0, ф(lс, 1))
    L.dimv(-Bb / 2, Bb / 2, Lb, Lb + 14.0)
    L.полка((Lb - ст, Bb / 2 - 14.0), (Lb + 5.0, Bb / 2 + 26.0), "4 штифта ⌀8", 3.0)
    L.title(Lb / 2, Bb / 2 + 44.0, "Половина нижняя, вид сверху")
    L.след([(Lb * 0.45, Bb / 2 + 8.0), (Lb * 0.45, -Bb / 2 - 8.0)], "А", (1, 0))
    # --- А-А
    L.вид(340.0, 205.0)
    for sg in (-1.0, 1.0):
        g = box(-Bb / 2, 0.0, Bb / 2, sg * hs).difference(Point(0.0, 0.0).buffer(d / 2, 128))
        L.hatch(g, 45.0 if sg > 0 else 135.0, 1.0)
    L.axis((-Bb / 2 - 6, 0.0), (Bb / 2 + 6, 0.0))
    L.cross((0.0, 0.0), d / 2 + 6)
    L.dimh(-d / 2, d / 2, 0.0, hs + 12.0, "⌀%s" % ф(d, 1))
    L.dimv(-hs, hs, Bb / 2, Bb / 2 + 12.0)
    L.title(0.0, hs + 24.0, "А-А")
    notes = ("Ящик деревянный разъёмный по оси стержня, берёза ГОСТ 2695-83. Размеры полости - с усадкой %s %%." % ф(T.УСАДКА, 1),
             "Стержень Ст. 1 - ХТС, засыпка с торца, уплотнение вибрацией, съём через %d мин." % T.ЛИТЬЁ["смесь"]["съём_мин"],
             "Рабочие поверхности - Ra 3,2, покрыть лаком. Разделительный состав перед каждой засыпкой.")
    return L.save("ВГ-2026_46_01-СЯ1_ящик_стержневой", "ВГ-2026.46.01-СЯ1", "Ящик стержневой",
                  "Оснастка - стержень Ст. 1 литого отверстия корпуса ВГ-2026.46.01", notes, "Берёза ГОСТ 2695-83")


def ящик_2_лист():
    L = Лист(1, "A3")
    kу = 1.0 + T.УСАДКА / 100.0
    ст2 = TW.стержень_2().scale(kу)
    bb = ст2.bounding_box()
    w = 22.0
    x0, x1, y0, y1 = bb.min.X - w, bb.max.X + w, bb.min.Y - w, bb.max.Y + w
    # --- план: полость стержня в ящике, засыпка сверху
    L.вид(140.0, 200.0 - (y0 + y1) / 2)
    L.rect(x0, y0, x1, y1)
    L.линии(hlr([ст2], "сверху")[0])
    L.line((0.0, y0 - 6), (0.0, y1 + 6), "07_ОСИ")
    L.dimh(x0, x1, y0, y0 - 14.0)
    L.dimv(y0, y1, x1, x1 + 28.0)
    L.dimh(bb.min.X, bb.max.X, bb.max.Y, y1 + 14.0, ф(bb.max.X - bb.min.X, 1))
    L.след([(x0 - 10.0, (bb.min.Y + bb.max.Y) / 2), (x1 + 10.0, (bb.min.Y + bb.max.Y) / 2)], "А", (0, 1))
    # --- А-А
    L.вид(330.0, 205.0)
    yc = (bb.min.Y + bb.max.Y) / 2
    g = сечение(ст2, "y", yc, "спереди")
    корпус_я = box(x0, bb.min.Z - w, x1, bb.max.Z).difference(g)
    L.hatch(корпус_я, 45.0, 1.0)
    L.geom(g)
    L.dimv(bb.min.Z, bb.max.Z, x1, x1 + 12.0, ф(bb.max.Z - bb.min.Z, 1))
    L.title(0.0, bb.max.Z + 14.0, "А-А")
    notes = ("Ящик деревянный из двух половин с разъёмом по оси, берёза ГОСТ 2695-83. Размеры полости - с усадкой %s %%." %
             ф(T.УСАДКА, 1),
             "Стержень Ст. 2 - ХТС, засыпка сверху, уплотнение вибрацией, съём через %d мин." % T.ЛИТЬЁ["смесь"]["съём_мин"],
             "Неуказанные размеры полости - по электронной модели стержня. Рабочие поверхности Ra 3,2, покрыть лаком.")
    return L.save("ВГ-2026_46_01-СЯ2_ящик_стержневой", "ВГ-2026.46.01-СЯ2", "Ящик стержневой",
                  "Оснастка - стержень Ст. 2 полости рукоятки корпуса ВГ-2026.46.01", notes, "Берёза ГОСТ 2695-83")


ЛИСТЫ = [сб, корпус_лист, стержень_лист, запор_лист, платик_лист, шайба_лист, литьё_лист, модель_лист, ящик_1_лист, ящик_2_лист]
#: листы прежнего узла - удалить вместе с растром и DWG
УСТАРЕЛИ = ["ВГ-2026_46_01-МП_плита_модельная", "ВГ-2026_46_01-СЯ_ящик_стержневой"]


def main():
    for имя in УСТАРЕЛИ:
        for p in (os.path.join(OUT, имя + ".dxf"), os.path.join(PNG.OUT, имя + ".png"),
                  os.path.join(ROOT, "CAD", "DWG", "узел", имя + ".dwg")):
            if os.path.exists(p):
                os.remove(p)
    for f in ЛИСТЫ:
        f()


if __name__ == "__main__":
    main()
