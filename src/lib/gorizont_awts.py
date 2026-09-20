# -*- coding: utf-8 -*-
"""Узел ВГ-2026.16.00 «Фундамент установки очистки сточных вод».

Установка очистки (мембранный биореактор чёрных стоков, биоблок серых
стоков, блок УФ и сепаратор льяльных вод) стоит в машинном отделении
на общей сварной раме. Рама решает четыре задачи сразу:

1.  Собирает четыре аппарата в один блок и передаёт их вес на флоры и
    стрингеры второго дна, а не на настил между ними.
2.  Держит блок при качке: вертикальная перегрузка отрывает аппараты от
    опор, поперечная сдвигает их к борту, поэтому кроме амортизаторов
    ставятся стопоры-ограничители.
3.  Стоит в поддоне: у установки со стоками пролив неизбежен, поддон с
    комингсом 150 мм отводит его в шламовую цистерну, а не в льяла.
4.  Развязывает вибрацию: насосы и воздуходувки установки работают
    круглосуточно рядом с каютами экипажа, поэтому блок посажен на
    амортизаторы, а собственная частота рамы отстроена от частот
    возбуждения дизель-генераторов и гребных винтов.

Размеры увязаны с gorizont_mach.MACHINES (позиции МБР, БИО, УФ, СЕП) и
с набором второго дна в машинном отделении.

Всё считается, а не объявляется: массы — из размеров профилей, нагрузки —
из перегрузок по РРР, напряжения — по сечению балки.
"""
import math
from . import gorizont as G
from . import gorizont_struct as S
from . import gorizont_mach as M

GRAV = 9.81
STEEL = "09Г2С"
MARK = "ВГ-2026.16.00"
NAME = "Фундамент установки очистки сточных вод"

# --- габариты узла ---------------------------------------------------------
X0, X1 = 30.20, 33.80          # по длине судна, м
Y0, Y1 = 0.60, 6.00            # от ДП к правому борту, м
Z_TANK_TOP = S.DB_HEIGHT_ER    # настил второго дна в МО, 0,55 м
Z_EQUIP = 0.56                 # опорная плоскость аппаратов (их лапы)
STACK = 0.098                  # подушка 16 + амортизатор 70 + плита 12, м
Z_TOP = Z_EQUIP - STACK        # верхняя полка балок фундамента, 0,462 м
H_BEAM = 0.20                  # высота балки фундамента, м
Z_TRAY = Z_TOP - H_BEAM        # днище поддона, 0,262 м
TRAY_COAMING = 0.15            # высота комингса поддона, м
# Настил второго дна под блоком местно опущен на 0,29 м: получается колодец,
# в котором стоит рама, а пролив со стоками собирается в поддон и уходит
# самозапорным клапаном в шламовую цистерну, а не в льяла.

N_LONG = 4                     # продольные балки
N_CROSS = 5                    # поперечные балки
PITCH_LONG = (Y1 - Y0) / (N_LONG - 1)
PITCH_CROSS = (X1 - X0) / (N_CROSS - 1)

# --- оборудование на раме --------------------------------------------------
# код, сухая масса т, рабочий объём жидкости м3, число лап
UNITS = [
    ("МБР", 4.2, 3.0, 4),
    ("БИО", 3.6, 2.5, 4),
    ("УФ",  0.6, 0.1, 2),
    ("СЕП", 1.1, 0.2, 2),
]
N_ISOLATORS = sum(u[3] for u in UNITS)
# Амортизатор подбирается по двум условиям сразу: статическая доля не выше
# номинала и собственная частота блока втрое ниже частоты возбуждения
# (дизель-генератор 750 об/мин = 12,5 Гц, лопастная частота винта
# 200 об/мин x 4 лопасти = 13,3 Гц). Из этого и взята жёсткость.
ISOLATOR = dict(type="АПС-1500", rated_kgf=1500.0, stiffness_kN_m=900.0)
F_DG = 750.0 / 60.0            # частота вращения ГДГ, Гц
F_BLADE = 200.0 / 60.0 * 4.0   # лопастная частота гребного винта, Гц

