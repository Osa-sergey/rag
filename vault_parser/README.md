# 🗃️ Vault Parser

CLI-модуль для извлечения задач, метрик сна/энергии и структурированного контента из Obsidian-заметок.
Автоматически загружает реестр людей для разделения упоминаний персон и wiki-ссылок на заметки.

---

## Быстрый старт

```bash
# Windows: включить UTF-8 для emoji-вывода
$env:PYTHONIOENCODING="utf-8"

# Статистика по вольту
python -m vault_parser mode=stats

# Все открытые задачи
python -m vault_parser mode=list-tasks status=open

# Таблица сна и энергии
python -m vault_parser mode=wellness

# Список людей из вольта
python -m vault_parser mode=people

# Полный JSON-дамп
python -m vault_parser mode=parse
```

---

## Режимы работы (`mode=`)

| Режим | Описание |
|-------|----------|
| `list-tasks` | Вывод задач с фильтрацией *(по умолчанию)* |
| `search` | Полнотекстовый поиск по тексту задач |
| `stats` | Агрегированная статистика (заметки, задачи, сон, энергия, люди) |
| `wellness` | Таблица сна и энергии с фильтрацией по дням |
| `people` | Реестр людей и групп из `people/` директории |
| `edit` | Редактор дневных заметок (MCP-режим) |
| `parse` | Полный JSON-дамп всех заметок с задачами и метаданными |

---

## Конфигурация вольта (`vault.*`)

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `vault.path` | `str` | `D:\vault\project_live\day_notes` | Корневая директория с заметками |
| `vault.daily_dir` | `str` | `daily` | Подпапка ежедневных заметок |
| `vault.weekly_dir` | `str` | `weekly` | Подпапка недельных заметок |
| `vault.monthly_dir` | `str` | `monthly` | Подпапка месячных заметок |
| `vault.people_dir` | `str` | `D:\vault\project_live\people` | Директория с заметками по людям и группам |

```bash
# Указать другой вольт
python -m vault_parser vault.path="C:\my\vault\notes" vault.daily_dir=days
```

---

## Фильтры задач

| Параметр | Тип | Значения | Описание |
|----------|-----|----------|----------|
| `status` | `str` | `open`, `done`, `cancelled`, `in_progress` | Фильтр по статусу чекбокса |
| `priority` | `str` | `critical`, `high`, `medium`, `low`, `normal` | Фильтр по приоритету |
| `date_range` | `str` | `today`, `this_week`, `this_month`, `YYYY-MM-DD`, `YYYY-MM-DD..YYYY-MM-DD` | Фильтр по дате заметки |
| `person` | `str` | любое имя | Задачи, упоминающие конкретного человека (из реестра) |
| `section` | `str` | любая подстрока | Фильтр по имени секции заметки |
| `query` | `str` | любой текст (латиница) | Полнотекстовый поиск по тексту задачи |

### Примеры фильтрации

```bash
# Открытые задачи высокого приоритета
python -m vault_parser status=open priority=high

# Задачи за сентябрь 2025
python -m vault_parser date_range=2025-09-01..2025-09-30

# Задачи на сегодня
python -m vault_parser date_range=today

# Задачи за текущую неделю
python -m vault_parser date_range=this_week

# Задачи, упоминающие конкретного человека
python -m vault_parser person="Федя"

# Задачи из секции "Основные дела"
python -m vault_parser section="Основные"
```

---

## Параметры вывода (`output.*`)

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `output.format` | `str` | `table` | Формат: `table` (цветной CLI), `json`, `csv` |
| `output.max_items` | `int` | `50` | Лимит строк в табличном выводе |
| `output.show_raw` | `bool` | `false` | Показывать исходную markdown-строку (только `list-tasks`) |

```bash
# JSON-вывод всех задач
python -m vault_parser output.format=json

# CSV для экспорта
python -m vault_parser output.format=csv > tasks.csv

# Первые 10 задач с исходными строками
python -m vault_parser output.max_items=10 output.show_raw=true
```

---

## Режим `wellness` — сон и энергия

