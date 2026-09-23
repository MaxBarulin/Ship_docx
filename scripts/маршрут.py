# -*- coding: utf-8 -*-
"""Маршрут на карте и путь по фарватеру для приложения.

    python scripts/маршрут.py              # маршрут.geojson + карты 04_маршрут.png (спутник) и 04а_маршрут_карта.png (Яндекс Карты с мостами)
    python scripts/маршрут.py --пересчитать

Порты и программа - `lib.gorizont_route`. Путь между портами прокладывается
по осевым линиям рек Natural Earth 10m (общественное достояние) - линии Волги,
Камы и Белой склеиваются в граф, порты привязываются к ближайшей вершине
своей реки, между соседними портами ищется кратчайший путь по графу. Длина
плеч - по этому пути, а не по прямой.

Карты - простые, как нарисованные поверх снимка в PowerPoint: кадр по маршруту,
маршрут одной красной линией, порты - белые кружки с номером дня и подписью
названием рядом (Calibri, белое гало), на второй карте - мосты и шлюзы значками
с высотой прохода и маленькая легенда в рамке. Заголовков, панелей и расписания
на картинке нет, программа по дням - таблицей в записке. Атрибуция подложки -
мелким текстом в углу (требование лицензии).

Подложка первой карты - Sentinel-2 cloudless 2020 (EOX IT Services GmbH, CC BY 4.0,
содержит изменённые данные Copernicus Sentinel 2020), тайлы z = 9 кэшируются
в %LOCALAPPDATA%/gorizont_cache. Второй - скриншот Яндекс Карт из того же кэша.
Линии и значки рисуются с тройным запасом разрешения и уменьшаются - края без
лесенки, текст - прямо на итоговой картинке. Подписи раскладываются без наложений
друг на друга, на значки и на линию маршрута, дальние - с выноской.
"""
import os, sys, io, json, math, heapq, time, zipfile, tempfile, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from lib import gorizont_route as R

КЭШ = os.path.join(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()), "gorizont_cache")
os.makedirs(os.path.join(КЭШ, "tiles"), exist_ok=True)
NE_URL = "https://naciscdn.org/naturalearth/10m/physical/ne_10m_rivers_lake_centerlines.zip"
TILE_URL = "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2020_3857/default/g/%d/%d/%d.jpg"
#: Источники тайлов: имя → (шаблон URL, порядок подстановки, расширение, кэш-префикс)
ИСТОЧНИКИ = {"s2": (TILE_URL, "zyx", "jpg", "s2"),
             "osm": ("https://tile.openstreetmap.org/%d/%d/%d.png", "zxy", "png", "osm")}
АТРИБУЦИЯ = ("Подложка Sentinel-2 cloudless 2020, © EOX IT Services GmbH (CC BY 4.0), "
             "изменённые данные Copernicus Sentinel 2020, реки Natural Earth")
АТРИБУЦИЯ_OSM = "Подложка © участники OpenStreetMap (ODbL), реки Natural Earth, положение мостов и шлюзов приближённое"
OUT_PNG = os.path.join(ROOT, "renders", "горизонт_2026", "схемы", "04_маршрут.png")
OUT_PNG2 = os.path.join(ROOT, "renders", "горизонт_2026", "схемы", "04а_маршрут_карта.png")
OUT_GEO = R.ФАЙЛ_ПУТИ
РЕКИ = {"Волга": ("Volga",), "Кама": ("Kama",), "Белая": ("Belaya",)}
F = r"C:\Windows\Fonts"
ZOOM = 9

#: Итоговая ширина карт, px (спутниковый снимок жмётся хуже - кадр меньше), и запас разрешения для линий и значков.
ШИРИНА, ШИРИНА_СПУТНИК = 2400, 2000
SS = 3
#: Стандартные цвета Office: «красный», «тёмно-красный», «синий».
КРАСНЫЙ, ТЁМНО_КРАСНЫЙ, СИНИЙ = (255, 0, 0), (192, 0, 0), (0, 112, 192)
ЧЁРНЫЙ, БЕЛЫЙ = (0, 0, 0), (255, 255, 255)
#: Кегли, px: порт, номер дня, мост, река, легенда, атрибуция.
КЕГЛЬ = dict(порт=40, номер=28, мост=30, река=36, легенда=30, атрибуция=21)


def _скачать(url, путь):
    if not os.path.exists(путь):
        req = urllib.request.Request(url, headers={"User-Agent": "gorizont-route/1.0 (Ship_docx)"})
        open(путь, "wb").write(urllib.request.urlopen(req, timeout=120).read())
    return путь


def шрифт(sz, курсив=False):
    return ImageFont.truetype(os.path.join(F, "calibrii.ttf" if курсив else "calibri.ttf"), sz)


