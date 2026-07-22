import base64
import json
from typing import List, Optional, Any, Union
from pydantic import BaseModel, Field, model_validator

# Request Schemas
class LogsRequest(BaseModel):
    cscId: str
    fromDate: str = Field(..., description="Format: DD-MM-YYYY")
    toDate: str = Field(..., description="Format: DD-MM-YYYY")
    search: str = ""
    rpp: int = 10
    cp: int = 1
    type: str

    @model_validator(mode='before')
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "cscId" not in data and "csc_id" in data:
                data["cscId"] = data["csc_id"]
            if "fromDate" not in data and "from_date" in data:
                data["fromDate"] = data["from_date"]
            if "toDate" not in data and "to_date" in data:
                data["toDate"] = data["to_date"]
            if "type" not in data and "txn_type" in data:
                data["type"] = data["txn_type"]
        return data

class PassbookRequest(BaseModel):
    cscId: str
    fromDate: str = Field(..., description="Format: DD-MM-YYYY")
    toDate: str = Field(..., description="Format: DD-MM-YYYY")
    search: str = ""
    rpp: int = 10
    cp: int = 1

    @model_validator(mode='before')
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "cscId" not in data and "csc_id" in data:
                data["cscId"] = data["csc_id"]
            if "fromDate" not in data and "from_date" in data:
                data["fromDate"] = data["from_date"]
            if "toDate" not in data and "to_date" in data:
                data["toDate"] = data["to_date"]
        return data

# Record Item Schemas (Internal documentation / Swagger visibility)
class LogRecord(BaseModel):
    custId: str
    custMobile: str
    stateCode: int
    districtCode: int
    lgrAmtBefRfd: float
    lgrAmtAftRfd: float
    id: int
    cscId: str
    ownerId: str
    txnId: str
    rrn: str
    balance: float
    dateTime: str
    result: str
    bankIin: str
    deviceType: str
    timeDiff: int
    lgrTimeDiff: int
    lgrAmt: float

class PassbookRecord(BaseModel):
    sno: int
    cscId: str
    cscTxn: str
    merchantTxn: str
    walletAc: str
    txnAmount: float
    vleComm: float
    gst: float
    interCharge: float
    vleTds: float
    walletDeduction: float
    walletBalance: float
    rrn: str
    category: str
    txnType: str
    txnDate: str
    creationDate: str
    customer: str
    remarks: str
    clientId: str
    deviceType: str

# Envelope Payload Structures
class LogsPayload(BaseModel):
    list: List[LogRecord]
    totalPages: int
    currentPage: int
    totalRecords: int

class PassbookPayload(BaseModel):
    list: List[PassbookRecord]
    totalPages: int
    currentPage: int
    totalRecords: int

# Generic API Response Envelopes
class EnvelopedResponse(BaseModel):
    status: str = "OK"
    msg: str = "success"
    errors: Optional[Any] = None
    resData: str  # Base64 encoded payload

def encode_payload_to_base64(payload: dict) -> str:
    """Helper to convert dictionary to json string and then to base64 string"""
    json_bytes = json.dumps(payload).encode("utf-8")
    return base64.b64encode(json_bytes).decode("utf-8")

# Auth Token Request/Response Schemas
class TokenRequest(BaseModel):
    username: str
    password: str
    cscId: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class WalletBalanceRequest(BaseModel):
    csc_ids: List[str]

    @model_validator(mode='before')
    @classmethod
    def normalize_csc_ids(cls, data: Any) -> Any:
        if isinstance(data, dict):
            raw = (
                data.get("csc_ids") 
                or data.get("cscId") 
                or data.get("csc_id") 
                or data.get("user_id") 
                or data.get("userId") 
                or data.get("merchant_id") 
                or data.get("merchantId")
            )
            if raw is not None:
                if isinstance(raw, (str, int)):
                    data["csc_ids"] = [str(raw).strip()]
                elif isinstance(raw, list):
                    data["csc_ids"] = [str(x).strip() for x in raw if str(x).strip()]
        return data


class DaywiseReportRequest(BaseModel):
    year_month: str = Field(..., description="Format: 'YYYY MonthName', e.g. '2026 June'")
    day: Optional[str] = Field(None, description="Format: 'DD', e.g. '19'")

