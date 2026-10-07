r"""Beam Rifle (Halo 3, wave A4): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=13, wave='A4', name='Beam Rifle', source='Halo 3',
    messages=(59, 60), icon=33, reticle=22, label='bm', teach_from='sr',
    sound_dir='sound\\weapons\\beam_rifle_port', weapon_dir='weapons\\beam rifle',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\beam_rifle\\beam_rifle',
            'provisional': 'Sniper Rifle',
            'alternatives': ['Plasma Pistol', 'Sentinel Beam'],
            'direct': None,
            'peers': ['Sniper Rifle'],
            'why': 'instant beam, two zoom levels, heat-limited fire + battery',
            'lacks': ''}},
    # step 11: the source game's ai\generic entry (17 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\rifle\\beam_rifle\\beam_rifle'},
)
