import tempfile
import unittest
from pathlib import Path

from ledger import Ledger


ROOT = Path(__file__).resolve().parents[1]


class LedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = Ledger.from_csv(
            ROOT / "data" / "sample_transactions.csv",
            ROOT / "data" / "sample_budgets.csv",
        )

    def test_october_totals_are_exact(self):
        result = self.ledger.get_spending_summary("2026-10")
        self.assertEqual(result["count"], 24)
        self.assertEqual(result["total"], "2052.00")
        self.assertEqual(result["by_category"]["餐饮"], "280.00")
        self.assertEqual(result["by_category"]["礼物"], "557.00")

    def test_september_comparison_value(self):
        self.assertEqual(self.ledger.get_spending_summary("2026-09")["total"], "1838.00")

    def test_budget_overrun_and_remaining(self):
        result = self.ledger.get_budget_status("2026-10", "餐饮")
        self.assertEqual(result["total_limit"], "250.00")
        self.assertEqual(result["total_spent"], "280.00")
        self.assertEqual(result["total_remaining"], "-30.00")
        self.assertTrue(result["items"][0]["over_budget"])

    def test_month_without_records_is_not_treated_as_zero_spending(self):
        self.assertEqual(self.ledger.get_spending_summary("2026-11")["status"], "no_data")
        self.assertEqual(self.ledger.get_budget_status("2026-11")["status"], "no_data")

    def test_month_and_category_validation(self):
        with self.assertRaises(ValueError):
            self.ledger.get_spending_summary("2026-13")
        with self.assertRaises(ValueError):
            self.ledger.get_spending_summary("2026-10", "投资")

    def test_duplicate_transaction_id_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            path = Path(folder) / "transactions.csv"
            path.write_text(
                "transaction_id,date,merchant,amount,category\n"
                "T1,2026-10-01,甲,10.00,餐饮\n"
                "T1,2026-10-02,乙,20.00,餐饮\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "重复"):
                Ledger.from_csv(path, ROOT / "data" / "sample_budgets.csv")


if __name__ == "__main__":
    unittest.main()
