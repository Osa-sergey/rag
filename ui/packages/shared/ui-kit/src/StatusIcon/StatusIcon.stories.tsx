import type { Meta, StoryObj } from "@storybook/react";
import { StatusIcon } from "./StatusIcon";

const meta: Meta<typeof StatusIcon> = {
    title: "UI Kit/StatusIcon",
    component: StatusIcon,
    tags: ["autodocs"],
    argTypes: {
        status: {
            control: "select",
            options: ["success", "error", "warning", "info", "idle", "running", "stale"],
        },
        size: { control: { type: "range", min: 6, max: 24, step: 2 } },
        pulse: { control: "boolean" },
    },
};

export default meta;
type Story = StoryObj<typeof StatusIcon>;

export const Success: Story = {
    args: { status: "success", label: "Active" },
};

export const Error: Story = {
    args: { status: "error", label: "Failed" },
};

export const Running: Story = {
    args: { status: "running", label: "Running...", pulse: true },
};

export const Stale: Story = {
    args: { status: "stale", label: "Outdated" },
};

export const AllStatuses: Story = {
    name: "All Statuses",
    render: () => (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <StatusIcon status="success" label="success" />
            <StatusIcon status="error" label="error" />
            <StatusIcon status="warning" label="warning" />
            <StatusIcon status="info" label="info" />
            <StatusIcon status="idle" label="idle" />
            <StatusIcon status="running" label="running" pulse />
            <StatusIcon status="stale" label="stale" />
        </div>
    ),
};

export const SizesComparison: Story = {
    name: "Sizes",
    render: () => (
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <StatusIcon status="success" size={6} label="6px" />
            <StatusIcon status="info" size={10} label="10px" />
            <StatusIcon status="error" size={16} label="16px" />
            <StatusIcon status="warning" size={24} label="24px" />
        </div>
    ),
};
