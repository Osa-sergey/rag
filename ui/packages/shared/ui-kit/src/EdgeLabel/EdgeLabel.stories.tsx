import type { Meta, StoryObj } from "@storybook/react";
import { EdgeLabel } from "./EdgeLabel";

const meta: Meta<typeof EdgeLabel> = {
    title: "React Flow/EdgeLabel",
    component: EdgeLabel,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
    argTypes: {
        variant: { control: "select", options: ["type", "score", "dependency"] },
    },
};

export default meta;
type Story = StoryObj<typeof EdgeLabel>;

export const TypeLabel: Story = {
    name: "🧩 Type Label — str (C1)",
    args: { label: "str", variant: "type" },
};

export const ScoreLabel: Story = {
    name: "🧩 Score Label — 0.87 (H2)",
    args: { label: "0.87", variant: "score" },
};

export const DependencyLabel: Story = {
    name: "Dependency — depends_on",
    args: { label: "depends_on", variant: "dependency" },
};

export const TypeError: Story = {
    name: "🧩 Type Mismatch — ⚠ (C2, F4)",
    args: { label: "dict → str", error: true },
};

export const HoverReveal: Story = {
    name: "Hover Reveal — Faded",
    args: { label: "List[str]", variant: "type", hoverReveal: true },
};

export const AllVariants: Story = {
    name: "All Variants",
    render: () => (
        <div className="flex items-center gap-3">
            <EdgeLabel label="str" variant="type" />
            <EdgeLabel label="0.92" variant="score" />
            <EdgeLabel label="depends_on" variant="dependency" />
            <EdgeLabel label="dict → str" error />
            <EdgeLabel label="List[str]" variant="type" hoverReveal />
        </div>
    ),
};
