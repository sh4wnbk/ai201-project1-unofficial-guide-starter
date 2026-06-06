# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

Financial aid navigation at Lehman College (CUNY) — the practical knowledge students need to apply for, maintain, and appeal federal and state aid (FAFSA, TAP, SAP, Excelsior). This knowledge is valuable because the official process is fragmented across multiple agencies (federal, NY State, CUNY, and Lehman), and the real-world guidance students need — what actually causes delays, how appeals work in practice, what happens when you withdraw or get dropped — lives in forums and word-of-mouth, not official pages. Around 89% of Lehman students receive some form of financial aid, yet the processes governing it are among the most confusing in higher education.

---

## Documents

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | Lehman Financial Aid FAQs | FAFSA process, CUNYfirst TO DO list, SAR, how to apply, TAP code | https://www.lehman.edu/financial-aid/faqs/ |
| 2 | Lehman TAP Program | Full TAP eligibility charts, waivers, Part-Time TAP, Summer TAP, repeated courses | https://www.lehman.edu/financial-aid/state-aid-information/tap/ |
| 3 | Lehman SAP Policy | SAP standards, credit/GPA tables, appeal process, probation rules (Spring 2026 deadlines) | https://www.lehman.edu/financial-aid/sap/ |
| 4 | Lehman Excelsior Scholarship | Excelsior eligibility, income limits ($125k), credit requirements, how to apply | https://www.lehman.edu/financial-aid/state-aid-information/excelsior-scholarship/ |
| 5 | Lehman State Aid FAQs | TAP edge cases, Dream Act, APTS, residency rules, IEP diploma eligibility | https://www.lehman.edu/financial-aid/state-aid-information/state-aid-faqs/ |
| 6 | Lehman Withdrawals Policy | Return of federal aid, 60% rule, unofficial withdrawals, consequences | https://www.lehman.edu/financial-aid/withdrawals/ |
| 7 | Lehman Special Circumstances | Income changes, dependency overrides, professional judgment appeals | https://www.lehman.edu/financial-aid/special-circumstances/ |
| 8 | Lehman CUNYfirst & FACTS Guide | How to check aid status, TO DO list, FACTS tool, disbursement schedule | https://www.lehman.edu/financial-aid/state-aid-information/facts/ |
| 9 | HESC Student Update Feb 2026 | Current FAFSA/TAP tips, Excelsior deadlines, Dream Act pathways | https://hesc.ny.gov/about/news-releases/student-update-february-2026 |
| 10 | HESC 2026-27 FAFSA/TAP Open | Current cycle application guide, early filing advice, virtual help events | https://hesc.ny.gov/about/news-releases/2026-27-fafsa-and-tap-applications-open |
| 11 | Reddit r/CUNY — Dropped from class | Real student experience: grade delays causing drops, prerequisite enforcement, step-by-step advice | reddit.com/r/cuny (manual copy) |
| 12 | Reddit r/CUNY — Academic integrity F | CUNY academic integrity process, grade appeals, Department Chair → Dean pathway, financial aid consequences | reddit.com/r/cuny (manual copy) |

---

## Chunking Strategy

**Chunk size:** 500 tokens

**Overlap:** 100 tokens

**Reasoning:**

My corpus has two distinct document types that informed this decision:

1. **Official policy pages** (Lehman FAQs, TAP eligibility charts, SAP tables, HESC guides) — these have natural structure: Q&A sections, numbered steps, policy paragraphs. I'm using LangChain's `RecursiveCharacterTextSplitter`, which respects these boundaries by trying paragraph breaks first, then sentences, only falling back to character splits when necessary. 500 tokens keeps full Q&A pairs together without merging unrelated policy sections.

