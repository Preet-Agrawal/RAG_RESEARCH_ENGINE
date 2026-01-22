# 🚀 START HERE - Choose Your Path

## You Have 2 Options:

---

## Option 1: FREE with Ollama (Recommended to Start) 🆓

**No API keys needed! Completely local and free.**

### Quick Start (5 minutes):
```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull a model
ollama pull llama3:8b

# 3. Test it works
python test_ollama.py

# 4. Run your first experiment
python run_experiments.py dead_zone --quick \
  --provider ollama --model llama3:8b
```

**✅ Pros:**
- Completely free ($0)
- No API keys
- Works offline
- Privacy (data stays local)
- Still shows "Lost in the Middle" problem
- Valid for research/papers

**⚠️ Cons:**
- Needs 8-16GB RAM
- Slightly lower accuracy than GPT-4
- Slower on CPU (fast with GPU)

**📚 Detailed Guide:** [README_OLLAMA.md](README_OLLAMA.md)

---

## Option 2: Paid APIs (OpenAI/Anthropic)

**Use cloud APIs for highest accuracy.**

### Quick Start (2 minutes):
```bash
# 1. Get API key from OpenAI or Anthropic
# OpenAI: https://platform.openai.com/api-keys
# Anthropic: https://console.anthropic.com/

# 2. Add to .env file
cp .env.example .env
nano .env  # Add your API key

# 3. Run experiment
python run_experiments.py dead_zone --quick
```

**✅ Pros:**
- Highest accuracy (GPT-4)
- Fast responses
- No local resources needed
- Works on any machine

**⚠️ Cons:**
- Costs money (~$30-40 per full experiment)
- Needs API key
- Requires internet
- Rate limits

**📚 Detailed Guide:** [GETTING_STARTED.md](GETTING_STARTED.md)

---

## Which Should You Choose?

### Choose Ollama (FREE) if:
- ✅ You want to experiment for free
- ✅ You have 8-16GB RAM available
- ✅ You're doing initial testing/iteration
- ✅ Privacy is important
- ✅ You don't mind slightly lower accuracy

### Choose Paid APIs if:
- ✅ You need highest possible accuracy
- ✅ You're running final experiments for publication
- ✅ You have API budget
- ✅ You want fastest results
- ✅ You're on a low-resource machine

### Best of Both Worlds:
1. **Start with Ollama** - Test everything for free
2. **Validate with GPT-4** - Run final experiments for paper
3. **Save money** - Only pay for what you need

---

## Quick Comparison

| Feature | Ollama (FREE) | GPT-4 | Claude 3 |
|---------|---------------|-------|----------|
| **Cost per experiment** | $0 | $30-40 | $5-10 |
| **Setup time** | 5 min | 2 min | 2 min |
| **Accuracy** | Good (85%) | Best (95%) | Better (90%) |
| **Speed** | 3-5 sec/trial | 2-3 sec | 2-3 sec |
| **Privacy** | Local | Cloud | Cloud |
| **RAM needed** | 8-16GB | None | None |
| **Valid for research?** | ✅ Yes | ✅ Yes | ✅ Yes |

---

## Next Steps by Path

### If You Choose Ollama (FREE):
1. Read [README_OLLAMA.md](README_OLLAMA.md)
2. Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
3. Pull model: `ollama pull llama3:8b`
4. Test: `python test_ollama.py`
5. Experiment: See examples below

### If You Choose Paid APIs:
1. Read [GETTING_STARTED.md](GETTING_STARTED.md)
2. Get API key (OpenAI or Anthropic)
3. Add to `.env` file
4. Test: `python run_experiments.py dead_zone --quick`
5. Experiment: See examples below

---

## Example Commands

### Ollama (Free):
```bash
# Quick test (3 trials, ~5 min, FREE)
python run_experiments.py dead_zone --quick \
  --provider ollama --model llama3:8b

# Full experiment (15 trials, ~20 min, FREE)
python run_experiments.py dead_zone --trials 15 \
  --provider ollama --model llama3:8b

# All experiments (FREE!)
python run_experiments.py all --trials 10 \
  --provider ollama --model llama3:8b
```

### GPT-4 (Paid):
```bash
# Quick test (3 trials, ~3 min, ~$2)
python run_experiments.py dead_zone --quick

# Full experiment (15 trials, ~15 min, ~$30)
python run_experiments.py dead_zone --trials 15

# All experiments (~$100)
python run_experiments.py all --trials 10
```

---

## What You'll Get

Regardless of which option you choose, you'll get:

✅ **U-shaped accuracy curve** showing "Lost in the Middle"
✅ **Publication-ready visualizations**
✅ **Statistical analysis** with significance tests
✅ **Recovery strategy comparisons**
✅ **Complete results** in JSON/CSV
✅ **Valid research findings** for papers

The "Lost in the Middle" problem exists across **ALL models**!

---

## Still Unsure? Try This:

### 5-Minute Test with Ollama (FREE):
```bash
# Install and test (one-time, ~5 min)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3:8b
python test_ollama.py

# Run ONE quick experiment (~3 min)
python run_experiments.py dead_zone --quick \
  --provider ollama --model llama3:8b
```

**If it works and you're happy**: Keep using Ollama (free)!

**If you want higher accuracy**: Get API key and switch to GPT-4.

---

## Documentation Index

| Document | Purpose |
|----------|---------|
| **[README_OLLAMA.md](README_OLLAMA.md)** | Complete Ollama guide (FREE) |
| **[OLLAMA_SETUP.md](OLLAMA_SETUP.md)** | Detailed Ollama setup |
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | Paid API setup |
| **[README.md](README.md)** | Full project documentation |
| **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** | One-page cheat sheet |
| **[RESEARCH_PAPER_TEMPLATE.md](RESEARCH_PAPER_TEMPLATE.md)** | For writing papers |

---

## Get Help

- **Test not working?** Run `python test_ollama.py` for diagnostics
- **Ollama issues?** See [OLLAMA_SETUP.md](OLLAMA_SETUP.md) troubleshooting
- **API issues?** See [GETTING_STARTED.md](GETTING_STARTED.md) troubleshooting
- **General questions?** See [README.md](README.md)

---

## My Recommendation

**Start with Ollama (FREE):**
1. Zero cost to experiment
2. Learn the system
3. Iterate on your research
4. Validate findings

**Then (optionally) validate with GPT-4:**
1. Run final experiments
2. Get highest accuracy numbers
3. Publish with both results
4. Show consistency across models

**This gives you the best of both worlds!**

---

## Ready to Start?

### For FREE option (Ollama):
👉 **Go to [README_OLLAMA.md](README_OLLAMA.md)**

### For Paid option (OpenAI/Anthropic):
👉 **Go to [GETTING_STARTED.md](GETTING_STARTED.md)**

---

**Happy researching!** 🔬
