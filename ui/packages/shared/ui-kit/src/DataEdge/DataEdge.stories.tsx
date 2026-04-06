import type { Meta, StoryObj } from "@storybook/react";
import { DataEdge } from "./DataEdge";

const meta: Meta<typeof DataEdge> = {
    title: "DAG Builder/DataEdge",
    component: DataEdge,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
    argTypes: {
        variant: { control: "select", options: ["normal", "mismatch", "animated"] },
    },
};

export default meta;
type Story = StoryObj<typeof DataEdge>;

export const StrType: Story = {
    name: "🧩 str Type Wire (C1)",
    args: { dataType: "str", variant: "normal" },
};

export const DictType: Story = {
    name: "🧩 dict — Structured Data",
    args: { dataType: "dict", variant: "normal" },
};

export const TypeMismatch: Story = {
    name: "🧩 Type Mismatch — ⚠ (C2, F4)",
    args: { dataType: "dict → str", variant: "mismatch" },
};

export const AnimatedFlow: Story = {
    name: "🧩 Animated Particle Flow (C4)",
    args: { dataType: "List[str]", variant: "animated", width: 250 },
};

export const AllVariants: Story = {
    name: "All Variants",
    render: () => (
        <div className="flex flex-col gap-4">
            <DataEdge dataType="str" variant="normal" />
            <DataEdge dataType="dict → str" variant="mismatch" />
            <DataEdge dataType="List[Concept]" variant="animated" width={250} />
        </div>
    ),
};
