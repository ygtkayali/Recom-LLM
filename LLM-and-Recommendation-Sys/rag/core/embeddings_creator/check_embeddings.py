#!/usr/bin/env python
"""Quick script to check embedding statistics."""

import sys
import os

# Add parent directories to path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, parent_dir)

from rag.core.custom_vector_store import CustomDatabaseVectorManager
from langchain_community.embeddings import HuggingFaceEmbeddings
from rag.core import config

def main():
    print("Checking embedding statistics...")
    
    # Create embedding model
    embedding_model = HuggingFaceEmbeddings(
        model_name=config.SENTENCE_TRANSFORMER_MODEL_NAME,
        model_kwargs={'device': 'cpu'}
    )
      # Create vector manager
    manager = CustomDatabaseVectorManager(
        embedding_model=embedding_model
    )
    
    # Get stats
    stats = manager.get_embedding_stats()
    print("\nCurrent Embedding Statistics:")
    if stats:
        for collection_name, count in stats.items():
            print(f"  {collection_name}: {count} embeddings")
    else:
        print("  No embeddings found or database connection failed")

if __name__ == "__main__":
    main()
