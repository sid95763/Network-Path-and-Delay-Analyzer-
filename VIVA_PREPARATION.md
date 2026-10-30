# Oral Examination & Viva Preparation Guide
## Network Path and Delay Analyzer (BCSE308P - Computer Networks Lab)

This guide provides the exact division of responsibilities, key technical explanations, and anticipated viva questions with model answers based directly on the project source code and final report.

---

## 1. Team Division & Presentation Strategy

| Team Member | Reg. No. | Modules Owned | Primary Viva Focus |
|---|---|---|---|
| **Abhik Boxi** | **24BCE0741** | • `netmodel.py`<br>• `analyzer.py`<br>• `simulate.py` | • $M/M/1/K$ queueing derivation & finite buffer handling.<br>• 4-component delay breakdown ($d_{\text{prop}} + d_{\text{tx}} + d_{\text{proc}} + d_{\text{queue}}$).<br>• Bottleneck hop identification & share calculation.<br>• Background traffic generator (sine wave + burst model). |
| **Siddharth Saini** | **24BKT0121** | • `routing.py`<br>• `experiments.py`<br>• `figures.py`<br>• `main.py` | • Baseline OSPF Dijkstra vs DAPS architecture.<br>• Active probing, EWMA smoothing, composite scoring.<br>• Anti-flapping mechanisms: Hysteresis & hold-down counter.<br>• 30-run statistical tests, ablation, and failure conditions. |

---

## 2. Top 15 Viva Questions & Model Answers

### Q1: Why did you model links as $M/M/1/K$ queues instead of standard $M/M/1$?
**Answer:**
> In the classic $M/M/1$ queue, average delay is given by $W = \frac{1}{\mu(1 - \rho)}$. When load bursts cause arrival rate $\lambda \ge \mu$ ($\rho \ge 1$), the denominator becomes zero or negative, predicting infinite queueing delay. 
> Real network routers have finite hardware buffers. We used an $M/M/1/K$ model ($K = 64$ packets) because:
> 1. It naturally keeps queueing delay bounded during burst periods ($\rho > 1$).
> 2. It directly computes packet loss probability ($P_K$), which standard $M/M/1$ cannot do.

### Q2: How does the code handle the numerical singularity when $\rho = 1.0$?
**Answer:**
> In the $M/M/1/K$ formula, the terms $(1 - \rho)$ and $(1 - \rho^{K+1})$ produce a $\frac{0}{0}$ indeterminate form when $\rho = 1.0$ exactly. In `netmodel.py`, line 50:
> ```python
> rho = np.where(np.abs(rho - 1.0) < 1e-6, 1.0 + 1e-6, rho)
> ```
> By nudging $\rho$ by $10^{-6}$ when it is within $10^{-6}$ of $1.0$, the code removes the singularity without altering physical accuracy.

### Q3: How do you guarantee a completely fair comparison between Baseline and DAPS?
**Answer:**
> Both schemes are subjected to **identical paired random conditions**:
> 1. In `simulate.py`, link background traffic is generated using a fixed seed (`seed`), meaning link utilization traces over all 300 seconds are bit-for-bit identical for both Baseline and DAPS.
> 2. Packet sampling randomness uses a separate pseudo-random generator stream (`10_000 + seed`).
> 3. We ran 30 paired runs across all 4 scenarios and evaluated differences using paired Student's $t$-tests ($p < 0.001$).

### Q4: Explain the 4 components of hop delay and how they are computed.
**Answer:**
> For each link hop:
> 1. **Propagation Delay ($d_{\text{prop}}$):** Time for signal to travel the physical medium; fixed parameter ($2\text{--}8\text{ ms}$).
> 2. **Transmission Delay ($d_{\text{tx}}$):** Time to push packet bits onto wire; $\frac{\text{packet size (8000 bits)}}{\text{bandwidth (bps)}}$.
> 3. **Processing Delay ($d_{\text{proc}}$):** Router header inspection latency; fixed at $0.1\text{ ms}$.
> 4. **Queueing Delay ($d_{\text{queue}}$):** Waiting time in buffer; computed as $W - \frac{1}{\mu}$, where $W$ is mean system time from the $M/M/1/K$ model.

### Q5: How does the Delay Analyzer determine the "bottleneck hop"?
**Answer:**
> In `analyzer.py`, the analyzer scans every hop in the path and identifies the link with the maximum queueing delay:
> $$\text{worst} = \max(\text{rows}, \text{key} = \lambda r: r[\text{"queue"}])$$
> It then computes its percentage share: $\text{Share}\% = 100 \times \frac{\text{worst queueing delay}}{\text{total end-to-end delay}}$. For example, in Scenario S4, link $R1\text{-}R2$ accounts for $123.27\text{ ms}$ queueing, which is $90\%$ of total path latency.

### Q6: Why doesn't OSPF avoid congested paths?
**Answer:**
> OSPF uses static administrative link costs, typically inversely proportional to link bandwidth ($\text{cost} = \frac{100}{\text{bandwidth}}$). These weights are configured statically and computed via Dijkstra's algorithm. Because OSPF routers do not track real-time queue lengths or delay, traffic stays pinned to the static shortest path ($P1$) even when background traffic pushes link utilization above $100\%$.

