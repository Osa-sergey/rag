import type { Meta, StoryObj } from "@storybook/react";
import { DataTable, Column } from "./DataTable";
import { Badge } from "../Badge";
import { StatusIcon } from "../StatusIcon";

const meta: Meta = {
    title: "UI Kit/DataTable",
    tags: ["autodocs"],
    parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj;

interface StepRow {
    name: string;
    module: string;
    status: string;
    config_fields: number;
    has_callbacks: boolean;
}

const stepColumns: Column<StepRow>[] = [
    {
        key: "name",
        header: "Step Name",
        sortable: true,
        width: "200px",
        render: (row) => (
            <span className="font-medium" style={{ color: "var(--color-step)" }}>
                {row.name}
            </span>
        ),
    },
    { key: "module", header: "Module", sortable: true },
    {
        key: "status",
        header: "Status",
        render: (row) => (
            <StatusIcon
                status={row.status === "success" ? "success" : row.status === "failed" ? "error" : "idle"}
                label={row.status}
                size={8}
            />
        ),
    },
    {
        key: "config_fields",
        header: "Config Fields",
        sortable: true,
        render: (row) => (
            <Badge variant="default" size="sm">{row.config_fields}</Badge>
        ),
    },
    {
        key: "has_callbacks",
        header: "Callbacks",
        render: (row) =>
            row.has_callbacks ? (
                <Badge variant="info" size="sm">✓</Badge>
            ) : (
                <span style={{ color: "var(--text-muted)" }}>—</span>
            ),
    },
];

const stepData: StepRow[] = [
    { name: "parse_articles", module: "raptor_pipeline.parse", status: "success", config_fields: 4, has_callbacks: false },
    { name: "build_raptor_tree", module: "raptor_pipeline.build", status: "success", config_fields: 8, has_callbacks: true },
    { name: "extract_keywords", module: "keyword_extractor.run", status: "idle", config_fields: 6, has_callbacks: true },
    { name: "build_concepts", module: "concept_builder.run", status: "failed", config_fields: 12, has_callbacks: true },
    { name: "index_vectors", module: "qdrant_indexer.upsert", status: "idle", config_fields: 3, has_callbacks: false },
];

export const PipelineSteps: Story = {
    name: "Pipeline Steps",
    render: () => (
        <DataTable<StepRow>
            columns={stepColumns}
            data={stepData}
            rowKey={(row) => row.name}
        />
    ),
};

export const Loading: Story = {
    name: "Loading State",
    render: () => (
        <DataTable<StepRow>
            columns={stepColumns}
            data={[]}
            rowKey={(row) => row.name}
            loading={true}
        />
    ),
};

export const Empty: Story = {
    name: "Empty State",
    render: () => (
        <DataTable<StepRow>
            columns={stepColumns}
            data={[]}
            rowKey={(row) => row.name}
            emptyMessage="No steps configured. Drag steps from the palette to begin."
        />
    ),
};

interface ConceptRow {
    name: string;
    domain: string;
    version: number;
    keywords_count: number;
    is_stale: boolean;
}

const conceptColumns: Column<ConceptRow>[] = [
    {
        key: "name",
        header: "Concept",
        sortable: true,
        render: (row) => (
            <span className="font-medium" style={{ color: "var(--color-concept)" }}>
                💡 {row.name}
            </span>
        ),
    },
    { key: "domain", header: "Domain", sortable: true },
    {
        key: "version",
        header: "Version",
        sortable: true,
        render: (row) => (
            <Badge variant="info" size="sm">v{row.version}</Badge>
        ),
    },
    {
        key: "keywords_count",
        header: "Keywords",
        sortable: true,
    },
    {
        key: "is_stale",
        header: "Status",
        render: (row) =>
            row.is_stale ? (
                <Badge variant="stale" size="sm">⚠️ stale</Badge>
            ) : (
                <Badge variant="success" size="sm">active</Badge>
            ),
    },
];

const conceptData: ConceptRow[] = [
    { name: "Event-Driven Architecture", domain: "architecture", version: 3, keywords_count: 18, is_stale: false },
    { name: "RAG Pipeline", domain: "ml", version: 2, keywords_count: 24, is_stale: true },
    { name: "Circuit Breaker", domain: "patterns", version: 1, keywords_count: 7, is_stale: false },
    { name: "RAPTOR Indexing", domain: "ml", version: 4, keywords_count: 32, is_stale: true },
];

export const ConceptsList: Story = {
    name: "Concepts List (KB)",
    render: () => (
        <DataTable<ConceptRow>
            columns={conceptColumns}
            data={conceptData}
            rowKey={(row) => row.name}
        />
    ),
};
