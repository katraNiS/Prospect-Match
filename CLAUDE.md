# NBA Scouting Tool — CLAUDE.md

## Τι είναι το project

Scouting εργαλείο (όχι quiz). Ο χρήστης ορίζει ένα **custom player profile** —
stats + βάρη ανά stat + επιθυμητά traits — και το σύστημα επιστρέφει τους
**πιο όμοιους πραγματικούς παίκτες** από τη βάση, με explainability.

Πτυχιακή. Προτεραιότητα στην **ακρίβεια και τη λογική τεκμηρίωση** κάθε
απόφασης — όχι σε γρήγορες λύσεις χωρίς αιτιολόγηση.

**Scope τώρα:** μόνο NBA. Η επεκτασιμότητα (NCAA, G-League, EuroLeague, EuroCup)
έρχεται αργότερα — το design πρέπει να την επιτρέπει χωρίς rewrite.

## Συνοδευτικά αρχεία τεκμηρίωσης

- `README.md` — human-facing επισκόπηση (στόχοι, status, roadmap).
- `ARCHETYPES.md` — **ΤΟ ΠΛΗΡΕΣ SPEC των archetypes** (18 primitives + 36 compounds
  με signals & players, real players επιβεβαιωμένα πάνω στο dataset). Συμβουλέψου το
  όταν αγγίζεις `src/archetypes.py`.
- `DEVELOPMENT.md` — architecture + setup/run/build του desktop stack (Electron+FastAPI+React).
- `PHASE_PROMPTS.md` — τα 5 phase prompts (0–4) που έχτισαν prospects/home screen· historical πλέον, όλα [DONE].
- `CLAUDE.md` (αυτό) — οδηγίες/context για το Claude Code.

---

## Tech Stack

- **Language (core + backend):** Python
- **Backend API:** FastAPI + uvicorn (`POST /similar`, `/classify`, `GET /stats`, `/archetypes`, …)
- **Frontend:** React 18 + TypeScript + Vite. Wrapped σε **Electron** desktop app.
  Το radar είναι **raw SVG** (`components/RadarChart.tsx`) — το Recharts αφαιρέθηκε στο
  Phase 12: το ίδιο component πρέπει να διαβάζεται και στα 84px (μέσα σε γραμμή πίνακα)
  και στα 252px (expanded row), και σε αυτά τα μεγέθη ticks/tooltips/legends είναι θόρυβος
  που δεν χωράει. Bundle 219 KB (από ~600 KB).
- **Legacy UI:** Streamlit (`app/streamlit_app.py`) — δουλεύει ακόμα ανεξάρτητα, δεν καταργήθηκε.
- **Data storage:** CSV flat file (`data/nba_stats_full.csv`) — χωρίς DB προς το παρόν.
  Τα user-created δεδομένα (prospects, search history) είναι ξεχωριστά: JSON flat files
  σε resolved data dir (βλ. `backend/store.py` και ενότητα "Prospect & search history storage").
- **ML/Math:** scikit-learn, pandas, numpy
- **Data sources:** nba_api — box/advanced/scoring/hustle + LeagueDashPtDefend (DFG%)

> Δεν υπάρχει PostgreSQL/SQLAlchemy στο παρόν στάδιο. Τα `db/` αρχεία είναι
> legacy από πρώιμο design — αγνόησέ τα.

> **ΚΡΙΣΙΜΟ constraint:** ο FastAPI backend **δεν μεταλλάσσει** το `src/`
> (preprocessing/archetypes/similarity) — το _wrap-άρει_ προσθέτοντάς το στο
> `sys.path` (βλ. `backend/engine.py`). Το `src/` παραμένει το single source of
> truth του matching, ώστε Streamlit / API / μελλοντικά leagues να μοιράζονται
> ακριβώς την ίδια λογική.
>
> Αυτό ΔΕΝ σημαίνει ότι το `src/` είναι παγωμένο. Σημαίνει ότι αλλάζει μόνο με
> **μετρημένη αιτιολόγηση** — διάγνωση πάνω στο dataset, before/after νούμερα,
> και test που κλειδώνει το αποτέλεσμα (βλ. Phase 8-9 και `tests/`). Κάθε αλλαγή
> στα `FEATURE_COLS` αλλάζει το feature space: τα αποθηκευμένα comps και το
> validation baseline πρέπει να ξανατρέξουν.
> Setup/run του desktop stack: βλ. **`DEVELOPMENT.md`**.

---

## Αρχιτεκτονική — Layers

```
[ Data Layer ]        → nba_api endpoints → CSV
      ↓
[ Processing Layer ]  → normalization, z-scores, tiered MPG filter        ┐
      ↓                                                                    │ src/ = single source
[ Archetype Layer ]   → 18 primitive traits → classifier → 36 compounds   │ = single source
      ↓                                                                    │   of matching logic
[ Matching Engine ]   → weighted L2 distance + trait boost + explanations ┘
      ↓
[ API Layer ]         → FastAPI (backend/) — wrap-άρει το src/, serialize σε display-ready JSON
      ↓
[ Client Layer ]      → React SPA (frontend/) — stat builder, match table, SVG radar
      ↓
[ Desktop Shell ]     → Electron (electron/) — spawn-άρει backend, φορτώνει το React UI
```

Παράλληλα: **Streamlit** (`app/streamlit_app.py`) καταναλώνει το `src/` απευθείας
(χωρίς το API) — legacy αλλά λειτουργικό.

---

## Project structure (τρέχουσα)

```
ProspectMatch/
├── README.md
├── CLAUDE.md                  ← αυτό
├── ARCHETYPES.md              ← spec archetypes [DONE]
├── DEVELOPMENT.md             ← setup/run/build του Electron+FastAPI+React stack [DONE]
├── package.json               ← root: `npm run dev` (concurrently) + `npm run dist` (electron-builder)
├── data/
│   └── nba_stats_full.csv     ← merged dataset, 13987×67 (~8.3k rows μετά MPG filter· δεν είναι στο git)
├── pipeline/
│   └── fetch_nba_data.py      ← 4-phase fetch: base+advanced / scoring / hustle / defense [DONE]
├── src/                       ← κοινός πυρήνας (ο backend το wrap-άρει, δεν το αλλάζει)
│   ├── preprocessing.py       ← load/clean/normalize, FEATURE_COLS, preprocess() [DONE]
│   ├── archetypes.py          ← 18 traits + signals + 36 compound presets + classify() [DONE]
│   └── similarity.py          ← find_similar(), explain_match() [DONE]
├── backend/                   ← FastAPI wrapper — δεν αλλάζει το src/ [DONE]
│   ├── main.py                ← app + lifespan (load dataset once) + routes + CORS
│   ├── engine.py              ← src/ στο sys.path· serialize σε display-ready JSON
│   ├── metadata.py            ← UI config (ranges/labels) + display↔internal ×100/÷100
│   ├── schemas.py              ← Pydantic request models (SimilarRequest, Prospect*, Comp*, ...)
│   ├── store.py                ← JSON repo για prospects.json + searches.json (atomic write, lock) [DONE]
│   └── run_server.py          ← prod entry (χωρίς --reload)
├── frontend/                  ← React + TS + Vite [DONE]
│   └── src/
│       ├── api.ts, types.ts   ← typed fetch client + response/request interfaces
│       ├── App.tsx            ← shell: title bar + dataset status strip + tab bar + routes [DONE]
│       ├── styles.css         ← Industry dark design system (tokens + όλες οι κλάσεις) [DONE]
│       ├── MetaContext.tsx    ← /stats fetched μία φορά, useMeta() hook [DONE]
│       ├── statFormat.ts      ← format/short label/percentile lookup — ένα σημείο [DONE]
│       ├── prospectUtils.ts   ← deriveAge, prospectFullName, toFromProspectPrefill [DONE]
│       ├── units.ts           ← kg→lbs (μοναδικό σημείο μετατροπής) [DONE]
│       ├── csv.ts             ← client-side CSV export (με coverage_pct) [DONE]
│       ├── screens/           ← HomeScreen, SearchScreen, ProspectsScreen, ProspectFormScreen [DONE]
│       └── components/        ← StatBuilder, ResultRow, RadarChart (SVG), Coverage
├── electron/                  ← desktop shell [DONE]
│   ├── main.cjs               ← spawn backend (env: PROSPECTMATCH_DATA_DIR=userData) → wait /health → load frontend/dist
│   └── preload.cjs
├── validation/                ← classifier validation harness [WIP]
│   ├── labels.py              ← 72 ground-truth παίκτες → canonical archetype (από ARCHETYPES.md)
│   ├── matching.py            ← accent/punct-tolerant name → row resolver
│   ├── evaluate.py            ← per-trait P/R/F1, macro-F1, archetype top-1, structural misses
│   ├── tune_threshold.py      ← score once → sweep threshold → REPORT.md
│   ├── REPORT.md              ← generated metrics snapshot
│   ├── defense_impact.py      ← era balance / corrupt-season / def_rating impact [DONE]
│   ├── DEFENSE_IMPACT.md      ← generated defensive-matching snapshot
│   ├── triage_archetypes.py   ← κατηγοριοποίηση misses: bug vs ground-truth [DONE]
│   └── TRIAGE.md              ← generated triage snapshot
├── tests/                     ← pytest suite (73 tests) [DONE]
│   ├── conftest.py            ← session-scoped fixtures· skip αν λείπει το dataset
│   ├── test_defensive_features.py  ← data integrity: corrupt σεζόν, def_rating, metadata sync
│   ├── test_defensive_matching.py  ← behaviour: era balance, discriminative power
│   ├── test_archetype_presets.py   ← preset reachability + signal directions
│   └── test_api_serialization.py   ← τι *δείχνει* το API: breakdown scope, per-stat
│                                     availability vs coverage, κατανομές του /stats
└── app/
    └── streamlit_app.py       ← Streamlit UI (legacy, λειτουργικό) [DONE]
```

