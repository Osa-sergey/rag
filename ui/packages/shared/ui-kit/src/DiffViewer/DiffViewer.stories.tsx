import type { Meta, StoryObj } from "@storybook/react";
import { DiffViewer } from "./DiffViewer";

const meta: Meta<typeof DiffViewer> = {
    title: "UI Kit/DiffViewer",
    component: DiffViewer,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
    argTypes: {
        mode: { control: "select", options: ["inline", "side-by-side"] },
    },
};

export default meta;
type Story = StoryObj<typeof DiffViewer>;

const oldConcept = `name: Gradient Descent
domain: ML
version: 2
description: An optimization algorithm for finding local minima.
keywords:
  - learning rate
  - SGD
  - batch
sources: 3`;

const newConcept = `name: Gradient Descent
domain: Machine Learning
version: 3
description: A first-order iterative optimization algorithm for finding a local minimum of a differentiable function.
keywords:
  - learning rate
  - SGD
  - batch
  - momentum
  - Adam
  - convergence
sources: 5
enriched_by: GPT-4`;

export const ShortDiff: Story = {
    name: "🧩 Concept Version Diff (J5)",
    args: {
        title: "v2 → v3",
        oldText: oldConcept,
        newText: newConcept,
        oldLabel: "v2 — Direct update",
        newLabel: "v3 — LLM enriched",
    },
};

const oldArticle = `# Neural Network Training

Training a neural network involves forward propagation,
computing the loss function, and backpropagation.

The learning rate controls step size during optimization.
Batch size affects gradient estimation quality.

## Common Optimizers

- SGD (Stochastic Gradient Descent)
- Adam (Adaptive Moment Estimation)`;

const newArticle = `# Neural Network Training

Training a neural network involves forward propagation,
computing the loss function, and backpropagation.

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

export const LongDiff: Story = {
    name: "🧩 Article Comparison (K3)",
    args: {
        title: "Article: Neural Network Training",
        oldText: oldArticle,
        newText: newArticle,
        oldLabel: "Snapshot (Jan 10)",
        newLabel: "Current (Mar 15)",
    },
};

export const NoChanges: Story = {
    name: "No Changes — Identical",
    args: {
        title: "v1 → v1 (re-indexed)",
        oldText: "name: Gradient Descent\ndomain: ML\nversion: 1",
        newText: "name: Gradient Descent\ndomain: ML\nversion: 1",
    },
};

export const SideBySide: Story = {
    name: "Side-by-Side Mode",
    args: {
        title: "Pipeline Config Diff (G1)",
        mode: "side-by-side" as const,
        oldText: `steps:
  - name: parse_articles
    config:
      max_length: 2048
      encoding: utf-8
  - name: build_tree
    config:
      levels: 3`,
        newText: `steps:
  - name: parse_articles
    config:
      max_length: 4096
      chunk_overlap: 128
      encoding: utf-8
  - name: build_tree
    config:
      levels: 4
      summarizer: gpt-4`,
        oldLabel: "Before",
        newLabel: "After (applied override)",
    },
};
