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
    # If already masked, return it
    if "X" in aadhaar or "x" in aadhaar:
        return aadhaar
    # Mask it (standard 12 digits Aadhaar: XXXX XXXX 1234)
    clean = aadhaar.replace(" ", "").replace("-", "")
    if len(clean) >= 4:
        last_4 = clean[-4:]
        return f"XXXX XXXX {last_4}"
    return aadhaar

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
              AND t.txn_date BETWEEN :from_date AND :to_date
              AND {type_filter_clause}
              {search_clause}
        """
        count_res = await db.execute(text(count_sql), params)
        total_records = count_res.scalar() or 0
        total_pages = math.ceil(total_records / rpp) if total_records > 0 else 1
        
        # 2. Query Page records
        # Use LEFT JOIN to join transactions with partitioned ledger table
        fetch_sql = f"""
            SELECT 
                t.id, t.user_id, t.txn_id, t.amount, t.type, t.status, t.date, t.category, t.mobile, t.masked_aadhaar, t.rrn,
                l.walletBalance, l.bank_iin, l.stateCode, l.districtCode
            FROM transactions t
            LEFT JOIN {ledger_table} l ON t.txn_id = l.merchantTxn
            WHERE t.user_id = :csc_id 
              AND t.txn_date BETWEEN :from_date AND :to_date
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
        # Determine partition ledger table for cscId
        ledger_table = get_ledger_table_name(csc_id)
        
        # Format dates
        from_date = parse_date(from_date_str)
        to_date = parse_date(to_date_str)
        
        # Pagination offsets
        offset = (cp - 1) * rpp
        
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
                AND (merchantTxn LIKE :search OR cscTxn LIKE :search 
                     OR isoRrn LIKE :search OR remarks LIKE :search OR customer LIKE :search)
            """
            params["search"] = f"%{search_query}%"
            
        # Load category mappings dynamically
        category_cache = await DigipayService.get_category_mappings(db)
        
        # 1. Query Total count in partition ledger
        count_sql = f"""
            SELECT COUNT(*) 
            FROM {ledger_table}
            WHERE cscId = :csc_id 
              AND txnDate BETWEEN :from_date AND :to_date
              {search_clause}
        """
        count_res = await db.execute(text(count_sql), params)
        total_records = count_res.scalar() or 0
        total_pages = math.ceil(total_records / rpp) if total_records > 0 else 1
        
        # 2. Query Page records from partition ledger
        fetch_sql = f"""
            SELECT *
            FROM {ledger_table}
            WHERE cscId = :csc_id
              AND txnDate BETWEEN :from_date AND :to_date
              {search_clause}
            ORDER BY creationDate DESC, sno DESC
            LIMIT :limit OFFSET :offset
        """
        
        res = await db.execute(text(fetch_sql), params)
        rows = res.fetchall()
        cols = res.keys()
        
        records = []
        for row_tuple in rows:
            # Map dynamic row columns cleanly
            row_dict = dict(zip(cols, row_tuple))
            
            sno = row_dict.get("sno", 0)
            csc_txn = row_dict.get("cscTxn") or row_dict.get("reqCode") or ""
            merchant_txn = row_dict.get("merchantTxn") or ""
            wallet_ac = row_dict.get("walletAc") or csc_id
            txn_amount = float(row_dict.get("txnAmount") or 0.0)
            
            # Map commission, gst, tds, intercharge
            vle_comm = float(row_dict.get("vleAmt") or 0.0)
            gst = float(row_dict.get("gstAmt") or 0.0)
            inter_charge = float(row_dict.get("interChange") or 0.0)
            vle_tds = float(row_dict.get("tds") or 0.0)
            
            # Map wallet deduction
            wallet_deduction = float(row_dict.get("walletTxnAmount") or row_dict.get("txnAmount") or 0.0)
            wallet_balance = float(row_dict.get("walletBalance") or 0.0)
            rrn = row_dict.get("isoRrn") or ""
            
            # Lookup category name from mapping cache
            category_id = row_dict.get("categoryId")
            category_name = "UNKNOWN"
            if category_id is not None:
                category_name = category_cache.get(int(category_id), "UNKNOWN")
            else:
                # Guess from remarks if categoryId column doesn't exist
                remarks_lower = (row_dict.get("remarks") or "").lower()
                if "mini statement" in remarks_lower or "ms/" in remarks_lower:
                    category_name = "AEPS_MINI_STATEMENT"
                elif "cash withdrawal" in remarks_lower or "cw/" in remarks_lower:
                    category_name = "AEPS_CASH_WITHDRAWAL"
                elif "payout" in remarks_lower:
                    category_name = "PAYOUT"
                elif "topup" in remarks_lower:
                    category_name = "DSP_TOPUP"
            
            # Adapt to user's exact response naming
            if category_name == "AEPS_WITHDRAWAL":
                category_name = "AEPS_CASH_WITHDRAWAL"
                
            txn_type = row_dict.get("txnType") or "Cr"
            txn_date = str(row_dict.get("txnDate") or "")
            
            creation_date = ""
            cr_date = row_dict.get("creationDate")
            if isinstance(cr_date, datetime.datetime):
                creation_date = cr_date.strftime("%Y-%m-%dT%H:%M:%S.000+00:00")
            elif isinstance(cr_date, str):
                try:
                    dt = datetime.datetime.strptime(cr_date, "%Y-%m-%d %H:%M:%S")
                    creation_date = dt.strftime("%Y-%m-%dT%H:%M:%S.000+00:00")
                except ValueError:
                    try:
                        dt = datetime.datetime.strptime(cr_date.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                        creation_date = dt.strftime("%Y-%m-%dT%H:%M:%S.000+00:00")
                    except ValueError:
                        creation_date = cr_date
            elif cr_date:
                creation_date = str(cr_date)
                
            customer_str = format_masked_aadhaar(row_dict.get("customer"))
            remarks_str = row_dict.get("remarks") or ""
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
                rrn=str(rrn),
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
