import React from "react";
import { ChevronRight, MoreHorizontal } from "lucide-react";

export interface BreadcrumbItem {
    /** Display label */
    label: string;
    /** Click handler (omit for last/current item) */
    onClick?: () => void;
    /** Icon (optional) */
    icon?: React.ReactNode;
}

export interface BreadcrumbProps {
    /** Items in path order */
    items: BreadcrumbItem[];
    /** Max visible items before collapsing (0 = no collapse) */
    maxVisible?: number;
    /** Separator */
    separator?: React.ReactNode;
}

export function Breadcrumb({
    items,
    maxVisible = 0,
    separator,
}: BreadcrumbProps) {
    const sep = separator ?? <ChevronRight size={12} style={{ color: "var(--text-muted)" }} />;

    let visibleItems = items;
    let hasCollapsed = false;

    if (maxVisible > 0 && items.length > maxVisible) {
        const first = items[0];
        const lastN = items.slice(-(maxVisible - 1));
        visibleItems = [first, { label: "…", icon: <MoreHorizontal size={14} /> }, ...lastN];
        hasCollapsed = true;
    }

    return (
        <nav aria-label="Breadcrumb">
            <ol className="flex items-center gap-1.5 text-sm">
                {visibleItems.map((item, i) => {
                    const isLast = i === visibleItems.length - 1;
                    const isCollapsed = hasCollapsed && i === 1;

                    return (
                        <li key={i} className="flex items-center gap-1.5">
                            {i > 0 && <span className="flex-shrink-0">{sep}</span>}

                            {isCollapsed ? (
                                <span
                                    className="flex items-center px-1 py-0.5 rounded hover:bg-white/5 cursor-pointer transition-colors"
                                    style={{ color: "var(--text-muted)" }}
                                    title="Show full path"
                                >
                                    {item.icon}
                                </span>
                            ) : isLast ? (
                                <span
                                    className="flex items-center gap-1 font-medium"
                                    style={{ color: "var(--text-primary)" }}
                                    aria-current="page"
                                >
                                    {item.icon}
                                    {item.label}
                                </span>
                            ) : (
                                <button
                                    onClick={item.onClick}
                                    className="flex items-center gap-1 hover:underline transition-colors"
                                    style={{ color: "var(--text-muted)" }}
                                >
                                    {item.icon}
                                    {item.label}
                                </button>
                            )}
                        </li>
                    );
                })}
            </ol>
        </nav>
    );
}
