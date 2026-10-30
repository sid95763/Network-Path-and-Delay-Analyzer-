"""experiments.py - repeated runs, statistics, sensitivity study and ablation."""
import os
import numpy as np
import pandas as pd
from scipy import stats
from simulate import run, SCENARIOS

N_RUNS = 30
METRICS = ["delay", "p95", "jitter", "loss"]


def compare(scenarios=("S1", "S2", "S3", "S4"), n=N_RUNS, daps_kwargs=None, bg_kwargs=None):
    """Run baseline and proposed on the same random link conditions (paired seeds)."""
    rows = []
    for sc in scenarios:
        for seed in range(1, n + 1):
            for scheme in ("baseline", "proposed"):
                r = run(scheme, sc, seed, daps_kwargs=daps_kwargs, bg_kwargs=bg_kwargs)
                rows.append(dict(scenario=sc, scheme=scheme, seed=seed, **r))
    return pd.DataFrame(rows)


def summarise(df):
    """Mean +- SD table, improvement % and paired t-test p-value per scenario/metric."""
    out = []
    for sc, d in df.groupby("scenario"):
        b = d[d.scheme == "baseline"].sort_values("seed")
        p = d[d.scheme == "proposed"].sort_values("seed")
        for m in METRICS:
            bm, pm = b[m].mean(), p[m].mean()
            imp = 100 * (bm - pm) / bm if bm > 1e-6 else np.nan
            diff = b[m].values - p[m].values
            pval = stats.ttest_rel(b[m].values, p[m].values).pvalue if diff.std() > 0 else np.nan
            ci = stats.t.interval(0.95, len(diff) - 1, loc=diff.mean(), scale=stats.sem(diff)) if diff.std() > 0 else (0, 0)
            out.append(dict(scenario=sc, metric=m, base_mean=bm, base_sd=b[m].std(ddof=1),
                            prop_mean=pm, prop_sd=p[m].std(ddof=1), improvement=imp,
                            p_value=pval, ci_lo=ci[0], ci_hi=ci[1],
                            switches=p["switches"].mean(), switches_sd=p["switches"].std(ddof=1)))
    return pd.DataFrame(out)


def sweep(name, values, make_kwargs, scenario="S3", n=N_RUNS):
    """One-parameter sensitivity study of the proposed scheme (baseline run once)."""
    base = [run("baseline", scenario, s) for s in range(1, n + 1)]
    rows = []
    for v in values:
        dk, bk = make_kwargs(v)
        runs_p = [run("proposed", scenario, s, daps_kwargs=dk, bg_kwargs=bk) for s in range(1, n + 1)]
        if bk:   # baseline must see the same background change
            base_v = [run("baseline", scenario, s, bg_kwargs=bk) for s in range(1, n + 1)]
        else:
            base_v = base
        bd = np.mean([r["delay"] for r in base_v]); pd_ = np.mean([r["delay"] for r in runs_p])
        rows.append(dict(parameter=name, value=v, base_delay=bd, prop_delay=pd_,
                         prop_sd=np.std([r["delay"] for r in runs_p], ddof=1),
                         improvement=100 * (bd - pd_) / bd,
                         prop_loss=np.mean([r["loss"] for r in runs_p]),
                         base_loss=np.mean([r["loss"] for r in base_v]),
                         prop_jitter=np.mean([r["jitter"] for r in runs_p]),
                         switches=np.mean([r["switches"] for r in runs_p]),
                         probes=np.mean([r["probes"] for r in runs_p])))
    return pd.DataFrame(rows)


ABLATIONS = {
    "Full DAPS": dict(),
    "Delay-only score": dict(use_jitter_loss=False),
    "No smoothing (alpha = 1)": dict(alpha=1.0),
    "No hysteresis (h = 0)": dict(hysteresis=0.0),
    "No hold-down (confirm = 1)": dict(confirm=1),
    "No hysteresis, no hold-down": dict(hysteresis=0.0, confirm=1),
}


