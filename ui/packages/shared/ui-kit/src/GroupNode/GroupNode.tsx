import React, { useState, useRef, useEffect, useLayoutEffect } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, ChevronRight, Layers, ArrowLeft, Maximize2, Minimize2 } from "lucide-react";

/** A node child to be rendered on the mini-canvas */
export interface CanvasChild {
    id: string;
    /** Render callback */
    render: React.ReactNode;
    /** Position on mini-canvas (0-100 %) */
    x?: number;
    y?: number;
    /** Width of child element (for edge anchoring) */
    width?: number;
    /** Height of child element (for edge anchoring) */
    height?: number;
}

/** SVG edge between child nodes */
export interface CanvasEdge {
    from: string;
    to: string;
    /** Arrow style */
    arrow?: "default" | "triangle" | "dot" | "diamond" | "none";
    /** Dashed or solid */
    dashed?: boolean;
}

export interface GroupNodeProps {
    /** Group title */
    title: string;
    /** Group color */
    color?: string;
    /** Number of children in the group */
    childCount?: number;
    /** Collapsed state */
    collapsed?: boolean;
    /** On toggle */
    onToggle?: () => void;
    /** Children slots (legacy simple children) */
    children?: React.ReactNode;
    /** Canvas children — positioned child nodes */
    canvasChildren?: CanvasChild[];
    /** Edges between canvas children */
    canvasEdges?: CanvasEdge[];
    /** Render depth: how many nesting levels to draw (default 1) */
    renderDepth?: number;
    /** Current depth (internal, used by nesting) */
    currentDepth?: number;
    /** Breadcrumb trail for fullscreen navigation */
    breadcrumbs?: string[];
    /** Canvas width */
    canvasWidth?: number;
    /** Canvas height */
    canvasHeight?: number;
    /** On fullscreen request */
    onFullscreen?: (groupTitle: string) => void;
    /** On exit fullscreen / go back */
    onBack?: () => void;
    /** Is currently in fullscreen mode */
    isFullscreen?: boolean;
    /** Min width for the group (auto-sized if title is long) */
    minWidth?: number;
    /** Called when user resizes via corner handle */
    onResize?: (width: number, height: number) => void;
}

/** Marker definitions for different arrow types - made smaller! */
function EdgeMarkers({ id }: { id: string }) {
    return (
        <defs>
            <marker id={`arrow-tri-${id}`} viewBox="0 0 8 6" refX="8" refY="3" markerWidth="5" markerHeight="4" orient="auto-start-reverse">
                <path d="M0,0 L8,3 L0,6 z" fill="currentColor" />
            </marker>
            <marker id={`arrow-dot-${id}`} viewBox="0 0 6 6" refX="3" refY="3" markerWidth="4" markerHeight="4" orient="auto">
                <circle cx="3" cy="3" r="2.5" fill="currentColor" />
            </marker>
            <marker id={`arrow-diamond-${id}`} viewBox="0 0 10 6" refX="10" refY="3" markerWidth="6" markerHeight="4" orient="auto-start-reverse">
                <path d="M0,3 L5,0 L10,3 L5,6 z" fill="currentColor" />
            </marker>
        </defs>
    );
}

/** Get marker URL for an arrow type */
function markerUrl(arrow: string, id: string): string {
    if (arrow === "triangle" || arrow === "default") return `url(#arrow-tri-${id})`;
    if (arrow === "dot") return `url(#arrow-dot-${id})`;
    if (arrow === "diamond") return `url(#arrow-diamond-${id})`;
    return "";
}

