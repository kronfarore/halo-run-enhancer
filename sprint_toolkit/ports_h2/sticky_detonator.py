r"""Sticky Detonator into Halo 2 (H2_PORT_PLAN.md wave C (Halo 4), #C8) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 20,
    'wave': 'C8',
    'name': 'Sticky Detonator',
    'source': 'Halo 4',
    'status': 'reserved',
    'source_tag': r'objects\weapons\pistol\storm_sticky_detonator\storm_sticky_detonator_pve',
    'reservations': {
        'message_prefix': 'sd2',
        'glyph': 0xE151,
        'weapon_dir': 'objects\\weapons\\pistol\\sticky_detonator',
        'effects_dir': 'effects\\objects\\weapons\\pistol\\sticky_detonator',
        'fp_graph': 'weapons\\pistol\\fp_sticky_detonator\\fp_sticky_detonator',
        'hud': 'ui\\hud\\sticky_detonator',
        'hud_bitmap_prefix': 'sticky_detonator_',
        'sound_dir': 'sound\\weapons\\sticky_detonator_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\support_low\\brute_shot\\brute_shot', 'message_prefix': 'bs',
              'why': "latch magazine arcing grenade; magazine -> 1 (one-handed in H4: the port's own graphs)"},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'Plasma Grenade + Rocket Launcher for the holes',
            'alternatives': ['Rocket Launcher', 'Flak Cannon'],
            'direct': 'none',
            'peers': ['Brute Shot', 'Rocket Launcher', 'Flak Cannon'],
            'why': '1-round double-latch-tether, arcing sticky explosive; no tether in H2 (stick + fuse, as H1)',
        },
    },
    'firing_profile': {'note': 'NO ai\\generic entry in any Halo 4 map (re-checked 2026-10-20): pick a Halo 2 stand-in', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}
