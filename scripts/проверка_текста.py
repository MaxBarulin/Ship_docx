# -*- coding: utf-8 -*-
"""Проверка текста на листах: имена людей, поручения команде, ссылки на код, наложения, текст за рамкой.

    python scripts/проверка_текста.py dxf                 # все CAD/**/*.dxf
    python scripts/проверка_текста.py картинки            # прогнать генераторы картинок и разобрать текст
    python scripts/проверка_текста.py картинки лист_проекта.py планы_кают.py
    python scripts/проверка_текста.py документы           # записка и сопутствующие документы docs/проект

Код выхода 1, если нашлось имя, ссылка на код или файл, наложение текста на текст,
текст за рамкой листа или за краем картинки. Поручения («сверить», «ждём», «TODO») -
предупреждение: слово «проверить» бывает законным шагом техпроцесса.

Зачем. На листах, схемах и в штампах оставались «редакция Лены», «по заданию Глеба»,
фамилии в графах «Разраб.»/«Пров.», пути `docs/…`, `gorizont_hydro.resistance` и
подписи, лежащие друг на друге. Глазами по сотне листов такое не ловится.

DXF: габарит каждого TEXT/MTEXT - `ezdxf.bbox` по метрикам шрифта; рамка листа -
вторая по площади замкнутая полилиния на слое рамки.
Картинки: генератор запускается под перехватом (режим --трасса): matplotlib - каждый
реально нарисованный Text (Text.draw) с рамкой в пикселях, у Annotation - без стрелки;
PIL - ImageDraw.text/multiline_text через textbbox. Временные имена (запись через
temp + os.replace) сводятся к итоговым; одна и та же строка со сдвигом до 12 px -
обводка (гало), а не наложение.
"""
import glob, io, json, os, re, runpy, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# журнал свой на каждый прогон - параллельные проверки не затирают друг друга;
# дочерний процесс трассы получает путь через окружение
ЛОГ = os.environ.get("GORIZONT_ЛОГ_ТЕКСТА") or os.path.join(
    tempfile.gettempdir(), "gorizont_проверка_текста_%d.jsonl" % os.getpid())

ИМЕНА = re.compile(r"(?<![А-Яа-яЁё])(Лен[аеуыо]й?|Маш[аеуи]й?|Глеб[аеу]?|Иван[аеу]?|Андре[йяюе]|Владимир[аеу]?|"
                   r"Алексе[йяюе]|Макс[аеу]?|Барулин[а-я]*|Соколов[а-я]*|Игнатьев[а-я]*|Рябов[а-я]*)(?![А-Яа-яЁё])")
ПОРУЧЕНИЯ = re.compile(r"(?i)(передат|передай|посмотре|сверит|уточнит|ждём|ждёт|вход от|TODO|FIXME|заглушк|"
                       r"поручени|нейро|Claude|\(принято\)|редакци[ия] [0-9])")
КОД = re.compile(r"(gorizont\w*|blender_\w+|\w+\.py\b|scripts/|src/lib|docs/|CAD/|renders/|\.md\b|\.docx|\.blend|checks\(\)|"
                 r"\w+\.(?:png|jpe?g|pdf|dxf|dwg|xlsx|geojson|glb|stl|step)\b)")

#: генераторы картинок, у которых на листе есть текст (рендеры Blender без подписей не нужны)
ГЕНЕРАТОРЫ = [
    "схема_колеса.py", "планы_компоновки.py", "планы_кают.py", "облик_2d.py", "теоретический_чертёж.py",
    "корпус_и_ординаты.py", "расчёты_графики.py", "чертёж_мидель.py", "чертёж_набора.py", "модельный_ряд.py",
    "персонал_и_дорожная_карта.py", "солнечная_палуба.py", "модульное_решение.py", "документы_фундамента.py",
    "производство_фундамента.py", "маршрут.py", "лист_кают.py", "лист_расчётов.py", "лист_проекта.py",
    "записка_рынок.py", "экономика_графики.py",
]


