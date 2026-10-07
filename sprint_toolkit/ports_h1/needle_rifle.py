r"""Needle Rifle (Halo Reach, wave B2): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=20, wave='B2', name='Needle Rifle', source='Halo Reach',
    messages=(73, 74), icon=40, reticle=29, label='nr', teach_from='pr',
    sound_dir='sound\\weapons\\needle_rifle_port', weapon_dir='weapons\\needle rifle',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\needle_rifle\\needle_rifle',
            'provisional': 'Needler',
            'alternatives': ['Pistol', 'Sniper Rifle'],
            'direct': None,
            'peers': ['Pistol', 'Needler', 'Sniper Rifle'],
            'why': 'magazine, semi-auto, 2x zoom, fast needle that supercombines like the needler',
            'lacks': ''}},
    # step 11: the source game's ai\generic entry (26 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\needle_rifle\\needle_rifle'},
)
