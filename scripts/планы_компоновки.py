# -*- coding: utf-8 -*-
"""Планы палуб из компоновки - стадия проектирования, без Blender.

    python scripts/планы_компоновки.py

Пять листов - второе дно (цистерны), трюм, главная, средняя, солнечная. Обвод берётся из
`gorizont_lines` и `gorizont_super`, зоны и каюты - из `gorizont_ga`, мебель - из
`gorizont_public`, слоты модулей - из `gorizont_modules`. Всё, что на листе, посчитано,
ни одна линия не нарисована руками. Поэтому план - это и есть задание на модель.

Вид - как чертёж общего расположения: шрифт по ГОСТ 2.304 (`plain.чертёж`), чёрные линии
разной толщины, мебель контуром, заливок и цветной легенды нет, заголовка на картинке нет -
название даёт подпись рисунка в записке. Помещение подписано внутри, если по измеренному
тексту там есть свободное место, иначе выноской над или под планом. Выноски раздвигаются
по длине так, чтобы подписи не налезали друг на друга, длинные переносятся по словам.

Ширина рисунка 8 дюймов, кегль 8,5 - при вставке на ширину текста А4 (165 мм) это 6,9 pt.
Все пять планов в одном масштабе и с одним полем по длине - на листе проекта они стоят
столбцом, шпангоут под шпангоутом.
"""
import os, sys, re
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon

from lib import plain as P
from lib import gorizont as G, gorizont_lines as L, gorizont_super as SU
from lib import gorizont_ga as GA, gorizont_public as PB, gorizont_wheel as W
from lib import gorizont_modules as MOD

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "планы")
os.makedirs(OUT, exist_ok=True)

ШИРИНА = 8.0                          # дюймов
КЕГЛЬ = 8.5                           # pt
ИНТЕРВАЛ = 1.1                        # межстрочный множитель подписей
X0, X1 = -5.0, G.LOA + 4.0            # поле по длине, м (аппарель торчит за транец на 4 м)
ПТ = 72.0 * ШИРИНА / (X1 - X0)        # pt на метр
КОНТУР, ЯРУС, СТЕНА, ПЕРЕБОРКА, ТОНКАЯ, МЕБЕЛЬ = 1.1, 0.8, 0.6, 1.3, 0.45, 0.3
СЕРЫЙ = "#3a3a3a"                     # мебель и оборудование
ЗАЗОР = 0.45                          # м, от подписи до линий


def м(pt):
    return pt / ПТ


#: в шрифте GOST Common часть знаков Latin-1 стоит не на своих местах: «·» рисуется как «¾»,
#: «°» как «¹», «Ø» как «Ý», кавычки-ёлочки как «¼½». Точка умножения в единицах - U+22C5
_ЗАМЕНА = {"·": "⋅", "°": " град", "Ø": "⌀", "«": "\"", "»": "\""}


def гост(s):
    for a, b in _ЗАМЕНА.items():
        s = s.replace(a, b)
    return s


# ---------------------------------------------------------------- измерение текста
_ИЗМ = {}


def размер(s, fs=КЕГЛЬ, пт=None):
    """(ширина, высота) текста в метрах поля - по отрисовке тем же шрифтом. пт - масштаб
    рисунка в pt на метр, по умолчанию масштаб планов."""
    пт = пт or ПТ
    k = (s, fs, пт)
    if k not in _ИЗМ:
        if "fig" not in _ИЗМ:
            _ИЗМ["fig"] = plt.figure(figsize=(ШИРИНА, 2.0), dpi=P.DPI)
        fig = _ИЗМ["fig"]
        t = fig.text(0, 0, s, fontsize=fs, linespacing=ИНТЕРВАЛ)
        bb = t.get_window_extent(fig.canvas.get_renderer())
        t.remove()
        f = 72.0 / fig.dpi / пт
        _ИЗМ[k] = (bb.width * f, bb.height * f)
    return _ИЗМ[k]


_ЧИСЛО = re.compile(r"^[\d,.'×]+$")


def _единицы(s):
    """Слова, которые переносятся только вместе: тире и «×» не начинают строку, короткие
    слова и числа не остаются в конце строки («на 4 автомобиля», «9,0 × 3,6 м»)."""
    т = s.split()
    клей = []
    for i, w in enumerate(т[:-1]):
        nxt = т[i + 1]
        клей.append(nxt in ("-", "×") or w == "×" or
                    (w != "-" and (len(w) <= 2 or _ЧИСЛО.match(w)) and not w.endswith(",")))
    out, cur = [], т[0] if т else ""
    for i, w in enumerate(т[1:]):
        if клей[i]:
            cur += " " + w
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


def перенос(s, ширина, fs=КЕГЛЬ, пт=None):
    строки, cur = [], ""
    for u in _единицы(s):
        c = (cur + " " + u) if cur else u
        if cur and размер(c, fs, пт)[0] > ширина:
            строки.append(cur)
            cur = u
        else:
            cur = c
    if cur:
        строки.append(cur)
    return строки


