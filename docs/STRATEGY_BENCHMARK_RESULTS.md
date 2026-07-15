# Cross-Strategy Needle-in-a-Haystack Benchmark — Results

Real measurements from one run of `scripts/run_strategy_benchmark.py`, executed
2026-07-15. Every number below is a direct read of `results/strategy_benchmark_20260715_221805.json`
— a raw dump of the actual pipeline calls, including full completion text. Nothing
here is estimated or backfilled; a strategy that failed would be listed as failed,
not given a guessed score (none did, in this run).

---

## 1. Why this document exists

`docs/PARA_EMPIRICAL_FINDINGS.md` established PARA's internal mechanics (recall vs.
reordering) via ablations *within* PARA. It did not compare PARA against the other
10 recovery strategies implemented in `process_pdf.py`. This document does that —
once, on one document, at one needle position — and reports exactly what happened,
including where PARA did not uniquely win.

**Before running anything**, all 11 strategies were audited for runnability and
output comparability. Summary of that audit (full detail in the commit that added
this doc):

- All 11 are runnable: `GROQ_API_KEY` live-tested, `sentence-transformers` +
  cached bi-encoder/cross-encoder models present, `openai`/`PyPDF2` installed.
- They are **not** structurally comparable out of the box. Three families exist:
  - **`para`** is the only strategy with a real top-k retrieval step — rank and
    candidate-pool size are genuine, measurable numbers only for this strategy.
  - **7 strategies** (`attention_anchoring`, `relevance_restructuring`,
    `query_aware_compression`, `query_aware_contextualization`, `reranking`,
    `chunk_by_chunk_reasoning`, `combined`) stuff *every* chunk into the prompt,
    reordered or annotated, and only drop content via a hard **24,000-character**
    truncation applied after assembly. No selection step, no rank.
  - **2 strategies** (`map_reduce`, `chunked_reading`) are two-phase: every chunk
    gets a shot at LLM-based fact extraction in batches, nothing is ever dropped.
  - **`baseline`** isn't retrieval at all — `pdf_text[:8000]`, first ~8,000 raw
    characters, no chunking used.
- Given that, "rank" is reported **only for `para`**. For the other 10, the
  measured proxy is: did the needle's exact text reach the real prompt sent to
  the LLM (captured by patching `LLMClient.generate` for the duration of each
  call — not inferred, not re-implemented separately from the production code
  path).

---

## 2. Experimental setup

| Parameter | Value |
|---|---|
| Document | `data/uploads/1783412814023_Object Oriented Programmings.pdf` — 11,594 words, 65,613 chars |
| Needle fact | *"According to the Kirchner benchmark, virtual function dispatch adds 7 nanoseconds of overhead per call."* |
| Needle question | *"According to the Kirchner benchmark, how many nanoseconds of overhead does virtual function dispatch add per call?"* |
| Insertion position | 0.5 (document middle — word offset 5,797 of 11,594) |
| Provider | `groq` (production default: `llama-3.3-70b-versatile` → `llama-3.1-8b-instant` → Gemini fallback, per `_build_resilient_client`) |
| Runs per strategy | 1 |
| Verified before use | `"kirchner"` and `"nanosecond"` both appear **0** times natively in the source PDF |

**Method:** each strategy was run through the real, unmodified `answer_question()`
— the same function the `/ask` endpoint calls — with `LLMClient.generate` patched
non-invasively to log every real prompt sent during that strategy's execution
(single choke point every strategy funnels through, so no strategy's internal
context-assembly logic was duplicated or guessed at). A strategy that raised an
exception was retried once, then recorded as failed and would have been excluded
from the table below — none needed exclusion in this run.

**Important limitation of the setup itself:** the needle sentence shares several
literal content words with the question (*Kirchner, nanoseconds, virtual, function,
dispatch, overhead, call*). That makes it an easy target for the keyword-overlap
heuristic (`_compute_relevance_score`) that several strategies use, and it's a
near-verbatim semantic match for PARA's embedding retrieval too. This setup tests
**recall and context-survival**, not paraphrase robustness — see §5.

