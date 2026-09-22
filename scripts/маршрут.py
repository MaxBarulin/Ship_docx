# -*- coding: utf-8 -*-
"""Маршрут на спутниковой карте и путь по фарватеру для приложения.

    python scripts/маршрут.py              # маршрут.geojson + карты 04_маршрут.png (спутник) и 04а_маршрут_карта.png (Яндекс Карты с мостами и легендой)
    python scripts/маршрут.py --пересчитать

Порты и программа — `lib.gorizont_route`. Путь между портами прокладывается
по осевым линиям рек Natural Earth 10m (общественное достояние): линии Волги,
Камы и Белой склеиваются в граф, порты привязываются к ближайшей вершине
своей реки, между соседними портами ищется кратчайший путь по графу. Длина
плеч — по этому пути, а не по прямой.

Подложка — Sentinel-2 cloudless 2020 (EOX IT Services GmbH, CC BY 4.0,
содержит изменённые данные Copernicus Sentinel 2020), тайлы z = 9 кэшируются
в %LOCALAPPDATA%/gorizont_cache. Лист 16:9 под слайд: карта слева, программа
по дням справа. Подписи с обводкой, шрифт не мельче 28 px на 3840 — читаемость
проверяется глазами, как и остальные схемы.
"""
import os, sys, io, json, math, heapq, zipfile, tempfile, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from PIL import Image, ImageDraw, ImageFont
from lib import gorizont_route as R
from lib import gorizont as G

КЭШ = os.path.join(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()), "gorizont_cache")
os.makedirs(os.path.join(КЭШ, "tiles"), exist_ok=True)
NE_URL = "https://naciscdn.org/naturalearth/10m/physical/ne_10m_rivers_lake_centerlines.zip"
TILE_URL = "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2020_3857/default/g/%d/%d/%d.jpg"
#: Источники тайлов: имя → (шаблон URL, порядок подстановки, расширение, кэш-префикс)
ИСТОЧНИКИ = {"s2": (TILE_URL, "zyx", "jpg", "s2"),
             "osm": ("https://tile.openstreetmap.org/%d/%d/%d.png", "zxy", "png", "osm")}
АТРИБУЦИЯ = "Подложка: Sentinel-2 cloudless 2020 © EOX IT Services GmbH (CC BY 4.0), данные Copernicus Sentinel 2020. Реки: Natural Earth."
АТРИБУЦИЯ_OSM = "Подложка: © участники OpenStreetMap (ODbL). Реки: Natural Earth. Положение мостов и шлюзов — приближённое, высоты — по таблице маршрутной группы."
OUT_PNG = os.path.join(ROOT, "renders", "горизонт_2026", "схемы", "04_маршрут.png")
OUT_PNG2 = os.path.join(ROOT, "renders", "горизонт_2026", "схемы", "04а_маршрут_карта.png")
OUT_GEO = R.ФАЙЛ_ПУТИ
РЕКИ = {"Волга": ("Volga",), "Кама": ("Kama",), "Белая": ("Belaya",)}
F = r"C:\Windows\Fonts"
INK, ACC, WHITE, PANEL = (24, 34, 52), (200, 16, 46), (255, 255, 255), (18, 30, 48)
ZOOM = 9


def _скачать(url, путь):
    if not os.path.exists(путь):
        req = urllib.request.Request(url, headers={"User-Agent": "gorizont-route/1.0 (Ship_docx)"})
        open(путь, "wb").write(urllib.request.urlopen(req, timeout=120).read())
    return путь


