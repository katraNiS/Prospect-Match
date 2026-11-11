# Changelog / Project log

Detailed development history of ProspectMatch, grouped by theme. This is a
project log rather than a release changelog: the project has no versioned
releases yet. It was moved out of the README to keep the README short; the
original Greek checklist is still available in [`README.el.md`](./README.el.md).

Notes on sourcing:
- Entries come from the "Κατάσταση project" checklist of the Greek README. A few
  entries marked *(from CLAUDE.md)* come from the more detailed status section of
  `CLAUDE.md`, which documents work (including negative results) that the README
  checklist only summarised or did not list.
- Numbers are kept as they were recorded at the time of each change. Where a
  later value differs, it is noted explicitly.

---

## Data pipeline

- [x] **Idea and scope** — NBA-only first. Multi-league support is deferred, but the design must allow it without a rewrite.
- [x] **API exploration** — the exact fields provided by `nba_api` were mapped out before building the pipeline.
- [x] **Data pipeline** (`pipeline/fetch_nba_data.py`) — box/advanced + scoring (`PCT_PTS_2PT_MR` etc.) + hustle (deflections etc.)
      + **defensive impact** (DFG% per zone: overall / 3PT / rim, from `LeagueDashPtDefend`, 2013-14+).
- [x] **Phase 1d — defensive impact fetch** *(from CLAUDE.md)* — `LeagueDashPtDefend`, 36 calls (3 categories × 12 seasons).
      Output: `data/seasons_defense.csv` (6315 rows, 2013-14 → 2024-25), merged into `nba_stats_full.csv`
      (55 → **67 columns**, 13987 rows unchanged). Coverage in the final dataset: **45.1%** (pre-2013 rows are NaN).
      The merge was verified to be functionally neutral: all 21 `FEATURE_COLS` byte-identical at the time, macro-F1 0.600 and
      archetype top-1 21/72 unchanged, 56 tests passing. The new columns just sit in the CSV; `preprocess()` ignores anything
      that is not in `FEATURE_COLS`.
      `d_ovr_diff` is era-stable without correction (unlike `def_rating`): `corr(d_ovr_diff, year) = −0.009`, season spread
      0.0096 vs within-season std 0.0744 (13%; `def_rating` was 364% before centering). `d_rim_diff` is slightly era-dependent
      (corr −0.128, ratio 42%).
      Small-sample noise: `std(d_ovr_diff)` drops 0.076 → 0.037 with `d_ovr_fga ≥ 6`; the extreme values (±0.674) come from rows
      with very few contested attempts.

## Matching engine

- [x] **`src/preprocessing.py`** — normalization, tiered MPG filter, z-scores.
- [x] **`src/similarity.py`** — weighted L2 matching, trait boost, explanations.
- [x] **Scale-invariant similarity** — weighted RMS instead of a raw sum, which avoids distance compression when many stats are specified.
- [x] **Defensive matching fixes** — three structural problems that made defensive queries unreliable:
      (a) the 2015-16 season had corrupt hustle data (a partial-season sample on the wrong scale) and dominated every
      query — 5/10 → 0/10 results from corrupt rows;
      (b) `def_rating` was missing from `FEATURE_COLS` although the classifier already used it — it was added with
      season-relative centering, because it is era-dependent (corr 0.62 with the season);
      (c) hustle stats are missing before 2016-17, so imputation de facto excluded 56% of the dataset from every
      defensive query (**0%** pre-2016 results).
      *(from CLAUDE.md)* Details: with season-relative centering, pre-2016 representation went from 84% (era selector) to
      63%, within the range of the offensive controls. Defensive queries went from **0% → 48-84%** pre-tracking representation;
      classifier macro-F1 at the best threshold 0.607 → 0.623; `versatile_wing_defender` F1 0.424 → 0.486,
      `rim_protector` 0.769 → 0.800.
- [x] **Availability-aware matching** — the distance is computed only over the dimensions that have real data for each
      player, with a confidence discount so rows with missing data do not displace rows with complete data.
      Defensive queries: **0% → 54.7%** pre-2016 representation (baseline 57.7%), with zero regression on offensive
      queries. The UI shows an «N% data» badge where a match was judged on fewer stats.
