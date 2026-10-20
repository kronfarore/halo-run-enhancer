r"""Plasma Repeater into Halo 2 (H2_PORT_PLAN.md wave B (Reach), #B3) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 8,
    'wave': 'B3',
    'name': 'Plasma Repeater',
    'source': 'Halo Reach',
    'status': 'reserved',
    'source_tag': 'objects\\weapons\\rifle\\plasma_repeater\\plasma_repeater',
    'reservations': {
        'message_prefix': 'rp2',
        'glyph': 0xE145,
        'weapon_dir': 'objects\\weapons\\rifle\\plasma_repeater',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\plasma_repeater',
        'fp_graph': 'weapons\\rifle\\fp_plasma_repeater\\fp_plasma_repeater',
        'hud': 'ui\\hud\\plasma_repeater',
        'hud_bitmap_prefix': 'plasma_repeater_',
        'sound_dir': 'sound\\weapons\\plasma_repeater_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\plasma_rifle\\plasma_rifle', 'message_prefix': 'pr',
              'why': 'spew heat automatic + battery + rate ramp; clear dual wield. Alt: brute_plasma_rifle (bpr)'},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'Plasma Rifle',
            'alternatives': ['Plasma Pistol'],
            'direct': 'Elite: carries the Plasma Rifle in both (= the provisional)',
            'peers': ['Plasma Rifle', 'Brute Plasma Rifle', 'SMG', 'Needler'],
            'why': "heat automatic plasma + battery, rate 15 -> 3 with heat (H1 pick). H2's trigger RAMPS over held time (6 -> 9) like Halo 1: H1's approximation B carries over",
        },
    },
    'firing_profile': {'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\plasma_repeater\\plasma_repeater', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}
