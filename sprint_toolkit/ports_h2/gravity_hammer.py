r"""Gravity Hammer into Halo 2 (H2_PORT_PLAN.md wave A (Halo 3), #A5) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

H3GH = r'objects\weapons\melee\gravity_hammer'        # the source's folder (H3EK) -- in H2EK Tartarus's
GH = r'objects\weapons\melee\gravity_hammer_port'     # the port's folder (H2EK, reserved)
FX = r'effects\objects\weapons\melee\gravity_hammer_port'
BEAM = r'objects\weapons\rifle\beam_rifle'            # the donor (H2EK)
BLADE = r'objects\weapons\melee\energy_blade'         # the yardstick + melee fields (H2EK)
H2EK = r'F:\SteamLibrary\steamapps\common\H2EK'

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
    # step 4a chose the TRIGGER route (energy per swing), so the donor needs a trigger + barrel with
    # battery aging: the sword's 0/0/0 has neither (a block insert). The H2 BEAM RIFLE is that shape
    # exactly: 0 magazines, one latch trigger, battery 'age generated per round' (0.0556), two-handed
    # -- its zoom and heat are plain fields (zeroed). Not the donor: the energy blade (0/0/0), the
    # plasma rifle (1 magazine, 3 barrels, one-handed). The HUD = the Energy Blade's plasma_sword
    # (battery meter only), the melee fields = the sword's (lunge dash_melee); the phase-0 proposal
    # was the blade (melee-only route)
    'donor': {'weapon': r'objects\weapons\rifle\beam_rifle\beam_rifle', 'message_prefix': 'be',
              'hud': r'ui\hud\plasma_sword', 'melee_from': r'objects\weapons\melee\energy_blade\energy_blade',
              'why': "trigger route (step 4a): 0 magazines / 1 latch trigger / battery age per round, "
                     "two-handed; HUD plasma_sword; melee fields the sword's"},
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
    # step 1 -- h2_port_geometry.py kind 'h3': Halo 3's world + FP hammer on their OWN skeleton
    # (hammer, shaft); the source folder is Bungie's melee\gravity_hammer (H3EK), the port's is
    # melee\gravity_hammer_port (H2EK: Tartarus's melee\gravity_hammer is never written).
    # Markers: the blast point `hammer_detonation` (world; `fp_hammer_detonation` in FP) is the
    # strike's origin = primary_trigger (Halo 1's Armed lesson: the AI fires from it); the hands
    # and the two effect markers (hammer_on's arcs + vent) keep their names
    'geometry': {
        'kind': 'h3',
        'world_rm': H3GH + r'\gravity_hammer.render_model',
        'fp_rm': H3GH + r'\fp_gravity_hammer\fp_gravity_hammer.render_model',
        'data_dir': GH,
        'world': 'gravity_hammer_port', 'fp': 'fp_gravity_hammer_port',
        'materials': {'hammer': 'gravity_hammer_port', 'hammer_shiny': 'gravity_hammer_port_shiny',
                      'hammer_dull': 'gravity_hammer_port_dull'},
        'markers': {'hammer_detonation': 'primary_trigger', 'fp_hammer_detonation': 'primary_trigger',
                    'left_hand': 'left_hand', 'right_hand': 'right_hand',
                    'fx_electric_arcs': 'fx_electric_arcs', 'fx_vent': 'fx_vent'},
        'ground_point': {'rot': (0.7071068883, -1.8e-09, -7.42e-08, -0.7071067095)},   # the SMG's (the AR's)
        'render': ['gravity_hammer_port', r'gravity_hammer_port\fp_gravity_hammer_port'],
    },
    # step 2 -- h2_port_textures.py kind 'h3': Halo 3's own maps; shaders reseeded from Bungie's Halo 2
    # hammer (Tartarus's `hammer`: tex_bump_env_illum -- bump, detail, base, env, a SEPARATE
    # self_illum_map; the Spike Rifle's seed too) for the lit head (hammer, hammer_shiny), the Brute
    # Shot's own (tex_bump_env) for the dull grip. Halo 3's illum map is a grey mask lit in BLUE on
    # both lit materials (self_illum_color d7 57 2e BGRA = 46 / 87 / 215, ports_h1/gravity_hammer.py);
    # Halo 2 draws a self_illum_map as it is -> TINTED here, the Spike Rifle's final recipe (PALE,
    # soft spots: Halo 3's bloom reads pale; grown blocks read 'crosses taped on')
    'textures': {
        'kind': 'h3',
        'rel': GH + r'\bitmaps',
        'shaders_dir': GH + r'\shaders',
        'bump_gain': 1.0,                      # the AR's (user: 1.6 read 'rough')
        'bitmaps': [(H3GH + r'\bitmaps\gravity_hammer.bitmap', 'gravity_hammer_port',
                     r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer', 'color', None),
                    (H3GH + r'\bitmaps\gravity_hammer_bump.bitmap', 'gravity_hammer_port_bump',
                     r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_bump', 'bump_snorm', None),
                    (H3GH + r'\bitmaps\gravity_hammer_illum.bitmap', 'gravity_hammer_port_illum',
                     r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_illum',
                     ('tint', (0.75, 0.78, 1.0), 0, 1.5), None)],
        'shaders': [
            ('gravity_hammer_port', r'objects\weapons\melee\gravity_hammer\shaders\hammer',
             {r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer': GH + r'\bitmaps\gravity_hammer_port',
              r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_bump': GH + r'\bitmaps\gravity_hammer_port_bump',
              r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_illum': GH + r'\bitmaps\gravity_hammer_port_illum'}),
            ('gravity_hammer_port_shiny', r'objects\weapons\melee\gravity_hammer\shaders\hammer',
             {r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer': GH + r'\bitmaps\gravity_hammer_port',
              r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_bump': GH + r'\bitmaps\gravity_hammer_port_bump',
              r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_illum': GH + r'\bitmaps\gravity_hammer_port_illum'}),
            # the camo bump FIRST: its path and the port's bump path are both 74 characters, so once
            # the bump is repointed h2_tagref cannot tell the two records apart (2026-10-28)
            ('gravity_hammer_port_dull', r'objects\weapons\support_low\brute_shot\shaders\brute_shot',
             {r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot_bump_active_camo': GH + r'\bitmaps\gravity_hammer_port_bump',
              r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot': GH + r'\bitmaps\gravity_hammer_port',
              r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot_bump': GH + r'\bitmaps\gravity_hammer_port_bump'}),
        ],
        'report_rows': [(GH + r'\bitmaps\gravity_hammer_port_bump', 'the port'),
                        (r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_bump', "Bungie's H2 hammer")],
    },
    'firing_profile': {'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\melee\\gravity_hammer\\gravity_hammer', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '07a_highcharity', 'dervish_level': '08b_deltacontrol'},   # parallel step 2
    'residency': {'levels': 'all', 'placements': False},
}
