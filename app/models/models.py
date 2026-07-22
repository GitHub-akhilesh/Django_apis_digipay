from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, Date, BigInteger, JSON
from app.database import Base

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(45), nullable=False, index=True)
    txn_id = Column(String(45), nullable=False, unique=True)
    amount = Column(DECIMAL(8, 2), nullable=True)
    type = Column(String(45), nullable=True)
    memo = Column(String(200), nullable=True)
    status = Column(String(45), nullable=True, index=True)
    ip_address = Column(String(100), nullable=True)
    date = Column(DateTime, nullable=True, index=True)
    category = Column(String(45), nullable=True, index=True)
    mobile = Column(String(10), nullable=True)
    masked_aadhaar = Column(String(15), nullable=True)
    rrn = Column(String(12), nullable=True, index=True)
    receipt = Column(JSON, nullable=True)
    disputed = Column(Integer, default=0)
    device_sno = Column(String(25), default="NA")
    user_consent = Column(String(6), default="NO")
    device_data = Column(JSON, nullable=True)
    commission = Column(DECIMAL(4, 2), default=0.0)
    tds = Column(DECIMAL(4, 2), default=0.0)
    RefundLedgerStatus = Column(Integer, default=0, index=True)
    txn_date = Column(Date, nullable=False, index=True)
    receipt_id = Column(String(35), nullable=True)

class CategoryMapping(Base):
    __tablename__ = "category_mapping"
    
    id = Column(BigInteger, primary_key=True, index=True)
    service = Column(String(50), nullable=False)
    txn_type = Column(String(50), nullable=False)
    category_name = Column(String(100), nullable=False)
    category_description = Column(String(100), nullable=True)

class Merchant(Base):
    __tablename__ = "merchants"
    
    id = Column(String(45), primary_key=True, index=True) # corresponds to cscId
    name = Column(String(100), nullable=False)
    phone = Column(String(15), nullable=True)
    email = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    status = Column(String(20), default="ACTIVE") # ACTIVE, INACTIVE, SUSPENDED
    bank_name = Column(String(100), nullable=True)
    bank_account_no = Column(String(30), nullable=True)
    bank_ifsc = Column(String(20), nullable=True)

class KYC(Base):
    __tablename__ = "kyc_details"
    
    merchant_id = Column(String(45), primary_key=True, index=True)
    status = Column(String(20), default="PENDING") # APPROVED, PENDING, REJECTED
    pan_number = Column(String(15), nullable=True)
    aadhaar_number = Column(String(15), nullable=True)
    comments = Column(String(255), nullable=True)
    updated_at = Column(DateTime, nullable=True)

class Wallet(Base):
    __tablename__ = "wallets"
    
    merchant_id = Column(String(45), primary_key=True, index=True)
    balance = Column(DECIMAL(12, 2), default=0.0)
    blocked_balance = Column(DECIMAL(12, 2), default=0.0)
    last_settlement_date = Column(DateTime, nullable=True)
    last_settlement_amount = Column(DECIMAL(12, 2), default=0.0)

class Settlement(Base):
    __tablename__ = "settlements"
    
    txn_id = Column(String(45), primary_key=True, index=True)
    status = Column(String(45), nullable=False) # processed, initiated, failed, auto-reversal-initiated
    settlement_date = Column(DateTime, nullable=True)
    utr = Column(String(50), nullable=True)
    failure_reason = Column(String(255), nullable=True)

class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(String(45), primary_key=True, index=True)
    merchant_id = Column(String(45), nullable=False, index=True)
    category = Column(String(50), nullable=False) # Refund, Settlement, KYC, etc.
    details = Column(String(500), nullable=True)
    status = Column(String(20), default="OPEN") # OPEN, RESOLVED, CLOSED, ESCALATED
    created_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

