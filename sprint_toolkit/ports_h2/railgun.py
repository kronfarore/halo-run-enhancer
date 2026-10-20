r"""Railgun into Halo 2 (H2_PORT_PLAN.md wave C (Halo 4), #C7) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 19,
    'wave': 'C7',
    'name': 'Railgun',
    'source': 'Halo 4',
    'status': 'reserved',
    'source_tag': 'objects\\weapons\\rifle\\storm_rail_gun\\storm_rail_gun',
    'reservations': {
        'message_prefix': 'rg2',
        'glyph': 0xE150,
        'weapon_dir': 'objects\\weapons\\support_high\\railgun',
        'effects_dir': 'effects\\objects\\weapons\\support_high\\railgun',
        'fp_graph': 'weapons\\support_high\\fp_railgun\\fp_railgun',
        'hud': 'ui\\hud\\railgun',
        'hud_bitmap_prefix': 'railgun_',
        'sound_dir': 'sound\\weapons\\railgun_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\support_high\\rocket_launcher\\rocket_launcher', 'message_prefix': 'rl',
              'why': '1-2 round magazine power weapon, 2 barrels, two-handed; trigger -> latch-autofire / Charge 0.75 s (UNTESTED with a magazine)'},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'Rocket Launcher',
            'alternatives': ['Flak Cannon', 'Sniper Rifle', 'Beam Rifle'],
            'direct': 'none',
            'peers': ['Rocket Launcher', 'Sniper Rifle', 'Flak Cannon', 'Spartan Laser (port)'],
            'why': '1-round magazine, charge-with-magazine 0.75 s, slug + blast (H1 pick). H2 has NO charge-with-magazine: Latch-Autofire / Charge on a magazine weapon is UNTESTED',
        },
    },
    'firing_profile': {'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map', 'from_weapon': 'objects\\weapons\\rifle\\storm_rail_gun\\storm_rail_gun_pve', 'note': 'the campaign tag storm_rail_gun_pve has the entry (C7, Halo 1)', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}
