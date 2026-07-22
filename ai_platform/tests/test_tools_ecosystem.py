import pytest
from tools.decorator import REGISTERED_TOOLS
from tools.discovery import discover_tools
from tools.registry import TOOL_REGISTRY, validate_tool_permission
from core.exceptions import AuthenticationException

@pytest.mark.anyio
async def test_tool_decorator_and_autodiscovery():
    # 1. Assert auto-discovery found at least 10 tools
    assert len(TOOL_REGISTRY) >= 10
    
    # 2. Check metadata on discovered tool
    balance_tool = TOOL_REGISTRY.get("getWalletBalance")
    assert balance_tool is not None
    assert balance_tool.name == "getWalletBalance"
    assert balance_tool.cacheable is True

@pytest.mark.anyio
async def test_new_domain_tools_execution():
    from tools.upi.vpa import validate_vpa
    from tools.settlement.payout import get_payout_status
    from tools.bank.ifsc import lookup_ifsc
    from tools.device.rd_service import get_rd_device_status
    from tools.ticket.support_ticket import get_ticket_status

    res_vpa = await validate_vpa("merchant@upi")
    assert res_vpa["valid"] is True

    res_payout = await get_payout_status("500100100014")
    assert res_payout["settlementStatus"] == "PROCESSED_SUCCESS"

    res_ifsc = await lookup_ifsc("SBIN0001234")
    assert res_ifsc["bank"] == "State Bank of India"

    res_rd = await get_rd_device_status("500100100014")
    assert res_rd["status"] == "READY_ACTIVE"

    res_tck = await get_ticket_status("TCK-123")
    assert res_tck["status"] == "IN_PROGRESS"

def test_tool_rbac_permissions():
    # Reverse transaction allows only SUPPORT and ADMIN
    with pytest.raises(AuthenticationException):
        validate_tool_permission("reverseTransaction", ["ROLE_MERCHANT"])
    
    # Should not raise exception for ROLE_SUPPORT
    validate_tool_permission("reverseTransaction", ["ROLE_SUPPORT"])
