#!/usr/bin/env python3
"""
FPL Live Data Tool
==================
Pulls real, current data from the OFFICIAL Fantasy Premier League API
(free, no API key needed) and prints the analysis that actually helps you
pick a team: best value players, in-form players, differentials, and the
easiest upcoming fixtures.

Data source: https://fantasy.premierleague.com/api/  (unofficial but stable)

Requires: Python 3.8+ only. No pip installs, no API key.

USAGE
-----
    python3 fpl_data.py                 # full report (all sections)
    python3 fpl_data.py --value         # best points-per-million only
    python3 fpl_data.py --form          # hottest form only
    python3 fpl_data.py --diff          # differentials (low ownership)
    python3 fpl_data.py --fixtures      # fixture difficulty, next 5 GWs
    python3 fpl_data.py --pos MID       # filter to a position (GK/DEF/MID/FWD)
    python3 fpl_data.py --max-price 8.0 # only players at/below this price
    python3 fpl_data.py --top 30        # show top N rows (default 20)
    python3 fpl_data.py --csv out.csv   # also dump every player to CSV
    python3 fpl_data.py --json          # save raw API data to fpl_raw.json
"""

import argparse
import csv
import json
import sys
import urllib.request
import urllib.error

API = "https://fantasy.premierleague.com/api"
POS_MAP = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
DIFF_COLORS = {1: "●●", 2: "● ", 3: "  ", 4: " ▲", 5: "▲▲"}  # visual difficulty hint


def fetch(path):
    """GET a JSON endpoint from the FPL API with a browser-like User-Agent."""
    url = f"{API}/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FPL-tool)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP error {e.code} fetching {url} — the API may be busy, try again.")
    except urllib.error.URLError as e:
        sys.exit(f"Network error fetching {url}: {e.reason}\n"
                 f"Check your internet connection. (This uses the official free FPL API.)")


def load_data(save_json=False):
    print("Fetching live data from the official FPL API...", file=sys.stderr)
    boot = fetch("bootstrap-static/")
    fixtures = fetch("fixtures/")
    if save_json:
        with open("fpl_raw.json", "w") as f:
            json.dump({"bootstrap": boot, "fixtures": fixtures}, f)
        print("Saved raw data to fpl_raw.json", file=sys.stderr)
    return boot, fixtures


def build_players(boot):
    teams = {t["id"]: t["short_name"] for t in boot["teams"]}
    players = []
    for e in boot["elements"]:
        price = e["now_cost"] / 10.0
        pts = e["total_points"]
        players.append({
            "id": e["id"],
            "name": e["web_name"],
            "team_id": e["team"],
            "team": teams.get(e["team"], "?"),
            "pos": POS_MAP.get(e["element_type"], "?"),
            "price": price,
            "points": pts,
            "form": float(e["form"] or 0),
            "ppm": round(pts / price, 2) if price else 0,          # points per million
            "owned": float(e["selected_by_percent"] or 0),          # ownership %
            "minutes": e["minutes"],
            "goals": e["goals_scored"],
            "assists": e["assists"],
            "status": e["status"],   # a=available, i=injured, d=doubt, s=suspended, u=unavailable
        })
    return players, teams


def current_gw(boot):
    for ev in boot["events"]:
        if ev.get("is_current"):
            return ev["id"]
    for ev in boot["events"]:
        if ev.get("is_next"):
            return ev["id"]
    return 1


STATUS_FLAG = {"a": "", "d": " (doubt)", "i": " (injured)", "s": " (susp)", "u": " (out)", "n": " (n/a)"}


def filt(players, pos=None, max_price=None, min_minutes=90, available_only=True):
    out = []
    for p in players:
        if pos and p["pos"] != pos:
            continue
        if max_price and p["price"] > max_price:
            continue
        if p["minutes"] < min_minutes:
            continue
        if available_only and p["status"] != "a":
            continue
        out.append(p)
    return out


def print_table(title, rows, cols, top):
    print(f"\n{'=' * 74}\n {title}\n{'=' * 74}")
    if not rows:
        print(" (no players match your filters)")
        return
    headers = [c[0] for c in cols]
    widths = [c[1] for c in cols]
    line = "".join(h.ljust(w) for h, w in zip(headers, widths))
    print(line)
    print("-" * len(line))
    for p in rows[:top]:
        cells = [c[2](p) for c in cols]
        print("".join(str(v).ljust(w) for v, w in zip(cells, widths)))


def report_value(players, pos, max_price, top):
    rows = sorted(filt(players, pos, max_price), key=lambda p: p["ppm"], reverse=True)
    cols = [
        ("Player", 16, lambda p: p["name"][:15] + STATUS_FLAG.get(p["status"], "")),
        ("Team", 6, lambda p: p["team"]),
        ("Pos", 5, lambda p: p["pos"]),
        ("£m", 7, lambda p: f"{p['price']:.1f}"),
        ("Pts", 6, lambda p: p["points"]),
        ("Pts/£m", 8, lambda p: p["ppm"]),
        ("Own%", 7, lambda p: p["owned"]),
    ]
    print_table("BEST VALUE  —  points per million (find your cheap enablers here)", rows, cols, top)


