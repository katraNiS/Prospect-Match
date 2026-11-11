# ProspectMatch

> 🇬🇧 English version: [README.md](./README.md)

Ένα **scouting εργαλείο** που βρίσκει πραγματικούς παίκτες με βάση ένα custom στατιστικό/χαρακτηριστικό προφίλ — όχι quiz τύπου "ποιος παίκτης είμαι", αλλά πραγματικό εργαλείο ανάλυσης για scouting και roster building.

> Project στο πλαίσιο πτυχιακής. Προτεραιότητα στην **ακρίβεια** και στην **τεκμηρίωση** κάθε σχεδιαστικής απόφασης.

---

## Τι κάνει

Ο χρήστης (scout) ορίζει ένα **player profile**: στατιστικά + βάρη ανά stat. Το σύστημα επιστρέφει τους **πιο όμοιους πραγματικούς παίκτες** από τη βάση, με **explainability** — δηλαδή _γιατί_ ταιριάζει ο καθένας (ποια stats συμπίπτουν, ποια αποκλίνουν, και κατά πόσο).

Ο χρήστης μπορεί επίσης να επιλέξει **traits** (π.χ. `lead_playmaker`, `spot_up_shooter`) για να δώσει μικρό boost σε παίκτες με αυτό το profile, χωρίς να αποκλείει κανέναν.

Πέρα από το similarity search, ο χρήστης μπορεί να κρατά τους δικούς του
**prospects** — παίκτες που παρακολουθεί χειροκίνητα (physicals, ομάδα, σημειώσεις) —
και να τους συνδέει απευθείας με NBA comps: prefill του search από τα physicals ενός
prospect, και αποθήκευση των αποτελεσμάτων πάνω στην εγγραφή του. Ένα home screen
συγκεντρώνει την κατάσταση του dataset, τους πρόσφατους prospects και το ιστορικό
αναζητήσεων.

---

## Πώς δουλεύει (high-level)

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
            /similar /classify /stats ...                       (legacy UI, λειτουργικό)
                         ↓
            frontend/ (React + TS, SVG radar)  ←  wrapped σε  →  electron/ (desktop app)
