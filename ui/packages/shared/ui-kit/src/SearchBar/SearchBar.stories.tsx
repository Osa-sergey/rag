import React, { useState, useMemo } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { SearchBar, FilterValue, Suggestion } from "./SearchBar";
import { Database, Brain, FileText, Tag, Layers, Zap } from "lucide-react";

const meta: Meta<typeof SearchBar> = {
    title: "UI Kit/SearchBar",
    component: SearchBar,
    tags: ["autodocs"],
    argTypes: {
        expandOnFocus: { control: "boolean" },
        collapsedWidth: { control: { type: "range", min: 120, max: 400, step: 20 } },
        expandedWidth: { control: { type: "range", min: 200, max: 600, step: 20 } },
    },
    parameters: { layout: "centered" },
};

export default meta;
type Story = StoryObj<typeof SearchBar>;

export const Default: Story = {
    args: { placeholder: "Search steps...", expandOnFocus: true },
};

export const WithValue: Story = {
    args: { value: "raptor_pipeline", placeholder: "Search steps..." },
};

// --- Grouped filters ---

const kbFilters = [
    { prefix: "type:", label: "Entity type", type: "select" as const, options: ["article", "concept", "keyword"], color: "var(--color-concept)", group: "Entity Filters" },
    { prefix: "domain:", label: "Domain", type: "select" as const, options: ["ML", "NLP", "Deep Learning", "Data Engineering"], color: "var(--color-info)", group: "Entity Filters" },
    { prefix: "status:", label: "Status", type: "select" as const, options: ["active", "stale", "manual"], color: "var(--color-warning)", group: "State Filters" },
    { prefix: "score:", label: "Relevance score", type: "range" as const, rangeLow: 0, rangeHigh: 1, step: 0.05, format: (v: number) => v.toFixed(2), color: "var(--color-success)", group: "Numeric Filters" },
    { prefix: "chunks:", label: "Chunk count", type: "integer" as const, rangeLow: 0, rangeHigh: 100, step: 1, color: "var(--color-info)", group: "Numeric Filters" },
];

const dagFilters = [
    { prefix: "status:", label: "Step status", type: "select" as const, options: ["idle", "running", "success", "failed"], color: "var(--color-info)", group: "Pipeline" },
    { prefix: "tag:", label: "Step tag", type: "select" as const, options: ["etl", "ml", "indexing", "validation"], color: "var(--color-success)", group: "Pipeline" },
    { prefix: "retries:", label: "Max retries", type: "integer" as const, rangeLow: 0, rangeHigh: 10, step: 1, color: "var(--color-warning)", group: "Config" },
    { prefix: "timeout:", label: "Timeout (sec)", type: "range" as const, rangeLow: 0, rangeHigh: 300, step: 10, color: "var(--color-error)", group: "Config" },
];

const WithFiltersDemo = ({ filterDefs, placeholder }: { filterDefs: any[]; placeholder: string }) => {
    const [val, setVal] = useState("");
    const [active, setActive] = useState<Record<string, FilterValue>>({});
    return (
        <SearchBar value={val} onChange={setVal} placeholder={placeholder} expandOnFocus expandedWidth={440}
            filters={filterDefs} activeFilters={active}
            onFilterChange={(prefix, value) => {
                if (value === undefined) setActive((prev) => { const n = { ...prev }; delete n[prefix]; return n; });
                else setActive((prev) => ({ ...prev, [prefix]: value }));
            }} />
    );
};

export const GroupedKBFilters: Story = {
    name: "🧩 Grouped KB Filters — Entity / State / Numeric",
    render: () => <WithFiltersDemo filterDefs={kbFilters} placeholder="Search KB... (try type: or score:)" />,
};

export const GroupedDAGFilters: Story = {
    name: "🧩 Grouped DAG Filters — Pipeline / Config",
    render: () => <WithFiltersDemo filterDefs={dagFilters} placeholder="Search steps... (try status: or timeout:)" />,
};

