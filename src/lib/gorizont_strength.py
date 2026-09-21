# -*- coding: utf-8 -*-
"""Общая продольная прочность «Волжского Горизонта».

Расчёт ведётся так, как его ставят в курсе строительной механики корабля
СПбГМТУ, и без единого «взятого из справочника» коэффициента для момента:

  1. Строевая нагрузки масс w(x) — из таблицы нагрузки `gorizont_hydro`,
     каждая группа распределена по своей длине, корпус — по площади
     сечения обшивки.
  2. Строевая сил поддержания b(x) = ро * omega(x) — из обводов.
  3. Судно уравновешивается на тихой воде и на волне: подбираются
     погружение и угол дифферента так, чтобы сходились и водоизмещение,
     и абсцисса центра величины.
  4. q(x) = w(x) - b(x), перерезывающая сила N(x) = интеграл q,
     изгибающий момент M(x) = интеграл N.
  5. Волна длиной в длину судна, высотой по классу РРР: для класса «М»
     h = 3.0 м. Считаются оба случая: вершина на миделе (перегиб) и
     подошва на миделе (прогиб).
  6. Напряжения по моменту сопротивления эквивалентного бруса из
     `gorizont_struct`.

Массы в тоннах, силы в кН, моменты в кН*м, напряжения в МПа.
"""
import math
from . import gorizont as G
from . import gorizont_hydro as H
from . import gorizont_struct as S

GRAV = 9.81


def _buoyancy(xs, z0, theta, wave_amp=0.0, wave_x0=0.0, wave_len=None):
    """Строевая сил поддержания, т/м."""
    if wave_len is None:
        wave_len = G.LOA
    out = []
    for x in xs:
        zw = z0 + theta * (x - G.LOA / 2.0)
        if wave_amp:
            zw += wave_amp * math.cos(2.0 * math.pi * (x - wave_x0) / wave_len)
        out.append(H.RHO * H.section_area(x, max(zw, 0.0)))
    return out


def balance(xs, D, xg, wave_amp=0.0, wave_x0=0.0, iters=60):
    """Погружение и дифферент, при которых сходятся водоизмещение и ЦВ."""
    z0 = H.equilibrium()["T"]
    theta = 0.0
    for _ in range(iters):
        b = _buoyancy(xs, z0, theta, wave_amp, wave_x0)
        V = H._trapz(b, xs)
        xc = H._trapz([q * x for q, x in zip(b, xs)], xs) / max(V, 1e-9)
        dV = D - V
        dX = xg - xc
        h = H.hydrostatics(max(z0, 0.4))
        z0 += 0.8 * dV / max(h["Aw"], 1.0)
        theta += 0.8 * dX * D / max(h["MCT"] * 100.0 * h["Lw"], 1.0)
        if abs(dV) < 0.3 and abs(dX) < 0.005:
            break
    b = _buoyancy(xs, z0, theta, wave_amp, wave_x0)
    return b, z0, theta


def _integrate(xs, q):
    N = [0.0]
    for i in range(len(xs) - 1):
        N.append(N[-1] + 0.5 * (q[i] + q[i + 1]) * (xs[i + 1] - xs[i]))
    M = [0.0]
    for i in range(len(xs) - 1):
        M.append(M[-1] + 0.5 * (N[i] + N[i + 1]) * (xs[i + 1] - xs[i]))
    return N, M


def case(condition="тихая вода", step=0.5, cls=None):
    """Расчёт одного случая нагружения."""
    cls = cls or H.CLASS
    xs = H._xs(step)
    w = H.weight_distribution(xs)
    ws = H.weight_summary()
    D, xg = ws["D"], ws["xg"]
    hw = H.WAVE_HEIGHT[cls]
    if condition == "тихая вода":
        amp, x0 = 0.0, 0.0
    elif condition == "перегиб":
        amp, x0 = hw / 2.0, G.LOA / 2.0
    elif condition == "прогиб":
        amp, x0 = -hw / 2.0, G.LOA / 2.0
    else:
        raise ValueError(condition)
    b, z0, theta = balance(xs, D, xg, amp, x0)
    q = [(wi - bi) * GRAV for wi, bi in zip(w, b)]
    N, M = _integrate(xs, q)
    n_end, m_end = N[-1], M[-1]
    L = xs[-1] - xs[0]
    N = [n - n_end * (x - xs[0]) / L for n, x in zip(N, xs)]
    M = [m - m_end * (x - xs[0]) / L for m, x in zip(M, xs)]
    i_max = max(range(len(M)), key=lambda i: abs(M[i]))
    return dict(condition=condition, xs=xs, w=w, b=b, q=q, N=N, M=M,
                z0=z0, theta=theta, D=D, xg=xg,
                M_max=M[i_max], x_M_max=xs[i_max],
                N_max=max(N, key=abs), wave=hw if amp else 0.0)


