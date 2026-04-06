import React from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { Slider } from "./Slider";

const meta: Meta<typeof Slider> = {
    title: "UI Kit/Slider",
    component: Slider,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
    argTypes: {
        disabled: { control: "boolean" },
        showValue: { control: "boolean" },
    },
};

export default meta;
type Story = StoryObj<typeof Slider>;

export const Default: Story = {
    args: {
        label: "Chunk Size",
        min: 64,
        max: 2048,
        step: 64,
        value: 512,
        showValue: true,
    },
};

export const SimilarityThreshold: Story = {
    name: "🧩 Similarity Threshold (H4)",
    args: {
        label: "Similarity Threshold",
        min: 0,
        max: 1,
        step: 0.05,
        value: 0.7,
        ticks: 10,
        formatValue: (v: number) => v.toFixed(2),
        color: "var(--color-concept)",
    },
};

export const WithTicks: Story = {
    name: "With Tick Marks",
    args: {
        label: "Max Retries",
        min: 0,
        max: 5,
        step: 1,
        value: 3,
        ticks: 5,
    },
};

export const Temperature: Story = {
    name: "🧩 LLM Temperature",
    args: {
        label: "Temperature",
        min: 0,
        max: 2,
        step: 0.1,
        value: 0.7,
        ticks: 4,
        formatValue: (v: number) => v.toFixed(1),
        color: "var(--color-warning)",
    },
};

export const Disabled: Story = {
    args: {
        label: "Overlap (locked)",
        value: 64,
        max: 512,
        disabled: true,
    },
};

export const FilterPanel: Story = {
    name: "🧩 KB Filter Panel",
    render: () => (
        <div className="flex flex-col gap-4 p-4 rounded-lg" style={{ background: "var(--bg-node)", border: "var(--border-node)", maxWidth: 320 }}>
            <h4 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                Filter Options
            </h4>
            <Slider
                label="Min Similarity"
                min={0} max={1} step={0.05} value={0.5}
                ticks={4} formatValue={(v) => v.toFixed(2)}
            />
            <Slider
                label="Min Confidence"
                min={0} max={1} step={0.1} value={0.7}
                ticks={5} formatValue={(v) => `${(v * 100).toFixed(0)}%`}
                color="var(--color-success)"
            />
            <Slider
                label="Max Depth"
                min={1} max={5} step={1} value={3}
                ticks={4}
                color="var(--color-warning)"
            />
        </div>
    ),
};
