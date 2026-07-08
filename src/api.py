"""
FastAPI HTTP layer for the RAG Research Engine.
Reuses logic from process_pdf.py — does not duplicate RAG implementation.
"""
import sys
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Request, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from process_pdf import (  # noqa: E402
    extract_text_from_pdf,
    answer_question,
    summarize_document,
    compare_strategies,
    run_needle_benchmark,
)

UPLOADS_DIR = ROOT / "data" / "uploads"

VALID_STRATEGIES = [
    "combined",
    "baseline",
    "attention_anchoring",
    "relevance_restructuring",
    "query_aware_compression",
    "query_aware_contextualization",
    "chunked_reading",
    "reranking",
    "chunk_by_chunk_reasoning",
    "map_reduce",
    "para",
]

app = FastAPI(title="RAG Research Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Surface the real error instead of a bare 'Internal Server Error'."""
    return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})


class AskRequest(BaseModel):
    filename: str
    question: str
    strategy: str = "combined"
    provider: str = "groq"


class SummarizeRequest(BaseModel):
    filename: str


class CompareRequest(BaseModel):
    filename: str
    question: str


class BenchmarkRequest(BaseModel):
    filename: str
    needle_fact: Optional[str] = None


def _ensure_uploads_dir() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _pdf_path(filename: str) -> Path:
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = UPLOADS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"PDF not found: {filename}")
    return path


def _load_pdf_text(filename: str) -> str:
    pdf_text = extract_text_from_pdf(str(_pdf_path(filename)))
    if pdf_text.startswith("Error"):
        raise HTTPException(status_code=400, detail=pdf_text)
    return pdf_text


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    _ensure_uploads_dir()
    timestamp = int(time.time() * 1000)
    safe_name = Path(file.filename).name
    filename = f"{timestamp}_{safe_name}"
    filepath = UPLOADS_DIR / filename

    try:
        content = await file.read()
        filepath.write_bytes(content)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {exc}") from exc

    return {
        "success": True,
        "filename": filename,
        "filepath": str(filepath),
        "size": len(content),
        "name": safe_name,
    }


@app.post("/ask")
def ask(body: AskRequest):
    if not body.question or not body.filename:
        raise HTTPException(status_code=400, detail="Question and filename are required")
    if body.strategy not in VALID_STRATEGIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy. Valid options: {', '.join(VALID_STRATEGIES)}",
        )

    pdf_text = _load_pdf_text(body.filename)
    result = answer_question(
        pdf_text,
        body.question,
        body.strategy,
        provider=body.provider,
    )

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    return {
        "success": True,
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "confidence": result.get("confidence", 0),
        "strategyUsed": result.get("strategy_used", body.strategy),
        "chunksProcessed": result.get("chunks_processed", 0),
        "latency": result.get("latency", 0),
        "strategyExplanation": result.get("strategy_explanation", ""),
    }


@app.post("/summarize")
def summarize(body: SummarizeRequest):
    if not body.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    pdf_text = _load_pdf_text(body.filename)
    response = summarize_document(pdf_text)

    if not response.get("success"):
        raise HTTPException(
            status_code=500,
            detail=response.get("error", "Failed to summarize document"),
        )

    return {
        "success": True,
        "totalChunks": response.get("total_chunks", 0),
        "chunkSummaries": [
            {
                "chunkId": chunk["chunk_id"],
                "totalChunks": chunk["total_chunks"],
                "zone": chunk["zone"],
                "position": chunk["position"],
                "summary": chunk["summary"],
                "isMiddle": chunk["is_middle"],
            }
            for chunk in response.get("chunk_summaries", [])
        ],
        "overallSummary": response.get("overall_summary", ""),
        "middleChunksCount": response.get("middle_chunks_count", 0),
        "latency": response.get("latency", 0),
    }


@app.post("/compare")
def compare(body: CompareRequest):
    if not body.question or not body.filename:
        raise HTTPException(status_code=400, detail="Question and filename are required")

    pdf_text = _load_pdf_text(body.filename)
    response = compare_strategies(pdf_text, body.question)

    if response.get("error"):
        raise HTTPException(status_code=500, detail=response["error"])

    return {
        "success": True,
        "question": response.get("question", body.question),
        "comparison": response.get("comparison", []),
        "bestStrategy": response.get("best_strategy"),
        "totalLatency": response.get("total_latency", 0),
    }


@app.post("/benchmark")
def benchmark(body: BenchmarkRequest):
    if not body.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    pdf_text = _load_pdf_text(body.filename)
    response = run_needle_benchmark(pdf_text, body.needle_fact)

    if response.get("error"):
        raise HTTPException(status_code=500, detail=response["error"])

    return {
        "success": True,
        "needleFact": response.get("needle_fact"),
        "testPositions": response.get("test_positions", []),
        "results": [
            {
                "positionPercent": r["position_percent"],
                "positionZone": r["position_zone"],
                "baselineFound": r["baseline_found"],
                "baselineConfidence": r["baseline_confidence"],
                "combinedFound": r["combined_found"],
                "combinedConfidence": r["combined_confidence"],
                "recoverySuccess": r["recovery_success"],
            }
            for r in response.get("results", [])
        ],
        "summary": {
            "baselineAccuracy": response["summary"]["baseline_accuracy"],
            "combinedAccuracy": response["summary"]["combined_accuracy"],
            "improvement": response["summary"]["improvement"],
            "deadZonePositions": response["summary"]["dead_zone_positions"],
            "deadZoneRecoveryRate": response["summary"]["dead_zone_recovery_rate"],
        },
        "totalLatency": response.get("total_latency", 0),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
