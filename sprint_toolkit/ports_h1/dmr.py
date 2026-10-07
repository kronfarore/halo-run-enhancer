r"""DMR (Halo Reach, wave B1): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=19, wave='B1', name='DMR', source='Halo Reach',
    messages=(71, 72), icon=39, reticle=28, label='dm', teach_from='ar',
    sound_dir='sound\\weapons\\dmr_port', weapon_dir='weapons\\dmr',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\dmr\\dmr',
            'provisional': 'Pistol',
            'alternatives': ['Sniper Rifle'],
            'direct': None,
            'peers': ['Pistol', 'Sniper Rifle'],
            'why': "semi-auto magazine 15, 3x zoom, near-instant bullet: the H1 magnum's role",
            'lacks': ''}},
    # step 11: the source game's ai\generic entry (26 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\dmr\\dmr'},
)