def _наложения(т, доля):
    """Пары текстов, у которых пересечение рамок больше `доля` площади меньшей. т - [(строка, x0, y0, x1, y1)]."""
    уник = []
    for x in т:
        if any(u[0] == x[0] and abs(u[1] - x[1]) <= 12 and abs(u[2] - x[2]) <= 12 for u in уник):
            continue                                  # обводка (гало) одной и той же подписи
        уник.append(x)
    уник.sort(key=lambda x: x[1])
    пары = []
    for i, a in enumerate(уник):
        for b in уник[i + 1:]:
            if b[1] > a[3]:
                break
            ix = min(a[3], b[3]) - max(a[1], b[1]); iy = min(a[4], b[4]) - max(a[2], b[2])
            if ix <= 0 or iy <= 0:
                continue
            m = min((a[3] - a[1]) * (a[4] - a[2]), (b[3] - b[1]) * (b[4] - b[2]))
            if m > 0 and ix * iy / m > доля:
                пары.append("«%s» × «%s»" % (a[0][:40].replace("\n", " "), b[0][:40].replace("\n", " ")))
    return пары


#: устаревшее название - Российский Речной Регистр с 20.07.2022 называется Российское классификационное общество (РКО)
УСТАРЕЛО = re.compile(r"(?<![А-ЯЁ])РРР(?![А-ЯЁ])|[Рр]ечн[а-яё]* [Рр]егистр")
#: длинное и среднее тире, знак минуса U+2212 - на листах только дефис-минус «-»
ТИРЕ = re.compile("[\u2014\u2013\u2212]")


def _слова(строки):
    return dict(имена=sorted({s[:90] for s in строки if ИМЕНА.search(s)}),
                код=sorted({s[:90] for s in строки if КОД.search(s)}),
                тире=sorted({s[:90] for s in строки if ТИРЕ.search(s)}),
                устарело=sorted({s[:90] for s in строки if УСТАРЕЛО.search(s)}),
                поручения=sorted({s[:90] for s in строки if ПОРУЧЕНИЯ.search(s)}))


def _печать(имя, р):
    ус = р.get("устарело", [])
    плохо = len(р["имена"]) + len(р["код"]) + len(р["тире"]) + len(р["наложения"]) + len(р["за_краем"]) + len(ус)
    print("%s %-62s имена %d  код %d  тире %d  наложений %d  за краем %d  поручения %d" % (
        "!!" if плохо else "  ", имя[-62:], len(р["имена"]), len(р["код"]), len(р["тире"]), len(р["наложения"]),
        len(р["за_краем"]), len(р["поручения"])))
    if ус:
        print("     РРР - устаревшее название, теперь РКО: %d" % len(ус))
    for k in ("имена", "код", "тире", "наложения", "за_краем", "устарело", "поручения"):
        for s in р[k][:6]:
            print("     %-10s %s" % (k, s))
    return плохо


# --- DXF ---------------------------------------------------------------------------
def проверить_dxf(маски=None):
    import ezdxf
    from ezdxf import bbox as B
    всего = 0
    for f in sorted(sum((glob.glob(m, recursive=True) for m in (маски or [os.path.join(ROOT, "CAD", "**", "*.dxf")])), [])):
        doc = ezdxf.readfile(f)
        msp = doc.modelspace()
        т = []
        for e in msp.query("TEXT MTEXT ATTRIB"):
            s = e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.text
            if not s or not s.strip():
                continue
            bb = B.extents([e], fast=False)
            if bb.has_data:
                т.append((s, bb.extmin.x, bb.extmin.y, bb.extmax.x, bb.extmax.y))
        пл = []
        for e in msp.query("LWPOLYLINE"):
            if "РАМК" in e.dxf.layer.upper() and e.closed:
                p = list(e.get_points("xy"))
                xs, ys = [q[0] for q in p], [q[1] for q in p]
                пл.append(((max(xs) - min(xs)) * (max(ys) - min(ys)), (min(xs), min(ys), max(xs), max(ys))))
        пл.sort(reverse=True)
        р_ = пл[1][1] if len(пл) > 1 else None
        р = _слова([s for s, *_ in т])
        р["наложения"] = _наложения(т, 0.25)
        р["за_краем"] = sorted({s[:60] for s, x0, y0, x1, y1 in т if р_ and (
            x0 < р_[0] - 1 or y0 < р_[1] - 1 or x1 > р_[2] + 1 or y1 > р_[3] + 1)})
        всего += _печать(os.path.relpath(f, ROOT), р)
    return всего


