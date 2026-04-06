import React, { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { GroupNode } from "./GroupNode";

const meta: Meta<typeof GroupNode> = {
    title: "React Flow/GroupNode",
    component: GroupNode,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
};

export default meta;
type Story = StoryObj<typeof GroupNode>;

const MiniStep = ({ name, color }: { name: string; color?: string }) => (
    <div className="px-2.5 py-1.5 rounded-lg text-[10px] font-medium whitespace-nowrap"
        style={{ background: "var(--bg-node)", border: "var(--border-node)", color: color ?? "var(--text-primary)" }}>
        {name}
    </div>
);

export const EmptyGroup: Story = {
    name: "Empty Cluster — ETL Group",
    args: { title: "ETL Group", childCount: 0, color: "var(--color-info)" },
};

export const LegacyChildren: Story = {
    name: "Legacy Children — Simple List",
    render: () => (
        <GroupNode title="Indexing Pipeline" color="var(--color-info)" childCount={3}>
            <MiniStep name="parse_articles" />
            <MiniStep name="extract_keywords" />
            <MiniStep name="build_concepts" />
        </GroupNode>
    ),
};

export const CanvasWithEdges: Story = {
    name: "🧩 Canvas — Triangle Arrows from Edges",
    render: () => (
        <GroupNode title="Indexing Sub-Pipeline" color="var(--color-info)" canvasWidth={380} canvasHeight={140}
            canvasChildren={[
                { id: "parse", render: <MiniStep name="parse_articles" />, x: 15, y: 50, width: 90, height: 28 },
                { id: "extract", render: <MiniStep name="extract_keywords" />, x: 50, y: 50, width: 100, height: 28 },
                { id: "build", render: <MiniStep name="build_concepts" />, x: 85, y: 50, width: 95, height: 28 },
            ]}
            canvasEdges={[
                { from: "parse", to: "extract", arrow: "triangle" },
                { from: "extract", to: "build", arrow: "triangle" },
            ]}
        />
    ),
};

export const MixedArrows: Story = {
    name: "🧩 Mixed Arrow Types — Triangle, Dot, Diamond",
    render: () => (
        <GroupNode title="Data Flow" color="#a855f7" canvasWidth={400} canvasHeight={180}
            canvasChildren={[
                { id: "source", render: <MiniStep name="source" color="#22c55e" />, x: 15, y: 25, width: 50, height: 28 },
                { id: "transform", render: <MiniStep name="transform" />, x: 50, y: 75, width: 70, height: 28 },
                { id: "sink", render: <MiniStep name="sink" color="#ef4444" />, x: 85, y: 25, width: 40, height: 28 },
                { id: "monitor", render: <MiniStep name="monitor" color="#f59e0b" />, x: 85, y: 75, width: 60, height: 28 },
            ]}
            canvasEdges={[
                { from: "source", to: "transform", arrow: "triangle", color: "var(--color-success)" },
                { from: "transform", to: "sink", arrow: "diamond", color: "var(--color-error)" },
                { from: "transform", to: "monitor", arrow: "dot", dashed: true, color: "var(--color-warning)" },
            ]}
        />
    ),
};

export const NestedGroups: Story = {
    name: "🧩 Nested Groups — Group Inside Group",
    render: () => (
        <GroupNode title="Full RAPTOR Pipeline" color="#a855f7" canvasWidth={440} canvasHeight={240} renderDepth={2}
            canvasChildren={[
                {
                    id: "ingest", x: 25, y: 50, width: 170, height: 120,
                    render: (
                        <GroupNode title="Ingest" color="var(--color-info)" currentDepth={1} renderDepth={2}
                            canvasWidth={140} canvasHeight={70}
                            canvasChildren={[
                                { id: "p", render: <MiniStep name="parse" />, x: 25, y: 50, width: 45, height: 28 },
                                { id: "c", render: <MiniStep name="chunk" />, x: 75, y: 50, width: 48, height: 28 },
                            ]}
                            canvasEdges={[{ from: "p", to: "c", arrow: "triangle" }]}
                        />
                    ),
                },
                {
                    id: "index", x: 75, y: 50, width: 170, height: 120,
                    render: (
                        <GroupNode title="Index" color="var(--color-success)" currentDepth={1} renderDepth={2}
                            canvasWidth={140} canvasHeight={70}
                            canvasChildren={[
                                { id: "e", render: <MiniStep name="embed" />, x: 25, y: 50, width: 48, height: 28 },
                                { id: "s", render: <MiniStep name="store" />, x: 75, y: 50, width: 44, height: 28 },
                            ]}
                            canvasEdges={[{ from: "e", to: "s", arrow: "triangle" }]}
                        />
                    ),
                },
            ]}
            canvasEdges={[{ from: "ingest", to: "index", arrow: "diamond", color: "#a855f7" }]}
        />
    ),
};

export const LongTitleCollapsed: Story = {
    name: "🧩 Long Title Collapsed — Auto-sized",
    render: () => (
        <GroupNode title="Very Long Pipeline Group Name That Should Not Overflow" color="var(--color-warning)" childCount={12} collapsed />
    ),
};

const FullscreenDemo = () => {
    const [fs, setFs] = useState(false);
    return (
        <div style={{ height: fs ? "100vh" : "auto" }}>
            <GroupNode title="RAPTOR Pipeline" color="#a855f7" isFullscreen={fs}
                breadcrumbs={fs ? ["Root", "RAPTOR Pipeline"] : []}
                onFullscreen={() => setFs(true)} onBack={() => setFs(false)}
                canvasWidth={400} canvasHeight={180}
                canvasChildren={[
                    { id: "parse", render: <MiniStep name="parse_articles" />, x: 12, y: 30, width: 90, height: 28 },
                    { id: "extract", render: <MiniStep name="extract_keywords" />, x: 38, y: 70, width: 100, height: 28 },
                    { id: "build", render: <MiniStep name="build_concepts" />, x: 65, y: 30, width: 95, height: 28 },
                    { id: "tree", render: <MiniStep name="build_tree" />, x: 88, y: 70, width: 70, height: 28 },
                ]}
                canvasEdges={[
                    { from: "parse", to: "extract", arrow: "triangle" },
                    { from: "extract", to: "build", arrow: "triangle" },
                    { from: "build", to: "tree", arrow: "diamond" },
                ]}
            />
        </div>
    );
};

export const Fullscreen: Story = {
    name: "🧩 Fullscreen — Expand + Back",
    render: () => <FullscreenDemo />,
};

export const Collapsed: Story = {
    name: "Collapsed — Summary Badge",
    render: () => <GroupNode title="ETL Steps" color="var(--color-warning)" childCount={5} collapsed />,
};
