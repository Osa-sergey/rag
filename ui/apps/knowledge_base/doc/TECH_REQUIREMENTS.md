# Knowledge Base — Технические требования (React Flow + Panels)

## Стек технологий
- **Граф знаний**: `@xyflow/react` (React Flow v12) — визуализация Neo4j графа
- **Фреймворк**: React 18+ (Vite)
- **Дерево RAPTOR**: Кастомный tree-компонент (или React Flow в вертикальном режиме)
- **Стейт**: Zustand (общий с dag_builder через `packages/shared`)
- **Стилизация**: CSS Modules + CSS Variables (dark mode)
- **Текстовый просмотр**: Markdown-рендерер (react-markdown) для отображения чанков
- **Diff-просмотр**: `react-diff-viewer` — для сравнения Snapshot vs Current текста

---

## 1. Архитектура компонентов

### 1.1. Layout (Корневой макет)

```
┌──────────────────────────────────────────────────────────────┐
│  TopBar (поиск, фильтры по domain/article, режим просмотра) │
├──────────┬─────────────────────────────┬─────────────────────┤
│ Navigator│     Main View              │  Detail Panel       │
│          │  (переключается)            │  (контекст выбр.   │
│ ○ Статьи │  ┌─ Graph View ──────────┐ │   элемента)         │
│ ○ Концепт│  │ ReactFlow Canvas      │ │                     │
│ ○ Inbox  │  │ (Neo4j визуализация)  │ │  ○ Описание         │
│          │  └───────────────────────┘ │  ○ Keywords          │
│ Фильтры: │  ┌─ Tree View ──────────┐ │  ○ Source chunks     │
│ [domain] │  │ RAPTOR иерархия      │ │  ○ Version history   │
│ [article]│  └───────────────────────┘ │  ○ Actions           │
│          │  ┌─ List View ──────────┐ │                     │
│          │  │ Табличный список     │ │                     │
│          │  └───────────────────────┘ │                     │
├──────────┴─────────────────────────────┴─────────────────────┤
│  BottomPanel: Source Text Viewer (чанк текста + подсветка)   │
└──────────────────────────────────────────────────────────────┘
```

### 1.2. Режимы Main View

| Режим | Назначение | Компонент |
|---|---|---|
| **Graph View** | Визуализация Neo4j графа (концепты, keywords, статьи) | React Flow Canvas |
| **Tree View** | RAPTOR иерархия для конкретной статьи | Кастомный Tree + React Flow vertical |
| **List View** | Табличный список концептов / keywords | Таблица с сортировкой и фильтрацией |

---

## 2. Graph View (React Flow Canvas)

### 2.1. Node Types

```tsx
const nodeTypes = {
  article: ArticleNode,
  keyword: KeywordNode,
  concept: ConceptNode,
  conceptInactive: ConceptInactiveNode,  // is_active = false
};
```

#### ArticleNode

```
┌─ ArticleNode ────────────────────┐
│  📄  "Трансформеры в NLP"        │
│  article_id: 986380              │
│  domain: nlp                     │
│  chunks: 24  keywords: 15        │
│──────────────────────────────────│
│  ○ HAS_KEYWORD (15)     Output ○│
└──────────────────────────────────┘
```

- **Handle right** (`source`): Исходящие ребра `HAS_KEYWORD`.
- **Handle left** (`target`): Входящие `REFERENCES` от другой статьи.
- Клик → Detail Panel показывает метаданные и список ключевых слов.

#### KeywordNode

```
┌─ KeywordNode ──────────┐
│  🏷️ "attention mechanism"│
│  score: 0.92           │
│  chunks: [c1, c3, c7]  │
└────────────────────────┘
```

- **Handle left** (`target`): Входящие `HAS_KEYWORD` от Article.
- **Handle right** (`source`): Исходящие `INSTANCE_OF` к Concept.
- Размер ноды масштабируется по `score` (ранжированные доказательства).
- Клик → Detail Panel показывает исходный текст чанков.

#### ConceptNode

```
┌─ ConceptNode ─────────────────────────┐
│  💡 "Механизмы внимания"        v2   │
│  domain: nlp                         │
│  articles: [986380, 987201]     🟢   │
│  keywords: 12                        │
│──────────────────────────────────────│
│  📤 CROSS_RELATED_TO (3)             │
│  🕐 Outdated Source ⚠️               │
└──────────────────────────────────────┘
```

- **Handle left** (`target`): Входящие `INSTANCE_OF` от Keywords.
- **Handle right** (`source`): Исходящие `CROSS_RELATED_TO` к другим Concepts.
- **Handle bottom** (`source`): Исходящие `EVOLVED_TO` к следующей версии.
- Бейдж версии (`v2`) + цветовой индикатор `is_active`.
- Маркер ⚠️ `Outdated Source` если `source_versions` не совпадает.
- `is_manual` → дополнительный бейдж "Manual".

