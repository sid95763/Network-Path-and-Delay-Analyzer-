"""analyzer.py - per-hop path and delay analyzer (traceroute-style report)."""
from netmodel import LINKS, link_name


def analyze_path(g, path, state):
    """Break the delay of a path into its components, hop by hop."""
    rows, cum = [], 0.0
    for hop, (a, b) in enumerate(zip(path[:-1], path[1:]), start=1):
        i = g[a][b]["idx"]
        total = state["total"][i]
        cum += total
        rows.append(dict(hop=hop, link=link_name(i), to=b, util=float(state["rho"][i]),
                         prop=float(state["prop"][i]), tx=float(state["tx"][i]),
                         queue=float(state["queue"][i]), total=float(total),
                         loss=float(state["loss"][i] * 100), cum=cum))
    if not rows:
        return [], {}
    worst = max(rows, key=lambda r: r["queue"])
    return rows, worst


def format_report(path, rows, worst):
    if not rows or not worst:
        return "Path: " + " -> ".join(path) + "\nNo hop data available."
    out = ["Path: " + " -> ".join(path),
           f"{'Hop':<4}{'Link':<8}{'Util':>6}{'Prop':>8}{'Tx':>7}{'Queue':>8}{'Total':>8}{'Loss%':>7}{'Cum':>8}"]
    for r in rows:
        out.append(f"{r['hop']:<4}{r['link']:<8}{r['util']:>6.2f}{r['prop']:>8.2f}{r['tx']:>7.2f}"
                   f"{r['queue']:>8.2f}{r['total']:>8.2f}{r['loss']:>7.2f}{r['cum']:>8.2f}")
    total = rows[-1]["cum"]
    share = 100 * worst["queue"] / total if total else 0
    out.append(f"End-to-end mean delay = {total:.2f} ms (all times in ms)")
    out.append(f"Bottleneck hop: {worst['link']} (queueing {worst['queue']:.2f} ms = {share:.0f}% of path delay)")
    return "\n".join(out)
