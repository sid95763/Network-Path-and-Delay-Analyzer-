"""
Network Path and Delay Analyzer - FastAPI Main Application.
Provides streaming SSE traceroute, ping analytics, SQLite history, and file exports.
"""

from __future__ import annotations

import csv
import io
import json
import os
import socket
import uuid
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager

from .database import (
    delete_analysis,
    get_all_analyses,
    get_analysis,
    init_db,
    save_analysis,
)
from .geolocator import GeoLocator
from .models import HopResult, TraceRecord
from .pinger import ping
from .security import RateLimiter, is_blocked_target, validate_target
from .tracer import build_analysis, run_traceroute

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="TracePulse — Network Path and Delay Analyzer",
    description="Live traceroute, hop latency decomposition, jitter, and geographic path visualizer.",
    version="2.0.0",
    lifespan=lifespan,
)

# Global services
geolocator = GeoLocator()
rate_limiter = RateLimiter()


# Mount static assets
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root() -> FileResponse:
    """Serve the single-page frontend application."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index_file):
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Frontend assets not found.")


@app.get("/api/disclaimer")
async def get_disclaimer() -> dict[str, str]:
    """Responsible use and ethics notice."""
    return {
        "disclaimer": (
            "This tool is designed strictly for educational network path analysis, "
            "diagnostic troubleshooting, and computer network research. Unauthorized "
            "automated probing of third-party networks may violate service terms. "
            "Always obtain authorization before testing non-public systems."
        )
    }


@app.get("/api/trace")
async def trace_stream(
    request: Request,
    target: str = Query(..., description="Target domain or IP address"),
    method: str = Query("icmp", pattern="^(icmp|udp|tcp)$"),
    max_hops: int = Query(30, ge=1, le=64),
    timeout: int = Query(5, ge=1, le=30),
) -> StreamingResponse:
    """Stream real-time traceroute hop results and delay analytics via Server-Sent Events."""
    client_ip = request.client.host if request.client else "127.0.0.1"

    # 1. Rate Limiting Check
    if not rate_limiter.check(client_ip, max_requests=15, window_seconds=60):
        async def rate_limit_err():
            yield "event: app_error\ndata: {\"message\": \"Rate limit exceeded (15 requests/min). Please wait before tracing again.\"}\n\n"
        return StreamingResponse(rate_limit_err(), media_type="text/event-stream")

    # 2. Input Validation
    try:
        clean_target = validate_target(target)
    except ValueError as e:
        async def validation_err():
            yield f"event: app_error\ndata: {json.dumps({'message': str(e)})}\n\n"
        return StreamingResponse(validation_err(), media_type="text/event-stream")

    # 3. SSRF & Private Network Blocklist
    if is_blocked_target(clean_target):
        async def blocked_err():
            yield "event: app_error\ndata: {\"message\": \"Target rejected: Localhost and private RFC 1918 addresses are prohibited.\"}\n\n"
        return StreamingResponse(blocked_err(), media_type="text/event-stream")

    # 4. Resolve Target DNS
    resolved_ip = None
    try:
        resolved_ip = socket.gethostbyname(clean_target)
    except Exception:
        pass

    async def event_generator():
        hops: list[HopResult] = []
        record_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        try:
            # Stream hops one-by-one as traceroute progresses
            async for hop in run_traceroute(
                target=clean_target,
                method=method,
                max_hops=max_hops,
                timeout=timeout,
                geolocator=geolocator,
            ):
                hops.append(hop)
                yield f"event: hop\ndata: {json.dumps(hop.model_dump())}\n\n"

            # Compute overall delay analysis
            analysis = build_analysis(hops)
            yield f"event: analysis\ndata: {json.dumps(analysis.model_dump())}\n\n"

            # Perform concurrent ping probe test for end-to-end stats
            ping_stats = await ping(clean_target, count=5)
            yield f"event: ping\ndata: {json.dumps(ping_stats.model_dump())}\n\n"

            # Persist completed analysis to SQLite
            record = TraceRecord(
                id=record_id,
                target=clean_target,
                resolved_ip=resolved_ip,
                method=method,
                timestamp=timestamp,
                total_hops=len(hops),
                end_to_end_rtt=analysis.end_to_end_rtt,
                hops=hops,
                ping=ping_stats,
                analysis=analysis,
            )
            save_analysis(record)

            # Signal completion
            completion_data = {
                "id": record_id,
                "target": clean_target,
                "resolved_ip": resolved_ip,
                "timestamp": timestamp,
                "total_hops": len(hops),
                "end_to_end_rtt": analysis.end_to_end_rtt,
            }
            yield f"event: complete\ndata: {json.dumps(completion_data)}\n\n"

        except Exception as exc:
            yield f"event: app_error\ndata: {json.dumps({'message': f'Traceroute encountered error: {exc}'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/history")
async def list_history() -> list[dict]:
    """Retrieve all stored analysis runs."""
    return get_all_analyses()


@app.get("/api/history/{analysis_id}")
async def fetch_history_item(analysis_id: str) -> dict:
    """Fetch full analysis record with all hop breakdowns."""
    record = get_analysis(analysis_id)
    if not record:
        raise HTTPException(status_code=404, detail="Analysis record not found.")
    return record.model_dump()


@app.delete("/api/history/{analysis_id}")
async def remove_history_item(analysis_id: str) -> dict:
    """Delete an analysis run from SQLite."""
    ok = delete_analysis(analysis_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Analysis record not found.")
    return {"ok": True}


@app.get("/api/export/{analysis_id}")
async def export_analysis(
    analysis_id: str,
    format: str = Query("json", pattern="^(json|csv)$"),
) -> Response:
    """Download analysis results as structured JSON or CSV."""
    record = get_analysis(analysis_id)
    if not record:
        raise HTTPException(status_code=404, detail="Analysis record not found.")

    filename_base = f"trace_{record.target}_{record.id[:8]}"

    if format == "json":
        content = json.dumps(record.model_dump(), indent=2)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.json"},
        )

    # Format CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Hop",
        "IP",
        "Hostname",
        "RTT_1_ms",
        "RTT_2_ms",
        "RTT_3_ms",
        "Min_RTT_ms",
        "Avg_RTT_ms",
        "Max_RTT_ms",
        "Jitter_ms",
        "Loss_Pct",
        "Incremental_Delay_ms",
        "City",
        "Country",
        "ISP",
        "ASN",
    ])

    for h in record.hops:
        geo = h.geo or {}
        r1 = h.rtts[0] if len(h.rtts) > 0 else ""
        r2 = h.rtts[1] if len(h.rtts) > 1 else ""
        r3 = h.rtts[2] if len(h.rtts) > 2 else ""

        writer.writerow([
            h.hop,
            h.ip or "*",
            h.hostname or "*",
            r1 if r1 is not None else "*",
            r2 if r2 is not None else "*",
            r3 if r3 is not None else "*",
            h.min_rtt if h.min_rtt is not None else "*",
            h.avg_rtt if h.avg_rtt is not None else "*",
            h.max_rtt if h.max_rtt is not None else "*",
            h.jitter if h.jitter is not None else "*",
            h.packet_loss,
            h.incremental_delay if h.incremental_delay is not None else "*",
            geo.get("city", ""),
            geo.get("country", ""),
            geo.get("isp", ""),
            geo.get("asn", ""),
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename_base}.csv"},
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

