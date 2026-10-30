"""
Traceroute execution engine and output parser for Linux and Windows.
Supports real streaming hop results via async generators using robust thread-safe subprocess execution.
"""

from __future__ import annotations

import asyncio
import platform
import re
import socket
import subprocess
from typing import AsyncGenerator

from .geolocator import GeoLocator
from .models import AnalysisSummary, HopResult


# ---------------------------------------------------------------------------
# Output parsing regexes
# ---------------------------------------------------------------------------

_WIN_HOP_RE = re.compile(
    r"^\s*(\d+)\s+"                       # Hop number
    r"(<1\s*ms|\d+\s*ms|\*)\s+"           # RTT 1
    r"(<1\s*ms|\d+\s*ms|\*)\s+"           # RTT 2
    r"(<1\s*ms|\d+\s*ms|\*)\s+"           # RTT 3
    r"(\S.*)$",                            # IP or "Request timed out."
    re.IGNORECASE,
)

_LINUX_HOP_RE = re.compile(r"^\s*(\d+)\s+(.+)$")
_MS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*ms", re.IGNORECASE)
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b|[0-9a-fA-F:]{3,39}")


def _parse_win_rtt(token: str) -> float | None:
    token = token.strip()
    if token == "*":
        return None
    if "<1" in token:
        return 0.8
    m = re.search(r"(\d+)", token)
    return float(m.group(1)) if m else None


def _parse_win_line(line: str) -> tuple[int, list[float | None], str | None] | None:
    m = _WIN_HOP_RE.match(line)
    if not m:
        return None
    hop_num = int(m.group(1))
    rtts = [_parse_win_rtt(m.group(i)) for i in (2, 3, 4)]
    target_part = m.group(5).strip()

    ip = None
    if "request timed out" not in target_part.lower():
        ip_match = _IP_RE.search(target_part)
        if ip_match:
            ip = ip_match.group(0).strip("[]()")

    return hop_num, rtts, ip


def _parse_linux_line(line: str) -> tuple[int, list[float | None], str | None] | None:
    m = _LINUX_HOP_RE.match(line)
    if not m:
        return None
    hop_num = int(m.group(1))
    rest = m.group(2).strip()

    ip = None
    ip_match = _IP_RE.search(rest)
    if ip_match:
        ip = ip_match.group(0).strip("[]()")

    ms_matches = _MS_RE.findall(rest)
    rtts: list[float | None] = []
    for val in ms_matches[:3]:
        rtts.append(float(val))

    while len(rtts) < 3:
        rtts.append(None)

    return hop_num, rtts, ip


async def _reverse_dns(ip: str) -> str:
    """Resolve reverse DNS hostname asynchronously."""
    try:
        host, _, _ = await asyncio.to_thread(socket.gethostbyaddr, ip)
        return host
    except Exception:
        return ip


# ---------------------------------------------------------------------------
# Traceroute execution generator
# ---------------------------------------------------------------------------

