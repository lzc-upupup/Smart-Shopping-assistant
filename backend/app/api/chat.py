from fastapi import APIRouter

from app.agent.graph import run_shopping_agent
from app.schemas.chat import ChatRequest, ChatResponse


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat_with_agent(request: ChatRequest) -> ChatResponse:
    return run_shopping_agent(request)
