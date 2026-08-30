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
import datetime
import json
import math
import re
import sys
import urllib.request
import urllib.error

API = "https://fantasy.premierleague.com/api"
UNDERSTAT = "https://understat.com/league/EPL"
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


def _f(val, default=0.0):
    """Safely turn an API value (which may be None, '', or a number) into a float."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def build_players(boot):
    teams = {t["id"]: t["short_name"] for t in boot["teams"]}
    players = []
    for e in boot["elements"]:
        price = e["now_cost"] / 10.0
        pts = e["total_points"]
        mins = e.get("minutes", 0) or 0
        # Defensive-contribution potential (2025/26 rule). Field names vary, so
        # try the direct per-90 value first, then fall back to summed raw actions.
        dc90 = e.get("defensive_contribution_per_90")
        if dc90 is None:
            raw = (_f(e.get("clearances_blocks_interceptions")) + _f(e.get("tackles"))
                   + _f(e.get("recoveries")))
            dc90 = (raw / mins * 90.0) if mins else 0.0
        players.append({
            "id": e["id"],
            "name": e["web_name"],
            "full_name": (str(e.get("first_name", "")) + " " + str(e.get("second_name", ""))).strip(),
            "team_id": e["team"],
            "team": teams.get(e["team"], "?"),
            "pos": POS_MAP.get(e["element_type"], "?"),
            "price": price,
            "points": pts,
            "ppg": _f(e.get("points_per_game")),                     # season points per game
            "form": _f(e.get("form")),
            "ppm": round(pts / price, 2) if price else 0,           # points per million
            # Official FPL "Value" metrics (points per £m). Fall back to a
            # direct calculation if the API doesn't provide the field.
            "value_season": _f(e.get("value_season")) or (round(pts / price, 2) if price else 0),
            "value_form": _f(e.get("value_form")) or (round(_f(e.get("form")) / price, 2) if price else 0),
            "owned": _f(e.get("selected_by_percent")),              # ownership %
            "minutes": mins,
            "starts": e.get("starts", 0) or 0,                      # number of matches started
            # chance of playing next round: None = fully fit (treat as 100)
            "chance": e.get("chance_of_playing_next_round"),
            "news": (e.get("news") or "").strip(),                   # injury/availability note
            "goals": e.get("goals_scored", 0),
            "assists": e.get("assists", 0),
            # --- more box-score stats (for the stats table) ---
            "clean_sheets": e.get("clean_sheets", 0) or 0,
            "saves": e.get("saves", 0) or 0,
            "goals_conceded": e.get("goals_conceded", 0) or 0,
            "bonus": e.get("bonus", 0) or 0,
            "bps": e.get("bps", 0) or 0,
            "ict": _f(e.get("ict_index")),                            # Influence+Creativity+Threat
            "threat": _f(e.get("threat")),
            "creativity": _f(e.get("creativity")),
            # --- underlying / predictive stats ---
            "xgi90": _f(e.get("expected_goal_involvements_per_90")),  # xG + xA per 90
            "xgi_total": _f(e.get("expected_goal_involvements")),      # season xG + xA
            "gi_actual": (e.get("goals_scored", 0) + e.get("assists", 0)),  # actual G+A
            "dc90": _f(dc90),                                         # defensive actions per 90
            "pens": (e.get("penalties_order") == 1),                  # first-choice pen taker
            "setpiece": bool(e.get("corners_and_indirect_freekicks_order")
                             or e.get("direct_freekicks_order")),      # takes corners/free kicks
            # set-piece "order" ranks: 1 = first choice, 2 = second, etc. (None if not a taker)
            "pen_order": e.get("penalties_order"),
            "fk_order": e.get("direct_freekicks_order"),
            "corner_order": e.get("corners_and_indirect_freekicks_order"),
            # --- price / momentum ---
            "t_in": e.get("transfers_in_event", 0) or 0,              # transfers in this GW
            "t_out": e.get("transfers_out_event", 0) or 0,            # transfers out this GW
            "cost_change": (e.get("cost_change_event", 0) or 0) / 10.0,   # £m change this GW
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


def build_season_matrix(boot, fixtures):
    """Full-season fixture matrix per team: every gameweek's opponent(s) & difficulty.

    Handles blank gameweeks (no game) and double gameweeks (two games) — a GW maps
    to a list of games (possibly empty). Powers the season heatmap and the
    slideable gameweek window in the app.
    """
    short = {t["id"]: t["short_name"] for t in boot["teams"]}
    full = {t["id"]: t["name"] for t in boot["teams"]}
    max_gw = max([ev["id"] for ev in boot["events"]], default=38)
    per_team = {tid: {} for tid in short}
    for fx in fixtures:
        ev = fx["event"]
        if ev is None:
            continue
        h, a = fx["team_h"], fx["team_a"]
        per_team.setdefault(h, {}).setdefault(ev, []).append(
            {"opp": short.get(a, "?"), "venue": "H", "diff": fx["team_h_difficulty"]})
        per_team.setdefault(a, {}).setdefault(ev, []).append(
            {"opp": short.get(h, "?"), "venue": "A", "diff": fx["team_a_difficulty"]})
    teams = []
    for tid in short:
        teams.append({"short": short[tid], "name": full[tid],
                      "gws": {str(gw): per_team[tid].get(gw, []) for gw in range(1, max_gw + 1)}})
    teams.sort(key=lambda t: t["short"])
    return {"current_gw": current_gw(boot), "max_gw": max_gw, "teams": teams}


def write_fixtures_outputs(boot, fixtures):
    """Write a self-contained colour-coded fixtures.html and a fixtures-data.json."""
    gw, horizon, ranked = compute_fixture_ranking(boot, fixtures)
    # JSON for the webpage tab
    with open("fixtures-data.json", "w") as f:
        json.dump({"gw": gw, "horizon": horizon, "ranked": ranked}, f, indent=2)
    # Full-season matrix for the season graph + slideable gameweek window
    with open("fixtures-season.json", "w") as f:
        json.dump(build_season_matrix(boot, fixtures), f, indent=2)

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


# ----------------------------------------------------------------------------
#  AUTO-BUILD: pick the best 15 within the rules, using the tactics.
#  Rules enforced (same as the real game):
#    - 2 GK, 5 DEF, 5 MID, 3 FWD
#    - max 3 players from any one Premier League club
#    - total price <= £100.0m
#  Tactics encoded in each player's `score`:
#    - season quality (points per game) + recent form
#    - a fixture multiplier (easier upcoming games score higher)
#    - only "nailed", available players are considered for the starting XI
#  We seed the cheapest legal squad (guarantees we can afford 15) then keep
#  making the single best-value upgrade swap until no swap improves the total
#  starting-XI score within budget — i.e. maximise points for your £100m.
# ----------------------------------------------------------------------------
SQUAD_QUOTA = {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}
BUDGET_CAP = 100.0
MAX_PER_CLUB = 3
# valid starting formations: (DEF, MID, FWD) — always 1 GK, 11 total
FORMATIONS = [(3, 4, 3), (3, 5, 2), (4, 4, 2), (4, 3, 3), (4, 5, 1),
              (5, 4, 1), (5, 3, 2), (5, 2, 3), (3, 3, 4)]


# Strategy presets — the "toggles". Each is a set of weights for the scoring
# model. They all share the same signals; the weights just tilt the emphasis.
#   quality  = season points per game        form   = recent points
#   xgi      = expected goals+assists /90     defcon = defensive actions /90
#   pen/set-piece = flat bonus for takers     value  = reward points-per-million
STRATEGIES = {
    "balanced":  {"quality": 0.45, "form": 0.25, "xgi": 1.4, "defcon": 0.25,
                  "pen": 0.6, "setpiece": 0.25, "value": 0.0, "label": "Balanced"},
    "attacking": {"quality": 0.35, "form": 0.30, "xgi": 2.2, "defcon": 0.05,
                  "pen": 1.0, "setpiece": 0.45, "value": 0.0, "label": "Attacking"},
    "value":     {"quality": 0.45, "form": 0.25, "xgi": 1.2, "defcon": 0.30,
                  "pen": 0.5, "setpiece": 0.25, "value": 0.9, "label": "Value"},
}


def player_rating(p, team_diff, weights):
    """The tactic-based score for one player (higher = better pick)."""
    diff = team_diff.get(p["team"], 3.0)
    fixture_mult = 1 + (3.0 - diff) * 0.06            # easy run boosts, hard run penalises
    # Heavily discount low-minute players: their per-90 stats are noisy small
    # samples, so a fringe player shouldn't out-rate a proven starter.
    mins_factor = 0.15 + 0.85 * min(p["minutes"], 1800) / 1800.0
    rating = (weights["quality"] * p["ppg"]
              + weights["form"] * p["form"]
              + weights["xgi"] * p["xgi90"]
              + weights["defcon"] * p["dc90"])
    if p["pens"]:
        rating += weights["pen"]                      # penalty takers: extra points route
    if p["setpiece"]:
        rating += weights["setpiece"]                 # corners/free-kick takers
    if weights.get("value"):
        rating += weights["value"] * (p["ppm"] / 5.0)   # tilt toward cheap points
    return round(rating * fixture_mult * mins_factor, 3)


def score_players(players, ranking, weights):
    """Attach a tactic-based `score` to each available player using the weights."""
    team_diff = {r["short"]: r["avg"] for r in ranking}
    pool = []
    for p in players:
        if p["status"] != "a":          # skip injured/suspended/doubtful
            continue
        p = dict(p)
        p["score"] = player_rating(p, team_diff, weights)
        pool.append(p)
    return pool


def team_strengths(boot):
    """Attack/defence strength per team (home & away) + league averages, from FPL data."""
    st = {}
    for t in boot["teams"]:
        st[t["id"]] = {
            "att_h": t.get("strength_attack_home", 1100), "att_a": t.get("strength_attack_away", 1100),
            "def_h": t.get("strength_defence_home", 1100), "def_a": t.get("strength_defence_away", 1100),
        }
    n = max(len(st), 1)
    avg_att = sum((s["att_h"] + s["att_a"]) / 2 for s in st.values()) / n
    avg_def = sum((s["def_h"] + s["def_a"]) / 2 for s in st.values()) / n
    return st, (avg_att or 1100), (avg_def or 1100)


def compute_projections(players, boot, fixtures, horizon=5):
    """Estimate projected FPL points per gameweek and clean-sheet % per team.

    Free model from official data:
      - clean sheet %: Poisson P(0) on expected goals conceded, from team attack/
        defence strengths and home/away.
      - projected points: season points-per-game adjusted for upcoming fixture
        difficulty, availability, and an xG over/under-performance nudge.
    Returns (xpts_by_id, cs_pct_by_team_id).
    """
    st, AVG_ATT, AVG_DEF = team_strengths(boot)
    LG_GOALS = 1.35                                   # avg goals a team concedes per game
    # Preseason, FPL hasn't set team strengths yet (they come through as 0/tiny).
    # Without real strengths the clean-sheet model is meaningless, so mark it unknown.
    have_strengths = AVG_ATT > 500 and AVG_DEF > 500 and \
        any((st[t]["att_h"] or 0) > 100 for t in st)
    gw = current_gw(boot)
    upcoming = range(gw, gw + horizon)
    # per team: list of (opponent_id, is_home, difficulty)
    fx = {t["id"]: [] for t in boot["teams"]}
    for f in fixtures:
        if f["event"] is None or f["event"] not in upcoming:
            continue
        fx.setdefault(f["team_h"], []).append((f["team_a"], True, f["team_h_difficulty"]))
        fx.setdefault(f["team_a"], []).append((f["team_h"], False, f["team_a_difficulty"]))

    cs_by_team, diff_by_team = {}, {}
    for tid, games in fx.items():
        if not games:
            cs_by_team[tid], diff_by_team[tid] = None, 3.0
            continue
        cs_vals, diffs = [], []
        for opp, home, d in games:
            our_def = st[tid]["def_h"] if home else st[tid]["def_a"]
            opp_att = st[opp]["att_a"] if home else st[opp]["att_h"]
            if our_def and opp_att:
                gc = LG_GOALS * (opp_att / AVG_ATT) * (AVG_DEF / our_def)
                cs_vals.append(math.exp(-min(max(gc, 0.15), 4.0)))   # Poisson P(0 conceded)
            diffs.append(d)
        cs_by_team[tid] = (round(sum(cs_vals) / len(cs_vals) * 100, 0)
                           if (have_strengths and cs_vals) else None)
        diff_by_team[tid] = sum(diffs) / len(diffs) if diffs else 3.0

    xpts = {}
    for p in players:
        if p["status"] != "a":
            xpts[p["id"]] = 0.0
            continue
        chance = 100 if p["chance"] is None else p["chance"]
        avail = chance / 100.0
        d = diff_by_team.get(p["team_id"], 3.0)
        fixture_adj = 1 + 0.16 * (3.0 - d)           # easy run boosts, hard run trims (strong swing)
        games = max(p["minutes"] / 90.0, 1)
        per_game_diff = (p["xgi_total"] - p["gi_actual"]) / games   # + = due, − = riding luck
        xg_nudge = min(max(1 + 0.12 * per_game_diff, 0.85), 1.20)
        # confidence in his minutes: a player who barely features shouldn't project
        # like a nailed starter even if his few games looked good.
        mins_conf = 0.2 + 0.8 * min(p["minutes"], 1800) / 1800.0
        xpts[p["id"]] = round(p["ppg"] * fixture_adj * avail * xg_nudge * mins_conf, 1)
    return xpts, cs_by_team


def write_players_db(players, ranking, boot, fixtures):
    """Write players-data.json: every player with a rating, projection and clean-sheet %."""
    team_diff = {r["short"]: r["avg"] for r in ranking}
    w = STRATEGIES["balanced"]
    xpts, cs_by_team = compute_projections(players, boot, fixtures)
    db = []
    for p in players:
        avail = p["status"] == "a"
        cs = cs_by_team.get(p["team_id"])
        db.append({
            "name": p["name"], "full": p.get("full_name", ""),
            "team": p["team"], "pos": p["pos"], "price": p["price"],
            "mins": p["minutes"], "starts": p.get("starts", 0),
            "owned": p["owned"], "form": p["form"], "xgi90": round(p["xgi90"], 2),
            "xgi_total": round(p["xgi_total"], 2),             # season xG+xA total (matches FPL's "Expected Goal Involvements")
            "rating": player_rating(p, team_diff, w) if avail else 0.0,
            "xpts": xpts.get(p["id"], 0.0),                    # projected points / gameweek
            "cs": (int(cs) if cs is not None else None),        # team clean-sheet % (for GK/DEF)
            "pens": p["pens"], "setpiece": p["setpiece"],
            "fixdiff": round(team_diff.get(p["team"], 3.0), 2),
            # box-score stats for the sortable Stats table
            "points": p["points"], "ppg": p["ppg"], "goals": p["goals"], "assists": p["assists"],
            "clean_sheets": p["clean_sheets"], "saves": p["saves"], "gc": p["goals_conceded"],
            "bonus": p["bonus"], "bps": p["bps"], "ict": round(p["ict"], 1),
            "vseason": p["value_season"], "vform": p["value_form"],
            "avail": avail, "status": p["status"],
        })
    with open("players-data.json", "w") as fh:
        json.dump({"players": db}, fh, indent=2)
    print(f"  Saved players-data.json ({len(db)} players) for Rate-My-Team.", file=sys.stderr)


def _club_counts(squad):
    counts = {}
    for p in squad:
        counts[p["team_id"]] = counts.get(p["team_id"], 0) + 1
    return counts


def optimise_squad(pool):
    """Return a legal 15-man squad maximising starting-XI score within budget."""
    by_pos = {pos: sorted([p for p in pool if p["pos"] == pos], key=lambda p: p["price"])
              for pos in SQUAD_QUOTA}

    # 1) Seed with the cheapest legal squad so the budget is always satisfiable.
    squad, counts = [], {}
    for pos, need in SQUAD_QUOTA.items():
        taken = 0
        for p in by_pos[pos]:
            if taken >= need:
                break
            if counts.get(p["team_id"], 0) < MAX_PER_CLUB:
                squad.append(p)
                counts[p["team_id"]] = counts.get(p["team_id"], 0) + 1
                taken += 1
        if taken < need:
            raise SystemExit("Not enough available players to fill the squad — try again later.")

    def total_price(sq):
        return sum(p["price"] for p in sq)

    # 2) Hill-climb: repeatedly apply the single best budget-legal upgrade swap.
    improved = True
    while improved:
        improved = False
        best_gain, best_swap = 1e-6, None
        cur_ids = {p["id"] for p in squad}
        cur_price = total_price(squad)
        cur_xi = pick_starting_xi(squad)[0]
        for i, out_p in enumerate(squad):
            for in_p in by_pos[out_p["pos"]]:
                if in_p["id"] in cur_ids:
                    continue
                # budget check
                if cur_price - out_p["price"] + in_p["price"] > BUDGET_CAP:
                    continue
                # club-limit check
                cnt = _club_counts(squad)
                cnt[out_p["team_id"]] -= 1
                if cnt.get(in_p["team_id"], 0) >= MAX_PER_CLUB:
                    continue
                trial = squad[:i] + [in_p] + squad[i + 1:]
                gain = pick_starting_xi(trial)[0] - cur_xi
                if gain > best_gain:
                    best_gain, best_swap = gain, (i, in_p)
        if best_swap:
            i, in_p = best_swap
            squad[i] = in_p
            improved = True
    return squad


def pick_starting_xi(squad):
    """Best legal XI + (captain, vice). Returns (xi_score, xi, bench, captain, vice)."""
    gk = sorted([p for p in squad if p["pos"] == "GK"], key=lambda p: p["score"], reverse=True)
    d = sorted([p for p in squad if p["pos"] == "DEF"], key=lambda p: p["score"], reverse=True)
    m = sorted([p for p in squad if p["pos"] == "MID"], key=lambda p: p["score"], reverse=True)
    f = sorted([p for p in squad if p["pos"] == "FWD"], key=lambda p: p["score"], reverse=True)
    best = None
    for nd, nm, nf in FORMATIONS:
        if len(d) < nd or len(m) < nm or len(f) < nf or not gk:
            continue
        xi = [gk[0]] + d[:nd] + m[:nm] + f[:nf]
        s = sum(p["score"] for p in xi)
        if best is None or s > best[0]:
            best = (s, xi)
    if best is None:                       # fallback (shouldn't happen with a legal squad)
        xi = squad[:11]
        best = (sum(p["score"] for p in xi), xi)
    xi = best[1]
    bench = [p for p in squad if p not in xi]
    # Captain/vice should be outfield players — you never captain a goalkeeper.
    # Prefer attackers (MID/FWD), then defenders, ranked by score.
    outfield = sorted([p for p in xi if p["pos"] != "GK"], key=lambda p: p["score"], reverse=True)
    attackers = [p for p in outfield if p["pos"] in ("MID", "FWD")]
    cap_pool = attackers if attackers else (outfield if outfield else xi)
    captain = cap_pool[0] if cap_pool else None
    vice = cap_pool[1] if len(cap_pool) > 1 else (outfield[1] if len(outfield) > 1 else None)
    return best[0], xi, bench, captain, vice


def _build_one(players, ranking, weights):
    """Build one squad for a given strategy and return its serialisable form."""
    pool = score_players(players, ranking, weights)
    squad = optimise_squad(pool)
    _, xi, _, captain, vice = pick_starting_xi(squad)
    xi_ids = {p["id"] for p in xi}
    order = {"GK": 0, "DEF": 1, "MID": 2, "FWD": 3}
    squad_sorted = sorted(squad, key=lambda p: (order[p["pos"]], -p["score"]))
    total = sum(p["price"] for p in squad)
    return {
        "budget_spent": round(total, 1),
        "captain_id": captain["id"] if captain else None,
        "vice_id": vice["id"] if vice else None,
        "players": [{
            "id": p["id"], "name": p["name"], "team": p["team"], "pos": p["pos"],
            "price": p["price"], "starting": p["id"] in xi_ids,
            "captain": bool(captain and p["id"] == captain["id"]),
            "vice": bool(vice and p["id"] == vice["id"]),
            "pens": p["pens"], "setpiece": p["setpiece"],
        } for p in squad_sorted],
    }, squad_sorted, xi_ids, captain, vice, total


def report_build(players, ranking):
    variants = {}
    first = True
    for key, w in STRATEGIES.items():
        data, squad_sorted, xi_ids, captain, vice, total = _build_one(players, ranking, w)
        variants[key] = data
        # Print the balanced squad in full; summarise the others.
        if first:
            print(f"\n{'=' * 78}\n  ⚡ AUTO-BUILT SQUAD — best 15 for your £100.0m ({w['label']} strategy)\n{'=' * 78}")
            print(f"  Spent £{total:.1f}m  |  In the bank £{BUDGET_CAP - total:.1f}m"
                  f"  |  Captain: {captain['name']}  Vice: {vice['name']}\n")
            print(f"  {'Pos':<4}{'Player':<15}{'Team':<6}{'£m':<6}{'Form':<6}{'xGI90':<7}{'Pen':<5}{'Start?':<6}")
            print("  " + "-" * 70)
            for p in squad_sorted:
                role = "(C)" if p["id"] == captain["id"] else "(V)" if p["id"] == vice["id"] else ""
                start = "XI" if p["id"] in xi_ids else "bench"
                pen = "P" if p["pens"] else ("s" if p["setpiece"] else "")
                print(f"  {p['pos']:<4}{(p['name'] + ' ' + role)[:14]:<15}{p['team']:<6}"
                      f"{p['price']:<6.1f}{p['form']:<6.1f}{p['xgi90']:<7.2f}{pen:<5}{start:<6}")
            first = False
        else:
            names = ", ".join(pp["name"] for pp in data["players"] if pp["starting"])[:120]
            print(f"\n  {w['label']} XI (£{data['budget_spent']:.1f}m): {names}…")

    out = {
        "generated": None,
        "default": "balanced",
        "labels": {k: v["label"] for k, v in STRATEGIES.items()},
        "variants": variants,
        # Backwards-compatible: also expose the balanced squad at the top level
        # so older versions of the page still work.
        **variants["balanced"],
    }
    with open("squad-data.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\n  Saved squad-data.json (3 strategies) — open the tool and use the toggle buttons.")


def _slim(p, extra=None):
    """Compact player dict for the insights JSON."""
    d = {"name": p["name"], "team": p["team"], "pos": p["pos"],
         "price": p["price"], "owned": p["owned"], "form": p["form"]}
    if extra:
        d.update(extra)
    return d


def write_insights(players, top=14):
    """Produce insights-data.json powering the Player Insights tab."""
    avail = [p for p in players if p["status"] == "a"]
    played = [p for p in avail if p["minutes"] >= 200]     # enough data to be meaningful

    # xG over/under performers (needs real minutes + some xGI data)
    xg_pool = [p for p in played if p["xgi_total"] > 0.5 or p["gi_actual"] > 0]
    over = sorted(xg_pool, key=lambda p: (p["gi_actual"] - p["xgi_total"]), reverse=True)
    under = sorted(xg_pool, key=lambda p: (p["xgi_total"] - p["gi_actual"]), reverse=True)

    # Penalty takers: first AND second choice, grouped by club, order 1 before 2.
    pens = sorted([p for p in avail if p["pen_order"] in (1, 2)],
                  key=lambda p: (p["team"], p["pen_order"]))
    # Set-piece takers: anyone on corners or direct free-kicks (first choice).
    setpieces = sorted([p for p in avail
                        if p["corner_order"] == 1 or p["fk_order"] == 1],
                       key=lambda p: (p["team"], p["fk_order"] or 9, p["corner_order"] or 9))

    def duties(p):
        """Human-readable set-piece duties for a player."""
        bits = []
        if p["pen_order"] == 1:
            bits.append("Penalties")
        elif p["pen_order"] == 2:
            bits.append("Pens (2nd)")
        if p["fk_order"] == 1:
            bits.append("Free-kicks")
        if p["corner_order"] == 1:
            bits.append("Corners")
        return ", ".join(bits) or "—"

    # "Nailed-on" rating: does he start, play the full 90, and is he fit?
    def nailed_info(p):
        chance = 100 if p["chance"] is None else p["chance"]
        mps = round(p["minutes"] / p["starts"], 0) if p["starts"] else 0   # avg mins per start
        if p["status"] != "a" or chance <= 25:
            rating, verdict = "out", "🔴 Doubt / out"
        elif chance < 100:
            rating, verdict = "doubt", f"🟡 Slight doubt ({int(chance)}%)"
        elif p["starts"] == 0:
            rating, verdict = "unknown", "⚪ No starts yet"
        elif mps >= 80:
            rating, verdict = "nailed", "🟢 Nailed — plays 90"
        elif mps >= 63:
            rating, verdict = "sub_risk", "🟡 Often subbed off"
        else:
            rating, verdict = "rotation", "🟠 Rotation / sub"
        return {"rating": rating, "verdict": verdict, "mps": mps, "starts": p["starts"],
                "chance": int(chance), "news": p["news"][:60]}

    # Bigger list here so the in-app search can find most relevant players.
    nailed = sorted([p for p in avail if p["minutes"] > 0 or p["starts"] > 0],
                    key=lambda p: (p["starts"], p["minutes"]), reverse=True)

    defcon_def = sorted([p for p in played if p["pos"] == "DEF"],
                        key=lambda p: p["dc90"], reverse=True)
    defcon_mid = sorted([p for p in played if p["pos"] in ("MID", "FWD")],
                        key=lambda p: p["dc90"], reverse=True)

    template = sorted(avail, key=lambda p: p["owned"], reverse=True)
    diffs = sorted([p for p in played if p["owned"] < 10 and (p["form"] > 0 or p["xgi90"] > 0)],
                   key=lambda p: (p["form"], p["xgi90"]), reverse=True)

    net = lambda p: p["t_in"] - p["t_out"]
    risers = sorted(avail, key=net, reverse=True)
    fallers = sorted(avail, key=net)

    # Official FPL "Value" rankings (points per £m). Season uses all players;
    # form needs a few played minutes to be meaningful.
    value_season = sorted(avail, key=lambda p: p["value_season"], reverse=True)
    value_form = sorted([p for p in avail if p["minutes"] >= 90],
                        key=lambda p: p["value_form"], reverse=True)

    out = {
        "xg_under": [_slim(p, {"xgi": round(p["xgi_total"], 1), "actual": p["gi_actual"],
                     "gap": round(p["xgi_total"] - p["gi_actual"], 1)}) for p in under[:top]],
        "xg_over": [_slim(p, {"xgi": round(p["xgi_total"], 1), "actual": p["gi_actual"],
                    "gap": round(p["gi_actual"] - p["xgi_total"], 1)}) for p in over[:top]],
        "penalties": [_slim(p, {"choice": "1st" if p["pen_order"] == 1 else "2nd",
                     "duties": duties(p)}) for p in pens[:24]],
        "setpieces": [_slim(p, {"duties": duties(p)}) for p in setpieces[:30]],
        "nailed": [_slim(p, dict({"minutes": p["minutes"]}, **nailed_info(p))) for p in nailed[:120]],
        "defcon_def": [_slim(p, {"dc90": round(p["dc90"], 1)}) for p in defcon_def[:top]],
        "defcon_mid": [_slim(p, {"dc90": round(p["dc90"], 1)}) for p in defcon_mid[:top]],
        "template": [_slim(p) for p in template[:top]],
        "differentials": [_slim(p, {"xgi90": round(p["xgi90"], 2)}) for p in diffs[:top]],
        "risers": [_slim(p, {"net": net(p), "cost_change": p["cost_change"]}) for p in risers[:top]],
        "fallers": [_slim(p, {"net": net(p), "cost_change": p["cost_change"]}) for p in fallers[:top]],
        "value_season": [_slim(p, {"val": round(p["value_season"], 1), "points": p["points"]}) for p in value_season[:top]],
        "value_form": [_slim(p, {"val": round(p["value_form"], 1)}) for p in value_form[:top]],
    }
    with open("insights-data.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("  Saved insights-data.json — populates the Player Insights tab.", file=sys.stderr)


# ----------------------------------------------------------------------------
#  UNDERSTAT — a second, independent expected-goals (xG) source.
#  Understat runs its own shot-quality model, so it's a useful cross-check on
#  FPL's own xG. We read the league page's embedded playersData JSON.
# ----------------------------------------------------------------------------
def _understat_season_year():
    """EPL season is labelled by its starting year on Understat (Aug-May)."""
    today = datetime.date.today()
    return today.year if today.month >= 7 else today.year - 1


def _fetch_understat_year(year):
    """Fetch and parse Understat's EPL playersData for one season. [] on any error."""
    url = f"{UNDERSTAT}/{year}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8")
    except Exception as e:                       # network / HTTP issues — degrade gracefully
        print(f"  Understat fetch failed ({year}): {e}", file=sys.stderr)
        return []
    m = re.search(r"var\s+playersData\s*=\s*JSON.parse\('(.*?)'\)", html)
    if not m:
        return []
    s = m.group(1).encode("utf-8").decode("unicode_escape")
    try:                                          # recover accented names (utf-8 via latin-1)
        s = s.encode("latin-1").decode("utf-8")
    except Exception:
        pass
    try:
        return json.loads(s)
    except Exception:
        return []


