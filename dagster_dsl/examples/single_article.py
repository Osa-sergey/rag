"""Example: Single article processing pipeline.

Process a single article through the entire chain:
  parse-md → raptor (single file) → topic prediction → concept building

Usage:
    python dagster_dsl/examples/single_article.py
"""
from dagster_dsl import pipeline

# ── Pipeline Definition ───────────────────────────────────────

with pipeline("single_article") as p:
    # Parse a single markdown file
    parse = p.step("document_parser.parse_md",
        input_file="data/article.md",
        output_dir="parsed_yaml",
    )

    # Index the single parsed file
    raptor = p.step("raptor_pipeline.run",
        input_dir="parsed_yaml",
        input_file="article.yaml",
    ).after(parse)

    # Predict topic for the article
    topic = p.step("topic_modeler.add_article",
        article_path="parsed_yaml/article.yaml",
    ).after(parse)

# ── Print ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print(p.describe())
