import React from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { Popover } from "./Popover";
import { Settings, HelpCircle, MoreVertical } from "lucide-react";

const meta: Meta<typeof Popover> = {
    title: "UI Kit/Popover",
    component: Popover,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
    argTypes: {
        trigger: { control: "select", options: ["click", "hover"] },
        placement: { control: "select", options: ["top", "bottom", "left", "right"] },
    },
};

export default meta;
type Story = StoryObj<typeof Popover>;

export const ClickTrigger: Story = {
    name: "Click Trigger",
    render: () => (
        <Popover
            trigger="click"
            content={
                <div className="p-3 flex flex-col gap-2" style={{ minWidth: 180 }}>
                    <button className="text-left text-xs px-2 py-1.5 rounded hover:bg-white/5" style={{ color: "var(--text-primary)" }}>Edit Step</button>
                    <button className="text-left text-xs px-2 py-1.5 rounded hover:bg-white/5" style={{ color: "var(--text-primary)" }}>Duplicate</button>
                    <button className="text-left text-xs px-2 py-1.5 rounded hover:bg-white/5" style={{ color: "var(--color-error)" }}>Delete</button>
                </div>
            }
        >
            <button className="p-2 rounded-lg" style={{ border: "var(--border-node)" }}>
                <MoreVertical size={16} style={{ color: "var(--text-muted)" }} />
            </button>
        </Popover>
    ),
};

export const HoverTrigger: Story = {
    name: "Hover Trigger (NodeTooltip)",
    render: () => (
        <Popover
            trigger="hover"
            placement="top"
            content={
                <div className="px-3 py-2">
                    <p className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>parse_articles</p>
                    <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>raptor.parse.ArticleParser</p>
                    <p className="text-[10px] mt-1" style={{ color: "var(--text-muted)" }}>Status: idle • Outputs: 2</p>
                </div>
            }
        >
            <div className="px-3 py-2 rounded-lg text-sm" style={{ background: "var(--bg-node)", border: "var(--border-node)", color: "var(--text-primary)" }}>
                Hover me (StepNode)
            </div>
        </Popover>
    ),
};

export const WithForm: Story = {
    name: "🧩 Callback Param Editor (D5)",
    render: () => (
        <Popover
            trigger="click"
            width={280}
            content={
                <div className="p-4 flex flex-col gap-3">
                    <h4 className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>Retry Parameters</h4>
                    <div className="flex flex-col gap-1">
                        <label className="text-[10px] font-medium" style={{ color: "var(--text-muted)" }}>max_retries</label>
                        <input className="px-2 py-1.5 rounded text-xs" style={{ background: "var(--bg-node)", border: "var(--border-node)", color: "var(--text-primary)" }} defaultValue="3" />
                    </div>
                    <div className="flex flex-col gap-1">
                        <label className="text-[10px] font-medium" style={{ color: "var(--text-muted)" }}>delay_seconds</label>
                        <input className="px-2 py-1.5 rounded text-xs" style={{ background: "var(--bg-node)", border: "var(--border-node)", color: "var(--text-primary)" }} defaultValue="5" />
                    </div>
                    <button className="px-3 py-1.5 rounded text-[11px] font-medium self-end" style={{ background: "var(--color-info)", color: "var(--text-inverse)" }}>
                        Apply
                    </button>
                </div>
            }
        >
            <button className="px-3 py-1.5 rounded-lg text-xs flex items-center gap-1.5" style={{ border: "var(--border-node)", color: "var(--text-secondary)" }}>
                <Settings size={12} /> Edit Retry
            </button>
        </Popover>
    ),
};
