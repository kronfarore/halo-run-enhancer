r"""LightRifle (Halo 4, wave C4): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=29, wave='C4', name='LightRifle', source='Halo 4',
    messages=(91, 92), icon=49, reticle=38, label='lr', teach_from='ar',
    sound_dir='sound\\weapons\\light_rifle_port', weapon_dir='weapons\\light rifle',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\storm_forerunner_rifle\\storm_forerunner_rifle',
            'provisional': 'Pistol',
            'alternatives': ['Sniper Rifle', 'Assault Rifle'],
            'direct': None,
            'peers': ['Pistol', 'Sniper Rifle'],
            'why': 'magazine 36, 3x zoom, near-instant precision',
            'lacks': 'unscoped 3-burst vs scoped 1-shot mode switch'}},
    # step 11: the source game's ai\generic entry (24 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map', 'from_weapon': 'objects\\weapons\\rifle\\storm_forerunner_rifle\\storm_forerunner_rifle'},
)