def варианты(s, fs=КЕГЛЬ, до=6, пт=None):
    """{число строк: (строки, ширина, высота)} - самый узкий перенос на каждое число строк."""
    s = гост(s)
    ед = _единицы(s)
    w = max(размер(u, fs, пт)[0] for u in ед)
    полная = размер(" ".join(ед), fs, пт)[0]
    шаг = 1.0 / (пт or ПТ)              # 1 pt
    out = {}
    while True:
        стр = перенос(s, w, fs, пт)
        n = len(стр)
        if n <= до and n not in out:
            out[n] = (стр, max(размер(x, fs, пт)[0] for x in стр), размер("\n".join(стр), fs, пт)[1])
        if n == 1 or w > полная:
            break
        w += шаг
    return out


def _пересек(a, b, з=0.0):
    return a[0] < b[2] + з and b[0] < a[2] + з and a[1] < b[3] + з and b[1] < a[3] + з


def _раздвинуть(c, w, lo, hi, зазор):
    """Центры подписей в ряд без налезаний, как можно ближе к желаемым (изотоническая
    регрессия, PAVA). None - если не помещаются в [lo, hi]."""
    n = len(c)
    s = [0.0] * n
    for i in range(1, n):
        s[i] = s[i - 1] + (w[i - 1] + w[i]) / 2.0 + зазор
    блоки = []
    for v in (c[i] - s[i] for i in range(n)):
        блоки.append([v, 1])
        while len(блоки) > 1 and блоки[-2][0] / блоки[-2][1] > блоки[-1][0] / блоки[-1][1]:
            a = блоки.pop()
            блоки[-1][0] += a[0]
            блоки[-1][1] += a[1]
    q = []
    for sm, k in блоки:
        q += [sm / k] * k
    lo_, hi_ = lo + w[0] / 2.0, hi - w[-1] / 2.0 - s[-1]
    if lo_ > hi_:
        return None
    return [min(max(v, lo_), hi_) + s[i] for i, v in enumerate(q)]


# ---------------------------------------------------------------- обводы
def борт(x):
    """Полуширота корпуса по палубе - с нишей колеса (ниша идёт до киля)."""
    return min(L.side_half(x), W.niche_half(x))


def _интерп(точки):
    xs = np.array([p[0] for p in точки])
    ys = np.array([p[1] for p in точки])

    def f(x):
        return 0.0 if x < xs[0] - 1e-6 or x > xs[-1] + 1e-6 else float(np.interp(x, xs, ys))
    return f, (float(xs[0]), float(xs[-1]))


def обвод_яруса(палуба):
    """Верхняя половина обвода стен яруса [(x, y)], по `gorizont_super`."""
    if палуба == "солнечная":
        пб = [(x, SU.полуширота(x, "средняя", z=G.DECKS["солнечная"] - 0.01) + SU.КАРНИЗ)
              for x, _ in SU.обвод("средняя", 0.5)]
    else:
        ярус = "главная" if палуба == "главная" else "средняя"
        пб = [(x, SU.полуширота(x, ярус, z=G.DECKS[палуба] + 0.6)) for x, _ in SU.обвод(ярус, 0.5)]
    return [(x, y) for x, y in пб if y > 0.05]


def обвод_прогулочной():
    """Кромка прогулочной палубы (крыша главного яруса) - на плане средней палубы, в портале -
    во всю ширину корпуса."""
    пб = [(x, L.side_half(x) - 0.02 if SU.в_портале(x) else
           SU.полуширота(x, "главная", z=G.DECKS["средняя"] - 0.01)) for x, _ in SU.обвод("главная", 0.5)]
    return [(x, y) for x, y in пб if y > 0.05]


def обвод_корпуса():
    xs = [i * 0.25 for i in range(int(G.LOA * 4) + 1)]
    return [(x, борт(x)) for x in xs]


def ряд(метки, lo, hi, до=4, сдвиг=9.0, зазор=3.5):
    """Ряд подписей-выносок над или под рисунком. Центры раздвигаются без налезаний с зазором
    `зазор` м, самая широкая подпись в тесном месте переносится на строку больше.
    метки - [dict(s, xa, ya, вар)], дописывает p (центр) и n (число строк). Возвращает высоту ряда."""
    метки.sort(key=lambda m: m["xa"])
    for m in метки:
        m["n"] = min(m["вар"])
    p = None
    for _ in range(400):
        ws = [m["вар"][m["n"]][1] for m in метки]
        p = _раздвинуть([m["xa"] for m in метки], ws, lo, hi, зазор)
        if p is not None:
            d = [abs(pi - m["xa"]) for pi, m in zip(p, метки)]
            i = int(np.argmax(d))
            if d[i] <= сдвиг:
                break
            # блок подписей, упёршихся друг в друга, вокруг самой сдвинутой
            a = b = i
            while a > 0 and p[a] - p[a - 1] <= (ws[a] + ws[a - 1]) / 2.0 + зазор + 1e-6:
                a -= 1
            while b < len(p) - 1 and p[b + 1] - p[b] <= (ws[b] + ws[b + 1]) / 2.0 + зазор + 1e-6:
                b += 1
            кандидаты = range(a, b + 1)
        else:
            кандидаты = range(len(метки))
        кандидаты = [j for j in кандидаты if any(k > метки[j]["n"] and k <= до for k in метки[j]["вар"])]
        if not кандидаты:
            break
        j = max(кандидаты, key=lambda j: метки[j]["вар"][метки[j]["n"]][1])
        метки[j]["n"] = min(k for k in метки[j]["вар"] if k > метки[j]["n"])
    if p is None:
        raise RuntimeError("подписи не помещаются по длине: %s" % [m["s"] for m in метки])
    for m, pi in zip(метки, p):
        m["p"] = pi
    return max(m["вар"][m["n"]][2] for m in метки)


