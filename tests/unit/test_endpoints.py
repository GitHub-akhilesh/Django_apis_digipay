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
        # Create standard schema
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
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS digipay_ledger_5 (
                sno INTEGER PRIMARY KEY AUTOINCREMENT,
                clientId VARCHAR(50),
                cscTxn VARCHAR(50),
                merchantTxn VARCHAR(45),
                cscId VARCHAR(12),
                walletAc VARCHAR(12),
                isoRrn VARCHAR(60),
                txnType VARCHAR(2),
                categoryId INTEGER,
                lastSno INTEGER,
                walletBalance DECIMAL(12,2),
                walletTxnAmount DECIMAL(12,2),
                bankAmt DECIMAL(12,2),
                cscAmt DECIMAL(12,2),
                grossRevenue DECIMAL(12,2),
                gstAmt DECIMAL(12,2),
                tds DECIMAL(12,2),
                interChange DECIMAL(12,2),
                txnAmount DECIMAL(12,2),
                vleAmt DECIMAL(12,2),
                txnCnt INTEGER,
                txnDate DATE,
                txnHash VARCHAR(72),
                stateCode VARCHAR(2),
                districtCode VARCHAR(6),
                bank_iin VARCHAR(10),
                createdBy VARCHAR(25),
                creationDate DATETIME,
                customer VARCHAR(24),
                remarks VARCHAR(200),
                reqCode VARCHAR(50),
                param1 VARCHAR(50),
                param2 VARCHAR(50),
                param3 VARCHAR(50),
                flag INTEGER,
                ipAddr VARCHAR(15)
            );
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS category_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service VARCHAR(50),
                txn_type VARCHAR(50),
                category_name VARCHAR(100),
                category_description VARCHAR(100)
            );
        """))
        
        # Seed tables
        await conn.execute(text("""
            INSERT INTO category_mapping (id, service, txn_type, category_name, category_description)
            VALUES (1, 'AEPS', 'CASH_WITHDRAWAL', 'AEPS_WITHDRAWAL', 'AEPS cash withdrawal');
        """))
        
        await conn.execute(text("""
            INSERT INTO transactions (id, user_id, txn_id, amount, type, status, date, category, mobile, masked_aadhaar, rrn, txn_date)
            VALUES (1, '500100100014', 'CZUCW178186672384906DQQOQSU69890796', -100.0, 'Cash Withdrawal', 'SUCCESS', '2026-06-19 16:26:05', 'AEPS', '6666666666', '123456786666', '617016890796', '2026-06-19');
        """))
        
        await conn.execute(text("""
            INSERT INTO digipay_ledger_5 (sno, clientId, cscTxn, merchantTxn, cscId, walletAc, isoRrn, txnType, categoryId, lastSno, walletBalance, walletTxnAmount, bankAmt, cscAmt, grossRevenue, gstAmt, tds, interChange, txnAmount, vleAmt, txnCnt, txnDate, txnHash, stateCode, districtCode, bank_iin, createdBy, creationDate, customer, remarks, reqCode, param1, param2, param3, flag, ipAddr)
            VALUES (1791, 'CSC-DGP', '722851395933401', 'CZUCW178186672384906DQQOQSU69890796', '500100100014', '500100100014', '617016890796', 'Cr', 1, 1790, 3821.42, 100.31, 0.0, 0.0, 0.0, 0.0, -0.01, 0.0, 100.0, 0.32, 1, '2026-06-19', 'hash', '00', '00', '607198', 'DGP-APP', '2026-06-19 15:21:13', 'XXXX XXXX 9685', 'AEPS CW/XXXX XXXX 9685', '0', '100.00', '', '', 0, '127.0.0.1');
        """))
    yield
    await engine.dispose()

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "OK", "msg": "API service is healthy"}

@pytest.mark.asyncio
async def test_token_and_authorized_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Fetch test token
        token_res = await ac.post("/api/v1/auth/token", json={
            "username": "testuser",
            "password": "testpassword",
            "cscId": "500100100014"
        })
        assert token_res.status_code == 200
        token = token_res.json()["access_token"]
        
        # 2. Make authorized request to logs endpoint
        headers = {"Authorization": f"Bearer {token}"}
        logs_res = await ac.post("/api/v1/txn-logs", json={
            "cscId": "500100100014",
            "fromDate": "18-06-2026",
            "toDate": "20-06-2026",
            "search": "",
            "rpp": 10,
            "cp": 1,
            "type": "AEPS_CASH_WITHDRAWAL"
        }, headers=headers)
        
        assert logs_res.status_code == 200
        body = logs_res.json()
        assert body["status"] == "OK"
        assert "fetched successfully!" in body["msg"]
        
        # Decode base64 resData
        res_data_raw = base64.b64decode(body["resData"].encode("utf-8")).decode("utf-8")
        res_data = json.loads(res_data_raw)
        assert res_data["totalRecords"] == 1
        assert len(res_data["list"]) == 1
        assert res_data["list"][0]["txnId"] == "CZUCW178186672384906DQQOQSU69890796"

@pytest.mark.asyncio
async def test_internal_client_bypass_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Request passbook with bypass headers
        headers = {
            "X-Client-Id": "PASSBOOK_SERVICE",
            "X-Bypass-Secret": "NPCI_INT3RNAL_Bypass_Secr3t_2026!"
        }
        
        passbook_res = await ac.post("/api/v1/passbook", json={
            "cscId": "500100100014",
            "fromDate": "18-06-2026",
            "toDate": "20-06-2026",
            "search": "",
            "rpp": 10,
            "cp": 1
        }, headers=headers)
        
        assert passbook_res.status_code == 200
        body = passbook_res.json()
        assert body["status"] == "OK"
        
        # Decode and verify contents
        res_data_raw = base64.b64decode(body["resData"].encode("utf-8")).decode("utf-8")
        res_data = json.loads(res_data_raw)
        assert res_data["totalRecords"] == 1
        assert len(res_data["list"]) == 1
        assert res_data["list"][0]["merchantTxn"] == "CZUCW178186672384906DQQOQSU69890796"
        assert res_data["list"][0]["category"] == "AEPS_CASH_WITHDRAWAL"

@pytest.mark.asyncio
async def test_unauthorized_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Request with no headers
        res = await ac.post("/api/v1/txn-logs", json={
            "cscId": "500100100014",
            "fromDate": "18-06-2026",
            "toDate": "20-06-2026",
            "search": "",
            "rpp": 10,
            "cp": 1,
            "type": "AEPS_CASH_WITHDRAWAL"
        })
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_wallet_balance_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = {
            "X-Client-Id": "WALLET_SERVICE",
            "X-Bypass-Secret": "NPCI_INT3RNAL_Bypass_Secr3t_2026!"
        }
        # 1. Standard POST with csc_ids
        res = await ac.post("/api/v1/get-wallet-balance", json={
            "csc_ids": ["500100100014", "999999999999"]
        }, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "500100100014" in data
        assert float(data["500100100014"]) == 3821.42  # matches seed data walletBalance
        assert float(data["999999999999"]) == 0.0

        # 2. Legacy POST payload key variation (cscId, user_id, merchantId)
        res_legacy = await ac.post("/api/v1/wallet_balance", json={
            "cscId": "500100100014"
        }, headers=headers)
        assert res_legacy.status_code == 200
        assert float(res_legacy.json()["500100100014"]) == 3821.42

        res_user_id = await ac.post("/api/v1/user_wallet_balance", json={
            "user_id": "500100100014"
        }, headers=headers)
        assert res_user_id.status_code == 200
        assert float(res_user_id.json()["500100100014"]) == 3821.42

        # 3. Legacy GET request with query params
        res_get = await ac.get("/api/v1/get-wallet-balance?cscId=500100100014", headers=headers)
        assert res_get.status_code == 200
        assert float(res_get.json()["500100100014"]) == 3821.42


@pytest.mark.asyncio
async def test_daywise_report_endpoint():
    import os
    import zipfile
    import io
    
    # Create temp directory structure
    os.makedirs("reports/2026", exist_ok=True)
    month_zip = "reports/2026/June.zip"
    
    # Create a dummy zip file
    with zipfile.ZipFile(month_zip, 'w') as zf:
        # Create a day zip inside the month zip
        day_buffer = io.BytesIO()
        with zipfile.ZipFile(day_buffer, 'w') as dzf:
            dzf.writestr("report.csv", "sno,clientId,amount\n1,CSC-DGP,100.0\n")
        zf.writestr("19.zip", day_buffer.getvalue())

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            headers = {
                "X-Client-Id": "LOG_SERVICE",
                "X-Bypass-Secret": "NPCI_INT3RNAL_Bypass_Secr3t_2026!"
            }
            # 1. Test downloading monthly zip
            res_month = await ac.post("/api/v1/daywise_report", json={
                "year_month": "2026 June"
            }, headers=headers)
            assert res_month.status_code == 200
            assert res_month.headers["content-type"] == "application/zip"
            
            # 2. Test downloading daywise zip
            res_day = await ac.post("/api/v1/daywise_report", json={
                "year_month": "2026 June",
                "day": "19"
            }, headers=headers)
            assert res_day.status_code == 200
            assert res_day.headers["content-type"] == "application/zip"
            
    finally:
        # Clean up
        if os.path.exists(month_zip):
            os.remove(month_zip)
        if os.path.exists("reports/2026"):
            os.rmdir("reports/2026")
        if os.path.exists("reports"):
            os.rmdir("reports")
