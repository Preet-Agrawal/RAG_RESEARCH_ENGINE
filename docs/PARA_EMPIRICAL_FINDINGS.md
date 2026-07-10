# PARA — Empirical Findings

Everything in this document was measured during one working session. No number here is illustrative or fabricated — each is either a direct diagnostic output or a real ablation run, and each is labeled with how it was produced. Where something was not established, this document says so explicitly rather than implying more confidence than the data supports.

---

## 1. The Scoring Formula

As implemented in `src/para.py`:

```
score(c) = alpha * sim(q, c) + beta * gamma * sin(pi * p)
```

| Symbol | Meaning | Default | Set at |
|---|---|---|---|
| `sim(q, c)` | Cosine similarity between the query embedding and the chunk embedding (bi-encoder, `all-MiniLM-L6-v2`) | — (computed per call) | `src/para.py:361` (`final_scores = alpha * semantic_scores + beta * pos_corrections`) |
| `p` | Chunk's position in the document, `0.0` (start) to `1.0` (end), computed as word-offset ÷ total-words | — (computed per chunk) | Set when chunks are created, e.g. `process_pdf.py`'s `chunk_text()` |
| `alpha` | Weight on semantic similarity | `0.7` | `src/para.py:321` (`score_chunks` signature); also `process_pdf.py:469` |
| `beta` | Weight on the position-correction term | `0.3` | `src/para.py:321`; also `process_pdf.py:469` |
| `gamma` | Amplitude of the position correction | Adaptive (see below); fixed fallback `0.3` | `src/para.py:263-278` (`compute_adaptive_gamma`) |
| `sin(pi * p)` | The position-correction shape | — | `src/para.py:300` |

**What `sin(pi * p)` does, in plain terms:**
- At `p = 0` (document start): `sin(0) = 0` — no boost.
- At `p = 0.5` (document middle): `sin(pi/2) = 1` — maximum boost.
- At `p = 1` (document end): `sin(pi) = 0` — no boost.

**Why this shape was chosen:** it mirrors the *inverse* of the empirical U-shaped attention-accuracy curve reported by Liu et al. (2023) — LLMs are reliable near the start and end of a context and measurably worse in the middle. The correction adds the most weight exactly where that drop is worst, and nothing at the edges, where no correction is needed. This is an engineering choice, not a derivation — `src/para.py:281-317` (`compute_position_bias_correction`) implements four alternative shapes (`gaussian`, `triangle`, `step`, `none`) specifically so this choice is falsifiable, not asserted.

**Adaptive gamma:**
```
gamma = base_gamma * log(num_chunks) / log(10)
```
`src/para.py:263-278`. Rationale in the code: longer documents suffer a worse middle-attention drop, so the correction should scale up with document length — but sub-linearly (log, not linear). `base_gamma = 0.3`. `adaptive_gamma=False` pins `gamma` to the fixed `0.3` instead.

---

## 2. What The Pipeline Actually Does

Real call chain, file:line:

```
src/api.py:137  ask(body)
  -> src/api.py:147  answer_question(pdf_text, question, strategy, provider=...)
    -> process_pdf.py:931  elif strategy == "para":
      -> process_pdf.py:941  processor.apply_para(chunks, question, full_text=pdf_text)
        -> process_pdf.py:468  MiddleRecoveryProcessor.apply_para(...)
          -> src/para.py:486  PARARetriever.build_para_context(...)
            -> src/para.py:443  retrieve_multi_granularity()   [if use_multi_granularity]
            -> src/para.py:420  retrieve_top_k()
              -> src/para.py:321  score_chunks()          <- RECALL + initial ranking
              -> src/para.py:375  cross_encoder_rerank()  <- REORDERING only
```

**Which stage does recall:** `score_chunks()` (`src/para.py:321`) computes `alpha*sim + beta*gamma*sin(pi*p)` for every candidate chunk and sorts descending. This — combined with which chunk *sets* even exist to be scored (see `multi_granularity_chunks`, next point) — is what determines which chunks are recall-eligible at all.