Τρέξε τα harnesses (measurement-only, δεν αλλάζουν το `src/`):
```bash
python validation/tune_threshold.py
```
```bash
python validation/defense_impact.py
```
```bash
python validation/triage_archetypes.py
```
```bash
python -m pytest tests/ -q
```

---

## Data pipeline (`pipeline/fetch_nba_data.py`)

3 phases:

**Phase 1a — Base + Advanced** (`LeagueDashPlayerStats`, measure_type="Base" + "Advanced"):
- Box: `pts`, `reb`, `ast`, `stl`, `blk`, `tov`, `oreb`, `dreb`, `min`, `gp`
- Advanced: `ts_pct`, `usg_pct`, `ast_pct`, `oreb_pct`, `dreb_pct`, `net_rating`, `efg_pct`, `ast_to`, `reb_pct`
- `CommonPlayerInfo` → `height_cm`, `weight_lbs`, `position`

**Phase 1b — Scoring** (`LeagueDashPlayerStats`, measure_type="Scoring"):
- `pct_pts_2pt_mr` (API: `PCT_PTS_2PT_MR`) — % points from mid-range, κρίσιμο για midrange_scorer
- `pct_fga_3pt`, `pct_pts_3pt`, `pct_pts_paint`, `pct_pts_ft`, `pct_uast_2pm`

**Phase 1c — Hustle** (`LeagueHustleStatsPlayer`, **αξιόπιστα από 2016-17+**):
- `deflections`, `charges_drawn`, `box_outs`, `screen_assists`
- Παλαιότερες σεζόν: NaN → group median
- **Το 2015-16 απορρίπτεται** (`preprocessing.CORRUPT_HUSTLE_SEASONS`): είναι η
  σεζόν που ξεκίνησε το hustle tracking, mid-season· μόνο 147/476 rows έχουν
  τιμές και είναι partial-season sample, όχι averages (89.8% ακέραιες,
  max 11.00 deflections/gm έναντι ~4-5 κάθε άλλης σεζόν).
- Το group-median imputation δίνει z ≈ 0 που είναι neutral **μόνο όσο ο χρήστης
  δεν ορίζει το stat**. Γι' αυτό το `load_and_clean()` καταγράφει `avail_<col>`
  boolean στήλες **πριν** από κάθε fillna — τις καταναλώνει το
  availability-aware masking του `similarity.py` (βλ. παρακάτω).

**Phase 1d — Defensive impact** (`LeagueDashPtDefend`, **2013-14+**):
Τι σουτάρουν οι αντίπαλοι όταν ο παίκτης είναι ο **κοντινότερος defender**.
Τρεις categories × 12 σεζόν = 36 calls → `data/seasons_defense.csv`.

| Category | Στήλες | Χρήση |
|---|---|---|
| `Overall` | `d_ovr_fga/pct/base/diff` | γενικό defensive impact |
| `3 Pointers` | `d_fg3_*` | perimeter defense |
| `Less Than 6Ft` | `d_rim_*` | rim protection |

Το `_diff` (API: `PCT_PLUSMINUS`) είναι το χρήσιμο σήμα: πόσο **χειρότερα**
σουτάρουν οι αντίπαλοι σε σχέση με τον κανονικό τους μέσο όρο. Είναι ήδη
baseline-adjusted → λιγότερο team/era-dependent από το raw DFG%.
**Αρνητικό = καλή άμυνα.**

Γιατί προστέθηκε: το `deflections` μετράει *στυλ* άμυνας (ball-hawking), όχι
ποιότητα. Μετρημένο στο 2023-24: `corr(deflections, d_ovr_diff) = +0.017` —
σχεδόν **ορθογώνια πληροφορία**. Ο Aaron Gordon (deflections 1.38, από τους
misses του `versatile_wing_defender`) βγαίνει 2ος καλύτερος με `d_ovr_diff`
−0.054· ο Gobert `d_rim_diff` −0.134· ο Herbert Jones `d_fg3_diff` −0.060.

⚠️ Κάθε category επιστρέφει **διαφορετικά** column names (`D_FG_PCT` vs
`FG3_PCT` vs `LT_06_PCT`) — κανονικοποιούνται στο `DEFEND_CATEGORIES` dict.
Το `FG3_PCT` **πρέπει** να μετονομαστεί: συγκρούεται με το offensive `fg3_pct`.
Επίσης το endpoint κλειδώνει στο `CLOSE_DEF_PERSON_ID`, όχι `PLAYER_ID`.

**Rate limiting:** `time.sleep(1.5)` ανά call. Trade dedup: κράτα row με max games.

---

## Data format — ΚΡΙΣΙΜΟ

Τα παρακάτω αποθηκεύονται ως **fractions (0.0–1.0)**, ΟΧΙ percentages:
`usg_pct`, `ts_pct`, `efg_pct`, `fg3_pct`, `ft_pct`, `ast_pct`, `oreb_pct`, `dreb_pct`, `pct_pts_2pt_mr`

Π.χ. `ast_pct = 0.26` (26%). Αν περάσεις `26.0` στο `find_similar()` θα πάρεις z-score ~285.

Το Streamlit UI κάνει τη μετατροπή (×100 slider → ÷100 internal) αυτόματα.

---

## Preprocessing (`src/preprocessing.py`)

**`FEATURE_COLS`** (23 features για similarity):
```
pts, usg_pct, ts_pct, efg_pct,
fg3a, fg3_pct, fta, ft_pct, pct_pts_2pt_mr,
ast_pct, ast_to, tov,
oreb_pct, dreb_pct,
stl, blk, deflections, def_rating,
d_fg3_diff, d_rim_diff,
net_rating, height_cm, weight_lbs
```

**Tiered MPG filter:**
- 1996–2012: ≥ 20 MPG (pre-tracking era, λείπουν hustle stats)
- 2013+: ≥ 10 MPG (full data, κρατάμε specialists)
- Min games: ≥ 20 GP

**NaN handling:**
- `deflections` κ.α. hustle cols pre-2016 + corrupt 2015-16: position_group median
- `fg3_pct` / `ft_pct` με 0 attempts: 0.0
- `ast_to` όταν ast=0: 0.0

