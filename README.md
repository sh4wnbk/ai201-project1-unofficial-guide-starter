# Lehman Financial Aid — Unofficial Guide (Project 1)

A retrieval-augmented Q&A system for Lehman College (CUNY) financial aid. Students can ask about FAFSA, TAP, SAP, Excelsior, withdrawals, and CUNYfirst, and receive answers grounded only in 12 scraped policy documents and forum threads — with source attribution shown alongside every answer.

---

## Domain

Financial aid navigation at Lehman College (CUNY) — the practical knowledge students need to apply for, maintain, and appeal federal and state aid (FAFSA, TAP, SAP, Excelsior). This knowledge is valuable because the official process is fragmented across multiple agencies (federal, NY State, CUNY, Lehman) and the real-world guidance students need — what actually causes delays, how appeals work in practice, what happens when you withdraw or get dropped — lives in forums and word-of-mouth, not on a single official page. Around 89% of Lehman students receive some form of financial aid, yet the processes governing it are among the most confusing in higher education.

---

## Document Sources

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Lehman Financial Aid FAQs | Official policy | https://www.lehman.edu/financial-aid/faqs/ |
| 2 | Lehman TAP Program | Official policy | https://www.lehman.edu/financial-aid/state-aid-information/tap/ |
| 3 | Lehman SAP Policy | Official policy | https://www.lehman.edu/financial-aid/sap/ |
| 4 | Lehman Excelsior Scholarship | Official policy | https://www.lehman.edu/financial-aid/state-aid-information/excelsior-scholarship/ |
| 5 | Lehman State Aid FAQs | Official policy | https://www.lehman.edu/financial-aid/state-aid-information/state-aid-faqs/ |
| 6 | Lehman Withdrawals Policy | Official policy | https://www.lehman.edu/financial-aid/withdrawals/ |
| 7 | Lehman Special Circumstances | Official policy | https://www.lehman.edu/financial-aid/special-circumstances/ |
| 8 | Lehman CUNYfirst & FACTS Guide | Official guide | https://www.lehman.edu/financial-aid/state-aid-information/facts/ |
| 9 | HESC Student Update Feb 2026 | NY State agency | https://hesc.ny.gov/about/news-releases/student-update-february-2026 |
| 10 | HESC 2026-27 FAFSA/TAP Open | NY State agency | https://hesc.ny.gov/about/news-releases/2026-27-fafsa-and-tap-applications-open |
| 11 | r/CUNY — "Dropped from class" | Reddit thread | reddit.com/r/cuny (manual copy) |
| 12 | r/CUNY — "Academic integrity F" | Reddit thread | reddit.com/r/cuny (manual copy) |

All 12 documents were pre-scraped to plain text and stored in `data/raw/`. Total corpus: ~60 KB.

---

## Architecture

```mermaid
flowchart TD
    subgraph BUILD["Build time (one-off, run by embed.py)"]
        A[12 .txt files in data/raw/] -->|ingest.py| B[RecursiveCharacterTextSplitter<br/>500 chars / 100 overlap<br/>filter chunks under 100 chars]
        B -->|98 chunks| C[all-MiniLM-L6-v2<br/>local sentence-transformer]
        C -->|vectors + source metadata| D[(ChromaDB<br/>chroma_db/)]
    end

    subgraph QUERY["Query time (per request, app.py)"]
        E[User question<br/>Gradio textbox] -->|embed query| F[all-MiniLM-L6-v2]
        F -->|query vector| G{Cosine similarity<br/>top-5}
        G -->|retrieved chunks| H[Grounded prompt<br/>system prompt + context + question]
        H -->|google-genai SDK| I[Gemini 2.5 Flash]
        I --> J[Answer text<br/>+ Sources panel<br/>filename · distance · preview]
    end

    D -.->|searched at query time| G
```

The build-time path runs once when you execute `embed.py`: it loads the corpus, chunks it, embeds every chunk, and persists the vectors to ChromaDB. The query-time path runs on every Gradio submission: the user's question is embedded with the same model, the top-5 most similar chunks are retrieved by cosine distance, and those chunks are injected into a grounded prompt sent to Gemini. The dashed line shows that the index built at build time is what's searched on every request.

---

## Chunking Strategy

**Splitter:** LangChain `RecursiveCharacterTextSplitter`
**Chunk size:** 500 characters
**Overlap:** 100 characters
**Post-filter:** chunks with fewer than 100 non-whitespace characters are dropped (removes header-only fragments).
**Final chunk count:** 98 (99 before the filter)

