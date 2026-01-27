# config.py

from pathlib import Path
from dotenv import load_dotenv
import os

# .env beolvasása (csak Pythonhoz)
load_dotenv()

# Projekt gyökér
PROJECT_ROOT = Path(__file__).resolve().parent

# Adat mappa (ingest.py-hoz, már most is használod)
DATA_DIR = PROJECT_ROOT / "data"

# Backend URL (ingest-hez)
BACKEND_BASE_URL = "http://localhost:3000"
UPLOAD_DOCS_PATH = "/api/upload-docs"
API_URL = BACKEND_BASE_URL + UPLOAD_DOCS_PATH

# ---- Eval specifikus configok ----

# OpenAI kulcs a Python judge-hoz - .env-ből jön
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Modellnév a judge-hoz
JUDGE_MODEL = "gpt-4.1-mini"

# Fájlnevek a beszélgetésekhez és az eredményekhez
CONVERSATIONS_PATH = PROJECT_ROOT / "conversations.json"
JUDGE_RESULTS_PATH = PROJECT_ROOT / "judge_results.json"