**`def_rating` — season-relative centering (ΚΡΙΣΙΜΟ):**
Το def_rating είναι έντονα era-dependent: `corr(def_rating, season) = 0.62`.
League mean 1998-99: **99.7** → 2023-24: **113.1** (spread 13.4 points), ενώ το
within-season std είναι μόλις **3.7** — δηλαδή η διαφορά *εποχής* είναι 3.6×
μεγαλύτερη από τη διαφορά *παικτών*.

Χωρίς διόρθωση το feature λειτουργεί ως **εποχή-selector** αντί για
defense-selector. Το `load_and_clean()` κάνει re-centering ανά σεζόν στο global
mean (`def_rating - season_mean + global_mean`), το οποίο:
- μηδενίζει το era leak (`corr → 0.000`, spread → 0.000)
- διατηρεί πλήρως το within-season signal (std παραμένει 3.69)
- **κρατά τις μονάδες** σε "def rating points", ώστε τα UI ranges και το API
  contract να μην αλλάξουν (γι' αυτό προτιμήθηκε από full per-season z-score)

Η αρχική τιμή διατηρείται ως `def_rating_raw` για display/debugging.

**Output:** `preprocess()` → `(df_clean, feature_matrix, scaler)` — fitted `StandardScaler`.

---

## ARCHETYPE SYSTEM — compositional

### Τα 18 primitive traits (ομάδες A–H)
- **A. Creation/scoring:** `on_ball_creator`, `slasher`, `midrange_scorer`
- **B. Shooting:** `spot_up_shooter`, `movement_shooter`
- **C. Playmaking:** `lead_playmaker`, `connective_passer`, `playmaking_big`
- **D. Interior offense:** `post_scorer`, `roll_finisher`, `stretch_big`
- **E. Perimeter D:** `point_of_attack_defender`, `versatile_wing_defender`
- **F. Interior D:** `rim_protector`, `help_defender`
- **G. Rebounding:** `defensive_rebounder`, `offensive_rebounder`
- **H. Efficiency:** `efficient_finisher`

Κάθε trait: `positions` (eligibility) + `signals` (stat + weight + κατεύθυνση + `pos_rel`).
- `pos_rel=True` → z-score vs position group (bigs) αντί global — για `ast_pct`, `fg3a`, `stl`, `blk` σε bigs.
- `def_rating` χαμηλό = καλή άμυνα → **αρνητικό** weight.
- `fine=True` → χαμηλότερο threshold (0.35 αντί 0.5) για rarer traits.

### Classifier logic (`classify()`)
1. Z-score ανά feature (global ή position-relative).
2. Trait score = weighted sum των signals.
3. Threshold: score > 0.5 → trait active (fine traits: 0.35).
4. Compound: βρες το preset με τo μεγαλύτερο subset των active traits.
5. Αν κανένα preset → fallback: noun (top score trait) + modifier (2nd).

### PRESET_POSITIONS — position-aware scoring
Κάθε preset έχει επιτρεπτά position groups (`PRESET_POSITIONS` dict, ~27 entries).
Στο `_label_archetype()`, το score είναι tuple `(pos_ok, trait_count)`:
- `pos_ok = 1` αν η θέση του παίκτη είναι στη λίστα, `0` αλλιώς.
- Primary tiebreaker: position match. Secondary: trait count. Tertiary: dict ordering.

Γιατί: χωρίς αυτό, ο Porzingis (F-C) → "Slashing Guard" επειδή τα guard presets ήρθαν πρώτα στο dict με ίσο trait count.

### Dict ordering για τριτεύον tie-breaking
Αν `(pos_ok, trait_count)` ισοπαλούν, κερδίζει το preset που εμφανίζεται **πρώτο** στο dict.
Π.χ. "Point Center" πριν "All-Around Forward" ώστε ο Giannis/Embiid → Point Center.

⚠️ Η σειρά μπορεί να κάνει ένα preset **δομικά απρόσιτο**. Το "3-and-D Wing" και
το "3-and-D Guard" έχουν και τα δύο 2 traits· με το Guard πρώτο, το Wing δεν
εμφανιζόταν **ΠΟΤΕ** (0/8382 rows) και 21 G-F wings (Majerle, Sefolosha, Ingles,
Eddie Jones) έπαιρναν λανθασμένα "Guard" label. Καμία μετρική ακρίβειας δεν το
έπιανε — γι' αυτό υπάρχει πλέον `tests/test_archetype_presets.py` που απαιτεί
**κάθε** preset να εμφανίζεται ≥1 φορά, και το `validation/triage_archetypes.py`
που τυπώνει όλες τις subset σχέσεις.

### Παραδείγματα (validation):
- Curry → Floor General / Two-Way Lead Guard ✓
- Jokić → Point Center ✓
- Draymond → Playmaking Rim Protector ✓
- OG Anunoby → Two-Way Sharpshooter ✓
- Gobert → Rim-Running Anchor ✓
- LeBron → All-Around Forward ✓

---

## Matching Engine (`src/similarity.py`)

**Metric:** Weighted RMS distance (masked):
```
distance = sqrt(Σ w_j × (user_z_j - player_z_j)² / Σ w_j)   [only specified features]
similarity = 1 / (1 + distance)   →   (0, 1]
```

Χρησιμοποιούμε L2 (όχι cosine) γιατί ζητάμε «βρες παίκτες ΚΟΝΤΑ σε αυτές τις τιμές».
Cosine κανονικοποιεί τον |player| vector — τιμωρεί αδίκως extreme players σε unspecified dims.
`1/(1+d)` αντί `exp(-d)` γιατί z-score distances είναι φυσικά μεγάλα (~4-15), το exp(-8)≈0 δεν δίνει range.

**Weighted RMS (scale-invariant):** Διαιρούμε με `Σ w_j` ώστε το distance να μην αυξάνεται
όσο ο χρήστης ορίζει περισσότερα stats. Χωρίς normalization, 6 stats με diff=0.5 δίνουν
`sqrt(6×0.25)≈1.22` αντί `sqrt(0.25)=0.5` → similarity 45% αντί 67%.

**Availability-aware masking + confidence discount (ΚΡΙΣΙΜΟ):**
Τα hustle stats λείπουν πριν το 2016-17 (56% της βάσης). Το distance υπολογίζεται
**μόνο** στις διαστάσεις που έχουν πραγματικά δεδομένα ανά row (renormalization
του Σw σε αυτές), αλλιώς κάθε imputed row κάθεται σε σταθερή απόσταση τιμωρίας
και οι defensive queries επιστρέφουν **0%** pre-2016 παίκτες.

Σκέτο masking όμως **υπερδιορθώνει**: λιγότερες διαστάσεις = λιγότερες ευκαιρίες
να απέχεις. Η διόρθωση είναι shrinkage προς το population prior:

```
coverage  = Σ(w διαθέσιμων) / Σ(w ζητούμενων)
sim_final = sim_pop + coverage^α × (sim_masked − sim_pop)
```

Το `sim_pop` υπολογίζεται **αναλυτικά**: το feature space είναι z-scored, άρα
`E[(u_j − P_j)²] = 1 + u_j²`. Ιδιότητες:
- `coverage = 1` → `sim_final = sim_masked` **ακριβώς** → μηδενικό regression σε
  offensive queries και σε tracking-era παίκτες
- `coverage → 0` → `sim_final → sim_pop`: «δεν ξέρουμε» ≠ «ταιριάζει»

`CONFIDENCE_ALPHA = 1.0` (γραμμικό shrinkage — posterior mean με το coverage ως
effective sample size). Καλιμπραρίστηκε μετρώντας: α=0 ρίχνει τον Alex Caruso
(coverage 1.00, προφανές match) στην 6η θέση πίσω από rows με 0.67· α≥1.5
επαναφέρει τον αποκλεισμό των pre-2016. Αποτέλεσμα: tracking queries **0% → 54.7%**
pre-2016 (baseline 57.7%).

Το `coverage` επιστρέφεται στο API και εμφανίζεται ως badge «N% data» στο
`ResultRow`.

**Trait boost:** `+0.004` ανά shared active trait — tiebreaker μόνο, δεν κυριαρχεί.

**Best season:** groupby player_id, κράτα σεζόν με max final_score.

**Season range:** "2010-2025" → φιλτράρει rows κατά start year.

---

## API Layer (`backend/`) — FastAPI

Wrap-άρει το `src/` **χωρίς να το αλλάζει** (adds `src/` στο `sys.path` στο `engine.py`).
Το dataset φορτώνεται **μία φορά** στο startup (FastAPI lifespan): `preprocess()` →
`classify()` → `build_percentile_matrix()`, και μένει in-memory.

**Endpoints:**

| Method | Path          | Περιγραφή |
|--------|---------------|-----------|
| GET    | `/health`     | liveness + πλήθος παικτών/rows |
| GET    | `/stats`      | feature metadata (ranges/labels/format/is_pct/**short/dist/pcts/n_rows**) + traits |
| GET    | `/archetypes` | τα 36 compound presets (traits + eligible positions) |
| GET    | `/players?q=` | autocomplete ονομάτων (diacritic-insensitive: "Jokic" → "Jokić") |
| POST   | `/similar`    | top-N όμοιοι παίκτες· input = display-unit stats, weights, top_n, active_traits, season_range, (προαιρετικό) prospect_id |
| POST   | `/classify`   | archetype + active traits + trait scores ενός πραγματικού παίκτη |
| GET/POST/PATCH/DELETE | `/prospects[/{id}]` | CRUD πάνω σε χειρόγραφες prospect εγγραφές — βλ. ενότητα "Prospects & search history" |
| POST/DELETE | `/prospects/{id}/comps[/{comp_id}]` | αποθηκευμένα NBA comp sets πάνω σε prospect |
| GET/DELETE | `/searches` | search history (τελευταίες 20) — καταγράφεται αυτόματα από το `/similar` |

**Data format (ΚΡΙΣΙΜΟ):** το API δέχεται/επιστρέφει **display-unit** τιμές (pct ως 0–100).
Η μετατροπή display↔internal (÷100 / ×100 για τα pct cols) γίνεται **μόνο** στο
`backend/metadata.py` (`to_internal`/`to_display`) — έτσι ο `find_similar()` παίρνει
ακριβώς τα fractions που περιμένει, και ο React client δεν χρειάζεται να ξέρει ποια
stats είναι fractions. Το serialization (z-score → display value + percentile +
match-quality class) γίνεται server-side στο `engine.py` ώστε ο client να μένει thin.

**Τι πρόσθεσε το Phase 12 στο serialization** (όλα στο `backend/`, το `src/` αμετάβλητο):

- **`/stats` → πραγματικές κατανομές.** Ανά feature: `dist` (24-bin histogram πάνω στο
  [min, max] των RANGES, normalized στο 1.0), `pcts` (101 quantiles p0–p100 σε display
  units) και `n_rows`. Υπολογίζονται **μόνο** πάνω σε rows με `avail_<col> = True` —
  αλλιώς το group-median imputation θα έφτιαχνε τεχνητή κορυφή στη median, δηλαδή ψέμα
  ακριβώς εκεί που το UI υπόσχεται ειλικρίνεια για την κάλυψη. Ο builder ζωγραφίζει το
  `dist` και βγάζει ακριβές percentile με binary search στα `pcts`, χωρίς round-trip ανά
  κίνηση του slider. Cache-άρονται στο `load()`.
- **`/stats` → `short`.** `SHORT_LABELS` στο `metadata.py` ("TS%", "DRTG", "MR%PTS").
  Τα `DISPLAY_LABELS` είναι για ανάγνωση· κάθε προσπάθεια να συντομευτούν client-side με
  regex έβγαζε σκουπίδια ("Height (cm)" → "cm", "Defensive Rating (lower = better)" →
  "lower = better"). Κλειδώνεται με test (unique + ≤ 8 χαρακτήρες).
- **`/similar` → breakdown scope.** Το `explain_match()` γεμίζει matching/diverging μέχρι
  top_n=4 με argsort πάνω σε ΟΛΑ τα features· τα unspecified πάνε τελευταία αλλά **δεν
  κόβονται**. Με 2-3 ζητούμενα stats οι λίστες γέμιζαν με features που δεν ζητήθηκαν (και
  δεν βάρυναν καθόλου στο distance) και **επικαλύπτονταν** μεταξύ τους. Το serializer
  φιλτράρει πλέον στα requested και κάνει dedupe — το ποια στοιχεία *δείχνεις* είναι
  ευθύνη του API, όχι του engine.
- **`/similar` → per-stat `available`.** Το row-level `coverage` έλεγε "50%" αλλά όχι
  *ποιο* 50%: το breakdown παρουσίαζε imputed τιμές σαν μετρημένες, με fit bar, ενώ το
  availability masking τις είχε ήδη αποκλείσει από το distance. Το `find_similar()`
  επιστρέφει προβολή μόνο των result_cols (οι `avail_*` δεν επιβιώνουν), οπότε το
  `Engine._build_imputed_index()` χτίζει `(player_name, season) → frozenset` στο startup.
  Το UI δείχνει «▨ / no data / εκτός».

Setup/run/build: **`DEVELOPMENT.md`**.

---

## UI Layer (`frontend/`) — Industry dark

Το UI υλοποιεί ένα dark inversion του "Industry" design system (Claude Design,
`ProspectMatch.dc.html`). Χαρακτήρας: **τεχνικό όργανο μέτρησης, όχι consumer app.**

- **Tokens** (`src/styles.css`): τρία επίπεδα επιφάνειας (`#0f1114` / `#121519` / `#1b1f24`)
  που ξεχωρίζουν με ελάχιστη διαφορά φωτεινότητας **συν hairline border** — χωρίς σκιές.
  `border-radius: 0` παντού. Accent `#94bce3` = "εδώ κοίτα", warn `#c58e4a` = "αυτό το
  νούμερο στηρίζεται σε λιγότερα δεδομένα" — το χρώμα είναι σήμα, όχι διακόσμηση.
- **Τυπογραφία:** Barlow (body) + Barlow Condensed (uppercase labels, tracking .1em) +
  monospace με `tabular-nums` για **κάθε** αριθμό, ώστε οι στήλες να στοιχίζονται.
  ⚠️ Καμία από τις δύο Barlow δεν έχει greek subset — τα ελληνικά πέφτουν per-glyph στα
  επόμενα του stack, γι' αυτό ονομάζονται ρητά greek-capable fallbacks (Roboto Condensed /
  Segoe UI). Σε offline packaged build δεν φορτώνει τίποτα και όλα πέφτουν στο Segoe UI:
  το layout δεν αλλάζει, γιατί μεγέθη/letter-spacing/uppercase ορίζονται ρητά.
- **Shell:** title bar → dataset status strip (rows/players/features, live από `/health`)
  → tab bar. Κάθε screen γεμίζει ό,τι απομένει και κάνει το δικό του scrolling.
- **Search:** δύο παράθυρα — builder rail (type-to-add αναζήτηση stat, category chips,
  ανά stat: πραγματικό histogram + marker + slider + `×1/×2/×3` segmented βάρος +
  «league pNN · N rows έχουν αυτό το stat») και πίνακας matches (rank / player / archetype /
  coverage cells / mini radar / similarity), με expandable row που δείχνει το breakdown και
  το μεγάλο radar overlay.
- **Διακριτά βάρη** (`×1/×2/×3` αντί για ελεύθερο number input): το βάρος είναι δήλωση
  προτεραιότητας, όχι βαθμονομημένη ποσότητα — τρία σκαλιά το εκφράζουν και αφαιρούν μια
  ολόκληρη κατηγορία λάθους (0.7×, 4.5×) που το engine ούτως ή άλλως κανονικοποιεί στο Σw.
- **Fit bar** στο breakdown: `fit = weight × (1 − |Δ percentile| / 100)`, με τη φόρμουλα
  τυπωμένη πάνω από τον πίνακα. Percentiles και όχι raw units, γιατί μόνο έτσι είναι
  συγκρίσιμα ανάμεσα σε features με τελείως διαφορετικές κλίμακες.
- **Responsive:** το Electron window είναι resizable ενώ ο πίνακας έχει ~618px σταθερών
  στηλών. Οι στήλες πέφτουν με σειρά προτεραιότητας (πρώτα το μικρό radar — υπάρχει σε
  μεγέθυνση στο expanded row — μετά το archetype). **Coverage και similarity δεν φεύγουν
  ποτέ**: είναι ο λόγος ύπαρξης του πίνακα.

---

## Prospects & search history (`backend/store.py`) — ξεχωριστό data layer

Οι **prospects** (χειρόγραφες scouted εγγραφές) και το **search history** είναι
τελείως ανεξάρτητα από το NBA dataset/`src/` — δύο JSON flat files (`prospects.json`,
`searches.json`) σε φάκελο που ορίζεται από:

1. `PROSPECTMATCH_DATA_DIR` env var (το θέτει το `electron/main.cjs` σε
   `app.getPath("userData")` για packaged builds — **ποτέ** μέσα στο install dir,
   που σε Windows είναι συνήθως μη εγγράψιμο Program Files).
2. Fallback: `./.prospectmatch-data/` (dev convenience, gitignored).

**Persistence pattern** (ίδιο και για τα δύο collections):
atomic write (temp file στον ίδιο φάκελο → `os.replace()`), in-memory list ως πηγή
αλήθειας μετά το πρώτο load, `threading.Lock` γύρω από κάθε read-modify-write
(ο uvicorn τρέχει sync handlers σε threadpool → πραγματικό ρίσκο race).

**Prospect fields:** `position` χρησιμοποιεί το ΙΔΙΟ vocabulary με το
`position_group`/`ALL_POSITIONS` του `src/archetypes.py` (`G/G-F/F/F-C/C`, όχι
PG/SG/SF/PF/C) — ώστε να μπορεί αργότερα να τροφοδοτήσει trait eligibility χωρίς
mapping table. Ύψος σε cm, βάρος σε **kg** (το tool στοχεύει Ευρωπαίους prospects)·
η μετατροπή kg→lbs για να ταΐσει το `weight_lbs` του engine γίνεται σε ένα σημείο,
`frontend/src/units.ts`.

**Comps** (`Prospect.comps`): αποθηκεύουν queries + slim αποτελέσματα (όχι radar/
explanations — derived data, θα φούσκωνε το store) που ο χρήστης έσωσε πάνω σε ένα
prospect μετά από `POST /prospects/{id}/comps`. Capped στα πιο πρόσφατα 20.

**Search history** (`searches.json`): κάθε `POST /similar` καταγράφει αυτόματα ένα
entry (query + top-3 results + προαιρετικό `prospect_id` αν το search ξεκίνησε με
prefill). Η καταγραφή είναι best-effort — μια αποτυχία εδώ ΔΕΝ πρέπει ποτέ να
χαλάσει το ίδιο το search (wrapped σε try/except στο `main.py`). Capped στα πιο
πρόσφατα 20.

---

## Κατάσταση (τι έχει γίνει)

- [x] Ιδέα & scope
- [x] API exploration
- [x] Archetype design: 18 primitives + compound presets (spec 29 → κώδικας 36) + `ARCHETYPES.md`
- [x] `pipeline/fetch_nba_data.py` — 4-phase fetch (base/advanced/scoring/hustle/defense)
- [x] **Phase 1d — defensive impact fetch** (`LeagueDashPtDefend`, 36 calls) — **έχει τρέξει**:
      `data/seasons_defense.csv` (6315 rows, 2013-14 → 2024-25) και merged στο `nba_stats_full.csv`
      (55 → **67 στήλες**, 13987 rows αμετάβλητα). Coverage στο τελικό dataset: **45.1%** (τα pre-2013
      rows είναι NaN).
      Επαληθεύτηκε ότι το merge είναι **λειτουργικά ουδέτερο**: και τα 21 `FEATURE_COLS` byte-identical,
      macro-F1 0.600 και archetype top-1 21/72 αμετάβλητα, 56 tests περνούν. Οι νέες στήλες απλώς
      κάθονται στο CSV — το `preprocess()` αγνοεί ό,τι δεν είναι στα `FEATURE_COLS`.
      **Era-stable χωρίς διόρθωση** (σε αντίθεση με το `def_rating`): `corr(d_ovr_diff, year) = −0.009`,
      spread σεζόν 0.0096 έναντι within-std 0.0744 (13%· το def_rating ήταν 364% πριν το centering).
      Το `d_rim_diff` είναι ελαφρώς era-dependent (corr −0.128, λόγος 42%) — προσοχή αν μπει στα features.
      ⚠️ **Small-sample noise:** `std(d_ovr_diff)` πέφτει 0.076 → 0.037 με `d_ovr_fga ≥ 6`. Οι ακραίες
      τιμές (±0.674) προέρχονται από rows με ελάχιστα contested attempts — θα χρειαστεί volume filter.
- [x] **Ένταξη των `d_*_diff` στο engine** (Phase 11) — `FEATURE_COLS` 21 → **23**.
      Επιλέχθηκαν `d_fg3_diff` + `d_rim_diff` γιατί είναι σχεδόν **ορθογώνια** (corr −0.01):
      perimeter και rim defense είναι ξεχωριστά skills. Το `d_ovr_diff` **παραλείφθηκε** — είναι
      μίγμα τους (0.44/0.60) και ήδη corr 0.43 με το `def_rating`.
      Το volume πρόβλημα λύθηκε μόνο του: μετά το MPG filter το 100% έχει `d_ovr_fga ≥ 3` και το
      std έπεσε 0.076 → 0.031, οπότε **δεν** χρειάστηκε volume filter.
      `avail_*` tracking + group-median imputation, όπως τα hustle.
      **Trait signal:** `d_fg3_diff` (weight −2.5) στο `point_of_attack_defender`, που είχε recall
      1.00 αλλά precision 0.24 — άναβε για κάθε guard με steals. Το DFG% μετράει αποτέλεσμα και
      κόβει τα FP: **F1 0.385 → 0.476** (+24% relative), macro-F1 **0.600 → 0.605**,
      archetype top-1 **21/72 → 22/72**. Best-threshold macro-F1 0.622 → **0.639**.
      **Μετρημένα ΑΡΝΗΤΙΚΑ αποτελέσματα** (δοκιμάστηκαν, δεν κρατήθηκαν): το `d_rim_diff` στον
      `rim_protector` ρίχνει το F1 **0.800 → 0.710** (το `blk` το καλύπτει ήδη, και το 44% imputed
      προσθέτει θόρυβο — ο classifier δεν έχει availability masking)· το `d_fg3_diff` στο
      `versatile_wing_defender` είναι ουδέτερο ή −1 στο top-1.
- [x] `src/preprocessing.py` — tiered MPG, NaN handling, z-scores
- [x] `src/archetypes.py` — trait signals + compound presets + classifier + PRESET_POSITIONS
- [x] `src/similarity.py` — weighted RMS matching + pct_cols output + explanations
- [x] `src/preprocessing.py` — percentile matrix (`build_percentile_matrix`, `stat_to_percentile`)
- [x] `app/streamlit_app.py` — Streamlit UI (stat builder + result cards + radar chart)
- [x] Validation: 20 παίκτες (stars + role players)
- [x] `validation/` harness — 72 labeled παίκτες, per-trait P/R/F1, threshold sweep, REPORT.md
- [x] **FastAPI backend** (`backend/`) — 6 endpoints, wrap-άρει το src/ αμετάβλητο, dataset load στο startup
- [x] **React frontend** (`frontend/`) — stat builder + result cards + radar, TS, error handling
- [x] **Electron shell** (`electron/`) — spawn backend + load UI· `npm run dev` (concurrently), `npm run dist`
- [x] **Router refactor** (Phase 0) — `react-router-dom` v6 `HashRouter`, `App.tsx`→shell, screens/ split, `MetaContext`
- [x] **Prospect storage** (Phase 1) — `backend/store.py` (JSON, atomic write, lock), `/prospects` CRUD, `PROSPECTMATCH_DATA_DIR`
- [x] **Prospect UI** (Phase 2) — `ProspectsScreen` (list/sort/delete) + `ProspectFormScreen` (create/edit, validation)
- [x] **Prospect → NBA comps** (Phase 3) — prefill search από physicals (kg→lbs σε `units.ts`), save/delete comp sets
- [x] **Home screen** (Phase 4) — dataset status, quick actions, recent prospects, search history (`/searches`)
- [x] **UI polish** (Phase 5) — position filter (client-side) + CSV export στο `SearchScreen` (`frontend/src/csv.ts`)
- [x] **Docs sync** (Phase 6) — `ARCHETYPES.md` 29 → 36 presets, real players επιβεβαιωμένα πάνω στο dataset
- [x] **Classifier tuning — eval hardening** (Phase 7) — `validation/labels.py` δεν χρησιμοποιούσε ΚΑΘΟΛΟΥ το
      `ignore` field παρόλο που το `evaluate.py` το προβλέπει ρητά. Query πάνω στο dataset έδειξε ότι σχεδόν
      όλα τα "false positives" των χειρότερων traits ήταν πραγματικά, τεκμηριωμένα δευτερεύοντα skills
      πολυδιάστατων stars (π.χ. Rudy Gobert = elite `efficient_finisher` λόγω rim finishing, απλά όχι
      μέρος του "Rim-Running Anchor" preset). Πρόσθεσα `ignore` για score ≥ 0.8 + τεκμηριωμένο skill →
      **macro-F1 0.494 → 0.601** (+22% relative), χωρίς να αλλάξει το `src/archetypes.py` καθόλου.
      Δοκιμάστηκε ΚΑΙ eligibility broadening (structural misses: `lead_playmaker`/`versatile_wing_defender`/
      `movement_shooter` επεκτάθηκαν σε ένα ακόμα position group) — αλλά έδειξε μηδαμινό κέρδος στο
      archetype top-1 (+1/72) με μικρή ζημιά στο macro-F1, οπότε ΔΕΝ κρατήθηκε.
- [x] **Defensive matching — data & feature fixes** (Phase 8) — διάγνωση έδειξε ότι το πρόβλημα με τους
      αμυντικούς ΔΕΝ ήταν τα weights αλλά δομικό. Τρία ευρήματα, όλα μετρημένα:
      **(α)** Η σεζόν 2015-16 ήταν corrupt (partial-season sample: 89.8% ακέραιες τιμές, max 11.00
      deflections/gm) και κυριαρχούσε σε κάθε high-deflections query — **5/10 → 0/10** αποτελέσματα
      από corrupt rows, με Curry/Harden/Butler να εμφανίζονται ως «elite stoppers».
      **(β)** Το `def_rating` (100% coverage, corr ≤0.16 με τα υπόλοιπα features) ήταν ήδη validated
      signal στον classifier αλλά **έλειπε από τα `FEATURE_COLS`** — ο χρήστης δεν μπορούσε να ζητήσει
      άμυνα χωρίς να αποκλείσει το 56% της βάσης μέσω του `deflections`.
      **(γ)** Σκέτη προσθήκη του def_rating ΔΕΝ αρκούσε: είναι era-dependent (corr 0.62 με τη σεζόν),
      οπότε λειτουργούσε ως εποχή-selector (84% pre-2016 vs baseline 58%). Χρειάστηκε season-relative
      centering → **63%**, μέσα στο εύρος των offensive controls.
      Αποτέλεσμα: defensive queries **0% → 48-84%** pre-tracking representation· classifier macro-F1
      στο βέλτιστο threshold **0.607 → 0.623**· `versatile_wing_defender` F1 0.424 → 0.486,
      `rim_protector` 0.769 → 0.800. Καλύπτεται από 34 tests (`tests/`).
- [x] **Availability-aware masking + confidence discount** (Phase 9) — το distance υπολογίζεται μόνο
      στις διαστάσεις με πραγματικά δεδομένα ανά row (νέες `avail_*` στήλες + `build_availability_matrix()`),
      με shrinkage προς το population prior ώστε να μην υπερδιορθώνει. Tracking queries **0% → 54.7%**
      pre-2016 (baseline 57.7%), με **μηδενικό regression** όπου coverage=1 (αποδεδειγμένο με test).
      Το `coverage` εκτίθεται στο API και ως badge «N% data» στο UI. Βλ. §Matching Engine.
- [x] **Επανα-συντονισμός `TRAIT_THRESHOLD`** (Phase 9) — διερευνήθηκε, **δεν αλλάχθηκε**. Το REPORT.md
      δείχνει best macro-F1 στο 0.9 (0.623 vs 0.597), αλλά η μετρική είναι τυφλή: τα 72 labeled stars
      έχουν 6-10 active traits και δεν γίνονται ποτέ Unclassified. Μετρημένο σε ΟΛΟ το dataset, το 0.9
      αφήνει **32% των παικτών χωρίς label** (από 15%) και σβήνει 4 archetypes, με **ίδιο** archetype
      top-1 (20/72). Ποιοτικά: ο Caruso πέφτει από "3-and-D Guard" σε fallback "Efficient Defender".
      Το `tune_threshold.py` τυπώνει πλέον και τις usability στήλες ώστε η απόφαση να μην ξαναγίνει
      στα τυφλά. Τα per-trait βέλτιστα συγκρούονται (0.4 έως 0.95) — per-trait thresholds θα ήταν
      overfitting σε support 4-5 παικτών.
- [x] **UI rebuild — Industry dark** (Phase 12) — υλοποίηση του `ProspectMatch.dc.html` από το
      Claude Design πάνω στις 4 οθόνες. Recharts → raw SVG radar (bundle ~600 KB → **219 KB**).
      Η υλοποίηση ανέδειξε **τρία πραγματικά σφάλματα** που το παλιό UI έκρυβε, όλα διορθωμένα
      στο serialization layer (`backend/engine.py`, το `src/` αμετάβλητο) και κλειδωμένα με
      `tests/test_api_serialization.py` (64 → **73 tests**):
      **(α)** Το breakdown έδειχνε features που ο χρήστης **δεν** ζήτησε και που δεν βάρυναν
      καθόλου στο distance (το `explain_match()` γεμίζει top_n=4 με argsort πάνω σε όλα τα
      features), και τα ίδια features **δύο φορές** (matching ∩ diverging ≠ ∅).
      **(β)** Οι imputed τιμές παρουσιάζονταν ως μετρημένες — το row-level coverage έλεγε
      "50%" χωρίς να λέει *ποιο* 50%. Νέο `available` flag ανά entry.
      **(γ)** Το `shortLabel` client-side μάντευε με regex πάνω στο label: "Height (cm)" → "cm".
      Νέα `SHORT_LABELS` στο `metadata.py` ως single source of truth.
      Επιπλέον: το `/stats` σερβίρει πλέον **πραγματικές κατανομές** (24-bin histogram + 101
      quantiles ανά feature, μετρημένα μόνο σε μη-imputed rows) ώστε το sparkline του builder
      και το «league pNN» readout να μη στηρίζονται σε εικασία.
- [x] **Archetype triage + δύο design fixes** (Phase 10) — το `validation/triage_archetypes.py`
      κατηγοριοποιεί τα misses ώστε να ξεχωρίζει η **τεχνική** δουλειά από την **απόφαση ground truth**.
      Ευρήματα: position mismatch **0** (το `PRESET_POSITIONS` δουλεύει), και το `versatile_wing_defender`
      είναι το #1 αίτιο (10 misses). Δύο διορθώσεις:
      **(α)** Το `versatile_wing_defender` είχε **θετικά** weights σε `reb_pct`/`height_cm`, με τη λογική
      «ο wing defender είναι ψηλός και μαζεύει». Μέσα όμως στο eligible pool (G-F/F/F-C) αυτά ξεχωρίζουν
      **bigs**: 6 από τα 8 false positives ήταν F-C. Μετρημένο Cohen's d expected-vs-FP: `reb_pct` −1.80,
      `screen_assists` −1.59, `height_cm` −1.39 — όλα **αντίθετα** από την υπόθεση. Αντιστροφή +
      προσθήκη `screen_assists` (καθαρός big-marker) → precision **0.529 → 0.692**, F1 **0.486 → 0.545**.
      **(β)** Το "3-and-D Wing" ήταν δομικά απρόσιτο (0/8382): ισοπαλούσε με το "3-and-D Guard" σε
      `(pos_ok, trait_count)` και έχανε στο dict ordering. Αναδιάταξη → 21 χρήσεις, μετρικές αμετάβλητες.
- [x] **`slasher` signal tuning — ΑΡΝΗΤΙΚΟ ΑΠΟΤΕΛΕΣΜΑ (δοκιμάστηκε, ΔΕΝ κρατήθηκε)** — το triage έδειξε
      `slasher` ως το #2 trait-αίτιο misses (8/72: Mitchell, Fox, Brown, Edwards, Gordon, Wiggins, Siakam,
      Randle). Διάγνωση: το signal `fg3a` (weight −1.0, «slashers αποφεύγουν τα 3s») τιμωρεί σύγχρονους
      combo guards/wings που σλασάρουν ΚΑΙ σουτάρουν πολλά 3s (fg3a z-score μέχρι +3.68 στους misses,
      έναντι μέσου −0.34 στον ενεργό `slasher` πληθυσμό).
      Δοκιμάστηκαν 4 παραλλαγές (μειωμένο/μηδενισμένο `fg3a` weight, προσθήκη `pct_pts_paint` ως θετικό
      σήμα): το per-trait F1 βελτιώνεται σημαντικά (0.364 → 0.54–0.59, recall 0.333 → 0.58–0.92), αλλά το
      **archetype top-1 πέφτει** σε όλες (22/72 → 18-20/72), όχι ανεβαίνει. Diff ανά παίκτη έδειξε **0/8**
      στοχευμένα misses να διορθώνονται στο top-1 label, plus 2 νέες παλινδρομήσεις (Trae Young, Bam
      Adebayo). Αιτία δομική, όχι signal-tuning: (1) οι περισσότεροι misses χρειάζονται ΚΑΙ το
      `versatile_wing_defender` που είναι ήδη τεκμηριωμένα αδιόρθωτο (βλ. παρακάτω) — άρα διόρθωση μόνο
      του `slasher` δεν αρκεί· (2) το `_label_archetype()` tie-break (preset με τα περισσότερα active
      traits) απλώς προσθέτει το ενεργοποιημένο `slasher` σε preset που ήδη κέρδιζε (π.χ. `Two-Way Lead
      Guard`) αντί να ξεκλειδώσει το πιο συγκεκριμένο (`Slashing Guard`)· (3) χαλαρώνοντας το `fg3a`
      penalty το trait γίνεται de facto «αποδοτικός σκόρερ υψηλού όγκου» και ανάβει λανθασμένα σε μη-
      slashers (Trae Young, Bam Adebayo), σπάζοντας δικά τους ήδη-σωστά tie-breaks.
- [x] **`_label_archetype()` tie-break — διάγνωση + partial fix** — μετρήθηκε ΠΟΣΑ misses οφείλονται
      καθαρά στο tie-break (το expected preset είναι ΗΔΗ πλήρως ικανοποιημένο από τα active traits, αλλά
      χάνει από άλλο preset): **17/50 (34%)** — ταυτίζεται ακριβώς με τα buckets B+E του triage. Δύο
      ξεχωριστοί μηχανισμοί:
      **(α) Trait-count dominance (12 περιπτώσεις)** — πολυδιάστατοι παίκτες με 6-10 active traits
      σχεδόν πάντα τραβιούνται προς το preset με τα περισσότερα traits (π.χ. Haliburton, Tatum, Embiid,
      DeRozan), ανεξάρτητα από «κύριο ρόλο». Θεμελιώδες ζήτημα στην ίδια την ευρετική
      `(pos_ok, len(preset))· ΔΕΝ διορθώνεται με dict reorder — παραμένει ανοιχτό.
      **(β) Equal-trait-count dict-order shadow (3 περιπτώσεις)** — ίδιο bug pattern με το Phase 10
      (`3-and-D Wing`/`Guard`), αλλά το `triage_archetypes.py` §1 detector δεν το έπιανε γιατί ψάχνει μόνο
      literal subset σχέσεις, όχι presets ίσου μεγέθους που χάνουν σε ισοπαλία λόγω dict order:
      `Stretch Rim Protector` {stretch_big, rim_protector} έχανε πάντα από `Stretch Big`
      {stretch_big, efficient_finisher} (Brook Lopez, Myles Turner)· `Energy Big` έχανε από
      `Rim-Running Anchor` (Hartenstein).
      Δοκιμάστηκε reorder και για τα δύο ζευγάρια χωριστά: το `Stretch Rim Protector`/`Stretch Big` ήταν
      **καθαρό κέρδος** (top-1 +2, macro-F1 αμετάβλητο, 0 νέες παλινδρομήσεις — 34→57 χρήσεις) και
      **εφαρμόστηκε** (`Stretch Rim Protector` πλέον προηγείται στο `COMPOUNDS` dict). Το
      `Energy Big`/`Rim-Running Anchor` ήταν **1-προς-1 trade** (διορθώνει Hartenstein, σπάει Rudy Gobert,
      net 0 — 14→117 χρήσεις, πολύ μεγάλη μετατόπιση συμπεριφοράς σε όλο το dataset) → **ΔΕΝ
      εφαρμόστηκε**, είναι γνήσια αμφίσημη περίπτωση που χρειάζεται νέο διαφοροποιητικό signal, όχι
      reorder. **Αποτέλεσμα: archetype top-1 22/72 → 24/72, macro-F1 αμετάβλητο 0.605.**
- [x] **Κατηγορία (α) trait-count dominance — αναλύθηκε περαιτέρω, 2 ακόμα dict-order fixes** — οι 12
      περιπτώσεις "trait-count dominance" δεν ήταν όλες γνήσια ανισότητα μήκους· ξαναμετρήθηκαν με
      ακρίβεια: **4/12 ήταν ισοπαλίες ίδιου μήκους** (ίδιο bug pattern με το `Stretch Rim Protector`),
      **8/12 γνήσια dominance** (μικρότερο preset χάνει από μεγαλύτερο, π.χ. Haliburton/Tatum/Embiid/JJJ —
      θεμελιώδες, δεν διορθώνεται με reorder).
      Από τις 4 ισοπαλίες, δοκιμάστηκε reorder ξεχωριστά για κάθε ζευγάρι:
      **`Wing Scorer` πριν το `Scoring Lead Guard`** (και τα δύο 3 traits, κοινά
      on_ball_creator+midrange_scorer) → καθαρό κέρδος, διορθώνει DeMar DeRozan, 0 παλινδρομήσεις,
      **εφαρμόστηκε**.
      **`Point Forward` πριν το `Two-Way Lead Guard`** (και τα δύο 3 traits, κοινά
      on_ball_creator+lead_playmaker) → καθαρό κέρδος, διορθώνει Scottie Barnes, 0 παλινδρομήσεις,
      **εφαρμόστηκε**.
      **`Instant Offense`/`Floor General`** (και τα δύο 2 traits, κοινό movement_shooter) → **1-προς-1
      trade** (διορθώνει Tyler Herro + Malik Monk, σπάει Trae Young + Stephen Curry, net 0) → **ΔΕΝ
      εφαρμόστηκε**, ίδιο pattern με το `Energy Big`/`Rim-Running Anchor` (αμφίσημη περίπτωση, χρειάζεται
      διαφοροποιητικό signal όχι reorder).
      **Αποτέλεσμα: archetype top-1 24/72 → 26/72, macro-F1 αμετάβλητο 0.605.**
      **Παραμένουν ανοιχτά** (γνήσια dominance, όχι tie): Haliburton, Norman Powell, Ja Morant, Derrick
      White, Jayson Tatum, Paul George, Joel Embiid, Jaren Jackson Jr. — εδώ ένα μικρότερο preset (π.χ.
      `Floor General`, 2 traits) είναι πάντα υποσύνολο ενός μεγαλύτερου matching preset (π.χ.
      `Two-Way Lead Guard`, 3 traits) για πολυδιάστατους παίκτες με 5+ active traits. Dict reorder δεν
      μπορεί να το διορθώσει — χρειάζεται διαφορετικό tie-break κριτήριο από το raw `len(preset)`
      (π.χ. score-weighted match αντί για μέτρημα traits, ή explicit "primary role" annotation). Bigger
      architectural αλλαγή, εκτός scope αυτού του pass.
- [x] **Score-weighted tie-break — ΑΡΝΗΤΙΚΟ ΑΠΟΤΕΛΕΣΜΑ (δοκιμάστηκε, ΔΕΝ κρατήθηκε)** — δοκιμάστηκε αν
      το mean trait-score (πόσο έντονα εκφράζονται τα traits ενός preset) μπορεί να αντικαταστήσει το
      raw trait-count ως tie-break criterion, στοχεύοντας ακριβώς τα 8 misses του trait-count dominance.
      **(α) Mean-score ως πρωτεύον κριτήριο** (πλήρης αντικατάσταση του `len(preset)`): καταστροφικό.
      top-1 22/72 → 18/72 στα labeled· dataset-wide 13.4% των rows (1122/8382) άλλαξαν label,
      `Rim-Running Anchor` 554 → 24 χρήσεις, `Bucket-Getter` έγινε 100% δομικά απρόσιτο (123 → 0). Ο
      μέσος όρος ευνοεί συστηματικά μικρότερα presets — λιγότεροι όροι στο mean = πιο εύκολο υψηλό score,
      ανεξάρτητα από correctness.
      **(β) Mean-score ΜΟΝΟ ως tertiary tie-break σε ισοπαλίες ίδιου μήκους** (γενίκευση του χειροκίνητου
      `Stretch Rim Protector`/`Wing Scorer`/`Point Forward` fix σε αυτόματο κανόνα): επίσης αρνητικό.
      top-1 26/72 → 22/72 — ΑΝΑΤΡΕΠΕΙ τα ήδη διορθωμένα (DeRozan) και σπάει άλλα ήδη-σωστά labeled
      players (SGA, Curry, Jimmy Butler, KAT) που εξαρτώνταν από το τρέχον dict order σε άλλα ζεύγη·
      dataset-wide 9.4% (788/8382) rows άλλαξαν label.
      **Γιατί αποτυγχάνει η γενίκευση:** το mean-score δεν είναι σταθερός discriminator ανά ζευγάρι
      presets — για κάποια ζεύγη προτιμά το σωστό preset, για άλλα όχι, οπότε ένας ενιαίος αυτόματος
      κανόνας διορθώνει λίγα αλλά σπάει περισσότερα. Η χειροκίνητη, per-pair, μετρημένη διόρθωση
      (dict reorder με explicit before/after ανά ζευγάρι) είναι **ουσιαστικά καλύτερη** από κάθε
      "principled" formula που δοκιμάστηκε, ακριβώς επειδή επεμβαίνει χειρουργικά μόνο εκεί που έχει
      επαληθευτεί μηδενικό trade-off, ενώ μια γενική φόρμουλα επεμβαίνει παντού αδιακρίτως.
      **Τα 8 misses γνήσιου trait-count dominance θεωρούνται μη διορθώσιμα** μέσα στην τρέχουσα
      compositional αρχιτεκτονική χωρίς σοβαρό collateral damage — θα χρειαζόταν πλήρης επανασχεδιασμός
      του `_label_archetype()` (π.χ. trained classifier ή explicit "primary role" annotation ανά preset),
      όχι tie-break tuning.
- [ ] Classifier tuning — archetype top-1 accuracy (26/72 @ 0.6). Το triage δείχνει πού να δουλέψει κανείς:
      **~31 misses = λείπει trait** (τεχνικό), **~16 = άλλος κλάδος** (ανά περίπτωση), **λίγα = ground truth**
      (το `got` είναι εξίσου/πιο σωστό → `accept_also` στο `labels.py`, που χρησιμοποιείται μόλις σε 12/72
      labels ενώ το `ignore` σε 46/72 — ανεκμετάλλευτο, ίδιο pattern με το Phase 7).
      **ΟΡΙΟ που τεκμηριώθηκε:** το `versatile_wing_defender` recall (0.450) **δεν διορθώνεται με weights**.
      Το `deflections` μετράει *στυλ* (ball-hawking), όχι ποιότητα: ο Mikal Bridges (elite on-ball, δεν
      κάνει gambles) έχει 1.71 ενώ ο Luka Doncic (γνωστά κακός defender) 3.38. Οι κατανομές επικαλύπτονται
      πλήρως (misses −0.63..+0.54, FPs +0.85..+2.88) και η αφαίρεση του deflections ρίχνει το recall σε 0.05.
      Χρειάζονται matchup / DFG% / contested-shots δεδομένα — δεν υπάρχουν στο nba_api pipeline.
- [ ] Per-36 normalization των `stl`/`blk` — `corr(stl, min) = +0.64`, δηλαδή το stl μετράει κατά κύριο
      λόγο *πόσο παίζεις*· per-36 πέφτει σε +0.08. Το rebounding είναι ήδη rate-adjusted (`oreb_pct`/
      `dreb_pct`, corr ≈ 0) — ασύμμετρος σχεδιασμός.
- [ ] Self-contained bundle: PyInstaller backend exe (τώρα fallback σε system Python)
- [ ] Multi-league support

---

## Επόμενα βήματα

Τα 5 phases του `PHASE_PROMPTS.md` (router refactor → prospect storage → prospect UI →
NBA comps → home screen) + Phases 5–8 (UI polish, docs sync, classifier eval hardening,
defensive matching fixes) έχουν ολοκληρωθεί. Παραμένουν από το αρχικό roadmap:

1. **Classifier tuning (archetype top-1)** — η per-trait ακρίβεια βελτιώθηκε σημαντικά (macro-F1 0.601),
   και τρία dict-order tie-break fixes ανέβασαν το top-1 σε 26/72 (βλ. `_label_archetype() tie-break`
   παραπάνω). Δοκιμάστηκε score-weighted tie-break (mean trait-score) ως γενική αντικατάσταση του
   `len(preset)` — **αρνητικό αποτέλεσμα και στις δύο εκδοχές** (βλ. `Score-weighted tie-break` παραπάνω),
   οπότε τα 8 misses γνήσιου trait-count dominance θεωρούνται μη διορθώσιμα χωρίς πλήρη επανασχεδιασμό
   του `_label_archetype()`. Παραμένει ανά-περίπτωση δουλειά σε misses που είναι γνήσια αμφίσημα (δύο
   εξίσου έγκυρα presets, `accept_also` candidates).
2. **Self-contained packaging** — PyInstaller exe για τον backend αντί system-Python fallback.
3. **Multi-league** — NCAA, EuroLeague: νέο pipeline, ίδιο `src/` + ίδιο API.

---

## Conventions

- Σχόλια & εξηγήσεις: στα Ελληνικά, technical terms στα Αγγλικά.
- Ζητούμενο: **ακρίβεια + αιτιολόγηση**. Εξήγησε το "γιατί" πίσω από κάθε επιλογή.
- Κάθε νέα στήλη/feature/βάρος: σκέψου αν επηρεάζει το matching ή είναι noise.
- Κράτα το design **επεκτάσιμο** (multi-league αργότερα) χωρίς over-engineering τώρα.
- **Άμυνα = αδύναμο σήμα** — τα defensive traits θα έχουν τα περισσότερα λάθη. Αυτό τεκμηριώνεται, δεν κρύβεται.
- Το nba_api ΔΕΝ είναι προσβάσιμο από sandboxed περιβάλλοντα — τρέχει μόνο τοπικά.
- **Πριν κάθε commit:** update README.md + CLAUDE.md να αντικατοπτρίζουν την τρέχουσα κατάσταση.