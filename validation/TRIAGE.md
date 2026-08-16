# Archetype Triage

Threshold: **0.6** · dataset rows: **8382** · labels: **72**

## 1. Shadowed presets

Το `_label_archetype()` κρατά το preset με τα **περισσότερα** traits.
Αν το preset A είναι subset του B, τότε όποιος ενεργοποιεί το A συνήθως
ενεργοποιεί και το B — και το A δεν εμφανίζεται ποτέ.

| Preset | Φορές σε χρήση | Σκιάζεται από |
|---|---|---|
| `Two-Way Wing` | 10 | `Two-Way Slashing Star`, `Point Forward` |
| `3-and-D Wing` | 21 | `Two-Way Sharpshooter`, `Connector / Glue Wing`, `Stretch Four / Combo Forward` |
| `Defensive Playmaker` | 44 | `Two-Way Lead Guard` |
| `Sharpshooter` | 118 | `Two-Way Sharpshooter` |
| `Pure Shooter` | 123 | `Sharpshooter`, `Two-Way Sharpshooter` |
| `Putback Finisher` | 130 | `Energy Big` |
| `Slashing Guard` | 142 | `Bucket-Getter`, `Two-Way Slashing Star`, `All-Around Forward` |
| `Shooting Stretch Big` | 156 | `Stretch Four / Combo Forward` |
| `Pure Defensive Center` | 171 | `Rim-Running Anchor` |
| `Instant Offense` | 189 | `Bucket-Getter`, `Wing Scorer` |
| `Stretch Big` | 417 | `Versatile Swiss-Army Big` |

> Κανένα preset δεν είναι εντελώς απρόσιτο.

## 2. Triage των 48 misses

| Κατηγορία | Πλήθος | Είδος δουλειάς |
|---|---|---|
| A. ΛΕΙΠΕΙ TRAIT | 30 | τεχνικό |
| B. ΠΙΟ ΣΥΓΚΕΚΡΙΜΕΝΟ LABEL | 2 | **ground truth** |
| C. ΛΙΓΟΤΕΡΟ ΣΥΓΚΕΚΡΙΜΕΝΟ | 3 | τεχνικό |
| D. POSITION MISMATCH | 0 | design |
| E. ΑΛΛΟΣ ΚΛΑΔΟΣ | 13 | ανά περίπτωση |

### A. ΛΕΙΠΕΙ TRAIT — τεχνικό, ΔΙΟΡΘΩΣΙΜΟ  (30)

_Ο classifier δεν άναψε trait που το expected preset απαιτεί. Δούλεψε στα signals του trait, όχι στο ground truth._

| Παίκτης | Θέση | Expected | Got | Λείπουν traits |
|---|---|---|---|---|
| Luka Doncic | G-F | `Scoring Lead Guard` | `Two-Way Lead Guard` | midrange_scorer |
| LaMelo Ball | G | `Scoring Lead Guard` | `Floor General` | midrange_scorer |
| Cade Cunningham | G | `Scoring Lead Guard` | `Floor General` | midrange_scorer |
| Jrue Holiday | G | `Two-Way Lead Guard` | `Pure Point Guard` | on_ball_creator |
| Donovan Mitchell | G | `Bucket-Getter` | `Two-Way Lead Guard` | slasher |
| De'Aaron Fox | G | `Slashing Guard` | `Two-Way Lead Guard` | slasher |
| Marcus Smart | G | `3-and-D Guard` | `Defensive Playmaker` | spot_up_shooter |
| Damian Lillard | G | `Sharpshooter` | `Two-Way Lead Guard` | efficient_finisher |
| Jaylen Brown | G-F | `Two-Way Slashing Star` | `Instant Offense` | slasher, versatile_wing_defender |
| Anthony Edwards | G | `Two-Way Slashing Star` | `Instant Offense` | slasher _(structural: versatile_wing_defender)_ |
| Kevin Durant | F | `Wing Scorer` | `Point Center` | midrange_scorer _(structural: movement_shooter)_ |
| Brandon Ingram | F | `Wing Scorer` | `All-Around Forward` | — _(structural: movement_shooter)_ |
| Mikal Bridges | G-F | `3-and-D Wing` | `Sharpshooter` | versatile_wing_defender |
| Herbert Jones | F | `3-and-D Wing` | `Helping Wing Defender` | spot_up_shooter |
| Jaden McDaniels | F | `3-and-D Wing` | `Two-Way Help Defender` | spot_up_shooter |
| Josh Hart | G | `Connector / Glue Wing` | `Pure Point Guard` | spot_up_shooter _(structural: versatile_wing_defender)_ |
| Royce O'Neale | F | `Connector / Glue Wing` | `Stretch Big` | versatile_wing_defender |
| Aaron Gordon | F | `Athletic Finisher Wing` | `Stretch Big` | slasher, versatile_wing_defender |
| Andrew Wiggins | F | `Athletic Finisher Wing` | `Shooting Stretch Big` | efficient_finisher, slasher, versatile_wing_defender |
| Domantas Sabonis | F-C | `Point Center` | `All-Around Forward` | post_scorer |
| Alperen Sengun | C | `Point Center` | `Playmaking Rim Protector` | efficient_finisher |
| Lauri Markkanen | F-C | `Stretch Big` | `Shooting Stretch Big` | efficient_finisher |
| Al Horford | F-C | `Versatile Swiss-Army Big` | `Shooting Stretch Big` | efficient_finisher, playmaking_big, versatile_wing_defender |
| Steven Adams | C | `Energy Big` | `Rim-Running Anchor` | help_defender |
| Nic Claxton | C | `Energy Big` | `Rim-Running Anchor` | help_defender |
| Jonas Valanciunas | C | `Throwback Post Hub` | `Glass Cleaner` | post_scorer |
| Nikola Vucevic | C | `Throwback Post Hub` | `Stretch Big` | post_scorer |
| Pascal Siakam | F | `Modern Two-Way Forward` | `Versatile Swiss-Army Big` | slasher |
| Julius Randle | F-C | `Modern Two-Way Forward` | `Creating Playmaking Big` | slasher, versatile_wing_defender |
| Paolo Banchero | F | `Modern Two-Way Forward` | `All-Around Forward` | versatile_wing_defender |

