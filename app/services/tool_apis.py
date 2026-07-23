import logging
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.models import Transaction, Merchant, KYC, Wallet, Settlement, Ticket

logger = logging.getLogger("digipay.tool_apis")

class ToolAPIs:
    @staticmethod
    async def get_transaction(db: AsyncSession, txn_id: str) -> Dict[str, Any]:
        """Retrieve transaction details. Returns status, amount, utr, bank, failureReason, settlementDate."""
        logger.info(f"Tool API: get_transaction(txn_id={txn_id})")
        stmt = select(Transaction).where(Transaction.txn_id == txn_id)
        result = await db.execute(stmt)
        txn = result.scalar_one_or_none()
        
        if not txn:
            raise ValueError(f"Transaction with ID {txn_id} not found.")

        # Check for settlement details
        settlement_stmt = select(Settlement).where(Settlement.txn_id == txn_id)
        settlement_result = await db.execute(settlement_stmt)
        settlement = settlement_result.scalar_one_or_none()

        return {
            "merchantId": txn.user_id,
            "txnId": txn.txn_id,
            "status": txn.status or "FAILED",
            "amount": float(txn.amount) if txn.amount is not None else 0.0,
            "category": txn.category,
            "type": txn.type,
            "mobile": txn.mobile,
            "maskedAadhaar": txn.masked_aadhaar or "XXXX XXXX XXXX",
            "rrn": txn.rrn or "N/A",
            "date": txn.date.strftime("%Y-%m-%d %H:%M:%S") if txn.date else None,
            "disputed": bool(txn.disputed),
            "settlementStatus": settlement.status if settlement else "PENDING",
            "settlementDate": settlement.settlement_date.strftime("%Y-%m-%d %H:%M:%S") if settlement and settlement.settlement_date else None,
            "utr": settlement.utr if settlement else None,
            "failureReason": settlement.failure_reason if settlement else (txn.memo or "Unknown bank timeout")
        }

    @staticmethod
    async def get_wallet_balance(db: AsyncSession, merchant_id: str) -> Dict[str, Any]:
        """Check wallet balance for merchant. Returns balance, blocked balance, last settlement."""
        logger.info(f"Tool API: get_wallet_balance(merchant_id={merchant_id})")
        from app.services.services import DigipayService
        
        wallet = None
        try:
            stmt = select(Wallet).where(Wallet.merchant_id == merchant_id)
            result = await db.execute(stmt)
            wallet = result.scalar_one_or_none()
        except Exception as e:
            logger.info(f"Wallet table query notice: {e}")
            try:
                await db.rollback()
            except Exception:
                pass
            wallet = None

        balances_dict = await DigipayService.get_wallet_balances(db, [merchant_id])
        ledger_bal_str = balances_dict.get(merchant_id, "0.00")
        try:
            ledger_balance = float(ledger_bal_str)
        except (ValueError, TypeError):
            ledger_balance = 0.0

        balance_val = float(wallet.balance) if wallet and wallet.balance is not None else ledger_balance
        blocked_val = float(wallet.blocked_balance) if wallet and wallet.blocked_balance is not None else 0.0
        last_date = wallet.last_settlement_date.strftime("%Y-%m-%d %H:%M:%S") if wallet and wallet.last_settlement_date else None
        last_amount = float(wallet.last_settlement_amount) if wallet and wallet.last_settlement_amount is not None else 0.0

        return {
            "merchantId": merchant_id,
            "balance": balance_val,
            "blockedBalance": blocked_val,
            "lastSettlementDate": last_date,
            "lastSettlementAmount": last_amount
        }

    @staticmethod
    async def get_kyc_status(db: AsyncSession, merchant_id: str) -> Dict[str, Any]:
        """Check merchant KYC status."""
        logger.info(f"Tool API: get_kyc_status(merchant_id={merchant_id})")
        stmt = select(KYC).where(KYC.merchant_id == merchant_id)
        result = await db.execute(stmt)
        kyc = result.scalar_one_or_none()

        if not kyc:
            return {
                "merchantId": merchant_id,
                "status": "PENDING",
                "panNumber": None,
                "aadhaarNumber": None,
                "comments": "KYC details not submitted yet.",
                "updatedAt": None
            }

        return {
            "merchantId": kyc.merchant_id,
            "status": kyc.status,
            "panNumber": kyc.pan_number,
            "aadhaarNumber": kyc.aadhaar_number,
            "comments": kyc.comments,
            "updatedAt": kyc.updated_at.strftime("%Y-%m-%d %H:%M:%S") if kyc.updated_at else None
        }

    @staticmethod
    async def get_settlement_status(db: AsyncSession, txn_id: str) -> Dict[str, Any]:
        """Retrieve settlement status for transaction."""
        logger.info(f"Tool API: get_settlement_status(txn_id={txn_id})")
        stmt = select(Settlement).where(Settlement.txn_id == txn_id)
        result = await db.execute(stmt)
        settlement = result.scalar_one_or_none()

        if not settlement:
            # Check transaction first
            txn_stmt = select(Transaction).where(Transaction.txn_id == txn_id)
            txn_res = await db.execute(txn_stmt)
            txn = txn_res.scalar_one_or_none()
            if not txn:
                raise ValueError(f"No transaction or settlement record found for txnId {txn_id}")
            
            return {
                "txnId": txn_id,
                "status": "NOT_INITIATED",
                "settlementDate": None,
                "utr": None,
                "failureReason": "Settlement process has not run for this transaction yet."
            }

        return {
            "txnId": settlement.txn_id,
            "status": settlement.status,
            "settlementDate": settlement.settlement_date.strftime("%Y-%m-%d %H:%M:%S") if settlement.settlement_date else None,
            "utr": settlement.utr,
            "failureReason": settlement.failure_reason
        }

    @staticmethod
    async def get_bank_account(db: AsyncSession, merchant_id: str) -> Dict[str, Any]:
        """Retrieve bank account details linked to merchant."""
        logger.info(f"Tool API: get_bank_account(merchant_id={merchant_id})")
        stmt = select(Merchant).where(Merchant.id == merchant_id)
        result = await db.execute(stmt)
        merchant = result.scalar_one_or_none()

        if not merchant:
            raise ValueError(f"Merchant with ID {merchant_id} not found.")

        return {
            "merchantId": merchant_id,
            "bankName": merchant.bank_name,
            "bankAccountNo": merchant.bank_account_no,
            "bankIfsc": merchant.bank_ifsc
        }

    @staticmethod
    async def get_merchant(db: AsyncSession, merchant_id: str) -> Dict[str, Any]:
        """Retrieve merchant details."""
        logger.info(f"Tool API: get_merchant(merchant_id={merchant_id})")
        stmt = select(Merchant).where(Merchant.id == merchant_id)
        result = await db.execute(stmt)
        merchant = result.scalar_one_or_none()

        if not merchant:
            raise ValueError(f"Merchant with ID {merchant_id} not found.")

        return {
            "merchantId": merchant.id,
            "name": merchant.name,
            "phone": merchant.phone,
            "email": merchant.email,
            "state": merchant.state,
            "status": merchant.status
        }

    @staticmethod
    async def get_aeps_status(db: AsyncSession, txn_id: str) -> Dict[str, Any]:
        """Retrieve AePS status."""
        logger.info(f"Tool API: get_aeps_status(txn_id={txn_id})")
        stmt = select(Transaction).where(Transaction.txn_id == txn_id, Transaction.category == "AEPS")
        result = await db.execute(stmt)
        txn = result.scalar_one_or_none()

        if not txn:
            raise ValueError(f"AePS transaction with ID {txn_id} not found.")

        return {
            "txnId": txn.txn_id,
            "amount": float(txn.amount) if txn.amount is not None else 0.0,
            "status": txn.status,
            "rrn": txn.rrn,
            "deviceSno": txn.device_sno,
            "type": txn.type,
            "maskedAadhaar": txn.masked_aadhaar,
            "date": txn.date.strftime("%Y-%m-%d %H:%M:%S") if txn.date else None
        }

    @staticmethod
    async def get_matm_status(db: AsyncSession, txn_id: str) -> Dict[str, Any]:
        """Retrieve MicroATM status."""
        logger.info(f"Tool API: get_matm_status(txn_id={txn_id})")
        stmt = select(Transaction).where(Transaction.txn_id == txn_id, Transaction.category == "MATM")
        result = await db.execute(stmt)
        txn = result.scalar_one_or_none()

        if not txn:
            # Try to match MATM in type/memo
            stmt2 = select(Transaction).where(Transaction.txn_id == txn_id)
            res2 = await db.execute(stmt2)
            txn = res2.scalar_one_or_none()
            if not txn or "MATM" not in (txn.type or ""):
                raise ValueError(f"MicroATM transaction with ID {txn_id} not found.")

        return {
            "txnId": txn.txn_id,
            "amount": float(txn.amount) if txn.amount is not None else 0.0,
            "status": txn.status,
            "rrn": txn.rrn,
            "deviceSno": txn.device_sno,
            "type": txn.type,
            "date": txn.date.strftime("%Y-%m-%d %H:%M:%S") if txn.date else None
        }

    @staticmethod
    async def raise_ticket(db: AsyncSession, merchant_id: str, category: str, details: str) -> Dict[str, Any]:
        """Open a dispute/complaint ticket."""
        logger.info(f"Tool API: raise_ticket(merchant_id={merchant_id}, category={category})")
        
        # Verify merchant exists
        merchant_stmt = select(Merchant).where(Merchant.id == merchant_id)
        merchant_res = await db.execute(merchant_stmt)
        if not merchant_res.scalar_one_or_none():
            raise ValueError(f"Merchant ID {merchant_id} does not exist. Cannot raise ticket.")

        ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
        ticket = Ticket(
            id=ticket_id,
            merchant_id=merchant_id,
            category=category,
            details=details,
            status="OPEN",
            created_at=datetime.utcnow()
        )
        db.add(ticket)
        await db.flush()

        return {
            "ticketId": ticket.id,
            "merchantId": ticket.merchant_id,
            "category": ticket.category,
            "details": ticket.details,
            "status": ticket.status,
            "createdAt": ticket.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }

    @staticmethod
    async def close_ticket(db: AsyncSession, ticket_id: str) -> Dict[str, Any]:
        """Close an active support ticket."""
        logger.info(f"Tool API: close_ticket(ticket_id={ticket_id})")
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        result = await db.execute(stmt)
        ticket = result.scalar_one_or_none()

        if not ticket:
            raise ValueError(f"Ticket with ID {ticket_id} not found.")

        ticket.status = "CLOSED"
        ticket.closed_at = datetime.utcnow()
        await db.flush()

        return {
            "ticketId": ticket.id,
            "status": ticket.status,
            "closedAt": ticket.closed_at.strftime("%Y-%m-%d %H:%M:%S")
        }

    @staticmethod
    async def check_refund_eligibility(db: AsyncSession, txn_id: str) -> Dict[str, Any]:
        """Check if a transaction is eligible for refund.
        Criteria:
        1. Transaction must exist and be in 'FAILED' status.
        2. Transaction must not be already refunded (RefundLedgerStatus != 1) and not disputed.
        3. Transaction must have occurred within the last 7 days.
        """
        logger.info(f"Tool API: check_refund_eligibility(txn_id={txn_id})")
        stmt = select(Transaction).where(Transaction.txn_id == txn_id)
        result = await db.execute(stmt)
        txn = result.scalar_one_or_none()

        if not txn:
            raise ValueError(f"Transaction with ID {txn_id} not found.")

        is_failed = txn.status == "FAILED"
        not_refunded = txn.RefundLedgerStatus != 1
        not_disputed = txn.disputed == 0
        
        # Check window (last 7 days)
        within_window = True
        if txn.date:
            within_window = txn.date >= (datetime.utcnow() - timedelta(days=7))

        eligible = is_failed and not_refunded and not_disputed and within_window
        reasons = []
        if not is_failed:
            reasons.append("Transaction status is not FAILED (currently: " + str(txn.status) + ").")
        if not not_refunded:
            reasons.append("Transaction is already refunded.")
        if not not_disputed:
            reasons.append("Transaction is already disputed.")
        if not within_window:
            reasons.append("Transaction occurred outside the 7-day refund window.")

        return {
            "txnId": txn_id,
            "eligible": eligible,
            "amount": float(txn.amount) if txn.amount is not None else 0.0,
            "reasons": reasons if not eligible else ["Passes all criteria."]
        }

    @staticmethod
    async def generate_statement(db: AsyncSession, merchant_id: str, from_date: str, to_date: str) -> Dict[str, Any]:
        """Generate transactions statement for a merchant."""
        logger.info(f"Tool API: generate_statement(merchant_id={merchant_id}, from={from_date}, to={to_date})")
        
        # Verify merchant
        merchant_stmt = select(Merchant).where(Merchant.id == merchant_id)
        merchant_res = await db.execute(merchant_stmt)
        if not merchant_res.scalar_one_or_none():
            raise ValueError(f"Merchant ID {merchant_id} does not exist.")

        # Query count and totals
        stmt = select(Transaction).where(
            Transaction.user_id == merchant_id,
            Transaction.txn_date >= datetime.strptime(from_date, "%Y-%m-%d").date(),
            Transaction.txn_date <= datetime.strptime(to_date, "%Y-%m-%d").date()
        )
        res = await db.execute(stmt)
        txns = res.scalars().all()

        total_txns = len(txns)
        total_amount = sum(float(t.amount) for t in txns if t.amount is not None)

        # Generate a mock file download link
        mock_file_url = f"https://api.digipay.in/statements/stmt_{merchant_id}_{from_date}_to_{to_date}.pdf"

        return {
            "merchantId": merchant_id,
            "fromDate": from_date,
            "toDate": to_date,
            "totalTransactions": total_txns,
            "totalVolume": total_amount,
            "downloadUrl": mock_file_url
        }