# --- реки → граф ---------------------------------------------------------------
def линии_рек():
    import shapefile
    zp = _скачать(NE_URL, os.path.join(КЭШ, "ne_rivers.zip"))
    d = os.path.join(КЭШ, "ne_rivers")
    if not os.path.isdir(d):
        zipfile.ZipFile(zp).extractall(d)
    shp = [f for f in os.listdir(d) if f.endswith(".shp")][0]
    rd = shapefile.Reader(os.path.join(d, shp), encoding="utf-8")
    out = []   # (река, [(lon, lat), ...])
    for sr in rd.iterShapeRecords():
        nm = sr.record.as_dict().get("name") or ""
        for река, имена in РЕКИ.items():
            if nm in имена:
                pts = sr.shape.points
                parts = list(sr.shape.parts) + [len(pts)]
                for a, b in zip(parts, parts[1:]):
                    seg = [(round(x, 5), round(y, 5)) for x, y in pts[a:b]]
                    if len(seg) > 1:
                        out.append((река, seg))
    return out


def граф(линии, склейка_км=12.0):
    """Вершины - точки линий, рёбра - соседние точки, концы линий склеиваются с
    ближайшей вершиной любой линии в пределах склейка_км (стыки рек и участков)."""
    узлы, рёбра, река_узла = {}, {}, {}

    def uid(p):
        if p not in узлы:
            узлы[p] = len(узлы); рёбра[узлы[p]] = {}
        return узлы[p]

    for река, seg in линии:
        ids = [uid(p) for p in seg]
        for i in ids:
            река_узла.setdefault(i, set()).add(река)
        for a, b, pa, pb in zip(ids, ids[1:], seg, seg[1:]):
            w = R._гаверсин(pa, pb)
            рёбра[a][b] = w; рёбра[b][a] = w
    точки = {v: k for k, v in узлы.items()}
    # склейка концов
    концы = []
    for река, seg in линии:
        концы += [узлы[seg[0]], узлы[seg[-1]]]
    for e in концы:
        pe = точки[e]
        лучшая = None
        for v, p in точки.items():
            if v == e or v in рёбра[e]:
                continue
            d = R._гаверсин(pe, p)
            if d <= склейка_км and (лучшая is None or d < лучшая[0]):
                лучшая = (d, v)
        if лучшая:
            рёбра[e][лучшая[1]] = лучшая[0]; рёбра[лучшая[1]][e] = лучшая[0]
    return точки, рёбра, река_узла


def ближайший(точки, река_узла, lon, lat, река):
    best = None
    for v, p in точки.items():
        if река not in река_узла.get(v, ()):
            continue
        d = R._гаверсин((lon, lat), p)
        if best is None or d < best[0]:
            best = (d, v)
    return best[1], best[0]


def дейкстра(рёбра, a, b):
    dist, prev, q = {a: 0.0}, {}, [(0.0, a)]
    while q:
        d, u = heapq.heappop(q)
        if u == b:
            break
        if d > dist.get(u, 1e18):
            continue
        for v, w in рёбра[u].items():
            nd = d + w
            if nd < dist.get(v, 1e18):
                dist[v] = nd; prev[v] = u; heapq.heappush(q, (nd, v))
    if b not in dist:
        return None, None
    path, v = [b], b
    while v != a:
        v = prev[v]; path.append(v)
    return path[::-1], dist[b]


def построить_путь():
    линии = линии_рек()
    точки, рёбра, река_узла = граф(линии)
    features, весь, плечи = [], [], []
    for a, b in zip(R.ПОРТЫ, R.ПОРТЫ[1:]):
        va, da = ближайший(точки, река_узла, a["lon"], a["lat"], a["река"])
        vb, db = ближайший(точки, река_узла, b["lon"], b["lat"], b["река"])
        path, км = дейкстра(рёбра, va, vb)
        if path is None:
            raise RuntimeError("нет пути %s → %s по графу рек" % (a["порт"], b["порт"]))
        coords = [(a["lon"], a["lat"])] + [точки[v] for v in path] + [(b["lon"], b["lat"])]
        км_всего = round(км + da + db)
        плечи.append((a["порт"], b["порт"], км_всего))
        features.append(dict(type="Feature", properties=dict(тип="плечо", от=a["порт"], до=b["порт"], км=км_всего),
                             geometry=dict(type="LineString", coordinates=[[x, y] for x, y in coords])))
        весь += coords if not весь else coords[1:]
    features.insert(0, dict(type="Feature", properties=dict(тип="маршрут", дней=R.ДНЕЙ, км=sum(p[2] for p in плечи), мост_мин=R.МОСТ_МИН),
                            geometry=dict(type="LineString", coordinates=[[x, y] for x, y in весь])))
    рп = {r["порт"] + str(r["день"]): r for r in R.расписание()}
    for p in R.ПОРТЫ:
        r = рп[p["порт"] + str(p["день"])]
        features.append(dict(type="Feature", properties=dict(тип="порт", день=p["день"], порт=p["порт"], река=p["река"],
                                                            стоянка=p.get("стоянка", 1), программа=p["программа"],
                                                            приход=r["приход_чч"], отход=r["отход_чч"]),
                             geometry=dict(type="Point", coordinates=[p["lon"], p["lat"]])))
    g = dict(type="FeatureCollection", name="Волжский Горизонт - маршрут Самара - Уфа - Самара", features=features)
    os.makedirs(os.path.dirname(OUT_GEO), exist_ok=True)
    json.dump(g, open(OUT_GEO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return весь, плечи


# --- подложки -------------------------------------------------------------------
def _tile_xy(lon, lat, z):
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.log(math.tan(math.radians(lat)) + 1.0 / math.cos(math.radians(lat))) / math.pi) / 2.0 * n
    return x, y


def подложка(bbox, z=ZOOM, источник="s2"):
    url, порядок, ext, префикс = ИСТОЧНИКИ[источник]
    lon0, lat0, lon1, lat1 = bbox
    x0, y1 = _tile_xy(lon0, lat0, z)
    x1, y0 = _tile_xy(lon1, lat1, z)
    tx0, tx1, ty0, ty1 = int(x0), int(x1), int(y0), int(y1)
    img = Image.new("RGB", ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256), (10, 20, 30))
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            p = os.path.join(КЭШ, "tiles", "%s_%d_%d_%d.%s" % (префикс, z, tx, ty, ext))
            try:
                _скачать(url % ((z, ty, tx) if порядок == "zyx" else (z, tx, ty)), p)
                img.paste(Image.open(p).convert("RGB"), ((tx - tx0) * 256, (ty - ty0) * 256))
            except Exception as e:
                print("тайл", z, tx, ty, "не скачан:", e)

    def px(lon, lat):
        x, y = _tile_xy(lon, lat, z)
        return (x - tx0) * 256, (y - ty0) * 256
    return img, px


