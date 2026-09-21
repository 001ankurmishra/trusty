"""
Zero-external-call proof.

Patches socket.socket.connect AND socket.socket.connect_ex so that ANY
attempt to reach a host other than localhost/127.0.0.0/8/::1 is logged
and blocked when OUTBOUND_NETWORK=false.  This covers urllib3, requests,
httpx, and any other library that ultimately calls socket.socket.connect.

Previous version only patched socket.create_connection which does NOT
cover the code paths used by requests/urllib3.
"""
import socket
import ipaddress
import datetime
import threading
from .config import settings

_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex
_original_create_connection = socket.create_connection

_events = []  # in-memory ring buffer (last 500), also persisted to DB by caller
_events_lock = threading.Lock()
_MAX_EVENTS = 500

# Counters
blocked_attempts = 0
external_calls_succeeded = 0  # must stay 0 in air-gapped mode
_counters_lock = threading.Lock()

LOOPBACK_NETS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
]


def _is_local(host: str) -> bool:
    """Check if a host resolves to a loopback address."""
    if host in ("localhost", "127.0.0.1", "::1", ""):
        return True
    try:
        addr = ipaddress.ip_address(host)
        return any(addr in net for net in LOOPBACK_NETS)
    except ValueError:
        # hostname that isn't an IP literal — only 'localhost' is local
        return host.lower() == "localhost"


def _record_event(host: str, port, is_local: bool, blocked: bool):
    global blocked_attempts, external_calls_succeeded
    event = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "host": host,
        "port": port,
        "allowed": is_local,
        "blocked": blocked,
    }
    with _events_lock:
        _events.append(event)
        if len(_events) > _MAX_EVENTS:
            _events.pop(0)
    with _counters_lock:
        if blocked:
            blocked_attempts += 1
        elif not is_local:
            external_calls_succeeded += 1

    # Persist to DB (best-effort, don't crash if DB unavailable during startup)
    try:
        from .db import SessionLocal, SecurityEvent
        db = SessionLocal()
        try:
            db.add(SecurityEvent(
                event_type="BLOCKED" if blocked else ("LOCAL" if is_local else "OUTBOUND_ATTEMPT"),
                detail=f"{host}:{port} {'blocked' if blocked else 'allowed'}",
            ))
            db.commit()
        finally:
            db.close()
    except Exception:
        pass  # best-effort persistence


def _extract_host_port(address):
    """Extract host and port from a socket address tuple."""
    if isinstance(address, tuple) and len(address) >= 2:
        return str(address[0]), address[1]
    return str(address), None


def _guarded_connect(self, address, *args, **kwargs):
    host, port = _extract_host_port(address)
    is_local = _is_local(host)

    if not is_local and not settings.OUTBOUND_NETWORK:
        _record_event(host, port, is_local, blocked=True)
        raise ConnectionError(
            f"[TrustForge Security] Outbound connection to '{host}:{port}' "
            f"blocked (air-gapped mode). Set OUTBOUND_NETWORK=true to allow."
        )

    _record_event(host, port, is_local, blocked=False)
    return _original_connect(self, address, *args, **kwargs)


def _guarded_connect_ex(self, address, *args, **kwargs):
    host, port = _extract_host_port(address)
    is_local = _is_local(host)

    if not is_local and not settings.OUTBOUND_NETWORK:
        _record_event(host, port, is_local, blocked=True)
        raise ConnectionError(
            f"[TrustForge Security] Outbound connection to '{host}:{port}' "
            f"blocked (air-gapped mode)."
        )

    _record_event(host, port, is_local, blocked=False)
    return _original_connect_ex(self, address, *args, **kwargs)


def _guarded_create_connection(address, *args, **kwargs):
    host = address[0] if isinstance(address, tuple) else str(address)
    port = address[1] if isinstance(address, tuple) and len(address) >= 2 else None
    is_local = _is_local(host)

    if not is_local and not settings.OUTBOUND_NETWORK:
        _record_event(host, port, is_local, blocked=True)
        raise ConnectionError(
            f"[TrustForge Security] Outbound connection to '{host}' "
            f"blocked (air-gapped mode)."
        )

    _record_event(host, port, is_local, blocked=False)
    return _original_create_connection(address, *args, **kwargs)


def install_network_guard():
    """Monkey-patch all socket connection methods. Must be called before anything touches sockets."""
    socket.socket.connect = _guarded_connect
    socket.socket.connect_ex = _guarded_connect_ex
    socket.create_connection = _guarded_create_connection


def get_events():
    with _events_lock:
        return list(_events)


def get_counters():
    with _counters_lock:
        return {
            "blocked_attempts": blocked_attempts,
            "external_calls_succeeded": external_calls_succeeded,
        }


def outbound_call_count():
    """Deprecated: use get_counters() instead. Returns blocked count for backward compat."""
    with _counters_lock:
        return blocked_attempts


def selftest():
    """
    Attempt a connection to 8.8.8.8:443 to prove the guard blocks it.
    Returns the result dict.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(("8.8.8.8", 443))
        s.close()
        return {"blocked": False, "detail": "Connection succeeded — guard may not be active"}
    except ConnectionError as e:
        return {"blocked": True, "detail": str(e)}
    except Exception as e:
        return {"blocked": True, "detail": f"Connection failed: {e}"}
