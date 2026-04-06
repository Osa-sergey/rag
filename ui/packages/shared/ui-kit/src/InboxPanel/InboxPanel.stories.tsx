import type { Meta, StoryObj } from "@storybook/react";
import { InboxPanel } from "./InboxPanel";

const meta: Meta<typeof InboxPanel> = {
    title: "Knowledge Base/InboxPanel",
    component: InboxPanel,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
};

export default meta;
type Story = StoryObj<typeof InboxPanel>;

export const Empty: Story = {
    name: "🧩 Empty — Inbox Clear (L5)",
    args: { items: [] },
};

export const ThreeStale: Story = {
    name: "🧩 3 Stale — Review Queue (L5)",
    args: {
        items: [
            { id: "1", conceptName: "Transformer Architecture", domain: "Deep Learning", staleDays: 14, severity: "high", sourceCount: 3 },
            { id: "2", conceptName: "Word2Vec", domain: "NLP", staleDays: 7, severity: "medium", sourceCount: 2 },
            { id: "3", conceptName: "Attention Mechanism", domain: "Deep Learning", staleDays: 3, severity: "low", sourceCount: 1 },
        ],
    },
};

export const LargeQueue: Story = {
    name: "Large Queue — 8 Items",
    args: {
        items: [
            { id: "1", conceptName: "BERT", domain: "NLP", staleDays: 30, severity: "high", sourceCount: 5 },
            { id: "2", conceptName: "GPT Architecture", domain: "LLM", staleDays: 21, severity: "high", sourceCount: 4 },
            { id: "3", conceptName: "Tokenization", domain: "NLP", staleDays: 14, severity: "medium", sourceCount: 2 },
            { id: "4", conceptName: "Embedding Models", domain: "ML", staleDays: 10, severity: "medium", sourceCount: 3 },
            { id: "5", conceptName: "Vector Search", domain: "DB", staleDays: 7, severity: "low", sourceCount: 1 },
            { id: "6", conceptName: "RAG Pipeline", domain: "ML", staleDays: 5, severity: "low", sourceCount: 2 },
            { id: "7", conceptName: "Knowledge Graph", domain: "DB", staleDays: 3, severity: "low", sourceCount: 1 },
            { id: "8", conceptName: "Prompt Engineering", domain: "LLM", staleDays: 2, severity: "low", sourceCount: 1 },
        ],
    },
};
