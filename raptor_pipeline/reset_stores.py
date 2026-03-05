"""Utility script to wipe all data from Qdrant and Neo4j."""
from __future__ import annotations

import hydra
from omegaconf import DictConfig
from qdrant_client import QdrantClient
from neo4j import GraphDatabase

@hydra.main(config_path="conf", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:
    # 1. Reset Qdrant
    q_cfg = cfg.stores.qdrant
    q_client = QdrantClient(host=q_cfg.host, port=q_cfg.port)
    collection = q_cfg.collection_name
    
    print(f"Cleaning Qdrant collection '{collection}'...")
    try:
        q_client.delete_collection(collection_name=collection)
        print("+ Qdrant collection deleted.")
    except Exception as e:
        print(f"x Qdrant error: {e}")

    # 2. Reset Neo4j
    n_cfg = cfg.stores.neo4j
    print(f"Cleaning Neo4j database '{n_cfg.database}'...")
    try:
        driver = GraphDatabase.driver(n_cfg.uri, auth=(n_cfg.user, n_cfg.password))
        with driver.session(database=n_cfg.database) as session:
            # Delete all nodes and relationships
            summary = session.run("MATCH (n) DETACH DELETE n").consume()
            print(f"+ Neo4j cleaned: {summary.counters.nodes_deleted} nodes deleted.")
        driver.close()
    except Exception as e:
        print(f"× Neo4j error: {e}")

    print("\nReset complete. You can now run the pipeline with a clean slate.")

if __name__ == "__main__":
    main()
