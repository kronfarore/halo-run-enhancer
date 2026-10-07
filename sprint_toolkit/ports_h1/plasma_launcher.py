r"""Plasma Launcher (Halo Reach, wave B6): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=24, wave='B6', name='Plasma Launcher', source='Halo Reach',
    messages=(81, 82), icon=44, reticle=33, label='pl', teach_from='rl',
    sound_dir='sound\\weapons\\plasma_launcher_port', weapon_dir='weapons\\plasma launcher',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\support_high\\plasma_launcher\\plasma_launcher',
            'provisional': 'Flak Cannon (H1 fuel rod)',
            'alternatives': ['Plasma Grenade', 'Rocket Launcher'],
            'direct': None,
            'peers': ['Rocket Launcher', 'Flak Cannon'],
            'why': 'charge-to-fire explosive plasma; heat + battery, no magazine',
            'lacks': 'multi-bolt charge (up to 4), lock-on, sticking'}},
    # step 11: the source game's ai\generic entry (24 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\support_high\\plasma_launcher\\plasma_launcher'},
)
