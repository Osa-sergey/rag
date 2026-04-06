import type { Meta, StoryObj } from "@storybook/react";
import { KeywordDetailPanel } from "./KeywordDetailPanel";

const meta: Meta<typeof KeywordDetailPanel> = {
    title: "KB Panels/KeywordDetailPanel",
    component: KeywordDetailPanel,
    tags: ["autodocs"],
    parameters: { layout: "fullscreen" },
    decorators: [
        (Story) => (
            <div className="w-[500px] h-[700px] border shadow-2xl overflow-hidden" style={{ borderColor: "var(--border-panel)" }}>
                <Story />
            </div>
        ),
    ],
};

export default meta;
type Story = StoryObj<typeof KeywordDetailPanel>;

const mockConcepts = [
    {
        id: "c1",
        name: "Backpropagation",
        domain: "Machine Learning",
        domainColor: "#3b82f6",
        version: "v2.1",
        description: "An algorithm for supervised learning of artificial neural networks using gradient descent.",
        status: "active" as const,
        keywordCount: 14,
        sourceCount: 3,
    },
    {
        id: "c2",
        name: "Gradient Descent",
        domain: "Optimization",
        domainColor: "#8b5cf6",
        version: "v1.0",
        description: "A first-order iterative optimization algorithm for finding a local minimum of a differentiable function.",
        status: "active" as const,
        keywordCount: 22,
        sourceCount: 8,
    },
];

const mockOccurrences = [
    {
        id: "occ_1",
        articleTitle: "Deep Learning Foundations (Pg. 45)",
        score: 0.94,
        text: "The weights are updated using the error derivative obtained during the backward pass of the network. This backward pass, or backprop, efficiently computes the gradients for all layers. The chain rule is the core principle making this possible.",
    },
    {
        id: "occ_2",
        articleTitle: "Optimization Techniques 2024",
        score: 0.81,
        text: "Stochastic approximations of the full dataset gradient can speed up convergence. While forward passes give the loss, the backward pass tells us how to adjust parameters.",
    },
    {
        id: "occ_3",
        articleTitle: "Intro to Neural Networks",
        score: 0.65,
        text: "Without the backward pass spreading the error signal from the output layer to the hidden ones, multi-layer perceptrons could not learn complex non-linear boundaries.",
    },
];

export const FullFeatures: Story = {
    name: "With Sources and Concepts",
    args: {
        keyword: "backward pass",
        domain: "Algorithm",
        globalFrequency: 142,
        occurrences: mockOccurrences,
        relatedConcepts: mockConcepts,
    },
};

export const WithoutConcepts: Story = {
    args: {
        keyword: "stochastic gradient",
        globalFrequency: 38,
        occurrences: mockOccurrences.slice(0, 2),
        relatedConcepts: [],
    },
};

export const Empty: Story = {
    args: {
        keyword: "non-existent-term",
        globalFrequency: 0,
        occurrences: [],
        relatedConcepts: [],
    },
};
