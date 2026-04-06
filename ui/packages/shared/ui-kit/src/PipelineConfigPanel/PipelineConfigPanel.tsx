import React, { useState, useEffect } from "react";
import { Settings, Play, Clock, GitBranch, Save } from "lucide-react";
import { Input } from "../Input";
import { Select } from "../Select";
import { Toggle } from "../Toggle";
import { Slider } from "../Slider";

export interface PipelineConfig {
    retries: number;
    concurrency: number;
    timeout: number;
    catchup: boolean;
    executor: string;
}

export interface PipelineConfigPanelProps {
    /** Current config */
    value?: Partial<PipelineConfig>;
    /** On change handler */
    onChange?: (val: Partial<PipelineConfig>) => void;
    /** On save or apply */
    onSave?: () => void;
}

const defaultCfg: PipelineConfig = {
    retries: 3,
    concurrency: 16,
    timeout: 3600,
    catchup: false,
    executor: "kubernetes",
};

export function PipelineConfigPanel({ value, onChange, onSave }: PipelineConfigPanelProps) {
    const [cfg, setCfg] = useState<PipelineConfig>({ ...defaultCfg, ...value });

    useEffect(() => {
        if (value) {
            setCfg(prev => ({ ...prev, ...value }));
        }
    }, [value]);

    const update = (partial: Partial<PipelineConfig>) => {
        const next = { ...cfg, ...partial };
        setCfg(next);
        onChange?.(next);
    };

    return (
        <div
            className="flex flex-col w-full max-w-md rounded-2xl overflow-hidden shadow-node"
            style={{ background: "var(--bg-panel)", border: "1px solid var(--border-node)" }}
        >
            {/* Header */}
            <div className="px-5 py-4 flex items-center justify-between" style={{ borderBottom: "1px solid var(--border-node)", background: "var(--bg-node)" }}>
                <div className="flex items-center gap-2.5">
                    <div className="p-1.5 rounded-lg" style={{ background: "rgba(99,102,241,0.1)", color: "var(--color-info)" }}>
                        <Settings size={16} />
                    </div>
                    <div>
                        <h2 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>Pipeline Settings</h2>
                        <p className="text-[10px] text-[var(--text-secondary)] font-medium mt-0.5">Top-level parameters for execution</p>
                    </div>
                </div>
            </div>

            {/* Body */}
            <div className="flex flex-col gap-6 p-5">

                {/* Executor Selection */}
                <div className="flex flex-col gap-2">
                    <Select
                        label="Executor Engine"
                        options={[
                            { label: "Kubernetes Executor", value: "kubernetes", group: "Scalable" },
                            { label: "Celery Executor", value: "celery", group: "Scalable" },
                            { label: "Local Executor", value: "local", group: "Standalone" },
                            { label: "Sequential Executor", value: "sequential", group: "Standalone" },
                        ]}
                        value={[cfg.executor]}
                        onChange={(v) => update({ executor: Array.isArray(v) ? v[0] : v })}
                        fullWidth
                    />
                    <p className="text-[9px] text-[var(--text-muted)] mt-1 px-1">
                        Determines the environment and scaling factor where tasks execute.
                    </p>
                </div>

                <div className="w-full h-px" style={{ background: "var(--border-node)" }} />

                {/* Retries & Timeout */}
                <div className="grid grid-cols-2 gap-4">
                    <Input
                        label="Default Retries"
                        type="number"
                        min={0}
                        max={10}
                        icon={<RefreshIcon size={14} />}
                        value={cfg.retries.toString()}
                        onChange={(v) => update({ retries: parseInt(v) || 0 })}
                    />
                    <Input
                        label="Timeout (s)"
                        type="number"
                        min={0}
                        icon={<Clock size={14} />}
                        value={cfg.timeout.toString()}
                        onChange={(v) => update({ timeout: parseInt(v) || 0 })}
                    />
                </div>

                {/* Concurrency Slider */}
                <div className="flex flex-col gap-3 mt-2">
                    <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-[var(--text-primary)]">Max Concurrency</span>
                        <span className="text-[10px] font-mono text-[var(--color-info)] bg-[rgba(99,102,241,0.1)] px-1.5 py-0.5 rounded">
                            {cfg.concurrency} tasks
                        </span>
                    </div>
                    <Slider
                        min={1}
                        max={128}
                        step={1}
                        value={cfg.concurrency}
                        onChange={(v) => update({ concurrency: v })}
                    />
                </div>

                {/* Catchup Toggle */}
                <div className="flex items-center justify-between mt-2 p-3 rounded-xl border border-[var(--border-node)] bg-[var(--bg-node)]">
                    <div className="flex items-center gap-3">
                        <div className="p-1.5 rounded-full" style={{ background: "rgba(34,197,94,0.1)", color: "var(--color-success)" }}>
                            <Play size={14} />
                        </div>
                        <div className="flex flex-col">
                            <span className="text-xs font-bold text-[var(--text-primary)]">Auto Catchup</span>
                            <span className="text-[9px] text-[var(--text-secondary)]">Run missed intervals</span>
                        </div>
                    </div>
                    <Toggle checked={cfg.catchup} onChange={(v) => update({ catchup: v })} />
                </div>
            </div>

            {/* Footer */}
            {onSave && (
                <div className="px-5 py-4 flex justify-end" style={{ background: "var(--bg-node)", borderTop: "1px solid var(--border-node)" }}>
                    <button
                        onClick={onSave}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold transition-transform active:scale-95"
                        style={{ background: "var(--color-info)", color: "#fff", boxShadow: "0 2px 8px rgba(99,102,241,0.25)" }}
                    >
                        <Save size={14} />
                        Save Settings
                    </button>
                </div>
            )}
        </div>
    );
}

const RefreshIcon = ({ size }: { size: number }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /><path d="M3 3v5h5" />
    </svg>
);
