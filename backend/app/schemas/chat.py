from pydantic import BaseModel, Field

from app.schemas.product import Product, ProductComparison


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ShoppingIntent(BaseModel):
    category: str | None = None
    budget_min: int | None = None
    budget_max: int | None = None
    use_case: str | None = None
    preferred_brands: list[str] = Field(default_factory=list)
    must_have: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    needs_clarification: bool
    clarification_questions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    intent: ShoppingIntent
    products: list[Product] = Field(default_factory=list)
    comparison: ProductComparison | None = None
