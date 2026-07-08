# Lost in the Middle: Position-Aware Retrieval Augmentation for Long-Context LLMs

## Complete Research Reference Document

---

## 1. The Problem

Large Language Models have a documented flaw — they pay strong attention to the beginning and end of their context window but **ignore information placed in the middle**. This is known as the "Lost in the Middle" phenomenon (Liu et al., 2023).

```
EMPIRICAL ATTENTION PATTERN (U-shaped curve):

Accuracy
  100% |  *                                             *
   80% |   *                                          *
   60% |     *                                     *
   40% |       *     *     *     *     *     *   
   20% |          *     *     *     *     *
    0% |________________________________________________
       0%    10%   20%   30%   40%   50%   60%   70%  100%
                        Document Position

       |<-- HIGH -->|<------- DEAD ZONE ------->|<-- HIGH -->|
        (primacy)     (information lost here)      (recency)
```

**Key finding from Liu et al. 2023:** When relevant information is placed in the middle of a long context, LLM performance degrades by 10-30% compared to when the same information is at the beginning or end. This holds across GPT-3.5, GPT-4, Claude, and open-source models.

**Why this matters:** In real-world RAG (Retrieval-Augmented Generation) systems, retrieved documents are concatenated into a long context. The ordering of these documents directly impacts whether the LLM finds and uses the relevant information.

---

## 2. Our Solution: 11 Recovery Strategies

This project implements 11 distinct strategies to recover lost middle-document content. The novel contribution is **PARA** — Position-Aware Retrieval Augmentation.

### Strategy Overview Table

| # | Strategy | Core Idea | Novel? |
|---|----------|-----------|--------|
| 1 | Baseline | Standard RAG — no recovery (control) | No |
| 2 | Attention Anchoring | Insert `[CRITICAL - READ CAREFULLY]` markers on middle sections + question reminders | No |
| 3 | Relevance Restructuring | Score chunks by keyword relevance, place high-relevance at edges | No |
| 4 | Query-Aware Compression | Compress irrelevant chunks, keep relevant chunks full at edges | No |
| 5 | Query-Aware Contextualization | Place query BEFORE and AFTER all documents (Liu et al. 2023) | No |
| 6 | Chunked Reading | Process 3 chunks at a time, extract relevant info per batch | No |
| 7 | Reranking Prompt | Most relevant at first and last position, least in middle | No |
| 8 | Chunk-by-Chunk Reasoning | Force per-passage evaluation before synthesis, require citations | No |
| 9 | Map-Reduce | MAP: extract facts per chunk batch; REDUCE: synthesize answer | No |
| 10 | Combined | All prompt-based strategies merged together | No |
| **11** | **PARA (Position-Aware Retrieval)** | **Semantic embeddings + sinusoidal position-bias correction** | **Yes** |

---

## 3. PARA — The Novel Contribution

### 3.1 Core Formula

```
final_score_i = alpha * semantic_sim(query, chunk_i) + beta * gamma * sin(pi * position_i)
```

Where:
- `semantic_sim(query, chunk_i)` = cosine similarity between query embedding and chunk embedding
- `position_i` = normalized position of chunk in document (0.0 = start, 1.0 = end)
- `sin(pi * position_i)` = sinusoidal correction that peaks at 0.5 (middle) and is 0 at edges

### 3.2 Why Sinusoidal Correction?

The U-shaped attention pattern means LLMs already attend well to edges (positions 0.0 and 1.0) but poorly to the middle (position 0.5). The sinusoidal correction is the **mathematical inverse** of this problem:

```
Position Bias Correction: gamma * sin(pi * position)

Correction
  0.30 |                    *  *  *
  0.25 |                *            *
  0.20 |             *                  *
  0.15 |          *                        *
  0.10 |       *                              *
  0.05 |    *                                    *
  0.00 | *                                          *
       |________________________________________________
       0.0   0.1   0.2   0.3   0.4   0.5   0.6   0.7   1.0
                        Document Position

  - At position 0.0 (start): correction = 0 (LLM already attends here)
  - At position 0.5 (middle): correction = gamma = 0.3 (maximum boost)
  - At position 1.0 (end):   correction = 0 (LLM already attends here)
```

This correction **boosts the retrieval score of middle-positioned chunks** to counteract the attention deficit, without penalizing edge chunks.

### 3.3 Hyperparameters

| Parameter | Default | Role |
|-----------|---------|------|
| alpha | 0.7 | Weight for semantic similarity (content relevance) |
| beta | 0.3 | Weight for position-bias correction |
| gamma | adaptive | Peak amplitude (scales with document length) |
| top_k | 10 | Number of chunks to retrieve |
| model | all-MiniLM-L6-v2 | Sentence embedding model (22M params, 80MB) |

**Design rationale:**
- `alpha > beta` because content relevance should still dominate — we don't want to retrieve irrelevant middle chunks just because they're in the middle
- `gamma` is now **adaptive** (see 3.6 below) — longer documents get stronger correction
- `sin(pi * position)` chosen over step function for mathematical smoothness and zero-at-edges property

### 3.4 PARA Step-by-Step Algorithm

