# Methodology

A full account of how a player's expected fantasy points are computed, and why each
modelling choice was made. The guiding principle is **interpretable components over a
black box**: every number a user sees can be traced back to an assumption stated here.

---

## 0. Notation

For a player *p* in a single match against opponent *o*:

- `m` — minutes played (a random variable)
- `λ_g`, `λ_a` — expected goals / assists (Poisson rates)
- `R_t`, `R_o` — 0–100 strength ratings of the player's team and the opponent
- `S(·)` — the fantasy scoring function

Expected points is `xP = E[ S(outcome) ]`, estimated by Monte-Carlo.

---

## 1. Matching: getting stats onto the right player

The squad list (from a FIFA PDF) and the stats (from FBref) disagree on spelling:
the PDF yields garbled, duplicated ALL-CAPS names (`MASTIL Melvin Melvin Feycal MASTIL
MASTIL`) while FBref is clean (`Melvin Mastil`), sometimes accented. Three separate
nation encodings (FIFA codes, FBref codes, full names) compound it.

**Approach.** Normalise names (strip accents → ASCII, lower-case, drop punctuation),
**block by nation** so each comparison is against ~26 candidates, and fuzzy-match with
`rapidfuzz` **`token_set_ratio`** — which ignores duplicate tokens and word order, exactly
the failure mode of the PDF names. A threshold of 85 accepts a match; anything under 90 is
logged for review. On real data this matches every marquee player at 100 and flags only a
handful of genuine edge cases (e.g. *Marco* vs *Mario Pašalić*).

Club and international stats are attached as **separate, source-tagged columns** — never
pre-averaged — so the model controls the blend.

---

## 2. Rate estimation with empirical-Bayes shrinkage

Counting stats are pooled across two club seasons and two World Cups with recency
weights (latest season ×1.0, prior ×0.6; latest tournament ×1.0, prior ×0.5) and World
Cup minutes up-weighted ×1.5 for level-of-competition relevance.

A raw per-90 rate is then **shrunk toward a position baseline**:

```
rate_hat = (events + K · baseline) / (nineties + K),   K = 8
```

`baseline` is the minutes-weighted per-90 mean for that position, **learned from the
matched pool itself** (empirical Bayes), so it adapts to the data rather than being hard-
coded. `K` acts as `K` matches of prior belief: at 8 nineties a player is half baseline,
half themselves; by 30+ nineties they are essentially their own rate. Rare events (reds,
own goals, penalties won/missed) use small fixed priors with a lighter `K`.

*Why this matters:* it is the single most important guard against overfitting small
samples — the classic "3 goals in 200 minutes ≠ a 1.35-per-90 striker" trap.

---

## 3. Minutes model

No pitch time, no points. From club playing time we derive:

- `p_start` — start probability, `0.65 · club_start_share + 0.35 · caps_factor`
  (caps stand in for players with little Big-5 data), clipped to [0.02, 0.98];
- `p_play` — start probability plus a bench-appearance term;
- `p_60` — probability of lasting the 60-minute mark (which gates the appearance bonus,
  clean-sheet points and conceded penalties).

Minutes when playing are drawn from the player's club minutes-per-appearance.

---

## 4. Team match model

Nation strength `R` is mapped to expected goals with a Poisson/Elo form:

```
edge      = β · (R_t − R_o) / scale                (β = 0.25, scale = 10)
goals_for     = BASE · exp(+edge)                  (BASE = 1.35 ≈ intl average)
goals_against = BASE · exp(−edge)
```

clamped to `[0.15, 4.5]`. From this:

- **clean-sheet probability** = `P(Poisson(goals_against) = 0) = exp(−goals_against)`;
- **attack multiplier** = `goals_for(vs o) / goals_for(vs average opponent)` — this scales
  a player's individual output up or down by fixture while holding their *share* of team
  output fixed.

### Strength ratings from the betting market
Where the market prices a team, ratings come from **live World Cup outright-winner odds**
(The Odds API). Decimal odds → raw implied probability `1/odds`, summed and divided out to
**remove the bookmaker margin** (overround), then compressed with a cube-root (title
probability is hugely skewed to favourites) and **calibrated onto the prior scale**
(anchored to the mean and spread of those same teams' priors) before a 50/50 blend. Teams
the market does not price keep their prior. This is the design the brief asked for: markets
first, priors as the reproducible fallback.

---

## 5. Monte-Carlo simulation

For each of a player's three group fixtures we run **4,000 simulations**, vectorised in
numpy:

1. draw a minutes bucket (DNP / 1–59 / 60+) from `p_play`, `p_60`;
2. draw goals ~ `Poisson(rate_g · minute_share · attack_mult)`, assists likewise;
3. draw clean sheet ~ `Bernoulli(cs_prob)` if 60+, goals conceded ~ `Poisson(goals_against)`;
4. draw cards, own goals, penalties won/missed;
5. score the game under the fantasy rules.

The mean is **xP**; the 10th and 90th percentiles are the **floor** and **ceiling**; the
share of games ≥ 9 points is the **haul probability**. Reporting the distribution rather
than a point estimate is what lets the tool distinguish a steady 5-point defender from a
volatile forward with the same mean.

Group-stage xP is the sum over the three fixtures.

---

## 6. Value and squad optimisation

**Value** = group-stage xP ÷ price. Prices are the official game's where scrapeable, else
**synthetic** — built from attacking output, minutes and reputation (how a real game prices),
deliberately *not* from our own xP, so value still rewards the model's fixture/position/
minutes edge rather than being circular.

The **squad optimiser** maximises total group-stage xP over a 15-player squad
(2 GK / 5 DF / 5 MF / 3 FW) subject to a budget and ≤ 3 players per nation — a
multi-constraint knapsack. It is solved by:

1. **Lagrangian relaxation.** Score each player `group_xp − λ · price` and greedily fill
   the positional slots (respecting the nation cap). Sweeping λ traces the price/points
   efficient frontier; every λ yields a different budget-feasible candidate squad.
2. **Multi-start local search.** Polish a spread of those candidates with 1-for-1 upgrade
   swaps and keep the best starting XI. Starting from *cheaper* frontier squads leaves
   budget for polish to buy premium-value players — which escapes the local optimum where a
   naive greedy spends its whole budget on mediocre players.

The result is near-optimal and fast enough to re-solve on every budget-slider tick.

---

## 7. Known limitations

- 2022 fantasy scoring stands in for the unpublished 2026 ruleset (one config file).
- No goalkeeping-save data in the fetched stat types → GK scoring omits save points.
- Club stats are Big-5 only; other leagues lean on international form + baselines.
- The match model treats fixtures independently and stops at the group stage.

None of these are hidden in the output: the dashboard labels the price source, and every
player panel exposes the underlying rates, start probability and team rating.