**Why these choices fit the documents:**

The corpus has two distinct document types:

1. **Official policy pages** (Lehman FAQs, TAP eligibility charts, SAP tables, HESC guides) have natural structure: Q&A blocks, numbered steps, policy paragraphs. `RecursiveCharacterTextSplitter` respects these boundaries by trying paragraph breaks first, then sentences, only falling back to character splits as a last resort. 500 characters keeps full Q&A pairs together without merging unrelated policy sections.

2. **Reddit threads** are short self-contained comments (1–5 sentences each). 500 characters is large enough to keep a parent post plus the highest-voted reply together, which matters for threaded advice.

**Why 100-character overlap:** Several documents have multi-part answers where the key fact appears at the end of one paragraph and the explanation at the start of the next — TAP eligibility tables are the clearest example. 100 characters of overlap ensures boundary facts appear in at least one complete chunk.

**Why the `< 100` char filter was added (diverged from the original spec):** Each document begins with a metadata header (`SOURCE:`, `DOCUMENT:`, `SCRAPED:`, a divider line). The splitter cleanly broke these into tiny header-only chunks that contained no useful answer content but would still surface in retrieval. Filtering them out improved precision without losing information.

---

## Sample Chunks (5, each labeled with its source document)

### 1. `lehman_cunyfirst_facts_guide.txt` (chunk 11/98)
```
HOW TO VIEW YOUR FINANCIAL AID AWARD IN CUNYFIRST:
1. Log on to CUNYfirst at home.cunyfirst.cuny.edu
2. Click on Student Center
3. Click on Financial Aid
4. Click the correct Aid Year (covers Summer, Fall, and Spring of that academic year)
5. Review your Award Summary
```

### 2. `lehman_sap_policy.txt` (chunk 35/98)
```
DEADLINE: THE DEADLINE TO SUBMIT A SAP APPEAL FOR SPRING 2026 SEMESTER WAS TUESDAY 05/26/2026.

HOW TO SUBMIT AN APPEAL:
- Undergraduate students: submit electronic SAP appeal at lehman.smapply.io/prog/undergraduate_appeals/
- Graduate students: submit typed written appeal via email to Takiyah.Ali@lehman.cuny.edu
```

### 3. `lehman_special_circumstances.txt` (chunk 45/98)
```
WHEN TO REQUEST A SPECIAL CIRCUMSTANCES REVIEW:
- Significant change in family income (job loss, reduced hours, retirement, divorce/separation)
- Death of a parent or spouse
- Unusual medical or dental expenses not covered by insurance
- Natural disaster affecting family finances
- Loss of untaxed income or benefits
- Student or parent became disabled
- Unusually high dependent care expenses
```

### 4. `lehman_tap_program.txt` (chunk 64/98)
```
TAP ELIGIBILITY CHARTS:
For students who received FIRST TAP award in SUMMER 2006 or later (Non-SEEK and SEEK):
Payment 1: 0 credits completed, 0 accumulated, GPA 0
Payment 2: 6 credits completed, 3 accumulated, GPA 1.1
Payment 3: 6 credits completed, 9 accumulated, GPA 1.2
Payment 4: 9 credits completed, 21 accumulated, GPA 1.3
Payment 5: 9 credits completed, 33 accumulated, GPA 2.0
Payment 6: 12 credits completed, 45 accumulated, GPA 2.0
```

### 5. `lehman_withdrawals_policy.txt` (chunk 72/98)
```
WHAT HAPPENS WHEN YOU WITHDRAW:
When a student withdraws from all classes before completing 60% of the semester, federal regulations require the college to calculate how much federal aid was "earned." The unearned portion must be returned to the federal aid programs.
```

---

## Embedding Model

**Model used:** `sentence-transformers/all-MiniLM-L6-v2` (local, no API)
**Vector store:** ChromaDB (persistent, cosine distance)
**Top-k:** 5

Runs entirely offline after first model download. Fast enough for interactive use (< 1s per query). MiniLM is the standard "good enough at small cost" choice for English general-purpose retrieval.

### Production tradeoff reflection

For a real deployment serving Lehman students, the three swappable layers (embedding model, vector store, generation service) each carry their own decisions.

**Embedding model alternatives:**

