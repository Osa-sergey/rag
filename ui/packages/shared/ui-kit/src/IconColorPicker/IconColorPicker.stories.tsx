import React, { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { IconColorPicker } from "./IconColorPicker";

const meta: Meta<typeof IconColorPicker> = {
    title: "UI Kit/IconColorPicker",
    component: IconColorPicker,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
};

export default meta;
type Story = StoryObj<typeof IconColorPicker>;

const InteractiveDemo = ({ initIcon, initColor, initSaved }: { initIcon?: string; initColor?: string; initSaved?: string[] }) => {
    const [icon, setIcon] = useState(initIcon ?? "brain");
    const [color, setColor] = useState(initColor ?? "#6366f1");
    const [saved, setSaved] = useState(initSaved ?? []);
    return (
        <IconColorPicker
            selectedIcon={icon}
            selectedColor={color}
            onChange={(i, c) => { setIcon(i); setColor(c); }}
            savedColors={saved}
            onSavedColorsChange={setSaved}
            label="Node Appearance"
        />
    );
};

export const Default: Story = {
    name: "🧩 Default — Icon + Color Merged (B11)",
    render: () => <InteractiveDemo />,
};

export const WithSavedColors: Story = {
    name: "🧩 Saved Colors — Removable ×",
    render: () => <InteractiveDemo initIcon="database" initColor="#22c55e" initSaved={["#ef4444", "#3b82f6", "#a855f7", "#f59e0b"]} />,
};

export const CustomColor: Story = {
    name: "🧩 Custom Hex Input",
    render: () => <InteractiveDemo initIcon="zap" initColor="#ff6b35" />,
};

export const PresetIconColor: Story = {
    name: "Preset Icon + Color",
    args: {
        selectedIcon: "workflow",
        selectedColor: "#8b5cf6",
        label: "Step Icon",
        savedColors: ["#ef4444", "#22c55e"],
    },
};
