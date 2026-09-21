# -*- coding: utf-8 -*-
"""Теория корабля «Волжского Горизонта».

Гидростатика, посадка, остойчивость, ходкость и качка. Считается всё от
обводов, а не от коэффициентов: плазовая таблица в `gorizont.OFFSETS`
задаёт три полушироты и три аппликаты на каждом сечении, между ними обвод
линейный, между шпангоутами — тоже. Это та же функция полушироты, по которой
построена поверхность корпуса в Blender, поэтому расчёт и модель описывают
одно судно.

Методика — курс теории корабля СПбГМТУ:
  * элементы теоретического чертежа — численным интегрированием по
    шпангоутам (правило трапеций по сгущённой сетке);
  * остойчивость на больших углах — пантокарены через отсечение сечения
    наклонной ватерлинией, диаграммы статической и динамической
    остойчивости, проверка по нормам РРР;
  * ходкость — сопротивление трения по ITTC-57 с формфактором, остаточное
    по аппроксимации серии полных обводов, поправка на мелководье по
    Шлихтингу, контроль адмиралтейским коэффициентом;
  * продольная прочность — в модуле gorizont_strength.

Массы в тоннах, длины в метрах, углы в градусах. Вода пресная, ро = 1.000.
"""
import math
from . import gorizont as G

RHO = 1.000          # плотность пресной воды, т/м3
NU = 1.14e-6         # кинематическая вязкость воды при 15 C, м2/с
GRAV = 9.81

_OFF = G.OFFSETS
_WL = G.WATERLINES
_XS = [r[1] for r in _OFF]


# --- монотонный кубический сплайн (Fritsch-Carlson) -------------------------
# Плазовая таблица задаёт обвод в узлах; между узлами его сглаживают. Берём
# монотонный кубический сплайн: он проходит через узлы точно и не даёт
# выбросов между ними — то же, что делает плазовщик гибкой рейкой.
def _pchip(xs, ys):
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0.0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def _end(dk, dk1, hk, hk1):
        t = ((2 * hk + hk1) * dk - hk * dk1) / (hk + hk1)
        if t * dk <= 0.0:
            return 0.0
        if dk * dk1 < 0.0 and abs(t) > abs(3.0 * dk):
            return 3.0 * dk
        return t

    if n > 2:
        m[0] = _end(d[0], d[1], h[0], h[1])
        m[-1] = _end(d[-1], d[-2], h[-1], h[-2])
    else:
        m[0] = m[-1] = d[0]
    return xs, ys, m, h


def _pchip_at(spl, x):
    xs, ys, m, h = spl
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xs[mid] <= x:
            lo = mid
        else:
            hi = mid
    t = (x - xs[lo]) / h[lo]
    t2, t3 = t * t, t * t * t
    return ((2 * t3 - 3 * t2 + 1) * ys[lo]
            + (t3 - 2 * t2 + t) * h[lo] * m[lo]
            + (-2 * t3 + 3 * t2) * ys[lo + 1]
            + (t3 - t2) * h[lo] * m[lo + 1])


_SPL_ZK = _pchip(_XS, [r[2] for r in _OFF])
_SPL_BK = _pchip(_XS, [r[3] for r in _OFF])
_SPL_ZB = _pchip(_XS, [r[4] for r in _OFF])
_SPL_BB = _pchip(_XS, [r[5] for r in _OFF])
_SPL_PHI = _pchip(_XS, [math.radians(G.SECTION_SHAPE[r[0]][0]) for r in _OFF])
_COLCACHE = {}
_PROFCACHE = {}


# --- геометрия шпангоута ----------------------------------------------------
# Сечение строится так же, как его строит плазовщик: плоское днище, скуловая
# дуга, касательная к днищу и к борту, и прямой борт с развалом phi. Радиус
# скулы из условия касания однозначен. Ординаты плазовой таблицы — отсчёты
# этого же сечения, поэтому таблица, расчёт и модель описывают один обвод.
# Ватерлиний ниже килевой линии не существует: в таблице там прочерк.
def bilge_radius(bk, bb, zk, zb, phi):
    s, c = math.sin(phi), math.cos(phi)
    return ((bb - bk) * c - (zb - zk) * s) / (1.0 - s)


def section_y(z, zk, bk, zb, bb, phi):
    """Полуширота сечения на высоте z; ниже килевой линии — 0."""
    if z < zk:
        return 0.0
    if z >= zb:
        return bb
    r = bilge_radius(bk, bb, zk, zb, phi)
    if r <= 1e-6:
        return bk + (bb - bk) * (z - zk) / max(zb - zk, 1e-9)
    z_t = zk + r * (1.0 - math.sin(phi))
    if z <= z_t:
        d = z - zk - r
        return bk + math.sqrt(max(r * r - d * d, 0.0))
    return bk + r * math.cos(phi) + (z - z_t) * math.tan(phi)


