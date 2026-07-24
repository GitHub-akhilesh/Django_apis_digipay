import json
from typing import Optional, Any
from app.utils.money_utils import inr_currency_format
from app.utils.masking_utils import format_masked_aadhaar

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


def format_txn_memo(
    raw_memo: Optional[str] = None,
    category: Optional[str] = None,
    txn_type: Optional[str] = None,
    remarks: Optional[str] = None,
    memo: Optional[str] = None
) -> str:
    target_memo = raw_memo or memo or remarks
    if not target_memo or str(target_memo).strip() in ("", "None", "null"):
        if category and txn_type:
            return f"{category} - {txn_type}"
        return "00 - Success"
    memo_str = str(target_memo).strip()
    if remarks and remarks not in memo_str:
        return f"{memo_str} ({remarks})"
    return memo_str
