"""DeepSeek tool-call orchestration. The model never computes ledger totals."""

from __future__ import annotations

import json
import re
from typing import Any

from ledger import Ledger

MODEL = "deepseek-flash"
BASE_URL = "https://api.deepseek.com"
DEMO_TODAY = "2026-10-31"
AMOUNT_PATTERN = re.compile(r"(?:¥|￥|\d+(?:\.\d+)?\s*元)")

SYSTEM_PROMPT = """你是个人收支管理 Agent，操作的是完全虚构的人民币账本。
模拟当前日期是 2026-10-31；“本月”指 2026-10。“上月”指 2026-09。
只回答账本支出与预算问题。任何具体支出、预算、余额或类别排名都必须先调用工具。
金额只能来自工具结果，不能自己猜、补全或计算百分比。跨月比较可分别查询两个月。
用户没有给出月份且上下文无法确定时，先简短追问月份。没有记录或预算时明确说没有。
不要把模拟数据说成真实个人账单。不要提供投资建议或自动分类。
回答使用简洁中文，金额标注人民币。"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_spending_summary",
            "description": "查询模拟账本指定月份的支出总额、笔数和各类别金额。比较两个月时分别调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {"type": "string", "description": "YYYY-MM，例如 2026-10"},
                    "category": {
                        "type": "string",
                        "enum": ["餐饮", "交通", "购物", "学习", "娱乐", "礼物"],
                        "description": "可选；不填则查询所有类别",
                    },
                },
                "required": ["month"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_budget_status",
            "description": "查询模拟账本指定月份的预算、已用金额、剩余额度和超支情况。",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {"type": "string", "description": "YYYY-MM，例如 2026-10"},
                    "category": {
                        "type": "string",
                        "enum": ["餐饮", "交通", "购物", "学习", "娱乐", "礼物"],
                        "description": "可选；不填则查询所有类别和预算总计",
                    },
                },
                "required": ["month"],
            },
        },
    },
]


class AgentError(Exception):
    """A safe, user-facing failure message."""


def _call_tool(ledger: Ledger, name: str, raw_arguments: str) -> dict[str, Any]:
    try:
        arguments = json.loads(raw_arguments)
        if not isinstance(arguments, dict):
            raise ValueError("参数必须是对象。")
        if set(arguments) - {"month", "category"} or "month" not in arguments:
            raise ValueError("参数包含未知字段或缺少月份。")
        month = arguments["month"]
        category = arguments.get("category")
        if name == "get_spending_summary":
            return ledger.get_spending_summary(month, category)
        if name == "get_budget_status":
            return ledger.get_budget_status(month, category)
        raise ValueError("未知工具。")
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return {"status": "invalid_arguments", "message": str(exc)}


def answer(
    user_text: str,
    history: list[dict[str, str]],
    ledger: Ledger,
    api_key: str | None = None,
    client: Any | None = None,
    trace: list[dict[str, Any]] | None = None,
) -> str:
    """Return one answer. Client injection enables protocol tests without spending API credits."""
    if not user_text.strip():
        raise AgentError("请输入问题。")
    if client is None:
        if not api_key:
            raise AgentError("请先在本机配置 DEEPSEEK_API_KEY。")
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=BASE_URL, timeout=25.0, max_retries=1)

    messages: list[Any] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(
        {"role": row["role"], "content": row["content"]}
        for row in history[-8:]
        if row.get("role") in {"user", "assistant"} and isinstance(row.get("content"), str)
    )
    messages.append({"role": "user", "content": user_text.strip()})
    used_tool = False

    for _ in range(5):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                extra_body={"thinking": {"type": "disabled"}},
            )
        except Exception as exc:
            raise AgentError("DeepSeek 暂时无法连接。请检查本机网络、密钥及额度后重试。") from exc
        if not response.choices:
            raise AgentError("模型没有返回结果，请重试。")
        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", None) or []
        if tool_calls:
            used_tool = True
            messages.append(message)
            for call in tool_calls:
                result = _call_tool(ledger, call.function.name, call.function.arguments)
                if trace is not None:
                    trace.append({
                        "tool": call.function.name,
                        "arguments": call.function.arguments,
                        "result": result,
                    })
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })
            continue
        content = (getattr(message, "content", None) or "").strip()
        if not content:
            raise AgentError("模型返回了空回答，请重试。")
        if not used_tool and AMOUNT_PATTERN.search(content):
            raise AgentError("模型未查询账本就给出了金额；已阻止这条回答，请换个问法重试。")
        return content
    raise AgentError("模型连续调用工具过多，已停止本轮查询。")
