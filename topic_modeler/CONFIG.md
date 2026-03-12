# Topic Modeler -- Конфигурация

Полная справка по параметрам конфигурации.
Файл конфига: `topic_modeler/conf/config.yaml`.

---

## CLI-опции (прямые)

Эти параметры доступны как Click-опции с `--help`, типизацией и автодополнением:

| Опция | Тип | YAML-путь | Описание |
|-------|-----|-----------|----------|
| `--input-dir` | TEXT | `input_dir` | Директория с YAML-статьями |
| `--model-dir` | TEXT | `model_dir` | Куда сохранить / откуда загрузить модель |
| `--device` | `cpu\|cuda\|mps` | `embeddings.model_kwargs.device` | Устройство для эмбеддингов |
| `--min-cluster-size` | INT | `hdbscan.min_cluster_size` | HDBSCAN: мин. размер кластера |
| `--nr-topics` | INT | `bertopic.nr_topics` | Число топиков (null = авто) |
| `-o, --override` | TEXT | любой | Hydra override `key=value` |
| `-v, --verbose` | flag | — | Подробный вывод (DEBUG) |

---

## Глубокие параметры (через `-o`)

Все остальные параметры передаются через `-o key=value`:

### UMAP (снижение размерности)

| Параметр | Тип | Диапазон | По умолчанию | Описание |
|----------|-----|----------|--------------|----------|
| `umap.n_neighbors` | int | 2..200 | 15 | Число ближайших соседей |
| `umap.n_components` | int | 2..100 | 5 | Размерность проекции |
| `umap.min_dist` | float | 0.0..1.0 | 0.1 | Минимальная дистанция |
| `umap.metric` | enum | `cosine\|euclidean\|manhattan\|correlation` | cosine | Метрика расстояния |

### HDBSCAN (кластеризация)

| Параметр | Тип | Диапазон | По умолчанию | Описание |
|----------|-----|----------|--------------|----------|
| `hdbscan.min_cluster_size` | int | 2..500 | 5 | Минимальный размер кластера |
| `hdbscan.min_samples` | int | 1..100 | 1 | Минимальная плотность |
| `hdbscan.metric` | enum | `euclidean\|manhattan\|cosine` | euclidean | Метрика |
| `hdbscan.cluster_selection_method` | enum | `eom\|leaf` | eom | Метод выбора кластеров |

### CountVectorizer (токенизация)

| Параметр | Тип | Диапазон | По умолчанию | Описание |
|----------|-----|----------|--------------|----------|
| `vectorizer.min_df` | int | >= 1 | 2 | Минимальная document frequency |
| `vectorizer.ngram_range` | list | [min, max] | [1, 2] | Диапазон N-грамм |
| `vectorizer.stop_words` | str\|null | — | null | Стоп-слова |

### BERTopic (основные)

| Параметр | Тип | Диапазон | По умолчанию | Описание |
|----------|-----|----------|--------------|----------|
| `bertopic.language` | str | — | russian | Язык текстов |
| `bertopic.top_n_words` | int | 1..50 | 15 | Слов на топик |
| `bertopic.min_topic_size` | int | 2..100 | 3 | Минимальный размер топика |
| `bertopic.nr_topics` | int\|null | >= 2 | null | Число топиков (null = авто) |

### Representation Models

| Параметр | Тип | Диапазон | По умолчанию | Описание |
|----------|-----|----------|--------------|----------|
| `representation.use_keybert` | bool | — | true | Использовать KeyBERT |
| `representation.keybert.top_n_words` | int | 1..50 | 10 | Слов в KeyBERT |
| `representation.use_mmr` | bool | — | true | Использовать MMR |
| `representation.mmr.diversity` | float | 0.0..1.0 | 0.3 | Разнообразие ключевых слов |

### Embeddings

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `embeddings.provider` | str | huggingface | Провайдер |
| `embeddings.model_name` | str | sergeyzh/BERTA | Модель |
| `embeddings.local_path` | str\|null | D:/models/BERTA | Локальный путь |
| `embeddings.model_kwargs.device` | str | cuda | Устройство |
| `embeddings.embedding_dim` | int | 768 | Размерность |

### Neo4j

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `stores.neo4j.uri` | str | bolt://localhost:7687 | URI подключения |
| `stores.neo4j.user` | str | neo4j | Пользователь |
| `stores.neo4j.password` | str | — | Пароль |
| `stores.neo4j.database` | str | neo4j | Имя базы данных |

---

## Кросс-валидации

Эти ограничения проверяются при загрузке конфига:

| Правило | Ошибка |
|---------|--------|
| `hdbscan.min_cluster_size >= bertopic.min_topic_size` | Кластер не может быть меньше мин. топика |
| `umap.n_components < embeddings.embedding_dim` | Проекция не может превышать размерность эмбеддинга |
| `vectorizer.ngram_range` — ровно 2 элемента, min >= 1, max >= min | Невалидный диапазон N-грамм |

---

## Примеры

```powershell
# Базовый запуск
python -m topic_modeler train

# С Click-опциями
python -m topic_modeler train --device cuda --min-cluster-size 3

# С Hydra-overrides
python -m topic_modeler train -o "umap.n_neighbors=10" -o "bertopic.nr_topics=20"

# Комбинация
python -m topic_modeler train --device cuda -o "umap.metric=euclidean"

# Проверка конфига
python -m topic_modeler validate
python -m topic_modeler validate -o "umap.metric=invalid"

# Показать сырой YAML
python -m topic_modeler show-config
```
