import React from "react";
import { Search, GripVertical } from "lucide-react";

export interface PaletteStep {
    id: string;
    name: string;
    module: string;
    category?: string;
    icon?: React.ReactNode;
}

export interface NodePaletteProps {
    /** Available steps */
    steps: PaletteStep[];
    /** Search query */
    searchQuery?: string;
    /** On search change */
    onSearch?: (query: string) => void;
    /** On step drag start */
    onDragStart?: (step: PaletteStep) => void;
    /** Group by category */
    grouped?: boolean;
}

export function NodePalette({
    steps,
    searchQuery = "",
    onSearch,
    onDragStart,
    grouped = false,
}: NodePaletteProps) {
    const filtered = steps.filter(
        (s) =>
            s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            s.module.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const groups: Record<string, PaletteStep[]> = {};
    if (grouped) {
        for (const s of filtered) {
            const cat = s.category ?? "Uncategorized";
            if (!groups[cat]) groups[cat] = [];
            groups[cat].push(s);
        }
    }

    const renderStep = (step: PaletteStep) => (
        <div
            key={step.id}
            className="flex items-center gap-2 px-3 py-2 rounded-lg cursor-grab transition-colors hover:bg-white/5 group"
            draggable
            onDragStart={() => onDragStart?.(step)}
        >
            <GripVertical size={10} className="flex-shrink-0 opacity-0 group-hover:opacity-50 transition-opacity" style={{ color: "var(--text-muted)" }} />
            <div className="flex-1 min-w-0">
                <div className="text-xs font-medium truncate" style={{ color: "var(--text-primary)" }}>
                    {step.name}
                </div>
                <div className="text-[9px] font-mono truncate" style={{ color: "var(--text-muted)" }}>
                    {step.module}
                </div>
            </div>
        </div>
    );

    return (
        <div
            className="rounded-xl overflow-hidden flex flex-col"
            style={{ background: "var(--bg-panel)", border: "var(--border-node)", width: "100%" }}
        >
            {/* Header */}
            <div className="px-3 py-2.5" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>Step Palette</span>
            </div>

            {/* Search */}
            <div className="px-3 py-2">
                <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg" style={{ background: "var(--bg-node)", border: "var(--border-node)" }}>
                    <Search size={11} style={{ color: "var(--text-muted)" }} />
                    <input
                        value={searchQuery}
                        onChange={(e) => onSearch?.(e.target.value)}
                        className="bg-transparent outline-none text-xs flex-1"
                        style={{ color: "var(--text-primary)" }}
                        placeholder="Search steps..."
                    />
                </div>
            </div>

            {/* Steps list */}
            <div className="flex-1 overflow-y-auto px-1 pb-2" style={{ maxHeight: 300 }}>
                {grouped ? (
                    Object.entries(groups).map(([cat, items]) => (
                        <div key={cat} className="mb-2">
                            <div className="text-[9px] font-semibold uppercase tracking-wider px-3 py-1" style={{ color: "var(--text-muted)" }}>
                                {cat} ({items.length})
                            </div>
                            {items.map(renderStep)}
                        </div>
                    ))
                ) : (
                    filtered.map(renderStep)
                )}

                {filtered.length === 0 && (
                    <div className="text-xs text-center py-6" style={{ color: "var(--text-muted)" }}>
                        No steps match your search
                    </div>
                )}
            </div>
        </div>
    );
}
