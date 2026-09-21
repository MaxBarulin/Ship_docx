# -*- coding: utf-8 -*-
"""Спецификация по ГОСТ 2.106-2019: форма 1 и листы продолжения.

Таблица спецификации на листе А4: графы «Формат», «Зона», «Поз.»,
«Обозначение», «Наименование», «Кол.», «Примечание». Разделы идут в порядке
ГОСТ: Документация, Комплексы, Сборочные единицы, Детали, Стандартные
изделия, Прочие изделия, Материалы, Комплекты.

Модуль только рисует; что именно писать — в `gorizont_awts.specification()`.
"""

from . import eskd

# ширины граф формы 1 по ГОСТ 2.106, мм; сумма 185 — ширина поля листа А4
COLS = [("Формат", 6.0), ("Зона", 6.0), ("Поз.", 8.0),
        ("Обозначение", 70.0), ("Наименование", 63.0), ("Кол.", 10.0),
        ("Примечание", 22.0)]
TABLE_W = sum(w for _, w in COLS)
VERT = (0, 1)                 # узкие графы подписываются поперёк листа
ROW_H = 8.0
HEAD_H = 15.0
NAME_X = 6.0 + 6.0 + 8.0 + 70.0        # левый край графы «Наименование»


def _grid(sh, x, y_top, n_rows, head=True):
    """Сетка таблицы; возвращает y верхней строки данных."""
    y = y_top
    bottom = y - (HEAD_H if head else 0.0) - n_rows * ROW_H
    cx = x
    for i, (name, w) in enumerate(COLS):
        sh._line(cx, y, cx, bottom, eskd.THIN)
        if head:
            if i in VERT:
                sh._text(cx + w / 2.0, y - HEAD_H / 2.0, name, size=2.2,
                         ha="center", rot=90)
            else:
                sh._text(cx + w / 2.0, y - HEAD_H / 2.0, name, size=2.5,
                         ha="center")
        cx += w
    sh._line(cx, y, cx, bottom, eskd.THIN)
    sh._line(x, y, x + TABLE_W, y, eskd.THICK)
    if head:
        y -= HEAD_H
        sh._line(x, y, x + TABLE_W, y, eskd.THICK)
    for k in range(1, n_rows + 1):
        sh._line(x, y - k * ROW_H, x + TABLE_W, y - k * ROW_H, eskd.THIN)
    return y


def _row(sh, x, y, cells, center=(0, 1, 2, 5)):
    cx = x
    for i, (_, w) in enumerate(COLS):
        v = cells[i] if i < len(cells) else ""
        if v:
            if i in center:
                sh._text(cx + w / 2.0, y - ROW_H / 2.0, str(v), size=2.5,
                         ha="center")
            else:
                sh._text(cx + 1.5, y - ROW_H / 2.0, str(v), size=2.5)
        cx += w


def draw(sections, mark, name, sheets_data, path_fmt, rows_per_sheet=27,
         rows_next=32, org=eskd.ORG):
    """Разложить разделы по листам А4 и сохранить.

    `sections` — [(заголовок раздела, [строки])]; строка — словарь с ключами
    fmt, zone, pos, mark, name, qty, note.
    """
    flat = []
    for title, rows in sections:
        if not rows:
            continue
        flat.append(("раздел", title))
        for r in rows:
            flat.append(("строка", r))
        flat.append(("пусто", None))
    pages, rest = [], list(flat)
    while rest or not pages:
        n = rows_per_sheet if not pages else rows_next
        pages.append(rest[:n])
        rest = rest[n:]
    made = []
    for i, page in enumerate(pages):
        n = rows_per_sheet if i == 0 else rows_next
        sh = eskd.Sheet("A4", mark=mark, name=name, scale="—",
                        sheet_no=i + 1, sheets=len(pages), org=org,
                        form=1 if i == 0 else "2a", **sheets_data)
        x = eskd.MARGIN_L
        y = _grid(sh, x, sh.H - eskd.MARGIN, n, head=(i == 0))
        for k, (kind, val) in enumerate(page):
            yy = y - k * ROW_H
            if kind == "раздел":
                sh._text(x + NAME_X + 31.5, yy - ROW_H / 2.0, val, size=3.0,
                         ha="center", bold=True)
                sh._line(x + NAME_X + 8.0, yy - ROW_H + 1.6,
                         x + NAME_X + 55.0, yy - ROW_H + 1.6, eskd.THIN)
            elif kind == "строка":
                _row(sh, x, yy,
                     [val.get("fmt", ""), val.get("zone", ""),
                      val.get("pos", ""), val.get("mark", ""),
                      val.get("name", ""), val.get("qty", ""),
                      val.get("note", "")])
        made.append(sh.save(path_fmt % (i + 1)))
    return made
