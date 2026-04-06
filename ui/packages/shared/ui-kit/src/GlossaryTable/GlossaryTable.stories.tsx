import type { Meta, StoryObj } from "@storybook/react";
import { GlossaryTable } from "./GlossaryTable";

const meta: Meta<typeof GlossaryTable> = {
    title: "Knowledge Base/GlossaryTable",
    component: GlossaryTable,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj<typeof GlossaryTable>;

const entries = [
    { keyword: "gradient descent", score: 0.95, domain: "ML", conceptCount: 3, chunkCount: 12 },
    { keyword: "transformer", score: 0.92, domain: "DL", conceptCount: 5, chunkCount: 18 },
    { keyword: "attention", score: 0.88, domain: "DL", conceptCount: 4, chunkCount: 15 },
    { keyword: "embedding", score: 0.85, domain: "ML", conceptCount: 3, chunkCount: 10 },
    { keyword: "tokenization", score: 0.72, domain: "NLP", conceptCount: 2, chunkCount: 8 },
    { keyword: "backpropagation", score: 0.68, domain: "ML", conceptCount: 2, chunkCount: 6 },
    { keyword: "RAPTOR", score: 0.65, domain: "DE", conceptCount: 1, chunkCount: 24 },
    { keyword: "clustering", score: 0.55, domain: "ML", conceptCount: 1, chunkCount: 4 },
    { keyword: "neo4j", score: 0.42, domain: "DE", conceptCount: 1, chunkCount: 3 },
    { keyword: "Qdrant", score: 0.38, domain: "DE", conceptCount: 1, chunkCount: 2 },
];

export const FullTable: Story = {
    name: "🧩 10 Keywords — Full Table (M4)",
    args: { entries, domains: ["ML", "DL", "NLP", "DE"] },
};

export const SortedByScore: Story = {
    name: "🧩 Sorted by Score — Ranking (M4)",
    args: { entries },
};

export const FilteredByDomain: Story = {
    name: "🧩 Filtered by Domain — ML (M2)",
    args: { entries, domains: ["ML", "DL", "NLP", "DE"], activeDomain: "ML" },
};
