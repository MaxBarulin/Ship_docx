# -*- coding: utf-8 -*-
"""Конструкция корпуса «Волжского Горизонта»: размеры связей и эквивалентный брус.

Система набора смешанная, как принято для речных судов такой длины:
продольная в днище, во втором дне и в главной палубе на средней части
корпуса, поперечная в оконечностях и по бортам. Шпация 0.55 м, рамная
шпация 2.20 м (каждый четвёртый шпангоут — рамный).

Из этого модуля берутся:
  * размеры связей для чертежа мидель-шпангоута;
  * момент сопротивления эквивалентного бруса для расчёта общей прочности;
  * масса корпусной стали и её центр тяжести для нагрузки масс;
  * геометрия набора для построения в Blender.

Материал основных связей — сталь 09Г2С по ГОСТ 19281 (предел текучести
325 МПа), второстепенных — ВСт3сп по ГОСТ 380 (235 МПа). Толщины в
миллиметрах, всё остальное в метрах, если не сказано иное.
"""
import math
from . import gorizont as G
from . import gorizont_hydro as H

RHO_STEEL = 7.85          # т/м3
SPACING = 0.55            # шпация, м
FRAME_SPACING = 2.20      # рамная шпация, м
DB_HEIGHT = 1.30          # высота двойного дна до настила первой палубы, м
DB_PLATFORM = 0.50        # промежуточная платформа цистерн двойного дна, м
DB_HEIGHT_ER = 0.55       # понижение второго дна в машинном отделении, м

STEEL = {
    "09Г2С": dict(ReH=325.0, Rm=470.0, E=2.06e5, rho=7.85,
                  name="09Г2С ГОСТ 19281-2014"),
    "ВСт3сп": dict(ReH=235.0, Rm=380.0, E=2.06e5, rho=7.85,
                   name="ВСт3сп5 ГОСТ 380-2005"),
}

# Толщины листовых связей, мм
PLATES = {
    "горизонтальный киль":      12.0,
    "днище":                     9.0,
    "скула":                    10.0,
    "борт в районе ВЛ":          9.0,
    "борт ниже пояса":           8.0,
    "ширстрек":                 10.0,
    "второе дно":                8.0,
    "настил главной палубы":     8.0,
    "палубный стрингер":        10.0,
    "настил второго дна в МО":   8.0,
    "переборки водонепроницаемые": 7.0,
    "настил верхней палубы":     6.0,
    "настил шлюпочной палубы":   6.0,
    "борта надстройки":          5.0,
    "крыша четвёртого яруса":    5.0,
}

# Профили набора: (высота стенки мм, толщина стенки мм, ширина пояска мм,
#                  толщина пояска мм)
PROFILES = {
    "вертикальный киль":        (1200, 12, 0, 0),
    "днищевой стрингер":        (1200, 10, 0, 0),
    "флор сплошной":            (1200,  9, 0, 0),
    "флор в машинном":          (500,  9, 0, 0),
    "ребро днища":              (140,  8, 60, 10),
    "ребро второго дна":        (120,  8, 50,  8),
    "ребро палубы":             (120,  8, 50,  8),
    "шпангоут":                 (120,  8, 50,  8),
    "рамный шпангоут":          (500, 10, 150, 12),
    "бортовой стрингер":        (400,  9, 100, 10),
    "карлингс":                 (600, 10, 180, 12),
    "рамный бимс":              (500, 10, 150, 12),
    "холостой бимс":            (120,  8, 50,  8),
    "стойка переборки":         (180,  8, 70, 10),
}


def profile_area(name):
    """Площадь сечения профиля, см2."""
    hw, tw, bf, tf = PROFILES[name]
    return (hw * tw + bf * tf) / 100.0


def profile_cg(name):
    """Расстояние от присоединённого пояска до ЦТ профиля, см."""
    hw, tw, bf, tf = PROFILES[name]
    aw, af = hw * tw, bf * tf
    if aw + af == 0:
        return 0.0
    return (aw * hw / 2 + af * (hw + tf / 2)) / (aw + af) / 10.0


def profile_inertia(name):
    """Собственный момент инерции профиля относительно своего ЦТ, см4."""
    hw, tw, bf, tf = PROFILES[name]
    aw, af = hw * tw / 100.0, bf * tf / 100.0
    zw, zf = hw / 20.0, (hw + tf / 2) / 10.0
    z0 = profile_cg(name)
    iw = tw / 10.0 * (hw / 10.0) ** 3 / 12.0 + aw * (zw - z0) ** 2
    if af > 0:
        iff = bf / 10.0 * (tf / 10.0) ** 3 / 12.0 + af * (zf - z0) ** 2
    else:
        iff = 0.0
    return iw + iff


