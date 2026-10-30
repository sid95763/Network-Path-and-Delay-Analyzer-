"""make_presentation.py - Generates the complete PowerPoint deck for the project review."""
import os
import shutil
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# Color palette
DARK_BLUE = RGBColor(31, 78, 121)    # #1F4E79
LIGHT_BLUE = RGBColor(222, 235, 247) # #DEEBF7
ORANGE = RGBColor(197, 90, 17)       # #C55A11
WHITE = RGBColor(255, 255, 255)
DARK_GREY = RGBColor(50, 50, 50)
LIGHT_BG = RGBColor(245, 247, 250)
BORDER_COLOR = RGBColor(200, 210, 225)

def create_deck(filename="Network_Path_and_Delay_Analyzer_Presentation.pptx"):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def add_header(slide, title_text, category="COMPUTER NETWORKS LAB (BCSE308P)"):
        # Top banner background
        top_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.15))
        top_bar.fill.solid()
        top_bar.fill.fore_color.rgb = DARK_BLUE
        top_bar.line.fill.background()

        # Category text
        tf_cat = top_bar.text_frame
        tf_cat.word_wrap = True
        tf_cat.margin_left = Inches(0.8)
        tf_cat.margin_top = Inches(0.12)
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category.upper()
        p_cat.font.size = Pt(10)
        p_cat.font.bold = True
        p_cat.font.color.rgb = RGBColor(200, 220, 245)

        # Main Title text
        p_title = tf_cat.add_paragraph()
        p_title.text = title_text
        p_title.font.size = Pt(22)
        p_title.font.bold = True
        p_title.font.color.rgb = WHITE

        # Footer
        footer = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(11.7), Inches(0.35))
        p_foot = footer.text_frame.paragraphs[0]
        p_foot.text = "Network Path & Delay Analyzer | Abhik Boxi (24BCE0741) & Siddharth Saini (24BKT0121)"
        p_foot.font.size = Pt(10)
        p_foot.font.color.rgb = RGBColor(120, 120, 120)

    # ==================== SLIDE 1: Title Slide ====================
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = DARK_BLUE
    bg1.line.fill.background()

    # Title box
    tb = s1.shapes.add_textbox(Inches(1.0), Inches(1.5), Inches(11.333), Inches(3.0))
    tf = tb.text_frame
    p0 = tf.paragraphs[0]
    p0.text = "BCSE308P - Computer Networks Lab Project"
    p0.font.size = Pt(16)
    p0.font.bold = True
    p0.font.color.rgb = RGBColor(220, 235, 255)

    p1 = tf.add_paragraph()
    p1.text = "NETWORK PATH AND DELAY ANALYZER"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = WHITE
    p1.space_before = Pt(10)

    p2 = tf.add_paragraph()
    p2.text = "Per-Hop Delay Decomposition & Delay-Aware Adaptive Path Selection (DAPS)"
    p2.font.size = Pt(18)
    p2.font.color.rgb = RGBColor(254, 217, 142)
    p2.space_before = Pt(8)

    # Details Box
    det = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(4.8), Inches(11.333), Inches(1.8))
    det.fill.solid()
    det.fill.fore_color.rgb = RGBColor(25, 60, 95)
    det.line.color.rgb = RGBColor(70, 120, 180)
    dtf = det.text_frame
    dtf.margin_left = Inches(0.4)
    dtf.margin_top = Inches(0.25)
    dp0 = dtf.paragraphs[0]
    dp0.text = "Project Team Members:"
    dp0.font.size = Pt(13)
    dp0.font.bold = True
    dp0.font.color.rgb = RGBColor(200, 220, 245)

    dp1 = dtf.add_paragraph()
    dp1.text = "• Abhik Boxi (Reg. No: 24BCE0741) — Modeling, Analyzer & Simulation Engine"
    dp1.font.size = Pt(14)
    dp1.font.color.rgb = WHITE
    dp1.space_before = Pt(4)

    dp2 = dtf.add_paragraph()
    dp2.text = "• Siddharth Saini (Reg. No: 24BKT0121) — Routing Algorithm (DAPS), Experiments & CLI"
    dp2.font.size = Pt(14)
    dp2.font.color.rgb = WHITE
    dp2.space_before = Pt(4)

    # ==================== SLIDE 2: Motivation & Problem ====================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "Motivation & Problem Statement")

    def add_card(slide, x, y, w, h, title, items, color=LIGHT_BLUE):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
        card.fill.solid()
        card.fill.fore_color.rgb = color
        card.line.color.rgb = BORDER_COLOR
        ctf = card.text_frame
        ctf.word_wrap = True
        ctf.margin_left = Inches(0.3)
        ctf.margin_right = Inches(0.3)
        ctf.margin_top = Inches(0.2)
        cp0 = ctf.paragraphs[0]
        cp0.text = title
        cp0.font.size = Pt(15)
        cp0.font.bold = True
        cp0.font.color.rgb = DARK_BLUE
        for it in items:
            p = ctf.add_paragraph()
            p.text = "• " + it
            p.font.size = Pt(12)
            p.font.color.rgb = DARK_GREY
            p.space_before = Pt(6)

    add_card(s2, 0.8, 1.45, 5.6, 5.3, "The Limitations of Current Routing", [
        "OSPF & Static Metrics: Link-state routing uses static metrics (cost = 100/bandwidth) computed once via Dijkstra.",
        "Blind to Transient Congestion: Costs do not adapt to runtime traffic. Even if a link experiences heavy congestion bursts, traffic remains pinned to the path.",
        "Buffer Saturation: Bursts cause buffer overflow and queueing delays, degrading voice/video services (high jitter and packet drops).",
        "Passive Diagnostics Only: Ping & Traceroute only measure latency/hops; they do not break down where the delay occurs nor do they reroute traffic."
    ])

    add_card(s2, 6.9, 1.45, 5.6, 5.3, "Our Solution & Research Goals", [
        "Component 1 — Hop-by-Hop Analyzer: Splits end-to-end latency into propagation, transmission, processing, and queueing parts to pinpoint bottleneck links.",
        "Component 2 — DAPS (Proposed Mechanism): Actively probes candidate paths every 2s, applies EWMA smoothing to delay/jitter/loss, and intelligently steers traffic.",
        "Anti-Flapping Protection: Employs 10% hysteresis margin and 2-cycle hold-down to stop oscillation.",
        "Rigorous Statistical Validation: Evaluated over 30 paired seed runs across 4 realistic scenarios (S1-S4) with Student's t-test."
    ], RGBColor(254, 243, 230))

    # ==================== SLIDE 3: System Topology & Architecture ====================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "System Architecture & Test Topology")

    if os.path.exists("figures/fig_topology.png"):
        s3.shapes.add_picture("figures/fig_topology.png", Inches(0.8), Inches(1.5), width=Inches(6.2))
    if os.path.exists("figures/fig_architecture.png"):
        s3.shapes.add_picture("figures/fig_architecture.png", Inches(7.2), Inches(1.5), width=Inches(5.3))

    # Descriptive text under pictures
    cap = s3.shapes.add_textbox(Inches(0.8), Inches(5.8), Inches(11.7), Inches(1.1))
    ctf = cap.text_frame
    cp = ctf.paragraphs[0]
    cp.text = "Topology & Candidate Paths from Source (S) to Destination (D):"
    cp.font.size = Pt(13)
    cp.font.bold = True
    cp.font.color.rgb = DARK_BLUE
    cp2 = ctf.add_paragraph()
    cp2.text = "• P1 (S-R1-R2-D): 3 hops, static cost = 20.0, prop = 10ms (Baseline OSPF choice)\n" \
               "• P2 (S-R3-R4-D): 3 hops, static cost = 22.5, prop = 12ms (First alternative)\n" \
               "• P3 (S-R1-R5-R4-D): 4 hops, static cost = 30.0, prop = 14ms (Second alternative via R5)"
    cp2.font.size = Pt(11)
    cp2.font.color.rgb = DARK_GREY

    # ==================== SLIDE 4: Mathematical Delay Model ====================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "Link Delay Model: M/M/1/K Queueing Analysis")

    add_card(s4, 0.8, 1.45, 5.6, 5.3, "M/M/1/K Queueing Formulation", [
        "Overcoming M/M/1 Singularity: In pure M/M/1, delay becomes infinite as utilization rho -> 1. Real routers have finite buffers.",
        "Finite Buffer (K = 64 packets): We model links as M/M/1/K queues. Loss probability is given by:\n  P_K = (1 - rho) * rho^K / (1 - rho^(K+1))",
        "Mean System Time (W): Derived from average packet occupancy N and effective arrival rate lambda_eff = rho * mu * (1 - P_K).",
        "Queueing Delay: Computed as W minus packet transmission time. Always stays bounded even when bursts push rho > 1.",
        "Processing Delay: Fixed at 0.1 ms per hop."
    ])

    add_card(s4, 6.9, 1.45, 5.6, 5.3, "Hop-by-Hop Delay Decomposition", [
        "Total Path Delay Breakdown:\n  d_path = Sum(d_prop + d_tx + d_proc + d_queue)",
        "Fixed Components:\n  • Propagation (2 - 8 ms based on physical distance)\n  • Transmission = (packet_bits / bandwidth)\n  • Processing (0.1 ms fixed)",
        "Variable Component:\n  • Queueing Delay: Grows non-linearly with background traffic bursts.",
        "Bottleneck Hop Identification:\n  Flags the link with max queueing delay and computes its share:\n  Share% = 100 * worst_queue / total_delay",
        "Example Output: Link R1-R2 under degradation suffers 123 ms queueing (90% of entire path delay)."
    ], RGBColor(240, 248, 255))

    # ==================== SLIDE 5: Proposed Mechanism (DAPS) ====================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "Proposed Mechanism: DAPS Algorithm & Logic")

    if os.path.exists("figures/fig_flowchart.png"):
        s5.shapes.add_picture("figures/fig_flowchart.png", Inches(0.8), Inches(1.4), height=Inches(5.4))

    add_card(s5, 5.5, 1.45, 7.0, 5.3, "Four Core Steps of DAPS", [
        "1. Active Probing (Every 2s):\n   Sends 4 lightweight probe packets (64B) along P1, P2, and P3. Computes sample mean delay d, jitter j, and packet loss ratio l.",
        "2. EWMA Smoothing:\n   D_hat = alpha*d + (1-alpha)*D_hat (alpha = 0.3)\n   Smooths out transient sample noise; single bad packets cannot trigger switches.",
        "3. Composite Score Formulation:\n   Score = D_hat + w_J * J_hat + w_L * L_hat\n   (w_J = 1.0, w_L = 1000.0 => 1% packet loss penalized like 10 ms delay).",
        "4. Anti-Flapping Protection:\n   • Hysteresis (h = 0.10): Best score must be at least 10% lower than current path.\n   • Hold-down (confirm = 2): Candidate must win 2 consecutive cycles (4s) before rerouting."
    ])

    # ==================== SLIDE 6: Experimental Setup & Scenarios ====================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "Experimental Setup & Evaluation Methodology")

    add_card(s6, 0.8, 1.45, 5.6, 5.3, "Four Experimental Scenarios", [
        "S1 (Low Load, load factor = 0.5):\nMean link utilization ~ 15-23%. Queues near zero; baseline optimal.",
        "S2 (Medium Load, load factor = 1.0):\nMean link utilization ~ 30-45%. Occasional background bursts.",
        "S3 (High Load, load factor = 1.5):\nMean utilization ~ 45-68%. Heavy bursts push links to saturation (rho ~ 1.0).",
        "S4 (Link Capacity Degradation):\nMedium load, but at t = 100-200s, primary link R1-R2 drops 60% capacity (10 -> 4 Mbps). OSPF static routing cannot detect capacity loss without link-down."
    ])

    add_card(s6, 6.9, 1.45, 5.6, 5.3, "Statistical Evaluation Rigor", [
        "30 Paired Random Seeds: Every test is executed across 30 identical background load realizations for both Baseline and DAPS.",
        "Statistical Significance: Paired Student's t-tests conducted for all metrics (p < 0.001 in congested scenarios).",
        "Key Metrics Evaluated (IPPM Standards):\n• Mean End-to-End Delay (ms)\n• 95th Percentile Delay (tail latency)\n• Delay Jitter (packet-to-packet variation)\n• Packet Loss Ratio (%)\n• Path Switching Frequency & Probe Overhead",
        "100% Reproducible: Seeded pseudo-random streams."
    ], RGBColor(254, 243, 230))

    # ==================== SLIDE 7: Key Results & Performance ====================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "Experimental Results: Baseline vs Proposed (30 Runs)")

    if os.path.exists("figures/fig_results.png"):
        s7.shapes.add_picture("figures/fig_results.png", Inches(6.8), Inches(1.4), width=Inches(5.8))

    # Add results table on left
    table_shape = s7.shapes.add_table(5, 4, Inches(0.8), Inches(1.5), Inches(5.7), Inches(3.2))
    tbl = table_shape.table
    tbl.columns[0].width = Inches(1.2)
    tbl.columns[1].width = Inches(1.5)
    tbl.columns[2].width = Inches(1.5)
    tbl.columns[3].width = Inches(1.5)

    headers = ["Scenario", "Baseline", "DAPS (Proposed)", "Improvement"]
    for i, h in enumerate(headers):
        cell = tbl.cell(0, i)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = DARK_BLUE
        cell.text_frame.paragraphs[0].font.size = Pt(11)
        cell.text_frame.paragraphs[0].font.bold = True
        cell.text_frame.paragraphs[0].font.color.rgb = WHITE

    data = [
        ("S1 (Low)", "13.14 ms | 0.0%", "13.22 ms | 0.0%", "-0.6% (Neutral)"),
        ("S2 (Med)", "16.48 ms | 0.16%", "15.55 ms | 0.03%", "+5.6% delay / +81% loss"),
        ("S3 (High)", "27.51 ms | 2.57%", "23.01 ms | 0.60%", "+16.4% delay / +76% loss"),
        ("S4 (Degr)", "44.38 ms | 13.7%", "17.13 ms | 0.20%", "+61.4% delay / +98% loss"),
    ]
    for row_idx, row_data in enumerate(data, start=1):
        for col_idx, val in enumerate(row_data):
            cell = tbl.cell(row_idx, col_idx)
            cell.text = val
            cell.text_frame.paragraphs[0].font.size = Pt(10)

    # Bullet summary below table
    rcard = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(4.9), Inches(5.7), Inches(1.9))
    rcard.fill.solid()
    rcard.fill.fore_color.rgb = LIGHT_BLUE
    rcard.line.color.rgb = BORDER_COLOR
    rtf = rcard.text_frame
    rtf.margin_left = Inches(0.2)
    rtf.margin_top = Inches(0.15)
    rp0 = rtf.paragraphs[0]
    rp0.text = "Key Findings:"
    rp0.font.bold = True
    rp0.font.size = Pt(12)
    rp0.font.color.rgb = DARK_BLUE
    for b in [
        "In S3: 95th-pct delay drops 37.2% (71ms -> 44ms), jitter drops 44.1%.",
        "In S4: Baseline stuck at 135ms during degradation; DAPS switches to P2/P3 in 2-4s.",
        "Overhead: Only 0.15% extra byte overhead (1800 probes / 300s run)."
    ]:
        p = rtf.add_paragraph()
        p.text = "• " + b
        p.font.size = Pt(10.5)

    # ==================== SLIDE 8: Time-Series Dynamics ====================
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "Time-Series Dynamics: S3 (High Load) & S4 (Degradation)")

    if os.path.exists("figures/fig_timeseries.png"):
        s8.shapes.add_picture("figures/fig_timeseries.png", Inches(0.8), Inches(1.4), width=Inches(7.2))

    add_card(s8, 8.3, 1.45, 4.2, 5.3, "Dynamic Trace Observations", [
        "Baseline Behavior (Orange):\nRemains pinned to P1 throughout the 300s run. In S3, background bursts create severe latency spikes up to 93 ms.",
        "DAPS Adaptation (Blue):\nContinuously probes alternate paths. Whenever R1-R2 or R3-R4 experiences a burst, traffic smoothly migrates.",
        "S4 Capacity Drop (t = 100-200s):\nR1-R2 loses 60% bandwidth. Baseline delay explodes to 135 ms and drops 42% packets.\nDAPS bypasses the bottleneck at t = 98s, maintaining delay at 18 ms.",
        "Path Switches (Vertical Dashes):\nControlled switches without endless oscillation."
    ])

    # ==================== SLIDE 9: Ablation & Sensitivity ====================
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "Ablation Study & Parameter Sensitivity")

    if os.path.exists("figures/fig_sensitivity.png"):
        s9.shapes.add_picture("figures/fig_sensitivity.png", Inches(6.8), Inches(1.4), width=Inches(5.8))

    add_card(s9, 0.8, 1.45, 5.7, 5.3, "Ablation: Why Anti-Flapping Matters", [
        "What drives performance?\nWe tested 6 variants in S3 (removing one stability feature at a time):",
        "• Full DAPS (Default): 23.01 ms delay, 25.8 path switches.",
        "• No Hysteresis (h=0) & No Hold-down (N=1):\n  Delay is 22.19 ms, but path switches jump from 25.8 to 72.0 per run!",
        "• The Trade-off:\n  DAPS sacrifices just 3.6% delay in exchange for cutting path switches by 64% (25.8 vs 72.0), preventing out-of-order packet delivery in TCP.",
        "• Probe Interval Sensitivity:\n  1s probe = 19.4% gain (higher overhead)\n  2s probe = 16.4% gain (optimal sweet spot)\n  >=10s probe = Negative gain (-2.5% to -5.2%)."
    ])

    # ==================== SLIDE 10: Failure Modes & Critical Evaluation ====================
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "Critical Evaluation: When Does DAPS Fail?")

    if os.path.exists("figures/fig_failure.png"):
        s10.shapes.add_picture("figures/fig_failure.png", Inches(6.8), Inches(1.4), width=Inches(5.8))

    add_card(s10, 0.8, 1.45, 5.7, 5.3, "Failure Conditions Identified", [
        "1. Slow Probing (>= 10s interval):\n   Background bursts have a mean duration of 12s. If probing is >=10s, measurement data is stale and DAPS moves into existing congestion.",
        "2. Self-Induced Congestion (Heavy Flows >= 4 Mbps):\n   Moving a large flow (4-6 Mbps) carries its own load to the destination path. Probes measured an empty path, so the flow immediately congests the new path, causing severe bouncing (-25.5% at 6 Mbps).",
        "3. Low Load Scenarios (S1):\n   Nothing to gain. Probing noise triggers ~3 needless switches to paths with higher propagation delay (-0.6% penalty).",
        "Honest Evaluation: Real engineering requires knowing where an algorithm breaks."
    ], RGBColor(255, 235, 235))

    # ==================== SLIDE 11: Team Division & Viva Guide ====================
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, "Team Contributions & Viva Presentation Split")

    add_card(s11, 0.8, 1.45, 5.6, 5.3, "Abhik Boxi (24BCE0741)", [
        "Modules Owned:\n• netmodel.py (Topology, M/M/1/K queue math, background generator)\n• analyzer.py (Hop-by-hop delay breakdown & bottleneck finder)\n• simulate.py (Discrete 1s simulation loop & metric collector)",
        "Viva Focus Topics:\n• Derivation of M/M/1/K queueing formula & handling rho >= 1\n• 4 physical delay components (prop, tx, proc, queue)\n• Bottleneck hop percentage calculation\n• Background traffic generation (sine wave + burst model)"
    ])

    add_card(s11, 6.9, 1.45, 5.6, 5.3, "Siddharth Saini (24BKT0121)", [
        "Modules Owned:\n• routing.py (Baseline Dijkstra & DAPS class implementation)\n• experiments.py (30-run statistical framework, ablation, sensitivity)\n• figures.py & main.py (All plotting functions & CLI interface)",
        "Viva Focus Topics:\n• DAPS active probing, EWMA smoothing (alpha = 0.3)\n• Anti-flapping logic: Hysteresis (10%) and Hold-down (N=2)\n• Student's t-test statistical validation\n• Honest failure modes: Stale probing & self-induced congestion"
    ], RGBColor(240, 248, 255))

    # ==================== SLIDE 12: Conclusion & Future Work ====================
    s12 = prs.slides.add_slide(blank_layout)
    add_header(s12, "Conclusion & Future Work")

    add_card(s12, 0.8, 1.45, 5.6, 5.3, "Summary of Work Done", [
        "Delivered a complete, reproducible Network Path and Delay Analyzer in Python.",
        "Demonstrated that DAPS reduces mean delay by 16.4%, 95th-percentile delay by 37.2%, and packet loss by 76.7% in high-load networks.",
        "Demonstrated 61.4% delay reduction during link capacity degradation events.",
        "Proved that hysteresis and hold-down effectively eliminate path flapping (reducing switches by 64%).",
        "Conducted thorough sensitivity, grid, and failure-boundary analyses."
    ], RGBColor(235, 245, 235))

    add_card(s12, 6.9, 1.45, 5.6, 5.3, "Limitations & Future Roadmap", [
        "1. Real Testbed Implementation:\n   Deploy over Mininet with Open vSwitch (OVS) and Linux Traffic Control (tc netem).",
        "2. Multi-Flow & TCP Evaluation:\n   Assess interaction between DAPS path switches and TCP cubic congestion window / out-of-order packet handling.",
        "3. Distributed Multi-Host DAPS:\n   Explore game-theoretic coordinator or randomization to prevent multiple hosts from synchronizing and simultaneously stampeding onto the same uncongested path."
    ], RGBColor(245, 245, 245))

    prs.save(filename)
    print(f"Presentation successfully created at: {filename}")

if __name__ == "__main__":
    create_deck()
