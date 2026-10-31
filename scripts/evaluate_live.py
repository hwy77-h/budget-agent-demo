"""Run fixed live DeepSeek questions against fictional data; never print the API key."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import AgentError, answer  # noqa: E402
from ledger import Ledger  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = [
    "2026 年 10 月总共花了多少？",
    "10 月餐饮花了多少？",
    "10 月哪类支出最多？",
    "10 月餐饮预算还剩多少？",
    "10 月整体预算够吗？",
    "9 月和 10 月分别花了多少？",
    "11 月花了多少？",
    "餐饮花了多少？",
    "10 月投资花了多少？",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=len(QUESTIONS))
    args = parser.parse_args()
    file_key = str(dotenv_values(ROOT / ".env").get("DEEPSEEK_API_KEY") or "").strip()
    environment_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    key = file_key if file_key and file_key != "在这里填入你自己的密钥" else environment_key
    if not key or key == "在这里填入你自己的密钥":
        raise SystemExit("尚未配置 DeepSeek 密钥；请只在本机 .env 文件中填写。")

    ledger = Ledger.from_csv(ROOT / "data" / "sample_transactions.csv", ROOT / "data" / "sample_budgets.csv")
    results = []
    for index, question in enumerate(QUESTIONS[: args.limit], start=1):
        trace: list[dict] = []
        try:
            reply = answer(question, [], ledger, api_key=key, trace=trace)
            error = None
        except AgentError as exc:
            reply = None
            error = str(exc)
        row = {"id": index, "question": question, "answer": reply, "error": error, "tools": trace}
        results.append(row)
        print(json.dumps({"id": index, "question": question, "answer": reply, "error": error, "tool_count": len(trace)}, ensure_ascii=False))
        if error and index == 1:
            break

    output = ROOT / ".eval_live.json"
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已保存 {len(results)} 条结果到本机忽略文件 {output.name}。")


if __name__ == "__main__":
    main()
