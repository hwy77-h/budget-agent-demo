import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from agent import AgentError, _call_tool, answer
from ledger import Ledger


ROOT = Path(__file__).resolve().parents[1]


def response(content=None, tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls or [])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def tool_call(name, arguments):
    return SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments, ensure_ascii=False)),
    )


class FakeClient:
    def __init__(self, responses=None, error=None):
        self.responses = list(responses or [])
        self.error = error
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.responses.pop(0)


class AgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = Ledger.from_csv(
            ROOT / "data" / "sample_transactions.csv",
            ROOT / "data" / "sample_budgets.csv",
        )

    def test_tool_result_returned_to_model(self):
        client = FakeClient([
            response(tool_calls=[tool_call("get_budget_status", {"month": "2026-10", "category": "餐饮"})]),
            response(content="模拟账本中，10 月餐饮超支 30.00 元。"),
        ])
        trace = []
        result = answer("10 月餐饮超支了吗？", [], self.ledger, client=client, trace=trace)
        self.assertIn("30.00", result)
        self.assertEqual(trace[0]["tool"], "get_budget_status")
        self.assertEqual(trace[0]["result"]["total_remaining"], "-30.00")
        sent = client.calls[1]["messages"]
        payload = json.loads(sent[-1]["content"])
        self.assertEqual(payload["total_remaining"], "-30.00")

    def test_invalid_tool_arguments_do_not_reach_ledger(self):
        result = _call_tool(self.ledger, "get_spending_summary", '{"month":"2026-13"}')
        self.assertEqual(result["status"], "invalid_arguments")
        result = _call_tool(self.ledger, "unknown", '{"month":"2026-10"}')
        self.assertEqual(result["status"], "invalid_arguments")

    def test_unqueried_amount_is_blocked(self):
        client = FakeClient([response(content="你花了 999 元。")])
        with self.assertRaisesRegex(AgentError, "未查询账本"):
            answer("10 月花了多少？", [], self.ledger, client=client)

    def test_amount_not_in_tool_result_is_blocked(self):
        client = FakeClient([
            response(tool_calls=[tool_call("get_spending_summary", {"month": "2026-10"})]),
            response(content="10 月支出 999 元。"),
        ])
        with self.assertRaisesRegex(AgentError, "工具未计算"):
            answer("10 月花了多少？", [], self.ledger, client=client)

    def test_clarifying_question_needs_no_tool(self):
        client = FakeClient([response(content="你想查哪个月份？")])
        self.assertEqual(answer("餐饮花了多少？", [], self.ledger, client=client), "你想查哪个月份？")

    def test_api_error_is_safe(self):
        client = FakeClient(error=RuntimeError("secret detail"))
        with self.assertRaisesRegex(AgentError, "暂时无法连接"):
            answer("10 月花了多少？", [], self.ledger, client=client)


if __name__ == "__main__":
    unittest.main()
