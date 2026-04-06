import React from "react";
import { RefreshCw, Bell, CheckCircle2, XCircle, LayoutTemplate } from "lucide-react";
import { iconMap } from "../IconPicker/IconPicker";
import { Popover } from "../Popover";
import { KeyValueList } from "../KeyValueList/KeyValueList";
import { ContextInspector } from "../ContextInspector/ContextInspector";

export type StepStatus = "idle" | "running" | "completed" | "failed";

export interface StepNodePort {
    id: string;
    label: string;
    type?: string;
}

export interface CallbackInfo {
    type?: "on_retry" | "on_success" | "on_failure" | "on_alert" | string;
    id?: string;
    name?: string;
    params?: string | any[];
    paramValues?: Record<string, string>;
}

export interface ContextInfo {
    provides?: string[];
    requires?: string[];
}

export interface StepNodeProps {
    /** Step name */
    name: string;
    /** Module path */
    module?: string;
    /** Current status */
    status?: StepStatus;
    /** Input ports */
    inputs?: StepNodePort[];
    /** Output ports */
    outputs?: StepNodePort[];
    /** Context info */
    context?: ContextInfo;
    /** Callbacks */
    callbacks?: CallbackInfo[];
    /** Tags */
    tags?: string[];
    /** Compact mode */
    compact?: boolean;
    /** Minified mode (header only) */
    minified?: boolean;
    /** Appearance override (color and icon) */
    appearance?: { color?: string; icon?: string };
    /** Selected */
    selected?: boolean;
    /** Validation errors */
    errors?: string[];
    /** On click */
    onClick?: () => void;
}

const statusStyles: Record<StepStatus, { glow: string; dot: string; anim?: string }> = {
    idle: { glow: "none", dot: "var(--text-muted)" },
    running: { glow: "0 0 16px rgba(99,102,241,0.3)", dot: "var(--color-info)", anim: "pulse 1.5s infinite" },
    completed: { glow: "0 0 16px rgba(34,197,94,0.25)", dot: "var(--color-success)" },
    failed: { glow: "0 0 16px rgba(239,68,68,0.25)", dot: "var(--color-error)" },
};

const callbackIcons: Record<string, React.ReactNode> = {
    on_retry: <RefreshCw size={9} />,
    on_success: <CheckCircle2 size={9} />,
    on_failure: <XCircle size={9} />,
    on_alert: <Bell size={9} />,
};