def font(sz, b=False):
    return ImageFont.truetype(os.path.join(F, "segoeuib.ttf" if b else "segoeui.ttf"), sz)


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
    """Вершины — точки линий; рёбра — соседние точки; концы линий склеиваются с
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
    g = dict(type="FeatureCollection", name="Волжский Горизонт — маршрут Самара — Уфа — Самара", features=features)
    os.makedirs(os.path.dirname(OUT_GEO), exist_ok=True)
    json.dump(g, open(OUT_GEO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return весь, плечи


# --- карта ----------------------------------------------------------------------
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


def _перенос(d, текст, f, ширина):
    """Перенос по словам под заданную ширину в пикселях — подписи не режутся краем панели."""
    строки, тек = [], ""
    for s in текст.split():
        проба = (тек + " " + s).strip()
        if тек and d.textlength(проба, font=f) > ширина:
            строки.append(тек); тек = s
        else:
            тек = проба
    if тек:
        строки.append(тек)
    return строки


def карта(путь, плечи):
    lons = [p[0] for p in путь] + [p["lon"] for p in R.ПОРТЫ]
    lats = [p[1] for p in путь] + [p["lat"] for p in R.ПОРТЫ]
    bbox = (min(lons) - 0.6, min(lats) - 0.35, max(lons) + 0.6, max(lats) + 0.35)
    img, px = подложка(bbox)
    # обрезка по bbox
    x0, y1 = px(bbox[0], bbox[1]); x1, y0 = px(bbox[2], bbox[3])
    img = img.crop((int(x0), int(y0), int(x1), int(y1)))
    ox, oy = int(x0), int(y0)
    d = ImageDraw.Draw(img)
    pts = [(px(lon, lat)[0] - ox, px(lon, lat)[1] - oy) for lon, lat in путь]
    d.line(pts, fill=WHITE, width=13, joint="curve")
    d.line(pts, fill=ACC, width=7, joint="curve")
    # порты; ходовой день — полый кружок без имени
    for p in R.ПОРТЫ:
        x, y = px(p["lon"], p["lat"]); x -= ox; y -= oy
        if p.get("ход"):
            f = font(26, True); лаб = "%d" % p["день"]; w = d.textlength(лаб, font=f)
            d.ellipse([x - 22, y - 22, x + 22, y + 22], fill=(18, 30, 48), outline=WHITE, width=4)
            d.text((x - w / 2, y - 17), лаб, font=f, fill=WHITE)
            continue
        лаб = "%d" % p["день"] if not p.get("стоянка", 1) > 1 else "%d–%d" % (p["день"], p["день"] + p["стоянка"] - 1)
        f = font(26, True)
        w = d.textlength(лаб, font=f)
        r = max(24, int(w / 2) + 12)               # кружок по ширине подписи: «9–10» шире «4»
        d.ellipse([x - r, y - r, x + r, y + r], fill=WHITE, outline=ACC, width=5)
        d.text((x - w / 2, y - 17), лаб, font=f, fill=INK)
        имя = p["порт"]
        f2 = font(34, True)
        tx, ty = x + r + 10, y - 20
        for dx in (-2, 2):
            for dy in (-2, 2):
                d.text((tx + dx, ty + dy), имя, font=f2, fill=(0, 0, 0))
        d.text((tx, ty), имя, font=f2, fill=WHITE)
    # лист 16:9: карта слева, программа справа
    W, H = 3840, 2160
    панель = 1180
    карт_w = W - панель
    sc = min(карт_w / img.width, H / img.height)
    m = img.resize((int(img.width * sc), int(img.height * sc)), Image.LANCZOS)
    лист = Image.new("RGB", (W, H), PANEL)
    лист.paste(m, (0, (H - m.height) // 2))
    d = ImageDraw.Draw(лист)
    # шапка на карте
    d.rectangle([0, 0, карт_w, 130], fill=(18, 30, 48))
    d.text((40, 28), "«Волжский Горизонт» · маршрут Самара — Казань — Уфа — Самара", font=font(56, True), fill=WHITE)
    d.text((40, 96), "Волга · Кама · Белая  ·  %d дней  ·  %d км по фарватеру  ·  самый низкий мост %s м  ·  осадка 1,26 м"
           % (R.ДНЕЙ, sum(p[2] for p in плечи), ("%.1f" % R.МОСТ_МИН).replace(".", ",")), font=font(30), fill=(176, 190, 212))
    # программа
    x, y = карт_w + 50, 40
    d.text((x, y), "ПРОГРАММА ТУРА", font=font(44, True), fill=WHITE); y += 80
    рп = {r["порт"] + str(r["день"]): r for r in R.расписание()}
    for p in R.ПОРТЫ:
        дн = "День %d" % p["день"] if p.get("стоянка", 1) == 1 else "Дни %d–%d" % (p["день"], p["день"] + p["стоянка"] - 1)
        if p.get("ход"):
            дн = "День %d" % p["день"]
        r = рп[p["порт"] + str(p["день"])]
        часы = " · ".join(s for s in (("приход " + r["приход_чч"]) if r["приход_чч"] else "", ("отход " + r["отход_чч"]) if r["отход_чч"] else "") if s)
        d.text((x, y), дн, font=font(26), fill=(176, 190, 212))
        d.text((x + 190, y - 4), p["порт"], font=font(34, True), fill=WHITE)
        y += 44
        # программа в две строки максимум
        ширина = панель - 50 - 190 - 30            # от начала текста до края панели
        for s in _перенос(d, p["программа"], font(24), ширина)[:2]:
            d.text((x + 190, y), s, font=font(24), fill=(210, 218, 230)); y += 32
        if часы:
            d.text((x + 190, y), часы, font=font(21), fill=(150, 168, 196)); y += 28
        y += 10
    низкие = sorted([m for m in R.МОСТЫ if m["высота"] is not None], key=lambda m: m["высота"])[:6]
    мосты_текст = "Самые низкие мосты, м: " + "; ".join("%s %s" % (m["мост"], ("%.1f" % m["высота"]).replace(".", ",")) for m in низкие) \
        + "; габарит судна %s м" % ("%.1f" % G.AIR_DRAFT).replace(".", ",")
    плечи_текст = "Плечи по фарватеру, км: " + "; ".join("%s → %s %d" % (a, b, k) for a, b, k in плечи)
    yy = H - 230
    for s in _перенос(d, мосты_текст, font(20), панель - 80)[:3]:
        d.text((x, yy), s, font=font(20), fill=(230, 200, 150)); yy += 27
    yy += 8
    for s in _перенос(d, плечи_текст, font(20), панель - 80)[:4]:
        d.text((x, yy), s, font=font(20), fill=(150, 168, 196)); yy += 27
    d.text((40, H - 40), АТРИБУЦИЯ, font=font(20), fill=(230, 230, 230))
    os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
    лист.save(OUT_PNG)
    return OUT_PNG


def _стрелка(d, p0, p1, размер, fill):
    """Стрелка направления хода на линии: треугольник в точке p1, смотрящий от p0."""
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    tip = p1
    a = (tip[0] - размер * math.cos(ang - 0.5), tip[1] - размер * math.sin(ang - 0.5))
    b = (tip[0] - размер * math.cos(ang + 0.5), tip[1] - размер * math.sin(ang + 0.5))
    d.polygon([tip, a, b], fill=fill)


def _обводка(d, xy, текст, f, fill, halo=(255, 255, 255), w=3):
    for dx in range(-w, w + 1, w):
        for dy in range(-w, w + 1, w):
            if dx or dy:
                d.text((xy[0] + dx, xy[1] + dy), текст, font=f, fill=halo)
    d.text(xy, текст, font=f, fill=fill)


#: Подложка второй карты — скриншот Яндекс Карт (решение пользователя 22.09.2026: скриншоты Яндекса
#: допустимы, тайлы Google — нет). Снимается настоящим Chrome через Playwright (headless Яндекс отдаёт
#: страницу «limited»), кэшируется в gorizont_cache; проекция Яндекса — EPSG:3395, эллипсоид.
ЯНДЕКС_Z = 9
ЯНДЕКС_E = 0.0818191908426
АТРИБУЦИЯ_ЯНДЕКС = "Подложка: скриншот Яндекс Карт, © Яндекс. Реки: Natural Earth. Положение мостов и шлюзов — приближённое, высоты — по таблице маршрутной группы."


def _меркатор_3395(lon, lat, z):
    n = 256 * 2 ** z
    x = (lon + 180.0) / 360.0 * n
    f = math.radians(lat)
    m = math.tan(math.pi / 4 + f / 2) * ((1 - ЯНДЕКС_E * math.sin(f)) / (1 + ЯНДЕКС_E * math.sin(f))) ** (ЯНДЕКС_E / 2)
    y = (0.5 - math.log(m) / (2 * math.pi)) * n
    return x, y


def подложка_яндекс(bbox, z=ЯНДЕКС_Z, пересчитать=False):
    """Скриншот карты Яндекса под bbox: центр — середина bbox, размер контейнера — по охвату плюс поле.
    Возвращает (img, px), как подложка()."""
    from playwright.sync_api import sync_playwright
    lon0, lat0, lon1, lat1 = bbox
    x0, y1 = _меркатор_3395(lon0, lat0, z)
    x1, y0 = _меркатор_3395(lon1, lat1, z)
    W = min(4000, int(x1 - x0) + 120)
    H = min(2700, int(y1 - y0) + 120)
    cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    # центр контейнера в градусах — обратная проекция по x прямая, по y подбором
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
                                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
            ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
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


def _стрелка(d, p0, p1, размер, fill):
    """Стрелка направления хода на линии: треугольник в точке p1, смотрящий от p0."""
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    tip = p1
    a = (tip[0] - размер * math.cos(ang - 0.5), tip[1] - размер * math.sin(ang - 0.5))
    b = (tip[0] - размер * math.cos(ang + 0.5), tip[1] - размер * math.sin(ang + 0.5))
    d.polygon([tip, a, b], fill=fill)


def _обводка(d, xy, текст, f, fill, halo=(255, 255, 255), w=3):
    for dx in range(-w, w + 1, w):
        for dy in range(-w, w + 1, w):
            if dx or dy:
                d.text((xy[0] + dx, xy[1] + dy), текст, font=f, fill=halo)
    d.text(xy, текст, font=f, fill=fill)


def _пересек(a, b, зазор=6):
    return not (a[2] + зазор < b[0] or b[2] + зазор < a[0] or a[3] + зазор < b[1] or b[3] + зазор < a[1])


ГРАНИЦЫ = None   # (x0, y0, x1, y1) области карты на листе — подписи не выводятся за неё


def _площадь_пересечения(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0]); h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def _разместить(занято, w, h, x, y, кандидаты):
    """Кандидат сдвига (dx, dy) с наименьшим перекрытием занятых прямоугольников; выход за границы
    карты считается перекрытием. К заданным кандидатам добавляются дальние варианты по восьми сторонам."""
    доп = [(40, -h - 40), (-w - 40, -h - 40), (40, 40), (-w - 40, 40), (-w / 2, -h - 60), (-w / 2, 60), (60, -h / 2), (-w - 60, -h / 2)]
    лучший, цена_лучшего = None, None
    for dx, dy in list(кандидаты) + доп:
        r = (x + dx, y + dy, x + dx + w, y + dy + h)
        цена = sum(_площадь_пересечения(r, z) for z in занято)
        if ГРАНИЦЫ is not None:
            вне = w * h - _площадь_пересечения(r, ГРАНИЦЫ)
            цена += 4.0 * вне
        if цена_лучшего is None or цена < цена_лучшего - 1e-6:
            лучший, цена_лучшего = r, цена
            if цена == 0:
                break
    занято.append(лучший)
    return лучший


def карта_схема(путь, плечи, пересчитать=False):
    """Вторая карта — картографическая подложка (Яндекс Карты скриншотом, при сбое — OSM),
    маршрут со стрелками хода, порты с расписанием, мосты и шлюзы с высотами, реки, легенда на карте."""
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
    x0, y1 = px(bbox[0], bbox[1]); x1, y0 = px(bbox[2], bbox[3])
    x0, y0 = max(0, int(x0)), max(0, int(y0)); x1, y1 = min(img.width, int(x1)), min(img.height, int(y1))
    img = img.crop((x0, y0, x1, y1))
    ox, oy = x0, y0
    W, H = 3840, 2160
    ШАПКА, ПОДВАЛ = 120, 36
    sc = min(W / img.width, (H - ШАПКА - ПОДВАЛ) / img.height)
    img = img.resize((int(img.width * sc), int(img.height * sc)), Image.LANCZOS)
    лист = Image.new("RGB", (W, H), (226, 232, 238))
    offx, offy = (W - img.width) // 2, ШАПКА + (H - ШАПКА - ПОДВАЛ - img.height) // 2
    лист.paste(img, (offx, offy))
    global ГРАНИЦЫ
    ГРАНИЦЫ = (offx, offy, offx + img.width, offy + img.height)
    d = ImageDraw.Draw(лист, "RGBA")

    def P(lon, lat):
        x, y = px(lon, lat)
        return ((x - ox) * sc + offx, (y - oy) * sc + offy)
    занято = [(W - 40 - 900, H - 44 - 470, W - 40, H - 44), (W - 40 - 760, 150, W - 40, 150 + 60 + 34 * len(R.расписание()) + 20)]
    # маршрут и стрелки направления
    pts = [P(lon, lat) for lon, lat in путь]
    d.line(pts, fill=WHITE, width=15, joint="curve")
    d.line(pts, fill=ACC, width=8, joint="curve")
    шаг = max(1, len(pts) // 18)
    for i in range(шаг, len(pts) - 1, шаг):
        _стрелка(d, pts[i - 1], pts[i], 26, WHITE)
        _стрелка(d, pts[i - 1], pts[i], 18, ACC)
    # реки — у середин характерных плеч
    def середина(a, b):
        ia = next(i for i, p in enumerate(R.ПОРТЫ) if p["порт"] == a); ib = next(i for i, p in enumerate(R.ПОРТЫ) if p["порт"] == b)
        return P(0.5 * (R.ПОРТЫ[ia]["lon"] + R.ПОРТЫ[ib]["lon"]), 0.5 * (R.ПОРТЫ[ia]["lat"] + R.ПОРТЫ[ib]["lat"]))
    f_r = font(40, True)
    реки = [("ВОЛГА", середина("Ульяновск", "Тетюши")), ("КАМА", середина("Чистополь", "Набережные Челны")), ("БЕЛАЯ", середина("Белая, ходовой день", "Уфа"))]
    # порты: сначала резервируем место под все маркеры и подписи, потом мосты, потом порты поверх
    рп = {r["порт"] + str(r["день"]): r for r in R.расписание()}
    f_n, f_h, f_l = font(36, True), font(22), font(26, True)
    имена = [p["порт"] for p in R.ПОРТЫ]
    порты = []
    for i, p in enumerate(R.ПОРТЫ):
        x, y = P(p["lon"], p["lat"])
        if p.get("ход"):
            порты.append(dict(x=x, y=y, r=22, ход=True, лаб="%d" % p["день"]))
            занято.append((x - 24, y - 24, x + 24, y + 24))
            continue
        if p["порт"] in имена[i + 1:]:
            continue                                   # тот же порт ещё встретится (Самара: посадка и высадка)
        лаб = "%d" % p["день"] if not p.get("стоянка", 1) > 1 else "%d–%d" % (p["день"], p["день"] + p["стоянка"] - 1)
        r_ = рп[p["порт"] + str(p["день"])]
        часы = " · ".join(s for s in ((r_["приход_чч"].replace("день ", "д") if r_["приход_чч"] else ""), ("отх. " + r_["отход_чч"].replace("день ", "д")) if r_["отход_чч"] else "") if s)
        if p["порт"] in имена[:i]:
            первый = R.ПОРТЫ[имена.index(p["порт"])]
            лаб = "%d/%s" % (первый["день"], лаб)
            r0 = рп[p["порт"] + str(первый["день"])]
            часы = "отх. %s · приход %s" % (r0["отход_чч"].replace("день ", "д"), r_["приход_чч"].replace("день ", "д"))
        w = d.textlength(лаб, font=f_l)
        r = max(24, int(w / 2) + 12)
        порты.append(dict(x=x, y=y, r=r, ход=False, лаб=лаб, имя=p["порт"], часы=часы))
        занято.append((x - r, y - r, x + r, y + r))
    for п in порты:
        if п["ход"]:
            continue
        tw = max(d.textlength(п["имя"], font=f_n), d.textlength(п["часы"], font=f_h))
        r = п["r"]
        п["rect"] = _разместить(занято, tw, 78, п["x"], п["y"], [(r + 12, -24), (r + 12, -70), (-tw - r - 12, -24), (-tw - r - 12, -70), (-tw / 2, r + 8), (-tw / 2, -r - 86)])
    # мосты и шлюзы: кластеры по близости, маркер отодвигается от маркера порта, одна подпись на кластер
    мосты = [m for m in R.МОСТЫ if "lat" in m]
    кластеры = []
    for m in мосты:
        x, y = P(m["lon"], m["lat"])
        for k in кластеры:
            if math.hypot(k["x"] - x, k["y"] - y) < 70:
                k["мосты"].append(m); break
        else:
            кластеры.append(dict(x=x, y=y, мосты=[m]))
    f_m = font(24, True)
    for k in кластеры:
        x, y = k["x"], k["y"]
        for п in порты:
            dist = math.hypot(п["x"] - x, п["y"] - y)
            if dist < п["r"] + 30:
                ux, uy = ((x - п["x"]) / dist, (y - п["y"]) / dist) if dist > 1 else (-0.7, 0.7)
                x, y = п["x"] + ux * (п["r"] + 34), п["y"] + uy * (п["r"] + 34)
        низкий = any(m["высота"] is not None and m["высота"] < 14.0 for m in k["мосты"])
        цвет = (150, 20, 40) if низкий else (20, 70, 140)
        if any("Шлюз" in m["мост"] for m in k["мосты"]):
            d.rectangle([x - 16, y - 16, x + 16, y + 16], fill=цвет, outline=WHITE, width=4)
        else:
            d.polygon([(x, y - 22), (x + 22, y), (x, y + 22), (x - 22, y)], fill=цвет, outline=WHITE)
        занято.append((x - 24, y - 24, x + 24, y + 24))
        строки = []
        for m in k["мосты"]:
            имя = m["мост"].split(" (")[0].replace("Мост М-12 «Восток» через ", "М-12, ").replace("железнодорожный", "ж.-д.")
            h = ("%s м" % ("%.1f" % m["высота"]).replace(".", ",")) if m["высота"] is not None else "разводной"
            строки.append("%s — %s" % (имя, h))
        tw = max(d.textlength(s, font=f_m) for s in строки); th = 30 * len(строки)
        rect = _разместить(занято, tw, th, x, y, [(30, -14), (30, 20), (-tw - 30, -14), (-tw - 30, 20), (-tw / 2, 30), (-tw / 2, -th - 30)])
        for i, s in enumerate(строки):
            _обводка(d, (rect[0], rect[1] + 30 * i), s, f_m, цвет, w=3)
    # порты поверх мостов
    for п in порты:
        x, y, r = п["x"], п["y"], п["r"]
        if п["ход"]:
            d.ellipse([x - 22, y - 22, x + 22, y + 22], fill=(18, 30, 48), outline=WHITE, width=4)
            w = d.textlength(п["лаб"], font=f_l)
            d.text((x - w / 2, y - 17), п["лаб"], font=f_l, fill=WHITE)
            continue
        d.ellipse([x - r, y - r, x + r, y + r], fill=WHITE, outline=ACC, width=5)
        w = d.textlength(п["лаб"], font=f_l)
        d.text((x - w / 2, y - 17), п["лаб"], font=f_l, fill=INK)
        _обводка(d, (п["rect"][0], п["rect"][1]), п["имя"], f_n, INK, w=4)
        _обводка(d, (п["rect"][0], п["rect"][1] + 44), п["часы"], f_h, (60, 70, 90), w=3)
    for имя, (x, y) in реки:
        tw = d.textlength(имя, font=f_r)
        rect = _разместить(занято, tw, 48, x, y, [(-tw - 60, -24), (60, -24), (-tw / 2, 50), (-tw / 2, -100)])
        _обводка(d, (rect[0], rect[1]), имя, f_r, (20, 70, 140), w=4)
    # шапка
    d.rectangle([0, 0, W, 120], fill=(18, 30, 48, 235))
    d.text((40, 22), "«Волжский Горизонт» · маршрут Самара — Казань — Уфа — Самара · карта с мостами и шлюзами", font=font(52, True), fill=WHITE)
    d.text((40, 84), "Волга · Кама · Белая  ·  %d дней  ·  %d км по фарватеру  ·  самый низкий мост %s м при габарите судна %s м  ·  осадка 1,26 м"
           % (R.ДНЕЙ, sum(p[2] for p in плечи), ("%.1f" % R.МОСТ_МИН).replace(".", ","), ("%.1f" % G.AIR_DRAFT).replace(".", ",")), font=font(28), fill=(176, 190, 212))
    # легенда — справа внизу
    lw, lh = 900, 470
    lx, ly = W - 40 - lw, H - 44 - lh
    d.rectangle([lx, ly, lx + lw, ly + lh], fill=(255, 255, 255, 228), outline=(18, 30, 48), width=3)
    d.text((lx + 24, ly + 16), "ЛЕГЕНДА", font=font(34, True), fill=INK)
    y = ly + 74
    d.line([(lx + 30, y + 14), (lx + 110, y + 14)], fill=WHITE, width=15); d.line([(lx + 30, y + 14), (lx + 110, y + 14)], fill=ACC, width=8)
    _стрелка(d, (lx + 80, y + 14), (lx + 112, y + 14), 20, ACC)
    d.text((lx + 130, y), "путь по фарватеру, стрелка — направление хода", font=font(26), fill=INK); y += 52
    d.ellipse([lx + 46, y - 4, lx + 94, y + 44], fill=WHITE, outline=ACC, width=5); d.text((lx + 62, y + 3), "4", font=f_l, fill=INK)
    d.text((lx + 130, y), "стоянка с программой, число — день круиза (6–7 — двое суток)", font=font(26), fill=INK); y += 52
    d.ellipse([lx + 48, y - 2, lx + 92, y + 42], fill=(18, 30, 48), outline=WHITE, width=4); d.text((lx + 63, y + 3), "8", font=f_l, fill=WHITE)
    d.text((lx + 130, y), "ходовой день без стоянки", font=font(26), fill=INK); y += 52
    d.polygon([(lx + 70, y - 2), (lx + 92, y + 20), (lx + 70, y + 42), (lx + 48, y + 20)], fill=(150, 20, 40), outline=WHITE)
    d.text((lx + 130, y), "мост с высотой прохода ниже 14 м", font=font(26), fill=INK); y += 52
    d.polygon([(lx + 70, y - 2), (lx + 92, y + 20), (lx + 70, y + 42), (lx + 48, y + 20)], fill=(20, 70, 140), outline=WHITE)
    d.text((lx + 130, y), "мост от 14 м или разводной", font=font(26), fill=INK); y += 52
    d.rectangle([lx + 54, y + 4, lx + 86, y + 36], fill=(20, 70, 140), outline=WHITE, width=4)
    d.text((lx + 130, y), "шлюзы ГЭС (высота прохода у подписи)", font=font(26), fill=INK); y += 52
    d.text((lx + 24, y + 4), "приход и отход у порта — расписание gorizont_route.расписание();", font=font(22), fill=(60, 70, 90)); y += 30
    d.text((lx + 24, y + 4), "против течения до Уфы, по течению обратно; шлюзы 290 × 30 м", font=font(22), fill=(60, 70, 90))
    # расписание — справа вверху
    строки = R.расписание()
    tw, th = 760, 60 + 34 * len(строки) + 20
    tx, ty = W - 40 - tw, 150
    d.rectangle([tx, ty, tx + tw, ty + th], fill=(255, 255, 255, 228), outline=(18, 30, 48), width=3)
    d.text((tx + 24, ty + 14), "ДЕНЬ · ПОРТ · ПРИХОД · ОТХОД", font=font(28, True), fill=INK)
    yy = ty + 62
    for r in строки:
        p = next(p_ for p_ in R.ПОРТЫ if p_["порт"] == r["порт"] and p_["день"] == r["день"])
        дн = "%d" % r["день"] if p.get("стоянка", 1) == 1 else "%d–%d" % (r["день"], r["день"] + p["стоянка"] - 1)
        d.text((tx + 24, yy), дн, font=font(24, True), fill=INK)
        d.text((tx + 100, yy), r["порт"], font=font(24), fill=INK)
        d.text((tx + 420, yy), r["приход_чч"].replace("день ", "д"), font=font(24), fill=(60, 70, 90))
        d.text((tx + 600, yy), r["отход_чч"].replace("день ", "д"), font=font(24), fill=(60, 70, 90))
        yy += 34
    d.rectangle([0, H - 36, W, H], fill=(18, 30, 48, 220))
    d.text((40, H - 32), атрибуция, font=font(20), fill=(230, 230, 230))
    os.makedirs(os.path.dirname(OUT_PNG2), exist_ok=True)
    лист.save(OUT_PNG2)
    return OUT_PNG2


def main(пересчитать=False):
    if пересчитать or not os.path.exists(OUT_GEO):
        путь, плечи = построить_путь()
    else:
        путь = R.путь()
        плечи = [(p["от"], p["до"], p["км"]) for p in R.плечи()]
    print("путь: %d точек, %d км" % (len(путь), sum(p[2] for p in плечи)))
    for a, b, k in плечи:
        print("  %-12s → %-12s %5d км" % (a, b, k))
    print(карта(путь, плечи))
    print(карта_схема(путь, плечи, пересчитать))


if __name__ == "__main__":
    main("--пересчитать" in sys.argv)
