import type { Meta, StoryObj } from "@storybook/react";
import { Breadcrumb } from "./Breadcrumb";
import { Home, GitBranch, FileText, Brain } from "lucide-react";

const meta: Meta<typeof Breadcrumb> = {
    title: "UI Kit/Breadcrumb",
    component: Breadcrumb,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj<typeof Breadcrumb>;

const noop = () => { };

export const Simple: Story = {
    args: {
        items: [
            { label: "Pipelines", onClick: noop },
            { label: "RAPTOR", onClick: noop },
            { label: "parse_articles" },
        ],
    },
};

export const WithIcons: Story = {
    name: "With Icons",
    args: {
        items: [
            { label: "Home", icon: <Home size={12} />, onClick: noop },
            { label: "DAG Builder", icon: <GitBranch size={12} />, onClick: noop },
            { label: "Step Config" },
        ],
    },
};

export const Truncated: Story = {
    name: "Truncated (maxVisible=3)",
    args: {
        maxVisible: 3,
        items: [
            { label: "Knowledge Base", onClick: noop },
            { label: "Articles", onClick: noop },
            { label: "Machine Learning", onClick: noop },
            { label: "Concepts", onClick: noop },
            { label: "Gradient Descent" },
        ],
    },
};

export const KBArticlePath: Story = {
    name: "🧩 KB Article Path",
    args: {
        items: [
            { label: "Knowledge Base", icon: <Brain size={12} />, onClick: noop },
            { label: "Articles", icon: <FileText size={12} />, onClick: noop },
            { label: "RAG Pipeline Patterns" },
        ],
    },
};

export const DAGStepPath: Story = {
    name: "🧩 DAG Step Inspector",
    args: {
        items: [
            { label: "RAPTOR Pipeline", icon: <GitBranch size={12} />, onClick: noop },
            { label: "Steps", onClick: noop },
            { label: "build_concepts" },
        ],
    },
};
