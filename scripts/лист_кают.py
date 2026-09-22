# -*- coding: utf-8 -*-
"""Лист интерьеров кают: шесть типов, по три кадра (от входа, от окна, план) и подпись
с площадью, местами и нормами эргономики. Собирается из renders/горизонт_2026/каюты/.

    python scripts/лист_кают.py
"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from PIL import Image, ImageDraw, ImageFont
from lib import gorizont_ga as GA, gorizont_cabin_layout as ПК, gorizont_style as S

R = os.path.join(ROOT, "renders", "горизонт_2026", "каюты")
F = r"C:\Windows\Fonts"
INK, INK2 = (24, 34, 52), (86, 98, 120)
ТИПЫ = ("люкс", "бизнес", "стандарт", "стандарт М4", "семейная", "эконом")


def font(sz, b=False):
    return ImageFont.truetype(os.path.join(F, "segoeuib.ttf" if b else "segoeui.ttf"), sz)


def main():
    W = 3400
    колонка = (W - 64 * 2 - 24 * 2) // 3
    выс = int(колонка * 850 / 1280)
    блок = выс + 150
    H = 210 + блок * len(ТИПЫ) + 70
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 196], fill=(18, 30, 48))
    d.text((64, 34), "ИНТЕРЬЕРЫ КАЮТ", font=font(66, True), fill=(255, 255, 255))
    d.text((64, 122), "«Волжский Горизонт» · шесть типов кают по расстановке планов (49 проверок эргономики по СанПиН 2.5.2-703-98) · "
            "отделка по классу: чем выше класс, тем дороже материалы · Blender Cycles", font=font(24), fill=(176, 190, 212))
    и = GA.итоги()
    y = 230
    for тип in ТИПЫ:
        к = GA.КАЮТЫ[тип]
        ф, гл, м = ПК.мебель(тип)
        n = sum(1 for c in GA.расстановка() if c["тип"] == тип)
        подпись = "%s — %.1f × %.2f м, %.1f м², %d мест, %s; в проекте %d кают" % (
            тип.capitalize(), ф, гл, ф * гл, к["мест"], "окно во всю ширину" if к["окно"] else "внутренняя, виртуальное окно", n)
        d.text((64, y), подпись, font=font(30, True), fill=INK)
        прим = к.get("примечание", "")
        норм = "койка 2,00 × 0,80; проход у койки ≥ %.2f м; дверь %.2f м; санузел ≥ %.1f × %.1f м; высота в свету 2,33 м" % (
            ПК.ПРОХОД[к["мест"]], ПК.ДВЕРЬ_М4 if к.get("М4") else ПК.ДВЕРЬ, ПК.САНУЗЕЛ_МИН[0], ПК.САНУЗЕЛ_МИН[1])
        отделка = "Отделка: " + S.ИНТЕРЬЕР[тип]["описание"] + ". "
        d.text((64, y + 42), отделка + (прим + ". " if прим else "") + норм, font=font(21), fill=INK2)
        x = 64
        for k, суф in enumerate(("1_от_входа", "2_от_окна", "3_план")):
            p = os.path.join(R, "%s_%s.jpg" % (тип.replace(" ", "_"), суф))
            if os.path.exists(p):
                im = Image.open(p).convert("RGB").resize((колонка, выс), Image.LANCZOS)
                img.paste(im, (x, y + 84))
            else:
                d.rectangle([x, y + 84, x + колонка, y + 84 + выс], outline=(220, 224, 232))
            d.text((x, y + 84 + выс + 8), ("от входа", "от окна", "план без подволока")[k], font=font(20), fill=INK2)
            x += колонка + 24
        y += блок
    d.rectangle([0, H - 64, W, H], fill=(18, 30, 48))
    d.text((64, H - 50), "scripts/blender_каюты.py · lib/gorizont_cabin_layout.py · планы/5_каюты.png — планировки с проверками", font=font(20), fill=(150, 168, 196))
    out = os.path.join(R, "00_лист_кают.png")
    img.save(out)
    print(out, img.size)


if __name__ == "__main__":
    main()
