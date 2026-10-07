r"""Covenant Carbine (Halo 3, wave A3): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=12, wave='A3', name='Covenant Carbine', source='Halo 3',
    messages=(57, 58), icon=32, reticle=21, label='cc', teach_from='ar',
    sound_dir='sound\\weapons\\covenant_carbine_port', weapon_dir='weapons\\covenant carbine',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\covenant_carbine\\covenant_carbine',
            'provisional': 'Pistol',
            'alternatives': ['Needler', 'Sniper Rifle'],
            'direct': None,
            'peers': ['Pistol', 'Sniper Rifle', 'Needler'],
            'why': 'semi-auto magazine (18), 2x zoom, instant slug: the Covenant precision rifle',
            'lacks': ''}},
    # step 11: the source game's ai\generic entry (26 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\rifle\\covenant_carbine\\covenant_carbine'},
)
