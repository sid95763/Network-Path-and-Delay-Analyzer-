"""test_pda.py - Unit and integration tests for Network Path and Delay Analyzer.

Run tests with:
    python -m unittest test_pda.py
"""
import unittest
import numpy as np
import networkx as nx

from netmodel import (
    LINKS, BUFFER_K, build_graph, link_name, mm1k, link_state, Background
)
from routing import baseline_path, candidate_paths, path_links, DAPS
from analyzer import analyze_path, format_report
from simulate import run, SCENARIOS, FG_RATE


class TestNetworkModel(unittest.TestCase):
    def setUp(self):
        self.g = build_graph()

    def test_topology_nodes_and_links(self):
        self.assertEqual(len(self.g.nodes), 7)
        self.assertEqual(len(self.g.edges), 8)
        self.assertTrue(self.g.has_node("S"))
        self.assertTrue(self.g.has_node("D"))

    def test_candidate_paths(self):
        paths = candidate_paths(self.g, k=3)
        self.assertEqual(len(paths), 3)
        # Baseline must be P1
        self.assertEqual(paths[0], ["S", "R1", "R2", "D"])
        self.assertEqual(paths[1], ["S", "R3", "R4", "D"])
        self.assertEqual(paths[2], ["S", "R1", "R5", "R4", "D"])
        self.assertEqual(baseline_path(self.g), paths[0])

    def test_mm1k_properties(self):
        mu = 2000.0  # pkts/s
        # 1. Normal load (rho = 0.5)
        w, loss = mm1k(0.5, mu, K=BUFFER_K)
        self.assertGreater(w, 0.0)
        self.assertGreaterEqual(loss, 0.0)
        self.assertLess(loss, 0.01)

        # 2. Singularity avoidance at rho = 1.0
        w_one, loss_one = mm1k(1.0, mu, K=BUFFER_K)
        self.assertFalse(np.isnan(w_one))
        self.assertFalse(np.isinf(w_one))
        self.assertGreater(w_one, 0.0)

        # 3. Overloaded link (rho = 1.5) must stay finite due to finite buffer K
        w_over, loss_over = mm1k(1.5, mu, K=BUFFER_K)
        self.assertFalse(np.isnan(w_over))
        self.assertFalse(np.isinf(w_over))
        self.assertGreater(loss_over, 0.1)  # Loss should be noticeable


class TestAnalyzer(unittest.TestCase):
    def setUp(self):
        self.g = build_graph()
        self.bg = Background(seed=1, load=1.0, T=50)

    def test_delay_decomposition(self):
        path = ["S", "R1", "R2", "D"]
        links = path_links(self.g, path)
        st = link_state(self.bg, t=10, fg_links=links, fg_rate_mbps=FG_RATE)
        rows, worst = analyze_path(self.g, path, st)

        self.assertEqual(len(rows), 3)
        # Check cumulative sum consistency
        self.assertAlmostEqual(rows[-1]["cum"], sum(r["total"] for r in rows), places=5)
        # Each total delay should equal prop + tx + proc (0.1ms included in state['total']) + queue
        for r in rows:
            self.assertGreater(r["prop"], 0)
            self.assertGreater(r["tx"], 0)
            self.assertGreaterEqual(r["queue"], 0)
            self.assertGreaterEqual(r["total"], r["prop"] + r["tx"])

        # Check report formatting
        report = format_report(path, rows, worst)
        self.assertIn("Bottleneck hop:", report)
        self.assertIn("End-to-end mean delay =", report)


class TestDAPSDecisionLogic(unittest.TestCase):
    def setUp(self):
        self.g = build_graph()

    def test_hysteresis_and_holddown(self):
        daps = DAPS(self.g, k=3, hysteresis=0.10, confirm=2)
        # Initial path index is 0 (P1)
        self.assertEqual(daps.cur, 0)

        # Mock initial EWMA scores: P0 = 40.0, P1 = 38.0 (only 5% better, does not beat 10% hysteresis)
        daps.D = np.array([40.0, 38.0, 45.0])
        daps.J = np.array([0.0, 0.0, 0.0])
        daps.L = np.array([0.0, 0.0, 0.0])

        choice = daps.decide()
        self.assertEqual(choice, 0, "Should stay on P0 because 38 > 40 * 0.9 = 36")

        # Now mock P1 = 30.0 (< 36.0, beats hysteresis by > 10%)
        daps.D = np.array([40.0, 30.0, 45.0])
        choice1 = daps.decide()
        # Hold-down requires 2 consecutive confirmations
        self.assertEqual(choice1, 0, "First confirmation: should not switch yet")
        self.assertEqual(daps.pending_target, 1)
        self.assertEqual(daps.pending, 1)

        # Second consecutive confirmation
        choice2 = daps.decide()
        self.assertEqual(choice2, 1, "Second confirmation: should switch to P1")
        self.assertEqual(daps.cur, 1)
        self.assertEqual(daps.switches, 1)


class TestSimulation(unittest.TestCase):
    def test_short_simulation_runs(self):
        # Quick 10-second runs to verify pipeline integrity
        b = run("baseline", "S1", seed=1, T=10)
        p = run("proposed", "S1", seed=1, T=10)

        for res in (b, p):
            self.assertIn("delay", res)
            self.assertIn("p95", res)
            self.assertIn("jitter", res)
            self.assertIn("loss", res)
            self.assertGreater(res["delay"], 0)
            self.assertGreaterEqual(res["loss"], 0)

    def test_all_scenarios_execute(self):
        for sc in ("S1", "S2", "S3", "S4"):
            res_b = run("baseline", sc, seed=1, T=5)
            res_p = run("proposed", sc, seed=1, T=5)
            self.assertGreater(res_b["delay"], 0.0)
            self.assertGreater(res_p["delay"], 0.0)

    def test_analyzer_empty_path(self):
        # Edge case test for empty/trivial path
        rows, worst = analyze_path(build_graph(), ["S"], {})
        self.assertEqual(len(rows), 0)
        self.assertEqual(worst, {})
        rep = format_report(["S"], rows, worst)
        self.assertIn("No hop data available", rep)


if __name__ == "__main__":
    unittest.main()
