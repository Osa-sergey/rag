import React from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { KeyValueList } from "./KeyValueList";

const meta: Meta<typeof KeyValueList> = {
    title: "UI Kit/KeyValueList",
    component: KeyValueList,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
    argTypes: {
        showSource: { control: "boolean" },
    },
};

export default meta;
type Story = StoryObj<typeof KeyValueList>;

export const SimpleConfig: Story = {
    name: "Simple Config",
    args: {
        entries: [
            { key: "model_name", value: '"gpt-4o"' },
            { key: "temperature", value: "0.1" },
            { key: "max_tokens", value: "4096" },
            { key: "chunk_size", value: "512" },
            { key: "overlap", value: "64" },
        ],
    },
};

export const WithSources: Story = {
    name: "With Source Badges",
    args: {
        showSource: true,
        entries: [
            { key: "model_name", value: '"gpt-4o"', source: "global" as const },
            { key: "temperature", value: "0.1", source: "default" as const },
            { key: "chunk_size", value: "512", source: "step" as const },
            { key: "overlap", value: "64", source: "override" as const },
            { key: "neo4j_uri", value: '"bolt://localhost"', source: "global" as const },
        ],
    },
};

export const Nested: Story = {
    name: "Nested Config",
    args: {
        showSource: true,
        entries: [
            { key: "model_name", value: '"gpt-4o"', source: "global" as const },
            {
                key: "embedding",
                value: "",
                source: "step" as const,
                children: [
                    { key: "model", value: '"text-embedding-3-small"', source: "step" as const },
                    { key: "dimensions", value: "1536", source: "default" as const },
                    { key: "batch_size", value: "32", source: "override" as const },
                ],
            },
            {
                key: "neo4j",
                value: "",
                source: "global" as const,
                children: [
                    { key: "uri", value: '"bolt://localhost:7687"', source: "global" as const },
                    { key: "database", value: '"habr"', source: "global" as const },
                ],
            },
        ],
    },
};

export const StepOutputs: Story = {
    name: "Step Outputs",
    args: {
        entries: [
            { key: "chunks", value: "list[str]" },
            { key: "metadata", value: "dict" },
            { key: "article_id", value: "str" },
            { key: "embedding_count", value: "int" },
        ],
    },
};
