import logging
import datetime
import math
from typing import Dict, List, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.schemas.schemas import LogRecord, PassbookRecord, LogsPayload, PassbookPayload, encode_payload_to_base64

logger = logging.getLogger("digipay.services")

# Router logic for table partitioning
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

import json

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

class DigipayService:
    @staticmethod
    async def get_category_mappings(db: AsyncSession) -> Dict[int, str]:
        """Fetch and cache category mappings dynamically from category_mapping table"""
        try:
            stmt = text("SELECT id, category_name FROM category_mapping")
            res = await db.execute(stmt)
            return {int(row[0]): row[1] for row in res.fetchall()}
        except Exception as e:
            logger.warning(f"Failed to fetch category mappings: {e}")
            return {}

    @staticmethod
    async def get_txn_logs(
        db: AsyncSession,
        csc_id: str,
        from_date_str: str,
        to_date_str: str,
        search_query: str,
        rpp: int,
        cp: int,
        txn_type: str
    ) -> dict:
        # Format query dates
        from_date = parse_date(from_date_str)
        to_date = parse_date(to_date_str)
        from_datetime = datetime.datetime.combine(from_date, datetime.time.min)
        to_datetime = datetime.datetime.combine(to_date, datetime.time.max)

        # Pagination offsets
        offset = (cp - 1) * rpp

        # Determine transaction filter by type/category
        type_filter_clause = "type NOT IN ('Bio Auth', 'Bio auth', 'Cash Deposit Advice(Cash Deposit)')"
        if txn_type and txn_type != "ALL":
            if txn_type == "AEPS_CASH_WITHDRAWAL":
                type_filter_clause += " AND (category = 'AEPS' AND type = 'Cash Withdrawal')"
            elif txn_type == "AEPS_MINI_STATEMENT":
                type_filter_clause += " AND (category = 'AEPS' AND type = 'Mini Statement')"
            elif txn_type == "PAYOUT":
                type_filter_clause += " AND (category = 'PAYOUT' OR type = 'Payout')"
            elif txn_type == "DSP_TOPUP":
                type_filter_clause += " AND (category = 'DSP_TOPUP' OR type = 'DSP Topup')"
            else:
                type_filter_clause += f" AND (category = '{txn_type}' OR type = '{txn_type}')"

        search_clause = ""
        params = {
            "csc_id": csc_id,
            "from_date": from_datetime,
            "to_date": to_datetime,
            "limit": rpp,
            "offset": offset
        }

        if search_query:
            search_clause = "AND (txn_id LIKE :search OR rrn LIKE :search OR mobile LIKE :search OR memo LIKE :search)"
            params["search"] = f"%{search_query}%"

        # 1. Query Total Records count from transactions directly
        count_sql = f"""
            SELECT COUNT(*)
            FROM transactions
            WHERE user_id = :csc_id
              AND date BETWEEN :from_date AND :to_date
              AND {type_filter_clause}
              {search_clause}
        """
        try:
            count_res = await db.execute(text(count_sql), params)
            total_records = count_res.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting transactions: {e}")
            total_records = 0

        total_pages = math.ceil(total_records / rpp) if total_records > 0 else 1

        # 2. Query Page records from transactions directly
        fetch_sql = f"""
            SELECT *
            FROM transactions
            WHERE user_id = :csc_id
              AND date BETWEEN :from_date AND :to_date
              AND {type_filter_clause}
              {search_clause}
            ORDER BY date DESC, id DESC
            LIMIT :limit OFFSET :offset
        """

        try:
            res = await db.execute(text(fetch_sql), params)
            rows = res.fetchall()
            cols = res.keys()
        except Exception as e:
            logger.error(f"Error fetching transaction logs: {e}")
            rows = []
            cols = []

        records = []
        for row_tuple in rows:
            row = dict(zip(cols, row_tuple))

            raw_amt = float(row.get("amount") or 0.0)
            comm = float(row.get("commission") or 0.0)
            tds_amt = float(row.get("tds") or 0.0)
            net_amt = calculate_net_txn_amount(raw_amt, comm, tds_amt)

            dt_str = ""
            row_date = row.get("date") or row.get("txn_date")
            if isinstance(row_date, datetime.datetime):
                dt_str = row_date.strftime("%d-%m-%Y %H:%M:%S")
            elif isinstance(row_date, str):
                dt_str = row_date
            elif row_date:
                dt_str = str(row_date)

            result_str = str(row.get("status") or "FAILURE")
            remarks_str = build_remarks_from_log(row)
            raw_memo = row.get("memo")
            memo_str = str(raw_memo) if raw_memo and str(raw_memo).strip() and str(raw_memo) != 'null' else remarks_str
            masked_cust = format_masked_aadhaar(row.get("masked_aadhaar") or row.get("customer"))
            raw_cust = str(row.get("customer") or row.get("masked_aadhaar") or "")

            rec = LogRecord(
                custId=masked_cust,
                custMobile=row.get("mobile") or "0000000000",
                stateCode=0,
                districtCode=0,
                lgrAmtBefRfd=0.0,
                lgrAmtAftRfd=0.0,
                id=row.get("id") or 0,
                cscId=csc_id,
                ownerId=csc_id,
                txnId=str(row.get("txn_id") or ""),
                rrn=str(row.get("rrn") or ""),
                balance=float(row.get("walletBalance") or 0.0),
                dateTime=dt_str,
                result=result_str,
                bankIin=extract_bank_name_from_receipt(row.get("receipt")),
                deviceType=str(row.get("device_sno") or "WEB"),
                timeDiff=0,
                lgrTimeDiff=0,
                lgrAmt=abs(net_amt),
                amount=raw_amt,
                amountFormatted=inr_currency_format(raw_amt),
                memo=memo_str,
                remarks=remarks_str,
                customerId=raw_cust,
                maskedAadhaar=masked_cust
            )
            records.append(rec)

        payload = {
            "list": [r.model_dump() for r in records],
            "totalPages": total_pages,
            "currentPage": cp,
            "totalRecords": total_records
        }

        return encode_payload_to_base64(payload)

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

    @staticmethod
    async def get_passbook(
        db: AsyncSession,
        csc_id: str,
        from_date_str: str,
        to_date_str: str,
        search_query: str,
        rpp: int,
        cp: int
    ) -> dict:
        # Format dates
        from_date = parse_date(from_date_str)
        to_date = parse_date(to_date_str)
        from_datetime = datetime.datetime.combine(from_date, datetime.time.min)
        to_datetime = datetime.datetime.combine(to_date, datetime.time.max)

        # 1. Fetch running balance & balance_update_at from DigipayUsers
        running_balance = 0.0
        balance_update_at = None

        try:
            user_stmt = text("SELECT wallet_balance, balance_update_at FROM DigipayUsers WHERE user_id = :csc_id")
            user_res = await db.execute(user_stmt, {"csc_id": csc_id})
            user_row = user_res.fetchone()

            if user_row and user_row[0] not in (None, 0, '0', '0.00'):
                running_balance = float(user_row[0])
                balance_update_at = user_row[1]
            else:
                calc_dict = await DigipayService.get_wallet_balances(db, [csc_id])
                running_balance = float(calc_dict.get(csc_id, 0.0))
        except Exception as e:
            logger.warning(f"Could not fetch DigipayUsers balance for {csc_id}: {e}")

        # 2. Query transactions directly from transactions table
        params = {
            "csc_id": csc_id,
            "from_date": from_datetime,
            "to_date": to_datetime
        }

        query_sql = """
            SELECT * FROM transactions
            WHERE user_id = :csc_id
              AND status IN ('SUCCESS', 'INITIATED', 'REFUNDED')
              AND date BETWEEN :from_date AND :to_date
              AND amount != 0
            ORDER BY id DESC
        """
        try:
            res = await db.execute(text(query_sql), params)
            rows = res.fetchall()
            cols = res.keys()
        except Exception as e:
            logger.error(f"Error querying transactions table for passbook: {e}")
            rows = []
            cols = []

        all_logs = []
        for row_tuple in rows:
            txn_dict = dict(zip(cols, row_tuple))
            amt = float(txn_dict.get("amount") or 0.0)
            tds_val = float(txn_dict.get("tds") or 0.0)
            comm_val = float(txn_dict.get("commission") or 0.0)
            status_val = str(txn_dict.get("status") or "")

            # Transaction for TDS
            if tds_val != 0 and status_val == 'SUCCESS':
                tds_tx = dict(txn_dict)
                tds_tx["amount"] = -tds_val
                tds_tx["running_balance"] = running_balance
                tds_tx["category"] = "TDS"
                tds_tx["tds_category"] = txn_dict.get("category")
                running_balance = update_running_balance(tds_tx, all_logs, balance_update_at, running_balance)
                amt += tds_val

            # Transaction for Commission
            if comm_val != 0 and status_val == 'SUCCESS':
                comm_tx = dict(txn_dict)
                comm_tx["amount"] = comm_val
                comm_tx["running_balance"] = running_balance
                comm_tx["category"] = "Commission"
                comm_tx["comm_category"] = txn_dict.get("category")
                running_balance = update_running_balance(comm_tx, all_logs, balance_update_at, running_balance)
                amt -= comm_val

            # Transaction for Refunded
            if status_val == 'REFUNDED':
                ref_tx = dict(txn_dict)
                ref_tx["amount"] = abs(amt)
                ref_tx["running_balance"] = running_balance
                running_balance = update_running_balance(ref_tx, all_logs, balance_update_at, running_balance)

            txn_dict["amount"] = amt
            txn_dict["running_balance"] = running_balance
            running_balance = update_running_balance(txn_dict, all_logs, balance_update_at, running_balance)

        # 3. Filter by search query if provided
        if search_query:
            sq = search_query.lower()
            filtered_logs = [
                log for log in all_logs
                if sq in str(log.get("rrn") or "").lower()
                or sq in str(log.get("txn_id") or "").lower()
                or sq in str(log.get("remarks") or "").lower()
            ]
        else:
            filtered_logs = all_logs

        total_records = len(filtered_logs)
        total_pages = math.ceil(total_records / rpp) if total_records > 0 else 1
        offset = (cp - 1) * rpp
        page_logs = filtered_logs[offset:offset + rpp]

        records = []
        for index, log in enumerate(page_logs, start=offset + 1):
            remarks_str = build_remarks_from_log(log)
            txn_amount = float(log.get("amount") or 0.0)
            run_bal = float(log.get("running_balance") or 0.0)
            txn_type = log.get("debit_credit") or ("Credit" if txn_amount > 0 else "Debit")
            customer_str = format_masked_aadhaar(log.get("customer") or log.get("masked_aadhaar"))

            rec = PassbookRecord(
                sno=index,
                cscId=csc_id,
                cscTxn=str(log.get("txn_id") or log.get("id") or ""),
                merchantTxn=str(log.get("merchantTxn") or log.get("txn_id") or ""),
                walletAc=str(csc_id),
                txnAmount=abs(txn_amount),
                vleComm=float(log.get("commission") or 0.0),
                gst=0.0,
                interCharge=0.0,
                vleTds=float(log.get("tds") or 0.0),
                walletDeduction=abs(txn_amount),
                walletBalance=run_bal,
                rrn=str(log.get("rrn") or ""),
                category=str(log.get("category") or "AEPS"),
                txnType=txn_type,
                txnDate=str(log.get("date") or log.get("txn_date") or ""),
                creationDate=str(log.get("date") or log.get("txn_date") or ""),
                customer=customer_str,
                remarks=remarks_str,
                clientId=str(log.get("client_id") or "CSC-DGP"),
                deviceType=str(log.get("device_type") or "WEB")
            )
            records.append(rec)

        payload = {
            "list": [r.model_dump() for r in records],
            "totalPages": total_pages,
            "currentPage": cp,
            "totalRecords": total_records
        }

        return encode_payload_to_base64(payload)

    @staticmethod
    async def get_wallet_balances(db: AsyncSession, csc_ids: List[str]) -> Dict[str, str]:
        """
        Calculate wallet balance without ledger logic:
        1. Queries SUM(amount) from transactions WHERE status IN ('SUCCESS', 'INITIATED') AND user_id IN (...)
        2. Updates DigipayUsers table (wallet_balance, balance_update_at)
        3. Returns user_id -> wallet_balance dictionary.
        """
        if not csc_ids:
            return {}

        clean_csc_ids = [str(cid).strip() for cid in csc_ids if str(cid).strip()]
        if not clean_csc_ids:
            return {}

        time_now = datetime.datetime.now()
        update_time = time_now.strftime('%Y-%m-%d %H:%M:%S')

        try:
            placeholders = ", ".join([f":id_{i}" for i in range(len(clean_csc_ids))])
            params = {f"id_{i}": cid for i, cid in enumerate(clean_csc_ids)}
            params["update_time"] = update_time

            # 1. Calculate sum from transactions table
            sum_query = f"""
                SELECT user_id, COALESCE(SUM(amount), 0) AS total
                FROM transactions
                WHERE status IN ('SUCCESS', 'INITIATED') AND user_id IN ({placeholders})
                GROUP BY user_id
            """
            res = await db.execute(text(sum_query), params)
            rows = res.fetchall()
            found_balances = {str(row[0]): float(row[1]) for row in rows}

            # 2. Update DigipayUsers table for updated balance timestamps
            for cid in clean_csc_ids:
                bal = found_balances.get(cid, 0.0)
                try:
                    update_query = """
                        UPDATE DigipayUsers
                        SET wallet_balance = :bal, balance_update_at = :update_time
                        WHERE user_id = :csc_id
                    """
                    await db.execute(text(update_query), {"bal": bal, "update_time": update_time, "csc_id": cid})
                except Exception as e:
                    logger.warning(f"Note: Could not update DigipayUsers for user_id={cid}: {e}")

            await db.commit()

            # 3. Format result dictionary
            result_balances = {}
            for cid in clean_csc_ids:
                val = found_balances.get(cid, 0.0)
                result_balances[cid] = f"{val:.2f}"

            return result_balances

        except Exception as e:
            logger.error(f"Error in cal_wallet_balance / get_wallet_balances: {e}", exc_info=True)
            return {cid: "0.00" for cid in clean_csc_ids}
