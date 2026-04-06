import type { Meta, StoryObj } from "@storybook/react";
import { KBNode } from "./KBNode";

const meta: Meta<typeof KBNode> = {
    title: "Knowledge Base/KBNode",
    component: KBNode,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
    argTypes: {
        type: { control: "select", options: ["article", "keyword", "concept"] },
    },
};

export default meta;
type Story = StoryObj<typeof KBNode>;

export const ArticleNode: Story = {
    name: "🧩 Article Node (H1)",
    args: { type: "article", label: "Attention Is All You Need", count: 8 },
};

export const KeywordHigh: Story = {
    name: "🧩 Keyword — High Score (H10)",
    args: { type: "keyword", label: "transformer", score: 0.92, count: 5 },
};

export const KeywordLow: Story = {
    name: "🧩 Keyword — Low Score",
    args: { type: "keyword", label: "optimizer", score: 0.35, count: 2 },
};

export const ConceptActive: Story = {
    name: "🧩 Concept — Active v3 (H1)",
    args: { type: "concept", label: "Gradient Descent", version: "v3", count: 12 },
};

export const ConceptStale: Story = {
    name: "🧩 Concept — Stale (J3, L5)",
    args: { type: "concept", label: "Transformer", version: "v2", stale: true },
};

export const Selected: Story = {
    name: "Selected — Glow",
    args: { type: "concept", label: "Selected Node", selected: true, version: "v3" },
};

export const AllTypes: Story = {
    name: "All Types Side by Side",
    render: () => (
        <div className="flex items-center gap-4">
            <KBNode type="article" label="Article" count={8} />
            <KBNode type="keyword" label="keyword" score={0.8} count={5} />
            <KBNode type="concept" label="Concept" version="v3" count={12} />
            <KBNode type="concept" label="Stale" version="v2" stale />
        </div>
    ),
};