#: Подложка второй карты - скриншот Яндекс Карт (решение пользователя 22.09.2026: скриншоты Яндекса
#: допустимы, тайлы Google - нет). Снимается настоящим Chrome через Playwright (headless Яндекс отдаёт
#: страницу «limited»), кэшируется в gorizont_cache; проекция Яндекса - EPSG:3395, эллипсоид.
ЯНДЕКС_Z = 9
ЯНДЕКС_E = 0.0818191908426
АТРИБУЦИЯ_ЯНДЕКС = "Подложка © Яндекс Карты, реки Natural Earth, положение мостов и шлюзов приближённое"


def _меркатор_3395(lon, lat, z):
    n = 256 * 2 ** z
    x = (lon + 180.0) / 360.0 * n
    f = math.radians(lat)
    m = math.tan(math.pi / 4 + f / 2) * ((1 - ЯНДЕКС_E * math.sin(f)) / (1 + ЯНДЕКС_E * math.sin(f))) ** (ЯНДЕКС_E / 2)
    y = (0.5 - math.log(m) / (2 * math.pi)) * n
    return x, y


def подложка_яндекс(bbox, z=ЯНДЕКС_Z, пересчитать=False):
    """Скриншот карты Яндекса под bbox. Центр - середина bbox, размер контейнера - по охвату плюс поле.
    Возвращает (img, px), как подложка()."""
    from playwright.sync_api import sync_playwright
    lon0, lat0, lon1, lat1 = bbox
    x0, y1 = _меркатор_3395(lon0, lat0, z)
    x1, y0 = _меркатор_3395(lon1, lat1, z)
    W = min(4000, int(x1 - x0) + 120)
    H = min(2700, int(y1 - y0) + 120)
    cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    # центр контейнера в градусах - обратная проекция по x прямая, по y подбором
    lon_c = cx / (256 * 2 ** z) * 360.0 - 180.0
    lo, hi = lat0, lat1
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if _меркатор_3395(lon_c, mid, z)[1] > cy:
            lo = mid
        else:
            hi = mid
    lat_c = 0.5 * (lo + hi)
    SIDE = 420
    кэш = os.path.join(КЭШ, "yandex_%.4f_%.4f_z%d_%dx%d.png" % (lon_c, lat_c, z, W, H))
    if пересчитать or not os.path.exists(кэш):
        url = "https://yandex.ru/maps/?ll=%.5f,%.5f&z=%d&l=map&lang=ru_RU" % (lon_c, lat_c, z)
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=False,
                                  args=["--disable-blink-features=AutomationControlled", "--window-size=1600,900"])
            ctx = b.new_context(viewport={"width": W + SIDE, "height": H}, device_scale_factor=1, locale="ru-RU",
                                user_agent="Mozilla/5.0 (Windows NT 10.0, Win64. X64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
            ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get - () => undefined});")
            pg = ctx.new_page()
            pg.goto(url, wait_until="load", timeout=120000)
            pg.wait_for_timeout(12000)
            pg.add_style_tag(content=".map-controls, .sidebar-view, aside {display:none !important}")
            pg.wait_for_timeout(1500)
            box = pg.locator(".map-container").bounding_box()
            pg.locator(".map-container").screenshot(path=кэш)
            b.close()
        print("скриншот Яндекса", os.path.basename(кэш), box)
    img = Image.open(кэш).convert("RGB")
    W, H = img.size
    ccx, ccy = _меркатор_3395(lon_c, lat_c, z)

    def px(lon, lat):
        x, y = _меркатор_3395(lon, lat, z)
        return (x - ccx + W / 2.0, y - ccy + H / 2.0)
    return img, px