Отдельный режим для анализа сна и энергии. Поддерживает фильтрацию по дням и все форматы вывода.

```bash
# Вся таблица сна и энергии
python -m vault_parser mode=wellness

# Только сентябрь 2025
python -m vault_parser mode=wellness date_range=2025-09-01..2025-09-30

# Текущая неделя
python -m vault_parser mode=wellness date_range=this_week

# Конкретный день
python -m vault_parser mode=wellness date_range=2025-11-28

# JSON-экспорт всех полей сна
python -m vault_parser mode=wellness output.format=json

# CSV для анализа в Excel / pandas
python -m vault_parser mode=wellness output.format=csv > sleep.csv
```

### Колонки табличного вывода

| Колонка | Описание |
|---------|----------|
| Date | Дата заметки |
| Sleep | Длительность сна (H:MM), `none` если не заполнено |
| Quality | Качество сна (1-10), `none` если не заполнено |
| Morning | Утренняя энергия (1-10), `none` если не заполнено |
| Day | Дневная энергия (1-10), `none` если не заполнено |
| Evening | Вечерняя энергия (1-10), `none` если не заполнено |
| Mood | Утреннее настроение (1-10), `none` если не заполнено |
| Exercise | Занимался спортом (`true`/`false`) |
| Late meal | Поздний ужин (`true`/`false`) |
| **AVG** | Средние значения за период (без учёта `none`) |

### Поля JSON-экспорта (`output.format=json`)

Включает **все 14 полей сна** + **4 поля энергии** из frontmatter:

```json
{
  "date": "2025-09-08",
  "sleep": {
    "bed_time_start": "1:00",
    "sleep_start": "1:00",
    "sleep_end": "9:30",
    "duration": "8:30",
    "duration_minutes": 510,
    "quality": 7,
    "quick_fall_asleep": true,
    "night_awakenings": false,
    "deep_sleep": true,
    "remembered_dreams": false,
    "no_nightmare": true,
    "no_phone": false,
    "physical_exercise": true,
    "late_dinner": false
  },
  "energy": {
    "morning_mood": 6,
    "morning_energy": 6,
    "day_energy": 6,
    "evening_energy": 8,
    "average": 6.7
  }
}
```

---

## Режим `people` — реестр людей

Загружает данные из `vault.people_dir`. Поддерживает два типа файлов:

- **Персоны** (`Котиков Федор.md`) — YAML frontmatter с `roles`, `interests`, `tg`
- **Группы** (`Группа КНАД.md`) — markdown-таблица `| [[Person]] | роль |`

```bash
# Все люди и группы (с ролями в группах)
python -m vault_parser mode=people

# JSON-экспорт
python -m vault_parser mode=people output.format=json
```

### Как работает распознавание людей

1. Парсер читает `people/` — каждый `.md` файл = одна персона/группа (имя файла = каноническое имя)
2. Из заметок автоматически собираются алиасы: `[[Котиков Федор|Федей]]` → "Федей" = "Котиков Федор"
3. **Сопоставление**: wiki-ссылка в задаче `[[filename|displayed]]` сопоставляется с реестром по `filename` (= имя файла в `people/`)
4. В результате:
   - `people` — только реальные люди из реестра (иконка `@Федей`)
   - `wiki_links` — все Obsidian-ссылки (не-персоны отображаются как `🔗ссылка`)

### Группы и роли

Группы загружаются из markdown-таблиц формата:

```markdown
| [[Малеев Алексей]] | руководитель ВШПИ |
| [[Созыкин Андрей]] | заместитель руководителя ВШПИ |
```

Поля группы: `members: dict[str, str]` — `{имя: роль}`.

Python API для поиска групп человека:

```python
registry = parser.people_registry

# Все группы, в которых состоит человек
memberships = registry.groups_for_person("Гюнай")
for m in memberships:
    print(f"{m.group_name} → {m.role}")
# Группа КНАД → менеджер по работе с преподавателями онлайн-программ ФКН
```

Без `people_dir` все wiki-ссылки попадают в `people` (обратная совместимость).

---

