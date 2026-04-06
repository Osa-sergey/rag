import React, { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { Drawer } from "./Drawer";
import { Search, FolderTree, BookOpen, Tag, Brain, Filter } from "lucide-react";

const meta: Meta<typeof Drawer> = {
    title: "UI Kit/Drawer",
    component: Drawer,
    tags: ["autodocs"],
    parameters: { layout: "fullscreen" },
    argTypes: {
        side: { control: "select", options: ["left", "right"] },
        size: { control: "select", options: ["sm", "md", "lg"] },
    },
};

export default meta;
type Story = StoryObj<typeof Drawer>;

const DrawerWrapper = (props: any) => {
    const [open, setOpen] = useState(true);
    return (
        <>
            <div className="p-6">
                <button
                    onClick={() => setOpen(true)}
                    className="px-4 py-2 rounded-lg text-sm font-medium"
                    style={{ background: "var(--color-info)", color: "var(--text-inverse)" }}
                >
                    Open Drawer
                </button>
            </div>
            <Drawer {...props} open={open} onClose={() => setOpen(false)}>
                {props.children}
            </Drawer>
        </>
    );
};

/* ── Story: KB NavigatorSidebar (S2, left) ── */
const NavItem = ({ icon, label, count, active }: { icon: React.ReactNode; label: string; count?: number; active?: boolean }) => (
    <div
        className="flex items-center gap-2.5 px-4 py-2 text-xs cursor-pointer transition-colors hover:bg-white/5"
        style={{
            color: active ? "var(--text-primary)" : "var(--text-secondary)",
            background: active ? "rgba(99,102,241,0.08)" : "transparent",
            borderLeft: active ? "2px solid var(--color-info)" : "2px solid transparent",
        }}
    >
        {icon}
        <span className="flex-1 truncate">{label}</span>
        {count !== undefined && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full" style={{ background: "var(--bg-node-hover)", color: "var(--text-muted)" }}>
                {count}
            </span>
        )}
    </div>
);

export const LeftNavigator: Story = {
    name: "🧩 KB NavigatorSidebar (S2, left)",
    render: () => (
        <DrawerWrapper side="left" size="sm" title="Knowledge Base">
            <div className="py-2">
                {/* Search */}
                <div className="px-3 py-2">
                    <div className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs" style={{ background: "var(--bg-node)", border: "var(--border-node)", color: "var(--text-muted)" }}>
                        <Search size={12} /> Search concepts...
                    </div>
                </div>

                {/* Tree */}
                <div className="mt-2 flex flex-col">
                    <NavItem icon={<FolderTree size={14} />} label="All Concepts" count={42} active />
                    <NavItem icon={<BookOpen size={14} />} label="Articles" count={18} />
                    <NavItem icon={<Tag size={14} />} label="Keywords" count={156} />
                    <NavItem icon={<Brain size={14} />} label="RAPTOR Trees" count={3} />
                    <NavItem icon={<Filter size={14} />} label="Stale Inbox" count={5} />
                </div>

                {/* Domain filters */}
                <div className="px-3 mt-4">
                    <p className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>Domains</p>
                    <div className="flex flex-wrap gap-1">
                        {["ML", "NLP", "DevOps", "Architecture"].map((d) => (
                            <span key={d} className="px-2 py-0.5 rounded-full text-[10px]" style={{ background: "var(--bg-node-hover)", color: "var(--text-secondary)" }}>
                                {d}
                            </span>
                        ))}
                    </div>
                </div>
            </div>
        </DrawerWrapper>
    ),
};

