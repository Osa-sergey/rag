# Concept Builder — кросс-статейное объединение ключевых слов

Модуль `concept_builder` строит **Concept-ноды** — обобщённые понятия, объединяющие семантически близкие ключевые слова из нескольких связанных статей. Для каждого понятия создаётся описание, определяется домен знаний, а между понятиями извлекаются **кросс-связи** (cross-relations).

---

## Обзор архитектуры

```
                  ┌─────────────────────┐
                  │   CLI (__main__.py)  │
                  │  dry-run / process   │
                  └──────────┬──────────┘
                             │
                  ┌──────────▼──────────┐
                  │  CrossArticleProcessor│ ← processor.py (оркестратор)
                  └──────────┬──────────┘
                             │
      ┌──────────┬───────────┼───────────┬──────────┐
      │          │           │           │          │
      ▼          ▼           ▼           ▼          ▼
 ArticleSelector  Keyword   Concept   Relation   Concept
  (BFS/DFS)     Describer  Clusterer  Builder   Inspector
```

### Компоненты

| Файл | Компонент | Назначение |
|------|-----------|------------|
| `article_selector.py` | `ArticleSelector` | Выбор связанных статей через граф `REFERENCES` |
| `keyword_describer.py` | `KeywordDescriber` | Генерация LLM-описаний для ключевых слов (dual-context) |
| `concept_clusterer.py` | `ConceptClusterer` | Кластеризация keywords → Concepts по cosine similarity |
| `relation_builder.py` | `RelationBuilder` | Извлечение кросс-связей между Concepts через LLM |
| `inspector.py` | `ConceptInspector` | Инспекция и трейсинг Concept → Keyword → Chunks |
| `processor.py` | `CrossArticleProcessor` | Оркестратор полного пайплайна |
| `models.py` | Dataclasses | `KeywordContext`, `ConceptNode`, `CrossRelation`, `DryRunReport` |
| `schemas.py` | Pydantic | Конфигурация (LLM, embeddings, stores, prompts) |
| `containers.py` | DI Container | dependency-injector, аналогично raptor_pipeline |
| `conf/config.yaml` | Hydra config | Пороги, промпты, подключения к stores |

---

## Пайплайн обработки — пошагово

### Шаг 1: Выбор статей (`ArticleSelector`)

Модуль работает с **группой связанных статей**. Есть два режима выбора:

#### 1a. Автоматический обход графа (BFS/DFS)

```
python -m concept_builder dry-run --base-article 986380 --strategy bfs --max-articles 10
```

Алгоритм:
1. Начинаем с указанной `base_article_id`.
2. Находим все статьи, связанные через рёбра `REFERENCES` (в **обоих** направлениях — Neo4j undirected match).
3. Обходим граф в ширину (BFS) или глубину (DFS).
4. Останавливаемся при достижении `max_articles`.

```cypher
-- Запрос для поиска соседей (обе направления REFERENCES)
MATCH (a:Article {id: $id})-[:REFERENCES]-(b:Article)
RETURN DISTINCT b.id AS neighbour_id
```

**Важно**: BFS/DFS может найти **placeholder-статьи** — ноды, которые существуют в Neo4j как цели ссылок, но ещё не были обработаны через `raptor_pipeline` (у них нет keywords). Такие статьи помечаются как `⚠️ НЕ ОБРАБОТАНА` и пропускаются при обработке.

#### 1b. Явный список статей

```
python -m concept_builder dry-run --article-ids 986380,983714,985200
```

- Каждая статья проверяется на существование в Neo4j.
- Несуществующие статьи пропускаются с предупреждением (выводятся похожие ID).
- Опционально проверяется связность (`--no-check-connectivity` для отключения).

#### Валидация

- Если `--base-article` не найдена → `ValueError` с подсказкой похожих статей.
- Если из `--article-ids` часть не найдена → предупреждение, продолжение с остальными.
- Если ни одна не найдена → ошибка.

---

### Шаг 2: Загрузка keywords из Neo4j

Для каждой **обработанной** статьи загружаются все keywords из графа:

```cypher
MATCH (a:Article {id: $id})-[r:HAS_KEYWORD]->(k:Keyword)
RETURN k.word, k.category, r.confidence, r.chunk_ids
```

Фильтрация по `min_keyword_confidence` (по умолчанию **0.8**). Из каждого keyword создаётся `KeywordContext`:

```python
KeywordContext(
    word="docker",
    article_id="986380",
    version="v3",
    category="technology",
    confidence=0.92,
    chunk_ids=["node_123", "node_456"],  # RAPTOR-ноды где встречается
)
```

