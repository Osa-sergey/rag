import type { Meta } from "@storybook/react";
import { useState, useMemo, useEffect, useCallback } from "react";
import { AppShell } from "../AppShell/AppShell";
import { TopBar } from "../TopBar/TopBar";
import { FlowCanvas, FlowNode } from "../FlowCanvas/FlowCanvas";
import { StepNode, StepStatus } from "../StepNode/StepNode";
import { PipelineToolbar } from "../PipelineToolbar/PipelineToolbar";
import { YamlPanel } from "../YamlPanel/YamlPanel";
import { ViewSwitcher } from "../ViewSwitcher/ViewSwitcher";
import { AlertBanner } from "../AlertBanner/AlertBanner";
import { Timeline } from "../Timeline/Timeline";
import { ProgressBar } from "../ProgressBar/ProgressBar";
import { DataTable } from "../DataTable/DataTable";
import { NodePalette } from "../NodePalette/NodePalette";
import { Badge } from "../Badge/Badge";
import { RAG_STEPS, RAG_EDGES, PALETTE_STEPS, PIPELINE_YAML, StepDef } from "./showcase-data";

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
            compact={(step as any).compact} />,
    };
}

// ═══════════════════════════════════════════════════════════════
// STORY 3: YAML Editor — bidirectional code view
// ═══════════════════════════════════════════════════════════════
export const YamlEditor = {
    name: "📝 YAML Editor",
    render: function YamlEditorStory() {
        const [view, setView] = useState("yaml");
        const [selectedStep, setSelectedStep] = useState("s_parse");

        const flowNodes = useMemo(() =>
            RAG_STEPS.map(s => stepToNode(s, selectedStep, setSelectedStep)),
            [selectedStep]);

        return (
            <div className="w-screen h-screen">
                <AppShell
                    topBar={
                        <TopBar title="raptor-indexing-pipeline"
                            breadcrumb={
                                <div className="flex items-center gap-3">
                                    <ViewSwitcher
                                        options={[
                                            { id: "canvas", label: "Canvas", icon: "grid" },
                                            { id: "yaml", label: "YAML", icon: "code" },
                                        ]}
                                        value={view}
                                        onChange={setView}
                                    />
                                    <Badge variant="info">v3.0</Badge>
                                </div>
                            }
                            showThemeToggle />
                    }
                    sidebar={
                        <div className="h-full flex flex-col">
                            <NodePalette steps={PALETTE_STEPS} grouped />
                        </div>
                    }
                    bottomPanel={
                        <div className="px-4 py-2">
                            <AlertBanner variant="info" message="Bidirectional sync: Changes in YAML → Graph and Graph → YAML (debounce 200ms)" />
                        </div>
                    }
                    bottomHeight={50}
                    canvas={
                        <div className="w-full h-full">
                            {view === "yaml" ? (
                                <div className="w-full h-full overflow-auto p-4">
                                    <YamlPanel content={PIPELINE_YAML} errorLines={[48, 49]} />
                                </div>
                            ) : (
                                <FlowCanvas nodes={flowNodes} edges={RAG_EDGES}
                                    onNodeClick={setSelectedStep} selectedNodeId={selectedStep}
                                    showMinimap showControls background="dots" />
                            )}
                        </div>
                    }
                />
            </div>
        );
    },
};

// ═══════════════════════════════════════════════════════════════
// STORY 5: Execution Monitor — animated status progression
// ═══════════════════════════════════════════════════════════════

const EXEC_ORDER = ["s_parse", "s_clean", "s_embed", "s_raptor", "s_qdrant", "s_neo4j", "s_validate", "s_alert"];
const EXEC_DURATIONS = [1200, 800, 1500, 2000, 1000, 1800, 600, 400];

