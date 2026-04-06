import type { Meta } from "@storybook/react";
import { useState, useMemo } from "react";
import { AppShell } from "../AppShell/AppShell";
import { TopBar } from "../TopBar/TopBar";
import { FlowCanvas, FlowNode } from "../FlowCanvas/FlowCanvas";
import { StepNode } from "../StepNode/StepNode";
import { InspectorPanel } from "../InspectorPanel/InspectorPanel";
import { ConfigForm } from "../ConfigForm/ConfigForm";
import { ValidationOverlay } from "../ValidationOverlay/ValidationOverlay";
import { EdgeBadge, RAG_STEPS, RAG_EDGES, INSPECTOR_DATA, StepDef, DEMO_ERRORS } from "./showcase-data";

const meta: Meta = {
    title: "Showcase/Pipeline Editor",
    parameters: { layout: "fullscreen" },
};
export default meta;

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════
function stepToFlowNode(step: StepDef, selectedStep: string, onSelect: (id: string) => void, positions: Record<string, { x: number; y: number }>): FlowNode {
    const x = positions[step.id]?.x ?? step.x;
    const y = positions[step.id]?.y ?? step.y;
    return {
        id: step.id, x, y,
        width: step.width ?? 200, height: step.height ?? 110,
        ports: [
            ...(step.inputs ?? []).map((inp, i, arr) => ({ id: inp.id, side: "left" as const, index: i, total: arr.length, dataType: inp.type })),
            ...(step.outputs ?? []).map((out, i, arr) => ({ id: out.id, side: "right" as const, index: i, total: arr.length, dataType: out.type })),
        ],
        content: <StepNode name={step.name} module={step.module} status={step.status}
            inputs={step.inputs} outputs={step.outputs} callbacks={step.callbacks}
            context={step.context} tags={step.tags} errors={step.errors}
            selected={selectedStep === step.id} onClick={() => onSelect(step.id)}
            compact={step.compact} />,
    };
}

// ═══════════════════════════════════════════════════════════════
// STORY 2: Step Inspector — deep config editing
// ═══════════════════════════════════════════════════════════════
export const StepInspector = {
    name: "⚙️ Step Inspector",
    render: function StepInspectorStory() {
        const [selectedStep, setSelectedStep] = useState("s_raptor");
        const [activeTab, setActiveTab] = useState<any>("config");
        const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});

        const flowNodes = useMemo(() =>
            RAG_STEPS.map(s => stepToFlowNode(s, selectedStep, setSelectedStep, positions)),
            [selectedStep, positions]);

        const inspectorData = useMemo(() =>
            INSPECTOR_DATA[selectedStep] ?? { stepName: selectedStep, module: "—" },
            [selectedStep]);

        const configGroups = useMemo(() => {
            const fields = inspectorData.configFields ?? [];
            return [{
                id: "main", title: "Parameters",
                fields: fields.map(f => ({
                    key: f.key, label: f.key, type: "string" as const,
                    value: f.value, source: (f.source ?? "DEF") as any,
                })),
            }];
        }, [inspectorData]);

        return (
            <div className="w-screen h-screen">
                <AppShell
                    topBar={<TopBar title="raptor-indexing-pipeline"
                        breadcrumb={<div className="flex items-center gap-1.5 text-xs">
                            <span style={{ color: "var(--text-muted)" }}>Pipeline</span>
                            <span style={{ color: "var(--text-muted)" }}>/</span>
                            <span style={{ color: "var(--text-muted)" }}>Steps</span>
                            <span style={{ color: "var(--text-muted)" }}>/</span>
                            <span style={{ color: "var(--text-primary)" }} className="font-medium">{inspectorData.stepName}</span>
                        </div>}
                        showThemeToggle />}
                    inspector={
                        <div className="h-full overflow-y-auto flex flex-col gap-4 p-2">
                            <InspectorPanel
                                stepName={inspectorData.stepName} module={inspectorData.module}
                                activeTab={activeTab} onTabChange={setActiveTab}
                                configFields={inspectorData.configFields}
                                inputFields={inspectorData.inputFields?.map(f => ({ ...f, description: f.description as any }))}
                                outputFields={inspectorData.outputFields?.map(f => ({ ...f, description: f.description as any }))}
                                callbacks={inspectorData.callbacks}
                                context={inspectorData.context}
                            />
                            {activeTab === "config" && (
                                <div className="rounded-xl p-3" style={{ background: "var(--bg-panel)", border: "var(--border-node)" }}>
                                    <ConfigForm groups={configGroups} />
                                </div>
                            )}
                        </div>
                    }
                    canvas={
                        <div className="w-full h-full relative">
                            <FlowCanvas nodes={flowNodes} edges={RAG_EDGES}
                                onNodeDrag={(id, x, y) => setPositions(p => ({ ...p, [id]: { x, y } }))}
                                onNodeClick={setSelectedStep} selectedNodeId={selectedStep}
                                showMinimap showControls background="dots" />
                        </div>
                    }
                />
            </div>
        );
    },
};

