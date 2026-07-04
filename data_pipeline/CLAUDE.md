# CLAUDE.md — World Cup 2026 Fantasy Value Predictor

> This is the single canonical source of truth for this project. It replaces the
> old `WC_FANTASY_PROJECT_HANDOFF.md`. Update it at every major edit or
> architectural decision. It auto-loads into every Claude Code session — do not
> maintain a second parallel handoff file.

---

## How to work with Mark (READ FIRST — this overrides Claude Code defaults)

Mark is a self-described **Python beginner** who wants to genuinely understand
the code, not just receive it. Claude Code's default "senior engineer, move fast"
style is **wrong for this project**. Instead:

- **Explain every line.** Imports (what the library does and why it's needed),
  function parameters (they are placeholders — real values arrive when the
  function is called elsewhere), control flow (`with` context managers,
  `if __name__ == "__main__"`), regex (break down each component), f-strings
  (`f"..."` and `{variable}` interpolation), list comprehensions (give the
  longhand `for`-loop equivalent alongside).
- **Architecture first.** Discuss the high-level logic and structure and get
  Mark's confirmation BEFORE writing any code. In Claude Code, use **Plan Mode**
  for this step. Encourage this pausing habit — don't rush to implementation.
- **Push back — do not just agree.** If Mark proposes something that conflicts
  with the established architecture, say so and explain why. Honest constructive
  challenge is expected and wanted.
- **Comment code generously.** Don't assume Mark remembers patterns from a
  previous session.

---

## Project goal

A Python data pipeline that predicts the **fantasy value** of players at the
2026 FIFA World Cup — an analytical tool producing estimated per-player value
scores, NOT a live fantasy game. Value is based on:

1. Club form (last ~2 seasons of Big-5 league stats from FBref)
2. International form (last ~2 tournaments from FBref)
3. Opponent strength (derived from betting odds — not a multi-feature model)
4. Fixture difficulty (each nation's group-stage opponents)

---

## Environment

- **OS:** Windows
- **Working dir:** `C:\Repos\world-cup-fantasy-value-tool\data_pipeline\`
- **Python:** 3.14
- **Active venv:** `data_pipeline/.venv` — ALWAYS use this one. There is a second
  redundant `.venv` at the repo root; ignore it. If Mark hits
  `ModuleNotFoundError`, first check the correct venv is active.
- **Repo:** https://github.com/marktommy/world-cup-fantasy-value-tool (public)
- **Encoding:** ALL file reads must use `encoding='utf-8'`. Windows defaults to
  `cp1252` and throws `UnicodeDecodeError` on the international CSVs otherwise.

### Module layout (confirmed on disk, 2026-07-04)
Logic is split across separate files (the old single-`fetchers.py` idea is dead):
- `fetch_squads.py` — Step 1, squad PDF parsing.
- `fbref_fetchers.py` — Step 2, FBref stat fetching (Selenium, local-only).
- `matching.py` — Step 3, consolidation + (upcoming) fuzzy matching.
- `main.py` — standalone fetcher of the 48 teams + their groups from
  `worldcup26.ir`. NOT part of the stats pipeline; it's a candidate data source
  for Step 5 (fixtures/groups), kept separate for now.

---

## Pipeline architecture (confirmed order)

```
1. fetch_squads.py            → squads_2026.csv              [DONE]
2. fetch_fbref_club_stats()   → raw club CSVs               [DONE — see status]
   fetch_fbref_international_stats() → raw intl CSVs         [DONE — see status]
3a. consolidate_season()      → *_consolidated.csv (4 files) [DONE]
3b. match_players_to_stats()  → squad_stats_merged.csv       [NOT STARTED]
4. fetch_odds (Odds API)      → opponent strength scores     [NOT STARTED]
5. fetch_fixtures (football-data.org) → group fixtures       [NOT STARTED]
6. merge & score              → fantasy_values_2026.csv      [NOT STARTED]
```

**Separation of concerns is load-bearing.** Fetching (save raw CSVs to disk),
matching (fuzzy-match against squads), and merging/scoring are DISTINCT
functions/files. A bug in matching must never require re-scraping FBref. Keep
them independently testable and re-runnable.

**Squad-first, always.** FBref is queried by league+season (returns thousands of
players); you then FILTER down to the ~1,248 players in `squads_2026.csv`. Never
query FBref by player name — the API doesn't support it. Order is always
squads → stats → merge.

---

## Current state

### Step 1 — Squad list: DONE
`fetch_squads.py` downloads the official FIFA 2026 squad PDF, parses it with
`pdfplumber` + regex, and outputs `squads_2026.csv` → **~1,248 players, 48
nations**, in `data/processed/`.

Fields (actual header): `jersey_number`, `position` (GK/DF/MF/FW), `name`,
`dob`, `nation` (full name), `nation_code` (3-letter FIFA code), `club`,
`club_country`, `height_cm`, `caps`, `int_goals`. This CSV is the master list
everything else filters against.

### Step 2 — Raw FBref fetch: DONE (produced 16 CSVs)
Fetch phase complete. Produced 16 FBref CSVs:
- **Club:** seasons `2024-25` and `2025-26` × 4 stat types
  (`standard`, `shooting`, `playing_time`, `misc`) → `data/raw/club/`
- **International:** tournaments `2018` and `2022` × 4 stat types → `data/raw/international/`

Scope decisions:
- **Big 5 European leagues only** for now, via soccerdata's
  `"Big 5 European Leagues Combined"` shortcut. soccerdata's FBref reader
  supports only 8 leagues (Big 5 + World Cup + Euros + Women's WC). Other leagues
  (Saudi, MLS, Brasileirão, Liga MX, Eredivisie…) would need direct FBref
  scraping — deferred. Accepted: non-Big-5 players have no club stats for now.
- **Stat types limited to** `standard`, `shooting`, `playing_time`, `misc`.
  soccerdata's `read_player_season_stats()` has NO `passing`/`defensive` type;
  true passing/defensive tables would need direct scraping — deferred.
- **Keep both** raw totals AND per-90 columns, plus **minutes played**. Per-90 is
  the primary fantasy signal; minutes let the model discount small samples
  (e.g. under ~500 mins).

Known technical details from real data:
- Club files: `nation` column is already clean 3-letter codes (`ENG`, `ESP`).
- International files: full country names in both `team` and `nation`
  (`Argentina`).
- All files share the same eight `id_cols`:
  `league, season, team, player, nation, pos, age, born` — verified unique within
  each file and identical across the four stat types, so they form a safe exact
  merge key. **Exception:** the international `standard` file for **2022 only**
  carries an extra `club` column (the 2018 file and all club files do not).

Status confirmed on disk (2026-07-04): the full fetch ran and all 16 CSVs are
present and populated (e.g. `2024-25_standard.csv` = 2,854 rows). Step 2 is DONE.

Infra notes for the fetchers:
- soccerdata's `FBref` inherits `BaseSeleniumReader` — it drives a **real
  headless Chrome via Selenium**, not plain HTTP. Chrome + matching chromedriver
  must exist locally. **Cannot be tested in Claude's sandbox** (network blocks the
  chromedriver download) — these functions must run on Mark's machine.
- `_flatten_columns()` helper: FBref returns **two-level (MultiIndex) column
  headers** (e.g. `('Performance','Gls')`). `reset_index()` flattens only the row
  index, NOT columns. `_flatten_columns()` joins each tuple into a clean flat
  string (`performance_gls`), called right after `reset_index()` before saving.
- Stale Selenium artifacts (`driver_fixing.lock`, `downloaded_files/`) can appear
  in the project dir — these are NOT pipeline outputs; don't mistake them for such.

### Step 3 — Matching: IN PROGRESS (Stage 1 DONE, Stage 2 next)
`matching.py`. Two stages; Stage 1 (consolidation) is now built and run.

**Stage 1 — Consolidation: DONE (2026-07-04).** `consolidate_season()` +
`consolidate_all()` merge the 4 stat-type CSVs per season into one wide table via
**exact merge** on the eight `id_cols`. Ran locally → four outputs in
`data/processed/`:
- `club_2024-25_consolidated.csv` (3,508 rows), `club_2025-26_consolidated.csv`
  (3,536 rows), `international_2018_consolidated.csv` (736 rows),
  `international_2022_consolidated.csv` (829 rows).

Implemented design decisions (Mark confirmed each):
- **Base table = `standard`**, then `shooting`, `playing_time`, `misc` joined on.
- **Outer join** — `playing_time` lists more players than the others (includes
  low-minute players); outer keeps them rather than dropping.
- **Tag only clashing columns.** ~6 columns repeat across tables; only those get
  their stat-type prefixed (e.g. `misc_90s`, `misc_performance_crdy`). Clean names
  everywhere else. Known cosmetic quirk: `playing_time`'s duplicate of the
  minutes columns becomes `playing_time_playing_time_mp` (harmless, identical
  values to the base copy).
- **Kept the intl `club` column** — rides along from `standard`; present only in
  `international_2022_consolidated.csv`.
- **One output file per season** (4 total), not combined.
- `consolidate_season()` is intentionally **generic and reusable** across club and
  international (same function, different `raw_dir`/`season`) — do NOT break this
  with source-specific logic.

**Stage 2 — Fuzzy matching: NOT STARTED (immediate next action).** Fuzzy-match the
consolidated tables against `squads_2026.csv` ONCE per table (not 16 times).
Planned design:
- **Composite match key = player name + nation** (NOT name + club — club name
  formatting differs between sources; nation codes are standardised).
- **Club vs international kept as SEPARATE columns**, not pre-averaged.
- **Fuzzy threshold ~85** (via `rapidfuzz`); anything under 90 logged for review
  so Mark can inspect low-confidence matches before they're discarded.
- **Country-name alias dictionary** needed: international files use full country
  names (e.g. `France`, `Argentina`) while squads uses 3-letter `nation_code`
  (`FRA`, `ARG`) — reconcile across the 48 WC nations.

---

## On the horizon

- Finish + validate `match_players_to_stats()` fuzzy matching (rapidfuzz).
- **Step 4 — Opponent strength (The Odds API):** get WC outright/group odds for
  all 48 nations → convert to implied probabilities (remove bookmaker
  overround) → normalise to a 0–1 strength score per nation →
  `opponent_strength.csv`. Free tier is rate-limited: fetch once, cache locally.
  Mark needs a key from the-odds-api.com.
- **Step 5 — Fixtures (football-data.org):** pull the 2026 group-stage schedule →
  list each nation's 3 group opponents → `fixtures_2026.csv`. Mark needs a key
  from football-data.org.
- **Step 6 — Merge & score:** join squads + club stats + intl stats on
  player/nation; join fixtures + opponent strength on nation; compute a weighted
  per-player value; output `fantasy_values_2026.csv`. Rough components: club-form
  score, intl-form score, fixture-difficulty multiplier (avg opponent strength
  across 3 group games), position-specific weighting (goals matter more for FW,
  clean sheets for GK). Formula not yet finalised.
- `_flatten_columns()` already in place for the fetchers (see Step 2).

---

## Key decisions & why (don't silently reverse these)

- **Betting odds for opponent strength, not a multi-feature model.** Markets
  already aggregate all relevant info; far fewer moving parts; easier to
  interpret. A goals-for/against + ELO model was considered and rejected. If Mark
  revisits this, push back — odds is the right call.
- **Squad-first pipeline** (not stats-first cross-reference). See architecture.
- **Fuzzy, not exact, name matching.** FIFA PDF and FBref use different
  conventions (accents, name order, abbreviations). Threshold ~85, log <90.
- **Nation code is a more reliable join key than club name** across sources.

---

## Libraries

| Library | Purpose |
|---|---|
| `pdfplumber` | Parse the FIFA squad PDF |
| `soccerdata` + Selenium | Query FBref (Selenium/Chrome, local only) |
| `rapidfuzz` | Fuzzy player-name matching |
| `pandas` | Consolidation, merging, CSV handling |
| `requests` | The Odds API + football-data.org calls |
| `re` (stdlib) | Regex parsing of PDF text |

---

## Watch-outs

1. Wrong venv → `ModuleNotFoundError`. Use `data_pipeline/.venv`.
2. FBref rate limiting — soccerdata caches locally; don't re-fetch needlessly.
3. Fuzzy false positives — threshold too low merges different players. ~85+, log <90.
4. Odds API free-tier limits — fetch once, cache.
5. FIFA PDF format changes — squad parser regex is tuned to the 2026 layout.
6. 48-team format — 12 groups of 4, still 3 group games each; fixture logic same
   as 32-team, just larger scale.
7. Selenium fetchers can't run in Claude's sandbox — run locally.
8. `encoding='utf-8'` on every read.