```
Input: query (string), document_chunks (list), alpha, beta, gamma, top_k

1. EMBED query using SentenceTransformer("all-MiniLM-L6-v2")
   → query_embedding (384-dimensional vector, L2-normalized)

2. EMBED all chunk contents
   → chunk_embeddings (n x 384 matrix, L2-normalized)

3. COMPUTE semantic similarity for each chunk:
   semantic_scores = chunk_embeddings @ query_embedding  (dot product = cosine sim)

4. COMPUTE position correction for each chunk:
   for each chunk_i with position p_i:
       correction_i = gamma * sin(pi * p_i)

5. COMPUTE final PARA score:
   final_score_i = alpha * semantic_scores_i + beta * correction_i

6. SORT chunks by final_score descending

7. SELECT top_k chunks

8. BUILD context string:
   - Query BEFORE retrieved sections (query-aware contextualization)
   - Each section with rank and relevance score
   - Query AFTER retrieved sections

9. RETURN (context_string, average_semantic_similarity_as_confidence)
```

### 3.5 Example: PARA in Action

Given a document with 7 chunks and query "What was the annual revenue?":

```
pos=  0%  final=0.252  semantic=0.359  pos_boost=0.000  | Introduction to the company...
pos= 10%  final=0.187  semantic=0.227  pos_boost=0.093  | The headquarters moved to Chicago...
pos= 30%  final=0.301  semantic=0.326  pos_boost=0.243  | Various marketing campaigns...
pos= 50%  final=0.540  semantic=0.642  pos_boost=0.300  | The annual revenue reached $45M... ← FOUND
pos= 60%  final=0.200  semantic=0.164  pos_boost=0.285  | Employee satisfaction scores...
pos= 80%  final=0.195  semantic=0.203  pos_boost=0.176  | New product launches...
pos=100%  final=0.215  semantic=0.308  pos_boost=0.000  | The board of directors...
```

**Key observations:**
- The revenue chunk at 50% (middle) is ranked **#1** with final_score=0.540
- Without position correction, it would score 0.642 * 0.7 = 0.449 (still highest, but barely)
- The position boost of 0.300 adds 0.3 * 0.300 = 0.090 to the final score
- Middle chunks (30%, 50%, 60%) all receive significant boosts
- Edge chunks (0%, 100%) receive zero boost — they don't need it

### 3.6 Adaptive Gamma — Position Correction Scales with Document Length

**Problem:** A fixed gamma=0.3 treats short and long documents the same, but longer documents have worse middle-attention drops.

**Solution:** Gamma scales logarithmically with the number of chunks:

```
gamma_adaptive = base_gamma * log(num_chunks) / log(10)

  5 chunks  → gamma = 0.210 (mild correction — short doc)
  10 chunks → gamma = 0.300 (default level)
  20 chunks → gamma = 0.390 (moderate correction)
  50 chunks → gamma = 0.510 (strong correction — long doc)
  100 chunks → gamma = 0.600 (heavy correction — very long doc)
```

**Why logarithmic?** The attention drop worsens sub-linearly with context length (Liu et al. 2023 found diminishing degradation beyond ~20 documents). A log scale matches this empirical behavior.

### 3.7 Semantic Chunking — Split at Topic Boundaries

**Problem:** Fixed-size chunking (every 400 words) cuts sentences and paragraphs in half, destroying semantic coherence. A fact like "Revenue was $45M in 2019" might be split across two chunks.

**Solution:** Use embedding similarity between consecutive paragraphs to detect topic changes:

```
Algorithm:
1. Split document into paragraphs
2. Embed all paragraphs with SentenceTransformer
3. For each consecutive pair (paragraph_i, paragraph_{i+1}):
   - Compute cosine similarity
   - If similarity < threshold (0.5) AND current chunk ≥ min_words (80):
     → Start new chunk (topic changed)
   - If current chunk > max_words (500):
     → Force split (chunk too large)
4. Each chunk contains complete, topically coherent paragraphs
```

**Result:** Chunks respect natural topic boundaries. Facts stay intact within a single chunk.

### 3.8 Multi-Granularity Retrieval — Three Levels Simultaneously

**Problem:** Paragraph-level retrieval sometimes misses a single key sentence (too coarse) or lacks surrounding context (too fine).

**Solution:** Retrieve at three granularity levels simultaneously and merge results:

```
Level 1: SENTENCE — individual sentences (~20-40 words)
         Best for: specific facts, numbers, names
         Example: "Revenue reached $45M in 2019."

Level 2: PARAGRAPH — natural paragraphs (~100-300 words)
         Best for: explanations, descriptions, context
         Example: The full revenue discussion paragraph

Level 3: SECTION — large sections (~500 words)
         Best for: complex topics that span paragraphs
         Example: The entire financial overview section

Merge algorithm:
1. Retrieve top-k from each level using PARA scoring
2. Combine all candidates
3. Deduplicate: if two chunks share >50% word overlap, keep higher-scored one
4. Return merged top-k
```

**Why it works:** A sentence-level hit on "Revenue was $45M" might have the highest semantic score, while a section-level hit provides the surrounding context. Both are included.

### 3.9 Cross-Encoder Reranking — Two-Stage Retrieval

