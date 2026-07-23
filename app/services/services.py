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
        # Format in Indian numbering system
        s, *d = f"{val:.2f}".split(".")
        r = ",".join([s[-3:]] + [s[:-3][max(0, i-2):i] for i in range(len(s[:-3]), 0, -2)][::-1]) if len(s) > 3 else s
        formatted = f"₹{r}.{d[0]}" if d else f"₹{r}"
        return formatted
    except (ValueError, TypeError):
        return str(value)

def generate_remarks(
    transaction_mode: str,
    cust_id: Optional[str] = None,
    payee_details: Optional[str] = None,
    vle_account: Optional[str] = None,
    date: Optional[str] = None,
    txn_id: Optional[str] = None,
    category: Optional[str] = None
) -> str:
    remarks_dict = {
        "Cash Withdrawal AEPS": f"Pay {cust_id} ({txn_id})",
        "Cash Deposit AEPS": f"BAV {cust_id} ({txn_id})",
        "MATM": f"MATM {cust_id} ({txn_id})",
        "DMT with payee detail": f"DMT payee detail {payee_details} ({txn_id})",
        "Payout": f"PT with vle account {vle_account} ({txn_id})",
        "REFUNDED": f"Refund against {txn_id}",
        "Cash Withdrawal Commission": f"Commission {category} {date} ({txn_id})",
        "Cash Deposit Commission": f"Commission {category} {date} ({txn_id})",
        "TDS Commission": f"TDS on Commission {category} {date} ({txn_id})",
        "DSP Topup": f"DSP recharge {category} {date} ({txn_id})"
    }
    return remarks_dict.get(transaction_mode, f"Transaction {txn_id} ({category})")

def build_remarks_from_log(log: dict) -> str:
    category = str(log.get('category') or "")
    txn_type = str(log.get('type') or log.get('txnType') or "")
    txn_id = str(log.get('txn_id') or log.get('cscTxn') or log.get('merchantTxn') or log.get('isoRrn') or "")
    date_str = str(log.get('date') or log.get('txnDate') or "")
    customer = format_masked_aadhaar(log.get('customer'))

    if log.get('remarks') and log['remarks'].strip() and log['remarks'] != 'null':
        return log['remarks']

    if txn_type in ("Payout", "DSP Topup") or category in ("PAYOUT", "DSP_TOPUP"):
        if log.get("status") == 'REFUNDED' and float(log.get("amount") or log.get("txnAmount") or 0) > 0:
            return generate_remarks("REFUNDED", txn_id=txn_id)
        return generate_remarks(txn_type if txn_type in ("Payout", "DSP Topup") else "Payout", date=date_str, txn_id=txn_id, category=category)

    if "WITHDRAWAL" in category.upper() or "CASH WITHDRAWAL" in txn_type.upper():
        return generate_remarks("Cash Withdrawal AEPS", cust_id=customer, txn_id=txn_id, category="AEPS")

    if "DEPOSIT" in category.upper() or "CASH DEPOSIT" in txn_type.upper():
        return generate_remarks("Cash Deposit AEPS", cust_id=customer, txn_id=txn_id, category="AEPS")

    if category == "Commission":
        return generate_remarks("Cash Withdrawal Commission", date=date_str, txn_id=txn_id, category=log.get("comm_category", "AEPS"))

    if category == "TDS":
        return generate_remarks("TDS Commission", date=date_str, txn_id=txn_id, category=log.get("tds_category", "AEPS"))

    if category == "MATM":
        return generate_remarks("MATM", cust_id=customer, txn_id=txn_id, category="MATM")

    return f"{category} {txn_type} ({txn_id})"

