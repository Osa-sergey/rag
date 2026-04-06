import React from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { TopBar } from "./TopBar";
import { Home, GitBranch, ChevronRight, Search, Bell, Settings, Layers } from "lucide-react";

const meta: Meta<typeof TopBar> = {
    title: "UI Kit/TopBar",
    component: TopBar,
    tags: ["autodocs"],
    parameters: { layout: "fullscreen" },
};

export default meta;
type Story = StoryObj<typeof TopBar>;

/* Simple breadcrumb helper for stories */
const Crumbs = ({ items }: { items: Array<{ label: string; icon?: React.ReactNode }> }) => (
    <nav className="flex items-center gap-1 text-xs" aria-label="Breadcrumb">
        {items.map((item, i) => (
            <React.Fragment key={item.label}>
                {i > 0 && <ChevronRight size={10} style={{ color: "var(--text-muted)" }} />}
                <span
                    className="flex items-center gap-1 cursor-pointer hover:underline"
                    style={{ color: i === items.length - 1 ? "var(--text-primary)" : "var(--text-muted)" }}
                >
                    {item.icon}
                    {item.label}
                </span>
            </React.Fragment>
        ))}
    </nav>
);

const IconBtn = ({ icon }: { icon: React.ReactNode }) => (
    <button className="p-2 rounded-lg transition-colors hover:bg-white/5" style={{ color: "var(--text-muted)" }}>
        {icon}
    </button>
);

export const Default: Story = {
    name: "🧩 DAG Builder TopBar (S1)",
    render: () => (
        <TopBar
            title="DAG Builder"
            leading={<Layers size={16} style={{ color: "var(--color-info)" }} />}
            actions={
                <>
                    <IconBtn icon={<Bell size={14} />} />
                    <IconBtn icon={<Settings size={14} />} />
                </>
            }
            showThemeToggle
        />
    ),
};

export const WithBreadcrumbs: Story = {
    name: "🧩 KB TopBar with Breadcrumbs (M1)",
    render: () => (
        <TopBar
            breadcrumb={
                <Crumbs items={[
                    { label: "Knowledge Base", icon: <Home size={10} /> },
                    { label: "Concepts" },
                    { label: "Gradient Descent" },
                ]} />
            }
            actions={<IconBtn icon={<Settings size={14} />} />}
            showThemeToggle
        />
    ),
};

export const WithSearch: Story = {
    name: "🧩 Global Search TopBar (M1)",
    render: () => (
        <TopBar
            title="Knowledge Base"
            search={
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs" style={{ background: "var(--bg-node)", border: "var(--border-node)", color: "var(--text-muted)" }}>
                    <Search size={12} />
                    <span>Search concepts, articles, keywords...</span>
                    <kbd className="ml-auto text-[9px] px-1 py-0.5 rounded" style={{ background: "var(--bg-node-hover)", color: "var(--text-muted)" }}>⌘K</kbd>
                </div>
            }
            actions={
                <>
                    <IconBtn icon={<Bell size={14} />} />
                    <IconBtn icon={<Settings size={14} />} />
                </>
            }
        />
    ),
};
