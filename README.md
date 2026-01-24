# Lost in the Middle: RAG Research Engine

A web-based research tool for studying and solving the "Lost in the Middle" problem in long-context language models.

> **FREE: Uses Groq API** - Get your free API key at [console.groq.com](https://console.groq.com)

## The Problem

LLMs have a documented flaw—they pay attention to the beginning and end of context but ignore information in the middle.

```
CONTEXT WINDOW ATTENTION PATTERN:

Position:    [START]----[MIDDLE]----[END]
Attention:   █████████░░░░░░░░░░████████
             ↑                      ↑
         HIGH ATTENTION         HIGH ATTENTION
                    ↑
              INFORMATION LOST
```

## Our Solution

This tool implements multiple recovery strategies to overcome this limitation:

| Strategy | Description |
|----------|-------------|
| **Combined** | All strategies together (recommended) |
| **Attention Anchoring** | Section markers and instructions for middle focus |
| **Relevance Restructuring** | Moves relevant content to document edges |
| **Chunked Reading** | Processes document in smaller segments |
| **Baseline** | Standard approach (for comparison) |

## Quick Start

### 1. Setup

```bash
# Clone and enter directory
git clone <your-repo-url>
cd RAG_RESEARCH_ENGINE

# Install Python dependencies
pip install -r requirements.txt

# Set up API key
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 2. Run Web Interface

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### 3. Use the App

1. Upload a PDF document
2. Select a recovery strategy
3. Ask questions about your document
4. Compare results with different strategies

## Project Structure

```
RAG_RESEARCH_ENGINE/
├── src/
│   └── core/
│       └── llm_client.py      # LLM API wrapper (Groq/OpenAI/Anthropic)
├── web/                        # Next.js web interface
│   └── src/
│       ├── app/               # Pages and API routes
│       ├── components/        # React components
│       └── types/             # TypeScript types
├── process_pdf.py             # PDF processing with recovery strategies
├── requirements.txt           # Python dependencies
└── .env.example              # Environment template
```

## Requirements

- Python 3.8+
- Node.js 18+
- Groq API key (free at console.groq.com)

## How It Works

1. **PDF Upload**: Extract text from your PDF
2. **Chunking**: Split document into overlapping chunks with position tracking
3. **Strategy Application**: Apply selected recovery strategy:
   - Add attention markers to middle content
   - Restructure by relevance
   - Process in smaller batches
4. **LLM Query**: Send optimized context to Groq's Llama 3.1
5. **Response**: Get answer with confidence score and metadata

## References

Based on "Lost in the Middle: How Language Models Use Long Contexts" (Liu et al., 2023)