---

### Шаг 3: Генерация описаний (`KeywordDescriber`)

Для каждого keyword генерируется контекстное описание с помощью **dual-context стратегии**:

```
Keyword: "docker"
    │
    ├── Broad context (max-level RAPTOR chunk)
    │   "Docker — платформа контейнеризации, используемая
    │    для изоляции приложений..."
    │
    └── Detail context (leaf chunk, level=0, max text length)
        "В данной статье Docker используется для деплоя
         микросервисной архитектуры на Kubernetes..."
```

**Алгоритм:**
1. По `chunk_ids` из `HAS_KEYWORD` → найти точки в Qdrant.
2. **Broad context**: чанк с максимальным `level` (обобщение из RAPTOR-дерева).
3. **Detail context**: leaf-чанк (level=0) с максимальной длиной текста.
4. Оба контекста усекаются до `max_prompt_tokens * 0.4` (по ~40% бюджета на каждый).
5. LLM генерирует 1-2 предложения, описывающие значение keyword в контексте статьи.

**Промпт** (из `conf/config.yaml`):
```
Ты получаешь два фрагмента текста, в которых упоминается ключевое слово "{keyword}".

== ОБОБЩЁННЫЙ КОНТЕКСТ (высокий уровень иерархии) ==
{broad_context}

== ДЕТАЛЬНЫЙ ИСХОДНЫЙ ТЕКСТ ==
{detail_context}

Напиши 1-2 предложения, описывающие значение "{keyword}" в контексте этой статьи.
```

---

### Шаг 4: Вычисление embeddings

Для каждого описания keyword вычисляется embedding через модель BERTA (`sergeyzh/BERTA`, dim=768):

```python
descriptions = ["docker используется для контейнеризации...", ...]
embeddings = embedder.embed_texts(descriptions)  # → list[list[float]]
```

---

### Шаг 5: Кластеризация → Concepts (`ConceptClusterer`)

**Ключевой шаг**: одинаковые или семантически близкие keywords из разных статей объединяются в один **Concept**.

#### Алгоритм (greedy single-pass clustering)

```
Вход: [KeywordContext с embeddings], threshold = 0.85

1. Сортировка по word (алфавитно, для детерминизма)
2. Для каждого keyword:
   a. Вычислить cosine similarity с центроидами существующих кластеров
   b. Если max(similarity) ≥ 0.85 → добавить в этот кластер, пересчитать центроид
   c. Иначе → создать новый кластер
```

**Пример:**

```
Keyword "docker" из статьи A (описание: "контейнеризация для CI/CD")
Keyword "docker" из статьи B (описание: "контейнеризация для микросервисов")
  → cosine_sim = 0.92 ≥ 0.85 → ОДИН кластер → Concept "docker"

Keyword "docker" из статьи C (описание: "инструмент сборки образов")
  → cosine_sim с центроидом = 0.87 ≥ 0.85 → добавляется в тот же Concept

Keyword "kubernetes" из статьи A (описание: "оркестрация контейнеров")
  → cosine_sim с "docker" = 0.72 < 0.85 → НОВЫЙ Concept "kubernetes"
```

**Важно**: одно и то же слово в разных доменах может дать **разные** Concepts, если описания сильно отличаются:
```
"pipeline" в DevOps → "CI/CD pipeline для автоматизации деплоя"
"pipeline" в ML     → "Pipeline для обучения моделей и препроцессинга"
  → cosine_sim = 0.65 < 0.85 → ДВА разных Concept
```

---

### Шаг 6: Создание Concept-нод (LLM обобщение)

Для каждого кластера из ≥2 keywords LLM генерирует обобщённое описание:

```
Промпт:
  Ниже приведены описания ключевого слова "docker" из разных статей:
  - [986380] Docker используется для контейнеризации CI/CD
  - [983714] Docker как основа микросервисной архитектуры

  Объедини в одно обобщённое определение. Определи домен знаний.

Ответ (JSON):
  {
    "canonical_name": "docker",
    "domain": "devops",
    "description": "Платформа контейнеризации для изоляции и развёртывания приложений..."
  }
```

Результат — `ConceptNode`:
```python
ConceptNode(
    id="uuid",
    canonical_name="docker",
    domain="devops",
    description="Платформа контейнеризации...",
    source_articles=["986380", "983714"],
    source_versions={"986380": "v3", "983714": "v2"},
    keyword_words=["docker", "Docker"],
    embedding=[0.12, -0.34, ...],  # 768-dim
)
```

