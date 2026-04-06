import React from "react";
import { iconMap } from "../IconPicker/IconPicker";

export interface NodeAppearance {
    color: string;
    icon: string;
}

export interface LiveNodePreviewProps {
    appearance?: NodeAppearance;
    label?: string;
    description?: string;
}

export function LiveNodePreview({
    appearance = { color: "var(--color-info)", icon: "database" },
    label = "Sample Node",
    description = "Preview configuration",
}: LiveNodePreviewProps) {
    const IconComponent = iconMap[appearance.icon] || iconMap["database"];

    return (
        <div className="flex flex-col items-center justify-center w-full">
            <span className="text-[9px] font-bold uppercase tracking-widest text-[var(--text-muted)] mb-3">Live Appearance Preview</span>
            <div
                className="rounded-xl overflow-hidden cursor-default transition-all shadow-node flex flex-col hover:shadow-hover hover:-translate-y-1"
                style={{
                    width: 240,
                    background: "var(--bg-node)",
                    border: "1px solid var(--border-node)",
                }}
            >
                <div className="h-2 w-full transition-colors" style={{ background: appearance.color }} />
                <div className="px-4 py-4 flex items-start gap-4">
                    <div
                        className="p-2.5 rounded-xl border border-[var(--border-node)] shadow-sm flex items-center justify-center transition-colors"
                        style={{ color: appearance.color, background: "var(--bg-canvas)" }}
                    >
                        {IconComponent}
                    </div>
                    <div className="flex flex-col min-w-0 flex-1 justify-center h-10">
                        <span className="text-sm font-bold text-[var(--text-primary)] truncate">{label}</span>
                        {description && (
                            <span className="text-[10px] text-[var(--text-secondary)] leading-snug truncate">
                                {description}
                            </span>
                        )}
                    </div>
                </div>
                <div className="px-4 py-2 border-t border-[var(--border-node)] flex items-center gap-2" style={{ background: "rgba(255,255,255,0.01)" }}>
                    <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: appearance.color, boxShadow: `0 0 8px ${appearance.color}` }} />
                    <span className="text-[9px] font-mono text-[var(--text-secondary)]">status: configured</span>
                </div>
            </div>
        </div>
    );
}
