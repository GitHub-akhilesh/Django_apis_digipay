from typing import Dict, Any

class WalletResponseBuilder:
    @staticmethod
    def format_wallet_balance(res: Dict[str, Any]) -> str:
        old_bal_text = f" Your Old DigiPay balance is ₹{res['oldDigipayBalance']:.2f}." if "oldDigipayBalance" in res else ""
        return (
            f"Your active wallet balance is ₹{res['balance']:.2f}.{old_bal_text} "
            f"Your blocked balance is ₹{res['blockedBalance']:.2f}. "
            f"Your last settlement was processed on {res['lastSettlementDate'] or 'N/A'} for ₹{res['lastSettlementAmount']:.2f}."
        )

    @staticmethod
    def format_old_digipay_balance(res: Dict[str, Any]) -> str:
        return f"Your Old DigiPay legacy balance is ₹{res.get('oldDigipayBalance', 0.0):.2f} for account {res.get('merchantId')}."
