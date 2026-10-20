r"""Concussion Rifle into Halo 2 (H2_PORT_PLAN.md wave B (Reach), #B5) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 10,
    'wave': 'B5',
    'name': 'Concussion Rifle',
    'source': 'Halo Reach',
    'status': 'reserved',
    'source_tag': 'objects\\weapons\\rifle\\concussion_rifle\\concussion_rifle',
    'reservations': {
        'message_prefix': 'cr2',
        'glyph': 0xE147,
        'weapon_dir': 'objects\\weapons\\rifle\\concussion_rifle',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\concussion_rifle',
        'fp_graph': 'weapons\\rifle\\fp_concussion_rifle\\fp_concussion_rifle',
        'hud': 'ui\\hud\\concussion_rifle',
        'hud_bitmap_prefix': 'concussion_rifle_',
        'sound_dir': 'sound\\weapons\\concussion_rifle_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\support_high\\flak_cannon\\flak_cannon', 'message_prefix': 'fc',
              'why': 'latch magazine (5 -> 6) explosive plasma bolt, two-handed Covenant HUD; zoom 1 -> 0'},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'Flak Cannon (fuel rod)',
            'alternatives': ['Rocket Launcher', 'Plasma Grenade'],
            'direct': 'none',
            'peers': ['Flak Cannon', 'Rocket Launcher', 'Brute Shot'],
            'why': "magazine 6 latch explosive plasma; Reach's AND H2's fuel rods are both 5-round magazines (cleaner than H1's charge fuel rod)",
        },
    },
    'firing_profile': {'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\concussion_rifle\\concussion_rifle', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}