# --- перегрузки по РРР для класса «М» --------------------------------------
# Вертикальная — от килевой и вертикальной качки в районе миделя, поперечная
# и продольная — от бортовой и килевой качки; крен и дифферент статические.
CASES = [
    ("тихая вода",        1.00, 0.00, 0.00,  0.0, 0.0),
    ("качка расчётная",   1.60, 0.50, 0.25, 15.0, 5.0),
    ("аварийный крен",    1.00, 0.30, 0.00, 22.5, 0.0),
    ("гидроиспытание",    1.00, 0.00, 0.00,  0.0, 0.0),
]


def _profile_T(h_mm, tw_mm, bf_mm, tf_mm):
    """Сечение сварного тавра: площадь, момент инерции и сопротивления."""
    h, tw = h_mm / 1000.0, tw_mm / 1000.0
    bf, tf = bf_mm / 1000.0, tf_mm / 1000.0
    Aw, Af = h * tw, bf * tf
    A = Aw + Af
    zw, zf = h / 2.0, h + tf / 2.0
    z0 = (Aw * zw + Af * zf) / A
    I = (tw * h ** 3 / 12.0 + Aw * (zw - z0) ** 2
         + bf * tf ** 3 / 12.0 + Af * (zf - z0) ** 2)
    W_bot = I / z0
    W_top = I / (h + tf - z0)
    return dict(A=A, I=I, z0=z0, W_min=min(W_bot, W_top),
                mass_kg_m=A * S.RHO_STEEL * 1000.0, h=h + tf)


LONG_SECTION = (140, 8, 100, 10)            # стенка h x t, поясок b x t, мм
CROSS_SECTION = (120, 6, 80, 8)
LONG_BEAM = _profile_T(*LONG_SECTION)       # продольная балка
CROSS_BEAM = _profile_T(*CROSS_SECTION)     # поперечная балка


def _tee(sec):
    return "тавр %dx%d + %dx%d" % sec


def masses():
    """Массы: оборудование сухое, рабочая заправка, металл рамы."""
    dry = sum(u[1] for u in UNITS)
    liq = sum(u[2] for u in UNITS)
    L_long = (X1 - X0) * N_LONG
    L_cross = (Y1 - Y0) * N_CROSS
    steel = (L_long * LONG_BEAM["mass_kg_m"]
             + L_cross * CROSS_BEAM["mass_kg_m"]) / 1000.0
    tray = ((X1 - X0 + 0.2) * (Y1 - Y0 + 0.2) * 6.0 / 1000.0 * S.RHO_STEEL
            + 2 * ((X1 - X0) + (Y1 - Y0)) * TRAY_COAMING * 8.0 / 1000.0
            * S.RHO_STEEL)
    return dict(dry=dry, liquid=liq, wet=dry + liq, steel=steel, tray=tray,
                total=dry + liq + steel + tray)


def loads():
    """Нагрузки по случаям: на раму, на балку, на амортизатор, на стопор."""
    m = masses()
    out = []
    for name, nz, ny, nx, heel, trim in CASES:
        wet = m["wet"] * (2.0 if name == "гидроиспытание" else 1.0) \
            if name == "гидроиспытание" else m["wet"]
        if name == "гидроиспытание":
            # аппараты залиты водой доверху: объём по габариту корпусов
            wet = m["dry"] + sum(u[2] for u in UNITS) * 2.0
        mass = wet + m["steel"]
        Fz = mass * GRAV * (nz + math.cos(math.radians(heel)) - 1.0)
        Fy = mass * GRAV * (ny + math.sin(math.radians(heel)))
        Fx = mass * GRAV * (nx + math.sin(math.radians(trim)))
        out.append(dict(case=name, nz=nz, ny=ny, nx=nx, heel=heel, trim=trim,
                        mass=mass, Fz=Fz, Fy=Fy, Fx=Fx,
                        per_isolator=Fz / N_ISOLATORS,
                        shear_per_stopper=Fy / 4.0))
    return out


