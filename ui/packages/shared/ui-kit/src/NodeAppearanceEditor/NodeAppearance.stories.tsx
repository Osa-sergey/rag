import React, { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { NodeAppearanceEditor, NodeAppearance } from "../NodeAppearanceEditor/NodeAppearanceEditor";
import { NodeTemplatePicker, NodeTemplate, defaultTemplates } from "../NodeTemplatePicker/NodeTemplatePicker";
import { LiveNodePreview } from "../LiveNodePreview/LiveNodePreview";
import { Plus, X } from "lucide-react";

const meta: Meta = {
    title: "DAG Builder/Step Style Registry",
    parameters: { layout: "centered" },
    decorators: [
        (Story) => (
            <div className="p-6 rounded-xl flex gap-6 h-full bg-[var(--bg-canvas)] min-w-[960px]">
                <Story />
            </div>
        ),
    ],
};

export default meta;
type Story = StoryObj;

// ═══════════════════════════════════════════════
// Types: each type has a name and a base style
// ═══════════════════════════════════════════════
interface StepType {
    id: string;
    name: string;
    style: NodeAppearance;
}

const INITIAL_TYPES: StepType[] = [
    { id: "extract", name: "Extract", style: { color: "var(--color-info)", icon: "database" } },
    { id: "transform", name: "Transform", style: { color: "#22c55e", icon: "git-branch" } },
    { id: "ml", name: "ML", style: { color: "var(--color-concept)", icon: "zap" } },
    { id: "deploy", name: "Deploy", style: { color: "var(--color-warning)", icon: "globe" } },
    { id: "notify", name: "Notify", style: { color: "var(--color-stale)", icon: "zap" } },
];

// ═══════════════════════════════════════════════
// Modules: each module may have a type and an optional override
// ═══════════════════════════════════════════════
interface ModuleEntry {
    module: string;
    label: string;
    typeId?: string;           // assigned type
    styleOverride?: NodeAppearance; // per-module override (if differs from type base)
}

const INITIAL_MODULES: ModuleEntry[] = [
    { module: "extract.hubspot", label: "HubSpot API", typeId: "extract", styleOverride: { color: "var(--color-info)", icon: "globe" } },
    { module: "extract.postgres", label: "Postgres Query", typeId: "extract" },
    { module: "transform.merge", label: "Merge Sources", typeId: "transform" },
    { module: "transform.clean", label: "Clean & Validate", typeId: "transform", styleOverride: { color: "#22c55e", icon: "shield" } },
    { module: "transform.features", label: "Feature Engineering", typeId: "transform" },
    { module: "ml.train", label: "Train Model", typeId: "ml" },
    { module: "ml.evaluate", label: "Evaluate Model", typeId: "ml", styleOverride: { color: "var(--color-concept)", icon: "file-text" } },
    { module: "deploy.registry", label: "Push Registry", typeId: "deploy", styleOverride: { color: "var(--color-warning)", icon: "database" } },
    { module: "deploy.k8s", label: "Deploy K8s", typeId: "deploy" },
    { module: "notify.slack", label: "Slack Alert", typeId: "notify" },
    // Unstyled modules — no type assigned
    { module: "article_parser.run", label: "Article Parser" },
    { module: "keyword_extractor.run", label: "Keyword Extractor" },
    { module: "sentiment.analyze", label: "Sentiment Analyzer" },
    { module: "cache.invalidate", label: "Cache Invalidator" },
];

export const StepStyleRegistry: Story = {
    name: "🎨 Step Style Registry",
    render: () => {
        const [types, setTypes] = useState<StepType[]>(INITIAL_TYPES);
        const [modules, setModules] = useState<ModuleEntry[]>(INITIAL_MODULES);
        const [selectedModule, setSelectedModule] = useState<string>("extract.hubspot");
        const [tab, setTab] = useState<"template" | "custom">("template");
        const [selectedTemplateId, setSelectedTemplateId] = useState<string | undefined>();
        const [templates, setTemplates] = useState<NodeTemplate[]>([...defaultTemplates]);
        const [templateName, setTemplateName] = useState("");
        const [newTypeName, setNewTypeName] = useState("");
        const [showNewType, setShowNewType] = useState(false);
        const [showAllTypes, setShowAllTypes] = useState(false);

        const currentMod = modules.find(m => m.module === selectedModule);
        const currentType = currentMod?.typeId ? types.find(t => t.id === currentMod.typeId) : undefined;
        const fallback: NodeAppearance = { color: "var(--text-muted)", icon: "database" };
        const resolvedStyle = currentMod?.styleOverride ?? currentType?.style ?? fallback;

        // Apply style to current module as an override
        const applyStyle = (app: NodeAppearance) => {
            setModules(prev => prev.map(m =>
                m.module === selectedModule ? { ...m, styleOverride: app } : m
            ));
        };

        // Assign type to current module
        const assignType = (typeId: string) => {
            setModules(prev => prev.map(m =>
                m.module === selectedModule ? { ...m, typeId, styleOverride: undefined } : m
            ));
        };

        // Reset module override → inherit from type
        const resetToType = () => {
            setModules(prev => prev.map(m =>
                m.module === selectedModule ? { ...m, styleOverride: undefined } : m
            ));
        };

        // Create new type
        const createType = () => {
            const name = newTypeName.trim();
            if (!name) return;
            const id = name.toLowerCase().replace(/\s+/g, "_");
            if (types.find(t => t.id === id)) return;
            const newType: StepType = { id, name, style: { ...resolvedStyle } };
            setTypes(prev => [...prev, newType]);
            // Assign the new type to the current module
            setModules(prev => prev.map(m =>
                m.module === selectedModule ? { ...m, typeId: id, styleOverride: undefined } : m
            ));
            setNewTypeName("");
            setShowNewType(false);
        };

        // Delete a type and unassign all its modules
        const deleteType = (typeId: string) => {
            setTypes(prev => prev.filter(t => t.id !== typeId));
            setModules(prev => prev.map(m =>
                m.typeId === typeId ? { ...m, typeId: undefined, styleOverride: undefined } : m
            ));
        };

        const handleTemplateSelect = (t: NodeTemplate) => {
            setSelectedTemplateId(t.id);
            applyStyle({ color: t.color, icon: t.icon });
        };

        const handleDeleteTemplate = (id: string) => {
            const idx = defaultTemplates.findIndex(t => t.id === id);
            if (idx !== -1) defaultTemplates.splice(idx, 1);
            setTemplates([...defaultTemplates]);
        };

        // Group modules: styled (have type) vs unstyled
        const styledModules = modules.filter(m => m.typeId);
        const unstyledModules = modules.filter(m => !m.typeId);
        const typeGroups = types.map(t => ({
            type: t,
            modules: styledModules.filter(m => m.typeId === t.id),
        })).filter(g => g.modules.length > 0);

        return (
            <div className="flex w-full gap-5">
                {/* ═══ LEFT: Module List ═══ */}
                <div className="w-[210px] flex flex-col gap-1 overflow-y-auto max-h-[560px] pr-1">
                    <div className="text-[9px] font-bold uppercase tracking-widest mb-1 px-2" style={{ color: "var(--text-muted)" }}>
                        Pipeline Modules
                    </div>

                    {/* Unstyled modules — shown first */}
                    {unstyledModules.length > 0 && (
                        <div className="mb-2 pb-2 border-b border-[var(--border-node)]">
                            <div className="text-[8px] font-bold uppercase tracking-widest px-2 py-1" style={{ color: "var(--color-error)" }}>
                                ⚠ No Type Assigned
                            </div>
                            {unstyledModules.map(m => {
                                const isActive = m.module === selectedModule;
                                return (
                                    <div key={m.module} onClick={() => setSelectedModule(m.module)}
                                        className="flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-all"
                                        style={{
                                            background: isActive ? "color-mix(in srgb, var(--color-error) 8%, var(--bg-node))" : "transparent",
                                            border: isActive ? "1px solid rgba(239,68,68,0.3)" : "1px solid transparent",
                                        }}>
                                        <span className="w-2.5 h-2.5 rounded-full flex-shrink-0 border border-dashed"
                                            style={{ borderColor: "var(--text-muted)" }} />
                                        <div className="flex flex-col min-w-0">
                                            <span className="text-[10px] font-semibold truncate" style={{ color: "var(--text-primary)" }}>{m.label}</span>
                                            <span className="text-[8px] font-mono truncate" style={{ color: "var(--text-muted)" }}>{m.module}</span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}

                    {/* Styled modules by type */}
                    {typeGroups.map(({ type, modules: mods }) => (
                        <div key={type.id} className="mb-1.5">
                            <div className="text-[8px] font-bold uppercase tracking-widest px-2 py-1"
                                style={{ color: type.style.color }}>
                                {type.name}
                            </div>
                            {mods.map(m => {
                                const s = m.styleOverride ?? type.style;
                                const isActive = m.module === selectedModule;
                                return (
                                    <div key={m.module} onClick={() => setSelectedModule(m.module)}
                                        className="flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-all"
                                        style={{
                                            background: isActive ? "color-mix(in srgb, var(--color-info) 12%, var(--bg-node))" : "transparent",
                                            border: isActive ? "1px solid rgba(99,102,241,0.3)" : "1px solid transparent",
                                        }}>
                                        <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: s.color }} />
                                        <div className="flex flex-col min-w-0">
                                            <span className="text-[10px] font-semibold truncate" style={{ color: "var(--text-primary)" }}>{m.label}</span>
                                            <span className="text-[8px] font-mono truncate" style={{ color: "var(--text-muted)" }}>{m.module}</span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    ))}
                </div>

                {/* ═══ CENTER: Style Editor ═══ */}
                <div className="w-[350px] flex flex-col gap-3 border-l border-r border-[var(--border-node)] px-5">
                    {/* Module header */}
                    <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-md"
                            style={{ background: "var(--bg-node)", color: "var(--text-primary)", border: "1px solid rgba(255,255,255,0.08)" }}>
                            {selectedModule}
                        </span>
                    </div>

                    {/* Type selector */}
                    <div className="flex flex-col gap-1.5">
                        <span className="text-[9px] font-bold uppercase tracking-widest px-1" style={{ color: "var(--text-muted)" }}>
                            Module Type
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                            {(() => {
                                const MAX_VISIBLE = 3;
                                const visibleTypes = showAllTypes ? types : types.filter((t, i) => i < MAX_VISIBLE || t.id === currentMod?.typeId);
                                const hiddenCount = types.length - visibleTypes.length;
                                return (
                                    <>
                                        {visibleTypes.map(t => {
                                            const isActive = currentMod?.typeId === t.id;
                                            return (
                                                <div key={t.id} className="group/type relative inline-flex">
                                                    <button onClick={() => assignType(t.id)}
                                                        className="px-2.5 py-1 rounded-md text-[9px] font-bold transition-all"
                                                        style={{
                                                            background: isActive ? t.style.color : "var(--bg-node)",
                                                            color: isActive ? "#fff" : "var(--text-secondary)",
                                                            border: isActive ? "none" : "1px solid rgba(255,255,255,0.08)",
                                                        }}>
                                                        {t.name}
                                                    </button>
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); deleteType(t.id); }}
                                                        className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full flex items-center justify-center opacity-0 group-hover/type:opacity-100 transition-opacity"
                                                        style={{ background: "var(--color-error)", color: "#fff" }}
                                                        title={`Delete type ${t.name}`}
                                                    >
                                                        <X size={8} />
                                                    </button>
                                                </div>
                                            );
                                        })}
                                        {types.length > MAX_VISIBLE && (
                                            <button
                                                onClick={() => setShowAllTypes(prev => !prev)}
                                                className="px-2 py-1 rounded-md text-[9px] font-medium transition-all hover:bg-white/5"
                                                style={{ color: "var(--color-info)", border: "1px dashed rgba(99,102,241,0.3)" }}>
                                                {showAllTypes ? "▴ Less" : `▾ ${hiddenCount} more`}
                                            </button>
                                        )}
                                    </>
                                );
                            })()}
                            {!showNewType ? (
                                <button onClick={() => setShowNewType(true)}
                                    className="px-2 py-1 rounded-md text-[9px] font-bold transition-all hover:bg-white/5 flex items-center gap-1"
                                    style={{ border: "1px dashed rgba(255,255,255,0.15)", color: "var(--text-muted)" }}>
                                    <Plus size={10} /> New
                                </button>
                            ) : (
                                <div className="flex items-center gap-1">
                                    <input type="text" value={newTypeName} onChange={e => setNewTypeName(e.target.value)}
                                        onKeyDown={e => e.key === "Enter" && createType()}
                                        placeholder="Type name…" autoFocus
                                        className="px-2 py-1 rounded-md text-[9px] font-medium outline-none w-[80px]"
                                        style={{ background: "var(--bg-node)", border: "1px solid var(--color-info)", color: "var(--text-primary)" }}
                                    />
                                    <button onClick={createType} className="text-[9px] font-bold px-1.5 py-1 rounded-md"
                                        style={{ background: "var(--color-info)", color: "#fff" }}>OK</button>
                                    <button onClick={() => { setShowNewType(false); setNewTypeName(""); }}
                                        className="p-0.5 rounded hover:bg-white/10" style={{ color: "var(--text-muted)" }}>
                                        <X size={10} />
                                    </button>
                                </div>
                            )}
                        </div>
                        {/* Reset to type button */}
                        {currentMod?.styleOverride && currentType && (
                            <button onClick={resetToType}
                                className="text-[9px] font-medium px-2 py-1 rounded-md transition-all hover:bg-white/5 self-start"
                                style={{ color: "var(--color-info)", border: "1px solid rgba(99,102,241,0.2)" }}>
                                ↺ Reset to {currentType.name} base style
                            </button>
                        )}
                    </div>

                    {/* Tab switcher — BLUE active */}
                    <div className="flex bg-[var(--bg-node)] rounded-lg p-1 border border-[var(--border-node)] shadow-sm">
                        <button
                            className={`flex-1 py-1.5 text-xs font-bold rounded-md transition-colors`}
                            style={{
                                background: tab === "template" ? "var(--color-info)" : "transparent",
                                color: tab === "template" ? "#fff" : "var(--text-muted)",
                            }}
                            onClick={() => setTab("template")}
                        >
                            Templates
                        </button>
                        <button
                            className={`flex-1 py-1.5 text-xs font-bold rounded-md transition-colors`}
                            style={{
                                background: tab === "custom" ? "var(--color-info)" : "transparent",
                                color: tab === "custom" ? "#fff" : "var(--text-muted)",
                            }}
                            onClick={() => setTab("custom")}
                        >
                            Custom
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto max-h-[340px] pr-1">
                        {tab === "template" ? (
                            <NodeTemplatePicker templates={templates} selectedId={selectedTemplateId}
                                onSelect={handleTemplateSelect} onDelete={handleDeleteTemplate} />
                        ) : (
                            <div className="flex flex-col gap-4">
                                <NodeAppearanceEditor value={resolvedStyle} onChange={applyStyle} />
                                <div className="flex flex-col gap-2 pt-3 border-t border-[var(--border-node)]">
                                    <input type="text" value={templateName} onChange={e => setTemplateName(e.target.value)}
                                        placeholder="Template name…"
                                        className="w-full px-3 py-2 rounded-lg text-[10px] font-medium outline-none"
                                        style={{ background: "var(--bg-node)", border: "1px solid rgba(255,255,255,0.1)", color: "var(--text-primary)" }}
                                    />
                                    <button onClick={() => {
                                        const name = templateName.trim() || `Custom ${templates.length + 1}`;
                                        const color = resolvedStyle.color;
                                        let hexColor = color;
                                        if (color.startsWith("var(")) {
                                            const varName = color.replace(/var\((.+)\)/, "$1").trim();
                                            const resolved = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
                                            if (resolved) hexColor = resolved;
                                        }
                                        const newT: NodeTemplate = {
                                            id: `custom_${Date.now()}`, name,
                                            description: `${resolvedStyle.icon}\n${hexColor}`,
                                            color: resolvedStyle.color, icon: resolvedStyle.icon,
                                        };
                                        defaultTemplates.push(newT);
                                        setTemplates([...defaultTemplates]);
                                        setTemplateName("");
                                    }}
                                        className="w-full py-2 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all hover:bg-white/5"
                                        style={{ border: "1px solid rgba(255,255,255,0.1)", color: "var(--text-secondary)" }}>
                                        💾 Save as Template
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* ═══ RIGHT: Preview ═══ */}
                <div className="flex-1 flex flex-col items-center justify-start gap-4 min-w-[200px] pt-2">
                    <div className="text-[9px] font-bold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                        Live Preview
                    </div>
                    <LiveNodePreview appearance={resolvedStyle}
                        label={currentMod?.label ?? selectedModule}
                        description={selectedModule} />

                    {currentType && (
                        <div className="text-[9px] px-2 py-1 rounded-md" style={{
                            background: `color-mix(in srgb, ${currentType.style.color} 10%, transparent)`,
                            color: currentType.style.color,
                        }}>
                            Type: {currentType.name}
                            {currentMod?.styleOverride && " (overridden)"}
                        </div>
                    )}
                    {!currentType && (
                        <div className="text-[9px] px-2 py-1 rounded-md" style={{
                            background: "rgba(239,68,68,0.08)", color: "var(--color-error)",
                        }}>
                            No type assigned
                        </div>
                    )}

                    {/* Mini grid of all modules */}
                    <div className="mt-3 pt-3 border-t border-[var(--border-node)] w-full">
                        <div className="text-[8px] font-bold uppercase tracking-widest mb-2 text-center" style={{ color: "var(--text-muted)" }}>
                            All Modules
                        </div>
                        <div className="grid grid-cols-2 gap-1">
                            {modules.map(m => {
                                const mType = m.typeId ? types.find(t => t.id === m.typeId) : undefined;
                                const s = m.styleOverride ?? mType?.style;
                                return (
                                    <div key={m.module} onClick={() => setSelectedModule(m.module)}
                                        className="flex items-center gap-1.5 px-2 py-1 rounded-md cursor-pointer transition-all hover:bg-white/5"
                                        style={{ background: m.module === selectedModule ? "rgba(99,102,241,0.08)" : undefined }}>
                                        {s ? (
                                            <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: s.color }} />
                                        ) : (
                                            <span className="w-2 h-2 rounded-full flex-shrink-0 border border-dashed" style={{ borderColor: "var(--text-muted)" }} />
                                        )}
                                        <span className="text-[8px] font-mono truncate" style={{ color: s ? "var(--text-secondary)" : "var(--text-muted)" }}>
                                            {m.module}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </div >
        );
    },
};
