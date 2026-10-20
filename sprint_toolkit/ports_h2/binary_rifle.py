r"""Binary Rifle into Halo 2 (H2_PORT_PLAN.md wave C (Halo 4), #C6) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 18,
    'wave': 'C6',
    'name': 'Binary Rifle',
    'source': 'Halo 4',
    'status': 'reserved',
    'source_tag': 'objects\\weapons\\rifle\\storm_forerunner_sniper_rifle\\storm_forerunner_sniper_rifle',
    'reservations': {
        'message_prefix': 'bi2',
        'glyph': 0xE14F,
        'weapon_dir': 'objects\\weapons\\rifle\\binary_rifle',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\binary_rifle',
        'fp_graph': 'weapons\\rifle\\fp_binary_rifle\\fp_binary_rifle',
        'hud': 'ui\\hud\\binary_rifle',
        'hud_bitmap_prefix': 'binary_rifle_',
        'sound_dir': 'sound\\weapons\\binary_rifle_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\sniper_rifle\\sniper_rifle', 'message_prefix': 'sn',
              'why': 'latch magazine instant, 2 zooms; magazine 4 -> 2'},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'Sniper Rifle',
            'alternatives': ['Beam Rifle (H4 storm_beam_rifle; a heat weapon -- magazine ratios degenerate)', 'Rocket Launcher'],
            'direct': 'none',
            'peers': ['Sniper Rifle', 'Beam Rifle', 'Spartan Laser (port)'],
            'why': 'magazine 2, two zooms 4-10, one-hit kill (H1 pick)',
        },
    },
    'firing_profile': {'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map', 'from_weapon': 'objects\\weapons\\rifle\\storm_forerunner_sniper_rifle\\storm_forerunner_sniper_rifle', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}
