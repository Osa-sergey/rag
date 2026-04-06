import { useState } from "react";
import { Timeline, TimelineItem } from "../Timeline";
import { Badge } from "../Badge";
import { DiffViewer } from "../DiffViewer";
import { History, ChevronLeft } from "lucide-react";

export interface ConceptChange {
    type: "add" | "remove" | "modify";
    field: string;
    oldValue?: string;
    newValue?: string;
}

export interface ConceptVersion {
    id: string;
    version: string;
    date: string;
    author: string;
    description: string;
    changes: ConceptChange[];
}

export interface VersionTimelineProps {
    versions: ConceptVersion[];
    currentVersionId?: string;
    onRestore?: (versionId: string) => void;
}

export function VersionTimeline({
    versions,
    currentVersionId,
    onRestore,
}: VersionTimelineProps) {
    const [compareSource, setCompareSource] = useState<ConceptVersion | null>(null);
    const [compareTarget, setCompareTarget] = useState<ConceptVersion | null>(null);

    const handleCompare = (targetIdx: number) => {
        if (targetIdx < versions.length - 1) {
            setCompareTarget(versions[targetIdx]);
            setCompareSource(versions[targetIdx + 1]);
        }
    };

    const timelineItems: TimelineItem[] = versions.map((v, idx) => {
        const isActive = v.id === (currentVersionId || versions[0]?.id);
        const isOldest = idx === versions.length - 1;

        return {
            id: v.id,
            title: `${v.version} - ${v.author}`,
            description: v.description,
            date: v.date,
            color: isActive ? "var(--color-success)" : "var(--color-info)",
            active: isActive,
            action: isOldest ? undefined : {
                label: "Compare with previous",
                onClick: () => handleCompare(idx)
            }
        };
    });

    const getChangeBadgeColor = (type: string) => {
        if (type === "add") return "success";
        if (type === "remove") return "error";
        return "warning";
    };

    return (
        <div className="flex flex-col h-full rounded-xl overflow-hidden shadow-2xl" style={{ background: "var(--bg-panel)", border: "1px solid var(--border-panel)" }}>

            {/* Header */}
            <div className="flex-shrink-0 flex items-center justify-between p-4 border-b relative overflow-hidden" style={{ borderColor: "var(--border-panel)", background: "var(--bg-node)" }}>
                <div className="absolute inset-0 opacity-10 pointer-events-none" style={{ background: "linear-gradient(90deg, var(--color-info), transparent)" }} />
                <div className="z-10 flex items-center gap-2">
                    <History size={16} style={{ color: "var(--color-info)" }} />
                    <h2 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
                        Version History
                    </h2>
                    <Badge variant="info">{versions.length} versions</Badge>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-y-auto flex flex-col relative">
                {compareSource && compareTarget ? (
                    <div className="absolute inset-0 bg-[var(--bg-panel)] flex flex-col animate-in slide-in-from-right-8 fade-in z-20">
                        {/* Compare Header */}
                        <div className="flex-shrink-0 p-3 border-b flex items-center gap-3 bg-[var(--bg-node)]" style={{ borderColor: "var(--border-node)" }}>
                            <button
                                onClick={() => { setCompareSource(null); setCompareTarget(null); }}
                                className="p-1.5 rounded-lg hover:bg-white/5 transition-colors"
                            >
                                <ChevronLeft size={16} style={{ color: "var(--text-primary)" }} />
                            </button>
                            <div className="flex-1 flex items-center gap-3 text-xs">
                                <Badge variant="info">{compareSource.version}</Badge>
                                <span style={{ color: "var(--text-muted)" }}>compared to</span>
                                <Badge variant="success">{compareTarget.version}</Badge>
                            </div>
                            <button
                                onClick={() => onRestore?.(compareTarget.id)}
                                className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded border hover:bg-white/5 transition-colors"
                                style={{ borderColor: "var(--border-node)", color: "var(--text-primary)" }}
                            >
                                Restore {compareTarget.version}
                            </button>
                        </div>

                        {/* Changes List */}
                        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
                            <h3 className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--text-secondary)" }}>
                                Detailed Changes ({compareTarget.changes.length})
                            </h3>
                            <div className="flex flex-col gap-3">
                                {compareTarget.changes.map((change, i) => (
                                    <div key={i} className="flex flex-col gap-2 p-3 rounded-lg border" style={{ borderColor: "var(--border-node)", background: "var(--bg-node)" }}>
                                        <div className="flex items-center gap-2">
                                            <Badge variant={getChangeBadgeColor(change.type) as any}>{change.type.toUpperCase()}</Badge>
                                            <span className="text-xs font-mono font-bold" style={{ color: "var(--text-primary)" }}>{change.field}</span>
                                        </div>
                                        {(change.oldValue || change.newValue) && (
                                            <div className="mt-2 rounded-lg overflow-hidden border" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
                                                <DiffViewer
                                                    oldText={change.oldValue || ""}
                                                    newText={change.newValue || ""}
                                                />
                                            </div>
                                        )}
                                    </div>
                                ))}
                                {compareTarget.changes.length === 0 && (
                                    <div className="text-xs italic p-4 text-center rounded-lg border border-dashed" style={{ color: "var(--text-muted)", borderColor: "var(--border-node)" }}>
                                        No specific field changes recorded.
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="flex-1 p-6 animate-in slide-in-from-left-4 fade-in">
                        <Timeline items={timelineItems} animated={true} />
                    </div>
                )}
            </div>
        </div>
    );
}