#### ConceptInactiveNode
Тот же `ConceptNode`, но с пониженной прозрачностью (opacity 0.4) и пунктирной рамкой. Показывается только при переключении "Show history".

### 2.2. Edge Types

```tsx
const edgeTypes = {
  hasKeyword: HasKeywordEdge,        // Article → Keyword
  instanceOf: InstanceOfEdge,        // Keyword → Concept
  crossRelated: CrossRelatedEdge,    // Concept ↔ Concept
  evolvedTo: EvolvedToEdge,          // Concept v1 → Concept v2
  references: ReferencesEdge,        // Article → Article
};
```

| Edge | Стиль | Label (EdgeLabelRenderer) |
|---|---|---|
| `HAS_KEYWORD` | Solid, thin, gray | `score: 0.92` (при hover) |
| `INSTANCE_OF` | Solid, medium, blue | `similarity: 0.87` |
| `CROSS_RELATED_TO` | Dashed, thick, orange | `type: "complementary"`, `source: [articles]` |
| `EVOLVED_TO` | Dotted, green arrow | `v1 → v2` |
| `REFERENCES` | Solid, thin, purple | — |

### 2.3. Уровни отображения (Layer Filters)

Граф слишком большой для показа целиком. UI должен поддерживать слои:

```tsx
const [visibleLayers, setVisibleLayers] = useState({
  articles: true,
  keywords: false,    // скрыты по умолчанию (их может быть сотни)
  concepts: true,
  crossRelations: true,
  versionHistory: false,
});
```

Панель фильтров (`<Panel position="top-left">`):
- ☑ Articles  ☑ Concepts  ☐ Keywords  ☑ Cross-relations  ☐ Version History
- Slider: "Minimum similarity score" (фильтрует `INSTANCE_OF` и `CROSS_RELATED_TO`).

---

## 3. Tree View (RAPTOR Hierarchy)

### 3.1. Источник данных

Коллекция `raptor_chunks` из Qdrant. Каждый point содержит:
- `level`: 0 (leaf chunk) → N (root summary)
- `children_ids`: ID дочерних узлов
- `text`: текст чанка или саммари

### 3.2. Компонент

Вертикальное дерево (React Flow с `dagre` layout или кастомный tree):

```
           ┌──────────────────┐
           │  Root Summary    │  level=2
           │  (краткое содерж)│
           └────────┬─────────┘
              ┌─────┴──────┐
        ┌─────┴──┐    ┌────┴───┐
        │Section │    │Section │  level=1
        │Summary │    │Summary │
        └────┬───┘    └────┬───┘
          ┌──┴──┐       ┌──┴──┐
        ┌─┴─┐ ┌─┴─┐  ┌─┴─┐ ┌─┴─┐
        │c1 │ │c2 │  │c3 │ │c4 │  level=0
        └───┘ └───┘  └───┘ └───┘  (original text)
```

- Клик на узел → Bottom Panel показывает текст.
- Expand/collapse анимация.
- Подсветка пути от выбранного keyword до корня.

---

## 4. Detail Panel (Инспектор выбранного элемента)

### 4.1. Для Concept

| Секция | Содержимое |
|---|---|
| **Header** | Название, domain, version badge, is_active, is_manual |
| **Description** | Полный текст описания (markdown-рендер) |
| **Keywords** | Список keyword-ов с similarity score (сортированный) |
| **Source Articles** | Список article_id с маркерами Outdated ⚠️ |
| **Source Text (Traceability)** | По клику на keyword → показ чанков (Snapshot / Current toggle) |
| **Version History** | Timeline: v1 → v2 → v3 с diff-ами описаний |
| **Actions** | [Expand] [Edit Description] [Delete] [Create New Version] |

### 4.2. Для Keyword

| Секция | Содержимое |
|---|---|
| **Header** | Название, тип (keyword/relation), score |
| **Source Chunks** | Список чанков текста откуда извлечено (+ подсветка) |
| **Used in Concepts** | Список концептов, которые включают этот keyword |
| **Articles** | В каких статьях встречается |

### 4.3. Source Text Viewer (Bottom Panel)

```
┌─ Source Text ──────────────────────────────────────────────┐
│  📄 Article: 986380 "Трансформеры в NLP"                   │
│  Chunk: c7 (level 0)                                       │
│                                                            │
│  [Snapshot] [Current] [Diff]  ← toggle                    │
│                                                            │
│  "...механизм внимания (attention) позволяет модели        │
│   фокусироваться на ██████████████████ релевантных частях  │
│   входной последовательности..."                           │
│                                                            │
│  Extracted: 🏷️ "attention mechanism" (score: 0.92)          │
└────────────────────────────────────────────────────────────┘
```

