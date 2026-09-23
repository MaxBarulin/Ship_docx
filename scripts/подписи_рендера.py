# -*- coding: utf-8 -*-
"""Подписи поверх рендера. Выноски от точек модели к подписям - в 2D, а не 3D-текстом в сцене.

    python scripts/подписи_рендера.py <рендер.png> <якоря.json> <выход.jpg>

Зачем. 3D-текст в сцене взрыв-схем закрывался деталями (колесо резало подпись
«72 фундамента-замка»), терялся белым по светлому корпусу, отражался в воде и
не совпадал по высоте со своей сборкой. Теперь Blender рендерит картинку без
текста и пишет рядом JSON с экранными координатами точек, к которым относится
подпись (`bpy_extras.object_utils.world_to_camera_view`), а подписи рисуются
здесь - всегда поверх, в белой прямоугольной рамке, с выноской до своей точки.

Вид простой, как выноски в PowerPoint или Word: Calibri, тонкая чёрная рамка без
скруглений, чёрные точки. Заголовка на кадре нет - название даёт подпись «Рисунок N»
в документе, поля «заголовок» и «подзаголовок» в JSON больше не рисуются.

Формат якорей - {"стиль" - "сборки" | "позиции", "заголовок" - "...", "подзаголовок" - "...",
"якоря" - [{"текст" - "...", "x" - px, "y" - px}, ...]}, x, y - пиксели рендера, y сверху.

* «сборки» - подписи столбцом у правого края, по порядку высоты точек, без наложений;
  выноска от точки на сборке до плашки.
* «позиции» - номера позиций в кружках (как на сборочном чертеже), кружок выносится
  от центра узла наружу, место подбирается без наложений на другие кружки.
"""
import os, sys, json, math
from PIL import Image, ImageDraw, ImageFont

INK, BG = (0, 0, 0), (255, 255, 255)


def _шрифт(px, жирный=False):
    for имя in (("calibrib.ttf" if жирный else "calibri.ttf"), ("DejaVuSans-Bold.ttf" if жирный else "DejaVuSans.ttf")):
        for d in (r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu"):
            p = os.path.join(d, имя)
            if os.path.exists(p):
                return ImageFont.truetype(p, px)
    return ImageFont.load_default()


def _пересек(a, b, зазор=8):
    return not (a[2] + зазор < b[0] or b[2] + зазор < a[0] or a[3] + зазор < b[1] or b[3] + зазор < a[1])


def _строки(d, текст, f, ширина):
    """Перенос по словам под ширину в пикселях."""
    out, тек = [], ""
    for s in текст.split():
        проба = (тек + " " + s).strip()
        if тек and d.textlength(проба, font=f) > ширина:
            out.append(тек); тек = s
        else:
            тек = проба
    if тек:
        out.append(тек)
    return out


def _сборки(img, d, якоря, W, H):
    """Столбец плашек у правого края (30 % ширины кадра), по порядку высоты точек, без наложений."""
    f = _шрифт(max(26, W // 80))
    pad = 12
    колонка = int(W * 0.30)
    x0 = W - 40 - колонка
    строки = [_строки(d, a["текст"], f, колонка - 2 * pad) for a in якоря]
    шаг = int(f.size * 1.25)
    hs = [len(с) * шаг + 2 * pad for с in строки]
    порядок = sorted(range(len(якоря)), key=lambda i: якоря[i]["y"])
    ys, низ = {}, 150 - 1e9
    for i in порядок:
        y = max(якоря[i]["y"] - hs[i] / 2, низ + 16, 150)
        ys[i] = y
        низ = y + hs[i]
    сдвиг = max(0.0, низ - (H - 30))
    for i in ys:
        ys[i] -= сдвиг
    for i, a in enumerate(якоря):
        y, h = ys[i], hs[i]
        ax, ay = a["x"], a["y"]
        # выноска: от точки к левому краю плашки, излом на уровне её середины
        d.line([(ax, ay), (x0 - 30, y + h / 2), (x0, y + h / 2)], fill=INK, width=2)
        d.ellipse([ax - 6, ay - 6, ax + 6, ay + 6], fill=INK)
        wmax = max(d.textlength(s, font=f) for s in строки[i])
        d.rectangle([x0, y, x0 + wmax + 2 * pad, y + h], fill=BG, outline=INK, width=2)
        for k, s in enumerate(строки[i]):
            d.text((x0 + pad, y + pad - 2 + k * шаг), s, font=f, fill=INK)


def _позиции(img, d, якоря, W, H):
    f = _шрифт(max(24, W // 70), True)
    r = int(f.size * 0.95)
    cx = sum(a["x"] for a in якоря) / len(якоря)
    cy = sum(a["y"] for a in якоря) / len(якоря)
    занято = [(a["x"] - 14, a["y"] - 14, a["x"] + 14, a["y"] + 14) for a in якоря]
    for a in sorted(якоря, key=lambda a: -math.hypot(a["x"] - cx, a["y"] - cy)):
        base = math.atan2(a["y"] - cy, a["x"] - cx) if math.hypot(a["x"] - cx, a["y"] - cy) > 5 else -math.pi / 2
        лучшее = None
        for dist in (70, 100, 135, 175):
            for dang in (0, 0.35, -0.35, 0.7, -0.7, 1.1, -1.1, 1.6, -1.6):
                ang = base + dang
                bx, by = a["x"] + dist * math.cos(ang), a["y"] + dist * math.sin(ang)
                rect = (bx - r, by - r, bx + r, by + r)
                if rect[0] < 10 or rect[1] < 10 or rect[2] > W - 10 or rect[3] > H - 10:
                    continue
                if not any(_пересек(rect, z, 6) for z in занято):
                    лучшее = (bx, by, rect)
                    break
            if лучшее:
                break
        if лучшее is None:
            bx, by = a["x"] + 70 * math.cos(base), a["y"] + 70 * math.sin(base)
            лучшее = (bx, by, (bx - r, by - r, bx + r, by + r))
        bx, by, rect = лучшее
        занято.append(rect)
        L = math.hypot(bx - a["x"], by - a["y"]) or 1.0
        ex, ey = bx - (bx - a["x"]) / L * r, by - (by - a["y"]) / L * r
        d.line([(a["x"], a["y"]), (ex, ey)], fill=INK, width=2)
        d.ellipse([a["x"] - 6, a["y"] - 6, a["x"] + 6, a["y"] + 6], fill=INK)
        d.ellipse(rect, fill=BG, outline=INK, width=2)
        tw = d.textlength(a["текст"], font=f)
        d.text((bx - tw / 2, by - f.size * 0.62), a["текст"], font=f, fill=INK)


def наложить(png, якоря_json, out):
    data = json.load(open(якоря_json, encoding="utf-8"))
    img = Image.open(png).convert("RGB")
    W, H = img.size
    d = ImageDraw.Draw(img)
    if data.get("стиль") == "позиции":
        _позиции(img, d, data["якоря"], W, H)
    else:
        _сборки(img, d, data["якоря"], W, H)
    tmp = os.path.join(os.path.dirname(out), "_tmp_overlay" + os.path.splitext(out)[1])
    if out.lower().endswith(".jpg"):
        img.save(tmp, quality=92)
    else:
        img.save(tmp)
    os.replace(tmp, out)
    return out


if __name__ == "__main__":
    print(наложить(sys.argv[1], sys.argv[2], sys.argv[3]))
