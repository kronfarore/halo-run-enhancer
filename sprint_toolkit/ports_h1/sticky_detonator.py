r"""Sticky Detonator (Halo 4, wave C8): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=33, wave='C8', name='Sticky Detonator', source='Halo 4',
    messages=(99, 100), icon=53, reticle=42, label='sd', teach_from='hp',
    sound_dir='sound\\weapons\\sticky_detonator_port', weapon_dir='weapons\\sticky detonator',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\pistol\\storm_sticky_detonator\\storm_sticky_detonator',
            'provisional': 'Rocket Launcher',
            'alternatives': ['Plasma Grenade', 'Flak Cannon'],
            'direct': None,
            'peers': ['Rocket Launcher', 'Flak Cannon'],
            'why': '1-round magazine, arcing sticky explosive (gravity 0.25)',
            'lacks': 'remote detonation, sticking (approximate: long fuse / second-shot trigger)'}},
    # step 11: NO source entry found
    firing_profile={'mode': 'same_game', 'donor_weapon': None, 'why': 'no ai\\generic entry for objects\\weapons\\pistol\\storm_sticky_detonator\\storm_sticky_detonator found in Halo 4 maps -- pick a Halo 1 stand-in'},
)
