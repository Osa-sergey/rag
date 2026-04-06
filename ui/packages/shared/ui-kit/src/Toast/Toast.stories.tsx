import type { Meta, StoryObj } from "@storybook/react";
import { Toast } from "./Toast";

const meta: Meta<typeof Toast> = {
    title: "UI Kit/Toast",
    component: Toast,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
    argTypes: {
        variant: { control: "select", options: ["success", "error", "warning", "info"] },
        duration: { control: "number" },
    },
};

export default meta;
type Story = StoryObj<typeof Toast>;

export const Success: Story = {
    args: {
        message: "Pipeline validated — 5 steps, 0 errors",
        variant: "success",
        duration: 0, // no auto-dismiss in stories
    },
};

export const Error: Story = {
    args: {
        message: "Step 'build_concepts' failed: ConnectionError to Neo4j",
        variant: "error",
        duration: 0,
    },
};

export const Warning: Story = {
    args: {
        message: "3 concepts are stale and need review",
        variant: "warning",
        duration: 0,
    },
};

export const Info: Story = {
    args: {
        message: "RAPTOR tree rebuilt with 4 levels from 12 articles",
        variant: "info",
        duration: 0,
    },
};

export const WithAction: Story = {
    name: "With Action Button",
    args: {
        message: "Pipeline config saved",
        variant: "success",
        duration: 0,
        action: { label: "Undo", onClick: () => console.log("undo") },
    },
};

export const AutoDismiss: Story = {
    name: "Auto Dismiss (5s)",
    args: {
        message: "Vector index updated — 1,536 embeddings synced",
        variant: "info",
        duration: 5000,
    },
};

export const AllVariants: Story = {
    name: "🧩 All Variants",
    render: () => (
        <div className="flex flex-col gap-3">
            <Toast message="Pipeline executed successfully" variant="success" duration={0} />
            <Toast message="Step 'parse_articles' failed with exit code 1" variant="error" duration={0} />
            <Toast message="Config override conflicts detected" variant="warning" duration={0} />
            <Toast message="Building RAPTOR tree... this may take a moment" variant="info" duration={0} />
        </div>
    ),
};