/** Compute edge path from edge of source element to edge of target element */
function computeEdgePath(
    fromX: number, fromY: number, fromW: number, fromH: number,
    toX: number, toY: number, toW: number, toH: number,
    canvasW: number, canvasH: number,
): { x1: number; y1: number; x2: number; y2: number } {
    // Convert percentages to pixels
    const fx = (fromX / 100) * canvasW;
    const fy = (fromY / 100) * canvasH;
    const tx = (toX / 100) * canvasW;
    const ty = (toY / 100) * canvasH;

    // Direction from source to target
    const dx = tx - fx;
    const dy = ty - fy;

    // Source anchor: exit from edge of bounding box
    let sx = fx, sy = fy;
    if (Math.abs(dx) > Math.abs(dy)) {
        // Horizontal dominant → exit right or left
        sx = dx > 0 ? fx + fromW / 2 : fx - fromW / 2;
        sy = fy;
    } else {
        // Vertical dominant → exit top or bottom
        sx = fx;
        sy = dy > 0 ? fy + fromH / 2 : fy - fromH / 2;
    }

    // Target anchor: enter from edge of bounding box
    let ex = tx, ey = ty;
    if (Math.abs(dx) > Math.abs(dy)) {
        ex = dx > 0 ? tx - toW / 2 : tx + toW / 2;
        ey = ty;
    } else {
        ex = tx;
        ey = dy > 0 ? ty - toH / 2 : ty + toH / 2;
    }

    return { x1: sx, y1: sy, x2: ex, y2: ey };
}

