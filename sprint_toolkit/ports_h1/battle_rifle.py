r"""Battle Rifle (Halo 3, wave A2): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=11, wave='A2', name='Battle Rifle', source='Halo 3',
    messages=(55, 56), icon=31, reticle=20, label='br', teach_from='ar',
    sound_dir='sound\\weapons\\battle_rifle_port', weapon_dir='weapons\\battle rifle',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\battle_rifle\\battle_rifle',
            'provisional': 'Pistol',
            'alternatives': ['Assault Rifle', 'Sniper Rifle'],
            'direct': None,
            'peers': ['Pistol', 'Assault Rifle', 'Sniper Rifle'],
            'why': "magazine, 2x scope, instant bullet: the H1 magnum's precision mid-range role",
            'lacks': '3-round burst'}},
    # step 11: the source game's ai\generic entry (26 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\rifle\\battle_rifle\\battle_rifle'},
)
