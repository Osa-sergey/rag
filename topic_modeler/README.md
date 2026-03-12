# Topic Modeler

Standalone утилита для тематического моделирования статей на базе [BERTopic](https://maartengr.github.io/BERTopic/).

Обучает модель на коллекции статей из `parsed_yaml/`, обнаруживает топики, обогащает Article-ноды метаданными из CSV и создаёт `:Topic` сущности в Neo4j.

> Подробная справка по конфигурации: [CONFIG.md](CONFIG.md)

---

## Быстрый старт

```powershell
# Посмотреть доступные команды
python -m topic_modeler --help

# Обучить модель
python -m topic_modeler train

# С настройками
python -m topic_modeler train --device cuda --min-cluster-size 3

# Добавить одну статью
python -m topic_modeler add-article parsed_yaml/957000.yaml

# Проверить конфиг (без запуска)
python -m topic_modeler validate

# Показать текущий YAML
python -m topic_modeler show-config
```

---

## Команды

| Команда | Описание |
|---------|----------|
| `train` | Обучить BERTopic на всех статьях |
| `add-article` | Предсказать топик для новой статьи |
| `validate` | Проверить конфигурацию без запуска |
| `show-config` | Показать текущий YAML-конфиг |

### train

Загружает тексты из `input-dir`, вычисляет эмбеддинги (BERTA), обучает BERTopic (UMAP + HDBSCAN + KeyBERT), сохраняет модель и обновляет Neo4j.

```powershell
python -m topic_modeler train
python -m topic_modeler train --device cuda --min-cluster-size 3
python -m topic_modeler train -o "umap.n_neighbors=10" -o "bertopic.nr_topics=20"
```

### add-article

Загружает сохранённую модель и определяет топик для новой статьи.

```powershell
python -m topic_modeler add-article parsed_yaml/957000.yaml
python -m topic_modeler add-article myfile.yaml --model-dir models/v2
```

### validate

Проверяет конфиг через pydantic (типы, диапазоны, cross-field). Ошибки — до запуска:

```
  Ошибки конфигурации:
    umap.n_neighbors: >= 2 (получено: -1)
    umap.metric: 'cosine'|'euclidean'|'manhattan'|'correlation' (получено: 'invalid')
```

---

## Neo4j Schema

```
(:Article {id, title, author, reading_time, complexity, labels, tags, hubs})
(:Topic   {id, label, top_keywords})
(:Article)-[:BELONGS_TO_TOPIC {confidence}]->(:Topic)
```

---

## Python API

```python
from pathlib import Path
from omegaconf import OmegaConf
from topic_modeler.modeler import TopicModeler

cfg = OmegaConf.load("topic_modeler/conf/config.yaml")
modeler = TopicModeler(cfg)

result = modeler.train(
    input_dir=Path("parsed_yaml"),
    csv_paths=[Path("data/row_data/scrapped_articles.csv")],
)
modeler.close()
```

---

## Архитектура

```
topic_modeler/
  __init__.py
  __main__.py         # Click CLI (train, add-article, validate, show-config)
  modeler.py          # TopicModeler (train / add_article)
  schemas.py          # Pydantic-модели конфигурации
  metadata_loader.py  # CSV → ArticleMeta
  containers.py       # DI-контейнер (dependency-injector)
  conf/config.yaml    # YAML-конфиг
  CONFIG.md           # Справка по параметрам
  README.md           # (вы здесь)

interfaces/           # Абстрактные базовые классы (ABC)
  base.py             # BaseEmbeddingProvider, BaseGraphStore, BaseVectorStore, ...
  __init__.py         # Re-exports

cli_base/             # Общий модуль для CLI
  config_loader.py    # Hydra → pydantic bridge
  common_commands.py  # validate, show-config
  class_resolver.py   # resolve_class() — динамическая загрузка классов

stores/               # Общие хранилища
  graph_store.py      # Neo4jGraphStore(BaseGraphStore)
  vector_store.py     # QdrantVectorStore(BaseVectorStore)

raptor_pipeline/embeddings/
  providers.py        # HuggingFace / Ollama / DeepSeek (BaseEmbeddingProvider)
```

### DI-контейнер и замена классов

Классы `EmbeddingProvider` и `GraphStore` можно заменить через конфиг:

```yaml
# topic_modeler/conf/config.yaml
embeddings:
  class_: raptor_pipeline.embeddings.providers.HuggingFaceEmbeddingProvider

stores:
  graph_store:
    class_: stores.graph_store.Neo4jGraphStore
```

При инициализации `resolve_class(dotted_path, BaseEmbeddingProvider)` проверяет `issubclass` — любая custom-реализация должна наследовать базовый ABC из `interfaces/`.

---

## Зависимости

```
bertopic, umap-learn, hdbscan, sentence-transformers, safetensors
neo4j, numpy, hydra-core, omegaconf, click, pydantic, dependency-injector
```

