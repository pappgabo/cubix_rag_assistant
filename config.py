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

# ------------------------------------------------------------
# Backend API endpointok (dokumentum ingest)
# ------------------------------------------------------------
BACKEND_BASE_URL = "http://localhost:3000"
UPLOAD_DOCS_PATH = "/api/upload-docs"
API_URL = BACKEND_BASE_URL + UPLOAD_DOCS_PATH
CHAT_ENDPOINT = "/api/chat"
# ------------------------------------------------------------
# OpenAI / modellek
# ------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Prompt-eval judge modell
JUDGE_MODEL = "gpt-4.1-mini"

# Prompt-eval modell
PROMPT_EVAL_MODEL = "gpt-4.1-mini"

# Embedding modell RAG-hoz
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# Reranker modell RAG-hoz
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# User simulation modell-hez
SIMULATED_USER_MODEL = "gpt-4.1-mini"

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

# Táblanevek
DOCUMENTS_BASELINE_TABLE = "documents_baseline"
DOCUMENTS_CHUNKS_TABLE = "documents_chunks"

# ------------------------------------------------------------
# RAG eval fájlok
# ------------------------------------------------------------
RAG_TESTS_PATH = PROJECT_ROOT / "rag_eval" / "rag_tests.json"
RAG_RESULTS_PATH = PROJECT_ROOT / "rag_eval" / "rag_results.json"
RAG_TOP_K = 5

# ------------------------------------------------------------
# Prompt-eval fájlok
# ------------------------------------------------------------
PROMPT_TESTS_PATH = Path("prompt_eval/prompt_tests.json")
PROMPT_EVAL_RESULTS_PATH = Path("prompt_eval/prompt_eval_results.json")
PROMPT_EVAL_JUDGE_PROMPT_PATH = Path("prompt_eval/prompt_eval_judge_system.txt")
PROMPT_EVAL_JUDGE_USER_PATH = Path("prompt_eval/prompt_eval_judge_user_p.txt")

# ------------------------------------------------------------
# Beszélgetések és judge eredmények
# ------------------------------------------------------------
CONVERSATIONS_PATH = PROJECT_ROOT / "outputs/conversations.json"
JUDGE_RESULTS_PATH = PROJECT_ROOT / "outputs/judge_results.json"

# ------------------------------------------------------------
# Batch runner konfiguráció
# ------------------------------------------------------------
BATCH_CONFIG_PATH = PROJECT_ROOT / "conversation_eval" / "batch_config.yaml"


