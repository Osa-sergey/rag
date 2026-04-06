import { StepStatus, StepNodePort, CallbackInfo, ContextInfo } from "../StepNode/StepNode";
import type { FlowEdge } from "../FlowCanvas/FlowCanvas";
import { PaletteStep } from "../NodePalette/NodePalette";
import { ValidationError } from "../ValidationOverlay/ValidationOverlay";
import { InspectorField } from "../InspectorPanel/InspectorPanel";

import { Popover } from "../Popover";
import { YamlPanel } from "../YamlPanel/YamlPanel";

// ═══════════════════════════════════════════════════════════════
// EdgeBadge — data-type label on edges
// ═══════════════════════════════════════════════════════════════
export function EdgeBadge({ text, variant = "normal", description }: { text: string; variant?: "normal" | "error", description?: string }) {
    const isErr = variant === "error";

    const badge = (
        <span className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold shadow-sm whitespace-nowrap transition-colors ${description ? "cursor-pointer hover:opacity-80" : ""}`}
            style={{
                background: isErr
                    ? "color-mix(in srgb, var(--color-error) 15%, var(--bg-canvas, #0a0a0f))"
                    : "color-mix(in srgb, var(--color-info) 15%, var(--bg-canvas, #0a0a0f))",
                color: isErr ? "var(--color-error)" : "var(--color-info)",
                border: isErr
                    ? "1px solid color-mix(in srgb, var(--color-error) 40%, transparent)"
                    : "1px solid color-mix(in srgb, var(--color-info) 20%, transparent)",
            }}>
            {isErr && "⚠ "}{text}
        </span>
    );

    if (description) {
        return (
            <Popover trigger="click" placement="top" width="auto" maxWidth={420} draggable content={
                <div className="rounded-xl overflow-hidden" style={{ width: 320, height: 220 }}>
                    <div className="w-full h-full overflow-auto">
                        <YamlPanel
                            title={`${text} Schema`}
                            content={description}
                        />
                    </div>
                </div>
            }>
                {badge}
            </Popover>
        );
    }

    return badge;
}

// ═══════════════════════════════════════════════════════════════
// Palette steps catalogue
// ═══════════════════════════════════════════════════════════════
export const PALETTE_STEPS: PaletteStep[] = [
    { id: "t_parse", name: "Parse Articles", module: "article_parser.run", category: "ETL" },
    { id: "t_fetch", name: "Fetch Sources", module: "extract.fetch", category: "ETL" },
    { id: "t_clean", name: "Clean Text", module: "transform.clean", category: "ETL" },
    { id: "t_chunk", name: "Chunk Text", module: "transform.chunk", category: "ETL" },
    { id: "t_embed", name: "Embed Vectors", module: "ml.embed", category: "ML" },
    { id: "t_train", name: "Train Model", module: "ml.train", category: "ML" },
    { id: "t_raptor", name: "Build RAPTOR", module: "raptor_pipeline.run", category: "Indexing" },
    { id: "t_qdrant", name: "Index Qdrant", module: "stores.qdrant.index", category: "Indexing" },
    { id: "t_neo4j", name: "Index Neo4j", module: "stores.neo4j.index", category: "Indexing" },
    { id: "t_validate", name: "Validate Schema", module: "validators.schema_check", category: "Validation" },
    { id: "t_alert", name: "Send Alert", module: "notify.slack", category: "Utility" },
    { id: "t_export", name: "Export Report", module: "export.report", category: "Utility" },
];

// ═══════════════════════════════════════════════════════════════
// Palette groups catalogue
// ═══════════════════════════════════════════════════════════════
import { PaletteGroupDef } from "../GroupPalette/GroupPalette";

import { StepNode } from "../StepNode/StepNode";

export const PALETTE_GROUPS: PaletteGroupDef[] = [
    {
        id: "g_rag_core",
        name: "Basic RAG Core",
        description: "Parse, Clean, Embed",
        previewNodes: [
            {
                id: "n1", x: 20, y: 30, width: 140, height: 75,
                ports: [{ id: "o1", side: "right", index: 0, total: 1, dataType: "List[str]" }],
                content: <StepNode name="parse_articles" module="article_parser" outputs={[{ id: "o1", label: "chunks" }]} compact />
            },
            {
                id: "n2", x: 180, y: 30, width: 140, height: 75,
                ports: [{ id: "i1", side: "left", index: 0, total: 1, dataType: "List[str]" }, { id: "o1", side: "right", index: 0, total: 1, dataType: "ndarray" }],
                content: <StepNode name="clean_text" module="transform" inputs={[{ id: "i1", label: "chunks" }]} outputs={[{ id: "o1", label: "clean" }]} compact />
            },
            {
                id: "n3", x: 340, y: 30, width: 140, height: 75,
                ports: [{ id: "i1", side: "left", index: 0, total: 1, dataType: "ndarray" }],
                content: <StepNode name="embed_vectors" module="ml" inputs={[{ id: "i1", label: "clean" }]} compact />
            },
        ],
        previewEdges: [
            { id: "e1", from: "n1", to: "n2", fromPort: "o1", toPort: "i1" },
            { id: "e2", from: "n2", to: "n3", fromPort: "o1", toPort: "i1" },
        ]
    },
    {
        id: "g_indexx",
        name: "Dual Indexing",
        description: "Qdrant + Neo4j RAPTOR",
        previewNodes: [
            {
                id: "n1", x: 20, y: 100, width: 140, height: 75,
                ports: [{ id: "o1", side: "right", index: 0, total: 1, dataType: "RaptorTree" }],
                content: <StepNode name="build_raptor" module="indexing" outputs={[{ id: "o1", label: "tree" }]} compact />
            },
            {
                id: "n2", x: 220, y: 30, width: 140, height: 75,
                ports: [{ id: "i1", side: "left", index: 0, total: 1, dataType: "ndarray" }],
                content: <StepNode name="index_qdrant" module="indexing" inputs={[{ id: "i1", label: "vectors" }]} compact />
            },
            {
                id: "n3", x: 220, y: 170, width: 140, height: 75,
                ports: [{ id: "i1", side: "left", index: 0, total: 1, dataType: "RaptorTree" }],
                content: <StepNode name="index_neo4j" module="indexing" inputs={[{ id: "i1", label: "tree" }]} compact />
            },
        ],
        previewEdges: [
            { id: "e1", from: "n1", to: "n3", fromPort: "o1", toPort: "i1" }
        ]
    }
];

// ═══════════════════════════════════════════════════════════════
// Step definitions for the RAG pipeline demo
// ═══════════════════════════════════════════════════════════════
export interface StepDef {
    id: string;
    name: string;
    module: string;
    status: StepStatus;
    x: number;
    y: number;
    tags?: string[];
    inputs?: StepNodePort[];
    outputs?: StepNodePort[];
    callbacks?: CallbackInfo[];
    context?: ContextInfo;
    errors?: string[];
    compact?: boolean;
    appearance?: { color: string; icon: string };
    typeId?: string;
    stepCallbacks?: any[];
    width?: number;
    height?: number;
}

export const RAG_STEPS: StepDef[] = [
    {
        id: "s_parse", name: "parse_articles", module: "article_parser.run",
        status: "idle", x: 40, y: 70, tags: ["etl"], typeId: "etl",
        outputs: [{ id: "o_chunks", label: "chunks", type: "List[str]" }, { id: "o_meta", label: "metadata", type: "dict" }],
        width: 200, height: 120,
    },
    {
        id: "s_clean", name: "clean_text", module: "transform.clean",
        status: "idle", x: 320, y: 75, tags: ["etl"], typeId: "etl",
        inputs: [{ id: "i_chunks", label: "raw_chunks", type: "List[str]" }],
        outputs: [{ id: "o_clean", label: "clean_chunks", type: "List[str]" }],
        width: 200, height: 110,
    },
    {
        id: "s_embed", name: "embed_vectors", module: "ml.embed",
        status: "idle", x: 320, y: 230, tags: ["ml"], typeId: "ml",
        inputs: [{ id: "i_meta", label: "metadata", type: "dict" }],
        outputs: [{ id: "o_vectors", label: "vectors", type: "ndarray" }],
        width: 200, height: 110,
    },
    {
        id: "s_raptor", name: "build_raptor", module: "raptor_pipeline.run",
        status: "idle", x: 600, y: 75, tags: ["indexing"], typeId: "indexing",
        inputs: [{ id: "i_chunks", label: "clean_chunks", type: "List[str]" }],
        outputs: [{ id: "o_tree", label: "raptor_tree", type: "RaptorTree" }],
        callbacks: [{ type: "on_retry", params: "max=3" }],
        context: { provides: ["RaptorContext"] },
        width: 200, height: 130,
    },
    {
        id: "s_qdrant", name: "index_qdrant", module: "stores.qdrant.index",
        status: "idle", x: 600, y: 240, tags: ["indexing"], typeId: "indexing",
        inputs: [{ id: "i_vectors", label: "vectors", type: "ndarray" }],
        outputs: [{ id: "o_ids", label: "point_ids", type: "List[str]" }],
        width: 200, height: 110,
    },
    {
        id: "s_neo4j", name: "index_neo4j", module: "stores.neo4j.index",
        status: "idle", x: 880, y: 75, tags: ["indexing"], typeId: "indexing",
        inputs: [{ id: "i_tree", label: "raptor_tree", type: "RaptorTree" }, { id: "i_ids", label: "point_ids", type: "List[str]" }],
        context: { requires: ["RaptorContext"] },
        callbacks: [{ type: "on_success" }, { type: "on_failure" }],
        width: 200, height: 130,
    },
    {
        id: "s_validate", name: "validate_output", module: "validators.schema_check",
        status: "idle", x: 880, y: 260, tags: ["validation"], typeId: "validation",
        inputs: [{ id: "i_ids", label: "point_ids", type: "List[str]" }],
        outputs: [{ id: "o_report", label: "report", type: "dict" }],
        width: 200, height: 110,
    },
    {
        id: "s_alert", name: "send_alert", module: "notify.slack",
        status: "idle", x: 1140, y: 160, tags: ["utility"], typeId: "notify",
        inputs: [{ id: "i_report", label: "report", type: "dict" }],
        callbacks: [{ type: "on_alert", params: "#pipeline-alerts" }],
        compact: true,
        width: 160, height: 80,
    },
];

// ═══════════════════════════════════════════════════════════════
// Edge definitions
// ═══════════════════════════════════════════════════════════════
export const RAPTOR_TREE_SCHEMA = `type: object
properties:
  root:
    type: string
    description: "ID of the root node"
  nodes:
    type: dict[str, Node]
    description: "All nodes in the tree"
  edges:
    type: list[tuple[str, str]]
    description: "Parent-child relationships"`;

export const RAG_EDGES: FlowEdge[] = [
    { id: "e1", from: "s_parse", to: "s_clean", fromPort: "o_chunks", toPort: "i_chunks", label: <EdgeBadge text="List[str]" /> },
    { id: "e2", from: "s_parse", to: "s_embed", fromPort: "o_meta", toPort: "i_meta", label: <EdgeBadge text="dict" /> },
    { id: "e3", from: "s_clean", to: "s_raptor", fromPort: "o_clean", toPort: "i_chunks", label: <EdgeBadge text="List[str]" /> },
    { id: "e4", from: "s_embed", to: "s_qdrant", fromPort: "o_vectors", toPort: "i_vectors", label: <EdgeBadge text="ndarray" /> },
    { id: "e5", from: "s_raptor", to: "s_neo4j", fromPort: "o_tree", toPort: "i_tree", label: <EdgeBadge text="RaptorTree" description={RAPTOR_TREE_SCHEMA} /> },
    { id: "e6", from: "s_qdrant", to: "s_neo4j", fromPort: "o_ids", toPort: "i_ids", label: <EdgeBadge text="List[str]" /> },
    { id: "e7", from: "s_qdrant", to: "s_validate", fromPort: "o_ids", toPort: "i_ids", label: <EdgeBadge text="List[str]" /> },
    { id: "e8", from: "s_validate", to: "s_alert", fromPort: "o_report", toPort: "i_report", label: <EdgeBadge text="dict" /> },
];

// ═══════════════════════════════════════════════════════════════
// Validation errors demo data
// ═══════════════════════════════════════════════════════════════
export const DEMO_ERRORS: ValidationError[] = [
    { id: "v1", severity: "error", message: "Output ref invalid: ${{ steps.train_model.embeddings }}", nodeId: "s_embed", nodeName: "embed_vectors", field: "config.input" },
    { id: "v2", severity: "error", message: "Type mismatch: output 'str' → input expects 'int'", nodeId: "s_qdrant", nodeName: "index_qdrant", field: "vectors" },
    { id: "v3", severity: "warning", message: "Context prerequisite: 'index_neo4j' requires RaptorContext", nodeId: "s_neo4j", nodeName: "index_neo4j" },
    { id: "v4", severity: "warning", message: "Missing dependency: depends_on 'normalize' — step not found", nodeId: "s_clean", nodeName: "clean_text" },
];

export const INSPECTOR_DATA: Record<string, {
    stepName: string; module: string;
    configFields?: InspectorField[];
    inputFields?: Array<{ key: string; type: string; description?: string }>;
    outputFields?: Array<{ key: string; type: string; description?: string }>;
    callbacks?: Array<{ type: string; params?: string }>;
    context?: { provides?: string[]; requires?: string[] };
}> = {
    s_parse: {
        stepName: "parse_articles", module: "article_parser.run",
        configFields: [
            { key: "chunk_size", value: "512", type: "number", source: "DEF" },
            { key: "overlap", value: "64", type: "number", source: "GLB" },
            { key: "format", value: "markdown", source: "STP" },
        ],
        outputFields: [
            { key: "chunks", type: "List[str]", description: "Parsed text chunks" },
            { key: "metadata", type: "dict", description: "Article metadata (title, date, author)" },
        ],
    },
    s_clean: {
        stepName: "clean_text", module: "transform.clean",
        configFields: [
            { key: "drop_nulls", value: "true", source: "GLB" },
            { key: "strip_html", value: "true", source: "DEF" },
            { key: "min_length", value: "50", source: "STP" },
        ],
        inputFields: [{ key: "raw_chunks", type: "List[str]" }],
        outputFields: [{ key: "clean_chunks", type: "List[str]" }],
    },
    s_embed: {
        stepName: "embed_vectors", module: "ml.embed",
        configFields: [
            { key: "model", value: "sentence-transformers/all-MiniLM-L6-v2", source: "STP" },
            { key: "batch_size", value: "32", source: "DEF" },
            { key: "dimension", value: "384", source: "DEF" },
        ],
        inputFields: [{ key: "metadata", type: "dict" }],
        outputFields: [{ key: "vectors", type: "ndarray" }],
    },
    s_raptor: {
        stepName: "build_raptor", module: "raptor_pipeline.run",
        configFields: [
            { key: "max_depth", value: "4", source: "STP" },
            { key: "summarizer", value: "gpt-4o-mini", source: "OVR" },
        ],
        inputFields: [{ key: "clean_chunks", type: "List[str]" }],
        outputFields: [{ key: "raptor_tree", type: "RaptorTree", description: RAPTOR_TREE_SCHEMA }],
        callbacks: [{ type: "on_retry", params: "max_retries=3, delay=5s" }],
        context: { provides: ["RaptorContext"] },
    },
    s_qdrant: {
        stepName: "index_qdrant", module: "stores.qdrant.index",
        configFields: [
            { key: "collection", value: "habr_articles", source: "STP" },
            { key: "host", value: "localhost:6333", source: "GLB" },
        ],
        inputFields: [{ key: "vectors", type: "ndarray" }],
        outputFields: [{ key: "point_ids", type: "List[str]" }],
    },
    s_neo4j: {
        stepName: "index_neo4j", module: "stores.neo4j.index",
        configFields: [
            { key: "uri", value: "bolt://localhost:7687", source: "GLB" },
            { key: "database", value: "habr", source: "STP" },
        ],
        inputFields: [
            { key: "raptor_tree", type: "RaptorTree", description: RAPTOR_TREE_SCHEMA },
            { key: "point_ids", type: "List[str]" },
        ],
        callbacks: [{ type: "on_success" }, { type: "on_failure" }],
        context: { requires: ["RaptorContext"] },
    },
    s_validate: {
        stepName: "validate_output", module: "validators.schema_check",
        configFields: [{ key: "strict", value: "true", source: "DEF" }],
        inputFields: [{ key: "point_ids", type: "List[str]" }],
        outputFields: [{ key: "report", type: "dict" }],
    },
    s_alert: {
        stepName: "send_alert", module: "notify.slack",
        configFields: [
            { key: "channel", value: "#pipeline-alerts", source: "STP" },
            { key: "severity", value: "info", source: "DEF" },
        ],
        inputFields: [{ key: "report", type: "dict" }],
        callbacks: [{ type: "on_alert", params: "#pipeline-alerts" }],
    },
};

// ═══════════════════════════════════════════════════════════════
// YAML content
// ═══════════════════════════════════════════════════════════════
export const PIPELINE_YAML = `pipeline:
  name: raptor_indexing
  version: "3.0"
  executor: kubernetes
  
  globals:
    stores:
      neo4j:
        uri: bolt://localhost:7687
        database: habr
      qdrant:
        host: localhost:6333
        collection: habr_articles

  steps:
    - name: parse_articles
      module: article_parser.run
      config:
        chunk_size: 512
        overlap: 64
        format: markdown
      outputs:
        chunks: List[str]
        metadata: dict

    - name: clean_text
      module: transform.clean
      depends_on: [parse_articles]
      config:
        drop_nulls: true
        strip_html: true
        min_length: 50
      inputs:
        raw_chunks: \${{ steps.parse_articles.chunks }}

    - name: embed_vectors
      module: ml.embed
      depends_on: [parse_articles]
      config:
        model: sentence-transformers/all-MiniLM-L6-v2
        batch_size: 32
      inputs:
        metadata: \${{ steps.parse_articles.metadata }}

    - name: build_raptor
      module: raptor_pipeline.run
      depends_on: [clean_text]
      config:
        max_depth: 4
        summarizer: gpt-4o-mini
      callbacks:
        - type: on_retry
          params: { max_retries: 3, delay: 5 }
      context:
        provides: [RaptorContext]

    - name: index_qdrant
      module: stores.qdrant.index
      depends_on: [embed_vectors]
      config:
        collection: \${{ globals.stores.qdrant.collection }}
        host: \${{ globals.stores.qdrant.host }}

    - name: index_neo4j
      module: stores.neo4j.index
      depends_on: [build_raptor, index_qdrant]
      config:
        uri: \${{ globals.stores.neo4j.uri }}
        database: \${{ globals.stores.neo4j.database }}
      context:
        requires: [RaptorContext]

    - name: validate_output
      module: validators.schema_check
      depends_on: [index_qdrant]
      config:
        strict: true

    - name: send_alert
      module: notify.slack
      depends_on: [validate_output]
      config:
        channel: "#pipeline-alerts"
`;