def ablation(scenarios=("S2", "S3"), n=N_RUNS):
    rows = []
    for sc in scenarios:
        full = None
        for name, kw in ABLATIONS.items():
            rs = [run("proposed", sc, s, daps_kwargs=kw) for s in range(1, n + 1)]
            dl = np.array([r["delay"] for r in rs])
            if full is None:
                full = dl
            pv = stats.ttest_rel(dl, full).pvalue if name != "Full DAPS" else np.nan
            rows.append(dict(scenario=sc, variant=name, p_vs_full=pv,
                             delay=np.mean([r["delay"] for r in rs]),
                             delay_sd=np.std([r["delay"] for r in rs], ddof=1),
                             jitter=np.mean([r["jitter"] for r in rs]),
                             loss=np.mean([r["loss"] for r in rs]),
                             switches=np.mean([r["switches"] for r in rs])))
    return pd.DataFrame(rows)


def fg_sweep(rates=(0.5, 1, 2, 4, 6), scenario="S3", n=N_RUNS):
    """Effect of foreground flow size (self-induced congestion)."""
    rows = []
    for fr in rates:
        b = [run("baseline", scenario, s, fg_rate=fr) for s in range(1, n + 1)]
        p = [run("proposed", scenario, s, fg_rate=fr) for s in range(1, n + 1)]
        bd = np.mean([r["delay"] for r in b]); pdl = np.mean([r["delay"] for r in p])
        rows.append(dict(parameter="fg_rate_mbps", value=fr, base_delay=bd, prop_delay=pdl,
                         improvement=100 * (bd - pdl) / bd,
                         base_loss=np.mean([r["loss"] for r in b]), prop_loss=np.mean([r["loss"] for r in p]),
                         switches=np.mean([r["switches"] for r in p])))
    return pd.DataFrame(rows)


def grid(intervals=(1, 2, 5, 10, 20), bursts=(2, 5, 12, 25, 50), scenario="S3", n=N_RUNS):
    """Improvement (%) in mean delay for each probe interval x burst duration pair."""
    rows = []
    for bm in bursts:
        bk = dict(burst_mean=bm)
        b = np.mean([run("baseline", scenario, s, bg_kwargs=bk)["delay"] for s in range(1, n + 1)])
        for iv in intervals:
            p = np.mean([run("proposed", scenario, s, daps_kwargs=dict(probe_interval=iv), bg_kwargs=bk)["delay"]
                         for s in range(1, n + 1)])
            rows.append(dict(burst_mean_s=bm, probe_interval_s=iv, base_delay=b, prop_delay=p,
                             improvement=100 * (b - p) / b))
    return pd.DataFrame(rows)


def all_sweeps(n=N_RUNS):
    parts = [
        sweep("probe_interval_s", [1, 2, 5, 10, 20], lambda v: (dict(probe_interval=v), None), n=n),
        sweep("ewma_alpha", [0.1, 0.3, 0.5, 0.8, 1.0], lambda v: (dict(alpha=v), None), n=n),
        sweep("hysteresis_h", [0.0, 0.05, 0.10, 0.20, 0.30], lambda v: (dict(hysteresis=v), None), n=n),
        sweep("burst_mean_s", [2, 5, 12, 25, 50], lambda v: (dict(), dict(burst_mean=v)), n=n),
    ]
    return pd.concat(parts, ignore_index=True)


if __name__ == "__main__":
    os.makedirs("results", exist_ok=True)
    df = compare()
    df.to_csv("results/raw_runs.csv", index=False)
    summarise(df).to_csv("results/summary.csv", index=False)
    all_sweeps().to_csv("results/sensitivity.csv", index=False)
    ablation().to_csv("results/ablation.csv", index=False)
    fg_sweep().to_csv("results/fg_rate.csv", index=False)
    grid().to_csv("results/grid.csv", index=False)
    print("done")