def нарисовать_ряд(ax, метки, колено, y_lab, s, пт=None, fs=КЕГЛЬ, lw=ТОНКАЯ * 0.8, z=8, гало=False):
    """Подписи ряда и выноски: точка на предмете, вертикаль до колена, наклонный отрезок к краю
    ближней строки подписи. s = 1 - ряд сверху (подпись над y_lab), -1 - снизу.
    гало - белая обводка выноски и точки, чтобы они читались и на тёмном (облик судна)."""
    import matplotlib.patheffects as PE
    эфф = [PE.withStroke(linewidth=lw + 1.4, foreground="white")] if гало else None
    м1 = 1.0 / (пт or ПТ)                 # метров в 1 pt
    for m in метки:
        стр, w, h = m["вар"][m["n"]]
        p = m["p"]
        ax.text(p, y_lab, "\n".join(стр), ha="center", va="bottom" if s > 0 else "top",
                fontsize=fs, linespacing=ИНТЕРВАЛ, zorder=z)
        wl = размер(стр[-1] if s > 0 else стр[0], fs, пт)[0]
        xe = min(max(m["xa"], p - wl / 2.0 + 1.5 * м1), p + wl / 2.0 - 1.5 * м1)
        ye = y_lab - s * 1.0 * м1
        if abs(xe - m["xa"]) < 0.2 * м1:
            xs, ys = [m["xa"], m["xa"]], [m["ya"], ye]
        else:
            xs, ys = [m["xa"], m["xa"], xe], [m["ya"], колено, ye]
        ax.plot(xs, ys, color="black", lw=lw, zorder=z - 1, solid_capstyle="butt", path_effects=эфф)
        ax.plot([m["xa"]], [m["ya"]], "o", ms=2.4 if гало else 2.0, mfc="black",
                mec="white" if гало else "black", mew=0.6 if гало else 0.0, zorder=z - 1)


