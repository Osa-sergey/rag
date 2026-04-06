import React, { useState } from "react";
import { Settings, Layers, Bell, Box, ArrowRightLeft } from "lucide-react";
import { Popover } from "../Popover";
import { NodeAppearanceEditor, type NodeAppearance } from "../NodeAppearanceEditor/NodeAppearanceEditor";
import { NodeTemplatePicker, type NodeTemplate, defaultTemplates } from "../NodeTemplatePicker/NodeTemplatePicker";
import { LiveNodePreview } from "../LiveNodePreview/LiveNodePreview";
import { YamlPanel } from "../YamlPanel/YamlPanel";
import { ContextInspector } from "../ContextInspector/ContextInspector";

export type InspectorTab = "config" | "io" | "callbacks" | "context" | "appearance";

export interface InspectorField {
    key: string;
    value: string;
    type?: string;
    source?: string;
}

export interface InspectorPanelProps {
    /** Step name */
    stepName: string;
    /** Module path */
    module?: string;
    /** Active tab */
    activeTab?: InspectorTab;
    /** Config fields */
    configFields?: InspectorField[];
    /** Input fields */
    inputFields?: Array<{ key: string; type: string; description?: React.ReactNode }>;
    /** Output fields */
    outputFields?: Array<{ key: string; type: string; description?: React.ReactNode }>;
    /** Callbacks */
    callbacks?: Array<{ type: string; name?: string; params?: string | unknown[] }>;
    /** Context provides/requires */
    /** Context provides/requires */
    context?: { provides?: string[]; requires?: string[] };
    /** Node appearance override */
    appearance?: NodeAppearance;
    /** On appearance change */
    onAppearanceChange?: (app: NodeAppearance) => void;
    /** On tab change */
    onTabChange?: (tab: InspectorTab) => void;
    /** On context select */
    onContextSelect?: (contextName: string) => void;
}

const tabs: Array<{ id: InspectorTab; label: string; icon: React.ReactNode }> = [
    { id: "config", label: "Config", icon: <Settings size={12} /> },
    { id: "io", label: "I/O", icon: <ArrowRightLeft size={12} /> },
    { id: "callbacks", label: "Callbacks", icon: <Bell size={12} /> },
    { id: "context", label: "Context", icon: <Layers size={12} /> },
    { id: "appearance", label: "Style", icon: <Box size={12} /> },
];

