import type { Meta, StoryObj } from "@storybook/react";
import { AppShell } from "./AppShell";

const meta: Meta<typeof AppShell> = {
    title: "AppShell/AppShell",
    component: AppShell,
    tags: ["autodocs"],
    parameters: { layout: "fullscreen" },
};

export default meta;
type Story = StoryObj<typeof AppShell>;

const TopBarMock = () => (
    <div className="flex items-center gap-4 px-4 py-2">
        <span className="text-xs font-bold" style={{ color: "var(--text-primary)" }}>🚀 RAPTOR Platform</span>
        <span className="text-[9px] px-2 py-0.5 rounded" style={{ background: "rgba(99,102,241,0.1)", color: "var(--color-info)" }}>DAG Builder</span>
    </div>
);

const SidebarMock = () => (
    <div className="p-3">
        <div className="text-[10px] font-semibold mb-2" style={{ color: "var(--text-muted)" }}>STEPS</div>
        {["parse_articles", "extract_keywords", "build_concepts", "build_tree", "index_vectors"].map((s) => (
            <div key={s} className="text-xs py-1.5 px-2 rounded hover:bg-white/3 cursor-pointer" style={{ color: "var(--text-secondary)" }}>{s}</div>
        ))}
    </div>
);

const InspectorMock = () => (
    <div className="p-3">
        <div className="text-xs font-semibold mb-2" style={{ color: "var(--text-primary)" }}>Inspector</div>
        <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>Select a node to inspect</div>
    </div>
);

const BottomMock = () => (
    <div className="p-3 font-mono text-[10px]" style={{ color: "var(--text-secondary)" }}>
        <div>name: raptor_indexing</div>
        <div>steps: 5</div>
        <div>edges: 4</div>
    </div>
);

export const FullLayout: Story = {
    name: "🧩 Full Layout — All Panels (S2)",
    args: {
        topBar: <TopBarMock />,
        sidebar: <SidebarMock />,
        inspector: <InspectorMock />,
        bottomPanel: <BottomMock />,
    },
    decorators: [(Story: any) => <div style={{ height: "500px" }}><Story /></div>],
};

export const WithSidebar: Story = {
    name: "🧩 With Sidebar — No Bottom (S4)",
    args: {
        topBar: <TopBarMock />,
        sidebar: <SidebarMock />,
        showBottom: false,
    },
    decorators: [(Story: any) => <div style={{ height: "400px" }}><Story /></div>],
};

export const CanvasOnly: Story = {
    name: "Canvas Only — Minimal",
    args: {
        topBar: <TopBarMock />,
        showSidebar: false,
        showInspector: false,
        showBottom: false,
    },
    decorators: [(Story: any) => <div style={{ height: "400px" }}><Story /></div>],
};
