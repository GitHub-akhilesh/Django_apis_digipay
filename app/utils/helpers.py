import re
import json
import datetime
from typing import Optional, Any

def mask_pii(text: str) -> str:
    if not text:
        return text
    text = re.sub(r'\b\d{8}(\d{4})\b', r'XXXX XXXX \1', text)
    text = re.sub(r'\b(\d{2})\d{6}(\d{2})\b', r'\1XXXXXX\2', text)
    return text


def get_ledger_table_name(csc_id: str) -> str:
    if not csc_id:
        return "digipay_ledger"
    first_char = str(csc_id)[0]
    if first_char in "123456789":
        return f"digipay_ledger_{first_char}"
    elif first_char == "0":
        return "digipay_ledger_1"
    else:
        return "digipay_ledger"


def parse_date(date_str: str) -> datetime.date:
    """Parses date from DD-MM-YYYY format to date object"""
    try:
        return datetime.datetime.strptime(date_str, "%d-%m-%Y").date()
    except ValueError:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()


def format_masked_aadhaar(aadhaar: Optional[str]) -> str:
    if not aadhaar:
        return "XXXX XXXX XXXX"
    if "X" in aadhaar or "x" in aadhaar:
        return aadhaar
    clean = aadhaar.replace(" ", "").replace("-", "")
    if len(clean) >= 4:
        last_4 = clean[-4:]
        return f"XXXX XXXX {last_4}"
    return aadhaar


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


def generate_remarks(
    transaction_mode: str,
    cust_id: Optional[str] = None,
    payee_details: Optional[str] = None,
    vle_account: Optional[str] = None,
    date: Optional[str] = None,
    txn_id: Optional[str] = None,
    category: Optional[str] = None,
    amount: Optional[Any] = None
) -> str:
    amt_str = f" {inr_currency_format(amount)}" if amount is not None and str(amount) != '0' and str(amount) != '0.0' else ""
    remarks_dict = {
        "Cash Withdrawal AEPS": f"Pay {cust_id}{amt_str} ({txn_id})",
        "Cash Deposit AEPS": f"BAV {cust_id}{amt_str} ({txn_id})",
        "MATM": f"MATM {cust_id}{amt_str} ({txn_id})",
        "DMT with payee detail": f"DMT payee detail {payee_details}{amt_str} ({txn_id})",
        "Payout": f"PT with vle account {vle_account}{amt_str} ({txn_id})",
        "REFUNDED": f"Refund against {txn_id}{amt_str}",
        "Cash Withdrawal Commission": f"Commission {category}{amt_str} {date} ({txn_id})".strip(),
        "Cash Deposit Commission": f"Commission {category}{amt_str} {date} ({txn_id})".strip(),
        "TDS Commission": f"TDS on Commission {category}{amt_str} {date} ({txn_id})".strip(),
        "DSP Topup": f"DSP recharge {category}{amt_str} {date} ({txn_id})".strip()
    }
    return remarks_dict.get(transaction_mode, f"Transaction {txn_id}{amt_str} ({category})")


def build_remarks_from_log(log: dict) -> str:
    category = str(log.get('category') or "")
    txn_type = str(log.get('type') or log.get('txnType') or "")
    txn_id = str(log.get('txn_id') or log.get('cscTxn') or log.get('merchantTxn') or log.get('isoRrn') or "")
    date_str = str(log.get('date') or log.get('txnDate') or "")
    customer = format_masked_aadhaar(log.get('customer') or log.get('masked_aadhaar'))
    amount = log.get('amount') or log.get('txnAmount') or log.get('lgrAmt')

    if log.get('remarks') and log['remarks'].strip() and log['remarks'] != 'null':
        return log['remarks']

    if txn_type in ("Payout", "DSP Topup") or category in ("PAYOUT", "DSP_TOPUP"):
        if log.get("status") == 'REFUNDED' and float(amount or 0) > 0:
            return generate_remarks("REFUNDED", txn_id=txn_id, amount=amount)
        return generate_remarks(txn_type if txn_type in ("Payout", "DSP Topup") else "Payout", date=date_str, txn_id=txn_id, category=category, amount=amount)

    if "WITHDRAWAL" in category.upper() or "CASH WITHDRAWAL" in txn_type.upper():
        return generate_remarks("Cash Withdrawal AEPS", cust_id=customer, txn_id=txn_id, category="AEPS", amount=amount)

    if "DEPOSIT" in category.upper() or "CASH DEPOSIT" in txn_type.upper():
        return generate_remarks("Cash Deposit AEPS", cust_id=customer, txn_id=txn_id, category="AEPS", amount=amount)

    if category == "Commission":
        return generate_remarks("Cash Withdrawal Commission", date=date_str, txn_id=txn_id, category=log.get("comm_category", "AEPS"), amount=amount)

    if category == "TDS":
        return generate_remarks("TDS Commission", date=date_str, txn_id=txn_id, category=log.get("tds_category", "AEPS"), amount=amount)

    if category == "MATM":
        return generate_remarks("MATM", cust_id=customer, txn_id=txn_id, category="MATM", amount=amount)

    amt_formatted = f" {inr_currency_format(amount)}" if amount is not None else ""
    return f"{category} {txn_type}{amt_formatted} ({txn_id})"


def extract_bank_name_from_receipt(receipt_str: Optional[str]) -> str:
    if not receipt_str or receipt_str == 'null':
        return "None"
    try:
        receipt_data = json.loads(receipt_str) if isinstance(receipt_str, str) else receipt_str
        if isinstance(receipt_data, dict):
            return receipt_data.get("Bank Name") or receipt_data.get("bank_name") or "None"
    except Exception:
        pass
    return "None"


def calculate_net_txn_amount(amount: float, commission: float, tds: float) -> float:
    return float(amount) - float(commission) + float(tds)


def format_txn_memo(memo: Optional[str]) -> str:
    if not memo:
        return "00 - Success"
    memo_str = str(memo).strip()
    return memo_str


def update_running_balance(transaction_data: dict, logs_list: list, balance_update_at, running_balance: float) -> float:
    amt = float(transaction_data.get('amount') or 0.0)
    tx_date = transaction_data.get('date')

    if balance_update_at is not None and isinstance(tx_date, (datetime.datetime, str)):
        try:
            if isinstance(tx_date, str):
                tx_date_dt = datetime.datetime.strptime(tx_date.split(".")[0], "%Y-%m-%d %H:%M:%S")
            else:
                tx_date_dt = tx_date
            if isinstance(balance_update_at, str):
                bal_up_dt = datetime.datetime.strptime(balance_update_at.split(".")[0], "%Y-%m-%d %H:%M:%S")
            else:
                bal_up_dt = balance_update_at

            if tx_date_dt < bal_up_dt:
                running_balance -= amt
        except Exception:
            running_balance -= amt
    else:
        running_balance -= amt

    transaction_data['debit_credit'] = "Credit" if amt > 0 else "Debit"
    logs_list.append(transaction_data)
    return running_balance
