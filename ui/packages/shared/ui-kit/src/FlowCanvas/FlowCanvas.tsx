import React, { useState, useRef, useCallback, useEffect } from "react";
import { ZoomIn, ZoomOut, Maximize2, Map } from "lucide-react";

export interface FlowNodePort {
    id: string;
    /** 'left' = input, 'right' = output */
    side: 'left' | 'right';
    /** Index among same-side ports (0-based) */
    index: number;
    /** Total number of ports on this side */
    total: number;
    /** Data type for type-checking on connect */
    dataType?: string;
}

export interface FlowNode {
    id: string;
    x: number;
    y: number;
    width?: number;
    height?: number;
    content: React.ReactNode;
    /** Port metadata for edge anchoring */
    ports?: FlowNodePort[];
}

export interface FlowEdge {
    id: string;
    from: string;
    to: string;
    /** Specific output port id on source node */
    fromPort?: string;
    /** Specific input port id on target node */
    toPort?: string;
    label?: React.ReactNode;
    /** Visual variant */
    variant?: "default" | "error" | "animated" | "dependency";
}

/** Connection request emitted when user drags from a source port to a target port */
export interface ConnectionRequest {
    fromNodeId: string;
    fromPortId: string;
    fromPortType?: string;
    toNodeId: string;
    toPortId: string;
    toPortType?: string;
}

/** Drop event emitted when user drops a palette item onto the canvas */
export interface CanvasDropEvent {
    x: number;
    y: number;
    /** Arbitrary data from the drag source (JSON string from dataTransfer) */
    data: string;
}

/** A rectangular zone on the canvas where nodes cannot be placed */
export interface ReservedZone {
    x: number;
    y: number;
    width: number;
    height: number;
}

export interface FlowCanvasProps {
    /** Nodes to place on canvas */
    nodes?: FlowNode[];
    /** Edges between nodes */
    edges?: FlowEdge[];
    /** Show minimap */
    showMinimap?: boolean;
    /** Show zoom controls */
    showControls?: boolean;
    /** Canvas height */
    height?: number | string;
    /** Background variant */
    background?: "dots" | "lines" | "none";
    /** Empty state slot */
    emptyState?: React.ReactNode;
    /** On Node Drag Handler */
    onNodeDrag?: (id: string, x: number, y: number) => void;
    /** Called when user completes an edge connection between ports */
    onConnect?: (connection: ConnectionRequest) => void;
    /** Called when a draggable is dropped onto the canvas */
    onCanvasDrop?: (event: CanvasDropEvent) => void;
    /** Called when user presses Delete with selection */
    onDelete?: (nodeIds: string[], edgeIds: string[]) => void;
    /** Called when user clicks a node */
    onNodeClick?: (nodeId: string) => void;
    /** Selected node id (controlled) */
    selectedNodeId?: string;
    /** Selected edge id (controlled) */
    selectedEdgeId?: string;
    /** Rectangular zones where nodes cannot be placed (e.g. toolbar overlay) */
    reservedZones?: ReservedZone[];
}

// ─── Port position helpers ───────────────────────────────────────

function getPortPosition(
    node: FlowNode,
    port: FlowNodePort,
    measured?: Map<string, { relX: number; relY: number }>,
): { x: number; y: number } {
    // Use DOM-measured position if available
    const key = `${node.id}:${port.id}`;
    const m = measured?.get(key);
    if (m) {
        return { x: node.x + m.relX, y: node.y + m.relY };
    }

    // Fallback: estimate from node dimensions
    const w = node.width ?? 200;
    const h = node.height ?? 80;
    const portRowHeight = 16;
    const totalPortsHeight = port.total * portRowHeight;
    const portSectionStart = h - totalPortsHeight - 14;
    const portY = portSectionStart + port.index * portRowHeight + portRowHeight / 2;

    if (port.side === "right") {
        return { x: node.x + w, y: node.y + portY };
    }
    return { x: node.x, y: node.y + portY };
}

