r"""Plasma Repeater (Halo Reach, wave B3): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=21, wave='B3', name='Plasma Repeater', source='Halo Reach',
    messages=(75, 76), icon=41, reticle=30, label='rp', teach_from='pr',
    sound_dir='sound\\weapons\\plasma_repeater_port', weapon_dir='weapons\\plasma repeater',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\plasma_repeater\\plasma_repeater',
            'provisional': 'Plasma Rifle',
            'alternatives': ['Plasma Pistol'],
            'direct': 'Elite (carries the Plasma Rifle in both games: same as the provisional)',
            'peers': ['Plasma Rifle', 'Assault Rifle', 'Needler'],
            'why': 'heat-based automatic plasma bolt, rate falls with heat',
            'lacks': 'manual vent'}},
    # step 11: the source game's ai\generic entry (23 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\plasma_repeater\\plasma_repeater'},
)
