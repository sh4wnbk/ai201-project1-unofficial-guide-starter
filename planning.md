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

**Top-k:** 7 chunks per query (originally 5; bumped after eval — see Stretch Feature below)

**Reasoning:** Started with 5, which gave the LLM enough context to synthesize answers for queries where the relevant chunks all clustered tightly. Bumped to 7 after the eval surfaced a recall-side failure on the SAP-appeal query: the chunk containing the post-appeal *probation* outcome ranked 6th, just outside top-5. Top-7 captures it without diluting precision (all current top hits remain from topically-correct documents). 7 chunks of ~500 chars each is trivially small for Gemini 2.5 Flash's context window.

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

## Stretch Feature: Conversational Memory (multi-turn chat)

**What.** Replace the single-turn textbox interface with a multi-turn chat (`gr.Chatbot`) so students can ask follow-up questions ("what happens if my appeal is granted?") after their initial query. The system retains conversation history and uses it to resolve references in follow-ups.

**Why this one.** A real student rarely asks one self-contained question. The corpus is procedural ("how do I X?" → "and after that?" → "what if it fails?"), so follow-ups are the natural use case. It's also the lowest-lift of the four stretch options — no new dependencies, no parallel retrieval system, no per-corpus tuning knobs.

**Approach.**

1. **State:** use `gr.Chatbot(type="messages")` to hold history as a list of `{role, content}` dicts. Native to Gradio — no LangChain `ConversationBufferMemory` needed (we'd be pulling in a heavy dep for what is a Python list).
2. **Retrieval per turn (smarter concat variant):** for each new user message, retrieve fresh top-7 chunks using a query built from the **immediately prior user message + the current message** concatenated. So when turn 2 is "what about if it's late?", the retrieval query becomes "what happens if I withdraw from all my classes? what about if it's late?" — pulling withdrawal-policy chunks instead of generic "late" chunks. Cheap (1 line) and addresses the obvious ambiguous-follow-up failure mode.
3. **Generation per turn:** Gemini receives the full prior conversation as `contents` history (role-tagged), plus the current turn's user message augmented with the freshly-retrieved context block. Each turn gets fresh chunks; old chunks are not re-sent, keeping the context window clean.
4. **System prompt:** Add one line telling the model it may use conversation history to resolve references like "it" or "that," but must still ground each answer in the *current* turn's context block (no carrying over stale facts from prior chunks).
5. **UI:** Add three demarcated sections of click-to-load prompt cards under the chat: (a) the 5 eval queries from this document, (b) the out-of-scope refusal test, (c) a multi-turn demo pair (SAP appeal → "what happens if my appeal is granted?"). Cards populate the input box but do NOT auto-submit — keeps the demo recorder in control of timing for screenshots / rate-limit pacing.
6. **Clear button:** explicit "Clear conversation" control so the demo recorder can reset between scenarios.

**What this does NOT do:**

- No query rewriting via an extra LLM call (cheap concat instead).
- No retrieval over the chat history itself (only over the document corpus).
- No LangChain memory abstractions.
- No new dependencies.

**Files modified:**

- `app.py` — replace single-turn UI + `answer()` with multi-turn `respond()` + `gr.Chatbot` + prompt cards.
- `planning.md` (this file) — spec for the stretch.
- `README.md` — append a "Stretch Feature: Conversational Memory" section.

**Demo scenario for the recording.**

After base eval queries are demonstrated:
- Click card: *"How do I appeal a SAP suspension at Lehman?"* → submit. Model answers with submission URL + requirements.
- Click card: *"What happens if my appeal is granted?"* → submit. Model uses (a) the concat-retrieval to surface the FINANCIAL AID PROBATION chunk, and (b) the conversation history to know "my appeal" refers to the SAP appeal just discussed. Answer should describe the one-semester probation outcome.

---

## Stretch Feature: Retrieval Tuning (two minimal fixes)

**Motivation.** The SAP appeal eval query (Q3) was documented as a partial-accuracy failure: the system's answer omitted the post-appeal *probation* outcome because that chunk ranked just outside top-5. A second behavioral note from the eval: header-only chunks (the `SOURCE:` / `DOCUMENT:` / `SCRAPED:` metadata blocks at the top of each source file) occasionally surfaced in retrieval despite carrying no answer content.

**What I tried first (and removed).** I prototyped hybrid retrieval (BM25 alongside semantic, combined with Reciprocal Rank Fusion). It fixed the SAP-appeal failure but introduced new regressions on two other queries: BM25 surfaced a Reddit anecdote that displaced the ORDER OF RETURN list (Q2), and a document-header chunk that displaced the CUNYfirst step-by-step instructions (Q5). Tuning attempts (weighted RRF, header filter on BM25 results) either preserved one win at the cost of another or required corpus-specific knobs that started feeling brittle. On a 98-chunk corpus, the added complexity wasn't justified.

**The simpler fix that shipped.** Two minimal changes, ~10 lines of code total:

1. **Bump `top_k` from 5 to 7.** The SAP probation chunk was already ranking 6th in semantic-only retrieval — just outside the window. Returning 7 chunks instead of 5 captures it without changing any other ranking. Gemini 2.5 Flash's context window has plenty of headroom for two extra chunks.
2. **Tighten the ingest-time header filter.** The original `<100 char` filter operated on raw text, so chunks that were mostly metadata but >100 chars total slipped through. The updated filter strips `SOURCE:`/`DOCUMENT:`/`SCRAPED:` lines and ASCII divider lines *before* the 100-char check (helper: `_substantive_len()` in `ingest.py`). This drops 3 additional header-only chunks at index time, removing the class of noise that hybrid-BM25 was trying to filter out at runtime.

**Comparison protocol.** Same 5 eval queries from this document, run through the new retriever (top-7 + filtered chunks). Verified that:
- Q3's probation chunk now appears in top-7 (rank 6) — failure case resolved.
- Q1, Q2, Q4, Q5 retain their previous top-5 hits and gain useful additional context in slots 6–7.
- Total indexed chunks went 98 → 95.

**Why this is a better stretch than hybrid was.**

- Targets the actual problem (a top-k cutoff and a chunk-hygiene gap) rather than introducing a parallel retrieval system.
- Fixes the documented failure case **in the shipped UI**, not just in an opt-in comparison script.
- No new dependencies, no new code paths, no per-corpus tuning knobs.
- Reflects the principle the slides repeated: *the secret sauce isn't the model* — it's the pipeline hygiene.

---

## AI Tool Plan

**Milestone 3 — Ingestion and chunking:**

I will give Claude my Documents table (document types, file locations) and my Chunking Strategy section. I will ask Claude to implement a `ingest.py` script that: loads all `.txt` files from `data/raw/`, attaches source filename as metadata, runs `RecursiveCharacterTextSplitter` with chunk_size=500 and chunk_overlap=100, and prints 5 sample chunks for inspection. I will verify output by reading the printed chunks and confirming they are self-contained, clean, and correctly labeled with source filenames.

**Milestone 4 — Embedding and retrieval:**

I will give Claude my Retrieval Approach section and Architecture diagram. I will ask Claude to implement an `embed.py` script that: loads chunks from the ingestion pipeline, embeds them with `all-MiniLM-L6-v2`, stores them in ChromaDB with source metadata, and exposes a `retrieve(query, k=5)` function. I will verify by running the 5 evaluation queries and manually checking whether returned chunks are topically relevant.

**Milestone 5 — Generation and interface:**

I will give Claude my grounding requirement (answers from retrieved context only, with source attribution), the output format (answer + source list), and the Gradio skeleton from the spec. I will ask Claude to implement `app.py` that wires retrieve() → prompt → Groq API → Gradio UI. I will verify grounding by asking a question my documents don't cover and confirming the system says "I don't have enough information" rather than generating a plausible answer from general knowledge.