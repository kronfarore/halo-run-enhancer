r"""Scattershot (Halo 4, wave C5): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=30, wave='C5', name='Scattershot', source='Halo 4',
    messages=(93, 94), icon=50, reticle=39, label='ss', teach_from='sg',
    sound_dir='sound\\weapons\\scattershot_port', weapon_dir='weapons\\scattershot',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\storm_spread_gun\\storm_spread_gun',
            'provisional': 'Shotgun',
            'alternatives': ['Energy Blade'],
            'direct': None,
            'peers': ['Shotgun', 'Energy Blade', 'Flamethrower'],
            'why': 'magazine 5, 6 projectiles per shot, close range',
            'lacks': 'ricocheting shards'}},
    # step 11: the source game's ai\generic entry (23 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map', 'from_weapon': 'objects\\weapons\\rifle\\storm_spread_gun\\storm_spread_gun'},
)
