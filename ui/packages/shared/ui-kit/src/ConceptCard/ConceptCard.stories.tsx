import type { Meta, StoryObj } from "@storybook/react";
import { ConceptCard } from "./ConceptCard";

const meta: Meta<typeof ConceptCard> = {
    title: "Knowledge Base/ConceptCard",
    component: ConceptCard,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
};

export default meta;
type Story = StoryObj<typeof ConceptCard>;

export const Active: Story = {
    name: "🧩 Active Concept (J1)",
    args: {
        name: "Gradient Descent",
        domain: "Machine Learning",
        domainColor: "var(--color-concept)",
        description: "An iterative optimization algorithm for finding the minimum of a differentiable function.",
        version: "v3",
        keywordCount: 12,
        sourceCount: 5,
        status: "active",
    },
};

export const Stale: Story = {
    name: "🧩 Stale — Outdated Source (J3, L5)",
    args: {
        name: "Transformer Architecture",
        domain: "Deep Learning",
        domainColor: "#a855f7",
        description: "Self-attention based model architecture used in modern NLP and vision tasks.",
        version: "v2",
        keywordCount: 18,
        sourceCount: 3,
        stale: true,
        status: "stale",
    },
};

export const Manual: Story = {
    name: "🧩 Manual — Human Created (L3)",
    args: {
        name: "RAPTOR Pipeline",
        domain: "Data Engineering",
        domainColor: "var(--color-info)",
        description: "Custom ETL pipeline for ingesting, parsing, and indexing documents into a knowledge graph.",
        version: "v1",
        keywordCount: 8,
        sourceCount: 2,
        status: "manual",
    },
};

export const AllVariants: Story = {
    name: "All Variants — Side by Side",
    render: () => (
        <div className="flex items-start gap-4">
            <ConceptCard name="Active Concept" domain="ML" version="v3" keywordCount={12} sourceCount={5} status="active" />
            <ConceptCard name="Stale Concept" domain="NLP" version="v2" keywordCount={8} sourceCount={3} stale status="stale" />
            <ConceptCard name="Manual Concept" domain="DE" version="v1" keywordCount={4} sourceCount={1} status="manual" />
        </div>
    ),
};
