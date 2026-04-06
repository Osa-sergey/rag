import type { Meta, StoryObj } from "@storybook/react";
import { ValidationOverlay } from "./ValidationOverlay";

const meta: Meta<typeof ValidationOverlay> = {
    title: "DAG Builder/ValidationOverlay",
    component: ValidationOverlay,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
};

export default meta;
type Story = StoryObj<typeof ValidationOverlay>;

export const NoErrors: Story = {
    name: "🧩 All Checks Passed — Green",
    args: { errors: [] },
};

export const ThreeErrors: Story = {
    name: "🧩 3 Errors — Clickable List (F9)",
    args: {
        errors: [
            { id: "1", severity: "error", message: "max_length must be ≥ 256", nodeId: "n1", nodeName: "parse_articles", field: "config.max_length" },
            { id: "2", severity: "error", message: "Missing required output: chunks", nodeId: "n1", nodeName: "parse_articles" },
            { id: "3", severity: "warning", message: "Unused output: metadata", nodeId: "n2", nodeName: "extract_keywords" },
        ],
    },
};

export const WarningsOnly: Story = {
    name: "Warnings Only",
    args: {
        errors: [
            { id: "1", severity: "warning", message: "Step has no callbacks configured", nodeName: "build_tree" },
            { id: "2", severity: "warning", message: "Default Pydantic values used for all fields", nodeName: "index_vectors" },
        ],
    },
};
