# UX/UI Design System — Единые визуальные стандарты

Документ фиксирует единые правила оформления для всех микрофронтендов UI-платформы: **DAG Builder** и **Knowledge Base**. Все компоненты разрабатываются и каталогизируются через **Storybook**.

---

## 1. Визуальная философия (на базе Python `diagrams`)

Стилистический ориентир — библиотека [diagrams](https://diagrams.mingrammer.com/): чистые, архитектурные диаграммы с узнаваемой эстетикой.

### 1.1. Принципы

| Принцип | Описание |
|---|---|
| **Clean Nodes** | Карточки узлов: светлый фон (`--bg-node`), мягкие тени (`box-shadow: 0 2px 8px rgba(0,0,0,0.08)`), скругленные углы (`border-radius: 12px`) |
| **Iconography** | Каждый тип узла имеет аккуратную иконку (lucide-react), индицирующую его суть: 🗃️ БД, 📄 документ, 🧠 модель, ⚙️ скрипт, 💡 концепт |
| **Clusters / Groups** | Логическая группировка узлов (SubFlows) обрамляется пунктирной рамкой с подписью заголовка группы. Контейнеры используют пастельный фон для отличия |
| **Smooth Edges** | Линии связей: SmoothStep / Bezier, не ломаные. Стрелки — тонкие, аккуратные, с выраженным направлением |
| **Whitespace** | Щедрые отступы между узлами (dagre/elkjs `nodesep: 80, ranksep: 120`) |
| **Palette Discipline** | Цвета не произвольные, а берутся из CSS Variables дизайн-системы (см. ниже) |

### 1.2. Цветовая палитра (CSS Variables)

```css
:root {
  /* --- Surface --- */
  --bg-canvas:      #f8f9fc;   /* Фон канваса */
  --bg-node:        #ffffff;   /* Фон ноды */
  --bg-node-hover:  #f0f4ff;   /* Hover */
  --bg-group:       #f3f0ff;   /* Фон SubFlow/Cluster */
  --bg-panel:       #ffffff;   /* Фон боковых панелей */
  
  /* --- Accent (По типу сущности) --- */
  --color-article:  #4a90e2;   /* 📄 Статьи / Document nodes */
  --color-keyword:  #50c878;   /* 🏷️ Keywords / Entity nodes */
  --color-concept:  #9b59b6;   /* 💡 Concepts */
  --color-step:     #3b82f6;   /* ⚙️ Pipeline Step (DAG) */
  --color-data:     #f59e0b;   /* 📤 Data Edge */
  --color-dep:      #94a3b8;   /* --- Dependency Edge (muted) */
  
  /* --- Status --- */
  --color-success:  #22c55e;
  --color-error:    #ef4444;
  --color-warning:  #f59e0b;
  --color-info:     #3b82f6;
  --color-stale:    #f97316;   /* Outdated / Needs Review */
  
  /* --- Borders & Shadows --- */
  --border-node:    1px solid #e2e8f0;
  --shadow-node:    0 2px 8px rgba(0, 0, 0, 0.08);
  --shadow-hover:   0 4px 16px rgba(0, 0, 0, 0.12);
  --radius-node:    12px;
  --radius-badge:   6px;
}

/* Dark mode */
[data-theme="dark"] {
  --bg-canvas:      #0f1117;
  --bg-node:        #1e2030;
  --bg-node-hover:  #262a3d;
  --bg-group:       #1a1730;
  --bg-panel:       #161824;
  --border-node:    1px solid #2d3148;
  --shadow-node:    0 2px 12px rgba(0, 0, 0, 0.4);
}
```

---

## 2. Компоненты дизайн-системы (ui-kit)

Все компоненты разрабатываются в `packages/shared/ui-kit/` и каталогизируются в **Storybook**.

### 2.1. Каталог базовых компонентов

| Компонент | Описание | Анимация (Framer Motion) |
|---|---|---|
| `<Panel>` | Resizable боковая/нижняя панель | `slide-in` / `slide-out` при открытии-закрытии |
| `<Badge>` | Цветной бейдж (статус, тип, версия) | `scale` при появлении |
| `<Form>` | Обертка @rjsf/core для JSON Schema форм | — |
| `<DiffViewer>` | Обертка react-diff-viewer | `fade-in` |
| `<SearchBar>` | Поле поиска с фильтрами | `expand` при фокусе |
| `<TabPanel>` | Переключатель с анимированным контентом | `crossfade` между табами |
| `<Dropdown>` | Выпадающий список с поиском | `height-auto` анимация |
| `<Timeline>` | Вертикальная timeline версий | Каскадное `stagger` появление элементов |
| `<StatusIcon>` | 🟢🔴🟡⚠️ иконки | `pulse` при изменении статуса |
| `<Tooltip>` | Контекстная подсказка | `fade + scale` |
| `<Accordion>` | Раскрывающийся блок | `height-auto` (Framer Motion `AnimatePresence`) |
| `<Skeleton>` | Loading placeholder | `shimmer` анимация |

### 2.2. Правила анимаций (Framer Motion)

```ts
// Общие пресеты — packages/shared/ui-kit/motion.ts
export const transitions = {
  spring:  { type: 'spring', stiffness: 300, damping: 24 },
  smooth:  { type: 'tween', duration: 0.2, ease: 'easeInOut' },
  stagger: { staggerChildren: 0.05 },
};

export const variants = {
  fadeIn:   { initial: { opacity: 0 }, animate: { opacity: 1 } },
  slideIn:  { initial: { x: 300, opacity: 0 }, animate: { x: 0, opacity: 1 } },
  scaleIn:  { initial: { scale: 0.9, opacity: 0 }, animate: { scale: 1, opacity: 1 } },
};
```

**Правила применения:**
- Анимации **не длиннее 300ms** — интерфейс должен ощущаться быстрым.
- **`AnimatePresence`** для mount/unmount (панели, модалки, тосты).
- **`layout`** prop для перераспределения элементов при фильтрации.
- Микро-анимации на hover (ноды графа: подъем тени, лёгкий scale 1.02).

---

## 3. Стили нод для графов

### 3.1. DAG Builder — StepNode

```
┌─────────────────────────────────────────┐ ← --radius-node, --shadow-node
│  ┌────┐  raptor_pipeline.run     ⟳ 🔔  │ ← Иконка модуля + callback icons
│  │icon│  "RAPTOR Pipeline"              │
│  └────┘  [devops] [indexing]            │ ← Tag badges
│─────────────────────────────────────────│
│  📥 Requires: ParseContext             │ ← Context badges
│  📤 Provides: RaptorContext            │
│─────────────────────────────────────────│
│  ○ input_dir: str    parsed_dir: str ○  │ ← I/O Handles
│─────────────────────────────────────────│
│  ⟳ retry: 3×30s  🔔 #data-errors       │ ← Callback summary (footer)
└─────────────────────────────────────────┘
```

**Цветовое кодирование рамки по статусу:**
- `idle` → `--border-node`
- `running` → `--color-info` (пульсирующая)
- `success` → `--color-success`
- `failed` → `--color-error`
- `validation error` → `--color-error` (пунктирная)

### 3.2. Knowledge Base — ArticleNode, KeywordNode, ConceptNode

| Нода | Акцентный цвет | Иконка | Масштабирование |
|---|---|---|---|
| `ArticleNode` | `--color-article` (синий) | 📄 | Фиксированный размер |
| `KeywordNode` | `--color-keyword` (зеленый) | 🏷️ | Размер пропорционален `score` |
| `ConceptNode` | `--color-concept` (фиолетовый) | 💡 | Фиксированный, с бейджем версии |
| `ConceptInactiveNode` | `--color-concept` + `opacity: 0.4` | 💡 | Пунктирная рамка |

### 3.3. Стили ребер

| Тип ребра | Стиль линии | Цвет | Маркер | Подпись |
|---|---|---|---|---|
| Data flow (`${{ }}`) | Solid, 2px | `--color-data` | Arrowhead | Тип данных (`str`) |
| Dependency (`depends_on`) | Dashed, 1px | `--color-dep` | Arrowhead | — |
| HAS_KEYWORD | Solid, 1px | gray | — | Score (hover) |
| INSTANCE_OF | Solid, 2px | blue | Arrowhead | Similarity |
| CROSS_RELATED_TO | Dashed, 2px | orange | Arrowhead | Predicate |
| EVOLVED_TO | Dotted, 2px | green | Arrowhead | `v1 → v2` |
| REFERENCES | Solid, 1px | purple | Arrowhead | — |

---

## 4. Кастомизация внешнего вида нод (Node Appearance Templates)

Пользователь может **создавать кастомный внешний вид** для новых компонентов пайплайна (Pipeline Steps) прямо в интерфейсе DAG Builder и сохранять как переиспользуемый шаблон.

### 4.1. Зачем

При регистрации нового `@register_step` в системе он получает generic-вид `StepNode`. Но для сложных пайплайнов, где десятки шагов, визуальное различие критично. Пользователь должен иметь возможность:
- Назначить свою **иконку** (из каталога lucide-react или загрузить SVG).
- Задать **акцентный цвет** (для рамки и заголовка ноды).
- Выбрать **layout** ноды (compact / expanded / wide).
- Определить, какие поля показывать **на самой ноде** (а не только в Inspector).
- Сохранить результат как **шаблон** (Node Appearance Template).

### 4.2. UI — редактор внешнего вида

```
┌─ Node Appearance Editor ──────────────────────────┐
│                                                    │
│  Step Type: raptor_pipeline.run                    │
│                                                    │
│  Icon:  [🧠 Search icons...   ▾]                  │
│  Color: [■ ■ ■ ■ ■ ■ ■ ■  │ Custom: #______]     │
│  Layout: ○ Compact  ● Expanded  ○ Wide             │
│                                                    │
│  Visible Fields on Node:                           │
│    ☑ module name                                   │
│    ☑ tags                                          │
│    ☐ description                                   │
│    ☑ context badges                                │
│    ☐ callback summary                              │
│    ☑ I/O ports                                     │
│                                                    │
│  ┌─ Live Preview ────────────────────────────┐     │
│  │  ┌────┐  raptor_pipeline.run              │     │
│  │  │ 🧠 │  "RAPTOR Pipeline"               │     │
│  │  └────┘  [indexing]                       │     │
│  │  📥 ParseContext  📤 RaptorContext        │     │
│  │  ○ input_dir: str       parsed_dir: str ○ │     │
│  └───────────────────────────────────────────┘     │
│                                                    │
│  Save as: [Template Name________]                  │
│                                                    │
│  [Cancel]        [Apply to this node]  [Save ▾]    │
│                            └─ Save as Template     │
│                            └─ Apply to all of type │
└────────────────────────────────────────────────────┘
```

### 4.3. Хранение шаблонов

```ts
interface NodeAppearanceTemplate {
  id: string;
  name: string;                    // "RAPTOR Dark"
  targetModule: string;            // "raptor_pipeline.run" или "*" (для всех)
  icon: string;                    // Имя lucide-react иконки или путь к SVG
  accentColor: string;             // "#9b59b6"
  layout: 'compact' | 'expanded' | 'wide';
  visibleFields: string[];         // ["module", "tags", "contextBadges", "ioPorts"]
  createdBy: string;
  createdAt: string;
}
```

Шаблоны сохраняются в **localStorage** (per-user) или через API (shared templates):
- `GET /api/ui/templates` — список шаблонов;
- `POST /api/ui/templates` — создать;
- `PUT /api/ui/templates/{id}` — обновить;
- `DELETE /api/ui/templates/{id}` — удалить.

### 4.4. Применение шаблонов

- **Автоматическое**: При Drag&Drop ноды из NodePalette система проверяет, есть ли шаблон для данного `module`. Если есть → применяет автоматически.
- **Ручное**: Правый клик на ноде → "Change Appearance" → выбрать из списка шаблонов.
- **Массовое**: "Apply to all nodes of type X" — обновить все ноды данного типа на канвасе.

---

## 5. Типографика

```css
:root {
  --font-family:     'Inter', system-ui, sans-serif;
  --font-mono:       'JetBrains Mono', 'Fira Code', monospace;
  --font-size-xs:    11px;   /* Метки на ребрах, мелкие бейджи */
  --font-size-sm:    13px;   /* Текст внутри нод */
  --font-size-base:  14px;   /* Inspector body */
  --font-size-lg:    16px;   /* Заголовки нод, панелей */
  --font-size-xl:    20px;   /* PageTitle */
  --line-height:     1.5;
  --font-weight-normal: 400;
  --font-weight-semibold: 600;
}
```

---

## 6. Layout-паттерны (общие для обоих приложений)

```
┌──────────────────────────────────────────────────────────┐
│  TopBar                                                   │  48px fixed
├─────────┬────────────────────────────┬────────────────────┤
│ Sidebar │     Main Canvas            │  Inspector Panel   │  flex-grow
│ (240px) │                            │  (360px, resizable)│
│ drag-   │  React Flow + Controls     │                    │
│ resize  │  MiniMap, Background       │  Tabs, Forms       │
│         │                            │                    │
├─────────┴────────────────────────────┴────────────────────┤
│  BottomPanel (resizable, collapsible)                     │  200px default
│  YAML Editor (DAG) / Source Text Viewer (KB)              │
└──────────────────────────────────────────────────────────┘
```

- Все панели **resizable** через CSS `resize` или react-resizable-panels.
- **Collapsible**: по двойному клику на разделитель панель сворачивается.
- Keyboard shortcut `Cmd+B` / `Ctrl+B` → скрыть Sidebar.
- `Cmd+J` / `Ctrl+J` → скрыть BottomPanel.

---

## 7. Storybook — структура каталога

```
ui/
├── .storybook/
│   ├── main.ts          ← Конфигурация (Vite + React)
│   ├── preview.ts       ← Global decorators, dark mode toggle
│   └── theme.ts         ← Storybook theme (брендинг)
├── packages/shared/ui-kit/
│   ├── Badge/
│   │   ├── Badge.tsx
│   │   ├── Badge.stories.tsx      ← Все варианты Badge
│   │   └── Badge.module.css
│   ├── Panel/
│   │   ├── Panel.tsx
│   │   └── Panel.stories.tsx
│   └── ...
├── apps/dag_builder/src/components/
│   ├── StepNode/
│   │   ├── StepNode.tsx
│   │   └── StepNode.stories.tsx   ← Нода шага в изоляции
│   └── DataEdge/
│       └── DataEdge.stories.tsx
└── apps/knowledge_base/src/components/
    ├── ConceptNode/
    │   └── ConceptNode.stories.tsx
    └── KeywordNode/
        └── KeywordNode.stories.tsx
```

Каждый Story включает:
- **Все варианты** компонента (размеры, состояния, dark/light).
- **Controls** для живого изменения пропсов.
- **Docs** — автодокументация из JSDoc / TypeScript.
