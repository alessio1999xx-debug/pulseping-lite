#!/usr/bin/env python3
"""pulseping-lite: check one URL or host:port and its TLS certificate expiry.

Free, MIT-licensed, reduced version of PulsePing CLI (https://py-forge.com).
Standard library only. Python 3.9+.

Exit codes: 0 = up (and certificate not close to expiry), 1 = down or certificate
expired / expiring within --warn-days, 2 = bad arguments.
"""

from __future__ import annotations

import argparse
import http.client
import json
import socket
import ssl
import sys
import time
import urllib.parse
from typing import Any, Dict, Optional, Tuple

VERSION = "0.1.0"
USER_AGENT = f"pulseping-lite/{VERSION}"


def parse_target(target: str) -> Tuple[str, str, int, str]:
    """Return (kind, host, port, path). kind is 'http', 'https' or 'tcp'."""
    target = target.strip()
    if "://" in target:
        parts = urllib.parse.urlsplit(target)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError(f"unsupported target {target!r}: use http(s)://host or host:port")
        port = parts.port or (443 if parts.scheme == "https" else 80)
        path = parts.path or "/"
        if parts.query:
            path += "?" + parts.query
        return parts.scheme, parts.hostname, port, path
    if target.startswith("["):  # [ipv6]:port
        host, _, rest = target[1:].partition("]")
        port_s = rest.lstrip(":")
    elif target.count(":") == 1:
        host, port_s = target.split(":")
    else:
        host, port_s = target, ""
    if not host or not port_s:
        raise ValueError(f"target {target!r} must be a URL or host:port")
    return "tcp", host, int(port_s), "/"


def days_left(cert: Dict[str, Any]) -> Optional[int]:
    not_after = cert.get("notAfter") if cert else None
    if not not_after:
        return None
    return int((ssl.cert_time_to_seconds(not_after) - time.time()) // 86400)


def tls_days(host: str, port: int, timeout: float, verify: bool) -> Tuple[Optional[int], str]:
    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as tls:
            cert = tls.getpeercert()
    issuer = ", ".join(v for rdn in cert.get("issuer", ()) for k, v in rdn if k in ("organizationName", "commonName"))
    return days_left(cert), issuer


def check(target: str, timeout: float = 5.0, warn_days: int = 14, verify: bool = True,
          tls: bool = False) -> Dict[str, Any]:
    """Run one check and return a result dict."""
    started = time.perf_counter()
    res: Dict[str, Any] = {"target": target, "up": False, "status_code": None,
                           "tls_days_left": None, "issuer": None, "latency_ms": None, "error": None}
    try:
        kind, host, port, path = parse_target(target)
        if kind in ("http", "https"):
            if kind == "https":
                conn: http.client.HTTPConnection = http.client.HTTPSConnection(
                    host, port, timeout=timeout,
                    context=ssl._create_unverified_context() if not verify else ssl.create_default_context())
            else:
                conn = http.client.HTTPConnection(host, port, timeout=timeout)
            try:
                conn.request("GET", path, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
                if kind == "https" and conn.sock is not None:
                    res["tls_days_left"] = days_left(conn.sock.getpeercert())
                resp = conn.getresponse()
                resp.read(1024)
                res["status_code"] = resp.status
            finally:
                conn.close()
            res["up"] = resp.status < 400
            if not res["up"]:
                res["error"] = f"HTTP status {resp.status}"
        else:
            with socket.create_connection((host, port), timeout=timeout):
                pass
            res["up"] = True
            if tls:
                res["tls_days_left"], res["issuer"] = tls_days(host, port, timeout, verify)
        res["latency_ms"] = round((time.perf_counter() - started) * 1000.0, 1)
        days = res["tls_days_left"]
        if days is not None and days < warn_days:
            res["up"] = False
            res["error"] = "certificate expired" if days < 0 else f"certificate expires in {days} days (warn at {warn_days})"
    except Exception as exc:  # network errors, TLS errors, timeouts
        res["latency_ms"] = round((time.perf_counter() - started) * 1000.0, 1)
        res["error"] = f"{type(exc).__name__}: {exc}"
    return res


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pulseping_lite.py",
        description="Check one URL or host:port, and report days until its TLS certificate expires.")
    p.add_argument("target", help="https://example.com/health, http://host:8080, or host:port")
    p.add_argument("--warn-days", type=int, default=14, help="fail when the certificate expires sooner (default 14)")
    p.add_argument("--timeout", type=float, default=5.0, help="seconds (default 5)")
    p.add_argument("--tls", action="store_true", help="for a host:port target, also read the TLS certificate (e.g. host:443)")
    p.add_argument("--insecure", action="store_true", help="do not verify the certificate chain")
    p.add_argument("--json", action="store_true", help="print the result as JSON")
    p.add_argument("--version", action="version", version=f"pulseping-lite {VERSION}")
    return p


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        parse_target(args.target)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    res = check(args.target, args.timeout, args.warn_days, not args.insecure, args.tls)
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        state = "UP  " if res["up"] else "DOWN"
        line = f"{state} {res['target']}"
        if res["status_code"] is not None:
            line += f"  status={res['status_code']}"
        if res["latency_ms"] is not None:
            line += f"  {res['latency_ms']} ms"
        if res["tls_days_left"] is not None:
            line += f"  cert expires in {res['tls_days_left']} days"
        print(line)
        if res["error"]:
            print(f"  {res['error']}")
    return 0 if res["up"] else 1


if __name__ == "__main__":
    sys.exit(main())
