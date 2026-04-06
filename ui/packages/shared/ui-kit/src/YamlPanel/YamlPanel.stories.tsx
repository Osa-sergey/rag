import type { Meta, StoryObj } from "@storybook/react";
import { YamlPanel } from "./YamlPanel";

const meta: Meta<typeof YamlPanel> = {
    title: "DAG Builder/YamlPanel",
    component: YamlPanel,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj<typeof YamlPanel>;

const validYaml = `name: raptor_indexing
globals:
  embedding_model: text-embedding-3-small
  chunk_size: 4096

steps:
  - name: parse_articles
    module: raptor.parse.ArticleParser
    config:
      max_length: 4096
      encoding: utf-8
    outputs:
      chunks: List[str]
      metadata: dict

  - name: extract_keywords
    module: raptor.keywords.KeywordExtractor
    inputs:
      text: steps.parse_articles.chunks
    config:
      top_k: 20

  - name: build_concepts
    module: raptor.concept.ConceptBuilder
    inputs:
      chunks: steps.parse_articles.chunks
      keywords: steps.extract_keywords.keywords
    callbacks:
      - type: on_retry
        params:
          max_retries: 3`;

export const ValidYaml: Story = {
    name: "🧩 Valid YAML — Serialized Graph (E1)",
    args: { content: validYaml },
};

export const WithErrors: Story = {
    name: "🧩 Error Markers — Red Lines (E3)",
    args: {
        content: validYaml,
        errorLines: [4, 11],
    },
};

export const Empty: Story = {
    name: "Empty — No Content",
    args: { content: "# Empty pipeline\nname: untitled\nsteps: []" },
};

export const RoundTrip: Story = {
    name: "🧩 Round-Trip Preview (E2)",
    args: {
        content: `# Auto-generated from graph
name: raptor_indexing
version: 2
generated_at: 2024-11-15T10:30:00Z

steps:
  - name: parse_articles
    module: raptor.parse.ArticleParser
  - name: build_concepts
    module: raptor.concept.ConceptBuilder
    depends_on:
      - parse_articles`,
    },
};
