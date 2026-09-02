#!/usr/bin/env python3
"""
tlsctx.py — one TLS context for every network call, and a diagnosis when it fails.

THE PROBLEM THIS SOLVES
    Python from python.org on macOS does not read the system keychain. So on a
    Mac it either has no trusted CAs at all (nobody ran
    `Install Certificates.command`) or, on a network or under security software
    that intercepts TLS, it cannot see the interception root that Safari and
    curl trust from the keychain. Both surface as

        [SSL: CERTIFICATE_VERIFY_FAILED] ... self-signed certificate in certificate chain

    and both are fixed the same way: give Python the operating system's trust
    store. The `truststore` package (written by the pip maintainers, and what
    pip itself uses) does exactly that.

WHAT THIS FILE WILL NOT DO
    Disable verification. `ssl._create_unverified_context` would make the
    error go away and would also let anyone between this machine and the
    broker read and rewrite the traffic. Every context built here has
    check_hostname on and verify_mode CERT_REQUIRED, and a test pins it.

ORDER OF PREFERENCE
    1. truststore   → the OS keychain (macOS Security.framework, Windows
                      CertStore, OpenSSL on Linux). Handles interception roots.
    2. certifi      → Mozilla's bundle, if installed. Handles the
                      "no CAs at all" case, not interception.
    3. ssl default  → whatever OpenSSL was built with.

USAGE
    import tlsctx
    urllib.request.urlopen(req, context=tlsctx.context())
    ...
    except Exception as e:
        if tlsctx.is_cert_failure(e): raise Unreachable(tlsctx.explain(e))
"""

import ssl
import sys


def _truststore():
    try:
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        return None


def _certifi():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return None


def context():
    """A verifying SSLContext, from the best trust store available."""
    ctx = _truststore() or _certifi() or ssl.create_default_context()
    # Belt and braces: never hand back a context that has been loosened.
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


def source():
    """Which trust store `context()` would use — for the diagnosis."""
    if _truststore() is not None:
        return "truststore (operating-system keychain)"
    if _certifi() is not None:
        return "certifi (Mozilla bundle; cannot see an interception root)"
    return "python's built-in OpenSSL defaults"


def is_cert_failure(exc):
    reason = getattr(exc, "reason", None)
    return (isinstance(exc, ssl.SSLCertVerificationError)
            or isinstance(reason, ssl.SSLCertVerificationError)
            or "CERTIFICATE_VERIFY_FAILED" in str(exc))


def explain(exc):
    """The error, what it means, and the two commands that fix it."""
    py = sys.executable
    return (
        f"TLS certificate verification failed: {exc}\n"
        f"\n"
        f"  Python is using: {source()}\n"
        f"  This Python is:  {py}\n"
        f"\n"
        f"  This is almost always Python not seeing the Mac keychain — either no\n"
        f"  CA bundle was ever installed, or something on this network is\n"
        f"  intercepting TLS with a root that Safari and curl trust and Python\n"
        f"  cannot see. Verification was NOT disabled and will not be.\n"
        f"\n"
        f"  Fix, in this order:\n"
        f"    {py} -m pip install truststore      # make Python use the keychain\n"
        f"  and if that is not enough (no CAs at all):\n"
        f"    open \"/Applications/Python 3.*/Install Certificates.command\"\n"
        f"\n"
        f"  To tell which case you are in:  curl -sI https://stooq.com | head -1\n"
        f"  If curl gets a 200 and Python does not, it is the keychain, and\n"
        f"  truststore fixes it.")


if __name__ == "__main__":
    ctx = context()
    print(f"trust store : {source()}")
    print(f"hostname    : {'checked' if ctx.check_hostname else 'NOT CHECKED'}")
    print(f"verify mode : {ctx.verify_mode.name}")
    print(f"python      : {sys.executable}")
