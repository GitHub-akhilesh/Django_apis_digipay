import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.tools import (
    WalletTool, TransactionTool, SettlementTool,
    KYCTool, MerchantTool, TicketTool, ReportTool
)

logger = logging.getLogger("digipay")

class ToolAPIs:
    """Facade wrapping domain tool implementations."""
    
    get_transaction = TransactionTool.get_transaction
    get_wallet_balance = WalletTool.get_wallet_balance
    get_old_digipay_balance = WalletTool.get_old_digipay_balance
    get_daywise_report = ReportTool.get_daywise_report
    get_txn_logs = TransactionTool.get_txn_logs
    get_kyc_status = KYCTool.get_kyc_status
    get_settlement_status = SettlementTool.get_settlement_status
    get_bank_account = MerchantTool.get_bank_account
    get_merchant = MerchantTool.get_merchant
    get_aeps_status = ReportTool.get_aeps_status
    get_matm_status = ReportTool.get_matm_status
    raise_ticket = TicketTool.raise_ticket
    close_ticket = TicketTool.close_ticket
    check_refund_eligibility = TransactionTool.check_refund_eligibility
    generate_statement = TransactionTool.generate_statement