# ---------------------------------------------------------------- план
class План:
    def __init__(self, палуба):
        self.палуба = палуба
        self.fig = plt.figure(figsize=(ШИРИНА, 3.0))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.axis("off")
        self.преп = []            # препятствия для подписей внутри - (x0, y0, x1, y1)
        self.тексты = []          # уже поставленные подписи - тоже препятствия
        self.выноски = []         # подписи снаружи
        self.запрет_x = []        # (x0, x1) - куда не ставить вертикаль выноски над планом (номера переборок)
        self.занято_x = {1: [], -1: []}
        self.верх_номеров = 0.0
        self.примечания = []
        self.y_край = 8.25

    # --- примитивы
    def прямоуг(self, x0, y0, x1, y1, lw=ТОНКАЯ, color="black", ls="-", преп=True, hatch=None, z=3):
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        self.ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec=color, lw=lw, ls=ls,
                                    hatch=hatch, zorder=z))
        if преп:
            self.преп.append((x0, y0, x1, y1))

    def линия(self, xs, ys, lw=СТЕНА, color="black", ls="-", преп=True, z=4):
        self.ax.plot(xs, ys, color=color, lw=lw, ls=ls, zorder=z, solid_capstyle="butt")
        if преп:
            for i in range(len(xs) - 1):
                self.преп.append((min(xs[i], xs[i + 1]) - 0.05, min(ys[i], ys[i + 1]) - 0.05,
                                  max(xs[i], xs[i + 1]) + 0.05, max(ys[i], ys[i + 1]) + 0.05))

    def ломаная_борта(self, пб, lw, ends=True):
        """Обвод по верхней половине: обе стороны, торцы - по желанию."""
        xs = [p[0] for p in пб]
        ys = [p[1] for p in пб]
        self.ax.plot(xs, ys, color="black", lw=lw, zorder=5)
        self.ax.plot(xs, [-y for y in ys], color="black", lw=lw, zorder=5)
        if ends:
            for x, y in (пб[0], пб[-1]):
                self.ax.plot([x, x], [-y, y], color="black", lw=lw, zorder=5, solid_capstyle="butt")

    def стена_поперёк(self, x, полу, проёмы, lw=СТЕНА):
        """Поперечная стена от борта до борта с проёмами."""
        отрезки = [(-полу, полу)]
        for a, b in sorted(проёмы):
            нов = []
            for c, d in отрезки:
                if b <= c or a >= d:
                    нов.append((c, d))
                    continue
                if a > c:
                    нов.append((c, a))
                if b < d:
                    нов.append((b, d))
            отрезки = нов
        for c, d in отрезки:
            if d - c > 0.05:
                self.линия([x, x], [c, d], lw=lw)
        return отрезки

    def текст(self, x, y, s, ha="center", va="center", fs=КЕГЛЬ, rot=0, преп=True):
        s = гост(s)
        self.ax.text(x, y, s, ha=ha, va=va, fontsize=fs, rotation=rot, linespacing=ИНТЕРВАЛ, zorder=8)
        if преп:
            w, h = размер(s, fs)
            if rot:
                w, h = h, w
            x0 = x - w / 2.0 if ha == "center" else (x if ha == "left" else x - w)
            y0 = y - h / 2.0 if va == "center" else (y if va == "bottom" else y - h)
            self.тексты.append((x0, y0, x0 + w, y0 + h))

    # --- подписи
    def _свободно(self, box, полу, зз=ЗАЗОР):
        for x in (box[0], (box[0] + box[2]) / 2.0, box[2]):
            if max(abs(box[1]), abs(box[3])) > полу(x) - зз:
                return False
        for o in self.преп:
            if _пересек(box, o, зз):
                return False
        for o in self.тексты:
            if _пересек(box, o, 0.4):
                return False
        return True

    def внутри(self, s, x0, x1, полу, до=4, поворот=False, fs=КЕГЛЬ, y0=None, y1=None, зз=ЗАЗОР):
        """Подпись внутри помещения [x0, x1], если по размеру есть свободное место. True - поставлена."""
        лучшее = None
        вар = варианты(s, fs, до)
        for n, (стр, w, h) in sorted(вар.items()):
            for rot in ((0, 90) if поворот else (0,)):
                bw, bh = (h, w) if rot else (w, h)
                if bw > x1 - x0 - 2 * зз:
                    continue
                xc0 = (x0 + x1) / 2.0
                dxs = sorted(np.arange(-(x1 - x0) / 2.0, (x1 - x0) / 2.0 + 0.01, 0.25), key=abs)
                ymax = max(полу(x) for x in np.linspace(x0, x1, 9))
                lo = -ymax if y0 is None else y0 + зз
                hi = ymax if y1 is None else y1 - зз
                yc0 = (lo + hi) / 2.0
                dys = sorted(np.arange(lo - yc0, hi - yc0 + 0.01, 0.25), key=abs)
                найдено = None
                for dx in dxs:
                    cx = xc0 + dx
                    if cx - bw / 2.0 < x0 + зз or cx + bw / 2.0 > x1 - зз:
                        continue
                    for dy in dys:
                        cy = yc0 + dy
                        if cy - bh / 2.0 < lo or cy + bh / 2.0 > hi:
                            continue
                        box = (cx - bw / 2.0, cy - bh / 2.0, cx + bw / 2.0, cy + bh / 2.0)
                        if self._свободно(box, полу, зз):
                            найдено = (abs(dx) + abs(dy), cx, cy)
                            break
                    if найдено and найдено[0] < abs(dx) - 1e-9:
                        break
                    if найдено:
                        break
                if найдено:
                    цена = (n - 1) * 2.0 + найдено[0] * 0.25 + (1.5 if rot else 0.0)
                    if лучшее is None or цена < лучшее[0]:
                        лучшее = (цена, "\n".join(стр), найдено[1], найдено[2], rot)
        if лучшее is None:
            return False
        _, t, cx, cy, rot = лучшее
        self.текст(cx, cy, t, fs=fs, rot=rot)
        return True

    def якорь(self, x0, x1, сторона, полу):
        """Точка выноски в помещении - у стены со стороны подписи, на свободном месте."""
        xc = (x0 + x1) / 2.0
        лучшее = None
        for dx in sorted(np.arange(-(x1 - x0) / 2.0 + 0.5, (x1 - x0) / 2.0 - 0.49, 0.25), key=abs):
            x = xc + dx
            if сторона > 0 and any(a - 0.6 <= x <= b + 0.6 for a, b in self.запрет_x):
                continue
            if any(abs(x - u) < 1.2 for u in self.занято_x[сторона]):
                continue
            стена = полу(x)
            if стена < 1.0:
                continue
            for d in np.arange(0.7, стена + 0.01, 0.25):
                y = сторона * (стена - d)
                if not any(o[0] - 0.2 <= x <= o[2] + 0.2 and o[1] - 0.2 <= y <= o[3] + 0.2 for o in self.преп):
                    пересечений = sum(1 for o in self.преп if o[0] <= x <= o[2] and
                                      min(y, сторона * стена) <= o[3] and max(y, сторона * стена) >= o[1])
                    # вдоль кромки на пути наружу выноска сливалась бы с линией
                    вдоль = sum(1 for o in self.преп if min(abs(x - o[0]), abs(x - o[2])) < 0.5 and
                                o[3] - o[1] > 0.3 and ((сторона > 0 and o[3] > y) or (сторона < 0 and o[1] < y)))
                    цена = пересечений * 3.0 + вдоль * 5.0 + abs(dx) * 0.3 + d * 0.3
                    if лучшее is None or цена < лучшее[0]:
                        лучшее = (цена, x, y)
                    break
        if лучшее is None:
            return xc, сторона * max(полу(xc) - 0.7, 0.0)
        return лучшее[1], лучшее[2]

    def выноска(self, s, xa, ya, сторона):
        self.выноски.append(dict(s=s, xa=xa, ya=ya, сторона=сторона, вар=варианты(s)))
        self.занято_x[сторона].append(xa)

    def подпись_зоны(self, s, x0, x1, полу, сторона, внутри=True, **kw):
        if внутри and self.внутри(s, x0, x1, полу, **kw):
            return
        xa, ya = self.якорь(x0, x1, сторона, полу)
        self.выноска(s, xa, ya, сторона)

    # --- выпуск
    def выпустить(self, путь):
        ax = self.ax
        yh = max(self.y_край, self.верх_номеров)
        верх = [m for m in self.выноски if m["сторона"] > 0]
        низ = [m for m in self.выноски if m["сторона"] < 0]
        y_top = yh + 0.4
        if верх:
            колено = yh + 0.5
            y_lab = колено + 1.6
            h = ряд(верх, X0 + 0.3, X1 - 0.3)
            нарисовать_ряд(ax, верх, колено, y_lab, 1)
            y_top = y_lab + h + 0.3
        y_bot = -self.y_край - 0.4
        if низ:
            колено = -self.y_край - 0.5
            y_lab = колено - 1.6
            h = ряд(низ, X0 + 0.3, X1 - 0.3)
            нарисовать_ряд(ax, низ, колено, y_lab, -1)
            y_bot = y_lab - h - 0.3
        # шкала в метрах от кормового перпендикуляра
        ys = y_bot - 1.0
        ax.plot([0, G.LOA], [ys, ys], color="black", lw=ТОНКАЯ)
        hn = 0.0
        for x in range(0, int(G.LOA) + 1, 10):
            ax.plot([x, x], [ys, ys - 0.7], color="black", lw=ТОНКАЯ)
            t = "%d" % x
            w, hn = размер(t)
            if x + 10 > G.LOA:
                ax.text(x - w / 2.0, ys - 0.9, t + " м", ha="left", va="top", fontsize=КЕГЛЬ, zorder=8)
            else:
                ax.text(x, ys - 0.9, t, ha="center", va="top", fontsize=КЕГЛЬ, zorder=8)
        y = ys - 0.9 - hn - 0.9
        for абз in self.примечания:
            for стр in перенос(гост(абз), X1 - X0 - 0.6):
                ax.text(X0 + 0.3, y, стр, ha="left", va="top", fontsize=КЕГЛЬ, zorder=8)
                y -= размер(стр)[1] + 0.25
        y_bot = y - 0.3
        self.fig.set_size_inches(ШИРИНА, (y_top - y_bot) * ПТ / 72.0)
        ax.set_xlim(X0, X1)
        ax.set_ylim(y_bot, y_top)
        P.сохранить(self.fig, путь)
        plt.close(self.fig)
        return путь


