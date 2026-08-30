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

## Data sources
- **Official FPL API** (free, no key) — prices, ownership, form, xG/xA, fixtures,
  difficulty ratings, penalty/set-piece takers. The main source.
- **Understat** (free, no key) — a second, independent expected-goals model, used
  as a cross-check. `python3 fpl_data.py --understat` writes `understat-data.json`,
  which powers the *Understat xG* view in the Player Insights tab (xG over/under
  performers and biggest goal threats). Also refreshed by the twice-daily Action.

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
- **fixtures-season.json** — the full-season fixture matrix (every team, every
  gameweek). Powers the *Season graph* heatmap and the ◀/▶ gameweek slider in the
  Fixture Ranking tab, so you can see fixture swings across all 38 GWs and rank any
  future gameweek window.

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
- **🧩 Template team builder** — in **🧮 Squad Builder → ⚡ Auto-Pick**, the **🧩 Template**
  strategy builds a proven-shape £100m squad straight from the live stats: it picks the
  actual template players (weighted by ownership + rating), keeps a legal 2·5·5·3 / max-3-
  per-club / ≤£100m squad with a cheap playing bench, and captains your best premium. It
  then shows a **🧩 Template make-up** card scoring the 15 against the winning ratios —
  goal threat (xGI/90 ≥ 0.4), penalty/set-piece takers, in-form players, budget enablers,
  template picks (30%+ owned) and premiums — with green ticks where it hits target. Tap
  **⬇ Use this as my team** to copy it into My Team. The **🧩 The optimal squad blueprint**
  card on **📖 Guide → Core Strategy** explains the ratios it's built to.
- **❓ Questions tab** — a searchable Q&A that answers common questions about how the
  app works and what its numbers mean (xPts vs xTot, the 0–100 Rating, the World Cup
  flag, chip halves, why a player isn't showing, cross-device saving, and more). New
  questions get added here as they come up.
- **📖 Guide** also documents the newer columns (**xTot**, **Rating**) and a
  "🧭 The tools" overview of what each part of the app does.
- **📊 Player detail card** — tap a player's **name on the Squad Builder pitch** (or the
  **📊** button), or **any row in the Stats table**, to open a card showing their price,
  full stats (points, points-per-match, form, ownership, minutes, goals, assists, clean
  sheets, xGI/90, ICT, bonus, projected points), a **projected season total**, and a
  **bar chart of their expected points for every gameweek of the season** — the
  projected points **number sits on top of each bar** (so you can read GW21, GW34, any
  week directly), with each fixture's opponent and difficulty (FDR 1 green → 5 red,
  blanks marked) underneath.
