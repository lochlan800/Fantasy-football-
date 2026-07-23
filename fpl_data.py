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


def compute_fixture_ranking(boot, fixtures, horizon=5):
    """Rank all teams by average fixture difficulty over the next `horizon` GWs.

    Returns (gw, horizon, ranked) where ranked is a list of dicts sorted from
    easiest to hardest run:
        {short, name, avg, games:[{opp, venue, diff}, ...]}
    The difficulty numbers are the OFFICIAL FPL fixture difficulty ratings
    (1 = easiest, 5 = hardest) — the same ones shown in the app.
    """
    short = {t["id"]: t["short_name"] for t in boot["teams"]}
    full = {t["id"]: t["name"] for t in boot["teams"]}
    gw = current_gw(boot)
    upcoming = range(gw, gw + horizon)
    per_team = {tid: [] for tid in short}
    for fx in fixtures:
        if fx["event"] is None or fx["event"] not in upcoming:
            continue
        h, a = fx["team_h"], fx["team_a"]
        per_team.setdefault(h, []).append(
            {"opp": short.get(a, "?"), "venue": "H", "diff": fx["team_h_difficulty"]})
        per_team.setdefault(a, []).append(
            {"opp": short.get(h, "?"), "venue": "A", "diff": fx["team_a_difficulty"]})
    ranked = []
    for tid, games in per_team.items():
        if not games:
            continue
        avg = round(sum(g["diff"] for g in games) / len(games), 2)
        ranked.append({"short": short.get(tid, "?"), "name": full.get(tid, "?"),
                       "avg": avg, "games": games})
    ranked.sort(key=lambda x: x["avg"])
    return gw, horizon, ranked


def report_fixtures(boot, fixtures, top):
    gw, horizon, ranked = compute_fixture_ranking(boot, fixtures)
    print(f"\n{'=' * 74}\n EASIEST FIXTURES  —  next {horizon} GWs (from GW{gw}). Lower avg = easier.\n{'=' * 74}")
    print(" [1]=easiest  [5]=hardest  |  target attackers from the top teams here")
    print("-" * 74)
    print("Rank  Team   Avg   " + f"Next {horizon} opponents (difficulty 1-5)")
    print("-" * 74)
    for i, r in enumerate(ranked[:top], 1):
        seq = "  ".join(f"{g['opp']}({g['venue']})[{g['diff']}]" for g in r["games"])
        print(f"{i:>3}.  {r['short']:<6} {r['avg']:>4.1f}  {seq}")


def write_fixtures_outputs(boot, fixtures):
    """Write a self-contained colour-coded fixtures.html and a fixtures-data.json."""
    gw, horizon, ranked = compute_fixture_ranking(boot, fixtures)
    # JSON for the webpage tab
    with open("fixtures-data.json", "w") as f:
        json.dump({"gw": gw, "horizon": horizon, "ranked": ranked}, f, indent=2)

    diff_bg = {1: "#0e8a3e", 2: "#37d67a", 3: "#5a6472", 4: "#ff8a5c", 5: "#ff5c73"}
    diff_fg = {1: "#fff", 2: "#06210f", 3: "#fff", 4: "#3a1400", 5: "#3a0009"}

    def cell(g):
        d = g["diff"]
        return (f'<td style="background:{diff_bg.get(d,"#5a6472")};'
                f'color:{diff_fg.get(d,"#fff")};text-align:center;font-weight:600;'
                f'padding:8px 6px;border-radius:6px;white-space:nowrap">'
                f'{g["opp"]}<br><small>({g["venue"]}) {d}</small></td>')

    rows = ""
    for i, r in enumerate(ranked, 1):
        cells = "".join(cell(g) for g in r["games"])
        rows += (f'<tr><td style="text-align:center;color:#9198a1">{i}</td>'
                 f'<td style="font-weight:700">{r["short"]}</td>'
                 f'<td style="color:#9198a1;font-size:13px">{r["name"]}</td>'
                 f'<td style="text-align:center;font-weight:700">{r["avg"]:.1f}</td>'
                 f'{cells}</tr>')

    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FPL Fixture Difficulty Ranking</title>
<style>
 body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
   background:#0d1117;color:#e6edf3;margin:0;padding:24px}}
 h1{{font-size:24px;margin:0 0 4px}} p.sub{{color:#9198a1;margin:0 0 18px}}
 .wrap{{max-width:920px;margin:0 auto}}
 table{{width:100%;border-collapse:separate;border-spacing:5px}}
 th{{color:#9198a1;font-size:12px;text-transform:uppercase;letter-spacing:.4px;text-align:left;padding:6px}}
 td{{background:#161b22;padding:8px 10px;border-radius:6px}}
 .legend{{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0;font-size:13px;align-items:center}}
 .chip{{padding:3px 10px;border-radius:6px;font-weight:700}}
 .note{{color:#9198a1;font-size:13px;margin-top:18px}}
 .scroll{{overflow-x:auto}}
</style></head><body><div class="wrap">
<h1>⚽ Fixture Difficulty Ranking</h1>
<p class="sub">Next {horizon} gameweeks from GW{gw}. Teams sorted easiest run → hardest.
Official FPL difficulty ratings. Target attackers from the teams up top.</p>
<div class="legend"><span>Difficulty:</span>
 <span class="chip" style="background:#0e8a3e;color:#fff">1 easiest</span>
 <span class="chip" style="background:#37d67a;color:#06210f">2</span>
 <span class="chip" style="background:#5a6472;color:#fff">3</span>
 <span class="chip" style="background:#ff8a5c;color:#3a1400">4</span>
 <span class="chip" style="background:#ff5c73;color:#3a0009">5 hardest</span>
</div>
<div class="scroll"><table>
<thead><tr><th>#</th><th>Team</th><th>Full name</th><th>Avg</th>
<th colspan="{horizon}">Next {horizon} opponents</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p class="note">Generated by fpl_data.py from the official free FPL API.
Fixtures and difficulty change through the season — regenerate before each deadline.</p>
</div></body></html>"""
    with open("fixtures.html", "w") as f:
        f.write(html)
    print("Wrote fixtures.html (open it in your browser) and fixtures-data.json", file=sys.stderr)


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
    ap.add_argument("--html", action="store_true",
                    help="generate a colour-coded fixtures.html ranking page")
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

    if args.html:
        write_fixtures_outputs(boot, fixtures)

    if args.csv:
        dump_csv(players, args.csv)

    print("\nTip: pair the BEST VALUE list with the EASIEST FIXTURES list —")
    print("cheap players from teams with a green run are where seasons are won.\n")


if __name__ == "__main__":
    main()
