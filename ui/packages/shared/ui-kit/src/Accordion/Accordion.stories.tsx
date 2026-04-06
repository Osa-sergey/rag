import React from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { Accordion } from "./Accordion";
import { Badge } from "../Badge";
import { StatusIcon } from "../StatusIcon";

const meta: Meta<typeof Accordion> = {
    title: "UI Kit/Accordion",
    component: Accordion,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
    argTypes: {
        multiple: { control: "boolean" },
    },
};

export default meta;
type Story = StoryObj<typeof Accordion>;

export const ConfigSections: Story = {
    name: "Step Config Sections",
    args: {
        defaultOpen: ["global"],
        items: [
            {
                id: "global",
                title: "Global Config",
                subtitle: "Applied to all steps",
                badge: <Badge variant="info" size="sm">4 fields</Badge>,
                content: (
                    <div className="font-mono text-xs space-y-1" style={{ color: "var(--text-secondary)" }}>
                        <div><span style={{ color: "var(--color-keyword)" }}>model_name</span>: "gpt-4o"</div>
                        <div><span style={{ color: "var(--color-keyword)" }}>temperature</span>: 0.1</div>
                        <div><span style={{ color: "var(--color-keyword)" }}>neo4j_uri</span>: "bolt://localhost:7687"</div>
                        <div><span style={{ color: "var(--color-keyword)" }}>qdrant_url</span>: "http://localhost:6333"</div>
                    </div>
                ),
            },
            {
                id: "step",
                title: "Step Override",
                subtitle: "raptor_pipeline.run",
                badge: <Badge variant="warning" size="sm">2 overrides</Badge>,
                content: (
                    <div className="font-mono text-xs space-y-1" style={{ color: "var(--text-secondary)" }}>
                        <div><span style={{ color: "var(--color-data)" }}>chunk_size</span>: 512 <span style={{ color: "var(--text-muted)" }}>← overrides default 256</span></div>
                        <div><span style={{ color: "var(--color-data)" }}>overlap</span>: 64 <span style={{ color: "var(--text-muted)" }}>← overrides default 32</span></div>
                    </div>
                ),
            },
            {
                id: "effective",
                title: "Effective Config",
                subtitle: "Merged result",
                badge: <StatusIcon status="success" size={8} />,
                content: (
                    <div className="text-xs" style={{ color: "var(--text-secondary)" }}>
                        The resolved config after merging global defaults → hydra defaults → step overrides.
                    </div>
                ),
            },
        ],
    },
};

export const Multiple: Story = {
    name: "Multiple Open",
    args: {
        multiple: true,
        defaultOpen: ["a", "c"],
        items: [
            { id: "a", title: "Section A", content: <div>Content A</div> },
            { id: "b", title: "Section B", content: <div>Content B</div> },
            { id: "c", title: "Section C", content: <div>Content C</div> },
        ],
    },
};

export const ConceptVersions: Story = {
    name: "Concept Version History",
    args: {
        items: [
            {
                id: "v3",
                title: "Version 3 (Current)",
                badge: <Badge variant="success" size="sm">active</Badge>,
                content: (
                    <div className="text-xs space-y-2" style={{ color: "var(--text-secondary)" }}>
                        <div>Expanded from 5 new articles covering distributed systems patterns.</div>
                        <div style={{ color: "var(--text-muted)" }}>Created: 2025-03-28</div>
                    </div>
                ),
            },
            {
                id: "v2",
                title: "Version 2",
                badge: <Badge variant="default" size="sm">inactive</Badge>,
                content: (
                    <div className="text-xs" style={{ color: "var(--text-secondary)" }}>
                        Initial expansion from core keyword set.
                    </div>
                ),
            },
            {
                id: "v1",
                title: "Version 1",
                badge: <Badge variant="default" size="sm">inactive</Badge>,
                content: (
                    <div className="text-xs" style={{ color: "var(--text-secondary)" }}>
                        Auto-created from article clustering.
                    </div>
                ),
            },
        ],
    },
};
