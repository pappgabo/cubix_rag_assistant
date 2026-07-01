"""Unit tesztek — metrikák, prompt betöltés, config path-ek, rag_core adatmodell."""

from config import (
    CONVERSATION_JUDGE_SYSTEM_PROMPT_PATH,
    PROMPT_EVAL_JUDGE_PROMPT_PATH,
    PROMPTS_DIR,
    RAG_EXPERIMENTS_DIR,
    RAG_SYSTEM_PROMPT_PATH,
    RAG_TESTS_PATH,
    RAG_USER_PROMPT_PATH,
    SIMULATED_USER_SYSTEM_PROMPT_PATH,
)
from rag_core.prompts import resolve_system_prompt_path, resolve_user_prompt_path
from rag_core.types import RAGRequest, RAGResponse, RetrievalStrategy, RetrievedChunk
from rag_eval.metrics import (
    eval_case,
    hit_at_k,
    mrr_at_k,
    precision_recall_at_k,
    unique_base_ids_in_order,
)
from utils.prompt_utils import load_prompt_file


# --- Prompt fájlok / életciklus ---

def test_core_prompt_files_exist():
    paths = [
        RAG_SYSTEM_PROMPT_PATH,
        RAG_USER_PROMPT_PATH,
        PROMPT_EVAL_JUDGE_PROMPT_PATH,
        CONVERSATION_JUDGE_SYSTEM_PROMPT_PATH,
        SIMULATED_USER_SYSTEM_PROMPT_PATH,
    ]
    for path in paths:
        assert path.exists(), f"Hiányzó prompt fájl: {path}"
    assert PROMPTS_DIR.is_dir()


def test_experiment_prompt_exists():
    assert (RAG_EXPERIMENTS_DIR / "system.friendly.txt").exists()


def test_resolve_system_prompt_path():
    # prod -> az élő system.txt
    assert resolve_system_prompt_path("prod") == RAG_SYSTEM_PROMPT_PATH
    # kísérleti verzió -> experiments/<verzió>.txt
    assert (
        resolve_system_prompt_path("system.friendly")
        == RAG_EXPERIMENTS_DIR / "system.friendly.txt"
    )


def test_user_template_uses_unified_placeholders():
    template = load_prompt_file(resolve_user_prompt_path())
    assert "{question}" in template
    assert "{context}" in template


# --- rag_core adatmodell ---

def test_rag_request_defaults():
    req = RAGRequest(question="Hogyan készül a hummus?", session_id="s1")
    assert req.strategy == RetrievalStrategy.BASELINE
    assert req.prompt_version == "prod"
    assert req.top_k >= 1


def test_rag_response_roundtrip():
    chunk = RetrievedChunk(doc_id="hummus", base_id="hummus", text="...", score=0.9)
    resp = RAGResponse(answer="válasz", chunks=[chunk], model="gpt-4.1-mini")
    dumped = resp.model_dump()
    assert dumped["answer"] == "válasz"
    assert dumped["chunks"][0]["base_id"] == "hummus"


def test_retrieval_strategy_values():
    assert {s.value for s in RetrievalStrategy} == {
        "baseline",
        "chunked",
        "chunked_rerank",
    }


# --- Metrikák ---

def test_precision_recall_at_k():
    expected = {"beef-tacos", "hummus"}
    retrieved = ["beef-tacos", "bagels", "hummus"]
    precision, recall = precision_recall_at_k(expected, retrieved, k=3)
    assert precision == 2 / 3
    assert recall == 1.0


def test_hit_and_mrr_at_k():
    expected = {"beef-tacos"}
    retrieved = ["bagels", "beef-tacos", "hummus"]
    assert hit_at_k(expected, retrieved, k=3) == 1.0
    assert mrr_at_k(expected, retrieved, k=3) == 0.5


def test_unique_base_ids_in_order():
    retrieved = [
        {"base_id": "a", "doc_id": "a_0"},
        {"base_id": "a", "doc_id": "a_1"},
        {"base_id": "b", "doc_id": "b_0"},
    ]
    assert unique_base_ids_in_order(retrieved, k=2) == ["a", "b"]


def test_eval_case_structure():
    metrics = eval_case({"beef-tacos"}, ["beef-tacos", "bagels"], top_k=2)
    assert metrics["precision_at_k"] == 0.5
    assert metrics["hit_at_k"] == 1.0
    assert "retrieved_ids" in metrics


def test_rag_tests_fixture_exists():
    assert RAG_TESTS_PATH.exists()
