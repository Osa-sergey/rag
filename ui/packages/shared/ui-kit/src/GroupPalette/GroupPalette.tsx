import React, { useState, useRef } from "react";
import { GripVertical, Layers } from "lucide-react";
import { createPortal } from "react-dom";
import { FlowCanvas, FlowNode, FlowEdge } from "../FlowCanvas/FlowCanvas";

export interface PaletteGroupDef {
    id: string;
    name: string;
    description: string;
    category?: string;
    icon?: React.ReactNode;
    previewNodes: FlowNode[];
    previewEdges?: FlowEdge[];
}

export interface GroupPaletteProps {
    groups: PaletteGroupDef[];
    searchQuery?: string;
    onSearch?: (query: string) => void;
    onDragStart?: (group: PaletteGroupDef) => void;
}

export function GroupPalette({
    groups,
    searchQuery = "",
    onSearch,
    onDragStart,
}: GroupPaletteProps) {
    const [hoveredGroup, setHoveredGroup] = useState<PaletteGroupDef | null>(null);
    const [hoverPos, setHoverPos] = useState({ x: 0, y: 0 });
    const hoverTimeout = useRef<number | undefined>();

    const filtered = groups.filter(
        (g) =>
            g.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            g.description.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const handleMouseEnter = (e: React.MouseEvent, group: PaletteGroupDef) => {
        const rect = e.currentTarget.getBoundingClientRect();
        setHoverPos({ x: rect.right + 12, y: rect.top });

        clearTimeout(hoverTimeout.current);
        hoverTimeout.current = setTimeout(() => {
            setHoveredGroup(group);
        }, 300); // 300ms delay to avoid flickering
    };

    const handleMouseLeave = () => {
        clearTimeout(hoverTimeout.current);
        setHoveredGroup(null);
    };

    const renderGroup = (group: PaletteGroupDef) => (
        <div
            key={group.id}
            className="flex items-center gap-2 px-3 py-2 rounded-lg cursor-grab transition-colors hover:bg-white/5 group relative"
            draggable
            onDragStart={() => onDragStart?.(group)}
            onMouseEnter={(e) => handleMouseEnter(e, group)}
            onMouseLeave={handleMouseLeave}
        >
            <GripVertical size={10} className="flex-shrink-0 opacity-0 group-hover:opacity-50 transition-opacity" style={{ color: "var(--text-muted)" }} />
            <div className="flex items-center justify-center w-6 h-6 rounded bg-white/5" style={{ color: "var(--color-info)" }}>
                {group.icon || <Layers size={12} />}
            </div>
            <div className="flex-1 min-w-0">
                <div className="text-xs font-medium truncate" style={{ color: "var(--text-primary)" }}>
                    {group.name}
                </div>
                <div className="text-[9px] font-mono truncate" style={{ color: "var(--text-muted)" }}>
                    {group.description}
                </div>
            </div>
        </div>
    );

    return (
        <>
            <div
                className="rounded-xl overflow-hidden flex flex-col"
                style={{ background: "var(--bg-panel)", border: "var(--border-node)", width: "100%" }}
            >
                {/* Header */}
                <div className="px-3 py-2" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                    <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>Group Palette</span>
                </div>

                {/* Search */}
                {onSearch && (
                    <div className="px-2 pt-2">
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={e => onSearch(e.target.value)}
                            placeholder="Search groups…"
                            className="w-full px-2.5 py-1.5 rounded-lg text-[10px] outline-none"
                            style={{
                                background: "var(--bg-node)",
                                border: "1px solid rgba(255,255,255,0.06)",
                                color: "var(--text-primary)",
                            }}
                        />
                    </div>
                )}

                {/* Steps list */}
                <div className="flex-1 overflow-y-auto px-1 py-2" style={{ maxHeight: 200 }}>
                    {filtered.map(renderGroup)}
                    {filtered.length === 0 && (
                        <div className="text-xs text-center py-6" style={{ color: "var(--text-muted)" }}>
                            No groups found
                        </div>
                    )}
                </div>
            </div>

            {/* Hover Preview Portal */}
            {hoveredGroup && typeof document !== "undefined" && createPortal(
                <div
                    className="fixed z-[100] rounded-xl shadow-2xl backdrop-blur-xl overflow-hidden flex flex-col"
                    style={{
                        left: hoverPos.x,
                        top: Math.min(hoverPos.y, window.innerHeight - 350), // Adjust for height
                        width: 480,
                        height: 300,
                        background: "var(--bg-panel)",
                        border: "1px solid var(--border-panel)",
                        boxShadow: "0 10px 40px -10px rgba(0,0,0,0.5)",
                    }}
                    onMouseEnter={() => setHoveredGroup(hoveredGroup)}
                    onMouseLeave={handleMouseLeave}
                >
                    <div className="px-3 py-2 border-b shrink-0 flex items-center justify-between pointer-events-auto" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
                        <div className="text-xs font-semibold text-white">{hoveredGroup.name}</div>
                        <div className="text-[9px] text-zinc-400">{hoveredGroup.previewNodes.length} steps</div>
                    </div>
                    <div className="flex-1 relative bg-black/20 pointer-events-none">
                        <FlowCanvas
                            nodes={hoveredGroup.previewNodes}
                            edges={hoveredGroup.previewEdges ?? []}
                            background="dots"
                            fitViewOnInit
                            showControls={false}
                            showMinimap={false}
                        />
                    </div>
                </div>,
                document.body
            )}
        </>
    );
}
