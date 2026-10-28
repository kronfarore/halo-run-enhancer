r"""Mauler into Halo 2 (H2_PORT_PLAN.md wave A (Halo 3), #A4) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 4,
    'wave': 'A4',
    'name': 'Mauler',
    'source': 'Halo 3',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\pistol\\excavator\\excavator',
    'reservations': {
        'message_prefix': 'mau2',
        'glyph': 0xE141,
        'weapon_dir': 'objects\\weapons\\pistol\\excavator',
        'effects_dir': 'effects\\objects\\weapons\\pistol\\excavator',
        'fp_graph': 'weapons\\pistol\\fp_excavator\\fp_excavator',
        'hud': 'ui\\hud\\brute_mauler',
        'hud_bitmap_prefix': 'brute_mauler_',
        'sound_dir': 'sound\\weapons\\brute_mauler_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\shotgun\\shotgun', 'message_prefix': 'sg',
              'why': 'latch magazine pellets 1/1/1; set can-be-dual-wielded. Alt: magnum (mp)'},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'Shotgun',
            'alternatives': ['Pistol'],
            'direct': 'none',
            'peers': ['Shotgun', 'Energy Blade', 'Magnum'],
            'why': 'magazine 5 latch, pellets, dual-wieldable one-hand shotgun (H1 pick)',
        },
    },
    'firing_profile': {'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\pistol\\excavator\\excavator', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '05b_deltatowers', 'dervish_level': '08a_deltacliffs'},   # parallel step 2
    'residency': {'levels': 'all', 'placements': False},
}
