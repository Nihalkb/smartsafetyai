import faiss
import numpy as np
from embed_documents import EmbedDocuments  # Ensure your updated embed_documents module is available

# Load your FAISS index and document mapping
embedder = EmbedDocuments()  # Instantiate your embed_documents class
embedder.load_index(index_path="faiss_index.bin", mapping_path="doc_mapping.npy")

# Print the number of vectors in the FAISS index
print("Total embeddings in FAISS index:", embedder.index.ntotal)

# Load the document mapping and display each chunk's metadata and the first few components of its embedding vector
for key, meta in embedder.doc_mapping.items():
    print("Vector ID:", key)
    print("Chunk Metadata:", meta)
    try:
        # Reconstruct the embedding vector from the index for this vector ID
        vector = embedder.index.reconstruct(int(key))
        print("Embedding vector (first 5 components):", vector[:5])
    except Exception as e:
        print(f"Error reconstructing vector for ID {key}: {e}")
    print("-" * 60)
