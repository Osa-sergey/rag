import type { Meta, StoryObj } from "@storybook/react";
import { AlertBanner } from "./AlertBanner";

const meta: Meta<typeof AlertBanner> = {
    title: "UI Kit/AlertBanner",
    component: AlertBanner,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
    argTypes: {
        variant: { control: "select", options: ["info", "warning", "error", "success"] },
        dismissible: { control: "boolean" },
    },
};

export default meta;
type Story = StoryObj<typeof AlertBanner>;

export const InfoBanner: Story = {
    name: "Info — Config Reloaded",
    args: {
        message: "Pipeline configuration reloaded from YAML. 2 steps updated.",
        variant: "info",
    },
};

export const WarningBanner: Story = {
    name: "🧩 Warning — Unlinked Outputs (F3)",
    args: {
        message: "3 step outputs are not connected to any downstream input.",
        variant: "warning",
        action: { label: "Show Details", onClick: () => console.log("show") },
    },
};

export const ErrorBanner: Story = {
    name: "🧩 Error — Connection Lost",
    args: {
        message: "Neo4j connection lost. Graph queries will fail until reconnected.",
        variant: "error",
        action: { label: "Reconnect", onClick: () => console.log("reconnect") },
    },
};

export const SuccessBanner: Story = {
    name: "Success — Build Complete",
    args: {
        message: "RAPTOR tree rebuilt successfully — 4 levels, 127 nodes.",
        variant: "success",
        dismissible: true,
    },
};

export const AllVariants: Story = {
    name: "🧩 All Variants Stacked",
    render: () => (
        <div className="flex flex-col" style={{ maxWidth: 600 }}>
            <AlertBanner variant="error" message="Build failed: 2 validation errors" action={{ label: "View Errors", onClick: () => { } }} />
            <AlertBanner variant="warning" message="3 concepts are stale — source articles have been updated" action={{ label: "Review", onClick: () => { } }} />
            <AlertBanner variant="info" message="Auto-save enabled — changes persist immediately" dismissible />
            <AlertBanner variant="success" message="All 5 steps passed validation ✓" />
        </div>
    ),
};
