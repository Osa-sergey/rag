import type { Meta, StoryObj } from "@storybook/react";
import { InspectorPanel } from "./InspectorPanel";

const meta: Meta<typeof InspectorPanel> = {
    title: "DAG Builder/InspectorPanel",
    component: InspectorPanel,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
};

export default meta;
type Story = StoryObj<typeof InspectorPanel>;

export const ConfigTab: Story = {
    name: "🧩 Config Tab — JsonSchemaForm (D1)",
    args: {
        stepName: "parse_articles",
        module: "raptor.parse.ArticleParser",
        activeTab: "config",
        configFields: [
            { key: "max_length", value: "4096", source: "DEF" },
            { key: "chunk_overlap", value: "256", source: "GLB" },
            { key: "encoding", value: "utf-8", source: "STP" },
            { key: "strip_html", value: "true", source: "DEF" },
            { key: "output_key", value: "parsed_articles", source: "STP" },
        ],
    },
};

export const IOTab: Story = {
    name: "🧩 I/O Tab — Grouped Inputs and Outputs",
    args: {
        stepName: "parse_articles",
        module: "raptor.parse.ArticleParser",
        activeTab: "io",
        inputFields: [
            { key: "raw_documents", type: "List[Document]", description: "Document {\n  id: str\n  content: str\n  metadata: dict\n}" },
            { key: "concept_schema", type: "Dict[str, Any]" },
        ],
        outputFields: [
            { key: "chunks", type: "List[str]" },
            { key: "metadata", type: "dict" },
            { key: "stats", type: "ParseStats", description: "ParseStats {\n  total_chars: int\n  parsed_nodes: int\n  failed_nodes: int\n}" },
        ],
    },
};

export const CallbacksTab: Story = {
    name: "🧩 Callbacks Tab (D5)",
    args: {
        stepName: "build_tree",
        module: "raptor.tree.TreeBuilder",
        activeTab: "callbacks",
        callbacks: [
            { type: "on_retry", params: "max_retries=3, delay=1.0" },
            { type: "on_failure" },
            { type: "on_alert", params: "channel=#pipeline" },
        ],
    },
};

export const ContextTab: Story = {
    name: "🧩 Context Tab — Requires + Provides (D7)",
    args: {
        stepName: "build_tree",
        module: "raptor.tree.TreeBuilder",
        activeTab: "context",
        context: {
            provides: ["RaptorContext", "TreeMetadata"],
            requires: ["ArticleContext"],
        },
    },
};

export const FullInspector: Story = {
    name: "🧩 Full Inspector — All Tabs (D1-D7)",
    args: {
        stepName: "build_concepts",
        module: "raptor.concept.ConceptBuilder",
        configFields: [
            { key: "model", value: "gpt-4", source: "GLB" },
            { key: "min_keywords", value: "3", source: "DEF" },
            { key: "max_concepts", value: "50", source: "STP" },
        ],
        outputFields: [
            { key: "concepts", type: "List[Concept]" },
        ],
        callbacks: [
            { type: "on_retry", params: "max=3" },
        ],
        context: {
            provides: ["ConceptContext"],
            requires: ["ArticleContext", "KeywordContext"],
        },
        inputFields: [
            { key: "raw_documents", type: "List[Document]" },
            { key: "concept_schema", type: "Dict[str, Any]" },
        ],
    },
};
