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

## Запуск

```bash
# Из корня проекта (habr/)
PYTHONPATH=. python scripts/estimate_tokens.py
```

### Требования

- Python 3.11+
- Установленные зависимости проекта (`pip install -r requirements.txt` или аналог)
- Основные пакеты: `hydra-core`, `omegaconf`, `sentence-transformers`, `torch`,
  `langchain-huggingface`, `numpy`, `scikit-learn`, `pyyaml`, `markdownify`

### Настройка device

Скрипт использует `device` из `raptor_pipeline/conf/embeddings/huggingface.yaml`.
По умолчанию стоит `mps` — для Mac с Apple Silicon это оптимально.

Для другого device можно переопределить через Hydra override в скрипте или
поменять в конфиге:

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
    summarizer                 12400 tok/article (p=8200 c=4200) [8.5 calls]
    keyword_extractor          42300 tok/article (p=28200 c=14100) [25.3 calls]
    keyword_refiner             8200 tok/article (p=5600 c=2600) [2.0 calls]
    relation_extractor         42532 tok/article (p=28400 c=14132) [25.3 calls]

  TOTAL across 100 articles: 10,543,200 tokens in 6,820 calls
  Elapsed: 342.1s
  CSV saved: outputs/token_estimation_dry_run.csv
════════════════════════════════════════════════════════════
```

*(числа примерные, зависят от размера статей)*

А также сохраняет построчный CSV в `outputs/token_estimation_dry_run.csv`.