# ------------------------------------------------- эквивалентный брус, миде́ль
X_MID = 70.0


def midship_elements(x=X_MID):
    """Связи мидель-шпангоута: (имя, площадь см2, аппликата z м, свой I см4).

    Площади считаются на всё сечение (оба борта). Для листов площадь —
    длина по обводу, умноженная на толщину; свой момент инерции листа
    относительно собственной оси учитывается только для вертикальных.
    """
    b_dn, b_sk, b_pal, z_sk, z_kil, z_brt = H._station(x)
    el = []

    def plate(name, length_m, z, t_mm, vertical=False):
        a = length_m * t_mm * 10.0            # см2
        i = 0.0
        if vertical:
            i = (t_mm / 10.0) * (length_m * 100.0) ** 3 / 12.0
        el.append((name, a, z, i))

    keel_half = 0.90
    # днище: горизонтальный киль + днищевая обшивка
    plate("Горизонтальный киль", 2 * keel_half, z_kil, PLATES["горизонтальный киль"])
    plate("Обшивка днища", 2 * (b_dn - keel_half), z_kil, PLATES["днище"])
    # скула
    g = math.hypot(b_sk - b_dn, z_sk - z_kil)
    plate("Скуловой пояс", 2 * g, (z_kil + z_sk) / 2, PLATES["скула"])
    # борт: три пояса
    z1, z2 = z_sk, 1.80
    z3, z4 = 3.40, z_brt
    plate("Борт ниже пояса ВЛ", 2 * (z2 - z1), (z1 + z2) / 2,
          PLATES["борт ниже пояса"], vertical=True)
    plate("Пояс переменных ватерлиний", 2 * (z3 - z2), (z2 + z3) / 2,
          PLATES["борт в районе ВЛ"], vertical=True)
    plate("Ширстрек", 2 * (z4 - z3), (z3 + z4) / 2,
          PLATES["ширстрек"], vertical=True)
    # второе дно и палубы
    plate("Настил второго дна", 2 * (b_sk - 0.30), DB_HEIGHT, PLATES["второе дно"])
    plate("Настил главной палубы", 2 * (b_pal - 0.60), z_brt,
          PLATES["настил главной палубы"])
    plate("Палубный стрингер", 2 * 0.60, z_brt, PLATES["палубный стрингер"])
    # продольный набор
    n_bot = int(2 * b_dn / SPACING) - 1
    n_db = int(2 * (b_sk - 0.30) / SPACING) - 1
    n_dk = int(2 * (b_pal - 0.60) / SPACING) - 1
    el.append(("Рёбра днища %d шт" % n_bot,
               n_bot * profile_area("ребро днища"),
               z_kil + profile_cg("ребро днища") / 100.0,
               n_bot * profile_inertia("ребро днища")))
    el.append(("Рёбра второго дна %d шт" % n_db,
               n_db * profile_area("ребро второго дна"),
               DB_HEIGHT - profile_cg("ребро второго дна") / 100.0,
               n_db * profile_inertia("ребро второго дна")))
    el.append(("Рёбра главной палубы %d шт" % n_dk,
               n_dk * profile_area("ребро палубы"),
               z_brt - profile_cg("ребро палубы") / 100.0,
               n_dk * profile_inertia("ребро палубы")))
    # вертикальный киль и днищевые стрингеры
    hw = PROFILES["вертикальный киль"][0] / 1000.0
    plate("Вертикальный киль", hw, z_kil + hw / 2,
          PROFILES["вертикальный киль"][1], vertical=True)
    hs = PROFILES["днищевой стрингер"][0] / 1000.0
    plate("Днищевые стрингеры 4 шт", 4 * hs, z_kil + hs / 2,
          PROFILES["днищевой стрингер"][1], vertical=True)
    # бортовые стрингеры и карлингсы
    el.append(("Бортовые стрингеры 4 шт",
               4 * profile_area("бортовой стрингер"), 2.60, 0.0))
    el.append(("Карлингсы 3 шт",
               3 * profile_area("карлингс"),
               z_brt - profile_cg("карлингс") / 100.0,
               3 * profile_inertia("карлингс")))
    return el


