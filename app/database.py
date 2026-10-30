"""
SQLite persistence layer for the Network Path and Delay Analyzer.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

from .models import (
    AnalysisSummary,
    HopResult,
    PingResult,
    TraceRecord,
)

_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_DB_PATH = os.path.join(_DB_DIR, "history.db")


def _connect() -> sqlite3.Connection:
    """Return a new connection to the SQLite database."""
    os.makedirs(_DB_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create the ``analyses`` table if it does not already exist."""
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                id            TEXT PRIMARY KEY,
                target        TEXT,
                resolved_ip   TEXT,
                method        TEXT,
                timestamp     TEXT,
                total_hops    INTEGER,
                end_to_end_rtt REAL,
                hops_json     TEXT,
                ping_json     TEXT,
                analysis_json TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def save_analysis(record: TraceRecord) -> None:
    """Persist a :class:`TraceRecord` to the database."""
    hops_json = json.dumps(
        [hop.model_dump() for hop in record.hops]
    )
    ping_json = json.dumps(record.ping.model_dump()) if record.ping else None
    analysis_json = (
        json.dumps(record.analysis.model_dump()) if record.analysis else None
    )

    conn = _connect()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO analyses
                (id, target, resolved_ip, method, timestamp,
                 total_hops, end_to_end_rtt, hops_json, ping_json, analysis_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.target,
                record.resolved_ip,
                record.method,
                record.timestamp,
                record.total_hops,
                record.end_to_end_rtt,
                hops_json,
                ping_json,
                analysis_json,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_all_analyses() -> list[dict[str, Any]]:
    """Return summary rows (no full hop data) for every stored analysis."""
    conn = _connect()
    try:
        cursor = conn.execute(
            """
            SELECT id, target, resolved_ip, method, timestamp,
                   total_hops, end_to_end_rtt
            FROM analyses
            ORDER BY timestamp DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_analysis(analysis_id: str) -> TraceRecord | None:
    """Return the full :class:`TraceRecord` for *analysis_id*, or ``None``."""
    conn = _connect()
    try:
        cursor = conn.execute(
            "SELECT * FROM analyses WHERE id = ?", (analysis_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None

        row = dict(row)

        hops = [
            HopResult(**h) for h in json.loads(row["hops_json"] or "[]")
        ]
        ping = (
            PingResult(**json.loads(row["ping_json"]))
            if row["ping_json"]
            else None
        )
        analysis = (
            AnalysisSummary(**json.loads(row["analysis_json"]))
            if row["analysis_json"]
            else None
        )

        return TraceRecord(
            id=row["id"],
            target=row["target"],
            resolved_ip=row["resolved_ip"],
            method=row["method"],
            timestamp=row["timestamp"],
            total_hops=row["total_hops"],
            end_to_end_rtt=row["end_to_end_rtt"],
            hops=hops,
            ping=ping,
            analysis=analysis,
        )
    finally:
        conn.close()


def delete_analysis(analysis_id: str) -> bool:
    """Delete the analysis with *analysis_id*. Return ``True`` on success."""
    conn = _connect()
    try:
        cursor = conn.execute(
            "DELETE FROM analyses WHERE id = ?", (analysis_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
