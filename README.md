# ⚡ TracePulse — Next-Gen Network Path & Latency Telemetry

<div align="center">

![TracePulse Banner](https://img.shields.io/badge/TracePulse-v2.0-06b6d4?style=for-the-badge&logo=fastapi&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Leaflet](https://img.shields.io/badge/Leaflet-1.9.4-199900?style=for-the-badge&logo=leaflet&logoColor=white)
![Chart.js](https://img.shields.io/badge/Chart.js-4.0+-FF6384?style=for-the-badge&logo=chartdotjs&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

**Live hop-by-hop traceroute telemetry, RTT latency decomposition, geographic path mapping, intelligent bottleneck diagnostics, and persistent SQLite history.**

[Features](#-key-features) • [Architecture](#-architecture) • [Quick Start](#-quick-start) • [API Reference](#-api-reference) • [Networking Concepts](#-computer-networking-concepts-demonstrated) • [Deployment](#-docker--deployment)

</div>

---

## 🌟 Overview

When you type a domain like `google.com` or `cloudflare.com`, your packets traverse 8 to 20 intermediate routers and subsea fiber cables around the world. 

**TracePulse** is a modern, cyber-sleek network diagnostic platform that reveals this hidden path in real time. It streams live traceroute hops into your browser via **Server-Sent Events (SSE)**, calculates microsecond-level latency and jitter, geolocates intermediate routers on an interactive world map, and diagnoses bottlenecks with plain-language explanations.

---

## 🚀 Key Features

- 🛰️ **Real-Time Traceroute Engine**: Discovers live hops via ICMP, UDP, or TCP probing with configurable max hops and timeout controls.
- ⏱️ **Delay Decomposition & Jitter**: Computes per-hop min, avg, max RTT, incremental latency jump, jitter variation, and packet loss percentage.
- ⚡ **Intelligent Bottleneck Detection**: Automatically pinpoints the router with the largest latency spike and provides automated diagnostic explanations.
- 🗺️ **Interactive Geographic Map**: Plots physical transit paths across continents using Leaflet.js and OpenStreetMap with glowing pulse markers and route vectors.
- 📊 **Dynamic RTT Charting**: Interactive Chart.js bar charts color-coded by performance (🟢 `<30ms`, 🟡 `30-100ms`, 🔴 `>100ms`).
- 📡 **Concurrent Ping Probes**: Performs parallel end-to-end ping telemetry for overall link reliability and packet drop auditing.
- 💾 **Persistent SQLite History**: Full session storage in `data/history.db` with one-click reload, side-by-side inspection, and record deletion.
- 📥 **One-Click Data Export**: Download complete hop telemetry as structured **CSV** (for Excel/Pandas) or **JSON**.
- 🛡️ **Defensive Security Guardrails**: Built-in rate limiting (15 req/min), command injection sanitization, and RFC 1918 private IP SSRF blocklists.
- 🎨 **Cyber-Sleek Glassmorphic UI**: Ultra-clean dashboard layout with side-by-side visualizers that never jump or push components off-screen.

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Browser                         │
│  (Cyber-Sleek UI • Chart.js • Leaflet.js • EventSource SSE) │
└──────────────────────────────┬──────────────────────────────┘
                               │
               SSE Stream (Hops, RTT, Diagnostics)
               REST API (History, Exports, Config)
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend Server                   │
│                                                             │
│   ├── app/main.py        (FastAPI App, SSE & Endpoints)    │
│   ├── app/tracer.py      (Thread-safe Traceroute Engine)    │
│   ├── app/pinger.py      (Subprocess Ping Probing)          │
│   ├── app/geolocator.py  (ip-api.com Geolocation Cache)     │
│   ├── app/database.py    (SQLite CRUD Persistence)          │
│   ├── app/security.py    (Rate Limiting & SSRF Filter)      │
│   └── app/models.py      (Pydantic Schemas & Types)         │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
     Subprocess Calls                  SQLite Database
     (tracert / traceroute / ping)     (data/history.db)
```

---

## ⚡ Quick Start

### Prerequisites
- **Python 3.10+** (Python 3.11 or 3.13 recommended)
- `ping` (built-in on Windows/Linux/macOS)
- `tracert` (Windows built-in) or `traceroute` (`sudo apt install traceroute` on Linux)

### 1. Clone & Install
```bash
git clone https://github.com/sid95763/Network-Path-and-Delay-Analyzer-.git
cd Network-Path-and-Delay-Analyzer-

# Install lightweight dependencies
pip install -r requirements.txt
```

### 2. Launch TracePulse

**Windows (One-Click):**
Double-click [`run.bat`](run.bat)

**Or via Terminal (All Platforms):**
```bash
python -m app.main
```

Open your browser to: **`http://localhost:8000`**

---

## 📡 API Reference

### 1. Start Live Traceroute (SSE Stream)
```http
GET /api/trace?target=google.com&method=icmp&max_hops=30&timeout=2
```
*Streams `text/event-stream` events: `hop`, `analysis`, `ping`, `complete`, `app_error`.*

**Example `hop` Event Payload:**
```json
{
  "hop": 3,
  "ip": "142.250.185.174",
  "hostname": "del12s17-in-f14.1e100.net",
  "rtts": [12.3, 11.8, 12.1],
  "min_rtt": 11.8,
  "avg_rtt": 12.07,
  "max_rtt": 12.3,
  "jitter": 0.35,
  "packet_loss": 0.0,
  "incremental_delay": 4.2,
  "geo": {
    "city": "Mumbai",
    "country": "India",
    "isp": "Google LLC",
    "asn": "AS15169",
    "lat": 19.0748,
    "lon": 72.8856
  }
}
```

### 2. History & Telemetry Storage
- `GET /api/history` — Lists all past recorded analyses.
- `GET /api/history/{id}` — Retrieves full hop breakdown for a specific analysis.
- `DELETE /api/history/{id}` — Removes an analysis record from the SQLite database.

### 3. File Exports
- `GET /api/export/{id}?format=csv` — Generates a downloadable tabular CSV.
- `GET /api/export/{id}?format=json` — Generates formatted JSON data for programmatic analysis.

---

## 🎓 Computer Networking Concepts Demonstrated

| Networking Concept | Where & How It Is Implemented |
|---|---|
| **TTL & ICMP Time Exceeded** | Core traceroute mechanism — packets with incrementing TTL trigger ICMP Type 11 replies from each router. |
| **Routing Hops** | Individual rows in the telemetry table representing IP packet forwarding nodes. |
| **Round-Trip Time (RTT)** | 3 probe samples per hop with minimum, average, and maximum calculation. |
| **Delay Decomposition** | Incremental delay analysis distinguishing distance propagation from router buffer queueing. |
| **Jitter Calculation** | Computed as the mean absolute variation across consecutive probe latencies ($\Delta\text{RTT}$). |
| **Packet Loss & Rate Limiting** | Identified as asterisks (`* * *`) denoting router ICMP deprioritization or link drops. |
| **DNS Resolution** | Forward resolution of domains and asynchronous reverse-DNS (`PTR`) for hostnames. |
| **Autonomous Systems (ASN)** | BGP routing boundaries and carrier ownership identified per hop (e.g. Google AS15169). |

---

## 🐳 Docker & Deployment

### Run with Docker (with Raw Sockets)
```bash
docker build -t tracepulse .
docker run --cap-add=NET_RAW -p 8000:8000 tracepulse
```
> **Note**: The `--cap-add=NET_RAW` flag grants permission for ICMP socket probing inside the container.

---

## 🛡️ Security & Ethical Guardrails

- **Command Injection Prevention**: Strict regex validation rejecting dangerous shell characters (`;`, `|`, `&`, `` ` ``, `$`).
- **SSRF Blocklist**: Prohibits tracing private RFC 1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.1`, loopback).
- **Rate Limiting**: Built-in in-memory rate limiter restricting requests to 15 per minute per client IP.
- **Responsible Use Notice**: Strictly intended for educational and authorized network diagnostics.

---

## 📄 License

Distributed under the **MIT License**. Free for academic, educational, and developer use.