/* ── Story: DAG InspectorPanel (D1, right) ── */
export const RightInspector: Story = {
    name: "🧩 DAG InspectorPanel (D1, right)",
    render: () => (
        <DrawerWrapper
            side="right"
            size="md"
            title="parse_articles"
            headerActions={
                <div className="flex gap-0.5">
                    {["Config", "Outputs", "Context"].map((tab, i) => (
                        <button
                            key={tab}
                            className="px-2 py-1 rounded text-[10px] font-medium transition-colors"
                            style={{
                                background: i === 0 ? "rgba(99,102,241,0.12)" : "transparent",
                                color: i === 0 ? "var(--color-info)" : "var(--text-muted)",
                            }}
                        >
                            {tab}
                        </button>
                    ))}
                </div>
            }
        >
            <div className="p-4 flex flex-col gap-4">
                {/* Module badge */}
                <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded" style={{ background: "var(--bg-node-hover)", color: "var(--text-muted)" }}>
                        raptor.parse.ArticleParser
                    </span>
                </div>

                {/* Config fields */}
                <div className="flex flex-col gap-3">
                    <h4 className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>Configuration</h4>
                    {[
                        { key: "max_length", value: "4096", source: "DEF" },
                        { key: "chunk_overlap", value: "128", source: "GLB" },
                        { key: "encoding", value: "utf-8", source: "STP" },
                    ].map((f) => (
                        <div key={f.key} className="flex items-center gap-2">
                            <span className="text-xs font-mono flex-1 truncate" style={{ color: "var(--text-secondary)" }}>{f.key}</span>
                            <input
                                className="px-2 py-1 rounded text-xs w-24 text-right"
                                style={{ background: "var(--bg-node)", border: "var(--border-node)", color: "var(--text-primary)" }}
                                defaultValue={f.value}
                            />
                            <span
                                className="text-[9px] font-bold px-1.5 py-0.5 rounded"
                                style={{
                                    background: f.source === "DEF" ? "rgba(99,102,241,0.12)" : f.source === "GLB" ? "rgba(245,158,11,0.12)" : "rgba(34,197,94,0.12)",
                                    color: f.source === "DEF" ? "var(--color-info)" : f.source === "GLB" ? "var(--color-warning)" : "var(--color-success)",
                                }}
                            >
                                {f.source}
                            </span>
                        </div>
                    ))}
                </div>

                {/* Callbacks */}
                <div className="flex flex-col gap-2">
                    <h4 className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>Callbacks</h4>
                    {["on_retry (max=3)", "on_failure → alert_admin"].map((cb) => (
                        <div key={cb} className="flex items-center gap-2 text-xs" style={{ color: "var(--text-secondary)" }}>
                            <span className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--color-success)" }} />
                            {cb}
                        </div>
                    ))}
                </div>
            </div>
        </DrawerWrapper>
    ),
};

/* ── Story: Large with tabs ── */
export const LargeWithContent: Story = {
    name: "Large (lg) Detail View",
    render: () => (
        <DrawerWrapper side="right" size="lg" title="Concept: Gradient Descent">
            <div className="p-4 flex flex-col gap-4">
                <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                    A first-order iterative optimization algorithm for finding a local minimum of a differentiable function.
                    The idea is to take repeated steps in the opposite direction of the gradient of the function at the current point.
                </p>
                <div className="flex flex-col gap-2">
                    <h4 className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>Keywords (12)</h4>
                    <div className="flex flex-wrap gap-1.5">
                        {["learning rate", "batch", "SGD", "momentum", "Adam", "convergence", "loss function", "backpropagation", "mini-batch", "epoch", "weights", "optimizer"].map((kw) => (
                            <span key={kw} className="px-2 py-0.5 rounded-full text-[10px]" style={{ background: "rgba(34,211,153,0.12)", color: "var(--color-keyword)" }}>
                                {kw}
                            </span>
                        ))}
                    </div>
                </div>
                <div className="flex flex-col gap-2">
                    <h4 className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>Source Articles (3)</h4>
                    {["Deep Learning Fundamentals", "Optimization in ML", "Neural Network Training"].map((a) => (
                        <div key={a} className="text-xs px-3 py-2 rounded-lg" style={{ background: "var(--bg-node)", color: "var(--text-secondary)" }}>
                            📄 {a}
                        </div>
                    ))}
                </div>
            </div>
        </DrawerWrapper>
    ),
};
