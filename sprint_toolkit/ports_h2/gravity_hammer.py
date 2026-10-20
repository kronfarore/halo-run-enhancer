r"""Gravity Hammer into Halo 2 (H2_PORT_PLAN.md wave A (Halo 3), #A5) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

PORT = {
    'order': 5,
    'wave': 'A5',
    'name': 'Gravity Hammer',
    'source': 'Halo 3',
    'status': 'reserved',
    'source_tag': 'objects\\weapons\\melee\\gravity_hammer\\gravity_hammer',
    'reservations': {
        'message_prefix': 'gh2',
        'glyph': 0xE142,
        'weapon_dir': 'objects\\weapons\\melee\\gravity_hammer_port',
        'effects_dir': 'effects\\objects\\weapons\\melee\\gravity_hammer_port',
        'fp_graph': 'weapons\\melee\\fp_gravity_hammer_port\\fp_gravity_hammer_port',
        'hud': 'ui\\hud\\gravity_hammer',
        'hud_bitmap_prefix': 'gravity_hammer_',
        'sound_dir': 'sound\\weapons\\gravity_hammer_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\melee\\energy_blade\\energy_blade', 'message_prefix': 'ps',
              'why': "melee-only, ages, 0/0/0, sword HUD; plus H2's own gravity_hammer model"},
    'yardstick': {
        'pick': None, 'reason': None,          # step 4a, WITH the user
        'candidates': {
            'provisional': 'Energy Blade',
            'alternatives': ["H2's own Gravity Hammer (Tartarus: a boss's numbers -- show, do not default)", 'Rocket / Fuel Rod melee'],
            'direct': "H2 gravity_hammer (Tartarus) = the same weapon, carded in both -- but its damage lives in tartarus_hammer_* (an AI boss's)",
            'peers': ['Energy Blade', 'Shotgun'],
            'why': "melee-only, ages per swing; the sword is H2's only player melee weapon with Bungie's own player numbers. THE FIX IS A FULL PORT: H2's hammer tag is a Tartarus stub (no triggers, no FP model/anims, no HUD, empty message ids, no player damage) -- a NEW player tag beside it, Tartarus untouched; Bungie's H2 hammer render/collision model reusable",
        },
    },
    'firing_profile': {'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\melee\\gravity_hammer\\gravity_hammer', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}
