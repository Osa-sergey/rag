# DAG Builder — Технические требования (React Flow)

## Стек технологий
- **Библиотека графов**: `@xyflow/react` (React Flow v12)
- **Фреймворк**: React 18+ (Vite)
- **Формы**: `react-hook-form` + `@hookform/resolvers/zod`
- **JSON Schema → UI**: `@rjsf/core` (React JSON Schema Form) — автогенерация форм из Pydantic-схем
- **YAML**: `yaml` (js-yaml) — парсинг/генерация YAML для round-trip
- **Стейт**: Zustand (рекомендация React Flow) + React Flow встроенные хуки
- **Стилизация**: CSS Modules + CSS Variables (поддержка dark mode через React Flow `colorMode`)
- **Код-редактор**: Monaco Editor (для YAML панели)

---

## 1. Архитектура компонентов

### 1.1. Layout (Корневой макет)

```
┌──────────────────────────────────────────────────────────────┐
│  TopBar (pipeline name, save, run, dry-run, git status)      │
├─────────┬──────────────────────────────┬─────────────────────┤
│ Sidebar │        ReactFlow Canvas      │  Inspector Panel    │
│ (Node   │  ┌────┐     ┌────┐          │  (config/callbacks  │
│ Palette)│  │Step│────▶│Step│          │   для выбранной     │
│         │  └────┘     └────┘          │   ноды)             │
│         │       ┌────┐                │                     │
│         │       │Step│                │                     │
│         │       └────┘                │                     │
│         │                              │                     │
│         │  ┌─────────────────────────┐ │                     │
│         │  │ MiniMap    Controls     │ │                     │
│         │  └─────────────────────────┘ │                     │
├─────────┴──────────────────────────────┴─────────────────────┤
│  BottomPanel: YAML Editor (Monaco, split-view, round-trip)   │
└──────────────────────────────────────────────────────────────┘
```

### 1.2. Компоненты React Flow (Canvas)

| Компонент | Реализация React Flow | Описание |
|---|---|---|
| **StepNode** | Custom Node (`nodeTypes`) | Кастомная нода с I/O портами, бейджами, иконкой модуля |
| **DataEdge** | Custom Edge (`edgeTypes`) | Ребро с подписью типа данных (`str`, `dict`...) через `EdgeLabelRenderer` |
| **DependencyEdge** | Built-in `smoothstep` | Простая зависимость `depends_on` без Data Contract |
| **NodePalette** | Custom `<Panel position="top-left">` | Drag-and-drop каталог доступных Step-типов из `StepRegistry` |
| **PipelineControls** | `<Panel position="top-right">` | Кнопки Run, Dry-run, Validate, Save |
| **ValidationOverlay** | `<Panel position="bottom-left">` | Лог ошибок inline-валидации (циклы, типы, missing deps) |

---

## 2. Custom Node: `StepNode`

### 2.1. Структура компонента

```tsx
interface StepNodeData {
  stepId: string;
  module: string;              // "raptor_pipeline.run"
  label: string;               // Человекочитаемое имя
  description: string;         // Из StepDefinition.description
  config: Record<string, any>; // Step-level overrides
  defaults: HydraDefault[];    // Hydra defaults selections
  outputs: Record<string, string>; // { key: type }
  
  // Callbacks
  onSuccess: CallbackConfig[];
  onFailure: CallbackConfig[];
  onRetry: CallbackConfig[];
  
  // Context (COP)
  providesContext: string | null;   // "ParseContext"
  requiresContexts: string[];      // ["RaptorContext"]
  
  // Validation state
  errors: ValidationError[];
  warnings: ValidationWarning[];
  
  // Runtime state (при execution monitoring)
  status?: 'idle' | 'running' | 'success' | 'failed';
  duration?: number;
}
```

### 2.2. Визуальная структура ноды

```
┌─ StepNode ──────────────────────────────────┐
│  ┌──────┐  raptor_pipeline.run        ⟳ 🔔  │
│  │ icon │  "RAPTOR Pipeline"          v     │
│  └──────┘  [devops] [indexing]              │
│─────────────────────────────────────────────│
│  📥 Requires: ParseContext                  │
│  📤 Provides: RaptorContext                 │
│─────────────────────────────────────────────│
│  INPUT HANDLES          OUTPUT HANDLES      │
│  ○ input_dir: str       parsed_dir: str ○   │
│  ○ max_concurrency: int                     │
│─────────────────────────────────────────────│
│  ⟳ retry: 3×30s  🔔 #data-errors           │
└─────────────────────────────────────────────┘
```

