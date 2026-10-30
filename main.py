"""main.py - command-line entry point for the Network Path and Delay Analyzer.

  python main.py demo --scenario S3 --seed 1                 # baseline vs proposed, live
  python main.py demo --scenario S3 --probe-interval 5 --hysteresis 0.2
  python main.py analyze --scenario S4 --seed 3 --at 150     # per-hop delay report
  python main.py experiments                                  # all runs, CSV files and figures
"""
import argparse
import subprocess
import sys
from netmodel import Background, build_graph, link_state
from routing import candidate_paths, path_links
from simulate import run, SCENARIOS, FG_RATE
from analyzer import analyze_path, format_report


def cmd_demo(a):
    dk = dict(alpha=a.alpha, probe_interval=a.probe_interval, hysteresis=a.hysteresis, confirm=a.confirm)
    bk = dict(burst_mean=a.burst_mean) if a.burst_mean else None
    b = run("baseline", a.scenario, a.seed, bg_kwargs=bk, fg_rate=a.fg_rate)
    p = run("proposed", a.scenario, a.seed, daps_kwargs=dk, bg_kwargs=bk, fg_rate=a.fg_rate)
    print(f"Scenario {a.scenario}, seed {a.seed}, proposed parameters: {dk}")
    print(f"{'Metric':<22}{'Baseline':>12}{'Proposed':>12}{'Improvement':>14}")
    for key, name in [("delay", "Mean delay (ms)"), ("p95", "95th pct delay (ms)"),
                      ("jitter", "Jitter (ms)"), ("loss", "Packet loss (%)")]:
        imp = f"{100 * (b[key] - p[key]) / b[key]:.1f}%" if b[key] > 1e-6 else "n/a"
        print(f"{name:<22}{b[key]:>12.2f}{p[key]:>12.2f}{imp:>14}")
    print(f"{'Path switches':<22}{b['switches']:>12.0f}{p['switches']:>12.0f}")
    print(f"{'Probe packets sent':<22}{b['probes']:>12.0f}{p['probes']:>12.0f}")


def cmd_analyze(a):
    g = build_graph()
    cfg = dict(SCENARIOS[a.scenario])
    bg = Background(a.seed, T=300, **cfg)
    for i, path in enumerate(candidate_paths(g), start=1):
        st = link_state(bg, a.at, path_links(g, path), FG_RATE)   # what-if: the flow uses this path
        rows, worst = analyze_path(g, path, st)
        print(f"--- P{i} at t = {a.at} s ({a.scenario}, seed {a.seed}) ---")
        print(format_report(path, rows, worst))
        print()


def cmd_experiments(_):
    subprocess.check_call([sys.executable, "experiments.py"])
    subprocess.check_call([sys.executable, "figures.py"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("demo")
    d.add_argument("--scenario", default="S3", choices=list(SCENARIOS))
    d.add_argument("--seed", type=int, default=1)
    d.add_argument("--alpha", type=float, default=0.3)
    d.add_argument("--probe-interval", type=int, default=2)
    d.add_argument("--hysteresis", type=float, default=0.10)
    d.add_argument("--confirm", type=int, default=2)
    d.add_argument("--fg-rate", type=float, default=FG_RATE)
    d.add_argument("--burst-mean", type=float, default=None)
    d.set_defaults(fn=cmd_demo)
    n = sub.add_parser("analyze")
    n.add_argument("--scenario", default="S3", choices=list(SCENARIOS))
    n.add_argument("--seed", type=int, default=1)
    n.add_argument("--at", type=int, default=120)
    n.set_defaults(fn=cmd_analyze)
    e = sub.add_parser("experiments")
    e.set_defaults(fn=cmd_experiments)
    args = ap.parse_args()
    args.fn(args)
