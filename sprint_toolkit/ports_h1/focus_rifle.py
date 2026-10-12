r"""Focus Rifle (Halo Reach, wave B7): a CONTINUOUS BEAM on heat + battery with two zoom levels, on a
copy of the Halo 1 PLASMA RIFLE (the yardstick, step 4a). Nearest shapes: plasma_repeater.py /
needle_rifle.py for the Reach plumbing, sentinel_beam.py for the beam on heat + battery (the 15/s
cap, the end-on contrail, the first-person offset, the held-trigger hum), beam_rifle.py for the
scope. Built in parallel with B5 (the Concussion Rifle): test level b30, zoom glyphs at
hud_reticles 48-51 only (H1_PORT_PLAN "Running two ports in parallel").

STEP 4a (user, 2026-10-12; h1_role_compare.py focus_rifle). Reach (HREK, h3_weapon_values --kit
reach): a spew beam, 3 a round (plasma_fast) x 30/s = 90 dps, 4000 wu/s, range 120, error 0,
heat 0.025 a round, loss 0.35 / 0.23 overheated, recovery 0.1, overheated 1, battery 0.0016125 a
round (campaign the same: 620 rounds = 20.7 s), zoom 2 (3.5, 9.5), aim 2/10 4/10, strike_melee.
REACH COOLS WHILE FIRING: the user's stopwatch in Reach, ~2.5 s to overheat from cold = 0.75 heat/s
generated - 0.35 loss (the meter never visibly falls); 'no cooling' would be 1.33 s. Halo 1 fires a
held 30/s at 15/s (the SMG / Sentinel Beam observation): per-SECOND damage, heat and battery are
kept -> 6 a round, battery 1/310; Halo 1 cools while firing at its ONE loss (the Plasma Repeater's
probe) -> heat a round fitted so the gun overheats on the same second as Reach."""
from ._common import reserved

PORT = reserved(
    order=25, wave='B7', name='Focus Rifle', source='Halo Reach',
    messages=(83, 84), icon=45, reticle=34, label='fo', teach_from='sr',
    sound_dir='sound\\weapons\\focus_rifle_port', weapon_dir='weapons\\focus rifle',
    yardstick={
        # step 4a (user, 2026-10-12): 'Plasma Rifle, check the H4 port for reference'
        'pick': 'Plasma Rifle',
        'reason': ("the heat + battery Covenant automatic of both games (Reach has one; the sniper "
                   "has no heat, battery or Flood damage, the plasma pistol is tapped). DEFAULT = "
                   "Reach's own numbers at Halo 1's 15/s (6 a round, overheat on the 39th round at "
                   "2.53 s = Reach's ~2.5 s, one heat loss = the MEAN of Reach's 0.35 / 0.23 (user; "
                   "the Beam Rifle's precedent): 0.29, a 3.1 s vent; Reach 3.9 s). BALANCED = the "
                   "plasma-rifle ratio. Materials (user, the Plasma Repeater's rule): the H1 plasma "
                   "rifle bolt's table in DEFAULT, x Reach's plasma_fast / plasma_slow per armour "
                   "class in BALANCED. The Halo 4 port of the same weapon (reference): Reach's own "
                   "values, heat + battery as the port's own, heat cards from the Sentinel Beam "
                   "(card_donors), ammo cards skipped"),
        # DEFAULT = Reach's own (above); these are the BALANCED rows (H1 plasma rifle x Reach focus
        # rifle / Reach plasma rifle). Reach plasma rifle: 10 plasma_slow x 6 -> 9/s (ramp 0.8 s),
        # heat 0.15 a round, loss 0.8525 / 0.35 overheated, recovery 0.1, battery 0.0025, 25 wu/s,
        # range 40, aim 5/12 9/18. H1 plasma rifle 12-14 (13) x 7 -> 10/s, heat 0.08, loss 0.3,
        # recovery 0.25, battery 0.005, 50 -> 25 wu/s, no range, aim 5/25 12/25
        'balanced': {
            'damage': 8.67,              # dps 13 x 10 = 130 x FR 90 / Reach PR 90 -> / 15/s
            'rate': (15.0, 15.0),        # 10 x 30/9 = 33 -> Halo 1's 15/s cap (damage keeps the dps)
            'overheat_s': 3.0,           # TIME TO OVERHEAT (both games cool while firing): H1 PR
                                         # 2.67 s x FR 2.47 / Reach PR 2.17 (19 rounds) -> the 46th round
            'heat_per_round': 0.0346,    # fitted under Halo 1's fire rule with the loss below
            'loss': 0.197,               # 0.3 (= the OVERHEATED loss, the Beam Rifle's reading) x 0.23/0.35
            'recovery': 0.25,            # 0.25 x 0.1/0.1 (vent 1 -> 0.25 at 0.197 = 3.8 s)
            'battery': 1 / 140.0,        # by TIME: H1 PR 20 s x FR 20.7 / Reach PR 44.4 = 9.3 s -> 140 rounds
            'velocity': 8000.0,          # 50 x 4000/25 -- see 4b (overpenetration: the laser's 1000)
            'range': 120.0,              # the H1 plasma rifle bolt has none: a zero on one side, Reach's
            'aim': (2.0, 20.83, 5.33, 13.89),  # 5 x 2/5, 25 x 10/12; 12 x 4/9, 25 x 10/18
            'zoom': None,                # the plasma rifle has none: Reach's 2 levels 3.5 / 9.5 kept
            'materials': 'x plasma_fast / plasma_slow (RP_FAST_SLOW in h1_role_compare)',
            'melee': None},              # Reach shares strike_melee: x1 = the plasma rifle's own
        'measured': 'h1_role_compare.py focus_rifle (rows "FR = Reach B, loss .29" and "FR = PR ratio")',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\focus_rifle\\focus_rifle',
            'provisional': 'Plasma Rifle',
            'alternatives': ['Sniper Rifle', 'Plasma Pistol'],
            'direct': None,
            'peers': ['Sniper Rifle', 'Sentinel Beam'],
            'why': "continuous instant beam, heat + battery (the H1 Sentinel Beam's model, but Reach has no Sentinel Beam)",
            'lacks': "Reach's 30 rounds a second (Halo 1: 15, per-second values kept); its TWO heat "
                     "losses (Halo 1: one, the mean); a beam drawn as one continuous ribbon (Halo 1: "
                     "a contrail a round)"}},
    # step 11: the source game's ai\generic entry (22 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\focus_rifle\\focus_rifle'},
)