def _column(x):
    """Параметры шпангоута, сглаженные по длине:
    (z киля, полуширота днища, z борта, полуширота по борту, развал борта)."""
    key = round(x, 4)
    c = _COLCACHE.get(key)
    if c is None:
        c = (_pchip_at(_SPL_ZK, x), max(0.0, _pchip_at(_SPL_BK, x)),
             _pchip_at(_SPL_ZB, x), max(0.0, _pchip_at(_SPL_BB, x)),
             _pchip_at(_SPL_PHI, x))
        if len(_COLCACHE) < 300000:
            _COLCACHE[key] = c
    return c


def profile(x):
    """Узлы обвода шпангоута снизу вверх: [(z, полуширота), ...].

    Килевая линия, ватерлинии плазовой таблицы выше неё и точка по борту.
    """
    zk, bk, zb, bb, phi = _column(x)
    pr = _PROFCACHE.get(round(x, 4))
    if pr is not None:
        return pr
    pts = [(zk, bk)]
    r = bilge_radius(bk, bb, zk, zb, phi)
    z_t = zk + r * (1.0 - math.sin(phi)) if r > 1e-6 else zk
    extra = [z_t] if zk + 1e-3 < z_t < zb - 1e-3 else []
    zs = sorted(set([z for z in _WL if zk + 1e-6 < z < zb - 1e-6] + extra))
    for z in zs:
        pts.append((z, section_y(z, zk, bk, zb, bb, phi)))
    pts.append((zb, bb))
    if len(_PROFCACHE) < 300000:
        _PROFCACHE[round(x, 4)] = pts
    return pts


def half_breadth(x, z):
    """Полуширота обвода на шпангоуте x и высоте z.

    Считается прямо по геометрии сечения, поэтому в узлах плазовой таблицы
    совпадает с таблицей точно, а между узлами обвод остаётся плавным.
    """
    zk, bk, zb, bb, phi = _column(x)
    return section_y(z, zk, bk, zb, bb, phi)


def side_height(x):
    """Высота борта (линия палубы) на шпангоуте x с учётом седловатости."""
    return _column(x)[2]


def keel_height(x):
    """Высота килевой линии на шпангоуте x."""
    return _column(x)[0]


def _station(x):
    """Совместимость: (днище, скула, палуба, z скулы, z киля, z борта).

    Скула — верхняя точка скуловой дуги, где она переходит в прямой борт.
    """
    zk, bk, zb, bb, phi = _column(x)
    r = bilge_radius(bk, bb, zk, zb, phi)
    if r <= 1e-6:
        return bk, bk, bb, zk, zk, zb
    z_sk = zk + r * (1.0 - math.sin(phi))
    b_sk = bk + r * math.cos(phi)
    return bk, b_sk, bb, z_sk, zk, zb


def super_half_breadth(x):
    """Полуширота надстройки — тот же обвод, по которому она построена."""
    if x < G.SUPER_START or x > G.SUPER_END:
        return 0.0
    base = min(G.SUPER_HALF, half_breadth(x, G.DEPTH) - G.SIDE_WALK)
    if x > 119.0:
        base = min(base, G.SUPER_HALF * (1.0 - ((x - 119.0) / 13.0) ** 1.55))
    if x < 15.0:
        base = min(base, G.SUPER_HALF * (1.0 - ((15.0 - x) / 5.5) ** 1.8))
    return max(0.0, base)


def section_polygon(x, z_top=None):
    """Полный контур шпангоута (оба борта), список (y, z).

    Контур строится по узлам плазовой таблицы, поэтому скула передаётся
    дугой, а не изломом. При z_top выше высоты борта в контур добавляется
    закрытая надстройка: она водонепроницаема на 86 % длины и на больших
    углах крена даёт дополнительный запас плавучести.
    """
    pts = profile(x)
    zk, zb = pts[0][0], pts[-1][0]
    if z_top is None:
        z_top = zb
    right = [(0.0, zk)]
    if z_top <= zb:
        for (z, y) in pts:
            if z <= z_top + 1e-9:
                right.append((y, z))
        right.append((half_breadth(x, z_top), z_top))
    else:
        for (z, y) in pts:
            right.append((y, z))
        bs = super_half_breadth(x)
        if bs > 0.05:
            right += [(bs, zb), (bs, z_top)]
        else:
            right += [(pts[-1][1], z_top)]
    left = [(-y, z) for (y, z) in reversed(right)]
    return left + right[1:]


def _clip_below(poly, nz, ny, c):
    """Отсечение многоугольника полуплоскостью nz*z + ny*y <= c."""
    if not poly:
        return []
    out = []
    n = len(poly)
    for i in range(n):
        y0, z0 = poly[i]
        y1, z1 = poly[(i + 1) % n]
        f0 = nz * z0 + ny * y0 - c
        f1 = nz * z1 + ny * y1 - c
        if f0 <= 0:
            out.append((y0, z0))
        if (f0 < 0 < f1) or (f1 < 0 < f0):
            t = f0 / (f0 - f1)
            out.append((y0 + t * (y1 - y0), z0 + t * (z1 - z0)))
    return out


def _poly_area_centroid(poly):
    n = len(poly)
    if n < 3:
        return 0.0, 0.0, 0.0
    a = cy = cz = 0.0
    for i in range(n):
        y0, z0 = poly[i]
        y1, z1 = poly[(i + 1) % n]
        cr = y0 * z1 - y1 * z0
        a += cr
        cy += (y0 + y1) * cr
        cz += (z0 + z1) * cr
    a *= 0.5
    if abs(a) < 1e-12:
        return 0.0, 0.0, 0.0
    return abs(a), cy / (6 * a), cz / (6 * a)


