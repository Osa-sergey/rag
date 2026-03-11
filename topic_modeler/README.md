# 📊 Topic Modeler

Standalone утилита для кросс-статейного тематического моделирования на базе [BERTopic](https://maartengr.github.io/BERTopic/).

Обучает модель на коллекции статей из `parsed_yaml/`, обнаруживает топики, обогащает Article-ноды метаданными из CSV и создаёт `:Topic` сущности в Neo4j.

---

## Быстрый старт

```powershell
# Обучить модель на всех статьях
python -m topic_modeler mode=train

# Добавить одну статью (инференс по сохранённой модели)
python -m topic_modeler mode=add_article article_path=parsed_yaml/957000_20260204_130209.yaml
```

---

## Режимы работы (`mode=`)

| Режим | Описание |
|-------|----------|
| `train` | Обучить BERTopic на всех статьях, сохранить модель, обновить Neo4j |
| `add_article` | Предсказать топик для новой статьи по сохранённой модели |

---

## Что происходит при `train`

1. Загрузка текстов из `parsed_yaml/*.yaml` (через `text_extractor`)
2. Загрузка метаданных из CSV → upsert `(:Article)` нод с полями author, reading_time, complexity, labels, tags, hubs
3. Вычисление эмбеддингов через BERTA (768d)
4. Обучение BERTopic: **UMAP → HDBSCAN → CountVectorizer → KeyBERT + MMR**
5. Создание `:Topic` нод: `{id, label, top_keywords}`
6. Создание связей `(:Article)-[:BELONGS_TO_TOPIC]->(:Topic)`
7. Сохранение модели в `safetensors` формате

## Что происходит при `add_article`

1. Загрузка сохранённой модели из `model_dir`
2. Загрузка текста и метаданных статьи
3. `topic_model.transform()` → предсказание топика
4. Upsert Article + MERGE `[:BELONGS_TO_TOPIC]`

---

## Neo4j Schema

```
(:Article {id, title, author, reading_time, complexity, labels, tags, hubs})
(:Topic   {id, label, top_keywords})
(:Article)-[:BELONGS_TO_TOPIC {confidence}]->(:Topic)
```

**Проверка результатов:**

```cypher
-- Все топики
MATCH (t:Topic) RETURN t.id, t.label, t.top_keywords

-- Статьи и их топики
MATCH (a:Article)-[:BELONGS_TO_TOPIC]->(t:Topic)
RETURN a.title, t.label

-- Метаданные статей
MATCH (a:Article) WHERE a.author IS NOT NULL
RETURN a.id, a.author, a.complexity, a.tags
```

---

## Конфигурация

Файл: `topic_modeler/conf/config.yaml`

### Пути

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `input_dir` | `parsed_yaml` | Директория с YAML-статьями |
| `article_path` | `null` | Путь к статье (для `add_article`) |
| `model_dir` | `outputs/bertopic_model` | Куда сохранять/откуда загружать модель |
| `csv_paths` | `data/row_data/scrapped_articles*.csv` | CSV с метаданными статей |

### Параметры суб-компонентов

Каждый компонент BERTopic-пайплайна настраивается отдельной секцией:

#### UMAP (снижение размерности)

```yaml
umap:
  n_neighbors: 15     # число ближайших соседей
  n_components: 5      # размерность проекции
  min_dist: 0.1        # минимальная дистанция
  metric: cosine       # метрика расстояния
```

#### HDBSCAN (кластеризация)

```yaml
hdbscan:
  min_cluster_size: 5               # мин. размер кластера
  min_samples: 1                     # мин. плотность
  metric: euclidean                  # метрика
  cluster_selection_method: eom     # метод выбора кластеров
```

#### CountVectorizer (токенизация)

```yaml
vectorizer:
  min_df: 2              # мин. document frequency
  ngram_range: [1, 2]    # uni- и bi-граммы
  stop_words: null       # null = без стоп-слов
```

#### BERTopic (основные параметры)

```yaml
bertopic:
  language: russian
  top_n_words: 15        # сколько слов на топик
  min_topic_size: 3      # мин. размер топика
  nr_topics: null        # null = автоматически
```

#### Representation Models (улучшение меток)

```yaml
representation:
  use_keybert: true      # KeyBERT-inspired представление
  keybert:
    top_n_words: 10
  use_mmr: true          # Maximal Marginal Relevance
  mmr:
    diversity: 0.3       # разнообразие 0..1
```

### Эмбеддинги и Neo4j

```yaml
embeddings:
  provider: huggingface
  model_name: sergeyzh/BERTA
  local_path: D:/models/BERTA    # локальная копия (опционально)
  embedding_dim: 768

stores:
  neo4j:
    uri: bolt://localhost:7687
    user: neo4j
    password: raptor_password
```

---

## CLI (Hydra overrides)

```powershell
# Тонкая настройка через CLI
python -m topic_modeler mode=train \
  umap.n_neighbors=10 \
  hdbscan.min_cluster_size=3 \
  bertopic.nr_topics=20 \
  representation.use_mmr=false

# Другая директория с данными
python -m topic_modeler mode=train input_dir=my_articles

# Другой путь к модели
python -m topic_modeler mode=add_article \
  article_path=parsed_yaml/123456.yaml \
  model_dir=models/v2
```

---

## Python API

```python
from pathlib import Path
from omegaconf import OmegaConf
from topic_modeler.modeler import TopicModeler

cfg = OmegaConf.load("topic_modeler/conf/config.yaml")
modeler = TopicModeler(cfg)

# ── Обучение ──────────────────────
result = modeler.train(
    input_dir=Path("parsed_yaml"),
    csv_paths=[
        Path("data/row_data/scrapped_articles.csv"),
        Path("data/row_data/scrapped_articles_1.csv"),
    ],
)
print(result)
# {'n_articles': 42, 'n_topics': 8, 'n_assigned': 38, 'n_outliers': 4, ...}

# ── Добавление статьи ────────────
result = modeler.add_article(
    yaml_path=Path("parsed_yaml/957000_20260204_130209.yaml"),
    csv_paths=[Path("data/row_data/scrapped_articles.csv")],
)
print(result)
# {'article_id': '957000', 'topic_id': 3, 'topic_label': 'NLP | BERT | ...', ...}

modeler.close()
```

### Загрузка метаданных отдельно

```python
from pathlib import Path
from topic_modeler.metadata_loader import load_metadata

meta = load_metadata([Path("data/row_data/scrapped_articles.csv")])
article = meta["957000"]
print(article.author, article.tags, article.complexity)
```

### ArticleMeta

| Поле | Тип | Описание |
|------|-----|----------|
| `title` | `str` | Название статьи |
| `author` | `str` | Автор |
| `reading_time` | `str` | Время чтения |
| `complexity` | `str` | Уровень сложности |
| `labels` | `list[str]` | Метки (перевод, туториал, ...) |
| `tags` | `list[str]` | Теги и хабы |
| `hubs` | `list[str]` | Хабы (отдельно, если удастся разделить) |

> **Примечание:** `views` и `karma` не сохраняются — они динамические.

---

## Архитектура модуля

```
topic_modeler/
├── __init__.py          # Пакет
├── __main__.py          # Hydra CLI entry point
├── modeler.py           # TopicModeler (train / add_article)
├── metadata_loader.py   # CSV → ArticleMeta
├── conf/
│   └── config.yaml      # Конфигурация всех компонентов
└── README.md            # ← вы здесь
```

Общие модули:
- `stores/graph_store.py` — Neo4j (Topic, Article, BELONGS_TO_TOPIC)
- `raptor_pipeline/embeddings/providers.py` — BERTA эмбеддинги

---

## Зависимости

```
bertopic
umap-learn
hdbscan
sentence-transformers
safetensors
neo4j
numpy
pandas / csv
hydra-core
omegaconf
```
