import React from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { TabPanel } from "./TabPanel";
import { Badge } from "../Badge";
import { StatusIcon } from "../StatusIcon";

const meta: Meta<typeof TabPanel> = {
    title: "UI Kit/TabPanel",
    component: TabPanel,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj<typeof TabPanel>;

const sampleTabs = [
    {
        id: "config",
        label: "Config",
        badge: 12,
        content: (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <StatusIcon status="success" label="Valid configuration" />
                </div>
                <div
                    className="font-mono text-xs p-3 rounded-lg"
                    style={{ background: "var(--bg-node-hover)", color: "var(--text-secondary)" }}
                >
                    <div>model_name: "gpt-4o"</div>
                    <div>temperature: 0.1</div>
                    <div>max_tokens: 4096</div>
                    <div>chunk_size: 512</div>
                    <div>overlap: 64</div>
                </div>
            </div>
        ),
    },
    {
        id: "defaults",
        label: "Defaults",
        content: (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <p style={{ color: "var(--text-secondary)", fontSize: 13 }}>
                    Hydra default groups for this step:
                </p>
                <div style={{ display: "flex", gap: 6 }}>
                    <Badge variant="default">base</Badge>
                    <Badge variant="info">production</Badge>
                    <Badge variant="warning">fast</Badge>
                </div>
            </div>
        ),
    },
    {
        id: "outputs",
        label: "Outputs",
        badge: 3,
        content: (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-primary)" }}>chunks</span>
                    <Badge variant="default" size="sm">list[str]</Badge>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-primary)" }}>metadata</span>
                    <Badge variant="default" size="sm">dict</Badge>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-primary)" }}>article_id</span>
                    <Badge variant="default" size="sm">str</Badge>
                </div>
            </div>
        ),
    },
    {
        id: "callbacks",
        label: "Callbacks",
        content: (
            <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
                No callbacks configured for this step.
            </div>
        ),
    },
];

export const InspectorTabs: Story = {
    name: "Inspector (DAG Builder)",
    args: { tabs: sampleTabs },
};

export const TwoTabs: Story = {
    name: "Two Tabs",
    args: {
        tabs: [
            { id: "graph", label: "Graph View", content: <div style={{ color: "var(--text-secondary)" }}>📊 Graph visualization would render here</div> },
            { id: "tree", label: "Tree View", content: <div style={{ color: "var(--text-secondary)" }}>🌲 RAPTOR hierarchy would render here</div> },
        ],
    },
};

export const WithBadges: Story = {
    name: "With Badge Counts",
    args: {
        tabs: [
            { id: "all", label: "All", badge: 24, content: <div style={{ color: "var(--text-secondary)" }}>24 items</div> },
            { id: "stale", label: "Needs Review", badge: 3, content: <div style={{ color: "var(--text-secondary)" }}>3 stale concepts</div> },
            { id: "manual", label: "Manual", badge: 1, content: <div style={{ color: "var(--text-secondary)" }}>1 manually created</div> },
        ],
    },
};
