from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, products


app = FastAPI(
    title="Smart Shopping Agent API",
    description="FastAPI + LangGraph backend for a mock intelligent shopping assistant.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(products.router, prefix="/api")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