function getDefaultAnchor(node: FlowNode, side: "left" | "right"): { x: number; y: number } {
    const w = node.width ?? 200;
    const h = node.height ?? 80;
    return side === "right"
        ? { x: node.x + w, y: node.y + h / 2 }
        : { x: node.x, y: node.y + h / 2 };
}

// ─── Bezier path generator ──────────────────────────────────────

function bezierPath(
    fx: number, fy: number, tx: number, ty: number,
): string {
    const dx = Math.abs(tx - fx);
    const cp = Math.max(60, dx * 0.4);
    return `M ${fx} ${fy} C ${fx + cp} ${fy}, ${tx - cp} ${ty}, ${tx} ${ty}`;
}

// ─── DFS cycle check ────────────────────────────────────────────

function wouldCreateCycle(
    edges: FlowEdge[],
    fromNodeId: string,
    toNodeId: string,
): boolean {
    if (fromNodeId === toNodeId) return true;
    const adj = new globalThis.Map<string, string[]>();
    for (const e of edges) {
        if (!adj.has(e.from)) adj.set(e.from, []);
        adj.get(e.from)!.push(e.to);
    }
    // Add the proposed edge
    if (!adj.has(fromNodeId)) adj.set(fromNodeId, []);
    adj.get(fromNodeId)!.push(toNodeId);

    // DFS from toNodeId to see if we can reach fromNodeId
    const visited = new Set<string>();
    const stack = [toNodeId];
    while (stack.length > 0) {
        const curr = stack.pop()!;
        if (curr === fromNodeId) return true;
        if (visited.has(curr)) continue;
        visited.add(curr);
        for (const next of adj.get(curr) ?? []) {
            stack.push(next);
        }
    }
    return false;
}

/**
 * FlowCanvas — visual canvas for DAG/graph display with interactive edge creation.
 * Lightweight Storybook-compatible implementation inspired by @xyflow/react patterns.
 */