```

Το **desktop app** (Electron + FastAPI + React) είναι η κύρια κατεύθυνση· το Streamlit
UI παραμένει λειτουργικό και καταναλώνει το `src/` απευθείας. Ο πυρήνας `src/`
(preprocessing/archetypes/similarity) είναι **κοινός** — ο FastAPI backend τον
_wrap-άρει_, δεν τον ξαναγράφει· αλλάζει μόνο με μετρημένη αιτιολόγηση και test.

**Compositional archetypes:** αντί για ~10 fixed κουτιά, ορίζουμε **18 primitive traits** (π.χ. `slasher`, `rim_protector`, `lead_playmaker`) που συνδυάζονται αυτόματα σε **36 σύνθετα archetypes** (π.χ. `playmaking_big` + `rim_protector` + `help_defender` = "Playmaking Rim Protector"). Ο ίδιος feature space χρησιμοποιείται και για το matching.

**Similarity metric:** weighted L2 distance στο z-score space, masked μόνο στα stats που ο χρήστης όρισε. `1/(1+distance)` → score (0, 1].

Πλήρεις ορισμοί traits/compounds στο [`ARCHETYPES.md`](./ARCHETYPES.md).

---

## Tech stack

| Layer | Επιλογή |
|---|---|
| Core / Language | Python (`src/` — preprocessing, archetypes, similarity) |
| Backend API | FastAPI + uvicorn |
| Frontend | React 18 + TypeScript + Vite (raw-SVG radar, χωρίς charting lib) |
| Desktop shell | Electron + electron-builder |
| Legacy UI | Streamlit (`app/streamlit_app.py`) |
| Data storage | CSV flat file (`data/nba_stats_full.csv`) |
| Data sources | nba_api (box + advanced + scoring + hustle + matchup defense) |
| ML / Math | scikit-learn, pandas, numpy |

> Δεν χρησιμοποιούμε βάση δεδομένων στο παρόν στάδιο — το CSV είναι αρκετό.
> PostgreSQL/SQLAlchemy παραμένει επιλογή για αργότερα.
>
> Πλήρες setup/run/build του desktop stack: **[`DEVELOPMENT.md`](./DEVELOPMENT.md)**.

---

## Κατάσταση project

- [x] Ορισμός ιδέας & scope (NBA-only πρώτα)
- [x] API exploration — ξέρουμε ακριβώς τι fields δίνει το `nba_api`
- [x] Archetype design: 18 primitives + 36 compound presets (`src/archetypes.py`· spec `ARCHETYPES.md`)
- [x] Data pipeline — box/advanced + scoring (PCT_PTS_2PT_MR κ.α.) + hustle (deflections κ.α.)
      + **defensive impact** (DFG% ανά zone: overall / 3PT / rim, από `LeagueDashPtDefend`, 2013-14+)
- [x] `src/preprocessing.py` — normalization, tiered MPG filter, z-scores
- [x] `src/archetypes.py` — trait signals + compound presets + classifier
- [x] `src/similarity.py` — weighted L2 matching, trait boost, explanations
- [x] `app/streamlit_app.py` — working Streamlit UI
- [x] Validation: 20 γνωστοί παίκτες (stars + role players) — archetypes & similarity
- [x] Position-aware preset matching (`PRESET_POSITIONS`) — διορθώνει misclassification (π.χ. Porzingis → "Slashing Guard")
- [x] Scale-invariant similarity — weighted RMS αντί raw sum, αποφεύγει compression με πολλά stats
- [x] Radar chart (percentile 0–100) — StatsBomb-style, player vs user target, `plotly`
- [x] Validation harness (`validation/`) — 72 labeled παίκτες, per-trait precision/recall/F1, threshold sweep → `REPORT.md`
- [x] **FastAPI backend** (`backend/`) — 6 endpoints (`/similar`, `/classify`, `/stats`, `/archetypes`, …), wrap-άρει το `src/` αμετάβλητο
- [x] **React frontend** (`frontend/`) — stat builder + result cards + radar (TypeScript)
- [x] **Electron desktop app** (`electron/`) — `npm run dev` (backend+frontend+electron μαζί), `npm run dist`
- [x] **Routing + πολλαπλά screens** — `react-router-dom` (`HashRouter`), Home / Search / Prospects screens
- [x] **Prospect tracking** — CRUD για χειρόγραφους prospects (JSON store, `PROSPECTMATCH_DATA_DIR`)
- [x] **Prospect ↔ NBA comps** — prefill search από prospect physicals, αποθήκευση/διαγραφή αποτελεσμάτων
- [x] **Home screen + search history** — dataset status, πρόσφατοι prospects, τελευταίες αναζητήσεις (re-run με ένα click)
- [x] **UI polish** — φίλτρο ανά position + export αποτελεσμάτων σε CSV (client-side, στο search screen)
- [x] **UI rebuild — "Industry dark"** — dark-mode-first, data-dense επανασχεδίαση και των 4 οθονών:
      stat builder με **πραγματικό histogram** του league ανά stat, πίνακας matches με coverage cells
      και expandable breakdown, raw-SVG radar overlay (αφαιρέθηκε το Recharts, bundle ~600 KB → 219 KB).
      Η υλοποίηση αποκάλυψε τρία σφάλματα παρουσίασης που το προηγούμενο UI έκρυβε — breakdown με
      features που δεν ζητήθηκαν, imputed τιμές που εμφανίζονταν ως μετρημένες, και συντομεύσεις labels
      που έβγαζαν "cm" αντί για "Height". Όλα διορθωμένα και κλειδωμένα με tests.
- [x] **`ARCHETYPES.md` sync** — 29 → 36 presets, real players επιβεβαιωμένα πάνω στο dataset
- [x] **Classifier eval hardening** — validation ground truth (`validation/labels.py`) διορθώθηκε ώστε να μην
      τιμωρεί legit δευτερεύοντα traits πολυδιάστατων players· macro-F1 0.494 → 0.601 (+22%), χωρίς αλλαγές
      στο `src/`
- [x] **Defensive matching fixes** — τρία δομικά προβλήματα που έκαναν τα defensive queries αναξιόπιστα:
      (α) η σεζόν 2015-16 είχε corrupt hustle data (partial-season sample σε λάθος κλίμακα) και κυριαρχούσε
      σε κάθε query — 5/10 → 0/10 αποτελέσματα από corrupt rows·
      (β) το `def_rating` έλειπε από τα `FEATURE_COLS` παρόλο που ο classifier το χρησιμοποιούσε ήδη —
      προστέθηκε με season-relative centering, γιατί είναι era-dependent (corr 0.62 με τη σεζόν)·
      (γ) τα hustle stats λείπουν πριν το 2016-17, οπότε το imputation απέκλειε de facto το 56% της βάσης
      από κάθε defensive query (**0%** pre-2016 αποτελέσματα)
- [x] **Availability-aware matching** — το distance υπολογίζεται μόνο στις διαστάσεις με πραγματικά δεδομένα
      ανά παίκτη, με confidence discount ώστε τα ελλιπή rows να μην εκτοπίζουν όσα έχουν πλήρη δεδομένα.
      Defensive queries: **0% → 54.7%** pre-2016 representation (baseline 57.7%), με μηδενικό regression
      στα offensive. Το UI δείχνει badge «N% data» όπου το match κρίθηκε σε λιγότερα stats.
- [x] **Test suite** (`tests/`) — 64 pytest tests: data integrity, era balance, discriminative power,
      threshold usability, preset reachability, metadata συνέπεια
- [x] **Archetype triage** (`validation/triage_archetypes.py`) — κατηγοριοποιεί τα misclassifications ώστε
      να ξεχωρίζει τι είναι τεχνικό bug και τι απόφαση ground truth. Οδήγησε σε δύο διορθώσεις: το
      `versatile_wing_defender` ανταμείβε το *μέγεθος* (6/8 false positives ήταν centers) → precision
      0.529 → 0.692· και το preset "3-and-D Wing" ήταν δομικά απρόσιτο (0 χρήσεις σε 8382 rows) επειδή
      έχανε σε ισοπαλία από το "3-and-D Guard" → 21 G-F wings έπαιρναν λάθος "Guard" label
- [x] **Matchup-based defensive impact στο engine** — τα `d_fg3_diff` (perimeter) και `d_rim_diff` (rim)
      μπήκαν στα `FEATURE_COLS`: ο χρήστης μπορεί πλέον να ζητήσει «καλή περιφερειακή άμυνα» ή
      «rim protection» με βάση το τι σουτάρουν οι αντίπαλοι, όχι το στυλ του αμυντικού.
      Στον classifier: `point_of_attack_defender` F1 0.385 → 0.476, archetype top-1 21/72 → 22/72
- [x] **`_label_archetype()` tie-break fixes** — διάγνωση έδειξε ότι 17/50 misses (34%) οφείλονται στο
      tie-break rule (preset με τα περισσότερα active traits), όχι σε λείποντα traits. Τρία dict-order
      fixes σε ισόμεγέθεις ισοπαλίες (`Stretch Rim Protector` πριν `Stretch Big`· `Wing Scorer` πριν
      `Scoring Lead Guard`· `Point Forward` πριν `Two-Way Lead Guard`) διόρθωσαν 4 misses χωρίς καμία
      παλινδρόμηση — archetype top-1 **22/72 → 26/72**. Δύο ακόμα ζευγάρια δοκιμάστηκαν αλλά ήταν
      1-προς-1 trades (net 0) και **δεν** εφαρμόστηκαν. Τα υπόλοιπα 8 misses είναι γνήσιο trait-count
      dominance (μικρότερο preset πάντα υποσύνολο μεγαλύτερου) — θεμελιώδες ζήτημα στο tie-break κριτήριο,
      όχι διορθώσιμο με reorder. Λεπτομέρειες στο `CLAUDE.md`.
- [ ] Classifier tuning: archetype top-1 accuracy (ξεχωριστό, πιο δύσκολο πρόβλημα — βλ. `CLAUDE.md`).
      Τεκμηριωμένο όριο: η *versatile wing defense* δεν είναι μετρήσιμη από τα διαθέσιμα stats — το
      `deflections` μετράει στυλ (ball-hawking), όχι ποιότητα άμυνας
- [ ] Per-36 normalization των `stl`/`blk` (τώρα counting stats ενώ το rebounding είναι rate-adjusted)
- [ ] Self-contained bundle (PyInstaller backend exe)
- [ ] Multi-league support (NCAA, EuroLeague κ.α.)

---

## Δομή αρχείων

```
ProspectMatch/
├── README.md                  ← αυτό το αρχείο
├── CLAUDE.md                  ← context/οδηγίες για το Claude Code
├── ARCHETYPES.md              ← πλήρες spec των archetypes (traits + compounds)
├── DEVELOPMENT.md             ← setup/run/build του desktop stack
├── package.json               ← root: npm run dev / npm run dist
├── data/
│   └── nba_stats_full.csv     ← merged dataset (δεν είναι στο git)
├── pipeline/
│   └── fetch_nba_data.py      ← fetch nba_api → CSV  [DONE]
├── src/                       ← κοινός πυρήνας (ο backend τον wrap-άρει, δεν τον μεταλλάσσει)
│   ├── preprocessing.py       ← load, clean, normalize  [DONE]
│   ├── archetypes.py          ← trait signals + presets + classifier  [DONE]
│   └── similarity.py          ← matching engine  [DONE]
├── backend/                   ← FastAPI API (wrap-άρει το src/)  [DONE]
│   └── store.py               ← JSON repo: prospects.json + searches.json (atomic write)  [DONE]
├── frontend/                  ← React + TS + Vite (Industry dark design system)  [DONE]
│   └── src/screens/           ← Home, Search, Prospects, ProspectForm (react-router HashRouter)  [DONE]
├── electron/                  ← desktop shell (spawn backend + load UI)  [DONE]
├── validation/                ← measurement harnesses (δεν αλλάζουν το src/)
│   ├── tune_threshold.py      ← per-trait P/R/F1 + threshold sweep → REPORT.md  [DONE]
│   ├── defense_impact.py      ← era balance / corrupt rows / def_rating → DEFENSE_IMPACT.md  [DONE]
│   └── triage_archetypes.py   ← misses: bug vs ground truth → TRIAGE.md  [DONE]
├── tests/                     ← pytest suite (73 tests)  [DONE]
└── app/
    └── streamlit_app.py       ← Streamlit UI (legacy, λειτουργικό)  [DONE]