def _кадр(img, px, bbox, ширина=ШИРИНА):
    """Обрезка подложки по bbox и уменьшение до ширины. Возвращает (картинка, P), P(lon, lat) → px кадра."""
    x0, y1 = px(bbox[0], bbox[1]); x1, y0 = px(bbox[2], bbox[3])
    x0, y0 = max(0, int(x0)), max(0, int(y0)); x1, y1 = min(img.width, int(x1)), min(img.height, int(y1))
    img = img.crop((x0, y0, x1, y1))
    sc = ширина / img.width
    img = img.resize((ширина, int(round(img.height * sc))), Image.LANCZOS)

    def P(lon, lat):
        x, y = px(lon, lat)
        return ((x - x0) * sc, (y - y0) * sc)
    return img, P


# --- раскладка подписей -----------------------------------------------------------
def _площадь_пересечения(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0]); h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def _точки_линии(pts, шаг=5.0):
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / шаг))
        out += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n)]
    out.append(pts[-1])
    return np.array(out)


class Раскладка:
    """Места подписей: занятые прямоугольники (значки, подписи, легенда), точки линии маршрута,
    край кадра. Ближнее место у значка, если оно свободно, иначе - дальнее с выноской."""

    def __init__(self, W, H, маршрут, поле=10):
        self.W, self.H, self.поле = W, H, поле
        self.занято = []
        self.м = _точки_линии(маршрут)

    def занять(self, r):
        self.занято.append(tuple(r))

    def цена(self, r):
        x0, y0, x1, y1 = r
        c = sum(_площадь_пересечения(r, z) for z in self.занято)
        п = self.поле
        c += 8.0 * ((x1 - x0) * (y1 - y0) - _площадь_пересечения(r, (п, п, self.W - п, self.H - п)))
        m = self.м
        k = np.count_nonzero((m[:, 0] > x0 - 4) & (m[:, 0] < x1 + 4) & (m[:, 1] > y0 - 4) & (m[:, 1] < y1 + 4))
        return c + 80.0 * k

    def место(self, w, h, x, y, rx, ry=None, выноска=True, зазор=6, сторона=None):
        """Прямоугольник w × h у значка с центром (x, y) и полуосями rx, ry. Возвращает (rect, нужна_выноска).
        `сторона` - (dx, dy), куда подпись ставится в первую очередь, если там свободно (как текст, сдвинутый руками)."""
        ry = rx if ry is None else ry
        g = зазор
        if сторона:
            dx, dy = сторона
            for доп in (0, 12, 24, 36):
                a = x + rx + g + доп if dx > 0 else x - rx - g - доп - w if dx < 0 else x - w / 2
                b = y + ry + g + доп if dy > 0 else y - ry - g - доп - h if dy < 0 else y - h / 2
                r = (a, b, a + w, b + h)
                if self.цена(r) == 0:
                    self.занять(r)
                    return r, False
        ближние = [(x + rx + g, y - h / 2), (x - rx - g - w, y - h / 2),
                   (x + 0.7 * rx + g, y - 0.7 * ry - h), (x + 0.7 * rx + g, y + 0.7 * ry),
                   (x - 0.7 * rx - g - w, y - 0.7 * ry - h), (x - 0.7 * rx - g - w, y + 0.7 * ry),
                   (x - w / 2, y - ry - g - h), (x - w / 2, y + ry + g)]
        варианты = [(self.цена((a, b, a + w, b + h)) + 3.0 * i, (a, b, a + w, b + h), False)
                    for i, (a, b) in enumerate(ближние)]
        if выноска:
            for дист in (40, 70, 110, 160, 220, 290):
                for k in range(16):
                    ang = 2 * math.pi * k / 16
                    cx, cy = math.cos(ang), math.sin(ang)
                    ax, ay = x + (rx + дист) * cx, y + (ry + дист) * cy
                    a = ax if cx > 0.38 else ax - w if cx < -0.38 else ax - w / 2
                    b = ay if cy > 0.38 else ay - h if cy < -0.38 else ay - h / 2
                    r = (a, b, a + w, b + h)
                    варианты.append((self.цена(r) + self.цена_выноски(x, y, rx, r) + 700 + 6.0 * дист, r, True))
        _, r, вын = min(варианты, key=lambda v: v[0])
        self.занять(r)
        if вын:                                 # выноска - тоже линия, следующие подписи её обходят
            self.м = np.vstack([self.м, self._выноска(x, y, rx, r)])
        return r, вын

    @staticmethod
    def _выноска(x, y, rx, r, шаг=4.0):
        """Точки выноски от края значка до ближайшей точки подписи."""
        tx, ty = min(max(x, r[0]), r[2]), min(max(y, r[1]), r[3])
        n = math.hypot(tx - x, ty - y)
        if n <= rx + 4:
            return np.zeros((0, 2))
        ts = np.arange(rx + 4, n - 2, шаг) / n
        return np.column_stack([x + (tx - x) * ts, y + (ty - y) * ts])

    def цена_выноски(self, x, y, rx, r):
        """Выноска не должна проходить через другие подписи и значки."""
        т = self._выноска(x, y, rx, r)
        c = 0
        for z in self.занято:
            if z[0] <= x <= z[2] and z[1] <= y <= z[3]:
                continue                        # свой значок
            c += np.count_nonzero((т[:, 0] > z[0] - 3) & (т[:, 0] < z[2] + 3) & (т[:, 1] > z[1] - 3) & (т[:, 1] < z[3] + 3))
        return 150.0 * c


