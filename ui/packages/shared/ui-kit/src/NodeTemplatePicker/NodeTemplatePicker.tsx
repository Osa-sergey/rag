import React from "react";
import { Check, Database, GitBranch, Zap, Shield, FileText, Globe, X } from "lucide-react";

export interface NodeTemplate {
    id: string;
    name: string;
    description: string;
    color: string;
    icon: string;
}

export const defaultTemplates: NodeTemplate[] = [
    { id: "data", name: "Data Source", description: "database\n#6366f1", color: "var(--color-info)", icon: "database" },
    { id: "process", name: "Transformation", description: "git-branch\n#a855f7", color: "var(--color-concept)", icon: "git-branch" },
    { id: "action", name: "Trigger / Action", description: "zap\n#f59e0b", color: "var(--color-warning)", icon: "zap" },
    { id: "security", name: "Validation", description: "shield\n#22c55e", color: "var(--color-success)", icon: "shield" },
    { id: "document", name: "Document", description: "file-text\n#3b82f6", color: "var(--color-article)", icon: "file-text" },
    { id: "network", name: "External API", description: "globe\n#f97316", color: "var(--color-stale)", icon: "globe" },
];

const renderIcon = (name: string, size = 16) => {
    switch (name) {
        case "database": return <Database size={size} />;
        case "git-branch": return <GitBranch size={size} />;
        case "zap": return <Zap size={size} />;
        case "shield": return <Shield size={size} />;
        case "file-text": return <FileText size={size} />;
        case "globe": return <Globe size={size} />;
        default: return <Database size={size} />;
    }
}

export interface NodeTemplatePickerProps {
    templates?: NodeTemplate[];
    selectedId?: string;
    onSelect?: (template: NodeTemplate) => void;
    onDelete?: (templateId: string) => void;
}

export function NodeTemplatePicker({
    templates = defaultTemplates,
    selectedId,
    onSelect,
    onDelete,
}: NodeTemplatePickerProps) {
    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
            {templates.map(t => {
                const isSelected = selectedId === t.id;
                return (
                    <div
                        key={t.id}
                        onClick={() => onSelect?.(t)}
                        className="group/tpl relative flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all hover:-translate-y-0.5"
                        style={{
                            background: isSelected ? `color-mix(in srgb, ${t.color} 10%, var(--bg-node))` : "var(--bg-node)",
                            borderColor: isSelected ? t.color : "var(--border-node)",
                            boxShadow: isSelected ? `0 0 0 1px ${t.color} inset` : "0 2px 8px rgba(0,0,0,0.05)",
                        }}
                    >
                        <div
                            className="flex items-center justify-center w-8 h-8 rounded-lg text-white"
                            style={{ background: t.color }}
                        >
                            {renderIcon(t.icon, 14)}
                        </div>
                        <div className="flex flex-col flex-1 min-w-0">
                            <span className="text-xs font-bold truncate text-[var(--text-primary)]">
                                {t.name}
                            </span>
                            <span className="text-[9px] leading-snug whitespace-pre-line" style={{ color: "var(--text-secondary)" }}>
                                {t.description}
                            </span>
                        </div>
                        {isSelected && (
                            <div className="absolute top-2 right-2">
                                <Check size={12} style={{ color: t.color }} />
                            </div>
                        )}
                        {onDelete && (
                            <button
                                className="absolute top-1 right-1 w-5 h-5 rounded-full flex items-center justify-center opacity-0 group-hover/tpl:opacity-100 transition-opacity hover:bg-red-500/20"
                                style={{ color: "var(--color-error)" }}
                                onClick={(e) => { e.stopPropagation(); onDelete(t.id); }}
                                title="Delete template"
                            >
                                <X size={10} />
                            </button>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
