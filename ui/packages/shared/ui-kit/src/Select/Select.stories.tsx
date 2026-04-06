import type { Meta, StoryObj } from "@storybook/react";
import { Select } from "./Select";
import { Database, Cloud, Cpu, Tag } from "lucide-react";

const meta: Meta<typeof Select> = {
    title: "UI Kit/Select",
    component: Select,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
    argTypes: {
        multiple: { control: "boolean" },
        searchable: { control: "boolean" },
        disabled: { control: "boolean" },
        fullWidth: { control: "boolean" },
    },
};

export default meta;
type Story = StoryObj<typeof Select>;

export const Single: Story = {
    args: {
        label: "Embedding Model",
        placeholder: "Choose model...",
        options: [
            { value: "openai", label: "OpenAI Ada-002", icon: <Cloud size={12} /> },
            { value: "hf", label: "HuggingFace E5-Large", icon: <Cpu size={12} /> },
            { value: "cohere", label: "Cohere Embed v3" },
        ],
        value: "openai",
    },
};

export const MultiSelect: Story = {
    name: "Multi Select (Tags)",
    args: {
        label: "Step Tags",
        multiple: true,
        placeholder: "Select tags...",
        options: [
            { value: "etl", label: "ETL", icon: <Tag size={12} /> },
            { value: "indexing", label: "Indexing" },
            { value: "ml", label: "Machine Learning" },
            { value: "nlp", label: "NLP" },
            { value: "graph", label: "Graph" },
        ],
        value: ["etl", "indexing"],
        fullWidth: true,
    },
};

export const Searchable: Story = {
    name: "Searchable",
    args: {
        label: "Domain Filter",
        searchable: true,
        placeholder: "Search domain...",
        options: [
            { value: "ml", label: "Machine Learning" },
            { value: "nlp", label: "NLP" },
            { value: "cv", label: "Computer Vision" },
            { value: "rl", label: "Reinforcement Learning" },
            { value: "devops", label: "DevOps" },
            { value: "data", label: "Data Engineering" },
            { value: "arch", label: "Architecture" },
        ],
        fullWidth: true,
    },
};

export const Grouped: Story = {
    name: "🧩 Grouped (Hydra Defaults D4)",
    args: {
        label: "Configuration Preset",
        searchable: true,
        placeholder: "Select preset...",
        options: [
            { value: "openai", label: "OpenAI Ada-002", group: "Embeddings" },
            { value: "hf", label: "HuggingFace E5", group: "Embeddings" },
            { value: "qdrant", label: "Qdrant", group: "Vector Store", icon: <Database size={12} /> },
            { value: "chroma", label: "ChromaDB", group: "Vector Store", icon: <Database size={12} /> },
            { value: "neo4j", label: "Neo4j", group: "Graph Store", icon: <Database size={12} /> },
        ],
        fullWidth: true,
    },
};

export const WithError: Story = {
    args: {
        label: "Required field",
        placeholder: "Please select...",
        options: [{ value: "a", label: "Option A" }],
        errorText: "This field is required",
    },
};
