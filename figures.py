"""figures.py - draws every figure used in the report from the saved result files."""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.ticker
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon
from netmodel import LINKS, build_graph, link_state, Background
from routing import candidate_paths, baseline_path, path_links
from simulate import run, FG_RATE
from analyzer import analyze_path, format_report

plt.rcParams.update({"font.family": "serif", "font.serif": ["Liberation Serif", "DejaVu Serif"],
                     "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
OUT = "figures"
BLUE, ORANGE, GREY = "#1f4e79", "#c55a11", "#7f7f7f"


def topology():
    pos = {"S": (0, 1), "R1": (2, 2), "R3": (2, 0), "R5": (3.6, 1.0), "R2": (5, 1.55), "R4": (5, 0.35), "D": (7.2, 1)}
    g = build_graph()
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    p = candidate_paths(g)
    styles = [(BLUE, 3.2, "-"), (ORANGE, 2.2, "--"), ("#548235", 2.2, ":")]
    for (a, b, bw, prop, _u) in LINKS:
        (x1, y1), (x2, y2) = pos[a], pos[b]
        ax.plot([x1, x2], [y1, y2], color="#bbbbbb", lw=1.5, zorder=1)
    for path, (c, lw, ls) in zip(p, styles):
        for a, b in zip(path[:-1], path[1:]):
            (x1, y1), (x2, y2) = pos[a], pos[b]
            off = {0: 0.0, 1: 0.0, 2: 0.0}
            ax.plot([x1, x2], [y1, y2], color=c, lw=lw, ls=ls, zorder=2, alpha=0.9)
    for (a, b, bw, prop, _u) in LINKS:
        (x1, y1), (x2, y2) = pos[a], pos[b]
        ox, oy = {("R1", "R5"): (-0.5, -0.32), ("R5", "R4"): (0.55, -0.1)}.get((a, b), (0, 0.16))
        ax.text((x1 + x2) / 2 + ox, (y1 + y2) / 2 + oy, f"{bw} Mbps\n{prop:g} ms", ha="center", va="bottom", fontsize=8.5,
                bbox=dict(fc="white", ec="none", pad=0.6), zorder=4)
    for n, (x, y) in pos.items():
        host = n in ("S", "D")
        ax.scatter([x], [y], s=900 if host else 620, c="#fce4d6" if host else "#deebf7",
                   edgecolors="black", zorder=5, marker="s" if host else "o")
        ax.text(x, y, n, ha="center", va="center", fontsize=11, weight="bold", zorder=6)
    ax.plot([], [], color=BLUE, lw=3.2, label="P1: S-R1-R2-D (baseline choice, lowest static cost)")
    ax.plot([], [], color=ORANGE, lw=2.2, ls="--", label="P2: S-R3-R4-D")
    ax.plot([], [], color="#548235", lw=2.2, ls=":", label="P3: S-R1-R5-R4-D")
    ax.legend(loc="lower left", fontsize=9, frameon=False, bbox_to_anchor=(-0.02, -0.12))
    ax.set_xlim(-0.6, 7.8); ax.set_ylim(-0.7, 2.6); ax.axis("off")
    fig.savefig(f"{OUT}/fig_topology.png"); plt.close(fig)


def box(ax, x, y, w, h, text, fc="#deebf7", fs=10):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=fc, ec="black", lw=1.1))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs)


def arrow(ax, x1, y1, x2, y2, text=None, dx=0.0, dy=0.0):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=1.2))
    if text:
        ax.text((x1 + x2) / 2 + dx, (y1 + y2) / 2 + dy, text, fontsize=9, ha="center", va="center")


