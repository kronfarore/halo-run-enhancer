r"""Concussion Rifle (Halo Reach, wave B5): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=23, wave='B5', name='Concussion Rifle', source='Halo Reach',
    messages=(79, 80), icon=43, reticle=32, label='cr', teach_from='pr',
    sound_dir='sound\\weapons\\concussion_rifle_port', weapon_dir='weapons\\concussion rifle',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\concussion_rifle\\concussion_rifle',
            'provisional': 'Flak Cannon (H1 fuel rod)',
            'alternatives': ['Rocket Launcher', 'Plasma Grenade'],
            'direct': None,
            'peers': ['Flak Cannon', 'Rocket Launcher', 'Plasma Rifle'],
            'why': "magazine 6, Covenant explosive plasma projectile; Reach's fuel rod is a 5-round magazine",
            'lacks': 'knockback emphasis'}},
    # step 11: the source game's ai\generic entry (26 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\concussion_rifle\\concussion_rifle'},
)
