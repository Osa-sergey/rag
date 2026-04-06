import type { Meta, StoryObj } from "@storybook/react";
import { JsonSchemaForm } from "./JsonSchemaForm";

const meta: Meta<typeof JsonSchemaForm> = {
    title: "UI Kit/JsonSchemaForm",
    component: JsonSchemaForm,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj<typeof JsonSchemaForm>;

export const SimpleConfig: Story = {
    name: "🧩 Step Config — 5 Fields (D1)",
    args: {
        title: "parse_articles",
        fields: [
            { key: "max_length", type: "number", value: 4096, defaultValue: 4096, description: "Maximum token length per chunk" },
            { key: "chunk_overlap", type: "number", value: 128, defaultValue: 64, description: "Overlap between adjacent chunks" },
            { key: "encoding", type: "select", value: "utf-8", options: ["utf-8", "ascii", "latin-1"], description: "Text encoding" },
            { key: "strip_html", type: "boolean", value: true, description: "Strip HTML tags before parsing" },
            { key: "output_key", type: "string", value: "parsed_articles", description: "Output context key" },
        ],
    },
};

export const NestedConfig: Story = {
    name: "🧩 Nested Config — stores.neo4j (D1)",
    args: {
        title: "Pipeline Configuration",
        fields: [
            { key: "name", type: "string", value: "raptor_indexing" },
            { key: "version", type: "number", value: 2 },
            {
                key: "stores",
                type: "group",
                label: "stores",
                children: [
                    {
                        key: "neo4j",
                        type: "group",
                        label: "neo4j",
                        children: [
                            { key: "host", type: "string", value: "bolt://localhost:7687" },
                            { key: "database", type: "string", value: "raptor" },
                            { key: "auth_enabled", type: "boolean", value: true },
                        ],
                    },
                    {
                        key: "qdrant",
                        type: "group",
                        label: "qdrant",
                        children: [
                            { key: "host", type: "string", value: "localhost:6333" },
                            { key: "collection", type: "string", value: "raptor_v2" },
                            { key: "vector_size", type: "number", value: 1536 },
                        ],
                    },
                ],
            },
        ],
    },
};

export const WithSourceBadges: Story = {
    name: "🧩 Source Badges — DEF/GLB/STP/OVR (D2)",
    args: {
        title: "parse_articles — Config Sources",
        showSources: true,
        fields: [
            { key: "max_length", type: "number", value: 4096, defaultValue: 4096, source: "DEF", description: "From Pydantic model default" },
            { key: "chunk_overlap", type: "number", value: 256, defaultValue: 64, source: "GLB", description: "Overridden in global_config" },
            { key: "encoding", type: "select", value: "utf-8", options: ["utf-8", "ascii", "latin-1"], source: "STP", description: "Set at step level" },
            { key: "output_key", type: "string", value: "custom_output", source: "OVR", description: "Runtime override via CLI" },
            { key: "strip_html", type: "boolean", value: true, source: "DEF", description: "Pydantic default (True)" },
        ],
    },
};

export const WithDefaults: Story = {
    name: "🧩 Pydantic Defaults + Placeholders (D3)",
    args: {
        title: "TreeBuilder — Defaults",
        showSources: true,
        fields: [
            { key: "levels", type: "number", value: undefined, defaultValue: 4, source: "DEF", description: "RAPTOR tree depth" },
            { key: "summarizer", type: "string", value: undefined, defaultValue: "gpt-4", source: "DEF", description: "LLM model for summarization" },
            { key: "min_cluster_size", type: "number", value: 5, defaultValue: 3, source: "STP", description: "Minimum items per cluster" },
            { key: "similarity_threshold", type: "number", value: undefined, defaultValue: 0.7, source: "DEF", description: "Cosine similarity cutoff" },
        ],
    },
};
