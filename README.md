# PARA: Position-Aware Retrieval for Lost-in-the-Middle LLMs

A research implementation and testbed for mitigating the "Lost in the Middle" problem (Liu et al., 2024) in long-context RAG systems.

> **Free tiers supported** — Groq + Gemini with automatic failover. Get keys at [console.groq.com](https://console.groq.com) and [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

---

## The Problem

LLMs under-attend to information in the **middle** of their context window. In retrieval-augmented generation, this means retrieved documents placed in the middle of a concatenated context are effectively ignored by the model.

```
U-SHAPED ATTENTION PATTERN (Liu et al. 2024):

Accuracy:  ████████████░░░░░░░░░░░░░░░░████████████
           ↑                                      ↑
         HIGH                                   HIGH
                          ↑
                    INFORMATION LOST
```

## Our Contribution

We add a single term to the retrieval score:

$$\text{score}(c_i) = \alpha \cdot \text{sim}(q, c_i) + \beta \cdot \gamma \cdot \sin(\pi \cdot p_i)$$

where $p_i \in [0,1]$ is the chunk's position in the document. The `sin(π·p)` correction **peaks at the middle and is zero at the edges** — the mathematical inverse of the empirical attention drop.

The rest of the pipeline (semantic chunking, multi-granularity retrieval, cross-encoder reranking, iterative refinement, grounding verification) is **established prior art** we integrate as the competitive baseline. See [`RESEARCH_REFERENCE.md`](RESEARCH_REFERENCE.md) §10.1 for the honest contribution breakdown and citations.

---

## Quick Start

### 1. Setup

```bash
git clone <your-repo-url>
cd RAG_RESEARCH_ENGINE

# Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# API keys — at least one required
cp .env.example .env
# Edit .env and add GROQ_API_KEY and/or GEMINI_API_KEY
```

### 2. Run the web interface

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### 3. Or run from the CLI

```bash
# Summarize a PDF
python process_pdf.py data/uploads/paper.pdf summarize

# Ask a question using PARA
python process_pdf.py data/uploads/paper.pdf ask "What are the main findings?" para

# Compare all 11 strategies on one question
python process_pdf.py data/uploads/paper.pdf compare "What are the main findings?"

# Needle-in-the-haystack benchmark
python process_pdf.py data/uploads/paper.pdf benchmark
```

---

## Running Ablations

Three pre-defined experiments address the core reviewer objections:

```bash
# "Why sin(π·p) and not Gaussian/step/triangle?" — 5 correction shapes
python scripts/run_ablation.py --pdf data/uploads/paper.pdf \
    --experiment correction_function --num-runs 3

# "Is the cross-encoder doing the work?" — 2×2 factorial
python scripts/run_ablation.py --pdf data/uploads/paper.pdf \
    --experiment cross_encoder --num-runs 3

# Marginal contribution of each component, incrementally
python scripts/run_ablation.py --pdf data/uploads/paper.pdf \
    --experiment component_stack --num-runs 3
```

Results save to `results/ablation_<experiment>_<timestamp>.json`.

See [`IMPLEMENTATION.md`](IMPLEMENTATION.md) §13a for details on what each experiment tests and runtime estimates.

---

## 11 Recovery Strategies

| Strategy | Type | Notes |
|----------|------|-------|
| **PARA** (ours) | Retrieval | Semantic + sin(π·p) position correction |
| Combined | Prompt | All prompt techniques together |
| Attention Anchoring | Prompt | Section markers on middle content |
| Relevance Restructuring | Prompt | Place relevant chunks at edges |
| Query-Aware Compression | Prompt | Compress irrelevant, keep relevant full |
| Query-Aware Contextualization | Prompt | Query before AND after docs (Liu et al. 2024) |
| Chunked Reading | Prompt | 3-chunk batches, extract-then-synthesize |
| Reranking | Prompt | Most relevant at positions 1 and N |
| Chunk-by-Chunk Reasoning | Prompt | Force per-passage evaluation |
| Map-Reduce | Prompt | Extract-per-chunk → synthesize |
| Baseline | Control | Standard RAG (no recovery) |

---

## Project Structure

```
RAG_RESEARCH_ENGINE/
├── process_pdf.py              # Main backend — all 11 strategies + CLI
├── requirements.txt
├── README.md                   # This file
├── RESEARCH_REFERENCE.md       # Paper/research reference
├── IMPLEMENTATION.md           # Full implementation guide
├── .env                        # API keys
│
├── src/
│   ├── para.py                 # PARA retriever + 5 correction functions
│   └── core/
│       └── llm_client.py       # Groq/Gemini/OpenAI/Anthropic + auto-fallback
│
├── scripts/
│   └── run_ablation.py         # Ablation experiment runner
│
├── data/uploads/               # Uploaded PDFs
├── results/                    # Ablation JSON output
│
└── web/                        # Next.js 14 frontend
    └── src/
        ├── app/                # Pages, API routes, theme
        └── components/         # Chat UI, dashboard, logo
```

---

## LLM Providers

| Provider | Default Model | Free Tier | Notes |
|----------|---------------|-----------|-------|
| Groq | `llama-3.3-70b-versatile` | Yes (30 req/min) | Primary |
| Gemini | `gemini-2.5-flash` | Yes | Automatic fallback |
| OpenAI | `gpt-4o` | No | Cross-model experiments |
| Anthropic | `claude-sonnet-4` | No | Cross-model experiments |

**Auto-fallback:** When both `GROQ_API_KEY` and `GEMINI_API_KEY` are set, the `ResilientLLMClient` automatically switches providers on any failure (rate limit, quota, auth, network). Once a provider works, it sticks. No artificial delays.

---

## Documentation

- [`RESEARCH_REFERENCE.md`](RESEARCH_REFERENCE.md) — Research-paper-oriented reference. Covers the novel contribution, prior art citations, anticipated reviewer objections + rebuttals, and ablation protocol.
- [`IMPLEMENTATION.md`](IMPLEMENTATION.md) — Complete implementation guide. Covers project structure, request flow, Python backend, PARA algorithm deep-dive, Next.js frontend, LLM providers, theme system, API reference, extension points, and troubleshooting.

---

## Requirements

- Python 3.8+ (tested on 3.11)
- Node.js 18+
- At least one of: `GROQ_API_KEY` (free), `GEMINI_API_KEY` (free)

---

## Citation

This is an in-progress research project. If you use it, please cite the foundational paper it builds on:

```
Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M.,
Petroni, F., & Liang, P. (2024). Lost in the Middle: How Language
Models Use Long Contexts. TACL, 12, 157–173.
```

Full bibliography in [`RESEARCH_REFERENCE.md`](RESEARCH_REFERENCE.md) §12.
