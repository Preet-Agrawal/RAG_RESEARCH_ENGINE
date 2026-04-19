# RAG Research Engine — Complete Implementation Guide

End-to-end technical documentation of how the project is built and how it works.

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [System Overview](#2-system-overview)
3. [Project Structure](#3-project-structure)
4. [Setup & Configuration](#4-setup--configuration)
5. [Request Flow](#5-request-flow-how-a-question-becomes-an-answer)
6. [Python Backend Implementation](#6-python-backend-implementation)
7. [PARA Algorithm — Deep Dive](#7-para-algorithm--deep-dive)
8. [Enhanced Features](#8-enhanced-features)
9. [Next.js Frontend Implementation](#9-nextjs-frontend-implementation)
10. [LLM Providers & Auto-Fallback](#10-llm-providers--auto-fallback)
11. [Theme System](#11-theme-system)
12. [API Reference](#12-api-reference)
13. [How to Extend](#13-how-to-extend-the-project)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Quick Start

### Run the full stack

```bash
# Terminal 1 — ensure Python venv is activated and deps installed
cd /Users/manojkumawat/sd/RAG_RESEARCH_ENGINE
source venv/bin/activate
pip install -r requirements.txt

# Terminal 2 — start the web UI
cd web
npm install    # first time only
npm run dev
```

Then open **http://localhost:3000** (or 3001 if port is taken).

### Required API keys in `.env`

```bash
GROQ_API_KEY=gsk_...              # Primary (free — console.groq.com)
GEMINI_API_KEY=AIzaSy...           # Fallback (free — aistudio.google.com/apikey)
```

At least one of Groq or Gemini is required. When both are present, the system automatically fails over between them.

---

## 2. System Overview

### What the project does
Addresses the **"Lost in the Middle"** problem (Liu et al. 2023) where LLMs ignore information placed in the middle of long contexts. Implements **11 recovery strategies** including the novel **PARA** (Position-Aware Retrieval Augmentation).

### Two-process architecture

```
┌─────────────────────────┐           ┌──────────────────────────┐
│   Next.js Frontend      │           │   Python Backend          │
│   (React + Tailwind)    │  spawn    │   (process_pdf.py)        │
│                         ├──────────▶│                          │
│   - Upload UI           │  JSON out │   - PDF extraction        │
│   - Chat interface      │◀──────────┤   - 11 strategies         │
│   - Modals & charts     │           │   - PARA + enhancements   │
│                         │           │   - Multi-provider LLM    │
└─────────────────────────┘           └──────────────────────────┘
         localStorage                        sentence-transformers
         recharts                            PyPDF2, openai SDK
         Next.js 14 App Router               numpy, rouge-score
```

Next.js API routes shell out to `process_pdf.py` using `child_process.exec()`. This keeps the frontend lightweight and the heavy Python-based ML work isolated.

---

## 3. Project Structure

```
RAG_RESEARCH_ENGINE/
├── process_pdf.py              # Main orchestrator — all 11 strategies
├── requirements.txt
├── README.md
├── RESEARCH_REFERENCE.md       # Research/paper-oriented reference
├── IMPLEMENTATION.md           # THIS FILE
├── .env                        # API keys (gitignored)
├── .env.example                # Template
│
├── src/                        # Python package
│   ├── __init__.py
│   ├── para.py                 # PARA: semantic + position-aware retrieval
│   └── core/
│       ├── __init__.py
│       └── llm_client.py       # Multi-provider + ResilientLLMClient
│
├── data/
│   └── uploads/                # Uploaded PDFs stored here
│
├── venv/                       # Python virtual environment
│
└── web/                        # Next.js 14 App Router frontend
    ├── package.json
    ├── tailwind.config.ts
    ├── next.config.js
    │
    └── src/
        ├── app/
        │   ├── layout.tsx              # Root layout + theme init script
        │   ├── page.tsx                # Main page (sidebar + chat)
        │   ├── globals.css             # CSS variables for theming
        │   ├── icon.svg                # Favicon (auto-discovered)
        │   ├── apple-icon.svg          # iOS touch icon
        │   │
        │   └── api/                    # Next.js API routes
        │       ├── upload/route.ts     # POST — receive PDF
        │       ├── summarize/route.ts  # POST — analyze document
        │       ├── ask/route.ts        # POST — answer question
        │       ├── compare/route.ts    # POST — run all strategies
        │       ├── benchmark/route.ts  # POST — needle-in-haystack
        │       └── kv-retrieval/route.ts
        │
        ├── components/
        │   ├── Logo.tsx                # Focus Band SVG logo
        │   ├── ThemeToggle.tsx         # Light/dark switcher
        │   ├── PDFUploader.tsx         # Drag-drop upload
        │   ├── ChatInterface.tsx       # Message list + input
        │   ├── DocumentOverview.tsx    # Chunk summary view
        │   ├── ChatHistory.tsx         # Saved chats sidebar
        │   ├── EvaluationDashboard.tsx # Position Recovery Test
        │   ├── MarkdownRenderer.tsx    # Response rendering
        │   ├── SuggestedQuestions.tsx
        │   └── Toast.tsx
        │
        ├── types/
        │   └── index.ts                # TypeScript types + STRATEGIES array
        │
        └── lib/
            └── chatStorage.ts          # localStorage helpers
```

---

## 4. Setup & Configuration

### Python dependencies (`requirements.txt`)

```
openai>=1.12.0                        # OpenAI SDK — used for Groq & Gemini too
anthropic>=0.18.0                     # Optional: Anthropic Claude
python-dotenv>=1.0.0
PyPDF2>=3.0.0

sentence-transformers>=3.0.0,<4.0.0   # For PARA embeddings
numpy>=1.24.0,<2.0.0                  # Pinned <2 for torch 2.2 compatibility
```

### Node dependencies (`web/package.json` key deps)

```
"next": "14.1.0"
"react": "^18.2.0"
"react-dropzone": "^14.2.3"          # PDF drag-drop
"react-markdown": "^10.1.0"          # Render LLM responses
"rehype-highlight": "^7.0.2"         # Code syntax highlight
"axios": "^1.6.0"
"lucide-react": "^0.400.0"           # Icons
"recharts": "^3.x"                   # U-shaped attention chart
"tailwindcss": "^3.4.0"
```

### Environment variables (`.env`)

| Variable | Required | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | Preferred | Primary LLM (free tier, fast) |
| `GEMINI_API_KEY` | Preferred | Fallback LLM (free tier) |
| `OPENAI_API_KEY` | Optional | GPT-4o for cross-model tests |
| `ANTHROPIC_API_KEY` | Optional | Claude for cross-model tests |

At least one of Groq/Gemini must be set. When both exist, they back each other up.

---

## 5. Request Flow — How a Question Becomes an Answer

### Full lifecycle of a user question with PARA strategy

```
┌─ USER BROWSER ───────────────────────────────────────────────────┐
│                                                                    │
│  1. User types question, clicks Send                               │
│  2. ChatInterface → onSendMessage(question)                        │
│                                                                    │
└────────────────────────┬───────────────────────────────────────────┘
                         │ HTTP POST /api/ask
                         │ { question, filename, strategy: "para", provider: "groq" }
                         ▼
┌─ NEXT.JS API ROUTE (web/src/app/api/ask/route.ts) ────────────────┐
│                                                                    │
│  3. Validate strategy + provider                                   │
│  4. Build shell command:                                           │
│     $ python process_pdf.py <pdf_path> ask "<question>" para groq  │
│  5. execAsync() — 2 min timeout                                    │
│                                                                    │
└────────────────────────┬───────────────────────────────────────────┘
                         │ stdin/argv + stdout JSON
                         ▼
┌─ process_pdf.py main() ────────────────────────────────────────────┐
│                                                                    │
│  6. extract_text_from_pdf() — PyPDF2 reads all pages               │
│  7. answer_question(pdf_text, question, "para", "groq")            │
│     │                                                              │
│     ├─ get_llm_client("groq")                                      │
│     │   → _build_resilient_client(primary="groq")                  │
│     │     Chain: [Groq-70B, Groq-8B, Groq-Gemma, Gemini-2.5, Gemini-1.5] │
│     │                                                              │
│     ├─ processor.chunk_text_semantic(pdf_text)                     │
│     │   → src/para.py semantic_chunk_text()                        │
│     │     Splits at topic boundaries using embedding similarity    │
│     │                                                              │
│     ├─ processor.apply_para(chunks, question, full_text=pdf_text)  │
│     │   │                                                          │
│     │   ├─ PARARetriever(model="all-MiniLM-L6-v2")                 │
│     │   │   (model cached — loaded once per process)               │
│     │   │                                                          │
│     │   ├─ compute_adaptive_gamma(num_chunks)                      │
│     │   │   → gamma = 0.3 * log10(num_chunks)                      │
│     │   │                                                          │
│     │   ├─ For len(text) > 200 words:                              │
│     │   │   retrieve_multi_granularity()                           │
│     │   │   ├─ Sentence-level chunks                               │
│     │   │   ├─ Paragraph-level chunks                              │
│     │   │   └─ Section-level chunks                                │
│     │   │   → Score each with PARA, dedupe by overlap              │
│     │   │                                                          │
│     │   ├─ score_chunks(query, chunks, alpha=0.7, beta=0.3)        │
│     │   │   semantic = embed(query) @ embed(chunks)                │
│     │   │   position_boost = gamma * sin(pi * position)            │
│     │   │   final = alpha * semantic + beta * position_boost       │
│     │   │                                                          │
│     │   ├─ cross_encoder_rerank(top-5)                             │
│     │   │   Model: cross-encoder/ms-marco-MiniLM-L-6-v2            │
│     │   │   Blended: 60% cross-encoder + 40% PARA score            │
│     │   │                                                          │
│     │   └─ build_para_context() — formatted string                 │
│     │     Query before + top chunks + Query after                  │
│     │                                                              │
│     ├─ client.generate(prompt, system_prompt)                      │
│     │   ResilientLLMClient tries each provider in chain            │
│     │   On rate-limit/quota/auth error: instant failover           │
│     │                                                              │
│     ├─ IF confidence < 0.4: iterative_middle_probe()               │
│     │   1. Filter chunks to position 0.25-0.75                     │
│     │   2. Re-run PARA with alpha=0.5, beta=0.5                    │
│     │   3. Ask LLM "did you find new info in the middle?"          │
│     │   4. Merge answers, boost confidence                         │
│     │                                                              │
│     └─ answer_grounding_check()                                    │
│         "Are all claims in the answer supported by the context?"   │
│         If UNGROUNDED: reduce confidence, warn user                │
│                                                                    │
│  8. Return JSON: { answer, confidence, chunks_processed, ... }     │
│                                                                    │
└────────────────────────┬───────────────────────────────────────────┘
                         │ stdout JSON
                         ▼
┌─ NEXT.JS API ROUTE (back in ask/route.ts) ─────────────────────────┐
│                                                                    │
│  9. Parse JSON, return NextResponse.json({ ...camelCased })        │
│                                                                    │
└────────────────────────┬───────────────────────────────────────────┘
                         │ HTTP 200 + JSON
                         ▼
┌─ USER BROWSER ─────────────────────────────────────────────────────┐
│                                                                    │
│  10. ChatInterface receives response                               │
│  11. Streaming word-by-word render (4 words / 15ms)                │
│  12. After stream done: swap to MarkdownRenderer for rich display  │
│  13. Metadata badges: confidence, latency, chunks, strategy        │
│  14. Auto-save to localStorage                                     │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

**Typical latency:** 15–60 seconds for PARA on a 200-chunk PDF.

---

## 6. Python Backend Implementation

### 6.1 The `MiddleRecoveryProcessor` class

Located in `process_pdf.py`. Holds all 11 strategies as methods. Each strategy takes `(chunks, query)` and returns a prompt-ready context string.

```python
class MiddleRecoveryProcessor:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    # Chunking methods
    def chunk_text(self, text, chunk_size=500, overlap=50): ...       # Fixed-size
    def chunk_text_semantic(self, text): ...                          # Topic-boundary

    # 10 prompt-based strategies
    def apply_attention_anchoring(self, chunks, query): ...
    def apply_relevance_restructuring(self, chunks, query): ...
    def apply_query_aware_compression(self, chunks, query): ...
    def apply_query_aware_contextualization(self, chunks, query): ...
    def apply_chunked_reading(self, chunks, query): ...
    def apply_reranking(self, chunks, query): ...
    def apply_chunk_by_chunk_reasoning(self, chunks, query): ...
    def apply_map_reduce(self, chunks, query): ...
    def apply_combined_strategy(self, chunks, query): ...
    
    # 1 retrieval-based strategy (the novel one)
    def apply_para(self, chunks, query,
                    alpha=0.7, beta=0.3, gamma=None, top_k=10, full_text=None,
                    correction_type="sin",      # sin | gaussian | triangle | step | none
                    adaptive_gamma=True,
                    use_cross_encoder=True,
                    use_multi_granularity=True): ...

    # Per-strategy system prompt
    def get_system_prompt(self, strategy): ...
```

### 6.2 The `answer_question()` dispatcher

The entry point for all QA. Takes `(pdf_text, question, strategy, provider)` and dispatches to the right strategy implementation.

Key sections:
```python
def answer_question(pdf_text, question, strategy="combined", provider="groq", model=None):
    client = get_llm_client(provider, model)       # ResilientLLMClient
    processor = MiddleRecoveryProcessor(client)
    chunks = processor.chunk_text(pdf_text, chunk_size=400, overlap=50)

    if strategy == "baseline":
        context = pdf_text[:8000]                   # Control
    elif strategy == "attention_anchoring":
        context = processor.apply_attention_anchoring(chunks, question)
    # ... 8 more elif branches for each strategy ...
    elif strategy == "para":
        # Uses semantic chunking, adaptive gamma, multi-granularity,
        # cross-encoder, iterative middle probing, and grounding check
        # (see Section 7 for full detail)
    else:  # combined
        context = processor.apply_combined_strategy(chunks, question)

    response = client.generate(prompt, system_prompt=system_prompt)
    confidence = _compute_confidence(response, strategy)
    return {
        "answer": response.text,
        "confidence": confidence,
        "strategy_used": strategy,
        "chunks_processed": len(chunks),
        "latency": time.time() - start_time,
        ...
    }
```

### 6.3 CLI interface (`main()`)

```bash
python process_pdf.py <pdf_path> <action> [args...]

# Actions:
summarize                          # Summarize each chunk with zone labels
ask "<question>" [strategy] [provider]   # Default: combined, groq
compare "<question>"                # Run all strategies, rank by confidence
benchmark [needle_fact]             # Needle-in-the-haystack at 7 positions
kv_retrieval [num_pairs]           # Synthetic UUID key-value test
```

**Examples:**
```bash
# Ask with PARA using Groq (with Gemini auto-fallback)
python process_pdf.py paper.pdf ask "What are the main findings?" para groq

# Compare all strategies
python process_pdf.py paper.pdf compare "What are the main findings?"

# Run the needle benchmark
python process_pdf.py paper.pdf benchmark
```

All output is JSON to stdout — no formatted text. This is important because Next.js parses stdout directly.

---

## 7. PARA Algorithm — Deep Dive

### 7.1 The core formula

```
final_score_i = α · semantic_sim(q, c_i) + β · γ · sin(π · position_i)
```

Where:
- `semantic_sim(q, c_i)` = cosine similarity between query and chunk embeddings
- `position_i` ∈ [0, 1] = chunk's normalized position in document
- `α = 0.7` (semantic weight, default)
- `β = 0.3` (position correction weight, default)
- `γ` = adaptive — scales with document length

### 7.2 Why `sin(π · position)`?

This function peaks at position 0.5 (middle) and is zero at positions 0.0 and 1.0 (edges). It's the **inverse shape of the empirical U-curve** from Liu et al. 2023:

```
LLM attention (empirical)           Position correction (ours)
┌─────────────────┐                  ┌─────────────────┐
│ ▓           ▓   │                  │       ▓▓▓       │
│  ▓         ▓    │                  │     ▓     ▓     │
│   ▓       ▓     │                  │    ▓       ▓    │
│    ▓     ▓      │                  │   ▓         ▓   │
│     ▓   ▓       │                  │  ▓           ▓  │
│      ▓ ▓        │                  │ ▓             ▓ │
│       ▓         │                  │▓               ▓│
└─────────────────┘                  └─────────────────┘
0.0  0.5  1.0                        0.0  0.5  1.0
HIGH LOW  HIGH                       ZERO BOOST ZERO
```

Adding them recovers the drop in middle positions.

### 7.3 Adaptive gamma (γ)

```python
def compute_adaptive_gamma(num_chunks: int, base_gamma: float = 0.3) -> float:
    if num_chunks <= 1: return 0.0
    return base_gamma * math.log(num_chunks) / math.log(10)
```

| Document size (chunks) | Gamma | Effect |
|------------------------|-------|--------|
| 5 | 0.21 | Mild correction — short docs |
| 10 | 0.30 | Default baseline |
| 30 | 0.44 | Moderate |
| 100 | 0.60 | Heavy — long documents |

Rationale: The attention drop worsens sub-linearly with context length. Log scaling matches this behavior.

### 7.4 Step-by-step PARA algorithm (from `src/para.py`)

```python
def score_chunks(query, chunks, alpha=0.7, beta=0.3, gamma=None):
    # 1. Adaptive gamma based on document length
    if gamma is None:
        gamma = compute_adaptive_gamma(len(chunks))

    # 2. Embed query and chunks (normalized vectors)
    query_emb = model.encode([query], normalize_embeddings=True)[0]
    chunk_embs = model.encode([c.content for c in chunks], normalize_embeddings=True)

    # 3. Cosine similarity (dot product of normalized vectors)
    semantic_scores = chunk_embs @ query_emb

    # 4. Position correction per chunk
    pos_corrections = np.array([gamma * math.sin(math.pi * c.position) for c in chunks])

    # 5. Combined score
    final_scores = alpha * semantic_scores + beta * pos_corrections

    # 6. Sort descending and return
    return sorted(zip(chunks, final_scores, semantic_scores, pos_corrections),
                  key=lambda x: x[1], reverse=True)
```

### 7.5 Real example

Query: `"What was the annual revenue?"` on a 7-chunk document.

```
pos= 50%  final=0.540  semantic=0.642  pos_boost=0.300  ← #1 Revenue chunk (middle)
pos= 30%  final=0.301  semantic=0.326  pos_boost=0.243
pos=  0%  final=0.252  semantic=0.359  pos_boost=0.000
pos=100%  final=0.215  semantic=0.308  pos_boost=0.000
pos= 60%  final=0.200  semantic=0.164  pos_boost=0.285
pos= 80%  final=0.195  semantic=0.203  pos_boost=0.176
pos= 10%  final=0.187  semantic=0.227  pos_boost=0.093
```

The revenue chunk at 50% ranks #1 thanks to the position boost compensating for LLM attention decay.

---

## 8. Enhanced Features

PARA is augmented with 6 additional techniques. All are applied automatically when the user selects the `para` strategy.

### 8.1 Semantic Chunking

**Where:** `src/para.py:semantic_chunk_text()`

Splits text at **topic boundaries** using embedding similarity, not fixed word count.

```python
def semantic_chunk_text(text, similarity_threshold=0.5, min_chunk_words=80, max_chunk_words=500):
    paragraphs = split_by_blank_lines(text)
    embeddings = model.encode(paragraphs)
    
    chunks = []
    current = [paragraphs[0]]
    for i in range(1, len(paragraphs)):
        sim = cosine_similarity(embeddings[i-1], embeddings[i])
        if sim < similarity_threshold and word_count(current) >= min_chunk_words:
            chunks.append(join(current))  # Topic changed
            current = [paragraphs[i]]
        elif word_count(current) > max_chunk_words:
            chunks.append(join(current))  # Size guard
            current = [paragraphs[i]]
        else:
            current.append(paragraphs[i])
    
    return chunks
```

**Result:** Chunks respect natural topic breaks. A fact like "Revenue was $45M" stays in one chunk with its surrounding context.

### 8.2 Multi-Granularity Retrieval

**Where:** `src/para.py:retrieve_multi_granularity()`

Retrieves at 3 levels simultaneously — sentence, paragraph, section — then merges.

```python
def retrieve_multi_granularity(query, text, k_per_level=5):
    levels = {
        "sentence": split_sentences(text),      # ~20-40 words each
        "paragraph": split_paragraphs(text),    # ~100-300 words
        "section": split_sections(text, 500),   # ~500 words
    }
    
    all_candidates = []
    for level_name, level_chunks in levels.items():
        scored = score_chunks(query, level_chunks)
        all_candidates.extend(scored[:k_per_level])
    
    # Deduplicate by word overlap >50%
    return dedupe_by_overlap(all_candidates, threshold=0.5)
```

### 8.3 Cross-Encoder Reranking

**Where:** `src/para.py:cross_encoder_rerank()`

Two-stage retrieval: fast bi-encoder → accurate cross-encoder.

```python
def cross_encoder_rerank(query, scored_chunks, top_n=5):
    candidates = scored_chunks[:top_n]
    
    # Cross-encoder sees (query, chunk) as a PAIR — more accurate than
    # comparing independent embeddings
    cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    ce_scores = cross_encoder.predict([(query, c.content) for c, _, _, _ in candidates])
    
    # Normalize to [0, 1]
    ce_norm = min_max_normalize(ce_scores)
    
    # Blend 60% cross-encoder + 40% original PARA score (preserves position awareness)
    reranked = [(c, 0.6 * ce_norm[i] + 0.4 * para_score, sem, pos)
                for i, (c, para_score, sem, pos) in enumerate(candidates)]
    
    return sort_by_score(reranked) + scored_chunks[top_n:]
```

**Why blend?** Pure cross-encoder would discard the position-bias correction. Blending keeps both signals.

### 8.4 Iterative Middle Probing

**Where:** `process_pdf.py` PARA branch in `answer_question()`

If the first answer has low confidence, re-probe the document middle with boosted position weight.

```python
# After first answer...
if confidence < 0.4 or "not contain" in answer_text.lower():
    middle_chunks = [c for c in chunks if 0.25 <= c.position <= 0.75]
    middle_context, _ = processor.apply_para(
        middle_chunks, question,
        alpha=0.5, beta=0.5  # Boost position weight for middle-only pass
    )
    reprobe_answer = client.generate(reprobe_prompt)
    if "not found" not in reprobe_answer.lower():
        answer_text += "\n\n[Additional info recovered from middle]:\n" + reprobe_answer
        confidence += 0.2
```

### 8.5 Answer Grounding Check

**Where:** `process_pdf.py` PARA branch

After generating an answer, a fact-check LLM call verifies claims against the retrieved context.

```python
grounding_prompt = f"""
CONTEXT: {context[:8000]}
ANSWER: {answer_text[:2000]}

Reply with ONLY: GROUNDED / PARTIALLY GROUNDED / UNGROUNDED
"""

grounding_result = client.generate(grounding_prompt, max_tokens=50).text
if "UNGROUNDED" in grounding_result:
    confidence -= 0.3
    answer_text += "\n\n*Note: Some claims could not be verified.*"
elif "PARTIALLY" in grounding_result:
    confidence -= 0.1
```

This catches LLM hallucinations — especially important to avoid falsely claiming "recovery" of middle content that wasn't actually there.

### 8.6 Other prompt-based strategies (summary)

| Strategy | Technique |
|----------|-----------|
| Attention Anchoring | Section markers + `[CRITICAL]` tags + question reminders |
| Relevance Restructuring | Keyword scoring → place relevant chunks at edges |
| Query-Aware Compression | Compress irrelevant, keep relevant full-text at edges |
| Query-Aware Contextualization | Query both before AND after docs (Liu et al. 2023) |
| Chunked Reading | 3 chunks at a time, extract relevant info per batch |
| Reranking | Most relevant at positions 1 and N, least in middle |
| Chunk-by-Chunk Reasoning | Force per-passage evaluation before synthesis |
| Map-Reduce | MAP: extract facts per chunk. REDUCE: synthesize |
| Combined | Applies 4+ prompt techniques together |

Full algorithmic detail in [`RESEARCH_REFERENCE.md`](RESEARCH_REFERENCE.md) section 4.

---

## 9. Next.js Frontend Implementation

### 9.1 Architecture

- **App Router** (Next.js 14) — file-based routing, server components by default
- **Client components** marked with `'use client'` for interactivity
- **API routes** co-located in `app/api/*/route.ts`
- **Tailwind CSS** with CSS-variable-driven theming
- **localStorage** for chat history persistence

### 9.2 Key components

#### `app/page.tsx` (~900 lines)
The single-page app. Manages:
- Document state (`currentDocument`, `uploadedFilename`)
- Messages array (`messages` + `setMessages`)
- Strategy selection
- Modals (Compare, Benchmark, Position Recovery Dashboard)
- Sidebar toggle
- Chat history save/restore/delete
- Export as JSON/Markdown

#### `components/ChatInterface.tsx`
- Messages display with user/assistant avatars
- Streaming word-by-word render (4 words per 15ms)
- Strategy selector dropdown
- Input textarea with Enter-to-send
- Copy-to-clipboard on each assistant message
- Auto-scroll to bottom with "scroll to bottom" button

#### `components/DocumentOverview.tsx`
Rendered as the first "assistant message" after PDF upload.
Shows:
- Overall summary (via MarkdownRenderer)
- Zone legend: Start / Middle / End chunk counts
- Expandable list of chunk summaries color-coded by zone
- Analysis latency

#### `components/EvaluationDashboard.tsx`
Modal for the Position Recovery Test.
- Config panel + Run button
- Runs `POST /api/benchmark` then `POST /api/ask` with `strategy=para`
- Merges both into a result
- Renders `recharts` LineChart with 3 lines (Baseline, Combined, PARA)
- Shades the middle "dead zone" (33-67%)
- Position-by-position table with ✓/✗ icons

#### `components/Logo.tsx`
The "Focus Band" inline SVG logo.
- Unique IDs per render (prevents `<defs>` collision if multiple instances)
- Scales from 16px (favicon) to 200px+ (hero)
- Two exports: `Logo` (mark only) and `LogoLockup` (mark + wordmark)

#### `components/ThemeToggle.tsx`
- Reads `document.documentElement.classList.contains('dark')` on mount
- Toggle → add/remove `.dark` class + save to `localStorage.theme`
- Returns Sun icon in dark mode, Moon icon in light mode

### 9.3 Streaming message render

```tsx
function StreamingMessage({ content, isNew }: Props) {
  const [visible, setVisible] = useState(isNew ? '' : content);
  
  useEffect(() => {
    if (!isNew) { setVisible(content); return; }
    let i = 0;
    const step = 4;  // words per tick
    const interval = setInterval(() => {
      i += step;
      setVisible(content.split(' ').slice(0, i).join(' '));
      if (i >= content.split(' ').length) {
        setVisible(content);
        clearInterval(interval);
      }
    }, 15);
    return () => clearInterval(interval);
  }, [content, isNew]);
  
  // During stream: plain text. After stream: swap to MarkdownRenderer
  return streaming ? <span>{visible}</span> : <MarkdownRenderer content={visible} />;
}
```

Plain text during stream is intentional — it's fast. MarkdownRenderer re-runs on every update which would be slow.

---

## 10. LLM Providers & Auto-Fallback

### 10.1 `LLMClient` (unified interface)

Supports 4 providers via 2 code paths:

| Provider | SDK | Base URL |
|----------|-----|----------|
| Groq | `openai` SDK | `https://api.groq.com/openai/v1` |
| Gemini | `openai` SDK | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| OpenAI | `openai` SDK | (default) |
| Anthropic | `anthropic` SDK | (native) |

Three providers share the OpenAI SDK because Groq and Gemini offer OpenAI-compatible endpoints.

### 10.2 `ResilientLLMClient` (auto-fallback)

Wraps multiple `LLMClient` instances. On any error, instantly switches to the next client in the chain.

```python
class ResilientLLMClient:
    def __init__(self, clients: List[LLMClient]):
        self.clients = clients
        self._active_idx = 0  # sticky — reuses last-working client

    def generate(self, prompt, system_prompt=None, **kwargs) -> LLMResponse:
        last_error = None
        for offset in range(len(self.clients)):
            idx = (self._active_idx + offset) % len(self.clients)
            try:
                response = self.clients[idx].generate(prompt, system_prompt, **kwargs)
                self._active_idx = idx  # Stick with working provider
                return response
            except Exception as e:
                last_error = e
                continue  # No sleep — API rejects are instant
        raise last_error
```

### 10.3 Default fallback chain

```python
def _build_resilient_client(primary="groq"):
    clients = []
    # Groq models (ordered by capability)
    clients.append(LLMClient("groq", "llama-3.3-70b-versatile"))
    clients.append(LLMClient("groq", "llama-3.1-8b-instant"))
    clients.append(LLMClient("groq", "gemma2-9b-it"))
    # Gemini models (Google free tier)
    clients.append(LLMClient("gemini", "gemini-2.5-flash"))
    clients.append(LLMClient("gemini", "gemini-1.5-flash-8b"))
    
    if primary == "gemini":
        clients = clients[3:] + clients[:3]  # Gemini first
    
    return ResilientLLMClient(clients)
```

### 10.4 What triggers a failover?

**Any exception** — rate limits (429), quota exhausted, auth errors (401), network errors, timeout. Only if every provider in the chain fails does the last error surface to the user.

**No waiting** — old code had `time.sleep(2.1)` between Groq calls. That's removed. Fallback is instant because the API itself rejects bad requests immediately.

### 10.5 Gemini-specific handling

Gemini 2.5 uses **thinking tokens** that count against `max_tokens`. If you set `max_tokens=20`, Gemini may use all of them on reasoning and return empty content.

Workaround in `LLMClient._generate_openai()`:
```python
effective_max = max_tokens * 3 if self.provider == "gemini" else max_tokens
```
Gemini gets 3× the requested token budget to leave room for thinking.

---

## 11. Theme System

### 11.1 CSS variables in `globals.css`

All colors are defined as CSS custom properties:

```css
:root {
  /* Light mode (default) */
  --claude-bg: #ffffff;
  --claude-surface: #f4f4f5;
  --claude-sidebar: #f0f0f2;
  /* ... */
}

.dark {
  /* Dark mode — overrides */
  --claude-bg: #171717;
  --claude-surface: #212121;
  --claude-sidebar: #0f0f0f;
  /* ... */
}
```

### 11.2 Tailwind uses the variables

```typescript
// tailwind.config.ts
colors: {
  claude: {
    bg: 'var(--claude-bg)',
    surface: 'var(--claude-surface)',
    // ...
  },
},
darkMode: 'class',
```

So writing `className="bg-claude-bg"` automatically swaps colors when `.dark` is toggled on `<html>`.

### 11.3 No-flash initialization

`layout.tsx` injects a `<script>` into `<head>` that runs **before React hydrates**:

```javascript
(function() {
  var saved = localStorage.getItem('theme');
  var prefersDark = matchMedia('(prefers-color-scheme: dark)').matches;
  var theme = saved || (prefersDark ? 'dark' : 'light');
  if (theme === 'dark') document.documentElement.classList.add('dark');
})();
```

This prevents the "flash of wrong theme" on page load.

### 11.4 Theme toggle

`ThemeToggle` component:
1. Reads current class on `<html>` on mount
2. On click: toggles `.dark` class + saves preference to `localStorage`
3. Icon: Moon (light mode, will switch to dark) / Sun (dark mode, will switch to light)

---

## 12. API Reference

All API routes live in `web/src/app/api/*/route.ts` and spawn `process_pdf.py` subprocesses.

### `POST /api/upload`
Upload a PDF.
```json
// Request: multipart/form-data with "file"
// Response:
{ "success": true, "filename": "1234567890_doc.pdf", "filepath": "...", "size": 1234567 }
```

### `POST /api/summarize`
Summarize each chunk of the uploaded PDF.
```json
// Request:
{ "filename": "1234567890_doc.pdf" }

// Response:
{
  "success": true,
  "totalChunks": 42,
  "chunkSummaries": [{ "chunkId": 1, "zone": "beginning", "position": 5, "summary": "..." }, ...],
  "overallSummary": "...",
  "middleChunksCount": 14,
  "latency": 23.4
}
```

### `POST /api/ask`
Answer a question using a chosen strategy.
```json
// Request:
{
  "question": "What is the main finding?",
  "filename": "1234567890_doc.pdf",
  "strategy": "para",        // any of 11 strategies
  "provider": "groq"          // groq | gemini | openai | anthropic
}

// Response:
{
  "success": true,
  "answer": "The main finding is...",
  "confidence": 0.87,
  "strategyUsed": "para",
  "chunksProcessed": 42,
  "latency": 18.2,
  "strategyExplanation": "PARA Enhanced: Semantic chunking + ..."
}
```

### `POST /api/compare`
Run a question through all strategies and rank by confidence.
```json
// Request:
{ "question": "...", "filename": "..." }

// Response:
{
  "success": true,
  "comparison": [{ "strategy": "para", "answer": "...", "confidence": 0.91, "latency": 18.2 }, ...],
  "bestStrategy": "para",
  "totalLatency": 280.5
}
```
**Timeout: 5 minutes.** Runs 8+ strategies sequentially.

### `POST /api/benchmark`
Needle-in-the-haystack test at 7 positions.
```json
// Request:
{ "filename": "...", "needleFact": "..." }  // needleFact optional

// Response:
{
  "success": true,
  "results": [{ "positionPercent": 40, "baselineFound": false, "combinedFound": true, ... }, ...],
  "summary": {
    "baselineAccuracy": 71.4,
    "combinedAccuracy": 100.0,
    "improvement": 28.6,
    "deadZonePositions": [40, 50, 60]
  }
}
```
**Timeout: 10 minutes.**

### `POST /api/kv-retrieval`
Synthetic key-value retrieval task (Liu et al. 2023, Section 3).
```json
// Request:
{ "numPairs": 75 }  // default 75

// Response:
{ "success": true, "summary": { "accuracy": 85.7, ... }, "results": [...] }
```

---

## 13. How to Extend the Project

### Add a new recovery strategy

1. Add a method to `MiddleRecoveryProcessor` in `process_pdf.py`:
   ```python
   def apply_my_strategy(self, chunks, query):
       # Build and return a context string
       return formatted_context
   ```

2. Add a case in `answer_question()`:
   ```python
   elif strategy == "my_strategy":
       context = processor.apply_my_strategy(chunks, question)
       system_prompt = processor.get_system_prompt("my_strategy")
   ```

3. Add a system prompt in `get_system_prompt()`.

4. Add `"my_strategy"` to:
   - `Strategy` union in `web/src/app/api/ask/route.ts`
   - `Strategy` type and `STRATEGIES` array in `web/src/types/index.ts`
   - `validStrategies` array in `ask/route.ts`

5. Optionally add to `compare_strategies()` list.

### Add a new LLM provider

1. Add `elif provider == "newprov":` branch in `LLMClient.__init__()`.
2. Implement or share `_generate_*()` method.
3. Add rate-limit entry in `_RATE_LIMITS` dict.
4. Add provider config in `get_llm_client()` in `process_pdf.py`.
5. Add to `validProviders` in `ask/route.ts`.

### Tune PARA hyperparameters

Edit defaults in `src/para.py:PARARetriever.score_chunks()`:
- `alpha` — semantic weight (default 0.7)
- `beta` — position weight (default 0.3)
- `gamma` — position amplitude (default: adaptive via `compute_adaptive_gamma`)

Or pass them at call time from `process_pdf.py:apply_para()`.

### Change the embedding model

Edit `src/para.py:PARARetriever.__init__()`:
```python
def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
```
Try:
- `all-mpnet-base-v2` — higher quality, slower
- `multi-qa-MiniLM-L6-cos-v1` — optimized for QA
- `gtr-t5-base` — strong on document retrieval

---

## 13a. Ablation Infrastructure (for the research paper)

PARA's novel contribution is the `sin(π·p)` position-bias correction. The rest of the pipeline (semantic chunking, multi-granularity retrieval, cross-encoder rerank, iterative probing, grounding) is prior art assembled as a testbed. The code supports ablating each component independently.

### 13a.1 Ablation flags on `apply_para()`

```python
processor.apply_para(
    chunks, query,
    # Core PARA parameters
    alpha=0.7,                   # semantic weight
    beta=0.3,                    # position-correction weight (0 = disabled)
    gamma=None,                  # None → adaptive (see adaptive_gamma)
    top_k=10,
    # Ablation toggles
    correction_type="sin",       # "sin" | "gaussian" | "triangle" | "step" | "none"
    adaptive_gamma=True,         # False → uses fixed gamma=0.3
    use_cross_encoder=True,      # False → skip 2nd-stage rerank
    use_multi_granularity=True,  # False → paragraph-level only
)
```

### 13a.2 Correction function shapes

All five functions peak at position 0.5 with amplitude γ, and differ in their shape:

| `correction_type` | Formula | Shape |
|---|---|---|
| `"sin"` (ours) | `γ · sin(π·p)` | Smooth, zero at edges |
| `"gaussian"` | `γ · exp(-((p-0.5)/0.2)²)` | Smooth, near-zero at edges |
| `"triangle"` | `γ · (1 − 2·|p − 0.5|)` | Linear, zero at edges |
| `"step"` | `γ` if 0.25 ≤ p ≤ 0.75 else 0 | Hard cutoff |
| `"none"` | 0 (disables correction) | Flat |

Empirical output at 11 equally-spaced positions (γ=0.3):
```
sin      : [0.00, 0.09, 0.18, 0.24, 0.29, 0.30, 0.29, 0.24, 0.18, 0.09, 0.00]
gaussian : [0.01, 0.04, 0.10, 0.18, 0.27, 0.30, 0.27, 0.18, 0.10, 0.04, 0.01]
triangle : [0.00, 0.06, 0.12, 0.18, 0.24, 0.30, 0.24, 0.18, 0.12, 0.06, 0.00]
step     : [0.00, 0.00, 0.00, 0.30, 0.30, 0.30, 0.30, 0.30, 0.00, 0.00, 0.00]
none     : [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00]
```

### 13a.3 Running ablation experiments

Three pre-defined experiments via `scripts/run_ablation.py`:

```bash
# Experiment 1 — Correction function shape (addresses "why sin?")
python scripts/run_ablation.py \
    --pdf data/uploads/paper.pdf \
    --experiment correction_function \
    --positions 0.05,0.15,0.25,0.35,0.45,0.5,0.55,0.65,0.75,0.85,0.95 \
    --num-runs 3

# Experiment 2 — 2×2 cross-encoder × position factorial
python scripts/run_ablation.py \
    --pdf data/uploads/paper.pdf \
    --experiment cross_encoder \
    --num-runs 3

# Experiment 3 — Incremental component stacking
python scripts/run_ablation.py \
    --pdf data/uploads/paper.pdf \
    --experiment component_stack \
    --num-runs 3
```

Each experiment inserts the same needle fact at multiple positions in the uploaded document, then evaluates every (config × position × run) combination. Results save to `results/ablation_<experiment>_<timestamp>.json`.

### 13a.4 Experiment definitions

All three experiments are defined as functions in `scripts/run_ablation.py`:

- **`exp_correction_function()`** — Holds everything constant, sweeps `correction_type` across `{sin, gaussian, triangle, step, none}`. 5 configs.
- **`exp_cross_encoder_factorial()`** — 2×2 design: `{no position, +position} × {no rerank, +cross-encoder}`. Isolates each mechanism's marginal contribution. 4 configs.
- **`exp_component_stack()`** — Incremental: semantic → +multi-granularity → +cross-encoder → +fixed-γ → +adaptive-γ (full PARA). Shows marginal F1 contribution of each component. 5 configs.

### 13a.5 Runtime estimates (Groq free tier)

| Experiment | LLM calls | Est. wall time |
|---|---|---|
| `correction_function` (5 cfg × 11 pos × 3 runs) | 165 | ~12 min |
| `cross_encoder` (4 cfg × 7 pos × 3 runs) | 84 | ~6 min |
| `component_stack` (5 cfg × 7 pos × 3 runs) | 105 | ~8 min |

With Groq → Gemini auto-fallback (see §10.4 [LLM Providers](#10-llm-providers--auto-fallback)), effective throughput is higher than Groq alone.

---

## 14. Troubleshooting

### "PARA requires sentence-transformers"
```bash
source venv/bin/activate
pip install "sentence-transformers<4" "numpy<2"
```

### `numpy` / `torch` compatibility error
```bash
pip install "numpy<2"  # Pin to numpy 1.x for torch 2.2 compatibility
```

### Gemini returns empty content
Model hit max_tokens on thinking. The code auto-multiplies `max_tokens × 3` for Gemini. If still failing, the grounding check or re-probe prompt may be too long — check stderr.

### "All Groq models rate-limited"
The ResilientLLMClient will automatically try Gemini. Make sure `GEMINI_API_KEY` is in `.env`.

### PDF extraction returns garbled text
PyPDF2 struggles with scanned PDFs or complex layouts. For better extraction, consider replacing with `pdfplumber` or `pymupdf` in `extract_text_from_pdf()`.

### Frontend dev server port conflict
Next.js will try port 3000, then 3001. Check the terminal output for the actual port.

### "Cannot find module '../../../api/evaluate/route.js'"
Stale Next.js cache after deleting API routes. Fix:
```bash
rm -rf web/.next
npm run dev
```

### Chat history not persisting
Check browser console for localStorage errors. Private/incognito browsing disables localStorage.

### CORS / `/api/...` 404
Make sure you're running the Next.js dev server (`npm run dev`), not the Python backend directly. The frontend expects routes relative to itself.

---

## Appendix: Key Files at a Glance

| File | Purpose | Lines |
|------|---------|-------|
| `process_pdf.py` | Main backend — strategies, CLI, orchestration | ~1400 |
| `src/para.py` | PARA retriever + 5 correction functions + ablation flags | ~560 |
| `src/core/llm_client.py` | Multi-provider + ResilientLLMClient fallback | ~270 |
| `scripts/run_ablation.py` | Ablation experiment runner (3 experiments) | ~250 |
| `web/src/app/page.tsx` | Main frontend page | ~900 |
| `web/src/components/ChatInterface.tsx` | Chat UI | ~370 |
| `web/src/components/Logo.tsx` | Circular "Focus Band" SVG logo | ~80 |
| `web/src/components/EvaluationDashboard.tsx` | Position Recovery Test | ~280 |
| `web/src/app/globals.css` | Theme CSS variables (light + dark) | ~180 |
| `web/tailwind.config.ts` | Tailwind config (CSS-var-driven) | ~60 |
| `RESEARCH_REFERENCE.md` | Research/paper-oriented reference | ~920 |
| `IMPLEMENTATION.md` | This file | — |