// ═══════════════════════════════════════════════════════════════
// STORY 4: Validation & Errors
// ═══════════════════════════════════════════════════════════════
export const ValidationPanel = {
    name: "🛡️ Validation & Errors",
    render: function ValidationStory() {
        const [selectedStep, setSelectedStep] = useState("s_embed");
        const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});

        // Add errors to specific steps
        const errorSteps = useMemo(() =>
            RAG_STEPS.map(s => {
                if (s.id === "s_embed") return { ...s, status: "failed" as const, errors: ["Output ref invalid: ${{ steps.train_model.embeddings }}"] };
                if (s.id === "s_qdrant") return { ...s, status: "failed" as const, errors: ["Type mismatch: 'str' → 'int'"] };
                if (s.id === "s_neo4j") return { ...s, errors: ["Missing context: RaptorContext"] };
                return s;
            }),
            []);

        // Error edges
        const errorEdges = useMemo(() =>
            RAG_EDGES.map(e => {
                if (e.from === "s_embed" || e.to === "s_qdrant") return { ...e, variant: "error" as const, label: <EdgeBadge text={e.id === "e4" ? "ndarray ≠ int" : "error"} variant="error" /> };
                return e;
            }),
            []);

        const flowNodes = useMemo(() =>
            errorSteps.map(s => stepToFlowNode(s, selectedStep, setSelectedStep, positions)),
            [errorSteps, selectedStep, positions]);

        return (
            <div className="w-screen h-screen">
                <AppShell
                    topBar={<TopBar title="raptor-indexing-pipeline — Validation"
                        breadcrumb={<div className="flex items-center gap-1.5 text-xs">
                            <span style={{ color: "var(--color-error)" }} className="font-bold">⚠ 4 issues found</span>
                        </div>}
                        showThemeToggle />}
                    bottomPanel={
                        <div className="p-2 flex gap-4">
                            <ValidationOverlay errors={DEMO_ERRORS}
                                onErrorClick={(err) => { if (err.nodeId) setSelectedStep(err.nodeId); }}
                                onRevalidate={() => alert("Re-validating...")} />
                            <div className="flex-1 flex items-center gap-3 px-3">
                                {["error", "warning"].map(sev => {
                                    const count = DEMO_ERRORS.filter(e => e.severity === sev).length;
                                    return (
                                        <span key={sev} className="text-[10px] font-bold px-2 py-1 rounded-full"
                                            style={{
                                                background: sev === "error" ? "rgba(239,68,68,0.1)" : "rgba(245,158,11,0.1)",
                                                color: sev === "error" ? "var(--color-error)" : "var(--color-warning)",
                                            }}>
                                            {count} {sev}{count > 1 ? "s" : ""}
                                        </span>
                                    );
                                })}
                            </div>
                        </div>
                    }
                    bottomHeight={80}
                    canvas={
                        <div className="w-full h-full relative">
                            <FlowCanvas nodes={flowNodes} edges={errorEdges}
                                onNodeDrag={(id, x, y) => setPositions(p => ({ ...p, [id]: { x, y } }))}
                                onNodeClick={setSelectedStep} selectedNodeId={selectedStep}
                                showMinimap showControls background="dots" />
                        </div>
                    }
                />
            </div>
        );
    },
};
