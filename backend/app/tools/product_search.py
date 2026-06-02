import json
from functools import lru_cache
from pathlib import Path

from app.schemas.chat import ShoppingIntent
from app.schemas.product import Product


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "mock_products.json"


@lru_cache
def list_products() -> list[Product]:
    with DATA_PATH.open("r", encoding="utf-8") as file:
        raw_products = json.load(file)
    return [Product(**item) for item in raw_products]


def search_products(intent: ShoppingIntent, query: str) -> list[Product]:
    products = list_products()
    scored_products = [_score_product(product, intent, query) for product in products]
    return [product for product in scored_products if product.score > 0]


def _score_product(product: Product, intent: ShoppingIntent, query: str) -> Product:
    score = 0.0
    reasons: list[str] = []

    if intent.category:
        if product.category == intent.category:
            score += 40
            reasons.append("品类匹配")
        else:
            return product.model_copy(update={"score": 0, "match_reasons": []})

    if intent.budget_max:
        if product.price <= intent.budget_max:
            score += 25
            reasons.append("在预算内")
        else:
            over_ratio = (product.price - intent.budget_max) / intent.budget_max
            score -= min(30, over_ratio * 60)
            reasons.append("略超预算")

    if intent.budget_min and product.price >= intent.budget_min:
        score += 5

    if intent.preferred_brands and product.brand in intent.preferred_brands:
        score += 18
        reasons.append("品牌偏好匹配")

    searchable_text = " ".join(
        [
            product.name,
            product.brand,
            " ".join(product.tags),
            " ".join(product.best_for),
            " ".join(product.pros),
            " ".join(product.specs.values()),
        ]
    ).lower()

    if intent.use_case and intent.use_case in searchable_text:
        score += 15
        reasons.append(f"适合{intent.use_case}")

    for feature in intent.must_have:
        if feature in searchable_text:
            score += 8
            reasons.append(f"满足{feature}")

    query_terms = [term for term in query.lower().split() if len(term) > 1]
    for term in query_terms:
        if term in searchable_text:
            score += 2

    score += product.rating * 2
    score += min(product.sales / 1000, 8)

    return product.model_copy(
        update={
            "score": round(max(score, 0), 2),
            "match_reasons": reasons,
        }
    )
