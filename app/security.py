"""
Input validation and rate limiting for the Network Path and Delay Analyzer.
"""

from __future__ import annotations

import ipaddress
import re
import time


# ---------------------------------------------------------------------------
# Target validation
# ---------------------------------------------------------------------------

_DANGEROUS_CHARS = re.compile(r'[;|&$`\\\n\r]')
_DOMAIN_RE = re.compile(
    r'^(?!-)'                       # cannot start with hyphen
    r'[A-Za-z0-9-]{1,63}'          # label
    r'(\.[A-Za-z0-9-]{1,63})*'     # more labels
    r'$'
)
_IPV4_RE = re.compile(
    r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
)


def _is_valid_ipv6(addr: str) -> bool:
    """Return True if *addr* is a syntactically valid IPv6 address."""
    try:
        ipaddress.IPv6Address(addr)
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def _is_valid_ipv4(addr: str) -> bool:
    """Return True if *addr* is a syntactically valid IPv4 address."""
    m = _IPV4_RE.match(addr)
    if not m:
        return False
    return all(0 <= int(g) <= 255 for g in m.groups())


def validate_target(target: str) -> str:
    """Validate and sanitise a user-supplied hostname or IP address.

    Returns the cleaned target string.  Raises ``ValueError`` if the
    target is invalid or contains dangerous characters.
    """
    if not target or not target.strip():
        raise ValueError("Target must not be empty.")

    target = target.strip()

    if len(target) > 255:
        raise ValueError("Target exceeds maximum length of 255 characters.")

    if _DANGEROUS_CHARS.search(target):
        raise ValueError(
            "Target contains disallowed characters (shell meta-characters)."
        )

    # Accept valid IPv4
    if _is_valid_ipv4(target):
        return target

    # Accept valid IPv6 (may be wrapped in brackets)
    bare = target.strip("[]")
    if _is_valid_ipv6(bare):
        return bare

    # Accept valid domain names
    if _DOMAIN_RE.match(target):
        return target

    raise ValueError(f"Invalid target: {target!r}")


# ---------------------------------------------------------------------------
# Private / reserved IP detection
# ---------------------------------------------------------------------------

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def is_private_ip(ip: str) -> bool:
    """Return True if *ip* falls within a private or reserved range."""
    try:
        addr = ipaddress.ip_address(ip.strip().strip("[]"))
    except ValueError:
        return False
    return any(addr in net for net in _PRIVATE_NETWORKS)


# ---------------------------------------------------------------------------
# Blocked-target check
# ---------------------------------------------------------------------------

_LOCALHOST_NAMES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
}


def is_blocked_target(target: str) -> bool:
    """Return True if the target should be blocked (private IPs, localhost)."""
    lower = target.strip().lower()

    if lower in _LOCALHOST_NAMES:
        return True

    # If it looks like an IP, check private ranges
    try:
        ipaddress.ip_address(lower.strip("[]"))
        return is_private_ip(lower)
    except ValueError:
        pass  # It is a domain; allow it — resolution happens later.

    return False


# ---------------------------------------------------------------------------
# Simple in-memory rate limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Token-bucket-style rate limiter keyed by client IP."""

    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = {}

    def check(
        self,
        client_ip: str,
        max_requests: int = 10,
        window_seconds: int = 60,
    ) -> bool:
        """Return ``True`` if the request should be **allowed**."""
        now = time.time()
        cutoff = now - window_seconds

        timestamps = self._requests.get(client_ip, [])
        # Purge stale entries
        timestamps = [t for t in timestamps if t > cutoff]

        if len(timestamps) >= max_requests:
            self._requests[client_ip] = timestamps
            return False

        timestamps.append(now)
        self._requests[client_ip] = timestamps
        return True
