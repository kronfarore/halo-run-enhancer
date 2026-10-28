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
    'status': 'in progress',
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
              'why': "melee-only, ages, 0/0/0, sword HUD; plus H2's own gravity_hammer model",
              # step 4a chose the TRIGGER route: the sword's 0/0/0 shape has no trigger / barrel to
              # carry 'age generated per round' (a block insert). Candidate shape 0/1/1 with battery
              # age per round = the BEAM RIFLE (0.0556 / round) + the sword's melee / HUD fields --
              # to be decided by the block shape before step 3 (recorded here when chosen)
              'open': 'donor block shape for the trigger route'},
    'yardstick': {
        # STEP 4a (user, 2026-10-28) -- measured on the H3EK / H2EK exports:
        #   H3 hammer: jab (melee button, 1st hit) smash_melee 80; RT slam = lunge crush_melee 150 +
        #     gravity_hammer_explosion 50..160 r 0.75->1.5 accel 3.5 stun 4.5 (an ANIMATION EFFECT,
        #     every swing); campaign external aging 0.05 a swing (20); autoaim 10/1.75, magnetism 10/6.
        #   H3 sword dash_melee 150 (strike + lunge), aim 10/2.5 10/6; H2 Energy Blade slice_melee 70,
        #     lunge dash_melee 150, aim 6/6 12/8, ages per KILL only (H2 has no per-swing aging field).
        #   Tartarus (shown, not picked): tartarus_hammer_melee 150..500 r 1.0 accel 4,
        #     tartarus_hammer_explosion 100..200 plasma r 0.4->0.8 accel 2.
        'pick': 'Energy Blade', 'ratio': 'lunge x1.0',
        'reason': "user: the sword's LUNGE ratio (150 -> 150) -- Balanced = Halo 3's own numbers: slam "
                  "crush 150 + blast 50..160 r 0.75-1.5, jab 80; aim by the sword's aim ratio "
                  "(autoaim 6 / 4.2, magnetism 12 / 8)",
        'decisions': {   # user, 2026-10-28 (step 4a)
            'energy': "TRIGGER ROUTE (Halo 1's recipe): RT fires an invisible strike that bursts into "
                      "the blast; the barrel's native 'age generated per round' 0.05 (20 swings, misses "
                      "count); the melee button = the pommel jab. Not chosen: melee-only + energy per "
                      "kill; a halo2.dll per-swing patch",
            'model': "Halo 3's hammer (world, 3P, FP) -- Bungie's H2 hammer (Tartarus's) untouched",
            '3p_class': "'melee' (the Brute graph's own hammer class); h2_graph_teach clones 'sword' as "
                        "'melee' in the masterchief and dervish graphs",
            'enhancer': "one card family 'Gravity Hammer' (enhancer session 2026-10-28): catalog weap = "
                        "the port's tag; it retargets the Halo 2 rows + derives the rest at hand-off "
                        "(tell it the slam / blast / jab jpt tags)",
        },
        'candidates': {
            'provisional': 'Energy Blade',
            'alternatives': ["H2's own Gravity Hammer (Tartarus: a boss's numbers -- show, do not default)", 'Rocket / Fuel Rod melee'],
            'direct': "H2 gravity_hammer (Tartarus) = the same weapon, carded in both -- but its damage lives in tartarus_hammer_* (an AI boss's)",
            'peers': ['Energy Blade', 'Shotgun'],
            'why': "melee-only, ages per swing; the sword is H2's only player melee weapon with Bungie's own player numbers. THE FIX IS A FULL PORT: H2's hammer tag is a Tartarus stub (no triggers, no FP model/anims, no HUD, empty message ids, no player damage) -- a NEW player tag beside it, Tartarus untouched; Bungie's H2 hammer render/collision model reusable",
        },
    },
    'firing_profile': {'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\melee\\gravity_hammer\\gravity_hammer', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '07a_highcharity', 'dervish_level': '08b_deltacontrol'},   # parallel step 2
    'residency': {'levels': 'all', 'placements': False},
}
