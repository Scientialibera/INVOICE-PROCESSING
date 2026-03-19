"""SSE streaming chat endpoint powered by Microsoft Agent Framework."""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.auth.token_validator import get_current_user
from api.services.agent_factory import build_agent
from api.services.session_store import get_thread_id, set_thread_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


@router.post("")
async def chat(body: ChatRequest, user: dict = Depends(get_current_user)):
    user_id = user["oid"]
    agent, client = build_agent()

    thread_id = get_thread_id(user_id)
    if not thread_id:
        session = client.create_session()
        thread_id = session.id
        set_thread_id(user_id, thread_id)

    session = client.get_session(thread_id)

    async def event_stream():
        try:
            async for chunk in agent.run(
                message=body.message,
                session=session,
                stream=True,
            ):
                event_data = _format_chunk(chunk)
                yield f"data: {json.dumps(event_data)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as exc:
            logger.exception("Agent run failed for user %s", user_id)
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _format_chunk(chunk: Any) -> dict:
    if hasattr(chunk, "type"):
        if chunk.type == "text_delta":
            return {"type": "text", "content": chunk.text}
        if chunk.type == "tool_call":
            return {"type": "tool_call", "name": getattr(chunk, "name", ""), "status": "calling"}
        if chunk.type == "tool_result":
            return {"type": "tool_result", "name": getattr(chunk, "name", ""), "status": "complete"}
        if chunk.type == "code_interpreter_input":
            return {"type": "code", "content": chunk.input}
        if chunk.type == "code_interpreter_output":
            return {"type": "code_output", "content": getattr(chunk, "text", "")}
        if chunk.type == "image":
            return {"type": "image", "file_id": getattr(chunk, "file_id", "")}

    if isinstance(chunk, str):
        return {"type": "text", "content": chunk}

    return {"type": "unknown", "content": str(chunk)}