# ---------------------------------------------------------------- наполнение
def _номера_переборок(пл, внутри_корпуса):
    """Водонепроницаемые переборки трюма: в трюме и на втором дне - толстой линией поперёк,
    на главной палубе (палуба переборок) - засечкой у борта. Над ними - отстояние от кормового
    перпендикуляра, м."""
    for x in GA.ПЕРЕБОРКИ:
        y = борт(x)
        if внутри_корпуса:
            пл.линия([x, x], [-y, y], lw=ПЕРЕБОРКА)
        y = L.side_half(x)          # у ниши колеса номер - над кромкой палубы, а не в нише
        if not внутри_корпуса:
            пл.ax.plot([x, x], [y + 0.25, y + 1.0], color="black", lw=ПЕРЕБОРКА, zorder=5)
        t = P.ч(x, 0)
        w, h = размер(t)
        y0 = y + (0.35 if внутри_корпуса else 1.15)
        пл.ax.text(x, y0, t, ha="center", va="bottom", fontsize=КЕГЛЬ, zorder=8)
        пл.запрет_x.append((x - w / 2.0, x + w / 2.0))
        пл.верх_номеров = max(пл.верх_номеров, y0 + h)


_КОД = {"люкс": "Л", "бизнес": "Б", "стандарт": "С", "эконом": "Э", "экипаж": "Эк"}
_ИМЯ = {"Л": "люкс", "Б": "бизнес", "С": "стандарт", "М4": "стандарт для маломобильных пассажиров",
        "Сем": "семейная", "Э": "эконом", "Эк": "экипаж"}
_ПОРЯДОК = ("Л", "Б", "С", "М4", "Сем", "Э", "Эк")


def _мест(n):
    return "%d %s" % (n, "место" if n == 1 else ("места" if n < 5 else "мест"))


def _каюты(пл, палуба):
    мест = {}
    for c in GA.расстановка():
        if c["палуба"] != палуба:
            continue
        y0, y1 = sorted((c["y0"], c["y1"]))
        пл.прямоуг(c["x0"], y0, c["x1"], y1, lw=ТОНКАЯ, преп=True, z=4)
        код = "М4" if c["М4"] else ("Сем" if c["тип"] == "семейная" else _КОД[c["категория"]])
        мест.setdefault(код, set()).add(c["мест"])
        fs = КЕГЛЬ
        w, h = размер(код, fs)
        while (w > c["x1"] - c["x0"] - 0.3 or h > y1 - y0 - 0.2) and fs > 7.6:
            fs -= 0.3
            w, h = размер(код, fs)
        пл.ax.text((c["x0"] + c["x1"]) / 2.0, (y0 + y1) / 2.0, код, ha="center", va="center",
                   fontsize=fs, zorder=8)
    части = []
    for код in _ПОРЯДОК:
        if код in мест:
            n = sorted(мест[код])
            места = _мест(n[0]) if len(n) == 1 else "%s и %s" % (", ".join(str(v) for v in n[:-1]), _мест(n[-1]))
            части.append("%s - %s на %s" % (код, _ИМЯ[код].split(" для ")[0], места) +
                         (" для " + _ИМЯ[код].split(" для ")[1] if " для " in _ИМЯ[код] else ""))
    пл.примечания.append("Каюты: " + ", ".join(части) + ".")