def _xs(step=0.5):
    n = int(round(G.LOA / step))
    return [i * G.LOA / n for i in range(n + 1)]


def _trapz(ys, xs):
    s = 0.0
    for i in range(len(xs) - 1):
        s += 0.5 * (ys[i] + ys[i + 1]) * (xs[i + 1] - xs[i])
    return s


def section_area(x, T):
    """Погружённая площадь шпангоута при осадке T, оба борта.

    Интегрируется по всем узлам плазовой таблицы, а не по трём точкам, —
    иначе скуловая дуга срезается хордой и объём теряется.
    """
    pts = profile(x)
    zk = pts[0][0]
    if T <= zk:
        return 0.0
    zs = [zk]
    for (z, _y) in pts[1:]:
        if z < T - 1e-9:
            zs.append(z)
    zs.append(min(T, pts[-1][0]))
    if T > pts[-1][0]:
        zs.append(T)
    a = 0.0
    for i in range(len(zs) - 1):
        z0, z1 = zs[i], zs[i + 1]
        if z1 - z0 < 1e-12:
            continue
        a += 0.5 * (half_breadth(x, z0) + half_breadth(x, z1)) * (z1 - z0)
    return 2.0 * a


_HCACHE = {}


def hydrostatics(T, step=0.5):
    """Элементы теоретического чертежа на ровный киль при осадке T."""
    key = (round(T, 6), step)
    if key in _HCACHE:
        return _HCACHE[key]
    xs = _xs(step)
    om = [section_area(x, T) for x in xs]
    bw = [2.0 * half_breadth(x, T) for x in xs]

    V = _trapz(om, xs)
    if V <= 1e-6:
        return None
    xc = _trapz([o * x for o, x in zip(om, xs)], xs) / V

    nz = 40
    zs = [T * i / nz for i in range(nz + 1)]
    Aw_z = [_trapz([2.0 * half_breadth(x, z) for x in xs], xs) for z in zs]
    V_chk = _trapz(Aw_z, zs)
    zc = _trapz([a * z for a, z in zip(Aw_z, zs)], zs) / max(V_chk, 1e-9)

    Aw = _trapz(bw, xs)
    xf = _trapz([b * x for b, x in zip(bw, xs)], xs) / max(Aw, 1e-9)
    Ix = _trapz([(b ** 3) / 12.0 for b in bw], xs)
    Iy = _trapz([b * (x - xf) ** 2 for b, x in zip(bw, xs)], xs)

    def girth(x):
        b_dn, b_sk, b_pal, z_sk, z_kil, z_brt = _station(x)
        if T <= z_kil:
            return 0.0
        pts = [(0.0, z_kil), (b_dn, z_kil), (b_sk, z_sk), (b_pal, z_brt)]
        g = 0.0
        for i in range(len(pts) - 1):
            y0, z0 = pts[i]
            y1, z1 = pts[i + 1]
            if z0 >= T:
                break
            if z1 > T:
                t = (T - z0) / max(z1 - z0, 1e-9)
                y1 = y0 + t * (y1 - y0)
                z1 = T
            g += math.hypot(y1 - y0, z1 - z0)
            if z1 >= T:
                break
        return 2.0 * g

    S = _trapz([girth(x) for x in xs], xs)

    wet = [x for x, b in zip(xs, bw) if b > 1e-6]
    Lw = max(wet) - min(wet)
    Bw = max(bw)
    Om_mid = max(om)
    delta = V / (Lw * Bw * T)
    alpha = Aw / (Lw * Bw)
    beta = Om_mid / (Bw * T)
    r = Ix / V
    R = Iy / V
    res = dict(T=T, V=V, D=RHO * V, Aw=Aw, S=S,
                xc=xc, zc=zc, xf=xf, Ix=Ix, Iy=Iy, r=r, R=R,
                zm=zc + r, zM=zc + R, Lw=Lw, Bw=Bw, Om=Om_mid,
                delta=delta, alpha=alpha, beta=beta,
                phi=delta / beta, chi=delta / alpha,
                TPC=0.01 * RHO * Aw,
                MCT=RHO * V * R / (100.0 * Lw))
    _HCACHE[key] = res
    return res


def curves(T_from=1.0, T_to=3.6, n=13):
    return [hydrostatics(T_from + (T_to - T_from) * i / n)
            for i in range(n + 1)]


