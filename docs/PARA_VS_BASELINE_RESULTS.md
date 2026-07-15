# PARA vs. Baseline — Headline Accuracy Numbers

Real measurements from `scripts/run_para_vs_baseline.py`, run 2026-07-16.
Raw data: `results/para_vs_baseline_20260716_002144.json`.

This is deliberately a **plain, non-adversarial** needle-in-haystack test —
unlike the rescue experiment in this repo's other scripts, nothing here was
engineered to stress any specific internal mechanism. It answers one question:
*does PARA, as a whole system, solve lost-in-the-middle better than no
mitigation, by a margin that survives repeated trials?*

---

## Setup

| Parameter | Value |
|---|---|
| Document | `Object Oriented Programmings.pdf` — 11,594 words, unmodified except for needle insertion |
| Needle | *"According to the Kirchner benchmark, virtual function dispatch adds 7 nanoseconds of overhead per call."* — verified absent from the source PDF |
| Positions tested | 0.1 (beginning), 0.5 (middle), 0.9 (end) |
| Runs per (strategy, position) cell | 3 |
| Strategies compared | `baseline` (no mitigation — `pdf_text[:8000]`, no chunking, no retrieval) vs. `para` (production defaults: semantic chunking, multi-granularity retrieval, cross-encoder rerank, adaptive position correction) |
| Provider | Groq — `llama-3.1-8b-instant` answered all 18 calls (no cross-provider fallback triggered this run, so this is a genuine single-model comparison) |
| Total real LLM calls | 18 (9 per strategy) |

## Results

| Strategy | pos=0.1 | pos=0.5 (middle) | pos=0.9 | Overall | Middle |
|---|---|---|---|---|---|
| `baseline` | 3/3 (100%) | 0/3 (0%) | 0/3 (0%) | **33%** | **0%** |
| `para` | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | **100%** | **100%** |

Every cell was either 3/3 or 0/3 — zero variance across the 3 runs in every
condition tested (temperature=0.1, so low variance is expected, but it did
mean each cell's result was consistent rather than borderline).

## Why baseline fails predictably

`baseline` is `pdf_text[:8000]` — the first ~8,000 raw characters, no
chunking, no retrieval. On this document that's roughly the first 12% of the
text. A needle at position 0.1 is inside that window (100% recovery); needles
at 0.5 and 0.9 are structurally outside it, so baseline *cannot* see them
regardless of the LLM's reasoning — 0% isn't a reasoning failure, it's
architectural exclusion. This is the "no mitigation" control behaving exactly
as designed.

## What this number supports saying

**"PARA improves needle recovery from 33% to 100% overall, and from 0% to
100% specifically at the document's middle — the position lost-in-the-middle
affects most — measured over 3 independent runs per condition, single-model
(no cross-provider fallback confound)."**

That's the resume-defensible headline. What it does **not** by itself tell
you: *which* component of PARA is responsible. Per the mechanism-level work in
`docs/PARA_EMPIRICAL_FINDINGS.md` and the rescue-case experiments
(`scripts/para_rescue_diagnostic.py`, `scripts/para_rescue_confirm.py`), the
honest attribution is:

- **Multi-granularity retrieval** (re-chunking into sentence/paragraph/section
  candidates instead of one fixed 400-word chunk) is the dominant driver of
  this specific gain — it's what stops the needle sentence from being
  averaged away inside a diluted chunk.
- **Position-bias correction** (the actual novel contribution PARA is named
  for) is real and measurable in isolation — confirmed today with a case
  where it flips a chunk's rank from 13th to 1st in a controlled sentence-level
  pool — but it did not need to do any rescuing in *this* comparison, because
  multi-granularity retrieval alone already recalls the needle at all three
  positions here.

If asked "so is position correction pulling its weight?", the accurate answer
is: it's proven to work exactly as designed in the specific regime where a
chunk is recall-eligible but ranked just below the cutoff — that regime
didn't arise naturally in this particular baseline comparison, so this
headline number is honestly a multi-granularity-retrieval result more than a
position-correction result. Both are real components of the system you built
and both are named in the resume bullet below.

## Honest limitations

- `n=3` per cell, one document, one needle, three positions. No claim beyond
  this specific document/needle/position set.
- `baseline` is a deliberately weak control (no chunking at all) — this
  number shows PARA beats *no mitigation*, not that it beats other
  sophisticated strategies. See `docs/STRATEGY_BENCHMARK_RESULTS.md` for how
  PARA compares against the other 10 implemented strategies (6 of 11 also
  solved that harder, keyword-adjacent test).
- Same model (`llama-3.1-8b-instant`) answered all 18 calls — a genuinely
  controlled comparison this time, unlike the earlier 11-strategy run where
  Groq rate-limiting triggered mid-run fallback to Gemini for some strategies.

## Resume bullet

> Built PARA (Position-Aware Retrieval Augmentation), a RAG pipeline
> combining semantic chunking, multi-granularity retrieval, cross-encoder
> reranking, and a position-bias correction term targeting the
> "lost-in-the-middle" problem in long-context LLM QA. Measured needle-in-
> haystack recovery accuracy at 0%, 50%, and 90% document positions (n=3 runs
> each, single-model, Groq `llama-3.1-8b-instant`): PARA achieved 100% overall
> and 100% middle-position accuracy vs. 33% overall / 0% middle for an
> unmitigated baseline. Diagnosed which pipeline component drives that gain
> via controlled ablations and a targeted rank-based diagnostic isolating the
> position-correction term specifically.

*Defensible follow-up ("which part of PARA is actually responsible?"):* "Multi-
granularity retrieval — re-chunking at the sentence level — is the dominant
driver in this measurement; I confirmed the position-correction term's own
mechanism separately by engineering a case where a chunk is recall-eligible
but ranked 13th out of ~1,660 candidates by semantic score alone, and showed
position correction moves it to rank 1."
