import pytest
from app.repositories import wallet_repo, txn_repo, kyc_repo, merchant_repo, settlement_repo, ticket_repo
from app.services.domain import WalletSnapshotService

@pytest.mark.asyncio
async def test_wallet_repository_and_snapshot(db_session):
    snapshot = await WalletSnapshotService.get_wallet_snapshot(db_session, "500100100014")
    assert snapshot.merchant_id == "500100100014"
    assert isinstance(snapshot.active_balance, float)
    assert isinstance(snapshot.legacy_balance, float)

@pytest.mark.asyncio
async def test_kyc_repository(db_session):
    kyc = await kyc_repo.get_by_merchant_id(db_session, "500100100014")
    assert kyc is None or hasattr(kyc, "status")

@pytest.mark.asyncio
async def test_merchant_repository(db_session):
    merchant = await merchant_repo.get_by_merchant_id(db_session, "500100100014")
    assert merchant is None or hasattr(merchant, "name")