def beam_check(case_name="качка расчётная"):
    """Продольная балка фундамента как неразрезная на поперечных балках."""
    ld = [c for c in loads() if c["case"] == case_name][0]
    st = S.STEEL[STEEL]
    q = ld["Fz"] / N_LONG / (X1 - X0)                 # кН/м на одну балку
    L = PITCH_CROSS                                   # пролёт между поперечными
    M_ = q * L ** 2 / 10.0                            # неразрезная балка
    Q = 0.6 * q * L
    W = LONG_BEAM["W_min"]
    sigma = M_ / W / 1000.0                           # МПа
    tau = Q / (LONG_BEAM["h"] * 0.008) / 1000.0
    sig_eq = math.sqrt(sigma ** 2 + 3 * tau ** 2)
    f = q * L ** 4 / (384.0 * st["E"] * 1e3 * LONG_BEAM["I"]) * 1000.0  # мм
    sig_allow = 0.70 * st["ReH"]
    tau_allow = 0.40 * st["ReH"]
    f_allow = L / 500.0 * 1000.0
    return dict(case=case_name, q=q, L=L, M=M_, Q=Q,
                W_cm3=W * 1e6, I_cm4=LONG_BEAM["I"] * 1e8,
                sigma=sigma, tau=tau, sigma_eq=sig_eq, f_mm=f,
                sigma_allow=sig_allow, tau_allow=tau_allow, f_allow=f_allow,
                ok=(sig_eq <= sig_allow and tau <= tau_allow and f <= f_allow))


def weld_check(case_name="качка расчётная", kf=0.006):
    """Поясной шов балки и шов приварки к флору."""
    ld = [c for c in loads() if c["case"] == case_name][0]
    st = S.STEEL[STEEL]
    q = ld["Fz"] / N_LONG / (X1 - X0)
    Q = 0.6 * q * PITCH_CROSS
    Sf = 0.120 * 0.012 * (LONG_BEAM["h"] - LONG_BEAM["z0"] - 0.006)
    tau_flange = Q * Sf / (LONG_BEAM["I"] * 2.0 * 0.7 * kf) / 1000.0
    l_node = 2.0 * (LONG_BEAM["h"] + 0.120)
    tau_node = (Q + abs(ld["Fy"]) / N_LONG / (N_CROSS - 1)) \
        / (0.7 * kf * l_node) / 1000.0
    allow = 0.6 * 0.40 * st["ReH"] * 2
    return dict(tau_flange=tau_flange, tau_node=tau_node, allow=allow,
                kf_mm=kf * 1000.0,
                ok=(tau_flange <= allow and tau_node <= allow))


def bolt_check(d_mm=20.0, cls=8.8, n=None):
    """Болты крепления лап оборудования к раме: отрыв и срез."""
    n = n or N_ISOLATORS
    worst_z = max(loads(), key=lambda c: c["Fz"])
    worst_y = max(loads(), key=lambda c: abs(c["Fy"]))
    As = 0.7854 * (d_mm - 0.9382 * 2.5) ** 2          # М20, шаг 2,5 мм
    Rm = int(cls) * 100.0                             # 8.8 -> Rm = 800 МПа
    Rb = Rm * round((cls - int(cls)) * 10.0) / 10.0   # предел текучести 640 МПа
    N_bolt = worst_z["Fz"] / n * 1000.0               # Н
    Q_bolt = abs(worst_y["Fy"]) / n * 1000.0
    sigma = N_bolt / As
    tau = Q_bolt / As
    sig_eq = math.sqrt(sigma ** 2 + 3 * tau ** 2)
    allow = 0.6 * Rb
    return dict(d=d_mm, cls=cls, n=n, As_mm2=As, Rb=Rb,
                sigma=sigma, tau=tau, sigma_eq=sig_eq, allow=allow,
                case_z=worst_z["case"], case_y=worst_y["case"],
                ok=sig_eq <= allow)


