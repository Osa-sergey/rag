import type { Meta, StoryObj } from "@storybook/react";
import { StepNode } from "./StepNode";

const meta: Meta<typeof StepNode> = {
    title: "DAG Builder/StepNode",
    component: StepNode,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
    argTypes: {
        status: { control: "select", options: ["idle", "running", "success", "failed"] },
        compact: { control: "boolean" },
        selected: { control: "boolean" },
    },
};

export default meta;
type Story = StoryObj<typeof StepNode>;

export const Idle: Story = {
    name: "🧩 Idle (B8)",
    args: {
        name: "parse_articles",
        module: "raptor.parse.ArticleParser",
        status: "idle",
        inputs: [
            { id: "in1", label: "raw_text", type: "str" },
        ],
        outputs: [
            { id: "out1", label: "chunks", type: "List[str]" },
            { id: "out2", label: "metadata", type: "dict" },
        ],
        tags: ["etl", "parsing"],
    },
};

export const Running: Story = {
    name: "🧩 Running + Pulse",
    args: {
        name: "build_concepts",
        module: "raptor.concept.ConceptBuilder",
        status: "running",
        inputs: [
            { id: "in1", label: "chunks", type: "List[str]" },
            { id: "in2", label: "keywords", type: "List[str]" },
        ],
        outputs: [
            { id: "out1", label: "concepts", type: "List[Concept]" },
        ],
        callbacks: [
            { type: "on_retry", params: "max=3" },
            { type: "on_alert" },
        ],
    },
};

export const Success: Story = {
    name: "🧩 Success — ✅ Green Glow",
    args: {
        name: "index_vectors",
        module: "raptor.store.QdrantIndexer",
        status: "success",
        inputs: [{ id: "in1", label: "embeddings" }],
        outputs: [{ id: "out1", label: "index_id" }],
        context: {
            requires: ["RaptorContext"],
        },
    },
};

export const Failed: Story = {
    name: "🧩 Failed — 🔴 Error Glow",
    args: {
        name: "build_tree",
        module: "raptor.tree.TreeBuilder",
        status: "failed",
        callbacks: [
            { type: "on_failure" },
            { type: "on_retry", params: "max=3" },
        ],
    },
};

export const WithErrors: Story = {
    name: "🧩 Validation Errors (F9)",
    args: {
        name: "parse_articles",
        module: "raptor.parse.ArticleParser",
        status: "idle",
        errors: [
            "max_length must be ≥ 256",
            "missing required output: chunks",
        ],
    },
};

export const WithContext: Story = {
    name: "🧩 Context Provides + Requires (B4)",
    args: {
        name: "build_tree",
        module: "raptor.tree.TreeBuilder",
        status: "success",
        context: {
            provides: ["RaptorContext"],
            requires: ["ArticleContext"],
        },
        inputs: [{ id: "in1", label: "concepts" }],
        outputs: [{ id: "out1", label: "tree" }],
    },
};

export const Compact: Story = {
    name: "Compact — 120px Width",
    args: {
        name: "parse_articles",
        status: "success",
        compact: true,
    },
};

export const Selected: Story = {
    name: "Selected — Blue Border",
    args: {
        name: "build_concepts",
        module: "raptor.concept.ConceptBuilder",
        status: "idle",
        selected: true,
        inputs: [{ id: "in1", label: "chunks" }, { id: "in2", label: "keywords" }],
        outputs: [{ id: "out1", label: "concepts" }],
        tags: ["ml", "indexing"],
    },
};

export const AllStatuses: Story = {
    name: "🧩 All Statuses Side-by-Side",
    render: () => (
        <div className="flex items-start gap-4">
            <StepNode name="step_1" status="idle" compact />
            <StepNode name="step_2" status="running" compact />
            <StepNode name="step_3" status="success" compact />
            <StepNode name="step_4" status="failed" compact />
        </div>
    ),
};
