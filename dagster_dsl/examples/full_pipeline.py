"""Example: Full habr document processing pipeline.

This demonstrates the DSL for building a complete pipeline:
  CSV → parse → RAPTOR indexing → topic modeling → concept building

Usage (view DAG without execution):
    python dagster_dsl/examples/full_pipeline.py

Usage (Dagster UI):
    dagster dev -f dagster_dsl/examples/full_pipeline.py
"""
from dagster_dsl import pipeline

# ── Pipeline Definition ───────────────────────────────────────

with pipeline("habr_full_pipeline") as p:
    # Global overrides — apply to all steps that share these config keys
    p.config_override(
        "stores.neo4j.uri", "bolt://localhost:7687",
        "stores.neo4j.password", "raptor_password",
        "stores.qdrant.host", "localhost",
    )

    # Step 1: Parse CSV with HTML articles → structured YAML
    parse = p.step("document_parser.parse_csv",
        input_file="data/habr_posts.csv",
        html_column="body_html",
        output_dir="parsed_yaml",
    )

    # Step 2: RAPTOR Pipeline — indexing into vector + graph stores
    # Depends on parse completing first
    raptor = p.step("raptor_pipeline.run",
        input_dir="parsed_yaml",
        max_concurrency=4,
    ).after(parse)

    # Step 3: Topic Modeling — parallel to raptor (both depend on parse)
    topics = p.step("topic_modeler.train",
        input_dir="parsed_yaml",
    ).after(parse)

    # Step 4: Concept Building — needs both raptor + topics to finish
    concepts = p.step("concept_builder.process",
        base_article="986380",
        max_articles=10,
        strategy="bfs",
    ).after(raptor, topics)

# ── Print DAG description ─────────────────────────────────────

if __name__ == "__main__":
    print(p.describe())
    print()
    print("To generate Dagster job:")
    print("  job = p.to_dagster_job()")
    print()
    print("To run in Dagster UI:")
    print("  dagster dev -f dagster_dsl/examples/full_pipeline.py")

# ── Dagster definitions (for `dagster dev`) ───────────────────

try:
    job = p.to_dagster_job()
    # Dagster webserver looks for `defs` or `Definitions`
    from dagster import Definitions
    defs = Definitions(jobs=[job])
except ImportError:
    # dagster not installed — no problem, just print the DAG
    pass