export function GroupNode({
    title,
    color = "var(--color-info)",
    childCount,
    collapsed: controlledCollapsed,
    onToggle,
    children,
    canvasChildren = [],
    canvasEdges = [],
    renderDepth = 1,
    currentDepth = 0,
    breadcrumbs = [],
    canvasWidth = 280,
    canvasHeight = 160,
    onFullscreen,
    onBack,
    isFullscreen = false,
    minWidth,
    onResize,
}: GroupNodeProps) {
    const [internalCollapsed, setInternalCollapsed] = useState(false);
    const headerRef = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLDivElement>(null);
    const [headerW, setHeaderW] = useState(0);
    const [actualCanvasSize, setActualCanvasSize] = useState({ w: canvasWidth, h: canvasHeight });

    const isCollapsed = controlledCollapsed ?? internalCollapsed;
    const shouldRenderChildren = currentDepth < renderDepth;
    const hasCanvasChildren = canvasChildren.length > 0;
    const totalChildren = childCount ?? canvasChildren.length;
    const markerId = `g-${title.replace(/\s/g, "")}-${currentDepth}`;

    const handleToggle = () => {
        setInternalCollapsed(!isCollapsed);
        onToggle?.();
    };

    // Auto-size header width
    useEffect(() => {
        if (headerRef.current) setHeaderW(headerRef.current.scrollWidth + 32);
    }, [title, totalChildren]);

    // Track dynamic canvas size using ResizeObserver
    useLayoutEffect(() => {
        if (!canvasRef.current) return;
        const obs = new ResizeObserver((entries) => {
            if (!entries[0]) return;
            const rect = entries[0].contentRect;
            if (rect.width > 0 && rect.height > 0) {
                setActualCanvasSize({ w: rect.width, h: rect.height });
            }
        });
        obs.observe(canvasRef.current);
        return () => obs.disconnect();
    }, [isFullscreen, isCollapsed, shouldRenderChildren]);

    const collapsedW = Math.max(minWidth ?? 160, headerW, 140);
    const expandedW = Math.max(canvasWidth + 32, collapsedW);
    // When resizable, fill parent container; otherwise use calculated width
    const width = isFullscreen ? "100%" : onResize ? "100%" : isCollapsed ? collapsedW : expandedW;
    const height = onResize && !isCollapsed && !isFullscreen ? "100%" : undefined;

    const content = (
        <div
            className="rounded-2xl transition-all flex flex-col relative"
            style={{
                border: isFullscreen ? 'none' : `2px dashed color-mix(in srgb, ${color} 40%, transparent)`,
                background: isFullscreen ? "var(--bg-canvas, #f8f9fa)" : `color-mix(in srgb, ${color} 3%, transparent)`,
                width: isFullscreen ? '100vw' : width,
                height: isFullscreen ? '100vh' : height,
                ...(isFullscreen ? { position: 'fixed' as const, inset: 0, zIndex: 9999, borderRadius: 0 } : {}),
            }}
        >
            {/* Breadcrumb trail (fullscreen only) */}
            {isFullscreen && breadcrumbs.length > 0 && (
                <div className="flex items-center gap-1.5 px-4 py-2" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                    <button onClick={onBack} className="flex items-center gap-1 text-[10px] font-medium transition-colors hover:opacity-80" style={{ color: "var(--text-muted)" }}>
                        <ArrowLeft size={12} /> Back
                    </button>
                    {breadcrumbs.map((crumb, i) => (
                        <React.Fragment key={i}>
                            <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>/</span>
                            <span className="text-[10px] font-medium" style={{ color: i === breadcrumbs.length - 1 ? color : "var(--text-muted)" }}>{crumb}</span>
                        </React.Fragment>
                    ))}
                </div>
            )}

            {/* Header */}
            <div ref={headerRef} className="flex items-center gap-2 w-full px-3 py-2" style={{ flexShrink: 0 }}>
                <button onClick={handleToggle} onMouseDown={e => e.stopPropagation()} className="flex items-center gap-2 flex-1 text-left hover:opacity-80 transition-opacity min-w-0">
                    {isCollapsed ? <ChevronRight size={12} style={{ color, flexShrink: 0 }} /> : <ChevronDown size={12} style={{ color, flexShrink: 0 }} />}
                    <Layers size={12} style={{ color, flexShrink: 0 }} />
                    <span className="text-xs font-semibold" style={{ color: "var(--text-primary)", whiteSpace: "nowrap" }}>{title}</span>
                    {totalChildren > 0 && (
                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full flex-shrink-0" style={{ background: `color-mix(in srgb, ${color} 15%, transparent)`, color }}>
                            {totalChildren}
                        </span>
                    )}
                </button>

                {currentDepth > 0 && (
                    <span className="text-[8px] font-mono px-1 py-0.5 rounded flex-shrink-0" style={{ background: `color-mix(in srgb, ${color} 8%, transparent)`, color: "var(--text-muted)" }}>
                        L{currentDepth}
                    </span>
                )}

                {/* Fullscreen toggle button */}
                {!isCollapsed && hasCanvasChildren && onFullscreen && (
                    <button
                        onClick={(e) => { e.stopPropagation(); isFullscreen ? onBack?.() : onFullscreen?.(title); }}
                        onMouseDown={e => e.stopPropagation()}
                        className="p-1 rounded hover:bg-black/5 transition-colors flex-shrink-0"
                        title={isFullscreen ? "Exit fullscreen" : "Expand group"}
                    >
                        {isFullscreen ? <Minimize2 size={11} style={{ color: "var(--text-muted)" }} /> : <Maximize2 size={11} style={{ color: "var(--text-muted)" }} />}
                    </button>
                )}
            </div>

            {/* Mini-Canvas (expanded) */}
            {!isCollapsed && hasCanvasChildren && shouldRenderChildren && (
                <div
                    ref={canvasRef}
                    className="relative mx-3 mb-3 rounded-xl overflow-hidden"
                    style={{
                        height: isFullscreen ? "calc(100% - 80px)" : canvasHeight,
                        // Make it slightly darker but inherit parent color tone securely
                        background: `color-mix(in srgb, ${color} 5%, transparent)`,
                        border: `1px solid color-mix(in srgb, ${color} 15%, transparent)`,
                    }}
                >
                    {/* Dot grid */}
                    <div className="absolute inset-0" style={{
                        backgroundImage: `radial-gradient(circle, color-mix(in srgb, ${color} 15%, transparent) 1px, transparent 1px)`,
                        backgroundSize: "20px 20px",
                    }} />

                    {/* SVG Edges — tracking actual canvas dimensions accurately */}
                    <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 1, color: "var(--color-step)", opacity: 0.6 }}>
                        <EdgeMarkers id={markerId} />
                        {canvasEdges.map((edge) => {
                            const fromNode = canvasChildren.find((c) => c.id === edge.from);
                            const toNode = canvasChildren.find((c) => c.id === edge.to);
                            if (!fromNode || !toNode) return null;

                            const fW = fromNode.width ?? 80;
                            const fH = fromNode.height ?? 28;
                            const tW = toNode.width ?? 80;
                            const tH = toNode.height ?? 28;

                            const { x1, y1, x2, y2 } = computeEdgePath(
                                fromNode.x ?? 50, fromNode.y ?? 50, fW, fH,
                                toNode.x ?? 50, toNode.y ?? 50, tW, tH,
                                actualCanvasSize.w || canvasWidth, actualCanvasSize.h || canvasHeight,
                            );

                            const arrowType = edge.arrow ?? "triangle";

                            return (
                                <line
                                    key={`${edge.from}-${edge.to}`}
                                    x1={x1} y1={y1} x2={x2} y2={y2}
                                    stroke="currentColor"
                                    strokeWidth={1.5}
                                    strokeDasharray={edge.dashed !== false ? "4 3" : undefined}
                                    markerEnd={arrowType !== "none" ? markerUrl(arrowType, markerId) : undefined}
                                />
                            );
                        })}
                    </svg>

                    {/* Child nodes */}
                    {canvasChildren.map((child) => (
                        <div key={child.id} className="absolute" style={{ left: `${child.x ?? 50}%`, top: `${child.y ?? 50}%`, transform: "translate(-50%, -50%)", zIndex: 2 }}>
                            {child.render}
                        </div>
                    ))}
                </div>
            )}

            {/* Depth-limited placeholder */}
            {!isCollapsed && hasCanvasChildren && !shouldRenderChildren && (
                <div className="mx-3 mb-3 rounded-xl flex items-center justify-center py-4"
                    style={{ background: "rgba(0,0,0,0.1)", border: `1px dashed color-mix(in srgb, ${color} 20%, transparent)` }}>
                    <button onClick={() => onFullscreen?.(title)} className="flex items-center gap-2 text-[10px] transition-colors hover:opacity-80" style={{ color }}>
                        <Maximize2 size={11} />
                        <span>{totalChildren} nodes • Click to expand</span>
                    </button>
                </div>
            )}

            {/* Legacy simple children */}
            {!isCollapsed && !hasCanvasChildren && children && (
                <div className="mx-3 mb-3 flex flex-col gap-2">{children}</div>
            )}

            {/* Collapsed summary */}
            {isCollapsed && totalChildren > 0 && (
                <div className="px-3 pb-2 text-[10px]" style={{ color: "var(--text-muted)" }}>
                    {totalChildren} step{totalChildren !== 1 ? "s" : ""} inside
                </div>
            )}

            {/* Resize handle — bottom-right corner */}
            {!isCollapsed && !isFullscreen && onResize && (
                <div
                    data-resize
                    className="absolute bottom-0 right-0 cursor-nwse-resize group/resize"
                    style={{ width: 18, height: 18, zIndex: 20 }}
                    onMouseDown={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        const startX = e.clientX;
                        const startY = e.clientY;
                        const el = (e.target as HTMLElement).closest('.rounded-2xl') as HTMLElement;
                        if (!el) return;
                        const startW = el.offsetWidth;
                        const startH = el.offsetHeight;
                        const onMove = (ev: MouseEvent) => {
                            const newW = Math.max(200, startW + ev.clientX - startX);
                            const newH = Math.max(80, startH + ev.clientY - startY);
                            onResize(newW, newH);
                        };
                        const onUp = () => {
                            document.removeEventListener('mousemove', onMove);
                            document.removeEventListener('mouseup', onUp);
                        };
                        document.addEventListener('mousemove', onMove);
                        document.addEventListener('mouseup', onUp);
                    }}
                >
                    {/* Diagonal lines */}
                    <svg width="18" height="18" viewBox="0 0 18 18" className="opacity-30 group-hover/resize:opacity-70 transition-opacity">
                        <line x1="14" y1="4" x2="4" y2="14" stroke={color} strokeWidth="1.5" />
                        <line x1="14" y1="8" x2="8" y2="14" stroke={color} strokeWidth="1.5" />
                        <line x1="14" y1="12" x2="12" y2="14" stroke={color} strokeWidth="1.5" />
                    </svg>
                </div>
            )}
        </div>
    );

    if (isFullscreen && typeof document !== 'undefined') {
        return createPortal(content, document.body);
    }
    return content;
}
