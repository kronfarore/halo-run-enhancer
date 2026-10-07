r"""Focus Rifle (Halo Reach, wave B7): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import reserved

PORT = reserved(
    order=25, wave='B7', name='Focus Rifle', source='Halo Reach',
    messages=(83, 84), icon=45, reticle=34, label='fo', teach_from='sr',
    sound_dir='sound\\weapons\\focus_rifle_port', weapon_dir='weapons\\focus rifle',
    yardstick={
        'pick': None, 'reason': None,          # step 4a, with the user
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\focus_rifle\\focus_rifle',
            'provisional': 'Plasma Rifle',
            'alternatives': ['Sniper Rifle', 'Plasma Pistol'],
            'direct': None,
            'peers': ['Sniper Rifle', 'Sentinel Beam'],
            'why': "continuous instant beam, heat + battery (the H1 Sentinel Beam's model, but Reach has no Sentinel Beam)",
            'lacks': ''}},
    # step 11: the source game's ai\generic entry (22 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\focus_rifle\\focus_rifle'},
)
