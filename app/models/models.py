from sqlalchemy import Column, Integer, String, Decimal, DateTime, Date, BigInteger, JSON
from app.database import Base

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(45), nullable=False, index=True)
    txn_id = Column(String(45), nullable=False, unique=True)
    amount = Column(Decimal(8, 2), nullable=True)
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
    commission = Column(Decimal(4, 2), default=0.0)
    tds = Column(Decimal(4, 2), default=0.0)
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