def equivalent_girder(x=X_MID):
    """Момент инерции и моменты сопротивления эквивалентного бруса."""
    el = midship_elements(x)
    A = sum(e[1] for e in el)                       # см2
    Az = sum(e[1] * e[2] * 100.0 for e in el)       # см2 * см
    z0 = Az / A / 100.0                             # м от ОП
    I = 0.0
    for name, a, z, i0 in el:
        I += i0 + a * ((z - z0) * 100.0) ** 2       # см4
    b_dn, b_sk, b_pal, z_sk, z_kil, z_brt = H._station(x)
    z_top = z_brt
    z_bot = z_kil
    W_deck = I / max((z_top - z0) * 100.0, 1e-6)    # см3
    W_bot = I / max((z0 - z_bot) * 100.0, 1e-6)
    return dict(elements=el, A=A, z0=z0, I=I,
                W_deck=W_deck, W_bot=W_bot,
                I_m4=I * 1e-8, W_deck_m3=W_deck * 1e-6, W_bot_m3=W_bot * 1e-6,
                z_top=z_top, z_bot=z_bot)


# ------------------------------------------------------ масса корпусной стали
def _girth_parts(x, z_top):
    """Длины поясов обшивки на шпангоуте: (днище, скула, борт)."""
    b_dn, b_sk, b_pal, z_sk, z_kil, z_brt = H._station(x)
    bottom = 2 * b_dn
    bilge = 2 * math.hypot(b_sk - b_dn, z_sk - z_kil)
    side = 2 * math.hypot(b_pal - b_sk, min(z_top, z_brt) - z_sk)
    return bottom, bilge, side


def steel_weight(step=1.0):
    """Масса и центр тяжести корпусной стали по группам связей."""
    xs = H._xs(step)
    items = []

    def add(name, area_m2, t_mm, z, x=None):
        m = area_m2 * t_mm / 1000.0 * RHO_STEEL
        items.append(dict(name=name, area=area_m2, t=t_mm, m=m, z=z,
                          x=x if x is not None else G.LOA / 2))

    # --- наружная обшивка
    bot = bil = sid = 0.0
    zb = zs_ = 0.0
    for i in range(len(xs) - 1):
        x = 0.5 * (xs[i] + xs[i + 1])
        dx = xs[i + 1] - xs[i]
        b, g, s = _girth_parts(x, G.DEPTH)
        bot += b * dx
        bil += g * dx
        sid += s * dx
        _, _, _, z_sk, z_kil, z_brt = H._station(x)
        zb += b * dx * z_kil
        zs_ += s * dx * (z_sk + z_brt) / 2
    add("Обшивка днища с горизонтальным килем", bot, 9.4, zb / max(bot, 1e-9))
    add("Скуловой пояс", bil, 10.0, 0.35)
    add("Обшивка борта", sid, 8.7, zs_ / max(sid, 1e-9))

    # --- настилы
    def deck_area(x0, x1, z, k=1.0):
        a = 0.0
        for i in range(len(xs) - 1):
            x = 0.5 * (xs[i] + xs[i + 1])
            if not (x0 <= x <= x1):
                continue
            a += 2 * H.half_breadth(x, min(z, G.DEPTH)) * (xs[i + 1] - xs[i])
        return a * k

    add("Настил главной палубы", deck_area(2, 137, G.DEPTH), 8.0, G.DEPTH)
    add("Второе дно (настил первой палубы)", deck_area(2, 127, 1.40, 0.92),
        8.0, 1.40)
    add("Платформа цистерн второго дна", deck_area(9.5, 117, 0.55, 0.88),
        6.0, 0.55)

    # --- переборки
    nb = len(H.BULKHEADS) - 1
    ab = 0.0
    for xb in H.BULKHEADS[1:-1]:
        ab += 2 * H.half_breadth(xb, 2.0) * G.DEPTH * 0.92
    add("Водонепроницаемые переборки %d шт" % (nb - 1), ab, 7.0, G.DEPTH / 2)

    # --- набор корпуса
    Lm = 125.0                       # длина, на которой идёт продольный набор
    n_bot = 24
    n_db = 27
    n_dk = 26
    for nm, n, prof, z in (("Рёбра жёсткости днища", n_bot, "ребро днища", 0.10),
                           ("Рёбра жёсткости второго дна", n_db,
                            "ребро второго дна", 1.30),
                           ("Рёбра жёсткости главной палубы", n_dk,
                            "ребро палубы", 4.10)):
        a = profile_area(prof) * 1e-4 * n * Lm
        items.append(dict(name=nm, area=a, t=0.0,
                          m=a * RHO_STEEL, z=z, x=G.LOA / 2))
    # вертикальный киль, стрингеры
    for nm, prof, n, z in (("Вертикальный киль", "вертикальный киль", 1, 0.45),
                           ("Днищевые стрингеры", "днищевой стрингер", 4, 0.45),
                           ("Бортовые стрингеры", "бортовой стрингер", 4, 2.60),
                           ("Карлингсы главной палубы", "карлингс", 3, 3.85)):
        hw, tw, bf, tf = PROFILES[prof]
        a = (hw * tw + bf * tf) * 1e-6 * n * 130.0
        items.append(dict(name=nm, area=a, t=0.0,
                          m=a * RHO_STEEL, z=z, x=G.LOA / 2))
    # флоры и шпангоуты
    n_fl = int(G.LOA / FRAME_SPACING)
    a_fl = 0.0
    for k in range(n_fl):
        x = (k + 0.5) * FRAME_SPACING
        b_dn, b_sk, b_pal, z_sk, z_kil, z_brt = H._station(x)
        a_fl += 2 * b_sk * (PROFILES["флор сплошной"][0] / 1000.0) * 0.72
    items.append(dict(name="Флоры сплошные %d шт" % n_fl, area=a_fl, t=9.0,
                      m=a_fl * 9.0 / 1000.0 * RHO_STEEL, z=0.45, x=G.LOA / 2))
    n_br = int(G.LOA / SPACING) - n_fl
    items.append(dict(name="Бракетные флоры %d шт" % n_br, area=a_fl * 0.45,
                      t=8.0, m=a_fl * 0.45 * 8.0 / 1000.0 * RHO_STEEL,
                      z=0.45, x=G.LOA / 2))
    # шпангоуты и бимсы
    n_sp = int(G.LOA / SPACING)
    h_side = 3.2
    a_sp = profile_area("шпангоут") * 1e-4 * 2 * h_side * n_sp
    items.append(dict(name="Шпангоуты %d шп." % n_sp, area=a_sp, t=0.0,
                      m=a_sp * RHO_STEEL, z=2.40, x=G.LOA / 2))
    n_rs = int(G.LOA / FRAME_SPACING)
    a_rs = profile_area("рамный шпангоут") * 1e-4 * 2 * h_side * n_rs
    items.append(dict(name="Рамные шпангоуты %d шт" % n_rs, area=a_rs, t=0.0,
                      m=a_rs * RHO_STEEL, z=2.40, x=G.LOA / 2))
    a_bm = profile_area("рамный бимс") * 1e-4 * 15.0 * n_rs
    items.append(dict(name="Рамные бимсы %d шт" % n_rs, area=a_bm, t=0.0,
                      m=a_bm * RHO_STEEL, z=G.DEPTH - 0.30, x=G.LOA / 2))

    m = sum(i["m"] for i in items)
    extra = 0.16 * m          # кницы, фундаменты, форштевень, ахтерштевень, сварка
    items.append(dict(name="Кницы, фундаменты, штевни, сварка (16 %)",
                      area=0.0, t=0.0, m=extra, z=1.80, x=G.LOA / 2))
    m += extra
    z = sum(i["m"] * i["z"] for i in items) / m
    return dict(items=items, m=m, z=z)


