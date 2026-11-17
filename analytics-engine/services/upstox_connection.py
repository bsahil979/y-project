"""User-bound Upstox OAuth and holdings preview. Single-process session storage."""
import os
import secrets
import time
from threading import Lock
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
router = APIRouter(prefix="/brokers/upstox")
_states = {}
_tokens = {}
_outcomes = {}
_lock = Lock()


def configured():
    return all(os.getenv(key) for key in ("UPSTOX_CLIENT_ID", "UPSTOX_CLIENT_SECRET",
               "UPSTOX_REDIRECT_URI", "SUPABASE_URL", "SUPABASE_ANON_KEY", "FRONTEND_ORIGIN"))


def owner(authorization: str = Header(default="")):
    if not configured():
        raise HTTPException(503, "Upstox connection needs server configuration.")
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sign in to connect a brokerage.")
    try:
        response = requests.get(os.environ["SUPABASE_URL"].rstrip("/") + "/auth/v1/user",
                                headers={"Authorization": authorization, "apikey": os.environ["SUPABASE_ANON_KEY"]},
                                timeout=15)
        response.raise_for_status()
        user_id = response.json()["id"]
    except (requests.RequestException, ValueError, KeyError):
        raise HTTPException(401, "Your app session expired. Sign in again.")
    return user_id


@router.get("/status")
def status():
    return {"configured": configured()}


@router.get("/connection")
def connection(user_id=Depends(owner)):
    with _lock:
        connected = bool(_tokens.get(user_id))
    return {"connected": connected, "storage": "server_session",
            "authorization_result": _outcomes.get(user_id)}


@router.post("/connect")
def connect(user_id=Depends(owner)):
    state = secrets.token_urlsafe(32)
    with _lock:
        for key in list(_states):
            if _states[key][1] < time.time():
                del _states[key]
        _states[state] = (user_id, time.time() + 600)
        _outcomes[user_id] = "pending"
    return {"url": "https://api.upstox.com/v2/login/authorization/dialog?" + urlencode({
        "client_id": os.environ["UPSTOX_CLIENT_ID"], "redirect_uri": os.environ["UPSTOX_REDIRECT_URI"],
        "response_type": "code", "state": state})}


def callback_result(result, user_id=None):
    if user_id is not None:
        with _lock:
            _outcomes[user_id] = result
    return RedirectResponse(
        os.environ["FRONTEND_ORIGIN"].rstrip("/") +
        "/dashboard/portfolio?" + urlencode({"upstox": result}),
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
    )


@router.get("/callback")
def callback(state: str = "", code: str = "", request_token: str = "", status: str = ""):
    # Older Kite developer registrations used this callback URL. Delegate only
    # Kite-shaped responses; Zerodha still validates its own single-use state.
    if request_token and not code:
        from services.zerodha_connection import callback as zerodha_callback
        return zerodha_callback(state=state, request_token=request_token, status=status)
    with _lock:
        pending = _states.pop(state, None)
    if not pending or pending[1] < time.time() or not code:
        raise HTTPException(400, "Connection expired or declined. Start again in the app.")
    try:
        response = requests.post("https://api.upstox.com/v2/login/authorization/token", data={
            "code": code, "client_id": os.environ["UPSTOX_CLIENT_ID"],
            "client_secret": os.environ["UPSTOX_CLIENT_SECRET"],
            "redirect_uri": os.environ["UPSTOX_REDIRECT_URI"], "grant_type": "authorization_code"}, timeout=20)
        if not response.ok:
            try:
                payload = response.json()
                errors = payload.get("errors", [])
                codes = {item.get("errorCode") or item.get("error_code")
                         for item in errors if isinstance(item, dict)}
            except (ValueError, AttributeError, TypeError):
                codes = set()
            reasons = {
                "UDAPI100069": "invalid_credentials",
                "UDAPI100070": "invalid_redirect",
                "UDAPI100057": "invalid_code",
            }
            reason = next((value for key, value in reasons.items() if key in codes),
                          "token_rejected")
            return callback_result(reason, pending[0])
        token = response.json().get("access_token")
        if not isinstance(token, str) or not token.strip():
            return callback_result("invalid_response", pending[0])
    except requests.RequestException:
        return callback_result("network_error", pending[0])
    except (ValueError, AttributeError):
        return callback_result("invalid_response", pending[0])
    with _lock:
        _tokens[pending[0]] = token
    return callback_result("connected", pending[0])



