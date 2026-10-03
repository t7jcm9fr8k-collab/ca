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
    (ALPACA_KEY_ID, ALPACA_SECRET_KEY) or, when the environment holds neither,
    the macOS login keychain (services alpaca-key-id, alpaca-secret-key;
    CA_NO_KEYCHAIN=1 turns that off) — never from arguments.
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

import hashlib
import http.client
import json
import math
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import tlsctx

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


# Where the keys may live, in order: the environment (as before), then the macOS
# login keychain under these service names — which keeps the secret out of
# ~/.zshrc, out of shell history, and out of the environment every shell and
# every agent inherits. CA_NO_KEYCHAIN=1 turns the keychain off (the tests set
# it, so a machine whose keychain holds real keys can never trade from them).
KEYCHAIN = {"ALPACA_KEY_ID": "alpaca-key-id", "ALPACA_SECRET_KEY": "alpaca-secret-key"}


def _keychain(service):
    """A secret from the macOS login keychain, or "" — never raises."""
    if os.environ.get("CA_NO_KEYCHAIN") or sys.platform != "darwin" or not shutil.which("security"):
        return ""
    try:
        r = subprocess.run(["security", "find-generic-password", "-s", service, "-w"],
                           capture_output=True, timeout=10)
        out = r.stdout.decode("ascii").strip()      # a key pair is ASCII; anything else is not one
    except (OSError, subprocess.SubprocessError, ValueError):
        return ""
    return out if r.returncode == 0 else ""


def credentials():
    """
    The Alpaca key pair — both halves from ONE place: the environment when it
    holds either, the keychain only when it holds neither. A mixed pair used
    to form silently, so unsetting one variable to disarm a run was undone by
    the keychain. A malformed value is refused by NAME and source, never
    shown: a two-line paste used to reach http.client, whose error quoted both
    halves into stderr, the cron log and any transcript saved from it.
    """
    env = {name: os.environ.get(name, "").strip() for name in KEYCHAIN}
    if any(env.values()):
        vals, where = env, {name: "the environment" for name in KEYCHAIN}
        if not all(vals.values()):
            missing = [n for n, v in vals.items() if not v][0]
            raise NoCredentials(f"only one of ALPACA_KEY_ID / ALPACA_SECRET_KEY is set in the "
                                f"environment ({missing} is not); the keychain is not consulted "
                                f"for half a pair. Set both, or unset both.")
    else:
        vals = {name: _keychain(svc) for name, svc in KEYCHAIN.items()}
        where = {name: f"the keychain item {svc}" for name, svc in KEYCHAIN.items()}
    if not all(vals.values()):
        raise NoCredentials("ALPACA_KEY_ID / ALPACA_SECRET_KEY are not set — neither in the "
                            "environment nor in the macOS keychain (services alpaca-key-id and "
                            "alpaca-secret-key). Never pass them as arguments.")
    for name, v in vals.items():
        if any(c.isspace() or not c.isprintable() or ord(c) > 126 for c in v):
            raise NoCredentials(f"{name} (from {where[name]}) contains whitespace or a "
                                f"non-printing character — a two-line paste? (its value is not shown)")
    return {"APCA-API-KEY-ID": vals["ALPACA_KEY_ID"], "APCA-API-SECRET-KEY": vals["ALPACA_SECRET_KEY"]}


def redact(text, hdr):
    """Remove the key and secret from any text that might be printed or logged."""
    for v in (hdr or {}).values():
        if isinstance(v, str) and len(v) >= 6:
            text = text.replace(v, "<redacted>")
    return text


def mask_account(number):
    """An account number as it may be printed: the last four characters."""
    s = str(number or "")
    return ("…" + s[-4:]) if len(s) > 4 else s


