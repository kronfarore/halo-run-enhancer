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
        'pick': None, 'reason': None,          # step 4a, with the user
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
