# -*- coding: utf-8 -*-
"""Сравнение движительных комплексов: один вал против двух.

Модуль отвечает на вопрос «почему два вала» не одним доводом, а таблицей:
считаются оба варианта в условиях НАШЕГО проекта — при осадке 2.17 м,
скорости 22 км/ч и фарватере, который на трассе бывает восьмиметровым.

Варианты специально даны в лучшем для одновального решения виде: ему
отданы и предельный по заглублению винт, и вариант с тоннельной кормой,
где кромка диска выходит к самой ватерлинии. Сравнивать надо сильнейшую
версию чужого решения, иначе обоснование не стоит ничего.

Метод. Площадь диска и нагрузка Ct = T / (0.5·ρ·A·Vₐ²) считаются по
буксировочному сопротивлению из gorizont_hydro. Идеальный КПД
η = 2/(1+√(1+Ct)) абсолютной величины не даёт, но корректно сравнивает
варианты: весь выигрыш второго вала сидит именно в площади диска.
Пропульсивный коэффициент варианта масштабируется от принятого
ηd = 0.62 по отношению идеальных КПД.
"""
import math

from . import gorizont as G
from . import gorizont_hydro as H
from . import gorizont_mach as M
from . import gorizont_power as P

T_DEDUCTION = P.T_DEDUCTION
WAKE = P.WAKE
ETA_D_BASE = 0.62          # пропульсивный коэффициент принятого варианта
ETA_SHAFT = 0.97

#: Практический предел удельной нагрузки диска для речного винта, кВт/м².
#: Выше начинается эрозионная кавитация и вибрация корпуса; для судна,
#: у которого над винтами каюты первой палубы, это ограничение жёсткое.
POWER_DENSITY_LIMIT = 1000.0

#: Удельный расход дизель-генератора: на валу дизеля и на шинах ГРЩ.
SFOC_ENGINE = 195.0        # г/(кВт·ч) при загрузке 75…85 %
GEN_EFF = 0.96
SFOC_BUS = SFOC_ENGINE / GEN_EFF

#: Суточный профиль круизного дня на Волге, часов.
DAY_PROFILE = [("ход", 14.0), ("манёвры", 1.0), ("стоянка", 9.0)]
SEASON_DAYS = 180          # навигация на ЕГС, суток

#: Разнос линий вала от ДП — из перечня машинного отделения.
SHAFT_OFFSET = 3.00
#: Упор подруливающего на киловатт и доля упора заднего хода от переднего.
THRUSTER_THRUST_KN_KW = 0.125
ASTERN_FRACTION = 0.70

#: Коэффициент качества реального движителя на швартовах по отношению к
#: идеальному диску; насадка Корт добавляет упор на малом ходу.
BOLLARD_QUALITY = 0.62
NOZZLE_BOLLARD_GAIN = 1.27


def tip_immersion(diameter, axis=None, draft=None):
    """Заглубление верхней кромки диска: метры и доли диаметра."""
    axis = G.SHAFT_Z_PROP if axis is None else axis
    draft = H.equilibrium()["T"] if draft is None else draft
    tip = axis + diameter / 2.0
    return dict(tip=tip, immersion=draft - tip,
                ratio=(draft - tip) / diameter, draft=draft)


VARIANTS = [
    dict(code="А", shafts=1, nozzle=False, tunnel=False,
         name="Один вал, открытый винт",
         note="диаметр — предельный по заглублению 0.15·D, без тоннеля"),
    dict(code="Б", shafts=1, nozzle=True, tunnel=True, diameter=2.10,
         name="Один вал, винт в насадке, тоннельная корма",
         note="кромка диска у самой ватерлинии, тоннель держит воду"),
    dict(code="В", shafts=2, nozzle=True, tunnel=True,
         diameter=G.PROP_DIAMETER, accepted=True,
         name="Два вала, винты в насадках (принят)",
         note="диаметр с запасом по заглублению 0.19·D"),
]


def variant_geometry(v):
    d = v.get("diameter") or P.max_propeller_diameter()
    imm = tip_immersion(d)
    area = v["shafts"] * math.pi / 4.0 * d ** 2
    return d, area, imm


def hydrodynamics(v, v_kmh=22.0, depth=None):
    """Нагрузка диска, идеальный и пропульсивный КПД варианта."""
    d, area, imm = variant_geometry(v)
    r = H.power(v_kmh, depth=depth)
    thrust = r["R"] / (1.0 - T_DEDUCTION)
    va = r["v"] * (1.0 - WAKE)
    ct = thrust * 1000.0 / (0.5 * 1000.0 * area * va ** 2)
    eta_i = 2.0 / (1.0 + math.sqrt(1.0 + ct))
    return dict(d=d, area=area, immersion=imm, thrust=thrust, va=va,
                ct=ct, eta_i=eta_i)


