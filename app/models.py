"""
Pydantic models for the Network Path and Delay Analyzer.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TraceRequest(BaseModel):
    """Request body for initiating a traceroute."""

    target: str
    method: Literal["icmp", "udp", "tcp"] = "icmp"
    max_hops: int = Field(default=30, ge=1, le=64)
    timeout: int = Field(default=5, ge=1, le=30)


class HopResult(BaseModel):
    """Result for a single hop along the route."""

    hop: int
    ip: str | None = None
    hostname: str | None = None
    rtts: list[float | None] = Field(default_factory=list)
    min_rtt: float | None = None
    avg_rtt: float | None = None
    max_rtt: float | None = None
    jitter: float | None = None
    packet_loss: float = 0.0
    geo: dict | None = None
    incremental_delay: float | None = None


class PingResult(BaseModel):
    """Aggregated ping statistics."""

    min_rtt: float = 0.0
    avg_rtt: float = 0.0
    max_rtt: float = 0.0
    jitter: float = 0.0
    packet_loss: float = 0.0
    probes: int = 0


class AnalysisSummary(BaseModel):
    """Automated analysis of the traceroute results."""

    bottleneck_hop: int | None = None
    bottleneck_delay: float | None = None
    explanation: str = ""
    total_hops: int = 0
    end_to_end_rtt: float | None = None


class TraceRecord(BaseModel):
    """Full record stored for every traceroute run."""

    id: str
    target: str
    resolved_ip: str | None = None
    method: str = "icmp"
    timestamp: str = ""
    total_hops: int = 0
    end_to_end_rtt: float | None = None
    hops: list[HopResult] = Field(default_factory=list)
    ping: PingResult | None = None
    analysis: AnalysisSummary | None = None
