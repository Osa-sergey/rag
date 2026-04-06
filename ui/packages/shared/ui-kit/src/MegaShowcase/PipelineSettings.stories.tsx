import type { Meta } from "@storybook/react";
import { useState, useMemo } from "react";
import { AppShell } from "../AppShell/AppShell";
import { TopBar } from "../TopBar/TopBar";
import { FlowCanvas, FlowNode } from "../FlowCanvas/FlowCanvas";
import { StepNode } from "../StepNode/StepNode";
import { Modal } from "../Modal/Modal";
import { TabPanel } from "../TabPanel/TabPanel";
import { PipelineConfigPanel } from "../PipelineConfigPanel/PipelineConfigPanel";
import { DiffViewer } from "../DiffViewer/DiffViewer";
import { VersionTimeline } from "../VersionTimeline/VersionTimeline";
import { ConfirmDialog } from "../ConfirmDialog/ConfirmDialog";
import { Badge } from "../Badge/Badge";
import { DataTable } from "../DataTable/DataTable";
import { RAG_STEPS, RAG_EDGES, StepDef } from "./showcase-data";

const meta: Meta = {
    title: "Showcase/Pipeline Editor",
    parameters: { layout: "fullscreen" },
};
export default meta;

function stepToNode(step: StepDef, selectedId: string, onSelect: (id: string) => void): FlowNode {
    return {
        id: step.id, x: step.x, y: step.y,
        width: step.width ?? 200, height: step.height ?? 110,
        ports: [
            ...(step.inputs ?? []).map((inp, i, arr) => ({ id: inp.id, side: "left" as const, index: i, total: arr.length })),
            ...(step.outputs ?? []).map((out, i, arr) => ({ id: out.id, side: "right" as const, index: i, total: arr.length })),
        ],
        content: <StepNode name={step.name} module={step.module} status={step.status}
            inputs={step.inputs} outputs={step.outputs} callbacks={step.callbacks}
            context={step.context} tags={step.tags} errors={step.errors}
            selected={selectedId === step.id} onClick={() => onSelect(step.id)}
            compact={step.compact} />,
    };
}

// ═══════════════════════════════════════════════════════════════
// STORY 6: Pipeline Settings & Templates
// ═══════════════════════════════════════════════════════════════
const VERSION_HISTORY = [
    {
        id: "v3", version: "v3.0", date: "2026-04-01", author: "osa-sergey",
        description: "Upgrade executor to kubernetes, improve RAPTOR summarizer",
        changes: [
            { type: "modify" as const, field: "executor", oldValue: "celery", newValue: "kubernetes" },
            { type: "modify" as const, field: "steps.build_raptor.config.summarizer", oldValue: "gpt-3.5-turbo", newValue: "gpt-4o-mini" },
        ],
    },
    {
        id: "v2", version: "v2.1", date: "2026-03-28", author: "osa-sergey",
        description: "Add embedding and validation steps",
        changes: [
            { type: "add" as const, field: "steps.embed_vectors", newValue: "added" },
            { type: "add" as const, field: "steps.validate_output", newValue: "added" },
        ],
    },
    {
        id: "v1", version: "v1.0", date: "2026-03-15", author: "osa-sergey",
        description: "Initial pipeline creation",
        changes: [
            { type: "add" as const, field: "pipeline", newValue: "initial" },
        ],
    },
];

const DIFF_OLD = `executor: celery
concurrency: 8

steps:
  - name: build_raptor
    config:
      summarizer: gpt-3.5-turbo
      max_depth: 3`;

const DIFF_NEW = `executor: kubernetes
concurrency: 16

steps:
  - name: build_raptor
    config:
      summarizer: gpt-4o-mini
      max_depth: 4`;

const IMPACT_ROWS = [
    { id: "1", step: "build_raptor", param: "summarizer", before: "gpt-3.5-turbo", after: "gpt-4o-mini", impact: "🧠 Higher quality summaries" },
    { id: "2", step: "build_raptor", param: "max_depth", before: "3", after: "4", impact: "📈 +33% tree depth" },
    { id: "3", step: "(global)", param: "executor", before: "celery", after: "kubernetes", impact: "⚡ Auto-scaling pods" },
    { id: "4", step: "(global)", param: "concurrency", before: "8", after: "16", impact: "🚀 2× parallelism" },
];

