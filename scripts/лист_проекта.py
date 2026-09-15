# -*- coding: utf-8 -*-
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
from PIL import ImageFont
F = r"C:\Windows\Fonts"
INK = (24, 34, 52)
INK2 = (86, 98, 120)
def font(sz, b=False, l=False):
    n = "segoeuib.ttf" if b else ("segoeuil.ttf" if l else "segoeui.ttf")
    return ImageFont.truetype(os.path.join(F, n), sz)
def text(d, xy, s, f, fill=INK, anchor="la"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)
def tw(d, s, f):
    b = d.textbbox((0,0), s, font=f); return b[2]-b[0], b[3]-b[1]
ROOT_R = os.path.join(ROOT, "renders", "горизонт_2026")
from PIL import Image, ImageDraw

R = ROOT_R
W, H = 3400, 3920
img = Image.new("RGB",(W,H),(255,255,255))
d = ImageDraw.Draw(img)

d.rectangle([0,0,W,196], fill=(18,30,48))
text(d,(64,34), "ВОЛЖСКИЙ ГОРИЗОНТ", font(72,b=True), (255,255,255))
text(d,(64,124), "Круизное судно для рек и озёр России · проект 2026 · команда УЖЦ ОСК",
     font(28), (176,190,212))
right = [("139.0 × 16.5 × 2.06 м","главные размерения"),
         ("106 / 212","кают / мест пассажиров"),
         ("31 / 57","кают / мест экипажа"),
         ("4 + 1","закрытых яруса и солнечная палуба")]
x = W-64
for t,s in reversed(right):
    w = max(tw(d,t,font(34,b=True))[0], tw(d,s,font(20))[0])
    text(d,(x, 48), t, font(34,b=True), (255,255,255), anchor="ra")
    text(d,(x, 96), s, font(20), (150,168,196), anchor="ra")
    x -= w + 64

def put(path, box):
    if not os.path.exists(path):
        d.rectangle(box, outline=(220,224,232)); return
    im = Image.open(path).convert("RGB")
    bw, bh = box[2]-box[0], box[3]-box[1]
    s = max(bw/im.width, bh/im.height)
    im = im.resize((int(im.width*s), int(im.height*s)), Image.LANCZOS)
    im = im.crop(((im.width-bw)//2, (im.height-bh)//2,
                  (im.width-bw)//2+bw, (im.height-bh)//2+bh))
    img.paste(im,(box[0],box[1]))

def fit(path, x, y, w):
    if not os.path.exists(path): return y
    im = Image.open(path).convert("RGB")
    s = w/im.width
    im = im.resize((w, int(im.height*s)), Image.LANCZOS)
    img.paste(im,(x,y))
    return y + im.height

def cap(x,y,t,s=""):
    text(d,(x,y), t, font(26,b=True), INK)
    if s: text(d,(x,y+34), s, font(20), INK2)

put(os.path.join(R,"виды","01_общий_вид.jpg"), (64,232,1780,1224))
cap(64,1240,"Общий вид", "Четыре закрытых яруса, шлюпки внутри габаритной ширины, солнечная палуба на крыше")
put(os.path.join(R,"виды","02_борт.jpg"), (1812,232,3336,700))
cap(1812,716,"Борт")
put(os.path.join(R,"виды","04_нос_и_рубка.jpg"), (1812,790,2560,1224))
put(os.path.join(R,"виды","05_шлюпочный_променад.jpg"), (2588,790,3336,1224))
cap(1812,1240,"Рубка и мачта", "мачта заваливается перед мостами")
cap(2588,1240,"Шлюпочный променад", "сквозной, 1.30 м, шлюпки на кильблоках")

y = 1330
for p in ("3_главная_палуба","4_верхняя_палуба","5_шлюпочная_палуба"):
    y = fit(os.path.join(R,"планы",p+".png"), 56, y, 1690) + 8

ys = fit(os.path.join(R,"схемы","продольный_разрез.png"), 1790, 1330, 1546) + 14
ys = fit(os.path.join(R,"схемы","судовые_системы.png"), 1790, ys, 1546) + 14

TX, TY = 1790, ys
TH = 700
d.rectangle([TX, TY, W-64, TY+TH], fill=(246,248,251), outline=(214,220,230))
text(d,(TX+28, TY+18), "Основные характеристики", font(28,b=True), INK)
ROWS = [("Длина / ширина","139.0 / 16.5 м"),
        ("Осадка в полном грузу","2.06 м, водоизмещение 3721 т"),
        ("Габаритная высота от ВЛ","13.2 м, мачта заваливается перед мостами"),
        ("Пассажиры","106 кают · 212 мест"),
        ("Каюты для маломобильных","8 в трёх категориях, у лифтов"),
        ("Экипаж","31 каюта · 57 мест"),
        ("Энергетика","4 × 1200 кВт ДГ, батарея 600 кВт·ч, 44 солнечных модуля"),
        ("Движители","2 винторулевые колонки 900 кВт, ПУ 300 кВт"),
        ("Скорость","22 км/ч при глубине от 8 м; максимум 24.3 км/ч"),
        ("Автономность","15 суток"),
        ("Остойчивость","h = 8.12 м, критерий погоды 13.6 при норме 1.0"),
        ("Прочность корпуса","152.6 МПа из допускаемых 195, запас 1.28"),
        ("Класс","РРР «О» (М-СП), Лед 1 / Arc 4"),
        ("Спасательные средства","6 шлюпок, 270 мест на каждый борт при 269 людях на борту")]
yy = TY+68
for k,v in ROWS:
    text(d,(TX+28, yy), k, font(22), INK2)
    text(d,(W-92, yy), v, font(22,b=True), INK, anchor="ra")
    yy += 42
    d.line([TX+28, yy-10, W-92, yy-10], fill=(226,231,238))

cy = TY+TH+26
cap(1790, cy, "Категории кают")
cx = 1790; cw = (W-64-1790-2*18)//3
for p in ("1_люкс_план","3_бизнес_план","7_эконом_план"):
    src = os.path.join(R,"каюты",p+".png")
    if os.path.exists(src):
        im = Image.open(src).convert("RGB")
        s = cw/im.width
        im = im.resize((cw,int(im.height*s)), Image.LANCZOS)
        img.paste(im,(cx, cy+56))
    cx += cw+18

d.rectangle([0,H-64,W,H], fill=(18,30,48))
text(d,(64,H-52), "blender/gorizont.blend · GLB/gorizont.glb · docs/проект/ · docs/расчёты/теория_корабля.md · renders/горизонт_2026/лист_расчётов_горизонт.png",
     font(20), (150,168,196))
img.save(os.path.join(R,"лист_проекта_горизонт.png"))
print("ok", img.size)
