from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from ingest import get_chunks

CHROMA_DIR = Path("chroma_db")
COLLECTION_NAME = "lehman_financial_aid"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)


def _client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def build_index() -> int:
    client = _client()
    if COLLECTION_NAME in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION_NAME)

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=_embedder,
        metadata={"hnsw:space": "cosine"},
    )

    chunks = get_chunks()
    ids = [f"{c['source']}::{c['chunk_index']}" for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {"source": c["source"], "chunk_index": c["chunk_index"]} for c in chunks
    ]

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    return len(chunks)


def retrieve(query: str, k: int = 5) -> list[dict]:
    client = _client()
    collection = client.get_collection(
        name=COLLECTION_NAME, embedding_function=_embedder
    )
    result = collection.query(query_texts=[query], n_results=k)
    return [
        {
            "text": doc,
            "source": meta["source"],
            "chunk_index": meta["chunk_index"],
            "distance": dist,
        }
        for doc, meta, dist in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0]
        )
    ]


EVAL_QUERIES = [
    "How many credits do I need to complete for my 5th TAP payment?",
    "What happens to my financial aid if I withdraw from all my classes?",
    "How do I appeal a SAP suspension at Lehman?",
    "What is the income limit to qualify for the Excelsior Scholarship?",
    "How do I check my financial aid status in CUNYfirst?",
]


def main() -> None:
    print(f"Building index in {CHROMA_DIR}/ using {EMBEDDING_MODEL}...")
    n = build_index()
    print(f"Indexed {n} chunks.\n")

    for i, query in enumerate(EVAL_QUERIES, 1):
        print(f"=== Query {i}: {query} ===")
        for j, hit in enumerate(retrieve(query, k=5), 1):
            preview = hit["text"].replace("\n", " ")[:160]
            print(
                f"  {j}. [{hit['source']}#{hit['chunk_index']}] "
                f"(dist={hit['distance']:.3f}) {preview}..."
            )
        print()


if __name__ == "__main__":
    main()