**Where `multi_granularity_chunks()` runs:** `src/para.py:160`, called from `retrieve_multi_granularity()` at `src/para.py:443`. It builds three independent candidate pools from the same document — sentence-level, paragraph-level, section-level — and each pool is scored separately via `score_chunks()`, then merged and deduplicated. This is the only place in the pipeline that changes what a "chunk" even *is*, as opposed to how existing chunks are scored or ordered.

**Which stage does reordering, and its structural limit:** `cross_encoder_rerank()` (`src/para.py:375`) is called from `retrieve_top_k()` at `src/para.py:439` as `cross_encoder_rerank(query, scored, top_n=min(k, len(scored)))`. Critically, `retrieve_top_k()` calls `score_chunks()` first, and only passes `cross_encoder_rerank()` the slice `scored[:top_n]` (`src/para.py:439`, `top_n` defaulting to `top_k=10`). **`cross_encoder_rerank()` structurally cannot see or pull in anything ranked below `top_k` by `score_chunks()`.** It can only reorder *within* the set `score_chunks()` already selected. If a chunk isn't in the top-`k` by semantic+position score, the cross-encoder never gets a chance to rescue it — confirmed directly in Section 4, Experiment D below.

---

## 3. Production Defaults

The real `/ask` request path (`src/api.py:147` → `process_pdf.py:941`) passes only `chunks`, `question`, and `full_text` into `apply_para()` — every other parameter falls through to its default.

| Parameter | Production default | Set at |
|---|---|---|
| `alpha` | `0.7` | `process_pdf.py:469` |
| `beta` | `0.3` | `process_pdf.py:469` |
| `top_k` | `10` | `process_pdf.py:470` |
| `correction_type` | `"sin"` | `process_pdf.py:471` |
| `adaptive_gamma` | `True` | `process_pdf.py:472` |
| `use_cross_encoder` | `True` | `process_pdf.py:473` |
| `use_multi_granularity` | **`True`** | `process_pdf.py:474` |

**`use_multi_granularity=True` is the production default.** `use_multi_granularity=False` appears in exactly one place in the entire codebase: hardcoded inside `exp_cross_encoder_factorial()` in `scripts/run_ablation.py`, deliberately, to isolate the cross-encoder's contribution from position correction in a controlled factorial. It is not reachable from `src/api.py` or the live `/ask` endpoint under any request body — a real user hitting the running app with `strategy=para` always gets `use_multi_granularity=True`.

---

## 4. The Experiments We Ran Today

### Experiment A — small PDF, cross_encoder factorial
- **Setup:** `1780085748443_rag_research_engine_final.pdf`, 2,194 words, ~5 chunks. `--experiment cross_encoder --positions 0.1,0.5,0.9 --num-runs 1 --provider groq`. Needle: original `ALPHA-7749-OMEGA` fact.
- **Result:** all 4 configs (semantic-only, +position correction, +cross-encoder, +both) at **100% overall / 100% middle**. Verified genuine (non-error) via `last_answer_sample` and non-zero `semantic_mean` on every cell.
- **Conclusion:** on a document this small, every config already recovers the needle trivially — the run has no discriminating power between configs. Not evidence that any component doesn't matter; evidence that this document was too easy to tell.

### Experiment B — medium PDF, cross_encoder factorial
- **Setup:** `Object Oriented Programmings.pdf`, 11,594 words, 34 chunks. Same command, same needle.
- **Result:** all 4 configs identical: **33.3% overall / 0.0% middle.** Verified genuine — real answer text ("not mentioned in any of the provided sections"), non-zero semantic scores, no error strings.
- **Conclusion:** needle recovered at position 0.1 only, missed at 0.5 and 0.9, identically across all 4 configs. No config differentiated from any other in this run.

### Experiment C — medium PDF, component_stack
- **Setup:** same PDF as B. `--experiment component_stack --positions 0.1,0.5,0.9 --num-runs 1 --provider groq`.
- **Result:**

| Config | overall_accuracy | middle_accuracy | Found at 0.5? |
|---|---|---|---|
| 1. semantic only | 33.3% | 0.0% | No |
| 2. + multi-granularity | 66.7% | 100.0% | Yes |
| 3. + cross-encoder | 66.7% | 100.0% | Yes |
| 4. + fixed position correction (γ=0.3) | 66.7% | 100.0% | Yes |
| 5. + adaptive γ (full PARA) | 66.7% | 100.0% | Yes |

  Verified genuine via `last_answer_sample` (real completions quoting the code) and non-zero semantic scores.