2. **Reddit threads** (student experience posts + comments) — each comment is already a short, self-contained thought (1-5 sentences). 500 tokens is large enough to keep a comment plus its parent context together, which matters for threaded advice (e.g. a student's question + the most upvoted answer).

**Why 100 token overlap:** Several documents contain multi-part answers where the key fact appears at the end of one paragraph and the explanation at the start of the next — TAP eligibility tables are the clearest example. 100 token overlap ensures boundary facts appear in at least one complete chunk.

**What bad chunking looks like for this corpus:**
- Too small (<200 tokens): TAP payment eligibility rows get split mid-row, destroying the GPA + credit + payment number relationship.
- Too large (>800 tokens): Multiple unrelated policy sections merge, diluting semantic signal. A query about SAP appeals retrieves a chunk that's 80% about Excelsior deadlines.
- Fixed character splitting: Ignores document structure entirely — slices mid-sentence through TAP tables.

**Stretch feature:** Implement Docling's HybridChunker as a second strategy on the official policy documents and compare retrieval quality against recursive splitting on the same 5 evaluation queries (Chunking Strategy Comparison stretch feature).

---

## Retrieval Approach

**Embedding model:** `all-MiniLM-L6-v2` via `sentence-transformers` — runs locally, no API key, no rate limits.

**Top-k:** 5 chunks per query

**Reasoning:** 5 chunks gives the LLM enough context to synthesize a complete answer (e.g. TAP eligibility requires GPA + credits + payment number — likely spread across 2-3 chunks) without diluting the context with loosely related material. Will tune down to 3 if responses become unfocused.

**Production tradeoff reflection:**

For a real deployment serving Lehman students, I would weigh:
- **`text-embedding-3-large` (OpenAI):** Higher accuracy on domain-specific policy text, longer context window — but API cost and rate limits make it unsuitable for a free student tool.
- **`multilingual-e5-large`:** Lehman has a large Spanish-speaking student population. Multilingual support would improve retrieval for students who phrase queries in Spanish, which `all-MiniLM-L6-v2` handles poorly.
- **`bge-large-en-v1.5`:** Strong benchmark performance on retrieval tasks, still runs locally — a better local option if accuracy needs improvement.
- **Latency:** `all-MiniLM-L6-v2` is fast enough for interactive use. Larger models introduce 2-5s latency per query, which degrades the UI experience.

---

## Evaluation Plan

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | How many credits do I need to complete for my 5th TAP payment? | 9 credits completed in the prior term, 33 credits accumulated, GPA of 2.0 |
| 2 | What happens to my financial aid if I withdraw from all my classes? | Aid is recalculated based on the 60% completion rule; unearned aid must be returned to federal programs in a specific order; future aid eligibility may be affected |
| 3 | How do I appeal a SAP suspension at Lehman? | Submit an electronic SAP appeal at lehman.smapply.io/prog/undergraduate_appeals/ with documentation of mitigating circumstances; if granted, placed on probation for one semester |
| 4 | What is the income limit to qualify for the Excelsior Scholarship? | Household federal adjusted gross income at or below $125,000 |
| 5 | How do I check my financial aid status in CUNYfirst? | Log into home.cunyfirst.cuny.edu → Student Center → Financial Aid → select Aid Year → review Award Summary; also check TO DO list for any required documents |

---

## Anticipated Challenges

1. **TAP eligibility table splitting:** The TAP chart (GPA + credits completed + credits accumulated per payment number) is a highly structured table. If recursive splitting cuts across payment rows, retrieval will return partial data — e.g. the GPA requirement without the credit requirement for the same payment. Mitigation: inspect chunks manually after splitting and adjust chunk size or switch to Docling for this document specifically.

2. **Semantic overlap between policy topics:** TAP, SAP, Excelsior, and FAFSA are closely related — queries about one may retrieve chunks from another. For example, "what GPA do I need?" could retrieve SAP GPA requirements when the user meant TAP GPA requirements, or vice versa. Mitigation: add source metadata to each chunk and test retrieval precision on evaluation queries before wiring in generation.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        RAG PIPELINE                             │
└─────────────────────────────────────────────────────────────────┘

1. DOCUMENT INGESTION
   Tool: Python (plain text .txt files, pre-scraped)
   Input: 12 .txt files in data/raw/
   Output: Cleaned text strings with source metadata
   ↓

2. CHUNKING
   Tool: LangChain RecursiveCharacterTextSplitter
   Chunk size: 500 tokens | Overlap: 100 tokens
   Output: List of (chunk_text, source_filename) tuples
   ↓

3. EMBEDDING + VECTOR STORE
   Embedding: sentence-transformers/all-MiniLM-L6-v2 (local)
   Vector Store: ChromaDB (local, persistent)
   Metadata stored: source filename, chunk index
   ↓

4. RETRIEVAL
   Input: User query string
   Process: Embed query → cosine similarity search → top-5 chunks
   Output: 5 chunks + source metadata
   ↓

5. GENERATION
   LLM: Groq llama-3.3-70b-versatile (free tier)
   Prompt: Retrieved chunks as context + grounding instruction
   Output: Grounded answer + source attribution
   ↓

6. INTERFACE
   Tool: Gradio
   Fields: Query input, Answer output, Sources output
```

---

## Stretch Feature: Hybrid Search (BM25 + Semantic)

**Motivation.** The SAP appeal eval query (Q3) is documented as a partial-accuracy failure in the README: the system's answer omitted the post-appeal probation outcome because the "probation" chunk ranked below top-5. Inspecting the retrieved set, all 5 hits clustered around *submission* and *documentation* vocabulary, which is semantically close to "how do I appeal." The probation chunk uses different vocabulary ("probation," "warning period") that the semantic embedding ranked further from the query. This is a classic recall failure caused by vocabulary mismatch — exactly what keyword search (BM25) is designed to catch.

**Approach.**

1. Build a BM25 index over the same 98 chunks already in ChromaDB, using the `rank_bm25` library (`BM25Okapi`).
2. Implement `retrieve_hybrid(query, k=5)` that runs both retrievals in parallel and combines them with **Reciprocal Rank Fusion (RRF)**:
   `score(doc) = Σ 1 / (k_rrf + rank_in_system_i)` with `k_rrf=60` (standard).
   RRF is rank-based, not score-based, so it doesn't require normalizing BM25 scores against cosine distances — a common pitfall when combining incompatible scoring systems.
3. Pull more candidates than top-k from each system (e.g., 20 each) before fusing, so good chunks that rank 15th in semantic but 2nd in BM25 still make the final top-5.

**Comparison protocol.**

Re-run the 5 evaluation queries from this document on three retrievers:
- Semantic-only (current `retrieve()`)
- BM25-only
- Hybrid (RRF over both)

For each query, record top-5 chunk IDs and distances/scores from each retriever, and grade whether the chunk needed for the expected answer appears in top-5. The SAP appeal "probation" chunk is the canonical test case — if hybrid pulls it into top-5 while semantic-only doesn't, that's a measurable win.

**Expected outcome (hypothesis).**

Hybrid should fix the SAP failure case (probation chunk surfaces via BM25 keyword match) and should not regress on the other 4 queries (where the answer chunks already rank well semantically). If hybrid *does* regress, the failure mode and explanation go in the writeup.

**Files to add/modify:**

- `requirements.txt` — add `rank-bm25` pinned to installed version
- `embed.py` — add BM25 indexer + `retrieve_hybrid(query, k=5)`
- `compare_retrievers.py` (new) — runs the 5 eval queries on all three retrievers and prints a side-by-side comparison
- `README.md` — append a "Stretch Feature: Hybrid Search" section reporting results
- (No changes to `app.py` unless hybrid wins decisively — then switch the default.)

**What this does NOT do:**

- No re-chunking, no new embedding model, no new vector store. Hybrid is purely a retrieval-layer addition.
- No UI toggle. The point is to compare and write up the result, not to ship a feature flag.

---

## AI Tool Plan

**Milestone 3 — Ingestion and chunking:**

I will give Claude my Documents table (document types, file locations) and my Chunking Strategy section. I will ask Claude to implement a `ingest.py` script that: loads all `.txt` files from `data/raw/`, attaches source filename as metadata, runs `RecursiveCharacterTextSplitter` with chunk_size=500 and chunk_overlap=100, and prints 5 sample chunks for inspection. I will verify output by reading the printed chunks and confirming they are self-contained, clean, and correctly labeled with source filenames.

**Milestone 4 — Embedding and retrieval:**

I will give Claude my Retrieval Approach section and Architecture diagram. I will ask Claude to implement an `embed.py` script that: loads chunks from the ingestion pipeline, embeds them with `all-MiniLM-L6-v2`, stores them in ChromaDB with source metadata, and exposes a `retrieve(query, k=5)` function. I will verify by running the 5 evaluation queries and manually checking whether returned chunks are topically relevant.

**Milestone 5 — Generation and interface:**

I will give Claude my grounding requirement (answers from retrieved context only, with source attribution), the output format (answer + source list), and the Gradio skeleton from the spec. I will ask Claude to implement `app.py` that wires retrieve() → prompt → Groq API → Gradio UI. I will verify grounding by asking a question my documents don't cover and confirming the system says "I don't have enough information" rather than generating a plausible answer from general knowledge.