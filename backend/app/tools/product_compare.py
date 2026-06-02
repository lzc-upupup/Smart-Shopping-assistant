from app.schemas.product import (
    CompareResponse,
    Product,
    ProductComparison,
    ProductComparisonItem,
)


def compare_products(products: list[Product]) -> CompareResponse:
    items = [
        ProductComparisonItem(
            product_id=product.id,
            name=product.name,
            price=product.price,
            summary=_build_summary(product),
            strengths=product.pros[:3],
            weaknesses=product.cons[:3],
            best_for=product.best_for[:3],
        )
        for product in products
    ]
    winner = max(products, key=lambda item: item.score, default=None)

    comparison = ProductComparison(
        items=items,
        winner_product_id=winner.id if winner else None,
        decision_note=_build_decision_note(winner) if winner else None,
    )
    return CompareResponse(comparison=comparison)


def _build_summary(product: Product) -> str:
    specs = "，".join(f"{key}: {value}" for key, value in list(product.specs.items())[:3])
    return f"{product.brand}，{product.price} 元，评分 {product.rating}。{specs}"


def _build_decision_note(product: Product) -> str:
    reasons = "；".join(product.match_reasons[:3]) or "综合排序最高"
    return f"{product.name} 当前最值得优先考虑：{reasons}。"
