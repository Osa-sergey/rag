import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Badge } from "../Badge";
import { Select } from "../Select";
import { DataTable, Column } from "../DataTable";
import { ArticleCard, ArticleCardProps } from "../ArticleCard";
import { ChevronRight, ChevronLeft, Check, FileText, Sparkles, BookOpen, Layers } from "lucide-react";
import { transitions } from "../motion";

export interface ExtractedKeyword {
    id: string;
    keyword: string;
    score: number;
    mentions: number;
}

export interface CreateConceptWizardProps {
    onClose?: () => void;
    onSubmit?: (data: any) => void;
    availableArticles?: (ArticleCardProps & { id: string })[];
    extractedKeywords?: ExtractedKeyword[];
}

const STEPS = [
    { num: 1, title: "Definition", icon: <BookOpen size={14} /> },
    { num: 2, title: "Sources", icon: <Layers size={14} /> },
    { num: 3, title: "Review", icon: <Sparkles size={14} /> },
];

export function CreateConceptWizard({
    onClose,
    onSubmit,
    availableArticles = [],
    extractedKeywords = [],
}: CreateConceptWizardProps) {
    const [step, setStep] = useState<1 | 2 | 3>(1);

    // Form State
    const [name, setName] = useState("");
    const [domain, setDomain] = useState("");
    const [description, setDescription] = useState("");
    const [selectedArticles, setSelectedArticles] = useState<Set<string>>(new Set());

    const toggleArticle = (id: string) => {
        const next = new Set(selectedArticles);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        setSelectedArticles(next);
    };

    const handleNext = () => setStep((s: 1 | 2 | 3) => Math.min(3, s + 1) as 1 | 2 | 3);
    const handlePrev = () => setStep((s: 1 | 2 | 3) => Math.max(1, s - 1) as 1 | 2 | 3);

    const keywordCols: Column<ExtractedKeyword>[] = [
        {
            key: "keyword",
            header: "Keyword",
            render: ({ keyword }) => <span className="font-semibold text-[11px] text-[var(--text-primary)]">{keyword}</span>,
        },
        {
            key: "score",
            header: "TF-IDF",
            width: "60px",
            render: ({ score }) => <span className="font-mono text-[10px] text-[var(--color-info)]">{Number(score).toFixed(2)}</span>,
        },
        {
            key: "mentions",
            header: "Mentions",
            width: "60px",
            render: ({ mentions }) => (
                <div className="flex justify-center w-full">
                    <Badge variant="warning">{mentions}</Badge>
                </div>
            ),
        },
    ];

    const isFormValid = name.trim().length > 0;

    return (
        <div className="flex flex-col h-full w-full max-w-[850px] mx-auto rounded-3xl overflow-hidden shadow-2xl bg-[var(--bg-panel)] relative" style={{ border: "1px solid var(--border-panel)", boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.7)" }}>

            {/* Header & Stylized Stepper */}
            <div className="flex-shrink-0 flex items-center justify-between p-6 px-8 relative overflow-hidden bg-[var(--bg-node)] z-20">
                <div className="absolute inset-0 opacity-10 pointer-events-none" style={{ background: "linear-gradient(90deg, var(--color-info), transparent)" }} />

                <div className="z-10 flex items-center gap-4">
                    <div className="w-12 h-12 rounded-2xl flex items-center justify-center shadow-lg backdrop-blur-md" style={{ background: "color-mix(in srgb, var(--color-info) 20%, transparent)", border: "1px solid color-mix(in srgb, var(--color-info) 30%, transparent)", color: "var(--color-info)" }}>
                        <Sparkles size={24} />
                    </div>
                    <div>
                        <h2 className="text-xl font-black tracking-tight" style={{ color: "var(--text-primary)" }}>
                            New Concept
                        </h2>
                        <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>Knowledge Base Synthesizer</p>
                    </div>
                </div>

                <div className="z-10 flex items-center gap-2">
                    {STEPS.map((s, idx) => {
                        const active = step === s.num;
                        const past = step > s.num;
                        return (
                            <div key={s.num} className="flex items-center gap-2">
                                <div className="flex flex-col items-center gap-2 transition-all" style={{ opacity: active || past ? 1 : 0.4, width: 64 }}>
                                    <div
                                        className="w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300 relative z-10"
                                        style={{
                                            background: active ? "var(--color-info)" : past ? "var(--bg-panel)" : "transparent",
                                            border: `2px solid ${active || past ? "var(--color-info)" : "var(--border-node)"}`,
                                            color: active ? "white" : past ? "var(--color-info)" : "var(--text-muted)",
                                            boxShadow: active ? "0 0 20px color-mix(in srgb, var(--color-info) 40%, transparent)" : "none",
                                        }}
                                    >
                                        {past ? <Check size={16} strokeWidth={3} /> : s.icon}
                                    </div>
                                    <span className="text-[10px] font-bold uppercase tracking-widest text-center w-full" style={{ color: active ? "var(--color-info)" : "var(--text-muted)" }}>
                                        {s.title}
                                    </span>
                                </div>
                                {idx < STEPS.length - 1 && (
                                    <div className="w-8 h-[2px] rounded-full mb-5 transition-colors" style={{ background: past ? "var(--color-info)" : "var(--border-node)" }} />
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Separator inside gradient header */}
            <div className="flex-shrink-0 h-[1px] w-full z-20" style={{ background: "linear-gradient(90deg, transparent, var(--border-panel), transparent)" }} />

            {/* Main Content Area */}
            {/* Remove Absolute & min-h to let flex grow naturally within parent */}
            <div className="flex-1 overflow-x-hidden overflow-y-auto bg-[var(--bg-panel)] p-8">
                <AnimatePresence mode="wait" initial={false}>
                    {step === 1 && (
                        <motion.div
                            key="step1"
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            transition={transitions.snappy}
                            className="flex flex-col gap-8 max-w-2xl mx-auto w-full"
                        >
                            <div className="text-center">
                                <h3 className="text-2xl font-bold mb-2" style={{ color: "var(--text-primary)" }}>Define the Concept</h3>
                                <p className="text-sm" style={{ color: "var(--text-muted)" }}>Give your concept a clear name and a synthesized description that unifies its meaning constraint.</p>
                            </div>

                            {/* Aligned Grid for Inputs */}
                            <div className="grid grid-cols-3 gap-6 items-start mt-2">
                                <div className="col-span-2 flex flex-col gap-2">
                                    <label className="text-[10px] font-bold uppercase tracking-widest pl-1" style={{ color: "var(--color-info)" }}>Concept Name *</label>
                                    <input
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                        placeholder="e.g. Backpropagation"
                                        className="w-full rounded bg-[var(--bg-node)] px-3 py-2 outline-none text-xs font-mono transition-colors"
                                        style={{
                                            minHeight: 42,
                                            border: "var(--border-node)",
                                            color: "var(--text-primary)"
                                        }}
                                        onFocus={(e) => e.target.style.borderColor = "var(--color-info)"}
                                        onBlur={(e) => e.target.style.border = "var(--border-node)"}
                                    />
                                    {!isFormValid && (
                                        <p className="text-[10px] font-medium leading-none mt-1" style={{ color: "var(--color-error)" }}>
                                            Required to proceed
                                        </p>
                                    )}
                                </div>
                                <div className="col-span-1 flex flex-col gap-2">
                                    <label className="text-[10px] font-bold uppercase tracking-widest pl-1" style={{ color: "var(--text-secondary)" }}>Domain</label>
                                    <Select
                                        value={domain}
                                        onChange={(v) => setDomain(Array.isArray(v) ? v[0] : v)}
                                        placeholder="Select Domain"
                                        options={[
                                            { label: "AI / Machine Learning", value: "AI" },
                                            { label: "Data Engineering", value: "Data Eng" },
                                            { label: "Software Architecture", value: "Architecture" },
                                        ]}
                                    />
                                </div>
                            </div>

                            <div className="flex flex-col gap-2 mt-2">
                                <label className="text-[10px] font-bold uppercase tracking-widest pl-1" style={{ color: "var(--text-secondary)" }}>Synthesized Description</label>
                                <div
                                    className="rounded overflow-hidden transition-colors"
                                    style={{ background: "var(--bg-node)", border: "var(--border-node)" }}
                                >
                                    <textarea
                                        value={description}
                                        onChange={(e) => setDescription(e.target.value)}
                                        className="w-full min-h-[160px] p-3 text-xs outline-none bg-transparent resize-y font-mono"
                                        style={{
                                            color: "var(--text-primary)",
                                            lineHeight: "1.6",
                                        }}
                                        placeholder="Describe the core idea of this concept..."
                                    />
                                </div>
                            </div>
                        </motion.div>
                    )}

                    {step === 2 && (
                        <motion.div
                            key="step2"
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            transition={transitions.snappy}
                            className="flex flex-col gap-6 h-full w-full"
                        >
                            <div className="text-center flex-shrink-0">
                                <h3 className="text-2xl font-bold mb-2" style={{ color: "var(--text-primary)" }}>Select Truth Sources</h3>
                                <p className="text-sm" style={{ color: "var(--text-muted)" }}>Choose standard articles framing this concept. Select articles on the left to review keywords on the right.</p>
                            </div>

                            <div className="grid grid-cols-[1fr_340px] gap-8" style={{ minHeight: 400 }}>
                                {/* Articles Grid */}
                                <div className="flex flex-col gap-4">
                                    <div className="flex items-center justify-between px-2">
                                        <span className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>Available Articles ({availableArticles.length})</span>
                                        <span className="text-xs font-bold px-2 py-1 rounded bg-[color-mix(in_srgb,var(--color-info)_15%,transparent)]" style={{ color: "var(--color-info)" }}>{selectedArticles.size} selected</span>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4 content-start">
                                        {availableArticles.map((article) => {
                                            const selected = selectedArticles.has(article.id);
                                            return (
                                                <div
                                                    key={article.id}
                                                    onClick={() => toggleArticle(article.id)}
                                                    className="relative cursor-pointer transition-all duration-300 group"
                                                >
                                                    <div className="transition-transform duration-300 pointer-events-none rounded-2xl" style={{ transform: selected ? "scale(0.97)" : "scale(1)", boxShadow: selected ? "0 0 0 2px var(--color-success)" : "0 0 0 1px transparent" }}>
                                                        {/* We use a wrapper to inject the ring cleanly */}
                                                        <div className="rounded-2xl overflow-hidden transition-all duration-300 group-hover:shadow-[0_4px_20px_rgba(0,0,0,0.3)] bg-[var(--bg-node)]">
                                                            <ArticleCard {...article} />
                                                        </div>
                                                    </div>
                                                    <AnimatePresence>
                                                        {selected && (
                                                            <motion.div
                                                                initial={{ scale: 0, opacity: 0 }}
                                                                animate={{ scale: 1, opacity: 1 }}
                                                                exit={{ scale: 0, opacity: 0 }}
                                                                className="absolute -top-3 -right-3 w-8 h-8 rounded-full flex items-center justify-center shadow-xl z-10"
                                                                style={{
                                                                    background: "var(--color-success)",
                                                                    color: "white",
                                                                    border: "2px solid var(--bg-panel)"
                                                                }}
                                                            >
                                                                <Check size={16} strokeWidth={4} />
                                                            </motion.div>
                                                        )}
                                                    </AnimatePresence>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>

                                {/* Keywords Preview Sidebar */}
                                <div className="flex flex-col gap-4 pl-8 border-l" style={{ borderColor: "var(--border-panel)" }}>
                                    <div className="text-xs font-bold uppercase tracking-wider flex items-center justify-between" style={{ color: "var(--text-secondary)" }}>
                                        <span>Extracted Keywords</span>
                                        {selectedArticles.size > 0 && <Badge variant="info">{extractedKeywords.length}</Badge>}
                                    </div>

                                    {selectedArticles.size === 0 ? (
                                        <div className="flex flex-col items-center justify-center text-center p-8 border-2 rounded-2xl border-dashed bg-[rgba(0,0,0,0.05)] h-64" style={{ borderColor: "var(--border-node)" }}>
                                            <div className="w-14 h-14 rounded-full flex items-center justify-center mb-4 shadow-inner" style={{ background: "var(--bg-node)", color: "var(--text-muted)" }}>
                                                <Layers size={24} />
                                            </div>
                                            <h4 className="font-bold text-sm mb-1" style={{ color: "var(--text-primary)" }}>Preview Empty</h4>
                                            <p className="text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>Select articles to preview top aggregated keywords right here.</p>
                                        </div>
                                    ) : (
                                        <div className="border rounded-2xl overflow-hidden shadow-inner flex flex-col h-[400px]" style={{ borderColor: "var(--border-node)", background: "var(--bg-node)" }}>
                                            <div className="flex-1 overflow-auto">
                                                <DataTable
                                                    columns={keywordCols}
                                                    data={extractedKeywords}
                                                    rowKey={(r) => r.id}
                                                />
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </motion.div>
                    )}

                    {step === 3 && (
                        <motion.div
                            key="step3"
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            transition={transitions.snappy}
                            className="flex flex-col gap-8 max-w-2xl mx-auto w-full align-center justify-center py-4"
                        >
                            <div className="text-center mb-4">
                                <div className="w-20 h-20 mx-auto rounded-3xl flex items-center justify-center mb-6 shadow-[0_0_40px_rgba(59,130,246,0.3)]" style={{ background: "linear-gradient(135deg, color-mix(in srgb, var(--color-info) 30%, transparent), transparent)", border: "1px solid var(--color-info)" }}>
                                    <Sparkles size={36} style={{ color: "var(--color-info)" }} />
                                </div>
                                <h3 className="text-3xl font-black mb-3 tracking-tight" style={{ color: "var(--text-primary)" }}>Ready to Synthesize!</h3>
                                <p className="text-sm font-medium" style={{ color: "var(--text-muted)" }}>Review your concept architecture before publishing.</p>
                            </div>

                            <div className="flex flex-col gap-6 p-8 rounded-3xl border shadow-inner backdrop-blur-sm relative overflow-hidden group" style={{ borderColor: "var(--border-node)", background: "color-mix(in srgb, var(--bg-node) 80%, transparent)" }}>
                                <div className="absolute top-0 right-0 w-64 h-64 bg-[var(--color-info)] opacity-5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3 group-hover:opacity-10 transition-opacity pointer-events-none" />

                                <div className="relative z-10 flex items-start justify-between">
                                    <div>
                                        <h1 className="text-3xl font-black tracking-tight mb-3 leading-tight" style={{ color: "var(--text-primary)" }}>{name || "Untitled Concept"}</h1>
                                        {domain && <div><Badge variant="info">{domain}</Badge></div>}
                                    </div>
                                </div>

                                <div className="relative z-10 h-[1px] w-full border-t border-dashed my-2" style={{ borderColor: "var(--border-panel)" }} />

                                <div className="relative z-10">
                                    <h4 className="text-[10px] font-bold uppercase tracking-widest mb-3" style={{ color: "var(--text-secondary)" }}>Description</h4>
                                    <div className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                                        {description ? `"${description}"` : <span className="italic opacity-50">No description provided.</span>}
                                    </div>
                                </div>

                                <div className="relative z-10 mt-2">
                                    <h4 className="text-[10px] font-bold uppercase tracking-widest mb-3 flex items-center gap-2" style={{ color: "var(--text-secondary)" }}>
                                        <FileText size={12} /> Sourced From {selectedArticles.size} Articles
                                    </h4>
                                    <div className="flex flex-wrap gap-2">
                                        {Array.from(selectedArticles).map(id => {
                                            const a = availableArticles.find(art => art.id === id);
                                            if (!a) return null;
                                            return (
                                                <div key={id} className="px-3 py-1.5 rounded-xl text-xs font-semibold border shadow-sm" style={{ background: "var(--bg-panel)", borderColor: "var(--border-node)", color: "var(--text-primary)" }}>
                                                    {a.title}
                                                </div>
                                            );
                                        })}
                                        {selectedArticles.size === 0 && <span className="text-xs italic" style={{ color: "var(--text-muted)" }}>No sources selected.</span>}
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Footer */}
            <div className="flex-shrink-0 flex items-center justify-between p-6 px-8 z-20" style={{ background: "var(--bg-node)", borderTop: "1px solid var(--border-panel)" }}>
                <button
                    onClick={onClose}
                    className="text-sm font-bold px-5 py-2.5 rounded-xl hover:bg-white/5 transition-colors"
                    style={{ color: "var(--text-muted)" }}
                >
                    Cancel
                </button>

                <div className="flex items-center gap-4">
                    {step > 1 && (
                        <button
                            onClick={handlePrev}
                            className="flex items-center gap-2 text-sm font-bold px-6 py-2.5 rounded-xl transition-all border shadow-sm hover:brightness-110 disabled:opacity-50"
                            style={{
                                background: "var(--bg-panel)",
                                borderColor: "var(--border-node)",
                                color: "var(--text-primary)"
                            }}
                        >
                            <ChevronLeft size={16} /> Back
                        </button>
                    )}

                    {step < 3 ? (
                        <button
                            onClick={handleNext}
                            className="flex items-center gap-2 text-sm font-bold px-8 py-2.5 rounded-xl transition-all shadow-lg hover:brightness-110 transform active:scale-95 disabled:pointer-events-none"
                            disabled={!isFormValid}
                            style={{
                                background: isFormValid ? "var(--color-info)" : "var(--bg-panel)",
                                color: isFormValid ? "var(--text-inverse)" : "var(--text-muted)",
                                borderColor: isFormValid ? "transparent" : "var(--border-node)",
                                borderWidth: 1,
                                boxShadow: isFormValid ? "0 4px 14px 0 color-mix(in srgb, var(--color-info) 40%, transparent)" : "none",
                                opacity: isFormValid ? 1 : 0.4
                            }}
                        >
                            Next <ChevronRight size={16} />
                        </button>
                    ) : (
                        <button
                            onClick={() => onSubmit?.({ name, domain, description, sources: Array.from(selectedArticles) })}
                            className="relative overflow-hidden group flex items-center gap-2 text-sm font-bold px-8 py-2.5 rounded-xl transition-all shadow-[0_0_20px_rgba(34,197,94,0.3)] hover:shadow-[0_0_30px_rgba(34,197,94,0.5)] transform active:scale-95"
                            style={{ background: "var(--color-success)", color: "white", textShadow: "0 1px 2px rgba(0,0,0,0.5)" }}
                        >
                            <div className="absolute inset-0 w-full h-full bg-white/20 -translate-x-full group-hover:translate-x-full transition-transform duration-700 ease-in-out skew-x-12 pointer-events-none" />
                            <Sparkles size={16} /> Publish Concept
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