class Подпись:
    """Текст в одну или несколько строк с гало: размеры для раскладки и отрисовка по baseline."""
    ГАЛО = 3

    def __init__(self, строки, f, fill, гало, гало_w=3):
        self.строки = [строки] if isinstance(строки, str) else list(строки)
        self.f, self.fill, self.гало, self.гало_w = f, fill, гало, гало_w
        self.asc, self.desc = f.getmetrics()
        self.шаг = int(round(f.size * 1.2))
        self.w = max(f.getlength(s) for s in self.строки) + 2 * self.ГАЛО
        self.h = self.asc + self.desc + (len(self.строки) - 1) * self.шаг + 2 * self.ГАЛО

    def нарисовать(self, d, r, выровнять="left"):
        for i, s in enumerate(self.строки):
            x = r[0] + self.ГАЛО
            if выровнять == "right":
                x = r[2] - self.ГАЛО - self.f.getlength(s)
            d.text((x, r[1] + self.ГАЛО + self.asc + i * self.шаг), s, font=self.f, fill=self.fill, anchor="ls",
                   stroke_width=self.гало_w, stroke_fill=self.гало)


# --- общая отрисовка карты -----------------------------------------------------------
def _число(v):
    return ("%.1f" % v).replace(".", ",")


#: Куда ставить подпись в первую очередь (dx, dy): Ширяево - за линию маршрута вправо, шлюзы
#: Жигулёвской ГЭС - вниз, на Жигули, иначе подписи Тольятти, Ширяева и шлюзов сбиваются в кучу.
СТОРОНА = {"Ширяево": (1, 0), "Шлюзы Жигулёвской ГЭС": (0, 1), "Бирский понтонный (наплавной) мост": (1, -1)}

#: Короткие подписи сооружений на карте: (название, род - «мост», «мосты», «шлюзы»).
КОРОТКО = {
    "Шлюзы Жигулёвской ГЭС": ("Жигулёвские шлюзы", "шлюзы"),
    "Императорский мост (Ульяновск)": ("Императорский", "мост"),
    "Президентский мост (Ульяновск)": ("Президентский", "мост"),
    "Алексеевский мост": ("Алексеевский", "мост"),
    "Шлюзы Нижнекамской ГЭС": ("Нижнекамские шлюзы", "шлюзы"),
    "Бирский понтонный (наплавной) мост": ("Наплавной", "мост"),
    "Затонские мосты (Уфа)": ("Затонские", "мосты"),
    "Дёмский железнодорожный мост (Уфа)": ("Дёмский", "мост"),
    "Бельский мостовой переход (Уфа)": ("Бельский", "мост"),
    "Сарапульский железнодорожный мост": ("Сарапульский ж.-д.", "мост"),
}


def _строки_кластера(мосты):
    """Подпись группы близких сооружений: одинаковые высоты - в одну строку («Дёмский и Бельский мосты 13,5 м»)."""
    группы = {}
    for m in мосты:
        группы.setdefault(m["высота"], []).append(m)
    строки = []
    for h in sorted(группы, key=lambda v: (v is None, v or 0)):
        имена = [КОРОТКО.get(m["мост"], (m["мост"].split(" (")[0], "")) for m in группы[h]]
        if len(имена) == 1:
            имя, род = имена[0]
            текст = имя if род == "шлюзы" or not род else "%s %s" % (имя, род)
        else:
            род = "мосты" if all(р in ("мост", "мосты") for _, р in имена) else ""
            текст = " и ".join(и for и, _ in имена) + (" " + род if род else "")
        строки += ["%s %s м" % (текст, _число(h))] if h is not None else [текст + ",", "разводной"]
    return строки


