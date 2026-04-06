import React from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { Checkbox } from "./Checkbox";

const meta: Meta<typeof Checkbox> = {
    title: "UI Kit/Checkbox",
    component: Checkbox,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
    argTypes: {
        size: { control: "select", options: ["sm", "md"] },
        disabled: { control: "boolean" },
        indeterminate: { control: "boolean" },
    },
};

export default meta;
type Story = StoryObj<typeof Checkbox>;

export const Default: Story = {
    args: { label: "Include this keyword" },
};

export const Checked: Story = {
    args: { label: "Verified keyword", checked: true },
};

export const Indeterminate: Story = {
    name: "Indeterminate (Partial)",
    args: { label: "Select all keywords", indeterminate: true },
};

export const WithDescription: Story = {
    args: {
        label: "Auto-validate on save",
        description: "Run config validation before persisting changes",
        checked: true,
    },
};

export const SmallSize: Story = {
    args: { label: "Compact", size: "sm", checked: true },
};

export const Disabled: Story = {
    args: { label: "Locked by admin", disabled: true, checked: true },
};

export const KeywordReviewList: Story = {
    name: "🧩 Keyword Review List (L2)",
    render: () => {
        const [selected, setSelected] = React.useState<Record<string, boolean>>({
            "machine learning": true,
            "neural networks": true,
            "back-propagation": false,
            "gradient descent": false,
            "transfer learning": true,
        });

        const allChecked = Object.values(selected).every(Boolean);
        const someChecked = Object.values(selected).some(Boolean);

        return (
            <div className="flex flex-col gap-1 p-4 rounded-lg" style={{ background: "var(--bg-node)", border: "var(--border-node)", maxWidth: 340 }}>
                <h4 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>
                    Candidate Keywords
                </h4>
                <Checkbox
                    label="Select all"
                    checked={allChecked}
                    indeterminate={someChecked && !allChecked}
                    onChange={(v) => setSelected(Object.fromEntries(Object.keys(selected).map((k) => [k, v])))}
                />
                <div className="border-t my-1" style={{ borderColor: "var(--text-muted)", opacity: 0.2 }} />
                {Object.entries(selected).map(([kw, checked]) => (
                    <Checkbox
                        key={kw}
                        label={kw}
                        checked={checked}
                        size="sm"
                        onChange={(v) => setSelected((s) => ({ ...s, [kw]: v }))}
                    />
                ))}
            </div>
        );
    },
};
