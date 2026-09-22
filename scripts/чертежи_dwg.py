# -*- coding: utf-8 -*-
"""Чертежи ОР в DWG: пакетная конвертация DXF → DWG через AutoCAD Core Console.

    python scripts/чертежи_dwg.py            # все CAD/ВГ-2026_ОР-*.dxf → CAD/DWG/*.dwg
    python scripts/чертежи_dwg.py --все      # и узел ВГ-2026_31_00_СБ тоже

Свободных библиотек, пишущих DWG, нет; AutoCAD 2023 на машине есть, а с ним —
accoreconsole.exe, безоконный движок AutoCAD, который открывает DXF и
сохраняет DWG командой SAVEAS по сценарию. Формат 2018 читают AutoCAD
и nanoCAD 22 (у команды стоит и то и другое).

Два подводных камня, оплаченные часом отладки:
  * запускать надо не из Git Bash: MSYS переписывает ключи `/i` и `/s` в
    пути вида `C:/Program Files/Git/i`, и консоль молча ждёт команды до
    таймаута. Из Python через subprocess ключи доходят как есть;
  * во входных именах не должно быть кириллицы — Core Console берёт путь из
    сценария в кодировке ANSI. Поэтому файл копируется под ASCII-именем во
    временную папку, а результат переименовывается обратно.
"""
import os, sys, glob, shutil, subprocess, tempfile, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "CAD")
OUT = os.path.join(ROOT, "CAD", "DWG")
ACC = r"C:\Program Files\Autodesk\AutoCAD 2023\accoreconsole.exe"
ФОРМАТ = "2018"


def конвертировать(dxf, dwg, таймаут=180):
    tmp = tempfile.mkdtemp(prefix="dwg_")
    try:
        src = os.path.join(tmp, "in.dxf")
        dst = os.path.join(tmp, "out.dwg")
        shutil.copyfile(dxf, src)
        scr = os.path.join(tmp, "conv.scr")
        with open(scr, "w", encoding="ascii", newline="\r\n") as f:
            f.write("_.SAVEAS\n%s\n%s\n_.QUIT\n_Y\n" % (ФОРМАТ, dst))
        t0 = time.time()
        try:
            subprocess.run([ACC, "/i", src, "/s", scr, "/l", "ru-RU"], cwd=tmp,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=таймаут)
        except subprocess.TimeoutExpired:
            pass                      # файл уже записан, консоль зависла на QUIT
        if not os.path.exists(dst):
            raise RuntimeError("Core Console не записал %s" % os.path.basename(dxf))
        os.makedirs(os.path.dirname(dwg), exist_ok=True)
        shutil.move(dst, dwg)
        return round(time.time() - t0, 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(все=False):
    if not os.path.exists(ACC):
        print("нет AutoCAD Core Console:", ACC); return 1
    os.makedirs(OUT, exist_ok=True)
    маска = "*.dxf" if все else "ВГ-2026_ОР-*.dxf"
    # листы ОР — в CAD/DWG; листы РТ — в CAD/DWG/расчёты; листы МР (модульное решение) — в CAD/DWG/модули
    задания = [(dxf, OUT) for dxf in sorted(glob.glob(os.path.join(SRC, маска)))]
    задания += [(dxf, os.path.join(OUT, "расчёты")) for dxf in sorted(glob.glob(os.path.join(SRC, "расчёты", "*.dxf")))]
    задания += [(dxf, os.path.join(OUT, "модули")) for dxf in sorted(glob.glob(os.path.join(SRC, "модули", "*.dxf")))]
    ошибок = 0
    for dxf, out_dir in задания:
        dwg = os.path.join(out_dir, os.path.splitext(os.path.basename(dxf))[0] + ".dwg")
        try:
            dt = конвертировать(dxf, dwg)
            print("%-48s %6d КБ  %5.1f с" % (os.path.relpath(dwg, OUT), os.path.getsize(dwg) // 1024, dt))
        except Exception as e:
            ошибок += 1
            print("ОШИБКА", os.path.basename(dxf), e)
    return 1 if ошибок else 0


if __name__ == "__main__":
    sys.exit(main("--все" in sys.argv))
