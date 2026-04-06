import React from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { InstanceOfEdge } from "./InstanceOfEdge";
import { CrossRelatedEdge } from "./CrossRelatedEdge";
import { EvolvedToEdge } from "./EvolvedToEdge";
import { ReferencesEdge } from "./ReferencesEdge";
import { HasKeywordEdge } from "./HasKeywordEdge";

const meta = {
    title: "Knowledge Base/Edges",
    parameters: {
        layout: "centered",
    },
    decorators: [
        (Story) => (
            <div className="p-12 rounded-xl" style={{ background: "var(--bg-canvas, #0a0a0f)" }}>
                <Story />
            </div>
        ),
    ],
} satisfies Meta;

export default meta;
type Story = StoryObj;

export const AllEdges: Story = {
    name: "🧩 All Edges Overview",
    render: () => (
        <div className="flex flex-col gap-8">
            <div>
                <h3 className="text-xs font-bold mb-4" style={{ color: "var(--text-secondary)" }}>1. InstanceOfEdge (Concept → Concept)</h3>
                <div className="flex items-center gap-8">
                    <div className="flex flex-col items-center gap-2">
                        <span className="text-[10px] text-gray-400">High Similarity (0.95)</span>
                        <InstanceOfEdge similarity={0.95} width={150} height={60} />
                    </div>
                    <div className="flex flex-col items-center gap-2">
                        <span className="text-[10px] text-gray-400">Medium Similarity (0.50)</span>
                        <InstanceOfEdge similarity={0.50} width={150} height={60} />
                    </div>
                    <div className="flex flex-col items-center gap-2">
                        <span className="text-[10px] text-gray-400">Low Similarity (0.20)</span>
                        <InstanceOfEdge similarity={0.20} width={150} height={60} />
                    </div>
                </div>
            </div>

            <div>
                <h3 className="text-xs font-bold mb-4" style={{ color: "var(--text-secondary)" }}>2. CrossRelatedEdge (Custom predicates)</h3>
                <div className="flex items-center gap-8">
                    <CrossRelatedEdge predicate="defines" confidence={0.98} width={200} height={60} />
                    <CrossRelatedEdge predicate="extends" width={200} height={60} />
                </div>
            </div>

            <div>
                <h3 className="text-xs font-bold mb-4" style={{ color: "var(--text-secondary)" }}>3. EvolvedToEdge (Version History)</h3>
                <div className="flex items-center gap-8">
                    <EvolvedToEdge fromVersion="v1 (1.0)" toVersion="v2 (1.1)" width={240} height={60} />
                    <EvolvedToEdge fromVersion="v2" toVersion="v3" isChain={true} width={240} height={60} />
                </div>
            </div>

            <div className="flex gap-16">
                <div>
                    <h3 className="text-xs font-bold mb-4" style={{ color: "var(--text-secondary)" }}>4. HasKeywordEdge</h3>
                    <div className="flex flex-col gap-4">
                        <HasKeywordEdge width={150} height={40} />
                        <HasKeywordEdge weight={0.65} width={150} height={40} />
                    </div>
                </div>
                <div>
                    <h3 className="text-xs font-bold mb-4" style={{ color: "var(--text-secondary)" }}>5. ReferencesEdge</h3>
                    <ReferencesEdge width={200} height={60} />
                </div>
            </div>
        </div>
    ),
};
