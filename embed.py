import re
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi

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


_bm25_index: BM25Okapi | None = None
_bm25_chunks: list[dict] | None = None


def _tokenize(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def _get_bm25() -> tuple[BM25Okapi, list[dict]]:
    global _bm25_index, _bm25_chunks
    if _bm25_index is None:
        _bm25_chunks = get_chunks()
        corpus_tokens = [_tokenize(c["text"]) for c in _bm25_chunks]
        _bm25_index = BM25Okapi(corpus_tokens)
    return _bm25_index, _bm25_chunks


def retrieve_bm25(query: str, k: int = 5) -> list[dict]:
    bm25, chunks = _get_bm25()
    scores = bm25.get_scores(_tokenize(query))
    top = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
    return [
        {
            "text": chunks[i]["text"],
            "source": chunks[i]["source"],
            "chunk_index": chunks[i]["chunk_index"],
            "bm25_score": float(scores[i]),
        }
        for i in top
    ]


def retrieve_hybrid(
    query: str, k: int = 5, candidates: int = 20, rrf_k: int = 60
) -> list[dict]:
    semantic_hits = retrieve(query, k=candidates)
    bm25_hits = retrieve_bm25(query, k=candidates)

    def cid(h: dict) -> str:
        return f"{h['source']}::{h['chunk_index']}"

    rrf_scores: dict[str, float] = {}
    chunk_map: dict[str, dict] = {}

    for rank, hit in enumerate(semantic_hits, start=1):
        key = cid(hit)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (rrf_k + rank)
        chunk_map[key] = hit

    for rank, hit in enumerate(bm25_hits, start=1):
        key = cid(hit)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (rrf_k + rank)
        chunk_map.setdefault(key, hit)

    top = sorted(rrf_scores.items(), key=lambda x: -x[1])[:k]
    return [
        {
            "text": chunk_map[key]["text"],
            "source": chunk_map[key]["source"],
            "chunk_index": chunk_map[key]["chunk_index"],
            "rrf_score": score,
        }
        for key, score in top
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
