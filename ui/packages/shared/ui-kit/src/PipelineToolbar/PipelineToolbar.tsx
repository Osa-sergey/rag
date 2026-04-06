import React from "react";
import { Play, Square, RotateCcw, FileDown, FileUp, Settings, Save, CheckCircle2 } from "lucide-react";

export interface PipelineToolbarProps {
    /** Pipeline name */
    name?: string;
    /** Pipeline status */
    status?: "idle" | "running" | "completed" | "failed";
    /** Step count */
    stepCount?: number;
    /** Edge count */
    edgeCount?: number;
    /** Has unsaved changes */
    dirty?: boolean;
    /** Action handlers */
    onRun?: () => void;
    onStop?: () => void;
    onReset?: () => void;
    onSave?: () => void;
    onExport?: () => void;
    onImport?: () => void;
    /** Extra elements like ViewSwitcher */
    children?: React.ReactNode;
}

export function PipelineToolbar({
    name = "Untitled Pipeline",
    status = "idle",
    stepCount = 0,
    edgeCount = 0,
    dirty = false,
    onRun, onStop, onReset, onSave, onExport, onImport,
    children,
}: PipelineToolbarProps) {
    const isRunning = status === "running";
    const isCompleted = status === "completed";

    return (
        <div
            className="flex items-center gap-3 px-4 py-2 rounded-xl"
            style={{ background: "var(--bg-panel)", border: "var(--border-node)" }}
        >
            {/* Pipeline name */}
            <div className="flex items-center gap-2 min-w-0 mr-2">
                <span className="text-xs font-semibold truncate" style={{ color: "var(--text-primary)" }}>
                    {name}
                </span>
                {dirty && (
                    <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: "var(--color-warning)" }} title="Unsaved changes" />
                )}
            </div>

            {/* Stats */}
            <div className="flex items-center gap-2 text-[10px] font-mono mr-2" style={{ color: "var(--text-muted)" }}>
                <span>{stepCount} steps</span>
                <span>·</span>
                <span>{edgeCount} edges</span>
            </div>

            {/* Separator */}
            <div className="w-px h-5" style={{ background: "rgba(255,255,255,0.08)" }} />

            {/* Custom injects like ViewSwitcher */}
            {children && (
                <div className="flex items-center">
                    {children}
                </div>
            )}

            {/* Run / Stop */}
            {isRunning ? (
                <button onClick={onStop} className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-colors hover:bg-red-500/20" style={{ background: "rgba(239,68,68,0.1)", color: "var(--color-error)" }}>
                    <Square size={11} /> Stop
                </button>
            ) : (
                <button onClick={onRun} className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-colors hover:bg-green-500/20" style={{ background: "rgba(34,197,94,0.1)", color: "var(--color-success)" }}>
                    <Play size={11} fill="currentColor" /> Run
                </button>
            )}

            {/* Status badge */}
            {isCompleted && (
                <span className="flex items-center gap-1 text-[10px] font-medium" style={{ color: "var(--color-success)" }}>
                    <CheckCircle2 size={11} /> Completed
                </span>
            )}

            {/* Reset */}
            <button onClick={onReset} className="p-1.5 rounded-lg transition-colors hover:bg-white/5" style={{ color: "var(--text-muted)" }} title="Reset">
                <RotateCcw size={13} />
            </button>

            {/* Separator */}
            <div className="w-px h-5" style={{ background: "rgba(255,255,255,0.08)" }} />

            {/* Save */}
            <button onClick={onSave} className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-[10px] font-medium transition-colors hover:bg-white/5" style={{ color: dirty ? "var(--color-info)" : "var(--text-muted)" }}>
                <Save size={11} /> Save
            </button>

            {/* Import / Export */}
            <button onClick={onImport} className="p-1.5 rounded-lg transition-colors hover:bg-white/5" style={{ color: "var(--text-muted)" }} title="Import YAML">
                <FileUp size={13} />
            </button>
            <button onClick={onExport} className="p-1.5 rounded-lg transition-colors hover:bg-white/5" style={{ color: "var(--text-muted)" }} title="Export YAML">
                <FileDown size={13} />
            </button>
        </div>
    );
}
