r"""DMR into Halo 2 (H2_PORT_PLAN.md wave B (Reach), #B1) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

DMR = r'objects\weapons\rifle\dmr'                 # the source's folder (HREK) AND the port's (H2EK)
BR = r'objects\weapons\rifle\battle_rifle'          # the donor (H2EK)
FX = r'effects\objects\weapons\rifle\dmr'           # the reserved effects folder
BRFX = r'effects\objects\weapons\rifle\battle_rifle'
SMG = r'objects\weapons\rifle\smg'                  # Bungie's bare-metal env shader
RL = r'objects\weapons\support_high\rocket_launcher'   # Bungie's alpha decal shader
R = 'reach:'                                         # an HREK path (reach_tags)
RM = R + DMR + r'\dmr.render_model'
H2EK = r'F:\SteamLibrary\steamapps\common\H2EK'
NEW_HUD = r'ui\hud\bitmaps\new_hud'

PORT = {
    'order': 6,
    'wave': 'B1',
    'name': 'DMR',
    'source': 'Halo Reach',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\rifle\\dmr\\dmr',
    'reservations': {
        'message_prefix': 'dmr2',
        'glyph': 0xE143,
        'weapon_dir': 'objects\\weapons\\rifle\\dmr',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\dmr',
        'fp_graph': 'weapons\\rifle\\fp_dmr\\fp_dmr',
        'hud': 'ui\\hud\\dmr',
        'hud_bitmap_prefix': 'dmr_',
        'sound_dir': 'sound\\weapons\\dmr_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\battle_rifle\\battle_rifle', 'message_prefix': 'br',
              'why': 'latch-zoom magazine instant bullet, 1 zoom level; burst -> single. Alt: sniper_rifle (sn)'},
    'yardstick': {
        # step 4a, user 2026-11-01 (balance_port.py DMR "Sniper Rifle" "Halo Reach" "Halo 2", TTK
        # scratch beside it): Reach's DMR 17.5 x 3/s, the sniper pair Reach 80 / H2 45
        'pick': 'Sniper Rifle',
        'reason': ('user 2026-11-01: the Sniper Rifle ratio, as in Halo 1 (shown beside BR via Halo 4 and the '
                   'Pistol); bullet MATERIALS the Battle Rifle\'s (group bullet_fast, Reach\'s own name); '
                   'range 40 / velocity 400 = the BR via Halo 4 chain\'s, not the sniper ratio\'s 60 / 600. Spread by '
                   'the SIBLING rule (Halo 1\'s ruling: the plain ratio inverts, 0.94 -> 0.25): 0.019-0.25. Zoom '
                   'Reach\'s 3x (Halo 1\'s ruling; the ratio gives 2.6-2.85x on one level). Legendary, body, BR materials: '
                   'Elite 16 / 5.01 s, Brute 26 / 7.23 s, Grunt 5 / 0.89 s, Jackal 7 / 1.33 s'),
        'balanced': {'damage': 9.844, 'rate': 4.5, 'fire_recovery': 0.22, 'magazine': 15, 'initial': 45, 'maximum': 75,
                     'error_deg': (0.019, 0.25), 'range': 40.0, 'velocity': 400.0, 'zoom': 3.0},
        'candidates': {
            'provisional': 'Sniper Rifle',
            'alternatives': ['Battle Rifle via Halo 4 (--hop "DMR:Halo Reach>Halo 4" --hop "Battle Rifle:Halo 4>Halo 2"; carries H4\'s scale -- the user\'s call)', 'Pistol'],
            'direct': 'none',
            'peers': ['Battle Rifle', 'Magnum', 'Sniper Rifle', 'Covenant Carbine'],
            'why': "semi-auto 15, 3x zoom, near-instant (H1 pick Sniper). The BR is H2's mid-range precision rifle but Reach has no BR",
        },
    },
    # step 1 -- h2_port_geometry.py kind 'h3' with `reach:` paths (THE REACH ROUTE, wave B's pilot):
    # Reach's ONE render model is world AND first person; its own skeleton b_gun / b_magazine / b_safety /
    # b_ophandle, b_gun at the grip (identity, x forward, z up: not tilted), 5 of its 15 marker groups;
    # 'unsc_decals_fp' the stencils; ones / tens the counter (`=?`, Bungie's BR symbols)
    'geometry': {
        'kind': 'h3',
        'world_rm': RM, 'fp_rm': RM,
        'data_dir': DMR,
        'world': 'dmr', 'fp': 'fp_dmr',
        'materials': {'dmr_metal': 'dmr_metal', 'dmr_metal_shiny': 'dmr_shiny', 'dmr_composite': 'dmr_composite',
                      'dmr_rubber': 'dmr_rubber', 'dmr_lens': 'dmr_lens', 'dmr_lens_glass': 'dmr_lens',
                      'unsc_decals_fp': 'dmr_decals', 'ones_dmr': 'dmr_ones=?', 'tens_dmr': 'dmr_tens=?'},
        'world_permutation': 'base', 'world_region': 'gun',          # the BR .model's variants
        'node_names': {'b_gun': 'frame gun', 'b_magazine': 'frame magazine', 'b_safety': 'frame safety',
                       'b_ophandle': 'frame OpHandle'},
        'markers': {'primary_trigger': 'primary_trigger', 'primary_ejection': 'primary_ejection',
                    'left_hand': 'left_hand', 'flashlight': 'flashlight', 'muzzle_flash': 'muzzle_flash'},
        'muzzle_drop': 0.0,
        'ground_point': {'rot': (0.7071068883, -1.8e-09, -7.42e-08, -0.7071067095)},   # the SMG's (the AR's)
        'render': ['dmr', r'dmr\fp_dmr'],
    },

    # step 2 -- kind 'h3' with `reach:` bitmaps (h3_hud_art.decode reads them): 1024 dxt5 + dxn -> 512
    # (Spartan Laser: true colour 1024 = a 6.8 MB tag); shaders reseeded from the BR (tex_bump_active_camo),
    # the SMG's env metal for Reach's shiny metal, the BR's lens (tex_bump_env + scope cubemap); self-illum is
    # OFF in every Reach DMR shader (H1's B1); counter digits = the BR's illum_detail + its plate
    'textures': {
        'kind': 'h3',
        'rel': DMR + r'\bitmaps',
        'shaders_dir': DMR + r'\shaders',
        'bump_gain': 1.0,
        'bitmaps': [(R + DMR + r'\bitmaps\dmr_diffuse.bitmap', 'dmr', BR + r'\bitmaps\battle_rifle', 'color', (512, 512)),
                    (R + DMR + r'\bitmaps\dmr_normal.bitmap', 'dmr_bump', BR + r'\bitmaps\battle_rifle_bump', 'bump', (512, 512)),
                    (R + r'objects\bitmaps\decals\bitmaps\unsc_decals_diffuse.bitmap', 'dmr_decals',
                     RL + r'\bitmaps\rocket_launcher_decal', 'color', (512, 512))],
        'shaders': [
            ('dmr_metal', BR + r'\shaders\battle_rifle_metal',
             {BR + r'\bitmaps\battle_rifle': DMR + r'\bitmaps\dmr',
              BR + r'\bitmaps\battle_rifle_bump': DMR + r'\bitmaps\dmr_bump',
              BR + r'\bitmaps\battle_rifle_bump_active_camo': DMR + r'\bitmaps\dmr_bump'}),
            ('dmr_composite', BR + r'\shaders\battle_rifle_plastic',
             {BR + r'\bitmaps\battle_rifle': DMR + r'\bitmaps\dmr',
              BR + r'\bitmaps\battle_rifle_bump': DMR + r'\bitmaps\dmr_bump',
              BR + r'\bitmaps\battle_rifle_bump_active_camo': DMR + r'\bitmaps\dmr_bump'}),
            ('dmr_rubber', SMG + r'\shaders\smg_rubber_grip',
             {SMG + r'\bitmaps\smg': DMR + r'\bitmaps\dmr',
              SMG + r'\bitmaps\smg_bump': DMR + r'\bitmaps\dmr_bump',
              SMG + r'\bitmaps\smg_bump_active_camo': DMR + r'\bitmaps\dmr_bump'}),
            ('dmr_shiny', SMG + r'\shaders\smg_bare_metal',
             {SMG + r'\bitmaps\smg': DMR + r'\bitmaps\dmr',
              SMG + r'\bitmaps\smg_bump': DMR + r'\bitmaps\dmr_bump',
              SMG + r'\bitmaps\smg_bump_active_camo': DMR + r'\bitmaps\dmr_bump'}),
            ('dmr_lens', BR + r'\shaders\battle_rifle_lens',
             {BR + r'\bitmaps\battle_rifle': DMR + r'\bitmaps\dmr',
              BR + r'\bitmaps\battle_rifle_bump': DMR + r'\bitmaps\dmr_bump'}),
            ('dmr_decals', RL + r'\shaders\rocket_launcher_decal',
             {RL + r'\bitmaps\rocket_launcher_decal': DMR + r'\bitmaps\dmr_decals'}),
            ('dmr_tens', BR + r'\shaders\tens', {}),
            ('dmr_ones', BR + r'\shaders\ones', {}),
        ],
        'report_rows': [(DMR + r'\bitmaps\dmr_bump', 'the port'), (BR + r'\bitmaps\battle_rifle_bump', 'Bungie BR')],
    },

    # step 3 -- h2_port_weapon.py: the BR's weapon (latch-zoom, magazine, instant bullet, one zoom,
    # two-handed; label rifle / br kept), everything a row or a look may touch cloned
    'weapon': {
        'weapon': DMR + r'\dmr.weapon',
        'clones': [(BR + r'\battle_rifle.weapon', DMR + r'\dmr.weapon'),
                   (BR + r'\battle_rifle.model', DMR + r'\dmr.model'),
                   (BR + r'\projectiles\battle_rifle_bullet.projectile', DMR + r'\projectiles\dmr_bullet.projectile'),
                   (BR + r'\damage_effects\battle_rifle_bullet.damage_effect', DMR + r'\damage_effects\dmr_bullet.damage_effect'),
                   (BR + r'\damage_effects\battle_rifle_trigger.damage_effect', DMR + r'\damage_effects\dmr_trigger.damage_effect'),
                   (BRFX + r'\fire_bullet.effect', FX + r'\dmr_fire.effect'),
                   (BRFX + r'\empty.effect', FX + r'\dmr_empty.effect'),
                   (BRFX + r'\muzzle_flash.light', FX + r'\dmr_muzzle_flash.light'),
                   (BRFX + r'\battle_rifle_bullet.contrail', FX + r'\dmr_bullet.contrail'),
                   (r'effects\materials\objects\weapons\battle_rifle.material_effects', FX + r'\dmr_bullet.material_effects'),
                   (r'ui\hud\battle_rifle.new_hud_definition', r'ui\hud\dmr.new_hud_definition')],
        'wiring': [
            (DMR + r'\dmr.weapon', 'hlmt', BR + r'\battle_rifle', DMR + r'\dmr', 'world model'),
            (DMR + r'\dmr.model', 'mode', BR + r'\battle_rifle', DMR + r'\dmr',
             'the world render model (it and the collision pool ONE path)', {'nth': 0}),
            (DMR + r'\dmr.weapon', 'mode', BR + r'\fp_battle_rifle\fp_battle_rifle', DMR + r'\fp_dmr\fp_dmr',
             'first person model, Master Chief', {'nth': 0}),
            (DMR + r'\dmr.weapon', 'mode', BR + r'\fp_battle_rifle\fp_battle_rifle', DMR + r'\fp_dmr\fp_dmr',
             'first person model, Dervish (one model)', {'nth': 0}),
            (DMR + r'\dmr.weapon', 'jmad', r'objects\characters\masterchief\fp\weapons\rifle\fp_battle_rifle\fp_battle_rifle',
             r'objects\characters\masterchief\fp\weapons\rifle\fp_dmr\fp_dmr', "Master Chief FP graph: Reach's own animations"),
            (DMR + r'\dmr.weapon', 'jmad', r'objects\characters\dervish\fp\weapons\rifle\fp_battle_rifle\fp_battle_rifle',
             r'objects\characters\dervish\fp\weapons\rifle\fp_dmr\fp_dmr', "Dervish FP graph: Reach's Elite animations"),
            (DMR + r'\dmr.weapon', 'proj', BR + r'\projectiles\battle_rifle_bullet', DMR + r'\projectiles\dmr_bullet', 'projectile'),
            (DMR + r'\projectiles\dmr_bullet.projectile', 'jpt!', BR + r'\damage_effects\battle_rifle_bullet',
             DMR + r'\damage_effects\dmr_bullet', 'impact damage'),
            (DMR + r'\dmr.weapon', 'jpt!', BR + r'\damage_effects\battle_rifle_trigger', DMR + r'\damage_effects\dmr_trigger', 'firing damage'),
            (DMR + r'\dmr.weapon', 'effe', BRFX + r'\fire_bullet', FX + r'\dmr_fire', 'firing effect'),
            (DMR + r'\dmr.weapon', 'effe', BRFX + r'\empty', FX + r'\dmr_empty', 'empty effect'),
            (DMR + r'\dmr.weapon', 'ligh', BRFX + r'\muzzle_flash', FX + r'\dmr_muzzle_flash', 'muzzle flash light'),
            (DMR + r'\projectiles\dmr_bullet.projectile', 'cont', BRFX + r'\battle_rifle_bullet', FX + r'\dmr_bullet', 'tracer contrail'),
            (DMR + r'\dmr.weapon', 'foot', r'effects\materials\objects\weapons\battle_rifle', FX + r'\dmr_bullet', 'material effects (the weapon)'),
            (DMR + r'\projectiles\dmr_bullet.projectile', 'foot', r'effects\materials\objects\weapons\battle_rifle', FX + r'\dmr_bullet', 'impact material effects'),
            (DMR + r'\dmr.weapon', 'nhdt', r'ui\hud\battle_rifle', r'ui\hud\dmr', 'its own HUD (step 7)'),
        ],
        'string_ids_done': ('weapon name', 'br'),
        'shared': [(r'objects\weapons\damage_effects\*_melee', 'shared by every Halo 2 weapon'),
                   (r'the particles inside dmr_fire', "the BR's (Reach particles do not port)"),
                   (r'objects\powerups\battle_rifle_ammo\br_ammo', "the BR's ammo pickup item (unused in campaign)")],
    },

    # step 4 -- h2_port_numbers.py: REACH's OWN values (Original); Balanced = the catalog's rows.
    # BURST TO SINGLE SHOT: the H2 sniper's shape, rate 0, one shot, paced by fire recovery alone
    # (Reach's 3/s = recovery 0.33). h3_weapon_values.py --kit reach rifle\dmr\dmr=rifle\fp_dmr\fp_dmr
    'numbers': {
        'numbers': [
            (DMR + r'\dmr.weapon', 'autoaim angle', '', 0, 0, 2.25),
            (DMR + r'\dmr.weapon', 'autoaim range', '', 0, 0, 20.0),
            (DMR + r'\dmr.weapon', 'magnetism angle', '', 0, 1, 5.0),
            (DMR + r'\dmr.weapon', 'magnetism range', '', 0, 1, 20.0),
            (DMR + r'\dmr.weapon', 'magnification range', '', 0, 0, [3.0, 3.0]),
            (DMR + r'\dmr.weapon', 'rounds loaded maximum', 'magazines', 0, 0, 15),
            (DMR + r'\dmr.weapon', 'rounds reloaded', 'magazines', 0, 0, 15),
            (DMR + r'\dmr.weapon', 'rounds total initial', 'magazines', 0, 0, 45),
            (DMR + r'\dmr.weapon', 'rounds total maximum', 'magazines', 0, 0, 75),
            (DMR + r'\dmr.weapon', 'rounds per second', 'barrels', 0, 0, [0.0, 0.0]),
            (DMR + r'\dmr.weapon', 'shots per fire', 'barrels', 0, 0, [1, 1]),
            (DMR + r'\dmr.weapon', 'fire recovery time', 'barrels', 0, 0, 0.33),
            (DMR + r'\dmr.weapon', 'rounds between tracers', 'barrels', 0, 0, 0),
            # the ERROR ramp (A1: nth 1): Reach blooms by a penalty function, decay 0.7 s; H1's B1 ramp
            (DMR + r'\dmr.weapon', 'acceleration time', 'barrels', 0, 1, 1.0),
            (DMR + r'\dmr.weapon', 'deceleration time', 'barrels', 0, 1, 0.7),
            (DMR + r'\dmr.weapon', 'error angle', 'barrels', 0, 1, [0.15, 2.0]),
            (DMR + r'\projectiles\dmr_bullet.projectile', 'initial velocity', '', 0, 0, 3000.0),
            (DMR + r'\projectiles\dmr_bullet.projectile', 'final velocity', '', 0, 0, 3000.0),
            (DMR + r'\projectiles\dmr_bullet.projectile', 'maximum range', '', 0, 0, 250.0),
            (DMR + r'\damage_effects\dmr_bullet.damage_effect', 'damage upper bound', '', 0, 0, [17.5, 17.5]),
            (DMR + r'\damage_effects\dmr_bullet.damage_effect', 'instantaneous acceleration', '', 0, 0, 0.4),
        ],
        'skipped': [('melee', 'Reach shares strike_melee, as Halo 2 does: no row'),
                    ('reload time', "the animation's 68 / 59 frames drive it (reload time 0, the BR's)")],
    },

    # step 5 -- the BR's authored hull on the port's own world skeleton
    'collision': {
        'donor': BR + r'\battle_rifle',
        'port': DMR + r'\dmr',
        'src': r'battle_rifle\collision\battle_rifle_collision.jms',
        'out': DMR + r'\collision\dmr.jms',
        'port_render_jms': DMR + r'\render\dmr.jms',
        'donor_render_jms': r'battle_rifle\render\battle_rifle_L5.jms',
        'max_growth': 1.25,
    },

    # step 9 -- h2_port_fp_anims.py kind 'reach' (module docstring): Reach's OWN FP animations for BOTH
    # species (Spartan -> masterchief, Elite -> dervish), by name, helpers dropped
    'fp_anims': {
        'kind': 'reach',
        'species': {
            'masterchief': {
                'graph': R + r'objects\characters\spartans\fp\weapons\rifle\fp_dmr\fp_dmr.model_animation_graph',
                'arms_rm': R + r'objects\characters\spartans\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_masterchief\fp_arms.jms',
                'source': r'objects\characters\masterchief\fp\weapons\rifle\fp_dmr',
                'seed': r'objects\characters\masterchief\fp\weapons\rifle\fp_battle_rifle\fp_battle_rifle'},
            'dervish': {
                'graph': R + r'objects\characters\elite\fp\weapons\rifle\fp_dmr\fp_dmr.model_animation_graph',
                'arms_rm': R + r'objects\characters\elite\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_dervish\dervish_fp_arms.jms',
                'source': r'objects\characters\dervish\fp\weapons\rifle\fp_dmr',
                'seed': r'objects\characters\dervish\fp\weapons\rifle\fp_battle_rifle\fp_battle_rifle'},
        },
        'weapon_dir': DMR + r'\fp_dmr',
        'weapon_rm': RM,
        'weapon_nodes': ['gun', 'magazine', 'ophandle', 'safety'],
        'node_names': {'b_gun': 'gun', 'b_magazine': 'magazine', 'b_ophandle': 'ophandle', 'b_safety': 'safety'},
        'drop_nodes': ('pedestal', 'aim_pitch', 'aim_yaw', 'l_humerus', 'r_humerus', 'l_radius', 'r_radius',
                       'l_handguard', 'r_handguard'),
        'aliases': {'first_person:look': ['first_person:overlays', 'first_person:pitch_and_turn']},
        # no Halo 2 slot for Reach's sprint / jump / land / fall / ready_initial (the SAW's list)
        'skip': ['first_person:look', 'first_person:acceleration_screens', 'first_person:fall', 'first_person:jump',
                 'first_person:land_hard', 'first_person:land_soft', 'first_person:ready_initial',
                 'first_person:sprint_enter', 'first_person:sprint_exit', 'first_person:sprint_loop',
                 'first_person:sprint_loop_airborne'],
        'looping': ['first_person:idle', 'first_person:posing:var1', 'first_person:posing:var2'],
        'overlay_reference': 'first_person:idle',
        'weights': {'first_person:posing:var1': 0.5, 'first_person:posing:var2': 0.5},
    },

    'firing_profile': {'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\dmr\\dmr', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}