**Problem:** PARA uses a bi-encoder (query and chunk encoded independently). This is fast but less accurate because the model never sees query+chunk together.

**Solution:** Two-stage pipeline:

```
Stage 1: Bi-encoder (PARA) — fast, retrieves top candidates
  - Encode query once, encode all chunks once
  - Cosine similarity + position correction
  - Select top-k candidates

Stage 2: Cross-encoder — accurate, reranks top candidates
  - Model: cross-encoder/ms-marco-MiniLM-L-6-v2
  - Input: (query, chunk) pairs — model sees both together
  - Produces relevance score per pair
  - Rerank top candidates by: 60% cross-encoder + 40% PARA score
```

**Why blend instead of replace?** The PARA score includes position-bias correction. A pure cross-encoder would lose this. Blending preserves position awareness while gaining cross-encoder accuracy.

### 3.10 Iterative Middle Probing — Self-Correcting Retrieval

**Problem:** Single-pass retrieval might still miss middle content. If the first answer has low confidence, we know something was probably missed.

**Solution:** A two-pass approach:

```
Pass 1: Standard PARA retrieval → answer + confidence
   If confidence ≥ 0.4: → return answer (good enough)
   If confidence < 0.4: → trigger Pass 2

Pass 2: Middle-focused re-probe
   1. Extract only middle chunks (positions 0.25 to 0.75)
   2. Run PARA again with boosted position weight (alpha=0.5, beta=0.5)
   3. Ask LLM specifically about middle content
   4. If new information found:
      → Merge with Pass 1 answer
      → Boost confidence by +0.2

Result: Two chances to find middle-document information
```

### 3.11 Answer Grounding Check — Verify Against Source

**Problem:** LLMs can hallucinate — generate plausible-sounding answers not actually supported by the retrieved content.

**Solution:** After generating an answer, verify it against the source chunks:

```
Algorithm:
1. Generate answer using PARA-retrieved context
2. Send grounding check prompt to LLM:
   "Given this CONTEXT and this ANSWER, is every claim in the answer
    supported by the context?"
3. LLM responds: GROUNDED / PARTIALLY GROUNDED / UNGROUNDED
4. Adjust confidence:
   - GROUNDED: no change
   - PARTIALLY GROUNDED: confidence -= 0.1
   - UNGROUNDED: confidence -= 0.3, add warning note to answer
```

**Why this matters for research:** Grounding verification provides a self-check mechanism that increases trust in the system's outputs. It also prevents the system from appearing to "recover" middle content when it's actually hallucinating.

---

## 4. Existing Strategy Algorithms (Detailed)

### 4.1 Attention Anchoring

**Idea:** Insert explicit markers and reminders to force LLM attention on middle sections.

```
Algorithm:
1. Split document into chunks
2. For each chunk at position i:
   - Add section marker: "SECTION {i}/{total}"
   - If chunk is within ±(total/4) of middle:
     → Add "[CRITICAL - READ CAREFULLY]" marker
3. At exact middle position:
   → Inject "REMINDER: Looking for answer to: {query}"
4. Wrap entire context with:
   - Opening: "READ ALL SECTIONS CAREFULLY"
   - Closing: "NOW ANSWER: {query}"
```

### 4.2 Relevance Restructuring

**Idea:** Exploit the U-shaped attention by placing relevant content at high-attention positions (edges).

```
Algorithm:
1. Score each chunk: relevance = keyword_match_score(query, chunk)
   - Exact word matches: +3.0 per word
   - Partial stem matches: +1.0 per word
   - Proximity bonus: +0.5 per co-occurring query word
   - Normalize to [0, 1]
2. Sort chunks by relevance (descending)
3. Place chunks alternately at left edge and right edge:
   - Rank 1 → position 0 (start)
   - Rank 2 → position N (end)
   - Rank 3 → position 1
   - Rank 4 → position N-1
   - ... (least relevant ends up in the middle)
```

### 4.3 Query-Aware Compression

**Idea:** Save tokens by compressing irrelevant chunks, keep relevant chunks at full length at edges.

```
Algorithm:
1. Score all chunks for relevance
2. Threshold = top 40% score value
3. Split into: relevant (≥ threshold) and less_relevant (< threshold)
4. Compress less_relevant chunks:
   - Batch 5 at a time
   - LLM prompt: "Compress to 1-2 sentences, keep anything related to {query}"
5. Layout:
   [FULL relevant chunks — first half]
   [COMPRESSED background sections]
   [FULL relevant chunks — second half]
```

### 4.4 Query-Aware Contextualization (Liu et al. 2023)

**Idea:** Place the query both before and after all documents so the LLM processes content with query awareness from the start.

```
Algorithm:
1. "QUESTION TO ANSWER: {query}"
2. "Read all the following document sections to find the answer:"
3. [All document sections with position markers]
4. "Based on ALL the document sections above, answer this question:"
5. "QUESTION: {query}"
```

**Why it works:** Standard RAG places the query only after the documents. By the time the LLM encounters the query, it has already processed (and partially forgotten) the documents. Placing the query first enables query-aware processing from the beginning.

