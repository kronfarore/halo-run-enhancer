r"""Storm Rifle (Halo 4, wave C1): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=26, wave='C1', name='Storm Rifle', source='Halo 4',
    messages=(85, 86), icon=46, reticle=35, label='st', teach_from='pr',
    sound_dir='sound\\weapons\\storm_rifle_port', weapon_dir='weapons\\storm rifle',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\storm_assault_carbine\\storm_assault_carbine',
            'provisional': 'Plasma Pistol',
            'alternatives': ['Assault Rifle', 'Needler'],
            'direct': None,
            'peers': ['Plasma Rifle', 'Assault Rifle', 'Needler'],
            'why': 'heat-based automatic plasma bolt; Halo 4 has no Plasma Rifle, so the Plasma Pistol is the only heat plasma weapon in both',
            'lacks': ''}},
    # step 11: the source game's ai\generic entry (23 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map', 'from_weapon': 'objects\\weapons\\rifle\\storm_assault_carbine\\storm_assault_carbine'},
)