- **xTot column on the Stats table** — the **projected total points for the rest of the
  season** (sum of each player's per-gameweek projection over their real fixtures),
  sortable like every other column, alongside PPG (points per match) and xPts (next GW).
- **⭐ "Yours" marker** — players in your Squad Builder team are flagged with a green
  **⭐ Yours** badge and a highlighted row on the Stats table, so you can instantly see
  which of the listed players you already own.
- **🚑 Injury / availability flags** — any player who's injured, suspended, doubtful or
  otherwise unavailable is flagged on the Stats table with a red badge (🚑 injured,
  🟥 suspended, ❓ doubt, ⛔ out) and a red-tinted row, so you can avoid picking someone
  who won't play — and spot when one of your own players is a doubt.
- **⭐ Rating (0–100) column & explainer** — the Stats table now has a **Rating** column:
  a 0–100 score for how good a player is *for his position* (100 = the best defender /
  midfielder / etc.), blending points, form, xG/xA, defensive actions and set-pieces,
  adjusted for fixtures and minutes — sort by it to find the best in each position. The
  player detail card explains it in plain English too, e.g. "99/100 — better than 99%
  of defenders", so the number actually means something.
- **Rank (#) column** — a 1, 2, 3, 4 … number down the left of the Stats table showing
  each player's position in the current sort, so the leaders for whatever column you've
  sorted by are numbered at the top.
- **Consistent xPts everywhere** — the Stats table's xPts now uses the **same
  per-gameweek model and real fixture as the Squad Builder pitch and the detail card**,
  so a player reads the same number in all three (they previously differed because the
  data file's xPts averages the next five gameweeks' difficulty, while the pitch uses
  that specific gameweek's fixture).
- **🗺 Planner Board** (built for a laptop / wide screen) — a fixtures-first planning
  board with two sub-tabs:
  - **📅 Fixtures grid** — every one of the 20 teams with their upcoming run and the
    official difficulty of each game (opponent, home/away, 1 green → 5 red), sorted
    easiest run first, with a per-team average. **Your own teams are starred (⭐) and
    pulled to the top**, and a **🎴 Chip plan row** lets you mark which gameweek you'll
    play each chip right on the grid — it saves and syncs with the Season Planner and
    your pitch, and the planned chip shows as a badge on that gameweek's column. Pick
    a window of the next 6/8/10/12 gameweeks, the whole season, or a **whole half** —
    **First half (GW1–19)** or **Second half (GW20–38)** — to plan each half of the
    chip cycle at once; DGW and blanks are marked. You can also **drag any team by its
    ⠿ handle** to slot it in front of another and build your own row order (saved
    between visits); a one-tap **↺ reset** puts it back to easiest-run-first.
  - **🎴 Chip advisor (built around your team)** — reads **your squad's** real fixtures
    and projected points across the season and tells you the best gameweek for each
    chip *for your team*: Bench Boost in **your** biggest double gameweek, Triple
    Captain on your highest-projected single-week haul (naming the player), Free Hit
    in **your** emptiest (most-blanked) week, and Wildcard just before **your** toughest
    projected run. It falls back to the league-wide picture (and a prompt to enter your
    team) until you've built a squad.
- **🔗 One shared chip plan everywhere** — the chip you set is now the **same plan**
  across the whole app: the Squad Builder pitch, the Season Planner, the Planner Board
  grid/advisor, and the standalone Chip Planner tab all read and write one store. Set
  "Bench Boost in GW10" in any of them and it shows up in all the others (and still
  obeys the one-per-half rule). The Chip Planner tab now takes a gameweek number for
  each chip instead of a separate free-text note.
- **🔁 Two chips per half (chip reset)** — FPL gives you **one of each chip in the first
  half (GW1–19) and a fresh set after they reset at GW20**. The app now enforces and
  tracks this: the chip advisor recommends a **first-half** and a **second-half** play
  for every chip, a usage tracker shows which chip is used (and where) in each half and
  what's still free, and the Fixtures grid marks the **🔁 reset line at GW20**. Setting a
  chip only clears the *same* chip in the *same* half (your other half's use is safe), so
  you can't accidentally plan two Wildcards in one half. This applies everywhere chips are
  set — the grid, the Season Planner and the pitch stepper all share it.
  - **⬌ Split view** — on a wide screen, splits the page in half so you can show two
    panels side by side (e.g. the fixtures grid next to the chip advice). A notice
    appears on phones, where split is turned off but the grid still scrolls sideways.
- **⋯ Per-shirt info menu** — the three-dots button in each pitch player's corner opens
  a menu to show an extra stat **under every player**: their **fixture difficulty for the
  next 3 gameweeks** (colour-coded opponents) or their **ownership %**. Pick one to apply
  it to all your players, or Off to hide it; the choice is saved.
- **☰ Burger menu** — the tab list (Squad Builder, Stats, Guide, Rotations, etc.)
  lives behind a three-line burger button that's **always** pinned to the top. Tap
  it to tuck the menu away for a cleaner screen and tap it again to bring it back;
  the button morphs to an ✕ while open and the bar shows which tab you're on. On
  phones the menu auto-tucks after you pick a tab, and your open/closed choice is
  remembered between visits.
- **📌 Pinned gameweek notes** (Season Planner) — pin your own note to any gameweek —
  a reminder like "transfer Salah in", "Wildcard here", or "Triple Captain vs the
  bottom side". Tap **📌 add note** in the Notes column, type it, and it saves
  automatically; pinned weeks are highlighted and marked with a 📌, and blanking a
  note removes it. The same notes also appear on the **Planner Board fixtures grid**
  — a 📌 Notes row you can edit, plus a 📌 marker (with the note on hover) on each
  gameweek's column header — so your reminders sit right next to the fixtures.
- **📆 Season Planner** — projects your team across all 38 gameweeks: each week's
  best-XI projected points (green = big week, red = a dip), using every player's
  scoring rate × their real fixture that week (doubles counted, blanks = 0). Slot
  chips into any week from a dropdown (Triple Captain / Bench Boost adjust the
  projection), see your season points total and your best/toughest weeks, and plan
  transfers around the red weeks. Saves automatically.
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

- **🔁 Substitutions (formation-flexible)** — on the pitch, tap a player in your XI
  then tap a bench player to swap them; the formation reshapes to any legal shape
  (3-5 DEF, 2-5 MID, 1-3 FWD), so you can bench a forward and bring on a
  midfielder/defender. Illegal swaps (e.g. a keeper for an outfielder, or a
  formation outside the limits) are blocked. Tap two bench players to reorder them.
- **🔄 Rotations tab** — finds the best pairs of teams to own one cheap player from
  each and rotate, playing whichever has the better fixture each week; ranked over
  the next 10 gameweeks with a week-by-week "play this team" grid. Great for £4.0–4.5m
  keepers and defenders. Also includes a **🎯 Find the best partner** picker — choose
  one club and it auto-finds its top 3 rotation partners with the side-by-side grids —
  a **⚖️ Compare two teams** picker to check any two clubs yourself, and a **📋 Fixture
  ticker** where you tick up to 6 teams to show/hide their fixtures side by side
  (sorted easiest run first). Each showing fixtures, averages and which team to play.
- **▶ "Assume he starts" override** — for players you expect to play more than the
  data shows (a new signing, or a backup covering an injury), tap ▶ on their shirt
  and their projection uses full minutes instead of their historical minutes. Your
  own read, applied to the numbers — without faking the official data.
- **🌍 World Cup returnee flag** — tap the red 🌍 button on a player's shirt to mark
  someone who went deep at the summer World Cup (e.g. France, England, Spain,
  Argentina). They come back late with almost no pre-season, so they're downgraded for
  the opening weeks — **−45% in GW1**, **−28% in GW2**, **−13% in GW3**, then **fully
  back to normal from GW4**. It downgrades both their **projected points** (pitch, Stats
  xPts/xTot, detail card, XI total, ⚡ Optimise, Season Planner) **and their rating**
  (Rate My Team score and percentile), so a tired returnee won't be over-rated. The flag
  saves per player, and the Stats/rating recompute the moment you toggle it. Flagged
  players show a red **🌍 WC** tag and a "WC return −x%" line on the affected gameweeks.
- **💾 Per-gameweek lineups** — each gameweek keeps its own saved lineup, captain and
  chip, so changes on one week don't overwrite another. A "Save this lineup" button
  confirms it, and a "saved" tag shows which weeks you've set.
- **⚡ Optimise for GW** — one tap picks your highest-projected legal XI for the shown
  gameweek from your 15 (reshaping the formation as needed) and benches the rest,
  ordered for auto-subs — it makes the close bench decisions for you.
- **⏭ Gameweek stepper on the pitch** (Squad Builder → My Team) — ◀ / ▶ buttons
  step your team through every gameweek. Each week the shirts show that GW's
  projected points ("blank" if no game), you set the captain (tap C) and a chip
  from the dropdown per week, and a header shows the projected total for that GW.
  Shares the same plan as the Season Planner tab.
- **⚽ Pitch view** (Squad Builder → My Team) — your team laid out on a football
  pitch in a 3-4-3 with a 4-man bench, like the real FPL. Tap the **＋** on any
  empty shirt to open a search that's locked to that position (a defender slot
  only shows defenders), pick a player and they drop into the shirt. Tap **C** to
  captain, **✕** to remove. Searches by first name or surname (accents ignored),
  blocks duplicates, and tracks your budget live. A **⚙ Filter** button adds a
  **club** filter and a **price cap** ("£X.Xm & below") so you can, say, show only
  Arsenal midfielders £6.0m and below — combine them with the search box, and a badge
  shows how many filters are active.
- **📋 Stats table** — a sortable table of every player, like the paid sites' main
  stats page: tap any column to sort (points, PPG, form, ownership, minutes, goals,
  assists, clean sheets, saves, xGI/90, ICT index, bonus, BPS, value, projected
  points), filter by position, minutes, **teams (tick any number of clubs — none ticked
  shows all) and a price cap ("£X.Xm & below")** with the controls at the top, and
  search by name.
- **📈 Ownership in the ratings** — heavily-owned "template" players are safer picks that
  protect your rank, so ownership now nudges the rating: about **+12% at 39%+ owned
  (must-have)**, **+7% at 27%+**, **+3% at 15%+**, and neutral below (differentials
  aren't penalised). It flows through the Rating column, Rate My Team and the transfer
  suggestions, where template picks show a **📈 template** / **📈 popular** tag.
- **🎯 Set-piece & penalty boost** — penalty takers and corner/free-kick takers get a
  lift in their projected points (penalties ×1.12, set-pieces ×1.06), reflecting their
  extra, reliable route to returns. It flows through every projection — the pitch, the
  Stats table's xPts/xTot (so they rank higher), best-XI totals and the detail card.
- **📈 Points projections** — an "expected FPL points per gameweek" figure for every
  player (from season points-per-game, fixture difficulty, availability and an
  xG over/under-performance nudge). Shown on each pitch shirt, in the position
  picker, and summed for your best XI (captain doubled) in Rate My Team — a free
  take on the paid sites' headline feature.
- **🛡 Clean-sheet %** for defenders and goalkeepers, from the FPL team
  attack/defence **strength ratings** (Poisson on expected goals conceded), shown
  in the position picker.
- **Understat shots & key passes** columns in the Understat xG view.
- **⭐ Rate my team** (Squad Builder) — enter your 15 players and it scores your
  team out of 100 with a grade, flags injured/unavailable players, and suggests
  who to bring in for your weakest spots. Powered by `players-data.json` (every
  player with a tactic-based rating), matched to the names you type.
- **Why? / ✕ Ignore on transfer suggestions** (Rate My Team) — every suggested transfer
  (Who to bring in, Biggest score boosts, Best upgrade with your bank) has a **Why?**
  button that expands a short argument — why the incoming player is good, why yours is
  weaker, and a verdict on why it's better — and a **✕ Ignore** button that hides that
  suggestion for good (with a "Show them again" link to restore ignored ones).
- **💰 Best upgrade with your bank** (Rate My Team) — if you have money spare, it reads
  how much is in your bank and suggests the best **pricier** upgrades you can actually
  afford (the most you can spend on a spot is its price + your bank), each with the
  extra cost and the score impact — so your leftover funds don't sit idle. It sits
  alongside the same-price "Biggest score boosts" and only appears when you have money
  to spend.
- **🎴 Chip-aware transfer advice** (Rate My Team) — when you've planned chips, the
  transfer advice adapts to them: **Bench Boost** shifts focus to strengthening your
  *bench* for that week (it names your weakest bench players, since all 15 score);
  **Free Hit** tells you *not* to transfer for it (it's a one-week team); **Triple
  Captain** points you at a premium with a great fixture that week; **Wildcard** says
  to bank your problems and batch-fix at the reset. It also reads the **sequence** —
  e.g. a Bench Boost followed by a Wildcard means you can pour everything (even hits)
  into the Bench Boost week, because the Wildcard rebuilds your team for free right after.
- **📈 How to raise your score** — the rating is the *average* ranking of your XI,
  so it's held down by your weakest starters, not lifted by your best (which is why
  it feels "stuck"). The tool now explains this and shows a **Biggest score boosts**
  table: the single same-price transfers that lift your rating the most, each with
  the exact before → after number (e.g. `86 → 90`), a short **why he's better**
  line and tag pills (🔒 nailed, 🟢 fixtures, 🎯 pens, ⚽ set-piece), plus a captain
  tip when captaining your top-rated starter would nudge it higher. The "why"
  line is always **grounded in real numbers** — e.g. "+2.1 projected pts a week ·
  3.5 vs 1.7 pts per game", "more goal threat (xGI/90 0.55 vs 0.30)", "better
  clean-sheet odds (61% vs 44%)" — and even a near-tie shows the actual ratings
  ("just edges it on overall rating 1.90 vs 1.50"), so you can judge (or overrule)
  every call yourself rather than trusting a black-box number. Do the top move first.

All of these save in your browser, and the data-driven ones refresh automatically
via the twice-daily GitHub Action.

**Winning move:** cross-reference the `--value` list with the `--fixtures` list —
cheap players from teams with an easy run are where seasons are won.

---
*Player prices, injuries and fixtures change constantly. Always confirm on the
official FPL site before making transfers.*
