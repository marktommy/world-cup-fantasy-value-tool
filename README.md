# World Cup 2026 — Fantasy Value Model

An end-to-end data pipeline and probabilistic model that estimates the **expected
fantasy points** and **value** (points per unit cost) of every player at the 2026
FIFA World Cup, served through an interactive React dashboard.

It is not a wrapper around someone else's numbers: raw player statistics are scraped,
matched, and fed through a purpose-built model — recency-weighted form, empirical-Bayes
shrinkage, a Poisson match model driven by live betting markets, and a Monte-Carlo
simulation of every fixture — to produce a full distribution of outcomes for all
~1,250 players.

```
FBref stats ─┐
Squad list  ─┼─►  match & clean  ─►  features  ─►  match model  ─►  Monte-Carlo  ─►  xP, value, distribution  ─►  React dashboard
Odds / draw ─┘        (fuzzy)        (shrinkage)     (Poisson)       (4k sims)
```

---

## What it produces

- **Expected points (xP)** per player for each group-stage match, opponent-adjusted.
- **A full outcome distribution** — floor (P10), ceiling (P90), and haul probability —
  not just a point estimate, so you can tell a safe pick from a captaincy punt.
- **Value** = group-stage xP ÷ price, surfacing under-priced players.
- **An optimal squad**: a budget-constrained optimiser that builds the highest-xP
  legal 15-player squad (2 GK / 5 DF / 5 MF / 3 FW, ≤ 3 per nation).

### The dashboard

Two views, built to read like an analytical instrument rather than a template:

- **Explorer** — a sortable, filterable table of every player with price, xP, value
  (colour-scaled), and an inline floor→ceiling range bar. Click any player for a panel
  showing their per-opponent points breakdown and the model inputs behind it.
- **Squad optimizer** — drag a budget slider and watch the optimal squad re-solve live,
  laid out on a pitch.

---

## Methodology

The model is deliberately built from interpretable components rather than a black box.
For each player it answers three questions — *will they play?*, *what do they do when
they play?*, and *who are they playing against?* — then simulates the result.

### 1. Form estimation with shrinkage
Per-90 rates (goals, assists, cards, …) are pooled from two club seasons and two past
World Cups, with **more recent data weighted higher** and World Cup minutes up-weighted
for relevance. Raw rates from small samples are unreliable, so each is **shrunk toward a
position baseline** learned from the data itself (empirical Bayes):

```
rate = (events + K · baseline) / (nineties + K)
```

A striker with 3 goals in 200 minutes is pulled firmly toward the league norm; one with
2,500 minutes barely moves. This is the difference between ranking a hot streak and
ranking a player.

### 2. Minutes model
Points require pitch time. Start probability, appearance probability, and the chance of
lasting 60+ minutes are estimated from club playing time, blended with international
caps for players with little Big-5 club data.

### 3. Match model (team strength → goals)
Nation strength is a 0–100 rating built from **live World Cup winner odds** (via The
Odds API, de-margined to implied probabilities) where the market prices a team, and
calibrated priors elsewhere. A Poisson/Elo-style mapping turns the rating gap between
two teams into expected goals for and against, which gives clean-sheet probabilities and
an attacking multiplier that scales each player's output by fixture difficulty.

### 4. Monte-Carlo simulation
Each player's three group games are simulated 4,000 times — sampling minutes, then
Poisson goals/assists, clean sheets, cards and goals conceded — and scored under the
FIFA World Cup fantasy rules. Averaging gives xP; the spread gives the floor, ceiling and
haul probability that a single expected value would hide.

### 5. Value & optimisation
Value is group-stage xP per unit price. The squad optimiser solves the budgeted knapsack
by **Lagrangian relaxation** (penalise price by λ, sweep λ to trace the efficient
frontier) followed by a multi-start local search — fast enough to re-solve on every
slider tick, and robust to the duality gap that traps naive greedy approaches.

Full detail: [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

---

## Repository structure

```
world-cup-fantasy-value-tool/
├── data_pipeline/                  # Python: data + model
│   ├── wcfv/
│   │   ├── paths.py                # cwd-independent path config
│   │   ├── env.py                  # .env loader (keeps the API key out of git)
│   │   ├── fetch/                  # squads, FBref, groups, odds/strength, prices
│   │   ├── process/                # country resolver, consolidation, fuzzy matching
│   │   ├── model/                  # features, match model, simulation, pricing, build
│   │   └── export.py               # emits players.json for the front-end
│   ├── config/countries.csv        # FIFA / FBref / name reconciliation for 48 nations
│   ├── data/  raw · processed · output
│   └── run_pipeline.py             # one command runs the whole thing
└── frontend/                       # React + TypeScript + Vite dashboard
    └── src/  components · lib (optimizer) · types
```

Separation of concerns is strict: every stage writes to disk, so a bug in matching never
forces a re-scrape of FBref, and the model can be re-run in seconds while iterating.

---

## Running it

### Pipeline (Python 3.11+)
```bash
cd data_pipeline
python -m venv .venv && .venv/Scripts/activate      # Windows; use bin/activate on macOS/Linux
pip install -r requirements.txt

# optional: enable live odds
echo "ODDS_API_KEY=your_key_here" > .env

python run_pipeline.py          # process + model + export (uses cached raw data)
python run_pipeline.py --fetch  # also re-scrape squads + FBref (needs Chrome + Selenium)
```
This writes `data/output/players.json` and copies it into the front-end.

### Dashboard (Node 18+)
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

---

## Data sources

| Source | Used for |
|---|---|
| FIFA squad-list PDF | the 48 official 26-man squads |
| FBref (via `soccerdata`) | club + international player statistics |
| worldcup26.ir | the group draw (with an embedded offline fallback) |
| The Odds API | live outright-winner odds → team strength |
| Official fantasy game | prices (best-effort scrape; synthetic fallback) |

Secrets are read from a gitignored `.env`; nothing sensitive is committed.

## Assumptions & limitations

Stated plainly, because a model is only as trustworthy as its caveats:

- **Scoring** follows the FIFA World Cup 2022 fantasy ruleset (2026's is not yet
  published); it lives in one config file and is trivial to update.
- **Goalkeeping saves** are not in the fetched stat types, so GK scoring rests on
  appearances, clean sheets and goals conceded.
- **Club stats cover the Big-5 European leagues only**; players elsewhere are modelled
  from international form and position baselines (shrinkage handles the thin data).
- **Prices are synthetic** unless the official feed is reachable — built from output,
  minutes and reputation (the way a real game prices), and clearly labelled as such.
- The horizon is the **group stage**; per-match projections are opponent-parametrised,
  so any fixture can be evaluated.

## Tech stack

**Python** (pandas, numpy, rapidfuzz, pdfplumber, soccerdata) ·
**TypeScript / React / Vite** · hand-rolled SVG viz and a from-scratch design system
(no component library, no chart library).
