import type { Meta, StoryObj } from "@storybook/react";
import { ProgressBar } from "./ProgressBar";

const meta: Meta<typeof ProgressBar> = {
    title: "UI Kit/ProgressBar",
    component: ProgressBar,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
    argTypes: {
        variant: { control: "select", options: ["info", "success", "warning", "error"] },
        value: { control: { type: "range", min: 0, max: 100 } },
        height: { control: { type: "range", min: 2, max: 12 } },
    },
};

export default meta;
type Story = StoryObj<typeof ProgressBar>;

export const Determinate: Story = {
    args: { value: 65, label: "Indexing vectors", showPercent: true },
};

export const Complete: Story = {
    args: { value: 100, label: "Build complete", showPercent: true, variant: "success" },
};

export const Indeterminate: Story = {
    name: "Indeterminate",
    args: { label: "Building RAPTOR tree..." },
};

export const WithVariants: Story = {
    name: "🧩 All Variants",
    render: () => (
        <div className="flex flex-col gap-4" style={{ maxWidth: 400 }}>
            <ProgressBar value={85} label="Processing articles" showPercent variant="info" />
            <ProgressBar value={100} label="Embeddings ready" showPercent variant="success" />
            <ProgressBar value={40} label="Low confidence" showPercent variant="warning" />
            <ProgressBar value={15} label="Failures" showPercent variant="error" />
            <ProgressBar label="Loading pipeline config..." />
        </div>
    ),
};

export const Thick: Story = {
    name: "Thick Progress Bar",
    args: { value: 72, label: "Step 3 of 5", showPercent: true, height: 8 },
};