---

## 3. Results

| Strategy | Chunks considered | Needle reached LLM's context | Correct answer | LLM calls | Latency | Model used |
|---|---|---|---|---|---|---|
| `baseline` | 34 (computed, unused — see §1) | **No** | ❌ No | 1 | 1.9s | llama-3.3-70b-versatile |
| `attention_anchoring` | 34 | **No** | ❌ No | 1 | 4.2s | gemini-2.5-flash |
| `relevance_restructuring` | 34 | Yes | ✅ Yes | 1 | 4.3s | gemini-2.5-flash |
| `query_aware_compression` | 34 | **No** | ❌ No | 5 | 9.6s | gemini-2.5-flash |
| `query_aware_contextualization` | 34 | **No** | ❌ No | 1 | 4.6s | gemini-2.5-flash |
| `reranking` | 34 | Yes | ✅ Yes | 1 | 3.6s | gemini-2.5-flash |
| `chunk_by_chunk_reasoning` | 34 | **No** | ❌ No | 1 | 4.3s | gemini-2.5-flash |
| `map_reduce` | 34 | Yes | ✅ Yes* | 10 | 177.3s | not captured (see §5) |
| `chunked_reading` | 34 | Yes | ✅ Yes | 13 | 202.8s | not captured (see §5) |
| `combined` | 34 | Yes | ✅ Yes | 1 | 12.5s | llama-3.1-8b-instant |
| `para` | 109 (semantic chunking, not the same unit as the row above — see §1) | Yes | ✅ Yes | 2 | 56.5s | llama-3.1-8b-instant |

**Rank/pool-size — meaningful only for `para`** (direct, non-LLM diagnostic against
`PARARetriever` internals, production defaults, same needle-inserted text):

| Candidate pool | Pool size | Needle rank | Inside top-10? |
|---|---|---|---|
| Top-level (semantic) chunks | 109 | **1** | Yes |
| Sentence-level (multi-granularity) | 697 | **1** | Yes |

No other strategy has an analogous "rank" — reported here only because it's real
for this one strategy, not extrapolated to the rest.

\* `map_reduce`'s answer contains the correct fact (correctly localized to
"passage 17") but the completion then degenerates into a ~60-repetition loop
of near-identical sentences about passages 23/24/33/34. `found_needle()` scores
this "correct" because the right number is stated early and clearly — but the
raw output is a real quality defect a boolean correctness check doesn't surface.
Full text is in the saved JSON if you want to see it archived, not reproduced
here.

---

## 4. What actually determined pass/fail

**5 of 11 failed** — and all five failed the same way: the needle's chunk never
reached the prompt the LLM saw. Confirmed directly (not inferred) via the prompt
log:

- **`baseline`**: structural, by design. The needle sits at the document's
  middle (~byte offset 33,000); baseline only ever sees the first 8,000
  characters (~12% of this document). This isn't a reasoning failure — it's the
  "no mitigation" control behaving exactly as it's supposed to.
- **`attention_anchoring`, `query_aware_contextualization`, `chunk_by_chunk_reasoning`**:
  all three preserve the chunks' *original* document order and only annotate or
  frame them — no reordering. With 34 chunks totaling ~74,700 characters against
  a 24,000-character truncation cap, only the first third or so of the document
  (by original order) survives. The needle, sitting at the middle, doesn't.
- **`query_aware_compression`**: partial case. Its own keyword scorer *did* rank
  the needle chunk as "high relevance" (kept full-text, not compressed) — but it
  places the first half of relevant chunks, then all compressed summaries, then
  the second half of relevant chunks. The needle landed in that second half, and
  by the time the compressed-middle text consumed budget, truncation cut it
  before it arrived.

**6 of 11 succeeded**, for two different reasons:

