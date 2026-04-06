import React, { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { Modal } from "./Modal";

const meta: Meta<typeof Modal> = {
    title: "UI Kit/Modal",
    component: Modal,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
    argTypes: {
        size: { control: "select", options: ["sm", "md", "lg", "full"] },
    },
};

export default meta;
type Story = StoryObj<typeof Modal>;

const ModalWrapper = (args: any) => {
    const [open, setOpen] = useState(true);
    return (
        <>
            <button
                onClick={() => setOpen(true)}
                className="px-4 py-2 rounded-lg text-sm font-medium"
                style={{ background: "var(--color-info)", color: "var(--text-inverse)" }}
            >
                Open Modal
            </button>
            <Modal {...args} open={open} onClose={() => setOpen(false)} />
        </>
    );
};

export const Default: Story = {
    render: (args) => (
        <ModalWrapper
            {...args}
            title="Pipeline Configuration"
            footer={
                <div className="flex gap-2">
                    <button className="px-3 py-1.5 rounded-lg text-xs" style={{ color: "var(--text-muted)" }}>
                        Cancel
                    </button>
                    <button className="px-3 py-1.5 rounded-lg text-xs font-medium" style={{ background: "var(--color-info)", color: "var(--text-inverse)" }}>
                        Save
                    </button>
                </div>
            }
        >
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                Configure global pipeline settings. These settings will affect all steps in the pipeline.
            </p>
        </ModalWrapper>
    ),
};

export const Large: Story = {
    name: "Large (Config View)",
    render: () => (
        <ModalWrapper
            size="lg"
            title="Full Configuration Preview"
        >
            <pre
                className="text-xs font-mono p-4 rounded-lg overflow-auto"
                style={{ background: "var(--bg-node)", color: "var(--text-secondary)", maxHeight: 300 }}
            >
                {`pipeline:
  name: raptor_indexing
  steps:
    - name: parse_articles
      module: raptor.parse.ArticleParser
      config:
        max_length: 4096
        chunk_overlap: 128
    - name: build_tree
      module: raptor.tree.TreeBuilder
      config:
        levels: 4
        summarizer: gpt-4
    - name: index_vectors
      module: raptor.store.QdrantIndexer
      config:
        collection: raptor_v2
        vector_size: 1536`}
            </pre>
        </ModalWrapper>
    ),
};

export const SmallConfirmation: Story = {
    name: "Small (Confirmation)",
    render: () => (
        <ModalWrapper
            size="sm"
            title="Delete Pipeline?"
            footer={
                <div className="flex gap-2">
                    <button className="px-3 py-1.5 rounded-lg text-xs" style={{ color: "var(--text-muted)" }}>
                        Cancel
                    </button>
                    <button className="px-3 py-1.5 rounded-lg text-xs font-medium" style={{ background: "var(--color-error)", color: "#fff" }}>
                        Delete
                    </button>
                </div>
            }
        >
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                This will permanently delete <strong>"raptor_indexing"</strong> and all its step configurations. This action cannot be undone.
            </p>
        </ModalWrapper>
    ),
};

export const WithForm: Story = {
    name: "🧩 Create Step Wizard (B6, G2)",
    render: () => (
        <ModalWrapper
            size="md"
            title="Add New Step"
            footer={
                <div className="flex gap-2">
                    <button className="px-3 py-1.5 rounded-lg text-xs" style={{ color: "var(--text-muted)" }}>
                        Cancel
                    </button>
                    <button className="px-3 py-1.5 rounded-lg text-xs font-medium" style={{ background: "var(--color-info)", color: "var(--text-inverse)" }}>
                        Add Step
                    </button>
                </div>
            }
        >
            <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-1">
                    <label className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>Step Name</label>
                    <input className="px-3 py-2 rounded-lg text-sm" style={{ background: "var(--bg-node)", border: "var(--border-node)", color: "var(--text-primary)" }} placeholder="e.g. parse_articles" />
                </div>
                <div className="flex flex-col gap-1">
                    <label className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>Module Path</label>
                    <input className="px-3 py-2 rounded-lg text-sm font-mono" style={{ background: "var(--bg-node)", border: "var(--border-node)", color: "var(--text-primary)" }} placeholder="e.g. raptor.parse.ArticleParser" />
                </div>
                <div className="flex flex-col gap-1">
                    <label className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>Description</label>
                    <textarea className="px-3 py-2 rounded-lg text-sm" rows={3} style={{ background: "var(--bg-node)", border: "var(--border-node)", color: "var(--text-primary)" }} placeholder="What does this step do?" />
                </div>
            </div>
        </ModalWrapper>
    ),
};
