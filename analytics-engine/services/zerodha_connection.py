"""User-bound Zerodha OAuth and holdings preview. Single-process session storage."""
import hashlib
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
router = APIRouter(prefix="/brokers/zerodha")
_states = {}
_tokens = {}
_outcomes = {}
_lock = Lock()


def configured():
    return all(os.getenv(key) for key in ("ZERODHA_CLIENT_ID", "ZERODHA_CLIENT_SECRET",
               "ZERODHA_REDIRECT_URI", "SUPABASE_URL", "SUPABASE_ANON_KEY", "FRONTEND_ORIGIN"))


def owner(authorization: str = Header(default="")):
    if not configured():
        raise HTTPException(503, "Zerodha connection needs server configuration.")
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
    return {"url": "https://kite.zerodha.com/connect/login?" + urlencode({
        "v": "3", "api_key": os.environ["ZERODHA_CLIENT_ID"],
        "redirect_params": urlencode({"state": state})})}



def callback_result(result, user_id=None):
    if user_id is not None:
        with _lock:
            _outcomes[user_id] = result
    return RedirectResponse(
        os.environ["FRONTEND_ORIGIN"].rstrip("/") +
        "/dashboard/portfolio?" + urlencode({"zerodha": result}),
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
    )


@router.get("/callback")
def callback(state: str = "", request_token: str = "", status: str = ""):
    with _lock:
        pending = _states.pop(state, None)
    if not pending or pending[1] < time.time():
        raise HTTPException(400, "Connection expired. Start again in the app.")
    if not request_token or status != "success":
        return callback_result("invalid_code", pending[0])
    checksum = hashlib.sha256((os.environ["ZERODHA_CLIENT_ID"] + request_token +
                               os.environ["ZERODHA_CLIENT_SECRET"]).encode()).hexdigest()
    try:
        response = requests.post("https://api.kite.trade/session/token", data={
            "api_key": os.environ["ZERODHA_CLIENT_ID"], "request_token": request_token,
            "checksum": checksum}, headers={"X-Kite-Version": "3"}, timeout=20)
        if not response.ok:
            return callback_result("token_rejected", pending[0])
        payload = response.json()
        token = payload.get("data", {}).get("access_token")
        if payload.get("status") != "success" or not isinstance(token, str) or not token.strip():
            return callback_result("invalid_response", pending[0])
    except requests.RequestException:
        return callback_result("network_error", pending[0])
    except (ValueError, AttributeError, TypeError):
        return callback_result("invalid_response", pending[0])
    with _lock:
        _tokens[pending[0]] = token
    return callback_result("connected", pending[0])


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
    "equities": ("portfolio/holdings", list),
    "mutual_funds": ("mf/holdings", list),
    "positions": ("portfolio/positions", dict),
    "sips": ("mf/sips", list),
    "fund_orders": ("mf/orders", list),
    "funds_margin": ("user/margins", dict),
}


def fetch_broker_section(token, path, expected_type):
    try:
        response = requests.get("https://api.kite.trade/" + path, headers={
            "Authorization": "token " + os.environ["ZERODHA_CLIENT_ID"] + ":" + token,
            "X-Kite-Version": "3"}, timeout=20)
        if response.status_code in (401, 403):
            return {"status": "authorization_expired", "data": None}
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data")
        if payload.get("status") != "success" or not isinstance(data, expected_type):
            raise ValueError("Invalid broker payload")
        if expected_type is list and any(not isinstance(row, dict) for row in data):
            raise ValueError("Invalid broker row")
        return {"status": "ok", "data": data}
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        return {"status": "unavailable", "data": None,
                "message": "Zerodha could not supply this category. Try again or check API access."}


def enrich_fund_navs(sections):
    """Use a public, dated AMFI quote when Kite omits the NAV date."""
    funds = sections.get("mutual_funds", {}).get("data") or []
    missing = [row for row in funds if not row.get("last_price_date")]
    if not missing:
        return
    from services.fund_nav import parse_nav
    try:
        response = requests.get("https://www.amfiindia.com/spages/NAVAll.txt", timeout=20)
        response.raise_for_status()
        for row in missing:
            try:
                quote = parse_nav(response.text, row.get("tradingsymbol", ""))
                row.update(last_price=quote["nav"], last_price_date=quote["date"],
                           valuation_source="AMFI")
            except (ValueError, LookupError):
                pass  # The preview reports the missing dated valuation explicitly.
    except requests.RequestException:
        pass


@router.post("/portfolio")
def broker_portfolio(user_id=Depends(owner)):
    from concurrent.futures import ThreadPoolExecutor
    from datetime import datetime, timezone
    with _lock:
        token = _tokens.get(user_id)
    if not token:
        raise HTTPException(409, "Connect Zerodha first. Connections expire after a server restart.")
    with ThreadPoolExecutor(max_workers=7) as pool:
        jobs = {name: pool.submit(fetch_broker_section, token, *spec)
                for name, spec in _PORTFOLIO_SECTIONS.items()}
        sections = {name: job.result() for name, job in jobs.items()}
    expired = any(section["status"] == "authorization_expired" for section in sections.values())
    if expired:
        with _lock:
            if _tokens.get(user_id) == token:
                _tokens.pop(user_id, None)
        raise HTTPException(401, "Zerodha authorization expired. Reconnect your account.")
    enrich_fund_navs(sections)
    return {"sections": sections, "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "Zerodha", "read_only": True}
