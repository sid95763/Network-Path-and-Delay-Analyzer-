"""routing.py - baseline (static OSPF-style) and proposed (DAPS) path selection."""
from itertools import islice
import numpy as np
import networkx as nx
from netmodel import sample_path, PROBE_BITS


def path_links(g, path):
    return [g[a][b]["idx"] for a, b in zip(path[:-1], path[1:])]


def baseline_path(g, src="S", dst="D"):
    """Static shortest path using cost = reference bandwidth / link bandwidth."""
    return nx.dijkstra_path(g, src, dst, weight="cost")


def candidate_paths(g, k=3, src="S", dst="D"):
    """The k loop-free paths with the lowest static cost."""
    return list(islice(nx.shortest_simple_paths(g, src, dst, weight="cost"), k))


class DAPS:
    """Delay-Aware Adaptive Path Selection (proposed mechanism).

    Every probe_interval seconds it sends n_probes small probes on each
    candidate path, smooths delay / jitter / loss with an EWMA, builds one score
    per path, and moves traffic only if another path is clearly and
    persistently better (hysteresis + hold-down).
    """

    def __init__(self, g, k=3, alpha=0.3, probe_interval=2, n_probes=4,
                 w_jitter=1.0, w_loss=1000.0, hysteresis=0.10, confirm=2,
                 use_jitter_loss=True):
        self.paths = candidate_paths(g, k)
        self.links = [path_links(g, p) for p in self.paths]
        self.alpha, self.interval, self.n_probes = alpha, probe_interval, n_probes
        self.w_j, self.w_l = w_jitter, w_loss
        self.h, self.confirm = hysteresis, confirm
        self.use_jl = use_jitter_loss
        self.cur = 0                       # start on the static best path
        self.D = self.J = self.L = None
        self.pending_target, self.pending = None, 0
        self.switches = 0
        self.probe_packets = 0

    def score(self):
        s = self.D.copy()
        if self.use_jl:
            s += self.w_j * self.J + self.w_l * self.L
        return s

    def probe(self, state, rng):
        n = len(self.paths)
        d, j, l = np.zeros(n), np.zeros(n), np.zeros(n)
        for i, lk in enumerate(self.links):
            x = sample_path(state, lk, self.n_probes, rng, bits=PROBE_BITS)
            ok = x[~np.isnan(x)]
            l[i] = 1.0 - len(ok) / self.n_probes
            d[i] = ok.mean() if len(ok) else 400.0   # all lost: large delay
            j[i] = np.abs(np.diff(ok)).mean() if len(ok) > 1 else 0.0
        self.probe_packets += self.n_probes * len(self.paths)
        if self.D is None:
            self.D, self.J, self.L = d, j, l
        else:
            a = self.alpha
            self.D = a * d + (1 - a) * self.D
            self.J = a * j + (1 - a) * self.J
            self.L = a * l + (1 - a) * self.L

    def decide(self):
        s = self.score()
        best = int(np.argmin(s))
        if best != self.cur and s[best] < (1 - self.h) * s[self.cur]:
            if self.pending_target == best:
                self.pending += 1
            else:
                self.pending_target, self.pending = best, 1
            if self.pending >= self.confirm:
                self.cur = best
                self.switches += 1
                self.pending_target, self.pending = None, 0
        else:
            self.pending_target, self.pending = None, 0
        return self.cur
