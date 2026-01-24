# Lost in the Middle: RAG Research Engine

A comprehensive research framework for studying and solving the "Lost in the Middle" problem in long-context language models.

> **🆓 FREE: Uses Groq API - blazing fast, no cost, no laptop heat!** Get your free API key at [console.groq.com](https://console.groq.com)

## 🎯 What This Solves

**The Problem**: Large Language Models (LLMs) have a proven, documented flaw—they pay attention to the beginning and end of their context window but ignore information in the middle. This is called **"Lost in the Middle"** and it's breaking RAG systems everywhere.

**Our Solution**: This research engine implements and tests multiple recovery strategies to overcome this limitation.

## 📊 Research Overview

### The Core Finding

```
CONTEXT WINDOW ATTENTION PATTERN:

Position:    [START]----[MIDDLE]----[END]
Attention:   █████████░░░░░░░░░░████████
             ↑                      ↑
         HIGH ATTENTION         HIGH ATTENTION
                    ↑
              INFORMATION GRAVEYARD
```

When you place 20 documents in context:
- Documents 1-3: Model pays attention ✅
- Documents 4-17: Model basically ignores ❌
- Documents 18-20: Model pays attention again ✅

### Our Experiments

This engine implements **5 comprehensive experiments** to map and solve this problem:

1. **Dead Zone Mapper** - Precisely map where attention dies
2. **Context Restructuring** - Intelligently reorder documents to avoid dead zones
3. **Chunked Reading** - Process context in strategic chunks instead of all at once
4. **Attention Anchoring** - Use markers and formatting to force middle attention
5. **Query-Aware Compression** - Compress irrelevant content, expand relevant content

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd RAG_RESEARCH_ENGINE

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up Groq API key (FREE)
cp .env.example .env
# Edit .env and add your GROQ_API_KEY from console.groq.com
```

### Running Experiments

```bash
# Run a quick test (3 trials)
python run_experiments.py dead_zone --quick

# Run full Dead Zone Mapper experiment (10 trials)
python run_experiments.py dead_zone --trials 10

# Run Context Restructuring experiment
python run_experiments.py restructuring --trials 10

# Run ALL experiments
python run_experiments.py all --trials 10
```

### Expected Output

Each experiment will:
1. Generate synthetic "needle in haystack" documents
2. Test retrieval accuracy at different positions
3. Save detailed results to `./results/`
4. Create visualizations in `./results/*/visualizations/`
5. Print comprehensive analysis

## 📁 Project Structure

```
RAG_RESEARCH_ENGINE/
├── src/
│   ├── core/                    # Core components
│   │   ├── llm_client.py       # LLM API wrapper
│   │   ├── document_generator.py # Synthetic data generation
│   │   └── experiment.py        # Base experiment class
│   ├── experiments/             # Experiment implementations
│   │   ├── dead_zone_mapper.py
│   │   └── context_restructuring_exp.py
│   ├── strategies/              # Recovery strategies
│   │   ├── context_restructuring.py
│   │   ├── chunked_reading.py
│   │   └── attention_anchoring.py
│   ├── evaluation/              # Metrics and evaluation
│   └── utils/                   # Utilities
│       └── visualization.py     # Plotting and analysis
├── config/                      # Configuration
│   └── config.py
├── notebooks/                   # Jupyter notebooks
├── results/                     # Experiment results
├── data/                        # Data storage
├── run_experiments.py           # Main runner script
└── requirements.txt
```

## 🔬 Experiments in Detail

### Experiment 1: Dead Zone Mapper

**Goal**: Create the most detailed map of where information gets lost

**Method**:
- Place a "needle" fact at different positions (5%, 10%, 20%...95%)
- Ask LLM to retrieve the fact
- Measure accuracy at each position

**Expected Result**: U-shaped curve (high at edges, low in middle)

**Novel Contribution**: Most granular attention death map in the literature

### Experiment 2: Context Restructuring

**Goal**: Test if intelligent document reordering improves retrieval

**Methods Tested**:
- Baseline (original order)
- Random shuffling (control)
- Relevance-based (high-relevance docs at edges)
- Alternating (high/low relevance interleaved)
- Reverse order

**Novel Contribution**: First automatic context optimization system

### Experiment 3: Chunked Iterative Reading

**Goal**: Test if processing in chunks beats full-context processing

**Methods**:
- Sequential chunks (read one chunk at a time)
- Hierarchical (scan → deep read)
- Query-guided (only read relevant chunks)

**Novel Contribution**: Systematic protocol for iterative context processing

### Experiment 4: Attention Anchoring

**Goal**: Test what markers/formatting help recover middle attention

**Strategies**:
- Section markers ("SECTION 5 of 20")
- Explicit instructions ("PAY ATTENTION TO...")
- Formatting (bold, separators)
- Redundancy (repeat middle content at end)
- Question injection (remind of query throughout)

**Novel Contribution**: Empirical ranking of anchoring techniques

### Experiment 5: Query-Aware Compression

**Goal**: Test if compressing irrelevant content helps

**Strategy**:
- Analyze query to determine relevance
- Summarize irrelevant documents (save tokens)
- Keep relevant documents in full detail
- Place detailed docs in high-attention positions

**Novel Contribution**: Adaptive compression based on attention patterns

## 📈 Results & Analysis

After running experiments, you'll get:

1. **Quantitative Metrics**
   - Accuracy at each position
   - Statistical significance tests
   - Improvement over baseline

2. **Visualizations**
   - Dead zone maps (U-curve plots)
   - Heatmaps (trials × positions)
   - Strategy comparison charts

3. **Detailed Reports**
   - JSON results files
   - CSV data for further analysis
   - Summary statistics

## 🎓 Research Applications

### For Academic Papers

This engine provides:
- Reproducible experiments
- Publication-ready visualizations
- Comprehensive statistics
- Novel contributions to the field

### For Production Systems

Use the findings to:
- Optimize RAG retrieval
- Improve long-context QA systems
- Build better document processing pipelines
- Reduce API costs (via compression strategies)

## 🔧 Configuration

Edit `config/config.py` to customize:
- LLM provider (Groq, OpenAI, Anthropic)
- Model selection (default: llama-3.1-8b-instant via Groq)
- Number of documents
- Document length (tokens)
- Needle positions
- Number of trials

## 📊 Sample Results

After running `dead_zone` experiment:

```
Dead Zone Mapping Results:
- Best position: 10% (accuracy: 95%)
- Worst position: 50% (accuracy: 35%)
- Accuracy range: 35% - 95%
- Drop in middle: 63%

✓ Dead zone DETECTED
  - Start accuracy: 92%
  - Middle accuracy: 38%
  - End accuracy: 90%
```

## 🤝 Contributing

This is a research framework. Contributions welcome:
- New recovery strategies
- Additional experiments
- Real-world datasets
- Improved visualizations

## 📚 References

Based on:
- "Lost in the Middle: How Language Models Use Long Contexts" (Liu et al., 2023)
- RAG best practices
- Attention mechanism research

## 📝 Citation

If you use this research engine, please cite:

```bibtex
@software{rag_research_engine,
  title={Lost in the Middle: RAG Research Engine},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/RAG_RESEARCH_ENGINE}
}
```

## ⚠️ Requirements

- Python 3.8+
- Groq API key (FREE - get it at console.groq.com)
- Or OpenAI/Anthropic API keys (paid alternatives)

## 💡 Tips for Best Results

1. **Start with Groq (FREE)** - Fast, free, and great for testing
2. **Use quick tests first** - Use `--quick` flag (3 trials)
3. **Run multiple trials** - 15-20 trials for statistical significance
4. **Watch rate limits** - Groq free tier: 30 requests/min, 6000 tokens/min

## 🐛 Troubleshooting

**API Errors**: Check your `.env` file has valid API keys

**Memory Issues**: Reduce `num_documents` or `tokens_per_doc` in config

**Slow Execution**: Use `--quick` flag or reduce `--trials`

## 📧 Contact

Questions? Issues? Open a GitHub issue or reach out!

---

**Built to solve the Lost in the Middle crisis. One experiment at a time.** 🔬