// --- Autocomplete ---

const allEntities: Suggestion[] = [
    { id: "c1", text: "RAG Pipeline Architecture", subtitle: "Core pipeline design concept", group: "Concepts", icon: <Brain size={12} />, color: "var(--color-concept)" },
    { id: "c2", text: "Embedding Models Comparison", subtitle: "OpenAI vs HuggingFace", group: "Concepts", icon: <Brain size={12} />, color: "var(--color-concept)" },
    { id: "c3", text: "RAPTOR Tree Summarization", subtitle: "Hierarchical abstraction", group: "Concepts", icon: <Brain size={12} />, color: "var(--color-concept)" },
    { id: "a1", text: "Building RAG Systems with LangChain", subtitle: "Article • 24 chunks", group: "Articles", icon: <FileText size={12} />, color: "var(--color-info)" },
    { id: "a2", text: "Qdrant Vector Database Guide", subtitle: "Article • 18 chunks", group: "Articles", icon: <FileText size={12} />, color: "var(--color-info)" },
    { id: "k1", text: "transformer", subtitle: "Score: 0.92 • 5 concepts", group: "Keywords", icon: <Tag size={12} />, color: "var(--color-success)" },
    { id: "k2", text: "gradient descent", subtitle: "Score: 0.95 • 3 concepts", group: "Keywords", icon: <Tag size={12} />, color: "var(--color-success)" },
    { id: "k3", text: "attention mechanism", subtitle: "Score: 0.88 • 4 concepts", group: "Keywords", icon: <Tag size={12} />, color: "var(--color-success)" },
    { id: "s1", text: "parse_articles", subtitle: "ETL step • idle", group: "Steps", icon: <Layers size={12} />, color: "var(--text-muted)" },
    { id: "s2", text: "build_raptor_tree", subtitle: "ML step • success", group: "Steps", icon: <Zap size={12} />, color: "var(--color-warning)" },
];

const AutocompleteDemo = () => {
    const [val, setVal] = useState("");

    const filtered = useMemo(() => {
        if (!val.trim()) return [];
        const q = val.toLowerCase();
        return allEntities.filter((e) => e.text.toLowerCase().includes(q) || e.subtitle?.toLowerCase().includes(q));
    }, [val]);

    return (
        <SearchBar
            value={val}
            onChange={setVal}
            placeholder="Search everything... (try 'rag' or 'trans')"
            expandOnFocus
            expandedWidth={440}
            suggestions={filtered}
            onSuggestionSelect={(s) => { setVal(s.text); alert(`Selected: ${s.text} (${s.group})`); }}
        />
    );
};

export const Autocomplete: Story = {
    name: "🧩 Autocomplete — Grouped Suggestions",
    render: () => <AutocompleteDemo />,
};

const FullDemo = () => {
    const [val, setVal] = useState("");
    const [active, setActive] = useState<Record<string, FilterValue>>({});

    const filtered = useMemo(() => {
        if (!val.trim()) return [];
        const q = val.toLowerCase();
        return allEntities.filter((e) => e.text.toLowerCase().includes(q));
    }, [val]);

    return (
        <SearchBar
            value={val}
            onChange={setVal}
            placeholder="KB search — filters + autocomplete"
            expandOnFocus
            expandedWidth={460}
            filters={kbFilters}
            activeFilters={active}
            onFilterChange={(prefix, value) => {
                if (value === undefined) setActive((prev) => { const n = { ...prev }; delete n[prefix]; return n; });
                else setActive((prev) => ({ ...prev, [prefix]: value }));
            }}
            suggestions={filtered}
            onSuggestionSelect={(s) => setVal(s.text)}
        />
    );
};

export const FullFeatured: Story = {
    name: "🧩 Full — Filters + Autocomplete + Groups",
    render: () => <FullDemo />,
};
