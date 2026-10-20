r"""Grenade Launcher into Halo 2 (H2_PORT_PLAN.md wave B (Reach), #B4) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 9,
    'wave': 'B4',
    'name': 'Grenade Launcher',
    'source': 'Halo Reach',
    'status': 'reserved',
    'source_tag': 'objects\\weapons\\rifle\\grenade_launcher\\grenade_launcher',
    'reservations': {
        'message_prefix': 'gl2',
        'glyph': 0xE146,
        'weapon_dir': 'objects\\weapons\\rifle\\grenade_launcher',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\grenade_launcher',
        'fp_graph': 'weapons\\rifle\\fp_grenade_launcher\\fp_grenade_launcher',
        'hud': 'ui\\hud\\grenade_launcher',
        'hud_bitmap_prefix': 'grenade_launcher_',
        'sound_dir': 'sound\\weapons\\grenade_launcher_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\support_low\\brute_shot\\brute_shot', 'message_prefix': 'bs',
              'why': 'latch magazine arcing explosive grenade, ballistic AI aim; magazine 4 -> 1'},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'Frag Grenade + Rocket Launcher for the holes',
            'alternatives': ['Rocket Launcher', 'Flak Cannon'],
            'direct': 'none',
            'peers': ['Brute Shot', 'Rocket Launcher', 'Flak Cannon'],
            'why': "1-round latch-tether, bouncing grenade (H1 pick). H2 has no tether trigger (approximate as in H1); the Brute Shot is H2's own grenade launcher -- a peer only (no Reach Brute Shot)",
        },
    },
    'firing_profile': {'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\grenade_launcher\\grenade_launcher', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}
