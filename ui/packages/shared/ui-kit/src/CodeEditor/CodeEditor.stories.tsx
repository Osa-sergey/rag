import React, { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { CodeEditor } from "./CodeEditor";

const meta: Meta<typeof CodeEditor> = {
    title: "UI Kit/CodeEditor",
    component: CodeEditor,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
    argTypes: {
        language: { control: "select", options: ["yaml", "json", "text"] },
        readOnly: { control: "boolean" },
    },
};

export default meta;
type Story = StoryObj<typeof CodeEditor>;

const pipelineYaml = `pipeline:
  name: raptor_indexing
  version: 2

  global_config:
    embedding_model: openai/ada-002
    vector_size: 1536

  steps:
    - name: parse_articles
      module: raptor.parse.ArticleParser
      config:
        max_length: 4096
        chunk_overlap: 128
        encoding: utf-8

    - name: build_tree
      module: raptor.tree.TreeBuilder
      config:
        levels: 4
        summarizer: gpt-4
        min_cluster_size: 3

    - name: index_vectors
      module: raptor.store.QdrantIndexer
      config:
        collection: raptor_v2
        batch_size: 64`;

const Editable = (args: any) => {
    const [val, setVal] = useState(args.value);
    return <CodeEditor {...args} value={val} onChange={setVal} />;
};

export const YamlConfig: Story = {
    name: "🧩 Pipeline Config (E1)",
    render: () => <Editable value={pipelineYaml} language="yaml" title="raptor_indexing.yaml" />,
};

const jsonSchema = `{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ArticleParser",
  "type": "object",
  "properties": {
    "max_length": {
      "type": "integer",
      "default": 4096,
      "minimum": 256,
      "maximum": 32768
    },
    "chunk_overlap": {
      "type": "integer",
      "default": 128
    },
    "encoding": {
      "type": "string",
      "enum": ["utf-8", "ascii", "latin-1"],
      "default": "utf-8"
    }
  },
  "required": ["max_length"]
}`;

export const JsonSchema: Story = {
    name: "🧩 JSON Schema View (E2)",
    render: () => (
        <CodeEditor
            value={jsonSchema}
            language="json"
            title="ArticleParser.schema.json"
            readOnly
        />
    ),
};

export const ReadOnlyOutput: Story = {
    name: "Read-Only Generated Output",
    render: () => (
        <CodeEditor
            value={`# Auto-generated pipeline summary
steps_total: 3
validation: passed
edges: 2
context_providers:
  - RaptorContext (build_tree → index_vectors)
warnings: 0`}
            language="yaml"
            title="pipeline_summary.yaml"
            readOnly
        />
    ),
};

export const WithErrors: Story = {
    name: "🧩 Validation Errors (E3)",
    render: () => (
        <Editable
            value={`pipeline:
  name: raptor_indexing
  steps:
    - name: parse_articles
      module: raptor.parse.ArticleParser
      config:
        max_length: -100
        chunk_overlap: abc
        encoding: utf-8
    - name: build_tree
      module:
      config:
        levels: 0`}
            language="yaml"
            title="raptor_indexing.yaml"
            errors={[
                { line: 7, message: "max_length must be ≥ 256 (got: -100)" },
                { line: 8, message: "chunk_overlap must be integer (got: 'abc')" },
                { line: 11, message: "module is required and cannot be empty" },
                { line: 13, message: "levels must be ≥ 1 (got: 0)" },
            ]}
        />
    ),
};
