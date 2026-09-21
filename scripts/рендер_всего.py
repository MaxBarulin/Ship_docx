# -*- coding: utf-8 -*-
r"""Пакетный рендер всей графики в отдельном процессе Blender.

Запускать только так — фоновым процессом, а не в открытом Blender:

    blender -b blender/gorizont.blend --python scripts/рендер_всего.py -- каюты виды

Причина простая: рендер одной каюты идёт полторы минуты, всей графики —
около часа, и если гнать это в таймере интерактивного Blender, окно всё
это время висит с надписью «не отвечает». Отдельный процесс читает
сохранённый файл, считает и пишет картинки, а рабочий Blender остаётся
живым.

Без аргументов делает всё. Аргументы после `--`: каюты, интерьеры, виды,
планы, разрез, схемы. Через двоеточие можно назвать один кадр:
`интерьеры:7_носовой_салон`.
"""
import bpy, sys, os, time, io, json

ROOT = r"E:\Ship_docx"
SC = os.path.join(ROOT, "scripts")
sys.path.insert(0, os.path.join(ROOT, "src"))
LOG = r"F:\Temp\claude\gor\рендер_всего.json"

STEPS = [
    ("каюты", "blender_рендер_кают.py", "render_all", {}),
    ("интерьеры", "blender_рендер_интерьеров.py", "render_rooms", {}),
    ("виды", "blender_рендер_видов.py", "render_views", {}),
    ("планы", "blender_рендер_планов.py", "render_plans", {}),
    ("разрез", "blender_рендер_планов.py", "render_section", {}),
    ("схемы", "blender_рендер_схем.py", "render_schemes", {}),
]


def run(path, fn, **kw):
    g = {"__name__": "__main__"}
    exec(compile(io.open(path, encoding="utf-8").read(), path, "exec"), g)
    return g[fn](verbose=True, **kw)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    # аргумент вида «интерьеры:7_носовой_салон» ограничивает шаг одним кадром
    want, only = {}, {}
    for a in argv:
        step, _, sub = a.partition(":")
        want[step] = True
        if sub:
            only.setdefault(step, []).append(sub)
    if not want:
        want = {s[0]: True for s in STEPS}
    rep, t0 = {}, time.time()
    for name, script, fn, kw in STEPS:
        if name not in want:
            continue
        t1 = time.time()
        print("### старт %s" % name, flush=True)
        try:
            if only.get(name):
                kw = dict(kw, only=only[name])
            r = run(os.path.join(SC, script), fn, **kw)
            rep[name] = {"файлов": len(r) if isinstance(r, list) else 1,
                         "сек": round(time.time() - t1, 1)}
        except Exception:
            import traceback
            rep[name] = {"ошибка": traceback.format_exc()[-1500:]}
        print("### %s: %s" % (name, rep[name]), flush=True)
        io.open(LOG, "w", encoding="utf-8").write(
            json.dumps(rep, ensure_ascii=False, indent=1))
    rep["итого_сек"] = round(time.time() - t0, 1)
    io.open(LOG, "w", encoding="utf-8").write(
        json.dumps(rep, ensure_ascii=False, indent=1))
    print("### всё:", rep["итого_сек"], "с", flush=True)


main()
