import type { Meta, StoryObj } from "@storybook/react";
import { PipelineToolbar } from "./PipelineToolbar";

const meta: Meta<typeof PipelineToolbar> = {
    title: "DAG Builder/PipelineToolbar",
    component: PipelineToolbar,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
    argTypes: {
        status: { control: "select", options: ["idle", "running", "completed", "failed"] },
    },
};

export default meta;
type Story = StoryObj<typeof PipelineToolbar>;

export const Idle: Story = {
    name: "🧩 Idle — Ready to Run (G3)",
    args: {
        name: "raptor_indexing",
        status: "idle",
        stepCount: 5,
        edgeCount: 4,
        dirty: false,
    },
};

export const Running: Story = {
    name: "🧩 Running (G4)",
    args: {
        name: "raptor_indexing",
        status: "running",
        stepCount: 5,
        edgeCount: 4,
    },
};

export const Completed: Story = {
    name: "🧩 Completed (G5)",
    args: {
        name: "raptor_indexing",
        status: "completed",
        stepCount: 5,
        edgeCount: 4,
    },
};

export const UnsavedChanges: Story = {
    name: "🧩 Unsaved Changes — Dirty",
    args: {
        name: "raptor_indexing [modified]",
        status: "idle",
        stepCount: 6,
        edgeCount: 5,
        dirty: true,
    },
};
