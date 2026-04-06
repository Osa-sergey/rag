import type { Meta, StoryObj } from "@storybook/react";
import { ConceptDetailPanel } from "./ConceptDetailPanel";

const meta: Meta<typeof ConceptDetailPanel> = {
    title: "Knowledge Base/ConceptDetailPanel",
    component: ConceptDetailPanel,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
};

export default meta;
type Story = StoryObj<typeof ConceptDetailPanel>;

export const FullConcept: Story = {
    name: "🧩 Full Concept (J1)",
    args: {
        name: "Gradient Descent",
        domain: "Machine Learning",
        description: "An iterative optimization algorithm for finding the minimum of a differentiable function, widely used for training neural networks.",
        currentVersion: "v3",
        keywords: ["optimization", "gradient", "learning rate", "convergence", "SGD", "momentum", "Adam", "loss function", "backpropagation", "batch size", "epochs", "weight update"],
        sources: [
            { id: "1", title: "Deep Learning (Goodfellow et al.)", type: "article" },
            { id: "2", title: "An Overview of Gradient Descent Optimization Algorithms", type: "article" },
            { id: "3", title: "Neural Networks and Deep Learning", type: "article" },
        ],
        versions: [
            { version: "v3", date: "2024-11-15", changeType: "expanded" },
            { version: "v2", date: "2024-09-20", changeType: "enriched" },
            { version: "v1", date: "2024-07-01", changeType: "created" },
        ],
    },
};

export const StaleWarning: Story = {
    name: "🧩 Stale Warning (J3)",
    args: {
        name: "Transformer Architecture",
        domain: "Deep Learning",
        domainColor: "#a855f7",
        description: "Self-attention based model architecture.",
        currentVersion: "v2",
        stale: true,
        staleReason: "2 source articles updated since last expansion (14 days ago)",
        keywords: ["self-attention", "multi-head", "positional encoding", "encoder", "decoder"],
        sources: [
            { id: "1", title: "Attention Is All You Need", type: "article" },
        ],
        versions: [
            { version: "v2", date: "2024-10-01", changeType: "enriched" },
            { version: "v1", date: "2024-08-15", changeType: "created" },
        ],
    },
};

export const VersionHistory: Story = {
    name: "🧩 Version History — Timeline + Diffs (J4, J5)",
    args: {
        name: "RAPTOR Pipeline",
        domain: "Data Engineering",
        domainColor: "var(--color-info)",
        currentVersion: "v5",
        keywords: ["RAPTOR", "tree", "retrieval", "embedding"],
        sources: [],
        versions: [
            { version: "v5", date: "2024-12-01", changeType: "expanded" },
            { version: "v4", date: "2024-11-15", changeType: "enriched" },
            { version: "v3", date: "2024-10-20", changeType: "expanded" },
            { version: "v2", date: "2024-09-10", changeType: "enriched" },
            { version: "v1", date: "2024-07-01", changeType: "created" },
        ],
    },
};
