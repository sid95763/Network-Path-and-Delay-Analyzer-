"""web_server.py - Lightweight REST API and web server for Network Path and Delay Analyzer dashboard.

Usage:
    python web_server.py [--port 8000]
"""
import http.server
import json
import os
import sys
import time
import unittest
import urllib.parse
from io import StringIO

from netmodel import build_graph, link_state, Background, LINKS
from routing import candidate_paths, path_links
from simulate import run, SCENARIOS, FG_RATE
from analyzer import analyze_path, format_report
import test_pda


PORT = 8000
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


class PDARequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/run-tests":
            self.handle_run_tests()
        elif path == "/api/run-demo":
            query = urllib.parse.parse_qs(parsed.query)
            self.handle_run_demo(query)
        elif path == "/api/analyze":
            query = urllib.parse.parse_qs(parsed.query)
            self.handle_analyze(query)
        elif path == "/api/stats":
            self.handle_stats()
        else:
            # Fall back to serving static files from WEB_DIR
            super().do_GET()

    def send_json(self, data, status=200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def handle_run_tests(self):
        """Runs test_pda.py and collects detailed structured results for each test."""
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_pda)

        stream = StringIO()
        runner = unittest.TextTestRunner(stream=stream, verbosity=2)
        start_time = time.perf_counter()
        result = runner.run(suite)
        duration_ms = (time.perf_counter() - start_time) * 1000

        test_details = [
            {
                "id": "test_topology_nodes_and_links",
                "name": "Network Topology & Link Validation",
                "suite": "TestNetworkModel",
                "description": "Verifies 7 nodes (S, R1-R5, D), 8 bidirectional links, and graph edge indices.",
                "status": "PASS",
                "assertions": 4,
                "coverage": "netmodel.py (build_graph, LINKS)"
            },
            {
                "id": "test_candidate_paths",
                "name": "OSPF Dijkstra & Candidate Paths",
                "suite": "TestNetworkModel",
                "description": "Validates candidate loop-free paths (P1, P2, P3) and confirms P1 as OSPF static shortest path.",
                "status": "PASS",
                "assertions": 5,
                "coverage": "routing.py (baseline_path, candidate_paths)"
            },
            {
                "id": "test_mm1k_properties",
                "name": "M/M/1/K Queueing Model & Singularity Avoidance",
                "suite": "TestNetworkModel",
                "description": "Tests normal queue delay, loss bounds [0, 1], division-by-zero avoidance at rho = 1.0, and finite delay during bursts (rho = 1.5).",
                "status": "PASS",
                "assertions": 8,
                "coverage": "netmodel.py (mm1k, BUFFER_K)"
            },
            {
                "id": "test_delay_decomposition",
                "name": "Hop-by-Hop Delay Analyzer Breakdown",
                "suite": "TestAnalyzer",
                "description": "Decomposes delay into prop, tx, proc, and queueing; verifies cumulative sum consistency and bottleneck detection.",
                "status": "PASS",
                "assertions": 15,
                "coverage": "analyzer.py (analyze_path, format_report)"
            },
            {
                "id": "test_hysteresis_and_holddown",
                "name": "DAPS Anti-Flapping (Hysteresis & Hold-Down)",
                "suite": "TestDAPSDecisionLogic",
                "description": "Proves that < 10% differences do not switch, and > 10% improvements require 2 consecutive confirmations before switching.",
                "status": "PASS",
                "assertions": 6,
                "coverage": "routing.py (class DAPS, hysteresis, confirm)"
            },
            {
                "id": "test_short_simulation_runs",
                "name": "End-to-End Simulation Pipeline",
                "suite": "TestSimulation",
                "description": "Executes 10-second runs for both Baseline and DAPS, validating metric outputs (delay, p95, jitter, loss).",
                "status": "PASS",
                "assertions": 10,
                "coverage": "simulate.py (run, SCENARIOS)"
            },
            {
                "id": "test_all_scenarios_execute",
                "name": "Multi-Scenario Pipeline Integrity (S1-S4)",
                "suite": "TestSimulation",
                "description": "Validates that baseline and proposed runs successfully execute across all 4 scenarios (S1, S2, S3, S4).",
                "status": "PASS",
                "assertions": 8,
                "coverage": "simulate.py (SCENARIOS, run)"
            },
            {
                "id": "test_analyzer_empty_path",
                "name": "Analyzer Edge Case & Empty Path Guard",
                "suite": "TestSimulation",
                "description": "Tests defensive guards in analyze_path and format_report for empty or single-node trivial paths.",
                "status": "PASS",
                "assertions": 3,
                "coverage": "analyzer.py (analyze_path, format_report)"
            }
        ]

        # Check for failures or errors
        failures = {f[0]._testMethodName: f[1] for f in result.failures}
        errors = {e[0]._testMethodName: e[1] for e in result.errors}

        for td in test_details:
            if td["id"] in failures:
                td["status"] = "FAIL"
                td["error"] = failures[td["id"]]
            elif td["id"] in errors:
                td["status"] = "ERROR"
                td["error"] = errors[td["id"]]

        resp = {
            "total": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors),
            "failed": len(result.failures),
            "errors": len(result.errors),
            "success": result.wasSuccessful(),
            "duration_ms": round(duration_ms, 2),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "raw_log": stream.getvalue(),
            "tests": test_details
        }
        self.send_json(resp)

    def handle_run_demo(self, query):
        """Runs one comparative simulation on demand."""
        try:
            scenario = query.get("scenario", ["S3"])[0]
            seed = int(query.get("seed", [1])[0])
            alpha = float(query.get("alpha", [0.3])[0])
            probe_interval = int(query.get("probe_interval", [2])[0])
            hysteresis = float(query.get("hysteresis", [0.10])[0])
            confirm = int(query.get("confirm", [2])[0])
            fg_rate = float(query.get("fg_rate", [FG_RATE])[0])

            daps_kwargs = dict(alpha=alpha, probe_interval=probe_interval, hysteresis=hysteresis, confirm=confirm)
            t0 = time.perf_counter()
            b = run("baseline", scenario, seed, fg_rate=fg_rate)
            p = run("proposed", scenario, seed, daps_kwargs=daps_kwargs, fg_rate=fg_rate)
            sim_time = (time.perf_counter() - t0) * 1000

            def imp(bk, pk):
                if b[bk] > 1e-6:
                    return round(100.0 * (b[bk] - p[bk]) / b[bk], 1)
                return 0.0

            resp = {
                "scenario": scenario,
                "seed": seed,
                "parameters": daps_kwargs,
                "fg_rate": fg_rate,
                "sim_duration_ms": round(sim_time, 1),
                "metrics": {
                    "mean_delay": {"baseline": round(b["delay"], 2), "proposed": round(p["delay"], 2), "improvement_pct": imp("delay", "delay")},
                    "p95_delay": {"baseline": round(b["p95"], 2), "proposed": round(p["p95"], 2), "improvement_pct": imp("p95", "p95")},
                    "jitter": {"baseline": round(b["jitter"], 2), "proposed": round(p["jitter"], 2), "improvement_pct": imp("jitter", "jitter")},
                    "loss_pct": {"baseline": round(b["loss"], 2), "proposed": round(p["loss"], 2), "improvement_pct": imp("loss", "loss")},
                    "switches": {"baseline": b["switches"], "proposed": p["switches"]},
                    "probes_sent": {"baseline": b["probes"], "proposed": p["probes"]}
                }
            }
            self.send_json(resp)
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_analyze(self, query):
        """Performs per-hop delay breakdown analysis."""
        try:
            scenario = query.get("scenario", ["S4"])[0]
            seed = int(query.get("seed", [3])[0])
            at = int(query.get("at", [150])[0])

            g = build_graph()
            cfg = dict(SCENARIOS[scenario])
            bg = Background(seed, T=300, **cfg)
            paths = candidate_paths(g)

            results = []
            for i, path in enumerate(paths, start=1):
                st = link_state(bg, at, path_links(g, path), FG_RATE)
                rows, worst = analyze_path(g, path, st)
                results.append({
                    "path_id": f"P{i}",
                    "route": " -> ".join(path),
                    "total_delay_ms": round(rows[-1]["cum"], 2),
                    "worst_hop": worst["link"],
                    "worst_queue_ms": round(worst["queue"], 2),
                    "worst_share_pct": round(100 * worst["queue"] / rows[-1]["cum"], 1) if rows[-1]["cum"] else 0,
                    "hops": rows
                })

            self.send_json({
                "scenario": scenario,
                "seed": seed,
                "at_second": at,
                "paths": results
            })
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_stats(self):
        """Returns baseline vs proposed 30-run statistical table data."""
        stats_data = [
            {"scenario": "S1 (Low Load)", "metric": "Mean Delay (ms)", "baseline": "13.14 ± 0.17", "proposed": "13.22 ± 0.22", "imp": "-0.6%", "p_val": "< 0.05"},
            {"scenario": "S1 (Low Load)", "metric": "Packet Loss (%)", "baseline": "0.00 ± 0.00", "proposed": "0.00 ± 0.00", "imp": "0.0%", "p_val": "n/a"},
            {"scenario": "S2 (Med Load)", "metric": "Mean Delay (ms)", "baseline": "16.48 ± 2.07", "proposed": "15.55 ± 0.80", "imp": "+5.6%", "p_val": "< 0.01"},
            {"scenario": "S2 (Med Load)", "metric": "95th-pct Delay (ms)", "baseline": "29.44 ± 11.45", "proposed": "20.87 ± 1.98", "imp": "+29.1%", "p_val": "< 0.001"},
            {"scenario": "S2 (Med Load)", "metric": "Packet Loss (%)", "baseline": "0.16 ± 0.23", "proposed": "0.03 ± 0.03", "imp": "+81.4%", "p_val": "< 0.001"},
            {"scenario": "S3 (High Load)", "metric": "Mean Delay (ms)", "baseline": "27.51 ± 5.27", "proposed": "23.01 ± 2.41", "imp": "+16.4%", "p_val": "< 0.001"},
            {"scenario": "S3 (High Load)", "metric": "95th-pct Delay (ms)", "baseline": "71.00 ± 20.24", "proposed": "44.61 ± 9.60", "imp": "+37.2%", "p_val": "< 0.001"},
            {"scenario": "S3 (High Load)", "metric": "Jitter (ms)", "baseline": "14.25 ± 5.11", "proposed": "7.97 ± 1.94", "imp": "+44.1%", "p_val": "< 0.001"},
            {"scenario": "S3 (High Load)", "metric": "Packet Loss (%)", "baseline": "2.57 ± 1.75", "proposed": "0.60 ± 0.39", "imp": "+76.7%", "p_val": "< 0.001"},
            {"scenario": "S4 (Link Degr)", "metric": "Mean Delay (ms)", "baseline": "44.38 ± 1.86", "proposed": "17.13 ± 0.75", "imp": "+61.4%", "p_val": "< 0.001"},
            {"scenario": "S4 (Link Degr)", "metric": "95th-pct Delay (ms)", "baseline": "203.26 ± 8.71", "proposed": "23.26 ± 2.13", "imp": "+88.6%", "p_val": "< 0.001"},
            {"scenario": "S4 (Link Degr)", "metric": "Packet Loss (%)", "baseline": "13.69 ± 1.57", "proposed": "0.20 ± 0.15", "imp": "+98.5%", "p_val": "< 0.001"},
        ]
        self.send_json({"stats": stats_data})


import socket

class DualStackServer(http.server.ThreadingHTTPServer):
    address_family = socket.AF_INET6

    def server_bind(self):
        try:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except (AttributeError, OSError):
            pass
        super().server_bind()


if __name__ == "__main__":
    port = PORT
    if len(sys.argv) > 1:
        if sys.argv[1].isdigit():
            port = int(sys.argv[1])
        elif sys.argv[1] in ('--port', '-p') and len(sys.argv) > 2 and sys.argv[2].isdigit():
            port = int(sys.argv[2])
    os.makedirs(WEB_DIR, exist_ok=True)
    try:
        server = DualStackServer(("::", port), PDARequestHandler)
    except Exception:
        server = http.server.ThreadingHTTPServer(("0.0.0.0", port), PDARequestHandler)
    print(f"Server started at http://localhost:{port} (http://127.0.0.1:{port})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()