def _трап(пл, a, b, y0=-1.6, y1=1.6):
    """Трап двумя маршами - ступени линиями, стрелка подъёма по маршу."""
    пл.прямоуг(a, y0, b, y1, lw=ТОНКАЯ, z=4)
    ym = (y0 + y1) / 2.0
    пл.ax.plot([a, b], [ym, ym], color="black", lw=ТОНКАЯ, zorder=4)
    n = max(int(round((b - a) / 0.6)), 4)
    for i in range(1, n):
        x = a + (b - a) * i / n
        пл.ax.plot([x, x], [y0, y1], color="black", lw=МЕБЕЛЬ, zorder=4)
    yс = (ym + y1) / 2.0
    пл.ax.annotate("", xy=(b - 0.4, yс), xytext=(a + 0.4, yс), zorder=5,
                   arrowprops=dict(arrowstyle="-|>", lw=ТОНКАЯ, color="black", mutation_scale=5,
                                   shrinkA=0, shrinkB=0))


def _лифт(пл, x0, x1, y0, y1):
    """Шахта лифта - контур с диагоналями. Трап обходит шахту - белая заливка закрывает ступени."""
    пл.ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="white", ec="black", lw=ТОНКАЯ, zorder=6))
    пл.преп.append((x0, y0, x1, y1))
    пл.ax.plot([x0, x1], [y0, y1], color="black", lw=МЕБЕЛЬ, zorder=6)
    пл.ax.plot([x0, x1], [y1, y0], color="black", lw=МЕБЕЛЬ, zorder=6)


def _мебель(пл, палуба):
    for p in PB.мебель(палуба):
        кл = p["класс"]
        if кл == "стена":
            пл.прямоуг(p["x0"], p["y0"], p["x1"], p["y1"], lw=СТЕНА, z=4)
        elif кл == "ограждение":
            пл.прямоуг(p["x0"], p["y0"], p["x1"], p["y1"], lw=ТОНКАЯ, z=4)
        elif кл == "шахта":
            пл.прямоуг(p["x0"], p["y0"], p["x1"], p["y1"], lw=ТОНКАЯ, hatch="//////", z=4)
        else:
            пл.прямоуг(p["x0"], p["y0"], p["x1"], p["y1"], lw=МЕБЕЛЬ, color=СЕРЫЙ, z=3)


def _трапы_и_лифты(пл):
    for имя, (a, b) in GA.ТРАПЫ.items():
        _трап(пл, a, b)
    for имя, (a, b, y0, y1) in GA.ЛИФТЫ.items():
        _лифт(пл, a, b, y0, y1)


def _колодцы(пл, плита):
    """Вырезы в палубе над планом - пунктиром. Над трапами и лифтами вырез совпадает с ними."""
    занято = [(a, b) for a, b in GA.ТРАПЫ.values()] + [(v[0], v[1]) for v in GA.ЛИФТЫ.values()]
    for x0, x1, y0, y1 in PB.колодцы(плита):
        if any(x0 >= a - 0.3 and x1 <= b + 0.3 for a, b in занято):
            continue
        пл.прямоуг(x0, y0, x1, y1, lw=ТОНКАЯ, ls=(0, (4, 2)), z=4)
        return True
    return False


def _стены_зон(пл, палуба, полу):
    зоны = GA.ЗОНЫ[палуба]
    x_нач, x_кон = зоны[0][0], зоны[-1][1]
    for x in sorted({z[0] for z in зоны} | {z[1] for z in зоны}):
        y = полу(x)
        if y < 0.3:
            continue
        пл.стена_поперёк(x, y, PB.проёмы_переборки(палуба, x), lw=ЯРУС if x in (x_нач, x_кон) else СТЕНА)


def второе_дно():
    пл = План("второе дно")
    пб = обвод_корпуса()
    пл.ломаная_борта(пб, КОНТУР)
    полу = борт
    for s in (1, -1):
        пл.линия([GA.ПЕРЕБОРКИ[0], GA.ПЕРЕБОРКИ[-2]], [s * G.LONG_BULKHEAD_Y] * 2, lw=СТЕНА)
    _номера_переборок(пл, True)
    for t in G.TANKS:
        пл.прямоуг(t["x0"], t["y0"], t["x1"], t["y1"], lw=СТЕНА, преп=False, z=4)
    # сначала цистерны, в которые подпись входит, потом узкие - выносками
    for t in sorted(G.TANKS, key=lambda t: -(t["x1"] - t["x0"])):
        s = "%s %s м³" % (t["code"], P.ч(t["vol"], 0))
        if not пл.внутри(s, t["x0"], t["x1"], полу, до=2, поворот=True, y0=t["y0"], y1=t["y1"], зз=0.2):
            xc = (t["x0"] + t["x1"]) / 2.0
            сторона = 1 if (t["y0"] + t["y1"]) >= 0 else -1
            if t["y0"] < 0 < t["y1"]:
                сторона = 1 if len(пл.занято_x[1]) <= len(пл.занято_x[-1]) else -1
            ya = сторона * (min(abs(t["y1"]), abs(t["y0"])) if t["y0"] * t["y1"] > 0 else 0.0)
            ya = (t["y0"] + t["y1"]) / 2.0 if t["y0"] < 0 < t["y1"] else ya + сторона * 1.0
            пл.выноска(s, xc, ya, сторона)
        пл.преп.append((t["x0"], t["y0"], t["x1"], t["y1"]))
    # расшифровка обозначений цистерн
    группы = {}
    for t in G.TANKS:
        п = t["code"].split("-")[0]
        имя = t["name"].split(",")[0].replace(" ПБ", "").replace(" ЛБ", "")
        группы.setdefault(п, []).append((t["code"], имя))
    части = []
    for п, тт in группы.items():
        имена = {n for _, n in тт}
        if len(имена) == 1:
            части.append("%s - %s" % (п, имена.pop().lower()))
        else:
            части += ["%s - %s" % (к, n[0].lower() + n[1:]) for к, n in тт]
    пл.примечания.append("Цистерны: " + ", ".join(части) + ".")
    пл.примечания.append("Толстыми линиями показаны водонепроницаемые переборки, над ними - расстояние от "
                         "кормового перпендикуляра в метрах, продольные переборки на %s м от ДП."
                         % P.ч(G.LONG_BULKHEAD_Y, 2))
    return пл


