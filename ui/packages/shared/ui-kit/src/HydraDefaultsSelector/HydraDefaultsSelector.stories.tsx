import React, { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { HydraDefaultsSelector, HydraDefaultGroup } from "./HydraDefaultsSelector";

const meta: Meta<typeof HydraDefaultsSelector> = {
    title: "DAG Builder/HydraDefaultsSelector",
    component: HydraDefaultsSelector,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
};

export default meta;
type Story = StoryObj<typeof HydraDefaultsSelector>;

const oneGroup: HydraDefaultGroup[] = [
    {
        id: "embed",
        label: "Embedding Model",
        options: [
            { label: "OpenAI text-embedding-ada-002", value: "openai_ada" },
            { label: "Mistral Embed", value: "mistral" },
            { label: "BGE Large (Local)", value: "bge_large" },
        ],
        selectedValue: "openai_ada"
    }
];

const threeGroups: HydraDefaultGroup[] = [
    {
        id: "embed",
        label: "Embedding Model",
        options: [
            { label: "OpenAI text-embedding-ada-002", value: "openai" },
            { label: "BGE Large (Local)", value: "bge_local" },
        ],
        selectedValue: "openai"
    },
    {
        id: "store",
        label: "Vector Store",
        options: [
            { label: "Qdrant", value: "qdrant" },
            { label: "ChromaDB", value: "chroma" },
            { label: "Neo4j Vector", value: "neo4j" },
        ],
        selectedValue: "qdrant"
    },
    {
        id: "chunk",
        label: "Chunking Strategy",
        options: [
            { label: "RecursiveCharacterTextSplitter", value: "recursive" },
            { label: "SemanticChunker", value: "semantic" },
            { label: "TokenTextSplitter", value: "token" },
        ],
        selectedValue: "semantic"
    }
];

const StatefulSelector = ({ initialGroups }: { initialGroups: HydraDefaultGroup[] }) => {
    const [groups, setGroups] = useState(initialGroups);
    return (
        <div className="w-[360px]">
            <HydraDefaultsSelector
                groups={groups}
                onChange={(groupId, value) => {
                    setGroups(groups.map(g => g.id === groupId ? { ...g, selectedValue: value } : g));
                }}
            />
        </div>
    );
};

export const OneGroup: Story = {
    name: "1 Group — Embedding Model",
    render: () => <StatefulSelector initialGroups={oneGroup} />,
};

export const ThreeGroups: Story = {
    name: "3 Groups — Embed + Store + Chunk",
    render: () => <StatefulSelector initialGroups={threeGroups} />,
};

export const Empty: Story = {
    args: { groups: [] },
};