def stresses(cls=None, grade="09Г2С"):
    """Напряжения в палубе и днище по всем случаям нагружения."""
    cls = cls or H.CLASS
    g = S.equivalent_girder()
    st = S.STEEL[grade]
    sig_allow = 0.60 * st["ReH"]
    rows = []
    for cond in ("тихая вода", "перегиб", "прогиб"):
        c = case(cond, cls=cls)
        M = c["M_max"]
        sd = abs(M) / g["W_deck_m3"] / 1000.0
        sb = abs(M) / g["W_bot_m3"] / 1000.0
        rows.append(dict(condition=cond, M=M, x=c["x_M_max"],
                         N=c["N_max"], sigma_deck=sd, sigma_bot=sb,
                         ok=max(sd, sb) <= sig_allow, case=c))
    return dict(rows=rows, girder=g, sigma_allow=sig_allow, steel=st)


# ----------------------------------------------- местная прочность, деталь
# Кница спонсона шлюпочной палубы. Она держит консоль, на которой стоит
# шлюпка на 100 человек и шлюпбалка, и работает на изгиб от их веса.
# Это та деталь, на которую делается чертёж и расчёт по конкурсному заданию.
BRACKET = dict(
    name="Кница спонсона шлюпочной палубы",
    mark="ВГ-2026.15.01",
    material="09Г2С",
    t=10.0,                 # толщина стенки, мм
    a=1.15,                 # вылет консоли от борта надстройки, м
    h_root=0.42,            # высота стенки в корне, м
    h_tip=0.16,             # высота стенки на конце, м
    flange_b=80.0,          # ширина пояска, мм
    flange_t=10.0,          # толщина пояска, мм
    corrosion=1.5,          # припуск на коррозию, мм
    pitch=2.20,             # шаг книц по длине, м
    boat_mass=9.8,          # шлюпка на 100 чел. с людьми и снабжением, т
    boat_span=8.6,          # длина шлюпки, м
    crowd=4.0,              # расчётная нагрузка на палубу, кПа
    k_dyn=2.2,              # испытательная нагрузка спускового устройства
)


def bracket_check(br=None, corroded=False):
    """Проверка кницы спонсона на изгиб, срез и устойчивость стенки."""
    b = dict(BRACKET) if br is None else dict(br)
    st = S.STEEL[b["material"]]
    dt = b.get("corrosion", 0.0) if corroded else 0.0
    n_br = max(2, int(round(b["boat_span"] / b["pitch"])) + 1)
    p_boat = b["boat_mass"] * GRAV / n_br * b["k_dyn"]        # кН
    p_deck = b["crowd"] * b["a"] * b["pitch"]                 # кН
    P = p_boat + p_deck
    arm = 0.62 * b["a"]
    M = P * arm                                               # кН*м

    tw = (b["t"] - dt) / 1000.0
    hw = b["h_root"]
    bf, tf = b["flange_b"] / 1000.0, (b["flange_t"] - dt) / 1000.0
    Aw, Af = hw * tw, bf * tf
    A = Aw + Af
    z_w, z_f = hw / 2.0, hw + tf / 2.0
    z0 = (Aw * z_w + Af * z_f) / A
    I = (tw * hw ** 3 / 12.0 + Aw * (z_w - z0) ** 2
         + bf * tf ** 3 / 12.0 + Af * (z_f - z0) ** 2)
    W_min = I / max(z0, hw + tf - z0)
    sigma = M / W_min / 1000.0
    tau = P / (Aw * 1000.0)
    sig_eq = math.sqrt(sigma ** 2 + 3 * tau ** 2)
    sig_allow = 0.65 * st["ReH"]
    tau_allow = 0.40 * st["ReH"]
    sigma_e = 0.9 * 4.0 * st["E"] * (tw / hw) ** 2
    sigma_cr = sigma_e if sigma_e <= 0.5 * st["ReH"] else \
        st["ReH"] * (1.0 - st["ReH"] / (4.0 * sigma_e))
    mass = ((0.5 * (b["h_root"] + b["h_tip"]) * b["a"] * tw)
            + bf * tf * b["a"]) * S.RHO_STEEL * 1000.0
    # сварной шов по корню: катет 6 мм, двусторонний
    kf = 0.006
    l_weld = 2.0 * (hw + bf)
    tau_weld = P / (0.7 * kf * l_weld * 1000.0)
    return dict(bracket=b, n_brackets=n_br, P=P, M=M, arm=arm,
                p_boat=p_boat, p_deck=p_deck,
                A_cm2=A * 1e4, I_cm4=I * 1e8, W_cm3=W_min * 1e6,
                sigma=sigma, tau=tau, sigma_eq=sig_eq,
                sigma_allow=sig_allow, tau_allow=tau_allow,
                sigma_cr=sigma_cr, tau_weld=tau_weld,
                mass_kg=mass, steel=st, corroded=corroded,
                ok=(sig_eq <= sig_allow and tau <= tau_allow
                    and sigma <= sigma_cr and tau_weld <= 0.6 * tau_allow * 2))


def report(cls=None):
    return dict(stresses=stresses(cls), bracket=bracket_check(),
                bracket_corroded=bracket_check(corroded=True))
