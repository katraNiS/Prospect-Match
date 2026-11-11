"""
Primitive trait definitions, compound archetype presets, και trait classifier.

Architecture:
  - TRAITS: 18 primitive traits με signals (weighted stats + κατεύθυνση)
  - COMPOUNDS: 29 named presets ως frozensets of trait combinations
  - classify(df): score κάθε παίκτη σε κάθε trait → compound archetype label
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

ALL_POSITIONS = ["G", "G-F", "F", "F-C", "C"]
BIG_POSITIONS = ["F", "F-C", "C"]   # group για position-relative normalization

# Threshold: score >= TRAIT_THRESHOLD → trait "ανάβει"
#
# ΜΗΝ το ανεβάσεις κοιτώντας μόνο το macro-F1 του validation/REPORT.md.
# Το REPORT δείχνει "best global threshold 0.9" αλλά αυτό μετριέται στα 72
# labeled stars, που έχουν 6-10 active traits και δεν γίνονται ΠΟΤΕ
# Unclassified — δηλαδή η μετρική είναι τυφλή στο πραγματικό κόστος.
# Μετρημένο σε ολόκληρο το dataset (8382 rows):
#
#   thr    macro-F1   top-1    Unclassified   presets σε χρήση
#   0.6      0.597    20/72       15.0%             35        ← εδώ
#   0.75     0.618    18/72       23.2%             35
#   0.9      0.623    20/72       31.8%             31
#
# Στο 0.9 κερδίζουμε +0.026 macro-F1 με ΙΔΙΟ archetype top-1, αλλά ένας στους
# τρεις παίκτες μένει χωρίς label στο UI και 4 archetypes παύουν να εμφανίζονται.
# Ποιοτικά: ο Alex Caruso χάνει το spot_up_shooter και πέφτει από "3-and-D Guard"
# σε fallback σύνθεση "Efficient Defender"· ο Giannis χάνει το efficient_finisher.
#
# Σημείωση: τα per-trait βέλτιστα κατώφλια συγκρούονται ευθέως
# (versatile_wing_defender → 0.4, point_of_attack_defender → 0.95), οπότε κανένα
# global threshold δεν είναι σωστό για όλα. Per-trait thresholds ΔΕΝ είναι λύση
# στο τρέχον validation set: πολλά traits έχουν support 4-5 παίκτες → overfitting.
TRAIT_THRESHOLD = 0.6


@dataclass
class Signal:
    col: str            # column name στο dataset (lowercase)
    weight: float       # + = θέλουμε υψηλό, - = θέλουμε χαμηλό
    pos_rel: bool = False   # True = position-relative z-score (για bigs vs bigs)


@dataclass
class Trait:
    name: str
    positions: list[str]        # eligible position_groups
    signals: list[Signal]
    fine: bool = False          # True = αδύναμο signal, επισημαίνεται στο UI


# ─── 18 Primitive Traits ──────────────────────────────────────────────────────

TRAITS: dict[str, Trait] = {

    # ── A. Creation & on-ball scoring ──────────────────────────────────────────

    "on_ball_creator": Trait(
        name="on_ball_creator",
        positions=["G", "G-F", "F", "F-C"],
        signals=[
            Signal("usg_pct", weight=2.0),
            Signal("pts",     weight=1.5),
            Signal("fta",     weight=0.5),
            Signal("ast_pct", weight=0.5),
        ],
    ),

    "slasher": Trait(
        name="slasher",
        positions=["G", "G-F", "F", "F-C"],
        signals=[
            Signal("fta",    weight=2.0),
            Signal("fg_pct", weight=1.5),
            Signal("pts",    weight=0.5),
            Signal("fg3a",   weight=-1.0),  # slashers αποφεύγουν τα 3s
        ],
    ),

    "midrange_scorer": Trait(
        name="midrange_scorer",
        positions=["G", "G-F", "F", "F-C"],
        signals=[
            # Κύριο signal: % πόντων από mid-range (από Scoring endpoint).
            # Πριν: ορίζαμε αρνητικά (χαμηλό fg3a) — έπιανε bigs, όχι πραγματικούς midrange scorers.
            # Τώρα: θετικό, direct signal. DeRozan ~35%, Curry ~5% → διακρίνει σωστά.
            Signal("pct_pts_2pt_mr", weight=3.0),
            Signal("pts",              weight=0.5),  # χρειάζεται volume για να μετρά
            Signal("fg3a",             weight=-0.5), # αδύνατο backup — διατηρείται για pre-Scoring seasons
        ],
        fine=True,  # εξαρτάται από Scoring endpoint data
    ),

    # ── B. Shooting (off-ball) ─────────────────────────────────────────────────

    "spot_up_shooter": Trait(
        name="spot_up_shooter",
        positions=["G", "G-F", "F", "F-C"],
        signals=[
            Signal("fg3_pct", weight=2.0),
            Signal("fg3a",    weight=1.5),
            Signal("usg_pct", weight=-0.5),  # catch-and-shoot = χαμηλό usage
            Signal("ts_pct",  weight=0.5),
            Signal("tov",     weight=-0.5),
        ],
    ),

    # usg_pct ως proxy για self-creation — χωρίς shot-tracking data δεν ξεχωρίζει πλήρως
    "movement_shooter": Trait(
        name="movement_shooter",
        positions=["G", "G-F"],
        signals=[
            Signal("fg3_pct", weight=2.0),
            Signal("fg3a",    weight=1.5),
            Signal("usg_pct", weight=1.0),  # υψηλότερο από spot_up = self-creation
            Signal("pts",     weight=0.5),
        ],
        fine=True,
    ),

    # ── C. Playmaking ──────────────────────────────────────────────────────────

    "lead_playmaker": Trait(
        name="lead_playmaker",
        positions=["G", "G-F"],
        signals=[
            Signal("ast_pct", weight=3.0),
            Signal("ast_to",  weight=1.5),
            Signal("usg_pct", weight=0.5),
        ],
    ),

    "connective_passer": Trait(
        name="connective_passer",
        positions=["G", "G-F", "F", "F-C"],
        signals=[
            Signal("ast_to",  weight=2.0),
            Signal("ast_pct", weight=1.0),
            Signal("tov",     weight=-1.0),
            Signal("usg_pct", weight=-0.5),  # secondary role = χαμηλό usage
        ],
    ),

    "playmaking_big": Trait(
        name="playmaking_big",
        positions=["F", "F-C", "C"],
        signals=[
            Signal("ast_pct", weight=3.0, pos_rel=True),  # vs άλλα bigs
            Signal("ast_to",  weight=1.5),
            Signal("pts",     weight=0.5),
            # reb_pct: οι πραγματικοί playmaking bigs (Jokić, Draymond) rebound καλά —
            # βοηθά να ξεχωρίσουν από stretch bigs που απλώς έχουν καλό ast_to
            Signal("reb_pct", weight=0.5, pos_rel=True),
        ],
    ),

    # ── D. Interior offense ────────────────────────────────────────────────────

    "post_scorer": Trait(
        name="post_scorer",
        positions=["F", "F-C", "C"],
        signals=[
            Signal("usg_pct", weight=2.0, pos_rel=True),
            Signal("pts",     weight=1.5),
            Signal("fta",     weight=1.0),
            Signal("fg3a",    weight=-1.5, pos_rel=True),  # post scorer ≠ perimeter shooter
        ],
    ),

    "roll_finisher": Trait(
        name="roll_finisher",
        positions=["F", "F-C", "C"],
        signals=[
            Signal("fg_pct",   weight=3.0),
            Signal("usg_pct",  weight=-1.0),   # finisher, όχι ball-handler
            Signal("oreb_pct", weight=0.5),
            Signal("fg3a",     weight=-1.5, pos_rel=True),
            Signal("ast_pct",  weight=-0.5),
        ],
    ),

    "stretch_big": Trait(
        name="stretch_big",
        positions=["F", "F-C", "C"],
        signals=[
            Signal("fg3a",    weight=3.0, pos_rel=True),  # κύριο signal: 3PA volume για big
            Signal("fg3_pct", weight=1.5),
            Signal("ts_pct",  weight=0.5),
        ],
    ),

    # ── E. Perimeter defense ───────────────────────────────────────────────────

    "point_of_attack_defender": Trait(
        name="point_of_attack_defender",
        positions=["G", "G-F"],
        signals=[
            Signal("stl",         weight=2.0),
            Signal("deflections", weight=2.0),   # direct δείκτης ball pressure (2016-17+)
            Signal("def_rating",  weight=-1.5),  # χαμηλό = καλή άμυνα
            Signal("usg_pct",     weight=-0.5),
            # Matchup-based perimeter defense (Phase 1d): πόσο χειρότερα σουτάρουν
            # οι αντίπαλοι από το 3ποντο όταν τους φυλάει. Αρνητικό = καλή άμυνα.
            #
            # Το trait είχε recall 1.00 αλλά precision 0.24 — άναβε για σχεδόν
            # κάθε guard με πολλά steals. Το d_fg3_diff μετράει ΑΠΟΤΕΛΕΣΜΑ και
            # κόβει τα false positives: precision 0.24 → 0.31, F1 0.385 → 0.476
            # (+24% relative), macro-F1 0.600 → 0.605, top-1 21/72 → 22/72.
            # Το -2.5 είναι σημείο κορεσμού (το -3.0 δίνει ίδιο αποτέλεσμα).
            Signal("d_fg3_diff",  weight=-2.5),
        ],
        fine=True,  # def_rating team stat · tracking signals μόνο από 2013-14/2016-17
    ),

    "versatile_wing_defender": Trait(
        name="versatile_wing_defender",
        positions=["G-F", "F", "F-C"],
        signals=[
            # Deflections: ο μόνος individual proxy για wing defense που έχουμε.
            # Μετρημένο: αφαίρεσή του ρίχνει το recall σε 0.05 — δεν υπάρχει
            # εναλλακτικό signal στο dataset.
            Signal("deflections", weight=2.5),
            Signal("def_rating",  weight=-2.0),
            Signal("stl",         weight=1.0),
            Signal("blk",         weight=0.5),
            # ── ΑΡΝΗΤΙΚΑ: "wing" σημαίνει ΟΧΙ big ────────────────────────────
            # Το trait είναι eligible σε G-F/F/F-C. Μέσα σε αυτό το pool, τα
            # reb_pct/height_cm/screen_assists δεν ξεχωρίζουν καλούς wing
            # defenders — ξεχωρίζουν BIGS. Είχαν θετικά weights (λογική «ο wing
            # defender είναι ψηλός και μαζεύει»), δηλαδή το trait ανταμείβε
            # ακριβώς τα χαρακτηριστικά των λάθος παικτών: 6 από τα 8 false
            # positives ήταν F-C (Embiid, KAT, Hartenstein, AD, Bam, JJJ).
            #
            # Μετρημένο separation expected vs FP (Cohen's d):
            #   reb_pct -1.80 | screen_assists -1.59 | blk -1.40 | height -1.39
            # δηλαδή όλα δείχνουν προς την ΑΝΤΙΘΕΤΗ κατεύθυνση απ' ό,τι υπέθετε
            # ο αρχικός σχεδιασμός. Το screen_assists είναι ο καθαρότερος
            # big-marker (screen setting = big-man action), γι' αυτό μπήκε.
            #
            # Αποτέλεσμα: precision 0.529 -> 0.692, F1 0.486 -> 0.545,
            # macro-F1 0.597 -> 0.600, archetype top-1 20/72 -> 21/72.
            Signal("reb_pct",        weight=-0.5),
            Signal("height_cm",      weight=-0.5),
            Signal("screen_assists", weight=-1.0),
            # wingspan_cm: θα προστεθεί όταν έρθει το Kaggle Draft Combine dataset
            #
            # ΓΝΩΣΤΟ ΟΡΙΟ — recall 0.450, δεν διορθώνεται με weights:
            # οι misses (Mikal Bridges 1.71 defl, Aaron Gordon 0.94, Andrew
            # Wiggins 1.52) είναι αναγνωρισμένοι wing defenders με ΧΑΜΗΛΑ
            # deflections, γιατί το deflections μετράει ΣΤΥΛ (ball-hawking),
            # όχι ποιότητα. Ο Bridges είναι elite on-ball defender που δεν
            # κάνει gambles· ο Luka Doncic έχει 3.38 deflections και είναι
            # γνωστά κακός defender. Οι δύο κατανομές επικαλύπτονται πλήρως
            # (misses -0.63..+0.54, FPs +0.85..+2.88) — κανένα threshold δεν
            # τις χωρίζει. Χρειάζονται matchup/DFG%/contested-shot δεδομένα.
        ],
    ),

    # ── F. Interior defense ────────────────────────────────────────────────────

    "rim_protector": Trait(
        name="rim_protector",
        # "F" προστέθηκε: shot-blocking forwards (Draymond, AD-as-PF) πρέπει να είναι
        # eligible — το blk signal (pos_rel=False) ήδη ζητά υψηλά blocks, οπότε
        # απλοί forwards χωρίς rim protection δεν ανάβουν το trait.
        positions=["F", "F-C", "C"],
        signals=[
            Signal("blk",        weight=3.0),
            Signal("def_rating", weight=-1.5),
            Signal("dreb_pct",   weight=0.5),
            Signal("height_cm",  weight=0.5),
            Signal("fg3a",       weight=-0.5, pos_rel=True),
            # wingspan_cm: θα προστεθεί όταν έρθει το Kaggle dataset
        ],
    ),

    "help_defender": Trait(
        name="help_defender",
        positions=["F", "F-C", "C"],
        signals=[
            Signal("deflections",   weight=1.5),
            # pos_rel=True: guards έχουν globally υψηλότερα stl/blk → χωρίς pos_rel
            # ένας average guard θα σκοράρει καλύτερα από έναν elite defensive big.
            Signal("stl",           weight=1.5, pos_rel=True),
            Signal("blk",           weight=1.5, pos_rel=True),
            Signal("def_rating",    weight=-2.0),
        ],
        fine=True,  # def_rating εξαρτάται από ομάδα · deflections μόνο 2015-16+
    ),

    # ── G. Rebounding ──────────────────────────────────────────────────────────

    "defensive_rebounder": Trait(
        name="defensive_rebounder",
        positions=["F", "F-C", "C"],
        signals=[
            Signal("dreb_pct",   weight=3.0),
            Signal("reb_pct",    weight=1.0),
            Signal("height_cm",  weight=0.3),
            Signal("weight_lbs", weight=0.3),
        ],
    ),

    "offensive_rebounder": Trait(
        name="offensive_rebounder",
        positions=["F-C", "C"],
        signals=[
            Signal("oreb_pct",   weight=3.0),
            Signal("fg_pct",     weight=0.5),   # putbacks
            Signal("weight_lbs", weight=0.3),
        ],
    ),

    # ── H. Efficiency ──────────────────────────────────────────────────────────

    "efficient_finisher": Trait(
        name="efficient_finisher",
        positions=ALL_POSITIONS,
        signals=[
            # Αφαιρέθηκε usg_pct=-1.0: τιμωρούσε τον Jokić (ψηλό usage αλλά elite efficiency)
            # και μπέρδευε το concept. Το trait τώρα ορίζεται αμιγώς από efficiency metrics.
            Signal("ts_pct",  weight=2.0),
            Signal("efg_pct", weight=1.5),
            Signal("fg_pct",  weight=1.0),
            Signal("tov",     weight=-1.0),
        ],
    ),
}


# ─── 29 Compound Archetypes ──────────────────────────────────────────────────
# Preset match: όταν ΟΛΑ τα traits ενός preset ανάβουν, ο παίκτης παίρνει αυτό το όνομα.
# Αν ταιριάζουν πολλά presets, κρατάμε το πιο συγκεκριμένο (περισσότερα traits).

COMPOUNDS: dict[str, frozenset[str]] = {
    # Guards ──────────────────────────────────────────────────────────────────
    "Floor General":
        frozenset({"lead_playmaker", "movement_shooter"}),
    # ΠΡΟΣΟΧΗ στη σειρά: το "Wing Scorer" ΠΡΕΠΕΙ να προηγείται του "Scoring Lead
    # Guard" — ίδιο μέγεθος (3 traits), κοινά on_ball_creator+midrange_scorer.
    # Χωρίς αυτό, players σαν τον DeMar DeRozan (movement_shooter + lead_playmaker
    # + midrange_scorer + on_ball_creator ενεργά) ισοπαλούσαν και έπαιρναν πάντα
    # "Scoring Lead Guard" (dict order), ενώ το position-eligible label για G-F
    # wings είναι "Wing Scorer". Μετρημένο: top-1 +1, macro-F1 αμετάβλητο, 0
    # παλινδρομήσεις (Scoring Lead Guard παραμένει σωστό εκεί που pos_ok διαφέρει).
    "Wing Scorer":
        frozenset({"on_ball_creator", "midrange_scorer", "movement_shooter"}),
    "Scoring Lead Guard":
        frozenset({"on_ball_creator", "lead_playmaker", "midrange_scorer"}),
    # Ίδιο pattern: "Point Forward" πριν το "Two-Way Lead Guard" (3 traits,
    # κοινά on_ball_creator+lead_playmaker). Ο Scottie Barnes ισοπαλούσε και
    # έχανε το πιο συγκεκριμένο "Point Forward" (G-F/F/F-C only) υπέρ του
    # guard-only "Two-Way Lead Guard". top-1 +1, macro-F1 αμετάβλητο, 0 παλινδρομήσεις.
    "Point Forward":
        frozenset({"on_ball_creator", "lead_playmaker", "versatile_wing_defender"}),
    "Two-Way Lead Guard":
        frozenset({"on_ball_creator", "lead_playmaker", "point_of_attack_defender"}),
    "Pure Point Guard":
        frozenset({"lead_playmaker", "connective_passer"}),
    "Bucket-Getter":
        frozenset({"on_ball_creator", "movement_shooter", "slasher"}),
    "Instant Offense":
        frozenset({"on_ball_creator", "movement_shooter"}),
    "Slashing Guard":
        frozenset({"slasher", "on_ball_creator"}),
    # ΠΡΟΣΟΧΗ στη σειρά: το "3-and-D Wing" ΠΡΕΠΕΙ να προηγείται του
    # "3-and-D Guard". Έχουν και τα δύο 2 traits, οπότε για έναν G-F παίκτη το
    # score (pos_ok, trait_count) ισοπαλεί και αποφασίζει το dict ordering.
    # Με το Guard πρώτο, το "3-and-D Wing" ΔΕΝ εμφανιζόταν ΠΟΤΕ (0/8382 rows)
    # και 21 G-F wings (Dan Majerle, Thabo Sefolosha, Joe Ingles, Eddie Jones…)
    # έπαιρναν λανθασμένα "Guard" label. Καθαροί guards δεν επηρεάζονται: το
    # "3-and-D Wing" δεν είναι position-eligible για "G" (pos_ok=0), οπότε
    # χάνει σωστά. Μετρημένο: 21 rows άλλαξαν, macro-F1 και archetype top-1
    # έμειναν αμετάβλητα (0.600 / 21-72).
    "3-and-D Wing":
        frozenset({"spot_up_shooter", "versatile_wing_defender"}),
    "3-and-D Guard":
        frozenset({"spot_up_shooter", "point_of_attack_defender"}),
    "Defensive Playmaker":
        frozenset({"lead_playmaker", "point_of_attack_defender"}),
    "Pure Shooter":
        frozenset({"movement_shooter", "spot_up_shooter"}),
    "Sharpshooter":
        frozenset({"movement_shooter", "spot_up_shooter", "efficient_finisher"}),
    "Two-Way Sharpshooter":
        frozenset({"movement_shooter", "spot_up_shooter", "efficient_finisher", "versatile_wing_defender"}),
    # Wings ───────────────────────────────────────────────────────────────────
    "Two-Way Wing":
        frozenset({"on_ball_creator", "versatile_wing_defender"}),
    "Two-Way Slashing Star":
        frozenset({"on_ball_creator", "slasher", "versatile_wing_defender"}),
    # "Wing Scorer" και "Point Forward" ορίζονται παραπάνω, πριν τα ισοπαλά
    # "Scoring Lead Guard"/"Two-Way Lead Guard" — βλ. σχόλια εκεί.
    # "3-and-D Wing": ορίζεται παραπάνω, πριν το "3-and-D Guard" — βλ. σχόλιο εκεί.
    "Connector / Glue Wing":
        frozenset({"connective_passer", "spot_up_shooter", "versatile_wing_defender"}),
    "Athletic Finisher Wing":
        frozenset({"slasher", "versatile_wing_defender", "efficient_finisher"}),
    # Bigs ────────────────────────────────────────────────────────────────────
    "Point Center":
        frozenset({"playmaking_big", "post_scorer", "efficient_finisher"}),
    # Μετά το Point Center: για unicorns με guard+big traits αλλά χωρίς efficient_finisher (LeBron).
    # Η θέση στο dict αποφασίζει tie: Point Center (3 traits) συναντάται πρώτο,
    # οπότε Giannis/KD/Embiid (έχουν efficient_finisher) παίρνουν Point Center.
    "All-Around Forward":
        frozenset({"on_ball_creator", "slasher", "playmaking_big"}),
    "Two-Way Scoring Big":
        frozenset({"post_scorer", "rim_protector"}),
    # ΠΡΟΣΟΧΗ στη σειρά: το "Stretch Rim Protector" ΠΡΕΠΕΙ να προηγείται του
    # "Stretch Big". Ίδιο μέγεθος (2 traits), ίδιο eligible pool· χωρίς αυτή τη
    # σειρά ισοπαλούσαν στο (pos_ok, trait_count) και το dict ordering έδινε
    # πάντα "Stretch Big" — 34 χρήσεις έναντι σχεδόν διπλάσιων δυνατών (57),
    # με Brook Lopez / Myles Turner να παίρνουν λάθος label παρόλο που το
    # rim_protector τους ήταν ενεργό. Μετρημένο: top-1 22/72 → 24/72, macro-F1
    # αμετάβλητο, καμία νέα παλινδρόμηση.
    "Stretch Rim Protector":
        frozenset({"stretch_big", "rim_protector"}),
    "Stretch Big":
        frozenset({"stretch_big", "efficient_finisher"}),
    "Shooting Stretch Big":
        frozenset({"stretch_big", "spot_up_shooter"}),
    "Rim-Running Anchor":
        frozenset({"rim_protector", "roll_finisher", "defensive_rebounder"}),
    "Pure Defensive Center":
        frozenset({"rim_protector", "defensive_rebounder"}),
    "Playmaking Rim Protector":
        frozenset({"playmaking_big", "rim_protector", "help_defender"}),
    # efficient_finisher προστέθηκε για να μην το παίρνει ο Draymond (δεν είναι efficient scorer)
    "Versatile Swiss-Army Big":
        frozenset({"playmaking_big", "versatile_wing_defender", "stretch_big", "efficient_finisher"}),
    # Για Draymond-type: playmaking big + wing defense + help defense, χωρίς shooting
    "Defensive Playmaking Big":
        frozenset({"playmaking_big", "versatile_wing_defender", "help_defender"}),
    "Energy Big":
        frozenset({"offensive_rebounder", "roll_finisher", "help_defender"}),
    "Throwback Post Hub":
        frozenset({"post_scorer", "offensive_rebounder"}),
    "Glass Cleaner":
        frozenset({"defensive_rebounder", "offensive_rebounder"}),
    "Putback Finisher":
        frozenset({"roll_finisher", "offensive_rebounder"}),
    "Stretch Four / Combo Forward":
        frozenset({"stretch_big", "spot_up_shooter", "versatile_wing_defender"}),
    "Modern Two-Way Forward":
        frozenset({"stretch_big", "slasher", "versatile_wing_defender"}),
}

# Επιτρεπτές position groups ανά compound preset.
# Αν ένας παίκτης ταιριάζει σε δύο presets ίδιου μεγέθους, κερδίζει αυτό
# που ταιριάζει τη θέση του — π.χ. Porzingis (F-C) δεν πρέπει να παίρνει
# "Slashing Guard" έστω κι αν έχει active slasher + on_ball_creator.
PRESET_POSITIONS: dict[str, list[str]] = {
    # Guards
    "Floor General":             ["G", "G-F"],
    "Scoring Lead Guard":        ["G", "G-F"],
    "Two-Way Lead Guard":        ["G", "G-F"],
    "Pure Point Guard":          ["G", "G-F"],
    "Bucket-Getter":             ["G", "G-F"],
    "Instant Offense":           ["G", "G-F"],
    "Slashing Guard":            ["G", "G-F"],
    "3-and-D Guard":             ["G", "G-F"],
    "Defensive Playmaker":       ["G", "G-F"],
    "Pure Shooter":              ["G", "G-F"],
    "Sharpshooter":              ["G", "G-F", "F"],
    "Two-Way Sharpshooter":      ["G", "G-F", "F"],
    # Wings
    "Two-Way Wing":              ["G-F", "F"],
    "Two-Way Slashing Star":     ["G-F", "F"],
    "Wing Scorer":               ["G-F", "F"],
    "3-and-D Wing":              ["G-F", "F"],
    "Point Forward":             ["G-F", "F", "F-C"],
    "Connector / Glue Wing":     ["G-F", "F"],
    "Athletic Finisher Wing":    ["G-F", "F", "F-C"],
    "Stretch Four / Combo Forward": ["F", "F-C"],
    "Modern Two-Way Forward":    ["F", "F-C"],
    "All-Around Forward":        ["F", "F-C"],
    # Bigs
    "Point Center":              ["F", "F-C", "C"],
    "Two-Way Scoring Big":       ["F", "F-C", "C"],
    "Stretch Big":               ["F", "F-C", "C"],
    "Shooting Stretch Big":      ["F", "F-C", "C"],
    "Stretch Rim Protector":     ["F-C", "C"],
    "Rim-Running Anchor":        ["F-C", "C"],
    "Pure Defensive Center":     ["F-C", "C"],
    "Playmaking Rim Protector":  ["F", "F-C", "C"],
    "Versatile Swiss-Army Big":  ["F", "F-C", "C"],
    "Defensive Playmaking Big":  ["F", "F-C", "C"],
    "Energy Big":                ["F", "F-C", "C"],
    "Throwback Post Hub":        ["F", "F-C", "C"],
    "Glass Cleaner":             ["F-C", "C"],
    "Putback Finisher":          ["F", "F-C", "C"],
}


# ─── Naming helpers ───────────────────────────────────────────────────────────

_TRAIT_NOUN: dict[str, str] = {
    "on_ball_creator":          "Creator",
    "slasher":                  "Slasher",
    "midrange_scorer":          "Scorer",
    "spot_up_shooter":          "Shooter",
    "movement_shooter":         "Shooter",
    "lead_playmaker":           "Playmaker",
    "connective_passer":        "Connector",
    "playmaking_big":           "Playmaking Big",
    "post_scorer":              "Post Scorer",
    "roll_finisher":            "Roll Finisher",
    "stretch_big":              "Stretch Big",
    "point_of_attack_defender": "Defender",
    "versatile_wing_defender":  "Wing Defender",
    "rim_protector":            "Rim Protector",
    "help_defender":            "Help Defender",
    "defensive_rebounder":      "Rebounder",
    "offensive_rebounder":      "Offensive Rebounder",
    "efficient_finisher":       "Finisher",
}

_TRAIT_ADJECTIVE: dict[str, str] = {
    "on_ball_creator":          "Creating",
    "slasher":                  "Slashing",
    "midrange_scorer":          "Scoring",
    "spot_up_shooter":          "Shooting",
    "movement_shooter":         "Shooting",
    "lead_playmaker":           "Playmaking",
    "connective_passer":        "Connective",
    "playmaking_big":           "Playmaking",
    "post_scorer":              "Post-Scoring",
    "roll_finisher":            "Roll-Finishing",
    "stretch_big":              "Stretch",
    "point_of_attack_defender": "Defending",
    "versatile_wing_defender":  "Two-Way",
    "rim_protector":            "Rim-Protecting",
    "help_defender":            "Helping",
    "defensive_rebounder":      "Rebounding",
    "offensive_rebounder":      "Crashing",
    "efficient_finisher":       "Efficient",
}


# ─── Classifier ───────────────────────────────────────────────────────────────

def compute_trait_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Υπολογίζει score ανά primitive trait για κάθε παίκτη.
    Επιστρέφει df με score_<trait> columns (NaN για non-eligible positions).

    Position-relative z-scores (pos_rel=True):
    - Bigs (F, F-C, C) κανονικοποιούνται μεταξύ τους για τα ανάλογα signals.
    - Ένα avg ast_pct για Center φαίνεται φυσιολογικό vs guards αλλά ψηλό vs bigs.
    """
    result = df.copy()

    # Columns που χρειάζονται — μόνο όσα υπάρχουν στο df
    sig_cols = list({s.col for t in TRAITS.values() for s in t.signals} & set(df.columns))
    data = df[sig_cols].astype(float)

    # Global z-scores
    mu_g  = data.mean()
    std_g = data.std().replace(0, 1)
    global_z = ((data - mu_g) / std_g).fillna(0.0)

    # Position-relative z-scores για bigs (override global μόνο για big rows)
    big_mask = df["position_group"].isin(BIG_POSITIONS)
    posrel_z = global_z.copy()
    if big_mask.sum() > 1:
        big_data = data.loc[big_mask]
        mu_b  = big_data.mean()
        std_b = big_data.std().replace(0, 1)
        posrel_z.loc[big_mask] = ((big_data - mu_b) / std_b).fillna(0.0)

    for trait_name, trait in TRAITS.items():
        eligible     = df["position_group"].isin(trait.positions)
        eligible_idx = df.index[eligible]
        score        = pd.Series(np.nan, index=df.index, dtype=float)

        total_w = sum(abs(s.weight) for s in trait.signals if s.col in sig_cols)
        if total_w == 0 or not eligible.any():
            result[f"score_{trait_name}"] = score
            continue

        s_acc = pd.Series(0.0, index=eligible_idx)
        for sig in trait.signals:
            if sig.col not in sig_cols:
                continue
            z     = (posrel_z if sig.pos_rel else global_z)[sig.col]
            s_acc = s_acc + sig.weight * z.loc[eligible_idx]

        score.loc[eligible_idx] = s_acc / total_w
        result[f"score_{trait_name}"] = score

    return result