# Нагрузка масс. Поля: имя, масса т, x0, x1 (границы распределения по длине),
# аппликата ЦТ м, момент свободной поверхности т·м.
# Масса корпуса и надстройки — не оценка, а результат gorizont_struct.steel_weight()
# и superstructure_weight(): сумма листов и профилей по фактическим размерам связей.
# Первые две группы не задаются числом, а считаются по толщинам связей в
# gorizont_struct: изменил толщину настила — сразу поехали масса, осадка и
# все нагрузки, а не только напряжение. Числа в таблице ниже — заглушки,
# фактические подставляет groups().
WEIGHT_GROUPS = [
    ("Корпус металлический",               846.0,   0.0, 128.0,  1.45,   0.0),
    ("Надстройка и рубка",                 281.0,   9.0, 121.0,  6.60,   0.0),
    # Зашивка и мебель на композитных панелях вместо мокрых зашивок:
    # дороже в закупке, легче на 20 %, и это же плюс в блок технологичности.
    ("Изоляция и зашивка, первая",          33.0,  10.0, 118.0,  1.80,   0.0),
    ("Изоляция и зашивка, главная",         46.0,   9.0, 121.0,  4.20,   0.0),
    ("Изоляция и зашивка, средняя",         46.0,   9.0, 121.0,  7.00,   0.0),
    ("Оборудование помещений, первая",      70.0,  10.0, 118.0,  1.90,   0.0),
    ("Оборудование помещений, главная",    125.0,   9.0, 121.0,  4.30,   0.0),
    ("Оборудование помещений, средняя",    115.0,   9.0, 121.0,  7.10,   0.0),
    ("Якорно-швартовное устройство",        24.0, 108.0, 126.0,  3.60,   0.0),
    # Надувные плоты вместо шлюпок. Класс «О» на внутренних путях это
    # допускает, спасение приходит с берега за минуты, а шлюпки — это
    # полсотни тонн на шлюпочной палубе, то есть высоко.
    # ПРОВЕРИТЬ по Правилам РРР часть II перед защитой.
    ("Спасательные средства (плоты)",       24.0,  30.0, 100.0,  8.80,   0.0),
    # Систем стало меньше не по экономии, а по устройству: у колёсного
    # судна нет валопроводов, дейдвудов, систем смазки и охлаждения
    # дейдвудных подшипников и нет тоннелей подруливающих устройств.
    ("Системы и трубопроводы",              165.0,   4.0, 124.0,  3.40,   0.0),
    ("ГДГ двухтопливные, ГРЩ, механизмы",  120.0,   8.0,  30.0,  1.30,   0.0),
    # Колёсный комплекс: колёса с шарнирными плицами, валы, редукторы, ГЭД.
    # Тяжелее винтового и стоит высоко — ось колеса на 2,65 м от основной.
    ("Колёсный комплекс",                   95.0,  14.0,  30.0,  2.20,   0.0),
    # Газовая система: танки типа C пустые, испарители, газовая рампа.
    # Стоит на солнечной палубе, и это самый высокий тяжёлый груз на судне.
    ("Газовая система СПГ",                 75.0,  46.0,  66.0,  9.20,   0.0),
    ("Котельная установка и утилизация",     12.0,  10.0,  18.0,  1.60,   0.0),
    ("Установка очистки стоков AWTS",        18.0,  70.0,  86.0,  1.20,   0.0),
    ("Электрооборудование и АСУ",           112.0,   6.0, 124.0,  3.60,   0.0),
    # Гараж: аппарель с гидроприводом, подкрепления настила под 3,5 т на
    # место, вентиляция на десять обменов, орошение, газовый контроль.
    ("Гараж, аппарель и его системы",        26.0,   8.0,  30.0,  3.40,   0.0),
    ("Запас водоизмещения 3 %",              66.0,   0.0, 128.0,  3.50,   0.0),
    # Дедвейт. Свободной поверхности в танках СПГ нет: тип C — сосуд под
    # давлением, жидкость в нём не плещется, как в открытой цистерне.
    ("СПГ 130 м3",                           58.5,  46.0,  66.0,  9.60,   0.0),
    ("Запальное топливо 12 м3",              10.3,  20.0,  24.0,  0.50,   6.0),
    # Пресной воды 90 м3 вместо 110: возврат обоих контуров сточных вод,
    # и серого, и чёрного, отдаёт 22 м3 в сутки. Это прямой выигрыш от
    # требования КЗ, а не догадка.
    ("Пресная вода 90 м3",                   90.0,  60.0,  96.0,  0.50,  34.0),
    ("Очищенные серые и чёрные воды 32 м3",  32.0,  70.0,  79.0,  0.50,  18.0),
    ("Буферные и аварийная сточные 44 м3",   44.0,  52.0,  85.0,  0.50,  24.0),
    ("Масло, шлам и льяльные 18 м3",         17.0,  12.0,  19.0,  0.50,  10.0),
    # 6 кг на человека в сутки на 269 человек и 15 суток — норма речного
    # пассажирского судна с ежедневным пополнением в портах захода.
    ("Провизия и снабжение",                 28.0,  40.0,  52.0,  1.50,   0.0),
    ("Экипаж 57 чел. с багажом",              6.8,  20.0, 110.0,  4.00,   0.0),
    ("Пассажиры 212 чел. с багажом",         31.8,   9.0, 121.0,  5.00,   0.0),
    ("Автомобили 4 x 3,5 т",                 14.0,   8.0,  30.0,  3.60,   0.0),
]
# Успокоительных цистерн в таблице пока нет: gorizont_roll настроен на
# прежний корпус, и подставлять его числа сюда значит врать. Настройка
# успокоителя под новый период качки — отдельный шаг плана перехода.
LIGHTSHIP_GROUPS = 18
# Балласт в таблицу не входит: в расчётном состоянии «полный запас»
# балластные цистерны пустые, они служат для дифферентовки и кренования.
BALLAST_CAPACITY = G.BALLAST_M3


