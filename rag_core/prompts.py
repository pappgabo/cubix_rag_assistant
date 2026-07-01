"""Prompt feloldás a prompt életciklushoz.

- "prod"  -> prompts/rag/system.txt  (az élő, egyetlen forrás)
- egyéb   -> prompts/rag/experiments/<version>.txt  (kísérleti verziók)

Az eval alapból a prod promptot méri (regresszió), de bármelyik kísérleti
verzióra ráállítható a RAGRequest.prompt_version mezővel.
"""

from __future__ import annotations

from pathlib import Path

from config import RAG_EXPERIMENTS_DIR, RAG_SYSTEM_PROMPT_PATH, RAG_USER_PROMPT_PATH


def resolve_system_prompt_path(prompt_version: str = "prod") -> Path:
    if prompt_version == "prod":
        return RAG_SYSTEM_PROMPT_PATH
    return RAG_EXPERIMENTS_DIR / f"{prompt_version}.txt"


def resolve_user_prompt_path() -> Path:
    return RAG_USER_PROMPT_PATH