REFERENCE_POWER = H.PROP_POWER      # 3600 кВт — установленная у принятого варианта


def _base_eta_i(v_kmh=22.0, depth=None):
    """Идеальный КПД принятого варианта в ТЕХ ЖЕ условиях.

    Сравнивать надо при одной глубине: на мелководье упор больше, нагрузка
    диска выше и идеальный КПД ниже у всех вариантов сразу. Если брать
    базу по глубокой воде, принятый вариант перестанет сходиться с
    gorizont_hydro, и записка разойдётся сама с собой.
    """
    accepted = next(v for v in VARIANTS if v.get("accepted"))
    return hydrodynamics(accepted, v_kmh, depth)["eta_i"]


def eta_d(v, v_kmh=22.0, depth=None):
    """Пропульсивный коэффициент варианта в этих условиях."""
    h = hydrodynamics(v, v_kmh, depth)
    return ETA_D_BASE * h["eta_i"] / _base_eta_i(v_kmh, depth)


def required_power(v, v_kmh=22.0, depth=None):
    """Мощность на фланцах валов для этой скорости, кВт.

    Для принятого варианта сводится ровно к gorizont_hydro.power().
    """
    r = H.resistance(v_kmh, depth=depth)
    pe = r["R"] * r["v"]
    return pe / eta_d(v, v_kmh, depth) / ETA_SHAFT


def speed_at(v, power, depth=None):
    """Скорость, которую вариант даёт на заданной мощности валов."""
    lo, hi = 4.0, 40.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if required_power(v, mid, depth) < power:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def power_for_reference_speed(v):
    """Сколько надо поставить, чтобы догнать принятый вариант по скорости."""
    accepted = next(x for x in VARIANTS if x.get("accepted"))
    target = speed_at(accepted, REFERENCE_POWER)
    lo, hi = 500.0, 12000.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if speed_at(v, mid) < target:
            lo = mid
        else:
            hi = mid
    return 100.0 * math.ceil(0.5 * (lo + hi) / 100.0)


def power_density(v, power=None):
    _d, area, _i = variant_geometry(v)
    return (REFERENCE_POWER if power is None else power) / area


def cavitation_power(v):
    """Мощность, которую диск примет, не выходя за предел нагрузки."""
    _d, area, _i = variant_geometry(v)
    return POWER_DENSITY_LIMIT * area


def cavitation_speed(v, depth=None):
    """Скорость, ограниченная не мотором, а нагрузкой диска."""
    return speed_at(v, min(cavitation_power(v), REFERENCE_POWER), depth)


def bollard_pull(v, power=None):
    """Упор на швартовах, кН — оценка по идеальному диску с поправками.

    Нужна не ради цифры, а ради сравнения: в камере шлюза и при отходе от
    необорудованного берега тяга на малом ходу важнее скорости.
    """
    _d, area, _i = variant_geometry(v)
    p = (REFERENCE_POWER if power is None else power) * 1000.0 * ETA_SHAFT
    ideal = (2.0 * 1000.0 * area * p ** 2) ** (1.0 / 3.0)
    gain = NOZZLE_BOLLARD_GAIN if v["nozzle"] else 1.0
    return ideal * BOLLARD_QUALITY * gain / 1000.0


def speed_on_one_shaft(v, depth=None):
    """Скорость при отказе одной линии вала.

    У одновального варианта это ноль: судно теряет ход целиком. У
    двухвального работает один винт — и работает хуже, потому что весь
    упор идёт через половину площади диска; плюс надбавка 8 % на
    сопротивление застопоренного винта и на постоянную перекладку руля.
    """
    if v["shafts"] == 1:
        return 0.0
    half = dict(v, shafts=1)
    avail = REFERENCE_POWER / v["shafts"]
    lo, hi = 3.0, 40.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if required_power(half, mid, depth) * 1.08 < avail:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# --- Масса комплекса --------------------------------------------------------

def _mach_mass(code):
    for c, _name, n, _b, _mir, _p, m, _note in M.EQUIPMENT:
        if c == code:
            return n * m
    return 0.0


ACCEPTED_MASS = {code: _mach_mass(code) for code in ("ГЭД", "ВАЛ", "ВФШ", "РУЛЬ")}


