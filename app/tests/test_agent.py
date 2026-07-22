import pytest
import pytest_asyncio
import base64
import json
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

# Force test configuration
from app.config import settings
settings.ENV = "TEST"
settings.ENABLE_INTERNAL_AUTH_BYPASS = True
settings.INTERNAL_BYPASS_SECRET = "NPCI_INT3RNAL_Bypass_Secr3t_2026!"
settings.INTERNAL_CLIENTS = "WALLET_SERVICE,PASSBOOK_SERVICE,LOG_SERVICE"

from app.main import app
from app.database import get_db

DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Override get_db dependency to point to SQLite in-memory test database
async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        # Create transactions table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(45) NOT NULL,
                txn_id VARCHAR(45) NOT NULL UNIQUE,
                amount DECIMAL(8,2),
                type VARCHAR(45),
                memo VARCHAR(200),
                status VARCHAR(45),
                ip_address VARCHAR(100),
                date DATETIME,
                category VARCHAR(45),
                mobile VARCHAR(10),
                masked_aadhaar VARCHAR(15),
                rrn VARCHAR(12),
                receipt TEXT,
                disputed INTEGER DEFAULT 0,
                device_sno VARCHAR(25) DEFAULT 'NA',
                user_consent VARCHAR(6) DEFAULT 'NO',
                device_data TEXT,
                commission DECIMAL(4,2) DEFAULT 0.0,
                tds DECIMAL(4,2) DEFAULT 0.0,
                RefundLedgerStatus INTEGER DEFAULT 0,
                txn_date DATE NOT NULL,
                receipt_id VARCHAR(35)
            );
        """))
        
        # Create merchants table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS merchants (
                id VARCHAR(45) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                phone VARCHAR(15),
                email VARCHAR(100),
                state VARCHAR(50),
                status VARCHAR(20),
                bank_name VARCHAR(100),
                bank_account_no VARCHAR(30),
                bank_ifsc VARCHAR(20)
            );
        """))

        # Create KYC table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS kyc_details (
                merchant_id VARCHAR(45) PRIMARY KEY,
                status VARCHAR(20),
                pan_number VARCHAR(15),
                aadhaar_number VARCHAR(15),
                comments VARCHAR(255),
                updated_at DATETIME
            );
        """))

        # Create wallets table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS wallets (
                merchant_id VARCHAR(45) PRIMARY KEY,
                balance DECIMAL(12,2),
                blocked_balance DECIMAL(12,2),
                last_settlement_date DATETIME,
                last_settlement_amount DECIMAL(12,2)
            );
        """))

        # Create settlements table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS settlements (
                txn_id VARCHAR(45) PRIMARY KEY,
                status VARCHAR(45) NOT NULL,
                settlement_date DATETIME,
                utr VARCHAR(50),
                failure_reason VARCHAR(255)
            );
        """))

        # Create tickets table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tickets (
                id VARCHAR(45) PRIMARY KEY,
                merchant_id VARCHAR(45) NOT NULL,
                category VARCHAR(50) NOT NULL,
                details VARCHAR(500),
                status VARCHAR(20),
                created_at DATETIME,
                closed_at DATETIME
            );
        """))

        # Seed initial transaction for merchant '500100100014'
        await conn.execute(text("""
            INSERT INTO transactions (id, user_id, txn_id, amount, type, status, date, category, mobile, masked_aadhaar, rrn, txn_date)
            VALUES (1, '500100100014', 'CZUCW178186672384906DQQOQSU69890796', 1000.00, 'Cash Withdrawal', 'SUCCESS', '2026-06-19 16:26:05', 'AEPS', '9988776655', '123456786666', '617016890796', '2026-06-19');
        """))

        # Seed foreign transaction (belonging to another merchant '999900001111') for RBAC check
        await conn.execute(text("""
            INSERT INTO transactions (id, user_id, txn_id, amount, type, status, date, category, mobile, masked_aadhaar, rrn, txn_date)
            VALUES (2, '999900001111', 'CZUCW999999999999999DQQOQSU99999999', 5000.00, 'Cash Withdrawal', 'SUCCESS', '2026-06-20 10:00:00', 'AEPS', '8888888888', '987654321012', '987654321012', '2026-06-20');
        """))

    yield
    await engine.dispose()

@pytest.mark.asyncio
async def test_agent_seed_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Since /api/v1/agent/test-seed is excluded from auth check, it should respond 200
        res = await ac.post("/api/v1/agent/test-seed")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "SUCCESS"
        assert "seeded successfully" in body["msg"]

@pytest.mark.asyncio
async def test_agent_wallet_balance_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # We fetch a test token to authenticate
        token_res = await ac.post("/api/v1/auth/token", json={
            "username": "testuser",
            "password": "testpassword",
            "cscId": "500100100014"
        })
        token = token_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Ask about wallet balance
        chat_res = await ac.post("/api/v1/agent/chat", json={
            "sessionId": "session_wallet_test",
            "message": "What is my current wallet balance?"
        }, headers=headers)
        
        assert chat_res.status_code == 200
        body = chat_res.json()
        assert body["status"] == "OK"
        assert "Wallet" in body["intent"]
        assert "4560.50" in body["response"] # balance from seed
        assert "120.00" in body["response"]  # blocked balance from seed
        assert body["policyChecked"] is True
        assert body["escalate"] is False

