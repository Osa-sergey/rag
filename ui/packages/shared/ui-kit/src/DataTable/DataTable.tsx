import React, { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react";

export interface Column<T> {
    /** Unique key matching the data field */
    key: string;
    /** Display header */
    header: string;
    /** Width (CSS value) */
    width?: string;
    /** Enable sorting */
    sortable?: boolean;
    /** Custom cell renderer */
    render?: (row: T) => React.ReactNode;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export interface DataTableProps<T extends Record<string, any>> {
    /** Column definitions */
    columns: Column<T>[];
    /** Data rows */
    data: T[];
    /** Row key extractor */
    rowKey: (row: T) => string;
    /** Callback on row click */
    onRowClick?: (row: T) => void;
    /** Show loading skeleton */
    loading?: boolean;
    /** Empty state message */
    emptyMessage?: string;
}

type SortDir = "asc" | "desc" | null;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function DataTable<T extends Record<string, any>>({
    columns,
    data,
    rowKey,
    onRowClick,
    loading = false,
    emptyMessage = "No data",
}: DataTableProps<T>) {
    const [sortKey, setSortKey] = useState<string | null>(null);
    const [sortDir, setSortDir] = useState<SortDir>(null);

    const handleSort = (key: string) => {
        if (sortKey === key) {
            setSortDir(sortDir === "asc" ? "desc" : sortDir === "desc" ? null : "asc");
            if (sortDir === "desc") setSortKey(null);
        } else {
            setSortKey(key);
            setSortDir("asc");
        }
    };

    const sortedData = useMemo(() => {
        if (!sortKey || !sortDir) return data;
        return [...data].sort((a, b) => {
            const av = a[sortKey];
            const bv = b[sortKey];
            if (av == null || bv == null) return 0;
            const cmp = av < bv ? -1 : av > bv ? 1 : 0;
            return sortDir === "asc" ? cmp : -cmp;
        });
    }, [data, sortKey, sortDir]);

    const SortIcon = ({ col }: { col: string }) => {
        if (sortKey !== col) return <ChevronsUpDown size={12} style={{ opacity: 0.3 }} />;
        return sortDir === "asc" ? (
            <ChevronUp size={12} style={{ color: "var(--color-info)" }} />
        ) : (
            <ChevronDown size={12} style={{ color: "var(--color-info)" }} />
        );
    };

    return (
        <div
            className="rounded-lg overflow-hidden"
            style={{ border: "var(--border-node)", background: "var(--bg-node)" }}
        >
            <table className="w-full text-sm">
                {/* Header */}
                <thead>
                    <tr style={{ borderBottom: "var(--border-node)", background: "var(--bg-panel)" }}>
                        {columns.map((col) => (
                            <th
                                key={col.key}
                                className="px-3 py-2.5 text-left font-medium select-none"
                                style={{
                                    color: "var(--text-secondary)",
                                    width: col.width,
                                    cursor: col.sortable ? "pointer" : "default",
                                }}
                                onClick={() => col.sortable && handleSort(col.key)}
                            >
                                <span className="inline-flex items-center gap-1">
                                    {col.header}
                                    {col.sortable && <SortIcon col={col.key} />}
                                </span>
                            </th>
                        ))}
                    </tr>
                </thead>

                {/* Body */}
                <tbody>
                    {loading ? (
                        Array.from({ length: 4 }).map((_, i) => (
                            <tr key={i} style={{ borderBottom: "var(--border-node)" }}>
                                {columns.map((col) => (
                                    <td key={col.key} className="px-3 py-3">
                                        <div
                                            className="h-3 rounded"
                                            style={{
                                                background: "var(--bg-node-hover)",
                                                width: `${40 + Math.random() * 40}%`,
                                                animation: "shimmer 1.5s ease-in-out infinite",
                                            }}
                                        />
                                    </td>
                                ))}
                            </tr>
                        ))
                    ) : sortedData.length === 0 ? (
                        <tr>
                            <td
                                colSpan={columns.length}
                                className="px-3 py-8 text-center"
                                style={{ color: "var(--text-muted)" }}
                            >
                                {emptyMessage}
                            </td>
                        </tr>
                    ) : (
                        <AnimatePresence>
                            {sortedData.map((row) => (
                                <motion.tr
                                    key={rowKey(row)}
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    className="transition-colors"
                                    style={{
                                        borderBottom: "var(--border-node)",
                                        cursor: onRowClick ? "pointer" : "default",
                                    }}
                                    onClick={() => onRowClick?.(row)}
                                    whileHover={{
                                        backgroundColor: "var(--bg-node-hover)",
                                    }}
                                >
                                    {columns.map((col) => (
                                        <td
                                            key={col.key}
                                            className="px-3 py-2.5"
                                            style={{ color: "var(--text-primary)" }}
                                        >
                                            {col.render ? col.render(row) : String(row[col.key] ?? "")}
                                        </td>
                                    ))}
                                </motion.tr>
                            ))}
                        </AnimatePresence>
                    )}
                </tbody>
            </table>
        </div>
    );
}