### 2.3. Handles (Порты ввода/вывода)

Используется `<Handle>` от React Flow с уникальными `id` для каждого порта:

```tsx
// Входные порты — слева, генерируются из полей config содержащих ${{ }}
<Handle
  type="target"
  position={Position.Left}
  id={`input-${fieldName}`}
  style={{ top: calculatePortPosition(index) }}
/>

// Выходные порты — справа, генерируются из outputs декларации
<Handle
  type="source"
  position={Position.Right}
  id={`output-${outputKey}`}
  style={{ top: calculatePortPosition(index) }}
/>
```

**Динамические Handles**: При изменении `outputs` или привязке `${{ }}` ссылок вызывается `useUpdateNodeInternals()` для пересчета позиций.

---

## 3. Custom Edge: `DataEdge`

### 3.1. Отображение типа на ребре

```tsx
function DataEdge({ id, sourceX, sourceY, targetX, targetY, data }) {
  const [path, labelX, labelY] = getSmoothStepPath({ sourceX, sourceY, targetX, targetY });
  
  return (
    <>
      <BaseEdge id={id} path={path} />
      <EdgeLabelRenderer>
        <div style={{ transform: `translate(${labelX}px, ${labelY}px)` }}
             className="edge-type-badge">
          {data.outputType}  {/* "str", "dict", "DataFrame" */}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
```

### 3.2. Валидация при создании ребра

При `onConnect` проверяется совместимость типов:

```tsx
const onConnect = useCallback((connection) => {
  const sourceNode = getNode(connection.source);
  const targetNode = getNode(connection.target);
  const outputKey = connection.sourceHandle.replace('output-', '');
  const inputField = connection.targetHandle.replace('input-', '');
  
  const outputType = sourceNode.data.outputs[outputKey];
  const expectedType = getFieldType(targetNode.data.module, inputField); // из JSON Schema
  
  if (!isTypeCompatible(outputType, expectedType)) {
    showError(`Тип ${outputType} несовместим с ${expectedType}`);
    return;
  }
  
  // Автоматически:
  // 1. Добавить depends_on
  // 2. Вставить ${{ steps.SOURCE.KEY }} в config целевой ноды
  // 3. Создать edge
}, []);
```

---

## 4. Inspector Panel (Боковая панель)

### 4.1. Табы Inspector

При клике на ноду (`onNodeClick`) открывается Inspector с табами:

| Tab | Содержимое |
|---|---|
| **Config** | Автоформа из JSON Schema (Pydantic → JSON Schema) с source badges (🔵default 🟢step 🟡override 🔷global) |
| **Defaults** | Dropdown-селекторы для Hydra defaults groups |
| **Outputs** | Таблица `output_key: type` с кнопкой "+ Add Output" |
| **Callbacks** | Три раздела (success/failure/retry) с Palette Picker + автоформы параметров |
| **Context** | Readonly: Provides/Requires context badges + поля dataclass |

### 4.2. Config Tab — автогенерация формы

**Источник**: API endpoint `/api/steps/{module}/schema` возвращает JSON Schema, сгенерированный из Pydantic `schema_class.model_json_schema()`.

```tsx
// Используем @rjsf/core для рендера формы из JSON Schema
<Form
  schema={stepJsonSchema}
  formData={node.data.config}
  uiSchema={generateUiSchema(stepJsonSchema)} // source badges, groups
  onChange={({ formData }) => updateNodeData(nodeId, { config: formData })}
  liveValidate={true}
/>
```

**Source Badges**: Каждое поле маркируется цветом:
- Значение получено через `inspect_pipeline_config` (annotate sources) → передается как `uiSchema` с доп. виджетом.

### 4.3. Callbacks Tab — Palette Picker

```tsx
// API: GET /api/callbacks → ["log_result", "notify", "send_alert", "retry", ...]
<CallbackSection title="on_failure" callbacks={node.data.onFailure}>
  <AddCallbackButton>
    <Dropdown items={availableCallbacks}>
      {/* При выборе "retry" → показать форму: */}
      <ParamForm params={{ max_attempts: { type: 'integer', default: 3 },
                           delay: { type: 'integer', default: 10 } }} />
    </Dropdown>
  </AddCallbackButton>
</CallbackSection>
```

---

## 5. YAML Panel (Бидирекциональная синхронизация)

### 5.1. Архитектура Round-trip