class DigipayService:
    @staticmethod
    async def get_category_mappings(db: AsyncSession) -> Dict[int, str]:
        """Fetch and cache category mappings dynamically from category_mapping table"""
        try:
            stmt = text("SELECT id, category_name FROM category_mapping")
            res = await db.execute(stmt)
            return {int(row[0]): row[1] for row in res.fetchall()}
        except Exception as e:
            logger.error(f"Error fetching category mapping: {e}")
            # Static fallback mapping
            return {
                1: "AEPS_WITHDRAWAL",
                2: "AEPS_DEPOSIT",
                3: "PAYOUT",
                4: "PAYOUT_REFUND",
                5: "DSP_TOPUP",
                6: "DSP_REFUND",
                7: "VATM_WITHDRAWAL",
                8: "MATM_WITHDRAWAL",
                9: "AEPS_MINI_STATEMENT",
                10: "MATME_WITHDRAWAL",
                11: "TPPC_TRANSFER",
                12: "AEPS_REFUND",
                13: "AEPS_RECOVERY",
                14: "MATM_RECOVERY",
                15: "MATM_REFUND",
                16: "VATM_REFUND",
                17: "VATM_RECOVERY"
            }

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
        # Determine partition ledger table for cscId to run the join
        ledger_table = get_ledger_table_name(csc_id)

        # Format query dates
        from_date = parse_date(from_date_str)
        to_date = parse_date(to_date_str)

        # Pagination offsets
        offset = (cp - 1) * rpp

        # Determine transaction filter by types
        # Map requested type (e.g. AEPS_CASH_WITHDRAWAL) to DB columns
        type_filter_clause = "1=1"
        if txn_type == "AEPS_CASH_WITHDRAWAL":
            type_filter_clause = "t.category = 'AEPS' AND t.type = 'Cash Withdrawal'"
        elif txn_type == "AEPS_MINI_STATEMENT":
            type_filter_clause = "t.category = 'AEPS' AND t.type = 'Mini Statement'"
        elif txn_type == "PAYOUT":
            type_filter_clause = "t.category = 'PAYOUT' OR t.type = 'Payout'"
        elif txn_type == "DSP_TOPUP":
            type_filter_clause = "t.category = 'DSP_TOPUP' OR t.type = 'DSP Topup'"
        else:
            type_filter_clause = f"(t.category = '{txn_type}' OR t.type = '{txn_type}')"

        search_clause = ""
        params = {
            "csc_id": csc_id,
            "from_date": from_date,
            "to_date": to_date,
            "limit": rpp,
            "offset": offset
        }

        if search_query:
            search_clause = "AND (t.txn_id LIKE :search OR t.rrn LIKE :search OR t.mobile LIKE :search)"
            params["search"] = f"%{search_query}%"

        # 1. Query Total Records count
        count_sql = f"""
            SELECT COUNT(*)
            FROM transactions t
            WHERE t.user_id = :csc_id
              AND t.date BETWEEN :from_date AND :to_date
              AND {type_filter_clause}
              {search_clause}
        """
        count_res = await db.execute(text(count_sql), params)
        total_records = count_res.scalar() or 0
        total_pages = math.ceil(total_records / rpp) if total_records > 0 else 1

        # 2. Query Page records
        # Use LEFT JOIN to join transactions with partitioned ledger table
        # We dynamically select join syntax: SQLite tests don't support CONVERT, but production MySQL needs it to join different collations/charsets efficiently.
        from app.config import settings
        join_clause = "CONVERT(t.txn_id USING latin1) = l.merchantTxn"
        if settings.ENV == "TEST":
            join_clause = "t.txn_id = l.merchantTxn"

        fetch_sql = f"""
            SELECT
                t.id, t.user_id, t.txn_id, t.amount, t.type, t.status, t.date, t.category, t.mobile, t.masked_aadhaar, t.rrn,
                l.walletBalance, l.bank_iin, l.stateCode, l.districtCode
            FROM transactions t
            LEFT JOIN {ledger_table} l ON {join_clause}
            WHERE t.user_id = :csc_id
              AND t.date BETWEEN :from_date AND :to_date
              AND {type_filter_clause}
              {search_clause}
            ORDER BY t.date DESC, t.id DESC
            LIMIT :limit OFFSET :offset
        """

        res = await db.execute(text(fetch_sql), params)
        rows = res.fetchall()

        records = []
        for row in rows:
            # Map Row to LogRecord schema
            # Handle stateCode / districtCode conversions defensively
            state_code = 0
            if row.stateCode:
                try:
                    state_code = int(row.stateCode)
                except ValueError:
                    pass

            district_code = 0
            if row.districtCode:
                try:
                    district_code = int(row.districtCode)
                except ValueError:
                    pass

            # Format date: e.g. "19-06-2026 16:26:05"
            dt_str = ""
            if row.date:
                if isinstance(row.date, str):
                    try:
                        dt = datetime.datetime.strptime(row.date, "%Y-%m-%d %H:%M:%S")
                        dt_str = dt.strftime("%d-%m-%Y %H:%M:%S")
                    except ValueError:
                        try:
                            dt = datetime.datetime.strptime(row.date.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                            dt_str = dt.strftime("%d-%m-%Y %H:%M:%S")
                        except ValueError:
                            dt_str = row.date
                elif hasattr(row.date, "strftime"):
                    dt_str = row.date.strftime("%d-%m-%Y %H:%M:%S")
                else:
                    dt_str = str(row.date)

            # Map result
            result_str = row.status or "FAILURE"

            rec = LogRecord(
                custId=format_masked_aadhaar(row.masked_aadhaar),
                custMobile=row.mobile or "0000000000",
                stateCode=state_code,
                districtCode=district_code,
                lgrAmtBefRfd=0.0,
                lgrAmtAftRfd=0.0,
                id=row.id,
                cscId=row.user_id,
                ownerId=row.user_id,
                txnId=row.txn_id,
                rrn=row.rrn or "",
                balance=float(row.walletBalance) if row.walletBalance is not None else 0.0,
                dateTime=dt_str,
                result=result_str,
                bankIin=row.bank_iin or "",
                deviceType="WEB",
                timeDiff=0,
                lgrTimeDiff=0,
                lgrAmt=abs(float(row.amount)) if row.amount is not None else 0.0
            )
            records.append(rec)

        payload = {
            "list": [r.model_dump() for r in records],
            "totalPages": total_pages,
            "currentPage": cp,
            "totalRecords": total_records
        }

        # Base64 encode the payload
        return encode_payload_to_base64(payload)

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
        offset = (cp - 1) * rpp

        category_cache = await DigipayService.get_category_mappings(db)

        # 1. Fetch current wallet_balance and balance_update_at from DigipayUsers
        running_balance = 0.0
        balance_update_at = None

        try:
            user_stmt = text("SELECT wallet_balance, balance_update_at FROM DigipayUsers WHERE user_id = :csc_id")
            user_res = await db.execute(user_stmt, {"csc_id": csc_id})
            u_row = user_res.fetchone()
            if u_row and u_row[0] is not None and float(u_row[0]) > 0:
                running_balance = float(u_row[0])
                balance_update_at = u_row[1]
            else:
                balances_dict = await DigipayService.get_wallet_balances(db, [csc_id])
                running_balance = float(balances_dict.get(csc_id, 0.0))
        except Exception as e:
            logger.warning(f"DigipayUsers query note: {e}")
            balances_dict = await DigipayService.get_wallet_balances(db, [csc_id])
            running_balance = float(balances_dict.get(csc_id, 0.0))

        # 2. Query transactions table with status IN ('SUCCESS', 'INITIATED', 'REFUNDED')
        search_clause = ""
        params = {
            "csc_id": csc_id,
            "from_date": from_date,
            "to_date": to_date,
            "limit": rpp,
            "offset": offset
        }

        if search_query:
            search_clause = """
                AND (rrn LIKE :search OR txn_id LIKE :search OR memo LIKE :search OR category LIKE :search)
            """
            params["search"] = f"%{search_query}%"

        txn_sql = f"""
            SELECT * FROM transactions
            WHERE user_id = :csc_id
              AND status IN ('SUCCESS', 'INITIATED', 'REFUNDED')
              AND date BETWEEN :from_date AND :to_date
              AND amount != 0
              {search_clause}
            ORDER BY id DESC
            LIMIT :limit OFFSET :offset
        """

        raw_rows = []
        cols = []
        try:
            res = await db.execute(text(txn_sql), params)
            raw_rows = res.fetchall()
            cols = res.keys()
        except Exception as e:
            logger.warning(f"Transactions query note (falling back to ledger table): {e}")

        # Fallback to partition ledger table if transactions table is empty or missing
        if not raw_rows:
            ledger_table = get_ledger_table_name(csc_id)
            count_sql = f"""
                SELECT COUNT(*)
                FROM {ledger_table}
                WHERE cscId = :csc_id
                  AND txnDate BETWEEN :from_date AND :to_date
            """
            try:
                count_res = await db.execute(text(count_sql), {"csc_id": csc_id, "from_date": from_date, "to_date": to_date})
                total_records = count_res.scalar() or 0
            except Exception:
                total_records = 0

            fetch_sql = f"""
                SELECT *
                FROM {ledger_table}
                WHERE cscId = :csc_id
                  AND txnDate BETWEEN :from_date AND :to_date
                ORDER BY creationDate DESC, sno DESC
                LIMIT :limit OFFSET :offset
            """
            try:
                res = await db.execute(text(fetch_sql), params)
                raw_rows = res.fetchall()
                cols = res.keys()
            except Exception:
                raw_rows = []
                cols = []

        total_records = len(raw_rows) if raw_rows else 0
        total_pages = math.ceil(total_records / rpp) if total_records > 0 else 1

        records = []
        for index, row_tuple in enumerate(raw_rows, start=1):
            row_dict = dict(zip(cols, row_tuple))

            sno = row_dict.get("sno") or row_dict.get("id") or index
            csc_txn = row_dict.get("cscTxn") or row_dict.get("txn_id") or ""
            merchant_txn = row_dict.get("merchantTxn") or row_dict.get("txn_id") or ""
            wallet_ac = row_dict.get("walletAc") or csc_id
            txn_amount = float(row_dict.get("txnAmount") or row_dict.get("amount") or 0.0)

            vle_comm = float(row_dict.get("vleAmt") or row_dict.get("commission") or 0.0)
            gst = float(row_dict.get("gstAmt") or 0.0)
            inter_charge = float(row_dict.get("interChange") or 0.0)
            vle_tds = float(row_dict.get("tds") or 0.0)

            wallet_deduction = float(row_dict.get("walletTxnAmount") or abs(txn_amount))
            wallet_balance = float(row_dict.get("walletBalance") or row_dict.get("running_balance") or running_balance)
            rrn = str(row_dict.get("isoRrn") or row_dict.get("rrn") or "")

            cat_raw = row_dict.get("category") or row_dict.get("categoryId") or "AEPS"
            category_name = str(cat_raw)
            if isinstance(cat_raw, int) or (isinstance(cat_raw, str) and cat_raw.isdigit()):
                category_name = category_cache.get(int(cat_raw), "UNKNOWN")

            txn_type = str(row_dict.get("txnType") or row_dict.get("type") or ("Credit" if txn_amount > 0 else "Debit"))
            txn_date = str(row_dict.get("txnDate") or row_dict.get("date") or "")

            creation_date = txn_date
            cr_date = row_dict.get("creationDate") or row_dict.get("date")
            if isinstance(cr_date, datetime.datetime):
                creation_date = cr_date.strftime("%Y-%m-%dT%H:%M:%S.000+00:00")
            elif cr_date:
                creation_date = str(cr_date)

            customer_str = format_masked_aadhaar(row_dict.get("customer") or row_dict.get("masked_aadhaar"))
            remarks_str = build_remarks_from_log(row_dict)
            client_id = row_dict.get("clientId") or "CSC-DGP"
            device_type = row_dict.get("deviceType") or "WEB"

            rec = PassbookRecord(
                sno=sno,
                cscId=csc_id,
                cscTxn=str(csc_txn),
                merchantTxn=str(merchant_txn),
                walletAc=str(wallet_ac),
                txnAmount=txn_amount,
                vleComm=vle_comm,
                gst=gst,
                interCharge=inter_charge,
                vleTds=vle_tds,
                walletDeduction=wallet_deduction,
                walletBalance=wallet_balance,
                rrn=rrn,
                category=category_name,
                txnType=txn_type,
                txnDate=txn_date,
                creationDate=creation_date,
                customer=customer_str,
                remarks=remarks_str,
                clientId=client_id,
                deviceType=device_type
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
