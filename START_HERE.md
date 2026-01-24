# 🚀 START HERE - Quick Setup Guide

## Getting Started with RAG Research Engine

This research framework uses **Groq** - a FREE, fast cloud API service.

---

## Quick Start (2 Minutes)

### 1. Get Your FREE Groq API Key

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up (it's free!)
3. Navigate to "API Keys"
4. Create a new API key
5. Copy the key

### 2. Install Dependencies

```bash
# Clone the repository
git clone <your-repo-url>
cd RAG_RESEARCH_ENGINE

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure API Key

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Groq API key
# GROQ_API_KEY=gsk_your_actual_key_here
```

### 4. Run Your First Experiment

```bash
# Quick test (3 trials, ~3 minutes)
python run_experiments.py dead_zone --quick

# Full experiment (10 trials, ~10 minutes)
python run_experiments.py dead_zone --trials 10
```

---

## What is Groq?

**Groq** is a cloud inference platform that provides:
- ✅ **FREE tier** with generous limits
- ✅ **Blazing fast** - 500+ tokens/second
- ✅ **No laptop heat** - runs on their servers
- ✅ **Good models** - Llama 3.1, Mixtral, Gemma

### Free Tier Limits:
- 30 requests per minute
- 6,000 tokens per minute
- More than enough for research experiments!

---

## Example Commands

### Quick Test (3 trials):
```bash
python run_experiments.py dead_zone --quick
```

### Full Dead Zone Experiment (10 trials):
```bash
python run_experiments.py dead_zone --trials 10
```

### Context Restructuring Experiment:
```bash
python run_experiments.py restructuring --trials 10
```

### All Experiments:
```bash
python run_experiments.py all --trials 10
```

---

## What You'll Get

After running experiments, you'll have:

✅ **U-shaped accuracy curve** showing "Lost in the Middle" phenomenon
✅ **Publication-ready visualizations** (saved as PNG files)
✅ **Statistical analysis** with confidence intervals
✅ **Detailed results** in JSON and CSV formats
✅ **Heatmaps** showing attention patterns

All saved to `./results/` directory!

---

## Configuration

The system is pre-configured for Groq, but you can customize in `config/config.py`:

- **Model**: llama-3.1-8b-instant (default)
- **Documents**: 10 documents × 250 tokens each
- **Positions**: 11 test positions (5%, 10%, ..., 95%)
- **Trials**: Configurable (3 for quick, 10+ for research)

---

## Troubleshooting

### Rate Limit Errors?
- Wait 60 seconds between runs
- Groq free tier resets every minute
- Or reduce document size in `run_experiments.py`

### API Key Not Working?
- Check your `.env` file has `GROQ_API_KEY=gsk_...`
- Make sure `.env` is in the project root
- Try: `python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('GROQ_API_KEY'))"`

### Import Errors?
- Make sure you're in the virtual environment
- Run: `pip install -r requirements.txt`

---

## Alternative Providers

Want to use a different provider? You can configure:

### OpenAI (Paid):
```python
# In run_experiments.py, change:
"llm_provider": "openai",
"llm_model": "gpt-4-turbo-preview",
```

### Anthropic (Paid):
```python
# In run_experiments.py, change:
"llm_provider": "anthropic",
"llm_model": "claude-3-opus-20240229",
```

---

## Next Steps

1. **Run your first experiment** (see commands above)
2. **Check results** in `./results/dead_zone_mapper/`
3. **View visualizations** in `./results/dead_zone_mapper/visualizations/`
4. **Read full documentation** in [README.md](README.md)
5. **Customize experiments** in `config/config.py`

---

## Documentation

| File | Description |
|------|-------------|
| [README.md](README.md) | Full project documentation |
| [START_HERE.md](START_HERE.md) | This quick start guide |
| `config/config.py` | Configuration settings |
| `run_experiments.py` | Main experiment runner |

---

## Ready to Begin?

Run your first experiment now:

```bash
python run_experiments.py dead_zone --quick
```

**Happy researching!** 🔬

---

**FREE • FAST • NO LAPTOP HEAT**
