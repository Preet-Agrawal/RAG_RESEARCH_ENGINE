# Getting Started Guide

Welcome to the Lost in the Middle RAG Research Engine! This guide will walk you through setup and running your first experiments.

## 🎯 What You'll Accomplish

By the end of this guide, you'll:
1. Have a working research environment
2. Understand the "Lost in the Middle" problem through hands-on demos
3. Run your first experiment mapping attention death zones
4. Generate publication-ready visualizations

## 📋 Prerequisites

- Python 3.8 or higher
- An OpenAI API key (GPT-4 recommended) OR Anthropic API key (Claude 3)
- ~2GB free disk space
- Basic command line knowledge

## 🚀 Step 1: Installation (5 minutes)

### Option A: Automated Setup (Recommended)

```bash
# Make setup script executable
chmod +x setup.sh

# Run setup
./setup.sh
```

The script will:
- Create a virtual environment
- Install all dependencies
- Set up directory structure
- Create your `.env` file

### Option B: Manual Setup

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p results data notebooks

# Set up environment
cp .env.example .env
```

## 🔑 Step 2: Configure API Keys (2 minutes)

Edit the `.env` file:

```bash
nano .env  # or use your favorite editor
```

Add your API key:

```
OPENAI_API_KEY=sk-your-key-here
# OR
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Save and close.

## 🧪 Step 3: Run Your First Experiment (10 minutes)

### Quick Test (Fastest)

Run a quick test to verify everything works:

```bash
python run_experiments.py dead_zone --quick
```

This runs 3 trials and should complete in ~2-3 minutes.

**Expected output:**
```
============================================================
Running Experiment: dead_zone_mapper
Number of trials: 3
============================================================

Setting up Dead Zone Mapper experiment...
Setup complete.
Running trial 1/3... ✓ (2.34s)
Running trial 2/3... ✓ (2.41s)
Running trial 3/3... ✓ (2.38s)

============================================================
Experiment completed: 3/3 successful
============================================================

Analyzing results...

============================================================
DEAD ZONE ANALYSIS
============================================================

Overall Accuracy: 58.1%

Accuracy by Position:
  📍 baseline:   45.0%
     10%:      90.0%
     25%:      85.0%
     50%:      35.0%  ← DEAD ZONE!
     75%:      88.0%
     90%:      92.0%

Dead Zone Detection:
  ✓ Dead zone DETECTED
    - Start accuracy: 87.5%
    - Middle accuracy: 35.0%
    - End accuracy: 90.0%
    - Drop: 60.7%

Results saved to: ./results/dead_zone_mapper
```

### Full Experiment (Recommended)

For publication-quality results, run 15+ trials:

```bash
python run_experiments.py dead_zone --trials 15
```

This takes ~10-15 minutes but provides statistically significant results.

## 📊 Step 4: View Results

Results are automatically saved to `./results/dead_zone_mapper/`:

```
results/
└── dead_zone_mapper/
    ├── results_20240120_143022.json    # Raw data
    ├── results_20240120_143022.csv     # For analysis
    └── visualizations/
        ├── dead_zone_map.png           # U-curve plot
        └── position_heatmap.png        # Trials × positions
```

Open the PNG files to see your results!

## 🎨 Step 5: Interactive Exploration (Optional)

For hands-on experimentation, use the Jupyter notebook:

```bash
# Install Jupyter (if not already installed)
pip install jupyter

# Launch notebook
jupyter notebook notebooks/01_quick_start.ipynb
```

The notebook lets you:
- Run single-trial experiments
- Test different strategies interactively
- Modify parameters on the fly
- Visualize results in real-time

## 📚 Step 6: Run Additional Experiments

### Context Restructuring

Test if reordering documents improves retrieval:

```bash
python run_experiments.py restructuring --trials 10
```

### Run All Experiments

For comprehensive results (takes ~1-2 hours):

```bash
python run_experiments.py all --trials 15
```

