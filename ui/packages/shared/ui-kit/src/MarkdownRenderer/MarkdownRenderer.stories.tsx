import type { Meta, StoryObj } from "@storybook/react";
import { MarkdownRenderer } from "./MarkdownRenderer";

const meta: Meta<typeof MarkdownRenderer> = {
    title: "UI Kit/MarkdownRenderer",
    component: MarkdownRenderer,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj<typeof MarkdownRenderer>;

export const ArticleText: Story = {
    name: "🧩 Parsed Article (K1)",
    args: {
        content: `# Neural Network Training

Training a neural network involves **forward propagation**, computing the **loss function**, and **backpropagation**.

## Key Concepts

The **learning rate** controls step size during optimization. Batch size affects gradient estimation quality.

Common optimizers include:

- **SGD** (Stochastic Gradient Descent) — simple and effective
- **Adam** (Adaptive Moment Estimation) — combines momentum with RMSProp
- **AdaGrad** — adapts learning rate per parameter

## Code Example

\`\`\`python
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
loss = criterion(output, target)
loss.backward()
optimizer.step()
\`\`\`

> Proper initialization is critical for convergence — see [Glorot & Bengio, 2010](http://proceedings.mlr.press/v9/glorot10a.html)

The \`lr_scheduler\` module provides cosine annealing, step decay, and warmup schedules.`,
    },
};

export const ConceptDescription: Story = {
    name: "🧩 Concept Description (J1)",
    args: {
        content: `# Gradient Descent

A first-order iterative optimization algorithm for finding a **local minimum** of a differentiable function. The idea is to take repeated steps in the opposite direction of the **gradient** of the function at the current point.

## Variants

- **Batch GD** — uses the entire dataset per update
- **Stochastic GD** — uses a single sample
- **Mini-batch GD** — uses a subset (most common)

## Properties

Convergence is guaranteed for **convex functions** with appropriate learning rate. For non-convex functions (e.g. neural networks), finds local minima that are often good enough in practice.`,
        compact: true,
    },
};

export const WithHighlights: Story = {
    name: "🧩 Keyword Highlights (K5)",
    args: {
        content: `Training a neural network involves forward propagation, computing the loss function, and backpropagation. The learning rate controls step size during optimization. Batch size affects gradient estimation quality. Common optimizers include SGD, Adam, and AdaGrad. Proper initialization is critical for convergence.`,
        highlights: [
            { start: 10, end: 25, label: "Keyword: neural network", color: "var(--color-keyword)" },
            { start: 35, end: 55, label: "Keyword: forward propagation" },
            { start: 71, end: 84, label: "Keyword: loss function", color: "var(--color-concept)" },
            { start: 90, end: 107, label: "Keyword: backpropagation" },
            { start: 113, end: 126, label: "Keyword: learning rate", color: "var(--color-article)" },
            { start: 193, end: 196, label: "Optimizer: SGD", color: "var(--color-info)" },
            { start: 198, end: 202, label: "Optimizer: Adam", color: "var(--color-info)" },
            { start: 208, end: 215, label: "Optimizer: AdaGrad", color: "var(--color-info)" },
        ],
    },
};
