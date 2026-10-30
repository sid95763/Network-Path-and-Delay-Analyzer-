"""
Async ping wrapper for the Network Path and Delay Analyzer.
Uses subprocess via asyncio.to_thread for universal Windows and Linux stability.
"""

from __future__ import annotations

import asyncio
import platform
import re
import subprocess

from .models import PingResult


# ---------------------------------------------------------------------------
# Output patterns
# ---------------------------------------------------------------------------
# Windows:
# "Reply from 1.2.3.4: bytes=32 time=12ms TTL=57"
# "Reply from 2404:6800:4007:836::200e: time=53ms"
_WIN_RTT_RE = re.compile(r"time[<=](\d+)\s*ms", re.IGNORECASE)
_WIN_LOSS_RE = re.compile(
    r"Sent\s*=\s*(\d+).*?Received\s*=\s*(\d+).*?Lost\s*=\s*(\d+)",
    re.IGNORECASE,
)

# Linux / macOS:
# "64 bytes from 1.2.3.4: icmp_seq=1 ttl=57 time=12.3 ms"
_LINUX_RTT_RE = re.compile(r"time[<=]([\d.]+)\s*ms", re.IGNORECASE)
_LINUX_LOSS_RE = re.compile(r"(\d+(?:\.\d+)?)%\s*packet loss", re.IGNORECASE)


async def ping(target: str, count: int = 5) -> PingResult:
    """Run a system ping and return aggregated statistics."""
    system = platform.system().lower()

    if system == "windows":
        cmd = ["ping", "-n", str(count), target]
    else:
        cmd = ["ping", "-c", str(count), target]

    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=count * 5 + 10,
        )
        output = proc.stdout
    except Exception:
        return PingResult(
            min_rtt=0.0,
            avg_rtt=0.0,
            max_rtt=0.0,
            jitter=0.0,
            packet_loss=100.0,
            probes=count,
        )

    # -- Extract individual RTTs ------------------------------------------
    rtts: list[float] = []
    rtt_re = _WIN_RTT_RE if system == "windows" else _LINUX_RTT_RE
    for m in rtt_re.finditer(output):
        rtts.append(float(m.group(1)))

    # -- Extract packet loss ----------------------------------------------
    packet_loss = 100.0
    if system == "windows":
        m = _WIN_LOSS_RE.search(output)
        if m:
            sent = int(m.group(1))
            lost = int(m.group(3))
            packet_loss = (lost / sent * 100.0) if sent else 100.0
        elif rtts:
            packet_loss = round(((count - len(rtts)) / count) * 100.0, 1)
    else:
        m = _LINUX_LOSS_RE.search(output)
        if m:
            packet_loss = float(m.group(1))
        elif rtts:
            packet_loss = round(((count - len(rtts)) / count) * 100.0, 1)

    # -- Compute stats ----------------------------------------------------
    if not rtts:
        return PingResult(
            min_rtt=0.0,
            avg_rtt=0.0,
            max_rtt=0.0,
            jitter=0.0,
            packet_loss=packet_loss,
            probes=count,
        )

    min_rtt = min(rtts)
    max_rtt = max(rtts)
    avg_rtt = sum(rtts) / len(rtts)

    # Jitter = mean absolute difference of consecutive RTTs
    jitter = 0.0
    if len(rtts) >= 2:
        diffs = [abs(rtts[i + 1] - rtts[i]) for i in range(len(rtts) - 1)]
        jitter = sum(diffs) / len(diffs)

    return PingResult(
        min_rtt=round(min_rtt, 3),
        avg_rtt=round(avg_rtt, 3),
        max_rtt=round(max_rtt, 3),
        jitter=round(jitter, 3),
        packet_loss=round(packet_loss, 2),
        probes=count,
    )
