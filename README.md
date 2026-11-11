# ProspectMatch

A desktop scouting tool that finds real NBA players matching a custom statistical profile, and explains why each one matches.

> 🇬🇷 Ελληνική έκδοση: [README.el.md](./README.el.md)

## Screenshots

| Home | Search | Prospects |
|---|---|---|
| ![Home screen](docs/screenshots/home.png) | ![Search screen](docs/screenshots/search.png) | ![Prospects screen](docs/screenshots/prospects.png) |

_Screenshots are not added yet; see [`docs/screenshots/`](./docs/screenshots/README.md)._

## Key results

All numbers below were taken from the repository or from running the code on 2026-11-11.

- **Data:** 8,382 player-season rows from 1,589 players (1996-97 to 2024-25), after the minutes filter. 23 features are used for matching.
- **Archetypes:** 18 primitive traits that combine into 36 compound presets (spec in [`ARCHETYPES.md`](./ARCHETYPES.md)).
- **Validation:** 72 hand-labeled players. Trait classifier macro-F1 is **0.605**; the full archetype label matches the expected one for **26 of 72** players (36%). See [Known limitations](#known-limitations) for what this does and does not show.
- **Defensive matching:** before availability-aware matching, defensive queries on tracking-era stats (deflections) returned 0% pre-2016 players. After it, they return 54.7%, against 57.7% pre-2016 share in the dataset ([`validation/DEFENSE_IMPACT.md`](./validation/DEFENSE_IMPACT.md)).
- **Tests:** 73 pytest tests pass (`python -m pytest tests/ -q`).

## What it does

- **Custom profile with weights.** The user picks stats (e.g. TS%, assist %, deflections, height), sets a target value for each, and a priority weight (×1 / ×2 / ×3).
- **Similarity search.** Returns the most similar real player-seasons, one best season per player.
- **Trait boost.** The user can select traits (e.g. `lead_playmaker`, `spot_up_shooter`). Players with those active traits get a small score boost; nobody is excluded.
- **Explainability.** Each match shows which requested stats agree, which diverge and by how much, a radar chart (percentile 0–100, player vs target), and a coverage badge when a match was judged on fewer stats because some data does not exist for that season.
- **Prospect tracking.** Hand-entered prospects (physicals, team, notes) can be linked to NBA comps: the search is prefilled from the prospect's physicals, and result sets can be saved on the prospect.
- **Home screen.** Dataset status, recent prospects, and search history (re-run a past search in one click).
- Position filter and CSV export on the search results.

## How it works

```
nba_api  →  pipeline/fetch_nba_data.py  →  data/nba_stats_full.csv
                                                    ↓
                                         src/preprocessing.py
                                         (normalization, z-scores)
                                                    ↓
                                         src/archetypes.py
                                         (18 primitives → 36 compound presets)
                                                    ↓
                                         src/similarity.py
                                         (weighted L2 matching + explanations)
                                                    ↓
                         ┌──────────────────────────┴──────────────────────────┐
                         ↓                                                       ↓
            backend/ (FastAPI API)                              app/streamlit_app.py
            /similar /classify /stats ...                       (legacy UI, still works)
                         ↓
            frontend/ (React + TS, SVG radar)  ←  wrapped in  →  electron/ (desktop app)
```

The desktop app (Electron + FastAPI + React) is the main interface. The legacy Streamlit UI still works and uses `src/` directly. `src/` is the single shared core: the FastAPI backend wraps it and does not reimplement it, so every interface uses the same matching logic. It changes only with measured justification and a test.

**Compositional archetypes.** Instead of about 10 fixed boxes, there are 18 primitive traits (e.g. `slasher`, `rim_protector`, `lead_playmaker`) that combine into 36 compound archetypes (e.g. `playmaking_big` + `rim_protector` + `help_defender` = "Playmaking Rim Protector"). The same feature space is used for matching.

**Similarity metric.**
- Weighted L2 distance in z-score space, computed only over the stats the user defined. Unspecified stats do not affect the score. The distance is normalized by the sum of weights (weighted RMS), so adding more stats does not by itself lower the similarity.
- `similarity = 1 / (1 + distance)`, in (0, 1].
- L2 rather than cosine, because the question is "find players *close to these values*"; cosine would penalize extreme players on unspecified dimensions.
- **Availability-aware matching.** Hustle stats exist only from 2016-17 and matchup defense (`d_fg3_diff`, `d_rim_diff`) from 2013-14. For each row, the distance uses only the dimensions that have real data, and the score is shrunk toward the population-average similarity in proportion to the share of requested weight that was available (`CONFIDENCE_ALPHA = 1.0`). With full coverage the result is exactly the plain masked score. The share is returned by the API and shown as an "N% data" badge.
- **Trait boost:** +0.004 per shared active trait (a tiebreaker only).

Full trait and preset definitions: [`ARCHETYPES.md`](./ARCHETYPES.md).

## Tech stack

| Layer | Choice |
|---|---|
| Core | Python (`src/`: preprocessing, archetypes, similarity) |
| ML / math | scikit-learn, pandas, numpy |
| Backend API | FastAPI + uvicorn |
| Frontend | React 18 + TypeScript + Vite (raw-SVG radar, no charting library) |
| Desktop shell | Electron + electron-builder |
| Legacy UI | Streamlit (`app/streamlit_app.py`) |
| Data storage | CSV flat file (`data/nba_stats_full.csv`); prospects and search history as JSON files |
| Data source | `nba_api` (box, advanced, scoring, hustle, matchup defense) |

There is no database. Details of the desktop stack: [`DEVELOPMENT.md`](./DEVELOPMENT.md).

## Quick start

**Requirements.** Developed on Python 3.12.1 and Node.js 24.17.0 (the test suite was run on this Python version). No minimum Python version is declared in the repo. The installed Electron 43 requires Node.js ≥ 22.12 and Vite 5 requires Node.js ≥ 18, so use Node.js 22.12 or newer. Python dependencies are listed in `requirements.txt` (legacy UI and data pipeline) and `backend/requirements.txt` (API).

**1. Data (once).** The dataset is not in the repository; see [Data sources and licensing](#data-sources-and-licensing).
```bash
pip install nba_api pandas scikit-learn numpy
python pipeline/fetch_nba_data.py     # → data/nba_stats_full.csv
```

**2. Desktop app (Electron + FastAPI + React).**
```bash
pip install -r backend/requirements.txt
npm install            # root: Electron toolchain + (postinstall) frontend deps
npm run dev            # backend + Vite + Electron together
```
`npm run dev` first frees ports 8000 and 5173 (it stops whatever is listening there). Set `PROSPECTMATCH_NO_KILL=1` to make it report instead. Build and troubleshooting notes: [`DEVELOPMENT.md`](./DEVELOPMENT.md).

**3. Backend only.**
```bash
cd backend && uvicorn main:app --reload      # → http://127.0.0.1:8000/docs
```

**4. Tests** (they need the dataset and are skipped without it).
```bash
python -m pytest tests/ -q
```

**5. Legacy Streamlit UI.**
```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

Prospects and search history are stored in `./.prospectmatch-data/` in development, or in the directory given by the `PROSPECTMATCH_DATA_DIR` environment variable.

## Data sources and licensing

- **`nba_api`** — a Python client for NBA.com statistics endpoints. The pipeline fetches box score and advanced stats (1996-97 onward), scoring profile, hustle stats, and matchup defense (`LeagueDashPtDefend`, 2013-14 onward), plus player height, weight and position.
- **Kaggle NBA Draft Combine (wingspan) — planned, not integrated.** The dataset has no wingspan column and no code reads one. `wingspan_cm` appears only as a planned signal in `ARCHETYPES.md` and in code comments.

The CSV is **not in git** (`data/` is gitignored). To regenerate it, run `python pipeline/fetch_nba_data.py`. The script calls the API with rate-limit pauses, and the per-player calls (about 2,500) take roughly an hour; it can resume from a checkpoint if interrupted.

**License.** The code in this repository is released under the [MIT License](./LICENSE). That license covers the code only, not the data.

**Terms of use.** This repository does not state or grant any license for the data. Anyone who fetches, stores or redistributes the data must check the terms of use of NBA.com / `nba_api` and of Kaggle themselves. In particular, `npm run dist` copies `data/nba_stats_full.csv` into the installer, so do not distribute built installers without checking those terms first.

## Known limitations

- **Defense is weakly captured by box-score stats.** The defensive traits have the most errors in validation. This is documented here, not hidden.
- **Versatile wing defense is not measurable from the available stats.** The `versatile_wing_defender` trait has recall 0.450 (precision 0.692) on the validation set. `deflections` measures style (ball-hawking), not quality: Mikal Bridges, an elite on-ball defender who does not gamble, has 1.71, while Luka Doncic, a known poor defender, has 3.38. The distributions overlap, and removing `deflections` drops recall to 0.05. Matchup data (`d_fg3_diff`) was added and helps `point_of_attack_defender` (F1 0.385 → 0.476), but adding it to `versatile_wing_defender` was neutral or slightly negative.
- **Archetype labeling is only partly accurate.** The top-1 label matches the expected one for 26 of 72 validation players. About 8 of the misses come from trait-count dominance in the label tie-break (a smaller preset is always a subset of a larger one), which the project could not fix by reordering presets. A score-weighted tie-break was tried and made results worse (see the changelog). At the current threshold, 15.0% of rows get no label and 29.3% get a fallback noun-plus-modifier label.
- **The validation set is small and not held out.** Labels come from the example players in `ARCHETYPES.md`. Thresholds and signals were tuned and checked against the same 72 players, so the scores above are not an independent test.
- **Several features are missing for older seasons.** Hustle stats are only available from 2016-17 (the 2015-16 season is discarded because its data is corrupt); matchup defense only from 2013-14. Older rows are handled with the availability-aware masking described above, which makes those matches rest on fewer stats; the coverage badge shows this. It does not recover the missing information.
- **`stl` and `blk` are counting stats.** They are not per-36 normalized: `corr(stl, min) = +0.64`, while rebounding is already rate-adjusted.
- **Missing stats by design.** VORP, PER and WS/48 are Basketball-Reference exclusives and are not included. Athleticism measurements (e.g. vertical) are out of scope.
- **NBA only,** and the packaged desktop build currently falls back to a system Python install for the backend.

Design principles: accuracy and a stated reason for each feature and weight; similarity masked to the stats the user defines; limitations documented rather than hidden; extensible to other leagues without over-engineering the present.

## Status and roadmap

This is a thesis project in progress. The NBA pipeline, matching engine, desktop app, prospect tracking and test suite work. Open items:

- Classifier tuning (archetype top-1 accuracy)
- Per-36 normalization of `stl` / `blk`
- Self-contained bundle (PyInstaller backend executable)
- Multi-league support (NCAA, G-League, EuroLeague, EuroCup)

## More documentation

- [`ARCHETYPES.md`](./ARCHETYPES.md) — the 18 primitives and 36 compound presets
- [`DEVELOPMENT.md`](./DEVELOPMENT.md) — architecture, setup, run and build of the desktop stack
- [`CHANGELOG.md`](./CHANGELOG.md) — detailed project log, including negative results
