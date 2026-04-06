import type { Meta, StoryObj } from "@storybook/react";
import { ArticleCard } from "./ArticleCard";

const meta: Meta<typeof ArticleCard> = {
    title: "Knowledge Base/ArticleCard",
    component: ArticleCard,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
};

export default meta;
type Story = StoryObj<typeof ArticleCard>;

export const Default: Story = {
    name: "🧩 Article with Preview (K1)",
    args: {
        title: "Attention Is All You Need",
        source: "arxiv.org/abs/1706.03762",
        date: "2024-03-15",
        chunkCount: 12,
        keywordCount: 8,
        conceptCount: 3,
        preview: "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms...",
    },
};

export const Parsed: Story = {
    name: "🧩 Recently Parsed",
    args: {
        title: "RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval",
        source: "habr.com/articles/raptor-rag",
        date: "2024-11-20",
        chunkCount: 24,
        keywordCount: 15,
        conceptCount: 5,
        preview: "RAPTOR introduces a novel approach to retrieval-augmented generation by constructing a recursive tree structure...",
    },
};

export const Minimal: Story = {
    name: "Minimal — Title Only",
    args: {
        title: "Introduction to Graph Databases",
        source: "neo4j.com/docs/getting-started",
        chunkCount: 6,
    },
};

export const AllCards: Story = {
    name: "All Cards — Grid",
    render: () => (
        <div className="flex items-start gap-4 flex-wrap">
            <ArticleCard title="Attention Is All You Need" source="arxiv.org" date="2024-03" chunkCount={12} keywordCount={8} conceptCount={3} />
            <ArticleCard title="RAPTOR: Tree-Organized Retrieval" source="habr.com" date="2024-11" chunkCount={24} keywordCount={15} conceptCount={5} />
            <ArticleCard title="Graph Databases 101" source="neo4j.com" chunkCount={6} keywordCount={4} />
        </div>
    ),
};
