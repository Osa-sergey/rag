import { useState } from "react";
import { Modal } from "../Modal";

export interface ConceptCardProps {
    /** Concept name */
    name: string;
    /** Domain (e.g. ML, NLP, Data Engineering) */
    domain?: string;
    /** Domain color */
    domainColor?: string;
    /** Description (truncated) */
    description?: string;
    /** Version label */
    version?: string;
    /** Keywords count */
    keywordCount?: number;
    /** Source articles count */
    sourceCount?: number;
    /** Is stale */
    stale?: boolean;
    /** Status */
    status?: "active" | "stale" | "manual";
    /** On click */
    onClick?: () => void;
}

export function ConceptCard({
    name,
    domain,
    domainColor = "var(--color-concept)",
    description,
    version,
    keywordCount,
    sourceCount,
    stale = false,
    status = "active",
    onClick,
}: ConceptCardProps) {
    const [isModalOpen, setIsModalOpen] = useState(false);

    const handleCardClick = () => {
        // Only open modal if it's the main card click, allows onClick to fire too
        setIsModalOpen(true);
        onClick?.();
    };

    return (
        <>
            <div
                className="rounded-xl overflow-hidden cursor-pointer transition-all hover:translate-y-[-2px] group relative"
                style={{
                    background: "var(--bg-node)",
                    border: stale ? "1px solid rgba(245,158,11,0.3)" : "1px solid var(--border-node)",
                    boxShadow: stale ? "0 0 12px rgba(245,158,11,0.1)" : "0 4px 16px rgba(0,0,0,0.15)",
                }}
                onClick={handleCardClick}
            >
                {/* Color accent strip */}
                <div style={{ height: 4, background: stale ? "var(--color-warning)" : domainColor }} />

                <div className="px-4 py-3 flex flex-col gap-2">
                    {/* Header */}
                    <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
                            {name}
                        </span>
                        {version && (
                            <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded flex-shrink-0" style={{ background: "rgba(99,102,241,0.1)", color: "var(--color-info)" }}>
                                {version}
                            </span>
                        )}
                    </div>

                    {/* Domain + status */}
                    <div className="flex items-center gap-1.5 flex-wrap">
                        {domain && (
                            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded" style={{ background: `color-mix(in srgb, ${domainColor} 12%, transparent)`, color: domainColor }}>
                                {domain}
                            </span>
                        )}
                        {status === "stale" && (
                            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded" style={{ background: "rgba(245,158,11,0.1)", color: "var(--color-warning)" }}>
                                ⚠ Stale
                            </span>
                        )}
                        {status === "manual" && (
                            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded" style={{ background: "rgba(99,102,241,0.1)", color: "var(--color-info)" }}>
                                ✎ Manual
                            </span>
                        )}
                    </div>

                    {/* Description */}
                    {description && (
                        <p className="text-[11px] leading-relaxed line-clamp-3 mt-1" style={{ color: "var(--text-secondary)" }}>
                            {description}
                        </p>
                    )}

                    {/* Stats */}
                    <div className="flex items-center gap-3 mt-2 text-[10px] font-medium" style={{ color: "var(--text-muted)" }}>
                        {keywordCount !== undefined && <span className="flex items-center gap-1">🏷 {keywordCount}</span>}
                        {sourceCount !== undefined && <span className="flex items-center gap-1">📄 {sourceCount}</span>}
                    </div>
                </div>

                {/* Hover affordance to show it expands */}
                <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
                    <span className="text-[10px] bg-[rgba(255,255,255,0.1)] px-1.5 py-0.5 rounded text-[var(--text-muted)]">Open</span>
                </div>
            </div>

            <Modal
                open={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                title={`Concept: ${name}`}
            >
                <div className="flex flex-col gap-4 p-1">
                    {/* Badges row */}
                    <div className="flex items-center gap-2 flex-wrap">
                        {domain && (
                            <span className="text-xs font-bold px-2 py-1 rounded" style={{ background: `color-mix(in srgb, ${domainColor} 12%, transparent)`, color: domainColor }}>
                                {domain}
                            </span>
                        )}
                        {version && (
                            <span className="text-xs font-mono font-bold px-2 py-1 rounded" style={{ background: "rgba(99,102,241,0.1)", color: "var(--color-info)" }}>
                                Version {version}
                            </span>
                        )}
                        {status === "stale" && (
                            <span className="text-xs font-bold px-2 py-1 rounded" style={{ background: "rgba(245,158,11,0.1)", color: "var(--color-warning)" }}>
                                ⚠ Stale Concept
                            </span>
                        )}
                        {status === "manual" && (
                            <span className="text-xs font-bold px-2 py-1 rounded" style={{ background: "rgba(99,102,241,0.1)", color: "var(--color-info)" }}>
                                ✎ Manually Edited
                            </span>
                        )}
                    </div>

                    {/* Full Description text */}
                    <div className="text-[13px] leading-relaxed p-4 rounded-lg" style={{ background: "var(--bg-node-hover)", color: "var(--text-primary)", border: "1px solid rgba(255,255,255,0.05)" }}>
                        {description || <span style={{ color: "var(--text-muted)", fontStyle: "italic" }}>No details provided for this concept.</span>}
                    </div>

                    {/* Stats */}
                    <div className="flex items-center gap-6 mt-2 text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
                        {keywordCount !== undefined && <div className="flex items-center gap-1.5">🏷 <span>{keywordCount} Keywords Found</span></div>}
                        {sourceCount !== undefined && <div className="flex items-center gap-1.5">📄 <span>{sourceCount} Source Articles</span></div>}
                    </div>
                </div>
            </Modal>
        </>
    );
}
