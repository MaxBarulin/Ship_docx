# -*- coding: utf-8 -*-
"""Экспорт фигуры matplotlib в DXF — расчётные графики и таблицы для CAD.

Зачем: теория корабля рисуется matplotlib (кривые элементов, строевая,
остойчивость, прочность, таблица ординат), а конструктору и технологу нужны
те же листы в DWG. Вместо второго рисовальщика — обход готовой фигуры после
отрисовки: линии, заливки, рамки осей, деления, сетка, тексты, легенды и
таблицы переносятся в DXF в миллиметрах листа (1 мм = 1 мм), положение
текста берётся из фактических габаритов надписи на канве, поэтому DXF
совпадает с PNG. Цвета — истинные (true color), слои по типу примитива.

    from lib import fig2dxf
    fig2dxf.save_dxf(fig, "CAD/расчёты/02_кривые_элементов.dxf", title="Кривые элементов")

Дальше DXF → DWG делает `scripts/чертежи_dwg.py` (AutoCAD Core Console).
"""
import os, math
import numpy as np
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA
from ezdxf import colors as _col
import matplotlib.colors as mc
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.collections import LineCollection, PolyCollection, PathCollection

LAYERS = [("00_РАМКА", 7), ("01_ЛИНИИ", 7), ("02_ОСИ", 8), ("03_СЕТКА", 9),
          ("04_ТЕКСТ", 7), ("05_ЗАЛИВКА", 8), ("06_ТАБЛИЦА", 7), ("07_ЛЕГЕНДА", 8)]
PT = 25.4 / 72.0               # пункт → мм
КАП = 0.72                     # высота прописной ≈ 0,72 кегля
LTYPE = {"--": "DASHED", "dashed": "DASHED", ":": "DOT", "dotted": "DOT", "-.": "DASHDOT", "dashdot": "DASHDOT"}


def _rgb(c, alpha_min=0.0):
    try:
        r, g, b, a = mc.to_rgba(c)
    except (ValueError, TypeError):
        return None
    if a < alpha_min:
        return None
    return _col.rgb2int((int(r * 255), int(g * 255), int(b * 255)))