export function InspectorPanel({
    stepName,
    module,
    activeTab: controlledTab,
    configFields = [],
    inputFields = [],
    outputFields = [],
    callbacks = [],
    context,
    appearance,
    onAppearanceChange,
    onTabChange,
    onContextSelect,
}: InspectorPanelProps) {
    const [internalTab, setInternalTab] = useState<InspectorTab>("config");
    const currentTab = controlledTab ?? internalTab;

    const [templateAppearance, setTemplateAppearance] = useState<NodeAppearance | undefined>(appearance);
    const [customAppearance, setCustomAppearance] = useState<NodeAppearance | undefined>(appearance);
    const [templates, setTemplates] = useState<NodeTemplate[]>(defaultTemplates);
    const [templateName, setTemplateName] = useState("");

    const handleDeleteTemplate = (id: string) => {
        const idx = defaultTemplates.findIndex(t => t.id === id);
        if (idx !== -1) defaultTemplates.splice(idx, 1);
        setTemplates([...defaultTemplates]);
    };

    React.useEffect(() => {
        setTemplateAppearance(appearance);
        setCustomAppearance(appearance);
    }, [appearance]);

    const handleTab = (tab: InspectorTab) => {
        setInternalTab(tab);
        onTabChange?.(tab);
    };

    return (
        <div
            className="rounded-xl overflow-hidden flex flex-col h-full"
            style={{ background: "var(--bg-panel)", border: "var(--border-node)", width: "100%" }}
        >
            {/* Header */}
            <div className="px-4 py-2.5" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <div className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>{stepName}</div>
                {module && <div className="text-[9px] font-mono mt-0.5" style={{ color: "var(--text-muted)" }}>{module}</div>}
            </div>

            {/* Tabs */}
            <div className="flex flex-wrap" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => handleTab(tab.id)}
                        className="flex items-center justify-center gap-1.5 flex-1 px-2 py-2.5 text-[10px] font-medium transition-colors"
                        style={{
                            color: currentTab === tab.id ? "var(--color-info)" : "var(--text-muted)",
                            borderBottom: currentTab === tab.id ? "2px solid var(--color-info)" : "2px solid transparent",
                        }}
                    >
                        {tab.icon} {tab.label}
                    </button>
                ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-3">
                {currentTab === "config" && (
                    <div className="flex flex-col gap-1">
                        {configFields.map((f) => (
                            <div key={f.key} className="flex items-center gap-2 py-1.5" style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                                <span className="text-[10px] font-mono w-[40%] truncate" style={{ color: "var(--text-secondary)" }}>{f.key}</span>
                                <span className="text-[10px] flex-1 truncate" style={{ color: "var(--text-primary)" }}>{f.value}</span>
                                {f.source && (
                                    <span className="text-[8px] font-bold px-1 py-0.5 rounded flex-shrink-0"
                                        style={{
                                            background: f.source === "DEF" ? "rgba(99,102,241,0.1)" : f.source === "GLB" ? "rgba(245,158,11,0.1)" : "rgba(34,197,94,0.1)",
                                            color: f.source === "DEF" ? "var(--color-info)" : f.source === "GLB" ? "var(--color-warning)" : "var(--color-success)",
                                        }}
                                    >{f.source}</span>
                                )}
                            </div>
                        ))}
                        {configFields.length === 0 && <div className="text-xs text-center py-4" style={{ color: "var(--text-muted)" }}>No config fields</div>}
                    </div>
                )}

                {currentTab === "io" && (
                    <div className="flex flex-col gap-4">
                        <div className="flex flex-col gap-1">
                            <div className="text-[9px] font-semibold uppercase tracking-wider mb-1" style={{ color: "var(--text-muted)" }}>Inputs</div>
                            {inputFields.map((f) => {
                                const typePill = <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${f.description ? "cursor-help underline underline-offset-2 decoration-dashed decoration-white/20" : ""}`} style={{ background: "var(--bg-node-hover)", color: "var(--text-muted)" }}>{f.type}</span>;
                                return (
                                    <div key={f.key} className="flex items-center gap-2 py-1.5" style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                                        <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: "var(--color-info)" }} />
                                        <span className="text-[10px] font-mono flex-1" style={{ color: "var(--text-primary)" }}>{f.key}</span>
                                        {f.description ? (
                                            <Popover trigger="hover" placement="left" width="auto" maxWidth={420} draggable content={
                                                typeof f.description === "string" ? (
                                                    <div className="rounded-xl overflow-hidden" style={{ width: 320, height: 220 }}>
                                                        <div className="w-full h-full overflow-auto">
                                                            <YamlPanel
                                                                title={`${f.type} Schema`}
                                                                content={f.description}
                                                            />
                                                        </div>
                                                    </div>
                                                ) : (
                                                    <div className="p-3 text-[10px] whitespace-pre text-left font-mono" style={{ color: "var(--text-secondary)" }}>
                                                        {f.description}
                                                    </div>
                                                )
                                            }>
                                                {typePill}
                                            </Popover>
                                        ) : typePill}
                                    </div>
                                )
                            })}
                            {inputFields.length === 0 && <div className="text-[10px] py-1 italic" style={{ color: "var(--text-muted)" }}>No bounded inputs.</div>}
                        </div>

                        <div className="flex flex-col gap-1">
                            <div className="text-[9px] font-semibold uppercase tracking-wider mb-1" style={{ color: "var(--text-muted)" }}>Outputs</div>
                            {outputFields.map((f) => {
                                const typePill = <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${f.description ? "cursor-help underline underline-offset-2 decoration-dashed decoration-white/20" : ""}`} style={{ background: "var(--bg-node-hover)", color: "var(--text-muted)" }}>{f.type}</span>;
                                return (
                                    <div key={f.key} className="flex items-center gap-2 py-1.5" style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                                        <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: "var(--color-success)" }} />
                                        <span className="text-[10px] font-mono flex-1" style={{ color: "var(--text-primary)" }}>{f.key}</span>
                                        {f.description ? (
                                            <Popover trigger="hover" placement="left" width="auto" draggable content={
                                                typeof f.description === "string" ? (
                                                    <div className="rounded-xl overflow-hidden" style={{ width: 320, height: 220 }}>
                                                        <div className="w-full h-full overflow-auto">
                                                            <YamlPanel
                                                                title={`${f.type} Schema`}
                                                                content={f.description}
                                                            />
                                                        </div>
                                                    </div>
                                                ) : (
                                                    <div className="p-3 text-[10px] whitespace-pre text-left font-mono" style={{ color: "var(--text-secondary)" }}>
                                                        {f.description}
                                                    </div>
                                                )
                                            }>
                                                {typePill}
                                            </Popover>
                                        ) : typePill}
                                    </div>
                                )
                            })}
                            {outputFields.length === 0 && <div className="text-[10px] py-1 italic" style={{ color: "var(--text-muted)" }}>No bounded outputs.</div>}
                        </div>
                    </div>
                )}

                {currentTab === "callbacks" && (
                    <div className="flex flex-col gap-4">
                        {callbacks.length === 0 && <div className="text-xs text-center py-4" style={{ color: "var(--text-muted)" }}>No callbacks</div>}
                        {Object.entries(
                            callbacks.reduce((acc, cb) => {
                                const groupName = cb.type || "Other";
                                if (!acc[groupName]) acc[groupName] = [];
                                acc[groupName].push(cb);
                                return acc;
                            }, {} as Record<string, typeof callbacks>)
                        ).map(([groupName, groupCallbacks]) => (
                            <div key={groupName} className="flex flex-col gap-1">
                                <div className="text-[9px] font-semibold uppercase tracking-wider mb-1" style={{ color: "var(--text-muted)" }}>
                                    {groupName}
                                </div>
                                {groupCallbacks.map((cb, i) => {
                                    const paramsDisplay = cb.params == null
                                        ? null
                                        : typeof cb.params === "string"
                                            ? cb.params
                                            : Array.isArray(cb.params)
                                                ? (cb.params as Array<{ key: string; default: unknown }>).map(p => `${p.key}=${p.default}`).join(", ")
                                                : String(cb.params);
                                    const displayName = cb.name || cb.type;
                                    return (
                                        <div key={i} className="flex items-center gap-2 py-1.5 px-2 rounded-lg" style={{ background: "var(--bg-node)" }}>
                                            <span className="text-[10px] font-mono font-semibold" style={{ color: "var(--text-primary)" }}>{displayName}</span>
                                            {paramsDisplay && <span className="text-[9px] ml-auto" style={{ color: "var(--text-muted)" }}>{paramsDisplay}</span>}
                                        </div>
                                    );
                                })}
                            </div>
                        ))}
                    </div>
                )}

                {currentTab === "context" && (() => {
                    const hasRequires = context?.requires && context.requires.length > 0;
                    const hasProvides = context?.provides && context.provides.length > 0;
                    if (!hasRequires && !hasProvides) return <ContextInspector />;

                    const renderContextPill = (c: string, type: 'require' | 'provide') => (
                        <div key={c}
                            onClick={() => onContextSelect?.(c)}
                            className="text-[10px] py-1 flex items-center gap-1 cursor-pointer hover:bg-white/5 px-2 rounded -mx-2 transition-colors"
                            style={{ color: type === 'require' ? "var(--color-info)" : "var(--color-success)" }}>
                            {type === 'require' ? "📥 " : "📤 "}{c}
                        </div>
                    );

                    return (
                        <div className="flex flex-col gap-4">
                            {hasRequires && (
                                <div>
                                    <div className="text-[9px] font-semibold uppercase tracking-wider mb-1" style={{ color: "var(--text-muted)" }}>Requires</div>
                                    <div className="flex flex-col gap-0.5">
                                        {context.requires!.map(c => renderContextPill(c, 'require'))}
                                    </div>
                                </div>
                            )}
                            {hasProvides && (
                                <div>
                                    <div className="text-[9px] font-semibold uppercase tracking-wider mb-1" style={{ color: "var(--text-muted)" }}>Provides</div>
                                    <div className="flex flex-col gap-0.5">
                                        {context.provides!.map(c => renderContextPill(c, 'provide'))}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })()}

                {currentTab === "appearance" && (
                    <div className="flex flex-col gap-6 p-2 pb-8">
                        {/* --- TOP SECTION --- */}
                        <div className="flex flex-col gap-3">
                            <span className="text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-widest px-1 mb-1">
                                Template Style
                            </span>

                            <div className="flex flex-col items-center w-full max-w-[280px] mx-auto scale-[0.95] origin-top mb-1">
                                <LiveNodePreview appearance={templateAppearance} label={stepName} description={module} />
                            </div>

                            <NodeTemplatePicker
                                templates={templates}
                                onSelect={(t) => setTemplateAppearance({ color: t.color, icon: t.icon })}
                                onDelete={handleDeleteTemplate}
                            />

                            <button
                                onClick={() => {
                                    if (templateAppearance) onAppearanceChange?.(templateAppearance);
                                }}
                                className="w-full py-2 rounded-lg text-xs font-semibold transition-all hover:opacity-90 mt-1"
                                style={{
                                    background: "linear-gradient(135deg, var(--color-info), color-mix(in srgb, var(--color-info) 70%, var(--color-success)))",
                                    color: "#fff",
                                    boxShadow: "0 2px 8px rgba(99,102,241,0.2)",
                                }}
                            >
                                ✓ Apply Template
                            </button>
                        </div>

                        <div className="w-full h-px bg-[var(--border-node)] shadow-sm" />

                        {/* --- BOTTOM SECTION --- */}
                        <div className="flex flex-col gap-3">
                            <span className="text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-widest px-1">
                                Custom Builder
                            </span>
                            <NodeAppearanceEditor
                                value={customAppearance}
                                onChange={(app) => setCustomAppearance(app)}
                            />

                            <div className="flex flex-col items-center w-full max-w-[280px] mx-auto scale-[0.95] origin-bottom mt-2">
                                <LiveNodePreview appearance={customAppearance} label={stepName} description={module} />
                            </div>

                            <div className="flex flex-col gap-2 mt-2 pt-4 border-t border-[var(--border-node)]">
                                {/* Template name input */}
                                <input
                                    type="text"
                                    value={templateName}
                                    onChange={(e) => setTemplateName(e.target.value)}
                                    placeholder="Template name…"
                                    className="w-full px-3 py-2 rounded-lg text-[10px] font-medium outline-none transition-colors"
                                    style={{
                                        background: "var(--bg-node)",
                                        border: "1px solid rgba(255,255,255,0.1)",
                                        color: "var(--text-primary)",
                                    }}
                                />
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => {
                                            if (customAppearance) {
                                                const name = templateName.trim() || `Custom ${templates.length + 1}`;
                                                const newT: NodeTemplate = {
                                                    id: `custom_${Date.now()}`,
                                                    name,
                                                    description: `${customAppearance.icon} • ${customAppearance.color}`,
                                                    color: customAppearance.color,
                                                    icon: customAppearance.icon
                                                };
                                                defaultTemplates.push(newT);
                                                setTemplates([...defaultTemplates]);
                                                setTemplateAppearance(customAppearance);
                                                setTemplateName("");
                                            }
                                        }}
                                        className="flex-1 py-2.5 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all hover:bg-white/5"
                                        style={{ border: "1px solid rgba(255,255,255,0.1)", color: "var(--text-secondary)" }}
                                    >
                                        💾 Save Template
                                    </button>
                                    <button
                                        onClick={() => {
                                            if (customAppearance) onAppearanceChange?.(customAppearance);
                                        }}
                                        className="flex-1 py-2.5 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all hover:opacity-90"
                                        style={{
                                            background: "var(--color-info)",
                                            color: "#fff",
                                        }}
                                    >
                                        🎨 Apply Custom
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
