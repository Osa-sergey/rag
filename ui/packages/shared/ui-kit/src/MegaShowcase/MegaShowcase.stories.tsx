import type { Meta } from "@storybook/react";
import { useState, useMemo, useCallback, useEffect } from "react";
import { Grid, Code, Check, LayoutTemplate } from "lucide-react";
import { AppShell } from "../AppShell/AppShell";
import { TopBar } from "../TopBar/TopBar";
import { NodePalette } from "../NodePalette/NodePalette";
import { GroupPalette } from "../GroupPalette/GroupPalette";
import { YamlPanel } from "../YamlPanel/YamlPanel";
import { ViewSwitcher } from "../ViewSwitcher/ViewSwitcher";
import { Badge } from "../Badge/Badge";
import { FlowCanvas, FlowNode, FlowEdge, ConnectionRequest, CanvasDropEvent } from "../FlowCanvas/FlowCanvas";
import { StepNode } from "../StepNode/StepNode";
import { PipelineToolbar } from "../PipelineToolbar/PipelineToolbar";
import { InspectorPanel } from "../InspectorPanel/InspectorPanel";
import { ValidationOverlay } from "../ValidationOverlay/ValidationOverlay";
import { ConfigForm } from "../ConfigForm/ConfigForm";
import { ProgressBar } from "../ProgressBar/ProgressBar";
import { Timeline } from "../Timeline/Timeline";
import { DataTable } from "../DataTable/DataTable";
import { CallbackPicker } from "../CallbackPicker/CallbackPicker";
import { ContextInspector } from "../ContextInspector/ContextInspector";
import {
    EdgeBadge, PALETTE_STEPS, PALETTE_GROUPS, RAG_STEPS, RAG_EDGES, INSPECTOR_DATA, StepDef,
} from "./showcase-data";

const meta: Meta = {
    title: "Showcase/Pipeline Editor",
    parameters: { layout: "fullscreen" },
};
export default meta;

// ═══════════════════════════════════════════════════════════════
// Step types with base styles
// ═══════════════════════════════════════════════════════════════
interface StepType { id: string; name: string; style: { color: string; icon: string } }
const STEP_TYPES: StepType[] = [
    { id: "etl", name: "ETL", style: { color: "var(--color-info)", icon: "database" } },
    { id: "ml", name: "ML", style: { color: "var(--color-concept)", icon: "zap" } },
    { id: "indexing", name: "Indexing", style: { color: "#22c55e", icon: "git-branch" } },
    { id: "validation", name: "Validation", style: { color: "var(--color-warning)", icon: "shield" } },
    { id: "notify", name: "Notify", style: { color: "var(--color-stale)", icon: "globe" } },
];

// ═══════════════════════════════════════════════════════════════
// Helper: build FlowNode from StepDef
// ═══════════════════════════════════════════════════════════════
function stepToFlowNode(
    step: StepDef,
    selectedStep: string,
    onSelect: (id: string) => void,
    positions: Record<string, { x: number; y: number }>,
    nodeView: "default" | "compact" | "minified" = "default"
): FlowNode {
    const x = positions[step.id]?.x ?? step.x;
    const y = positions[step.id]?.y ?? step.y;
    return {
        id: step.id,
        x, y,
        width: step.width ?? 200,
        height: step.height ?? 110,
        ports: [
            ...(step.inputs ?? []).map((inp, i, arr) => ({
                id: inp.id, side: "left" as const, index: i, total: arr.length, dataType: inp.type,
            })),
            ...(step.outputs ?? []).map((out, i, arr) => ({
                id: out.id, side: "right" as const, index: i, total: arr.length, dataType: out.type,
            })),
        ],
        content: (
            <StepNode
                name={step.name} module={step.module} status={step.status}
                inputs={step.inputs} outputs={step.outputs}
                callbacks={step.stepCallbacks?.filter((c: any) => c.enabled) ?? step.callbacks} context={step.context}
                tags={step.tags} errors={step.errors}
                selected={selectedStep === step.id}
                onClick={() => onSelect(step.id)}
                compact={nodeView === "compact" || step.compact}
                minified={nodeView === "minified"}
                appearance={step.appearance}
            />
        ),
    };
}

