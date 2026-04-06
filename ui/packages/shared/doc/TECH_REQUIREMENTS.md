# Shared Packages — Общие модули для микрофронтендов

## Архитектура

```
ui/
├── apps/
│   ├── dag_builder/        ← Микрофронтенд 1
│   └── knowledge_base/     ← Микрофронтенд 2
├── packages/
│   └── shared/             ← Общие модули (npm workspace / turborepo)
│       ├── ui-kit/         ← Дизайн-система (кнопки, формы, панели)
│       ├── react-flow/     ← Обертки над @xyflow/react
│       ├── api-client/     ← Типизированный API-клиент (fetch + Zod)
│       ├── store/          ← Zustand store factories
│       └── types/          ← Общие TypeScript типы
```

---

## 1. `packages/shared/ui-kit`

Общая дизайн-система (CSS Variables + компоненты). **Разработка и документирование всех компонентов ведется в изолированной среде [Storybook](https://storybook.js.org/).**

| Компонент | Описание | Используется в |
|---|---|---|
| `<Panel>` | Обертка для боковых/нижних панелей (resizable) с анимацией slide-in | Оба приложения |
| `<Badge>` | Цветные бейджи (статус, тип, version) | Оба |
| `<Form>` | Обертка JSON Schema Form (@rjsf/core) | DAG Builder (config), KB (create concept) |
| `<DiffViewer>` | react-diff-viewer wrapper | KB (snapshot vs current), DAG (YAML versions) |
| `<SearchBar>` | Поле поиска с фильтрами | Оба |
| `<TabPanel>` | Tab-переключатель с контентом | Оба (inspector tabs) |
| `<Dropdown>` | Выпадающий список с поиском | DAG (callback picker), KB (article selector) |
| `<Timeline>` | Вертикальная timeline для версий | KB (version history), DAG (execution log) |
| `<StatusIcon>` | 🟢🔴🟡⚠️ иконки статусов | Оба |

**Стилизация и UX**: 
- CSS Variables для dark/light mode, единая цветовая палитра.
- **Framer Motion** для плавных анимаций (появление модалок, аккордеонов, нод).
- Референс для UI-кита: shadcn/ui.
- Строгий компонентный подход тестируемый через **Storybook**.

---

## 2. `packages/shared/react-flow`

Общие обертки и утилиты над `@xyflow/react`:

| Модуль | Описание |
|---|---|
| `FlowCanvas` | Преднастроенный `<ReactFlow>` с Controls, MiniMap, Background |
| `useGraphLayout` | Автолейаут через `dagre` / `elkjs` |
| `TypedEdge` | Базовый custom edge с `EdgeLabelRenderer` для подписей |
| `FilterPanel` | Панель фильтрации слоев графа (checkboxes + sliders) |
| `NodeTooltip` | Hover-tooltip для нод (React Flow Portal) |

---

## 3. `packages/shared/api-client`

Типизированный HTTP-клиент для общения с FastAPI бэкендом:

```ts
// Автогенерация из OpenAPI schema
export const api = {
  // DAG Builder
  steps: { list, getSchema, getDefaults },
  callbacks: { list },
  pipeline: { validate, dryRun, run, getStatus, serialize, deserialize },
  
  // Knowledge Base
  kb: {
    articles: { list, get, getChunks, getTree, getKeywords },
    concepts: { list, get, getHistory, getChunks, expand, finalize, create, getStale },
    graph: { get, getNeighbors },
  },
};
```

---

## 4. `packages/shared/types`

Общие TypeScript-типы зеркалирующие Pydantic-модели бэкенда:

```ts
// Shared
export interface ValidationError { nodeId: string; field: string; message: string; severity: 'error' | 'warning' }

// DAG Builder
export interface StepDefinition { name: string; module_name: string; tags: Record<string, string>; ... }
export interface PipelineYaml { name: string; config: Record<string, any>; steps: Record<string, StepYaml> }

// Knowledge Base
export interface Concept { id: string; name: string; version: number; is_active: boolean; source_articles: string[]; ... }
export interface Keyword { id: string; name: string; type: string; score: number; chunk_ids: string[] }
```

---

## 5. Микрофронтенд-интеграция

**Подход**: Module Federation (Webpack 5) или просто Monorepo (Turborepo/pnpm workspaces).

```json
// package.json (root)
{
  "workspaces": [
    "apps/*",
    "packages/*"
  ]
}
```

Каждое приложение собирается и деплоится **независимо**, но импортирует общие модули из `packages/shared/*`:

```ts
// apps/dag_builder/src/App.tsx
import { FlowCanvas, FilterPanel } from '@habr-ui/react-flow';
import { Panel, Badge, Form } from '@habr-ui/ui-kit';
import { api } from '@habr-ui/api-client';
```
