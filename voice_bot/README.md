# 🎙️ Voice Bot

Голосовой Telegram-бот с модульной архитектурой интеграций.
Распознаёт голосовые сообщения, классифицирует намерение, извлекает структурированные данные через LLM
и направляет результат в нужную интеграцию — с подтверждением через inline-клавиатуру прямо в чате.

---

## Архитектура

```
voice_bot/
│
├── conf/                          # Hydra-конфигурация
│   ├── config.yaml                # Master config (defaults composition)
│   ├── intents/default.yaml       # Интенты → интеграция + действие
│   ├── firefly/default.yaml       # Firefly III настройки
│   ├── obsidian/default.yaml      # Obsidian vault настройки
│   ├── llm/llama_cpp.yaml         # LLM endpoint
│   ├── embeddings/huggingface.yaml
│   ├── transcriber/gigaam.yaml
│   ├── telegram/default.yaml
│   ├── categories/default.yaml
│   └── database/postgresql.yaml
│
├── intent_classifier/             # Общий модуль (НЕ интеграция)
│   ├── classifier.py              # Embedding-based cosine similarity
│   ├── categories.py              # Классификатор категорий расходов
│   └── registry.py                # Реестр интентов
│
├── integrations/                  # Модульные интеграции
│   ├── firefly_iii/               # Финансы (Firefly III API)
│   │   ├── client.py              # HTTP-клиент к Firefly III
│   │   ├── extractor.py           # LLM-извлечение транзакций
│   │   ├── account_resolver.py    # Маппинг названий → счета (embeddings)
│   │   ├── handler.py             # Бизнес-логика отправки
│   │   ├── ui.py                  # Inline-клавиатуры подтверждения
│   │   └── schemas.py             # Pydantic-модели
│   │
│   └── obsidian_tasks/            # Задачи (Obsidian vault)
│       ├── vault.py               # Фасад над vault_parser.DailyNoteEditor
│       ├── extractor.py           # LLM-извлечение задач
│       ├── handlers.py            # FSM-обработчики (create/show/update)
│       ├── ui.py                  # Inline-клавиатуры
│       └── schemas.py             # Dataclass-модели задач
│
├── bot.py                         # Главный роутер + config-driven dispatch
├── containers.py                  # DI-контейнер (Hydra → компоненты)
├── date_parser.py                 # Общий NL → date парсер (русский)
├── transcriber.py                 # STT (GigaAM)
├── extractor.py                   # LLM-извлечение (Firefly)
├── schemas.py                     # Корневые Pydantic-модели
├── storage.py                     # PostgreSQL-хранилище (legacy)
└── __main__.py                    # Entry point
```

---

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install -e ".[voice_bot]"
```

### 2. Настройка окружения

Скопируйте `.env.example` → `.env` и заполните:

```bash
# Обязательно
TELEGRAM_BOT_TOKEN=123456:ABC-...

# Firefly III (если используете)
FIREFLY_URL=http://localhost:9090
FIREFLY_TOKEN=eyJ0...

# Obsidian (если используете)
OBSIDIAN_VAULT_PATH=D:/vault/project_live/day_notes
```

### 3. Запуск

```bash
python -m voice_bot
```

Переопределение параметров из командной строки (Hydra):

```bash
python -m voice_bot telegram.bot_token=YOUR_TOKEN log_level=DEBUG
```

---

## Конфигурация

Вся конфигурация собирается [Hydra](https://hydra.cc/) из YAML-файлов в `voice_bot/conf/`.

### Master config (`conf/config.yaml`)

```yaml
defaults:
  - transcriber: gigaam
  - llm: llama_cpp
  - embeddings: huggingface
  - categories: default
  - telegram: default
  - firefly: default
  - obsidian: default
  - intents: default        # ← интенты + привязка к интеграциям
  - _self_

log_level: INFO
```

### Интенты (`conf/intents/default.yaml`)

Каждый интент привязан к интеграции и действию:

```yaml
unknown_threshold: 0.35        # порог cosine similarity для "unknown"

intents:
  - name: expense              # уникальный ID
    integration: firefly_iii   # пакет в integrations/
    action: create_transaction # стандартное действие
    reference_phrases:         # фразы для embedding-матчинга
      - потратил деньги
      - купил
      - заплатил за обед
```

**Naming convention:**
- `integration` — имя пакета в `voice_bot/integrations/<name>/`
- `action` — формат `<verb>_<object>`: `create_transaction`, `create_task`, `show_tasks`, `update_task`

### Текущие интенты

| Интент | Интеграция | Действие | Описание |
|---|---|---|---|
| `expense` | `firefly_iii` | `create_transaction` | Расход |
| `transfer` | `firefly_iii` | `create_transaction` | Перевод между счетами |
| `deposit` | `firefly_iii` | `create_transaction` | Пополнение / доход |
| `task_create` | `obsidian_tasks` | `create_task` | Создание задачи |
| `task_show` | `obsidian_tasks` | `show_tasks` | Показ задач за дату |
| `task_update` | `obsidian_tasks` | `update_task` | Изменение существующей задачи |

---

## Как работает pipeline

```
🎤 Голос
  → STT (GigaAM)
  → Intent Classifier (cosine similarity по эмбеддингам)
  → Config-driven dispatch:
       intent → (integration, action) → handler_fn
  → LLM Extractor (структурированные данные)
  → Inline-подтверждение в Telegram
  → API-вызов (Firefly III / Obsidian vault)
