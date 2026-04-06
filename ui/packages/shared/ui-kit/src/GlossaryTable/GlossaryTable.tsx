import React, { useState } from "react";
import { ArrowUpDown, Search } from "lucide-react";

export interface GlossaryEntry {
    keyword: string;
    score: number;
    domain?: string;
    conceptCount: number;
    chunkCount: number;
}

export interface GlossaryTableProps {
    /** Entries */
    entries: GlossaryEntry[];
    /** On row click */
    onRowClick?: (entry: GlossaryEntry) => void;
    /** Active domain filter */
    activeDomain?: string;
    /** Available domains */
    domains?: string[];
    /** On domain filter */
    onDomainFilter?: (domain: string | undefined) => void;
}

export function GlossaryTable({
    entries,
    onRowClick,
    activeDomain,
    domains = [],
    onDomainFilter,
}: GlossaryTableProps) {
    const [sortBy, setSortBy] = useState<"keyword" | "score" | "conceptCount">("score");
    const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
    const [searchQ, setSearchQ] = useState("");

    const toggleSort = (col: typeof sortBy) => {
        if (sortBy === col) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
        else { setSortBy(col); setSortDir("desc"); }
    };

    const filtered = entries
        .filter((e) => !activeDomain || e.domain === activeDomain)
        .filter((e) => e.keyword.toLowerCase().includes(searchQ.toLowerCase()))
        .sort((a, b) => {
            const m = sortDir === "asc" ? 1 : -1;
            if (sortBy === "keyword") return m * a.keyword.localeCompare(b.keyword);
            return m * ((a as any)[sortBy] - (b as any)[sortBy]);
        });

    return (
        <div
            className="rounded-xl overflow-hidden flex flex-col"
            style={{ background: "var(--bg-panel)", border: "var(--border-node)", width: 480 }}
        >
            {/* Header */}
            <div className="px-4 py-2.5 flex items-center gap-3" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>Glossary</span>
                <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>{filtered.length} keywords</span>

                {/* Search */}
                <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg ml-auto" style={{ background: "var(--bg-node)", border: "var(--border-node)" }}>
                    <Search size={10} style={{ color: "var(--text-muted)" }} />
                    <input
                        value={searchQ}
                        onChange={(e) => setSearchQ(e.target.value)}
                        className="bg-transparent outline-none text-[10px] w-24"
                        style={{ color: "var(--text-primary)" }}
                        placeholder="Search..."
                    />
                </div>
            </div>

            {/* Domain chips */}
            {domains.length > 0 && (
                <div className="px-4 py-1.5 flex gap-1 flex-wrap" style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                    <button
                        onClick={() => onDomainFilter?.(undefined)}
                        className="text-[9px] px-2 py-0.5 rounded-full transition-colors"
                        style={{ background: !activeDomain ? "rgba(99,102,241,0.12)" : "transparent", color: !activeDomain ? "var(--color-info)" : "var(--text-muted)" }}
                    >All</button>
                    {domains.map((d) => (
                        <button key={d} onClick={() => onDomainFilter?.(d)}
                            className="text-[9px] px-2 py-0.5 rounded-full transition-colors"
                            style={{ background: activeDomain === d ? "rgba(99,102,241,0.12)" : "transparent", color: activeDomain === d ? "var(--color-info)" : "var(--text-muted)" }}
                        >{d}</button>
                    ))}
                </div>
            )}

            {/* Table */}
            <div className="overflow-auto" style={{ maxHeight: 350 }}>
                <table className="w-full text-[10px]">
                    <thead>
                        <tr style={{ background: "rgba(0,0,0,0.1)" }}>
                            {[
                                { id: "keyword" as const, label: "Keyword", w: "40%" },
                                { id: "score" as const, label: "Score", w: "15%" },
                                { id: "conceptCount" as const, label: "Concepts", w: "15%" },
                            ].map(({ id, label, w }) => (
                                <th key={id} className="font-semibold text-left px-3 py-2 cursor-pointer hover:bg-white/3 select-none" style={{ color: "var(--text-muted)", width: w }} onClick={() => toggleSort(id)}>
                                    <span className="flex items-center gap-1">{label} <ArrowUpDown size={8} /></span>
                                </th>
                            ))}
                            <th className="font-semibold text-left px-3 py-2" style={{ color: "var(--text-muted)", width: "15%" }}>Chunks</th>
                            <th className="font-semibold text-left px-3 py-2" style={{ color: "var(--text-muted)", width: "15%" }}>Domain</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filtered.map((entry) => (
                            <tr
                                key={entry.keyword}
                                className="hover:bg-white/3 cursor-pointer transition-colors"
                                style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}
                                onClick={() => onRowClick?.(entry)}
                            >
                                <td className="px-3 py-1.5 font-medium" style={{ color: "var(--text-primary)" }}>{entry.keyword}</td>
                                <td className="px-3 py-1.5 font-mono" style={{ color: entry.score >= 0.8 ? "var(--color-success)" : entry.score >= 0.5 ? "var(--color-warning)" : "var(--text-muted)" }}>
                                    {entry.score.toFixed(2)}
                                </td>
                                <td className="px-3 py-1.5" style={{ color: "var(--text-secondary)" }}>{entry.conceptCount}</td>
                                <td className="px-3 py-1.5" style={{ color: "var(--text-secondary)" }}>{entry.chunkCount}</td>
                                <td className="px-3 py-1.5">
                                    {entry.domain && (
                                        <span className="text-[8px] px-1.5 py-0.5 rounded" style={{ background: "var(--bg-node-hover)", color: "var(--text-muted)" }}>{entry.domain}</span>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