def _рисовать(основа, P, путь, стиль, мосты=False, атрибуция=""):
    """Маршрут, порты с номерами дней, реки, при мосты=True - мосты и шлюзы с высотами, легенда, атрибуция.
    Линии и значки - на прозрачном слое с запасом SS, текст - на итоговой картинке."""
    W, H = основа.size
    линия = стиль["линия"]
    ov = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)

    def S(*xy):
        return [v * SS for v in xy]

    pts = [P(lon, lat) for lon, lat in путь]
    ρ = Раскладка(W, H, pts)
    текст_порт = dict(fill=стиль["текст"], гало=стиль["гало"], гало_w=стиль.get("гало_w", 3))
    f_порт, f_ном, f_мост = шрифт(КЕГЛЬ["порт"]), шрифт(КЕГЛЬ["номер"]), шрифт(КЕГЛЬ["мост"])
    f_лег, f_атр, f_река = шрифт(КЕГЛЬ["легенда"]), шрифт(КЕГЛЬ["атрибуция"]), шрифт(КЕГЛЬ["река"], курсив=True)

    # легенда и атрибуция - правый нижний угол, место резервируется первым
    атр = Подпись(атрибуция, f_атр, **стиль["атрибуция"])
    атр_r = (W - 12 - атр.w, H - 8 - атр.h, W - 12, H - 8)
    ρ.занять(атр_r)
    легенда = [("линия", "маршрут по фарватеру"), ("кружок", "стоянка в порту, число - день круиза")]
    if мосты:
        легенда += [("мост", "мост, высота прохода"), ("шлюз", "шлюзы ГЭС, высота прохода")]
    шаг_л, поле_л, знак_л = int(КЕГЛЬ["легенда"] * 1.55), 16, 74
    лег_w = поле_л * 2 + знак_л + max(f_лег.getlength(t) for _, t in легенда)
    лег_h = поле_л * 2 + шаг_л * len(легенда) - (шаг_л - КЕГЛЬ["легенда"])
    лег_r = (W - 20 - лег_w, атр_r[1] - 14 - лег_h, W - 20, атр_r[1] - 14)
    ρ.занять(лег_r)

    # порты: Самара в начале и в конце - один кружок «1 и 15»
    имена = [p["порт"] for p in R.ПОРТЫ]
    порты = []
    for i, p in enumerate(R.ПОРТЫ):
        if p["порт"] in имена[i + 1:]:
            continue
        x, y = P(p["lon"], p["lat"])
        лаб = "%d" % p["день"] if p.get("стоянка", 1) == 1 else "%d-%d" % (p["день"], p["день"] + p["стоянка"] - 1)
        if p["порт"] in имена[:i]:
            лаб = "%d и %s" % (R.ПОРТЫ[имена.index(p["порт"])]["день"], лаб)
        ry = 18
        rx = max(ry, f_ном.getlength(лаб) / 2 + 9)
        порты.append(dict(x=x, y=y, rx=rx, ry=ry, лаб=лаб, имя="ходовой день" if p.get("ход") else p["порт"],
                          ход=bool(p.get("ход"))))
        ρ.занять((x - rx - 3, y - ry - 3, x + rx + 3, y + ry + 3))

    # мосты и шлюзы: близкие - одним значком, значок не заходит на кружок порта
    знаки = []
    if мосты:
        for m in (m for m in R.МОСТЫ if "lat" in m):
            x, y = P(m["lon"], m["lat"])
            for k in знаки:
                if math.hypot(k["x0"] - x, k["y0"] - y) < 40:
                    k["мосты"].append(m); break
            else:
                знаки.append(dict(x0=x, y0=y, мосты=[m]))
        for k in знаки:
            k["x0"] = sum(P(m["lon"], m["lat"])[0] for m in k["мосты"]) / len(k["мосты"])
            k["y0"] = sum(P(m["lon"], m["lat"])[1] for m in k["мосты"]) / len(k["мосты"])
            x, y = k["x0"], k["y0"]
            for п in порты:
                dx, dy = x - п["x"], y - п["y"]
                dist = math.hypot(dx / (п["rx"] + 16), dy / (п["ry"] + 16))
                if dist < 1.0:
                    ux, uy = (dx, dy) if math.hypot(dx, dy) > 1 else (-0.7, 0.7)
                    n = math.hypot(ux, uy)
                    ux, uy = ux / n, uy / n
                    t = 1.0 / math.hypot(ux / (п["rx"] + 16), uy / (п["ry"] + 16))
                    x, y = п["x"] + ux * t, п["y"] + uy * t
            k["x"], k["y"] = x, y
            k["шлюз"] = all(КОРОТКО.get(m["мост"], ("", ""))[1] == "шлюзы" for m in k["мосты"])
            ρ.занять((x - 13, y - 13, x + 13, y + 13))

    # подписи портов, потом мостов, потом рек
    for п in порты:
        п["подпись"] = Подпись(п["имя"], шрифт(int(КЕГЛЬ["порт"] * 0.8)) if п["ход"] else f_порт, **текст_порт)
        п["r"], п["выноска"] = ρ.место(п["подпись"].w, п["подпись"].h, п["x"], п["y"], п["rx"] + 2, п["ry"] + 2,
                                       сторона=СТОРОНА.get(п["имя"]))
    for k in знаки:
        k["подпись"] = Подпись(_строки_кластера(k["мосты"]), f_мост, **стиль["мост_текст"])
        k["r"], k["выноска"] = ρ.место(k["подпись"].w, k["подпись"].h, k["x"], k["y"], 13,
                                       сторона=СТОРОНА.get(k["мосты"][0]["мост"]) if len(k["мосты"]) == 1 else None)

    def на_пути(a, b):
        ia, ib = имена.index(a), имена.index(b)
        mx = 0.5 * (R.ПОРТЫ[ia]["lon"] + R.ПОРТЫ[ib]["lon"]); my = 0.5 * (R.ПОРТЫ[ia]["lat"] + R.ПОРТЫ[ib]["lat"])
        lon, lat = min(путь, key=lambda q: (q[0] - mx) ** 2 + (q[1] - my) ** 2)
        return P(lon, lat)
    реки = []
    for имя, (a, b) in (("Волга", ("Ульяновск", "Тетюши")), ("Кама", ("Чистополь", "Набережные Челны")),
                        ("Белая", ("Белая, ходовой день", "Уфа"))):
        x, y = на_пути(a, b)
        пд = Подпись(имя, f_река, **стиль["река"])
        r, _ = ρ.место(пд.w, пд.h, x, y, 22, выноска=False, зазор=4)
        реки.append((пд, r))

    # --- линии и значки (слой с запасом) ---
    od.line([tuple(S(*p)) for p in pts], fill=линия + (255,), width=стиль["ширина"] * SS, joint="curve")

    def выноска(x, y, rx, ry, r):
        tx, ty = min(max(x, r[0]), r[2]), min(max(y, r[1]), r[3])
        dx, dy = tx - x, ty - y
        n = math.hypot(dx, dy)
        if n < 1:
            return
        t = 1.0 / math.hypot(dx / n / (rx + 2), dy / n / (ry + 2))
        od.line(S(x + dx / n * t, y + dy / n * t, tx, ty), fill=стиль["выноска"] + (255,), width=int(1.5 * SS))
    for k in знаки:
        if k["выноска"]:
            выноска(k["x"], k["y"], 11, 11, k["r"])
        x, y = k["x"], k["y"]
        if k["шлюз"]:
            od.rectangle(S(x - 10, y - 10, x + 10, y + 10), fill=ЧЁРНЫЙ + (255,), outline=БЕЛЫЙ + (255,), width=2 * SS)
        else:
            od.polygon([tuple(S(x, y - 13)), tuple(S(x + 12, y + 9)), tuple(S(x - 12, y + 9))], fill=ЧЁРНЫЙ + (255,),
                       outline=БЕЛЫЙ + (255,), width=2 * SS)
    for п in порты:
        if п["выноска"]:
            выноска(п["x"], п["y"], п["rx"], п["ry"], п["r"])
        x, y, rx, ry = п["x"], п["y"], п["rx"], п["ry"]
        od.ellipse(S(x - rx, y - ry, x + rx, y + ry), fill=БЕЛЫЙ + (255,), outline=стиль["обвод"] + (255,), width=3 * SS)
    # легенда
    lx0, ly0, lx1, ly1 = лег_r
    od.rectangle(S(lx0, ly0, lx1, ly1), fill=БЕЛЫЙ + (255,), outline=ЧЁРНЫЙ + (255,), width=int(1.5 * SS))
    for i, (знак, _) in enumerate(легенда):
        cx, cy = lx0 + поле_л + знак_л / 2 - 6, ly0 + поле_л + i * шаг_л + КЕГЛЬ["легенда"] / 2 + 1
        if знак == "линия":
            od.line(S(cx - 26, cy, cx + 26, cy), fill=линия + (255,), width=стиль["ширина"] * SS)
        elif знак == "кружок":
            od.ellipse(S(cx - 18, cy - 18, cx + 18, cy + 18), fill=БЕЛЫЙ + (255,), outline=стиль["обвод"] + (255,), width=3 * SS)
        elif знак == "мост":
            od.polygon([tuple(S(cx, cy - 13)), tuple(S(cx + 12, cy + 9)), tuple(S(cx - 12, cy + 9))], fill=ЧЁРНЫЙ + (255,))
        else:
            od.rectangle(S(cx - 10, cy - 10, cx + 10, cy + 10), fill=ЧЁРНЫЙ + (255,))
    ov = ov.convert("RGBa").resize((W, H), Image.LANCZOS).convert("RGBA")
    лист = основа.convert("RGBA")
    лист.alpha_composite(ov)
    лист = лист.convert("RGB")

    # --- текст ---
    d = ImageDraw.Draw(лист)

    def по_центру(s, f, x, y, fill):
        l, t, r_, b = f.getbbox(s)
        d.text((x - (l + r_) / 2, y - (t + b) / 2), s, font=f, fill=fill)
    for п in порты:
        по_центру(п["лаб"], f_ном, п["x"], п["y"], ЧЁРНЫЙ)
        п["подпись"].нарисовать(d, п["r"])
    for k in знаки:
        k["подпись"].нарисовать(d, k["r"])
    for пд, r in реки:
        пд.нарисовать(d, r)
    for i, (знак, текст) in enumerate(легенда):
        cy = ly0 + поле_л + i * шаг_л + КЕГЛЬ["легенда"] / 2 + 1
        if знак == "кружок":
            по_центру("4", f_ном, lx0 + поле_л + знак_л / 2 - 6, cy, ЧЁРНЫЙ)
        a, dsc = f_лег.getmetrics()
        d.text((lx0 + поле_л + знак_л, cy + (a - dsc) / 2), текст, font=f_лег, fill=ЧЁРНЫЙ, anchor="ls")
    атр.нарисовать(d, атр_r, выровнять="right")
    return лист