### 4.5 Chunked Reading

**Idea:** Avoid the attention problem entirely by processing small batches of 3 chunks at a time.

```
Algorithm:
1. For each batch of 3 chunks:
   - LLM prompt: "Extract ONLY information relevant to: {query}"
   - If relevant info found → save it
   - If not → "No relevant information in this section"
2. Concatenate all extracted relevant information
3. Final LLM call: synthesize extracted information into answer
```

### 4.6 Reranking Prompt

**Idea:** Place most relevant chunks at positions 1 (primacy) and N (recency), least relevant in the middle.

```
Algorithm:
1. Score chunks by keyword relevance
2. Sort descending
3. Alternating edge placement:
   sorted[0] → position[left], left++
   sorted[1] → position[right], right--
   sorted[2] → position[left], left++
   ...
4. Include instruction: "Pay EQUAL attention to ALL passages regardless of position"
5. Require: "Before answering, identify which passages contain relevant information"
```

### 4.7 Chunk-by-Chunk Reasoning

**Idea:** Force the LLM to evaluate each passage individually before combining insights.

```
Algorithm:
1. Present all passages with position metadata
2. Instructions:
   Step 1: "Evaluate EACH passage individually — is it relevant?"
   Step 2: "Combine insights from ALL relevant passages"
   Step 3: "Cite passage numbers (e.g., [Passage 3])"
```

**Why it works:** Prevents the LLM from doing a quick scan and latching onto the first relevant-looking passage. Forces systematic evaluation.

### 4.8 Map-Reduce

**Idea:** Two-phase approach that processes every chunk independently, then synthesizes.

```
MAP Phase:
1. For each batch of 4 chunks:
   - "Extract any facts relevant to: {query}"
   - LLM outputs specific facts or "NONE"
2. Collect all extracted facts

REDUCE Phase:
3. "Using ONLY these extracted facts, answer: {query}"
4. LLM synthesizes final comprehensive answer
```

### 4.9 Combined

**Idea:** Apply multiple recovery techniques simultaneously for maximum coverage.

```
Algorithm (combines 4 techniques):
1. Score chunks by relevance → sort by (-relevance, position)
2. Add query-aware instruction at top: "QUESTION: {query}"
3. Mark high-scoring sections with [POTENTIALLY RELEVANT]
4. Insert question reminders every 3 sections
5. System prompt emphasizes: "LLMs tend to ignore middle content"
```

---

## 5. Document Processing Pipeline

### 5.1 PDF Extraction

```
Input: PDF file path
Process: PyPDF2 iterates all pages, extracts text, concatenates
Output: Full document text string
```

### 5.2 Chunking Algorithm

```
Parameters:
  - chunk_size = 400 words (default, configurable)
  - overlap = 50 words

Algorithm:
  i = 0, chunk_id = 0
  while i < total_words:
      chunk = words[i : i + chunk_size]
      position = i / total_words  (normalized 0.0 to 1.0)
      chunks.append(TextChunk(content, chunk_id, position))
      i += chunk_size - overlap  (step forward by 350 words)
```

**Position tracking:** Every chunk stores its normalized position (0.0 = document start, 1.0 = document end). This is critical for PARA's position-bias correction and for the attention curve analysis.

### 5.3 Relevance Scoring (Keyword-Based)

Used by: Relevance Restructuring, Query-Aware Compression, Reranking, Combined.

```
Algorithm (_compute_relevance_score):
1. Extract query words (remove 50+ stopwords, words must be >2 chars)
2. For each query word:
   - Exact word boundary match: +3.0
   - Partial stem match (first 4 chars): +1.0
3. Bonus: if ≥2 query words found in text: +0.5 per word
4. Normalize: score / (num_query_words * 4.0), capped at 1.0
```

### 5.4 Semantic Scoring (PARA)

Used by: PARA strategy only.

```
Algorithm:
1. Load SentenceTransformer("all-MiniLM-L6-v2") — cached after first load
2. Encode query → 384-dim normalized vector
3. Encode all chunks → n x 384 normalized matrix
4. Cosine similarity = dot product (since vectors are normalized)
5. Combine with sinusoidal position correction
```

---

## 6. Confidence Scoring

### Standard Strategies (Heuristic)

```
confidence = 0.85  (default)
if "not contain" or "cannot find" in response:
    confidence = 0.3
elif len(response) > 100 characters:
    confidence = 0.9
```

### PARA Strategy (Semantic)

```
confidence = average cosine similarity of top-k retrieved chunks
if "not contain" or "cannot find" in response:
    confidence = 0.15
```

PARA's confidence is more meaningful because it reflects how semantically close the retrieved content is to the query, rather than a fixed heuristic.

---

## 7. Needle-in-the-Haystack Benchmark

### Purpose
Empirically demonstrate the U-shaped attention drop and measure recovery effectiveness.

### Method