def трюм():
    пл = План("трюм")
    пб = обвод_корпуса()
    пл.ломаная_борта(пб, КОНТУР)
    полу = борт
    _номера_переборок(пл, True)
    зоны = GA.ЗОНЫ["трюм"]
    for x in sorted({z[1] for z in зоны[:-1]}):
        if x not in GA.ПЕРЕБОРКИ:
            пл.линия([x, x], [-борт(x), борт(x)], lw=СТЕНА)
    к = SU.кожух()
    for s in (1, -1):
        пл.прямоуг(к["ниша_x0"], s * к["колесо_внутр"], к["ниша_x1"], s * к["колесо_наруж"],
                   lw=ТОНКАЯ, ls=(0, (4, 2)))
    пл.выноска("Гребное колесо", W.X_AXIS + 2.5, (к["колесо_внутр"] + к["колесо_наруж"]) / 2.0, 1)
    k = 0
    for x0, x1, тип, имя, _ in зоны:
        сторона = 1 if k % 2 == 0 else -1
        if not пл.внутри(имя, x0, x1, полу, до=5):
            пл.подпись_зоны(имя, x0, x1, полу, сторона, внутри=False)
            k += 1
    пл.примечания.append("Толстыми линиями показаны водонепроницаемые переборки, над ними - расстояние от "
                         "кормового перпендикуляра в метрах. Пунктиром - гребные колёса в нишах корпуса.")
    return пл


def главная():
    пл = План("главная")
    корп = обвод_корпуса()
    пл.ломаная_борта(корп, КОНТУР)
    ярус = обвод_яруса("главная")
    полу, (xa, xb) = _интерп(ярус)
    пл.ломаная_борта(ярус, ЯРУС, ends=False)
    _стены_зон(пл, "главная", полу)
    _номера_переборок(пл, False)
    # аппарель в корме, гараж
    г = G.GARAGE
    пл.прямоуг(-4.0, -г["ramp_width"] / 2.0, -4.0 + г["ramp_len"], г["ramp_width"] / 2.0, lw=ТОНКАЯ, z=4)
    for i in range(г["places"]):
        cx = г["x0"] + 2.0 + (i % 2) * (г["vehicle_len"] + 1.2)
        cy = 2.8 if i < 2 else -2.8
        пл.прямоуг(cx, cy - г["vehicle_width"] / 2.0, cx + г["vehicle_len"], cy + г["vehicle_width"] / 2.0,
                   lw=МЕБЕЛЬ, color=СЕРЫЙ)
        пл.ax.plot([cx + г["vehicle_len"] * 0.62] * 2, [cy - г["vehicle_width"] / 2.0 + 0.2,
                   cy + г["vehicle_width"] / 2.0 - 0.2], color=СЕРЫЙ, lw=МЕБЕЛЬ, zorder=3)
    _каюты(пл, "главная")
    _трапы_и_лифты(пл)
    _мебель(пл, "главная")
    вырез = _колодцы(пл, "средняя")
    # колёса под кожухами, выгородки ГЭД
    к = SU.кожух()
    for s in (1, -1):
        пл.прямоуг(к["x0"], s * к["y_внутр"], к["x1"], s * к["y_наруж"], lw=СТЕНА)
        пл.прямоуг(к["ниша_x0"], s * к["колесо_внутр"], к["ниша_x1"], s * к["колесо_наруж"],
                   lw=ТОНКАЯ, ls=(0, (4, 2)))
        пл.прямоуг(W.X_AXIS - 3.0, s * 3.0, W.X_AXIS + 3.0, s * 4.6, lw=ТОНКАЯ)
    пл.выноска("Гребное колесо", W.X_AXIS + 2.5, (к["колесо_внутр"] + к["колесо_наруж"]) / 2.0, 1)
    пл.выноска("ГЭД и редуктор", W.X_AXIS - 1.5, -3.8, -1)
    for p in PB.мебель("главная"):
        if p["класс"] == "шахта":
            пл.выноска("Шахта выхлопа", (p["x0"] + p["x1"]) / 2.0, (p["y0"] + p["y1"]) / 2.0, -1)
    k = 0
    for x0, x1, тип, имя, _ in GA.ЗОНЫ["главная"]:
        if тип == "cabins":
            continue
        if x0 < xa - 0.1 or x1 > xb + 0.1:
            # открытые площадки за стенами яруса - подпись выноской, точка на настиле
            if тип == "open" and x0 < 1.0:
                имя = "%s %s × %s м" % (имя, P.ч(г["ramp_len"]), P.ч(г["ramp_width"]))
            сторона = 1 if k % 2 == 0 else -1
            xm = (x0 + x1) / 2.0
            xm = min(max(xm, x0 + 1.0), x1 - 1.0)
            пл.выноска(имя, xm, сторона * max(борт(xm) - 1.2, 0.0) if xm > 1 else сторона * 2.8, сторона)
            k += 1
            continue
        if пл.внутри(имя, x0, x1, полу, до=3):
            continue
        сторона = 1 if k % 2 == 0 else -1
        пл.подпись_зоны(имя, x0, x1, полу, сторона, внутри=False)
        k += 1
    пл.примечания.append("Над контуром отмечены водонепроницаемые переборки трюма, цифры - расстояние от "
                         "кормового перпендикуляра в метрах. Пунктиром показаны гребные колёса под кожухами"
                         + (" и вырез в палубе над атриумом." if вырез else "."))
    return пл