_GROUPS = None


def groups():
    """Нагрузка масс с пересчитанными по толщинам корпусом и надстройкой."""
    global _GROUPS
    if _GROUPS is None:
        from . import gorizont_struct as _S
        hull = _S.steel_weight()
        sup = _S.superstructure_weight()
        g = list(WEIGHT_GROUPS)
        g[0] = (g[0][0], round(hull["m"], 1), g[0][2], g[0][3],
                round(hull["z"], 2), g[0][5])
        g[1] = (g[1][0], round(sup["m"], 1), g[1][2], g[1][3],
                round(sup["z"], 2), g[1][5])
        # жидкость успокоительных цистерн: берётся из gorizont_roll, чтобы
        # настройка цистерны и нагрузка масс не разъезжались. Подстановка
        # здесь, а не в таблице: gorizont_roll импортирует этот модуль.
        from . import gorizont_roll as _R
        w = _R.water()
        for i, row in enumerate(g):
            if row[0].startswith("Успокоительные"):
                g[i] = (row[0], round(w["mass"], 1), row[2], row[3],
                        round(_R.TANKS[0]["z0"] + _R.LEVEL / 2.0, 2),
                        round(w["mfs"], 1))
        _GROUPS = g
    return _GROUPS


def group_xcg(g):
    """Абсцисса ЦТ группы. Корпус распределяется по площади сечения обшивки."""
    name, m, x0, x1, z, fs = g
    if not name.startswith("Корпус"):
        return 0.5 * (x0 + x1)
    xs = _xs(1.0)
    w = []
    for x in xs:
        b_dn, b_sk, b_pal, z_sk, z_kil, z_brt = _station(x)
        w.append(2 * b_dn + 2 * math.hypot(b_sk - b_dn, z_sk - z_kil)
                 + 2 * (z_brt - z_sk) + 2 * b_pal)
    return _trapz([a * x for a, x in zip(w, xs)], xs) / _trapz(w, xs)


def weight_summary():
    tot = sum(g[1] for g in groups())
    mx = sum(g[1] * group_xcg(g) for g in groups())
    mz = sum(g[1] * g[4] for g in groups())
    mfs = sum(g[5] for g in groups())
    light = sum(g[1] for g in groups()[:LIGHTSHIP_GROUPS])
    zl = sum(g[1] * g[4] for g in groups()[:LIGHTSHIP_GROUPS]) / light
    return dict(D=tot, xg=mx / tot, zg=mz / tot, Mfs=mfs,
                lightship=light, zg_light=zl, deadweight=tot - light,
                dzg_fs=mfs / tot)


def weight_distribution(xs):
    """Строевая нагрузки масс w(x), т/м."""
    w = [0.0] * len(xs)
    for g in groups():
        name, m, x0, x1, z, fs = g
        if name.startswith("Корпус"):
            sh = []
            for x in xs:
                b_dn, b_sk, b_pal, z_sk, z_kil, z_brt = _station(x)
                sh.append(2 * b_dn + 2 * math.hypot(b_sk - b_dn, z_sk - z_kil)
                          + 2 * (z_brt - z_sk) + 2 * b_pal)
            k = m / _trapz(sh, xs)
            for i in range(len(xs)):
                w[i] += k * sh[i]
        else:
            q = m / max(x1 - x0, 1e-6)
            for i, x in enumerate(xs):
                if x0 <= x <= x1:
                    w[i] += q
    return w


_ECACHE = {}


def equilibrium(step=0.5):
    """Осадка и дифферент из равенства водоизмещения и совпадения абсцисс."""
    if step in _ECACHE:
        return _ECACHE[step]
    w = weight_summary()
    D = w["D"]
    lo, hi = 0.3, G.DEPTH
    for _ in range(60):
        T = 0.5 * (lo + hi)
        h = hydrostatics(T, step)
        if h is None or h["D"] < D:
            lo = T
        else:
            hi = T
    T = 0.5 * (lo + hi)
    h = hydrostatics(T, step)
    dx = w["xg"] - h["xc"]
    trim_cm = D * dx / h["MCT"]
    trim = trim_cm / 100.0
    Ta = T - trim * h["xf"] / h["Lw"]
    Tf = T + trim * (h["Lw"] - h["xf"]) / h["Lw"]
    res = dict(T=T, trim=trim, Ta=Ta, Tf=Tf, D=D, xg=w["xg"], xc=h["xc"],
               zg=w["zg"], zm=h["zm"], hydro=h, weight=w)
    _ECACHE[step] = res
    return res


def initial_stability():
    e = equilibrium()
    h0 = e["zm"] - e["zg"]
    dh = e["weight"]["Mfs"] / e["D"]
    return dict(h0=h0, dh_fs=dh, h=h0 - dh, zg=e["zg"], zm=e["zm"],
                zc=e["hydro"]["zc"], r=e["hydro"]["r"], T=e["T"],
                D=e["D"], H=e["hydro"]["zM"] - e["zg"])


