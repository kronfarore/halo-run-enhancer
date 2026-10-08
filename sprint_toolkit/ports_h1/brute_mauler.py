r"""Mauler (Halo 3, wave A6): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=15, wave='A6', name='Mauler', source='Halo 3',
    messages=(63, 64), icon=35, reticle=24, label='ml', teach_from='sg',
    sound_dir='sound\\weapons\\mauler_port', weapon_dir='weapons\\mauler',
    yardstick={
        # step 4a (user, 2026-10-08): h3_weapon_values.py (excavator / shotgun / magnum /
        # energy_blade) + the projectiles' `conical spread` block + h1_role_compare.py
        # brute_mauler. Halo 3's mauler is the shotgun's own projectile with other numbers:
        # 15 pellets (3 x 5 grid, 7.5 deg) both, bullet_slow both, falloff both -- every value
        # has a shotgun counterpart; the pistol has no pellets, no cone and no falloff
        'pick': 'Shotgun',
        'reason': "user, step 4a 2026-10-08: the same projectile family in Halo 3 (15-pellet "
                  "7.5 deg cone, bullet_slow, distance falloff) -- H1 value = H1 shotgun x H3 "
                  "mauler / H3 shotgun; keeps Halo 3's relation (140 vs 150 dps -> 301 vs 322). "
                  "The reload stays WHOLE-MAGAZINE (the ratio of a full reload lands on 55 fr)",
        # DEFAULT = Halo 3's own numbers (PORTING "Balance"); these are the BALANCED rows.
        # H3: mauler / shotgun. H1 shotgun: 15 x 18..25 (lower 8 over 1.5 -> 3 wu), 1/s,
        # 12 (24 / 60) 0.4 s a shell, error 10, 140 -> 100 wu/s, range 40, aim 6/15 12/15,
        # melee 55. Default (H3 own): 15 x 7 (lower 1.5 over 2.5 -> 5), 0.75 s, 5 (10 / 25),
        # 55 fr, 7.5 deg, 480 wu/s, range 8, aim 8/7 16/7, cut_melee 72
        'balanced': {
            'pellets': 15,                 # 15 x 15/15
            'damage': (12.6, 17.5),        # 18..25 x 7/10 (mean 15.05)
            'damage_lower': 4.0,           # 8 x 1.5/3
            'damage_range': (1.875, 3.75),  # 1.5 x 2.5/2, 3 x 5/4
            'fire_recovery_s': 0.75,       # 1.0 s x 0.75/1.0 (rounds_per_second 1.333)
            'magazine': 10,                # 12 x 5/6
            'rounds_total_initial': 13,    # 24 x 10/18
            # DUAL-WIELD CARRY RULE: 60 x (25/36) x 1.5 = 62.5
            'rounds_total_maximum': 62,
            # WHOLE magazine: H1 shotgun empty -> full (12 shells x 12 fr = 144) x H3 mauler
            # 55 fr / H3 shotgun empty -> full (14 + 6 x 16 + 34 = 144) = 55 fr
            'reload_s': 55 / 30.0,
            'error_deg': 10.0,             # 10 x 7.5/7.5 (Halo 1: a random cone, no grid)
            'velocity': (140.0, 100.0),    # x 480/480
            'range': 53.3,                 # 40 x 8/6
            'aim': (6.0, 19.1, 12.0, 19.1),  # 6 x 8/8, 15 x 7/5.5; 12 x 16/16, 15 x 7/5.5
            'melee': 56.6},                # 55 x cut_melee 72 / strike_melee 70
        'measured': 'h1_role_compare.py brute_mauler',
        'candidates': {
            'source_weapon': 'objects\\weapons\\pistol\\excavator\\excavator',
            'provisional': 'Shotgun',
            'alternatives': ['Pistol'],
            'direct': None,
            'peers': ['Shotgun', 'Energy Blade', 'Flamethrower'],
            'why': '5-round magazine, instant pellets, 8 wu range: a one-hand shotgun',
            'lacks': 'dual wield'}},
    # step 11: the source game's ai\generic entry (14 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\pistol\\excavator\\excavator'},
)