```
Needle fact: "The secret code for the research project is ALPHA-7749-OMEGA."
Needle question: "What is the secret code for the research project?"
Test positions: [10%, 25%, 40%, 50%, 60%, 75%, 90%]

For each position:
  1. Insert needle at that position in the document
  2. Run Baseline strategy → check if "7749" or "ALPHA" in answer
  3. Run Combined strategy → check if "7749" or "ALPHA" in answer
  4. Record: found/not-found for each strategy

Metrics:
  - Baseline accuracy: % of positions where baseline found the needle
  - Combined accuracy: % of positions where combined found it
  - Dead zone positions: where baseline failed but combined succeeded
  - Recovery rate: (successful recoveries) / (baseline failures)
```

### Expected Results

```
Position  | Zone      | Baseline | Combined | PARA
----------|-----------|----------|----------|------
10%       | Beginning | Found    | Found    | Found
25%       | Beginning | Found    | Found    | Found
40%       | Middle    | MISSED   | Found    | Found    ← Recovery
50%       | Middle    | MISSED   | Found    | Found    ← Recovery
60%       | Middle    | MISSED   | Found    | Found    ← Recovery
75%       | End       | Found    | Found    | Found
90%       | End       | Found    | Found    | Found
```

---

## 8. System Architecture

```
┌─────────────────────────────────────────────────────┐
│                 USER BROWSER                         │
│   ┌──────────┐  ┌──────────┐  ┌──────────────┐     │
│   │ Upload   │  │ Chat     │  │ Position     │     │
│   │ PDF      │  │ Interface│  │ Recovery Test│     │
│   └────┬─────┘  └────┬─────┘  └──────┬───────┘     │
│        │              │               │              │
└────────┼──────────────┼───────────────┼──────────────┘
         │              │               │
    ┌────▼──────────────▼───────────────▼──────┐
    │         NEXT.JS API ROUTES                │
    │  /api/upload  /api/ask  /api/benchmark    │
    │  /api/summarize  /api/compare             │
    │  /api/kv-retrieval                        │
    └──────────────────┬────────────────────────┘
                       │ child_process.exec
    ┌──────────────────▼────────────────────────┐
    │         process_pdf.py (Python)            │
    │                                            │
    │  ┌──────────────────────────────┐          │
    │  │  MiddleRecoveryProcessor      │          │
    │  │  ├─ apply_attention_anchoring │          │
    │  │  ├─ apply_relevance_restr...  │          │
    │  │  ├─ apply_chunked_reading     │          │
    │  │  ├─ apply_query_aware_comp... │          │
    │  │  ├─ apply_query_aware_ctx...  │          │
    │  │  ├─ apply_reranking           │          │
    │  │  ├─ apply_chunk_by_chunk...   │          │
    │  │  ├─ apply_map_reduce          │          │
    │  │  ├─ apply_combined_strategy   │          │
    │  │  └─ apply_para ──────────────────┐      │
    │  └──────────────────────────────┘    │      │
    │                                      │      │
    │  ┌──────────────────────────────┐    │      │
    │  │  LLMClient                    │    │      │
    │  │  ├─ Groq (Llama 3.3 70B)     │    │      │
    │  │  ├─ OpenAI (GPT-4o)           │    │      │
    │  │  └─ Anthropic (Claude)        │    │      │
    │  └──────────────────────────────┘    │      │
    └──────────────────────────────────────┼──────┘
                                           │
    ┌──────────────────────────────────────▼──────┐
    │  src/para.py (PARARetriever)                 │
    │  ├─ SentenceTransformer (all-MiniLM-L6-v2)  │
    │  ├─ Semantic similarity scoring              │
    │  ├─ Sinusoidal position-bias correction      │
    │  └─ Top-k retrieval with PARA formula        │
    └──────────────────────────────────────────────┘
```

---

## 9. LLM Provider Configuration

| Provider | Default Model | API Base | Rate Limit | Free Tier |
|----------|---------------|----------|------------|-----------|
| Groq | llama-3.3-70b-versatile | api.groq.com/openai/v1 | ~30 req/min | Yes |
| OpenAI | gpt-4o | api.openai.com | ~500 req/min | No |
| Anthropic | claude-sonnet-4 | api.anthropic.com | ~300 req/min | No |

Groq has automatic fallback: if llama-3.3-70b is rate-limited, it falls back to llama-3.1-8b-instant, then gemma2-9b-it.

All providers are accessed through a unified `LLMClient` class with rate limiting built in.

---

## 10. What Makes This Research-Worthy

### 10.1 What's Actually Novel: The sin(π·p) Correction Term

**Honest framing.** PARA has seven components. **One is novel. Six are prior art that we integrate as a retrieval testbed.** This matters because reviewers will immediately spot over-claiming.

**The novel contribution:**
- **Sinusoidal position-bias correction** (§3.1–3.2): `γ · sin(π · position)` added to the retrieval score. To our knowledge, no prior retrieval method adds an explicit, closed-form position-bias correction whose shape matches the inverse of the empirical Lost-in-the-Middle attention curve.
- **Adaptive γ scaling** (§3.6): `γ = 0.3 · log₁₀(n_chunks)`. Scales correction strength with document length.

**The six prior-art components (integrated as testbed):**