def _heeled_volume(theta_deg, c, xs, z_top):
    th = math.radians(theta_deg)
    nz, ny = math.cos(th), -math.sin(th)
    areas, ys, zs_ = [], [], []
    for x in xs:
        poly = section_polygon(x, z_top)
        cp = _clip_below(poly, nz, ny, c)
        a, cy, cz = _poly_area_centroid(cp)
        areas.append(a)
        ys.append(cy)
        zs_.append(cz)
    V = _trapz(areas, xs)
    if V < 1e-9:
        return 0.0, 0.0, 0.0
    yc = _trapz([a * y for a, y in zip(areas, ys)], xs) / V
    zc = _trapz([a * z for a, z in zip(areas, zs_)], xs) / V
    return V, yc, zc


def pantocarene(theta_deg, V_target, xs=None, z_top=None):
    """Плечо остойчивости формы l_k при заданном объёмном водоизмещении."""
    if xs is None:
        xs = _xs(1.0)
    if z_top is None:
        z_top = G.DEPTH
    lo, hi = -G.BEAM, G.DEPTH + G.BEAM
    for _ in range(60):
        c = 0.5 * (lo + hi)
        V, yc, zc = _heeled_volume(theta_deg, c, xs, z_top)
        if V < V_target:
            lo = c
        else:
            hi = c
    c = 0.5 * (lo + hi)
    V, yc, zc = _heeled_volume(theta_deg, c, xs, z_top)
    th = math.radians(theta_deg)
    lk = yc * math.cos(th) + zc * math.sin(th)
    return dict(theta=theta_deg, lk=lk, V=V, yc=yc, zc=zc, c=c)


def gz_curve(thetas=(0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60,
                     65, 70, 75, 80, 85, 90),
             step=1.0, z_top=None):
    st = initial_stability()
    e = equilibrium()
    V = e["hydro"]["V"]
    zg = st["zg"] + st["dh_fs"]
    xs = _xs(step)
    out = []
    for t in thetas:
        p = pantocarene(t, V, xs, z_top)
        gz = p["lk"] - zg * math.sin(math.radians(t))
        out.append(dict(theta=t, lk=p["lk"], gz=gz))
    return out, dict(zg=zg, V=V, D=e["D"], h=st["h"])


def dynamic_arms(gz):
    out = [0.0]
    for i in range(1, len(gz)):
        t0 = math.radians(gz[i - 1]["theta"])
        t1 = math.radians(gz[i]["theta"])
        out.append(out[-1] + 0.5 * (gz[i - 1]["gz"] + gz[i]["gz"]) * (t1 - t0))
    return out


def _interp(xs, ys, x):
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + t * (ys[i + 1] - ys[i])
    return ys[-1] if x > xs[-1] else ys[0]


def stability_summary(z_top=None):
    gz, meta = gz_curve(z_top=z_top)
    th = [g["theta"] for g in gz]
    arms = [g["gz"] for g in gz]
    dyn = dynamic_arms(gz)
    gz_max = max(arms)
    th_max = th[arms.index(gz_max)]
    th_zero = th[-1]
    for i in range(arms.index(gz_max), len(arms) - 1):
        if arms[i] > 0 >= arms[i + 1]:
            t = arms[i] / (arms[i] - arms[i + 1])
            th_zero = th[i] + t * (th[i + 1] - th[i])
            break
    res = dict(theta=th, gz=arms, lk=[g["lk"] for g in gz], dyn=dyn,
               gz_max=gz_max, theta_max=th_max, theta_zero=th_zero,
               gz30=_interp(th, arms, 30.0))
    res.update(meta)
    return res


WIND_PRESSURE = {"О": 0.294, "М": 0.392, "М-СП": 0.490}
# Разряд района плавания по классу судна: считаем по тому классу, который
# объявлен в gorizont.RRR_CLASS, а не по зашитому в функции «О».
CLASS = G.RRR_CLASS.split()[0]
WAVE_HEIGHT = {"О": 2.0, "М": 3.0, "М-СП": 3.5}
WAVE_LENGTH = {"О": 20.0, "М": 30.0, "М-СП": 40.0}


def windage(T):
    """Площадь парусности и возвышение её центра над ватерлинией.

    Слагаемые берутся из размерений, а не вписаны числами: у прежнего судна
    они были зашиты как «120» и «96», и при смене корпуса молча стали врать.

    Кожухи колёс в парусность входят. Они стоят по бортам и в тени корпуса
    работают не полностью, но при осадке 1,5 м и надводном борте 1,5 м
    списывать два объёма 8 x 2,5 м со счёта нельзя: у мелкосидящего судна
    парусность и так главная беда остойчивости.
    """
    from . import gorizont_wheel as _W
    d = G.DECKS
    L_над = G.SUPER_END - G.SUPER_START
    к = _W.paddle_box(T, d["главная"], d["средняя"])
    parts = [
        (G.LOA * 0.96, G.DEPTH - T, T),                       # надводный борт
        (L_над, d["средняя"] - d["главная"], d["главная"]),   # ярус главной
        (L_над - 10.0, d["солнечная"] - d["средняя"], d["средняя"]),  # ярус средней
        (9.0, G.WHEELHOUSE_ROOF - G.WHEELHOUSE_FLOOR, G.WHEELHOUSE_FLOOR),
        (_W.COUNT * к["длина"], к["высота_кожуха"], d["главная"]),    # кожухи колёс
    ]
    A = sum(l * h for l, h, z in parts)
    z = sum(l * h * (z0 + h / 2) for l, h, z0 in parts) / A
    return A, z - T


