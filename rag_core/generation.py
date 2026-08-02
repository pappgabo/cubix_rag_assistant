"""Kanonikus válaszgenerálás: prompt betöltés + OpenAI chat + egységes logolás."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from openai import OpenAI

from config import OPENAI_API_KEY, RAG_CHAT_MODEL, RAG_GENERATION_TEMPERATURE, RAG_MAX_COMPLETION_TOKENS
from monitoring.log_llm_usage import log_llm_usage, calc_cost_usd
from utils.prompt_utils import load_prompt_file

from .prompts import resolve_system_prompt_path, resolve_user_prompt_path

_client = OpenAI(api_key=OPENAI_API_KEY)


def _format_context(chunk_texts: List[str]) -> str:
    return "\n\n".join(
        f"Dokumentum {i + 1}:\n{text}" for i, text in enumerate(chunk_texts)
    )


def generate_answer(
    question: str,
    chunk_texts: List[str],
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
    prompt_version: str = "prod",
) -> str:
    """RAG válasz generálása a megadott kontextusból.

    A system prompt a prompt_version szerint dől el (prod vagy kísérleti verzió).
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY hiányzik a konfigurációból.")

    start = time.perf_counter()
    r_id = request_id or str(uuid.uuid4())
    s_id = session_id or f"gen-fallback-{uuid.uuid4().hex[:6]}"

    prompt_tokens = 0
    completion_tokens = 0
    cost_usd = 0.0
    success = False
    error_msg = None
    final_text = ""

    try:
        system_message = load_prompt_file(resolve_system_prompt_path(prompt_version))
        user_template = load_prompt_file(resolve_user_prompt_path())

        user_message = user_template.format(
            question=question,
            context=_format_context(chunk_texts) or "[Nincs találat a tudásbázisban]",
        )

        resp = _client.chat.completions.create(
            model=RAG_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            max_completion_tokens=RAG_MAX_COMPLETION_TOKENS,
            temperature=RAG_GENERATION_TEMPERATURE,
            timeout=30.0,
        )

        final_text = resp.choices[0].message.content
        prompt_tokens = resp.usage.prompt_tokens
        completion_tokens = resp.usage.completion_tokens
        cost_usd = calc_cost_usd(RAG_CHAT_MODEL, prompt_tokens, completion_tokens)
        success = True

    except Exception as e:
        error_msg = str(e)
        final_text = f"Hiba a generálás során: {error_msg}"
        print(f"❌ RAG Response Error: {error_msg}")

    finally:
        latency_ms = int((time.perf_counter() - start) * 1000)
        log_llm_usage(
            {
                "timestamp": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                "sessionId": s_id,
                "requestId": r_id,
                "component": "rag-response",
                "model": RAG_CHAT_MODEL,
                "provider": "openai",
                "promptTokens": prompt_tokens,
                "completionTokens": completion_tokens,
                "totalTokens": prompt_tokens + completion_tokens,
                "costUsd": cost_usd,
                "latencyMs": latency_ms,
                "success": success,
                "errorMessage": error_msg,
            }
        )

    return final_text
