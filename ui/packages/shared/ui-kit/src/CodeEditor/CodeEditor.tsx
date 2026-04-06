import React, { useState, useRef, useCallback } from "react";
import { Copy, Check, AlertCircle, FileCode } from "lucide-react";

export type CodeLanguage = "yaml" | "json" | "text";

export interface CodeEditorError {
    /** 1-based line number */
    line: number;
    /** Error message */
    message: string;
}

export interface CodeEditorProps {
    /** Code content (controlled) */
    value: string;
    /** Change handler */
    onChange?: (value: string) => void;
    /** Language for syntax hinting */
    language?: CodeLanguage;
    /** Read-only mode */
    readOnly?: boolean;
    /** Title */
    title?: string;
    /** Error markers */
    errors?: CodeEditorError[];
    /** Line numbers (default true) */
    lineNumbers?: boolean;
    /** Max height in px (0 = no limit) */
    maxHeight?: number;
    /** Placeholder text */
    placeholder?: string;
}

export function CodeEditor({
    value,
    onChange,
    language = "yaml",
    readOnly = false,
    title,
    errors = [],
    lineNumbers = true,
    maxHeight = 400,
    placeholder = "Enter code...",
}: CodeEditorProps) {
    const [copied, setCopied] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const lines = value.split("\n");
    const errorLineSet = new Set(errors.map((e) => e.line));

    const handleCopy = useCallback(async () => {
        await navigator.clipboard.writeText(value);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
    }, [value]);

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Tab") {
            e.preventDefault();
            const ta = textareaRef.current;
            if (!ta || readOnly) return;
            const start = ta.selectionStart;
            const end = ta.selectionEnd;
            const newVal = value.substring(0, start) + "  " + value.substring(end);
            onChange?.(newVal);
            requestAnimationFrame(() => {
                ta.selectionStart = ta.selectionEnd = start + 2;
            });
        }
    };

    const langLabel: Record<CodeLanguage, string> = {
        yaml: "YAML",
        json: "JSON",
        text: "TEXT",
    };

    return (
        <div
            className="rounded-xl overflow-hidden flex flex-col"
            style={{ background: "var(--bg-node)", border: "var(--border-node)" }}
        >
            {/* Header */}
            <div
                className="flex items-center justify-between px-4 py-2 gap-2 flex-shrink-0"
                style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
            >
                <div className="flex items-center gap-2 min-w-0">
                    <FileCode size={14} style={{ color: "var(--color-info)" }} />
                    {title && (
                        <span className="text-xs font-semibold truncate" style={{ color: "var(--text-primary)" }}>
                            {title}
                        </span>
                    )}
                    <span
                        className="text-[9px] font-mono px-1.5 py-0.5 rounded"
                        style={{ background: "var(--bg-node-hover)", color: "var(--text-muted)" }}
                    >
                        {langLabel[language]}
                    </span>
                    {readOnly && (
                        <span
                            className="text-[9px] font-medium px-1.5 py-0.5 rounded"
                            style={{ background: "rgba(245,158,11,0.1)", color: "var(--color-warning)" }}
                        >
                            READ-ONLY
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-1">
                    {errors.length > 0 && (
                        <div className="flex items-center gap-1 text-[10px] font-medium mr-2" style={{ color: "var(--color-error)" }}>
                            <AlertCircle size={12} />
                            {errors.length} error{errors.length > 1 ? "s" : ""}
                        </div>
                    )}
                    <button
                        onClick={handleCopy}
                        className="p-1.5 rounded-lg transition-colors hover:bg-white/5"
                        style={{ color: copied ? "var(--color-success)" : "var(--text-muted)" }}
                        title="Copy to clipboard"
                    >
                        {copied ? <Check size={12} /> : <Copy size={12} />}
                    </button>
                </div>
            </div>

            {/* Editor body */}
            <div
                className="flex overflow-auto"
                style={{ maxHeight: maxHeight > 0 ? maxHeight : undefined, fontFamily: "'JetBrains Mono', monospace" }}
            >
                {/* Line numbers */}
                {lineNumbers && (
                    <div
                        className="flex flex-col items-end px-3 py-3 select-none flex-shrink-0"
                        style={{ background: "rgba(0,0,0,0.1)", borderRight: "1px solid rgba(255,255,255,0.04)" }}
                    >
                        {lines.map((_, i) => (
                            <div
                                key={i}
                                className="text-[11px] leading-5"
                                style={{
                                    color: errorLineSet.has(i + 1) ? "var(--color-error)" : "var(--text-muted)",
                                    opacity: errorLineSet.has(i + 1) ? 1 : 0.4,
                                    fontWeight: errorLineSet.has(i + 1) ? 700 : 400,
                                }}
                            >
                                {i + 1}
                            </div>
                        ))}
                    </div>
                )}

                {/* Code area */}
                <div className="relative flex-1 min-w-0">
                    {/* Error line highlights */}
                    {errors.length > 0 && (
                        <div className="absolute inset-0 pointer-events-none" style={{ padding: "12px 0" }}>
                            {lines.map((_, i) =>
                                errorLineSet.has(i + 1) ? (
                                    <div
                                        key={i}
                                        className="h-5"
                                        style={{ background: "rgba(239,68,68,0.06)" }}
                                    />
                                ) : (
                                    <div key={i} className="h-5" />
                                )
                            )}
                        </div>
                    )}

                    <textarea
                        ref={textareaRef}
                        value={value}
                        onChange={(e) => onChange?.(e.target.value)}
                        onKeyDown={handleKeyDown}
                        readOnly={readOnly}
                        placeholder={placeholder}
                        className="w-full h-full resize-none outline-none p-3"
                        style={{
                            background: "transparent",
                            color: "var(--text-primary)",
                            fontSize: 11,
                            lineHeight: "20px",
                            fontFamily: "inherit",
                            tabSize: 2,
                            caretColor: "var(--color-info)",
                            minHeight: Math.max(lines.length * 20 + 24, 80),
                        }}
                        spellCheck={false}
                    />
                </div>
            </div>

            {/* Error messages footer */}
            {errors.length > 0 && (
                <div
                    className="flex flex-col gap-0.5 px-4 py-2 flex-shrink-0"
                    style={{ borderTop: "1px solid rgba(239,68,68,0.15)", background: "rgba(239,68,68,0.03)" }}
                >
                    {errors.map((err, i) => (
                        <div key={i} className="flex items-center gap-2 text-[10px]" style={{ color: "var(--color-error)" }}>
                            <span className="font-mono font-bold">L{err.line}</span>
                            <span>{err.message}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