def isolator_check():
    """Амортизаторы: статическая доля, перегрузка и отстройка по частоте."""
    m = masses()
    st_load = (m["wet"] + m["steel"]) * 1000.0 / N_ISOLATORS      # кгс
    worst = max(loads(), key=lambda c: c["per_isolator"])
    dyn = worst["per_isolator"] * 1000.0 / GRAV                   # кгс
    k = ISOLATOR["stiffness_kN_m"] * N_ISOLATORS                  # кН/м
    f0 = math.sqrt(k * 1000.0 / ((m["wet"] + m["steel"]) * 1000.0)) / (2 * math.pi)
    # частоты возбуждения
    f_dg, f_blade = F_DG, F_BLADE
    delta = (m["wet"] + m["steel"]) * 1000.0 * GRAV / (k * 1000.0) * 1000.0
    return dict(type=ISOLATOR["type"], n=N_ISOLATORS,
                rated=ISOLATOR["rated_kgf"], static=st_load, dynamic=dyn,
                case=worst["case"], f0=f0, f_dg=f_dg, f_blade=f_blade,
                delta_mm=delta,
                ratio_dg=f_dg / f0, ratio_blade=f_blade / f0,
                ok=(st_load <= ISOLATOR["rated_kgf"]
                    and dyn <= ISOLATOR["rated_kgf"] * 1.5
                    and f_dg / f0 >= 2.0 and f_blade / f0 >= 2.0))


def _plate(area_m2, t_mm):
    return round(area_m2 * t_mm * S.RHO_STEEL, 1)


def _bar(length_m, b_mm, t_mm):
    return round(length_m * b_mm * t_mm * S.RHO_STEEL * 1e-3, 1)


_M = masses()

# поз., обозначение, наименование, кол., материал / примечание, масса кг за шт.
PARTS = [
    (1, "ВГ-2026.16.01", "Балка продольная, " + _tee(LONG_SECTION), N_LONG,
     "Лист 8 и 12 ГОСТ 19903, " + STEEL,
     round(LONG_BEAM["mass_kg_m"] * (X1 - X0), 1)),
    (2, "ВГ-2026.16.02", "Балка поперечная, " + _tee(CROSS_SECTION), N_CROSS,
     "Лист 8 и 10 ГОСТ 19903, " + STEEL,
     round(CROSS_BEAM["mass_kg_m"] * (Y1 - Y0), 1)),
    (3, "ВГ-2026.16.03", "Поддон, лист 6", 1,
     "Лист 6 ГОСТ 19903, " + STEEL,
     _plate((X1 - X0 + 0.2) * (Y1 - Y0 + 0.2), 6.0)),
    (4, "ВГ-2026.16.04", "Комингс поддона, полоса 150 x 8", 1,
     "Полоса 150 x 8 ГОСТ 103, " + STEEL,
     _bar(2 * ((X1 - X0) + (Y1 - Y0)), 150, 8)),
    (5, "ВГ-2026.16.05", "Кница к флору, лист 10", 20,
     "Лист 10 ГОСТ 19903, " + STEEL, 6.4),
    (6, "ВГ-2026.16.06", "Подушка под лапу, лист 16", N_ISOLATORS,
     "Лист 16 ГОСТ 19903, " + STEEL, 3.8),
    (7, "ВГ-2026.16.07", "Стопор-ограничитель перемещений", 8,
     "Лист 12 и полоса, " + STEEL, 5.2),
    (8, "ВГ-2026.16.08", "Настил площадки обслуживания, рифлёный 4", 1,
     "Лист рифлёный 4 ГОСТ 8568, " + STEEL, 96.0),
    (9, "ВГ-2026.16.09", "Трап-сходня к площадке", 1,
     "Полоса и пруток, " + STEEL, 24.0),
    (10, "ВГ-2026.16.10", "Приёмный колодец поддона с трубой DN50", 1,
     "Лист 6, труба 57x4, " + STEEL, 11.0),
]

