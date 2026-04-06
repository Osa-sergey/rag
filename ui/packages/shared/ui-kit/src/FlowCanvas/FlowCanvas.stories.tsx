import type { Meta, StoryObj } from "@storybook/react";
import { FlowCanvas } from "./FlowCanvas";
import { Plus, FileText } from "lucide-react";

const meta: Meta<typeof FlowCanvas> = {
    title: "React Flow/FlowCanvas",
    component: FlowCanvas,
    tags: ["autodocs"],
    parameters: { layout: "fullscreen" },
};

export default meta;
type Story = StoryObj<typeof FlowCanvas>;

/* Mini step node for demo */
const MiniNode = ({ name, status }: { name: string; status: "idle" | "success" | "running" }) => (
    <div
        className="px-3 py-2 rounded-lg text-xs font-medium min-w-[120px] text-center"
        style={{
            background: "var(--bg-node)",
            border: "var(--border-node)",
            color: "var(--text-primary)",
            boxShadow: status === "success"
                ? "0 0 12px rgba(34,197,94,0.3)"
                : status === "running"
                    ? "0 0 12px rgba(99,102,241,0.3)"
                    : "0 4px 12px rgba(0,0,0,0.2)",
        }}
    >
        <div className="flex items-center gap-1.5 justify-center">
            <span
                className="w-1.5 h-1.5 rounded-full"
                style={{
                    background: status === "success" ? "var(--color-success)" : status === "running" ? "var(--color-info)" : "var(--text-muted)",
                    animation: status === "running" ? "pulse 1.5s infinite" : "none",
                }}
            />
            {name}
        </div>
    </div>
);

export const EmptyCanvas: Story = {
    name: "Empty — No Graph Loaded",
    render: () => (
        <FlowCanvas
            emptyState={
                <div className="flex flex-col items-center gap-3 text-center">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: "rgba(99,102,241,0.08)" }}>
                        <Plus size={24} style={{ color: "var(--color-info)" }} />
                    </div>
                    <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>No pipeline loaded</p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>Drag steps from the palette or import a YAML file</p>
                </div>
            }
        />
    ),
};

export const WithNodes: Story = {
    name: "🧩 DAG Pipeline — 5 Steps (A2)",
    render: () => (
        <FlowCanvas
            showMinimap
            nodes={[
                { id: "1", x: 40, y: 60, content: <MiniNode name="parse_articles" status="success" /> },
                { id: "2", x: 40, y: 180, content: <MiniNode name="extract_keywords" status="success" /> },
                { id: "3", x: 280, y: 120, content: <MiniNode name="build_concepts" status="running" /> },
                { id: "4", x: 520, y: 60, content: <MiniNode name="build_tree" status="idle" /> },
                { id: "5", x: 520, y: 180, content: <MiniNode name="index_vectors" status="idle" /> },
            ]}
            edges={[
                { id: "e1", from: "1", to: "3" },
                { id: "e2", from: "2", to: "3" },
                { id: "e3", from: "3", to: "4" },
                { id: "e4", from: "3", to: "5" },
            ]}
        />
    ),
};

export const DarkWithMinimap: Story = {
    name: "🧩 Dark Mode + Minimap + Controls (S1)",
    render: () => (
        <FlowCanvas
            background="dots"
            showMinimap
            showControls
            nodes={[
                { id: "1", x: 80, y: 80, content: <MiniNode name="fetch_data" status="success" /> },
                { id: "2", x: 300, y: 80, content: <MiniNode name="transform" status="success" /> },
                { id: "3", x: 300, y: 200, content: <MiniNode name="validate" status="running" /> },
                { id: "4", x: 520, y: 140, content: <MiniNode name="build_tree" status="idle" /> },
            ]}
            edges={[
                { id: "e1", from: "1", to: "2" },
                { id: "e2", from: "1", to: "3" },
                { id: "e3", from: "2", to: "4" },
                { id: "e4", from: "3", to: "4" },
            ]}
        />
    ),
};

export const LinesBackground: Story = {
    name: "Grid Lines Background",
    render: () => (
        <FlowCanvas
            background="lines"
            height={300}
            nodes={[
                { id: "1", x: 100, y: 80, content: <MiniNode name="step_a" status="idle" /> },
                { id: "2", x: 350, y: 80, content: <MiniNode name="step_b" status="idle" /> },
            ]}
            edges={[{ id: "e1", from: "1", to: "2" }]}
        />
    ),
};
