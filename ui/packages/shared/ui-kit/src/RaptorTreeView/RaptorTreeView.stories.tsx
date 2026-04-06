import type { Meta, StoryObj } from "@storybook/react";
import { RaptorTreeView } from "./RaptorTreeView";

const meta: Meta<typeof RaptorTreeView> = {
    title: "Knowledge Base/RaptorTreeView",
    component: RaptorTreeView,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
};

export default meta;
type Story = StoryObj<typeof RaptorTreeView>;

export const TwoLevels: Story = {
    name: "🧩 2 Levels — Root + Leaves (I1)",
    args: {
        nodes: [
            {
                id: "r1", label: "Optimization Methods", level: 0,
                summary: "Summary of gradient-based and derivative-free optimization techniques",
                children: [
                    { id: "l1", label: "Gradient Descent basics", level: 1, summary: "First-order iterative optimization algorithm" },
                    { id: "l2", label: "SGD with momentum", level: 1, summary: "Stochastic variant with exponential averaging" },
                    { id: "l3", label: "Adam optimizer", level: 1, summary: "Adaptive moment estimation" },
                ],
            },
        ],
    },
};

export const DeepTree: Story = {
    name: "🧩 4 Levels — Deep Tree",
    args: {
        nodes: [
            {
                id: "r1", label: "Machine Learning", level: 0,
                children: [
                    {
                        id: "c1", label: "Supervised Learning", level: 1,
                        children: [
                            {
                                id: "c1a", label: "Neural Networks", level: 2,
                                children: [
                                    { id: "l1", label: "Transformer Architecture", level: 3, summary: "Self-attention mechanism" },
                                    { id: "l2", label: "Convolutional Networks", level: 3, summary: "Spatial feature extraction" },
                                ],
                            },
                            { id: "c1b", label: "Decision Trees", level: 2 },
                        ],
                    },
                    {
                        id: "c2", label: "Unsupervised Learning", level: 1,
                        children: [
                            { id: "c2a", label: "Clustering", level: 2 },
                            { id: "c2b", label: "Dimensionality Reduction", level: 2 },
                        ],
                    },
                ],
            },
        ],
    },
};

export const PathHighlight: Story = {
    name: "🧩 Keyword Trail Highlight (I3)",
    args: {
        nodes: [
            {
                id: "r1", label: "NLP Techniques", level: 0,
                children: [
                    {
                        id: "c1", label: "Attention Mechanisms", level: 1,
                        children: [
                            { id: "l1", label: "Self-Attention", level: 2, summary: "Query-Key-Value computation" },
                            { id: "l2", label: "Cross-Attention", level: 2 },
                        ],
                    },
                    { id: "c2", label: "Tokenization", level: 1 },
                ],
            },
        ],
        highlightedPath: ["r1", "c1", "l1"],
    },
};
