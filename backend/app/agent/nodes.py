import json
import re

from app.agent.state import ShoppingAgentState
from app.llm.client import LLMError, complete_json, complete_text, is_llm_configured
from app.schemas.chat import ShoppingIntent
from app.schemas.product import Product
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

VALID_CATEGORIES = {"laptop", "headphones", "keyboard", "monitor", "phone"}
CATEGORY_ALIASES = {
    "笔记本": "laptop",
    "电脑": "laptop",
    "耳机": "headphones",
    "键盘": "keyboard",
    "显示器": "monitor",
    "屏幕": "monitor",
    "手机": "phone",
}


def extract_intent(state: ShoppingAgentState) -> ShoppingAgentState:
    fallback_intent = _extract_intent_by_rules(state["message"])
    if not is_llm_configured():
        return {
            "intent": fallback_intent,
            "steps": _append_step(state, "LLM 未配置，使用规则解析购物需求"),
        }

    try:
        payload = complete_json(
            [
                {
                    "role": "system",
                    "content": (
                        "你是购物助手的需求解析器。只输出 JSON，不要输出解释。"
                        "从用户中文购物需求和对话历史中抽取结构化信息。"
                        "category 只能是 laptop、headphones、keyboard、monitor、phone 或 null。"
                        "budget_min 和 budget_max 使用人民币整数；不要把商品型号数字当成预算。"
                        "缺失信息填 null 或空数组，不要臆测。"
                    ),
                },
                {
                    "role": "user",
                    "content": _build_intent_prompt(state),
                },
            ],
            temperature=0,
        )
        intent = _normalize_llm_intent(payload, fallback_intent)
        return {
            "intent": intent,
            "steps": _append_step(state, "LLM 已解析购物意图"),
        }
    except (LLMError, Exception):
        return {
            "intent": fallback_intent,
            "steps": _append_step(state, "LLM 解析失败，已回退到规则解析"),
        }


def _extract_intent_by_rules(message: str) -> ShoppingIntent:
    message = message.lower()

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
    return intent


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
        "steps": _append_step(state, "检查是否需要继续追问"),
    }


def write_clarification(state: ShoppingAgentState) -> ShoppingAgentState:
    questions = state.get("clarification_questions", [])
    reply = "我还需要补充一点信息，才能给出可靠推荐：\n" + "\n".join(
        f"{index + 1}. {question}" for index, question in enumerate(questions)
    )
    return {
        "reply": reply,
        "products": [],
        "comparison": None,
        "steps": _append_step(state, "生成澄清问题"),
    }


def search_candidate_products(state: ShoppingAgentState) -> ShoppingAgentState:
    products = search_products(state["intent"], state["message"])
    return {
        "products": products,
        "steps": _append_step(state, f"调用商品搜索工具，找到 {len(products)} 个候选商品"),
    }


def rank_candidate_products(state: ShoppingAgentState) -> ShoppingAgentState:
    products = sorted(state.get("products", []), key=lambda item: item.score, reverse=True)
    return {
        "products": products[:5],
        "steps": _append_step(state, "按预算、场景、品牌和评分排序候选商品"),
    }


def compare_candidate_products(state: ShoppingAgentState) -> ShoppingAgentState:
    products = state.get("products", [])[:3]
    comparison = compare_products(products).comparison if products else None
    return {
        "comparison": comparison,
        "steps": _append_step(state, "生成前三个候选商品的对比结论"),
    }


def write_recommendation(state: ShoppingAgentState) -> ShoppingAgentState:
    products = state.get("products", [])
    intent = state["intent"]

    if not products:
        return {
            "reply": "没有在 mock 商品库里找到足够匹配的商品。可以放宽预算、换一个品类，或者后续接入真实商品数据源。",
            "steps": _append_step(state, "没有足够匹配商品，返回放宽条件建议"),
        }

    if is_llm_configured():
        try:
            reply = complete_text(
                [
                    {
                        "role": "system",
                        "content": (
                            "你是谨慎的智能购物顾问。只能基于传入的 mock 商品数据回答，"
                            "不能编造商品参数、价格、优惠、库存或真实平台链接。"
                            "涉及价格、评分、销量、配置等数字时，必须和候选商品 JSON 完全一致；"
                            "不能自行概括、换算、补充品牌型号或推断性能表现。"
                            "用中文给出推荐，说明首选商品、备选商品、关键理由和风险点。"
                            "如果匹配度有限，要明确说明限制。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": _build_recommendation_prompt(state),
                    },
                ],
                temperature=0.3,
            )
            return {
                "reply": reply,
                "steps": _append_step(state, "LLM 已生成推荐说明"),
            }
        except (LLMError, Exception):
            pass

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


def _build_intent_prompt(state: ShoppingAgentState) -> str:
    history = "\n".join(
        f"{message.role}: {message.content}" for message in state.get("history", [])[-8:]
    )
    return (
        "请抽取购物需求 JSON，字段如下：\n"
        "{\n"
        '  "category": "laptop | headphones | keyboard | monitor | phone | null",\n'
        '  "budget_min": "integer | null",\n'
        '  "budget_max": "integer | null",\n'
        '  "use_case": "string | null",\n'
        '  "preferred_brands": ["string"],\n'
        '  "must_have": ["string"],\n'
        '  "exclusions": ["string"]\n'
        "}\n\n"
        f"对话历史：\n{history or '无'}\n\n"
        f"当前用户消息：{state['message']}"
    )


def _build_recommendation_prompt(state: ShoppingAgentState) -> str:
    products = [_product_to_prompt(product) for product in state.get("products", [])[:3]]
    return (
        f"用户原始需求：{state['message']}\n"
        f"结构化需求：{state['intent'].model_dump_json(ensure_ascii=False)}\n"
        f"候选商品 JSON：{json.dumps(products, ensure_ascii=False)}\n"
        f"对比结论：{state.get('comparison').model_dump_json(ensure_ascii=False) if state.get('comparison') else '无'}"
    )


def _product_to_prompt(product: Product) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "brand": product.brand,
        "category": product.category,
        "price": product.price,
        "rating": product.rating,
        "sales": product.sales,
        "tags": product.tags,
        "specs": product.specs,
        "pros": product.pros,
        "cons": product.cons,
        "best_for": product.best_for,
        "score": product.score,
        "match_reasons": product.match_reasons,
    }


def _normalize_llm_intent(payload: dict, fallback: ShoppingIntent) -> ShoppingIntent:
    category = payload.get("category") or fallback.category
    if isinstance(category, str):
        category = CATEGORY_ALIASES.get(category.strip().lower(), category.strip().lower())
    if category not in VALID_CATEGORIES:
        category = None

    budget_min = _int_or_none(payload.get("budget_min")) or fallback.budget_min
    budget_max = _int_or_none(payload.get("budget_max")) or fallback.budget_max
    return ShoppingIntent(
        category=category,
        budget_min=budget_min,
        budget_max=budget_max,
        use_case=_string_or_none(payload.get("use_case")) or fallback.use_case,
        preferred_brands=_string_list(payload.get("preferred_brands")) or fallback.preferred_brands,
        must_have=_string_list(payload.get("must_have")) or fallback.must_have,
        exclusions=_string_list(payload.get("exclusions")) or fallback.exclusions,
    )


def _append_step(state: ShoppingAgentState, step: str) -> list[str]:
    return [*state.get("steps", []), step]


def _string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _string_or_none(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_or_none(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


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