- **`text-embedding-3-large` (OpenAI):** Higher accuracy on domain-specific policy text and longer context, but per-query API cost and rate limits make it a poor fit for a free student tool.
- **`multilingual-e5-large`:** Lehman has a large Spanish-speaking student population. Multilingual support would noticeably improve retrieval for Spanish-phrased queries, which MiniLM handles poorly. This is probably the single biggest accuracy upgrade for *this user base*, not raw benchmark scores.
- **`bge-large-en-v1.5`:** Strong English retrieval benchmark scores, still runs locally — a drop-in upgrade if accuracy needs improvement without leaving the offline footprint.
- **Latency:** MiniLM is fast enough for an interactive interface. Larger local models add 2–5s per query, which degrades the perceived responsiveness in the Gradio UI.

The right embedding choice depends on what failure mode hurts most: domain precision (→ larger English model), accessibility (→ multilingual), or cost (→ stay on MiniLM).

**Vector store alternatives:**

ChromaDB is ideal for development and a small persistent corpus, but a real deployment serving thousands of students concurrently would want managed infrastructure.

- **Pinecone:** Fully managed serverless vector DB with strong multi-tenant isolation and zero DevOps overhead. The case to switch is when the corpus outgrows what fits in a single Chroma instance, the system needs to serve many concurrent users without latency spikes, or there's no engineer to operate the index in-house.
- **AWS OpenSearch Service + S3 Vectors:** Native AWS path. OpenSearch handles vector + hybrid (semantic + keyword) retrieval; S3 Vectors stores embeddings directly in object storage (up to ~2B vectors per index) at much lower per-vector cost. The case to switch is when the rest of the stack is already in AWS — keeping retrieval, storage, and generation in one account simplifies auth, billing, and compliance.

**Generation service alternatives:**

Currently the system calls Gemini 2.5 Flash directly via the `google-genai` SDK. Two production-grade alternatives:

- **Amazon Bedrock:** Managed access to multiple foundation models (Claude, Llama, Titan, etc.) through a single API. Worth it when A/B-testing models, consolidating billing across model providers, or pairing generation with OpenSearch/S3 Vectors above for a fully AWS-native pipeline.
- **Direct Anthropic / OpenAI APIs:** Lowest abstraction — pick one model and own the integration. Cheapest path when the model choice is settled and you don't need cross-provider routing.

Across all three layers, the meta-question is the same: **what failure mode hurts most?** Cost (stay local), accuracy on policy prose (larger English embedder + Claude/GPT-4 class generator), accessibility for Spanish speakers (multilingual embedder), or operational simplicity at scale (Pinecone or AWS-native).

---

## Retrieval Test Results

Three queries from the evaluation set, with the top-5 retrieved chunks for each. Distance is cosine distance — lower is closer.

### Query A: "What happens to my financial aid if I withdraw from all my classes?"
| Rank | Source | Distance |
|---|---|---|
| 1 | `lehman_withdrawals_policy.txt` (UNOFFICIAL WITHDRAWALS) | 0.170 |
| 2 | `lehman_financial_aid_faqs.txt` (DROPPING OR WITHDRAWING warning) | 0.191 |
| 3 | `lehman_withdrawals_policy.txt` (WHAT HAPPENS WHEN YOU WITHDRAW / 60% rule) | 0.205 |
| 4 | `lehman_withdrawals_policy.txt` (ORDER OF RETURN) | 0.364 |
| 5 | `lehman_withdrawals_policy.txt` (document header) | 0.379 |

**Why these chunks are relevant:** Four of the top five hits come from the dedicated withdrawals policy doc, and the fifth is the warning paragraph from the general FAQ. The top hit at distance 0.170 is the lowest score across the whole eval set — the question and the document share vocabulary ("withdraw," "classes," "federal aid"), so the embedding model aligns them cleanly. The retrieved set covers the three sub-topics needed for a complete answer (60% rule, return order, future-aid consequences), all within one document, which means the LLM can synthesize without conflicting sources.

### Query B: "What is the income limit to qualify for the Excelsior Scholarship?"
| Rank | Source | Distance |
|---|---|---|
| 1 | `lehman_state_aid_faqs.txt` (Excelsior FAQ block) | 0.261 |
| 2 | `lehman_excelsior_scholarship.txt` (doc header) | 0.426 |
| 3 | `hesc_student_update_feb2026.txt` (Spring 2026 Excelsior reminder) | 0.460 |
| 4 | `lehman_excelsior_scholarship.txt` (IMPORTANT NOTE — application closed) | 0.515 |
| 5 | `lehman_excelsior_scholarship.txt` (IMPORTANT CREDIT NOTE) | 0.519 |

