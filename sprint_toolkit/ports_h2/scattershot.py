r"""Scattershot into Halo 2 (H2_PORT_PLAN.md wave C (Halo 4), #C5) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 17,
    'wave': 'C5',
    'name': 'Scattershot',
    'source': 'Halo 4',
    'status': 'reserved',
    'source_tag': 'objects\\weapons\\rifle\\storm_spread_gun\\storm_spread_gun',
    'reservations': {
        'message_prefix': 'ss2',
        'glyph': 0xE14E,
        'weapon_dir': 'objects\\weapons\\rifle\\scattershot',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\scattershot',
        'fp_graph': 'weapons\\rifle\\fp_scattershot\\fp_scattershot',
        'hud': 'ui\\hud\\scattershot',
        'hud_bitmap_prefix': 'scattershot_',
        'sound_dir': 'sound\\weapons\\scattershot_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\shotgun\\shotgun', 'message_prefix': 'sg',
              'why': 'latch magazine pellets; 10 -> 6 projectiles, 12 -> 5 rounds'},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'Shotgun',
            'alternatives': ['Energy Blade'],
            'direct': 'none',
            'peers': ['Shotgun', 'Energy Blade', 'Mauler (port)'],
            'why': 'magazine 5 latch, 6 shards, close range, ricochet (H1 pick)',
        },
    },
    'firing_profile': {'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map', 'from_weapon': 'objects\\weapons\\rifle\\storm_spread_gun\\storm_spread_gun', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}
