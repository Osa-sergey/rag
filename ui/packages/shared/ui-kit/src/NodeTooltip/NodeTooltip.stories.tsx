import type { Meta, StoryObj } from "@storybook/react";
import { NodeTooltip } from "./NodeTooltip";

const meta: Meta<typeof NodeTooltip> = {
    title: "React Flow/NodeTooltip",
    component: NodeTooltip,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
};

export default meta;
type Story = StoryObj<typeof NodeTooltip>;

export const Simple: Story = {
    name: "Simple — Name + Type",
    args: {
        name: "parse_articles",
        type: "Step",
        module: "raptor.parse.ArticleParser",
    },
};

export const Rich: Story = {
    name: "🧩 Rich — Stats + Status (H6, B3)",
    args: {
        name: "build_concepts",
        type: "Step",
        typeColor: "var(--color-info)",
        module: "raptor.concept.ConceptBuilder",
        status: "running",
        stats: [
            { label: "Outputs", value: 2 },
            { label: "Config fields", value: 5 },
            { label: "Callbacks", value: 3 },
            { label: "Keywords", value: 42 },
        ],
    },
};

export const ConceptNode: Story = {
    name: "🧩 Concept Node Tooltip",
    args: {
        name: "Gradient Descent",
        type: "Concept",
        typeColor: "var(--color-concept)",
        status: "success",
        stats: [
            { label: "Domain", value: "ML" },
            { label: "Version", value: "v3" },
            { label: "Keywords", value: 12 },
            { label: "Sources", value: 5 },
        ],
    },
};

export const Loading: Story = {
    name: "Loading — Skeleton",
    args: {
        name: "",
        loading: true,
    },
};