export function StepNode({
    name,
    module,
    status = "idle",
    inputs = [],
    outputs = [],
    context,
    callbacks = [],
    tags = [],
    compact = false,
    minified = false,
    appearance,
    selected = false,
    errors = [],
    onClick,
}: StepNodeProps) {
    const st = statusStyles[status] || statusStyles.idle;
    const hasErrors = errors.length > 0;
    const IconComponent = appearance?.icon ? (iconMap[appearance.icon] || iconMap["database"]) : null;

    return (
        <div
            className="rounded-xl transition-all cursor-pointer group"
            style={{
                width: minified ? 160 : compact ? 140 : 200,
                background: "var(--bg-node)",
                border: selected ? "1.5px solid var(--color-info)" : hasErrors ? "1.5px solid var(--color-error)" : "var(--border-node)",
                boxShadow: selected ? "0 0 20px rgba(99,102,241,0.2)" : st.glow,
            }}
            onClick={onClick}
        >
            {/* Top color strip if appearance color is given */}
            {appearance?.color && (
                <div className="h-1 w-full rounded-t-xl transition-colors" style={{ background: appearance.color }} />
            )}

            {/* Header */}
            <div
                className="flex items-center gap-2 px-3 py-2"
                style={{ borderBottom: minified ? "none" : "1px solid rgba(255,255,255,0.04)" }}
            >
                {/* Status dot */}
                <span
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ background: st.dot, animation: st.anim }}
                />

                {/* Custom Icon */}
                {IconComponent && (
                    <span className="flex items-center" style={{ color: appearance?.color || "var(--text-muted)" }}>
                        {React.cloneElement(IconComponent as React.ReactElement, { size: 12 })}
                    </span>
                )}

                {/* Name */}
                <span className="text-[11px] font-semibold truncate" style={{ color: "var(--text-primary)" }}>
                    {name}
                </span>

                {/* Callback icons */}
                {callbacks.length > 0 && (
                    <div className="flex items-center gap-0.5 ml-auto flex-shrink-0">
                        {callbacks.map((cb, idx) => {
                            const cbId = cb.id || cb.type || "";
                            const displayName = cb.name || cb.type || cbId;

                            // Get KV pairs either from new paramValues or by parsing old string params
                            let pairs: { key: string, value: string }[] = [];
                            if (cb.paramValues) {
                                pairs = Object.entries(cb.paramValues)
                                    .filter(([_, v]) => v) // skip empty
                                    .map(([k, v]) => ({ key: k, value: String(v) }));
                            } else if (typeof cb.params === "string") {
                                pairs = cb.params.split(',').map(s => {
                                    const [k, v] = s.split('=');
                                    return { key: k?.trim() || '', value: v?.trim() || '' };
                                }).filter(p => p.key);
                            } else if (Array.isArray(cb.params)) {
                                pairs = cb.params.map(p => ({
                                    key: p.label || p.key || '',
                                    value: String(cb.paramValues?.[p.key] ?? p.default ?? '')
                                })).filter(p => p.key);
                            }

                            const iconNode = (
                                <span key={`icon_${idx}`} style={{ color: "var(--text-muted)", cursor: pairs.length > 0 ? "help" : "default" }} title={pairs.length === 0 ? displayName : undefined}>
                                    {callbackIcons[cbId] || callbackIcons["on_success"]}
                                </span>
                            );

                            return pairs.length > 0 ? (
                                <Popover key={`pop_${idx}`} trigger="hover" placement="top" content={
                                    <div className="p-1 min-w-[140px]">
                                        <div className="text-[9px] font-bold tracking-wider px-2 pt-1 pb-1 uppercase"
                                            style={{ color: "var(--text-primary)" }}>
                                            {displayName}
                                        </div>
                                        <KeyValueList entries={pairs} />
                                    </div>
                                }>
                                    {iconNode}
                                </Popover>
                            ) : iconNode;
                        })}
                    </div>
                )}
            </div>

            {/* Return early in minified mode: no details shown */}
            {minified && (
                <>
                    {/* Render invisible anchor ports so edges still connect perfectly to left/right bounds */}
                    {inputs.map((p) => (
                        <div key={p.id} className="absolute top-1/2 left-0 w-[4px] h-[4px] opacity-0" data-port-id={p.id} data-port-side="left">
                            <span className="rounded-full w-full h-full block" />
                        </div>
                    ))}
                    {outputs.map((p) => (
                        <div key={p.id} className="absolute top-1/2 right-0 w-[4px] h-[4px] opacity-0" data-port-id={p.id} data-port-side="right">
                            <span className="rounded-full w-full h-full block" />
                        </div>
                    ))}
                </>
            )}
            {!minified && (
                <>
                    {/* Module path */}
                    {!compact && module && (
                        <div className="px-3 py-1">
                            <span className="text-[9px] font-mono truncate block" style={{ color: "var(--text-muted)" }}>
                                {module}
                            </span>
                        </div>
                    )}

                    {/* Tags */}
                    {!compact && tags.length > 0 && (
                        <div className="px-3 pb-1 flex flex-wrap gap-0.5">
                            {tags.map((tag) => (
                                <span key={tag} className="text-[8px] px-1 py-0.5 rounded" style={{ background: "var(--bg-node-hover)", color: "var(--text-muted)" }}>
                                    {tag}
                                </span>
                            ))}
                        </div>
                    )}

                    {/* Ports */}
                    {(inputs.length > 0 || outputs.length > 0) && (
                        <div className="flex justify-between px-2 py-1.5 gap-2">
                            {/* Inputs — blue dots flush left */}
                            <div className="flex flex-col gap-1">
                                {inputs.map((p) => (
                                    <div key={p.id} className="flex items-center gap-1.5" data-port-id={p.id} data-port-side="left">
                                        <span className="w-[6px] h-[6px] rounded-full flex-shrink-0 -ml-[11px]" style={{ background: "var(--color-info)", boxShadow: "0 0 6px rgba(99,102,241,0.5)" }} />
                                        <span className="text-[9px] font-mono" style={{ color: "var(--text-muted)" }}>{p.label}</span>
                                    </div>
                                ))}
                            </div>
                            {/* Outputs — green dots flush right */}
                            <div className="flex flex-col gap-1 items-end">
                                {outputs.map((p) => (
                                    <div key={p.id} className="flex items-center gap-1.5" data-port-id={p.id} data-port-side="right">
                                        <span className="text-[9px] font-mono" style={{ color: "var(--text-muted)" }}>{p.label}</span>
                                        <span className="w-[6px] h-[6px] rounded-full flex-shrink-0 -mr-[11px]" style={{ background: "var(--color-success)", boxShadow: "0 0 6px rgba(34,197,94,0.5)" }} />
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Context */}
                    {context && (context.provides?.length || context.requires?.length) && (() => {
                        const mockFields = [
                            { name: "session_dir", type: "Path", description: "Directory where downloaded source HTML is temporarily stored." },
                            { name: "timeout_sec", type: "int", description: "Parsing timeout per page." },
                            { name: "parser_flags", type: "dict[str, bool]" },
                        ];
                        return (
                            <div className="px-2 py-1 flex flex-wrap gap-1" style={{ borderTop: "1px solid rgba(255,255,255,0.04)" }}>
                                {context.provides?.map((c) => (
                                    <Popover key={c} trigger="click" placement="bottom" content={<div className="p-3 max-w-[280px]"><ContextInspector contextName={c} fields={mockFields} /></div>}>
                                        <span className="text-[8px] px-1 py-0.5 rounded flex items-center gap-0.5 cursor-pointer hover:opacity-80 transition-opacity" style={{ background: "rgba(34,197,94,0.08)", color: "var(--color-success)" }}>
                                            📤 {c}
                                        </span>
                                    </Popover>
                                ))}
                                {context.requires?.map((c) => (
                                    <Popover key={c} trigger="click" placement="bottom" content={<div className="p-3 max-w-[280px]"><ContextInspector contextName={c} fields={mockFields} /></div>}>
                                        <span className="text-[8px] px-1 py-0.5 rounded flex items-center gap-0.5 cursor-pointer hover:opacity-80 transition-opacity" style={{ background: "rgba(99,102,241,0.08)", color: "var(--color-info)" }}>
                                            📥 {c}
                                        </span>
                                    </Popover>
                                ))}
                            </div>
                        );
                    })()}

                    {/* Errors overlay */}
                    {hasErrors && (
                        <div className="px-2 py-1" style={{ borderTop: "1px solid rgba(239,68,68,0.15)", background: "rgba(239,68,68,0.04)" }}>
                            {errors.map((err, i) => (
                                <div key={i} className="text-[8px] truncate" style={{ color: "var(--color-error)" }}>
                                    ⚠ {err}
                                </div>
                            ))}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
