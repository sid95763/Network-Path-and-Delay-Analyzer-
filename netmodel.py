"""netmodel.py - topology, link delay model and background traffic generator.

Each link is modelled as an M/M/1/K queue (Poisson arrivals, exponential
service, K-packet buffer). From the offered load we get the mean delay and the
loss probability of the link. Delay of a hop = propagation + transmission +
processing + queueing.
"""
import math
import numpy as np
import networkx as nx

PKT_BITS = 8000          # data packet = 1000 bytes
PROBE_BITS = 512         # probe packet = 64 bytes
BUFFER_K = 64            # buffer size in packets (M/M/1/K)
PROC_MS = 0.1            # fixed router processing delay per hop (ms)
REF_BW = 100.0           # reference bandwidth for OSPF-style cost (Mbps)

# (node a, node b, bandwidth Mbps, propagation ms, mean background utilisation at load factor 1.0)
LINKS = [
    ("S",  "R1", 20, 2.0, 0.30),
    ("S",  "R3", 20, 2.0, 0.30),
    ("R1", "R2", 10, 6.0, 0.45),
    ("R2", "D",  20, 2.0, 0.30),
    ("R3", "R4",  8, 8.0, 0.40),
    ("R4", "D",  20, 2.0, 0.30),
    ("R1", "R5", 10, 5.0, 0.35),
    ("R5", "R4", 10, 5.0, 0.35),
]


def build_graph():
    """Return the network graph; edge attribute 'idx' is the link index."""
    g = nx.Graph()
    for i, (a, b, bw, prop, util) in enumerate(LINKS):
        g.add_edge(a, b, idx=i, bw=bw, prop=prop, base_util=util, cost=REF_BW / bw)
    return g


def link_name(i):
    return f"{LINKS[i][0]}-{LINKS[i][1]}"


def mm1k(rho, mu, K=BUFFER_K):
    """Mean sojourn time (s) and loss probability of an M/M/1/K queue.

    rho = offered load, mu = service rate (packets/s). Works for rho > 1 too.
    The point rho = 1 is a removable singularity, so it is nudged away.
    """
    rho = np.clip(np.asarray(rho, dtype=float), 1e-6, 3.0)
    rho = np.where(np.abs(rho - 1.0) < 1e-6, 1.0 + 1e-6, rho)
    rk1 = rho ** (K + 1)
    p_loss = (1 - rho) * rho ** K / (1 - rk1)
    n_avg = rho / (1 - rho) - (K + 1) * rk1 / (1 - rk1)
    lam_eff = rho * mu * (1 - p_loss)
    return n_avg / lam_eff, p_loss


class Background:
    """Random background utilisation of every link for one run.

    u(t) = base * load * jitter + slow sine wave + on/off bursts.
    Optionally one link loses capacity during a window (degradation event).
    """

    def __init__(self, seed, load, T=300, burst_mean=12.0, burst_amp=0.30,
                 burst_rate=0.02, degrade=None):
        rng = np.random.default_rng(seed)
        n = len(LINKS)
        base = np.array([l[4] for l in LINKS]) * load
        base = base * rng.uniform(0.85, 1.15, n)
        t = np.arange(T)[:, None]
        period = rng.uniform(60, 120, n)
        phase = rng.uniform(0, 2 * np.pi, n)
        wave = 0.06 * load * np.sin(2 * np.pi * t / period + phase)
        burst = np.zeros((T, n))
        on = np.zeros(n, dtype=bool)
        p_end = 1.0 / burst_mean
        for k in range(T):
            start = (~on) & (rng.random(n) < burst_rate)
            stop = on & (rng.random(n) < p_end)
            on = (on | start) & ~stop
            burst[k] = np.where(on, burst_amp, 0.0)
        self.util = np.clip(base + wave + burst, 0.0, 1.5)
        self.cap = np.ones((T, n))
        if degrade is not None:                      # (link index, t0, t1, factor)
            li, t0, t1, f = degrade
            self.cap[t0:t1, li] = f
        self.T = T


def link_state(bg, t, fg_links, fg_rate_mbps):
    """Per-link mean queueing delay, total mean delay (ms), loss prob at time t.

    fg_links: indices of links used by the foreground flow (adds load).
    Returns dict of numpy arrays.
    """
    bw = np.array([l[2] for l in LINKS], dtype=float)
    prop = np.array([l[3] for l in LINKS], dtype=float)
    mu_nom = bw * 1e6 / PKT_BITS                      # packets/s at nominal capacity
    lam = bg.util[t] * mu_nom
    if len(fg_links):
        lam = lam.copy()
        lam[list(fg_links)] += fg_rate_mbps * 1e6 / PKT_BITS
    mu = mu_nom * bg.cap[t]
    rho = lam / mu
    w, p_loss = mm1k(rho, mu)
    tx = PKT_BITS / (bw * 1e6 * bg.cap[t]) * 1e3      # ms
    w_ms = w * 1e3
    queue = np.maximum(w_ms - tx, 0.0)
    return dict(rho=rho, queue=queue, tx=tx, prop=prop, loss=p_loss,
                total=prop + tx + queue + PROC_MS, bits_tx=bw * 1e6 * bg.cap[t])


def sample_path(state, links, n, rng, bits=PKT_BITS):
    """Sample n packets over the given links. Returns delays (ms), NaN if lost."""
    links = list(links)
    q = rng.exponential(1.0, size=(n, len(links))) * state["queue"][links]
    fixed = state["prop"][links] + PROC_MS + bits / state["bits_tx"][links] * 1e3
    d = (q + fixed).sum(axis=1)
    lost = (rng.random((n, len(links))) < state["loss"][links]).any(axis=1)
    d[lost] = np.nan
    return d