export function FlowCanvas({
    nodes = [],
    edges = [],
    showMinimap = false,
    showControls = true,
    height = 500,
    background = "dots",
    emptyState,
    onNodeDrag,
    onConnect,
    onCanvasDrop,
    onDelete,
    onNodeClick,
    selectedNodeId,
    selectedEdgeId,
    reservedZones = [],
    fitViewOnInit = false,
}: FlowCanvasProps & { fitViewOnInit?: boolean }) {
    const [zoom, setZoom] = useState(1);
    const [pan, setPan] = useState({ x: 0, y: 0 });
    const canvasRef = useRef<HTMLDivElement>(null);
    const transformRef = useRef<HTMLDivElement>(null);
    const isDragging = useRef(false);
    const lastPos = useRef({ x: 0, y: 0 });
    const draggingNode = useRef<string | null>(null);

    // ── Connection line state ──
    const [connecting, setConnecting] = useState<{
        fromNodeId: string;
        fromPortId: string;
        fromPortType?: string;
        startX: number;
        startY: number;
        currentX: number;
        currentY: number;
    } | null>(null);

    // ── DOM-based port measurement ──
    // Stores relative (to node) port dot positions measured from the DOM
    const portOffsetsRef = useRef<globalThis.Map<string, { relX: number; relY: number }>>(new globalThis.Map());
    const [portMeasureGen, setPortMeasureGen] = useState(0);

    useEffect(() => {
        const tEl = transformRef.current;
        if (!tEl || nodes.length === 0) return;

        const measure = () => {
            const newMap = new globalThis.Map<string, { relX: number; relY: number }>();

            for (const node of nodes) {
                const nEl = tEl.querySelector(`[data-id="${node.id}"]`) as HTMLElement;
                if (!nEl) continue;
                const nRect = nEl.getBoundingClientRect();
                if (nRect.width === 0) continue;

                const portEls = nEl.querySelectorAll('[data-port-id]');
                portEls.forEach(pe => {
                    const pid = pe.getAttribute('data-port-id');
                    const side = pe.getAttribute('data-port-side');
                    if (!pid || !side) return;

                    const dot = pe.querySelector('.rounded-full') as HTMLElement;
                    if (!dot) return;

                    const currentScale = nRect.width > 0 && nEl.offsetWidth > 0 ? nRect.width / nEl.offsetWidth : 1;
                    const dRect = dot.getBoundingClientRect();
                    const relX = (dRect.left + dRect.width / 2 - nRect.left) / currentScale;
                    const relY = (dRect.top + dRect.height / 2 - nRect.top) / currentScale;

                    newMap.set(`${node.id}:${pid}`, { relX, relY });
                });
            }

            // Only trigger re-render if measurements changed
            let changed = newMap.size !== portOffsetsRef.current.size;
            if (!changed) {
                newMap.forEach((v: { relX: number, relY: number }, k: string) => {
                    const old = portOffsetsRef.current.get(k);
                    if (!old || Math.abs(old.relX - v.relX) > 1 || Math.abs(old.relY - v.relY) > 1) {
                        changed = true;
                    }
                });
            }

            if (changed) {
                portOffsetsRef.current = newMap;
                setPortMeasureGen(g => g + 1);
            }
        };

        let rafId: number;
        // Observe size changes of all node elements to recalculate ports dynamically (fixes issues when CSS transitions are running)
        const ro = new ResizeObserver(() => {
            cancelAnimationFrame(rafId);
            rafId = requestAnimationFrame(measure);
        });

        // Add inner node elements to the observer so it correctly fires continuously during their CSS transitions
        for (const node of nodes) {
            const nEl = tEl.querySelector(`[data-id="${node.id}"]`) as HTMLElement;
            if (nEl && nEl.firstElementChild) {
                ro.observe(nEl.firstElementChild);
            } else if (nEl) {
                ro.observe(nEl);
            }
        }

        // Add transitionend listener to ensure the final measurement is perfectly aligned if RO misses the final frame
        const onTransitionEnd = (e: TransitionEvent) => {
            if (e.propertyName === "width" || e.propertyName === "height") {
                cancelAnimationFrame(rafId);
                rafId = requestAnimationFrame(measure);
            }
        };
        tEl.addEventListener("transitionend", onTransitionEnd);

        rafId = requestAnimationFrame(measure);

        return () => {
            ro.disconnect();
            tEl.removeEventListener("transitionend", onTransitionEnd);
            cancelAnimationFrame(rafId);
        };
    }, [nodes, zoom]);

    // ── Fit View ──
    const handleFitView = useCallback(() => {
        if (nodes.length === 0 || !canvasRef.current) return;
        const rect = canvasRef.current.getBoundingClientRect();

        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        nodes.forEach(n => {
            minX = Math.min(minX, n.x);
            minY = Math.min(minY, n.y);
            maxX = Math.max(maxX, n.x + (n.width ?? 200));
            maxY = Math.max(maxY, n.y + (n.height ?? 80));
        });

        const padding = 40;
        const contentW = maxX - minX + padding * 2;
        const contentH = maxY - minY + padding * 2;

        const scaleX = rect.width / contentW;
        const scaleY = rect.height / contentH;
        let newZoom = Math.min(scaleX, scaleY, 1.5);
        newZoom = Math.max(newZoom, 0.2);

        const cx = minX + (maxX - minX) / 2;
        const cy = minY + (maxY - minY) / 2;

        setZoom(newZoom);
        setPan({
            x: rect.width / 2 - cx * newZoom,
            y: rect.height / 2 - cy * newZoom
        });
    }, [nodes]);

    // ── Initial Fit View ──
    useEffect(() => {
        if (fitViewOnInit && nodes.length > 0) {
            const timer = setTimeout(() => handleFitView(), 50); // slight delay ensures DOM sizing is ready
            return () => clearTimeout(timer);
        }
    }, [fitViewOnInit, handleFitView]);

    // ── Pan ──
    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        const nodeEl = (e.target as HTMLElement).closest("[data-node]");
        const portEl = (e.target as HTMLElement).closest("[data-port-handle]");
        if (nodeEl || portEl) return;
        isDragging.current = true;
        lastPos.current = { x: e.clientX, y: e.clientY };
    }, []);

    // ── Node drag ──
    const handleNodeMouseDown = useCallback((e: React.MouseEvent, nodeId: string) => {
        let el: HTMLElement | null = e.target as HTMLElement;
        const nodeWrapper = e.currentTarget as HTMLElement;
        while (el && el !== nodeWrapper) {
            const tag = el.tagName?.toLowerCase();
            if (tag === 'button' || tag === 'a' || tag === 'input' || tag === 'select' ||
                el.hasAttribute('data-resize') || el.hasAttribute('data-interactive') ||
                el.hasAttribute('data-port-handle')) {
                return;
            }
            el = el.parentElement;
        }
        draggingNode.current = nodeId;
        lastPos.current = { x: e.clientX, y: e.clientY };
        onNodeClick?.(nodeId);
    }, [onNodeClick]);

    // ── Port drag start (begin edge creation) ──
    const handlePortMouseDown = useCallback((
        e: React.MouseEvent,
        nodeId: string,
        portId: string,
        portType?: string,
        startX?: number,
        startY?: number,
    ) => {
        e.stopPropagation();
        e.preventDefault();
        if (!onConnect) return;
        setConnecting({
            fromNodeId: nodeId,
            fromPortId: portId,
            fromPortType: portType,
            startX: startX ?? e.clientX,
            startY: startY ?? e.clientY,
            currentX: startX ?? e.clientX,
            currentY: startY ?? e.clientY,
        });
    }, [onConnect]);

    // ── Mouse move (pan, node drag, connection line) ──
    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        // Connection line
        if (connecting) {
            // Convert screen coords to canvas coords
            const rect = canvasRef.current?.getBoundingClientRect();
            if (rect) {
                const canvasX = (e.clientX - rect.left - pan.x) / zoom;
                const canvasY = (e.clientY - rect.top - pan.y) / zoom;
                setConnecting(prev => prev ? { ...prev, currentX: canvasX, currentY: canvasY } : null);
            }
            return;
        }

        // Node dragging
        if (draggingNode.current && onNodeDrag) {
            const dx = (e.clientX - lastPos.current.x) / zoom;
            const dy = (e.clientY - lastPos.current.y) / zoom;
            const n = nodes.find(n => n.id === draggingNode.current);
            if (n) {
                let newX = n.x + dx;
                let newY = n.y + dy;
                const GAP = 8;
                const nw = n.width ?? 0;
                const nh = n.height ?? 0;
                for (const other of nodes) {
                    if (other.id === n.id) continue;
                    const ow = other.width ?? 0;
                    const oh = other.height ?? 0;
                    const overlapX = newX < other.x + ow + GAP && newX + nw + GAP > other.x;
                    const overlapY = newY < other.y + oh + GAP && newY + nh + GAP > other.y;
                    if (overlapX && overlapY) {
                        const pushRight = (other.x + ow + GAP) - newX;
                        const pushLeft = newX + nw + GAP - other.x;
                        const pushDown = (other.y + oh + GAP) - newY;
                        const pushUp = newY + nh + GAP - other.y;
                        const minPush = Math.min(pushRight, pushLeft, pushDown, pushUp);
                        if (minPush === pushRight) newX = other.x + ow + GAP;
                        else if (minPush === pushLeft) newX = other.x - nw - GAP;
                        else if (minPush === pushDown) newY = other.y + oh + GAP;
                        else newY = other.y - nh - GAP;
                    }
                }
                // Check reserved zones (toolbar, etc.)
                for (const zone of reservedZones) {
                    const overlapX = newX < zone.x + zone.width + GAP && newX + nw + GAP > zone.x;
                    const overlapY = newY < zone.y + zone.height + GAP && newY + nh + GAP > zone.y;
                    if (overlapX && overlapY) {
                        const pushRight = (zone.x + zone.width + GAP) - newX;
                        const pushLeft = newX + nw + GAP - zone.x;
                        const pushDown = (zone.y + zone.height + GAP) - newY;
                        const pushUp = newY + nh + GAP - zone.y;
                        const minPush = Math.min(pushRight, pushLeft, pushDown, pushUp);
                        if (minPush === pushRight) newX = zone.x + zone.width + GAP;
                        else if (minPush === pushLeft) newX = zone.x - nw - GAP;
                        else if (minPush === pushDown) newY = zone.y + zone.height + GAP;
                        else newY = zone.y - nh - GAP;
                    }
                }
                onNodeDrag(n.id, newX, newY);
            }
            lastPos.current = { x: e.clientX, y: e.clientY };
            return;
        }

        // Canvas pan
        if (!isDragging.current) return;
        const dx = e.clientX - lastPos.current.x;
        const dy = e.clientY - lastPos.current.y;
        setPan((p) => ({
            x: p.x + dx,
            y: p.y + dy,
        }));
        lastPos.current = { x: e.clientX, y: e.clientY };
    }, [zoom, nodes, onNodeDrag, connecting, pan]);

    // ── Mouse up (end drag or complete connection) ──
    const handleMouseUp = useCallback((e: React.MouseEvent) => {
        // Complete connection — check if over a port
        if (connecting && onConnect) {
            const portEl = (e.target as HTMLElement).closest("[data-port-handle]");
            if (portEl) {
                const toNodeId = portEl.getAttribute("data-node-id") ?? "";
                const toPortId = portEl.getAttribute("data-port-id") ?? "";
                const toPortType = portEl.getAttribute("data-port-type") ?? undefined;
                const toSide = portEl.getAttribute("data-port-side") ?? "";

                // Only connect output → input
                if (toSide === "left" && toNodeId !== connecting.fromNodeId) {
                    // Cycle check
                    if (!wouldCreateCycle(edges, connecting.fromNodeId, toNodeId)) {
                        onConnect({
                            fromNodeId: connecting.fromNodeId,
                            fromPortId: connecting.fromPortId,
                            fromPortType: connecting.fromPortType,
                            toNodeId,
                            toPortId,
                            toPortType,
                        });
                    }
                }
            }
            setConnecting(null);
        }
        isDragging.current = false;
        draggingNode.current = null;
    }, [connecting, onConnect, edges]);

    // ── Wheel zoom ──
    const handleWheel = useCallback((e: React.WheelEvent) => {
        setZoom((z) => Math.min(1.5, Math.max(0.5, z - e.deltaY * 0.001)));
    }, []);

    // ── Drop from palette ──
    const handleDragOver = useCallback((e: React.DragEvent) => {
        if (onCanvasDrop) {
            e.preventDefault();
            e.dataTransfer.dropEffect = "copy";
        }
    }, [onCanvasDrop]);

    const handleDrop = useCallback((e: React.DragEvent) => {
        if (!onCanvasDrop || !canvasRef.current) return;
        e.preventDefault();
        const rect = canvasRef.current.getBoundingClientRect();
        const x = (e.clientX - rect.left - pan.x) / zoom;
        const y = (e.clientY - rect.top - pan.y) / zoom;
        const data = e.dataTransfer.getData("application/json") || e.dataTransfer.getData("text/plain") || "";
        onCanvasDrop({ x, y, data });
    }, [onCanvasDrop, pan, zoom]);

    // ── Keyboard ──
    const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
        if ((e.key === "Delete" || e.key === "Backspace") && onDelete) {
            const selNodes = selectedNodeId ? [selectedNodeId] : [];
            const selEdges = selectedEdgeId ? [selectedEdgeId] : [];
            if (selNodes.length > 0 || selEdges.length > 0) {
                onDelete(selNodes, selEdges);
            }
        }
    }, [selectedNodeId, selectedEdgeId, onDelete]);

    // ── Background pattern ──
    const bgPattern = background === "dots"
        ? "radial-gradient(circle, rgba(255,255,255,0.04) 1px, transparent 1px)"
        : background === "lines"
            ? "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)"
            : "none";

    // ── Edge rendering helper ──
    const renderEdge = (edge: FlowEdge) => {
        const fromNode = nodes.find(n => n.id === edge.from);
        const toNode = nodes.find(n => n.id === edge.to);
        if (!fromNode || !toNode) return null;

        // Port-level anchoring
        const srcPort = edge.fromPort && fromNode.ports?.find(p => p.id === edge.fromPort && p.side === 'right');
        const tgtPort = edge.toPort && toNode.ports?.find(p => p.id === edge.toPort && p.side === 'left');

        let fx: number, fy: number, tx: number, ty: number;

        if (srcPort) {
            const pos = getPortPosition(fromNode, srcPort, portOffsetsRef.current);
            fx = pos.x; fy = pos.y;
        } else {
            const pos = getDefaultAnchor(fromNode, "right");
            fx = pos.x; fy = pos.y;
        }

        if (tgtPort) {
            const pos = getPortPosition(toNode, tgtPort, portOffsetsRef.current);
            tx = pos.x; ty = pos.y;
        } else {
            const pos = getDefaultAnchor(toNode, "left");
            tx = pos.x; ty = pos.y;
        }

        const variant = edge.variant ?? (edge.id?.includes("err") ? "error" : "default");
        const isError = variant === "error";
        const isDep = variant === "dependency";
        const isAnimated = variant === "animated";
        const isSelected = edge.id === selectedEdgeId;

        const strokeColor = isError
            ? "rgba(239,68,68,0.5)"
            : isDep ? "rgba(148,163,184,0.4)"
                : isSelected ? "rgba(99,102,241,0.8)"
                    : "rgba(99,102,241,0.35)";

        const markerId = isError ? "fc-arrow-err" : "fc-arrow";
        const path = bezierPath(fx, fy, tx, ty);

        return (
            <g key={edge.id}>
                {/* Source port dot */}
                <circle cx={fx} cy={fy} r={5}
                    fill={isError ? "rgba(239,68,68,0.2)" : "rgba(34,197,94,0.3)"}
                    stroke={isError ? "rgba(239,68,68,0.6)" : "rgba(34,197,94,0.7)"}
                    strokeWidth={1.5} />
                {/* Bezier curve */}
                <path
                    d={path}
                    fill="none"
                    stroke={strokeColor}
                    strokeWidth={isSelected ? 3 : 2}
                    strokeDasharray={isError || isDep ? "6 3" : "none"}
                    markerEnd={`url(#${markerId})`}
                />
                {/* Animated particle */}
                {isAnimated && (
                    <circle r={3} fill="var(--color-info, #6366f1)">
                        <animateMotion dur="1.5s" repeatCount="indefinite" path={path} />
                    </circle>
                )}
                {/* Target port dot */}
                <circle cx={tx} cy={ty} r={5}
                    fill={isError ? "rgba(239,68,68,0.15)" : "rgba(99,102,241,0.2)"}
                    stroke={isError ? "rgba(239,68,68,0.5)" : "rgba(99,102,241,0.6)"}
                    strokeWidth={1.5} />
            </g>
        );
    };

    // ── Port handle rendering (interactive connection dots) ──
    const renderPortHandles = (node: FlowNode) => {
        if (!node.ports || !onConnect) return null;
        return node.ports.map(port => {
            const pos = getPortPosition(node, port, portOffsetsRef.current);
            const isOutput = port.side === "right";
            const size = 14; // Larger invisible hit area

            return (
                <div
                    key={`${node.id}-${port.id}-handle`}
                    data-port-handle
                    data-node-id={node.id}
                    data-port-id={port.id}
                    data-port-side={port.side}
                    data-port-type={port.dataType ?? ""}
                    className="absolute rounded-full"
                    style={{
                        left: pos.x - size / 2,
                        top: pos.y - size / 2,
                        width: size,
                        height: size,
                        background: "transparent",
                        cursor: isOutput ? "crosshair" : "pointer",
                        zIndex: 50,
                    }}
                    onMouseDown={(e) => {
                        if (isOutput) {
                            handlePortMouseDown(e, node.id, port.id, port.dataType, pos.x, pos.y);
                        }
                    }}
                />
            );
        });
    };

    return (
        <div
            ref={canvasRef}
            className="relative overflow-hidden select-none h-full w-full"
            style={{
                background: "var(--bg-canvas, #0a0a0f)",
                backgroundImage: bgPattern,
                backgroundSize: background === "dots" ? "20px 20px" : "40px 40px",
                cursor: connecting ? "crosshair" : isDragging.current ? "grabbing" : "grab",
                outline: "none",
            }}
            tabIndex={0}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onKeyDown={handleKeyDown}
        >
            {/* Transform layer */}
            <div
                ref={transformRef}
                className="absolute inset-0"
                style={{
                    transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                    transformOrigin: "0 0",
                    transition: isDragging.current || draggingNode.current ? "none" : "transform 0.1s ease",
                }}
            >
                {/* SVG edges */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ overflow: "visible" }}>
                    <defs>
                        <marker id="fc-arrow" viewBox="0 0 10 8" refX="10" refY="4" markerWidth="8" markerHeight="6" orient="auto-start-reverse">
                            <path d="M 0 0 L 10 4 L 0 8 z" fill="rgba(99,102,241,0.5)" />
                        </marker>
                        <marker id="fc-arrow-err" viewBox="0 0 10 8" refX="10" refY="4" markerWidth="8" markerHeight="6" orient="auto-start-reverse">
                            <path d="M 0 0 L 10 4 L 0 8 z" fill="rgba(239,68,68,0.5)" />
                        </marker>
                    </defs>
                    {edges.map(renderEdge)}

                    {/* Connection line (rubber-band while dragging) */}
                    {connecting && (
                        <path
                            d={bezierPath(connecting.startX, connecting.startY, connecting.currentX, connecting.currentY)}
                            fill="none"
                            stroke="rgba(99,102,241,0.6)"
                            strokeWidth={2}
                            strokeDasharray="4 4"
                        />
                    )}
                </svg>

                {/* Nodes */}
                {nodes.map((node) => (
                    <div
                        key={node.id}
                        data-node
                        data-id={node.id}
                        className="absolute"
                        style={{
                            left: node.x,
                            top: node.y,
                            width: node.width,
                            height: node.height,
                            cursor: "grab",
                            zIndex: node.id === selectedNodeId ? 30 : 10,
                        }}
                        onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
                    >
                        {node.content}
                    </div>
                ))}

                {/* Interactive port handles */}
                {nodes.map(renderPortHandles)}

                {/* Edge labels */}
                {edges.map((edge) => {
                    const fromNode = nodes.find(n => n.id === edge.from);
                    const toNode = nodes.find(n => n.id === edge.to);
                    if (!fromNode || !toNode || !edge.label) return null;

                    // Use port-aware anchor positions for label placement
                    const srcPort = edge.fromPort && fromNode.ports?.find(p => p.id === edge.fromPort && p.side === 'right');
                    const tgtPort = edge.toPort && toNode.ports?.find(p => p.id === edge.toPort && p.side === 'left');
                    const src = srcPort ? getPortPosition(fromNode, srcPort, portOffsetsRef.current) : getDefaultAnchor(fromNode, "right");
                    const tgt = tgtPort ? getPortPosition(toNode, tgtPort, portOffsetsRef.current) : getDefaultAnchor(toNode, "left");

                    const lx = (src.x + tgt.x) / 2;
                    const ly = (src.y + tgt.y) / 2;

                    return (
                        <div key={`label-${edge.id}`} className="absolute" style={{ left: lx, top: ly, transform: "translate(-50%, -50%)", zIndex: 20 }}>
                            {edge.label}
                        </div>
                    );
                })}
            </div>

            {/* Empty state */}
            {nodes.length === 0 && emptyState && (
                <div className="absolute inset-0 flex items-center justify-center">
                    {emptyState}
                </div>
            )}

            {/* Zoom controls */}
            {showControls && (
                <div
                    className="absolute bottom-3 left-3 flex flex-col gap-0.5 rounded-lg overflow-hidden"
                    style={{ background: "var(--bg-panel)", border: "var(--border-node)" }}
                >
                    <button onClick={() => setZoom((z) => Math.min(2, z + 0.15))} className="p-2 hover:bg-white/5 transition-colors" style={{ color: "var(--text-muted)" }}>
                        <ZoomIn size={14} />
                    </button>
                    <button onClick={() => setZoom((z) => Math.max(0.3, z - 0.15))} className="p-2 hover:bg-white/5 transition-colors" style={{ color: "var(--text-muted)" }}>
                        <ZoomOut size={14} />
                    </button>
                    <button onClick={handleFitView} className="p-2 hover:bg-white/5 transition-colors" style={{ color: "var(--text-muted)" }}>
                        <Maximize2 size={14} />
                    </button>
                </div>
            )}

            {/* Minimap */}
            {showMinimap && nodes.length > 0 && (() => {
                let mmMinX = Infinity, mmMinY = Infinity, mmMaxX = -Infinity, mmMaxY = -Infinity;
                nodes.forEach(n => {
                    mmMinX = Math.min(mmMinX, n.x);
                    mmMinY = Math.min(mmMinY, n.y);
                    mmMaxX = Math.max(mmMaxX, n.x + (n.width ?? 200));
                    mmMaxY = Math.max(mmMaxY, n.y + (n.height ?? 80));
                });
                const mmW = Math.max(mmMaxX - mmMinX, 100) + 200;
                const mmH = Math.max(mmMaxY - mmMinY, 100) + 200;

                return (
                    <div
                        className="absolute bottom-3 right-3 rounded-lg overflow-hidden"
                        style={{
                            width: 120,
                            height: 80,
                            background: "rgba(0,0,0,0.4)",
                            border: "1px solid rgba(255,255,255,0.08)",
                            backdropFilter: "blur(6px)",
                        }}
                    >
                        <div className="relative w-full h-full p-1">
                            <Map size={8} className="absolute top-1 left-1" style={{ color: "var(--text-muted)", opacity: 0.5 }} />
                            {nodes.map((node) => (
                                <div
                                    key={node.id}
                                    className="absolute rounded-sm"
                                    style={{
                                        width: Math.max(6, ((node.width ?? 200) / mmW) * 100) + "%",
                                        height: Math.max(3, ((node.height ?? 80) / mmH) * 100) + "%",
                                        background: node.id === selectedNodeId ? "rgba(99,102,241,0.9)" : "rgba(99,102,241,0.5)",
                                        left: `${((node.x - mmMinX + 100) / mmW) * 100}%`,
                                        top: `${((node.y - mmMinY + 100) / mmH) * 100}%`,
                                    }}
                                />
                            ))}
                        </div>
                    </div>
                );
            })()}

            {/* Zoom indicator */}
            <div className="absolute top-3 right-3 px-2 py-0.5 rounded text-[9px] font-mono" style={{ background: "var(--bg-panel)", color: "var(--text-muted)", border: "var(--border-node)" }}>
                {Math.round(zoom * 100)}%
            </div>
        </div>
    );
}
