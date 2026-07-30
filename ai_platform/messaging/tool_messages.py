"""
Per-tool chat message catalogue.

Every tool the assistant can run has an entry here so the reply is worded
deliberately rather than left entirely to the model: a progress line, a success
headline, an empty-result line, a failure line, and a role-denied line.

`fields` lists the payload keys worth surfacing, in the order a user wants to
read them. `row_fields` does the same for the rows of a paginated list.
Unknown keys are simply skipped, so a gateway response that grows new fields
never breaks rendering.
"""

from typing import Dict, List, Optional, Tuple

# (label, payload key) — the key is matched case-insensitively and also against
# its snake_case spelling, so both `cscId` and `csc_id` resolve.
FieldSpec = Tuple[str, str]


class ToolMessage:
    def __init__(
        self,
        label: str,
        working: str,
        success: str,
        empty: str,
        error: str,
        denied: Optional[str] = None,
        fields: Optional[List[FieldSpec]] = None,
        row_fields: Optional[List[FieldSpec]] = None,
        footnote: Optional[str] = None,
    ):
        self.label = label
        self.working = working
        self.success = success
        self.empty = empty
        self.error = error
        self.denied = denied or (
            f"{label} is restricted. Your account role does not have access to this information. "
            "Please raise a request with your DigiPay administrator if you need it."
        )
        self.fields = fields or []
        self.row_fields = row_fields or []
        self.footnote = footnote


def _admin_denied(label: str) -> str:
    return (
        f"{label} is an administrator report. Your account role does not have access to it. "
        "If you need this data, please ask a DigiPay administrator."
    )


