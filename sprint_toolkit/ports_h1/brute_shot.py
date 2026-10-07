r"""Brute Shot (Halo 3, wave A7): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=16, wave='A7', name='Brute Shot', source='Halo 3',
    messages=(65, 66), icon=36, reticle=25, label='bs', teach_from='rl',
    sound_dir='sound\\weapons\\brute_shot_port', weapon_dir='weapons\\brute shot',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\support_low\\brute_shot\\brute_shot',
            'provisional': 'Rocket Launcher',
            'alternatives': ['Flak Cannon (H1 fuel rod)', 'Frag Grenade'],
            'direct': None,
            'peers': ['Rocket Launcher', 'Flak Cannon'],
            'why': 'magazine 6, explosive grenade projectile (16 -> 7 wu/s)',
            'lacks': 'bounce-detonate arc, blade melee'}},
    # step 11: the source game's ai\generic entry (21 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\support_low\\brute_shot\\brute_shot'},
)