### Q7: What is the probe overhead of DAPS? Does it congest the network?
**Answer:**
> No. DAPS sends 4 small probe packets ($64\text{ bytes} = 512\text{ bits}$) on each of the 3 candidate paths every 2 seconds:
> $$\text{Probe Rate} = \frac{3 \times 4 \times 512\text{ bits}}{2\text{ s}} = 3.072\text{ kbps}$$
> Over a 300 s simulation run, only 1,800 probe packets are transmitted. This represents just **$0.15\%$** of the foreground flow's volume ($2\text{ Mbps}$), which is negligible.

### Q8: What happens if all probe packets on a path are dropped?
**Answer:**
> If all 4 probes are lost on a path, sample delay cannot be computed. In `routing.py` (line 59), DAPS assigns a **penalty delay of $400\text{ ms}$**. Because $400\text{ ms}$ is much higher than normal path latency ($10\text{--}30\text{ ms}$), the composite score skyrockets and DAPS immediately steers traffic away from that path.

### Q9: Why is EWMA smoothing necessary in DAPS?
**Answer:**
> Network traffic is noisy. If path decisions were made using raw instantaneous probe samples, a single transient delay spike or a single dropped probe would trigger unnecessary path changes. 
> By applying EWMA ($\alpha = 0.3$), the current sample contributes $30\%$ and historical performance contributes $70\%$, providing robust noise filtering similar to TCP RTT estimation.

### Q10: Why is $w_L = 1000$ in the composite score?
**Answer:**
> The composite score is $S = D + w_J \cdot J + w_L \cdot L$. 
> Delay ($D$) and jitter ($J$) are in milliseconds ($10\text{--}50\text{ ms}$), whereas packet loss ratio ($L$) is a fraction ($0.00\text{--}0.15$). 
> Setting $w_L = 1000$ scales the loss fraction so that a $1\%$ loss ($L = 0.01$) adds $10\text{ ms}$ to the score, prioritizing loss avoidance for reliable transport.

### Q11: Explain the Anti-Flapping mechanism (Hysteresis & Hold-Down).
**Answer:**
> Path flapping (frequent bouncing between paths) causes packet reordering and degrades TCP performance. DAPS suppresses flapping with two mechanisms:
> 1. **Hysteresis ($h = 0.10$):** An alternate path must be at least $10\%$ better than the current path before switching is considered ($\text{Score}_{\text{new}} < 0.90 \times \text{Score}_{\text{current}}$).
> 2. **Hold-Down Counter ($N = 2$):** Even if the alternate path is $10\%$ better, it must sustain that advantage for **two consecutive probe rounds** ($4\text{ seconds}$) before traffic is migrated.

### Q12: In the ablation study, removing hysteresis and hold-down lowered delay to $22.19\text{ ms}$ (vs $23.01\text{ ms}$). Why did you keep them?
**Answer:**
> Without hysteresis and hold-down, path switches surged from **$25.8$ to $72.0$ per run** (a $179\%$ increase). In real IP networks, each route change causes out-of-order packet delivery, triggering duplicate TCP ACKs and false retransmissions. 
> Trading $3.6\%$ mean delay to cut route oscillations by $64\%$ is an essential engineering design choice.

### Q13: Why did DAPS perform slightly worse ($-0.6\%$) in Scenario S1?
**Answer:**
> In S1 (low load, factor $0.5$), links are nearly empty ($\rho \approx 0.15\text{--}0.23$) and queueing delay is negligible. Total latency is dominated by physical propagation delay.
> Baseline path $P1$ has the lowest propagation delay ($10\text{ ms}$ vs $12\text{ ms}$ for $P2$ and $14\text{ ms}$ for $P3$). In S1, small random noise in probe measurements occasionally surpassed the $10\%$ threshold, causing DAPS to switch ~3 times to paths with longer physical cables.

### Q14: What is "Self-Induced Congestion" (Failure Condition)?
**Answer:**
> When the monitored flow is small ($2\text{ Mbps}$), moving it to another path has minimal impact on that path's queues.
> However, if the flow is large ($\ge 4\text{--}6\text{ Mbps}$), moving it carries a large traffic burden. Probes measured an empty alternative path, but the moment the heavy flow moves there, it **creates its own congestion**. The alternative path immediately degrades, forcing DAPS to bounce back. In tests with a $6\text{ Mbps}$ flow, DAPS performed **$25.5\%$ worse** than baseline with over 60 path switches.

### Q15: What happens if the probe interval is too slow ($10\text{--}20\text{ s}$)?
**Answer:**
> Background traffic bursts have a mean lifespan of $12\text{ seconds}$. 
> If DAPS probes every $10\text{ s}$ or $20\text{ s}$, probe data becomes stale. By the time DAPS decides to switch, the burst on the original path may have already ended, or a new burst may have started on the alternative path. In our sensitivity sweep, $10\text{ s}$ probing produced a **$-2.5\%$** degradation and $20\text{ s}$ produced **$-5.2\%$**.

---

## 3. Live Demonstration Cheat Sheet for Viva

Run these commands during the evaluation:

```powershell
# 1. Compare Baseline vs Proposed on Scenario S3 (High Load):
python main.py demo --scenario S3 --seed 1

# 2. Show live parameter tuning (faster 1s probing, 20% hysteresis):
python main.py demo --scenario S3 --probe-interval 1 --hysteresis 0.20

# 3. Show Hop-by-Hop Bottleneck Analysis for Scenario S4 at t=150s:
python main.py analyze --scenario S4 --seed 3 --at 150

# 4. Run the automated unit test suite to prove code correctness:
python -m unittest test_pda.py
```