class _Экспорт:
    def __init__(self, fig, path, title, note):
        self.fig = fig
        fig.canvas.draw()
        self.r = fig.canvas.get_renderer()
        self.dpi = fig.dpi
        self.W = fig.get_figwidth() * 25.4
        self.H = fig.get_figheight() * 25.4
        self.doc = ezdxf.new("R2013", setup=True)
        self.doc.header["$INSUNITS"] = 4
        self.doc.header["$MEASUREMENT"] = 1
        for name, aci in LAYERS:
            self.doc.layers.add(name, color=aci)
        # кириллица в AutoCAD: тот же стиль, что на листах ОР (чертежи_dxf.newdoc)
        if "ГОСТ" not in self.doc.styles:
            self.doc.styles.add("ГОСТ", font="ISOCPEUR.TTF")
        self.msp = self.doc.modelspace()
        self.path, self.title, self.note = path, title, note

    # --- координаты --------------------------------------------------------------
    def mm(self, xy):
        xy = np.asarray(xy, dtype=float)
        return xy / self.dpi * 25.4

    def _attrs(self, layer, color=None, ls=None, lw=None):
        d = {"layer": layer}
        tc = _rgb(color) if color is not None else None
        if tc is not None:
            d["true_color"] = tc
        lt = LTYPE.get(ls) if ls else None
        if lt and lt in self.doc.linetypes:
            d["linetype"] = lt
        if lw:
            d["lineweight"] = int(min(211, max(0, round(lw * PT * 100))))   # сотые мм
        return d

    def polyline(self, pts, layer, color=None, ls=None, lw=None, closed=False):
        pts = np.asarray(pts, dtype=float)
        if len(pts) < 2:
            return
        # разрывы по NaN — отдельные полилинии
        ok = ~np.isnan(pts).any(axis=1)
        start = 0
        for i in range(len(pts) + 1):
            if i == len(pts) or not ok[i]:
                seg = pts[start:i]
                if len(seg) >= 2:
                    self.msp.add_lwpolyline([tuple(p) for p in self.mm(seg)], close=closed,
                                            dxfattribs=self._attrs(layer, color, ls, lw))
                start = i + 1

    def hatch(self, pts, color, layer="05_ЗАЛИВКА"):
        pts = np.asarray(pts, dtype=float)
        if len(pts) < 3 or np.isnan(pts).any():
            return
        tc = _rgb(color, alpha_min=0.15)
        if tc is None:
            return
        h = self.msp.add_hatch(dxfattribs={"layer": layer, "true_color": tc})
        h.paths.add_polyline_path([tuple(p) for p in self.mm(pts)], is_closed=True)

    # --- примитивы --------------------------------------------------------------
    def text(self, t, layer="04_ТЕКСТ"):
        if t is None or not t.get_visible():
            return
        s = t.get_text()
        if not s or not s.strip():
            return
        try:
            bb = t.get_window_extent(self.r)
        except Exception:
            return
        cx, cy = self.mm(((bb.x0 + bb.x1) / 2.0, (bb.y0 + bb.y1) / 2.0))
        h = t.get_fontsize() * PT * КАП
        attrs = self._attrs(layer, t.get_color())
        attrs["style"] = "ГОСТ"
        rot = t.get_rotation()
        if "\n" in s:
            attrs["char_height"] = h
            attrs["attachment_point"] = 5
            attrs["rotation"] = rot
            m = self.msp.add_mtext(s, dxfattribs=attrs)
            m.dxf.insert = (cx, cy)
        else:
            attrs["height"] = h
            attrs["rotation"] = rot
            self.msp.add_text(s, dxfattribs=attrs).set_placement((cx, cy), align=TA.MIDDLE_CENTER)

    def line2d(self, ln, layer="01_ЛИНИИ"):
        if not ln.get_visible():
            return
        xy = ln.get_xydata()
        if xy is None or len(xy) == 0:
            return
        disp = ln.get_transform().transform(np.asarray(xy, dtype=float))
        ls = ln.get_linestyle()
        if ls not in ("None", "none", None, "") and ln.get_linewidth() > 0:
            self.polyline(disp, layer, ln.get_color(), ls, ln.get_linewidth())
        mk = ln.get_marker()
        if mk not in ("None", "none", None, "", " "):
            rad = ln.get_markersize() * PT / 2.0
            if mk in ("|", "_", 2, 3, "TICKDOWN", "TICKUP", "TICKLEFT", "TICKRIGHT", 0, 1):
                return          # деления осей рисуются отдельно
            for p in self.mm(disp):
                if not np.isnan(p).any():
                    self.msp.add_circle(tuple(p), max(rad, 0.3), dxfattribs=self._attrs(layer, ln.get_markerfacecolor()))

    def patch(self, p, layer="01_ЛИНИИ"):
        if not p.get_visible():
            return
        try:
            tp = p.get_path().transformed(p.get_transform())
        except Exception:
            return
        ec = p.get_edgecolor()
        fc = p.get_facecolor()
        filled = p.get_fill() and _rgb(fc, alpha_min=0.15) is not None
        for poly in tp.to_polygons(closed_only=False):
            if len(poly) < 2:
                continue
            if filled:
                self.hatch(poly, fc)
            if p.get_linewidth() > 0 and _rgb(ec, alpha_min=0.15) is not None:
                self.polyline(poly, layer, ec, p.get_linestyle(), p.get_linewidth(), closed=True)

    def collection(self, c, layer="01_ЛИНИИ"):
        if not c.get_visible():
            return
        tr = c.get_transform()
        if isinstance(c, LineCollection):
            cols = c.get_colors()
            for i, seg in enumerate(c.get_segments()):
                col = cols[i % len(cols)] if len(cols) else "k"
                self.polyline(tr.transform(np.asarray(seg, dtype=float)), layer, col, None, c.get_linewidths()[0] if len(c.get_linewidths()) else None)
        elif isinstance(c, PolyCollection):
            fcs = c.get_facecolors(); ecs = c.get_edgecolors()
            for i, path in enumerate(c.get_paths()):
                for poly in path.transformed(tr).to_polygons(closed_only=False):
                    if len(fcs):
                        self.hatch(poly, fcs[i % len(fcs)])
                    if len(ecs) and _rgb(ecs[i % len(ecs)], 0.15) is not None:
                        self.polyline(poly, layer, ecs[i % len(ecs)], None, None, closed=True)
        elif isinstance(c, PathCollection):
            offs = c.get_offset_transform().transform(c.get_offsets())
            sizes = c.get_sizes()
            fcs = c.get_facecolors()
            for i, o in enumerate(self.mm(offs)):
                rad = math.sqrt(sizes[i % len(sizes)] if len(sizes) else 20.0) * PT / 2.0
                self.msp.add_circle(tuple(o), max(rad, 0.3), dxfattribs=self._attrs(layer, fcs[i % len(fcs)] if len(fcs) else "k"))

    # --- оси ---------------------------------------------------------------------
    def axes(self, ax):
        if not ax.get_visible():
            return
        for ln in ax.xaxis.get_gridlines() + ax.yaxis.get_gridlines():
            if ln.get_visible():
                self.line2d(ln, "03_СЕТКА")
        if ax.axison:
            for sp in ax.spines.values():
                if sp.get_visible():
                    self.patch(sp, "02_ОСИ")
            bb = ax.get_window_extent(self.r)
            for axis, гор in ((ax.xaxis, True), (ax.yaxis, False)):
                for tick in axis.get_major_ticks():
                    if not tick.get_visible():
                        continue
                    loc = tick.get_loc()
                    size = tick.get_tick_padding() and tick.tick1line.get_markersize() * PT or 1.2
                    if гор:
                        x = ax.transData.transform((loc, 0.0))[0]
                        if bb.x0 - 1 <= x <= bb.x1 + 1 and tick.tick1line.get_visible():
                            p = self.mm((x, bb.y0))
                            self.msp.add_line(tuple(p), (p[0], p[1] - size), dxfattribs=self._attrs("02_ОСИ"))
                    else:
                        y = ax.transData.transform((0.0, loc))[1]
                        if bb.y0 - 1 <= y <= bb.y1 + 1 and tick.tick1line.get_visible():
                            p = self.mm((bb.x0, y))
                            self.msp.add_line(tuple(p), (p[0] - size, p[1]), dxfattribs=self._attrs("02_ОСИ"))
                    if tick.label1.get_visible():
                        self.text(tick.label1, "02_ОСИ")
            self.text(ax.xaxis.label, "02_ОСИ")
            self.text(ax.yaxis.label, "02_ОСИ")
        for t in (ax.title, getattr(ax, "_left_title", None), getattr(ax, "_right_title", None)):
            self.text(t)
        for ln in ax.get_lines():
            self.line2d(ln)
        for p in ax.patches:
            self.patch(p)
        for c in ax.collections:
            self.collection(c)
        for t in ax.texts:
            self.text(t)
            arr = getattr(t, "arrow_patch", None)
            if arr is not None and arr.get_visible():
                self.patch(arr)
        for tb in ax.tables:
            for cell in tb.get_celld().values():
                try:
                    cb = cell.get_window_extent(self.r)
                except Exception:
                    continue
                pts = [(cb.x0, cb.y0), (cb.x1, cb.y0), (cb.x1, cb.y1), (cb.x0, cb.y1)]
                fc = cell.get_facecolor()
                if _rgb(fc, 0.15) is not None and mc.to_hex(fc) not in ("#ffffff", "#fbfcfd"):
                    self.hatch(pts, fc, "06_ТАБЛИЦА")
                self.polyline(pts, "06_ТАБЛИЦА", cell.get_edgecolor(), None, cell.get_linewidth(), closed=True)
                self.text(cell.get_text(), "06_ТАБЛИЦА")
        leg = ax.get_legend()
        if leg is not None and leg.get_visible():
            fr = leg.get_frame()
            if fr is not None and fr.get_visible():
                self.patch(fr, "07_ЛЕГЕНДА")
            handles = getattr(leg, "legend_handles", None) or getattr(leg, "legendHandles", [])
            for h in handles:
                if isinstance(h, Line2D):
                    self.line2d(h, "07_ЛЕГЕНДА")
                elif isinstance(h, Patch):
                    self.patch(h, "07_ЛЕГЕНДА")
            for t in leg.get_texts():
                self.text(t, "07_ЛЕГЕНДА")

    # --- лист ---------------------------------------------------------------------
    def run(self):
        self.msp.add_lwpolyline([(0, 0), (self.W, 0), (self.W, self.H), (0, self.H)], close=True,
                                dxfattribs={"layer": "00_РАМКА"})
        for ax in self.fig.axes:
            self.axes(ax)
        for t in self.fig.texts:
            self.text(t)
        st = getattr(self.fig, "_suptitle", None)
        if st is not None:
            self.text(st)
        подпись = "«Волжский Горизонт» · %s · лист %.0f × %.0f мм, 1 мм = 1 мм листа; величины по осям — как на графике" % (
            self.title, self.W, self.H)
        if self.note:
            подпись += " · " + self.note
        self.msp.add_text(подпись, dxfattribs={"layer": "00_РАМКА", "height": 2.5, "style": "ГОСТ"}).set_placement((2.0, -4.5), align=TA.LEFT)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.doc.saveas(self.path)
        return self.path


def save_dxf(fig, path, title="", note=""):
    """Записать фигуру matplotlib в DXF (мм листа). Вызывать до plt.close(fig)."""
    return _Экспорт(fig, path, title, note).run()