def _сохранить(im, путь, палитра=False):
    """PNG по кириллическому пути - во временное имя и перенос, с повтором (запись иногда даёт EINVAL).
    палитра=True - 256 цветов: карта Яндекса из плоских заливок так же на вид, а файл втрое меньше."""
    os.makedirs(os.path.dirname(путь), exist_ok=True)
    if палитра:
        im = im.convert("P", palette=Image.ADAPTIVE, colors=256)
    tmp = путь + ".tmp.png"
    for попытка in range(4):
        try:
            im.save(tmp, optimize=True)
            os.replace(tmp, путь)
            return путь
        except OSError:
            if попытка == 3:
                raise
            time.sleep(0.5)
    return путь


#: Оформление: на спутнике - белые подписи с тёмной обводкой, на карте Яндекса - чёрные с белым гало.
СТИЛЬ_СПУТНИК = dict(линия=КРАСНЫЙ, обвод=КРАСНЫЙ, ширина=5, текст=БЕЛЫЙ, гало=(20, 20, 20), гало_w=2, выноска=БЕЛЫЙ,
                     мост_текст=dict(fill=БЕЛЫЙ, гало=(20, 20, 20), гало_w=2),
                     река=dict(fill=(190, 225, 255), гало=(20, 20, 20), гало_w=2),
                     атрибуция=dict(fill=БЕЛЫЙ, гало=(20, 20, 20), гало_w=1))