**Why these chunks are relevant:** All five hits are Excelsior-related across three different sources. Interestingly, the top hit is the **state aid FAQs**, not the dedicated Excelsior page — the FAQ phrases the $125,000 income limit as a direct Q&A, which embeds closer to the query than the Excelsior page's narrative prose. The dedicated Excelsior page is still in the top 5, so the LLM has both phrasings. The answer is correct either way — but it's a useful data point showing that documents written as Q&A pairs tend to dominate retrieval for question-shaped queries.

### Query C: "How do I check my financial aid status in CUNYfirst?"
| Rank | Source | Distance |
|---|---|---|
| 1 | `lehman_cunyfirst_facts_guide.txt` (HOW TO VIEW step-by-step) | 0.298 |
| 2 | `lehman_financial_aid_faqs.txt` (HOW TO VIEW in CUNYfirst) | 0.299 |
| 3 | `lehman_cunyfirst_facts_guide.txt` (TO DO LIST) | 0.331 |
| 4 | `lehman_cunyfirst_facts_guide.txt` (CUNYfirst overview) | 0.368 |
| 5 | `lehman_financial_aid_faqs.txt` (CHECK CUNYFIRST alerts) | 0.374 |

(Explanation not required for this third query — included to show retrieval consistency.)

---

## Grounded Generation

Grounding is enforced by the **system prompt** attached to the Gemini model on every call. The system prompt explicitly forbids the model from using any knowledge outside the retrieved context, and mandates a specific refusal phrase for out-of-scope questions. The retrieved chunks are then injected into the user message as labeled `[Source N: filename]` blocks above the question.

**Verbatim system prompt** (`app.py`):

```
You are a financial-aid assistant for Lehman College (CUNY) students.

Answer using ONLY the information in the Context block below. The context is
labeled [Source N: filename] for each chunk. Do not use any prior knowledge,
general knowledge, training data, or plausible-sounding inference. Do not
fabricate dates, amounts, deadlines, URLs, eligibility rules, or procedures
that are not explicitly stated in the context.

If the context does not contain enough information to answer the question,
respond with EXACTLY this sentence and nothing else:
"I don't have enough information on that".

When the context is sufficient, write a direct, plain-prose answer. Do not
include inline citations or "[Source N]" markers — the UI shows sources in a
separate panel.
```

**How source attribution is surfaced:** The Gradio UI renders sources in a dedicated **Sources** panel below the answer textbox. Each retrieved chunk is shown as `filename` + cosine distance + a ~200-char preview, in retrieval rank order. Inline citations were deliberately kept *out* of the answer text so the prose reads naturally — the user verifies grounding by inspecting the side panel.

---

## Example Responses

### Example 1 — Excelsior income limit (grounded answer with sources)

**Query:** *What is the income limit to qualify for the Excelsior Scholarship?*

**Answer:** Household federal adjusted gross income can total up to $125,000 to be eligible for the Excelsior Scholarship.

**Sources (top 5):**
1. `lehman_state_aid_faqs.txt` (dist 0.261)
2. `lehman_excelsior_scholarship.txt` (dist 0.426)
3. `hesc_student_update_feb2026.txt` (dist 0.460)
4. `lehman_excelsior_scholarship.txt` (dist 0.515)
5. `lehman_excelsior_scholarship.txt` (dist 0.519)

### Example 2 — TAP 5th payment requirements (grounded answer with sources)

**Query:** *How many credits do I need to complete for my 5th TAP payment?*

**Answer:** For your 5th TAP payment, you need to complete 9 credits and have accumulated 33 credits, with a GPA of 2.0.

**Sources (top 5):**
1. `lehman_tap_program.txt` (dist 0.329) — TAP ELIGIBILITY CHARTS
2. `lehman_tap_program.txt` (dist 0.340) — PART-TIME TAP
3. `lehman_tap_program.txt` (dist 0.357) — SUMMER TAP AWARDS
4. `lehman_tap_program.txt` (dist 0.361) — TAP INELIGIBILITY
5. `lehman_tap_program.txt` (dist 0.391) — TAP QUALIFICATIONS

### Example 3 — Withdrawal from all classes (strongest retrieval case)

**Query:** *What happens to my financial aid if I withdraw from all my classes?*

