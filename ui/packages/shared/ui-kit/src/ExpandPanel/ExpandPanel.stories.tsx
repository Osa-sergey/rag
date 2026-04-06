import type { Meta, StoryObj } from "@storybook/react";
import { ExpandPanel } from "./ExpandPanel";

const meta: Meta<typeof ExpandPanel> = {
    title: "Knowledge Base/ExpandPanel",
    component: ExpandPanel,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
};

export default meta;
type Story = StoryObj<typeof ExpandPanel>;

export const V1ToV2: Story = {
    name: "🧩 v1→v2 — Direct Comparison (L1)",
    args: {
        conceptName: "Gradient Descent",
        fromVersion: "v1",
        toVersion: "v2",
        diffLines: [
            { type: "unchanged", content: "An iterative optimization algorithm" },
            { type: "removed", content: "for minimizing functions." },
            { type: "added", content: "for finding the minimum of a differentiable function," },
            { type: "added", content: "widely used for training neural networks." },
            { type: "unchanged", content: "Uses first-order derivatives." },
        ],
        candidateKeywords: [
            { keyword: "neural networks", checked: true },
            { keyword: "differentiable", checked: true },
            { keyword: "training", checked: false },
            { keyword: "backpropagation" },
        ],
    },
};

export const LLMEnrichment: Story = {
    name: "🧩 LLM Enrichment — v2→v3",
    args: {
        conceptName: "Transformer Architecture",
        fromVersion: "v2",
        toVersion: "v3",
        diffLines: [
            { type: "unchanged", content: "Self-attention based model architecture" },
            { type: "added", content: "Extended with multi-head attention mechanism" },
            { type: "added", content: "Supports both encoder-decoder and decoder-only variants" },
            { type: "removed", content: "Primarily for sequence-to-sequence tasks" },
            { type: "added", content: "Foundation for GPT, BERT, and modern LLMs" },
        ],
        candidateKeywords: [
            { keyword: "multi-head attention", checked: true },
            { keyword: "GPT", checked: true },
            { keyword: "BERT", checked: true },
            { keyword: "decoder-only", checked: false },
            { keyword: "encoder-decoder" },
            { keyword: "LLM" },
        ],
    },
};

export const WithKeywordReview: Story = {
    name: "🧩 Keyword Review — Checkboxes (L2)",
    args: {
        conceptName: "RAPTOR Pipeline",
        fromVersion: "v1",
        toVersion: "v2",
        diffLines: [],
        candidateKeywords: [
            { keyword: "recursive", checked: true },
            { keyword: "abstractive", checked: true },
            { keyword: "tree-organized", checked: true },
            { keyword: "retrieval", checked: false },
            { keyword: "embedding", checked: false },
            { keyword: "chunking" },
            { keyword: "clustering" },
            { keyword: "summarization" },
        ],
    },
};