## Режим `edit` — редактор дневных заметок

Создание и обновление дневных заметок. Подготовлен для MCP-сервера.

### CLI

```bash
# Создать заметку из шаблона
python -m vault_parser mode=edit action=create date=2025-12-01

# Сон (partial update — только указанные поля)
python -m vault_parser mode=edit action=set-sleep date=2025-12-01 sleep_quality=8 deep_sleep=true

# Энергия
python -m vault_parser mode=edit action=set-energy date=2025-12-01 morning=7 evening=9

# Добавить задачу с датами и рекурренцией
python -m vault_parser mode=edit action=add-task date=2025-12-01 \
  text=стендап start_date=2025-12-01 due_date=2025-06-30 \
  "recurrence=every 2 weeks"

# Пометить задачу как выполненную
python -m vault_parser mode=edit action=done date=2025-12-01 query=стендап

# Отменить задачу
python -m vault_parser mode=edit action=cancel date=2025-12-01 query=отчет

# Прочитать заметку (JSON)
python -m vault_parser mode=edit action=read date=2025-12-01
```

> **Примечание**: значения с запятыми нужно экранировать для Hydra: `"recurrence='every mon,wed,fri'"`

### Python API

```python
from vault_parser.writer import DailyNoteEditor
from vault_parser.models import TaskStatus
from datetime import date

editor = DailyNoteEditor(r"D:\vault\project_live\day_notes\daily")

# Создать заметку
editor.create_from_template("2025-12-01")

# Partial frontmatter
editor.set_sleep("2025-12-01", sleep_quality=8, deep_sleep=True)
editor.set_energy("2025-12-01", morning=7)  # day/evening — позже

# Задача с рекурренцией
editor.add_task("2025-12-01", "стендап",
    section="main",
    people=["Илюхин Влад"],
    time_slot="10:00-10:15",
    start_date=date(2025, 12, 1),
    recurrence="every mon,wed,fri",
)

# Статус
editor.update_task_status("2025-12-01", "стендап", TaskStatus.DONE)

# Секции
editor.set_focus("2025-12-01", ["Написать модуль", "Провести ревью"])
editor.set_gratitude("2025-12-01", "Сделал много дел")

# Чтение обратно
note = editor.read("2025-12-01")
print(note.all_tasks)
```

### Recurrence API

```python
from vault_parser.recurrence import expand_occurrences, next_occurrence
from vault_parser.models import Recurrence
from datetime import date

rec = Recurrence(rule="every 2 weeks", until=date(2025, 12, 31))
dates = expand_occurrences(rec, date(2025, 9, 1), date(2025, 10, 1))
# [2025-09-01, 2025-09-15, 2025-09-29]

nxt = next_occurrence(rec, date(2025, 9, 15))
# 2025-09-16
```

---

## Что извлекается из заметок

### Ежедневные заметки (`YYYY-MM-DD.md`)

#### YAML Frontmatter → `SleepData` + `EnergyData`

| Поле frontmatter | Модель | Тип | Описание |
|------------------|--------|-----|----------|
| `bed-time-start` | `SleepData` | `str` | Время отхода ко сну |
| `sleep-start` | `SleepData` | `str` | Время засыпания |
| `sleep-end` | `SleepData` | `str` | Время пробуждения |
| `sleep-duration` | `SleepData` | `str` | Длительность сна (`H:MM`) |
| `sleep-quality` | `SleepData` | `int\|None` | Качество сна (1-10) |
| `quick-fall-asleep` | `SleepData` | `bool` | Заснул быстро (default: `false`) |
| `night-awakenings` | `SleepData` | `bool` | Ночные пробуждения (default: `false`) |
| `deep-sleep` | `SleepData` | `bool` | Глубокий сон (default: `false`) |
| `remembered-dreams` | `SleepData` | `bool` | Запомнил сны (default: `false`) |
| `no-nightmare` | `SleepData` | `bool` | Без кошмаров (default: `false`) |
| `morning-mood` | `SleepData` | `int\|None` | Утреннее настроение (1-10) |
| `no-phone` | `SleepData` | `bool` | Не залипал в экран (default: `false`) |
| `physical-exercise` | `SleepData` | `bool` | Занимался спортом (default: `false`) |
| `late-dinner` | `SleepData` | `bool` | Поздний ужин (default: `false`) |
| `morning-energy` | `EnergyData` | `int\|None` | Утренняя энергия (1-10) |
| `day-energy` | `EnergyData` | `int\|None` | Дневная энергия (1-10) |
| `evening-energy` | `EnergyData` | `int\|None` | Вечерняя энергия (1-10) |

