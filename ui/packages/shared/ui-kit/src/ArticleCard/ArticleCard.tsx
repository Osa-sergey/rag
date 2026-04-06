import { FileText, Calendar, Tag } from "lucide-react";
import { Checkbox } from "../Checkbox";

export interface ArticleCardProps {
    /** Article title */
    title: string;
    /** Source (URL or file path) */
    source?: string;
    /** Date parsed */
    date?: string;
    /** Chunk count */
    chunkCount?: number;
    /** Keyword count */
    keywordCount?: number;
    /** Linked concepts count */
    conceptCount?: number;
    /** Preview text (first ~100 chars) */
    preview?: string;
    /** Is selected? */
    selected?: boolean;
    /** Is selectable? */
    selectable?: boolean;
    /** On select toggle via dedicated area */
    onToggleSelect?: (selected: boolean) => void;
    /** On click anywhere on the card */
    onClick?: () => void;
}

export function ArticleCard({
    title,
    source,
    date,
    chunkCount,
    keywordCount,
    conceptCount,
    preview,
    selected = false,
    selectable = false,
    onToggleSelect,
    onClick,
}: ArticleCardProps) {
    return (
        <div
            className="rounded-xl flex overflow-hidden cursor-pointer transition-all hover:translate-y-[-2px] group"
            style={{
                background: selected ? "color-mix(in srgb, var(--color-success) 8%, var(--bg-node))" : "var(--bg-node)",
                border: "var(--border-node)",
                boxShadow: "0 4px 16px rgba(0,0,0,0.1)",
                width: selectable ? 320 : 280,
            }}
            onClick={onClick}
        >
            {/* Selectable left column */}
            {selectable && (
                <div
                    className="flex flex-col items-center pt-4 transition-colors"
                    style={{
                        width: 44,
                        borderRight: "1px solid rgba(255,255,255,0.06)",
                        background: selected ? "color-mix(in srgb, var(--color-success) 12%, transparent)" : "transparent"
                    }}
                    onClick={(e) => {
                        e.stopPropagation();
                        onToggleSelect?.(!selected);
                    }}
                >
                    <Checkbox checked={selected} onChange={(val) => onToggleSelect?.(val)} />
                </div>
            )}

            <div className="flex-1 flex flex-col min-w-0 relative">
                {/* Color accent */}
                <div className="absolute top-0 left-0 w-full transition-colors" style={{ height: 3, background: selected ? "var(--color-success)" : "var(--color-article, #3b82f6)" }} />

                <div className="px-4 py-3 flex flex-col gap-2 mt-1">
                    {/* Title */}
                    <div className="flex items-start gap-2">
                        <FileText size={14} className="flex-shrink-0 mt-0.5" style={{ color: selected ? "var(--color-success)" : "var(--color-article, #3b82f6)" }} />
                        <span className="text-sm font-semibold leading-tight line-clamp-2" style={{ color: selected ? "var(--color-success)" : "var(--text-primary)" }}>
                            {title}
                        </span>
                    </div>

                    {/* Source */}
                    {source && (
                        <span className="text-[9px] font-mono truncate" style={{ color: "var(--text-muted)" }}>
                            {source}
                        </span>
                    )}

                    {/* Preview */}
                    {preview && (
                        <p className="text-[11px] leading-relaxed line-clamp-2" style={{ color: "var(--text-secondary)" }}>
                            {preview}
                        </p>
                    )}

                    {/* Stats */}
                    <div className="flex items-center gap-3 text-[10px] flex-wrap mt-1" style={{ color: "var(--text-muted)" }}>
                        {date && (
                            <span className="flex items-center gap-1">
                                <Calendar size={9} /> {date}
                            </span>
                        )}
                        {chunkCount !== undefined && <span>📦 {chunkCount} chunks</span>}
                        {keywordCount !== undefined && (
                            <span className="flex items-center gap-1">
                                <Tag size={9} /> {keywordCount}
                            </span>
                        )}
                        {conceptCount !== undefined && <span>🧠 {conceptCount}</span>}
                    </div>
                </div>
            </div>
        </div>
    );
}
