import { useState } from "react";
import { SearchBar } from "../SearchBar";
import { ArticleCard, ArticleCardProps } from "../ArticleCard";
import { Database, FolderHeart, X, ArrowRight } from "lucide-react";

export interface ArticlePoolSelectorProps {
    availableArticles: (ArticleCardProps & { id: string; domain?: string })[];
    selectedIds?: string[];
    onSelectionChange?: (ids: string[]) => void;
    onSearch?: (query: string) => void;
    isSearching?: boolean;
}

export function ArticlePoolSelector({
    availableArticles,
    selectedIds = [],
    onSelectionChange,
    onSearch,
    isSearching = false,
}: ArticlePoolSelectorProps) {
    const [query, setQuery] = useState("");

    const handleToggle = (id: string, checked: boolean) => {
        if (!onSelectionChange) return;
        if (checked) {
            onSelectionChange([...selectedIds, id]);
        } else {
            onSelectionChange(selectedIds.filter(x => x !== id));
        }
    };

    const handleClearSelected = () => {
        onSelectionChange?.([]);
    };

    const filteredArticles = query
        ? availableArticles.filter(a => a.title.toLowerCase().includes(query.toLowerCase()) || a.domain?.toLowerCase().includes(query.toLowerCase()))
        : availableArticles;

    return (
        <div
            className="flex flex-col h-full rounded-2xl overflow-hidden"
            style={{ background: "var(--bg-panel)", border: "1px solid var(--border-node)", boxShadow: "0 10px 30px -10px rgba(0, 0, 0, 0.3)" }}
        >
            {/* Header */}
            <div className="flex-shrink-0 flex items-center justify-between p-5 z-10" style={{ background: "var(--bg-node)", borderBottom: "var(--border-node)" }}>
                <div className="flex items-center gap-3">
                    <Database size={20} style={{ color: "var(--color-info)" }} />
                    <div>
                        <h2 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>Article Pool</h2>
                        <p className="text-[10px] font-semibold uppercase tracking-widest mt-0.5" style={{ color: "var(--text-secondary)" }}>Knowledge Base Selection</p>
                    </div>
                </div>
                {selectedIds.length > 0 && (
                    <div className="px-3 py-1.5 rounded-lg text-xs font-bold" style={{ background: "var(--bg-panel)", border: "1px solid var(--border-node)", color: "var(--text-primary)" }}>
                        {selectedIds.length} Selected
                    </div>
                )}
            </div>

            {/* Selected Chips Area */}
            {selectedIds.length > 0 && (
                <div className="flex-shrink-0 p-5 pb-4 z-10" style={{ background: "var(--bg-panel)", borderBottom: "1px solid var(--border-node)" }}>
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-[10px] font-bold uppercase tracking-widest flex items-center gap-2" style={{ color: "var(--text-secondary)" }}>
                            <FolderHeart size={14} style={{ color: "var(--color-success)" }} />
                            Staged For Synthesis
                        </span>
                        <button
                            onClick={handleClearSelected}
                            className="text-[10px] font-bold uppercase tracking-wider hover:underline"
                            style={{ color: "var(--color-error)" }}
                        >
                            Clear all
                        </button>
                    </div>
                    <div className="flex flex-wrap gap-2 max-h-[120px] overflow-y-auto">
                        {selectedIds.map(id => {
                            const art = availableArticles.find(a => a.id === id);
                            if (!art) return null;
                            return (
                                <div
                                    key={id}
                                    className="group flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-colors cursor-pointer"
                                    style={{
                                        background: "var(--bg-node)",
                                        borderColor: "var(--border-node)",
                                        color: "var(--text-primary)"
                                    }}
                                    onClick={() => handleToggle(id, false)}
                                >
                                    <span className="text-xs font-medium truncate max-w-[200px]">{art.title}</span>
                                    <X size={12} className="opacity-50 group-hover:opacity-100" style={{ color: "var(--text-muted)" }} />
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Body */}
            <div className="flex-1 overflow-hidden flex flex-col bg-[var(--bg-panel)] relative">
                <div className="flex-shrink-0 p-5 pb-2">
                    <SearchBar
                        value={query}
                        onChange={(v) => {
                            setQuery(v);
                            onSearch?.(v);
                        }}
                        placeholder="Search articles by title or domain..."
                    />
                </div>

                <div className="flex-1 overflow-y-auto p-5 pt-3">
                    {isSearching ? (
                        <div className="flex flex-col items-center justify-center p-12 text-center" style={{ color: "var(--color-info)" }}>
                            <div className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin mb-4" style={{ borderColor: "currentColor transparent currentColor currentColor" }} />
                            <span className="text-xs font-bold uppercase tracking-widest">Searching Knowledge Base...</span>
                        </div>
                    ) : filteredArticles.length === 0 ? (
                        <div className="flex flex-col items-center justify-center p-12 text-center rounded-xl border border-dashed" style={{ borderColor: "var(--border-node)" }}>
                            <span className="text-sm font-bold mb-2" style={{ color: "var(--text-primary)" }}>No articles found</span>
                            <span className="text-xs" style={{ color: "var(--text-muted)" }}>Try adjusting your search query</span>
                        </div>
                    ) : (
                        <div className="flex flex-wrap gap-5 justify-start">
                            {filteredArticles.map(article => {
                                const isSelected = selectedIds.includes(article.id);
                                return (
                                    <ArticleCard
                                        key={article.id}
                                        {...article}
                                        selectable
                                        selected={isSelected}
                                        onToggleSelect={(val) => handleToggle(article.id, val)}
                                        onClick={() => handleToggle(article.id, !isSelected)}
                                    />
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>

            {/* Footer Form Action */}
            {selectedIds.length > 0 && (
                <div className="flex-shrink-0 px-6 py-4 z-10" style={{ background: "var(--bg-node)", borderTop: "var(--border-node)" }}>
                    <button
                        className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-bold transition-transform active:scale-[0.99] shadow-sm"
                        style={{ background: "var(--color-info)", color: "white" }}
                    >
                        Proceed with {selectedIds.length} Article{selectedIds.length !== 1 ? 's' : ''} <ArrowRight size={16} />
                    </button>
                </div>
            )}
        </div>
    );
}
