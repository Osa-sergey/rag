import React, { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { ConfirmDialog } from "./ConfirmDialog";

const meta: Meta<typeof ConfirmDialog> = {
    title: "UI Kit/ConfirmDialog",
    component: ConfirmDialog,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj<typeof ConfirmDialog>;

const DialogWrapper = (args: any) => {
    const [open, setOpen] = useState(true);
    return (
        <>
            <button
                onClick={() => setOpen(true)}
                className="px-4 py-2 rounded-lg text-sm font-medium"
                style={{ background: args.intent === "destructive" ? "var(--color-error)" : "var(--color-info)", color: "#fff" }}
            >
                Open Dialog
            </button>
            <ConfirmDialog {...args} open={open} onClose={() => setOpen(false)} onConfirm={() => console.log("confirmed")} />
        </>
    );
};

export const DeleteStep: Story = {
    name: "🧩 Delete Step (B6)",
    render: () => (
        <DialogWrapper
            intent="destructive"
            title='Remove "parse_articles"?'
            description="This step and its configuration will be permanently deleted. Connected edges will be removed."
        />
    ),
};

export const DeleteConcept: Story = {
    name: "🧩 Delete Concept (L6)",
    render: () => (
        <DialogWrapper
            intent="destructive"
            title='Delete concept "Gradient Descent"?'
            description="This will permanently delete the concept, its version history, and all keyword associations. This action cannot be undone."
            confirmLabel="Delete Concept"
        />
    ),
};

export const OverwriteOutput: Story = {
    name: "Info — Overwrite Output",
    render: () => (
        <DialogWrapper
            intent="info"
            title="Overwrite existing output?"
            description='Step "build_concepts" already has output key "concepts". Re-running will replace the current data.'
            confirmLabel="Overwrite"
        />
    ),
};