| Component | Prior Art | Role in PARA |
|-----------|-----------|--------------|
| Semantic chunking (§3.7) | Kamradt (2023) semantic chunker; Sarthi et al. RAPTOR (ICLR 2024) | Chunking backend |
| Multi-granularity retrieval (§3.8) | Sarthi et al. RAPTOR (ICLR 2024); ProposalQA / hierarchical RAG | Retrieval unit selection |
| Cross-encoder reranking (§3.9) | Reimers & Gurevych SBERT (EMNLP 2019); Nogueira et al. monoBERT (2020); ms-marco-MiniLM model card | Second-stage rerank |
| Iterative retrieval (§3.10) | Asai et al. Self-RAG (ICLR 2024); Yan et al. CRAG (2024) | Low-confidence re-probe |
| Answer grounding (§3.11) | Zheng et al. LLM-as-judge (NeurIPS 2023); Es et al. RAGAS (2024) | Confidence calibration |
| Bi-encoder semantic retrieval | Karpukhin et al. DPR (EMNLP 2020); Reimers & Gurevych (2019) | Base retrieval |

We cite all of these in §2 (Related Work). Our contribution claim is narrow: **the sin(π·p) term, when added to an otherwise-standard RAG pipeline, measurably reduces middle-position retrieval failures.** Everything else in the pipeline is the competitive baseline we build on top of.

### 10.2 Defensible Claim (Moderate Framing)

> *"We propose a position-aware retrieval score that augments bi-encoder similarity with a sinusoidal position-bias correction, γ·sin(π·p), and show that adding this single term to otherwise-standard dense retrieval improves middle-document retrieval on the NaturalQuestions-Open Lost-in-the-Middle benchmark of Liu et al. (2024)."*

This claim is defensible if (and only if) we run the experiments in §11 below. If we don't, fall back to the **conservative framing**: a case-study tech report at a workshop.

### 10.3 Practical System

Orthogonal to the research claim, we provide a working web UI that:
- Lets practitioners try all 11 strategies on real PDFs
- Visualizes the U-shaped attention curve per document
- Supports multi-provider LLM access (Groq, Gemini, OpenAI, Anthropic) with automatic failover — useful as a reference implementation regardless of the research contribution.

---

## 11. Suggested Paper Structure

```
Title: "PARA: Position-Aware Retrieval Augmentation for Recovering
        Lost-in-the-Middle Information in Long-Context LLMs"

Abstract:
  - Problem: LLMs ignore middle content (U-shaped attention)
  - Solution: PARA — semantic retrieval + sinusoidal position correction
  - Key result: PARA recovers middle content that baseline approaches miss

1. Introduction
   - The Lost-in-the-Middle problem (Liu et al. 2023)
   - Why existing RAG is position-blind
   - Our contribution: PARA

2. Related Work
   - Liu et al. 2023 — original LitM paper
   - RAG systems (Lewis et al. 2020, etc.)
   - Long-context methods (extending context windows)
   - Prompt engineering for attention (markers, reordering)

3. Method
   3.1 Problem Formulation
       - U-shaped attention as function of document position p ∈ [0,1]
       - Why retrieval scoring should be position-aware
   3.2 Position-Aware Retrieval Score (the contribution)
       - Standard bi-encoder similarity baseline
       - Sinusoidal position-bias correction: γ · sin(π·p)
       - Why sin: zero at edges (0,1), single peak at 0.5, smooth, 1 hyperparam
       - Adaptive γ: γ = 0.3 · log₁₀(n_chunks)
   3.3 Pipeline Integration (the testbed)
       - We integrate the correction term into a standard RAG pipeline:
         semantic chunking (Kamradt 2023, Sarthi et al. 2024),
         multi-granularity retrieval (RAPTOR 2024),
         cross-encoder reranking (Reimers & Gurevych 2019; Nogueira 2020),
         iterative refinement (Self-RAG 2024; CRAG 2024),
         grounding verification (Zheng 2023; RAGAS 2024)
       - Each component is cited as prior art; they serve as the competitive
         baseline on top of which we measure the correction's marginal effect.

4. Experimental Setup
   4.1 Primary: Liu et al. 2024 NQ-Open Replication
       - Multi-document QA with 10, 20, 30 documents per query
       - 500 queries per condition from NaturalQuestions-Open
       - Gold-document placed at positions {1, 5, 10, 15, 20, ...}
       - Metrics: Exact Match, token F1, best-answer position found
   4.2 Secondary: Needle-in-the-Haystack Diagnostic
       - 21 positions (5%, 10%, ..., 95%) for finer-grained analysis
       - Binary found/not-found
   4.3 Models
       - Primary: Llama-3.3-70B (Groq), Gemini-2.5-Flash
       - Cross-model: GPT-4o, Claude (for generality claim)

5. Results
   5.1 Main Result — Table 1 (NQ-Open Multi-Doc QA)
       - F1 and EM for baseline vs baseline+sin(π·p), across 10/20/30 docs
       - Gain attributed to the correction term alone
   5.2 Why sin(π·p)? — Table 3 (Correction Function Ablation)
       - sin vs Gaussian vs triangle vs step vs none
       - Addresses reviewer objection 2 (§11a)
       - Produced by scripts/run_ablation.py --experiment correction_function
   5.3 Is it really the correction? — Table 2 (2×2 Factorial)
       - semantic-only / +position / +cross-encoder / +both
       - Marginal gain of position correction with and without cross-encoder
       - Addresses reviewer objection 3 (§11a)
       - Produced by scripts/run_ablation.py --experiment cross_encoder
   5.4 Attention Curve Diagnostic — Figure 2
       - Per-position accuracy, baseline vs +correction
       - Shows where the correction helps most (middle positions)

6. Analysis
   6.1 Where the gain comes from (breakdown by position zone)
   6.2 When the correction hurts (edge-heavy queries, small documents)
   6.3 Sensitivity to γ (gamma sweep, fixed vs adaptive)
   6.4 Failure modes and limitations

7. Conclusion
   - PARA addresses position-blindness in RAG
   - Practical system for real-world document QA
   - Future: adaptive gamma, cross-document retrieval

References
```