**Answer:** If you withdraw from all your classes, or stop attending them without officially withdrawing, several things can happen to your financial aid:

- **Return of Federal Aid:** If you withdraw from all classes before completing 60% of the semester, federal regulations require Lehman College to calculate how much federal aid you "earned." The unearned portion must be returned to the federal aid programs. The college will use your last date of attendance to calculate this if you unofficially withdraw.
- **Financial Obligations:** You may owe money back to Lehman College and/or the federal government. This can include increased out-of-pocket payments toward tuition or having to repay received funds to the U.S. Department of Education.
- **Impact on Future Aid:** Your financial aid for future semesters may be affected, and you could lose part or all of the following semester's financial aid. Your SAP status may also be impacted, and you may lose TAP eligibility for that semester.
- **Student Loans:** A student loan could be forced into repayment.
- **Order of Return:** Funds must be returned in a specific order: Unsubsidized Direct Loan, Subsidized Direct Loan, PLUS loans, Pell Grant, SEOG, and other federal aid.

It is strongly advised to always consult a financial aid counselor before withdrawing from all courses, as the consequences can extend beyond one semester.

**Sources (top 5):**
1. `lehman_withdrawals_policy.txt` (dist 0.170) — UNOFFICIAL WITHDRAWALS
2. `lehman_financial_aid_faqs.txt` (dist 0.191) — DROPPING OR WITHDRAWING warning
3. `lehman_withdrawals_policy.txt` (dist 0.205) — WHAT HAPPENS WHEN YOU WITHDRAW / 60% rule
4. `lehman_withdrawals_policy.txt` (dist 0.364) — ORDER OF RETURN
5. `lehman_withdrawals_policy.txt` (dist 0.379) — document header

This is the strongest retrieval case in the eval set: 4 of 5 chunks come from the dedicated withdrawals policy doc and the top hit has the lowest distance (0.170) of any eval query.

---

## Refusal / Out-of-Scope Example

**Query:** *How do I apply for a parking permit at Lehman?*

**Answer:** I don't have enough information on that.

Parking is not covered in any of the indexed documents, so the system prompt's refusal clause triggers and the model emits the exact refusal phrase. Without RAG, Gemini would happily generate a plausible-sounding parking procedure from general knowledge. With grounding enforced via the system prompt, it cleanly refuses instead of hallucinating.

---

## Query Interface

Built with Gradio (`gradio==6.16.0`). The UI has three visible regions:

| Field | Type | Purpose |
|---|---|---|
| **Your question** | Textbox (2 lines, editable) | Free-text input. Submits on Enter or via the **Ask** button. |
| **Answer** | Textbox (8 lines, read-only) | Gemini's response text. Plain prose, no inline citations. |
| **Sources** | Static "### Sources" heading + Markdown panel | Numbered list of the 5 retrieved chunks: source filename, cosine distance, and a 200-char preview. Visible from page load with a placeholder before the first query. |

### Sample interaction transcript

```
[USER types]
How do I appeal a SAP suspension at Lehman?

[USER clicks Ask]

[ANSWER panel renders]
To appeal a SAP suspension at Lehman College, undergraduate
students should submit an electronic SAP appeal at
lehman.smapply.io/prog/undergraduate_appeals/. Graduate students
should submit a typed written appeal via email to
Takiyah.Ali@lehman.cuny.edu.

The SAP appeal must include:
*   A detailed explanation of mitigating circumstances (such as
    personal illness/injury, family illness/death, loss of
    employment, or academic program changes).
*   Supporting documentation (such as medical records, a death
    certificate, or court/legal records).
*   A discussion of changes in circumstances and personal
    adjustments that will help maintain SAP in the future.
*   An academic plan for achieving and maintaining future SAP
    requirements.

A SAP review can be requested after any term in which aid was
suspended.

[SOURCES panel renders]
**Sources (top 5)**

1. `lehman_sap_policy.txt` (dist 0.386)
   > RE-ESTABLISHING ELIGIBILITY: - A SAP review can be requested...
2. `lehman_sap_policy.txt` (dist 0.409)
   > DEADLINE: THE DEADLINE TO SUBMIT A SAP APPEAL FOR SPRING 2026...
3. `lehman_sap_policy.txt` (dist 0.423)
   > SOURCE: https://www.lehman.edu/financial-aid/sap/ ...
4. `lehman_sap_policy.txt` (dist 0.447)
   > THE SAP APPEAL MUST INCLUDE: - Detailed explanation of...
5. `lehman_sap_policy.txt` (dist 0.464)
   > FINANCIAL AID SUSPENSION: Failure to satisfy any SAP criteria...
```

