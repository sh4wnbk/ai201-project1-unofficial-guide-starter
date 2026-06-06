import random
from collections import defaultdict
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

RAW_DIR = Path("data/raw")
CHUNKS_OUT = Path("data/chunks.txt")


def load_documents(raw_dir: Path) -> list[tuple[str, str]]:
    docs = []
    for path in sorted(raw_dir.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        docs.append((path.name, text))
    return docs


def chunk_documents(docs: list[tuple[str, str]]) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
    )
    chunks = []
    for source, text in docs:
        for i, piece in enumerate(splitter.split_text(text)):
            chunks.append({"text": piece, "source": source, "chunk_index": i})
    return chunks


def get_chunks(raw_dir: Path = RAW_DIR) -> list[dict]:
    docs = load_documents(raw_dir)
    chunks = chunk_documents(docs)
    return [c for c in chunks if len(c["text"].strip()) >= 100]


def main() -> None:
    docs = load_documents(RAW_DIR)
    chunks = chunk_documents(docs)

    before = len(chunks)
    chunks = [c for c in chunks if len(c["text"].strip()) >= 100]
    print(f"Filtered out {before - len(chunks)} short chunks (<100 chars)")
    print(f"Total chunks: {len(chunks)}")
    print()

    with CHUNKS_OUT.open("w", encoding="utf-8") as f:
        for i, chunk in enumerate(chunks):
            f.write(f"--- Chunk {i + 1} / {len(chunks)} ---\n")
            f.write(f"Source: {chunk['source']}\n\n")
            f.write(chunk["text"])
            f.write("\n\n")
    print(f"Wrote all chunks to {CHUNKS_OUT}")
    print()

    by_source: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        by_source[chunk["source"]].append(chunk)

    sources = random.sample(list(by_source.keys()), k=min(5, len(by_source)))
    samples = [random.choice(by_source[src]) for src in sources]

    for i, chunk in enumerate(samples):
        print(f"--- Sample chunk {i + 1} ---")
        print(f"Source: {chunk['source']}")
        print(chunk["text"])
        print()


if __name__ == "__main__":
    main()