- [x] **Matchup-based defensive impact in the engine** — `d_fg3_diff` (perimeter) and `d_rim_diff` (rim) were added to
      `FEATURE_COLS`: the user can now ask for "good perimeter defense" or "rim protection" based on what opponents shoot,
      not on the defender's style.
      In the classifier: `point_of_attack_defender` F1 0.385 → 0.476, archetype top-1 21/72 → 22/72.
      *(from CLAUDE.md)* `FEATURE_COLS` 21 → **23**. `d_fg3_diff` and `d_rim_diff` were chosen because they are nearly
      orthogonal (corr −0.01); `d_ovr_diff` was left out (a mix of the two, 0.44/0.60, and already corr 0.43 with `def_rating`).
      After the MPG filter 100% of rows have `d_ovr_fga ≥ 3` and std fell 0.076 → 0.031, so no volume filter was needed.
      Measured negative results (tried, not kept): `d_rim_diff` in `rim_protector` drops F1 **0.800 → 0.710** (`blk` already
      covers it, and the 44% imputed values add noise because the classifier has no availability masking); `d_fg3_diff`
      in `versatile_wing_defender` is neutral or −1 in top-1.

## Classifier and validation

- [x] **Archetype design** — 18 primitives + 36 compound presets (`src/archetypes.py`; spec in `ARCHETYPES.md`).
- [x] **`src/archetypes.py`** — trait signals + compound presets + classifier.
- [x] **Position-aware preset matching** (`PRESET_POSITIONS`) — fixes misclassification (e.g. Porzingis → "Slashing Guard").
- [x] **Validation: 20 known players** (stars + role players) — archetypes and similarity.
- [x] **Validation harness** (`validation/`) — 72 labeled players, per-trait precision/recall/F1, threshold sweep → `REPORT.md`.
- [x] **Classifier eval hardening** — the validation ground truth (`validation/labels.py`) was fixed so it no longer
      penalises legitimate secondary traits of multi-dimensional players; macro-F1 0.494 → 0.601 (+22%), with no changes
      to `src/`.
      *(from CLAUDE.md)* `labels.py` did not use the `ignore` field at all although `evaluate.py` supports it. A dataset
      query showed that almost all "false positives" of the worst traits were real, documented secondary skills (e.g.
      Rudy Gobert as an elite `efficient_finisher` through rim finishing). `ignore` was added for score ≥ 0.8 plus a
      documented skill. Eligibility broadening for `lead_playmaker` / `versatile_wing_defender` / `movement_shooter`
      was also tried: negligible gain in archetype top-1 (+1/72) with a small macro-F1 loss, so it was not kept.
- [x] **`TRAIT_THRESHOLD` re-tuning (investigated, not changed)** *(from CLAUDE.md)* — `REPORT.md` shows the best macro-F1 at
      0.9 (0.623 vs 0.597 at the time), but the metric is blind: the 72 labeled stars have 6-10 active traits and never become
      Unclassified. Measured over the whole dataset, 0.9 leaves **32% of players without a label** (up from 15%) and removes
      4 archetypes, with the **same** archetype top-1 (20/72). Per-trait optima conflict (0.4 to 0.95), and per-trait
      thresholds would be overfitting to a support of 4-5 players. `tune_threshold.py` now also prints the usability columns.
- [x] **Archetype triage** (`validation/triage_archetypes.py`) — categorises misclassifications to separate technical bugs
      from ground-truth decisions. It led to two fixes: `versatile_wing_defender` rewarded *size* (6/8 false positives were
      centers) → precision 0.529 → 0.692; and the "3-and-D Wing" preset was structurally unreachable (0 uses in 8382 rows)
      because it lost a tie to "3-and-D Guard" → 21 G-F wings received a wrong "Guard" label.
      *(from CLAUDE.md)* Measured Cohen's d expected-vs-false-positive for the old signals: `reb_pct` −1.80, `screen_assists`
      −1.59, `height_cm` −1.39, all opposite to the hypothesis. Inverting them and adding `screen_assists` raised F1
      0.486 → 0.545.
- [x] **`_label_archetype()` tie-break fixes** — diagnosis showed that 17/50 misses (34%) are due to the tie-break rule
      (the preset with the most active traits), not to missing traits. Three dict-order fixes for equal-size ties
      (`Stretch Rim Protector` before `Stretch Big`; `Wing Scorer` before `Scoring Lead Guard`; `Point Forward` before
      `Two-Way Lead Guard`) fixed 4 misses with no regression — archetype top-1 **22/72 → 26/72**. Two more pairs were
      tried but were 1-for-1 trades (net 0) and were **not** applied. The remaining 8 misses are genuine trait-count
      dominance (the smaller preset is always a subset of the larger one) — a fundamental issue in the tie-break
      criterion, not fixable by reordering. Details in `CLAUDE.md`.
- [x] **`slasher` signal tuning — negative result, not kept** *(from CLAUDE.md)* — the triage showed `slasher` as the #2
      trait cause of misses (8/72). The `fg3a` signal (weight −1.0) penalises modern combo guards/wings who slash *and*
      take many threes. Four variants were tried (reduced/zeroed `fg3a` weight, `pct_pts_paint` as a positive signal):
      per-trait F1 improves (0.364 → 0.54–0.59, recall 0.333 → 0.58–0.92), but archetype top-1 **drops** (22/72 → 18-20/72).
      0/8 targeted misses were fixed at top-1, plus 2 new regressions (Trae Young, Bam Adebayo).
