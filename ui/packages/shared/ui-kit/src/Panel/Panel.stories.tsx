import React, { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { Panel } from "./Panel";

const meta: Meta<typeof Panel> = {
    title: "UI Kit/Panel",
    component: Panel,
    tags: ["autodocs"],
    argTypes: {
        side: { control: "select", options: ["left", "right", "bottom"] },
        open: { control: "boolean" },
        defaultSize: { control: { type: "range", min: 100, max: 600, step: 20 } },
    },
    parameters: { layout: "fullscreen" },
};

export default meta;
type Story = StoryObj<typeof Panel>;

const DemoContent = () => (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <p style={{ color: "var(--text-secondary)", fontSize: 13 }}>
            This panel is resizable — drag the edge to resize.
            Double-click the header to collapse.
        </p>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {["Config", "Defaults", "Outputs", "Callbacks", "Context"].map((tab) => (
                <button
                    key={tab}
                    className="px-3 py-1 rounded text-xs"
                    style={{
                        background: "var(--bg-node-hover)",
                        color: "var(--text-primary)",
                    }}
                >
                    {tab}
                </button>
            ))}
        </div>
    </div>
);

const PanelWrapper = ({
    side,
    title,
}: {
    side: "left" | "right" | "bottom";
    title: string;
}) => {
    const [open, setOpen] = useState(true);
    const isHorizontal = side !== "bottom";

    return (
        <div
            style={{
                display: "flex",
                flexDirection: isHorizontal ? "row" : "column",
                height: 400,
                width: "100%",
                background: "var(--bg-canvas)",
                border: "var(--border-node)",
                borderRadius: "var(--radius-node)",
                overflow: "hidden",
            }}
        >
            {side === "left" && (
                <Panel side="left" open={open} onToggle={() => setOpen(!open)} title={title}>
                    <DemoContent />
                </Panel>
            )}
            <div
                className="flex-1 flex items-center justify-center"
                style={{ color: "var(--text-muted)" }}
            >
                <div className="text-center">
                    <div className="text-lg mb-2">Main Canvas</div>
                    <button
                        onClick={() => setOpen(!open)}
                        className="px-4 py-2 rounded-lg text-sm"
                        style={{ background: "var(--color-step)", color: "#fff" }}
                    >
                        Toggle {title}
                    </button>
                </div>
            </div>
            {side === "right" && (
                <Panel side="right" open={open} onToggle={() => setOpen(!open)} title={title}>
                    <DemoContent />
                </Panel>
            )}
            {side === "bottom" && (
                <Panel side="bottom" open={open} onToggle={() => setOpen(!open)} title={title}>
                    <DemoContent />
                </Panel>
            )}
        </div>
    );
};

export const RightPanel: Story = {
    name: "Right (Inspector)",
    render: () => <PanelWrapper side="right" title="Inspector" />,
};

export const LeftPanel: Story = {
    name: "Left (Sidebar)",
    render: () => <PanelWrapper side="left" title="Node Palette" />,
};

export const BottomPanel: Story = {
    name: "Bottom (YAML Editor)",
    render: () => <PanelWrapper side="bottom" title="YAML Editor" />,
};