def complex_mass(v):
    """Масса ГЭД, валопроводов, винтов и рулей, т.

    Одновальный вариант считается пересчётом от принятого: масса
    электродвигателя растёт как P^0.8, диаметр вала — как корень кубический
    из момента, масса вала — как квадрат диаметра, масса винта — как куб
    диаметра. Один вал легче двух, и это его единственное настоящее
    преимущество; прятать его незачем.
    """
    d, _area, _i = variant_geometry(v)
    if v["shafts"] == 2:
        return dict(ACCEPTED_MASS, total=round(sum(ACCEPTED_MASS.values()), 1))
    p_unit = REFERENCE_POWER
    motor = ACCEPTED_MASS["ГЭД"] / 2.0 * (p_unit / G.PROP_MOTOR_POWER) ** 0.8
    shaft = ACCEPTED_MASS["ВАЛ"] / 2.0 * (p_unit / G.PROP_MOTOR_POWER) ** (2.0 / 3.0)
    prop = ACCEPTED_MASS["ВФШ"] / 2.0 * (d / G.PROP_DIAMETER) ** 3
    # руль у одновального один, но крупнее: площадь пера считается от
    # площади диаметральной плоскости, а она от числа валов не зависит
    rudder = ACCEPTED_MASS["РУЛЬ"] / 2.0 * 1.35
    out = dict(ГЭД=round(motor, 1), ВАЛ=round(shaft, 1),
               ВФШ=round(prop, 1), РУЛЬ=round(rudder, 1))
    out["total"] = round(sum(out.values()), 1)
    return out


# --- Топливо ----------------------------------------------------------------

def daily_fuel(v):
    """Расход топлива за типовой круизный день, т.

    Гостиничная часть от варианта не зависит, движительная — обратно
    пропорциональна пропульсивному коэффициенту в своём режиме.
    """
    kwh = 0.0
    for mode, hours in DAY_PROFILE:
        b = P.balance(mode)
        depth = next((d for k, _n, _v, d in P.MODES if k == mode), None)
        scale = ETA_D_BASE / eta_d(v, 22.0, depth)
        kwh += hours * (b["hotel"] + b["propulsion"] * scale)
    return kwh * SFOC_BUS / 1e6


def fuel_autonomy(v):
    """Автономность по запасу топлива, суток."""
    mass = G.FUEL_M3 * G.FUEL_RHO
    return mass / daily_fuel(v)


# --- Энергетическая установка под вариант -----------------------------------

def plant(v):
    """Сколько и каких ГДГ требует вариант.

    Единичная мощность подбирается по той же проверке, что и в
    электробалансе: при отказе одной машины судно обязано держать
    служебные 22 км/ч на восьмиметровом фарватере.
    """
    b = P.balance("мелководье")
    scale = ETA_D_BASE / eta_d(v, 22.0, 8.0)
    total = b["hotel"] + b["propulsion"] * scale
    for unit in (1200, 1400, 1600, 1800, 2000, 2200, 2500):
        avail = 0.9 * 2 * unit - b["hotel"]
        shaft = max(avail, 0.0) * P.ETA_DRIVE
        lo, hi = 5.0, 40.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if required_power(v, mid, 8.0) < shaft:
                lo = mid
            else:
                hi = mid
        if 0.5 * (lo + hi) >= G.SPEED_KMH:
            return dict(unit=unit, count=3, total=round(total, 1),
                        installed=3 * unit,
                        load=round(100.0 * total / (2 * unit), 1),
                        n1_speed=round(0.5 * (lo + hi), 1))
    return dict(unit=None, count=3, total=round(total, 1), installed=None,
                load=None, n1_speed=None)


def plant_mass(v):
    """Масса главных дизель-генераторов под этот вариант, т.

    Считать массу одного движительного комплекса нечестно: одновальный
    вариант экономит на валопроводе, но требует более крупной станции —
    и выигрыш возвращается обратно через фундаменты ГДГ.
    """
    unit = plant(v)["unit"]
    base = next(e[6] for e in M.EQUIPMENT if e[0] == "ГДГ-1")
    return round(3.0 * base * (unit / G.DG_POWER) ** 0.85, 1)


def season_fuel(v):
    """Расход топлива за навигацию, т."""
    return daily_fuel(v) * SEASON_DAYS