---

## Evaluation Report

All 5 test questions from `planning.md` run through the live system.

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|---|---|---|---|---|
| 1 | How many credits do I need for my 5th TAP payment? | 9 credits completed in the prior term, 33 credits accumulated, GPA of 2.0 | "9 credits and accumulated 33 credits, with a GPA of 2.0" | Relevant (all 5 hits from `lehman_tap_program.txt`) | **Accurate** — minor: omitted the "prior term" qualifier on the 9 credits |
| 2 | What happens to my financial aid if I withdraw from all my classes? | 60% completion rule, unearned aid returned to federal programs in specific order, future eligibility may be affected | Covers 60% rule, return order, loans being forced into repayment, SAP impact, and future-semester aid loss | Relevant (4/5 from `lehman_withdrawals_policy.txt`, dist 0.170) | **Accurate** — thorough and well-organized |
| 3 | How do I appeal a SAP suspension at Lehman? | Submit electronic SAP appeal at lehman.smapply.io/prog/undergraduate_appeals/ with documentation; if granted, placed on probation for one semester | Submission URL + grad routing + 4 required appeal components | Relevant (all 5 from `lehman_sap_policy.txt`) | **Partially accurate** — omitted the post-appeal probation outcome |
| 4 | What is the income limit to qualify for the Excelsior Scholarship? | Household federal AGI at or below $125,000 | "Household federal adjusted gross income can total up to $125,000" | Relevant (top hit from state-aid FAQs, not dedicated Excelsior page — see Failure Case note) | **Accurate** |
| 5 | How do I check my financial aid status in CUNYfirst? | Log into home.cunyfirst.cuny.edu → Student Center → Financial Aid → Aid Year → Award Summary; also check TO DO list | Full step path + TO DO list discussion | Relevant (top 2 from CUNYfirst guide and FAQ) | **Accurate** |

**Summary:** 4 of 5 accurate, 1 partially accurate. Retrieval quality was **Relevant** on all 5 — every top hit pulled from a topically correct source document. The single failure was a *completeness* gap, not a *correctness* gap.

---

## Failure Case Analysis

**Question that failed:** *How do I appeal a SAP suspension at Lehman?*

**What the system returned:** A correct description of the submission URL (`lehman.smapply.io/prog/undergraduate_appeals/`), graduate-vs-undergraduate routing, and the four required components of an appeal package (mitigating circumstances, supporting documentation, change in circumstances, academic plan). What it **omitted**: the outcome of a successful appeal — that the student is placed on probation for one semester. A student asking "how do I appeal" almost certainly wants to know "and what happens next?"

**Root cause (retrieval stage):** Inspecting the top-5 retrieved chunks for this query, all five came from `lehman_sap_policy.txt` and covered: how to submit (chunk 1), what to include (chunk 4), re-establishing eligibility (chunk 9), the document header (chunk 0), and suspension consequences (chunk 6). The "probation after a granted appeal" content lives in a different chunk of the same document — but it ranked sixth or lower because the query embedding for "how do I appeal" lexically clusters around *submission* and *documentation* vocabulary, not *outcome* vocabulary like "probation" or "warning period." With `top_k=5`, the probation chunk was just outside the retrieved window.

**What I would change to fix it:**

