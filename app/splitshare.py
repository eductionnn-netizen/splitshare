"""SplitShare: integer-kopeck expense splitting and settlement suggestions."""

import argparse
import json
from pathlib import Path


def calculate(data):
    if not isinstance(data, dict):
        raise ValueError("Входные данные должны быть JSON-объектом")
    members = data.get("members")
    if not isinstance(members, list) or not members:
        raise ValueError("Нужен непустой список участников")
    if any(not isinstance(name, str) or not name.strip() for name in members):
        raise ValueError("Имена участников должны быть непустыми строками")
    if len(set(members)) != len(members):
        raise ValueError("Имена участников должны быть уникальны")
    expenses = data.get("expenses")
    if not isinstance(expenses, list):
        raise ValueError("Расходы должны быть списком")
    paid = dict.fromkeys(members, 0)
    owed = dict.fromkeys(members, 0)
    for expense in expenses:
        if not isinstance(expense, dict):
            raise ValueError("Каждый расход должен быть объектом")
        payer = expense.get("payer")
        amount = expense.get("amount_kopecks")
        participants = expense.get("participants")
        if not isinstance(payer, str) or payer not in paid:
            raise ValueError("Плательщик должен входить в группу")
        if type(amount) is not int or amount <= 0:
            raise ValueError("Сумма должна быть положительным целым числом копеек")
        if not isinstance(participants, list) or not participants:
            raise ValueError("У расхода должны быть участники")
        if any(not isinstance(name, str) or name not in paid for name in participants):
            raise ValueError("Участники расхода должны входить в группу")
        if len(set(participants)) != len(participants):
            raise ValueError("Участники расхода не должны повторяться")
        share, remainder = divmod(amount, len(participants))
        paid[payer] += amount
        for index, name in enumerate(participants):
            owed[name] += share + int(index < remainder)
    balances = {name: paid[name] - owed[name] for name in members}
    debtors = sorted([[name, -value] for name, value in balances.items() if value < 0],
                     key=lambda item: (-item[1], item[0]))
    creditors = sorted([[name, value] for name, value in balances.items() if value > 0],
                       key=lambda item: (-item[1], item[0]))
    transfers = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        amount = min(debtors[i][1], creditors[j][1])
        transfers.append({"from": debtors[i][0], "to": creditors[j][0],
                          "amount_kopecks": amount})
        debtors[i][1] -= amount
        creditors[j][1] -= amount
        if debtors[i][1] == 0:
            i += 1
        if creditors[j][1] == 0:
            j += 1
    return {"currency": "RUB", "paid_kopecks": paid, "shares_kopecks": owed,
            "balances_kopecks": balances, "transfers": transfers}


def main():
    parser = argparse.ArgumentParser(description="SplitShare — разделить расходы друзей")
    parser.add_argument("input", type=Path, help="JSON-файл группы и расходов")
    args = parser.parse_args()
    try:
        result = calculate(json.loads(args.input.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(2, "Ошибка: {}\n".format(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
