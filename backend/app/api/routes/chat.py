"""Grounded chat endpoint for applicants and case officers."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.agents.chat import answer_question
from app.db import mongo
from app.schemas.application import ChatHistoryResponse, ChatRequest, ChatResponse, ChatTurn

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    answer = answer_question(str(payload.application_id), payload.message)
    return ChatResponse(application_id=payload.application_id, answer=answer)


@router.get("/history/{application_id}", response_model=ChatHistoryResponse)
def chat_history(application_id: uuid.UUID, limit: int = 50) -> ChatHistoryResponse:
    turns = mongo.get_chat_history(str(application_id), limit=limit)
    return ChatHistoryResponse(
        application_id=application_id,
        turns=[ChatTurn(role=t["role"], content=t["content"]) for t in turns],
    )
