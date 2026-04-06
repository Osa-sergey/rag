import React, { useState, useEffect } from "react";
import { Input } from "../Input";
import { Select } from "../Select";
import { Toggle } from "../Toggle";
import { Bell, CheckCircle2, XCircle, RefreshCw, Save, X, Settings2 } from "lucide-react";

export type CallbackType = "on_retry" | "on_success" | "on_failure" | "on_alert";

export interface CallbackParamFormProps {
    /** The type of callback being configured */
    type: CallbackType;
    /** JSON string of initial params */
    initialParams?: string;
    /** Save handler */
    onSave?: (params: string) => void;
    /** Cancel handler */
    onCancel?: () => void;
}

const icons: Record<CallbackType, React.ReactNode> = {
    on_retry: <RefreshCw size={14} />,
    on_success: <CheckCircle2 size={14} />,
    on_failure: <XCircle size={14} />,
    on_alert: <Bell size={14} />,
};

const labels: Record<CallbackType, string> = {
    on_retry: "Retry Logic handler",
    on_success: "Success Hook",
    on_failure: "Failure Hook",
    on_alert: "Alert Notification",
};

const colors: Record<CallbackType, string> = {
    on_retry: "var(--color-stale)",
    on_success: "var(--color-success)",
    on_failure: "var(--color-error)",
    on_alert: "var(--color-warning)",
};

