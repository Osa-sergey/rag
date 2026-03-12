# Оценка расхода токенов (dry-run)

Скрипт `scripts/estimate_tokens.py` прогоняет RAPTOR-пайплайн на 100 случайных
статьях из `parsed_yaml/` с **фейковыми LLM** — реальные модели не вызываются.
Эмбеддинги считаются настоящей моделью (`sergeyzh/BERTA`), чтобы чанкинг и
построение RAPTOR-дерева были реалистичными.

## Что считается

| Поле | Описание |
|------|----------|
| `prompt_tokens` | Оценка: `len(text) / 4` (1 токен ≈ 3.5 символа для русского) |
| `completion_tokens` | 75 % ± 5 % от `max_tokens` из конфига |
| `cached_tokens` | Всегда 0 (фейковый прогон) |
| Количество keywords | 75 % от `max_keywords` (конфиг) |
| Количество relations | 75 % от `max_relations` (конфиг) |

## Запуск через uv

```bash
# Из корня проекта (habr/)

# 1. Синхронизировать окружение (установит все зависимости из pyproject.toml)
uv sync

# 2. Запустить скрипт
PYTHONPATH=. uv run python scripts/estimate_tokens.py
```

> **Первый запуск** скачает модель `sergeyzh/BERTA` (~500 MB) с HuggingFace Hub.
> Последующие запуски используют кеш.

### Альтернативный запуск (без uv sync)

Если не хотите создавать виртуальное окружение, `uv run` с `--no-project`
поставит зависимости во временное окружение:

```bash
PYTHONPATH=. uv run --no-project --with-requirements <(uv pip compile pyproject.toml) \
    python scripts/estimate_tokens.py
```

Но рекомендуется `uv sync` — быстрее при повторных запусках.

### Настройка device

Скрипт использует `device` из `raptor_pipeline/conf/embeddings/huggingface.yaml`.
По умолчанию стоит **`mps`** — оптимально для Mac с Apple Silicon.

```yaml
# raptor_pipeline/conf/embeddings/huggingface.yaml
model_kwargs:
  device: mps   # mps / cuda / cpu
```

## Результат

Скрипт выводит сводную таблицу в stdout:

```
════════════════════════════════════════════════════════════
  DRY-RUN TOKEN ESTIMATION (100 articles)
════════════════════════════════════════════════════════════
  Avg chunks/article:      25.3
  Avg RAPTOR nodes/article:32.1
  Avg keywords/article:    120.5
  Avg relations/article:   240.8
  Avg LLM calls/article:   68.2
  Avg tokens/article:      105432

  Per-component averages:
    summarizer                 12400 tok/article ...
    keyword_extractor          42300 tok/article ...
    keyword_refiner             8200 tok/article ...
    relation_extractor         42532 tok/article ...
════════════════════════════════════════════════════════════
```

А также сохраняет построчный CSV в `outputs/token_estimation_dry_run.csv`.