def weather_criterion(cls=None, z_top=None):
    """Критерий погоды K = M_опр / M_кр по нормам РРР."""
    cls = cls or CLASS
    s = stability_summary(z_top)
    e = equilibrium()
    T = e["T"]
    D = e["D"]
    A, zw = windage(T)
    p = WIND_PRESSURE[cls]
    Mv = p * A * zw / GRAV
    lw = Mv / D
    h = s["h"]
    # амплитуда качки: максимальный уклон волны класса при её длине,
    # с поправкой на демпфирование скуловыми килями
    hw = WAVE_HEIGHT[cls]
    lam = WAVE_LENGTH[cls]
    theta_r = math.degrees(1.10 * math.pi * hw / lam)
    theta_r = max(8.0, min(theta_r, 25.0))
    th = s["theta"]
    dyn = s["dyn"]
    th_lim = min(s["theta_zero"], 60.0)
    d_r = _interp(th, dyn, theta_r)
    best = 0.0
    th_opr = theta_r
    for i in range(1, 401):
        t = theta_r + (th_lim - theta_r) * i / 400.0
        d = _interp(th, dyn, t)
        lo = (d - d_r) / (math.radians(t) + math.radians(theta_r))
        if lo > best:
            best = lo
            th_opr = t
    lopr = best
    Mopr = lopr * D
    return dict(K=Mopr / max(Mv, 1e-9), Mv=Mv, Mopr=Mopr, lw=lw, lopr=lopr,
                A=A, zw=zw, theta_r=theta_r, theta_opr=th_opr, cls=cls, h=h,
                theta_stat=math.degrees(math.atan(lw / max(h, 1e-6))))


def rrr_checks(cls=None, z_top=None):
    s = stability_summary(z_top)
    cls = cls or CLASS
    w = weather_criterion(cls, z_top)
    e = equilibrium()
    ldyn30 = _interp(s["theta"], s["dyn"], 30.0)
    ldyn40 = _interp(s["theta"], s["dyn"], min(40.0, s["theta_zero"]))
    # Угол максимума ДСО. Правила РРР требуют 25 град, но для широких судов
    # с B/T >= 2.5 (а у нас 16,5 / 2,17 = 7,6) допускают снижение до 15 град:
    # у таких обводов палуба входит в воду раньше, и максимум ДСО физически
    # не может прийтись на 25 град при любом разумном положении ЦТ.
    bt = G.BEAM / e["T"]
    theta_max_lim = 15.0 if bt >= 2.5 else 25.0
    rows = [
        ("Критерий погоды K", w["K"], 1.0, ">="),
        ("Начальная метацентрическая высота h, м", s["h"], 0.20, ">="),
        ("Максимальное плечо ДСО, м", s["gz_max"], 0.25, ">="),
        ("Угол максимума ДСО, град (B/T = %.1f)" % bt, s["theta_max"], theta_max_lim, ">="),
        ("Угол заката ДСО, град", s["theta_zero"], 55.0, ">="),
        ("Плечо ДСО при 30 град, м", s["gz30"], 0.20, ">="),
        ("Работа ДДО до 30 град, м-рад", ldyn30, 0.055, ">="),
        ("Работа ДДО до 40 град, м-рад", ldyn40, 0.090, ">="),
        ("Статический крен от ветра, град", w["theta_stat"], 12.0, "<="),
    ]
    out = []
    for name, val, lim, op in rows:
        ok = val >= lim if op == ">=" else val <= lim
        out.append(dict(name=name, value=val, limit=lim, op=op, ok=ok))
    return out, s, w, e


# Переборки нового корпуса. Кормовая группа посажена по нишам колёс: ниша
# идёт от 18,4 до 25,6 м, и переборки стоят по её краям, иначе вырез
# приходится на середину отсека.
BULKHEADS = [0.0, 6.0, 14.0, 18.0, 26.0, 46.0, 64.0, 84.0, 104.0, 118.0, G.LOA]
# Названий ровно столько, сколько отсеков между переборками. Раньше их было
# на один меньше, и flooding() молча считал не тот отсек.
COMPARTMENTS = [
    "Ахтерпик",                       # 0…6
    "Машинное отделение, ГДГ",        # 6…14
    "Электростанция и ГРЩ",           # 14…18
    "Отсек приводов колёс",           # 18…26, по нишам
    "Служебный блок и цистерны",      # 26…46
    "Каюты, отсек 1",                 # 46…64
    "Каюты, отсек 2",                 # 64…84
    "Каюты, отсек 3",                 # 84…104
    "Балластные цистерны",            # 104…118
    "Форпик и таранный отсек",        # 118…128
]
assert len(COMPARTMENTS) == len(BULKHEADS) - 1, "отсеков и названий должно быть поровну"