---

## 11a. Anticipated Reviewer Objections & Rebuttals

These are the objections we expect and the evidence we need to defend against each. Items marked **[MUST RUN]** are experiments that still need to be executed.

### Objection 1 — "Only the sin(π·p) term is novel. The rest is engineering."

**Rebuttal.** We are explicit throughout the paper that the novel contribution is the sinusoidal position-bias correction (§3.1–3.2) and its adaptive amplitude (§3.6). The remaining five components are established techniques (Kamradt 2023; Sarthi et al. 2024; Reimers & Gurevych 2019; Asai et al. 2024; Zheng et al. 2023 — see §2) included as the retrieval testbed. We are not claiming to invent semantic chunking, cross-encoder reranking, or RAG self-correction; we are claiming that adding one well-motivated term to this standard stack measurably improves middle-document retrieval.

### Objection 2 — "Why sin(π·p) and not a Gaussian, step, or learned correction?"

**Rebuttal.** Table 3 (correction-function ablation) reports five correction shapes on the same benchmark: sin(π·p), Gaussian(μ=0.5, σ=0.2), triangle, step(0.25≤p≤0.75), and none. All three smooth corrections (sin, Gaussian, triangle) reduce middle-position failures. sin is within X F1 of the best while having three properties we want: zero at p∈{0,1} so edge chunks are unaffected, single smooth peak at p=0.5 matching Liu et al. (2024) Figure 3, and one hyperparameter. A learned correction is a natural extension we discuss in §6. **[MUST RUN]** `scripts/run_ablation.py --experiment correction_function`

### Objection 3 — "The cross-encoder is doing all the work."

**Rebuttal.** Table 2 (cross-encoder × position factorial) reports four configurations: (i) semantic-only baseline, (ii) +position correction, (iii) +cross-encoder, (iv) +both (full PARA). The marginal gain from adding position correction is X points in (ii) vs (i) and Y points in (iv) vs (iii). The effect is smaller but nonzero when the cross-encoder is present, showing the two mechanisms address different failure modes. **[MUST RUN]** `scripts/run_ablation.py --experiment cross_encoder`

### Objection 4 — "7 needle positions on 1 document is anecdotal."

**Rebuttal.** Our primary evaluation (§4.1) is exactly Liu et al. (2024)'s multi-document QA setup on NaturalQuestions-Open with 10, 20, and 30-document conditions, 500 queries per condition. The single-needle probe (§4.2) is retained as a secondary diagnostic because it enables finer per-position analysis (21 positions vs Liu's 10). **[MUST RUN]** — this is the Stage 2(a) experiment.

### Objection 5 — "Relationship to Self-RAG, CRAG, LongRAG?"

**Rebuttal.** Self-RAG and CRAG address retrieval quality via learned critics and query reformulation respectively; neither models document position. LongRAG (Jiang et al. 2024) uses a long-context reader with coarse retrieval units but does not correct for position bias within retrieved chunks. Our contribution is orthogonal — the sin(π·p) correction can be applied on top of any of these methods. §2 covers this explicitly.

---

## 11b. Ablation Protocol

All ablations are reproducible via `scripts/run_ablation.py`. The script exposes three pre-defined experiments:

### (A) Correction-function ablation (Objection 2)

```bash
python scripts/run_ablation.py \
    --pdf data/uploads/paper.pdf \
    --experiment correction_function \
    --positions 0.05,0.15,0.25,0.35,0.45,0.5,0.55,0.65,0.75,0.85,0.95 \
    --num-runs 3 \
    --provider groq
```

Compares **sin, Gaussian, triangle, step, none** with all other PARA components held constant. Reports needle-found rate per position, overall accuracy, and middle-zone accuracy. Total LLM calls: 5 configs × 11 positions × 3 runs = 165.

### (B) Cross-encoder 2×2 factorial (Objection 3)

```bash
python scripts/run_ablation.py \
    --pdf data/uploads/paper.pdf \
    --experiment cross_encoder \
    --num-runs 3 \
    --provider groq
```

Four configs: semantic-only, +position, +cross-encoder, +both. Isolates marginal contribution of the correction term with and without cross-encoder reranking.

### (C) Component stack ablation (for Table 2)

```bash
python scripts/run_ablation.py \
    --pdf data/uploads/paper.pdf \
    --experiment component_stack \
    --num-runs 3 \
    --provider groq
```