def assign_archetypes(
    df: pd.DataFrame,
    threshold: float = TRAIT_THRESHOLD,
) -> pd.DataFrame:
    """
    score >= threshold → trait active → compound archetype label.
    Προσθέτει: active_<trait>, active_traits (list), compound_archetype.
    """
    result      = df.copy()
    trait_names = list(TRAITS.keys())

    for t in trait_names:
        col = f"score_{t}"
        result[f"active_{t}"] = (result[col] >= threshold) if col in result.columns else False

    result["active_traits"] = result.apply(
        lambda row: [t for t in trait_names if row.get(f"active_{t}", False)],
        axis=1,
    )
    result["compound_archetype"] = result.apply(
        lambda row: _label_archetype(row, trait_names), axis=1
    )
    return result


def _label_archetype(row: pd.Series, trait_names: list[str]) -> str:
    active = frozenset(t for t in trait_names if row.get(f"active_{t}", False))

    if not active:
        return "Unclassified"

    # Πιο συγκεκριμένο preset που είναι υποσύνολο των active.
    # Score = (pos_ok, trait_count): position-compatibility πρωτεύει,
    # μετά ο αριθμός traits. Dict ordering ως tertiary tiebreaker.
    pos = row.get("position_group", "Unknown")
    best_name, best_score = None, (-1, 0)
    for name, preset in COMPOUNDS.items():
        if preset <= active:
            allowed = PRESET_POSITIONS.get(name)
            pos_ok  = 1 if (allowed is None or pos in allowed) else 0
            score   = (pos_ok, len(preset))
            if score > best_score:
                best_name  = name
                best_score = score

    if best_name:
        return best_name

    # Fallback: noun = κορυφαίο trait, modifier = δεύτερο
    sorted_active = sorted(
        active,
        key=lambda t: row.get(f"score_{t}", float("-inf")),
        reverse=True,
    )
    noun = _TRAIT_NOUN.get(sorted_active[0], sorted_active[0].replace("_", " ").title())
    if len(sorted_active) >= 2:
        modifier = _TRAIT_ADJECTIVE.get(
            sorted_active[1], sorted_active[1].replace("_", " ").title()
        )
        return f"{modifier} {noun}"
    return noun


def classify(df: pd.DataFrame, threshold: float = TRAIT_THRESHOLD) -> pd.DataFrame:
    """
    Κεντρική συνάρτηση.
    Input : cleaned df από preprocessing.load_and_clean()
    Output: df με score_*, active_*, active_traits, compound_archetype columns
    """
    df_scored = compute_trait_scores(df)
    return assign_archetypes(df_scored, threshold=threshold)
