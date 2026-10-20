r"""Plasma Launcher into Halo 2 (H2_PORT_PLAN.md wave B (Reach), #B6) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 11,
    'wave': 'B6',
    'name': 'Plasma Launcher',
    'source': 'Halo Reach',
    'status': 'reserved',
    'source_tag': 'objects\\weapons\\support_high\\plasma_launcher\\plasma_launcher',
    'reservations': {
        'message_prefix': 'pl2',
        'glyph': 0xE148,
        'weapon_dir': 'objects\\weapons\\support_high\\plasma_launcher',
        'effects_dir': 'effects\\objects\\weapons\\support_high\\plasma_launcher',
        'fp_graph': 'weapons\\support_high\\fp_plasma_launcher\\fp_plasma_launcher',
        'hud': 'ui\\hud\\plasma_launcher',
        'hud_bitmap_prefix': 'plasma_launcher_',
        'sound_dir': 'sound\\weapons\\plasma_launcher_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\pistol\\plasma_pistol\\plasma_pistol', 'message_prefix': 'pp',
              'why': 'charge trigger + 2 barrels + heat/battery HUD, 0 mags; clear dual wield, charge 0.6 -> 3.0. Alt: flak_cannon (fc)'},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'Plasma Grenade + Rocket Launcher for the holes',
            'alternatives': ['Flak Cannon', 'Rocket Launcher'],
            'direct': 'none',
            'peers': ['Rocket Launcher', 'Flak Cannon', 'Brute Shot'],
            'why': 'charge 3 s, heat 0.4/round + battery, 3x zoom, sticky explosive bolts (H1 pick); H2 has Charge / Latch-Autofire, no lock-on (guidance approximates)',
        },
    },
    'firing_profile': {'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\support_high\\plasma_launcher\\plasma_launcher', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}
