import type { Meta, StoryObj } from "@storybook/react";
import { ArticleDetailPanel } from "./ArticleDetailPanel";

const meta: Meta<typeof ArticleDetailPanel> = {
    title: "KB Panels/ArticleDetailPanel",
    component: ArticleDetailPanel,
    tags: ["autodocs"],
    parameters: { layout: "fullscreen" },
    decorators: [
        (Story) => (
            <div className="w-[450px] h-[700px] border shadow-2xl overflow-hidden" style={{ borderColor: "var(--border-panel)" }}>
                <Story />
            </div>
        ),
    ],
};

export default meta;
type Story = StoryObj<typeof ArticleDetailPanel>;

const mockKeywords = [
    { id: "kw1", keyword: "neural architecture", score: 0.89, mentions: 12 },
    { id: "kw2", keyword: "gradient descent", score: 0.76, mentions: 8 },
    { id: "kw3", keyword: "backpropagation", score: 0.61, mentions: 5 },
    { id: "kw4", keyword: "loss function", score: 0.55, mentions: 4 },
];

const mockChunks = [
    {
        id: "c1",
        sequence: 1,
        text: "The conceptual foundation of modern neural networks lies in the parallel processing of information through dense architectures. Each layer contributes to a higher-level abstraction, enabling deep learning models to recognize complex patterns that simple linear models cannot capture.",
    },
    {
        id: "c2",
        sequence: 2,
        text: "Training these models relies extensively on optimization algorithms like stochastic gradient descent (SGD). By moving opposite to the gradient of the loss function, the network iteratively reduces error. The gradients themselves are computed precisely using the backpropagation algorithm.",
    },
    {
        id: "c3",
        sequence: 3,
        text: "This effectively means that an error found in the final layer is chained backwards using calculus (specifically, the chain rule), distributing 'blame' for the wrong prediction to all antecedent layers. Without this mechanism, training deep networks would be computationally intractable.",
    },
];

export const FullFeatures: Story = {
    args: {
        title: "Deep Learning Foundations and Mathematical Origins",
        domain: "Computer Science",
        dateIndexed: "Oct 24, 2024",
        wordCount: 1450,
        keywords: mockKeywords,
        chunks: mockChunks,
    },
};

export const Empty: Story = {
    args: {
        title: "A Brief History of Time",
        domain: "Physics",
        dateIndexed: "Pending",
        wordCount: 0,
        keywords: [],
        chunks: [],
    },
};
