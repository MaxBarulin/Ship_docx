# -*- coding: utf-8 -*-
"""Формы технологических документов по ЕСКТД.

Основная надпись у технологических документов своя - ГОСТ 3.1103, а не
2.104 - блок сверху листа с полями «Дубл.», «Взам.», «Подл.», разработчиками,
обозначением документа, наименованием изделия и детали, материалом и массой.

Поддержаны формы, которые нужны шагу 1:
  МК  - маршрутная карта, ГОСТ 3.1118-82 форма 1;
  ОК  - операционная карта, ГОСТ 3.1404-86 форма 3;
  КЭ  - карта эскизов, ГОСТ 3.1105-84 форма 7;
  ККИ - карта контроля, ГОСТ 3.1502-85 форма 2.
"""

from . import eskd

HEAD_H = 42.0            # высота блока основной надписи сверху листа
SIDE_W = 7.0             # левая колонка «Дубл. / Взам. / Подл.»


class TechSheet(object):
    """Лист технологического документа А4 с шапкой по ГОСТ 3.1103."""

    def __init__(self, form, doc_mark, detail, sheet_no=1, sheets=1,
                 fmt="A4", dpi=150, org=eskd.ORG):
        self.sh = eskd.Sheet(fmt, form=0, dpi=dpi)
        self.form = form
        self.W, self.H = self.sh.W, self.sh.H
        self._head(form, doc_mark, detail, sheet_no, sheets, org)

    # --- служебное ---------------------------------------------------------

    def line(self, x0, y0, x1, y1, lw=eskd.THIN):
        self.sh._line(x0, y0, x1, y1, lw)

    def text(self, x, y, s, size=2.5, **kw):
        self.sh._text(x, y, s, size=size, **kw)

    def save(self, path):
        return self.sh.save(path)

    # --- шапка -------------------------------------------------------------

    def _head(self, form, mark, d, no, sheets, org):
        x0 = eskd.MARGIN_L
        x1 = self.W - eskd.MARGIN
        yt = self.H - eskd.MARGIN
        yb = yt - HEAD_H
        self.line(x0, yt, x1, yt, eskd.THICK)
        self.line(x0, yb, x1, yb, eskd.THICK)
        self.line(x0, yt, x0, yb, eskd.THICK)
        self.line(x1, yt, x1, yb, eskd.THICK)
        # левая колонка служебных полей
        self.line(x0 + SIDE_W, yt, x0 + SIDE_W, yb)
        for k, t in enumerate(("Дубл.", "Взам.", "Подл.")):
            yy = yt - (k + 1) * HEAD_H / 3.0
            if k < 2:
                self.line(x0, yy, x0 + SIDE_W, yy)
            self.text(x0 + SIDE_W / 2.0, yy + HEAD_H / 6.0, t, size=1.8,
                      ha="center", rot=90)
        xa = x0 + SIDE_W
        # строка разработчиков
        y1 = yt - 12.0
        self.line(xa, y1, x1, y1)
        cols = eskd.PEOPLE
        w = (x1 - xa) / 5.0
        for i, (role, fam) in enumerate(cols):
            cx = xa + i * w
            if i:
                self.line(cx, yt, cx, y1)
            self.text(cx + 1.2, yt - 4.0, role, size=1.9)
            self.text(cx + 1.2, yt - 9.0, fam, size=2.2)
        # организация и обозначение документа
        y2 = y1 - 12.0
        self.line(xa, y2, x1, y2)
        self.line(xa + 78.0, y1, xa + 78.0, y2)
        self.text(xa + 2.0, y1 - 6.0, org, size=2.4)
        self.text(xa + 80.0, y1 - 6.0, mark, size=3.2, bold=True)
        # изделие, деталь, материал
        y3 = y2 - 10.0
        self.line(xa, y3, x1, y3)
        self.line(xa + 78.0, y2, xa + 78.0, yb)
        self.text(xa + 2.0, y2 - 5.0, d["assembly"] + "  " + d["assembly_name"],
                  size=2.2)
        self.text(xa + 80.0, y2 - 5.0,
                  "%s  %s" % (d["mark"], d["name"]), size=2.6, bold=True)
        self.text(xa + 2.0, y3 - 5.0,
                  "Материал  %s   Профиль  %s" % (d["material"], d["profile"]),
                  size=2.2)
        self.text(xa + 80.0, y3 - 5.0,
                  "Масса детали  %.1f кг   Лист %d из %d"
                  % (d["mass_kg"], no, sheets), size=2.2)
        # наименование формы - под шапкой справа
        self.text(x1 - 3.0, yb - 4.5, form, size=2.4, ha="right",
                  color="#56627a")
        self.top = yb - 9.0
        return self.top

    # --- таблицы -----------------------------------------------------------

    def table(self, cols, rows, y=None, row_h=6.0, head_h=8.0, size=2.2,
              head_size=2.2, center=(), wrap=True):
        """Таблица во всю ширину поля. `cols` - [(заголовок, ширина мм)].

        Длинный текст переносится по ширине графы, а строка растёт по числу
        строк - иначе средства контроля вылезали в соседнюю графу.
        """
        import textwrap
        x0 = eskd.MARGIN_L
        y = self.top if y is None else y
        total = sum(w for _, w in cols)
        k = (self.W - eskd.MARGIN - x0) / total
        # перенос по ширине графы: ширина знака ≈ 0.55 от высоты шрифта
        cells, heights = [], []
        for r in rows:
            wrapped, n = [], 1
            for j_, (_, w) in enumerate(cols):
                v = str(r[j_]) if j_ < len(r) and r[j_] else ""
                lim = max(4, int((w * k - 2.4) / (size * 0.55)))
                lines = textwrap.wrap(v, lim) if (wrap and v) else ([v] if v else [])
                wrapped.append(lines)
                n = max(n, len(lines))
            cells.append(wrapped)
            heights.append(max(row_h, n * size * 1.5 + 2.0))
        h_all = sum(heights)
        self.line(x0, y, x0 + total * k, y, eskd.THICK)
        self.line(x0, y - head_h, x0 + total * k, y - head_h, eskd.THICK)
        cx = x0
        for name, w in cols:
            self.line(cx, y, cx, y - head_h - h_all)
            self.text(cx + w * k / 2.0, y - head_h / 2.0, name,
                      size=head_size, ha="center")
            cx += w * k
        self.line(cx, y, cx, y - head_h - h_all)
        yy = y - head_h
        for i_, wrapped in enumerate(cells):
            hr = heights[i_]
            self.line(x0, yy - hr, x0 + total * k, yy - hr)
            cx = x0
            for j_, (_, w) in enumerate(cols):
                lines = wrapped[j_]
                for m, ln in enumerate(lines):
                    ty = yy - hr / 2.0 + (len(lines) - 1 - 2 * m) * size * 0.75
                    if j_ in center:
                        self.text(cx + w * k / 2.0, ty, ln, size=size,
                                  ha="center")
                    else:
                        self.text(cx + 1.2, ty, ln, size=size)
                cx += w * k
            yy -= hr
        self.top = yy - 4.0
        return self.top

    def block(self, title, lines, y=None, size=2.3, gap=4.4):
        """Текстовый блок - переходы, базирование, примечания. Строка длиннее поля переносится
        по словам с отступом продолжения - иначе примечание МК сборки уходило за рамку."""
        import textwrap
        x0 = eskd.MARGIN_L
        y = self.top if y is None else y
        self.text(x0, y - 3.0, title, size=3.0, bold=True)
        yy = y - 8.0
        lim = max(20, int((self.W - eskd.MARGIN - x0 - 4.0) / (size * 0.55)))
        for t in lines:
            for m, ln in enumerate(textwrap.wrap(t, lim) or [""]):
                self.text(x0 + 2.0 + (3.0 if m else 0.0), yy, ln, size=size)
                yy -= gap
        self.top = yy - 2.0
        return self.top