- **`relevance_restructuring`, `reranking`, `combined`** all share the same
  keyword-overlap scorer (`_compute_relevance_score`). Because the needle
  sentence literally contains most of the question's content words, it scored
  near the top and got placed at an edge (or first) — well inside the 24k
  truncation window. This is keyword luck specific to this needle's design, not
  evidence these three would recover a paraphrased or keyword-poor fact the same
  way.
- **`map_reduce`, `chunked_reading`** succeed structurally: neither ever drops a
  chunk — every chunk gets a dedicated extraction call. That guarantee costs
  10–13 LLM calls and 175–200s of latency, roughly 15–50x the single-call
  strategies.
- **`para`** succeeded via genuine semantic retrieval — cosine similarity ranked
  the needle chunk **#1** out of both a 109-chunk and a 697-chunk candidate pool,
  independent of keyword overlap with the query. Mechanistically distinct from
  the keyword-luck group above, even though the pass/fail outcome looks the same
  in this one table.

---

## 5. Honest limitations — read before citing any of this

- **PARA does not uniquely win here.** 5 other strategies (`relevance_restructuring`,
  `reranking`, `combined`, `map_reduce`, `chunked_reading`) also produced the
  correct answer in this single test. What's different about PARA is *mechanism*
  (real rank-1 semantic retrieval vs. keyword-overlap luck or brute-force
  full-document processing), not raw pass/fail count in this one setup.
- **The needle is keyword-friendly.** It shares literal words with the question.
  A harder, paraphrased needle would very plausibly break the keyword-scorer-based
  strategies (`relevance_restructuring`, `reranking`, `combined`,
  `query_aware_compression`) while leaving PARA's embedding-based retrieval
  comparatively unaffected — but that experiment was not run. This document
  doesn't claim it was.
- **`n=1`.** Single run per strategy, single position (0.5), single document,
  single needle. No variance data exists for any cell in the table above — same
  caveat `PARA_EMPIRICAL_FINDINGS.md` already applies to its own ablations.
- **`model_used` is not fully comparable across the row.** During this run, Groq
  rate-limited after the first couple of calls and the app's built-in
  cross-provider resilience (`ResilientLLMClient`) failed over to Gemini
  automatically for several strategies, then back to a smaller Groq model later.
  Three different underlying models answered different rows of this table
  (`llama-3.3-70b-versatile`, `gemini-2.5-flash`, `llama-3.1-8b-instant`) — a real
  and expected consequence of the app's resilience design, but it means this
  table is not a controlled single-model comparison.
- **`model_used` is missing entirely for `map_reduce` and `chunked_reading`.**
  Their code path in `process_pdf.py` returns early with its own response dict
  that doesn't include a `model_used` key — a real gap in `process_pdf.py`'s
  return schema, not a benchmarking omission. It's flagged here rather than
  filled in with a guess.
- **This does not supersede or repeat the "57%"/"99.2%" figures** flagged as
  unverifiable in `PARA_EMPIRICAL_FINDINGS.md` §7. Those remain unsupported;
  this document doesn't reference or validate them.

---

## 6. What this document supports you saying in an interview

- "I ran a controlled needle-in-a-haystack test across all 11 implemented
  strategies against the same document, needle, and question, and measured —
  not estimated — whether each strategy's real prompt to the LLM contained the
  needle and whether its real completion stated the fact correctly."
- "6 of 11 strategies recovered the needle; the 5 that failed all failed for the
  same measured reason — the needle's chunk was truncated out of the assembled
  context before the LLM ever saw it, either by design (`baseline`) or as a side
  effect of keeping original chunk order under a fixed character budget."
- "PARA recovered the needle via a mechanistically different path — direct
  semantic similarity ranking it #1 of 109/697 candidates — rather than the
  keyword-overlap heuristic that explains why 3 of the other successful
  strategies also passed this specific test."
- "I have not yet shown PARA winning where the others fail — this test doesn't
  isolate that case. That would need a paraphrased, keyword-poor needle, which
  is the natural next experiment."

*Raw data: `results/strategy_benchmark_20260715_221805.json`. Runner:
`scripts/run_strategy_benchmark.py`.*