def superstructure_weight():
    """Масса надстройки и рубки: настилы, борта, крыша, переборки."""
    items = []

    def add(name, area, t_mm, z):
        items.append(dict(name=name, area=area, t=t_mm,
                          m=area * t_mm / 1000.0 * RHO_STEEL, z=z))

    L = 120.0
    add("Настил верхней палубы", L * 13.6, 6.0, 7.00)
    add("Настил шлюпочной палубы", L * 13.6, 6.0, 9.80)
    add("Крыша четвёртого яруса", 96.0 * 11.6, 5.0, 12.60)
    add("Борта надстройки, главная палуба", 2 * L * 2.8, 5.0, 5.60)
    add("Борта надстройки, верхняя палуба", 2 * L * 2.8, 5.0, 8.40)
    add("Борта четвёртого яруса", 2 * 96.0 * 2.8, 5.0, 11.20)
    add("Поперечные переборки надстройки", 18 * 13.6 * 2.6, 5.0, 7.60)
    add("Рулевая рубка", 7.0 * 10.0 + 2 * 2.4 * 12.0, 5.0, 11.00)
    m = sum(i["m"] for i in items)
    extra = 0.22 * m          # набор надстройки, стойки, кницы
    items.append(dict(name="Набор надстройки, стойки, кницы (22 %)",
                      area=0.0, t=0.0, m=extra, z=8.40))
    m += extra
    z = sum(i["m"] * i["z"] for i in items) / m
    return dict(items=items, m=m, z=z)
