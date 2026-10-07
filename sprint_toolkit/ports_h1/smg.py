r"""SMG (Halo 3, wave A1): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=10, wave='A1', name='SMG', source='Halo 3',
    messages=(53, 54), icon=30, reticle=19, label='sm', teach_from='ar',
    sound_dir='sound\\weapons\\smg_port', weapon_dir='weapons\\smg',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\smg\\smg',
            'provisional': 'Assault Rifle',
            'alternatives': ['Pistol', 'Plasma Rifle'],
            'direct': None,
            'peers': ['Assault Rifle', 'Plasma Rifle', 'Needler'],
            'why': 'magazine full-auto bullet, a non-instant projectile in H3 like the H3 AR',
            'lacks': 'dual wield'}},
    # step 11: the source game's ai\generic entry (24 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\rifle\\smg\\smg'},
)