- [x] **Score-weighted tie-break — negative result, not kept** *(from CLAUDE.md)* — mean trait-score as a replacement for
      raw trait-count. (a) As the primary criterion: top-1 22/72 → 18/72; 13.4% of rows (1122/8382) changed label;
      `Rim-Running Anchor` 554 → 24 uses; `Bucket-Getter` became unreachable (123 → 0). (b) Only as a tertiary tie-break
      for equal-size ties: top-1 26/72 → 22/72; 9.4% (788/8382) of rows changed label. The per-pair, measured dict-order
      fixes were better than any general formula tried.
- [x] **Test suite** (`tests/`) — 64 pytest tests at the time of this entry (73 as of the latest run, after the serialization
      tests were added): data integrity, era balance, discriminative power, threshold usability, preset reachability,
      metadata consistency.
- [ ] **Classifier tuning: archetype top-1 accuracy** (a separate, harder problem — see `CLAUDE.md`). Documented limit:
      *versatile wing defense* is not measurable from the available stats — `deflections` measures style (ball-hawking),
      not defensive quality.
      *(from CLAUDE.md)* Example: Mikal Bridges (elite on-ball defender, does not gamble) has 1.71 deflections while Luka
      Doncic (a known poor defender) has 3.38. Distributions overlap fully, and removing `deflections` drops recall to 0.05.
      Matchup / DFG% / contested-shot data would be needed.
- [ ] **Per-36 normalization of `stl`/`blk`** (currently counting stats while rebounding is rate-adjusted).
      *(from CLAUDE.md)* `corr(stl, min) = +0.64`; per-36 drops it to +0.08.

## Desktop app and UI

- [x] **`app/streamlit_app.py`** — working Streamlit UI (legacy, still functional).
- [x] **Radar chart** (percentile 0–100) — StatsBomb-style, player vs user target, `plotly` (Streamlit UI).
- [x] **FastAPI backend** (`backend/`) — initially 6 endpoints (`/similar`, `/classify`, `/stats`, `/archetypes`, …), wrapping `src/` unchanged.
      (Prospect and search-history routes were added later; see `DEVELOPMENT.md` for the current list.)
- [x] **React frontend** (`frontend/`) — stat builder + result cards + radar (TypeScript).
- [x] **Electron desktop app** (`electron/`) — `npm run dev` (backend + frontend + electron together), `npm run dist`.
- [x] **Routing + multiple screens** — `react-router-dom` (`HashRouter`), Home / Search / Prospects screens.
- [x] **Prospect tracking** — CRUD for hand-entered prospects (JSON store, `PROSPECTMATCH_DATA_DIR`).
- [x] **Prospect ↔ NBA comps** — prefill the search from prospect physicals, save/delete results.
- [x] **Home screen + search history** — dataset status, recent prospects, latest searches (re-run with one click).
- [x] **UI polish** — position filter + CSV export of results (client-side, in the search screen).
- [x] **UI rebuild — "Industry dark"** — dark-mode-first, data-dense redesign of all 4 screens:
      stat builder with a **real league histogram** per stat, match table with coverage cells and an expandable
      breakdown, raw-SVG radar overlay (Recharts removed, bundle ~600 KB → 219 KB).
      The implementation exposed three presentation errors that the previous UI hid — a breakdown with features
      that were not requested, imputed values shown as measured, and label shortcuts that produced "cm" instead of
      "Height". All fixed and locked in with tests.
      *(from CLAUDE.md)* The fixes are in the serialization layer (`backend/engine.py`, `src/` unchanged) and are covered
      by `tests/test_api_serialization.py` (64 → **73 tests**): (a) the breakdown showed features the user did not request
      (`explain_match()` fills top_n=4 via argsort over all features) and the same feature twice (matching ∩ diverging ≠ ∅);
      (b) imputed values were presented as measured — a new per-entry `available` flag; (c) client-side `shortLabel` guessed
      with a regex — a new `SHORT_LABELS` in `metadata.py` is now the single source of truth. `/stats` now serves real
      distributions (24-bin histogram + 101 quantiles per feature, measured only on non-imputed rows).

## Documentation

- [x] **`ARCHETYPES.md` sync** — 29 → 36 presets, real players confirmed against the dataset.

## Open items

- [ ] Classifier tuning (see above).
- [ ] Per-36 normalization of `stl`/`blk` (see above).
- [ ] Self-contained bundle (PyInstaller backend exe; currently falls back to system Python).
- [ ] Multi-league support (NCAA, EuroLeague, etc.).
