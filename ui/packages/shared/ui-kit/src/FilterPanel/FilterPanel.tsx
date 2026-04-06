import React, { useState } from "react";
import { Filter, ChevronDown, RotateCcw } from "lucide-react";

export interface FilterGroup {
    /** Group label */
    label: string;
    /** Filter options */
    options: Array<{
        id: string;
        label: string;
        color?: string;
        checked?: boolean;
    }>;
}

export interface SliderFilter {
    id: string;
    label: string;
    min: number;
    max: number;
    value: number;
    step?: number;
    format?: (v: number) => string;
}

export interface FilterPanelProps {
    /** Chip filter groups (e.g. entity types, statuses) */
    groups?: FilterGroup[];
    /** Range sliders (e.g. similarity threshold) */
    sliders?: SliderFilter[];
    /** Toggle filters */
    toggles?: Array<{ id: string; label: string; checked?: boolean }>;
    /** On filter change */
    onFilterChange?: (type: string, id: string, value: any) => void;
    /** Compact mode */
    compact?: boolean;
}

export function FilterPanel({
    groups = [],
    sliders = [],
    toggles = [],
    onFilterChange,
    compact = false,
}: FilterPanelProps) {
    const [groupStates, setGroupStates] = useState<Record<string, Set<string>>>(() => {
        const init: Record<string, Set<string>> = {};
        for (const g of groups) {
            init[g.label] = new Set(g.options.filter((o) => o.checked).map((o) => o.id));
        }
        return init;
    });

    const [sliderValues, setSliderValues] = useState<Record<string, number>>(() => {
        const init: Record<string, number> = {};
        for (const s of sliders) init[s.id] = s.value;
        return init;
    });

    const [toggleValues, setToggleValues] = useState<Record<string, boolean>>(() => {
        const init: Record<string, boolean> = {};
        for (const t of toggles) init[t.id] = t.checked ?? false;
        return init;
    });

    const toggleChip = (group: string, id: string) => {
        setGroupStates((prev) => {
            const s = new Set(prev[group]);
            if (s.has(id)) s.delete(id); else s.add(id);
            onFilterChange?.("chip", id, s.has(id));
            return { ...prev, [group]: s };
        });
    };

    const activeCount = Object.values(groupStates).reduce((a, s) => a + s.size, 0)
        + Object.values(toggleValues).filter(Boolean).length;

    return (
        <div
            className="rounded-xl overflow-hidden flex flex-col gap-0"
            style={{ background: "var(--bg-panel)", border: "var(--border-node)", width: compact ? 240 : 280 }}
        >
            {/* Header */}
            <div
                className="flex items-center justify-between px-3 py-2.5"
                style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
            >
                <div className="flex items-center gap-2">
                    <Filter size={13} style={{ color: "var(--text-muted)" }} />
                    <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>Filters</span>
                    {activeCount > 0 && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded-full font-bold" style={{ background: "rgba(99,102,241,0.12)", color: "var(--color-info)" }}>
                            {activeCount}
                        </span>
                    )}
                </div>
                <button
                    onClick={() => {
                        setGroupStates((prev) => {
                            const reset: Record<string, Set<string>> = {};
                            for (const k of Object.keys(prev)) reset[k] = new Set();
                            return reset;
                        });
                        setToggleValues((prev) => {
                            const reset: Record<string, boolean> = {};
                            for (const k of Object.keys(prev)) reset[k] = false;
                            return reset;
                        });
                    }}
                    className="p-1 rounded hover:bg-white/5 transition-colors"
                    style={{ color: "var(--text-muted)" }}
                    title="Reset all"
                >
                    <RotateCcw size={11} />
                </button>
            </div>

            <div className="px-3 py-2 flex flex-col gap-3">
                {/* Chip groups */}
                {groups.map((group) => (
                    <div key={group.label} className="flex flex-col gap-1.5">
                        <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                            {group.label}
                        </span>
                        <div className="flex flex-wrap gap-1">
                            {group.options.map((opt) => {
                                const active = groupStates[group.label]?.has(opt.id);
                                return (
                                    <button
                                        key={opt.id}
                                        onClick={() => toggleChip(group.label, opt.id)}
                                        className="flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-medium transition-all"
                                        style={{
                                            background: active
                                                ? `color-mix(in srgb, ${opt.color ?? "var(--color-info)"} 15%, transparent)`
                                                : "var(--bg-node)",
                                            color: active ? (opt.color ?? "var(--color-info)") : "var(--text-muted)",
                                            border: `1px solid ${active ? (opt.color ?? "var(--color-info)") : "rgba(255,255,255,0.06)"}`,
                                        }}
                                    >
                                        {active && <span>✓</span>}
                                        {opt.label}
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                ))}

                {/* Sliders */}
                {sliders.map((slider) => (
                    <div key={slider.id} className="flex flex-col gap-1">
                        <div className="flex items-center justify-between">
                            <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                                {slider.label}
                            </span>
                            <span className="text-[10px] font-mono font-bold" style={{ color: "var(--color-info)" }}>
                                {slider.format ? slider.format(sliderValues[slider.id]) : sliderValues[slider.id]}
                            </span>
                        </div>
                        <input
                            type="range"
                            min={slider.min}
                            max={slider.max}
                            step={slider.step ?? 0.01}
                            value={sliderValues[slider.id]}
                            onChange={(e) => {
                                const v = Number(e.target.value);
                                setSliderValues((p) => ({ ...p, [slider.id]: v }));
                                onFilterChange?.("slider", slider.id, v);
                            }}
                            className="w-full h-1 rounded-full appearance-none cursor-pointer"
                            style={{ background: `linear-gradient(to right, var(--color-info) ${((sliderValues[slider.id] - slider.min) / (slider.max - slider.min)) * 100}%, var(--bg-node-hover) ${((sliderValues[slider.id] - slider.min) / (slider.max - slider.min)) * 100}%)` }}
                        />
                    </div>
                ))}

                {/* Toggles */}
                {toggles.map((toggle) => (
                    <div key={toggle.id} className="flex items-center justify-between">
                        <span className="text-xs" style={{ color: "var(--text-secondary)" }}>{toggle.label}</span>
                        <button
                            onClick={() => {
                                setToggleValues((p) => ({ ...p, [toggle.id]: !p[toggle.id] }));
                                onFilterChange?.("toggle", toggle.id, !toggleValues[toggle.id]);
                            }}
                            className="relative w-8 h-4.5 rounded-full transition-colors flex-shrink-0"
                            style={{
                                width: 32,
                                height: 18,
                                background: toggleValues[toggle.id] ? "var(--color-info)" : "var(--text-muted)",
                            }}
                        >
                            <div
                                className="absolute top-0.5 w-3.5 h-3.5 rounded-full transition-all"
                                style={{
                                    width: 14,
                                    height: 14,
                                    left: toggleValues[toggle.id] ? 16 : 2,
                                    background: "white",
                                }}
                            />
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
}
