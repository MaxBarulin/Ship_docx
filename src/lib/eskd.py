# -*- coding: utf-8 -*-
"""Лист по ЕСКД для растровых чертежей: формат, рамка, основная надпись.

DXF-чертежи в `CAD/` рамку и штамп имеют, а PNG-чертежи в
`renders/горизонт_2026/чертежи/` были плакатами: заголовок сверху, подпись
справа. Этот модуль даёт им ту же форму, что и у DXF.

    from lib import eskd
    sh = eskd.Sheet("A1", mark="ВГ-2026.16.00 СБ",
                    name="Фундамент установки\\nочистки сточных вод",
                    material="Сталь 09Г2С ГОСТ 19281-2014",
                    mass=1247.0, scale="1:10")
    ax = sh.axes(20, 40, 400, 300)      # поле в миллиметрах листа
    ...
    sh.notes(["Сварка полуавтоматическая в среде CO2 по ГОСТ 14771-76.", ...])
    sh.save(path)

Координаты всюду в миллиметрах листа, начало — левый нижний угол.
Размеры рамки: слева 20 мм под подшивку, с остальных сторон по 5 мм
(ГОСТ 2.301-68). Основная надпись — ГОСТ 2.104-2006, форма 1, 185 x 55 мм.
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# ГОСТ 2.301-68, размеры в мм (по короткой стороне x длинной)
FORMATS = {
    "A4": (210.0, 297.0),
    "A3": (420.0, 297.0),
    "A2": (594.0, 420.0),
    "A1": (841.0, 594.0),
    "A0": (1189.0, 841.0),
    "A1x2": (1682.0, 594.0),
}

INK = "#16202f"
THIN = 0.5
THICK = 1.4

MARGIN_L = 20.0
MARGIN = 5.0
TB_W, TB_H = 185.0, 55.0
TB_H2A = 15.0                 # форма 2а для листов продолжения

ORG = "УЖЦ ОСК 2026 · «Волжский Горизонт»"
PEOPLE = [("Разраб.", "Барулин М."),
          ("Пров.", "Соколов А."),
          ("Т. контр.", "Игнатьев Г."),
          ("Н. контр.", "Рябова М."),
          ("Утв.", "Соколов А.")]


class Sheet(object):
    """Лист чертежа: рамка, основная надпись, поле для изображений."""

    def __init__(self, fmt="A1", mark="", name="", material=None, mass=None,
                 scale="1:1", sheet_no=1, sheets=1, lit="У", dpi=150,
                 people=None, org=ORG, form=1):
        if fmt not in FORMATS:
            raise ValueError("формат %s не по ГОСТ 2.301" % fmt)
        self.fmt = fmt
        self.W, self.H = FORMATS[fmt]
        self.dpi = dpi
        self.fig = plt.figure(figsize=(self.W / 25.4, self.H / 25.4), dpi=dpi)
        self.fig.patch.set_facecolor("white")
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, self.W)
        self.ax.set_ylim(0, self.H)
        self.ax.axis("off")
        self.ax.set_aspect("equal")
        self.form = form
        # form=0 — лист без основной надписи ЕСКД: её место занимает своя
        # шапка технологического документа по ГОСТ 3.1103
        self.tb_h = {1: TB_H, "2a": TB_H2A}.get(form, 0.0)
        self._frame()
        if form == 1:
            self._title_block(mark, name, material, mass, scale, sheet_no,
                              sheets, lit, people or PEOPLE, org)
        elif form == "2a":
            self._title_block_2a(mark, sheet_no)

    # --- геометрия листа ---------------------------------------------------

    def field(self):
        """Свободное поле листа: (x0, y0, x1, y1) в мм."""
        return (MARGIN_L, MARGIN + self.tb_h, self.W - MARGIN,
                self.H - MARGIN)

    def axes_frac(self, x, y, w, h, aspect=None):
        """Оси в долях свободного поля листа: [0..1] внутри рамки.

        Позволяет перенести готовый чертёж-плакат на лист по ГОСТ, не
        пересчитывая раскладку: доли те же, а поле сузилось на рамку и
        основную надпись.
        """
        fx0, fy0, fx1, fy1 = self.field()
        fw, fh = fx1 - fx0, fy1 - fy0
        return self.axes(fx0 + x * fw, fy0 + y * fh, w * fw, h * fh,
                         aspect=aspect)

    def text_frac(self, x, y, s, size=3.0, **kw):
        """Надпись в долях свободного поля."""
        fx0, fy0, fx1, fy1 = self.field()
        self._text(fx0 + x * (fx1 - fx0), fy0 + y * (fy1 - fy0), s,
                   size=size, **kw)

    def axes(self, x, y, w, h, aspect=None):
        """Оси внутри листа по координатам в миллиметрах."""
        a = self.fig.add_axes([x / self.W, y / self.H, w / self.W, h / self.H])
        a.axis("off")
        if aspect:
            a.set_aspect(aspect)
        return a

    # --- отрисовка ---------------------------------------------------------

    def _line(self, x0, y0, x1, y1, lw=THIN):
        self.ax.plot([x0, x1], [y0, y1], color=INK, lw=lw,
                     solid_capstyle="butt", zorder=5)

    def _text(self, x, y, s, size=2.5, ha="left", va="center", bold=False,
              color=INK, rot=0):
        # размер шрифта задаётся высотой прописной буквы в мм по ГОСТ 2.304
        self.ax.text(x, y, s, fontsize=size * 72.0 / 25.4 * 0.95, ha=ha,
                     va=va, color=color, rotation=rot, zorder=6,
                     fontweight="bold" if bold else "normal")

    def _frame(self):
        self.ax.add_patch(Rectangle((0, 0), self.W, self.H, fill=False,
                                    ec=INK, lw=THIN, zorder=4))
        self.ax.add_patch(Rectangle(
            (MARGIN_L, MARGIN), self.W - MARGIN_L - MARGIN,
            self.H - 2 * MARGIN, fill=False, ec=INK, lw=THICK, zorder=5))

    def _title_block(self, mark, name, material, mass, scale, no, sheets,
                     lit, people, org):
        x0 = self.W - MARGIN - TB_W
        y0 = MARGIN
        self.ax.add_patch(Rectangle((x0, y0), TB_W, TB_H, fill=False, ec=INK,
                                    lw=THICK, zorder=5))
        # --- левый блок 65 мм: изменения сверху, подписи снизу
        for k in range(1, 11):
            lw = THICK if k in (5, 8) else THIN
            self._line(x0, y0 + 5 * k, x0 + 65, y0 + 5 * k, lw)
        for dx in (7, 17, 40, 55):
            self._line(x0 + dx, y0, x0 + dx, y0 + 55)
        self._line(x0 + 65, y0, x0 + 65, y0 + 55, THICK)
        head = ("Изм.", "Лист", "№ докум.", "Подп.", "Дата")
        cols = (0, 7, 17, 40, 55, 65)
        for i, t in enumerate(head):
            self._text(x0 + (cols[i] + cols[i + 1]) / 2.0, y0 + 27.5, t,
                       size=2.0, ha="center")
        for i, (role, fam) in enumerate(people):
            yy = y0 + 22.5 - i * 5.0
            self._text(x0 + 1.0, yy, role, size=2.0)
            self._text(x0 + 18.0, yy, fam, size=2.0)
        # --- правый блок
        self._line(x0 + 65, y0 + 40, x0 + TB_W, y0 + 40, THICK)
        self._line(x0 + 65, y0 + 15, x0 + TB_W, y0 + 15, THICK)
        self._line(x0 + 65, y0 + 25, x0 + 135, y0 + 25)
        self._line(x0 + 135, y0 + 15, x0 + 135, y0 + 40)
        self._line(x0 + 135, y0 + 25, x0 + TB_W, y0 + 25)
        self._line(x0 + 135, y0 + 32, x0 + TB_W, y0 + 32)
        for dx in (150, 168):
            self._line(x0 + dx, y0 + 25, x0 + dx, y0 + 40)
        self._line(x0 + 160, y0 + 15, x0 + 160, y0 + 25)
        # обозначение документа
        self._text(x0 + 125.0, y0 + 47.5, mark, size=5.0, ha="right",
                   bold=True)
        # наименование изделия
        lines = [l for l in name.split("\n") if l]
        for i, l in enumerate(lines):
            self._text(x0 + 100.0, y0 + 34.0 - i * 4.2 + (len(lines) - 1) * 2.1,
                       l, size=3.5, ha="center")
        if material:
            self._text(x0 + 100.0, y0 + 20.0, material, size=2.5, ha="center")
        for i, t in enumerate(("Лит.", "Масса", "Масштаб")):
            xx = (x0 + 142.5, x0 + 159.0, x0 + 176.5)[i]
            self._text(xx, y0 + 36.0, t, size=2.0, ha="center")
        self._text(x0 + 142.5, y0 + 28.5, lit, size=3.5, ha="center")
        self._text(x0 + 159.0, y0 + 28.5,
                   "—" if mass is None else "%.0f" % mass, size=3.5,
                   ha="center")
        self._text(x0 + 176.5, y0 + 28.5, scale, size=3.5, ha="center")
        self._text(x0 + 147.5, y0 + 20.0, "Лист %d" % no, size=2.5,
                   ha="center")
        self._text(x0 + 172.5, y0 + 20.0, "Листов %d" % sheets, size=2.5,
                   ha="center")
        self._text(x0 + 100.0, y0 + 7.5, org, size=3.0, ha="center")

    def _title_block_2a(self, mark, no):
        """Основная надпись формы 2а: листы продолжения (ГОСТ 2.104)."""
        x0 = self.W - MARGIN - TB_W
        y0 = MARGIN
        self.ax.add_patch(Rectangle((x0, y0), TB_W, TB_H2A, fill=False,
                                    ec=INK, lw=THICK, zorder=5))
        for k in (5, 10):
            self._line(x0, y0 + k, x0 + 65, y0 + k)
        for dx in (7, 17, 40, 55):
            self._line(x0 + dx, y0, x0 + dx, y0 + TB_H2A)
        self._line(x0 + 65, y0, x0 + 65, y0 + TB_H2A, THICK)
        self._line(x0 + 165, y0, x0 + 165, y0 + TB_H2A)
        head = ("Изм.", "Лист", "№ докум.", "Подп.", "Дата")
        cols = (0, 7, 17, 40, 55, 65)
        for i, t in enumerate(head):
            self._text(x0 + (cols[i] + cols[i + 1]) / 2.0, y0 + 2.5, t,
                       size=2.0, ha="center")
        self._text(x0 + 115.0, y0 + 7.5, mark, size=5.0, ha="center",
                   bold=True)
        self._text(x0 + 175.0, y0 + 10.5, "Лист", size=2.0, ha="center")
        self._text(x0 + 175.0, y0 + 4.5, str(no), size=3.5, ha="center")

    # --- дополнительные блоки ---------------------------------------------

    def notes(self, items, width=170.0, size=2.5):
        """Технические требования над основной надписью (ГОСТ 2.316)."""
        import textwrap
        x = self.W - MARGIN - TB_W
        y = MARGIN + self.tb_h + 4.0
        wrapped = []
        for i, t in enumerate(items):
            first = "%d. " % (i + 1)
            chunks = textwrap.wrap(t, int(width / (size * 0.62)))
            for j, ch in enumerate(chunks):
                wrapped.append((first if j == 0 else "   ") + ch)
        for k, line in enumerate(reversed(wrapped)):
            self._text(x, y + k * (size * 1.55), line, size=size)
        self._text(x, y + len(wrapped) * (size * 1.55) + 1.5,
                   "Технические требования", size=3.0, bold=True)
        return y + (len(wrapped) + 1) * (size * 1.55) + 3.0

    def stamp(self, text, size=2.5):
        """Надпись у левого края под подшивку (графа 27-30 повёрнутая)."""
        self._text(10.0, self.H / 2.0, text, size=size, ha="center", rot=90,
                   color="#7b8798")

    def save(self, path, dxf=None, title=""):
        """Растр листа; с `dxf` — тот же лист и в DXF (fig2dxf, мм = мм листа)."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.fig.savefig(path, dpi=self.dpi, facecolor="white")
        if dxf:
            from . import fig2dxf
            fig2dxf.save_dxf(self.fig, dxf, title=title or os.path.splitext(os.path.basename(path))[0])
        plt.close(self.fig)
        return path


def check(path, fmt):
    """Совпадает ли растр с форматом по ГОСТ 2.301 и пропорциям листа."""
    from PIL import Image
    W, H = FORMATS[fmt]
    with Image.open(path) as im:
        w, h = im.size
    r = (w / float(h)) / (W / H)
    return abs(r - 1.0) < 0.01, (w, h), round(r, 4)
