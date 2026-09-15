"""
Runs a batch of local Quoridor matches between two player files and reports
win/turn/time statistics.

Each round is launched as a separate `main_quoridor.py -t local -r` subprocess
(the same code path used for a real match), so timing and rule enforcement are
identical to an actual game. Colors are swapped every round so both players
spend an equal number of games as White and Black.

Usage:
    python run_match_stats.py player1.py player2.py number_of_rounds
    python run_match_stats.py player1.py player2.py number_of_rounds --no-alternate
    python run_match_stats.py player1.py player2.py number_of_rounds --timeout 2400
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN_SCRIPT = HERE / "main_quoridor.py"
PER_PLAYER_TIME_LIMIT = 15 * 60  # matches the constant hardcoded in main_quoridor.play()


def _label(player_path: str) -> str:
    return Path(player_path).stem


def _existing_recordings() -> set[str]:
    return set(glob.glob(str(HERE / "__REC__*.json")))


def _new_recording(before: set[str]) -> str | None:
    new = _existing_recordings() - before
    return new.pop() if new else None


def run_one_game(path_a: str, path_b: str, timeout: float, port: int) -> dict:
    """
    Plays one game with `path_a` as White and `path_b` as Black, via a fresh
    `main_quoridor.py -t local` subprocess. Returns a dict describing the
    outcome, keyed by the original file paths (not by color).

    Each call must use its own `port`: main_quoridor.py always binds a TCP
    socket for event broadcasting (even headless), so reusing a port before
    the OS has released it -- or colliding with another game already running
    -- makes the subprocess crash on bind().
    """
    before = _existing_recordings()
    cmd = [sys.executable, str(MAIN_SCRIPT), "-t", "local", "-g", "-r",
          "-p", str(port), path_a, path_b]

    start = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(HERE), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        stale = _new_recording(before)
        if stale:
            os.remove(HERE / stale)
        return {"status": "hung", "wall_time": time.time() - start}

    wall_time = time.time() - start
    record_path = _new_recording(before)
    if record_path is None:
        return {"status": "crashed", "wall_time": wall_time,
                "stderr": proc.stderr[-2000:]}

    with open(record_path) as f:
        data = json.load(f)
    os.remove(record_path)

    summary = data.get("final_summary")
    steps = data.get("steps") or []
    if summary is None or not steps:
        return {"status": "crashed", "wall_time": wall_time,
                "stderr": proc.stderr[-2000:]}

    # summary["players"][0] is always path_a (White), [1] is path_b (Black):
    # main_quoridor.py builds `players` in that fixed order regardless of outcome.
    id_to_path = {
        summary["players"][0]["id"]: path_a,
        summary["players"][1]["id"]: path_b,
    }
    last_step = steps[-1]
    remaining_time = {int(pid): t for pid, t in last_step.get("remaining_time", {}).items()}

    return {
        "status": summary.get("status", "unknown"),  # "done" (normal finish) or "cancelled" (disqualification)
        "turns": last_step.get("step", len(steps)),
        "winners": [id_to_path[wid] for wid in summary.get("winners_id", []) if wid in id_to_path],
        "time_used": {id_to_path[pid]: PER_PLAYER_TIME_LIMIT - t
                      for pid, t in remaining_time.items() if pid in id_to_path},
        "white": path_a,
        "black": path_b,
        "wall_time": wall_time,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("player1", help="Path to the first player's .py file")
    parser.add_argument("player2", help="Path to the second player's .py file")
    parser.add_argument("rounds", type=int, help="Number of games to play")
    parser.add_argument("--no-alternate", action="store_true",
                        help="Keep player1 as White for every round (default: swap colors each round)")
    parser.add_argument("--timeout", type=float, default=2 * PER_PLAYER_TIME_LIMIT + 120,
                        help="Per-game subprocess watchdog in seconds (default: enough for two full 15 min budgets)")
    parser.add_argument("--port-base", type=int, default=17000,
                        help="First port to use; each round gets its own (base + round index) "
                             "so it never collides with another game (default: 17000, since "
                             "main_quoridor.py's own default port 16001 may be in use elsewhere)")
    args = parser.parse_args()

    label_a, label_b = _label(args.player1), _label(args.player2)
    stats = {
        label_a: {"wins": 0, "time_used": [], "disqualified": 0},
        label_b: {"wins": 0, "time_used": [], "disqualified": 0},
    }
    game_lengths = []
    anomalies = []

    for i in range(args.rounds):
        swap = (not args.no_alternate) and (i % 2 == 1)
        path_a, path_b = (args.player2, args.player1) if swap else (args.player1, args.player2)
        label_of = {path_a: (label_b if swap else label_a), path_b: (label_a if swap else label_b)}

        print(f"[{i + 1}/{args.rounds}] {label_of[path_a]} (White) vs {label_of[path_b]} (Black) ...",
             flush=True)
        result = run_one_game(path_a, path_b, args.timeout, args.port_base + i)

        if result["status"] not in ("done", "cancelled"):
            print(f"    -> {result['status']} ({result.get('wall_time', 0):.1f}s)")
            anomalies.append({"round": i + 1, **result})
            continue

        for path, seconds in result["time_used"].items():
            stats[label_of[path]]["time_used"].append(seconds)
        game_lengths.append(result["turns"])

        winner_labels = [label_of[w] for w in result["winners"]]
        for lbl in winner_labels:
            stats[lbl]["wins"] += 1
        if result["status"] == "cancelled":
            loser_labels = [l for l in (label_a, label_b) if l not in winner_labels]
            for lbl in loser_labels:
                stats[lbl]["disqualified"] += 1

        tag = "DQ" if result["status"] == "cancelled" else "ok"
        print(f"    -> winner: {', '.join(winner_labels) or 'none'} "
             f"[{tag}, {result['turns']} turns, {result['wall_time']:.1f}s wall]")

    # --- Summary -----------------------------------------------------
    completed = args.rounds - len(anomalies)
    print("\n" + "=" * 60)
    print(f"Results over {completed}/{args.rounds} completed rounds "
         f"({label_a} vs {label_b})")
    if game_lengths:
        print(f"Average game length: {sum(game_lengths) / len(game_lengths):.1f} turns")
    print("=" * 60)

    for label in (label_a, label_b):
        s = stats[label]
        n = completed
        win_rate = s["wins"] / n * 100 if n else 0.0
        avg_time = sum(s["time_used"]) / len(s["time_used"]) if s["time_used"] else 0.0
        print(f"{label}:")
        print(f"    wins            : {s['wins']}/{n} ({win_rate:.1f}%)")
        print(f"    disqualified    : {s['disqualified']}")
        print(f"    avg time used   : {avg_time:.1f}s / {PER_PLAYER_TIME_LIMIT}s budget")

    if anomalies:
        print(f"\n{len(anomalies)} round(s) did not complete normally:")
        for a in anomalies:
            print(f"  round {a['round']}: {a['status']}"
                 + (f" -- {a['stderr'].strip().splitlines()[-1]}" if a.get("stderr") else ""))


if __name__ == "__main__":
    main()