```

---

## Добавление новой интеграции

### Шаг 1. Создайте пакет

```
voice_bot/integrations/my_service/
├── __init__.py
├── extractor.py    # LLM-извлечение данных из текста
├── handlers.py     # async entry-point функции
├── ui.py           # Inline-клавиатуры
└── schemas.py      # Dataclass / Pydantic модели
```

### Шаг 2. Реализуйте entry-point handler

Каждый handler — async-функция с сигнатурой:

```python
async def create_reminder(
    message: Message,        # исходное сообщение пользователя
    state: FSMContext,       # FSM-контекст для inline-редактирования
    text: str,               # распознанный текст
    status_msg: Message,     # сообщение-статус (edit_text для in-place UI)
    # + любые DI-зависимости из dispatcher:
    date_parser=None,
    task_extractor=None,
    vault=None,
    **kwargs,
) -> None:
    ...
```

### Шаг 3. Добавьте конфигурацию

**`conf/my_service/default.yaml`** — настройки интеграции:

```yaml
api_url: "http://localhost:8080"
api_key: "${oc.env:MY_SERVICE_KEY}"
```

**`conf/intents/default.yaml`** — новый интент:

```yaml
  - name: reminder_create
    integration: my_service
    action: create_reminder
    reference_phrases:
      - напомни мне
      - поставь напоминание
      - напомни через час
      - создай напоминание
```

**`conf/config.yaml`** — добавьте в defaults:

```yaml
defaults:
  - ...
  - my_service: default
  - intents: default
  - _self_
```

### Шаг 4. Зарегистрируйте handler

В `voice_bot/bot.py` добавьте запись в реестр:

```python
from voice_bot.integrations.my_service.handlers import create_reminder

_INTENT_HANDLERS: dict[tuple[str, str], object] = {
    ...
    ("my_service", "create_reminder"): create_reminder,
}
```

### Шаг 5. Инициализация (если нужен DI)

В `voice_bot/containers.py` добавьте фабрику:

```python
def my_service_client(self):
    from voice_bot.integrations.my_service.client import MyClient
    return MyClient(self.config.my_service)
```

В `voice_bot/__main__.py` инжектируйте в dispatcher:

```python
dp["my_service"] = container.my_service_client()
```

### Шаг 6. Добавьте новый интент (без новой интеграции)

Если интеграция уже существует — достаточно:

1. Добавить блок в `conf/intents/default.yaml`
2. Добавить handler в `handlers.py` интеграции
3. Зарегистрировать `(integration, action)` в `_INTENT_HANDLERS`

---

## Настройки интеграций

### Firefly III (`conf/firefly/default.yaml`)

```yaml
base_url: "${oc.env:FIREFLY_URL,http://localhost:9090}"
token: "${oc.env:FIREFLY_TOKEN}"
```

Требует Docker-контейнер с Firefly III. Бот использует Personal Access Token для API.

### Obsidian Tasks (`conf/obsidian/default.yaml`)

```yaml
vault_path: "${oc.env:OBSIDIAN_VAULT_PATH}"
daily_notes_folder: "Daily"       # папка с YYYY-MM-DD.md
people_folder: "People"           # карточки людей для [[ссылок]]
```

Задачи записываются в daily notes используя `vault_parser.DailyNoteEditor`.
Формат совместим с плагином Obsidian Tasks: `- [ ] Текст 📅 2026-03-25 🔁 every monday`.

**Поддерживаемые поля задач:**

| Поле | Emoji | Источник |
|---|---|---|
| due_date | 📅 | LLM + DateParser |
| start_date | 🛫 | LLM + DateParser |
| scheduled_date | ⏳ | LLM + DateParser |
| time_slot | (prefix) | LLM / ручной ввод |
| recurrence | 🔁 | LLM + пресеты UI |
| people | `[[Имя]]` | LLM → PeopleRegistry |
| priority | секция main/secondary | LLM / выбор из списка |

### LLM (`conf/llm/llama_cpp.yaml`)

```yaml
model_name: "your-model"
base_url: "http://localhost:8000/v1"
temperature: 0.1
max_tokens: 1024
```

Используется OpenAI-совместимый API (llama.cpp server, vLLM, Ollama и др.)

### Embeddings (`conf/embeddings/huggingface.yaml`)

```yaml
model_name: "intfloat/multilingual-e5-small"
```

Используются для intent classification и account name resolution (cosine similarity).

### STT (`conf/transcriber/gigaam.yaml`)

```yaml
model_name: "GigaAM-CTC"
```

---

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Приветствие и инструкция |
| `/categories` | Список категорий расходов Firefly III |
| `/tasks` | Задачи на сегодня из Obsidian |
| 🎤 *голосовое* | Автоматическое распознавание и роутинг |

---

## Тесты

```bash
# Все тесты
python -m pytest tests/ -q

# Только тесты бота
python -m pytest tests/test_date_parser.py tests/test_account_resolver.py -q
```

---

## Переменные окружения

| Переменная | Описание | Обязательна |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота | ✅ |
| `FIREFLY_URL` | URL Firefly III | Для firefly_iii |
| `FIREFLY_TOKEN` | Personal Access Token | Для firefly_iii |
| `OBSIDIAN_VAULT_PATH` | Путь к vault | Для obsidian_tasks |
