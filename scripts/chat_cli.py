"""Interactive Terminal CLI for chatting directly with the Multi-Agent Coffee Assistant.

Usage:
    .venv\\Scripts\\python.exe scripts/chat_cli.py
"""

import asyncio
import uuid

from src.api.dependencies import (
    get_chat_service,
    get_embeddings_client,
    get_model_client,
    get_neo4j_client,
)
from src.observability.logging import setup_logging
from src.schema.chat import ChatRequest


async def run_cli() -> None:
    setup_logging(console=False)
    chat_service = get_chat_service()
    session_id = f"cli-{uuid.uuid4().hex[:6]}"

    print("=" * 68)
    print(" ☕ HIGHLANDS COFFEE — MULTI-AGENT CHAT CLI")
    print(f" Session ID : {session_id}")
    print(" Gõ '/new' để tạo phiên mới, '/exit' hoặc 'quit' để thoát.")
    print("=" * 68)

    try:
        while True:
            try:
                user_text = input("\nBạn: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nTạm biệt!")
                break

            if not user_text:
                continue
            if user_text.lower() in {"/exit", "exit", "quit", "/quit"}:
                print("Tạm biệt!")
                break
            if user_text.lower() == "/new":
                session_id = f"cli-{uuid.uuid4().hex[:6]}"
                print(f"[Hệ thống] Đã tạo phiên mới: {session_id}")
                continue

            response = await chat_service.chat(
                ChatRequest(session_id=session_id, message=user_text)
            )
            print(f"\nBot [{response.action.value.upper()}]: {response.reply}")
    finally:
        if get_model_client.cache_info().currsize:
            await get_model_client().aclose()
        if get_embeddings_client.cache_info().currsize:
            await get_embeddings_client().aclose()
        if get_neo4j_client.cache_info().currsize:
            await get_neo4j_client().close()


if __name__ == "__main__":
    asyncio.run(run_cli())