> Булевы поля: `true`/`false`, без состояния "не установлено". Числовые: `None` если не заполнено, не учитываются в статистике.

#### Секции → Поля `DayNote`

| Секция | Поле модели | Что извлекается |
|--------|-------------|-----------------|
| `## Фокус дня` | `focus: list[str]` | Пункты списка (без чекбоксов) |
| `## Основные дела` | `tasks: list[VaultTask]` | Задачи с priority=`medium` |
| `## Второстепенные задачи` | `tasks: list[VaultTask]` | Задачи с priority=`low` |
| `# Чему я рад...` | `gratitude: str` | Свободный текст |
| `# Что пошло не так` | `problems: list[ReflectionBlock]` | Подсекции (Что / Причина / Последствия) |
| `# Заметки` | `notes_text: str` | Свободный текст |
| `# Надо подумать о` | `think_about: list[VaultTask]` | Задачи или пункты списка |

### Задачи (`VaultTask`)

Из каждой строки-чекбокса извлекаются:

| Поле | Описание | Пример |
|------|----------|--------|
| `status` | Статус чекбокса | `[x]`→done, `[ ]`→open, `[-]`→cancelled, `[/]`→in_progress |
| `priority` | Emoji или секция | `⏫`→critical, `🔺`→high, `🔼`→medium, `🔽`→low |
| `completion_date` | Дата завершения | `✅ 2025-11-28` |
| `scheduled_date` | Запланированная дата | `⏳ 2025-08-29` |
| `start_date` | Дата начала | `🛫 2025-09-01` |
| `due_date` | Дедлайн | `📅 2025-09-15` |
| `recurrence` | Периодичность | `🔁 every 2 weeks until 2025-12-31` |
| `time_slot` | Временной слот | `11:30-12:00` |
| `wiki_links` | Все Obsidian-ссылки | `[[[Котиков Федор\|Федей]], [[MCP]]]` |
| `people` | Только реальные люди (из реестра) | `["Котиков Федор"]` |
| `tags` | Хэш-теги | `["python", "rag"]` |
| `inline_comment` | Текст в скобках | `"не получилось"` |
| `text` | Очищенный текст | без emoji/дат/синтаксиса |

#### Периодические задачи (🔁)

Формат рекурренции (аналог cron для дней и выше):

| Правило | Описание |
|---------|----------|
| `every day` | Каждый день |
| `every 2 days` | Каждые 2 дня |
| `every week` | Каждую неделю |
| `every 2 weeks` | Раз в 2 недели |
| `every month` | Каждый месяц |
| `every 3 months` | Раз в квартал |
| `every mon,wed,fri` | Конкретные дни недели (EN/RU: mon/пн, tue/вт, wed/ср...) |

Опционально `until YYYY-MM-DD` — дата окончания повторений.

#### Отображение в таблице

В табличном выводе `list-tasks`:
- `@Котиков Федор,Коряев Илья` — реальные люди (голубой)
- `🔗mlp_авиатека.drawio` — wiki-ссылки на заметки (серый)
- `🛫2025-09-01` — дата начала
- `📅2025-09-15` — дедлайн
- `⏳2025-08-29` — запланированная дата (жёлтый)
- `✅2025-11-28` — дата завершения (зелёный)
- `🔁 every week` — периодичность
- `16:00-17:00` — временной слот (пурпурный)

### Недельные заметки (`YYYY-Wnn.md`)

Dataview-блоки автоматически исключаются. Извлекаются:

