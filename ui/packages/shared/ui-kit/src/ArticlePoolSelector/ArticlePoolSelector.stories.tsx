import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { ArticlePoolSelector } from "./ArticlePoolSelector";

const meta: Meta<typeof ArticlePoolSelector> = {
    title: "KB Panels/ArticlePoolSelector",
    component: ArticlePoolSelector,
    tags: ["autodocs"],
    parameters: { layout: "fullscreen" },
    decorators: [
        (Story) => (
            <div className="w-[500px] h-[700px] border shadow-2xl overflow-hidden m-8" style={{ borderColor: "var(--border-panel)" }}>
                <Story />
            </div>
        ),
    ],
};

export default meta;
type Story = StoryObj<typeof ArticlePoolSelector>;

const mockArticles = [
    {
        id: "art_1",
        title: "Attention Is All You Need",
        domain: "AI",
        date: "2017-06-12",
        author: "Vaswani et al.",
        previewText: "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
        keywordsCount: 12,
        chunksCount: 45,
        status: "indexed" as const,
    },
    {
        id: "art_2",
        title: "BERT: Pre-training of Deep Bidirectional Transformers",
        domain: "NLP",
        date: "2018-10-11",
        author: "Devlin et al.",
        previewText: "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers.",
        keywordsCount: 20,
        chunksCount: 88,
        status: "indexed" as const,
    },
    {
        id: "art_3",
        title: "Understanding LSTM Networks",
        domain: "AI",
        date: "2015-08-27",
        author: "Olah",
        previewText: "Recurrent Neural Networks have magical capabilities. But they are hard to train. LSTMs solve the vanishing gradient problem.",
        keywordsCount: 8,
        chunksCount: 32,
        status: "failed" as const,
    },
    {
        id: "art_4",
        title: "Graph Neural Networks: A Review",
        domain: "ML",
        date: "2020-01-01",
        author: "Wu et al.",
        previewText: "Deep learning has revolutionized many machine learning tasks in recent years. However, applying deep learning to graph data is challenging.",
        keywordsCount: 15,
        chunksCount: 60,
        status: "indexing" as const,
    }
];

export const Empty: Story = {
    args: {
        availableArticles: mockArticles,
        selectedIds: [],
    },
    render: (args) => {
        const [selected, setSelected] = useState<string[]>([]);
        return <ArticlePoolSelector {...args} selectedIds={selected} onSelectionChange={setSelected} />;
    }
};

export const PreSelected: Story = {
    args: {
        availableArticles: mockArticles,
        selectedIds: ["art_1", "art_2"],
    },
    render: (args) => {
        const [selected, setSelected] = useState<string[]>(args.selectedIds || []);
        return <ArticlePoolSelector {...args} selectedIds={selected} onSelectionChange={setSelected} />;
    }
};

export const Searching: Story = {
    args: {
        availableArticles: mockArticles,
        selectedIds: ["art_1"],
        isSearching: true,
    },
    render: (args) => {
        const [selected, setSelected] = useState<string[]>(args.selectedIds || []);
        return <ArticlePoolSelector {...args} selectedIds={selected} onSelectionChange={setSelected} />;
    }
};
