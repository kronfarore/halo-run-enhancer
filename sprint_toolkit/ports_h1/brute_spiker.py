r"""Spike Rifle (Halo 3, wave A5): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=14, wave='A5', name='Spike Rifle', source='Halo 3',
    messages=(61, 62), icon=34, reticle=23, label='sk', teach_from='hp',
    sound_dir='sound\\weapons\\spiker_port', weapon_dir='weapons\\spiker',
    yardstick={
        # step 4a (user, 2026-10-08): h3_weapon_values.py (spiker / needler / AR / plasma
        # rifle) + h1_role_compare.py brute_spiker. Halo 3's spiker is bullet_slow -- the
        # AR's damage group, not the needler's plasma_slow -- and does the AR's dps (72 vs
        # 75/s). AR ratio: 12 x 12/s = 144/s (H1 AR 150), every value scales, 12/s is under
        # the 15/s cap observation; needler ratio 180/s on the needle's materials (Flood in
        # 3 shots), its spread minimum 0/0 and the needle tag's speed 4 do not scale
        'pick': 'Assault Rifle',
        'reason': "user, step 4a 2026-10-08: the same damage type (Halo 3 bullet_slow, both) "
                  "and role (magazine automatic); H1 value = H1 AR x H3 spiker / H3 AR. "
                  "Values with no AR counterpart keep Halo 3's own in both versions: air "
                  "gravity 0.2 (H3 AR 0) and the ricochet material responses",
        # DEFAULT = Halo 3's own numbers (PORTING "Balance"); these are the BALANCED rows.
        # H3: spiker / AR. H1 AR: 10 dmg x 15/s, 60 (240 / 600), 87 fr reload, error 2 ->
        # 6.5 (min 0), 324 wu/s, gravity 1.0, range 40, aim 6/25 12/25, melee 55
        'balanced': {
            'damage': 12.0,              # 10 x 9/7.5
            'rounds_per_second': 12.0,   # 15 x 8/10
            'magazine': 75,              # 60 x 40/32
            'rounds_total_initial': 300,  # 240 x 120/96
            # DUAL-WIELD CARRY RULE: 600 x (160/384) x 1.5 = 375
            'rounds_total_maximum': 375,
            'reload_s': 2.8,             # 87 fr x 56/58 = 84 fr
            # the minimum's own ratio is degenerate (2 x 0.5/0.1 = 10 > the max): the
            # maximum's 6.5/3.0 on both bounds (the SMG rule): 0.5 -> 1.08, 1.25 -> 2.71
            'error_deg': (1.08, 2.71),
            'velocity': (101.25, 70.88),  # 324 x 25/80, 324 x 17.5/80
            'air_gravity': 0.2,          # H3 AR 0: no ratio -- Halo 3's own (user)
            'range': 70.0,               # 40 x 70/40
            'aim': (6.0, 20.0, 14.4, 22.5),  # 6 x 5/5, 25 x 12/15; 12 x 12/10, 25 x 18/20
            'melee': 56.6},              # 55 x cut_melee 72 / strike_melee 70
        'measured': 'h1_role_compare.py brute_spiker',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\spike_rifle\\spike_rifle',
            'provisional': 'Needler',
            'alternatives': ['Assault Rifle'],
            'direct': None,
            'peers': ['Assault Rifle', 'Needler', 'Plasma Rifle'],
            'why': "magazine 40 automatic, slow arcing projectile (25 wu/s, gravity): the needler's family",
            'lacks': 'dual wield, blade melee'}},
    # step 11: the source game's ai\generic entry (26 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\rifle\\spike_rifle\\spike_rifle'},
)
