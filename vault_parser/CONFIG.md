# Vault Parser -- Конфигурация

Полная справка по параметрам конфигурации.
Файл конфига: `vault_parser/conf/config.yaml`.

---

## CLI-опции по командам

### `list-tasks`

| Опция | Тип | YAML-путь | Описание |
|-------|-----|-----------|----------|
| `--status` | `open\|done\|cancelled\|in_progress` | `status` | Фильтр по статусу |
| `--priority` | `critical\|high\|medium\|low\|normal` | `priority` | Фильтр по приоритету |
| `--date-range` | TEXT | `date_range` | Фильтр по дате |
| `--person` | TEXT | `person` | Задачи человека |
| `--section` | TEXT | `section` | Фильтр по секции |
| `--query, -q` | TEXT | `query` | Поиск по тексту |
| `--format` | `table\|json\|csv` | `output.format` | Формат вывода |
| `--max-items` | INT | `output.max_items` | Лимит строк |
| `--show-raw` | flag | `output.show_raw` | Показать markdown |

### `search`

| Опция | Тип | Описание |
|-------|-----|----------|
| `QUERY` | аргумент | Текст для поиска (обязательный) |
| `--format` | `table\|json\|csv` | Формат вывода |
| `--max-items` | INT | Лимит строк |

### `wellness`

| Опция | Тип | Описание |
|-------|-----|----------|
| `--date-range` | TEXT | Фильтр по дате |
| `--format` | `table\|json\|csv` | Формат вывода |
| `--max-items` | INT | Лимит строк |

### `people`

| Опция | Тип | Описание |
|-------|-----|----------|
| `--format` | `table\|json` | Формат вывода |

### `edit`

| Опция | Тип | Описание |
|-------|-----|----------|
| `--date` | TEXT | Дата заметки YYYY-MM-DD (обязательный) |
| `--action` | enum (13 значений) | Действие |
| `--text` | TEXT | Текст задачи / секции |
| `--section` | TEXT | Секция: main / secondary |
| `--query, -q` | TEXT | Поиск задачи (done/cancel/progress) |

### `stats`, `parse`

Нет специальных CLI-опций. Используйте `-o` для настройки vault paths.

### Общие для всех команд

| Опция | Тип | Описание |
|-------|-----|----------|
| `-v, --verbose` | flag | Подробный вывод (DEBUG) |
| `-o, --override` | TEXT | Hydra override `key=value` |

---

## Параметры через `-o`

### Vault (пути)

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `vault.path` | str | D:\vault\project_live\day_notes | Корневая директория |
| `vault.daily_dir` | str | daily | Подпапка дневных заметок |
| `vault.weekly_dir` | str | weekly | Подпапка недельных заметок |
| `vault.monthly_dir` | str | monthly | Подпапка месячных заметок |
| `vault.people_dir` | str\|null | D:\vault\project_live\people | Реестр людей |
| `vault.template_path` | str\|null | ...templates/t_daily.md | Шаблон дневной заметки |

### Output

| Параметр | Тип | Диапазон | По умолчанию | Описание |
|----------|-----|----------|--------------|----------|
| `output.format` | enum | `table\|json\|csv` | table | Формат вывода |
| `output.max_items` | int | 1..1000 | 50 | Лимит строк |
| `output.show_raw` | bool | — | false | Показать markdown |

### Edit mode (через `-o`)

Поля, не имеющие прямых Click-опций:

| Параметр | Тип | Описание |
|----------|-----|----------|
| `items` | str | Фокус дня (через `;`) |
| `people` | str | Люди (через `,`) |
| `time_slot` | str | HH:MM-HH:MM |
| `scheduled_date` | str | YYYY-MM-DD |
| `start_date` | str | YYYY-MM-DD |
| `due_date` | str | YYYY-MM-DD |
| `recurrence` | str | every day, every 2 weeks, etc. |
| `what` | str | Проблема: что |
| `cause` | str | Проблема: причина |
| `consequences` | str | Проблема: последствия |

### Sleep-поля (через `-o` с `action=set-sleep`)

| Параметр | Тип | Диапазон | Описание |
|----------|-----|----------|----------|
| `sleep_quality` | int | 1..10 | Качество сна |
| `morning_mood` | int | 1..10 | Утреннее настроение |
| `bed_time_start` | str | — | Время отхода ко сну |
| `sleep_start` | str | — | Время засыпания |
| `sleep_end` | str | — | Время пробуждения |
| `quick_fall_asleep` | bool | — | Заснул быстро |
| `night_awakenings` | bool | — | Ночные пробуждения |
| `deep_sleep` | bool | — | Глубокий сон |
| `remembered_dreams` | bool | — | Запомнил сны |
| `no_nightmare` | bool | — | Без кошмаров |
| `no_phone` | bool | — | Без телефона |
| `physical_exercise` | bool | — | Спорт |
| `late_dinner` | bool | — | Поздний ужин |

### Energy-поля (через `-o` с `action=set-energy`)

| Параметр | Тип | Диапазон | Описание |
|----------|-----|----------|----------|
| `morning` | int | 1..10 | Утренняя энергия |
| `day_energy` | int | 1..10 | Дневная энергия |
| `evening` | int | 1..10 | Вечерняя энергия |

---

## Кросс-валидации

| Правило | Ошибка |
|---------|--------|
| `mode=edit` | требует `date` |
| `action=add-task` | требует `text` |
| `action=done\|cancel\|progress` | требует `query` |
| `mode=search` | требует `query` |
| `date_range` | формат: `today`, `this_week`, `this_month`, `YYYY-MM-DD`, `YYYY-MM-DD..YYYY-MM-DD` |
| `sleep_quality`, `morning_mood` | 1..10 |
| `morning`, `day_energy`, `evening` | 1..10 |
| `output.max_items` | 1..1000 |

---

## Примеры

```powershell
# Задачи с фильтрами
python -m vault_parser list-tasks --status open --priority high
python -m vault_parser list-tasks --date-range this_week --format json

# Поиск
python -m vault_parser search "python"

# Сон и энергия
python -m vault_parser wellness --date-range 2025-09-01..2025-09-30

# Редактирование
python -m vault_parser edit --date 2025-12-01 --action create
python -m vault_parser edit --date 2025-12-01 --action add-task --text "стендап"
python -m vault_parser edit --date 2025-12-01 --action set-sleep -o sleep_quality=8

# Проверка конфига
python -m vault_parser validate
python -m vault_parser validate -o "output.format=invalid"

# Сырой YAML
python -m vault_parser show-config
```
