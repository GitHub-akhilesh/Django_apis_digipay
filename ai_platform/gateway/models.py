from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class BaseGatewayResponse(BaseModel):
    success: bool = True
    message: str = ""
    traceId: Optional[str] = None
    requestId: Optional[str] = None

class WalletBalanceResponse(BaseGatewayResponse):
    balance: float
    currency: str = "INR"

class WalletLimitsResponse(BaseGatewayResponse):
    dailyLimit: float
    remainingLimit: float

class WalletDetailsResponse(BaseGatewayResponse):
    walletId: str
    status: str
    merchantId: str

class MerchantProfileResponse(BaseGatewayResponse):
    merchantId: str
    businessName: str
    status: str
    email: str

class MerchantStatusResponse(BaseGatewayResponse):
    status: str
    kycStatus: str
    active: bool

class LedgerStatementResponse(BaseGatewayResponse):
    merchantId: str
    entries: List[Dict[str, Any]] = Field(default_factory=list)

class TransactionResponse(BaseGatewayResponse):
    txnId: str
    amount: float
    status: str
    merchantId: str
    timestamp: str

class TransactionListResponse(BaseGatewayResponse):
    transactions: List[Dict[str, Any]] = Field(default_factory=list)

class PassbookResponse(BaseGatewayResponse):
    merchantId: str
    records: List[Dict[str, Any]] = Field(default_factory=list)

class AEPSBalanceResponse(BaseGatewayResponse):
    balance: float
    terminalId: str
    status: str

class AEPSWithdrawalResponse(BaseGatewayResponse):
    txnId: str
    amount: float
    status: str

class NotificationAlertResponse(BaseGatewayResponse):
    status: str
    sentAt: str

class TicketResponse(BaseGatewayResponse):
    ticketId: str
    merchantId: str
    category: str
    details: str
    status: str
    createdAt: str

class TicketCloseResponse(BaseGatewayResponse):
    ticketId: str
    status: str
    closedAt: str
