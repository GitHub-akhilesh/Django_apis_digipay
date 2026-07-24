from app.repositories.wallet_repo import WalletRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.merchant_repo import MerchantRepository
from app.repositories.kyc_repo import KYCRepository
from app.repositories.settlement_repo import SettlementRepository
from app.repositories.ticket_repo import TicketRepository

wallet_repo = WalletRepository()
txn_repo = TransactionRepository()
merchant_repo = MerchantRepository()
kyc_repo = KYCRepository()
settlement_repo = SettlementRepository()
ticket_repo = TicketRepository()

__all__ = [
    "WalletRepository", "TransactionRepository", "MerchantRepository",
    "KYCRepository", "SettlementRepository", "TicketRepository",
    "wallet_repo", "txn_repo", "merchant_repo", "kyc_repo",
    "settlement_repo", "ticket_repo"
]