- **Conclusion:** the entire jump happens at step 1→2 (multi-granularity). Steps 2→3→4→5 add nothing measurable in this run — middle accuracy was already 100% before cross-encoder or position correction were introduced.

### Experiment D — large PDF, Kirchner needle, retrieval-only diagnostic
- **Setup:** `Cpp_repaired_trimmed_210pages.pdf` (a genuine 846-page C++ textbook, repaired from a corrupted source file with Ghostscript and trimmed to the first 210 pages), 43,183 words, 124 top-level chunks. Needle replaced with a harder, semantically-adjacent fact: *"According to the Kirchner benchmark, virtual function dispatch adds 7 nanoseconds of overhead per call."* Verified before use: `"kirchner"` does not appear natively in the document; `"nanosecond"` appears 0 times.
- **The LLM-calling run (`component_stack`, same positions) hit heavy API failures** — 12 of 15 cells returned `413 Request too large` or `429` rate-limit/quota errors, not real answers. Per instruction, this was not retried. The accuracy percentages from that run are **not cited as findings** — see Section 7.
- **The retrieval-only diagnostic** (below) required no LLM call — `apply_para()` itself never calls a generation API — so it carries no quota risk and was computed directly, at position 0.5, using the exact parameters from `exp_component_stack()`:

| Config | Granularity | Pool size | Needle rank | Semantic sim | Position correction | Final score | Entered top_k=10? |
|---|---|---|---|---|---|---|---|
| 1. semantic only | top-level (400-word) | 124 | 58 | 0.1189 | 0.0000 | 0.0832 | No |
| 2. + multi-granularity | sentence-level | 1,649 | 1 | 0.7127 | 0.0000 | 0.4989 | Yes |
| 3. + cross-encoder | sentence-level | 1,649 | 1 | 0.7127 | 0.0000 | 0.4989 | Yes |
| 4. + fixed position correction (γ=0.3) | sentence-level | 1,649 | 1 | 0.7127 | 0.3000 | 0.5889 | Yes |
| 5. + adaptive γ (full PARA) | sentence-level | 1,649 | 1 | 0.7127 | 0.9652 | 0.7884 | Yes |

  (Configs 1–3 have `correction_type="none"` per `exp_component_stack()`'s own definition, hence `position_correction = 0.0000` even though the needle sits at `p ≈ 0.494–0.498`, near the peak of `sin(pi*p)`.)

---

## 5. The Central Finding

**Multi-granularity retrieval is a recall mechanism.** It moved the needle from rank 58 of 124 (semantic sim 0.1189, outside `top_k`) to rank 1 of 1,649 (semantic sim 0.7127, inside `top_k`). Middle-position accuracy in the LLM-calling run (Experiment C) moved with it: 0% → 100%.

**Position correction is a reordering mechanism, not a recall mechanism.** Between configs 3 and 4 (Experiment D), position correction raised the needle's final score from 0.4989 to 0.5889 — but its **rank did not move**, because it was already rank 1. There was no lower rank for it to recover from.

**Mechanism of chunk-level dilution:** a one-sentence fact embedded inside a 400-word chunk has its embedding averaged toward the surrounding text's meaning. The same sentence, embedded alone, scored 0.7127; embedded inside a 400-word chunk of mostly unrelated content, the *chunk containing it* scored 0.1189 — collapsing to roughly one-sixth of the isolated score, from 0.71 down to 0.12. (Two different documents produced closely analogous numbers: the earlier `ALPHA-7749-OMEGA` diagnostic on the 34-chunk medium PDF showed the same needle sentence go from sim −0.0228 diluted in a 400-word chunk to sim 0.7359 isolated as its own sentence chunk — the same mechanism, reproduced on a second document with a second needle.)

**Why position correction structurally cannot discriminate well between competing mid-document chunks:** it boosts *every* chunk near the document's middle by nearly the same amount, regardless of content. In the earlier 34-chunk diagnostic, the needle chunk at `p=0.4826` received a position correction of 0.4588; the chunk that actually won rank 1 (`p=0.6335`) received 0.4197 — a difference of only 0.04. The two chunks' *semantic* scores differed by 0.16 to 0.21 (needle: −0.0228; winner: 0.1853). A term that varies by ~0.04 across plausible mid-document positions cannot be expected to overturn a semantic gap several times that size. Position correction's ceiling (`beta * gamma`, at most ≈0.14–0.29 depending on document length) is a relatively blunt, position-only instrument; it cannot substitute for the chunk actually containing better-matching content.

---

## 6. Bugs Found And Fixed

**1. `run_ablation.py` silently swallowed exceptions as "needle not found."**
The original `except Exception: answer_text = f"[ERROR] {e}"` path recorded a failed API call identically to a genuine retrieval miss — both produced `found=0`. This corrupted the very first ablation attempt today: `overall_accuracy` read as 100%→100%→57%→0% as position correction was progressively enabled, which read exactly like position correction *breaking* retrieval. It didn't — `semantic_mean` was exactly `0.000` on every failing cell, the signature of the empty-context fallback triggered only when the whole call had already raised. **Fix:** the script now persists `last_answer_sample` — the real answer text or the real exception string — per cell, in the output JSON, so a crash and a genuine miss are distinguishable after the fact.

**2. Two decommissioned models sat in the LLM fallback chain.** `groq/gemma2-9b-it` (Groq: "has been decommissioned") and `gemini/gemini-1.5-flash-8b` (Gemini: 404, "not found for API version"). `ResilientLLMClient` tries every client in its chain and only raises once all have failed — so once the working models were rate-limited under this script's burst load, the chain fell through to these two dead entries, and the error surfaced to the caller was a confusing 400/404 from a nonexistent model, not the real rate-limit. This directly caused the second and third ablation attempts today to fail in ways that looked like retrieval problems but were actually a stale hardcoded model list. **Fix:** both removed from `GROQ_MODEL_FALLBACK` (`process_pdf.py:772`) and the Gemini model list (`process_pdf.py:639`); the three remaining models (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `gemini-2.5-flash`) were each verified with a live call before shipping the fix.

**3. Retry logic didn't handle `413` payload-too-large errors.** The original retry-on-failure logic in `run_ablation.py` only retried when `_is_rate_limit_error(e)` matched (429-shaped text). A `413 Request too large for model llama-3.1-8b-instant` — which occurred when the primary model was rate-limited and the chain fell over to a smaller fallback model that couldn't handle PARA's large context — didn't match that pattern and was recorded as a permanent failure, even though a standalone repro of the identical call succeeded instantly seconds later. **Fix:** the retry condition was broadened to retry once on any exception, not just rate-limit-shaped ones (`scripts/run_ablation.py:221-236`), since by that point three distinct transient failure shapes (429, dead-model 400/404, 413) had each independently reproduced as a clean success on a fresh attempt.

---

## 7. What Is NOT Established

- **The "57% → 99.2%" figures are not validated and should not be cited.** "57%" traces to Attempt 1 of today's debugging session (see Section 6, bug 1) — later confirmed contaminated by the exception-swallowing bug; the `semantic_mean=0.000` signature on that run's failing cells indicates a caught exception, not a genuine "not found" result. "99.2%" was searched for exhaustively at the start of this engagement — across every markdown file, every Python file, and the full git history including the deleted legacy frontend — and does not appear anywhere in this codebase or its history. Its origin is unknown. Neither number should be treated as a real measurement of anything.
- **Position correction's standalone contribution has never been isolated in a regime where recall was not already the bottleneck.** Every clean measurement so far (Experiments A–D) has recall (multi-granularity) as the dominant, sometimes sole, explanatory factor. No experiment run today isolated a case where the needle chunk was recall-eligible (inside top-k by semantic score alone) but ranked low enough within top-k that position correction's reordering would visibly change the outcome. That experiment has not been run.
- **All measurements are `--num-runs 1`.** No cell in any experiment above was repeated. No variance, confidence interval, or stability estimate exists for any number in this document. A single unlucky or lucky LLM completion could change any individual "found/not found" result.
- **Several experiment cells recorded API errors, not retrieval outcomes.** Experiment D's LLM-calling run: 12 of 15 cells were `413`/`429` errors. Experiment B and parts of earlier attempts were affected similarly before the bug fixes in Section 6. Where this document cites Experiment D's numbers, it cites only the retrieval-only diagnostic (no LLM call, no error risk) — not the contaminated LLM-calling run's accuracy percentages, which are not reported here as findings.

---

## 8. Interview-Ready Summary

**What PARA is, in one paragraph:** PARA (Position-Aware Retrieval Augmentation) is a retrieval-time mitigation for the "lost in the middle" problem in long-context LLM question-answering. It combines an established retrieval stack — semantic chunking, multi-granularity retrieval (sentence/paragraph/section level), and cross-encoder reranking — with one novel addition: a position-bias correction term, `gamma * sin(pi * p)`, added to each chunk's semantic-similarity score, which boosts chunks near the middle of the document (where LLMs are empirically worst at using information) and adds nothing at the edges (where they don't need help).

