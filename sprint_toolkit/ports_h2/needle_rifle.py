r"""Needle Rifle into Halo 2 (H2_PORT_PLAN.md wave B (Reach), #B2) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 7,
    'wave': 'B2',
    'name': 'Needle Rifle',
    'source': 'Halo Reach',
    'status': 'reserved',
    'source_tag': 'objects\\weapons\\rifle\\needle_rifle\\needle_rifle',
    'reservations': {
        'message_prefix': 'nr2',
        'glyph': 0xE144,
        'weapon_dir': 'objects\\weapons\\rifle\\needle_rifle',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\needle_rifle',
        'fp_graph': 'weapons\\rifle\\fp_needle_rifle\\fp_needle_rifle',
        'hud': 'ui\\hud\\needle_rifle',
        'hud_bitmap_prefix': 'needle_rifle_',
        'sound_dir': 'sound\\weapons\\needle_rifle_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\covenant_carbine\\covenant_carbine', 'message_prefix': 'cc',
              'why': 'Covenant semi-auto magazine, latch-zoom 2x, 1/1/2; projectile from the needler (supercombine)'},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'Needler',
            'alternatives': ['Pistol', 'Sniper Rifle'],
            'direct': 'none',
            'peers': ['Covenant Carbine', 'Needler', 'Battle Rifle'],
            'why': '21-round semi-auto 4/s, 2x zoom, supercombining needle (H1 pick). The Carbine is its H2 role twin but Reach has none and there is no bridge',
        },
    },
    'firing_profile': {'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\needle_rifle\\needle_rifle', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}
