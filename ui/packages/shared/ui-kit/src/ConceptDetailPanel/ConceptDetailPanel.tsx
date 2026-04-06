import React, { useState } from "react";
import { Brain, Tag, FileText, Clock, ChevronRight, ExternalLink, AlertTriangle, GitBranch } from "lucide-react";

export interface ConceptDetailVersion {
    version: string;
    date: string;
    changeType?: "created" | "enriched" | "expanded";
}

export interface ConceptDetailSource {
    id: string;
    title: string;
    type: "article" | "manual";
}

export interface ConceptDetailPanelProps {
    /** Concept name */
    name: string;
    /** Domain */
    domain: string;
    /** Domain color */
    domainColor?: string;
    /** Description */
    description?: string;
    /** Keywords */
    keywords?: string[];
    /** Sources */
    sources?: ConceptDetailSource[];
    /** Version history */
    versions?: ConceptDetailVersion[];
    /** Current version */
    currentVersion?: string;
    /** Is stale */
    stale?: boolean;
    /** Stale reason */
    staleReason?: string;
}

export function ConceptDetailPanel({
    name,
    domain,
    domainColor = "var(--color-concept)",
    description,
    keywords = [],
    sources = [],
    versions = [],
    currentVersion,
    stale = false,
    staleReason,
}: ConceptDetailPanelProps) {
    const [activeSection, setActiveSection] = useState<string | null>("keywords");

    const sections = [
        { id: "keywords", label: "Keywords", count: keywords.length, icon: <Tag size={12} /> },
        { id: "sources", label: "Sources", count: sources.length, icon: <FileText size={12} /> },
        { id: "versions", label: "History", count: versions.length, icon: <Clock size={12} /> },
    ];

    return (
        <div
            className="rounded-xl overflow-hidden flex flex-col"
            style={{ background: "var(--bg-panel)", border: "var(--border-node)", width: 320 }}
        >
            {/* Header */}
            <div className="px-4 py-3" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <div className="flex items-center gap-2 mb-1">
                    <Brain size={14} style={{ color: domainColor }} />
                    <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{name}</h3>
                    {currentVersion && (
                        <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ml-auto" style={{ background: "rgba(99,102,241,0.1)", color: "var(--color-info)" }}>
                            {currentVersion}
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-1.5 mb-2">
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded" style={{ background: `color-mix(in srgb, ${domainColor} 12%, transparent)`, color: domainColor }}>
                        {domain}
                    </span>
                </div>
                {description && (
                    <p className="text-[11px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>{description}</p>
                )}
            </div>

            {/* Stale warning */}
            {stale && (
                <div className="flex items-center gap-2 px-4 py-2" style={{ background: "rgba(245,158,11,0.06)", borderBottom: "1px solid rgba(245,158,11,0.1)" }}>
                    <AlertTriangle size={12} style={{ color: "var(--color-warning)" }} />
                    <span className="text-[10px]" style={{ color: "var(--color-warning)" }}>
                        {staleReason ?? "Source articles have been updated since last expansion"}
                    </span>
                </div>
            )}

            {/* Collapsible sections */}
            <div className="flex flex-col">
                {sections.map((sec) => (
                    <div key={sec.id}>
                        <button
                            onClick={() => setActiveSection(activeSection === sec.id ? null : sec.id)}
                            className="w-full flex items-center gap-2 px-4 py-2 text-left hover:bg-white/3 transition-colors"
                            style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}
                        >
                            <ChevronRight
                                size={10}
                                className="transition-transform"
                                style={{ transform: activeSection === sec.id ? "rotate(90deg)" : "none", color: "var(--text-muted)" }}
                            />
                            <span style={{ color: "var(--text-muted)" }}>{sec.icon}</span>
                            <span className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>{sec.label}</span>
                            <span className="text-[9px] ml-auto" style={{ color: "var(--text-muted)" }}>{sec.count}</span>
                        </button>

                        {activeSection === sec.id && (
                            <div className="px-4 py-2">
                                {sec.id === "keywords" && (
                                    <div className="flex flex-wrap gap-1">
                                        {keywords.map((kw) => (
                                            <span key={kw} className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: "rgba(34,197,94,0.08)", color: "var(--color-keyword, #22c55e)" }}>
                                                {kw}
                                            </span>
                                        ))}
                                    </div>
                                )}
                                {sec.id === "sources" && (
                                    <div className="flex flex-col gap-1">
                                        {sources.map((src) => (
                                            <div key={src.id} className="flex items-center gap-2 text-xs py-1">
                                                <FileText size={10} style={{ color: "var(--text-muted)" }} />
                                                <span className="truncate" style={{ color: "var(--text-secondary)" }}>{src.title}</span>
                                                <ExternalLink size={9} className="flex-shrink-0" style={{ color: "var(--text-muted)", opacity: 0.5 }} />
                                            </div>
                                        ))}
                                    </div>
                                )}
                                {sec.id === "versions" && (
                                    <div className="flex flex-col gap-1">
                                        {versions.map((v, i) => (
                                            <div key={v.version} className="flex items-center gap-2 text-[10px] py-1">
                                                <GitBranch size={10} style={{ color: i === 0 ? "var(--color-info)" : "var(--text-muted)" }} />
                                                <span className="font-mono font-bold" style={{ color: i === 0 ? "var(--color-info)" : "var(--text-muted)" }}>
                                                    {v.version}
                                                </span>
                                                <span style={{ color: "var(--text-muted)" }}>{v.date}</span>
                                                {v.changeType && (
                                                    <span className="ml-auto text-[8px] px-1 py-0.5 rounded" style={{ background: "var(--bg-node-hover)", color: "var(--text-muted)" }}>
                                                        {v.changeType}
                                                    </span>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
