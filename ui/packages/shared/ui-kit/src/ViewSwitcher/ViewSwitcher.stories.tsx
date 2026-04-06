import type { Meta, StoryObj } from "@storybook/react";
import { ViewSwitcher } from "./ViewSwitcher";
import { Network, List, TreePine, Code, LayoutGrid } from "lucide-react";

const meta: Meta<typeof ViewSwitcher> = {
    title: "UI Kit/ViewSwitcher",
    component: ViewSwitcher,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
    argTypes: {
        size: { control: "select", options: ["sm", "md"] },
    },
};

export default meta;
type Story = StoryObj<typeof ViewSwitcher>;

export const KBViewModes: Story = {
    name: "🧩 KB View Modes (M3)",
    args: {
        options: [
            { id: "graph", label: "Graph", icon: <Network size={12} /> },
            { id: "tree", label: "Tree", icon: <TreePine size={12} /> },
            { id: "table", label: "Table", icon: <List size={12} /> },
        ],
        value: "graph",
    },
};

export const DAGViews: Story = {
    name: "🧩 DAG Canvas / YAML",
    args: {
        options: [
            { id: "canvas", label: "Canvas", icon: <LayoutGrid size={12} /> },
            { id: "yaml", label: "YAML", icon: <Code size={12} /> },
        ],
        value: "canvas",
    },
};

export const SmallSize: Story = {
    name: "Small Size",
    args: {
        size: "sm",
        options: [
            { id: "all", label: "All" },
            { id: "active", label: "Active" },
            { id: "stale", label: "Stale" },
        ],
        value: "all",
    },
};

export const TextOnly: Story = {
    name: "Text Only (No Icons)",
    args: {
        options: [
            { id: "day", label: "Day" },
            { id: "week", label: "Week" },
            { id: "month", label: "Month" },
        ],
        value: "week",
    },
};
