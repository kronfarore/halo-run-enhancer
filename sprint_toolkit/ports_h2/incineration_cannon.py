r"""Incineration Cannon into Halo 2 (H2_PORT_PLAN.md wave C (Halo 4), #C9) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 21,
    'wave': 'C9',
    'name': 'Incineration Cannon',
    'source': 'Halo 4',
    'status': 'reserved',
    'source_tag': 'objects\\weapons\\support_high\\storm_forerunner_incineration_launcher\\storm_forerunner_incineration_launcher',
    'reservations': {
        'message_prefix': 'ic2',
        'glyph': 0xE152,
        'weapon_dir': 'objects\\weapons\\support_high\\incineration_cannon',
        'effects_dir': 'effects\\objects\\weapons\\support_high\\incineration_cannon',
        'fp_graph': 'weapons\\support_high\\fp_incineration_cannon\\fp_incineration_cannon',
        'hud': 'ui\\hud\\incineration_cannon',
        'hud_bitmap_prefix': 'incineration_cannon_',
        'sound_dir': 'sound\\weapons\\incineration_cannon_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\support_high\\rocket_launcher\\rocket_launcher', 'message_prefix': 'rl',
              'why': 'rocket-launcher type, 1.8x zoom already, latch-rocketlauncher -> latch, magazine 2 -> 1'},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'Rocket Launcher',
            'alternatives': ['Flak Cannon'],
            'direct': 'none',
            'peers': ['Rocket Launcher', 'Flak Cannon'],
            'why': "rocket-launcher type, 1 round, latch, 1.8x zoom (= H2 RL's exactly); cluster approximated (H1 pick)",
        },
    },
    'firing_profile': {'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map', 'from_weapon': 'objects\\weapons\\support_high\\storm_forerunner_incineration_launcher\\storm_forerunner_incineration_launcher', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}