def report_form(players, pos, max_price, top):
    rows = sorted(filt(players, pos, max_price), key=lambda p: p["form"], reverse=True)
    cols = [
        ("Player", 16, lambda p: p["name"][:15] + STATUS_FLAG.get(p["status"], "")),
        ("Team", 6, lambda p: p["team"]),
        ("Pos", 5, lambda p: p["pos"]),
        ("£m", 7, lambda p: f"{p['price']:.1f}"),
        ("Form", 7, lambda p: p["form"]),
        ("Pts", 6, lambda p: p["points"]),
        ("Own%", 7, lambda p: p["owned"]),
    ]
    print_table("HOTTEST FORM  —  avg points over recent games (buy the run)", rows, cols, top)


def report_diff(players, pos, max_price, top):
    # Differential: good form/points but low ownership
    pool = [p for p in filt(players, pos, max_price) if p["owned"] < 10 and p["points"] > 0]
    rows = sorted(pool, key=lambda p: (p["form"], p["points"]), reverse=True)
    cols = [
        ("Player", 16, lambda p: p["name"][:15] + STATUS_FLAG.get(p["status"], "")),
        ("Team", 6, lambda p: p["team"]),
        ("Pos", 5, lambda p: p["pos"]),
        ("£m", 7, lambda p: f"{p['price']:.1f}"),
        ("Form", 7, lambda p: p["form"]),
        ("Pts", 6, lambda p: p["points"]),
        ("Own%", 7, lambda p: p["owned"]),
    ]
    print_table("DIFFERENTIALS  —  in form but owned by <10% (climb the ranks)", rows, cols, top)


def report_fixtures(boot, fixtures, top):
    teams = {t["id"]: t["short_name"] for t in boot["teams"]}
    gw = current_gw(boot)
    horizon = 5
    upcoming = range(gw, gw + horizon)
    # team_id -> list of (opp_short, difficulty) for the next `horizon` GWs
    per_team = {tid: [] for tid in teams}
    for fx in fixtures:
        if fx["event"] is None or fx["event"] not in upcoming:
            continue
        h, a = fx["team_h"], fx["team_a"]
        per_team.setdefault(h, []).append((teams.get(a, "?") + " (H)", fx["team_h_difficulty"]))
        per_team.setdefault(a, []).append((teams.get(h, "?") + " (A)", fx["team_a_difficulty"]))
    # rank by average difficulty (lower = easier)
    ranked = []
    for tid, games in per_team.items():
        if not games:
            continue
        avg = sum(d for _, d in games) / len(games)
        ranked.append((teams.get(tid, "?"), avg, games))
    ranked.sort(key=lambda x: x[1])

    print(f"\n{'=' * 74}\n EASIEST FIXTURES  —  next {horizon} GWs (from GW{gw}). Lower avg = easier.\n{'=' * 74}")
    print(" ●=easy  ▲=hard  |  target attackers from the top teams here")
    print("-" * 74)
    print("Team   Avg   " + f"Next {horizon} opponents (difficulty 1-5)")
    print("-" * 74)
    for name, avg, games in ranked[:top]:
        seq = "  ".join(f"{opp}[{d}]" for opp, d in games)
        print(f"{name:<6} {avg:>4.1f}  {seq}")


def dump_csv(players, path):
    keys = ["name", "team", "pos", "price", "points", "form", "ppm", "owned",
            "minutes", "goals", "assists", "status"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for p in sorted(players, key=lambda p: p["points"], reverse=True):
            w.writerow(p)
    print(f"\nWrote {len(players)} players to {path}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="Live FPL data from the official free API.")
    ap.add_argument("--value", action="store_true", help="best points-per-million")
    ap.add_argument("--form", action="store_true", help="hottest form")
    ap.add_argument("--diff", action="store_true", help="differentials (<10%% owned)")
    ap.add_argument("--fixtures", action="store_true", help="easiest upcoming fixtures")
    ap.add_argument("--pos", choices=["GK", "DEF", "MID", "FWD"], help="filter position")
    ap.add_argument("--max-price", type=float, help="max price in £m")
    ap.add_argument("--top", type=int, default=20, help="rows to show (default 20)")
    ap.add_argument("--csv", metavar="FILE", help="dump all players to CSV")
    ap.add_argument("--json", action="store_true", help="save raw API data to fpl_raw.json")
    args = ap.parse_args()

    boot, fixtures = load_data(save_json=args.json)
    players, _ = build_players(boot)

    show_all = not (args.value or args.form or args.diff or args.fixtures)

    gw = current_gw(boot)
    print(f"\n⚽ FPL LIVE DATA  |  Gameweek {gw}  |  {len(players)} players loaded")
    if args.pos or args.max_price:
        bits = []
        if args.pos:
            bits.append(f"position={args.pos}")
        if args.max_price:
            bits.append(f"max £{args.max_price:.1f}m")
        print("   Filters: " + ", ".join(bits))

    if show_all or args.value:
        report_value(players, args.pos, args.max_price, args.top)
    if show_all or args.form:
        report_form(players, args.pos, args.max_price, args.top)
    if show_all or args.diff:
        report_diff(players, args.pos, args.max_price, args.top)
    if show_all or args.fixtures:
        report_fixtures(boot, fixtures, args.top)

    if args.csv:
        dump_csv(players, args.csv)

    print("\nTip: pair the BEST VALUE list with the EASIEST FIXTURES list —")
    print("cheap players from teams with a green run are where seasons are won.\n")


if __name__ == "__main__":
    main()
