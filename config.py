# config.py
# ------------------------------------------------------------
# Globális konfigurációk RAG, prompt-eval és backend ingest számára
# ------------------------------------------------------------

from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# ------------------------------------------------------------
# Projekt alapútvonalak
# ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

# ------------------------------------------------------------
# Prompt fájlok
# ------------------------------------------------------------
# Élő (prod) RAG promptok — egyetlen forrás prod és eval számára.
RAG_SYSTEM_PROMPT_PATH = PROMPTS_DIR / "rag" / "system.txt"
RAG_USER_PROMPT_PATH = PROMPTS_DIR / "rag" / "user.template.txt"
# Kísérleti prompt verziók (prompt életciklus): prompts/rag/experiments/<verzió>.txt
RAG_EXPERIMENTS_DIR = PROMPTS_DIR / "rag" / "experiments"

PROMPT_EVAL_JUDGE_PROMPT_PATH = PROMPTS_DIR / "eval" / "prompt_judge_system.txt"
PROMPT_EVAL_JUDGE_USER_PATH = PROMPTS_DIR / "eval" / "prompt_judge_user.template.txt"
CONVERSATION_JUDGE_SYSTEM_PROMPT_PATH = (
    PROMPTS_DIR / "eval" / "conversation_judge_system.txt"
)
SIMULATED_USER_SYSTEM_PROMPT_PATH = (
    PROMPTS_DIR / "simulation" / "user_system.template.txt"
)

# ------------------------------------------------------------
# Backend API endpointok (dokumentum ingest)
# ------------------------------------------------------------
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:3000")
UPLOAD_DOCS_PATH = "/api/upload-docs"
API_URL = BACKEND_BASE_URL + UPLOAD_DOCS_PATH
CHAT_ENDPOINT = "/api/chat"

# ------------------------------------------------------------
# OpenAI / modellek
# ------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gpt-4.1-mini")
PROMPT_EVAL_MODEL = os.getenv("PROMPT_EVAL_MODEL", "gpt-4.1-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
RERANKER_MODEL = os.getenv(
    "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-12-v2"
)
SIMULATED_USER_MODEL = os.getenv("SIMULATED_USER_MODEL", "gpt-4.1-mini")

# RAG generálás (rag_core) — a prod TS oldal ugyanezt a CHAT_MODEL-t használja.
RAG_CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4.1-mini")
RAG_GENERATION_TEMPERATURE = float(os.getenv("RAG_GENERATION_TEMPERATURE", "0.2"))

# ------------------------------------------------------------
# PostgreSQL kapcsolat (pgvector)
# ------------------------------------------------------------
PG_DSN = os.getenv(
    "PG_DSN",
    "postgresql://{user}:{password}@{host}:{port}/{db}".format(
        user=os.getenv("PGUSER", "raguser"),
        password=os.getenv("PGPASSWORD", "ragpass"),
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        db=os.getenv("PGDATABASE", "ragdb"),
    ),
)

DOCUMENTS_BASELINE_TABLE = "documents_baseline"
DOCUMENTS_CHUNKS_TABLE = "documents_chunks"

# ------------------------------------------------------------
# RAG eval fájlok
# ------------------------------------------------------------
RAG_TESTS_PATH = PROJECT_ROOT / "rag_eval" / "rag_tests.json"
RAG_RESULTS_PATH = PROJECT_ROOT / "rag_eval" / "rag_results.json"
RAG_TOP_K = 5
# Rerank pipeline: hányszoros jelöltlistából válogat a reranker (candidate_k = top_k * ez).
RAG_CANDIDATE_MULTIPLIER = int(os.getenv("RAG_CANDIDATE_MULTIPLIER", "4"))

# ------------------------------------------------------------
# Prompt-eval fájlok
# ------------------------------------------------------------
PROMPT_TESTS_PATH = PROJECT_ROOT / "prompt_eval" / "prompt_tests.json"
PROMPT_EVAL_RESULTS_PATH = PROJECT_ROOT / "prompt_eval" / "prompt_eval_results.json"

# ------------------------------------------------------------
# Beszélgetések és judge eredmények
# ------------------------------------------------------------
CONVERSATIONS_PATH = PROJECT_ROOT / "outputs" / "conversations.json"
JUDGE_RESULTS_PATH = PROJECT_ROOT / "outputs" / "judge_results.json"

# ------------------------------------------------------------
# Batch runner konfiguráció
# ------------------------------------------------------------
BATCH_CONFIG_PATH = PROJECT_ROOT / "conversation_eval" / "batch_config.yaml"
