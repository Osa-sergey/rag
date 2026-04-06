import type { Meta, StoryObj } from "@storybook/react";
import { SourceTextViewer } from "./SourceTextViewer";

const meta: Meta<typeof SourceTextViewer> = {
    title: "UI Kit/SourceTextViewer",
    component: SourceTextViewer,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj<typeof SourceTextViewer>;

const snapshotText = `# Neural Network Training

Training a neural network involves forward propagation, computing the loss function, and backpropagation.

The learning rate controls step size during optimization.
Batch size affects gradient estimation quality.

## Common Optimizers

- SGD (Stochastic Gradient Descent)
- Adam (Adaptive Moment Estimation)`;

const currentText = `# Neural Network Training

Training a neural network involves forward propagation, computing the loss function, and backpropagation.

The learning rate controls step size during optimization.
Batch size affects gradient estimation quality.
Proper initialization is critical for convergence.

## Common Optimizers

- SGD (Stochastic Gradient Descent)
- Adam (Adaptive Moment Estimation)
- AdaGrad (Adaptive Gradient)
- RMSProp

## Learning Rate Schedules

Cosine annealing, step decay, and warmup are widely used.`;

export const SnapshotTab: Story = {
    name: "🧩 Text Snapshot (K2)",
    args: {
        articleTitle: "Neural Network Training",
        snapshotText,
        currentText,
        snapshotDate: "2024-01-10",
        currentDate: "2024-03-15",
        defaultTab: "snapshot",
    },
};

export const CurrentTab: Story = {
    name: "Current Version",
    args: {
        articleTitle: "Neural Network Training",
        snapshotText,
        currentText,
        snapshotDate: "2024-01-10",
        currentDate: "2024-03-15",
        defaultTab: "current",
    },
};

export const DiffTab: Story = {
    name: "🧩 Diff Comparison (K3)",
    args: {
        articleTitle: "Neural Network Training",
        snapshotText,
        currentText,
        snapshotDate: "2024-01-10",
        currentDate: "2024-03-15",
        defaultTab: "diff",
    },
};

export const HighlightsTab: Story = {
    name: "🧩 Keyword Highlights (K5)",
    args: {
        articleTitle: "Neural Network Training",
        snapshotText,
        currentText,
        snapshotDate: "2024-01-10",
        currentDate: "2024-03-15",
        defaultTab: "highlights",
        highlights: [
            { start: 28, end: 48, label: "neural network", color: "var(--color-keyword)" },
            { start: 58, end: 78, label: "forward propagation" },
            { start: 94, end: 107, label: "loss function", color: "var(--color-concept)" },
            { start: 113, end: 130, label: "backpropagation" },
            { start: 136, end: 149, label: "learning rate", color: "var(--color-article)" },
        ],
    },
};
