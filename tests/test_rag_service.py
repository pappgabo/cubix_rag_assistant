"""FastAPI rag_service endpoint tesztek (mockolt run_rag)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from rag_core.types import RAGResponse, RetrievedChunk, RetrievalStrategy
from rag_service.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_rag_query_success():
    mock_response = RAGResponse(
        answer="teszt válasz",
        chunks=[
            RetrievedChunk(
                doc_id="hummus",
                base_id="hummus",
                text="recept szöveg",
                score=0.9,
            )
        ],
        strategy=RetrievalStrategy.BASELINE,
        model="gpt-4.1-mini",
        prompt_version="prod",
    )
    with patch("rag_service.main.run_rag", return_value=mock_response) as mock_run:
        resp = client.post(
            "/v1/rag/query",
            json={
                "question": "Hogyan készül a hummus?",
                "session_id": "test-session",
                "request_id": "req-1",
                "strategy": "baseline",
                "prompt_version": "prod",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "teszt válasz"
    assert data["chunks"][0]["base_id"] == "hummus"
    assert data["strategy"] == "baseline"
    assert data["model"] == "gpt-4.1-mini"
    mock_run.assert_called_once()
    called_request = mock_run.call_args[0][0]
    assert called_request.question == "Hogyan készül a hummus?"
    assert called_request.session_id == "test-session"


def test_rag_query_validation_error():
    resp = client.post("/v1/rag/query", json={"question": "hi"})
    assert resp.status_code == 422


def test_rag_query_server_error():
    with patch("rag_service.main.run_rag", side_effect=RuntimeError("db down")):
        resp = client.post(
            "/v1/rag/query",
            json={"question": "q", "session_id": "s"},
        )

    assert resp.status_code == 500
    assert resp.json()["detail"] == "db down"
