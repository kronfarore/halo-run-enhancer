r"""Spartan Laser (Halo 3, wave A8): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=17, wave='A8', name='Spartan Laser', source='Halo 3',
    messages=(67, 68), icon=37, reticle=26, label='sl', teach_from='rl',
    sound_dir='sound\\weapons\\spartan_laser_port', weapon_dir='weapons\\spartan laser',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\support_high\\spartan_laser\\spartan_laser',
            'provisional': 'Sniper Rifle',
            'alternatives': ['Rocket Launcher', 'Sentinel Beam'],
            'direct': None,
            'peers': ['Rocket Launcher', 'Sniper Rifle', 'Flak Cannon'],
            'why': 'instant beam, one huge shot, battery (age) not magazine',
            'lacks': '2.5 s charge-up (the fuel rod charge is the H1 precedent)'}},
    # step 11: the source game's ai\generic entry (18 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\support_high\\spartan_laser\\spartan_laser'},
)
