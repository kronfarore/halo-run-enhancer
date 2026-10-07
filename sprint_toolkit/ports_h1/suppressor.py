r"""Suppressor (Halo 4, wave C2): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=27, wave='C2', name='Suppressor', source='Halo 4',
    messages=(87, 88), icon=47, reticle=36, label='su', teach_from='ar',
    sound_dir='sound\\weapons\\suppressor_port', weapon_dir='weapons\\suppressor',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\storm_forerunner_smg\\storm_forerunner_smg',
            'provisional': 'Assault Rifle',
            'alternatives': ['Needler', 'Sentinel Beam (H4 storm_sentinel_beam, AI-only)'],
            'direct': None,
            'peers': ['Assault Rifle', 'Plasma Rifle', 'Needler'],
            'why': 'magazine 48 full-auto, decelerating hardlight projectile (60 -> 15 wu/s)',
            'lacks': ''}},
    # step 11: the source game's ai\generic entry (18 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map', 'from_weapon': 'objects\\weapons\\rifle\\storm_forerunner_smg\\storm_forerunner_smg'},
)