def turning_moment(v):
    """Разворачивающий момент на месте, кН·м: враздрай плюс подруливающие.

    Это единственная численная мера управляемости, которую можно получить
    без модельных испытаний, и для шлюза она и есть главная: судно должно
    доворачиваться в камере шириной %s м без буксира.
    """ % ("%.1f" % G.LOCK_WIDTH)
    per_shaft = bollard_pull(v) / v["shafts"]
    if v["shafts"] >= 2:
        screws = per_shaft * (1.0 + ASTERN_FRACTION) * SHAFT_OFFSET
    else:
        screws = 0.0
    mid = G.LOA / 2.0
    thrusters = sum(th["power"] * THRUSTER_THRUST_KN_KW * abs(th["x"] - mid)
                    for th in G.THRUSTERS.values())
    return dict(screws=round(screws, 0), thrusters=round(thrusters, 0),
                total=round(screws + thrusters, 0),
                screw_share=round(100.0 * screws / (screws + thrusters), 0))


def compare(v_kmh=22.0):
    """Сравнение при ОДИНАКОВОЙ установленной мощности 3600 кВт.

    Иначе сравниваются разные суда: вариант, которому дали больше мотора,
    всегда быстрее. Одинаковая мощность — это одинаковые деньги и
    одинаковый габарит машинного отделения; что на них получается — и есть
    предмет сравнения. Отдельной строкой показано, сколько пришлось бы
    поставить одновальному, чтобы догнать по скорости.
    """
    rows = []
    for v in VARIANTS:
        h = hydrodynamics(v, v_kmh)
        pl = plant(v)
        mass = complex_mass(v)
        rows.append(dict(
            code=v["code"], name=v["name"], note=v["note"],
            accepted=bool(v.get("accepted")), shafts=v["shafts"],
            nozzle=v["nozzle"], tunnel=v["tunnel"],
            d=round(h["d"], 2), area=round(h["area"], 2),
            tip=round(h["immersion"]["tip"], 2),
            immersion=round(h["immersion"]["immersion"], 2),
            imm_ratio=round(h["immersion"]["ratio"], 3),
            imm_ok=h["immersion"]["ratio"] >= 0.15,
            ct=round(h["ct"], 2), eta_i=round(h["eta_i"], 3),
            eta_d=round(eta_d(v, v_kmh), 3),
            pb22=round(required_power(v, 22.0), 0),
            pb24=round(required_power(v, 24.0), 0),
            pb22_shallow=round(required_power(v, 22.0, depth=8.0), 0),
            installed=REFERENCE_POWER,
            density=round(power_density(v), 0),
            density_ok=power_density(v) <= POWER_DENSITY_LIMIT,
            cav_power=round(cavitation_power(v), 0),
            cav_speed=round(cavitation_speed(v), 1),
            bollard=round(bollard_pull(v), 0),
            vmax=round(speed_at(v, REFERENCE_POWER), 1),
            v_shallow=round(speed_at(v, REFERENCE_POWER, depth=8.0), 1),
            v_one_shaft=round(speed_on_one_shaft(v), 1),
            need_power=power_for_reference_speed(v),
            mass=mass["total"], mass_rows=mass,
            dg_unit=pl["unit"], dg_installed=pl["installed"],
            dg_load=pl["load"], n1_speed=pl["n1_speed"],
            fuel_day=round(daily_fuel(v), 2),
            fuel_days=round(fuel_autonomy(v), 1),
            fuel_season=round(season_fuel(v), 0),
            plant_mass=plant_mass(v),
            total_mass=round(mass["total"] + plant_mass(v), 1),
            moment=turning_moment(v),
        ))
    return rows


def deltas():
    """Отклонения вариантов от принятого — то, чем и заканчивается анализ."""
    rows = compare()
    acc = next(r for r in rows if r["accepted"])
    out = []
    for r in rows:
        if r["accepted"]:
            continue
        out.append(dict(
            code=r["code"], name=r["name"],
            speed=round(r["cav_speed"] - acc["cav_speed"], 1),
            need_power=round(100.0 * (r["need_power"] / acc["installed"] - 1.0), 1),
            fuel=round(100.0 * (r["fuel_day"] / acc["fuel_day"] - 1.0), 1),
            mass=round(r["mass"] - acc["mass"], 1),
            total_mass=round(r["total_mass"] - acc["total_mass"], 1),
            fuel_season=round(r["fuel_season"] - acc["fuel_season"], 0),
            bollard=round(100.0 * (r["bollard"] / acc["bollard"] - 1.0), 1),
            density=round(100.0 * (r["density"] / acc["density"] - 1.0), 1),
            immersion_ok=r["imm_ok"], density_ok=r["density_ok"],
            v_one_shaft=r["v_one_shaft"],
        ))
    return out