СТИЛЬ_КАРТА = dict(линия=ТЁМНО_КРАСНЫЙ, обвод=ТЁМНО_КРАСНЫЙ, ширина=5, текст=ЧЁРНЫЙ, гало=БЕЛЫЙ, гало_w=3, выноска=ЧЁРНЫЙ,
                   мост_текст=dict(fill=ЧЁРНЫЙ, гало=БЕЛЫЙ, гало_w=3),
                   река=dict(fill=СИНИЙ, гало=БЕЛЫЙ, гало_w=3),
                   атрибуция=dict(fill=(60, 60, 60), гало=БЕЛЫЙ, гало_w=2))


def карта(путь, плечи):
    """Первая карта - спутниковая подложка, маршрут и порты с номерами дней."""
    lons = [p[0] for p in путь] + [p["lon"] for p in R.ПОРТЫ]
    lats = [p[1] for p in путь] + [p["lat"] for p in R.ПОРТЫ]
    bbox = (min(lons) - 0.30, min(lats) - 0.12, max(lons) + 0.55, max(lats) + 0.14)
    img, px = подложка(bbox)
    img, P = _кадр(img, px, bbox, ШИРИНА_СПУТНИК)
    лист = _рисовать(img, P, путь, СТИЛЬ_СПУТНИК, мосты=False, атрибуция=АТРИБУЦИЯ)
    return _сохранить(лист, OUT_PNG)


def карта_схема(путь, плечи, пересчитать=False):
    """Вторая карта - скриншот Яндекс Карт (при сбое - OSM), маршрут, порты, мосты и шлюзы с высотами, легенда."""
    lons = [p[0] for p in путь] + [p["lon"] for p in R.ПОРТЫ] + [m["lon"] for m in R.МОСТЫ if "lon" in m]
    lats = [p[1] for p in путь] + [p["lat"] for p in R.ПОРТЫ] + [m["lat"] for m in R.МОСТЫ if "lat" in m]
    bbox = (min(lons) - 0.35, min(lats) - 0.10, max(lons) + 0.45, max(lats) + 0.16)
    атрибуция = АТРИБУЦИЯ_ЯНДЕКС
    try:
        img, px = подложка_яндекс(bbox, пересчитать=пересчитать)
    except Exception as e:
        print("Яндекс не снялся (%s), подложка OSM" % e)
        img, px = подложка(bbox, 10, "osm")
        атрибуция = АТРИБУЦИЯ_OSM
    img, P = _кадр(img, px, bbox)
    лист = _рисовать(img, P, путь, СТИЛЬ_КАРТА, мосты=True, атрибуция=атрибуция)
    return _сохранить(лист, OUT_PNG2, палитра=True)


def main(пересчитать=False):
    if пересчитать or not os.path.exists(OUT_GEO):
        путь, плечи = построить_путь()
    else:
        путь = R.путь()
        плечи = [(p["от"], p["до"], p["км"]) for p in R.плечи()]
    print("путь - %d точек, %d км" % (len(путь), sum(p[2] for p in плечи)))
    for a, b, k in плечи:
        print("  %-12s → %-12s %5d км" % (a, b, k))
    print(карта(путь, плечи))
    print(карта_схема(путь, плечи, пересчитать))


if __name__ == "__main__":
    main("--пересчитать" in sys.argv)
