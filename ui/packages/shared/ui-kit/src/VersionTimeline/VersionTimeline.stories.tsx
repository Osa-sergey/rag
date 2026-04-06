import type { Meta, StoryObj } from "@storybook/react";
import { VersionTimeline } from "./VersionTimeline";

const meta: Meta<typeof VersionTimeline> = {
    title: "KB Panels/VersionTimeline",
    component: VersionTimeline,
    tags: ["autodocs"],
    parameters: { layout: "fullscreen" },
    decorators: [
        (Story) => (
            <div className="w-[450px] h-[600px] border shadow-2xl overflow-hidden m-8" style={{ borderColor: "var(--border-panel)" }}>
                <Story />
            </div>
        ),
    ],
};

export default meta;
type Story = StoryObj<typeof VersionTimeline>;

const mockVersions = [
    {
        id: "v3",
        version: "v3.0",
        date: "Today, 14:30",
        author: "AI Synthesis Engine",
        description: "Re-structured the definition to include LLM-based embeddings and removed stale keyword correlations.",
        changes: [
            { type: "modify" as const, field: "description", oldValue: "Old description about word2vec.", newValue: "New description including Transformer-based embeddings." },
            { type: "remove" as const, field: "keywords", oldValue: "keyword: word2vec\nkeyword: skip-gram", newValue: "" }
        ]
    },
    {
        id: "v2",
        version: "v2.1",
        date: "Yesterday, 09:15",
        author: "Alice Smith",
        description: "Added 2 new source articles and extracted 15 new keywords.",
        changes: [
            { type: "add" as const, field: "sources", oldValue: "", newValue: "Article: Attention is all you need\nArticle: BERT pre-training" }
        ]
    },
    {
        id: "v1",
        version: "v1.0",
        date: "Oct 12, 2023",
        author: "Initial Import",
        description: "Concept created via bulk import from legacy system.",
        changes: []
    }
];

export const FullHistory: Story = {
    args: {
        versions: mockVersions,
        currentVersionId: "v3",
    },
};

export const LegacyLongChain: Story = {
    args: {
        versions: [
            ...mockVersions,
            { id: "v0.9", version: "v0.9-beta", date: "Sep 01, 2023", author: "Bob", description: "Drafted concept", changes: [] },
            { id: "v0.1", version: "v0.1-alpha", date: "Aug 15, 2023", author: "System", description: "Created empty placeholder", changes: [] },
        ],
        currentVersionId: "v2",
    },
};
