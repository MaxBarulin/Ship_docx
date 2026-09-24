# -*- coding: utf-8 -*-
"""Лист проекта: виды, планы палуб, колесо, основные характеристики.

Вид простой, как лист, сверстанный вручную: белое поле, заголовок чёрным, тонкие серые линии,
без тёмных плашек. Числа из библиотек и с десятичной запятой, путей к файлам на листе нет.
"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from lib import gorizont as G, gorizont_hydro as HY, gorizont_ga as GA, gorizont_route as RT, gorizont_wheel as WH
EQ = HY.equilibrium()
_и = GA.итоги()
SUM = dict(pass_cabins=_и["пассажирских_кают"], passengers=_и["пассажиров"], crew_cabins=_и["кают_экипажа"], crew=_и["мест_экипажа"], accessible=_и["кают_М4"], onboard=_и["пассажиров"] + G.CREW)
STB = HY.stability_summary()
WC = HY.weather_criterion()
STR = __import__("lib.gorizont_strength", fromlist=["x"]).report()
SMAX = max(max(r["sigma_deck"], r["sigma_bot"]) for r in STR["stresses"]["rows"])
SALL = STR["stresses"]["sigma_allow"]
P22, P24 = HY.power(G.SPEED_KMH)["Pb"], HY.power(G.SPEED_MAX_KMH)["Pb"]
from PIL import ImageFont
F = r"C:\Windows\Fonts"
INK = (24, 34, 52)
INK2 = (86, 98, 120)
#: вне Windows (облачная сессия) - DejaVu Sans той же гарнитурной группы, чуть шире Segoe
_ЗАПАС = "/usr/share/fonts/truetype/dejavu"
def font(sz, b=False, l=False):
    n = "segoeuib.ttf" if b else ("segoeuil.ttf" if l else "segoeui.ttf")
    if os.path.exists(os.path.join(F, n)):
        return ImageFont.truetype(os.path.join(F, n), sz)
    return ImageFont.truetype(os.path.join(_ЗАПАС, "DejaVuSans-Bold.ttf" if b else "DejaVuSans.ttf"), int(sz * 0.92))
def з(x, nd=1):
    return ("%.*f" % (nd, x)).replace(".", ",")
ЛИНИЯ = (191, 191, 191)
def text(d, xy, s, f, fill=INK, anchor="la"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)
def tw(d, s, f):
    b = d.textbbox((0,0), s, font=f); return b[2]-b[0], b[3]-b[1]
ROOT_R = os.path.join(ROOT, "renders", "горизонт_2026")
from PIL import Image, ImageDraw

R = ROOT_R
W, H = 3400, 4160
img = Image.new("RGB",(W,H),(255,255,255))
d = ImageDraw.Draw(img)

text(d,(64,40), "Волжский Горизонт", font(72,b=True), INK)
text(d,(64,132), "Круизное судно для рек и озёр России", font(28), INK2)
d.line([64, 190, W-64, 190], fill=ЛИНИЯ, width=2)
right = [("%s × %s × %s м" % (з(G.LOA), з(G.BEAM), з(EQ["T"], 2)), "главные размерения"),
         ("%d / %d" % (SUM["pass_cabins"], SUM["passengers"]), "кают / мест пассажиров"),
         ("%d / %d" % (SUM["crew_cabins"], SUM["crew"]), "кают / мест экипажа"),
         ("2 + 1","жилые палубы и солнечная палуба")]
x = W-64
for t,s in reversed(right):
    w = max(tw(d,t,font(34,b=True))[0], tw(d,s,font(20))[0])
    text(d,(x, 58), t, font(34,b=True), INK, anchor="ra")
    text(d,(x, 106), s, font(20), INK2, anchor="ra")
    x -= w + 64

def put(path, box):
    if not os.path.exists(path):
        d.rectangle(box, outline=(220,224,232)); return
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        im = Image.alpha_composite(
            Image.new("RGBA", im.size, (255, 255, 255, 255)), im)
    im = im.convert("RGB")
    bw, bh = box[2]-box[0], box[3]-box[1]
    s = max(bw/im.width, bh/im.height)
    im = im.resize((int(im.width*s), int(im.height*s)), Image.LANCZOS)
    im = im.crop(((im.width-bw)//2, (im.height-bh)//2,
                  (im.width-bw)//2+bw, (im.height-bh)//2+bh))
    img.paste(im,(box[0],box[1]))

def fit(path, x, y, w):
    if not os.path.exists(path): return y
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        im = Image.alpha_composite(
            Image.new("RGBA", im.size, (255, 255, 255, 255)), im)
    im = im.convert("RGB")
    s = w/im.width
    im = im.resize((w, int(im.height*s)), Image.LANCZOS)
    img.paste(im,(x,y))
    return y + im.height

def cap(x,y,t,s=""):
    text(d,(x,y), t, font(26,b=True), INK)
    if s: text(d,(x,y+34), s, font(20), INK2)

put(os.path.join(R,"виды","01_общий_вид.jpg"), (64,232,1780,1224))
cap(64,1240,"Общий вид", "Чёрный корпус, два яруса тёмного стекла в светлой раме, колёса в портале на миделе")
put(os.path.join(R,"виды","02_борт.jpg"), (1812,232,3336,700))
cap(1812,716,"Борт")
put(os.path.join(R,"виды","04_нос_и_рубка.jpg"), (1812,790,2560,1224))
put(os.path.join(R,"виды","03_корма_и_колесо.jpg"), (2588,790,3336,1224))
cap(1812,1240,"Нос и рубка", "рубка стационарная - мосты маршрута от %s м" % з(RT.МОСТ_МИН))
cap(2588,1240,"Корма и колесо", "шарнирные плицы, портал, красная линия")

y = 1330
for p in ("2_главная","3_средняя","4_солнечная","1_трюм"):
    y = fit(os.path.join(R,"планы",p+".png"), 56, y, 1690) + 8

ys = fit(os.path.join(R,"виды","10_у_причала.jpg"), 1790, 1330, 1546) + 10
cap(1790, ys, "У причала порта приписки", "смена модуля портальным краном, трап и аппарель")
ys += 84
ys = fit(os.path.join(R,"схемы","01_колесо_шарнирное_и_радиальное.png"), 1790, ys, 1546) + 14

TX, TY = 1790, ys
TH = 740
d.rectangle([TX, TY, W-64, TY+TH], fill=(255,255,255), outline=ЛИНИЯ)
text(d,(TX+28, TY+18), "Основные характеристики", font(28,b=True), INK)
ROWS = [("Длина / ширина","%s / %s м" % (з(G.LOA), з(G.BEAM))),
        ("Осадка в полном грузу","%s м, водоизмещение %.0f т" % (з(EQ["T"], 2), EQ["D"])),
        ("Габаритная высота от ВЛ","%s м, рубка стационарная, мосты маршрута от %s м" % (з(G.AIR_DRAFT), з(RT.МОСТ_МИН))),
        ("Пассажиры","%d кают, %d мест" % (SUM["pass_cabins"], SUM["passengers"])),
        ("Каюты М4","%d, у лифтов" % SUM["accessible"]),
        ("Экипаж","%d каюты, %d мест" % (SUM["crew_cabins"], SUM["crew"])),
        ("Энергетика","%d × %d кВт ГДГ на метаноле, ГРЩ %d В, батарея %d кВт·ч, солнечные модули %.0f кВт"
         % (G.DG_COUNT, G.DG_POWER, G.SWITCHBOARD_V, G.BATTERY_KWH, G.SOLAR_KW)),
        ("Движители","%d гребных колеса Ø%s м с шарнирными плицами, ГЭД 2 × %d кВт, носовой водомёт %d кВт"
         % (G.WHEEL_COUNT, з(WH.DIAMETER, 2), G.WHEEL_MOTOR_POWER, G.THRUSTERS["носовой водомёт"]["kw"])),
        ("Скорость","%s км/ч - %.0f кВт, %s км/ч - %.0f кВт из %d кВт установленных"
         % (з(G.SPEED_KMH), P22, з(G.SPEED_MAX_KMH), P24, HY.PROP_POWER)),
        ("Цистерны","%d шт., %.0f м³, из них топливо %.0f м³ и пресная вода %.0f м³"
         % (len(G.TANKS), G.tank_summary()["vol"], G.FUEL_METHANOL_M3, G.FRESH_WATER_M3)),
        ("Автономность","%d суток" % G.AUTONOMY_DAYS),
        ("Остойчивость","h = %s м, критерий погоды %s при норме не менее 1,0" % (з(STB["h"], 2), з(WC["K"]))),
        ("Прочность корпуса","%s МПа из допускаемых %.0f, запас %s"
         % (з(SMAX), SALL, з(SALL / SMAX, 2))),
        ("Класс", "РКО %s" % G.RRR_CLASS),
        ("Спасательные средства","надувные плоты на %d человек на борту, спуск с обоих бортов" % SUM["onboard"])]
yy = TY+68
for k,v in ROWS:
    text(d,(TX+28, yy), k, font(22), INK2)
    text(d,(W-92, yy), v, font(22,b=True), INK, anchor="ra")
    yy += 42
    d.line([TX+28, yy-10, W-92, yy-10], fill=(217,217,217))

# интерьеры - в левой колонке под планами: справа после колеса и таблицы места нет
cy = y + 30
cap(56, cy, "Интерьеры кают", "люкс, стандарт и эконом, все шесть типов и их планировки - в пояснительной записке, раздел 2.3")
cx = 56; cw = (1690-2*18)//3
for p in ("люкс_1_от_входа", "стандарт_1_от_входа", "эконом_1_от_входа"):
    src = os.path.join(R, "каюты", p + ".jpg")
    if os.path.exists(src):
        im = Image.open(src).convert("RGB")
        s = cw/im.width
        im = im.resize((cw,int(im.height*s)), Image.LANCZOS)
        img.paste(im, (cx, cy + 84))
    cx += cw+18

d.line([64, H-70, W-64, H-70], fill=ЛИНИЯ, width=2)
text(d,(64,H-52), "УЖЦ ОСК 2026, «Волжский Горизонт». Чертежи ВГ-2026 ОР-01…08, расчёты РТ-01…09, узел ВГ-2026.46.00",
     font(20), INK2)
путь = os.path.join(R,"лист_проекта_горизонт.png")
img.save(путь + ".tmp.png")
os.replace(путь + ".tmp.png", путь)
print("ok", img.size)
