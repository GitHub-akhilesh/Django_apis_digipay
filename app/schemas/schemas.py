import base64
import json
from typing import List, Optional, Any
from pydantic import BaseModel, Field

# Request Schemas
class LogsRequest(BaseModel):
    cscId: str
    fromDate: str = Field(..., description="Format: DD-MM-YYYY")
    toDate: str = Field(..., description="Format: DD-MM-YYYY")
    search: str = ""
    rpp: int = 10
    cp: int = 1
    type: str

class PassbookRequest(BaseModel):
    cscId: str
    fromDate: str = Field(..., description="Format: DD-MM-YYYY")
    toDate: str = Field(..., description="Format: DD-MM-YYYY")
    search: str = ""
    rpp: int = 10
    cp: int = 1

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
