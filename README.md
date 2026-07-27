# ⚽ Fantasy Premier League Toolkit

Two tools to help you win your FPL mini-league this season.

## 🤖 Hands-off mode (no Python needed)
A GitHub Action (`.github/workflows/update-fpl-data.yml`) runs the script **on
GitHub's servers twice a day**, fetches the live data, and commits the fixture
rankings and auto-built squad back to the repo. Your GitHub Pages site then shows
them automatically — you never run a command.

- **Turn it on:** on GitHub, open the **Actions** tab and enable workflows if
  prompted. It then runs on a schedule by itself.
- **Refresh right now:** Actions tab → **Update FPL data** → **Run workflow**.
  Wait ~1 minute, then reload your page — the Fixture Ranking and Auto-build
  best team will be populated.

Everything below is the manual/local way to do the same thing if you prefer.

## 1. `index.html` — strategy & planners
A single, self-contained web page. **Just double-click it** to open in any browser
(no internet needed), or view it live via GitHub Pages at
<https://lochlan800.github.io/Fantasy-football-/>. It has:
- The core winning tactics (budget structure, template vs differentials, fixtures, transfers)
- An interactive **squad builder** with live £100.0m budget tracking
- A **chip planner** (Wildcard / Bench Boost / Triple Captain / Free Hit timing)
- A **captaincy & transfer** notepad and a **weekly pre-deadline checklist**

Everything you type saves automatically in your browser.

## 2. `fpl_data.py` — LIVE real data from the official API
Pulls **current, real** player prices, form, ownership and fixture difficulty
straight from the official Fantasy Premier League API.

### Is there a free FPL API / API key?
Yes — the **official FPL API is 100% free and needs NO API key.**
Base URL: `https://fantasy.premierleague.com/api/`

Try it in your browser: <https://fantasy.premierleague.com/api/bootstrap-static/>

Key endpoints:
| Endpoint | Data |
|---|---|
| `bootstrap-static/` | all players, prices, form, ownership, teams, gameweeks |
| `fixtures/` | all fixtures + difficulty ratings |
| `element-summary/{id}/` | one player's full history |
| `entry/{team_id}/` | a manager's team |
| `leagues-classic/{id}/standings/` | mini-league standings |

Notes: it's unofficial/undocumented (but very stable), and **browsers block it via
CORS** — which is exactly why this Python script exists (scripts aren't blocked).

### Running the script
Needs **Python 3.8+ only** — no `pip install`, no key.

```bash
python3 fpl_data.py                 # full report: value, form, differentials, fixtures
python3 fpl_data.py --value         # best points-per-million (find cheap enablers)
python3 fpl_data.py --form          # hottest form (buy the run)
python3 fpl_data.py --diff          # differentials owned by <10%
python3 fpl_data.py --fixtures      # rank all 20 teams by easiest fixtures (next 5 GWs)
python3 fpl_data.py --html          # build a colour-coded fixtures.html ranking page
python3 fpl_data.py --build         # AUTO-BUILD the best legal 15-man squad
python3 fpl_data.py --pos MID       # filter to a position (GK/DEF/MID/FWD)
python3 fpl_data.py --max-price 8.0 # cap the price
python3 fpl_data.py --top 30        # show more rows
python3 fpl_data.py --csv all.csv   # export every player to a spreadsheet
```

### Fixture difficulty ranking (like the app's FDR)
`python3 fpl_data.py --html` uses the **official FPL fixture difficulty ratings**
(1 = easiest … 5 = hardest — the same ones in the app) to rank every team by how
easy their next 5 games are. It writes:
- **fixtures.html** — a standalone colour-coded ranking; just open it in a browser.
- **fixtures-data.json** — the data file the main tool's *Fixture Ranking* tab reads.
  Drop it next to `index.html` (or push it to your GitHub Pages site) and the live
  ranked table appears inside the tool automatically.

Re-run it before each deadline — fixtures and ratings change through the season.

### Auto-build the best team (the tactics, applied automatically)
`python3 fpl_data.py --build` picks the **best legal 15-man squad for £100.0m**
and prints it, then saves `squad-data.json`. It applies the tactics for you:
- Enforces the real rules: 2 GK · 5 DEF · 5 MID · 3 FWD, max 3 players per club,
  total ≤ £100.0m.
- Scores every available player on **season quality (points per game) + recent
  form**, adjusted by a **fixture multiplier** (easier upcoming games score higher).
- Skips injured/suspended players and maximises your **starting XI** score, then
  picks a captain and vice.

Then open the tool, go to **Squad Builder**, and use the **⚡ Auto-build** strategy
toggles — it reads `squad-data.json` and fills in all 15 players plus your captain.
(The file must sit next to `index.html`, e.g. in the same folder or pushed to your
GitHub Pages site.) It's a strong data-driven starting point — always sense-check
it against the latest team news before your deadline.

**What the optimiser now considers** (not just past points):
- **Expected goals & assists (xG/xA per 90)** — players genuinely due to score.
- **Minutes played** — rewards nailed-on starters over rotation risks.
- **Penalty & set-piece takers** — a bonus points route each week.
- **Defensive-contribution points (2025/26 rule)** — tackles/interceptions/recoveries,
  which make hard-working defenders & midfielders great value.
- **Fixture difficulty** — easier upcoming games score higher.

**Three strategy toggles** (all three are generated each run):
- **Balanced** — best all-round team (the default).
- **Attacking** — leans into xG/xA and attacking returns for a high ceiling.
- **Value** — maximises points per £m, banking funds to build team value.

## More in the app
The web tool now also includes:
- **📊 Player Insights tab** — live shortlists from the data (`insights-data.json`,
  auto-generated with `--build`): players *due a haul* (high xG, few goals) vs
  *riding their luck*; penalty & set-piece takers; a searchable *nailed-on checker*
  (does he start, play 90, and is he fit?);
  best defensive-contribution value; the ownership *template* vs the best
  *differentials*; and weekly price *risers & fallers*.
- **🥊 Rival Tracker** (Winning Edge tab) — enter your mini-league rival's captain,
  key players and the points gap; it gives tailored "cover them" or "go different"
  advice depending on whether you're ahead or behind.
- **🗺 Multi-gameweek transfer planner** (Captaincy tab) — map out moves 3–4
  gameweeks ahead so single free transfers keep your squad healthy without hits.
- **🪑 Bench-order & deadline guidance** in the Squad Builder.

All of these save in your browser, and the data-driven ones refresh automatically
via the twice-daily GitHub Action.

**Winning move:** cross-reference the `--value` list with the `--fixtures` list —
cheap players from teams with an easy run are where seasons are won.

---
*Player prices, injuries and fixtures change constantly. Always confirm on the
official FPL site before making transfers.*
