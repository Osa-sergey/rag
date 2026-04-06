import type { Meta, StoryObj } from "@storybook/react";
import { ColorPicker } from "./ColorPicker";

const meta: Meta<typeof ColorPicker> = {
    title: "UI Kit/ColorPicker",
    component: ColorPicker,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj<typeof ColorPicker>;

export const DesignTokens: Story = {
    name: "🧩 Design Token Colors",
    args: {
        label: "Accent Color",
        value: "#6366f1",
    },
};

export const NodeAppearance: Story = {
    name: "🧩 Node Color (B11)",
    args: {
        label: "Step Node Color",
        value: "#3b82f6",
        palette: [
            "#3b82f6", "#6366f1", "#8b5cf6", "#a855f7",
            "#22c55e", "#10b981", "#f59e0b", "#ef4444",
            "#64748b", "#1e293b",
        ],
    },
};

export const CustomHex: Story = {
    name: "Custom Hex Input",
    args: {
        label: "Custom Color",
        allowCustom: true,
    },
};
