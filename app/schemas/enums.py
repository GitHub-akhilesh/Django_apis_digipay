from enum import Enum

class TxnStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"
    INITIATED = "INITIATED"
    REFUNDED = "REFUNDED"

class TxnCategory(str, Enum):
    AEPS = "AEPS"
    PAYOUT = "PAYOUT"
    DSP_TOPUP = "DSP_TOPUP"
    MATM = "MATM"
    COMMISSION = "Commission"
    TDS = "TDS"
    ALL = "ALL"

class ToolName(str, Enum):
    GET_WALLET_BALANCE = "getWalletBalance"
    GET_OLD_DIGIPAY_BALANCE = "getOldDigipayBalance"
    GET_TRANSACTION = "getTransaction"
    GET_KYC_STATUS = "getKYCStatus"
    GET_SETTLEMENT_STATUS = "getSettlementStatus"
    GET_BANK_ACCOUNT = "getBankAccount"
    GET_MERCHANT = "getMerchant"
    GET_AEPS_STATUS = "getAEPSStatus"
    GET_MATM_STATUS = "getMATMStatus"
    RAISE_TICKET = "raiseTicket"
    CLOSE_TICKET = "closeTicket"
    REFUND_ELIGIBILITY = "refundEligibility"
    GENERATE_STATEMENT = "generateStatement"
    GET_DAYWISE_REPORT = "getDaywiseReport"
    GET_TXN_LOGS = "getTxnLogs"