Five incremental configs: semantic-only → +multi-granularity → +cross-encoder → +fixed-γ correction → +adaptive-γ (full PARA). Shows the marginal F1 contribution of each component in turn.

### Runtime budget (Groq free tier, 30 req/min)

| Experiment | LLM calls | Est. time |
|-----------|-----------|-----------|
| (A) correction function, 11 pos × 5 cfg × 3 runs | 165 | ~12 min |
| (B) cross-encoder 2×2, 7 pos × 4 cfg × 3 runs | 84 | ~6 min |
| (C) component stack, 7 pos × 5 cfg × 3 runs | 105 | ~8 min |

With auto-fallback to Gemini, effective throughput is ~45 req/min. If Groq is unavailable, Gemini 2.5 Flash handles the full load at roughly the same rate.

---

## 12. Key References

### Primary motivation
1. **Liu, N. F. et al. (2024).** *Lost in the Middle: How Language Models Use Long Contexts.* TACL 12:157–173. The foundational U-shaped attention paper. Motivates the sin(π·p) correction.

### Retrieval-Augmented Generation
2. **Lewis, P. et al. (2020).** *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* NeurIPS 2020. Original RAG framework.
3. **Karpukhin, V. et al. (2020).** *Dense Passage Retrieval for Open-Domain Question Answering.* EMNLP 2020. DPR — the bi-encoder dense retrieval baseline PARA builds on.

### Components we use as prior art (MUST be cited in §2 Related Work)
4. **Reimers, N. & Gurevych, I. (2019).** *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.* EMNLP 2019. The `sentence-transformers` backbone for all-MiniLM-L6-v2.
5. **Nogueira, R. et al. (2020).** *Passage Re-ranking with BERT.* arXiv:1901.04085. Cross-encoder reranking (the two-stage retrieval pattern PARA uses).
6. **Kamradt, G. (2023).** *5 Levels Of Text Splitting.* Public notebook / LlamaIndex docs. The semantic-chunking technique PARA uses for topic-boundary splits.
7. **Sarthi, P. et al. (2024).** *RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval.* ICLR 2024. Multi-granularity / hierarchical retrieval.
8. **Asai, A. et al. (2024).** *Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection.* ICLR 2024. Self-correcting RAG (related to PARA's iterative middle probing).
9. **Yan, S.-Q. et al. (2024).** *Corrective Retrieval Augmented Generation.* arXiv:2401.15884. CRAG — another iterative/self-correcting RAG method we should contrast against.
10. **Jiang, Z. et al. (2024).** *LongRAG: Enhancing Retrieval-Augmented Generation with Long-context LLMs.* arXiv:2406.15319. Related long-context RAG; orthogonal contribution to PARA.

### Evaluation & benchmarks
11. **Kwiatkowski, T. et al. (2019).** *Natural Questions: a Benchmark for Question Answering Research.* TACL 7:453–466. NQ-Open — the benchmark Liu et al. (2024) use and which PARA must replicate.
12. **Pang, R. Y. et al. (2022).** *QuALITY: Question Answering with Long Input Texts, Yes!* NAACL 2022. Long-document multiple-choice QA benchmark.
13. **Es, S. et al. (2024).** *RAGAS: Automated Evaluation of Retrieval Augmented Generation.* EACL 2024. LLM-as-judge evaluation for RAG (PARA's grounding check is a simplified variant).
14. **Zheng, L. et al. (2023).** *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.* NeurIPS 2023. LLM-as-judge methodology.

### Long-context architecture (orthogonal but relevant)
15. **Press, O. et al. (2022).** *Train Short, Test Long: Attention with Linear Biases (ALiBi).* ICLR 2022. Position-aware attention (architectural approach vs. PARA's retrieval-time approach).
16. **Peng, B. et al. (2024).** *YaRN: Efficient Context Window Extension of Large Language Models.* ICLR 2024. Context-window extension method.

**Note for paper writing:** §2 Related Work must cite refs 4–10 explicitly, one sentence each, stating what PARA shares with and differs from each. Not citing them is the fastest way to invite Objection 1.

---

## 13. Project File Structure

```
RAG_RESEARCH_ENGINE/
├── process_pdf.py              # Main: all 11 strategies + CLI
├── requirements.txt            # Python dependencies
├── README.md                   # Quick start guide
├── RESEARCH_REFERENCE.md       # This file
├── .env                        # API keys (GROQ_API_KEY)
│
├── src/
│   ├── __init__.py
│   ├── para.py                 # PARA: semantic + position-bias retrieval
│   └── core/
│       ├── __init__.py
│       └── llm_client.py       # Unified LLM client (Groq/OpenAI/Anthropic)
│
├── data/uploads/               # Uploaded PDFs
├── scripts/run_ablation.py     # Ablation experiment runner
│
├── src/api.py                  # FastAPI HTTP layer (port 8000)
├── server/                     # Express.js API proxy (port 5000)
│   ├── index.js
│   └── routes/api.js
└── client/                     # React + Vite frontend (port 3000)
    └── src/
        ├── App.jsx
        └── components/         # ChatUI, Dashboard, StrategySelector
```
