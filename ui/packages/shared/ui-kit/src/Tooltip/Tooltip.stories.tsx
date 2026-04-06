import type { Meta, StoryObj } from "@storybook/react";
import { Tooltip } from "./Tooltip";
import { Badge } from "../Badge";

const meta: Meta<typeof Tooltip> = {
    title: "UI Kit/Tooltip",
    component: Tooltip,
    tags: ["autodocs"],
    argTypes: {
        position: {
            control: "select",
            options: ["top", "bottom", "left", "right"],
        },
        delay: { control: { type: "range", min: 0, max: 500, step: 50 } },
    },
    parameters: { layout: "centered" },
};

export default meta;
type Story = StoryObj<typeof Tooltip>;

export const Top: Story = {
    args: {
        content: "This is a tooltip",
        position: "top",
        children: <button className="px-4 py-2 rounded-lg bg-blue-500 text-white text-sm">Hover me</button>,
    },
};

export const Bottom: Story = {
    args: {
        content: "Tooltip below",
        position: "bottom",
        children: <button className="px-4 py-2 rounded-lg bg-blue-500 text-white text-sm">Hover me</button>,
    },
};

export const Left: Story = {
    args: {
        content: "Tooltip left",
        position: "left",
        children: <button className="px-4 py-2 rounded-lg bg-blue-500 text-white text-sm">Hover me</button>,
    },
};

export const Right: Story = {
    args: {
        content: "Tooltip right",
        position: "right",
        children: <button className="px-4 py-2 rounded-lg bg-blue-500 text-white text-sm">Hover me</button>,
    },
};

export const RichContent: Story = {
    name: "Rich Content",
    args: {
        position: "top",
        content: (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <strong>raptor_pipeline.run</strong>
                <span>RAPTOR indexing pipeline</span>
            </div>
        ),
        children: <Badge variant="info">raptor_pipeline</Badge>,
    },
};

export const AllPositions: Story = {
    name: "All Positions",
    render: () => (
        <div style={{ display: "flex", gap: 32, padding: 64 }}>
            <Tooltip content="Top" position="top"><button className="px-3 py-1 border rounded text-sm" style={{ borderColor: "var(--color-dep)" }}>Top</button></Tooltip>
            <Tooltip content="Bottom" position="bottom"><button className="px-3 py-1 border rounded text-sm" style={{ borderColor: "var(--color-dep)" }}>Bottom</button></Tooltip>
            <Tooltip content="Left" position="left"><button className="px-3 py-1 border rounded text-sm" style={{ borderColor: "var(--color-dep)" }}>Left</button></Tooltip>
            <Tooltip content="Right" position="right"><button className="px-3 py-1 border rounded text-sm" style={{ borderColor: "var(--color-dep)" }}>Right</button></Tooltip>
        </div>
    ),
};