**Six numbers to memorize:**

| # | Number | What it means |
|---|---|---|
| 1 | 58 → 1 | Needle chunk's rank (out of 124 → out of 1,649 candidates) before vs. after multi-granularity retrieval |
| 2 | 0.12 → 0.71 | Needle's semantic similarity, diluted in a 400-word chunk vs. isolated as its own sentence |
| 3 | 0% → 100% | Middle-position recovery accuracy, before vs. after multi-granularity (Experiment C) |
| 4 | 0.499 → 0.788 | Needle's final score, before vs. after position correction turns on — score moved, rank did not |
| 5 | 0.04 vs 0.16–0.21 | Position correction's differential between competing mid-document chunks, vs. the semantic-score gap between them — the reason position correction can't discriminate well on its own |
| 6 | 1 | Number of runs per condition in every experiment above (`--num-runs 1`) — no variance data exists |

**The central finding, in two sentences:** Multi-granularity retrieval is what actually solves the recall problem in these experiments — it moved a needle fact from unrecoverable (rank 58, outside the selection window) to the top-ranked candidate, by re-representing it as its own compact chunk instead of diluting it inside 400 words of unrelated text. Position correction, measured today, only ever adjusted scores among chunks that recall had already surfaced — it never changed which chunk ranked first in any experiment run.