# --- картинки -------------------------------------------------------------------------
def _трасса(скрипт, аргументы):
    """Запустить генератор, перехватив вывод текста (вызывается в отдельном процессе)."""
    последний = {}

    def лог(path, тексты, W, H):
        try:
            path = os.path.abspath(str(path))
        except Exception:
            return
        r = dict(файл=path, W=W, H=H, тексты=тексты)
        последний[os.path.normcase(path)] = r
        with open(ЛОГ, "a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    _replace = os.replace

    def replace(src, dst, *a, **k):
        res = _replace(src, dst, *a, **k)
        r = последний.get(os.path.normcase(os.path.abspath(str(src))))
        if r:
            лог(dst, r["тексты"], r["W"], r["H"])
        return res
    os.replace = replace

    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.figure import Figure
    from matplotlib.text import Text
    нарисовано = [None]
    _draw = Text.draw

    def draw(self, renderer):
        if нарисовано[0] is not None:
            try:
                s = self.get_text()
                if self.get_visible() and s and s.strip():
                    bb = Text.get_window_extent(self, renderer)
                    cb = self.get_clip_box() if self.get_clip_on() else None
                    if bb.width > 0 and bb.height > 0 and not (
                            cb is not None and (bb.x1 < cb.x0 or bb.x0 > cb.x1 or bb.y1 < cb.y0 or bb.y0 > cb.y1)):
                        нарисовано[0].append((s, bb))
            except Exception:
                pass
        return _draw(self, renderer)
    Text.draw = draw
    _savefig = Figure.savefig

    def savefig(self, fname, *a, **k):
        нарисовано[0] = []
        try:
            self.canvas.draw()
            H = self.bbox.height
            т = [[s, bb.x0, H - bb.y1, bb.x1, H - bb.y0] for s, bb in нарисовано[0]]
            tight = (k.get("bbox_inches") or matplotlib.rcParams.get("savefig.bbox")) == "tight"
            лог(getattr(fname, "name", fname), т, 0 if tight else self.bbox.width, H)
        finally:
            нарисовано[0] = None
        return _savefig(self, fname, *a, **k)
    Figure.savefig = savefig

    from PIL import Image, ImageDraw
    тексты = {}
    имена = ("fill", "font", "anchor", "spacing", "align")

    def запомнить(d, xy, text, k):
        try:
            im = getattr(d, "_image", None)
            if im is not None and str(text).strip():
                b = d.textbbox(xy, text, font=k.get("font"), anchor=k.get("anchor"), spacing=k.get("spacing", 4),
                               align=k.get("align", "left"))
                тексты.setdefault(id(im), []).append([str(text), b[0], b[1], b[2], b[3]])
        except Exception:
            pass
    _text, _mtext = ImageDraw.ImageDraw.text, ImageDraw.ImageDraw.multiline_text

    def text(self, xy, t, *a, **k):
        if "\n" not in str(t):
            запомнить(self, xy, t, dict(k, **dict(zip(имена, a))))
        return _text(self, xy, t, *a, **k)

    def mtext(self, xy, t, *a, **k):
        запомнить(self, xy, t, dict(k, **dict(zip(имена, a))))
        return _mtext(self, xy, t, *a, **k)
    ImageDraw.ImageDraw.text, ImageDraw.ImageDraw.multiline_text = text, mtext
    _Draw = ImageDraw.Draw

    def Draw(im, mode=None):
        d = _Draw(im, mode)
        d._image = im
        return d
    ImageDraw.Draw = Draw
    for имя in ("convert", "copy"):
        _o = getattr(Image.Image, имя)

        def обёртка(self, *a, _o=_o, **k):
            new = _o(self, *a, **k)
            if id(self) in тексты:
                тексты[id(new)] = list(тексты[id(self)])
            return new
        setattr(Image.Image, имя, обёртка)
    _save = Image.Image.save

    def save(self, fp, *a, **k):
        if тексты.get(id(self)):
            лог(fp if isinstance(fp, (str, os.PathLike)) else getattr(fp, "name", "<буфер>"), тексты[id(self)], *self.size)
        return _save(self, fp, *a, **k)
    Image.Image.save = save

    sys.argv = [скрипт] + list(аргументы)
    sys.path.insert(0, os.path.dirname(os.path.abspath(скрипт)))
    runpy.run_path(скрипт, run_name="__main__")


def проверить_картинки(скрипты=None):
    if os.path.exists(ЛОГ):
        os.remove(ЛОГ)
    env = dict(os.environ, PYTHONUTF8="1", MPLBACKEND="Agg", GORIZONT_ЛОГ_ТЕКСТА=ЛОГ)
    for s in скрипты or ГЕНЕРАТОРЫ:
        p = subprocess.run([sys.executable, "-X", "utf8", os.path.abspath(__file__), "--трасса",
                            os.path.join(ROOT, "scripts", s)], cwd=ROOT, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if p.returncode:
            print("!! %s: код выхода %d\n%s" % (s, p.returncode, p.stderr[-600:]))
    по_файлу = {}
    for ln in open(ЛОГ, encoding="utf-8") if os.path.exists(ЛОГ) else []:
        r = json.loads(ln)
        имя = os.path.basename(r["файл"])
        if "_tmp" not in имя and ".tmp." not in имя:
            по_файлу[r["файл"]] = r
    всего = 0
    for f, r in по_файлу.items():
        т, W, H = r["тексты"], r["W"], r["H"]
        р = _слова([x[0] for x in т])
        р["наложения"] = _наложения(т, 0.15)
        р["за_краем"] = sorted({x[0][:60] for x in т if W and (x[1] < -1 or x[2] < -1 or x[3] > W + 1 or x[4] > H + 1)})
        всего += _печать(os.path.relpath(f, ROOT) if f.startswith(ROOT) else f, р)
    return всего


# --- документы --------------------------------------------------------------------------
#: документы пакета; пути к рисункам и чертежам в них пока допустимы (по ним верстают), модули кода - нет
ДОКУМЕНТЫ = ["записка", "теория_корабля", "узел_фундамент_twistlock", "модульное_решение",
             "солнечная_палуба_нагрузка", "персонал_и_дорожная_карта"]
КОД_ДОК = re.compile(r"(gorizont\w*|blender_\w+|\w+\.py\b|src/lib|checks\(\)|[Сс]обрано `|(?<![А-Яа-яЁё])[Гг]енерир)")


def проверить_документы():
    всего = 0
    for имя in ДОКУМЕНТЫ:
        строки = io.open(os.path.join(ROOT, "docs", "проект", имя + ".md"), encoding="utf-8").read().splitlines()
        р = dict(имена=sorted({s[:90] for s in строки if ИМЕНА.search(s)}),
                 код=sorted({s[:90] for s in строки if КОД_ДОК.search(s)}),
                 тире=sorted({s[:90] for s in строки if ТИРЕ.search(s)}),
                 устарело=sorted({s[:90] for s in строки if УСТАРЕЛО.search(s)}),
                 поручения=sorted({s[:90] for s in строки if ПОРУЧЕНИЯ.search(s)}),
                 наложения=[], за_краем=[])
        всего += _печать("docs/проект/%s.md" % имя, р)
    return всего


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--трасса":
        _трасса(sys.argv[2], sys.argv[3:])
        sys.exit(0)
    режим = sys.argv[1] if len(sys.argv) > 1 else "dxf"
    n = (проверить_dxf() if режим == "dxf" else проверить_документы() if режим == "документы"
         else проверить_картинки(sys.argv[2:] or None))
    print("замечаний: %d" % n)
    sys.exit(1 if n else 0)
