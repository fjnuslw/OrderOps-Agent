from __future__ import annotations

import re


ORDER_OR_SELLER_ID_PATTERN = re.compile(r"\b[a-f0-9]{32}\b", re.IGNORECASE)


INJECTION_PATTERNS = (
    r"ignore\s+(all\s+)?previous",
    r"system\s+prompt",
    r"developer\s+message",
    r"bypass",
    r"jailbreak",
    r"drop\s+table",
    r"delete\s+from",
    r"update\s+\w+\s+set",
    r"insert\s+into",
    r"truncate\s+table",
    r"customer_unique_id",
    r"api[_-]?key",
    r"泄露",
    r"绕过",
    r"忽略.*指令",
    r"删除.*表",
    r"修改.*数据库",
)


def extract_hex_id(text: str) -> str | None:
    match = ORDER_OR_SELLER_ID_PATTERN.search(text)
    return None if match is None else match.group(0).lower()


def detect_prompt_injection(text: str) -> str | None:
    normalized = text.strip().lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            return f"Blocked by input guard pattern: {pattern}"
    return None


def infer_intent(message: str, user_role: str) -> str:
    text = message.lower()
    asks_policy_only = any(
        keyword in text
        for keyword in (
            "政策",
            "policy",
            "规则",
            "条款",
            "平台",
            "规定",
            "流程",
            "如何处理",
            "怎么处理",
        )
    )
    has_case_context = extract_hex_id(text) is not None or any(
        keyword in text for keyword in ("申请", "能否", "是否", "可以", "帮我", "用户", "这个订单")
    )
    if asks_policy_only and not has_case_context:
        return "policy_qa"
    if any(keyword in text for keyword in ("退款", "refund", "退货", "返款")):
        return "refund_review"
    if any(keyword in text for keyword in ("延迟", "迟到", "晚到", "送达", "赔付", "补偿", "delivery delay")):
        return "delivery_compensation"
    if any(keyword in text for keyword in ("卖家", "seller", "质量", "risk", "风险")):
        return "seller_quality"
    if user_role == "ops_admin" and any(keyword in text for keyword in ("sql", "统计", "分析", "count", "分布")):
        return "ops_sql_analysis"
    if any(keyword in text for keyword in ("政策", "policy", "规则", "条款")):
        return "policy_qa"
    return "policy_qa"


def safe_ops_sql_for_message(message: str) -> str | None:
    text = message.lower()
    if "order_status" in text or "订单状态" in text or "状态分布" in text:
        return (
            "SELECT order_status, COUNT(*) AS count "
            "FROM orders GROUP BY order_status ORDER BY count DESC"
        )
    if "ticket" in text or "工单" in text:
        return (
            "SELECT scenario, status, COUNT(*) AS count "
            "FROM support_tickets GROUP BY scenario, status ORDER BY count DESC"
        )
    return None