- **Snapshot**: Текст на момент создания концепта.
- **Current**: Текущий текст из Qdrant.
- **Diff**: `react-diff-viewer` показывает изменения.
- Подсветка извлеченных сущностей прямо в тексте (highlight spans).

---

## 5. Concept Lifecycle Panels

### 5.1. Expand Panel (Обновление концепта)

```
┌─ Expand Concept: "Механизмы внимания" ─────────────────────┐
│                                                            │
│  Add Articles: [+ Select articles]                         │
│  Selected: 📄 992001 "Multi-head attention"                │
│                                                            │
│  ┌─ Version Comparison ──────────────────────────────────┐ │
│  │  v1 (current)  │  v2 (direct)   │  v3 (LLM-verified) │ │
│  │  12 keywords   │  +5 keywords   │  +8 keywords        │ │
│  │                │  cos ≥ 0.85    │  + LLM check        │ │
│  │  [Active]      │  [Select]      │  [Select]           │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                            │
│  New keywords:                                             │
│    ✅ "multi-head attention" (0.93)  — direct match        │
│    ✅ "scaled dot-product" (0.88)    — direct match        │
│    ☐  "cross-attention" (0.72)       — candidate (LLM ✓)  │
│    ☐  "positional encoding" (0.65)   — candidate (LLM ✗)  │
│                                                            │
│  [Cancel]                    [Apply v2]  [Apply v3]        │
└────────────────────────────────────────────────────────────┘
```

### 5.2. Create Concept Wizard

```
Step 1/3: Define                  Step 2/3: Review               Step 3/3: Confirm
┌─────────────────────┐          ┌──────────────────────┐       ┌─────────────────┐
│ Name: [___________] │          │ Direct matches (8):  │       │ Final Review:   │
│ Domain: [dropdown]  │   ──▶    │  ✅ "transformer"    │  ──▶  │ Name: ...       │
│ Description:        │          │  ✅ "self-attention"  │       │ Keywords: 12    │
│ [________________]  │          │                      │       │ Articles: 3     │
│ Articles:           │          │ Candidates (5):      │       │ Description:    │
│  [+ Add articles]   │          │  ☐ "BERT encoder"    │       │  (LLM enriched) │
│                     │          │  ☐ "GPT decoder"     │       │ [Create]        │
└─────────────────────┘          └──────────────────────┘       └─────────────────┘
```

### 5.3. Inbox / Needs Review

Список `Stale` концептов, у которых обновились исходные статьи:

```
┌─ Needs Review (3) ─────────────────────────────────────────┐
│                                                            │
│  ⚠️ "Механизмы внимания" v2                                │
│     Article 986380 updated 2h ago  │  [Review Diff] [Skip] │
│                                                            │
│  ⚠️ "Трансферное обучение" v1                               │
│     Article 987201 updated 1d ago  │  [Review Diff] [Skip] │
│                                                            │
│  ⚠️ "Tokenization" v3                                       │
│     2 articles updated             │  [Review Diff] [Skip] │
└────────────────────────────────────────────────────────────┘
```

---

## 6. API Layer (Backend)

| Method | Endpoint | Описание |
|---|---|---|
| GET | `/api/kb/articles` | Список статей (с фильтрами domain, status) |
| GET | `/api/kb/articles/{id}` | Метаданные статьи |
| GET | `/api/kb/articles/{id}/chunks` | Чанки текста (level 0) |
| GET | `/api/kb/articles/{id}/tree` | RAPTOR-дерево (все уровни) |
| GET | `/api/kb/articles/{id}/keywords` | Keywords статьи с scores |
| GET | `/api/kb/concepts` | Список активных концептов |
| GET | `/api/kb/concepts/{id}` | Концепт + keywords + versions |
| GET | `/api/kb/concepts/{id}/history` | Цепочка `EVOLVED_TO` версий |
| GET | `/api/kb/concepts/{id}/chunks` | Исходные чанки (snapshot + current) |
| POST | `/api/kb/concepts/expand` | Запуск expand (article_ids, concept_id) |
| POST | `/api/kb/concepts/expand/finalize` | Применить выбранную версию |
| POST | `/api/kb/concepts/create` | Manual concept creation |
| GET | `/api/kb/concepts/stale` | Список Stale концептов (Inbox) |
| GET | `/api/kb/graph` | Подграф Neo4j для визуализации (с фильтрами) |
| GET | `/api/kb/graph/neighbors/{id}` | Ближайший подграф для конкретного узла |
