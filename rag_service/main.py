"""FastAPI service — a prod és eval közös rag_core.run_rag hívása HTTP-n keresztül."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from rag_core.pipeline import run_rag
from rag_core.types import RAGRequest, RAGResponse

app = FastAPI(
    title="CUBIX RAG Service",
    version="0.1.0",
    description="HTTP façade for rag_core.run_rag",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/rag/query", response_model=RAGResponse)
def rag_query(request: RAGRequest) -> RAGResponse:
    try:
        return run_rag(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
