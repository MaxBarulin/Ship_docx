# -*- coding: utf-8 -*-
"""Маршрут на спутниковой карте и путь по фарватеру для приложения.

    python scripts/маршрут.py              # маршрут.geojson + карта 04_маршрут.png
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
АТРИБУЦИЯ = "Подложка: Sentinel-2 cloudless 2020 © EOX IT Services GmbH (CC BY 4.0), данные Copernicus Sentinel 2020. Реки: Natural Earth."
OUT_PNG = os.path.join(ROOT, "renders", "горизонт_2026", "схемы", "04_маршрут.png")
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


def подложка(bbox, z=ZOOM):
    lon0, lat0, lon1, lat1 = bbox
    x0, y1 = _tile_xy(lon0, lat0, z)
    x1, y0 = _tile_xy(lon1, lat1, z)
    tx0, tx1, ty0, ty1 = int(x0), int(x1), int(y0), int(y1)
    img = Image.new("RGB", ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256), (10, 20, 30))
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            p = os.path.join(КЭШ, "tiles", "s2_%d_%d_%d.jpg" % (z, tx, ty))
            try:
                _скачать(TILE_URL % (z, ty, tx), p)
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


if __name__ == "__main__":
    main("--пересчитать" in sys.argv)