---

### Шаг 7: Извлечение кросс-связей (`RelationBuilder`)

LLM анализирует все созданные Concepts и находит семантические связи:

```
Промпт:
  Даны понятия из разных статей:
  - docker (devops): Платформа контейнеризации...
  - kubernetes (devops): Оркестрация контейнеров...
  - CI/CD (devops): Непрерывная интеграция и доставка...

  Найди семантические связи между ними.

Ответ (JSON):
  [
    {"source": "docker", "target": "kubernetes",
     "predicate": "используется_в", "description": "Docker-контейнеры оркестрируются Kubernetes", "confidence": 0.95},
    {"source": "CI/CD", "target": "docker",
     "predicate": "использует", "description": "CI/CD пайплайны используют Docker для сборки", "confidence": 0.88}
  ]
```

---

### Шаг 8: Сохранение в хранилища

#### Neo4j — граф

```
(:Concept {id, canonical_name, domain, description, source_articles})
(:Keyword)-[:INSTANCE_OF]->(:Concept)
(:Concept)-[:CROSS_RELATED_TO {predicate, description, confidence}]->(:Concept)
```

#### Qdrant — векторное хранилище

Два отдельных collection с embeddings (dim=768, cosine distance):

- **`concepts`** — embedding описания Concept (для семантического поиска по понятиям)
- **`cross_relations`** — embedding описания связи (для поиска по типам отношений)

---

## Граф-схема (полная)

```
(:Article)-[:HAS_KEYWORD {confidence, chunk_ids}]->(:Keyword)
(:Keyword)-[:RELATED_TO {predicate, confidence}]->(:Keyword)
(:Keyword)-[:INSTANCE_OF]->(:Concept)
(:Concept)-[:CROSS_RELATED_TO {predicate, description, confidence}]->(:Concept)
(:Article)-[:REFERENCES]->(:Article)
```

---

## CLI-команды

### dry-run — предпросмотр без LLM

```bash
# От базовой статьи BFS с лимитом
python -m concept_builder dry-run -b 986380 --strategy bfs --max-articles 10

# Явный список статей
python -m concept_builder dry-run -a 986380,983714

# Без проверки связности
python -m concept_builder dry-run -a 986380,983714 --no-check-connectivity
```

Вывод:
```
═══════════════════════════════════════════════════
  DRY RUN — 3 статей
═══════════════════════════════════════════════════

  📄 986380 (docker_article) — 15/20 keywords (≥0.8 / total)
     confidence: ≥0.8: 15, 0.5-0.8: 3, <0.5: 2, NULL: 0
  📄 983714 (kubernetes_article) — 12/18 keywords (≥0.8 / total)
  ⚠️  985200 (linked_article) — НЕ ОБРАБОТАНА (нет keywords)

  ⚠️  1 из 3 статей не обработаны. Сначала запустите raptor_pipeline для них.

  Связи между статьями (2):
    983714 → 986380
    985200 → 986380

  Всего keywords (≥0.8): 27
  Оценка LLM-вызовов: ~37
```

### process — полный запуск

```bash
python -m concept_builder process -b 986380 --max-articles 5
python -m concept_builder process -a 986380,983714
```

### inspect-concept — инспекция с трейсингом

```bash
python -m concept_builder inspect-concept -c <concept-uuid>
```

Выводит: описание Concept → список keywords → для каждого keyword → chunk_ids → тексты чанков из Qdrant.

### trace-keyword — трейсинг keyword до чанков

```bash
python -m concept_builder trace-keyword -w docker -a 986380
```

### validate / show-config

```bash
python -m concept_builder validate
python -m concept_builder show-config
```

---

## Конфигурация (`conf/config.yaml`)

| Параметр | Значение | Описание |
|----------|---------|----------|
| `similarity_threshold` | 0.85 | cosine ≥ X → один Concept |
| `min_keyword_confidence` | 0.8 | порог confidence для keywords |
| `max_prompt_tokens` | 3000 | лимит токенов для промптов |
| `default_strategy` | bfs | стратегия обхода по умолчанию |
| `default_max_articles` | 20 | лимит статей при обходе |

---

## Зависимости от других модулей

```
concept_builder
  ├── raptor_pipeline   → embeddings (BERTA), LLM (_build_llm), TokenTracker
  ├── stores            → graph_store (Neo4j), vector_store (Qdrant)
  ├── interfaces        → ABCs (BaseArticleSelector, BaseKeywordDescriber, ...)
  └── cli_base          → load_config, resolve_class, add_common_commands
```
