import React from "react";
import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";
import { Tooltip } from "../Tooltip";

export interface KeyValueEntry {
    /** Key / label */
    key: string;
    /** Value (string, number, or React node for badges etc.) */
    value: React.ReactNode;
    /** Optional source indicator */
    source?: "default" | "global" | "step" | "override";
    /** Optional nested entries */
    children?: KeyValueEntry[];
}

export interface KeyValueListProps {
    /** Entries to display */
    entries: KeyValueEntry[];
    /** Show source badges */
    showSource?: boolean;
    /** Show legend (auto-shown when showSource=true) */
    showLegend?: boolean;
}

const sourceColors: Record<string, string> = {
    default: "var(--color-info)",
    global: "var(--color-keyword)",
    step: "var(--color-data)",
    override: "var(--color-concept)",
};

const sourceLabels: Record<string, string> = {
    default: "DEF",
    global: "GLB",
    step: "STP",
    override: "OVR",
};

const sourceDescriptions: Record<string, string> = {
    default: "Default — значение из Pydantic-схемы шага",
    global: "Global — переопределено на уровне pipeline globals",
    step: "Step — задано в конфигурации самого шага",
    override: "Override — финальное переопределение (высший приоритет)",
};

function SourceBadge({ source }: { source: string }) {
    return (
        <Tooltip content={sourceDescriptions[source]} position="left" delay={100}>
            <span
                className="text-[9px] font-bold px-1 py-0.5 rounded cursor-help"
                style={{
                    background: sourceColors[source],
                    color: "var(--text-inverse)",
                    opacity: 0.9,
                }}
            >
                {sourceLabels[source]}
            </span>
        </Tooltip>
    );
}

function SourceLegend() {
    return (
        <div
            className="flex items-center gap-3 px-3 py-1.5 text-[10px]"
            style={{
                borderBottom: "var(--border-node)",
                background: "var(--bg-panel)",
                color: "var(--text-muted)",
            }}
        >
            <span className="font-medium" style={{ color: "var(--text-secondary)" }}>Source:</span>
            {Object.entries(sourceLabels).map(([key, label]) => (
                <span key={key} className="inline-flex items-center gap-1">
                    <span
                        className="inline-block w-2 h-2 rounded-sm"
                        style={{ background: sourceColors[key] }}
                    />
                    <span>{label} — {sourceDescriptions[key].split(" — ")[1]}</span>
                </span>
            ))}
        </div>
    );
}

function EntryRow({
    entry,
    depth = 0,
    showSource,
}: {
    entry: KeyValueEntry;
    depth?: number;
    showSource?: boolean;
}) {
    const [expanded, setExpanded] = React.useState(true);
    const hasChildren = entry.children && entry.children.length > 0;

    return (
        <>
            <div
                className="flex items-center gap-2 py-1.5 px-2 rounded-md transition-colors hover:bg-[--bg-node-hover] group"
                style={{ paddingLeft: 8 + depth * 16 }}
            >
                {/* Expand toggle for nested */}
                {hasChildren ? (
                    <button
                        onClick={() => setExpanded(!expanded)}
                        className="flex-shrink-0"
                    >
                        <motion.div
                            animate={{ rotate: expanded ? 90 : 0 }}
                            transition={{ duration: 0.15 }}
                        >
                            <ChevronRight size={12} style={{ color: "var(--text-muted)" }} />
                        </motion.div>
                    </button>
                ) : (
                    <span style={{ width: 12 }} />
                )}

                {/* Key */}
                <span
                    className="font-mono text-xs font-medium flex-shrink-0"
                    style={{ color: "var(--color-keyword)" }}
                >
                    {entry.key}
                </span>

                {/* Separator */}
                <span className="flex-1 border-b border-dotted" style={{ borderColor: "var(--text-muted)", opacity: 0.3 }} />

                {/* Source badge with tooltip */}
                {showSource && entry.source && (
                    <SourceBadge source={entry.source} />
                )}

                {/* Value */}
                <span className="font-mono text-xs text-right" style={{ color: "var(--text-primary)" }}>
                    {entry.value}
                </span>
            </div>

            {/* Children */}
            {hasChildren && expanded && (
                <div>
                    {entry.children!.map((child, i) => (
                        <EntryRow
                            key={child.key + i}
                            entry={child}
                            depth={depth + 1}
                            showSource={showSource}
                        />
                    ))}
                </div>
            )}
        </>
    );
}

export function KeyValueList({ entries, showSource = false, showLegend }: KeyValueListProps) {
    const shouldShowLegend = showLegend ?? showSource;

    return (
        <div
            className="rounded-lg overflow-hidden"
            style={{
                background: "var(--bg-node)",
                border: "var(--border-node)",
            }}
        >
            {shouldShowLegend && <SourceLegend />}
            {entries.map((entry, i) => (
                <EntryRow key={entry.key + i} entry={entry} showSource={showSource} />
            ))}
        </div>
    );
}