def средняя():
    пл = План("средняя")
    пр = обвод_прогулочной()
    пл.ломаная_борта(пр, КОНТУР)
    ярус = обвод_яруса("средняя")
    полу, (xa, xb) = _интерп(ярус)
    пл.ломаная_борта(ярус, ЯРУС, ends=False)
    _стены_зон(пл, "средняя", полу)
    _каюты(пл, "средняя")
    _трапы_и_лифты(пл)
    _мебель(пл, "средняя")
    k = 0
    for x0, x1, тип, имя, _ in GA.ЗОНЫ["средняя"]:
        if тип == "cabins":
            continue
        if пл.внутри(имя, x0, x1, полу, до=3):
            continue
        сторона = 1 if k % 2 == 0 else -1
        пл.подпись_зоны(имя, x0, x1, полу, сторона, внутри=False)
        k += 1
    # прогулочная палуба в корме, между кромкой крыши главного яруса и стеной среднего
    пр_полу, _ = _интерп(пр)
    xm = (пр[0][0] + xa) / 2.0
    пл.выноска("Прогулочная палуба - крыша главного яруса", xm, -max(пр_полу(xm) - 1.2, 0.5), -1)
    return пл


def солнечная():
    пл = План("солнечная")
    пб = обвод_яруса("солнечная")
    пл.ломаная_борта(пб, КОНТУР)
    полу, _ = _интерп(пб)
    р = SU.РУБКА
    пл.прямоуг(р["x0"], -р["полу"], р["x1"], р["полу"], lw=ЯРУС, z=5, преп=False)
    for x in (р["x0"], р["x1"]):
        пл.преп.append((x - 0.05, -р["полу"], x + 0.05, р["полу"]))
    for y in (-р["полу"], р["полу"]):
        пл.преп.append((р["x0"], y - 0.05, р["x1"], y + 0.05))
    слоты = MOD.слоты()
    for s in слоты:
        пл.прямоуг(s["x0"], s["y0"], s["x1"], s["y1"], lw=ТОНКАЯ, ls=(0, (3, 2)), z=5)
        for (x, y) in s["фундаменты"]:
            пл.ax.add_patch(Rectangle((x - 0.2, y - 0.2), 0.4, 0.4, fc="black", ec="none", zorder=6))
    _мебель(пл, "солнечная")
    k = 0
    for x0, x1, тип, имя, _ in GA.ЗОНЫ["солнечная"]:
        if тип == "tech" and abs(x0 - р["x0"]) < 0.5:
            # рубка - подпись в её контуре
            if пл.внутри(имя, р["x0"], р["x1"], lambda x: р["полу"], до=2):
                continue
        elif пл.внутри(имя, x0, x1, полу, до=3):
            continue
        сторона = 1 if k % 2 == 0 else -1
        пл.подпись_зоны(имя, x0, x1, полу, сторона, внутри=False)
        k += 1
    s0 = слоты[0]
    пл.примечания.append("Пунктиром показаны слоты под модули 20' HC %s × %s м, %d шт., точками - "
                         "фундаменты-замки, %d шт." % (P.ч(s0["x1"] - s0["x0"], 2), P.ч(s0["y1"] - s0["y0"], 2),
                                                       len(слоты), len(MOD.фундаменты())))
    return пл


def build(verbose=True):
    листы = [("второе дно", второе_дно), ("трюм", трюм), ("главная", главная),
             ("средняя", средняя), ("солнечная", солнечная)]
    пути = []
    with P.чертёж():
        for i, (п, f) in enumerate(листы):
            пл = f()
            p = пл.выпустить(os.path.join(OUT, "%d_%s.png" % (i, п.replace(" ", "_"))))
            пути.append(p)
            if verbose:
                print("  ", os.path.basename(p))
    return пути


if __name__ == "__main__":
    build()
