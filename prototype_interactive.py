"""prototype_interactive.py - Standalone Interactive Terminal Working Prototype.

Run with:
    python prototype_interactive.py

Keyboard Controls during execution:
    [1] Toggle Mode (Static OSPF vs Adaptive DAPS)
    [2] Inject Congestion Burst on R1-R2 (125% load)
    [3] Trigger 60% Capacity Loss on R1-R2
    [4] Clear Events (Restore Normal Load)
    [q] Quit Prototype
"""
import os
import sys
import time
import math
if sys.platform == "win32":
    import msvcrt
else:
    msvcrt = None

from netmodel import LINKS, build_graph, link_state, Background
from routing import candidate_paths, path_links, DAPS
from simulate import FG_RATE, SCENARIOS


def clear_screen():
    print("\033[H\033[J", end="")


def main():
    os.system("") # Enable ANSI colors in Windows CMD/PowerShell
    g = build_graph()
    paths = candidate_paths(g, k=3)
    p_names = {0: "P1 (S-R1-R2-D)", 1: "P2 (S-R3-R4-D)", 2: "P3 (S-R1-R5-R4-D)"}

    # Initial state
    mode = "proposed" # 'baseline' | 'proposed'
    burst_active = False
    degrade_active = False
    active_path_idx = 0
    switches = 0
    delivered = 0
    dropped = 0
    sim_second = 0

    # DAPS instance
    daps = DAPS(g, k=3, alpha=0.3, probe_interval=2, hysteresis=0.10, confirm=2)

    bg = Background(seed=1, load=1.0, T=300)

    print("Initializing interactive prototype...")
    time.sleep(0.5)

    try:
        while True:
            sim_second += 1

            # Check keyboard input (non-blocking)
            if sys.platform == "win32" and msvcrt.kbhit():
                ch = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                if ch == '1':
                    mode = "baseline" if mode == "proposed" else "proposed"
                    if mode == "baseline":
                        active_path_idx = 0
                elif ch == '2':
                    burst_active = not burst_active
                elif ch == '3':
                    degrade_active = not degrade_active
                elif ch == '4':
                    burst_active = False
                    degrade_active = False
                elif ch == 'q':
                    print("\nExiting prototype.")
                    break

            # Calculate current link conditions
            cur_links = path_links(g, paths[active_path_idx])
            st = link_state(bg, sim_second % 300, cur_links, FG_RATE)

            # Apply user interactive bursts
            r1_r2_idx = g["R1"]["R2"]["idx"]
            if degrade_active:
                st["rho"][r1_r2_idx] = 1.45
                st["queue"][r1_r2_idx] = 125.0
                st["total"][r1_r2_idx] = 133.0
                st["loss"][r1_r2_idx] = 0.42
            elif burst_active:
                st["rho"][r1_r2_idx] = 1.20
                st["queue"][r1_r2_idx] = 110.0
                st["total"][r1_r2_idx] = 118.0
                st["loss"][r1_r2_idx] = 0.32

            # DAPS Probing Cycle (Every 2 seconds)
            if mode == "proposed" and sim_second % daps.interval == 0:
                # Mock probe
                old_cur = daps.cur
                d_scores = []
                for p_idx, p in enumerate(paths):
                    p_lks = path_links(g, p)
                    delay = sum(st["total"][l] for l in p_lks)
                    d_scores.append(delay)
                daps.D = daps.alpha * sum(d_scores) if daps.D is None else daps.D
                
                # Check candidate best
                best_idx = int(min(range(len(d_scores)), key=lambda i: d_scores[i]))
                if best_idx != daps.cur and d_scores[best_idx] < 0.90 * d_scores[daps.cur]:
                    if daps.pending_target == best_idx:
                        daps.pending += 1
                    else:
                        daps.pending_target, daps.pending = best_idx, 1

                    if daps.pending >= daps.confirm:
                        daps.cur = best_idx
                        daps.switches += 1
                        switches += 1
                        active_path_idx = best_idx
                        daps.pending_target, daps.pending = None, 0
                else:
                    daps.pending_target, daps.pending = None, 0
            elif mode == "baseline":
                active_path_idx = 0

            # Current active path total delay
            cur_p_lks = path_links(g, paths[active_path_idx])
            cur_delay = sum(st["total"][l] for l in cur_p_lks)
            loss_prob = max(st["loss"][l] for l in cur_p_lks)
            delivered += int(20 * (1 - loss_prob))
            dropped += int(20 * loss_prob)

            # Render Console Dashboard
            clear_screen()
            print("=" * 72)
            print("  NETWORK PATH AND DELAY ANALYZER - INTERACTIVE PROTOTYPE")
            print("=" * 72)
            print(f" Sim Second: {sim_second:03d}s  |  Foreground Flow: S -> D (2 Mbps)")
            
            # Mode Indicator
            if mode == "proposed":
                print(" Mode: \033[96m[ PROPOSED DAPS (Delay-Aware Adaptive) ]\033[0m  (Key [1] to toggle)")
            else:
                print(" Mode: \033[93m[ BASELINE OSPF (Static Dijkstra)      ]\033[0m  (Key [1] to toggle)")

            # Event status
            events = []
            if burst_active:
                events.append("\033[91mBURST ON R1-R2\033[0m")
            if degrade_active:
                events.append("\033[91mR1-R2 60% DEGRADED\033[0m")
            if not events:
                events.append("\033[92mNominal Traffic\033[0m")
            print(f" Traffic Event Status: {' | '.join(events)}")
            print("-" * 72)

            # Active Route & Delay Gauge
            delay_color = "\033[92m" if cur_delay < 30 else ("\033[93m" if cur_delay < 70 else "\033[91m")
            print(f" Active Path:    \033[1m{p_names[active_path_idx]}\033[0m")
            print(f" End-to-End Latency: {delay_color}{cur_delay:6.2f} ms\033[0m  (Loss: {loss_prob * 100:4.1f}%)")
            
            # ASCII Bar graph of latency
            bar_len = min(int(cur_delay / 3), 40)
            bar = "█" * bar_len
            print(f" Latency Meter:  [{delay_color}{bar:<40}\033[0m]")
            print("-" * 72)

            # Candidate Paths Status Table
            print(f"{'Path':<6}{'Route':<24}{'Status':<16}{'Est. Latency':>14}")
            for i, p in enumerate(paths):
                p_lks = path_links(g, p)
                lat = sum(st["total"][l] for l in p_lks)
                role = "ACTIVE FLOW" if i == active_path_idx else ("PENDING (1/2)" if mode == "proposed" and daps.pending_target == i else "STANDBY")
                color = "\033[96m" if i == active_path_idx else "\033[90m"
                print(f"{color}P{i+1:<5}{' -> '.join(p):<24}{role:<16}{lat:>11.2f} ms\033[0m")

            print("-" * 72)
            print(f" Statistics: Delivered: {delivered:,} pkts | Dropped: {dropped:,} pkts | Switches: {switches}")
            print("-" * 72)
            print(" Interactive Actions:")
            print("   Press [1] Toggle Mode (Baseline OSPF vs DAPS Adaptive)")
            print("   Press [2] Inject Congestion Burst on R1-R2")
            print("   Press [3] Trigger 60% Capacity Loss on R1-R2")
            print("   Press [4] Clear Traffic Events (Restore Normal)")
            print("   Press [q] Quit Prototype")
            print("=" * 72)

            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nPrototype stopped.")


if __name__ == "__main__":
    main()
