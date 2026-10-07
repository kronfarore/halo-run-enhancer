r"""Incineration Cannon (Halo 4, wave C9): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=34, wave='C9', name='Incineration Cannon', source='Halo 4',
    messages=(101, 102), icon=54, reticle=43, label='ic', teach_from='pc',
    sound_dir='sound\\weapons\\incineration_cannon_port', weapon_dir='weapons\\incineration cannon',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\support_high\\storm_forerunner_incineration_launcher\\storm_forerunner_incineration_launcher',
            'provisional': 'Rocket Launcher',
            'alternatives': ['Flak Cannon'],
            'direct': None,
            'peers': ['Rocket Launcher', 'Flak Cannon'],
            'why': 'a rocket-launcher-type weapon, 1-round magazine, explosive projectile, 1.8x zoom',
            'lacks': 'cluster explosion / burn'}},
    # step 11: the source game's ai\generic entry (24 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map', 'from_weapon': 'objects\\weapons\\support_high\\storm_forerunner_incineration_launcher\\storm_forerunner_incineration_launcher'},
)