BOUGHT = [
    (11, "—", "Амортизатор резинометаллический %s" % ISOLATOR["type"],
     N_ISOLATORS,
     "номинал %d кгс, жёсткость %d кН/м" % (ISOLATOR["rated_kgf"],
                                            ISOLATOR["stiffness_kN_m"]), 9.4),
    (12, "—", "Болт М20x80 кл. 8.8 с гайкой и шайбами", 48,
     "ГОСТ 7798 / 5915 / 6402, оцинкованные", 0.32),
    (13, "—", "Клапан самозапорный DN50 на сливе поддона", 1,
     "с выводом в шламовую цистерну", 6.0),
    (14, "—", "Перемычка заземляющая", 4, "медь 16 мм2", 0.4),
]


def steel_mass():
    return round(sum(n * m for _, _, _, n, _, m in PARTS), 1)


def total_mass():
    return round(steel_mass() + sum(n * m for _, _, _, n, _, m in BOUGHT), 1)


def rows():
    out = []
    for num, mark, name, n, mat, m in PARTS + BOUGHT:
        out.append(dict(pos=num, mark=mark, name=name, n=n, material=mat,
                        mass=m, total=round(n * m, 1),
                        kind="деталь" if mark != "—" else "покупное"))
    return out


def report():
    """Полная сводка по узлу: геометрия, массы, нагрузки, проверки."""
    return dict(
        mark=MARK, name=NAME, steel=STEEL,
        geometry=dict(x0=X0, x1=X1, y0=Y0, y1=Y1, z_tray=Z_TRAY, z_top=Z_TOP,
                      z_equip=Z_EQUIP, stack=STACK, z_tank_top=Z_TANK_TOP,
                      h_beam=H_BEAM, n_long=N_LONG, n_cross=N_CROSS,
                      pitch_long=PITCH_LONG, pitch_cross=PITCH_CROSS,
                      coaming=TRAY_COAMING),
        units=UNITS, masses=masses(), loads=loads(),
        beam=beam_check(), weld=weld_check(), bolt=bolt_check(),
        isolator=isolator_check(),
        spec=rows(), steel_mass=steel_mass(), total_mass=total_mass())


def checks():
    """Итоговые проверки узла одной таблицей."""
    b, w, bo, iso = beam_check(), weld_check(), bolt_check(), isolator_check()
    return [
        ("Балка фундамента, экв. напряжение", b["sigma_eq"], b["sigma_allow"],
         "МПа", b["sigma_eq"] <= b["sigma_allow"]),
        ("Балка фундамента, касательное", b["tau"], b["tau_allow"],
         "МПа", b["tau"] <= b["tau_allow"]),
        ("Прогиб балки", b["f_mm"], b["f_allow"], "мм", b["f_mm"] <= b["f_allow"]),
        ("Поясной шов, катет %g мм" % w["kf_mm"], w["tau_flange"], w["allow"],
         "МПа", w["tau_flange"] <= w["allow"]),
        ("Шов приварки к флору", w["tau_node"], w["allow"], "МПа",
         w["tau_node"] <= w["allow"]),
        ("Болт М20 кл. 8.8, экв. напряжение", bo["sigma_eq"], bo["allow"],
         "МПа", bo["sigma_eq"] <= bo["allow"]),
        ("Амортизатор, статическая доля", iso["static"], iso["rated"],
         "кгс", iso["static"] <= iso["rated"]),
        ("Амортизатор, динамическая нагрузка", iso["dynamic"],
         iso["rated"] * 1.5, "кгс", iso["dynamic"] <= iso["rated"] * 1.5),
        ("Отстройка от частоты ГДГ", iso["ratio_dg"], 2.0, "раз",
         iso["ratio_dg"] >= 2.0),
        ("Отстройка от лопастной частоты", iso["ratio_blade"], 2.0, "раз",
         iso["ratio_blade"] >= 2.0),
    ]
