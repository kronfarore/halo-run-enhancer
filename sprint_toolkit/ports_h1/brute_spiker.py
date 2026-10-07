r"""Spike Rifle (Halo 3, wave A5): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=14, wave='A5', name='Spike Rifle', source='Halo 3',
    messages=(61, 62), icon=34, reticle=23, label='sk', teach_from='hp',
    sound_dir='sound\\weapons\\spiker_port', weapon_dir='weapons\\spiker',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\spike_rifle\\spike_rifle',
            'provisional': 'Needler',
            'alternatives': ['Assault Rifle'],
            'direct': None,
            'peers': ['Assault Rifle', 'Needler', 'Plasma Rifle'],
            'why': "magazine 40 automatic, slow arcing projectile (25 wu/s, gravity): the needler's family",
            'lacks': 'dual wield, blade melee'}},
    # step 11: the source game's ai\generic entry (26 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\rifle\\spike_rifle\\spike_rifle'},
)
