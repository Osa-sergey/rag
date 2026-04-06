import type { Meta, StoryObj } from "@storybook/react";
import { FilterChips } from "./FilterChips";
import { FileText, Brain, Tag, Layers, Cog } from "lucide-react";

const meta: Meta<typeof FilterChips> = {
    title: "UI Kit/FilterChips",
    component: FilterChips,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
    argTypes: {
        multiple: { control: "boolean" },
        size: { control: "select", options: ["sm", "md"] },
    },
};

export default meta;
type Story = StoryObj<typeof FilterChips>;

export const EntityTypes: Story = {
    name: "Entity Types (KB filter)",
    args: {
        chips: [
            { id: "article", label: "Articles", icon: <FileText size={12} />, color: "var(--color-article)" },
            { id: "keyword", label: "Keywords", icon: <Tag size={12} />, color: "var(--color-keyword)" },
            { id: "concept", label: "Concepts", icon: <Brain size={12} />, color: "var(--color-concept)" },
        ],
        selected: ["article"],
    },
};

export const StepStatuses: Story = {
    name: "Step Status (DAG filter)",
    args: {
        chips: [
            { id: "idle", label: "Idle" },
            { id: "success", label: "Success", color: "var(--color-success)" },
            { id: "failed", label: "Failed", color: "var(--color-error)" },
            { id: "running", label: "Running", color: "var(--color-warning)" },
        ],
        selected: ["success", "failed"],
    },
};

export const SingleSelect: Story = {
    name: "Single Select (View Mode)",
    args: {
        multiple: false,
        chips: [
            { id: "graph", label: "Graph View", icon: <Layers size={12} /> },
            { id: "tree", label: "Tree View" },
            { id: "table", label: "Table View" },
        ],
        selected: ["graph"],
    },
};

export const SmallSize: Story = {
    name: "Small Chips",
    args: {
        size: "sm",
        chips: [
            { id: "ml", label: "ML" },
            { id: "arch", label: "Architecture" },
            { id: "devops", label: "DevOps" },
            { id: "data", label: "Data" },
            { id: "patterns", label: "Patterns" },
        ],
        selected: ["ml", "data"],
    },
};

export const PipelineDomains: Story = {
    name: "🧩 Domain Filter Composite",
    render: () => (
        <div
            className="flex flex-col gap-3 p-4 rounded-lg"
            style={{ background: "var(--bg-node)", border: "var(--border-node)", maxWidth: 450 }}
        >
            <h4 className="text-xs font-semibold" style={{ color: "var(--text-secondary)" }}>
                Filter by Domain
            </h4>
            <FilterChips
                chips={[
                    { id: "all", label: "All" },
                    { id: "raptor", label: "RAPTOR", icon: <Layers size={12} />, color: "var(--color-concept)" },
                    { id: "qdrant", label: "Qdrant", icon: <Cog size={12} />, color: "var(--color-data)" },
                    { id: "neo4j", label: "Neo4j", icon: <Brain size={12} />, color: "var(--color-keyword)" },
                ]}
                selected={["raptor", "neo4j"]}
            />
        </div>
    ),
};