@router.post("/holdings")
def holdings(user_id=Depends(owner)):
    with _lock:
        token = _tokens.get(user_id)
    if not token:
        raise HTTPException(409, "Connect Upstox first. Connections expire after a server restart.")
    try:
        response = requests.get("https://api.upstox.com/v2/portfolio/long-term-holdings",
                                headers={"Authorization": "Bearer " + token}, timeout=20)
        if response.status_code in (401, 403):
            with _lock:
                if _tokens.get(user_id) == token:
                    _tokens.pop(user_id, None)
            raise HTTPException(401, "Upstox authorization expired. Reconnect your account.")
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success" or not isinstance(payload.get("data"), list):
            raise ValueError("Invalid holdings response")
    except (requests.RequestException, ValueError):
        raise HTTPException(502, "Upstox holdings could not be fetched. Try again.")
    return {"holdings": payload["data"]}


@router.delete("/connection")
def disconnect(user_id=Depends(owner)):
    with _lock:
        _tokens.pop(user_id, None)
        _outcomes.pop(user_id, None)
        for key in list(_states):
            if _states[key][0] == user_id:
                del _states[key]
    return {"disconnected": True}


# Read-only broker sections. Failed sections are never represented as empty accounts.
_PORTFOLIO_SECTIONS = {
    "equities": ("v2/portfolio/long-term-holdings", False, list),
    "mutual_funds": ("v2/mf/holdings", False, list),
    "positions": ("v2/portfolio/short-term-positions", False, list),
    "mtf_positions": ("v3/portfolio/mtf-positions", False, list),
    "sips": ("v2/mf/sips", True, list),
    "fund_orders": ("v2/mf/orders", True, list),
    "funds_margin": ("v2/user/get-funds-and-margin", False, dict),
}


def fetch_broker_section(token, path, paginated, expected_type):
    rows = []
    for page in range(1, 101):
        try:
            response = requests.get(
                "https://api.upstox.com/" + path,
                headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
                params={"page_number": page, "records": 30} if paginated else None,
                timeout=20)
            if response.status_code == 401:
                return {"status": "authorization_expired", "data": None, "message": "Upstox authorization expired. Reconnect."}
            if response.status_code in (403, 404):
                return {"status": "unavailable", "data": None, "message": "Upstox did not permit this endpoint. Check API subscription access for this category."}
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data")
            if payload.get("status") != "success" or not isinstance(data, expected_type):
                raise ValueError("Invalid broker payload")
            if expected_type is list and any(not isinstance(row, dict) for row in data):
                raise ValueError("Invalid broker row")
            if not paginated:
                return {"status": "ok", "data": data}
            rows.extend(data)
            total_pages = payload.get("meta_data", {}).get("page", {}).get("total_pages")
            if (total_pages is not None and page >= int(total_pages)) or (total_pages is None and len(data) < 30):
                return {"status": "ok", "data": rows}
        except (requests.RequestException, ValueError, TypeError, AttributeError):
            return {"status": "unavailable", "data": None, "message": "Upstox could not supply this category. Try again or check your API subscription."}
    return {"status": "partial", "data": rows, "message": "Showing the first 3,000 records; additional records were not fetched."}


@router.post("/portfolio")
def broker_portfolio(user_id=Depends(owner)):
    from concurrent.futures import ThreadPoolExecutor
    from datetime import datetime, timezone
    with _lock:
        token = _tokens.get(user_id)
    if not token:
        raise HTTPException(409, "Connect Upstox first. Connections expire after a server restart.")
    with ThreadPoolExecutor(max_workers=7) as pool:
        jobs = {name: pool.submit(fetch_broker_section, token, *spec)
                for name, spec in _PORTFOLIO_SECTIONS.items()}
        sections = {name: job.result() for name, job in jobs.items()}
    expired = any(section["status"] == "authorization_expired" for section in sections.values())
    if expired:
        with _lock:
            if _tokens.get(user_id) == token:
                _tokens.pop(user_id, None)
        raise HTTPException(401, "Upstox authorization expired. Reconnect your account.")
    return {"sections": sections, "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "Upstox", "read_only": True}