export const ExecutionMonitor = {
    name: "▶️ Execution Monitor",
    render: function ExecutionMonitorStory() {
        const [currentIndex, setCurrentIndex] = useState(-1);
        const [isRunning, setIsRunning] = useState(false);
        const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());
        const [failedSteps, setFailedSteps] = useState<Set<string>>(new Set());
        const [selectedStep, setSelectedStep] = useState("s_parse");
        const [logRows, setLogRows] = useState<Array<{ step: string; status: string; duration: string; time: string }>>([]);

        const getStatus = useCallback((stepId: string): StepStatus => {
            if (failedSteps.has(stepId)) return "failed";
            if (completedSteps.has(stepId)) return "success";
            if (isRunning && EXEC_ORDER[currentIndex] === stepId) return "running";
            return "idle";
        }, [completedSteps, failedSteps, isRunning, currentIndex]);

        const handleRun = useCallback(() => {
            setIsRunning(true);
            setCurrentIndex(0);
            setCompletedSteps(new Set());
            setFailedSteps(new Set());
            setLogRows([]);
        }, []);

        const handleStop = useCallback(() => {
            setIsRunning(false);
        }, []);

        const handleReset = useCallback(() => {
            setIsRunning(false);
            setCurrentIndex(-1);
            setCompletedSteps(new Set());
            setFailedSteps(new Set());
            setLogRows([]);
        }, []);

        // Auto-advance execution
        useEffect(() => {
            if (!isRunning || currentIndex < 0 || currentIndex >= EXEC_ORDER.length) return;
            const stepId = EXEC_ORDER[currentIndex];
            const duration = EXEC_DURATIONS[currentIndex];
            const timer = setTimeout(() => {
                const now = new Date().toLocaleTimeString();
                // Simulate Neo4j failure
                if (stepId === "s_neo4j") {
                    setFailedSteps(prev => new Set(prev).add(stepId));
                    setLogRows(prev => [...prev, { step: stepId.replace("s_", ""), status: "❌ failed", duration: `${duration}ms`, time: now }]);
                    setIsRunning(false);
                    return;
                }
                setCompletedSteps(prev => new Set(prev).add(stepId));
                setLogRows(prev => [...prev, { step: stepId.replace("s_", ""), status: "✅ ok", duration: `${duration}ms`, time: now }]);
                if (currentIndex < EXEC_ORDER.length - 1) {
                    setCurrentIndex(currentIndex + 1);
                } else {
                    setIsRunning(false);
                }
            }, duration);
            return () => clearTimeout(timer);
        }, [isRunning, currentIndex]);

        const execSteps = useMemo(() =>
            RAG_STEPS.map(s => ({ ...s, status: getStatus(s.id) })),
            [getStatus]);

        const execEdges = useMemo(() =>
            RAG_EDGES.map(e => {
                const fromDone = completedSteps.has(e.from);
                const toDone = completedSteps.has(e.to);
                const isActive = fromDone && EXEC_ORDER[currentIndex] === e.to;
                return { ...e, variant: (isActive ? "animated" : fromDone && toDone ? "default" : "dependency") as any };
            }),
            [completedSteps, currentIndex]);

        const flowNodes = useMemo(() =>
            execSteps.map(s => stepToNode(s, selectedStep, setSelectedStep)),
            [execSteps, selectedStep]);

        const progress = completedSteps.size / EXEC_ORDER.length * 100;
        const pipelineStatus = isRunning ? "running" : failedSteps.size > 0 ? "failed" : completedSteps.size === EXEC_ORDER.length ? "success" : "idle";

        const timelineItems = useMemo(() =>
            EXEC_ORDER.map((id, i) => ({
                id,
                title: id.replace("s_", ""),
                color: failedSteps.has(id) ? "var(--color-error)" : completedSteps.has(id) ? "var(--color-success)" : isRunning && currentIndex === i ? "var(--color-warning)" : "var(--color-info)",
                active: isRunning && currentIndex === i,
                date: logRows.find(r => r.step === id.replace("s_", ""))?.time,
            })), [completedSteps, failedSteps, currentIndex, isRunning, logRows]);

        return (
            <div className="w-screen h-screen">
                <AppShell
                    topBar={<TopBar title="raptor-indexing — Execution"
                        breadcrumb={<div className="flex items-center gap-3 text-xs">
                            <Badge variant={pipelineStatus === "running" ? "info" : pipelineStatus === "failed" ? "error" : pipelineStatus === "success" ? "success" : "default"}>
                                {pipelineStatus.toUpperCase()}
                            </Badge>
                            {isRunning && <span style={{ color: "var(--text-muted)" }}>Step {currentIndex + 1}/{EXEC_ORDER.length}</span>}
                        </div>}
                        showThemeToggle />}
                    inspector={
                        <div className="h-full overflow-y-auto flex flex-col gap-4 p-3">
                            <div className="rounded-xl p-3" style={{ background: "var(--bg-panel)", border: "var(--border-node)" }}>
                                <div className="text-xs font-semibold mb-2" style={{ color: "var(--text-primary)" }}>Progress</div>
                                <ProgressBar value={progress} showPercent />

                            </div>
                            <div className="rounded-xl p-3" style={{ background: "var(--bg-panel)", border: "var(--border-node)" }}>
                                <div className="text-xs font-semibold mb-2" style={{ color: "var(--text-primary)" }}>Execution Order</div>
                                <Timeline items={timelineItems} />
                            </div>
                            {logRows.length > 0 && (
                                <div className="rounded-xl overflow-hidden" style={{ background: "var(--bg-panel)", border: "var(--border-node)" }}>
                                    <DataTable
                                        columns={[
                                            { key: "step", header: "Step", width: "100px" },
                                            { key: "status", header: "Status", width: "70px" },
                                            { key: "duration", header: "Duration", width: "70px" },
                                            { key: "time", header: "Time", width: "80px" },
                                        ]}
                                        data={logRows}
                                        rowKey={(r) => r.step + r.time}
                                    />
                                </div>
                            )}
                        </div>
                    }
                    bottomPanel={
                        <div className="p-2">
                            <PipelineToolbar name="raptor-indexing" status={pipelineStatus as any}
                                stepCount={RAG_STEPS.length} edgeCount={RAG_EDGES.length}
                                onRun={handleRun} onStop={handleStop} onReset={handleReset} />
                        </div>
                    }
                    bottomHeight={54}
                    canvas={
                        <div className="w-full h-full relative">
                            <FlowCanvas nodes={flowNodes} edges={execEdges}
                                onNodeClick={setSelectedStep} selectedNodeId={selectedStep}
                                showMinimap showControls background="dots" />
                        </div>
                    }
                />
            </div>
        );
    },
};
