r"""Grenade Launcher (Halo Reach, wave B4): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=22, wave='B4', name='Grenade Launcher', source='Halo Reach',
    messages=(77, 78), icon=42, reticle=31, label='gl', teach_from='sg',
    sound_dir='sound\\weapons\\grenade_launcher_port', weapon_dir='weapons\\grenade launcher',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\grenade_launcher\\grenade_launcher',
            'provisional': 'Rocket Launcher',
            'alternatives': ['Frag Grenade', 'Flak Cannon'],
            'direct': None,
            'peers': ['Rocket Launcher', 'Flak Cannon'],
            'why': '1-round magazine, bouncing explosive grenade (gravity 0.7)',
            'lacks': 'hold-to-detonate, EMP'}},
    # step 11: the source game's ai\generic entry (19 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\grenade_launcher\\grenade_launcher'},
)