def architecture():
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 5); ax.axis("off")
    box(ax, 1.6, 4.0, 2.6, 0.9, "Network model\n(topology + M/M/1/K links)", "#fce4d6")
    box(ax, 1.6, 2.5, 2.6, 0.9, "Background traffic\ngenerator (load, bursts)", "#fce4d6")
    box(ax, 5.0, 4.0, 2.6, 0.9, "Probe engine\n(4 probes / path / 2 s)")
    box(ax, 5.0, 2.5, 2.6, 0.9, "Estimator\n(EWMA delay, jitter, loss)")
    box(ax, 5.0, 1.0, 2.6, 0.9, "Path selector (DAPS)\nscore + hysteresis")
    box(ax, 8.5, 4.0, 2.4, 0.9, "Baseline\n(static OSPF-style)", "#e2efda")
    box(ax, 8.5, 2.5, 2.4, 0.9, "Foreground flow\nS to D, 2 Mbps", "#e2efda")
    box(ax, 8.5, 1.0, 2.4, 0.9, "Analyzer and metrics\n(per-hop table, graphs)", "#fff2cc")
    arrow(ax, 1.6, 3.5, 1.6, 2.95)
    arrow(ax, 2.9, 4.0, 3.7, 4.0)
    arrow(ax, 5.0, 3.55, 5.0, 2.95)
    arrow(ax, 5.0, 2.05, 5.0, 1.45)
    arrow(ax, 6.3, 1.0, 7.3, 1.0)
    arrow(ax, 6.3, 3.9, 7.3, 3.2)
    arrow(ax, 6.3, 1.2, 7.3, 2.3, "path choice", 0.2, 0.0)
    arrow(ax, 8.5, 2.05, 8.5, 1.45)
    arrow(ax, 8.5, 3.55, 8.5, 2.95)
    fig.savefig(f"{OUT}/fig_architecture.png"); plt.close(fig)


def flowchart():
    fig, ax = plt.subplots(figsize=(6.4, 8.2))
    ax.set_xlim(0, 10); ax.set_ylim(0, 14); ax.axis("off")
    box(ax, 4, 13.2, 4.6, 0.8, "Start of each second t", "#e2efda")
    d = Polygon([(4, 12.3), (6.1, 11.4), (4, 10.5), (1.9, 11.4)], fc="#fff2cc", ec="black", lw=1.1)
    ax.add_patch(d); ax.text(4, 11.4, "t divisible by\nprobe interval?", ha="center", va="center", fontsize=9.5)
    arrow(ax, 4, 12.8, 4, 12.3)
    box(ax, 4, 9.5, 5.0, 0.9, "Send probes on each\ncandidate path (P1, P2, P3)")
    arrow(ax, 4, 10.5, 4, 9.95, "yes", 0.35, 0)
    box(ax, 4, 8.1, 5.0, 0.9, "Update EWMA of delay,\njitter and loss per path")
    arrow(ax, 4, 9.05, 4, 8.55)
    box(ax, 4, 6.7, 5.0, 0.9, "score = D + wj*J + wl*L\n(lower is better)")
    arrow(ax, 4, 7.65, 4, 7.15)
    d2 = Polygon([(4, 5.9), (6.4, 4.85), (4, 3.8), (1.6, 4.85)], fc="#fff2cc", ec="black", lw=1.1)
    ax.add_patch(d2); ax.text(4, 4.85, "best score < (1-h) x\ncurrent score?", ha="center", va="center", fontsize=9.5)
    arrow(ax, 4, 6.25, 4, 5.9)
    d3 = Polygon([(4, 3.2), (6.4, 2.25), (4, 1.3), (1.6, 2.25)], fc="#fff2cc", ec="black", lw=1.1)
    ax.add_patch(d3); ax.text(4, 2.25, "same winner for\n2 checks in a row?", ha="center", va="center", fontsize=9.5)
    arrow(ax, 4, 3.8, 4, 3.2, "yes", 0.35, 0)
    box(ax, 7.9, 2.25, 2.2, 0.9, "Switch traffic\nto best path", "#fce4d6")
    arrow(ax, 5.6, 2.25, 6.8, 2.25, "yes", 0, 0.25)
    box(ax, 4, 0.5, 5.0, 0.8, "Send foreground packets on current path", "#e2efda")
    arrow(ax, 4, 1.3, 4, 0.9, "no", 0.35, 0)
    # switch box goes down to the merge line
    ax.plot([7.9, 7.9], [1.8, 0.5], color="black", lw=1.2)
    # right-hand return line for the two 'no' branches
    ax.plot([6.1, 9.5], [11.4, 11.4], color="black", lw=1.1)
    ax.plot([6.4, 9.5], [4.85, 4.85], color="black", lw=1.1)
    ax.plot([9.5, 9.5], [11.4, 0.5], color="black", lw=1.1)
    ax.annotate("", xy=(6.5, 0.5), xytext=(9.5, 0.5), arrowprops=dict(arrowstyle="->", lw=1.2))
    ax.text(7.8, 11.55, "no: keep current path", fontsize=8.5, ha="center")
    ax.text(7.95, 5.0, "no: reset counter", fontsize=8.5, ha="center")
    fig.savefig(f"{OUT}/fig_flowchart.png"); plt.close(fig)


