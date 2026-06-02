from fastapi import APIRouter, HTTPException

from app.schemas.product import CompareRequest, CompareResponse, Product
from app.tools.product_compare import compare_products
from app.tools.product_search import list_products


router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[Product])
def get_products(category: str | None = None) -> list[Product]:
    products = list_products()
    if category:
        products = [product for product in products if product.category == category]
    return products


@router.get("/{product_id}", response_model=Product)
def get_product(product_id: str) -> Product:
    for product in list_products():
        if product.id == product_id:
            return product
    raise HTTPException(status_code=404, detail="Product not found")


@router.post("/compare", response_model=CompareResponse)
def compare(request: CompareRequest) -> CompareResponse:
    products = [product for product in list_products() if product.id in request.product_ids]
    if not products:
        raise HTTPException(status_code=404, detail="No products found")
    return compare_products(products)
