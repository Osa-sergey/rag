import type { Meta, StoryObj } from "@storybook/react";
import { EmptyState } from "./EmptyState";
import { Database } from "lucide-react";

const meta: Meta<typeof EmptyState> = {
    title: "UI Kit/EmptyState",
    component: EmptyState,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
    argTypes: {
        type: { control: "select", options: ["no-data", "no-results", "error", "first-time"] },
    },
};

export default meta;
type Story = StoryObj<typeof EmptyState>;

export const NoData: Story = {
    args: { type: "no-data" },
};

export const NoResults: Story = {
    args: { type: "no-results" },
};

export const Error: Story = {
    args: { type: "error", action: { label: "Retry", onClick: () => console.log("retry") } },
};

export const FirstTime: Story = {
    name: "First Time Setup",
    args: {
        type: "first-time",
        title: "Build your first pipeline",
        description: "Drag steps from the palette to the canvas to create a DAG",
        action: { label: "Open Tutorial", onClick: () => console.log("tutorial") },
    },
};

export const CustomIcon: Story = {
    name: "Custom (No Vectors)",
    args: {
        title: "No vectors indexed",
        description: "Run the pipeline to generate embeddings and index them in Qdrant",
        icon: <Database size={40} />,
        action: { label: "Run Pipeline", onClick: () => console.log("run") },
    },
};

export const NoStaleConcepts: Story = {
    name: "🧩 KB: No Stale Concepts",
    args: {
        type: "no-data",
        title: "All concepts are up to date",
        description: "The Inbox is empty — no stale concepts need review right now.",
    },
};
