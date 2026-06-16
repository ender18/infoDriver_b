import hmac
import hashlib
import json
import os

import requests as http_requests
from fastapi import HTTPException


PEIBO_BASE = os.getenv("PEIBO_BASE_URL")


def send_transfer(company, peibo_payload: dict) -> tuple[int, dict]:
    payload_str = json.dumps(peibo_payload, separators=(",", ":"), ensure_ascii=False)
    signature   = hmac.new(
        company.peibo_api_key.encode("utf-8"),
        payload_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    headers = {
        "Content-Type":    "application/json",
        "X-MSG-SIGNATURE": signature,
        "X-CUSTOMER-KEY":  company.peibo_customer_key,
    }

    try:
        resp = http_requests.post(
            f"{PEIBO_BASE}/latest/order/transfer",
            data=payload_str.encode("utf-8"),
            headers=headers,
            timeout=30,
        )
    except http_requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Error de conexión con Peibo: {exc}")

    try:
        peibo_response = resp.json()
    except Exception:
        peibo_response = {"raw": resp.text}

    return resp.status_code, peibo_response