```

---

## Setup

**Data (μία φορά, τρέχει μόνο τοπικά — nba_api δεν λειτουργεί σε sandbox):**
```bash
pip install nba_api pandas scikit-learn numpy
python pipeline/fetch_nba_data.py     # → data/nba_stats_full.csv
```

**Desktop app (Electron + FastAPI + React) — κύρια κατεύθυνση:**
```bash
pip install -r backend/requirements.txt
npm install            # root: electron toolchain + (postinstall) frontend deps
npm run dev            # backend + Vite + Electron μαζί (concurrently)
```
Λεπτομέρειες, build & troubleshooting: **[`DEVELOPMENT.md`](./DEVELOPMENT.md)**.

**Ή μόνο το backend API:**
```bash
cd backend && uvicorn main:app --reload      # → http://127.0.0.1:8000/docs
```

**Tests & validation harnesses** (χρειάζονται το dataset· αλλιώς κάνουν skip):
```bash
python -m pytest tests/ -q
```
```bash
python validation/tune_threshold.py     # → validation/REPORT.md
```
```bash
python validation/defense_impact.py     # → validation/DEFENSE_IMPACT.md
```
```bash
python validation/triage_archetypes.py  # → validation/TRIAGE.md
```

> Prospects + search history γράφονται σε `./.prospectmatch-data/` (dev) ή στο path
> του `PROSPECTMATCH_DATA_DIR` env var (packaged app) — βλ. `DEVELOPMENT.md`.

**Ή το legacy Streamlit UI:**
```bash
pip install streamlit plotly
streamlit run app/streamlit_app.py
```

---

## Data sources

**nba_api** — box score + advanced stats (1996–σήμερα), scoring profile (2013-14+), hustle stats (2015-16+).

**Kaggle (NBA Draft Combine)** — `wingspan` (2000+), που δεν υπάρχει στο API.

Τι **δεν** έχουμε (συνειδητές αποφάσεις):
- `VORP`, `PER`, `WS/48` — Basketball-Reference exclusive· limitation που τεκμηριώνεται.
- Wingspan μόνο 2000+· athleticism/vertical εκτός scope.

---

## Σχεδιαστικές αρχές

- **Ακρίβεια + αιτιολόγηση** — κάθε feature/βάρος έχει λόγο ύπαρξης.
- **Masked similarity** — stats που ο χρήστης δεν ορίζει δεν επηρεάζουν το score.
- **Honest limitations** — η άμυνα πιάνεται αδύναμα από box-score stats· τα defensive traits έχουν τα περισσότερα λάθη, και αυτό τεκμηριώνεται αντί να κρύβεται.
- **Επεκτασιμότητα χωρίς over-engineering** — multi-league αργότερα, καθαρά, χωρίς να περιπλέκουμε το τώρα.