### B. ΠΙΟ ΣΥΓΚΕΚΡΙΜΕΝΟ LABEL — ΑΠΟΦΑΣΗ GROUND TRUTH  (2)

_Το expected είναι subset του got: ο classifier βρήκε ΠΕΡΙΣΣΟΤΕΡΑ traits. Συχνά το got είναι σωστότερο → σκέψου `accept_also` στο labels.py._

| Παίκτης | Θέση | Expected | Got | Λείπουν traits |
|---|---|---|---|---|
| Jakob Poeltl | C | `Pure Defensive Center` | `Rim-Running Anchor` | — |
| Mitchell Robinson | F-C | `Pure Defensive Center` | `Rim-Running Anchor` | — |

### C. ΛΙΓΟΤΕΡΟ ΣΥΓΚΕΚΡΙΜΕΝΟ — τεχνικό  (3)

_Το got είναι subset του expected: έλειψε ένα trait για το πλήρες preset._

| Παίκτης | Θέση | Expected | Got | Λείπουν traits |
|---|---|---|---|---|
| Klay Thompson | G | `Sharpshooter` | `Pure Shooter` | efficient_finisher |
| Naz Reid | F-C | `Stretch Four / Combo Forward` | `Shooting Stretch Big` | versatile_wing_defender |
| Grant Williams | F | `Stretch Four / Combo Forward` | `Shooting Stretch Big` | versatile_wing_defender |

### D. POSITION MISMATCH — design gap στο PRESET_POSITIONS  (0)

_Κανένα position-valid preset δεν ταίριαξε, οπότε κέρδισε ένα άκυρο._

_(καμία)_

### E. ΑΛΛΟΣ ΚΛΑΔΟΣ — ανά περίπτωση  (13)

_Καμία subset σχέση· ο classifier πήγε σε τελείως άλλη οικογένεια._

| Παίκτης | Θέση | Expected | Got | Λείπουν traits |
|---|---|---|---|---|
| Tyrese Haliburton | G | `Floor General` | `Two-Way Lead Guard` | — |
| Tyler Herro | G | `Instant Offense` | `Floor General` | — |
| Malik Monk | G | `Instant Offense` | `Floor General` | — |
| Norman Powell | G | `Instant Offense` | `Sharpshooter` | — |
| Ja Morant | G | `Slashing Guard` | `Two-Way Lead Guard` | — |
| Derrick White | G | `3-and-D Guard` | `Sharpshooter` | — |
| Jayson Tatum | G-F | `Two-Way Wing` | `Two-Way Lead Guard` | — |
| Paul George | F | `Two-Way Wing` | `Defensive Playmaking Big` | — |
| DeMar DeRozan | G-F | `Wing Scorer` | `Scoring Lead Guard` | — |
| Scottie Barnes | G-F | `Point Forward` | `Two-Way Lead Guard` | — |
| Joel Embiid | F-C | `Two-Way Scoring Big` | `Point Center` | — |
| Jaren Jackson Jr. | F-C | `Stretch Rim Protector` | `Modern Two-Way Forward` | — |
| Isaiah Hartenstein | F-C | `Energy Big` | `Rim-Running Anchor` | — |

## 3. Ποιο trait ξεκλειδώνει τα περισσότερα misses

Πόσα misses θα διορθώνονταν αν το trait έπιανε σωστά (κατηγορίες A + C).
Αυτή είναι η σειρά προτεραιότητας για τεχνική δουλειά.

| Trait | Misses που ξεκλειδώνει |
|---|---|
| `versatile_wing_defender` | 10 |
| `slasher` | 8 |
| `efficient_finisher` | 6 |
| `midrange_scorer` | 4 |
| `spot_up_shooter` | 4 |
| `post_scorer` | 3 |
| `help_defender` | 2 |
| `on_ball_creator` | 1 |
| `playmaking_big` | 1 |

> Προσοχή: ένα miss μπορεί να χρειάζεται **περισσότερα** από ένα traits,
> οπότε τα νούμερα δεν αθροίζονται στο σύνολο των misses.

