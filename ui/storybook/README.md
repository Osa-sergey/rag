# Storybook — Каталог компонентов UI-платформы

Изолированная среда для разработки, документирования и тестирования UI-компонентов для обоих микрофронтендов: **DAG Builder** и **Knowledge Base**.

## Запуск

```bash
# 1. Установить зависимости (из корня ui/)
cd d:\repo\airflow\habr\ui
pnpm install

# 2. Запустить Storybook (dev-сервер на порту 6006)
pnpm storybook

# 3. Открыть в браузере
# → http://localhost:6006
```

## Сборка статической версии

```bash
pnpm storybook:build
# → Результат в ui/storybook-static/
```

---

## Структура

```
ui/
├── .storybook/
│   ├── main.ts          ← Конфигурация (Vite builder, addons, globs)
│   └── preview.ts       ← Глобальные декораторы (dark/light mode toggle)
│
├── packages/shared/ui-kit/
│   ├── src/
│   │   ├── styles/
│   │   │   ├── tokens.css     ← CSS Variables (дизайн-токены)
│   │   │   └── globals.css    ← Tailwind + шрифты
│   │   ├── motion.ts          ← Framer Motion пресеты анимаций
│   │   ├── Badge/
│   │   │   ├── Badge.tsx            ← Компонент
│   │   │   ├── Badge.stories.tsx    ← Stories для Storybook
│   │   │   └── index.ts            ← Barrel export
│   │   ├── StatusIcon/ ...
│   │   ├── Tooltip/ ...
│   │   ├── Skeleton/ ...
│   │   ├── Panel/ ...
│   │   ├── SearchBar/ ...
│   │   └── index.ts           ← Общий barrel export
│   └── package.json
│
└── package.json               ← Root (pnpm workspaces)
```

---

## Как добавить новый компонент

### 1. Создать папку

```bash
mkdir packages/shared/ui-kit/src/MyComponent
```

### 2. Создать компонент

```tsx
// packages/shared/ui-kit/src/MyComponent/MyComponent.tsx
import React from "react";

export interface MyComponentProps {
  label: string;
  variant?: "primary" | "secondary";
}

export function MyComponent({ label, variant = "primary" }: MyComponentProps) {
  return <div className={`my-component ${variant}`}>{label}</div>;
}
```

### 3. Написать Stories

```tsx
// packages/shared/ui-kit/src/MyComponent/MyComponent.stories.tsx
import type { Meta, StoryObj } from "@storybook/react";
import { MyComponent } from "./MyComponent";

const meta: Meta<typeof MyComponent> = {
  title: "UI Kit/MyComponent",    // Дерево навигации в Storybook
  component: MyComponent,
  tags: ["autodocs"],              // Автоматическая документация
  argTypes: {
    variant: { control: "select", options: ["primary", "secondary"] },
  },
};

export default meta;
type Story = StoryObj<typeof MyComponent>;

export const Primary: Story = {
  args: { label: "Hello", variant: "primary" },
};

export const Secondary: Story = {
  args: { label: "World", variant: "secondary" },
};
```

### 4. Экспортировать

```ts
// packages/shared/ui-kit/src/MyComponent/index.ts
export { MyComponent } from "./MyComponent";
export type { MyComponentProps } from "./MyComponent";
```

```ts
// Добавить в packages/shared/ui-kit/src/index.ts
export { MyComponent } from "./MyComponent";
```

### 5. Открыть в Storybook

Перезапустите или дождитесь HMR — компонент появится в сайдбаре.

---

## Возможности Storybook

| Возможность | Описание |
|---|---|
| **Controls** | Интерактивные пропсы — меняйте параметры компонента в реальном времени |
| **Dark Mode Toggle** | Переключатель тем в toolbar (data-theme="dark") |
| **Autodocs** | Авто-документирование типов из TypeScript |
| **Viewport** | Тестирование под разные размеры экрана |
| **Measure & Outline** | Визуализация отступов и контуров элементов |
| **Actions** | Логирование вызовов callback-ов (onClick, onChange) |
| **Interactions** | Авто-тестирование поведения компонентов |

## Компоненты (текущие)

| Компонент | Stories | Описание |
|---|---|---|
| `Badge` | 11 | Статусы, версии, теги, иконки, размеры |
| `StatusIcon` | 6 | 7 статусов, pulse-анимация, размеры |
| `Tooltip` | 6 | 4 позиции, rich content, задержка |
| `Skeleton` | 6 | Text, circle, card, row, node placeholder |
| `Panel` | 3 | Left/Right/Bottom, resize, toggle |
| `SearchBar` | 5 | Expand/collapse, clear, focus animation |

## Использование компонентов в приложении

```tsx
// В apps/dag_builder или apps/knowledge_base
import { Badge, Panel, SearchBar, StatusIcon } from "@ui/ui-kit";

function MyPage() {
  return (
    <Panel side="right" open={true} title="Inspector">
      <Badge variant="success">active</Badge>
      <StatusIcon status="running" pulse label="Processing..." />
      <SearchBar placeholder="Search steps..." expandOnFocus />
    </Panel>
  );
}
```
