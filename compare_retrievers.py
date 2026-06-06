from embed import EVAL_QUERIES, retrieve, retrieve_bm25, retrieve_hybrid

K = 5


def fmt_hit(i: int, hit: dict, score_key: str) -> str:
    cid = f"{hit['source']}#{hit['chunk_index']}"
    score = hit.get(score_key, 0.0)
    preview = hit["text"].replace("\n", " ")[:90]
    return f"  {i}. [{cid}] (score={score:.3f}) {preview}..."


def main() -> None:
    for i, query in enumerate(EVAL_QUERIES, 1):
        print(f"\n{'=' * 80}")
        print(f"QUERY {i}: {query}")
        print("=" * 80)

        print("\n[SEMANTIC ONLY]")
        for j, h in enumerate(retrieve(query, k=K), 1):
            print(fmt_hit(j, h, "distance"))

        print("\n[BM25 ONLY]")
        for j, h in enumerate(retrieve_bm25(query, k=K), 1):
            print(fmt_hit(j, h, "bm25_score"))

        print("\n[HYBRID (RRF)]")
        for j, h in enumerate(retrieve_hybrid(query, k=K), 1):
            print(fmt_hit(j, h, "rrf_score"))

        sem_ids = {f"{h['source']}#{h['chunk_index']}" for h in retrieve(query, k=K)}
        hyb_ids = {f"{h['source']}#{h['chunk_index']}" for h in retrieve_hybrid(query, k=K)}
        added = hyb_ids - sem_ids
        dropped = sem_ids - hyb_ids
        print(f"\n  Hybrid changed top-{K}: +{len(added)} added, -{len(dropped)} dropped")
        if added:
            print(f"    added:   {sorted(added)}")
        if dropped:
            print(f"    dropped: {sorted(dropped)}")


if __name__ == "__main__":
    main()
