"""
IP geolocation via the free ip-api.com service.
"""

from __future__ import annotations

import asyncio
import json
import urllib.request
from typing import Any

from .security import is_private_ip


class GeoLocator:
    """Async-friendly IP geolocation with an in-memory cache."""

    _API_URL = "http://ip-api.com/json/{ip}?fields=status,message,country,city,isp,as,lat,lon"

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any] | None] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------

    def _fetch_sync(self, ip: str) -> dict[str, Any] | None:
        """Blocking HTTP call to ip-api.com (run in a thread)."""
        try:
            url = self._API_URL.format(ip=ip)
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())

            if data.get("status") == "success":
                return {
                    "city": data.get("city", ""),
                    "country": data.get("country", ""),
                    "isp": data.get("isp", ""),
                    "asn": data.get("as", ""),
                    "lat": data.get("lat"),
                    "lon": data.get("lon"),
                }
        except Exception:
            pass  # Never crash
        return None

    # ------------------------------------------------------------------

    async def locate(self, ip: str) -> dict[str, Any] | None:
        """Return geolocation data for *ip*, or ``None`` on failure.

        Results are cached.  Private / reserved IPs always return ``None``.
        A small sleep is inserted between API calls to respect ip-api.com
        rate limits (~45 req/min for the free tier).
        """
        if is_private_ip(ip):
            return None

        if ip in self._cache:
            return self._cache[ip]

        # Serialise API calls so we don't exceed the rate limit.
        async with self._lock:
            # Double-check after acquiring the lock.
            if ip in self._cache:
                return self._cache[ip]

            result = await asyncio.to_thread(self._fetch_sync, ip)
            self._cache[ip] = result

            # Respect ip-api.com free-tier rate limit.
            await asyncio.sleep(0.1)

        return result