1. **Cheap fix:** bump `TOP_K` from 5 to 7 or 8 — likely pulls the probation chunk into context without diluting precision (every current top hit is from the same document anyway, so there's headroom).
2. **Better fix:** add query expansion for procedural questions — "how do I X" should also retrieve "what happens after X."
3. **Best fix for this corpus:** chunk the SAP appeal content as one unit (submission + requirements + outcome) rather than letting `RecursiveCharacterTextSplitter` divide it across boundaries. Docling's `HybridChunker` targets exactly this and is on my stretch list.

A second behavioral note from the eval (not a failure, but worth documenting): for the Excelsior income query, the dedicated `lehman_excelsior_scholarship.txt` ranked *below* `lehman_state_aid_faqs.txt`. Both contain the $125k figure, so the answer is still correct, but documents written in explicit Q&A form tend to win retrieval for question-shaped queries over documents written as narrative policy prose.

---

## Stretch Feature: Hybrid Search (BM25 + Semantic via RRF)

**What I built.** A second retriever (`retrieve_bm25`) using `rank_bm25`'s `BM25Okapi` over the same 98 chunks, plus a fusion function (`retrieve_hybrid`) that combines semantic and BM25 candidate sets via **Reciprocal Rank Fusion** with the standard `k=60` constant. Each side contributes its top-20 candidates; RRF fuses by rank, not raw score, so it sidesteps the cosine-vs-BM25 score-scale mismatch. Implementation lives in `embed.py`; a comparison script at `compare_retrievers.py` runs the 5 eval queries through all three retrievers (semantic-only, BM25-only, hybrid) and prints a per-query diff.

**Hypothesis.** The documented SAP-appeal failure was a *recall* problem driven by vocabulary mismatch — the relevant "probation" chunk ranked outside top-5 because the query "how do I appeal" embeds far from outcome-vocabulary like *probation* or *warning period*. BM25, matching surface keywords, should surface that chunk; hybrid should pull it into top-5 without losing the semantic wins on the other queries.

**Results.**

| # | Query | Hybrid effect on top-5 | Verdict |
|---|---|---|---|
| 1 | TAP 5th payment | Added `tap_program#6` (continuation of payment chart) + `state_aid_faqs#1` (TAP FAQ); dropped `#2` (Part-time TAP) and `#9` (Summer TAP) | Mild improvement — payment chart now contiguous |
| 2 | Withdraw all classes | **Dropped `withdrawals#3` (the ORDER OF RETURN list)**, added a Reddit anecdote chunk | Mild regression |
| 3 | **SAP appeal** | **Added `sap_policy#8` (FINANCIAL AID PROBATION) at rank 5** — the exact chunk needed to fix the documented failure case | **Clear win** |
| 4 | Excelsior income | No change | Neutral |
| 5 | CUNYfirst aid status | **Dropped `faqs#6` (the step-by-step instructions)**, added the document header `cunyfirst_facts#0` | Mild regression |

**Verdict.** Hybrid is a **targeted fix, not a universal upgrade.** It fixed exactly the failure case I designed it to address: the FINANCIAL AID PROBATION chunk that lives at `lehman_sap_policy.txt#8` jumped from rank 6+ (semantic-only) to rank 5 (hybrid), which means the grounded answer would now include the post-appeal probation outcome that the original system missed. But on two other queries (Withdrawals, CUNYfirst) BM25 pulled in surface-keyword matches that lack semantic depth — a Reddit personal anecdote because it contains "withdraw," and a document header because it contains "CUNYFIRST" — at the cost of more substantive chunks.

**Why this pattern is consistent with theory.** BM25 helps when query terms are rare and meaningful (*probation*, *eligibility chart*); it hurts when query terms are common across the corpus (*withdraw*, *CUNYfirst*) because keyword matches no longer differentiate substance from surface mentions. Hybrid via RRF averages the two systems' ranks — if one system gets the right chunk at rank 1 and the other ranks a noisy chunk at rank 1, the noisy chunk leaks into top-5 too.

**What I would change to make hybrid a default.** Two cheap, complementary fixes:

1. **Weighted RRF** — multiply the semantic side's RRF contribution by 1.5–2x. Tilts the fusion toward semantic, lets BM25 only override when its signal is strong enough to outvote the weight.
2. **Filter the BM25 candidate set** — drop chunks shorter than ~200 chars or that match a "header pattern" (lines like `SOURCE:`, `DOCUMENT:`, `SCRAPED:` near the top). Most of the BM25-induced regressions came from header chunks that contain the query keyword but no answer content.

**Why I am not switching the app's default.** The win on Q3 is real, but the two regressions cost real information (an enumerated list of return order, step-by-step CUNYfirst instructions). Defaulting `app.py` to hybrid would regress two out of five eval queries to fix one. The honest move is to leave the default as semantic-only, document hybrid as available, and ship the targeted weighted-RRF + header-filter tuning before defaulting to it. Both `retrieve()` and `retrieve_hybrid()` are exposed in `embed.py` for anyone who wants to A/B them.

**Reproduce:** `ai201_env/bin/python compare_retrievers.py`

---

## Spec Reflection

**One way the spec helped during implementation:**

The `planning.md` document forced every architectural decision upfront before any code was written — chunk size, overlap, embedding model, top-k, the exact 12 documents, even the 5 evaluation queries with expected answers. That meant each milestone's code task was a near-mechanical translation of a spec section, and I could verify correctness immediately at every stage instead of guessing what "good" looked like. The 5 evaluation queries especially: I ran them at the end of Milestone 4 (retrieval) and again at the end of Milestone 5 (generation), so any regression would have shown up at the milestone boundary, not at submission time.

**One way the implementation diverged from the spec, and why:**

The spec called for `Groq llama-3.3-70b-versatile` in the architecture diagram, but the final implementation uses **Gemini 2.5 Flash via the `google-genai` SDK**. The first divergence was forced: Groq signup kept erroring out with a `trace_id` failure I couldn't get past, so I switched providers. The second divergence (2.0 → 2.5 Flash) was forced: Gemini's free tier returned `limit: 0` for `gemini-2.0-flash` on my project, so I tested `gemini-2.5-flash` and it worked. A smaller but parallel divergence: I added a `<100 character` filter to drop header-only chunks after chunking — not in the original spec, but the un-filtered chunks polluted retrieval with metadata-only fragments. Both divergences kept the contract the spec was actually trying to enforce (grounded answers + source attribution); only the choice of provider and a chunk hygiene step changed.

---

## AI Usage

**Instance 1 — Ingestion script (Milestone 3)**

- *What I gave the AI:* The completed `planning.md` Documents table and Chunking Strategy section, plus an explicit spec: load all `.txt` files from `data/raw/`, attach source filename as metadata to each chunk, use LangChain `RecursiveCharacterTextSplitter` with `chunk_size=500` and `chunk_overlap=100`, print total chunk count plus 5 sample chunks with their source filenames. I included the directive "Do not add features not described there."
- *What it produced:* A clean `ingest.py` with `load_documents`, `chunk_documents`, and a `main()` that printed sequential samples 1–5. It also missed that `langchain-text-splitters` wasn't in `requirements.txt` until I told it to add it, and missed that the venv's `pip` was broken (system Python was in `PATH` instead of the venv).
- *What I changed or overrode:* (1) Overrode "5 sequential samples" with "5 random samples from 5 different source documents" — sequential samples all came from the same file and were useless for inspecting chunking quality across the corpus. (2) Added the `<100 character` chunk filter — the AI's chunks included tiny header-only fragments from the document metadata blocks, which I caught when reading the printed samples. (3) After it tried to write `ingest.py` without pinning the new dependency, I gave it a durable rule — "dependency issues that aren't pinned will bite whoever tries to run the project later" — and it pinned every transitive dependency it touched for the rest of the project.

**Instance 2 — LLM provider swap (Milestone 5)**

- *What I gave the AI:* "Replace Groq with Google Gemini API using `gemini-2.0-flash`. Use the google-generativeai Python SDK. Add GEMINI_API_KEY to .env and requirements.txt. Keep everything else the same — same grounding prompt, same source attribution, same Gradio UI." *Context:* the swap was forced — Groq signup kept failing with a `trace_id` error (a recurring platform issue I couldn't get past after multiple attempts and public tagging), not a preference.
- *What it produced:* A correct swap to the legacy `google-generativeai` SDK, but it flagged in the plan that this SDK is officially deprecated by Google in favor of the newer `google-genai`. After install, the runtime printed the same deprecation warning.
- *What I changed or overrode:* (1) Directed it to swap a second time, from the legacy `google-generativeai` to the current `google-genai` package — which has a different API surface (`genai.Client(...)`, `client.models.generate_content(...)`, config via `types.GenerateContentConfig`). (2) The first end-to-end run hit `429 limit: 0` on the free tier for `gemini-2.0-flash`, so I had it switch the model constant to `gemini-2.5-flash` — and that's the model in the final code. (3) Caught that the Gradio Sources panel rendered invisibly when empty (`gr.Markdown()` with no value) — had it add a static `### Sources` heading and a placeholder value so the panel is visible from page load, before recording the demo video.

---

## Setup & Run

```bash
# 1. Create venv and install
python -m venv ai201_env
source ai201_env/bin/activate
pip install -r requirements.txt

# 2. Configure Gemini key
cp .env.example .env
# edit .env and replace `your_key_here` with your key from https://aistudio.google.com/apikey

# 3. Ingest + chunk (writes data/chunks.txt for inspection)
python ingest.py

# 4. Build the Chroma vector index (downloads MiniLM ~80MB on first run)
python embed.py

# 5. Launch the UI
python app.py
# → http://127.0.0.1:7860
```
