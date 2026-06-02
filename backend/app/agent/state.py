from typing import TypedDict

from app.schemas.chat import ChatMessage, ShoppingIntent
from app.schemas.product import Product, ProductComparison


class ShoppingAgentState(TypedDict, total=False):
    message: str
    session_id: str
    history: list[ChatMessage]
    intent: ShoppingIntent
    steps: list[str]
    needs_clarification: bool
    clarification_questions: list[str]
    products: list[Product]
    comparison: ProductComparison | None
    reply: str
