"""
Builder for `com.digipay.common.bos.FillterBO`, the request body shared by
almost every paginated read endpoint on the DigiPay gateway.

Validation here mirrors the Jakarta constraints on the Java BO so the assistant
fails fast with a helpful message instead of round-tripping to collect
VALIDATION_ERRORS:

    cscId / ownerId  exactly 12 characters
    notifId          exactly 6 characters
    rpp              >= 1   (records per page)
    cp               >= 1   (current page)
    fromDate/toDate  dd-MM-yyyy
"""

import re
from typing import Any, Dict, Optional

from core.exceptions import ValidationException

DATE_PATTERN = re.compile(r"^\d{2}-\d{2}-\d{4}$")

MAX_RECORDS_PER_PAGE = 50


def _normalise_date(value: Optional[str], field: str) -> Optional[str]:
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip()
    if DATE_PATTERN.match(text):
        return text
    # Accept the ISO form users naturally type and convert it for the gateway.
    iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text)
    if iso:
        return f"{iso.group(3)}-{iso.group(2)}-{iso.group(1)}"
    raise ValidationException(
        f"'{field}' must be in dd-MM-yyyy format (received '{text}')."
    )


def require_csc_id(csc_id: Optional[str], field: str = "cscId") -> str:
    if not csc_id or not str(csc_id).strip():
        raise ValidationException(f"'{field}' is required and must be a non-empty string.")
    text = str(csc_id).strip()
    if len(text) != 12:
        raise ValidationException(f"'{field}' length must be exactly 12 (received {len(text)}).")
    return text


def require_txn_id(txn_id: Optional[str], field: str = "txnId") -> str:
    if not txn_id or not str(txn_id).strip():
        raise ValidationException(f"'{field}' is required and must be a non-empty string.")
    return str(txn_id).strip()


def build_filter(
    csc_id: Optional[str] = None,
    owner_id: Optional[str] = None,
    txn_id: Optional[str] = None,
    rrn: Optional[str] = None,
    csc_txn: Optional[str] = None,
    utr: Optional[str] = None,
    bank_iin: Optional[str] = None,
    search: Optional[str] = None,
    state_code: Optional[int] = None,
    district_code: Optional[int] = None,
    lgr_txn_type: Optional[str] = None,
    type: Optional[str] = None,
    txn_type: Optional[str] = None,
    notification_type: Optional[str] = None,
    device_type: Optional[str] = None,
    active_status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    rpp: int = 10,
    cp: int = 1,
    notif_id: Optional[str] = None,
    result_type: Optional[str] = None,
    role: Optional[str] = None,
    auth_for: Optional[str] = None,
    status: Optional[str] = None,
    require_csc: bool = False,
) -> Dict[str, Any]:
    """Assemble a validated FillterBO payload, omitting unset fields."""
    if require_csc:
        csc_id = require_csc_id(csc_id)
    elif csc_id is not None and str(csc_id).strip():
        csc_id = require_csc_id(csc_id)
    else:
        csc_id = None

    if owner_id is not None and str(owner_id).strip():
        owner_id = require_csc_id(owner_id, "ownerId")
    else:
        owner_id = None

    if notif_id is not None and str(notif_id).strip():
        notif_id = str(notif_id).strip()
        if len(notif_id) != 6:
            raise ValidationException(
                f"'notifId' length must be exactly 6 (received {len(notif_id)})."
            )
    else:
        notif_id = None

    try:
        rpp = int(rpp)
        cp = int(cp)
    except (TypeError, ValueError):
        raise ValidationException("'rpp' and 'cp' must be integers.")

    if rpp < 1:
        raise ValidationException("'rpp' (records per page) must be at least 1.")
    if cp < 1:
        raise ValidationException("'cp' (current page) must be at least 1.")
    # Chat renders a summary, never thousands of rows; keep pages conversational.
    rpp = min(rpp, MAX_RECORDS_PER_PAGE)

    payload: Dict[str, Any] = {
        "cscId": csc_id,
        "ownerId": owner_id,
        "txnId": (str(txn_id).strip() if txn_id else None),
        "rrn": (str(rrn).strip() if rrn else None),
        "cscTxn": (str(csc_txn).strip() if csc_txn else None),
        "utr": (str(utr).strip() if utr else None),
        "bankIin": (str(bank_iin).strip() if bank_iin else None),
        "search": (str(search).strip() if search else None),
        "stateCode": state_code,
        "districtCode": district_code,
        "lgrTxnType": (str(lgr_txn_type).strip().upper() if lgr_txn_type else None),
        "type": (str(type).strip().upper() if type else None),
        "txnType": (str(txn_type).strip().upper() if txn_type else None),
        "notificationType": (str(notification_type).strip().upper() if notification_type else None),
        "deviceType": (str(device_type).strip().upper() if device_type else None),
        "activeStatus": (str(active_status).strip().upper() if active_status else None),
        "fromDate": _normalise_date(from_date, "fromDate"),
        "toDate": _normalise_date(to_date, "toDate"),
        "notifId": notif_id,
        "resultType": (str(result_type).strip().upper() if result_type else None),
        "role": (str(role).strip().upper() if role else None),
        "authFor": (str(auth_for).strip() if auth_for else None),
        "status": (str(status).strip().upper() if status else None),
        "rpp": rpp,
        "cp": cp,
    }
    return {k: v for k, v in payload.items() if v is not None}
