import React, { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { NavigatorSidebar, NavigatorTab } from "./NavigatorSidebar";

const meta: Meta<typeof NavigatorSidebar> = {
    title: "Knowledge Base/NavigatorSidebar",
    component: NavigatorSidebar,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj<typeof NavigatorSidebar>;

const articles = [
    { id: "1", label: "Attention Is All You Need", type: "arxiv.org", badge: "12 chunks" },
    { id: "2", label: "RAPTOR: Tree-Organized Retrieval", type: "habr.com", badge: "24 chunks" },
    { id: "3", label: "Introduction to Graph Databases", type: "neo4j.com", badge: "6 chunks" },
    { id: "4", label: "Scaling Laws for Neural LMs", type: "arxiv.org", badge: "18 chunks" },
];

const concepts = [
    { id: "1", label: "Gradient Descent", badge: "v3", badgeColor: "var(--color-concept)" },
    { id: "2", label: "Transformer Architecture", badge: "v2", badgeColor: "var(--color-warning)", stale: true },
    { id: "3", label: "RAPTOR Pipeline", badge: "v1", badgeColor: "var(--color-info)" },
];

const Interactive = ({ tab, items, inbox }: { tab: NavigatorTab; items: any[]; inbox?: number }) => {
    const [activeTab, setActiveTab] = useState<NavigatorTab>(tab);
    return <NavigatorSidebar activeTab={activeTab} items={items} onTabChange={setActiveTab} inboxCount={inbox} />;
};

export const ArticlesList: Story = {
    name: "🧩 Articles List (M2)",
    render: () => <Interactive tab="articles" items={articles} />,
};

export const ConceptsList: Story = {
    name: "🧩 Concepts — Filtered by Domain",
    render: () => <Interactive tab="concepts" items={concepts} />,
};

export const InboxWithStale: Story = {
    name: "🧩 Inbox — 3 Stale (L5)",
    render: () => (
        <Interactive
            tab="inbox"
            inbox={3}
            items={[
                { id: "1", label: "Transformer Architecture", type: "Stale since 14 days", stale: true, badge: "Review" as any, badgeColor: "var(--color-error)" },
                { id: "2", label: "Word2Vec", type: "Stale since 7 days", stale: true, badge: "Review" as any, badgeColor: "var(--color-error)" },
                { id: "3", label: "Attention Mechanism", type: "Stale since 3 days", stale: true, badge: "Review" as any, badgeColor: "var(--color-warning)" },
            ]}
        />
    ),
};

export const EmptyState: Story = {
    name: "Empty — No Results",
    render: () => <Interactive tab="keywords" items={[]} />,
};
