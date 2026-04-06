import React, { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { ConfigForm, ConfigGroup, ConfigSource } from "./ConfigForm";

const meta: Meta<typeof ConfigForm> = {
    title: "DAG Builder/ConfigForm",
    component: ConfigForm,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
};

export default meta;
type Story = StoryObj<typeof ConfigForm>;

const simpleGroups: ConfigGroup[] = [
    {
        id: "core",
        title: "Core Settings",
        fields: [
            { key: "timeout", label: "Timeout (seconds)", type: "number", value: 300, source: "DEF", description: "Maximum execution time before failing." },
            { key: "retries", label: "Max Retries", type: "number", value: 3, source: "GLB" },
            { key: "debug", label: "Debug Mode", type: "boolean", value: false, source: "STP" },
            { key: "model", label: "LLM Model", type: "select", value: "gpt-4-turbo", source: "OVR", options: [{ label: "GPT-4 Turbo", value: "gpt-4-turbo" }, { label: "Claude 3 Opus", value: "claude-3-opus" }] },
            { key: "prompt_prefix", label: "Prompt Prefix", type: "string", value: "You are a helpful assistant.", source: "DEF" },
        ],
    },
];

const validationGroups: ConfigGroup[] = [
    {
        id: "db",
        title: "Database Connection",
        fields: [
            { key: "host", label: "Host Address", type: "string", value: "localhost", source: "DEF" },
            { key: "port", label: "Port", type: "number", value: -1, source: "OVR", error: "Port must be between 1 and 65535" },
            { key: "engine", label: "Storage Engine", type: "select", value: "unknown", source: "STP", options: [{ label: "PostgreSQL", value: "postgres" }, { label: "MySQL", value: "mysql" }], error: "Invalid storage engine selected" },
        ],
    },
];

const nestedGroups: ConfigGroup[] = [
    {
        id: "stores.neo4j",
        title: "stores.neo4j Config",
        fields: [
            { key: "uri", label: "Connection URI", type: "string", value: "bolt://localhost:7687", source: "GLB" },
            { key: "username", label: "Auth Username", type: "string", value: "neo4j", source: "DEF" },
            { key: "labels", label: "Node Labels Mapping", type: "dict", value: { "Article": "Document", "Concept": "Entity" }, source: "STP", description: "Mapping from internal types to Neo4j labels." },
        ],
    },
];

const StatefulForm = ({ initialGroups }: { initialGroups: ConfigGroup[] }) => {
    const [groups, setGroups] = useState(initialGroups);
    return (
        <div className="w-[400px]">
            <ConfigForm
                groups={groups}
                onChange={(groupId, key, value) => {
                    setGroups(groups.map(g => {
                        if (g.id !== groupId) return g;
                        return {
                            ...g,
                            fields: g.fields.map(f => f.key === key ? { ...f, value, error: undefined } : f)
                        };
                    }));
                }}
            />
        </div>
    );
};

export const SimpleSchema: Story = {
    name: "Simple Schema — 5 Fields",
    render: () => <StatefulForm initialGroups={simpleGroups} />,
};

export const ValidationErrors: Story = {
    name: "Validation Errors — Red Borders",
    render: () => <StatefulForm initialGroups={validationGroups} />,
};

export const NestedConfig: Story = {
    name: "Nested — stores.neo4j with Dict",
    render: () => <StatefulForm initialGroups={nestedGroups} />,
};

export const Empty: Story = {
    args: { groups: [] },
};