This runs:
1. Dead Zone Mapper
2. Context Restructuring
3. (More experiments can be added)

## 🔍 Understanding the Output

### What the Metrics Mean

**Accuracy by Position**: Shows retrieval success rate at each context position
- High (>80%): Model attends well
- Medium (50-80%): Partial attention
- Low (<50%): Dead zone

**Dead Zone Detection**: Automatically identifies if a U-shaped pattern exists
- Start/End accuracy: Performance at context edges
- Middle accuracy: Performance at 40-60% position
- Drop percentage: How much worse middle is than edges

### Reading the Visualizations

**Dead Zone Map (U-Curve)**:
- X-axis: Position in context (0% = start, 100% = end)
- Y-axis: Retrieval accuracy
- Shaded area: Dead zone region
- Expected: U-shaped curve (high edges, low middle)

**Position Heatmap**:
- Rows: Individual trials
- Columns: Positions tested
- Green: Correct retrieval
- Red: Failed retrieval
- Pattern: Green edges, red middle

## 💡 Next Steps

### For Academic Research

1. **Run full experiment suite**:
   ```bash
   python run_experiments.py all --trials 20
   ```

2. **Analyze results**: Use the generated CSVs for statistical analysis

3. **Write paper**: Use `RESEARCH_PAPER_TEMPLATE.md` as a starting point

4. **Create figures**: Publication-ready PNGs in `results/*/visualizations/`

### For Production Applications

1. **Test with your data**: Modify `src/core/document_generator.py` to use your documents

2. **Tune configuration**: Edit `config/config.py` for your use case

3. **Deploy best strategy**: Implement the highest-performing strategy in your RAG system

### For Further Experimentation

1. **Try different models**:
   ```python
   # In config.py
   model="gpt-4-turbo-preview"  # or "claude-3-opus-20240229"
   ```

2. **Adjust document count**:
   ```python
   num_documents=30  # Test with more documents
   ```

3. **Test real queries**: Replace synthetic needles with actual questions from your domain

## 🐛 Troubleshooting

### "API key not found"
- Check `.env` file exists and has your key
- Make sure key starts with `sk-` (OpenAI) or `sk-ant-` (Anthropic)
- Verify key has no extra spaces or quotes

### "Module not found"
- Activate virtual environment: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

### "Rate limit exceeded"
- Add delay between requests in `src/core/llm_client.py`
- Reduce `--trials` count
- Use cheaper model for testing

### Slow execution
- Use `--quick` flag for fast tests
- Reduce number of positions tested
- Use smaller `tokens_per_doc` in config

### Out of memory
- Reduce `num_documents` in config
- Process in smaller batches
- Close other applications

## 📞 Getting Help

- **Documentation**: See [README.md](README.md)
- **Issues**: Open a GitHub issue
- **Questions**: Check existing issues first

## 🎓 Learning Resources

### Understanding the Problem
1. Read the research motivation in [README.md](README.md)
2. Run the quick start notebook
3. Look at example results

### Diving Deeper
1. Study `src/experiments/dead_zone_mapper.py` to understand experiment design
2. Explore `src/strategies/` to see recovery techniques
3. Modify and extend for your use case

### Publishing Your Research
1. Use `RESEARCH_PAPER_TEMPLATE.md` as a structure
2. Generate all visualizations
3. Run statistical significance tests
4. Write up your findings

## ✅ Quick Checklist

- [ ] Python 3.8+ installed
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] API key configured in `.env`
- [ ] Quick test runs successfully
- [ ] Results generated and viewable
- [ ] Understand the output metrics

## 🎉 You're Ready!

You now have a fully functional research engine for studying and solving the Lost in the Middle problem.

**Recommended first steps**:
1. Run `python run_experiments.py dead_zone --quick` to see it work
2. Open the generated visualizations
3. Run the full experiment with 15+ trials
4. Start exploring different recovery strategies

Happy researching! 🔬
