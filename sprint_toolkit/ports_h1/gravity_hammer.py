r"""Gravity Hammer (Halo 3, wave A9): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=18, wave='A9', name='Gravity Hammer', source='Halo 3',
    messages=(69, 70), icon=38, reticle=27, label='gh', teach_from='f',
    sound_dir='sound\\weapons\\gravity_hammer_port', weapon_dir='weapons\\gravity hammer',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\melee\\gravity_hammer\\gravity_hammer',
            'provisional': 'Energy Blade',
            'alternatives': ['any H1 weapon melee'],
            'direct': None,
            'peers': ['Energy Blade', 'Shotgun'],
            'why': "pure melee, energy aging per swing like the sword (whose H1 numbers are Bungie's own)",
            'lacks': 'area knockback blast'}},
    # step 11: the source game's ai\generic entry (8 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\melee\\gravity_hammer\\gravity_hammer'},
)
