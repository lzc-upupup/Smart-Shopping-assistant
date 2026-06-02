import re

from app.agent.state import ShoppingAgentState
from app.schemas.chat import ShoppingIntent
from app.tools.product_compare import compare_products
from app.tools.product_search import search_products


CATEGORY_KEYWORDS = {
    "laptop": ["笔记本", "电脑", "轻薄本", "游戏本", "laptop"],
    "headphones": ["耳机", "头戴", "入耳", "降噪", "headphone"],
    "keyboard": ["键盘", "机械键盘", "轴体", "keyboard"],
    "monitor": ["显示器", "屏幕", "monitor"],
    "phone": ["手机", "iphone", "安卓", "拍照"],
}

BRAND_KEYWORDS = {
    "Apple": ["苹果", "apple", "mac", "macbook", "iphone"],
    "Lenovo": ["联想", "lenovo", "thinkpad"],
    "Asus": ["华硕", "asus"],
    "Sony": ["索尼", "sony"],
    "Bose": ["bose", "博士"],
    "Logitech": ["罗技", "logitech"],
    "Keychron": ["keychron"],
    "Dell": ["戴尔", "dell"],
    "Xiaomi": ["小米", "xiaomi", "redmi"],
}

USE_CASE_KEYWORDS = {
    "剪视频": ["剪视频", "视频剪辑", "pr", "达芬奇", "渲染"],
    "编程": ["编程", "开发", "写代码", "后端", "前端"],
    "游戏": ["游戏", "电竞", "高刷", "3a"],
    "办公": ["办公", "文档", "会议", "网课"],
    "通勤": ["通勤", "地铁", "出差", "便携"],
    "降噪": ["降噪", "安静", "飞机"],
    "拍照": ["拍照", "摄影", "影像"],
}

MUST_HAVE_KEYWORDS = {
    "轻薄": ["轻薄", "便携", "不重"],
    "长续航": ["续航", "电池"],
    "高性能": ["性能", "高性能", "独显", "显卡"],
    "高刷新率": ["高刷", "刷新率"],
    "降噪": ["降噪"],
    "无线": ["无线", "蓝牙"],
    "性价比": ["性价比", "划算", "值"],
}


def extract_intent(state: ShoppingAgentState) -> ShoppingAgentState:
    message = state["message"].lower()

    category = _first_keyword_match(message, CATEGORY_KEYWORDS)
    preferred_brands = _all_keyword_matches(message, BRAND_KEYWORDS)
    use_case = _first_keyword_match(message, USE_CASE_KEYWORDS)
    must_have = _all_keyword_matches(message, MUST_HAVE_KEYWORDS)
    budget_min, budget_max = _extract_budget(message)

    intent = ShoppingIntent(
        category=category,
        budget_min=budget_min,
        budget_max=budget_max,
        use_case=use_case,
        preferred_brands=preferred_brands,
        must_have=must_have,
    )
    return {"intent": intent}


def check_clarification(state: ShoppingAgentState) -> ShoppingAgentState:
    intent = state["intent"]
    questions: list[str] = []

    if not intent.category:
        questions.append("你想买哪一类商品？比如笔记本、耳机、键盘、显示器或手机。")
    if not intent.budget_max:
        questions.append("你的预算上限大概是多少？")
    if intent.category in {"laptop", "phone"} and not intent.use_case:
        questions.append("主要使用场景是什么？比如办公、编程、游戏、剪视频或拍照。")

    return {
        "needs_clarification": len(questions) > 0,
        "clarification_questions": questions[:2],
    }


def write_clarification(state: ShoppingAgentState) -> ShoppingAgentState:
    questions = state.get("clarification_questions", [])
    reply = "我还需要补充一点信息，才能给出可靠推荐：\n" + "\n".join(
        f"{index + 1}. {question}" for index, question in enumerate(questions)
    )
    return {"reply": reply, "products": [], "comparison": None}


def search_candidate_products(state: ShoppingAgentState) -> ShoppingAgentState:
    products = search_products(state["intent"], state["message"])
    return {"products": products}


def rank_candidate_products(state: ShoppingAgentState) -> ShoppingAgentState:
    products = sorted(state.get("products", []), key=lambda item: item.score, reverse=True)
    return {"products": products[:5]}


def compare_candidate_products(state: ShoppingAgentState) -> ShoppingAgentState:
    products = state.get("products", [])[:3]
    comparison = compare_products(products).comparison if products else None
    return {"comparison": comparison}


def write_recommendation(state: ShoppingAgentState) -> ShoppingAgentState:
    products = state.get("products", [])
    intent = state["intent"]

    if not products:
        return {
            "reply": "没有在 mock 商品库里找到足够匹配的商品。可以放宽预算、换一个品类，或者后续接入真实商品数据源。",
        }

    best = products[0]
    use_case_text = f"用于{intent.use_case}" if intent.use_case else "结合你的需求"
    budget_text = f"预算 {intent.budget_max} 元以内" if intent.budget_max else "当前预算"
    reasons = "；".join(best.match_reasons[:3]) or "综合评分最高"

    alternatives = products[1:3]
    alt_text = ""
    if alternatives:
        alt_text = "\n\n可备选：" + "；".join(
            f"{item.name}（{item.price} 元）" for item in alternatives
        )

    reply = (
        f"我会优先推荐 {best.name}，价格 {best.price} 元，适合{use_case_text}。"
        f"在{budget_text}这个条件下，它的主要优势是：{reasons}。"
        f"\n\n需要注意：{'; '.join(best.cons[:2]) if best.cons else '暂无明显短板'}。"
        f"{alt_text}"
    )
    return {"reply": reply}


def _first_keyword_match(message: str, keyword_map: dict[str, list[str]]) -> str | None:
    for value, keywords in keyword_map.items():
        if any(keyword.lower() in message for keyword in keywords):
            return value
    return None


def _all_keyword_matches(message: str, keyword_map: dict[str, list[str]]) -> list[str]:
    matches = []
    for value, keywords in keyword_map.items():
        if any(keyword.lower() in message for keyword in keywords):
            matches.append(value)
    return matches


def _extract_budget(message: str) -> tuple[int | None, int | None]:
    range_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(万|千|k)?\s*(?:-|到|至|~)\s*(\d+(?:\.\d+)?)\s*(万|千|k)?",
        message,
    )
    if range_match:
        return (
            _normalize_amount(range_match.group(1), range_match.group(2)),
            _normalize_amount(range_match.group(3), range_match.group(4)),
        )

    patterns = [
        r"(?:预算|价格|价位|不超过|最高|控制在|大概)\s*(\d+(?:\.\d+)?)\s*(万|千|k)?",
        r"(\d+(?:\.\d+)?)\s*(万|千|k)?\s*(?:元|块|rmb|人民币)\s*(?:以内|以下|内|左右)?",
        r"(\d+(?:\.\d+)?)\s*(万|千|k)\s*(?:以内|以下|内|左右)?",
        r"(\d+(?:\.\d+)?)\s*(?:以内|以下|内)",
    ]

    for pattern in patterns:
        max_match = re.search(pattern, message)
        if max_match:
            unit = max_match.group(2) if len(max_match.groups()) > 1 else None
            return None, _normalize_amount(max_match.group(1), unit)

    return None, None


def _normalize_amount(value: str, unit: str | None = None) -> int:
    amount = float(value)
    if unit == "万":
        amount *= 10000
    elif unit in {"千", "k"}:
        amount *= 1000
    return int(amount)