async def run_traceroute(
    target: str,
    method: str = "icmp",
    max_hops: int = 30,
    timeout: int = 2,
    geolocator: GeoLocator | None = None,
) -> AsyncGenerator[HopResult, None]:
    """Execute traceroute and yield HopResult objects as each hop completes."""
    system = platform.system().lower()

    if system == "windows":
        # -d: no reverse DNS during probe (much faster)
        # -h: maximum hops
        # -w: timeout in ms (cap at 1500ms to keep hops snappy)
        timeout_ms = min(int(timeout * 1000), 2000)
        cmd = ["tracert", "-d", "-h", str(max_hops), "-w", str(timeout_ms), target]
    else:
        # Linux / Unix
        cmd = ["traceroute", "-n", "-m", str(max_hops), "-w", str(timeout)]
        if method == "icmp":
            cmd.append("-I")
        elif method == "tcp":
            cmd.append("-T")
        cmd.append(target)

    try:
        # Using subprocess.Popen via to_thread ensures seamless compatibility on Windows
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except Exception as exc:
        yield HopResult(
            hop=1,
            ip=None,
            hostname=f"Traceroute execution failed: {exc}",
            rtts=[None, None, None],
            packet_loss=100.0,
        )
        return

    prev_avg_rtt: float | None = None

    try:
        while True:
            line = await asyncio.to_thread(proc.stdout.readline)
            if not line:
                break

            line_str = line.strip()
            if not line_str:
                continue

            parsed = _parse_win_line(line_str) if system == "windows" else _parse_linux_line(line_str)
            if not parsed:
                continue

            hop_num, rtts, ip = parsed

            valid_rtts = [r for r in rtts if r is not None]
            loss_pct = ((3 - len(valid_rtts)) / 3.0) * 100.0

            min_rtt = min(valid_rtts) if valid_rtts else None
            max_rtt = max(valid_rtts) if valid_rtts else None
            avg_rtt = (sum(valid_rtts) / len(valid_rtts)) if valid_rtts else None

            jitter: float | None = None
            if len(valid_rtts) >= 2:
                diffs = [abs(valid_rtts[i + 1] - valid_rtts[i]) for i in range(len(valid_rtts) - 1)]
                jitter = round(sum(diffs) / len(diffs), 3)

            incremental_delay: float | None = None
            if avg_rtt is not None:
                if prev_avg_rtt is not None:
                    incremental_delay = round(max(0.0, avg_rtt - prev_avg_rtt), 3)
                else:
                    incremental_delay = round(avg_rtt, 3)
                prev_avg_rtt = avg_rtt

            # Reverse DNS lookup
            hostname = None
            if ip:
                hostname = await _reverse_dns(ip)

            # Geolocation lookup
            geo = None
            if ip and geolocator:
                geo = await geolocator.locate(ip)

            result = HopResult(
                hop=hop_num,
                ip=ip,
                hostname=hostname,
                rtts=[round(r, 3) if r is not None else None for r in rtts],
                min_rtt=round(min_rtt, 3) if min_rtt is not None else None,
                avg_rtt=round(avg_rtt, 3) if avg_rtt is not None else None,
                max_rtt=round(max_rtt, 3) if max_rtt is not None else None,
                jitter=jitter,
                packet_loss=round(loss_pct, 1),
                geo=geo,
                incremental_delay=incremental_delay,
            )

            yield result

    finally:
        try:
            proc.kill()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Delay & bottleneck analysis
# ---------------------------------------------------------------------------

def build_analysis(hops: list[HopResult]) -> AnalysisSummary:
    """Generate high-level delay analysis and plain-language explanation."""
    if not hops:
        return AnalysisSummary(explanation="No hops recorded.")

    total_hops = len(hops)
    valid_hops = [h for h in hops if h.avg_rtt is not None]
    timeout_hops = [h for h in hops if h.ip is None or h.packet_loss == 100.0]

    end_to_end_rtt = valid_hops[-1].avg_rtt if valid_hops else None

    bottleneck_hop: int | None = None
    bottleneck_delay: float | None = None
    bottleneck_obj: HopResult | None = None

    max_inc = -1.0
    for h in hops:
        if h.incremental_delay is not None and h.incremental_delay > max_inc and h.hop > 1:
            max_inc = h.incremental_delay
            bottleneck_hop = h.hop
            bottleneck_delay = h.incremental_delay
            bottleneck_obj = h

    notes: list[str] = []
    if end_to_end_rtt is not None:
        notes.append(f"Trace completed across {total_hops} hops with an end-to-end average latency of {end_to_end_rtt:.1f} ms.")
    else:
        notes.append(f"Trace reached {total_hops} hops without full destination response.")

    if bottleneck_hop and bottleneck_delay and bottleneck_delay > 10.0:
        hop_desc = f"Hop {bottleneck_hop}"
        if bottleneck_obj and bottleneck_obj.ip:
            hop_desc += f" ({bottleneck_obj.ip}"
            if bottleneck_obj.geo and bottleneck_obj.geo.get("city"):
                hop_desc += f" in {bottleneck_obj.geo['city']}, {bottleneck_obj.geo.get('country')}"
            hop_desc += ")"

        notes.append(
            f"{hop_desc} introduced the largest delay spike (+{bottleneck_delay:.1f} ms), "
            "indicating a significant distance jump, inter-AS transit peering link, or router buffer queue."
        )

    if timeout_hops:
        timeout_pct = round((len(timeout_hops) / total_hops) * 100.0)
        notes.append(
            f"{len(timeout_hops)} hop(s) ({timeout_pct}%) timed out (* * *), "
            "which typically reflects ICMP rate-limiting or firewall drop policies at intermediate routers."
        )

    high_jitter_hops = [h for h in hops if h.jitter is not None and h.jitter > 15.0]
    if high_jitter_hops:
        hops_str = ", ".join(f"Hop {h.hop}" for h in high_jitter_hops[:3])
        notes.append(f"Elevated jitter (>15 ms) detected on {hops_str}, signifying variable link queueing.")

    return AnalysisSummary(
        bottleneck_hop=bottleneck_hop,
        bottleneck_delay=bottleneck_delay,
        explanation=" ".join(notes),
        total_hops=total_hops,
        end_to_end_rtt=end_to_end_rtt,
    )