def flooding(i, perm=0.85, step=0.5):
    """Осадка при затоплении отсека, метод постоянного водоизмещения."""
    x0, x1 = BULKHEADS[i], BULKHEADS[i + 1]
    e = equilibrium()
    T0 = e["T"]
    xs = _xs(step)
    v = _trapz([section_area(x, T0) if x0 <= x <= x1 else 0.0 for x in xs], xs)
    v *= perm
    Aw_lost = _trapz([2.0 * half_breadth(x, T0) if x0 <= x <= x1 else 0.0
                      for x in xs], xs) * perm
    Aw = e["hydro"]["Aw"] - Aw_lost
    dT = v / max(Aw, 1e-6)
    T1 = T0 + dT
    return dict(i=i, name=COMPARTMENTS[i], x0=x0, x1=x1, v=v, dT=dT, T=T1,
                freeboard=G.DEPTH - T1, ok=T1 < G.DEPTH - 0.10)


def resistance(v_kmh, T=None, depth=None):
    """Буксировочное сопротивление, кН.

    Трение — по линии ITTC-57 с формфактором Ватанабе и надбавкой на
    шероховатость 0.0004. Остаточное сопротивление — по аппроксимации
    для полных речных обводов: при Fr = 0.17 оно составляет около
    четверти от трения и растёт как четвёртая степень числа Фруда.
    Воздушное — 0.0002.

    Если задана глубина фарватера, сопротивление умножается на поправку
    мелководья; она действительна только до Fr_h = 0.7, выше судно
    подходит к критической скорости и метод неприменим — такой режим
    помечается флагом `valid`.
    """
    if T is None:
        T = equilibrium()["T"]
    h = hydrostatics(T)
    v = v_kmh / 3.6
    L, B, S = h["Lw"], h["Bw"], h["S"]
    Re = v * L / NU
    Cf = 0.075 / (math.log10(Re) - 2.0) ** 2
    Cb = h["delta"]
    k = -0.095 + 25.6 * Cb / ((L / B) ** 2 * math.sqrt(B / T))
    dCf = 0.0004
    Fn = v / math.sqrt(GRAV * L)
    Cr = 1e-3 * (0.05 + 0.35 * (Fn / 0.17) ** 4 * (Cb / 0.80) ** 2
                 * math.sqrt(B / T / 5.0))
    Cair = 0.0002
    Ct = Cf * (1 + k) + dCf + Cr + Cair
    R = 0.5 * RHO * 1000.0 * S * v ** 2 * Ct / 1000.0
    out = dict(v_kmh=v_kmh, v=v, Re=Re, Fn=Fn, Cf=Cf, k=k, Cr=Cr, Ct=Ct,
               R_deep=R, R=R, S=S, T=T, kshallow=1.0, Fnh=0.0, valid=True,
               depth=depth)
    if depth:
        Fnh = v / math.sqrt(GRAV * depth)
        ks = 1.0 + 0.55 * Fnh ** 2 / max(1.0 - Fnh ** 2, 0.02)
        out.update(Fnh=Fnh, kshallow=ks, R=R * ks, valid=Fnh <= 0.70)
    return out


def critical_speed(depth):
    """Критическая скорость на мелководье, км/ч: корень из g*H."""
    return math.sqrt(GRAV * depth) * 3.6


def power(v_kmh, eta_d=0.62, eta_s=0.97, depth=None):
    """Буксировочная, валовая и мощность на фланце ГД, кВт."""
    r = resistance(v_kmh, depth=depth)
    Pe = r["R"] * r["v"]
    Pd = Pe / eta_d
    Pb = Pd / eta_s
    out = dict(Pe=Pe, Pd=Pd, Pb=Pb)
    out.update(r)
    return out


PROP_POWER = G.WHEEL_COUNT * G.WHEEL_MOTOR_POWER      # 2 x 550 = 1100 кВт


def max_speed(P_avail=None, depth=None, eta_d=0.62, eta_s=0.97):
    """Скорость, на которую хватает мощности движителей, км/ч."""
    if P_avail is None:
        P_avail = PROP_POWER
    lo, hi = 5.0, 40.0
    for _ in range(50):
        v = 0.5 * (lo + hi)
        if power(v, eta_d, eta_s, depth)["Pb"] < P_avail:
            lo = v
        else:
            hi = v
    return 0.5 * (lo + hi)


def admiralty(v_kmh, Pb):
    """Адмиралтейский коэффициент: D^(2/3) * v[уз]^3 / P[кВт]."""
    e = equilibrium()
    return e["D"] ** (2.0 / 3.0) * (v_kmh / 1.852) ** 3 / max(Pb, 1e-6)


def roll_period(h=None):
    if h is None:
        h = initial_stability()["h"]
    return 0.80 * G.BEAM / math.sqrt(max(h, 1e-6))


def pitch_period(T=None):
    if T is None:
        T = equilibrium()["T"]
    return 2.4 * math.sqrt(T)
