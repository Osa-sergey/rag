import type { Meta, StoryObj } from "@storybook/react";
import { KeywordReviewList } from "./KeywordReviewList";

const meta: Meta<typeof KeywordReviewList> = {
    title: "KB Panels/KeywordReviewList",
    component: KeywordReviewList,
    tags: ["autodocs"],
    parameters: { layout: "fullscreen" },
    decorators: [
        (Story) => (
            <div className="w-[600px] h-[500px] p-6 bg-black/10 backdrop-blur-sm">
                <Story />
            </div>
        ),
    ],
};

export default meta;
type Story = StoryObj<typeof KeywordReviewList>;

const mockKeywords = [
    {
        id: "k1",
        keyword: "reinforcement learning",
        score: 0.96,
        mentions: 45,
        sourceArticles: 12,
        status: "pending" as const,
    },
    {
        id: "k2",
        keyword: "bellman equation",
        score: 0.82,
        mentions: 14,
        sourceArticles: 3,
        status: "pending" as const,
    },
    {
        id: "k3",
        keyword: "markov decision process",
        score: 0.88,
        mentions: 31,
        sourceArticles: 8,
        status: "pending" as const,
    },
    {
        id: "k4",
        keyword: "policy gradient",
        score: 0.74,
        mentions: 9,
        sourceArticles: 2,
        status: "pending" as const,
    },
];

export const PendingReview: Story = {
    args: {
        keywords: mockKeywords,
    },
};

export const Empty: Story = {
    args: {
        keywords: [
            { ...mockKeywords[0], status: "approved" as const },
            { ...mockKeywords[1], status: "rejected" as const },
        ],
    },
};
