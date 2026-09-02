#!/usr/bin/env python3
"""
broker.py — send an order to Alpaca, paper or live, and report what came back.

Runs on the Mac, and only ever by Daniel's hand. No agent in this fleet calls
this file; the standing constraint every one of them carries — never publish,
post, list, or buy — reads here as: never places an order.

TWO ENDPOINTS, KEPT APART BY NAME
    PAPER  https://paper-api.alpaca.markets    simulated money, real fills
    LIVE   https://api.alpaca.markets          real money

    A paper key pair does not work on the live endpoint and vice versa, which
    is a useful property: pointing the wrong keys at the wrong base fails
    loudly rather than trading the wrong account.

WHAT IT REFUSES
    No credentials → NoCredentials. They come from the environment
    (ALPACA_KEY_ID, ALPACA_SECRET_KEY), never from arguments.
    A rejected order → Rejected, with Alpaca's own message.
    An unreachable host → Unreachable.
    None of those ever return a fake order.

FILLS ARE ASYNCHRONOUS
    A market order is `accepted` immediately and `filled` a moment later.
    `wait_for_fill` polls briefly. If it is still unfilled when the wait ends,
    the record says so with filled_qty 0 — and run.py's live gate will not
    count it as evidence. That is correct: an order that never filled proves
    nothing about slippage.
"""

import json
import os
import time
import urllib.error
import urllib.request

PAPER = "https://paper-api.alpaca.markets"
LIVE = "https://api.alpaca.markets"
TIMEOUT = 20
UA = "market-tools/1.0"


class NoCredentials(Exception):
    pass


class Unreachable(Exception):
    pass


class Rejected(Exception):
    """Alpaca said no, and said why."""


def credentials():
    key = os.environ.get("ALPACA_KEY_ID", "").strip()
    sec = os.environ.get("ALPACA_SECRET_KEY", "").strip()
    if not key or not sec:
        raise NoCredentials("ALPACA_KEY_ID / ALPACA_SECRET_KEY are not set. "
                            "Export them in the shell; never pass them as arguments.")
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}


def _call(base, path, hdr, body=None, method=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        base + path, data=data, method=method or ("POST" if data else "GET"),
        headers={"User-Agent": UA, "Content-Type": "application/json",
                 "Accept": "application/json", **hdr})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")[:400]
        if e.code in (401, 403):
            raise Unreachable(f"HTTP {e.code} — credentials refused for {base}: {msg}")
        if 400 <= e.code < 500:
            raise Rejected(f"HTTP {e.code}: {msg}")
        raise Unreachable(f"HTTP {e.code}: {msg}")
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise Unreachable(f"{type(e).__name__}: {e}")


def account(base, hdr):
    """Who am I about to trade as. Print this before any live order."""
    a = _call(base, "/v2/account", hdr)
    return {"account_number": a.get("account_number"), "status": a.get("status"),
            "equity": a.get("equity"), "buying_power": a.get("buying_power"),
            "paper": base == PAPER}


def place_order(base, hdr, symbol, side, qty, order_type="market", tif="day"):
    if side not in ("buy", "sell"):
        raise ValueError("side must be buy or sell")
    if qty <= 0:
        raise ValueError("qty must be positive")
    return _call(base, "/v2/orders", hdr, {
        "symbol": symbol.upper(), "qty": str(qty), "side": side,
        "type": order_type, "time_in_force": tif})


def get_order(base, hdr, order_id):
    return _call(base, f"/v2/orders/{order_id}", hdr)


def wait_for_fill(base, hdr, order_id, seconds=10, every=1.0):
    deadline = time.time() + seconds
    o = get_order(base, hdr, order_id)
    while o.get("status") not in ("filled", "canceled", "rejected", "expired") \
            and time.time() < deadline:
        time.sleep(every)
        o = get_order(base, hdr, order_id)
    return o


def summarise(o):
    """The fields the ledger keeps. filled_qty 0 means it proves nothing yet."""
    return {"order_id": o.get("id"), "status": o.get("status"),
            "side": o.get("side"), "qty": float(o.get("qty") or 0),
            "filled_qty": float(o.get("filled_qty") or 0),
            "filled_avg_price": float(o["filled_avg_price"])
            if o.get("filled_avg_price") else None,
            "submitted_at": o.get("submitted_at"), "filled_at": o.get("filled_at")}