def results():
    s = pd.read_csv("results/summary.csv")
    scen = ["S1", "S2", "S3", "S4"]
    labels = {"S1": "S1\nlow", "S2": "S2\nmedium", "S3": "S3\nhigh", "S4": "S4\ndegradation"}
    fig, axs = plt.subplots(2, 2, figsize=(8.6, 6.2)); axs = axs.ravel()
    meta = [("delay", "Mean end-to-end delay (ms)"), ("p95", "95th-percentile delay (ms)"),
            ("jitter", "Jitter (ms)"), ("loss", "Packet loss (%)")]
    x = np.arange(len(scen)); w = 0.38
    for ax, (m, title) in zip(axs, meta):
        d = s[s.metric == m].set_index("scenario").loc[scen]
        ax.bar(x - w / 2, d.base_mean, w, yerr=d.base_sd, capsize=3, color=GREY, label="Baseline")
        ax.bar(x + w / 2, d.prop_mean, w, yerr=d.prop_sd, capsize=3, color=BLUE, label="Proposed (DAPS)")
        ax.set_xticks(x); ax.set_xticklabels([labels[k].replace("\n", " ") for k in scen], fontsize=9)
        ax.set_title(title, fontsize=10.5)
    axs[0].legend(fontsize=8.5, frameon=False)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_results.png"); plt.close(fig)


def timeseries():
    fig, axs = plt.subplots(2, 1, figsize=(9, 5.8), sharex=True)
    for ax, sc in zip(axs, ["S3", "S4"]):
        b = run("baseline", sc, 3, trace=True)
        p = run("proposed", sc, 3, trace=True)
        k = 3
        sm = lambda v: pd.Series(v).rolling(k, min_periods=1, center=True).mean().values
        ax.plot(sm(b["step_mean"]), color=GREY, lw=1.2, label="Baseline")
        ax.plot(sm(p["step_mean"]), color=BLUE, lw=1.2, label="Proposed (DAPS)")
        for i, t in enumerate(p["switch_t"]):
            ax.axvline(t, color=ORANGE, lw=0.6, alpha=0.7, label="Path switch" if i == 0 else None)
        ax.set_ylabel("Delay (ms)")
        ax.set_title(f"{sc}, run with seed 3", fontsize=10.5, loc="left")
        if sc == "S4":
            ax.axvspan(100, 200, color="#f4cccc", alpha=0.35, label="R1-R2 degraded")
        if sc == "S4":
            ax.set_yscale("log"); ax.set_yticks([15, 20, 30, 50, 100, 200])
            ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter()); ax.minorticks_off()
        ax.legend(fontsize=8.5, frameon=False, ncol=4, loc="upper right")
    axs[1].set_xlabel("Time (s)")
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_timeseries.png"); plt.close(fig)