def fetch_understat():
    """Return (season_year, players). Falls back to last season if this one is empty."""
    year = _understat_season_year()
    for yr in (year, year - 1):
        data = _fetch_understat_year(yr)
        if data:
            return yr, data
    return year, []


def write_understat():
    """Write understat-data.json: xG over/under performers and top threats."""
    try:
        year, rows = fetch_understat()
    except Exception as e:
        print(f"  Understat unavailable: {e}", file=sys.stderr)
        year, rows = _understat_season_year(), []

    def num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    players = []
    for p in rows:
        mins = num(p.get("time"))
        if mins < 180:                            # need enough minutes to be meaningful
            continue
        goals, xg = num(p.get("goals")), num(p.get("xG"))
        assists, xa = num(p.get("assists")), num(p.get("xA"))
        players.append({
            "name": p.get("player_name", "?"),
            "team": p.get("team_title", "?"),
            "pos": p.get("position", ""),
            "games": int(num(p.get("games"))),
            "goals": int(goals), "xg": round(xg, 1),
            "assists": int(assists), "xa": round(xa, 1),
            "shots": int(num(p.get("shots"))),        # total shots
            "kp": int(num(p.get("key_passes"))),       # key passes (chances created)
            "threat": round(xg + xa, 1),          # total goal involvement threat (xG+xA)
            "over": round((goals + assists) - (xg + xa), 1),   # + = overperforming (lucky)
        })

    def slim(p):
        return {k: p[k] for k in ("name", "team", "pos", "games", "goals", "xg",
                                  "assists", "xa", "shots", "kp", "threat", "over")}

    out = {
        "season": year,
        "source": "Understat",
        "top_threat": [slim(p) for p in sorted(players, key=lambda p: p["threat"], reverse=True)[:16]],
        "xg_under": [slim(p) for p in sorted(players, key=lambda p: p["over"])[:16]],       # most due
        "xg_over": [slim(p) for p in sorted(players, key=lambda p: p["over"], reverse=True)[:16]],  # riding luck
    }
    with open("understat-data.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"  Saved understat-data.json ({len(players)} players, {year} season).", file=sys.stderr)


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
    ap.add_argument("--build", action="store_true",
                    help="auto-build the best legal 15-man squad and save squad-data.json")
    ap.add_argument("--understat", action="store_true",
                    help="fetch Understat xG and save understat-data.json")
    args = ap.parse_args()

    boot, fixtures = load_data(save_json=args.json)
    players, _ = build_players(boot)

    show_all = not (args.value or args.form or args.diff or args.fixtures
                    or args.build or args.html or args.csv or args.understat)

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

    if show_all or args.build:
        _, _, ranking = compute_fixture_ranking(boot, fixtures)
        report_build(players, ranking)
        write_insights(players)
        write_players_db(players, ranking, boot, fixtures)

    if show_all or args.build or args.understat:
        write_understat()

    if args.html:
        write_fixtures_outputs(boot, fixtures)

    if args.csv:
        dump_csv(players, args.csv)

    print("\nTip: pair the BEST VALUE list with the EASIEST FIXTURES list —")
    print("cheap players from teams with a green run are where seasons are won.\n")


if __name__ == "__main__":
    main()
