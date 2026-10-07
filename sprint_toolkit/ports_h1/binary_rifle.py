r"""Binary Rifle (Halo 4, wave C6): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=31, wave='C6', name='Binary Rifle', source='Halo 4',
    messages=(95, 96), icon=51, reticle=40, label='bi', teach_from='sr',
    sound_dir='sound\\weapons\\binary_rifle_port', weapon_dir='weapons\\binary rifle',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\storm_forerunner_sniper_rifle\\storm_forerunner_sniper_rifle',
            'provisional': 'Sniper Rifle',
            'alternatives': ['Rocket Launcher'],
            'direct': None,
            'peers': ['Sniper Rifle'],
            'why': 'magazine 2, two zoom levels, near-instant: a one-hit-kill sniper',
            'lacks': ''}},
    # step 11: the source game's ai\generic entry (25 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map', 'from_weapon': 'objects\\weapons\\rifle\\storm_forerunner_sniper_rifle\\storm_forerunner_sniper_rifle'},
)