// ═══════════════════════════════════════════════════════════════
// YAML Editor Mock
// ═══════════════════════════════════════════════════════════════
const yamlMockData = `version: "3"
name: raptor-indexing-pipeline
description: "RAG Pipeline with dual vector index"
schedule: "0 0 * * *"

steps:
  parse_articles:
    module: article_parser.run
    inputs:
      documents: \${trigger.event.files}
    outputs:
      chunks: \${self.chunks}
      
  clean_text:
    module: transform.clean
    inputs:
      chunks: \${parse_articles.chunks}
    outputs:
      clean: \${self.clean}
      
  embed_vectors:
    module: ml.embed
    inputs:
      clean: \${clean_text.clean}
    outputs:
      vectors: \${self.vectors}
      
  build_raptor:
    module: indexing.build_raptor
    inputs:
      vectors: \${embed_vectors.vectors}
    outputs:
      tree: \${self.tree}
`;

function YamlMockView() {
    return (
        <div className="w-full h-full p-4 overflow-auto" style={{ background: "var(--bg-canvas)" }}>
            <YamlPanel content={yamlMockData} className="h-full" />
        </div>
    );
}

// ═══════════════════════════════════════════════════════════════
// STORY 1: Main Canvas — Assembly workspace
// ═══════════════════════════════════════════════════════════════
export const MainCanvas = {
    name: "🎯 Main Canvas: Assembly",
    render: function MainCanvasStory() {
        const [viewMode, setViewMode] = useState<"canvas" | "yaml" | "monitor">("canvas");
        const [nodeView, setNodeView] = useState<"default" | "compact" | "minified">("default");
        const [selectedStep, setSelectedStep] = useState<string>("s_raptor");
        const [activeTab, setActiveTab] = useState<any>("config");
        const [selectedContext, setSelectedContext] = useState<string | null>(null);
        const [steps, setSteps] = useState<StepDef[]>(() => {
            const cbRegistry = [
                { id: "on_retry", name: "Retry on Failure", type: "Recovery", description: "Automatically retries step execution on exception.", hasParams: true, params: [{ key: "max_retries", label: "Max Retries", default: "3", type: "number" as const }, { key: "delay", label: "Delay (s)", default: "5", type: "number" as const }, { key: "backoff", label: "Exponential Backoff", default: "true", type: "boolean" as const }] },
                { id: "on_success", name: "On Success", type: "Lifecycle", description: "Trigger after successful completion.", hasParams: true, params: [{ key: "notify", label: "Notify", default: "true", type: "boolean" as const }, { key: "channel", label: "Channel", default: "#pipeline-ok", type: "string" as const }] },
                { id: "on_failure", name: "On Failure", type: "Lifecycle", description: "Trigger on step failure.", hasParams: true, params: [{ key: "notify", label: "Notify", default: "true", type: "boolean" as const }, { key: "channel", label: "Channel", default: "#pipeline-alerts", type: "string" as const }] },
                { id: "on_alert", name: "Slack Alert", type: "Notifications", description: "Sends a notification to a Slack channel.", hasParams: true, params: [{ key: "channel", label: "Channel", default: "#alerts", type: "string" as const }, { key: "mention", label: "Mention @oncall", default: "false", type: "boolean" as const }] },
                { id: "on_timeout", name: "Timeout Guard", type: "Recovery", description: "Trigger when step exceeds time limit.", hasParams: true, params: [{ key: "timeout_s", label: "Timeout (s)", default: "300", type: "number" as const }] },
                { id: "on_skip", name: "Skip Handler", type: "Lifecycle", description: "Trigger when step is skipped.", hasParams: false },
                { id: "on_data_quality", name: "Data Quality Check", type: "Validation", description: "Run data quality checks on output.", hasParams: true, params: [{ key: "min_rows", label: "Min Rows", default: "1", type: "number" as const }, { key: "max_null_pct", label: "Max Null %", default: "5", type: "number" as const }] },
            ];

            return RAG_STEPS.map(s => {
                let step = s;
                if (!step.appearance) {
                    const t = STEP_TYPES.find(st => st.id === step.typeId);
                    if (t) step = { ...step, appearance: t.style };
                }

                // Convert legacy callbacks array from showcase-data to new stepCallbacks property
                if (step.callbacks && !step.stepCallbacks) {
                    const mappedCbs = step.callbacks.map(c => {
                        const reg = cbRegistry.find(r => r.id === c.type);
                        if (!reg) return null;

                        // Try to extract some params if they were present as a string like "max=3"
                        const paramValues: Record<string, string> = {};
                        if (c.params && typeof c.params === 'string') {
                            const pairs = c.params.split(',').map(pair => pair.trim().split('='));
                            pairs.forEach(([k, v]) => {
                                if (k && v && reg.params?.find(p => p.key === k || p.label === k || k.includes(p.key.split('_')[0]))) {
                                    // fuzzy matching for demo data
                                    const matchedKey = reg.params.find(p => p.key === k || p.label === k || k.includes(p.key.split('_')[0]))?.key;
                                    if (matchedKey) paramValues[matchedKey] = v;
                                }
                            });
                        }
                        return { ...reg, enabled: true, paramValues };
                    }).filter(Boolean);
                    step = { ...step, stepCallbacks: mappedCbs };
                }
                return step;
            });
        });
        const [customEdges, setCustomEdges] = useState<FlowEdge[]>(RAG_EDGES);
        const [paletteSearch, setPaletteSearch] = useState("");
        const [groupSearch, setGroupSearch] = useState("");
        const [dirty, setDirty] = useState(false);
        const [stepTypes] = useState<StepType[]>(STEP_TYPES);
        const [showAllTypes, setShowAllTypes] = useState(false);
        let nextId = steps.length;

        // ── Execution Monitor state ──
        const [currentIndex, setCurrentIndex] = useState(-1);
        const [isRunning, setIsRunning] = useState(false);
        const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());
        const [failedSteps, setFailedSteps] = useState<Set<string>>(new Set());
        const [logRows, setLogRows] = useState<Array<{ step: string; status: string; duration: string; time: string }>>([]);

        const execOrder = useMemo(() => steps.map(s => s.id), [steps]);

        const getStatus = useCallback((stepId: string): any => {
            if (failedSteps.has(stepId)) return "failed";
            if (completedSteps.has(stepId)) return "completed";
            if (isRunning && execOrder[currentIndex] === stepId) return "running";
            return "idle";
        }, [completedSteps, failedSteps, isRunning, currentIndex, execOrder]);

        const handleRun = useCallback(() => {
            setViewMode("monitor");
            setIsRunning(true);
            setCurrentIndex(0);
            setCompletedSteps(new Set());
            setFailedSteps(new Set());
            setLogRows([]);
        }, []);

        const handleStop = useCallback(() => {
            setIsRunning(false);
        }, []);

        const handleResetExec = useCallback(() => {
            setIsRunning(false);
            setCurrentIndex(-1);
            setCompletedSteps(new Set());
            setFailedSteps(new Set());
            setLogRows([]);
            setViewMode("canvas");
        }, []);

        useEffect(() => {
            if (!isRunning || currentIndex < 0 || currentIndex >= execOrder.length) return;
            const stepId = execOrder[currentIndex];
            const duration = 600; // Simulated latency
            const timer = setTimeout(() => {
                const now = new Date().toLocaleTimeString();
                setCompletedSteps(prev => new Set(prev).add(stepId));
                setLogRows(prev => [...prev, { step: stepId.replace("s_", ""), status: "✅ ok", duration: `${duration}ms`, time: now }]);
                if (currentIndex < execOrder.length - 1) {
                    setCurrentIndex(currentIndex + 1);
                } else {
                    setIsRunning(false);
                }
            }, duration);
            return () => clearTimeout(timer);
        }, [isRunning, currentIndex, execOrder]);


        // ── Edit mode state ──
        const [editing, setEditing] = useState(false);
        const [editValues, setEditValues] = useState<Record<string, Record<string, string>>>({});
        const [savedValues, setSavedValues] = useState<Record<string, Record<string, string>>>({});

        const handleDrag = useCallback((id: string, x: number, y: number) => {
            setSteps(prev => prev.map(s => s.id === id ? { ...s, x, y } : s));
            setDirty(true);
        }, []);

        const handleConnect = useCallback((conn: ConnectionRequest) => {
            const edgeId = `e_${conn.fromNodeId}_${conn.toNodeId}_${Date.now()}`;
            const fromStep = steps.find(s => s.id === conn.fromNodeId);
            const fromPort = fromStep?.outputs?.find(p => p.id === conn.fromPortId);
            setCustomEdges(prev => [...prev, {
                id: edgeId,
                from: conn.fromNodeId,
                to: conn.toNodeId,
                fromPort: conn.fromPortId,
                toPort: conn.toPortId,
                label: <EdgeBadge text={fromPort?.type ?? "data"} />,
            }]);
            setDirty(true);
        }, [steps]);

        const handleDrop = useCallback((evt: CanvasDropEvent) => {
            try {
                const data = JSON.parse(evt.data);
                const newId = `s_drop_${++nextId}_${Date.now()}`;
                setSteps(prev => [...prev, {
                    id: newId,
                    name: data.name ?? "New Step",
                    module: data.module ?? "unknown",
                    status: "idle" as const,
                    x: evt.x, y: evt.y,
                    tags: [data.category?.toLowerCase() ?? "custom"],
                    inputs: [{ id: "i1", label: "input", type: "any" }],
                    outputs: [{ id: "o1", label: "output", type: "any" }],
                    width: 200, height: 110,
                }]);
                setDirty(true);
            } catch { /* ignore invalid drops */ }
        }, []);

        const handleDelete = useCallback((nodeIds: string[], edgeIds: string[]) => {
            if (nodeIds.length > 0) {
                setSteps(prev => prev.filter(s => !nodeIds.includes(s.id)));
                setCustomEdges(prev => prev.filter(e => !nodeIds.includes(e.from) && !nodeIds.includes(e.to)));
            }
            if (edgeIds.length > 0) {
                setCustomEdges(prev => prev.filter(e => !edgeIds.includes(e.id)));
            }
            setDirty(true);
        }, []);

        const inspectorData = useMemo(() =>
            INSPECTOR_DATA[selectedStep] ?? { stepName: selectedStep, module: "—" },
            [selectedStep]);

        // ── Edit helpers ──
        const getOriginalValues = useCallback((stepId: string): Record<string, string> => {
            const data = INSPECTOR_DATA[stepId];
            if (!data?.configFields) return {};
            const vals: Record<string, string> = {};
            data.configFields.forEach(f => { vals[f.key] = f.value; });
            return vals;
        }, []);

        const getCurrentValues = useCallback((stepId: string): Record<string, string> => {
            if (editValues[stepId]) return editValues[stepId];
            return savedValues[stepId] ?? getOriginalValues(stepId);
        }, [editValues, savedValues, getOriginalValues]);

        const handleStartEdit = useCallback(() => {
            setEditing(true);
            if (!editValues[selectedStep]) {
                setEditValues(prev => ({
                    ...prev,
                    [selectedStep]: getCurrentValues(selectedStep),
                }));
            }
        }, [selectedStep, editValues, getCurrentValues]);

        const handleFieldChange = useCallback((_group: string, key: string, value: any) => {
            setEditValues(prev => ({
                ...prev,
                [selectedStep]: { ...(prev[selectedStep] ?? getCurrentValues(selectedStep)), [key]: String(value) },
            }));
        }, [selectedStep, getCurrentValues]);

        const handleSave = useCallback(() => {
            const current = editValues[selectedStep];
            if (current) {
                setSavedValues(prev => ({ ...prev, [selectedStep]: { ...current } }));
            }
            setEditing(false);
            setDirty(true);
        }, [selectedStep, editValues]);

        const handleReset = useCallback(() => {
            const saved = savedValues[selectedStep] ?? getOriginalValues(selectedStep);
            setEditValues(prev => ({ ...prev, [selectedStep]: { ...saved } }));
        }, [selectedStep, savedValues, getOriginalValues]);

        const handleCancelEdit = useCallback(() => {
            setEditValues(prev => {
                const next = { ...prev };
                delete next[selectedStep];
                return next;
            });
            setEditing(false);
        }, [selectedStep]);

        // ── Diff detection ──
        const currentVals = getCurrentValues(selectedStep);
        const baseVals = savedValues[selectedStep] ?? getOriginalValues(selectedStep);
        const modifiedKeys = useMemo(() => {
            const keys: string[] = [];
            Object.keys(currentVals).forEach(k => {
                if (currentVals[k] !== baseVals[k]) keys.push(k);
            });
            return keys;
        }, [currentVals, baseVals]);

        // ── Monitor tracking ──
        const progress = execOrder.length === 0 ? 0 : completedSteps.size / execOrder.length * 100;
        const timelineItems = useMemo(() =>
            execOrder.map((id, i) => ({
                id,
                title: id.replace("s_", ""),
                color: failedSteps.has(id) ? "var(--color-error)" : completedSteps.has(id) ? "var(--color-success)" : isRunning && currentIndex === i ? "var(--color-warning)" : "var(--color-info)",
                active: isRunning && currentIndex === i,
                date: logRows.find(r => r.step === id.replace("s_", ""))?.time,
            })), [completedSteps, failedSteps, currentIndex, isRunning, logRows, execOrder]);

        const flowNodes = useMemo(() =>
            steps.map(s => ({
                id: s.id, x: s.x, y: s.y,
                width: nodeView === "minified" ? 160 : nodeView === "compact" ? 140 : 200,
                height: nodeView === "minified" ? 34 : nodeView === "compact" ? 90 : 110,
                ports: [
                    ...(s.inputs ?? []).map((inp, i, arr) => ({ id: inp.id, side: "left" as const, index: i, total: arr.length })),
                    ...(s.outputs ?? []).map((out, i, arr) => ({ id: out.id, side: "right" as const, index: i, total: arr.length })),
                ],
                content: <StepNode name={s.name} module={s.module} status={(viewMode === "monitor" ? getStatus(s.id) : s.status) as any}
                    appearance={s.appearance}
                    inputs={s.inputs} outputs={s.outputs}
                    callbacks={s.stepCallbacks?.filter((c: any) => c.enabled) ?? s.callbacks}
                    context={s.context}
                    tags={s.tags}
                    compact={nodeView === "compact" || s.compact}
                    minified={nodeView === "minified"}
                    selected={selectedStep === s.id} onClick={() => setSelectedStep(s.id)} />,
            })),
            [steps, selectedStep, viewMode, getStatus, nodeView]);

        const flowEdges = useMemo(() => {
            if (viewMode !== "monitor") return customEdges;
            return customEdges.map(e => {
                const fromDone = completedSteps.has(e.from);
                const toDone = completedSteps.has(e.to);
                const isActive = fromDone && execOrder[currentIndex] === e.to;
                return { ...e, variant: isActive ? "animated" : (fromDone && toDone) ? "default" : "dependency" } as FlowEdge;
            });
        }, [customEdges, viewMode, completedSteps, execOrder, currentIndex]);

        // ConfigForm groups with diff badges
        const configGroups = useMemo(() => {
            const fields = inspectorData.configFields ?? [];
            return [{
                id: "main", title: "Parameters",
                fields: fields.map(f => ({
                    key: f.key,
                    label: f.key,
                    type: "string" as const,
                    value: currentVals[f.key] ?? f.value,
                    source: (f.source ?? "DEF") as any,
                    description: modifiedKeys.includes(f.key)
                        ? `⚡ Modified (was: ${baseVals[f.key] ?? f.value})`
                        : undefined,
                })),
            }];
        }, [inspectorData, currentVals, baseVals, modifiedKeys]);

        return (
            <div className="w-screen h-screen">
                <AppShell
                    topBar={
                        <TopBar title="raptor-indexing-pipeline"
                            breadcrumb={<div className="flex items-center gap-1.5 text-xs">
                                <span style={{ color: "var(--text-muted)" }}>Production</span>
                                <span style={{ color: "var(--text-muted)" }}>/</span>
                                <span style={{ color: "var(--text-primary)" }} className="font-medium">Pipelines</span>
                            </div>}
                            actions={
                                <div className="flex items-center gap-3">
                                    <ViewSwitcher
                                        options={[
                                            { id: "canvas", label: "Canvas", icon: "grid" },
                                            { id: "yaml", label: "YAML", icon: "code" },
                                        ]}
                                        value={viewMode}
                                        onChange={(v) => setViewMode(v as any)}
                                    />
                                    <Badge variant="info">v3.0</Badge>
                                </div>
                            }
                            showThemeToggle />
                    }
                    sidebar={
                        <div className="h-full overflow-y-auto p-2 flex flex-col gap-4">
                            <div className="flex-shrink-0">
                                <NodePalette
                                    steps={PALETTE_STEPS}
                                    grouped
                                    searchQuery={paletteSearch}
                                    onSearch={setPaletteSearch}
                                    onDragStart={(_step) => {
                                        // Native drag will carry data for onCanvasDrop
                                    }}
                                />
                            </div>
                            <div className="flex-shrink-0">
                                <GroupPalette
                                    groups={PALETTE_GROUPS}
                                    searchQuery={groupSearch}
                                    onSearch={setGroupSearch}
                                    onDragStart={(_group) => {
                                        // Handled via native drag / showcase mock
                                    }}
                                />
                            </div>
                        </div>
                    }
                    inspector={
                        viewMode === "monitor" ? (
                            <div className="flex flex-col gap-4 p-3">
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
                        ) : (
                            <div className="flex flex-col gap-2 p-2">
                                {/* Type selector */}
                                {(() => {
                                    const MAX_VISIBLE = 3;
                                    const sel = steps.find(s => s.id === selectedStep);
                                    // Always show the active type in the visible set
                                    const visibleTypes = showAllTypes ? stepTypes : stepTypes.filter((t, i) => i < MAX_VISIBLE || t.id === sel?.typeId);
                                    const hiddenCount = stepTypes.length - visibleTypes.length;
                                    return (
                                        <div className="rounded-xl overflow-hidden p-3" style={{ background: "var(--bg-panel)", border: "var(--border-node)" }}>
                                            <div className="text-[9px] font-bold uppercase tracking-widest mb-2" style={{ color: "var(--text-muted)" }}>Module Type</div>
                                            <div className="flex flex-wrap gap-1.5">
                                                {visibleTypes.map(t => {
                                                    const isActive = sel?.typeId === t.id;
                                                    return (
                                                        <button key={t.id}
                                                            onClick={() => {
                                                                setSteps(prev => prev.map(s =>
                                                                    s.id === selectedStep
                                                                        ? { ...s, typeId: t.id, appearance: t.style }
                                                                        : s
                                                                ));
                                                                setDirty(true);
                                                            }}
                                                            className="px-2.5 py-1 rounded-md text-[9px] font-bold transition-all"
                                                            style={{
                                                                background: isActive ? t.style.color : "var(--bg-node)",
                                                                color: isActive ? "#fff" : "var(--text-secondary)",
                                                                border: isActive ? "none" : "1px solid rgba(255,255,255,0.08)",
                                                            }}>
                                                            {t.name}
                                                        </button>
                                                    );
                                                })}
                                                {stepTypes.length > MAX_VISIBLE && (
                                                    <button
                                                        onClick={() => setShowAllTypes(prev => !prev)}
                                                        className="px-2 py-1 rounded-md text-[9px] font-medium transition-all hover:bg-white/5"
                                                        style={{ color: "var(--color-info)", border: "1px dashed rgba(99,102,241,0.3)" }}>
                                                        {showAllTypes ? "▴ Less" : `▾ ${hiddenCount} more`}
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })()}
                                {/* Read-only inspector summary */}
                                <InspectorPanel
                                    stepName={inspectorData.stepName}
                                    module={inspectorData.module}
                                    activeTab={activeTab}
                                    onTabChange={(tab) => {
                                        setActiveTab(tab);
                                        if (tab !== "context") setSelectedContext(null);
                                    }}
                                    configFields={inspectorData.configFields}
                                    inputFields={inspectorData.inputFields?.map(f => ({ ...f, description: f.description as any }))}
                                    outputFields={inspectorData.outputFields?.map(f => ({ ...f, description: f.description as any }))}
                                    callbacks={steps.find(s => s.id === selectedStep)?.stepCallbacks?.filter((c: any) => c.enabled) ?? steps.find(s => s.id === selectedStep)?.callbacks ?? inspectorData.callbacks}
                                    context={inspectorData.context}
                                    appearance={steps.find(s => s.id === selectedStep)?.appearance}
                                    onAppearanceChange={(app) => {
                                        setSteps(prev => prev.map(s => s.id === selectedStep ? { ...s, appearance: app } : s));
                                        setDirty(true);
                                    }}
                                    onContextSelect={setSelectedContext}
                                />
                                {/* Edit button / Edit panel / CallbackPicker */}
                                {activeTab === "context" && selectedContext ? (
                                    <div className="rounded-xl flex flex-col mt-2"
                                        style={{ border: "var(--border-node)", background: "var(--bg-panel)" }}>
                                        <div className="flex items-center justify-between px-3 py-2"
                                            style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", background: "var(--bg-node)" }}>
                                            <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-primary)" }}>
                                                Context Identity
                                            </span>
                                            <button onClick={() => setSelectedContext(null)}
                                                className="text-[10px] px-2 py-0.5 rounded hover:bg-white/5 transition-colors"
                                                style={{ color: "var(--text-muted)" }}>
                                                ✕ Close
                                            </button>
                                        </div>
                                        <div className="p-3">
                                            <ContextInspector
                                                contextName={selectedContext}
                                                fields={[
                                                    { name: "session_dir", type: "Path", description: "Directory where downloaded source HTML is temporarily stored." },
                                                    { name: "timeout_sec", type: "int", description: "Parsing timeout per page." },
                                                    { name: "parser_flags", type: "dict[str, bool]" },
                                                ]}
                                            />
                                        </div>
                                    </div>
                                ) : activeTab === "callbacks" ? (() => {
                                    const step = steps.find(s => s.id === selectedStep);
                                    const cbRegistry = [
                                        {
                                            id: "on_retry", name: "Retry on Failure", type: "Recovery", description: "Automatically retries step execution on exception.", hasParams: true,
                                            params: [{ key: "max_retries", label: "Max Retries", default: "3", type: "number" as const }, { key: "delay", label: "Delay (s)", default: "5", type: "number" as const }, { key: "backoff", label: "Exponential Backoff", default: "true", type: "boolean" as const }]
                                        },
                                        {
                                            id: "on_success", name: "On Success", type: "Lifecycle", description: "Trigger after successful completion.", hasParams: true,
                                            params: [{ key: "notify", label: "Notify", default: "true", type: "boolean" as const }, { key: "channel", label: "Channel", default: "#pipeline-ok", type: "string" as const }]
                                        },
                                        {
                                            id: "on_failure", name: "On Failure", type: "Lifecycle", description: "Trigger on step failure.", hasParams: true,
                                            params: [{ key: "notify", label: "Notify", default: "true", type: "boolean" as const }, { key: "channel", label: "Channel", default: "#pipeline-alerts", type: "string" as const }]
                                        },
                                        {
                                            id: "on_alert", name: "Slack Alert", type: "Notifications", description: "Sends a notification to a Slack channel.", hasParams: true,
                                            params: [{ key: "channel", label: "Channel", default: "#alerts", type: "string" as const }, { key: "mention", label: "Mention @oncall", default: "false", type: "boolean" as const }]
                                        },
                                        {
                                            id: "on_timeout", name: "Timeout Guard", type: "Recovery", description: "Trigger when step exceeds time limit.", hasParams: true,
                                            params: [{ key: "timeout_s", label: "Timeout (s)", default: "300", type: "number" as const }]
                                        },
                                        { id: "on_skip", name: "Skip Handler", type: "Lifecycle", description: "Trigger when step is skipped.", hasParams: false },
                                        {
                                            id: "on_data_quality", name: "Data Quality Check", type: "Validation", description: "Run data quality checks on output.", hasParams: true,
                                            params: [{ key: "min_rows", label: "Min Rows", default: "1", type: "number" as const }, { key: "max_null_pct", label: "Max Null %", default: "5", type: "number" as const }]
                                        },
                                    ];
                                    // Convert step callbacks to CallbackConfig format
                                    const cbConfigs = (step?.stepCallbacks ?? []) as any[];
                                    return (
                                        <CallbackPicker
                                            callbacks={cbConfigs}
                                            registry={cbRegistry}
                                            onAdd={(id) => {
                                                const reg = cbRegistry.find(r => r.id === id);
                                                if (!reg) return;
                                                setSteps(prev => prev.map(s =>
                                                    s.id === selectedStep
                                                        ? { ...s, stepCallbacks: [...((s as any).stepCallbacks ?? []), { ...reg, enabled: true }] as any }
                                                        : s
                                                ));
                                                setDirty(true);
                                            }}
                                            onRemove={(id) => {
                                                setSteps(prev => prev.map(s =>
                                                    s.id === selectedStep
                                                        ? { ...s, stepCallbacks: ((s as any).stepCallbacks ?? []).filter((c: any) => c.id !== id) } as any
                                                        : s
                                                ));
                                                setDirty(true);
                                            }}
                                            onToggle={(id, enabled) => {
                                                setSteps(prev => prev.map(s =>
                                                    s.id === selectedStep
                                                        ? { ...s, stepCallbacks: ((s as any).stepCallbacks ?? []).map((c: any) => c.id === id ? { ...c, enabled } : c) } as any
                                                        : s
                                                ));
                                                setDirty(true);
                                            }}
                                            onSaveParams={(id, values) => {
                                                setSteps(prev => prev.map(s =>
                                                    s.id === selectedStep
                                                        ? { ...s, stepCallbacks: ((s as any).stepCallbacks ?? []).map((c: any) => c.id === id ? { ...c, paramValues: values } : c) } as any
                                                        : s
                                                ));
                                                setDirty(true);
                                            }}
                                        />
                                    );
                                })() : activeTab === "config" && (!editing ? (
                                    <button
                                        onClick={handleStartEdit}
                                        className="w-full py-2 rounded-lg text-xs font-semibold transition-all hover:opacity-90"
                                        style={{
                                            background: "linear-gradient(135deg, var(--color-info), color-mix(in srgb, var(--color-info) 70%, var(--color-success)))",
                                            color: "#fff",
                                            boxShadow: "0 2px 8px rgba(99,102,241,0.3)",
                                        }}
                                    >
                                        ✏️ Edit Step Config
                                    </button>
                                ) : (
                                    <div className="rounded-xl overflow-hidden flex flex-col"
                                        style={{ border: "var(--border-node)", background: "var(--bg-panel)" }}>
                                        {/* Edit header */}
                                        <div className="flex items-center justify-between px-3 py-2"
                                            style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", background: "var(--bg-node)" }}>
                                            <div className="flex items-center gap-2">
                                                <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-primary)" }}>
                                                    Edit Config
                                                </span>
                                                {modifiedKeys.length > 0 && (
                                                    <Badge variant="warning">{modifiedKeys.length} changed</Badge>
                                                )}
                                            </div>
                                            <button onClick={handleCancelEdit}
                                                className="text-[10px] px-2 py-0.5 rounded hover:bg-white/5 transition-colors"
                                                style={{ color: "var(--text-muted)" }}>
                                                ✕ Close
                                            </button>
                                        </div>

                                        {/* Editable ConfigForm */}
                                        <div className="p-3">
                                            <ConfigForm
                                                groups={configGroups}
                                                onChange={handleFieldChange}
                                            />
                                        </div>

                                        {/* Modified fields summary */}
                                        {modifiedKeys.length > 0 && (
                                            <div className="px-3 pb-2">
                                                <div className="rounded-lg p-2 flex flex-col gap-1"
                                                    style={{ background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.15)" }}>
                                                    <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: "var(--color-warning)" }}>
                                                        Unsaved changes
                                                    </span>
                                                    {modifiedKeys.map(k => (
                                                        <div key={k} className="flex items-center gap-2 text-[10px]">
                                                            <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: "var(--color-warning)" }} />
                                                            <span className="font-mono font-medium" style={{ color: "var(--text-primary)" }}>{k}</span>
                                                            <span style={{ color: "var(--text-muted)" }}>
                                                                {baseVals[k]} → {currentVals[k]}
                                                            </span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Action buttons */}
                                        <div className="flex items-center gap-2 px-3 pb-3">
                                            <button onClick={handleReset}
                                                className="flex-1 py-1.5 rounded-lg text-[10px] font-semibold transition-colors hover:bg-white/5"
                                                style={{ border: "1px solid rgba(255,255,255,0.1)", color: "var(--text-secondary)" }}>
                                                ↩ Reset
                                            </button>
                                            <button onClick={handleSave}
                                                className="flex-1 py-1.5 rounded-lg text-[10px] font-semibold transition-colors"
                                                style={{
                                                    background: modifiedKeys.length > 0 ? "var(--color-success)" : "var(--bg-node-hover)",
                                                    color: modifiedKeys.length > 0 ? "#fff" : "var(--text-muted)",
                                                }}>
                                                💾 Save
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )
                    }
                    inspectorWidth={320}
                    bottomPanel={
                        <div className="p-2">
                            <ValidationOverlay errors={[
                                { id: "err1", message: "Context prerequisite: 'index_neo4j' requires RaptorContext", severity: "warning", nodeName: "index_neo4j" },
                            ]} onErrorClick={(err) => { if (err.nodeId) setSelectedStep(err.nodeId); }} />
                        </div>
                    }
                    bottomHeight={120}
                    canvas={
                        viewMode === "canvas" || viewMode === "monitor" ? (
                            <div className="w-full h-full relative">
                                <div className="absolute top-2 left-2 z-20 pointer-events-auto">
                                    <PipelineToolbar name="raptor-indexing"
                                        status={isRunning ? "running" : failedSteps.size > 0 ? "failed" : (completedSteps.size > 0 && completedSteps.size === execOrder.length) ? "completed" : "idle"}
                                        stepCount={steps.length} edgeCount={customEdges.length} dirty={dirty}
                                        onRun={handleRun} onStop={handleStop} onReset={handleResetExec}
                                    >
                                        <ViewSwitcher
                                            options={[
                                                { id: "default", label: "Default", icon: <LayoutTemplate size={14} /> },
                                                { id: "compact", label: "Compact", icon: <Grid size={14} /> },
                                                { id: "minified", label: "Minified", icon: <Code size={14} /> },
                                            ]}
                                            value={nodeView}
                                            onChange={(v) => setNodeView(v as any)}
                                            size="sm"
                                        />
                                    </PipelineToolbar>
                                </div>
                                <FlowCanvas
                                    nodes={flowNodes}
                                    edges={flowEdges}
                                    onNodeDrag={handleDrag}
                                    onConnect={handleConnect}
                                    onCanvasDrop={handleDrop}
                                    onDelete={handleDelete}
                                    onNodeClick={setSelectedStep}
                                    selectedNodeId={selectedStep}
                                    showMinimap showControls background="dots"
                                    reservedZones={[{ x: 0, y: 0, width: 560, height: 56 }]}
                                />
                            </div>
                        ) : (
                            <YamlMockView />
                        )
                    }
                />
            </div>
        );
    },
};