def sensitivity():
    s = pd.read_csv("results/sensitivity.csv")
    fig, axs = plt.subplots(1, 3, figsize=(11.5, 3.5))
    d = s[s.parameter == "probe_interval_s"]
    axs[0].plot(d.value, d.improvement, "o-", color=BLUE)
    axs[0].axhline(0, color="black", lw=0.8)
    axs[0].set_xlabel("Probe interval (s)"); axs[0].set_ylabel("Delay improvement (%)")
    axs[0].set_title("(a) Probe interval", fontsize=10.5)
    d = s[s.parameter == "ewma_alpha"]
    axs[1].plot(d.value, d.improvement, "o-", color=BLUE, label="Delay improvement (%)")
    axs[1].set_xlabel("EWMA weight alpha"); axs[1].set_ylabel("Delay improvement (%)")
    a2 = axs[1].twinx(); a2.spines["right"].set_visible(True)
    a2.plot(d.value, d.switches, "s--", color=ORANGE); a2.set_ylabel("Path switches per run", color=ORANGE)
    axs[1].set_title("(b) Smoothing weight", fontsize=10.5)
    d = s[s.parameter == "hysteresis_h"]
    axs[2].plot(d.value, d.improvement, "o-", color=BLUE)
    axs[2].set_xlabel("Hysteresis threshold h"); axs[2].set_ylabel("Delay improvement (%)")
    a3 = axs[2].twinx(); a3.spines["right"].set_visible(True)
    a3.plot(d.value, d.switches, "s--", color=ORANGE); a3.set_ylabel("Path switches per run", color=ORANGE)
    axs[2].set_title("(c) Hysteresis", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_sensitivity.png"); plt.close(fig)


def failure():
    g = pd.read_csv("results/grid.csv")
    pv = g.pivot(index="burst_mean_s", columns="probe_interval_s", values="improvement")
    f = pd.read_csv("results/fg_rate.csv")
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.9), gridspec_kw=dict(width_ratios=[1.15, 1]))
    ax = axs[0]
    im = ax.imshow(pv.values, cmap="RdYlGn", vmin=-25, vmax=25, origin="lower", aspect="auto")
    ax.set_xticks(range(len(pv.columns))); ax.set_xticklabels(pv.columns)
    ax.set_yticks(range(len(pv.index))); ax.set_yticklabels(pv.index)
    for i in range(pv.shape[0]):
        for j in range(pv.shape[1]):
            ax.text(j, i, f"{pv.values[i, j]:.1f}", ha="center", va="center", fontsize=9)
    ax.set_xlabel("Probe interval (s)"); ax.set_ylabel("Mean burst length (s)")
    ax.set_title("(a) Delay improvement (%), S3", fontsize=10.5)
    for sp in ax.spines.values():
        sp.set_visible(False)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    ax = axs[1]
    ax.plot(f.value, f.base_delay, "o-", color=GREY, label="Baseline")
    ax.plot(f.value, f.prop_delay, "o-", color=BLUE, label="Proposed (DAPS)")
    ax.set_xlabel("Foreground flow rate (Mbps)"); ax.set_ylabel("Mean delay (ms)")
    ax.set_title("(b) Effect of flow size, S3", fontsize=10.5)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_failure.png"); plt.close(fig)


def analyzer_samples():
    g = build_graph()
    txt = []
    for sc, seed, t in [("S3", 3, 120), ("S4", 3, 150)]:
        from simulate import SCENARIOS
        cfg = dict(SCENARIOS[sc]); bg = Background(seed, T=300, **cfg)
        for name, path in [("Baseline path P1", candidate_paths(g)[0]), ("Alternative path P2", candidate_paths(g)[1])]:
            st = link_state(bg, t, path_links(g, path), FG_RATE)
            rows, worst = analyze_path(g, path, st)
            txt.append(f"[{sc}, seed {seed}, t = {t} s] {name}\n" + format_report(path, rows, worst) + "\n")
    open("results/analyzer_samples.txt", "w").write("\n".join(txt))
    print("\n".join(txt))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    topology(); architecture(); flowchart(); results(); timeseries(); sensitivity(); failure()
    analyzer_samples()
