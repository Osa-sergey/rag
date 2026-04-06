import type { Meta, StoryObj } from "@storybook/react";
import { CreateConceptWizard } from "./CreateConceptWizard";

const meta: Meta<typeof CreateConceptWizard> = {
    title: "KB Panels/CreateConceptWizard",
    component: CreateConceptWizard,
    tags: ["autodocs"],
    parameters: { layout: "fullscreen" },
    decorators: [
        (Story) => (
            <div className="w-full h-[600px] flex items-center justify-center p-8 bg-black/50 backdrop-blur-sm">
                <Story />
            </div>
        ),
    ],
};

export default meta;
type Story = StoryObj<typeof CreateConceptWizard>;

const mockArticles = [
    {
        id: "a1",
        title: "Introduction to Transformers",
        domain: "AI",
        dateIndexed: "Oct 24, 2024",
        wordCount: 1540,
        status: "indexed" as const,
        keywordCount: 12,
    },
    {
        id: "a2",
        title: "Self-Attention Mechanism",
        domain: "AI",
        dateIndexed: "Oct 25, 2024",
        wordCount: 890,
        status: "indexed" as const,
        keywordCount: 8,
    },
    {
        id: "a3",
        title: "Positional Encoding",
        domain: "AI",
        dateIndexed: "Oct 26, 2024",
        wordCount: 1120,
        status: "pending" as const,
        keywordCount: 3,
    },
    {
        id: "a4",
        title: "History of Deep Learning",
        domain: "History",
        dateIndexed: "Sep 12, 2024",
        wordCount: 2400,
        status: "indexed" as const,
        keywordCount: 45,
    },
];

const mockExtractedKeywords = [
    { id: "kw1", keyword: "transformer architecture", score: 0.95, mentions: 24 },
    { id: "kw2", keyword: "self-attention", score: 0.88, mentions: 18 },
    { id: "kw3", keyword: "positional encoding", score: 0.72, mentions: 12 },
    { id: "kw4", keyword: "deep learning", score: 0.65, mentions: 45 },
    { id: "kw5", keyword: "neural networks", score: 0.58, mentions: 30 },
];

export const Default: Story = {
    args: {
        availableArticles: mockArticles,
        extractedKeywords: mockExtractedKeywords,
    },
};