```
┌─────────────┐       serialize()        ┌──────────────┐
│ React Flow  │ ──────────────────────▶ │ Monaco YAML  │
│   State     │                          │   Editor     │
│ (nodes,     │ ◀────────────────────── │              │
│  edges)     │       deserialize()      │              │
└─────────────┘                          └──────────────┘
```

- **Graph → YAML** (`serialize`): Срабатывает при каждом изменении в графе (debounced 300ms). Генерирует `PipelineYaml`-совместимый YAML.
- **YAML → Graph** (`deserialize`): Срабатывает при ручном редактировании в Monaco (debounced 500ms). Парсит YAML, валидирует через `PipelineYaml` schema, перестраивает nodes/edges.
- **Конфликты**: Если обе стороны изменились одновременно, побеждает последнее write.

### 5.2. Monaco Editor

```tsx
<MonacoEditor
  language="yaml"
  value={yamlContent}
  onChange={handleYamlChange}
  options={{
    minimap: { enabled: false },
    lineNumbers: 'on',
    // Inline-подсветка ошибок валидации
    markers: validationErrors.map(e => ({
      startLineNumber: e.line,
      message: e.message,
      severity: MarkerSeverity.Error,
    })),
  }}
/>
```

---

## 6. Inline Validation Engine

### 6.1. Правила валидации (запускаются на каждое изменение графа)

| Правило | Проверка | Источник в dagster-dsl |
|---|---|---|
| **Cycle detection** | Алгоритм Кана, нет циклов в `depends_on` | `PipelineYaml.validate_no_cycles` |
| **Missing dependency** | Все `depends_on` ссылаются на существующие step_id | `PipelineYaml.validate_depends_on_references` |
| **Unknown module** | `module` зарегистрирован в `StepRegistry` | `yaml_loader` step 2 |
| **Output ref exists** | `${{ steps.X.Y }}` → шаг X существует + Y в его outputs | `_validate_and_mock_output_refs` |
| **Output ref in deps** | Шаг X должен быть в `depends_on` текущего шага | `_validate_and_mock_output_refs` |
| **Type compatibility** | Тип output совместим с target field Pydantic-схемой | `_check_type_compatibility` |
| **Config schema** | Step config проходит валидацию Pydantic/Hydra | `validate_step_config` |
| **Context prerequisites** | `requires_contexts` шага покрыты upstream `context_class` | `execute_step` runtime check |

### 6.2. UI отображение ошибок

- **На ноде**: Красная рамка + иконка ⚠️ с tooltip.
- **На ребре**: Красный пунктир + badge "Type mismatch".
- **ValidationOverlay Panel**: Список всех ошибок с кликабельными ссылками (клик → фокус на проблемную ноду).

---

## 7. Node Palette (Каталог шагов)

### 7.1. Источник данных

API endpoint: `GET /api/steps` → возвращает список из `StepRegistry.list_steps()` с метаданными:

```json
[
  {
    "name": "raptor_pipeline.run",
    "description": "RAPTOR Pipeline — индексация документов",
    "module_name": "raptor_pipeline",
    "tags": { "module": "raptor_pipeline", "type": "indexing" },
    "has_schema": true,
    "context_class": "RaptorContext",
    "requires_contexts": ["ParseContext"]
  }
]
```

### 7.2. UX

- Группировка по `tags.module` (Accordion).
- Поиск по имени/описанию.
- Drag-and-drop на Canvas → создает ноду с дефолтными значениями.

---

## 8. API Layer (Backend)

Минимальный набор REST endpoints (FastAPI):

| Method | Endpoint | Описание |
|---|---|---|
| GET | `/api/steps` | Список зарегистрированных шагов |
| GET | `/api/steps/{module}/schema` | JSON Schema конфигурации шага |
| GET | `/api/steps/{module}/defaults` | Доступные Hydra defaults groups |
| GET | `/api/callbacks` | Список зарегистрированных callbacks + их параметры |
| POST | `/api/pipeline/validate` | Валидация YAML pipeline (возвращает ошибки) |
| POST | `/api/pipeline/dry-run` | Dry-run: порядок выполнения + resolved конфиги |
| POST | `/api/pipeline/run` | Запуск pipeline |
| GET | `/api/pipeline/run/{id}/status` | Статус выполнения (SSE или polling) |
| POST | `/api/pipeline/serialize` | Graph state → YAML |
| POST | `/api/pipeline/deserialize` | YAML → Graph state (nodes/edges) |