def _call(base, path, hdr, body=None, method=None):
    data = json.dumps(body).encode() if body is not None else None
    try:
        req = urllib.request.Request(
            base + path, data=data, method=method or ("POST" if data else "GET"),
            headers={"User-Agent": UA, "Content-Type": "application/json",
                     "Accept": "application/json", **hdr})
        # Credentialed: a redirect is refused, never followed with the keys attached.
        with tlsctx.opener(follow_redirects=False).open(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")
        except (OSError, http.client.HTTPException):
            body = "(the error body could not be read)"
        # Redacted BEFORE it is cut: a secret straddling the cut used to leave
        # its first part in the message. `from None` everywhere a message is
        # redacted: the chained original still holds the raw text.
        msg = redact(body, hdr)[:400]
        if e.code in (401, 403):
            raise Unreachable(f"HTTP {e.code} — credentials refused for {base}: {msg}") from None
        if 400 <= e.code < 500:
            raise Rejected(f"HTTP {e.code}: {msg}") from None
        raise Unreachable(f"HTTP {e.code}: {msg}") from None
    except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as e:
        # http.client's IncompleteRead / BadStatusLine — a reply cut short after
        # the broker may have accepted the order — escaped as a traceback and
        # skipped the lookup that settles it. Now Unreachable like any other.
        if tlsctx.is_cert_failure(e):
            raise Unreachable(tlsctx.explain(e)) from None
        raise Unreachable(redact(f"{type(e).__name__}: {e}", hdr)) from None


def account(base, hdr):
    """Who am I about to trade as. Print this before any live order."""
    a = _call(base, "/v2/account", hdr)
    return {"account_number": a.get("account_number"), "status": a.get("status"),
            "equity": a.get("equity"), "buying_power": a.get("buying_power"),
            "paper": base == PAPER}


def positions(base, hdr):
    """{symbol: qty} of open positions. Empty dict means flat, not unknown;
    a quantity that is not a readable, finite number raises Unreachable."""
    out = {}
    for p in _call(base, "/v2/positions", hdr) or []:
        try:
            q = float(p.get("qty") or 0)
        except (TypeError, ValueError):
            q = math.nan
        if not math.isfinite(q):
            # "NaN" compares False with everything: a sell check passed it, and
            # a position skipped as unreadable read as flat, which invites a
            # buy. Unknown, so nothing trades.
            raise Unreachable(f"the broker reported a quantity for {p.get('symbol')!r} "
                              f"that is not a finite number; positions are unknown")
        out[str(p.get("symbol", "")).upper()] = q
    return out


def client_order_id(*parts):
    """
    The same decision always gets the same id. Alpaca refuses a second order
    under an id it has already seen, so a retry after an ambiguous failure — a
    timeout on the POST, a lost reply, a crash before the ledger write — cannot
    place the order twice. "ca-" plus 40 hex characters: under Alpaca's limit.
    """
    return "ca-" + hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:40]


def is_duplicate(err):
    """True when Alpaca refused an order because its client_order_id was already used."""
    return isinstance(err, Rejected) and "client_order_id" in str(err).lower()


def order_by_client_id(base, hdr, coid):
    """
    The order this decision's id names, or None when the broker has none. Only
    a 404 means none: a 429 or a 400 used to read the same, and the caller
    then told the user "nothing sent, safe to re-run" about an order that had
    landed. Any other refusal is an unanswered question — Unreachable.
    """
    try:
        return _call(base, "/v2/orders:by_client_order_id?client_order_id="
                     + urllib.parse.quote(coid, safe=""), hdr)
    except Rejected as e:
        if str(e).startswith("HTTP 404"):
            return None
        raise Unreachable(f"the order lookup was refused, so whether it exists is unknown: {e}") from None


def place_order(base, hdr, symbol, side, qty=None, notional=None, order_type="market",
                tif="day", client_order_id=None):
    """
    One of `qty` (shares) or `notional` (dollars, fractional shares) — never
    both, never neither. Alpaca fills a notional market order in fractional
    shares, which is what lets a rule hold 0.37 of an allocation.
    """
    if side not in ("buy", "sell"):
        raise ValueError("side must be buy or sell")
    if (qty is None) == (notional is None):
        raise ValueError("give exactly one of qty or notional")
    if qty is not None and not (math.isfinite(float(qty)) and float(qty) > 0):
        raise ValueError("qty must be a positive, finite number")
    if notional is not None and not (math.isfinite(float(notional))
                                     and round(float(notional), 2) > 0):
        # 0.004 used to pass "> 0" and go out as notional "0.00"
        raise ValueError("notional must be a positive, finite amount of at least $0.01")
    body = {"symbol": symbol.upper(), "side": side, "type": order_type, "time_in_force": tif}
    if qty is not None:
        body["qty"] = str(qty)
    else:
        body["notional"] = f"{float(notional):.2f}"
    if client_order_id:
        body["client_order_id"] = client_order_id
    return _call(base, "/v2/orders", hdr, body)


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
