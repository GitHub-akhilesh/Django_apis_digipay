import logging
from dataclasses import dataclass
from typing import Optional, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import wallet_repo
from app.repositories.settlement_repo import SettlementRepository

logger = logging.getLogger("digipay")


def _to_amount(value) -> float:
    """
    Coerce a batch-balance entry to a float.

    get_wallet_balances_batch() returns the BALANCE_UNAVAILABLE sentinel rather
    than fabricating "0.00" when it cannot determine a balance, so this is a
    string field that is not always numeric. Treat anything non-numeric as 0.0
    and let the caller's other sources decide -- never raise, or an unavailable
    balance turns into a failed request.
    """
    if value is None or value == wallet_repo.BALANCE_UNAVAILABLE:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        logger.warning("Unexpected wallet balance value %r; treating as 0.0", value)
        return 0.0

@dataclass
class WalletSnapshot:
    merchant_id: str
    active_balance: float
    blocked_balance: float
    legacy_balance: float
    last_settlement_date: Optional[str]
    last_settlement_amount: float

class WalletSnapshotService:
    """Service providing consolidated wallet balance snapshots."""

    @staticmethod
    async def get_wallet_snapshot(db: AsyncSession, merchant_id: str) -> WalletSnapshot:
        wallet = await wallet_repo.get_wallet_by_merchant_id(db, merchant_id)
        legacy_bal = await wallet_repo.get_user_legacy_balance(db, merchant_id)
        
        calc_dict = await wallet_repo.get_wallet_balances_batch(db, [merchant_id])
        calc_bal = _to_amount(calc_dict.get(merchant_id))

        last_payout = await SettlementRepository.get_last_payout_from_transactions(db, merchant_id)

        if wallet and wallet.balance is not None:
            active_balance = float(wallet.balance)
            blocked_balance = float(wallet.blocked_balance or 0.0)
            last_settlement_date = wallet.last_settlement_date.strftime("%Y-%m-%d %H:%M:%S") if wallet.last_settlement_date else (last_payout.get("date") if last_payout else None)
            last_settlement_amount = float(wallet.last_settlement_amount or 0.0) or (last_payout.get("amount", 0.0) if last_payout else 0.0)
        else:
            active_balance = legacy_bal if legacy_bal != 0.0 else calc_bal
            blocked_balance = 0.0
            last_settlement_date = last_payout.get("date") if last_payout else None
            last_settlement_amount = float(last_payout.get("amount", 0.0)) if last_payout else 0.0

        old_digipay_balance = legacy_bal if legacy_bal != 0.0 else calc_bal

        return WalletSnapshot(
            merchant_id=merchant_id,
            active_balance=active_balance,
            blocked_balance=blocked_balance,
            legacy_balance=old_digipay_balance,
            last_settlement_date=last_settlement_date,
            last_settlement_amount=last_settlement_amount
        )