@pytest.mark.asyncio
async def test_agent_kyc_status_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        token_res = await ac.post("/api/v1/auth/token", json={
            "username": "testuser",
            "password": "testpassword",
            "cscId": "500100100014"
        })
        token = token_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Ask about KYC
        chat_res = await ac.post("/api/v1/agent/chat", json={
            "sessionId": "session_kyc_test",
            "message": "Is my KYC application approved yet?"
        }, headers=headers)

        assert chat_res.status_code == 200
        body = chat_res.json()
        assert body["status"] == "OK"
        assert body["intent"] == "KYC"
        assert "APPROVED" in body["response"]
        assert body["policyChecked"] is True

@pytest.mark.asyncio
async def test_agent_failed_transaction_reversal_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        token_res = await ac.post("/api/v1/auth/token", json={
            "username": "testuser",
            "password": "testpassword",
            "cscId": "500100100014"
        })
        token = token_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Insert a FAILED transaction
        async with TestingSessionLocal() as session:
            await session.execute(text("""
                INSERT INTO transactions (id, user_id, txn_id, amount, type, status, date, category, mobile, masked_aadhaar, rrn, txn_date)
                VALUES (3, '500100100014', 'CZUCW111222333444555DQQOQSU11122233', 500.00, 'Cash Withdrawal', 'FAILED', '2026-06-20 12:00:00', 'AEPS', '9988776655', '123456786666', '617016890797', '2026-06-20');
            """))
            # Insert reversal settlement
            await session.execute(text("""
                INSERT INTO settlements (txn_id, status, settlement_date, utr, failure_reason)
                VALUES ('CZUCW111222333444555DQQOQSU11122233', 'auto-reversal-initiated', '2026-06-20 12:05:00', 'REV99887766', 'Bank timeout');
            """))
            await session.commit()

        # Query status
        chat_res = await ac.post("/api/v1/agent/chat", json={
            "sessionId": "session_reversal_test",
            "message": "Where is my money for failed txn CZUCW111222333444555DQQOQSU11122233?"
        }, headers=headers)

        assert chat_res.status_code == 200
        body = chat_res.json()
        assert "failed" in body["response"].lower()
        assert "automatic reversal has already been initiated" in body["response"]
        assert "20 minutes" in body["response"]

@pytest.mark.asyncio
async def test_agent_rbac_security_block_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Authenticate as VLE '500100100014'
        token_res = await ac.post("/api/v1/auth/token", json={
            "username": "testuser",
            "password": "testpassword",
            "cscId": "500100100014"
        })
        token = token_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Attempt to query transaction of another merchant (user_id '999900001111')
        # Txn: CZUCW999999999999999DQQOQSU99999999
        chat_res = await ac.post("/api/v1/agent/chat", json={
            "sessionId": "session_security_test",
            "message": "Give me transaction details of CZUCW999999999999999DQQOQSU99999999"
        }, headers=headers)

        assert chat_res.status_code == 200
        body = chat_res.json()
        # Should detect breach, validation node marks status SECURITY_BLOCKED, triggers human escalation
        assert body["escalate"] is True
        assert "escalate" in body["response"] or "represenative" in body["response"] or "issue retrieving" in body["response"]

@pytest.mark.asyncio
async def test_agent_pii_masking_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        token_res = await ac.post("/api/v1/auth/token", json={
            "username": "testuser",
            "password": "testpassword",
            "cscId": "500100100014"
        })
        token = token_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Ask standard biometric RD service question (which triggers SOP search)
        chat_res = await ac.post("/api/v1/agent/chat", json={
            "sessionId": "session_pii_test",
            "message": "What is the RD service version requirement? Here is my Aadhaar card 333344445555 and mobile number 9988776655 for confirmation."
        }, headers=headers)

        assert chat_res.status_code == 200
        body = chat_res.json()
        assert "XXXX XXXX 5555" in body["response"] # Aadhaar masked
        assert "XXXXXXX655" in body["response"]    # Mobile masked

@pytest.mark.asyncio
async def test_agent_history_retrieval_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        token_res = await ac.post("/api/v1/auth/token", json={
            "username": "testuser",
            "password": "testpassword",
            "cscId": "500100100014"
        })
        token = token_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        session_id = "session_history_test"
        
        # Send first message
        await ac.post("/api/v1/agent/chat", json={
            "sessionId": session_id,
            "message": "Hi, what is my wallet balance?"
        }, headers=headers)

        # Get history
        history_res = await ac.get(f"/api/v1/agent/history/{session_id}", headers=headers)
        assert history_res.status_code == 200
        history_body = history_res.json()
        
        assert history_body["sessionId"] == session_id
        assert len(history_body["history"]) == 2
        assert history_body["history"][0]["role"] == "user"
        assert history_body["history"][0]["content"] == "Hi, what is my wallet balance?"
        assert history_body["history"][1]["role"] == "assistant"