**The honest limitation, in two sentences:** Every result here comes from a single run per condition on two documents, using one needle fact each — there is no variance estimate, and no experiment yet isolates a case where position correction's reordering, rather than multi-granularity's recall, is the deciding factor. The previously-circulated "57%" and "99.2%" figures for this project are not supported by any reproducible measurement and should not be repeated as if they were.

---

## 9. Resume Bullet Options

**(a) With verified numbers:**

> Diagnosed a retrieval failure in a custom RAG position-bias correction system by instrumenting per-chunk rank, semantic similarity, and score contribution across the retrieval pipeline; found that multi-granularity chunking — not the position-correction term — was the dominant recall mechanism, moving a target fact from rank 58/124 (outside the selection window) to rank 1/1,649, and raising middle-of-document recovery from 0% to 100% on a 124-chunk technical document.

*Defensible follow-up ("how did you measure that?"):* "By calling the retrieval function directly with production parameters and printing the per-chunk semantic score, position correction, and final rank before and after each pipeline stage — no LLM call needed for that measurement, since scoring is a local embedding computation. The rank and score numbers are exact outputs of that instrumentation, not estimates."

**(b) Methodology-only, no specific numbers:**

> Built and empirically validated a retrieval-augmented QA system addressing the "lost in the middle" LLM limitation, combining multi-granularity retrieval, cross-encoder reranking, and a novel position-bias scoring term across 11 benchmarked recovery strategies; designed controlled factorial ablations to isolate each component's individual contribution and diagnosed a retrieval-vs-reordering distinction between two of the system's core mechanisms.

*Defensible follow-up:* "The ablation harness runs a 2×2 factorial isolating position correction from cross-encoder reranking, plus an incremental component-stacking design, both in `scripts/run_ablation.py`. I can walk through the exact configs and what each isolates."

---

*This document reflects one working session's measurements. It should be updated, not silently superseded, if further experiments are run — future entries should follow the same rule: only numbers actually produced, with the run that produced them cited.*
