from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    check_clarification,
    compare_candidate_products,
    extract_intent,
    rank_candidate_products,
    search_candidate_products,
    write_clarification,
    write_recommendation,
)
from app.agent.state import ShoppingAgentState
from app.schemas.chat import ChatRequest, ChatResponse


def route_after_clarification_check(state: ShoppingAgentState) -> str:
    return "clarify" if state.get("needs_clarification") else "search"


def build_graph():
    builder = StateGraph(ShoppingAgentState)

    builder.add_node("extract_intent", extract_intent)
    builder.add_node("check_clarification", check_clarification)
    builder.add_node("write_clarification", write_clarification)
    builder.add_node("search_products", search_candidate_products)
    builder.add_node("rank_products", rank_candidate_products)
    builder.add_node("compare_products", compare_candidate_products)
    builder.add_node("write_recommendation", write_recommendation)

    builder.add_edge(START, "extract_intent")
    builder.add_edge("extract_intent", "check_clarification")
    builder.add_conditional_edges(
        "check_clarification",
        route_after_clarification_check,
        {
            "clarify": "write_clarification",
            "search": "search_products",
        },
    )
    builder.add_edge("write_clarification", END)
    builder.add_edge("search_products", "rank_products")
    builder.add_edge("rank_products", "compare_products")
    builder.add_edge("compare_products", "write_recommendation")
    builder.add_edge("write_recommendation", END)

    return builder.compile()


shopping_graph = build_graph()


def run_shopping_agent(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or str(uuid4())
    result = shopping_graph.invoke(
        {
            "message": request.message,
            "session_id": session_id,
            "history": request.history,
        }
    )

    return ChatResponse(
        session_id=session_id,
        reply=result["reply"],
        needs_clarification=result.get("needs_clarification", False),
        clarification_questions=result.get("clarification_questions", []),
        intent=result["intent"],
        products=result.get("products", []),
        comparison=result.get("comparison"),
    )