| Секция | Поле `WeeklyNote` |
|--------|---------------------|
| `## Список задач` | `tasks: list[VaultTask]` |
| `## Основной фокус` | `focus: list[str]` |
| `## Ключевые достижения` | `achievements: list[str]` |
| `## Новые инсайты` | `insights: list[str]` |
| `## Причины отклонений` | `plan_deviations: list[str]` |
| `## Что тормозило` | `problems: list[str]` |
| `## Возможные решения` | `solutions: list[str]` |
| `week-mark:: N` | `week_mark: int` (1-10) |
| `## Статьи, книги, видео` | `resources: list[str]` |
| `# Рефлексия` | `reflections: list[ReflectionBlock]` |

### Месячные заметки (`YYYY-MM.md`)

| Секция | Поле `MonthlyNote` |
|--------|---------------------|
| `# Общая динамика` | `dynamics: str` |
| `# Ключевые достижения` | `achievements: list[str]` |
| `# Инсайты месяца` | `insights: list[str]` |
| `# Сравнение планов и факта` | `plan_vs_fact: str` |
| `# Навыки, привычки` | `skills: list[str]` |
| `# Проблемы и блоки` | `problems: list[str]` |
| `# Самооценка` | `self_assessment: str` + `month_score: int` |
| `# Находки` | `resources: list[str]` |
| `# Рефлексия` | `reflection: str` |

---

## Программное использование (Python API)

```python
from vault_parser import VaultParser

parser = VaultParser(
    r"D:\vault\project_live\day_notes",
    daily_subdir="daily",
    weekly_subdir="weekly",
    monthly_subdir="monthly",
    people_dir=r"D:\vault\project_live\people",  # реестр людей
)

# Реестр людей
registry = parser.people_registry
print(registry.all_names())        # ["Котиков Федор", "Илюхин Влад", ...]
print(registry.is_person("Федя"))  # True
print(registry.lookup("Федей"))    # Person(name="Котиков Федор", ...)

# Все заметки
all_notes = parser.parse_all()   # {"daily": [...], "weekly": [...], "monthly": [...]}

# Все задачи (из daily + weekly)
tasks = parser.all_tasks()

# Только открытые
open_tasks = parser.open_tasks()

# Поиск по тексту
results = parser.search_tasks("tts")

# Задачи конкретного человека (с фаззи-поиском по реестру)
fed_tasks = parser.tasks_mentioning("Федя")

# Задачи за дату
from datetime import date
day_tasks = parser.tasks_for_date(date(2025, 11, 28))

# Фильтрация
from vault_parser.filters import filter_tasks, overdue_tasks
filtered = filter_tasks(tasks, status="open", priority="high")
overdue = overdue_tasks(tasks)
```

---

## Архитектура модуля

```
vault_parser/
├── __init__.py          # Публичное API
├── __main__.py          # Hydra CLI entry point
├── models.py            # Dataclass-модели (VaultTask, Recurrence, DayNote, ...)
├── parser.py            # Regex-парсинг markdown + VaultParser facade
├── people.py            # PeopleRegistry, Person, GroupMembership
├── recurrence.py        # Движок рекурренции: next_occurrence, expand_occurrences
├── filters.py           # Фильтрация задач по критериям
├── formatters.py        # Table / JSON / CSV / Stats / People форматирование
├── writer/              # Редактор дневных заметок
│   ├── __init__.py      # re-export DailyNoteEditor
│   ├── editor.py       # DailyNoteEditor (CRUD)
│   ├── frontmatter.py  # YAML frontmatter сериализация
│   ├── sections.py     # Markdown-секции заметок
│   └── task_lines.py   # Форматирование строк задач
├── conf/
│   └── config.yaml      # Hydra-конфиг по умолчанию
└── README.md            # ← вы здесь
```

---

## Ограничения

- **Hydra + кириллица**: CLI-аргументы с кириллицей требуют config-overrides вместо CLI
- **Месячные заметки**: не содержат чекбоксов — извлекается только текст секций
- **YAML sexagesimal**: `sleep-duration: 6:30` автоматически конвертируется YAML в 390 — парсер обрабатывает это корректно
