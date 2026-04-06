import React, { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { NodePalette } from "./NodePalette";

const meta: Meta<typeof NodePalette> = {
    title: "DAG Builder/NodePalette",
    component: NodePalette,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj<typeof NodePalette>;

const sampleSteps = [
    { id: "1", name: "parse_articles", module: "raptor.parse.ArticleParser", category: "ETL" },
    { id: "2", name: "extract_keywords", module: "raptor.keywords.KeywordExtractor", category: "ETL" },
    { id: "3", name: "build_concepts", module: "raptor.concept.ConceptBuilder", category: "ML" },
    { id: "4", name: "build_tree", module: "raptor.tree.TreeBuilder", category: "ML" },
    { id: "5", name: "index_vectors", module: "raptor.store.QdrantIndexer", category: "Indexing" },
];

const ShortList = () => {
    const [q, setQ] = useState("");
    return <NodePalette steps={sampleSteps} searchQuery={q} onSearch={setQ} />;
};

export const FiveSteps: Story = {
    name: "🧩 5 Steps — Short List (A1)",
    render: () => <ShortList />,
};

const manySteps = [
    ...sampleSteps,
    { id: "6", name: "validate_schema", module: "raptor.validate.SchemaValidator", category: "Validation" },
    { id: "7", name: "embed_chunks", module: "raptor.embed.ChunkEmbedder", category: "ML" },
    { id: "8", name: "merge_duplicates", module: "raptor.dedup.DuplicateMerger", category: "ETL" },
    { id: "9", name: "export_neo4j", module: "raptor.store.Neo4jExporter", category: "Indexing" },
    { id: "10", name: "notify_pipeline", module: "raptor.notify.PipelineNotifier", category: "Utility" },
    { id: "11", name: "cache_results", module: "raptor.cache.ResultCache", category: "Utility" },
    { id: "12", name: "compute_similarity", module: "raptor.sim.SimilarityComputer", category: "ML" },
    { id: "13", name: "filter_stale", module: "raptor.filter.StaleFilter", category: "Validation" },
    { id: "14", name: "generate_summary", module: "raptor.llm.SummaryGenerator", category: "ML" },
    { id: "15", name: "publish_api", module: "raptor.api.ApiPublisher", category: "Utility" },
];

const GroupedList = () => {
    const [q, setQ] = useState("");
    return <NodePalette steps={manySteps} searchQuery={q} onSearch={setQ} grouped />;
};

export const GroupedByCategory: Story = {
    name: "🧩 Grouped by Category — 15 Steps",
    render: () => <GroupedList />,
};

const SearchableList = () => {
    const [q, setQ] = useState("build");
    return <NodePalette steps={sampleSteps} searchQuery={q} onSearch={setQ} />;
};

export const SearchFiltered: Story = {
    name: "Search — 'build'",
    render: () => <SearchableList />,
};
