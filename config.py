# config.py

from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"

BACKEND_BASE_URL = "http://localhost:3000"
UPLOAD_DOCS_PATH = "/api/upload-docs"
API_URL = BACKEND_BASE_URL + UPLOAD_DOCS_PATH

# ---- Eval specifikus configok ----

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Modellnév a judge-hoz
JUDGE_MODEL = "gpt-4.1-mini"

# Fájlnevek a beszélgetésekhez és az eredményekhez
CONVERSATIONS_PATH = PROJECT_ROOT / "conversations.json"
JUDGE_RESULTS_PATH = PROJECT_ROOT / "judge_results.json"

# ---- RAG eval specifikus dolgok ----

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

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

RAG_TESTS_PATH = PROJECT_ROOT / "rag_eval" / "rag_tests.json"
RAG_RESULTS_PATH = PROJECT_ROOT / "rag_eval" / "rag_results.json"
RAG_TOP_K = 5