import type { Meta, StoryObj } from "@storybook/react";
import { Badge } from "./Badge";
import { Tag, AlertTriangle, GitBranch, Database } from "lucide-react";

const meta: Meta<typeof Badge> = {
    title: "UI Kit/Badge",
    component: Badge,
    tags: ["autodocs"],
    argTypes: {
        variant: {
            control: "select",
            options: ["success", "error", "warning", "info", "stale", "default"],
        },
        size: {
            control: "select",
            options: ["sm", "md", "lg"],
        },
    },
};

export default meta;
type Story = StoryObj<typeof Badge>;

export const Default: Story = {
    args: { children: "default", variant: "default", size: "md" },
};

export const Success: Story = {
    args: { children: "active", variant: "success" },
};

export const Error: Story = {
    args: { children: "failed", variant: "error" },
};

export const Warning: Story = {
    args: { children: "needs review", variant: "warning" },
};

export const Info: Story = {
    args: { children: "running", variant: "info" },
};

export const Stale: Story = {
    args: { children: "outdated", variant: "stale" },
};

export const VersionBadge: Story = {
    args: {
        children: "v2",
        variant: "info",
        size: "sm",
        icon: <GitBranch size={12} />,
    },
};

export const TagBadge: Story = {
    args: {
        children: "indexing",
        variant: "default",
        icon: <Tag size={12} />,
    },
};

export const WithIcon: Story = {
    args: {
        children: "outdated source",
        variant: "stale",
        icon: <AlertTriangle size={14} />,
    },
};

export const AllSizes: Story = {
    render: () => (
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <Badge size="sm" variant="success">sm</Badge>
            <Badge size="md" variant="info">md</Badge>
            <Badge size="lg" variant="warning">lg</Badge>
        </div>
    ),
};

export const AllVariants: Story = {
    render: () => (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Badge variant="success">success</Badge>
            <Badge variant="error">error</Badge>
            <Badge variant="warning">warning</Badge>
            <Badge variant="info">info</Badge>
            <Badge variant="stale">stale</Badge>
            <Badge variant="default">default</Badge>
        </div>
    ),
};

export const ModuleTags: Story = {
    name: "Pipeline Module Tags",
    render: () => (
        <div style={{ display: "flex", gap: 6 }}>
            <Badge variant="default" icon={<Database size={12} />}>raptor_pipeline</Badge>
            <Badge variant="default" icon={<Tag size={12} />}>indexing</Badge>
            <Badge variant="default" icon={<Tag size={12} />}>devops</Badge>
        </div>
    ),
};
