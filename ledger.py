"""Deterministic calculations over fictional spending records."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


CATEGORIES = ("餐饮", "交通", "购物", "学习", "娱乐", "礼物")
MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
MONEY = Decimal("0.01")


def money(value: Decimal) -> str:
    return str(value.quantize(MONEY))


def validate_month(month: str) -> None:
    if not isinstance(month, str) or not MONTH_PATTERN.fullmatch(month):
        raise ValueError("月份须为 YYYY-MM，例如 2026-10。")


def validate_category(category: str | None) -> None:
    if category is not None and category not in CATEGORIES:
        raise ValueError(f"类别须为：{'、'.join(CATEGORIES)}。")


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    date: date
    merchant: str
    amount: Decimal
    category: str

    @property
    def month(self) -> str:
        return self.date.strftime("%Y-%m")


class Ledger:
    def __init__(self, transactions: list[Transaction], budgets: dict[tuple[str, str], Decimal]):
        self.transactions = transactions
        self.budgets = budgets
        self.available_months = tuple(sorted({row.month for row in transactions}))

    @classmethod
    def from_csv(cls, transactions_path: Path, budgets_path: Path) -> "Ledger":
        transactions: list[Transaction] = []
        seen_ids: set[str] = set()
        with transactions_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != ["transaction_id", "date", "merchant", "amount", "category"]:
                raise ValueError("消费记录 CSV 表头不正确。")
            for line, row in enumerate(reader, start=2):
                tx_id = row["transaction_id"].strip()
                if not tx_id or tx_id in seen_ids:
                    raise ValueError(f"消费记录第 {line} 行编号缺失或重复。")
                seen_ids.add(tx_id)
                try:
                    day = date.fromisoformat(row["date"])
                    amount = Decimal(row["amount"])
                except (ValueError, InvalidOperation) as exc:
                    raise ValueError(f"消费记录第 {line} 行日期或金额无效。") from exc
                if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
                    raise ValueError(f"消费记录第 {line} 行金额须为大于零、最多两位小数。")
                category = row["category"].strip()
                validate_category(category)
                transactions.append(Transaction(tx_id, day, row["merchant"].strip(), amount, category))

        budgets: dict[tuple[str, str], Decimal] = {}
        with budgets_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != ["month", "category", "limit"]:
                raise ValueError("预算 CSV 表头不正确。")
            for line, row in enumerate(reader, start=2):
                month = row["month"].strip()
                category = row["category"].strip()
                validate_month(month)
                validate_category(category)
                try:
                    limit = Decimal(row["limit"])
                except InvalidOperation as exc:
                    raise ValueError(f"预算第 {line} 行金额无效。") from exc
                if not limit.is_finite() or limit < 0 or limit.as_tuple().exponent < -2:
                    raise ValueError(f"预算第 {line} 行金额须为非负、最多两位小数。")
                key = (month, category)
                if key in budgets:
                    raise ValueError(f"预算第 {line} 行月份与类别重复。")
                budgets[key] = limit
        return cls(transactions, budgets)

    def get_spending_summary(self, month: str, category: str | None = None) -> dict:
        validate_month(month)
        validate_category(category)
        if month not in self.available_months:
            return {"status": "no_data", "month": month, "message": "该月没有模拟消费记录，不能推断支出。"}
        rows = [row for row in self.transactions if row.month == month]
        if category is not None:
            rows = [row for row in rows if row.category == category]
        totals = {
            name: money(sum((row.amount for row in rows if row.category == name), Decimal("0")))
            for name in CATEGORIES
            if category is None or name == category
        }
        return {
            "status": "ok",
            "month": month,
            "category": category,
            "currency": "CNY",
            "count": len(rows),
            "total": money(sum((row.amount for row in rows), Decimal("0"))),
            "by_category": totals,
        }

    def get_budget_status(self, month: str, category: str | None = None) -> dict:
        validate_month(month)
        validate_category(category)
        if month not in self.available_months:
            return {"status": "no_data", "month": month, "message": "该月没有模拟消费记录，不能计算预算使用情况。"}
        names = (category,) if category else CATEGORIES
        missing = [name for name in names if (month, name) not in self.budgets]
        if missing:
            return {"status": "no_budget", "month": month, "missing_categories": missing}
        items = []
        for name in names:
            limit = self.budgets[(month, name)]
            spent = sum(
                (row.amount for row in self.transactions if row.month == month and row.category == name),
                Decimal("0"),
            )
            items.append({
                "category": name,
                "limit": money(limit),
                "spent": money(spent),
                "remaining": money(limit - spent),
                "over_budget": spent > limit,
            })
        return {
            "status": "ok",
            "month": month,
            "category": category,
            "currency": "CNY",
            "items": items,
            "total_limit": money(sum((Decimal(item["limit"]) for item in items), Decimal("0"))),
            "total_spent": money(sum((Decimal(item["spent"]) for item in items), Decimal("0"))),
            "total_remaining": money(sum((Decimal(item["remaining"]) for item in items), Decimal("0"))),
        }

    def get_spending_comparison(self, month_a: str, month_b: str, category: str | None = None) -> dict:
        """Compare two months; all arithmetic stays in Python."""
        first = self.get_spending_summary(month_a, category)
        second = self.get_spending_summary(month_b, category)
        if first["status"] != "ok" or second["status"] != "ok":
            return {
                "status": "no_data",
                "months_without_records": [
                    item["month"] for item in (first, second) if item["status"] != "ok"
                ],
                "message": "至少一个月份没有模拟消费记录，不能计算差额。",
            }
        return {
            "status": "ok",
            "currency": "CNY",
            "category": category,
            "month_a": month_a,
            "total_a": first["total"],
            "count_a": first["count"],
            "month_b": month_b,
            "total_b": second["total"],
            "count_b": second["count"],
            "difference_b_minus_a": money(Decimal(second["total"]) - Decimal(first["total"])),
        }
