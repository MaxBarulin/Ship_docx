# Ship_docx

CAD-рабочее пространство с установленной библиотекой скиллов
[earthtojake/text-to-cad](https://github.com/earthtojake/text-to-cad) (v0.5.1).

## Что установлено

Скиллы лежат в `.agents/skills/` (универсальный формат) и подключены к Claude
Code симлинками из `.claude/skills/`. Состав зафиксирован в `skills-lock.json`.

| Скилл | Назначение |
| --- | --- |
| `cad` | Параметрические детали и сборки, STEP как основной вывод, плюс STL/3MF/GLB |
| `cad-viewer` | Локальный браузерный просмотр CAD- и робот-файлов |
| `dxf` | 2D-чертежи: профили, шаблоны, прокладки, раскладки под раскрой |
| `step-parts` | Поиск покупных STEP-моделей: крепёж, подшипники, моторы, разъёмы |
| `urdf` / `srdf` / `sdf` | Описания роботов, планировочные группы MoveIt, миры симулятора |
| `dfam-check` | Проверка печатопригодности сетки: стенки, нависания, ориентация |
| `gcode` | Слайсинг мешей в `.gcode` через реальные CLI слайсеров |
| `sendcutsend` | Проверка DXF/STEP перед загрузкой в SendCutSend |
| `bambu-labs` | Отправка и запуск заданий печати на принтерах Bambu Lab |

Python-рантайм (`cadgen` и зависимости) ставится в `.venv/` — он не в git.

## Запуск

Окружение восстанавливается автоматически хуком `SessionStart`
(`.claude/settings.json`). Вручную — тем же скриптом:

```bash
bash scripts/setup-cad.sh
```

Скрипт идемпотентен: на готовом окружении отрабатывает за пару секунд, с нуля —
около минуты.

Проверка, что версия `cadgen` совпадает с пином скилла:

```bash
.venv/bin/cadgen doctor .agents/skills/cad
```

## Как считать деталь

Модель — обычный Python-скрипт с декоратором; сборку запускает вызов из
`__main__`:

```python
from cadgen import build123d as bd
from cadgen import step


@step
def bracket():
    plate = bd.Box(40, 25, 4)
    hole = bd.Cylinder(2.25, 8)
    return plate - bd.Pos(-12, 0, 0) * hole - bd.Pos(12, 0, 0) * hole


if __name__ == "__main__":
    bracket()
```

```bash
.venv/bin/python bracket.py                          # -> bracket.step
.venv/bin/cadgen step snapshot bracket.step out.png  # PNG-рендер для проверки
.venv/bin/cadgen step inspect bracket.step --help    # замеры и селекторы
.venv/bin/cadgen viewer                              # просмотр в браузере
```

## Рендеринг и Chromium

Снимки и вьюер рисуются headless-Chromium через Playwright, а Playwright
запускает только ту сборку браузера, которую пинит его собственная версия.
`scripts/ensure_chromium.py` разбирает оба случая: если браузер уже лежит в
`PLAYWRIGHT_BROWSERS_PATH` (песочницы с предустановленным Chromium и закрытым
CDN), он подбирает под него версию Playwright; иначе просто скачивает нужную
сборку. Скрипт вызывается из `setup-cad.sh`, отдельно запускать не нужно.

## Обновление скиллов

```bash
npx skills add earthtojake/text-to-cad   # переустанавливает и добавляет новые
```

`npx skills update` обновляет только то, что уже в lock-файле, и молча
пропускает скиллы, появившиеся в новом релизе. После обновления сверьте пин
`cadgen` в `requirements-cad.txt` с `.agents/skills/cad/requirements.txt`.

Скиллы выполняются с полными правами агента — просматривайте изменения перед
использованием.
