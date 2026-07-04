# CLAUDE.md — World Cup 2026 Fantasy Value Predictor

> Canonical source of truth for this project. Update it at every major edit or
> architectural decision. It auto-loads into every Claude Code session — do not
> maintain a second parallel handoff file.

---

## How to work with Mark (READ FIRST — overrides Claude Code defaults)

Mark is a self-described **Python beginner** who wants to genuinely understand the
code, not just receive it.

- **Explain every line** — imports (what the library does and why), function
  parameters (placeholders until called), control flow, regex, f-strings, list
  comprehensions (give the longhand loop alongside).
- **Architecture first.** Discuss structure and get confirmation before writing code;
  use Plan Mode. Encourage pausing.
- **Push back** — don't just agree; challenge choices that conflict with the design.
- **Comment code generously.**

> Note: for the large autonomous build (data sources, the model, the React front-end)
> Mark explicitly asked for the whole project to be completed end-to-end after an
> up-front round of questions. The default "ask before each step" habit still applies
> to normal incremental work.

---

## Project goal

An analytical tool that estimates the **expected fantasy points** and **value**
(points per unit cost) of every player at the 2026 FIFA World Cup — NOT a live game.
Signals: club form (Big-5, ~2 seasons), international form (~2 World Cups), opponent
strength (betting odds), and fixture difficulty (group opponents).

---

## Environment

- **OS:** Windows · **Python:** 3.14 · **Node:** 18+
- **Working dir:** `C:\Repos\world-cup-fantasy-value-tool\`
- **Python venv:** `data_pipeline/.venv` (canonical). A redundant repo-root `.venv`
  exists — ignore it.
- **Run Python as a module** from `data_pipeline/`, e.g.
  `./.venv/Scripts/python.exe -m wcfv.model.build`. Paths are resolved from the
  package (`wcfv/paths.py`), so cwd no longer matters for data locations, but the
  package must be importable (run from `data_pipeline/`).
- **Encoding:** every file read/write uses `encoding='utf-8'`. On Windows also set
  `PYTHONUTF8=1` (or `sys.stdout.reconfigure(encoding='utf-8')`) before printing
  non-ASCII player names, or stdout throws `UnicodeEncodeError`.
- **Secrets:** `ODDS_API_KEY` lives in a gitignored `data_pipeline/.env`, loaded by
  `wcfv/env.py`. Never commit the key.

---

## Architecture (all stages complete)

Clean package under `data_pipeline/wcfv/`, orchestrated by `run_pipeline.py`:

```
fetch/     squads.py  fbref.py  groups.py  strength.py  prices.py
process/   countries.py  consolidate.py  match.py
model/     features.py  matchmodel.py  simulate.py  pricing.py  scoring.py  build.py
export.py  -> data/output/players.json (+ copy into frontend/public/data)
```

Pipeline order and status:

```
1  fetch/squads.py            FIFA PDF        -> squads_2026.csv                [DONE]
2  fetch/fbref.py             FBref/Selenium  -> 16 raw CSVs                    [DONE]
3a process/consolidate.py     merge 4 stat types/season -> *_consolidated.csv  [DONE]
3b process/match.py           fuzzy match -> squad_stats_merged.csv            [DONE]
4  fetch/strength.py          Odds API + priors -> team_strength.csv           [DONE]
4b fetch/prices.py            scrape (best-effort) / synthetic fallback        [DONE]
5  fetch/groups.py            worldcup26.ir -> groups_2026 + fixtures_2026     [DONE]
6  model/build.py + export.py xP, value, sims -> players.json                  [DONE]
```

**Separation of concerns is load-bearing.** Every stage writes to disk; a bug in one
never forces re-running an earlier (slow/network) one. Fetching, matching, and
modelling are distinct and independently runnable.

**Front-end:** `frontend/` — React + TypeScript + Vite dashboard (Explorer table,
player detail panel, budget squad optimiser). Reads `public/data/players.json`.
`npm run dev`.

---

## Key facts learned from the real data

- **Nation codes:** FBref club `nation` == FIFA code for every WC nation present, so
  club stats join directly on `nation_code` (no remap). International files use full
  names → mapped via `config/countries.csv`. Only Curaçao/Qatar have no Big-5 club
  players; the intl `standard` file for **2022 only** carries an extra `club` column.
- **Consolidation:** merge on the 8 shared id-cols
  (`league,season,team,player,nation,pos,age,born`), outer join (playing_time lists
  more players than the other tables); only the ~6 repeated columns get their stat
  type prefixed.
- **Matching:** squad names from the PDF are garbled/duplicated → `rapidfuzz`
  `token_set_ratio`, nation-blocked, threshold 85 (log <90). Coverage: ~40% have
  Big-5 club stats, ~24% were at the 2022 WC (expected).
- **Strength:** live Odds API prices only ~16 contenders; those are de-vigged,
  calibrated to the prior scale, and blended 50/50 — the other 32 keep priors.

---

## Key decisions & why (don't silently reverse)

- **Betting odds for opponent strength**, not a multi-feature model — markets
  aggregate everything; interpretable; fewer moving parts.
- **Squad-first pipeline** — query FBref by league/season, then filter to the ~1,248
  squad players. Never query FBref by player name.
- **Empirical-Bayes shrinkage** toward learned position baselines — the core guard
  against small-sample overfitting.
- **Monte-Carlo** (4k sims/fixture) for a distribution, not just a point estimate.
- **Lagrangian relaxation + multi-start** for the budget squad optimiser (in
  `frontend/src/lib/optimizer.ts`).
- **Synthetic prices are output-based, not xP-based**, so value isn't circular.

---

## Watch-outs

1. Wrong venv → `ModuleNotFoundError`. Use `data_pipeline/.venv`, run from
   `data_pipeline/` as a module.
2. `PYTHONUTF8=1` when printing player names on Windows.
3. FBref fetch needs Chrome + Selenium (local only); raw CSVs are cached, so
   `run_pipeline.py` without `--fetch` skips it.
4. Odds API free tier is limited; `/sports` is free but odds calls cost quota.
5. Fuzzy false positives — threshold 85, review file logs <90.
6. Scoring = 2022 ruleset (`model/scoring.py`) until 2026's is published.