TOOL_MESSAGES: Dict[str, ToolMessage] = {

    # =====================================================================
    # Ledger / wallet (gateway-service: LedgerController)
    # =====================================================================
    # Field names confirmed against the live UAT gateway. GET /v2/ledger/balance
    # returns the wallet balance together with the most recent ledger entry, so
    # the amount is `walletBalance` (not `balance`) and the surrounding keys
    # describe that last transaction: txnAmount, txnType, txnDate, remarks, rrn,
    # vleComm, vleTds, gst, walletDeduction, walletAc, customer, category.
    "getLedgerBalanceV2": ToolMessage(
        label="Wallet balance",
        working="Checking your DigiPay wallet balance…",
        success="Here is your current DigiPay wallet balance.",
        empty="No balance was returned for this CSC ID. The wallet may not be activated yet.",
        error="I couldn't fetch your balance just now — the ledger service did not respond. Please try again in a moment.",
        fields=[
            ("Balance", "walletBalance"),
            ("Wallet account", "walletAc"),
            ("CSC ID", "cscId"),
            ("Last transaction", "txnType"),
            ("Last amount", "txnAmount"),
            ("Last transaction on", "txnDate"),
            ("Narration", "remarks"),
        ],
        footnote="Your balance is read live from the DigiPay ledger, shown with your most recent entry.",
    ),
    # Row shape confirmed against the live gateway: the passbook returns ledger
    # rows in the same shape as /v2/ledger/balance, so the amount is `txnAmount`,
    # the running balance is `walletBalance` and the kind is `txnType` — not the
    # amount/closingBalance/lgrTxnType originally guessed from the Java source.
    "getLedgerPassbookV2": ToolMessage(
        label="Your passbook",
        working="Pulling up your passbook entries…",
        success="Here are your passbook entries, newest first.",
        empty="No passbook entries were found for that period. Try widening the date range.",
        error="I couldn't load your passbook right now. Please try again shortly.",
        row_fields=[
            ("Date", "txnDate"),
            ("Type", "txnType"),
            ("Amount", "txnAmount"),
            ("Balance after", "walletBalance"),
            ("Narration", "remarks"),
            ("RRN", "rrn"),
        ],
        footnote="Ask for a date range, a service, or another page to narrow this down.",
    ),
    "getLedgerRecoveryList": ToolMessage(
        label="Ledger recovery list",
        working="Fetching the ledger recovery cases…",
        success="Here are the ledger recovery cases on record.",
        empty="No ledger recovery cases were found for the given filters.",
        error="The recovery listing could not be retrieved right now.",
        denied=_admin_denied("The ledger recovery list"),
        row_fields=[
            ("Date", "txnDate"),
            ("CSC ID", "cscId"),
            ("Txn ID", "txnId"),
            ("Amount", "amount"),
            ("Status", "status"),
            ("Remarks", "remarks"),
        ],
    ),

    # =====================================================================
    # Transaction logs (gateway-service: TxnLogController)
    # =====================================================================
    "getTxnLogs": ToolMessage(
        label="Transaction log",
        working="Searching your DigiPay transaction history…",
        success="Here is what I found in your transaction history.",
        empty="No transactions matched those filters. Try a different date range, service type or status.",
        error="I couldn't search your transaction history right now. Please try again in a moment.",
        row_fields=[
            ("Date", "txnDate"),
            ("Txn ID", "txnId"),
            ("Service", "type"),
            ("Amount", "amount"),
            ("Status", "status"),
            ("RRN", "rrn"),
        ],
        footnote="Ask me about any transaction ID from this list and I will pull the full switch response.",
    ),
    "getTxnResponse": ToolMessage(
        label="Transaction response",
        working="Retrieving the switch response for that transaction…",
        success="Here is the recorded response for that transaction.",
        empty="No response record exists for that reference number. Please double-check the reference and service type.",
        error="I couldn't retrieve the transaction response just now.",
        fields=[
            ("Txn ID", "txnId"),
            ("Reference", "refNo"),
            ("RRN", "rrn"),
            ("Status", "status"),
            ("Amount", "amount"),
            ("Response code", "respCode"),
            ("Response message", "respMsg"),
            ("Bank", "bankName"),
            ("UTR", "utr"),
            ("Date", "txnDate"),
        ],
    ),

    # =====================================================================
    # AePS enquiries and logs (gateway-service: AepsController)
    # =====================================================================
    "getAepsBalanceEnquiryResponse": ToolMessage(
        label="AePS balance enquiry result",
        working="Looking up that AePS balance enquiry result…",
        success="Here is the result of that AePS balance enquiry.",
        empty="No AePS balance enquiry was found for that reference number.",
        error="I couldn't fetch that AePS balance enquiry result right now.",
        fields=[
            ("Reference", "refNo"),
            ("Txn ID", "txnId"),
            ("Status", "status"),
            ("Customer balance", "balance"),
            ("Bank", "bankName"),
            ("RRN", "rrn"),
            ("Date", "txnDate"),
        ],
        footnote="This is a record of a completed enquiry — I cannot start a new biometric enquiry from chat.",
    ),
    "getAepsBalanceEnquiryList": ToolMessage(
        label="AePS balance enquiry history",
        working="Fetching your AePS balance enquiry history…",
        success="Here are your recent AePS balance enquiries.",
        empty="No AePS balance enquiries were found for those filters.",
        error="I couldn't load your AePS balance enquiry history right now.",
        row_fields=[
            ("Date", "txnDate"),
            ("Txn ID", "txnId"),
            ("Bank", "bankName"),
            ("Status", "status"),
            ("RRN", "rrn"),
        ],
    ),
    "getAepsBalanceEnquiryDetails": ToolMessage(
        label="AePS balance enquiry detail",
        working="Opening that AePS balance enquiry record…",
        success="Here is the full AePS balance enquiry record.",
        empty="No AePS balance enquiry matched that transaction ID or RRN.",
        error="I couldn't open that AePS balance enquiry record right now.",
        fields=[
            ("Txn ID", "txnId"),
            ("RRN", "rrn"),
            ("Status", "status"),
            ("Bank", "bankName"),
            ("Bank IIN", "bankIin"),
            ("Customer balance", "balance"),
            ("Response code", "respCode"),
            ("Response message", "respMsg"),
            ("Date", "txnDate"),
        ],
    ),
    "getAepsLogs": ToolMessage(
        label="AePS transaction log",
        working="Searching your AePS transaction logs…",
        success="Here are the AePS transactions I found.",
        empty="No AePS transactions matched those filters.",
        error="I couldn't search the AePS logs right now.",
        row_fields=[
            ("Date", "txnDate"),
            ("Txn ID", "txnId"),
            ("Type", "txnType"),
            ("Amount", "amount"),
            ("Status", "status"),
            ("Bank", "bankName"),
        ],
    ),
    "getAepsLogDetails": ToolMessage(
        label="AePS transaction detail",
        working="Opening that AePS transaction record…",
        success="Here is the full AePS transaction record.",
        empty="No AePS transaction matched that transaction ID or RRN.",
        error="I couldn't open that AePS transaction record right now.",
        fields=[
            ("Txn ID", "txnId"),
            ("RRN", "rrn"),
            ("Type", "txnType"),
            ("Amount", "amount"),
            ("Status", "status"),
            ("Bank", "bankName"),
            ("Response code", "respCode"),
            ("Response message", "respMsg"),
            ("Date", "txnDate"),
        ],
    ),

    # =====================================================================
    # Notifications (gateway-service: NotificationController)
    # =====================================================================
    "getNotifications": ToolMessage(
        label="Notifications",
        working="Checking your DigiPay notifications…",
        success="Here are your notifications.",
        empty="You have no notifications right now.",
        error="I couldn't load your notifications just now.",
        row_fields=[
            ("Date", "createdAt"),
            ("Title", "title"),
            ("Type", "notificationType"),
            ("Message", "message"),
        ],
    ),
    "getLoginNotifications": ToolMessage(
        label="Login announcements",
        working="Checking the latest DigiPay announcements…",
        success="Here are the current DigiPay announcements.",
        empty="There are no active announcements at the moment.",
        error="I couldn't load the announcements just now.",
        row_fields=[
            ("Date", "createdAt"),
            ("Title", "title"),
            ("Message", "message"),
        ],
    ),

    # =====================================================================
    # Operators, devices, services (gateway-service)
    # =====================================================================
    "getOperatorList": ToolMessage(
        label="Operator list",
        working="Fetching the operators registered under your CSC ID…",
        success="Here are the operators registered under your CSC ID.",
        empty="No operators are registered under this CSC ID yet.",
        error="I couldn't fetch your operator list right now.",
        row_fields=[
            ("Operator ID", "operatorId"),
            ("Name", "name"),
            ("Mobile", "mobile"),
            ("Role", "role"),
            ("Status", "status"),
        ],
        footnote="I can show operators, but adding or modifying an operator has to be done from the DigiPay portal.",
    ),
    "getDeviceList": ToolMessage(
        label="Registered devices",
        working="Checking your registered biometric devices…",
        success="Here are the biometric devices registered to your account.",
        empty="No biometric devices are registered against this CSC ID.",
        error="I couldn't fetch your registered devices right now.",
        row_fields=[
            ("Device type", "deviceType"),
            ("Model", "deviceModel"),
            ("Serial", "serialNo"),
            ("Status", "status"),
            ("Registered on", "createdAt"),
        ],
        footnote="Device registration and deregistration are performed from the DigiPay app, not from chat.",
    ),
    "getServiceCatalog": ToolMessage(
        label="Your services",
        working="Checking which DigiPay services are enabled for you…",
        success="Here are the DigiPay services enabled on your account.",
        empty="No services are currently enabled on your account. Please contact DigiPay support.",
        error="I couldn't load your service list right now.",
        row_fields=[
            ("Service", "serviceName"),
            ("Code", "serviceCode"),
            ("Status", "status"),
        ],
    ),
    "getMasterServiceList": ToolMessage(
        label="DigiPay service catalogue",
        working="Fetching the full DigiPay service catalogue…",
        success="Here is the full DigiPay service catalogue.",
        empty="The service catalogue came back empty.",
        error="I couldn't load the service catalogue right now.",
        row_fields=[
            ("Service", "serviceName"),
            ("Code", "serviceCode"),
            ("Category", "category"),
            ("Status", "status"),
        ],
    ),

    # =====================================================================
    # Analytics (gateway-service: AnalyticsController)
    # =====================================================================
    "getTxnAnalytics": ToolMessage(
        label="Transaction analytics",
        working="Crunching your transaction analytics…",
        success="Here is your transaction summary.",
        empty="There is no analytics data for that period yet.",
        error="I couldn't generate your analytics right now.",
        fields=[
            ("Total transactions", "totalTxn"),
            ("Successful", "successCount"),
            ("Failed", "failedCount"),
            ("Pending", "pendingCount"),
            ("Total value", "totalAmount"),
            ("Commission earned", "commission"),
        ],
    ),

    # =====================================================================
    # Status lookups (gateway-service)
    # =====================================================================
    "getPayoutStatusV2": ToolMessage(
        label="Payout status",
        working="Checking that payout's settlement status…",
        success="Here is the current status of that payout.",
        empty="No payout was found for that transaction ID. Please re-check the ID.",
        error="I couldn't check the payout status right now.",
        fields=[
            ("Txn ID", "txnId"),
            ("Status", "status"),
            ("Amount", "amount"),
            ("Mode", "mode"),
            ("UTR", "utr"),
            ("Beneficiary", "beneficiaryName"),
            ("Date", "txnDate"),
        ],
        footnote="This is a status check only — initiating or refunding a payout is not something I can do.",
    ),
    "getDspTopUpStatus": ToolMessage(
        label="DSP top-up status",
        working="Checking that DSP top-up…",
        success="Here is the current status of that DSP top-up.",
        empty="No DSP top-up was found for that transaction ID.",
        error="I couldn't check the DSP top-up status right now.",
        fields=[
            ("Txn ID", "txnId"),
            ("Status", "status"),
            ("Amount", "amount"),
            ("UTR", "utr"),
            ("Date", "txnDate"),
        ],
    ),
    "getAuaAuthStatus": ToolMessage(
        label="Aadhaar authentication status",
        working="Checking that Aadhaar authentication attempt…",
        success="Here is the status of that Aadhaar authentication attempt.",
        empty="No Aadhaar authentication record was found for that transaction ID.",
        error="I couldn't check the Aadhaar authentication status right now.",
        fields=[
            ("Txn ID", "txnId"),
            ("Status", "status"),
            ("Category", "category"),
            ("Response code", "respCode"),
            ("Response message", "respMsg"),
            ("Date", "txnDate"),
        ],
        footnote="I can report on an authentication that already happened; I cannot perform a biometric authentication.",
    ),

    # =====================================================================
    # UPI + platform utilities (gateway-service)
    # =====================================================================
    "getUpiVpaSuggestions": ToolMessage(
        label="UPI VPA suggestions",
        working="Fetching available UPI handle suggestions…",
        success="Here are the UPI VPA handles available to you.",
        empty="No VPA suggestions are available right now.",
        error="I couldn't fetch VPA suggestions right now.",
        row_fields=[("Suggested VPA", "vpa")],
        footnote="Creating a UPI merchant or QR has to be done from the DigiPay app.",
    ),
    "getMyProfile": ToolMessage(
        label="Your DigiPay account",
        working="Fetching your DigiPay account details…",
        success="Here are your account details.",
        empty="I couldn't find profile details for your account.",
        error="I couldn't fetch your account details just now.",
        fields=[
            ("Name", "name"),
            ("CSC ID", "cscId"),
            ("Mobile", "mobile"),
            ("Email", "email"),
            ("Role", "role"),
            ("Status", "activeStatus"),
            ("State", "stateName"),
            ("District", "districtName"),
            ("Bank", "bankName"),
            ("Account number", "accountNo"),
            ("IFSC", "ifsc"),
            ("KYC status", "kycStatus"),
        ],
        footnote="To change any of these, please use the DigiPay app or portal.",
    ),
    "getPlatformPublicKey": ToolMessage(
        label="Platform public key",
        working="Fetching the active DigiPay public key…",
        success="Here is the currently active DigiPay encryption public key.",
        empty="No active public key was returned by the gateway.",
        error="I couldn't fetch the public key right now.",
        fields=[
            ("Key ID", "keyId"),
            ("Algorithm", "algorithm"),
            ("Valid from", "validFrom"),
        ],
        footnote="Use this key to encrypt request payloads for the DigiPay APIs.",
    ),

    # =====================================================================
    # Admin reports (gateway-service: AdminController) — ROLE_ADMIN only
    # =====================================================================
    "adminGetUserList": ToolMessage(
        label="User directory",
        working="Searching the DigiPay user directory…",
        success="Here are the users matching your search.",
        empty="No users matched those filters.",
        error="I couldn't search the user directory right now.",
        denied=_admin_denied("The user directory"),
        row_fields=[
            ("CSC ID", "cscId"),
            ("Name", "name"),
            ("Mobile", "mobile"),
            ("State", "stateName"),
            ("Status", "activeStatus"),
        ],
    ),
    "adminGetUserDetails": ToolMessage(
        label="User record",
        working="Opening that user's DigiPay record…",
        success="Here is the user record.",
        empty="No user record was found for that CSC ID.",
        error="I couldn't open that user record right now.",
        denied=_admin_denied("User records"),
        fields=[
            ("CSC ID", "cscId"),
            ("Name", "name"),
            ("Mobile", "mobile"),
            ("Email", "email"),
            ("Role", "role"),
            ("Status", "activeStatus"),
            ("State", "stateName"),
            ("District", "districtName"),
            ("Registered on", "createdAt"),
        ],
    ),
    "adminGetDailyTxnReport": ToolMessage(
        label="Daily transaction report",
        working="Compiling the daily transaction report…",
        success="Here is the daily transaction report.",
        empty="No transaction activity was recorded for that period.",
        error="I couldn't compile the daily transaction report right now.",
        denied=_admin_denied("The daily transaction report"),
        row_fields=[
            ("Date", "txnDate"),
            ("Service", "type"),
            ("Count", "totalTxn"),
            ("Value", "totalAmount"),
            ("Success", "successCount"),
            ("Failed", "failedCount"),
        ],
    ),
    "adminGetReport": ToolMessage(
        label="Consolidated admin report",
        working="Generating the consolidated report…",
        success="Here is the consolidated report.",
        empty="The report came back with no rows for those filters.",
        error="I couldn't generate that report right now.",
        denied=_admin_denied("Consolidated reports"),
    ),
    "adminGetTxnDetails": ToolMessage(
        label="Transaction record",
        working="Looking up that transaction across DigiPay services…",
        success="Here is the transaction record.",
        empty="No transaction was found for that reference number and service type.",
        error="I couldn't look up that transaction right now.",
        denied=_admin_denied("Cross-service transaction lookup"),
        fields=[
            ("Txn ID", "txnId"),
            ("Reference", "refNo"),
            ("CSC ID", "cscId"),
            ("Service", "type"),
            ("Amount", "amount"),
            ("Status", "status"),
            ("RRN", "rrn"),
            ("UTR", "utr"),
            ("Date", "txnDate"),
        ],
    ),
    "adminGetProfileOperatorList": ToolMessage(
        label="Profile and operators",
        working="Fetching that profile along with its operators…",
        success="Here is the profile with its mapped operators.",
        empty="No profile or operator mapping was found for that CSC ID.",
        error="I couldn't fetch that profile right now.",
        denied=_admin_denied("Profile and operator details"),
    ),
    "adminGetLoginJourney": ToolMessage(
        label="Login journey",
        working="Reconstructing that user's login journey…",
        success="Here is the login journey for that user.",
        empty="No login activity was recorded for those filters.",
        error="I couldn't fetch the login journey right now.",
        denied=_admin_denied("Login journey audit"),
        row_fields=[
            ("Time", "createdAt"),
            ("Stage", "stage"),
            ("Status", "status"),
            ("Device", "deviceType"),
            ("IP", "ipAddress"),
        ],
    ),
    "adminGetBlockHistory": ToolMessage(
        label="Block history",
        working="Fetching the block/unblock history…",
        success="Here is the block and unblock history.",
        empty="No block or unblock actions are recorded for those filters.",
        error="I couldn't fetch the block history right now.",
        denied=_admin_denied("Block history"),
        row_fields=[
            ("Time", "createdAt"),
            ("CSC ID", "cscId"),
            ("Action", "action"),
            ("Service", "type"),
            ("Reason", "remarks"),
            ("By", "actionBy"),
        ],
        footnote="This is a read-only history. Blocking or unblocking access is not something I can perform.",
    ),
    "adminGetUserOperators": ToolMessage(
        label="Mapped operators",
        working="Fetching the operators mapped to that user…",
        success="Here are the operators mapped to that user.",
        empty="No operators are mapped to that user.",
        error="I couldn't fetch the mapped operators right now.",
        denied=_admin_denied("Operator mappings"),
        row_fields=[
            ("Operator ID", "operatorId"),
            ("Name", "name"),
            ("Mobile", "mobile"),
            ("Status", "status"),
        ],
    ),
    "adminGetAgentAuthLogs": ToolMessage(
        label="Agent authentication logs",
        working="Fetching the agent biometric authentication logs…",
        success="Here are the agent authentication attempts.",
        empty="No agent authentication attempts matched those filters.",
        error="I couldn't fetch the agent authentication logs right now.",
        denied=_admin_denied("Agent authentication logs"),
        row_fields=[
            ("Time", "createdAt"),
            ("CSC ID", "cscId"),
            ("Auth for", "authFor"),
            ("Status", "status"),
            ("Response", "respMsg"),
        ],
    ),
    "adminGetServiceHistory": ToolMessage(
        label="Service usage history",
        working="Fetching that user's service usage history…",
        success="Here is the service usage history.",
        empty="No service usage was recorded for those filters.",
        error="I couldn't fetch the service usage history right now.",
        denied=_admin_denied("Service usage history"),
        row_fields=[
            ("Date", "txnDate"),
            ("Service", "type"),
            ("Count", "totalTxn"),
            ("Value", "totalAmount"),
        ],
    ),
    "adminGetTimeoutTxnList": ToolMessage(
        label="Timed-out transactions",
        working="Fetching the AePS timed-out transaction list…",
        success="Here are the transactions that timed out.",
        empty="No timed-out transactions were found for those filters. That is good news.",
        error="I couldn't fetch the timeout list right now.",
        denied=_admin_denied("The timed-out transaction list"),
        row_fields=[
            ("Date", "txnDate"),
            ("CSC ID", "cscId"),
            ("Txn ID", "txnId"),
            ("Amount", "amount"),
            ("Status", "status"),
            ("Bank", "bankName"),
        ],
    ),
    "adminGetDspWalletTransferLogs": ToolMessage(
        label="DSP wallet transfer logs",
        working="Fetching the DSP wallet transfer logs…",
        success="Here are the DSP wallet transfers.",
        empty="No DSP wallet transfers matched those filters.",
        error="I couldn't fetch the DSP wallet transfer logs right now.",
        denied=_admin_denied("DSP wallet transfer logs"),
        row_fields=[
            ("Date", "txnDate"),
            ("Txn ID", "txnId"),
            ("CSC ID", "cscId"),
            ("Amount", "amount"),
            ("Status", "status"),
            ("UTR", "utr"),
        ],
    ),
    "adminGetDspWalletTransferDetails": ToolMessage(
        label="DSP wallet transfer detail",
        working="Opening that DSP wallet transfer…",
        success="Here is the DSP wallet transfer record.",
        empty="No DSP wallet transfer was found for that transaction ID.",
        error="I couldn't open that DSP wallet transfer right now.",
        denied=_admin_denied("DSP wallet transfer details"),
        fields=[
            ("Txn ID", "txnId"),
            ("CSC ID", "cscId"),
            ("Amount", "amount"),
            ("Status", "status"),
            ("UTR", "utr"),
            ("Response message", "respMsg"),
            ("Date", "txnDate"),
        ],
    ),
    "adminGetDspDailySettlement": ToolMessage(
        label="DSP daily settlement",
        working="Fetching the DSP daily settlement listing…",
        success="Here is the DSP daily settlement listing.",
        empty="No DSP settlements were recorded for that period.",
        error="I couldn't fetch the DSP settlement listing right now.",
        denied=_admin_denied("DSP daily settlement"),
        row_fields=[
            ("Date", "txnDate"),
            ("CSC ID", "cscId"),
            ("Total", "totalAmount"),
            ("Count", "totalTxn"),
            ("Status", "status"),
        ],
    ),
    "adminGetExternalVleBalance": ToolMessage(
        label="Partner VLE balance",
        working="Fetching that VLE's balance via the partner client API…",
        success="Here is the VLE ledger balance reported to partner clients.",
        empty="No balance was returned for that CSC ID.",
        error="I couldn't fetch the partner VLE balance right now.",
        denied=_admin_denied("The partner client balance API"),
        fields=[
            ("CSC ID", "cscId"),
            ("Balance", "balance"),
            ("Status", "status"),
        ],
    ),

    # =====================================================================
    # Legacy DigiPay API service (app/main.py), called over HTTP on its own
    # original URLs. Wording says "legacy system" explicitly so a user can tell
    # which system a figure came from when both are reachable.
    # =====================================================================
    "getLegacyTxnLogs": ToolMessage(
        label="Transaction log (legacy system)",
        working="Searching the legacy DigiPay system for your transactions…",
        success="Here is what the legacy DigiPay system holds for that period.",
        empty="The legacy system has no transactions for those filters. It only holds older records — ask me to check the current system instead.",
        error="I couldn't reach the legacy DigiPay system just now. Please try again shortly.",
        row_fields=[
            ("Date", "txnDate"),
            ("Txn ID", "txnId"),
            ("Type", "type"),
            ("Amount", "amount"),
            ("Status", "status"),
            ("RRN", "rrn"),
        ],
        footnote="These records come from the legacy DigiPay system.",
    ),
    "getLegacyPassbook": ToolMessage(
        label="Passbook (legacy system)",
        working="Pulling up your legacy DigiPay passbook…",
        success="Here are your legacy passbook entries.",
        empty="The legacy system has no passbook entries for that period.",
        error="I couldn't load your legacy passbook right now.",
        row_fields=[
            ("Date", "txnDate"),
            ("Txn ID", "txnId"),
            ("Type", "txnType"),
            ("Amount", "amount"),
            ("Closing balance", "closingBalance"),
            ("Narration", "remarks"),
        ],
        footnote="These entries come from the legacy DigiPay system.",
    ),
    "getLegacyWalletBalance": ToolMessage(
        label="Wallet balance (legacy system)",
        working="Checking your legacy DigiPay wallet balance…",
        success="Here is your legacy DigiPay wallet balance.",
        empty="The legacy system returned no balance for this CSC ID.",
        error="I couldn't fetch your legacy wallet balance just now.",
        fields=[("CSC ID", "cscId"), ("Balance", "balance")],
        footnote="This balance comes from the legacy DigiPay system, which may differ from the current ledger.",
    ),

    # =====================================================================
    # Pre-existing DigiPay tools — wording added so these render consistently
    # alongside the gateway tools. Their behaviour is unchanged.
    # =====================================================================
    "getWalletBalance": ToolMessage(
        label="Wallet balance",
        working="Checking your wallet balance…",
        success="Here is your current wallet balance.",
        empty="No wallet balance record was returned.",
        error="I couldn't fetch your wallet balance just now.",
        fields=[("Balance", "balance"), ("Currency", "currency"), ("Blocked", "blockedBalance")],
    ),
    "getLimits": ToolMessage(
        label="Transaction limits",
        working="Checking your transaction limits…",
        success="Here are your current transaction limits.",
        empty="No limit configuration was returned for your account.",
        error="I couldn't fetch your transaction limits just now.",
        fields=[
            ("Per transaction", "perTxnLimit"),
            ("Daily limit", "dailyLimit"),
            ("Daily used", "dailyUsed"),
            ("Monthly limit", "monthlyLimit"),
        ],
    ),
    "getMerchantProfile": ToolMessage(
        label="Merchant profile",
        working="Fetching your merchant profile…",
        success="Here is your merchant profile.",
        empty="No merchant profile was returned.",
        error="I couldn't fetch your merchant profile just now.",
    ),
    "getMerchantStatus": ToolMessage(
        label="Merchant status",
        working="Checking your KYC and account status…",
        success="Here is your current account status.",
        empty="No status record was returned for your account.",
        error="I couldn't check your account status just now.",
    ),
    "getLedgerStatement": ToolMessage(
        label="Ledger statement",
        working="Generating your ledger statement…",
        success="Here is your ledger statement.",
        empty="No statement entries were found for that period.",
        error="I couldn't generate your ledger statement just now.",
    ),
    "getTransaction": ToolMessage(
        label="Transaction details",
        working="Looking up that transaction…",
        success="Here are the transaction details.",
        empty="No transaction was found for that ID.",
        error="I couldn't look up that transaction just now.",
    ),
    "getPassbook": ToolMessage(
        label="Passbook",
        working="Fetching your passbook…",
        success="Here is your passbook.",
        empty="No passbook entries were found.",
        error="I couldn't fetch your passbook just now.",
    ),
    "balanceEnquiry": ToolMessage(
        label="AePS balance enquiry",
        working="Running the AePS balance enquiry…",
        success="Here is the AePS balance enquiry result.",
        empty="The AePS balance enquiry returned no data.",
        error="The AePS balance enquiry could not be completed just now.",
    ),
    "cashWithdrawalStatus": ToolMessage(
        label="Cash withdrawal status",
        working="Checking that cash withdrawal…",
        success="Here is the cash withdrawal status.",
        empty="No cash withdrawal was found for that transaction ID.",
        error="I couldn't check that cash withdrawal just now.",
    ),
    "getPayoutStatus": ToolMessage(
        label="Settlement status",
        working="Checking your settlement status…",
        success="Here is your settlement status.",
        empty="No settlement record was returned.",
        error="I couldn't check your settlement status just now.",
    ),
    "getRDDeviceStatus": ToolMessage(
        label="RD device status",
        working="Checking your biometric device status…",
        success="Here is your biometric device status.",
        empty="No device registration was found.",
        error="I couldn't check your device status just now.",
    ),
    "lookupIFSC": ToolMessage(
        label="IFSC lookup",
        working="Looking up that IFSC code…",
        success="Here are the bank branch details.",
        empty="No branch was found for that IFSC code.",
        error="I couldn't look up that IFSC code just now.",
    ),
    "validateVPA": ToolMessage(
        label="VPA validation",
        working="Validating that UPI address…",
        success="Here is the VPA validation result.",
        empty="The VPA could not be resolved.",
        error="I couldn't validate that UPI address just now.",
    ),
    "raiseTicket": ToolMessage(
        label="Support ticket",
        working="Raising a support ticket for you…",
        success="Your support ticket has been raised.",
        empty="The ticket could not be created.",
        error="I couldn't raise the support ticket just now.",
    ),
    "getTicketStatus": ToolMessage(
        label="Ticket status",
        working="Checking your support ticket…",
        success="Here is your support ticket status.",
        empty="No ticket was found for that ID.",
        error="I couldn't check your support ticket just now.",
    ),
    # Note: `closeTicket` deliberately has no entry. The original prompts
    # advertised it, but no such tool is registered — `tools/ticket.py` exposes
    # close_ticket as a plain function that was never decorated with @tool. Since
    # the catalogue handed to the model is now generated from the registry, the
    # name can no longer be emitted, and closing a ticket is a write action that
    # stays out of chat regardless.
    "sendAlert": ToolMessage(
        label="Send alert",
        working="Dispatching that alert…",
        success="The alert has been dispatched.",
        empty="The alert could not be dispatched.",
        error="I couldn't dispatch the alert just now.",
    ),
    "reverseTransaction": ToolMessage(
        label="Transaction reversal",
        working="Processing the transaction reversal…",
        success="The reversal has been processed.",
        empty="The reversal could not be processed.",
        error="I couldn't process the reversal just now.",
    ),
}


_GENERIC = ToolMessage(
    label="Request",
    working="Working on that…",
    success="Here is what I found.",
    empty="No data was returned for that request.",
    error="I couldn't complete that request just now. Please try again shortly.",
)


def get_message(tool_name: str) -> ToolMessage:
    """Return the wording for a tool, falling back to neutral generic copy."""
    return TOOL_MESSAGES.get(tool_name, _GENERIC)
