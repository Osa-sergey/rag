import React, { useState } from "react";
import { ChevronRight, Layers, FileText, List } from "lucide-react";

export interface TreeNode {
    id: string;
    label: string;
    summary?: string;
    level: number;
    children?: TreeNode[];
    highlighted?: boolean;
}

export interface RaptorTreeViewProps {
    /** Root nodes */
    nodes: TreeNode[];
    /** Max visible levels */
    maxLevels?: number;
    /** Highlighted path (keyword trail) */
    highlightedPath?: string[];
    /** On node click */
    onNodeClick?: (node: TreeNode) => void;
}

function TreeNodeItem({
    node,
    expanded,
    onToggle,
    onNodeClick,
    highlightedPath,
}: {
    node: TreeNode;
    expanded: Set<string>;
    onToggle: (id: string) => void;
    onNodeClick?: (node: TreeNode) => void;
    highlightedPath?: Set<string>;
}) {
    const isExpanded = expanded.has(node.id);
    const isHighlighted = highlightedPath?.has(node.id);
    const hasChildren = node.children && node.children.length > 0;

    return (
        <div className="flex flex-col">
            <button
                onClick={() => { if (hasChildren) onToggle(node.id); onNodeClick?.(node); }}
                className="flex items-start gap-2 py-1.5 px-2 rounded-lg text-left transition-colors hover:bg-white/3"
                style={{ paddingLeft: node.level * 16 + 8 }}
            >
                {hasChildren ? (
                    <ChevronRight
                        size={10}
                        className="flex-shrink-0 mt-1 transition-transform"
                        style={{ transform: isExpanded ? "rotate(90deg)" : "none", color: "var(--text-muted)" }}
                    />
                ) : (
                    <div className="w-2.5 flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                        <Layers size={10} className="flex-shrink-0" style={{ color: isHighlighted ? "var(--color-concept)" : "var(--text-muted)" }} />
                        <span
                            className="text-[10px] font-medium truncate"
                            style={{
                                color: isHighlighted ? "var(--color-concept)" : "var(--text-primary)",
                                fontWeight: isHighlighted ? 700 : 500,
                            }}
                        >
                            L{node.level}: {node.label}
                        </span>
                        {hasChildren && (
                            <span className="text-[8px]" style={{ color: "var(--text-muted)" }}>({node.children!.length})</span>
                        )}
                    </div>
                    {node.summary && isExpanded && (
                        <p className="text-[9px] mt-0.5 leading-relaxed line-clamp-2" style={{ color: "var(--text-muted)" }}>
                            {node.summary}
                        </p>
                    )}
                </div>
            </button>
            {isExpanded && node.children?.map((child) => (
                <TreeNodeItem key={child.id} node={child} expanded={expanded} onToggle={onToggle} onNodeClick={onNodeClick} highlightedPath={highlightedPath} />
            ))}
        </div>
    );
}

export function RaptorTreeView({
    nodes,
    onNodeClick,
    highlightedPath = [],
}: RaptorTreeViewProps) {
    const [expanded, setExpanded] = useState<Set<string>>(() => {
        const init = new Set<string>();
        const addAll = (ns: TreeNode[]) => { for (const n of ns) { init.add(n.id); if (n.children) addAll(n.children); } };
        addAll(nodes);
        return init;
    });

    const highlightSet = new Set(highlightedPath);

    const toggle = (id: string) => {
        setExpanded((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id); else next.add(id);
            return next;
        });
    };

    return (
        <div
            className="rounded-xl overflow-hidden flex flex-col"
            style={{ background: "var(--bg-panel)", border: "var(--border-node)", width: 320, maxHeight: 400 }}
        >
            <div className="px-4 py-2.5 flex items-center gap-2" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <List size={13} style={{ color: "var(--text-muted)" }} />
                <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>RAPTOR Tree</span>
                <span className="text-[9px] ml-auto" style={{ color: "var(--text-muted)" }}>{nodes.length} root{nodes.length !== 1 ? "s" : ""}</span>
            </div>
            <div className="flex-1 overflow-y-auto py-1">
                {nodes.map((node) => (
                    <TreeNodeItem key={node.id} node={node} expanded={expanded} onToggle={toggle} onNodeClick={onNodeClick} highlightedPath={highlightSet} />
                ))}
            </div>
        </div>
    );
}
