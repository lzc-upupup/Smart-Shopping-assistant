from pydantic import BaseModel, Field


class Product(BaseModel):
    id: str
    name: str
    category: str
    brand: str
    price: int
    rating: float
    sales: int
    image: str
    url: str
    tags: list[str] = Field(default_factory=list)
    specs: dict[str, str] = Field(default_factory=dict)
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    best_for: list[str] = Field(default_factory=list)
    score: float = 0
    match_reasons: list[str] = Field(default_factory=list)


class ProductComparisonItem(BaseModel):
    product_id: str
    name: str
    price: int
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    best_for: list[str]


class ProductComparison(BaseModel):
    items: list[ProductComparisonItem]
    winner_product_id: str | None = None
    decision_note: str | None = None


class CompareRequest(BaseModel):
    product_ids: list[str]


class CompareResponse(BaseModel):
    comparison: ProductComparison
