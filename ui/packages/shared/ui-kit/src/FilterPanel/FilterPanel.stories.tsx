import type { Meta, StoryObj } from "@storybook/react";
import { FilterPanel } from "./FilterPanel";

const meta: Meta<typeof FilterPanel> = {
    title: "React Flow/FilterPanel",
    component: FilterPanel,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj<typeof FilterPanel>;

export const AllLayers: Story = {
    name: "🧩 All Layers Checked (H3)",
    args: {
        groups: [
            {
                label: "Entity Types",
                options: [
                    { id: "articles", label: "Articles", color: "var(--color-article)", checked: true },
                    { id: "keywords", label: "Keywords", color: "var(--color-keyword)", checked: true },
                    { id: "concepts", label: "Concepts", color: "var(--color-concept)", checked: true },
                ],
            },
        ],
    },
};

export const WithSlider: Story = {
    name: "🧩 Similarity Threshold (H4)",
    args: {
        groups: [
            {
                label: "Entity Types",
                options: [
                    { id: "concepts", label: "Concepts", color: "var(--color-concept)", checked: true },
                ],
            },
        ],
        sliders: [
            {
                id: "similarity",
                label: "Similarity Threshold",
                min: 0,
                max: 1,
                value: 0.7,
                step: 0.05,
                format: (v: number) => v.toFixed(2),
            },
        ],
        toggles: [
            { id: "showEdges", label: "Show edge labels", checked: true },
            { id: "animate", label: "Animate flow", checked: false },
        ],
    },
};

export const StepFilters: Story = {
    name: "🧩 DAG Step Filters (B8)",
    args: {
        groups: [
            {
                label: "Step Status",
                options: [
                    { id: "idle", label: "Idle", color: "var(--text-muted)", checked: true },
                    { id: "running", label: "Running", color: "var(--color-info)", checked: true },
                    { id: "success", label: "Success", color: "var(--color-success)" },
                    { id: "failed", label: "Failed", color: "var(--color-error)" },
                ],
            },
            {
                label: "Categories",
                options: [
                    { id: "etl", label: "ETL", checked: true },
                    { id: "ml", label: "ML" },
                    { id: "indexing", label: "Indexing", checked: true },
                ],
            },
        ],
    },
};
