# ⚽ Fantasy Premier League Toolkit

Two tools to help you win your FPL mini-league this season.

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

**Winning move:** cross-reference the `--value` list with the `--fixtures` list —
cheap players from teams with an easy run are where seasons are won.

---
*Player prices, injuries and fixtures change constantly. Always confirm on the
official FPL site before making transfers.*