export const PipelineSettings = {
    name: "⚙️ Pipeline Settings & Templates",
    render: function PipelineSettingsStory() {
        const [selectedStep, setSelectedStep] = useState("s_parse");
        const [showModal, setShowModal] = useState(true);
        const [activeTab, setActiveTab] = useState("config");
        const [showRollback, setShowRollback] = useState(false);

        const flowNodes = useMemo(() =>
            RAG_STEPS.map(s => stepToNode(s, selectedStep, setSelectedStep)),
            [selectedStep]);

        const configContent = (
            <div className="flex flex-col gap-6">
                <PipelineConfigPanel
                    value={{ retries: 3, concurrency: 16, timeout: 3600, catchup: false, executor: "kubernetes" }}
                    onSave={() => alert("Settings saved!")}
                />
                <div className="rounded-xl overflow-hidden" style={{ border: "var(--border-node)" }}>
                    <div className="px-4 py-2" style={{ background: "var(--bg-node)", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                        <span className="text-xs font-bold" style={{ color: "var(--text-primary)" }}>Impact Preview</span>
                    </div>
                    <DataTable
                        columns={[
                            { key: "step", header: "Step", width: "120px" },
                            { key: "param", header: "Parameter", width: "120px" },
                            { key: "before", header: "Before", width: "120px" },
                            { key: "after", header: "After", width: "120px" },
                            { key: "impact", header: "Impact", width: "180px" },
                        ]}
                        data={IMPACT_ROWS}
                        rowKey={(r) => r.id}
                    />
                </div>
            </div>
        );

        const versionsContent = (
            <VersionTimeline
                versions={VERSION_HISTORY}
                onRestore={() => setShowRollback(true)}
            />
        );

        const diffContent = (
            <DiffViewer
                title="v2.1 → v3.0"
                oldText={DIFF_OLD}
                newText={DIFF_NEW}
                oldLabel="v2.1"
                newLabel="v3.0"
            />
        );

        const tabs = [
            { id: "config", label: "⚙️ Global Config", content: configContent },
            { id: "versions", label: "📋 Version History", content: versionsContent },
            { id: "diff", label: "🔀 Diff Viewer", content: diffContent },
        ];

        return (
            <div className="w-screen h-screen">
                <AppShell
                    topBar={<TopBar title="raptor-indexing-pipeline — Settings"
                        breadcrumb={<div className="flex items-center gap-2 text-xs">
                            <Badge variant="info">v3.0</Badge>
                            <button onClick={() => setShowModal(true)}
                                className="px-2 py-1 rounded text-[10px] font-bold transition-colors hover:opacity-80"
                                style={{ background: "rgba(99,102,241,0.15)", color: "var(--color-info)" }}>
                                Open Settings
                            </button>
                        </div>}
                        showThemeToggle />}
                    canvas={
                        <div className="w-full h-full relative">
                            <FlowCanvas nodes={flowNodes} edges={RAG_EDGES}
                                onNodeClick={setSelectedStep} selectedNodeId={selectedStep}
                                showMinimap showControls background="dots" />
                        </div>
                    }
                />

                {/* Settings Modal */}
                <Modal open={showModal} title="Pipeline Settings" size="lg" onClose={() => setShowModal(false)}>
                    <TabPanel
                        tabs={tabs}
                        activeId={activeTab}
                        onChange={setActiveTab}
                    />
                </Modal>

                {/* Rollback confirmation */}
                <ConfirmDialog
                    open={showRollback}
                    title="Rollback Pipeline?"
                    description="This will revert the pipeline to v2.1, undoing all changes made in v3.0 including executor change and RAPTOR config updates."
                    confirmLabel="Rollback to v2.1"
                    intent="destructive"
                    onConfirm={() => { setShowRollback(false); alert("Rolled back to v2.1"); }}
                    onClose={() => setShowRollback(false)}
                />
            </div>
        );
    },
};
