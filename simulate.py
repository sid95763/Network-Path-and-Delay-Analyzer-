"""simulate.py - one simulation run (baseline or proposed) and its metrics."""
import numpy as np
from netmodel import Background, build_graph, link_state, sample_path
from routing import baseline_path, path_links, DAPS

FG_RATE = 2.0        # Mbps foreground flow (S -> D)
PKTS_PER_STEP = 20   # foreground packets sampled each second

SCENARIOS = {
    "S1": dict(load=0.5),                                   # low load
    "S2": dict(load=1.0),                                   # medium load
    "S3": dict(load=1.5),                                   # high load
    "S4": dict(load=1.0, degrade=(2, 100, 200, 0.4)),       # R1-R2 loses 60% capacity, t = 100-200 s
}


def run(scheme, scenario, seed, T=300, daps_kwargs=None, bg_kwargs=None, trace=False, fg_rate=FG_RATE):
    g = build_graph()
    cfg = dict(SCENARIOS[scenario] if isinstance(scenario, str) else scenario)
    cfg.update(bg_kwargs or {})
    bg = Background(seed, T=T, **cfg)
    rng = np.random.default_rng(10_000 + seed)       # packet-level randomness
    if scheme == "baseline":
        sel = None
        links = path_links(g, baseline_path(g))
        cur_links = links
    else:
        sel = DAPS(g, **(daps_kwargs or {}))
        cur_links = sel.links[sel.cur]
    all_d, step_mean, sent, lost, switch_t, path_id = [], [], 0, 0, [], []
    for t in range(T):
        if sel is not None and t % sel.interval == 0:
            sel.probe(link_state(bg, t, cur_links, fg_rate), rng)
            before = sel.cur
            sel.decide()
            if sel.cur != before:
                switch_t.append(t)
            cur_links = sel.links[sel.cur]
        st = link_state(bg, t, cur_links, fg_rate)
        d = sample_path(st, cur_links, PKTS_PER_STEP, rng)
        sent += len(d); lost += int(np.isnan(d).sum())
        ok = d[~np.isnan(d)]
        all_d.append(ok)
        step_mean.append(ok.mean() if len(ok) else np.nan)
        path_id.append(sel.cur if sel is not None else 0)
    d = np.concatenate(all_d) if len(all_d) else np.array([])
    if len(d) > 0:
        mean_d = float(d.mean())
        p95_d = float(np.percentile(d, 95))
        jit = float(np.abs(np.diff(d)).mean()) if len(d) > 1 else 0.0
    else:
        mean_d, p95_d, jit = 400.0, 400.0, 0.0
    res = dict(delay=mean_d, p95=p95_d, jitter=jit,
               loss=100.0 * lost / sent if sent > 0 else 0.0,
               switches=0 if sel is None else sel.switches,
               probes=0 if sel is None else sel.probe_packets)
    if trace:
        res.update(step_mean=np.array(step_mean), switch_t=switch_t, path_id=np.array(path_id))
    return res
