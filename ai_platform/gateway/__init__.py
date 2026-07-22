from gateway.client import GatewayClient
from gateway.headers import get_downstream_headers
from gateway.wallet_client import WalletClient
from gateway.merchant_client import MerchantClient
from gateway.ledger_client import LedgerClient
from gateway.transaction_client import TransactionClient
from gateway.passbook_client import PassbookClient
from gateway.aeps_client import AEPSClient
from gateway.notification_client import NotificationClient
from gateway.ticket_client import TicketClient

# Instantiated SDK Singletons matching microservice injection structures
wallet_client = WalletClient()
merchant_client = MerchantClient()
ledger_client = LedgerClient()
transaction_client = TransactionClient()
passbook_client = PassbookClient()
aeps_client = AEPSClient()
notification_client = NotificationClient()
ticket_client = TicketClient()

__all__ = [
    "GatewayClient",
    "get_downstream_headers",
    "wallet_client",
    "merchant_client",
    "ledger_client",
    "transaction_client",
    "passbook_client",
    "aeps_client",
    "notification_client",
    "ticket_client"
]
