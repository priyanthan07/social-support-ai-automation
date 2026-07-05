"""Grounded chat endpoint for applicants and case officers."""

from __future__ import annotations

from fastapi import APIRouter

from app.agents.chat import answer_question
from app.schemas.application import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    answer = answer_question(str(payload.application_id), payload.message)
    return ChatResponse(application_id=payload.application_id, answer=answer)
