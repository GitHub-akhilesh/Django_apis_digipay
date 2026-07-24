from typing import Dict, Any, Callable
from app.schemas.enums import ToolName
from app.services.response_builders.wallet_builder import WalletResponseBuilder
from app.services.response_builders.transaction_builder import TransactionResponseBuilder
from app.services.response_builders.kyc_builder import KYCResponseBuilder
from app.services.response_builders.settlement_builder import SettlementResponseBuilder
from app.services.response_builders.ticket_builder import TicketResponseBuilder
from app.services.response_builders.report_builder import ReportResponseBuilder

RESPONSE_FORMATTERS: Dict[str, Callable[[Dict[str, Any]], str]] = {
    ToolName.GET_WALLET_BALANCE.value: WalletResponseBuilder.format_wallet_balance,
    ToolName.GET_OLD_DIGIPAY_BALANCE.value: WalletResponseBuilder.format_old_digipay_balance,
    ToolName.GET_TRANSACTION.value: TransactionResponseBuilder.format_transaction,
    ToolName.GET_TXN_LOGS.value: TransactionResponseBuilder.format_txn_logs,
    ToolName.GENERATE_STATEMENT.value: TransactionResponseBuilder.format_statement,
    ToolName.GET_KYC_STATUS.value: KYCResponseBuilder.format_kyc_status,
    ToolName.GET_BANK_ACCOUNT.value: KYCResponseBuilder.format_bank_account,
    ToolName.GET_SETTLEMENT_STATUS.value: SettlementResponseBuilder.format_settlement,
    ToolName.RAISE_TICKET.value: TicketResponseBuilder.format_raise_ticket,
    ToolName.CLOSE_TICKET.value: TicketResponseBuilder.format_close_ticket,
    ToolName.GET_DAYWISE_REPORT.value: ReportResponseBuilder.format_daywise_report,
}

class ResponseBuilderRegistry:
    @staticmethod
    def format_response(tool_name: str, result: Dict[str, Any]) -> str:
        formatter = RESPONSE_FORMATTERS.get(tool_name)
        if formatter:
            return formatter(result)
        return f"Completed {tool_name} successfully."
