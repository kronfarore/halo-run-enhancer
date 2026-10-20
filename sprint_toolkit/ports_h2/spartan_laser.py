r"""Spartan Laser into Halo 2 (H2_PORT_PLAN.md wave A (Halo 3), #A2) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 2,
    'wave': 'A2',
    'name': 'Spartan Laser',
    'source': 'Halo 3',
    'status': 'reserved',
    'source_tag': 'objects\\weapons\\support_high\\spartan_laser\\spartan_laser',
    'reservations': {
        'message_prefix': 'spl2',
        'glyph': 0xE13F,
        'weapon_dir': 'objects\\weapons\\support_high\\spartan_laser',
        'effects_dir': 'effects\\objects\\weapons\\support_high\\spartan_laser',
        'fp_graph': 'weapons\\support_high\\fp_spartan_laser\\fp_spartan_laser',
        'hud': 'ui\\hud\\spartan_laser',
        'hud_bitmap_prefix': 'spartan_laser_',
        'sound_dir': 'sound\\weapons\\spartan_laser_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\beam_rifle\\beam_rifle', 'message_prefix': 'be',
              'why': 'battery + heat, instant beam, two-handed, 0 mags; trigger latch -> Charge 2.5 s, zoom levels 2 -> 1. Alt: plasma_pistol (pp: 2 barrels + charge, one-hand)'},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'Rocket Launcher',
            'alternatives': ['Beam Rifle', 'Sniper Rifle', 'Sentinel Beam'],
            'direct': 'none',
            'peers': ['Rocket Launcher', 'Beam Rifle', 'Sniper Rifle', 'Flak Cannon'],
            'why': "spew-charge 2.5 s, battery, heat 1.0/shot, 2.5x zoom, instant beam (H1 pick RL: laser damage = explosion_large). H2 has no spew-charge: Charge (the scarab main gun's, 2.8 s) is the closest -- UNTESTED on a player weapon",
        },
    },
    'firing_profile': {'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\support_high\\spartan_laser\\spartan_laser', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}
