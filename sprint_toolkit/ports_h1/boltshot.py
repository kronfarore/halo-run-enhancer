r"""Boltshot (Halo 4, wave C3): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=28, wave='C3', name='Boltshot', source='Halo 4',
    messages=(89, 90), icon=48, reticle=37, label='bo', teach_from='pp',
    sound_dir='sound\\weapons\\boltshot_port', weapon_dir='weapons\\boltshot',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\pistol\\storm_stasis_pistol\\storm_stasis_pistol',
            'provisional': 'Pistol (bolt) + Shotgun (charged blast)',
            'alternatives': ['Plasma Pistol'],
            'direct': None,
            'peers': ['Pistol', 'Plasma Pistol', 'Shotgun'],
            'why': 'magazine 10 semi-auto bolt; a 0.6 s charge fires a 5-pellet blast: a ratio per mode',
            'lacks': 'charge-to-blast mode (approximate: plasma pistol charge route)'}},
    # step 11: the source game's ai\generic entry (25 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map', 'from_weapon': 'objects\\weapons\\pistol\\storm_stasis_pistol\\storm_stasis_pistol'},
)
