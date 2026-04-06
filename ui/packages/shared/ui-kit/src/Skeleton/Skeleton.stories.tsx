import type { Meta, StoryObj } from "@storybook/react";
import { Skeleton } from "./Skeleton";

const meta: Meta<typeof Skeleton> = {
    title: "UI Kit/Skeleton",
    component: Skeleton,
    tags: ["autodocs"],
    argTypes: {
        variant: {
            control: "select",
            options: ["text", "circle", "card", "row"],
        },
        count: { control: { type: "range", min: 1, max: 8, step: 1 } },
    },
    parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj<typeof Skeleton>;

export const TextLine: Story = {
    args: { variant: "text", width: 240 },
};

export const MultipleLines: Story = {
    name: "Text Block (3 lines)",
    args: { variant: "text", count: 3, width: 300 },
};

export const Circle: Story = {
    args: { variant: "circle", width: 48, height: 48 },
};

export const Card: Story = {
    args: { variant: "card", width: 320, height: 140 },
};

export const TableRows: Story = {
    name: "Table Rows",
    args: { variant: "row", count: 4, width: 400 },
};

export const NodePlaceholder: Story = {
    name: "Node Card Placeholder",
    render: () => (
        <div
            style={{
                width: 280,
                padding: 16,
                borderRadius: "var(--radius-node)",
                border: "var(--border-node)",
                display: "flex",
                flexDirection: "column",
                gap: 12,
            }}
        >
            <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                <Skeleton variant="circle" width={32} height={32} />
                <Skeleton variant="text" width={160} height={16} />
            </div>
            <Skeleton variant="text" count={2} width="100%" />
            <div style={{ display: "flex", gap: 8 }}>
                <Skeleton variant="text" width={60} height={20} />
                <Skeleton variant="text" width={60} height={20} />
            </div>
        </div>
    ),
};
