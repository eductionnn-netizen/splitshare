import copy
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

from app.splitshare import calculate, format_report


class SplitShareTests(unittest.TestCase):
    def setUp(self):
        self.data = {"members": ["Аня", "Борис", "Вика"], "expenses": [
            {"payer": "Аня", "amount_kopecks": 300000,
             "participants": ["Аня", "Борис", "Вика"]},
            {"payer": "Борис", "amount_kopecks": 90000,
             "participants": ["Аня", "Борис", "Вика"]}]}

    def test_weekend_balances(self):
        self.assertEqual(calculate(self.data)["balances_kopecks"],
                         {"Аня": 170000, "Борис": -40000, "Вика": -130000})

    def test_weekend_transfers(self):
        self.assertEqual(calculate(self.data)["transfers"], [
            {"from": "Вика", "to": "Аня", "amount_kopecks": 130000},
            {"from": "Борис", "to": "Аня", "amount_kopecks": 40000}])

    def test_empty_expenses(self):
        self.data["expenses"] = []
        self.assertEqual(calculate(self.data)["transfers"], [])

    def test_rounding_preserves_every_kopeck(self):
        self.data["expenses"] = [dict(self.data["expenses"][0], amount_kopecks=100)]
        result = calculate(self.data)
        self.assertEqual(result["shares_kopecks"], {"Аня": 34, "Борис": 33, "Вика": 33})
        self.assertEqual(sum(result["balances_kopecks"].values()), 0)

    def test_payer_can_pay_for_others_only(self):
        self.data["expenses"] = [{"payer": "Аня", "amount_kopecks": 100,
                                  "participants": ["Борис", "Вика"]}]
        self.assertEqual(calculate(self.data)["balances_kopecks"],
                         {"Аня": 100, "Борис": -50, "Вика": -50})

    def test_single_person(self):
        self.assertEqual(calculate({"members": ["Аня"], "expenses": [
            {"payer": "Аня", "amount_kopecks": 1, "participants": ["Аня"]}
        ]})["transfers"], [])

    def test_invalid_amounts(self):
        for amount in [0, -1, 1.5, "100", True, None]:
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                self.data["expenses"][0]["amount_kopecks"] = amount
                calculate(self.data)

    def test_unknown_payer(self):
        self.data["expenses"][0]["payer"] = "Незнакомец"
        with self.assertRaises(ValueError):
            calculate(self.data)

    def test_invalid_participants(self):
        for participants in [[], ["Аня", "Аня"], ["Незнакомец"], [None], "Аня"]:
            with self.subTest(participants=participants), self.assertRaises(ValueError):
                self.data["expenses"][0]["participants"] = participants
                calculate(self.data)

    def test_invalid_members(self):
        for members in [[], ["Аня", "Аня"], [" "], [None], "Аня"]:
            with self.subTest(members=members), self.assertRaises(ValueError):
                calculate({"members": members, "expenses": []})

    def test_invalid_structures(self):
        for data in [[], None, {}, {"members": ["Аня"], "expenses": {}},
                     {"members": ["Аня"], "expenses": [None]}]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                calculate(data)

    def test_input_is_not_mutated(self):
        original = copy.deepcopy(self.data)
        calculate(self.data)
        self.assertEqual(self.data, original)

    def test_many_groups_settle_to_zero(self):
        rng = random.Random(42)
        for size in range(2, 12):
            members = [str(i) for i in range(size)]
            expenses = [{"payer": rng.choice(members), "amount_kopecks": rng.randint(1, 100000),
                         "participants": rng.sample(members, rng.randint(1, size))}
                        for _ in range(30)]
            result = calculate({"members": members, "expenses": expenses})
            balances = result["balances_kopecks"].copy()
            self.assertEqual(sum(balances.values()), 0)
            self.assertEqual(sum(result["shares_kopecks"].values()),
                             sum(e["amount_kopecks"] for e in expenses))
            for transfer in result["transfers"]:
                self.assertGreater(transfer["amount_kopecks"], 0)
                balances[transfer["from"]] += transfer["amount_kopecks"]
                balances[transfer["to"]] -= transfer["amount_kopecks"]
            self.assertTrue(all(value == 0 for value in balances.values()))
            self.assertLessEqual(len(result["transfers"]), size - 1)

    def test_cli_success(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, str(root / "app/splitshare.py"),
                                 str(root / "examples/weekend.json")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["currency"], "RUB")

    def test_cli_bad_json_has_nonzero_exit(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text("{broken", encoding="utf-8")
            result = subprocess.run([sys.executable, str(root / "app/splitshare.py"), str(path)],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Ошибка:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_text_report_cli(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, str(root / "app/splitshare.py"),
                                 str(root / "examples/weekend.json"), "--format", "text"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Аня: получит 1700.00 ₽", result.stdout)
        self.assertIn("Вика → Аня: 1300.00 ₽", result.stdout)
        self.assertIn("Борис → Аня: 400.00 ₽", result.stdout)

    def test_text_report_preserves_small_and_large_amounts(self):
        amount = 10 ** 20 + 1
        result = calculate({"members": ["Аня", "Борис"], "expenses": [
            {"payer": "Аня", "amount_kopecks": amount, "participants": ["Борис"]}]})
        self.assertIn("Борис → Аня: 1000000000000000000.01 ₽", format_report(result))

    def test_text_report_when_settled(self):
        self.data["expenses"] = []
        self.assertIn("Все рассчитались — переводов нет.", format_report(calculate(self.data)))


if __name__ == "__main__":
    unittest.main()