export function CallbackParamForm({
    type,
    initialParams = "{}",
    onSave,
    onCancel,
}: CallbackParamFormProps) {
    const [params, setParams] = useState<Record<string, any>>({});

    useEffect(() => {
        try {
            setParams(JSON.parse(initialParams));
        } catch (e) {
            setParams({});
        }
    }, [initialParams, type]);

    const update = (key: string, val: any) => {
        setParams(prev => ({ ...prev, [key]: val }));
    };

    const handleSave = () => {
        onSave?.(JSON.stringify(params));
    };

    const renderDynamicFields = () => {
        switch (type) {
            case "on_success":
            case "on_failure":
                return (
                    <>
                        <div className="flex flex-col gap-1">
                            <Input
                                label="Webhook Endpoint URL"
                                placeholder="https://api.example.com/webhook"
                                value={params.url || ""}
                                onChange={(v) => update("url", v)}
                            />
                        </div>
                        <div className="flex flex-col gap-1">
                            <Select
                                label="Method"
                                options={[{ label: "POST", value: "POST" }, { label: "GET", value: "GET" }]}
                                value={[params.method || "POST"]}
                                onChange={(v) => update("method", Array.isArray(v) ? v[0] : v)}
                                fullWidth
                            />
                        </div>
                        <div className="flex flex-col gap-1">
                            <label className="text-xs font-bold text-[var(--text-secondary)]">Custom Payload (JSON template)</label>
                            <textarea
                                className="w-full h-24 p-3 rounded-lg text-[10px] font-mono outline-none resize-none transition-all focus:ring-1"
                                style={{ background: "var(--bg-canvas)", border: "1px solid var(--border-node)", color: "var(--text-primary)" }}
                                placeholder={`{\n  "status": "completed",\n  "run_id": "{{ run_id }}"\n}`}
                                value={params.payload || ""}
                                onChange={(e) => update("payload", e.target.value)}
                            />
                            <p className="text-[9px] text-[var(--text-muted)]">You can use Jinja macros like {'{{ task_id }}'}</p>
                        </div>
                    </>
                );
            case "on_alert":
                return (
                    <>
                        <div className="flex flex-col gap-1">
                            <Select
                                label="Channel"
                                options={[
                                    { label: "Slack", value: "slack" },
                                    { label: "Email", value: "email" },
                                    { label: "PagerDuty", value: "pagerduty" }
                                ]}
                                value={[params.channel || "slack"]}
                                onChange={(v) => update("channel", Array.isArray(v) ? v[0] : v)}
                                fullWidth
                            />
                        </div>
                        <div className="flex flex-col gap-1">
                            <Input
                                label="Destination (Channel ID / Email)"
                                placeholder="#alerts-data-eng"
                                value={params.destination || ""}
                                onChange={(v) => update("destination", v)}
                            />
                        </div>
                        <div className="flex items-center justify-between p-3 rounded-xl border border-[var(--border-node)] bg-[var(--bg-canvas)]">
                            <span className="text-xs font-bold" style={{ color: "var(--text-primary)" }}>High Priority Mention</span>
                            <Toggle checked={params.high_priority || false} onChange={(v) => update("high_priority", v)} />
                        </div>
                    </>
                );
            case "on_retry":
                return (
                    <>
                        <div className="grid grid-cols-2 gap-3">
                            <Input
                                label="Max Delay (s)"
                                type="number"
                                value={(params.max_delay || 60).toString()}
                                onChange={(v) => update("max_delay", parseInt(v) || 0)}
                            />
                            <Input
                                label="Multiplier"
                                type="number"
                                value={(params.multiplier || 2).toString()}
                                onChange={(v) => update("multiplier", parseFloat(v) || 1)}
                            />
                        </div>
                        <div className="flex items-center justify-between p-3 rounded-xl border border-[var(--border-node)] bg-[var(--bg-canvas)]">
                            <span className="text-xs font-bold" style={{ color: "var(--text-primary)" }}>Apply Jitter</span>
                            <Toggle checked={params.jitter !== false} onChange={(v) => update("jitter", v)} />
                        </div>
                        <p className="text-[9px] text-[var(--text-muted)] leading-tight">
                            Jitter adds randomness to retry intervals to prevent thundering herd problems on recovering systems.
                        </p>
                    </>
                );
            default:
                return null;
        }
    };

    return (
        <div
            className="flex flex-col w-full max-w-[320px] rounded-2xl overflow-hidden shadow-node"
            style={{ background: "var(--bg-node)", border: "1px solid var(--border-node)" }}
        >
            {/* Header */}
            <div className="px-4 py-3 flex items-start justify-between" style={{ borderBottom: "1px solid var(--border-node)", background: `color-mix(in srgb, ${colors[type]} 10%, transparent)` }}>
                <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-lg bg-[var(--bg-panel)] shadow-sm" style={{ color: colors[type] }}>
                        {icons[type]}
                    </div>
                    <div className="flex flex-col">
                        <span className="text-[10px] font-bold uppercase tracking-widest leading-none drop-shadow-sm" style={{ color: colors[type] }}>{type}</span>
                        <span className="text-[9px] font-semibold text-[var(--text-secondary)] mt-0.5">{labels[type]}</span>
                    </div>
                </div>
                {onCancel && (
                    <button onClick={onCancel} className="p-1 hover:bg-black/10 rounded-full text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors">
                        <X size={14} />
                    </button>
                )}
            </div>

            {/* Form */}
            <div className="p-4 flex flex-col gap-4">
                {renderDynamicFields()}
            </div>

            {/* Actions */}
            {onSave && (
                <div className="px-4 py-3 flex items-center justify-end gap-2" style={{ borderTop: "1px solid var(--border-node)", background: "var(--bg-panel)" }}>
                    {onCancel && (
                        <button
                            onClick={onCancel}
                            className="px-3 py-1.5 rounded-lg text-[10px] font-bold hover:bg-[var(--bg-node-hover)] transition-colors text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                        >
                            Cancel
                        </button>
                    )}
                    <button
                        onClick={handleSave}
                        className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-bold transition-transform active:scale-95 text-white"
                        style={{ background: colors[type], boxShadow: `0 2px 8px color-mix(in srgb, ${colors[type]} 30%, transparent)` }}
                    >
                        <Save size={12} /> Apply
                    </button>
                </div>
            )}
        </div>
    );
}
