from typing import Any, Optional

def inr_currency_format(value) -> str:
    try:
        val = float(value)
        s, *d = f"{val:.2f}".split(".")
        if len(s) > 3:
            last3 = s[-3:]
            rest = s[:-3]
            groups = []
            while rest:
                groups.append(rest[-2:])
                rest = rest[:-2]
            r = ",".join(reversed(groups)) + "," + last3
        else:
            r = s
        return f"₹{r}.{d[0]}" if d else f"₹{r}"
    except (ValueError, TypeError):
        return str(value)


def calculate_net_txn_amount(amount: float, commission: float, tds: float) -> float:
    return float(amount) - float(commission) + float(tds)


def update_running_balance(
    running_balance_or_data: Any,
    amt_or_logs: Any = None,
    txn_type_or_up_at: Any = None,
    running_balance: Optional[float] = None
) -> float:
    if isinstance(running_balance_or_data, (int, float)):
        curr_bal = float(running_balance_or_data)
        amt = float(amt_or_logs or 0.0)
        txn_type = str(txn_type_or_up_at or "").lower()
        if "withdrawal" in txn_type or "payout" in txn_type or "debit" in txn_type:
            return curr_bal - amt
        return curr_bal + amt

    transaction_data = running_balance_or_data if isinstance(running_balance_or_data, dict) else {}
    logs_list = amt_or_logs if isinstance(amt_or_logs, list) else []
    curr_bal = float(running_balance or 0.0)
    amt = float(transaction_data.get('amount') or 0.0)
    curr_bal -= amt
    if isinstance(transaction_data, dict):
        transaction_data['debit_credit'] = "Credit" if amt > 0 else "Debit"
        logs_list.append(transaction_data)
    return curr_bal
