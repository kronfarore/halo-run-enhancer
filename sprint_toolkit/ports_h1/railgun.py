r"""Railgun (Halo 4, wave C7): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=32, wave='C7', name='Railgun', source='Halo 4',
    messages=(97, 98), icon=52, reticle=41, label='rg', teach_from='rl',
    sound_dir='sound\\weapons\\railgun_port', weapon_dir='weapons\\railgun',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\storm_rail_gun\\storm_rail_gun',
            'provisional': 'Rocket Launcher',
            'alternatives': ['Flak Cannon (H1 fuel rod: charge-to-fire)', 'Sniper Rifle'],
            'direct': None,
            'peers': ['Rocket Launcher', 'Sniper Rifle', 'Flak Cannon'],
            'why': '1-round magazine, 0.75 s charge, slug with impact + explosion damage',
            'lacks': 'charge with a magazine (the H1 fuel rod is the precedent)'}},
    # step 11: NO source entry found
    firing_profile={'mode': 'same_game', 'donor_weapon': None, 'why': 'no ai\\generic entry for objects\\weapons\\rifle\\storm_rail_gun\\storm_rail_gun found in Halo 4 maps -- pick a Halo 1 stand-in'},
)
