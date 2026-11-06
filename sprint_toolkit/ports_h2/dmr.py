r"""DMR into Halo 2 (H2_PORT_PLAN.md wave B (Reach), #B1) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

DMR = r'objects\weapons\rifle\dmr'                 # the source's folder (HREK) AND the port's (H2EK)
BR = r'objects\weapons\rifle\battle_rifle'          # the donor (H2EK)
FX = r'effects\objects\weapons\rifle\dmr'           # the reserved effects folder
BRFX = r'effects\objects\weapons\rifle\battle_rifle'
SN = r'objects\weapons\rifle\sniper_rifle'          # the yardstick (H2EK)
SMG = r'objects\weapons\rifle\smg'                  # Bungie's bare-metal env shader
RL = r'objects\weapons\support_high\rocket_launcher'   # Bungie's alpha decal shader
R = 'reach:'                                         # an HREK path (reach_tags)
RM = R + DMR + r'\dmr.render_model'
H2EK = r'F:\SteamLibrary\steamapps\common\H2EK'
NEW_HUD = r'ui\hud\bitmaps\new_hud'
DMR_JMS = H2EK + r'\data' + '\\' + DMR + r'\render\dmr.jms'       # the mesh the HUD art is drawn from
RS = r'data\sound\weapons'                           # source folders in MCC's haloreach sfx.fsb (.info)
import os as _os

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
                      'dmr_rubber': 'dmr_rubber', 'dmr_lens': 'dmr_lens', 'dmr_lens_glass': 'dmr_glass',
                      'unsc_decals_fp': 'dmr_decals', 'ones_dmr': 'dmr_ones=?', 'tens_dmr': 'dmr_tens=?'},
        'world_permutation': 'base', 'world_region': 'gun',          # the BR .model's variants
        'node_names': {'b_gun': 'frame gun', 'b_magazine': 'frame magazine', 'b_safety': 'frame safety',
                       'b_ophandle': 'frame OpHandle'},
        'markers': {'primary_trigger': 'primary_trigger', 'primary_ejection': 'primary_ejection',
                    'left_hand': 'left_hand', 'flashlight': 'flashlight', 'muzzle_flash': 'muzzle_flash'},
        'muzzle_drop': 0.0,
        'ground_point': {'rot': (0.7071068883, -1.8e-09, -7.42e-08, -0.7071067095)},   # the SMG's (the AR's)
        'render': ['dmr', r'dmr\fp_dmr'],
        # boot 1 ('the glass on the scope is missing, the display looks wrong'): tool's render weld (1/512 of the
        # model) dropped 16,286 -> 5,717 triangles; h2_tool_fineweld keeps 16,290. The glass its own material
        'fine_weld': True,
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
            # Reach's dmr_lens_glass (env glass over grey 50%, green-tinted in game) = the BR's opaque lens look
            # (scope cubemap, green / blue tints) on a flat grey: the glass UVs point nowhere on the DMR diffuse
            ('dmr_glass', BR + r'\shaders\battle_rifle_lens',
             {BR + r'\bitmaps\battle_rifle': r'shaders\default_bitmaps\bitmaps\gray_50_percent',
              BR + r'\bitmaps\battle_rifle_bump': r'shaders\default_bitmaps\bitmaps\default_vector'}),
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
            (DMR + r'\damage_effects\dmr_bullet.damage_effect', 'damage lower bound', '', 0, 0, 17.5),
            (DMR + r'\damage_effects\dmr_bullet.damage_effect', 'damage upper bound', '', 0, 0, [17.5, 17.5]),
            (DMR + r'\damage_effects\dmr_bullet.damage_effect', 'instantaneous acceleration', '', 0, 0, 0.4),
            # step 4b (port_field_audit --port h2:dmr, before boot 1). List 4: Reach's DMR and sniper are
            # both plain latch, as the H2 sniper: the BR's latch-zoom goes. List 2 by the sniper ratio:
            # ai scariness, illumination recovery, camo damage. The ammo item's `rounds` stays the BR's 72:
            # h2_tagfield cannot reach the nested magazines block, and the item is unused in campaign
            (DMR + r'\dmr.weapon', 'behavior', 'new triggers', 0, 0, 1),
            (DMR + r'\dmr.weapon', 'ai scariness', '', 0, 0, 2.0),
            (DMR + r'\dmr.weapon', 'illumination recovery time', 'barrels', 0, 0, 0.06),
            (DMR + r'\damage_effects\dmr_bullet.damage_effect', 'active camouflage damage', '', 0, 0, 0.225),
            # first-person placement: the BR's 0.02 minus Halo 1's 0.025 forward for Reach's arms (a Halo 1
            # observation, to check on boot 1)
            # boot 1 ('start by going down', the user's Reach screenshot beside ours): the counter 235 px too high
            # and 20 px left at 1080p; at its depth (0.12 wu, f ~1500 px) = 0.019 down, 0.002 right
            # boot 2: 'move 2 more units down' (1 unit = 0.01, the SAW's reading)
            # boot 3: 'back up 1 unit'
            (DMR + r'\dmr.weapon', 'first person weapon offset', '', 0, 0, [-0.005, -0.002, -0.033]),
            # the scope picture (h2_port_scope `art`) centred on the crosshair: its registration
            # point stays the widget's 0, 0 (a zero field), so the offset is half the 1024 picture
            (r'ui\hud\dmr.new_hud_definition', 'fullscreen offset', 'bitmap widgets', 9, 0, [-512, -512]),
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

    # step 7 -- the HUD: the BR's clone (single, two-handed, zoom gates). 15 Reach pills in one row (one
    # magazine in Original and Balanced, so no `sequences`); plate + backpack + glyph from the port's own mesh
    'meter': {
        'donor_meter': NEW_HUD + r'\meters\battle_rifle_meter',
        'rel': NEW_HUD + r'\meters',
        'name': 'dmr_meter',
        'donor_hud': r'ui\hud\battle_rifle',
        'port_hud': r'ui\hud\dmr',
        'weapon': DMR + r'\dmr.weapon',
        'rounds': 15, 'rows': 1,
        'canvas': (197, 34), 'tick_w': 10,
        'tick_art': {'h3': (R + r'ui\chud\bitmaps\ballistic_meters', 0), 'h': 30},
        'backpack': NEW_HUD + r'\backpack_weapons',
        'backpack_port': NEW_HUD + r'\dmr_backpack',
        'backpack_size': (62, 30),
        'model_3p': DMR_JMS,
        'preview': 'dmr_meter_preview.png',
    },
    'hud_plate': {
        'rel': NEW_HUD + r'\backgrounds',
        'donor': NEW_HUD + r'\backgrounds\battle_rifle_bkd',
        'other': NEW_HUD + r'\backgrounds\smg_bkd',
        'name': 'dmr_bkd',
        'hud': r'ui\hud\dmr',
        'model_3p': DMR_JMS,
        'fallback_box': (105, 191, 5, 34),
        'stretch': 1.4,
    },
    # Reach's circle (hud_reticles #14, chud scale 0.9). target_ink = Reach's on-screen size: 1 chud
    # unit = 1080 / 711 px at 1080p (the 1152 x 640 canvas = the 90% safe area, Halo 1's B1), and
    # 1.117 screen px a bitmap px (the AR)
    'reticle': {
        'rel': NEW_HUD + r'\crosshairs',
        'donor': NEW_HUD + r'\crosshairs\hud_reticles',
        'donor_sequence': 17,
        'name': 'dmr_reticle',
        'hud': r'ui\hud\dmr',
        'footprint': 1.0,
        # boot 1: 'missing the inner smaller section' -- Reach's error_reticule_small (#36, chud scale 1.0)
        # inside the circle (#14 at 0.9): a layer at 1 / 0.9
        'h3_art': {'sheet': R + r'ui\chud\bitmaps\hud_reticles', 'sequence': 14, 'yardstick': 14, 'target_ink': 40,
                   'layers': [((R + r'ui\chud\bitmaps\hud_reticles', 36), 1.0 / 0.9)]},
        'preview': 'dmr_reticle_preview.png',
    },
    # Reach's scope: h2_port_scope `art`. The ring on `scope_mask` (Reach's own quarter ring, mirrored
    # both ways; Halo 2's widget has the same shape), everything else (rulers, gauge, the '10's, Halo 1's
    # static arc + slider at the DMR's one zoom) as one picture on `distance_meter`, centred by its
    # offset in the numbers; the BR's other scope widgets blank. Span 711 = Reach's canvas / 0.9
    'scope': {
        'rel': NEW_HUD + r'\scope_masks',
        'donor': NEW_HUD + r'\scope_masks\battle_rifle_scope_mask',
        'name': 'dmr_scope_blank',
        'hud': r'ui\hud\dmr.new_hud_definition',
        'widgets': ('scope_mask', 'left_crosshair', 'right_crosshair', 'bottom_crosshair', 'top_crosshair',
                    '2x', 'distance_meter'),
        'size': (8, 8),
        'art': {'chud': R + r'ui\chud\dmr',
                'ring': ('scope', 'scope_mask', 'dmr_scope_mask'), 'ring_size': 512,
                # boot 1: an oval (~440 x 800 px; the stretched 512 quarter, the Needle Rifle's finding) and
                # the gauges ~1.2x Reach's -> `ring_quarter` + the span from the user's Reach screenshot: lens
                # opening 595 x 573 px at 1080p = the ring's 489 chud units at 1.19 px a unit -> span 900
                'span': 900.0, 'aspect': 16.0 / 9.0,
                'ring_quarter': (860, 484),
                'picture': ('distance_meter', 'dmr_scope_art'), 'picture_size': 1024,
                'px_per_unit': 1080.0 / 900.0 / 1.117,
                # boot 3: 'the zoom ladder is too close to the outer circle, the pointer touches it' -- arc and
                # its labels 12 units left; boot 4: 'the pointer alone back to the outer circle' -> at its boot-2 spot
                'per_widget': {'scope_distance_meter': {'scale': (1.0, 1.0), 'offset': (-12.0, 0.0)},
                               # boot 2: 'incorrectly orientated' -- Reach TURNS the slider about the crosshair
                               # along the arc; at the same spot (141, -186): radius 233.4 on the right, turned
                               # 52.8 deg counter-clockwise
                               'distance_slider': {'origin': (0.0, 0.0), 'offset': (233.4, 0.0), 'rotate': 52.84}}},
    },

    # step 8 -- the pickup icon at the reserved U+E143, untinted (the H2 ICON RULE); br_* -> dmr2_*
    'glyph': {
        'box': (160, 62),
        'model_3p': DMR_JMS,
        'tif': 'dmr_h2_glyph.tif',
        'colour': (255, 255, 255),
        # boot 1: 'lines within the texture' -- Reach's dense mesh creased into specks: pieces under 14 px dropped
        'style': {'line': (255, 255, 255), 'body': (153, 153, 153), 'min_line': 14},
    },
    'messages': {
        'donor_prefix': 'br', 'donor_icon': '&battle_rifle',
        'donor_name': 'Battle Rifle', 'port_name': 'DMR',
        'weapon': DMR + r'\dmr.weapon',
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
                # the SMG for its 17 sound slots: Reach cues seven sounds, the BR seed has 4 (the SAW's reason)
                'seed': r'objects\characters\masterchief\fp\weapons\rifle\fp_smg\fp_smg'},
            'dervish': {
                'graph': R + r'objects\characters\elite\fp\weapons\rifle\fp_dmr\fp_dmr.model_animation_graph',
                'arms_rm': R + r'objects\characters\elite\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_dervish\dervish_fp_arms.jms',
                'source': r'objects\characters\dervish\fp\weapons\rifle\fp_dmr',
                'seed': r'objects\characters\dervish\fp\weapons\rifle\fp_smg\fp_smg'},
        },
        'weapon_dir': DMR + r'\fp_dmr',
        'weapon_rm': RM,
        'weapon_nodes': ['gun', 'magazine', 'ophandle', 'safety'],
        'node_names': {'b_gun': 'gun', 'b_magazine': 'magazine', 'b_ophandle': 'ophandle', 'b_safety': 'safety'},
        'drop_nodes': ('pedestal', 'aim_pitch', 'aim_yaw', 'l_humerus', 'r_humerus', 'l_radius', 'r_radius',
                       'l_handguard', 'r_handguard'),
        'aliases': {'first_person:look': ['first_person:overlays', 'first_person:pitch_and_turn']},
        # boot 2: 'the left hand clips, idle too; the fidget; the melee with the right arm further out' (melee 2).
        # Hand edges cutting the gun a frame (scratch cut.py): idle 102 -> 24, fidget 1 102 -> 24, fidget 2 95 -> 18,
        # melee 1 129 -> 47, melee 2 108 -> 64 (y -0.3 there: 71 without), reload 38 -> 16. Reach's own arms: 4.7% of
        # their edges in idle, ours 8.5% -> 2.0%. Gun frame, wu (0.75 JMS units down). Chief only: the Arbiter unjudged
        # boot 3: 'slightly up in idle and fidget'; the LONG fidget (var2): 'the gun doesn't sit on the left hand'
        'left_arm_offset': {'masterchief': {'*': (0.0, 0.0, -0.0075),
                                            'first_person:idle': (0.0, 0.0, -0.005),
                                            'first_person:posing:var1': (0.0, 0.0, -0.005),
                                            # boot 4 (video): mid-fidget the rolled gun lies on the open left palm;
                                            # the shift fades out as the gun rolls (up 0.95 -> 0.85; frames 18-72)
                                            'first_person:posing:var2': {'offset': (0.0, 0.0, -0.0025),
                                                                         'upright': (0.85, 0.95)},
                                            'first_person:melee_strike_2': (0.0, -0.003, -0.0075)}},
        # no Halo 2 slot for Reach's sprint / jump / land / fall / ready_initial (the SAW's list)
        'skip': ['first_person:look', 'first_person:acceleration_screens', 'first_person:fall', 'first_person:jump',
                 'first_person:land_hard', 'first_person:land_soft', 'first_person:ready_initial',
                 'first_person:sprint_enter', 'first_person:sprint_exit', 'first_person:sprint_loop',
                 'first_person:sprint_loop_airborne'],
        'looping': ['first_person:idle', 'first_person:posing:var1', 'first_person:posing:var2'],
        'overlay_reference': 'first_person:idle',
        'weights': {'first_person:posing:var1': 0.5, 'first_person:posing:var2': 0.5},
        # the SMG seed's left-hand IK and dual-wield sound flags (the SAW's two fixes)
        'drop_ik': ['masterchief'],
        'clear_sound_ref_flags': True,
        'clear_verify': True,
        # Reach's graph: one sound event an animation, at frame 0
        'source_events': {'cues': {'first_person:melee_strike_1': [('dmr_melee1', 0)],
                                   'first_person:melee_strike_2': [('dmr_melee2', 0)],
                                   'first_person:posing:var1': [('dmr_pose1', 0)],
                                   'first_person:posing:var2': [('dmr_pose2', 0)],
                                   'first_person:ready': [('dmr_ready', 0)],
                                   'first_person:reload_empty': [('dmr_reload_empty', 0)],
                                   'first_person:reload_full': [('dmr_reload_full', 0)]}},
    },

    # step 10 -- h2_port_sounds.py: Reach's OWN sounds from MCC's haloreach sfx.fsb (the Halo 3 reader,
    # `bank`). Reach's firing effect plays the shot, an exterior tail and a far layer: shot + tail mixed
    # (Halo 1's B1), the far layer in the BR's fire_lod slot. One Spartan set for both species: Reach's
    # Elite FP sounds (dmr_elite_fp) are not used (graph_sounds names one sound per slot in both graphs)
    'sounds': {
        'weapon': DMR + r'\dmr.weapon',
        'fire_fx': FX + r'\dmr_fire.effect',
        'bank': 'haloreach',
        'audio': _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'out', 'h2_sounds', 'dmr'),
        'audio_key': 'DMR',
        'h3_bank': {'dmr_fire': [RS + r'\marksman_rifle\marksman_rifle_fire', RS + r'\marksman_rifle\marksman_tail_ext'],
                    'dmr_fire_lod': [RS + r'\marksman_rifle\marksman_lod_far'],
                    'dmr_dryfire': [RS + r'\battle_rifle\dryfire'],
                    'dmr_reload_empty': [RS + r'\dmr\dmr_reload_empty'],
                    'dmr_reload_full': [RS + r'\dmr\dmr_reload_full'],
                    'dmr_ready': [RS + r'\dmr\dmr_ready'],
                    'dmr_melee1': [RS + r'\dmr\dmr_melee_1'],
                    'dmr_melee2': [RS + r'\dmr\dmr_melee_2'],
                    'dmr_pose1': [RS + r'\dmr\dmr_pose_1'],
                    'dmr_pose2': [RS + r'\dmr\dmr_pose_2'],
                    'dmr_zoom_in': [RS + r'\battle_rifle\battle_rifle_zoom_in'],
                    'dmr_zoom_out': [RS + r'\battle_rifle\battle_rifle_zoom_out'],
                    'dmr_ammo': [RS + r'\battle_rifle\battle_rifle_ammo']},
        'sounds': {'dmr_fire': ('dmr_fire', 'weapon_fire'), 'dmr_fire_lod': ('dmr_fire_lod', 'weapon_fire'),
                   'dmr_dryfire': ('dmr_dryfire', 'weapon_empty'), 'dmr_reload_empty': ('dmr_reload_empty', 'weapon_reload'),
                   'dmr_reload_full': ('dmr_reload_full', 'weapon_reload'), 'dmr_ready': ('dmr_ready', 'weapon_ready'),
                   'dmr_melee1': ('dmr_melee1', 'weapon_melee'), 'dmr_melee2': ('dmr_melee2', 'weapon_melee'),
                   'dmr_pose1': ('dmr_pose1', 'weapon_animation'), 'dmr_pose2': ('dmr_pose2', 'weapon_animation'),
                   'dmr_zoom_in': ('dmr_zoom_in', 'weapon_ready'), 'dmr_zoom_out': ('dmr_zoom_out', 'weapon_ready'),
                   'dmr_ammo': ('dmr_ammo', 'weapon_reload')},
        'repoint_fx': [(r'sound\weapons\battle_rifle\fire_burst', 'dmr_fire'),
                       (r'sound_remastered\weapons\battle_rifle\fire_lod', 'dmr_fire_lod')],
        'repoint_weapon': [(r'sound\weapons\battle_rifle\zoom_in', 'dmr_zoom_in'),
                           (r'sound\weapons\battle_rifle\zoom_out', 'dmr_zoom_out'),
                           (r'sound\weapons\battle_rifle\battle_rifle_ammo', 'dmr_ammo')],
        'repoint_tags': [(FX + r'\dmr_empty.effect', r'sound\weapons\battle_rifle\dryfire', 'dmr_dryfire')],
        # the SMG seed's 17 references, all repointed; unused dual slots point at the ready
        'graph_sounds': (('smg_melee1', 'dmr_melee1'), ('smg_ready', 'dmr_ready'), ('smg_reload', 'dmr_reload_empty'),
                         ('smg_reload_full', 'dmr_reload_full'), ('smg_dual_ready', 'dmr_melee2'),
                         ('smg_posing_var0', 'dmr_pose1'), ('smg_posing_var1', 'dmr_pose2'),
                         ('smg_dual_reload_left', 'dmr_ready'), ('smg_dual_reload_right', 'dmr_ready'),
                         ('smg_dual_posing_0_l', 'dmr_ready'), ('smg_dual_posing_0_r', 'dmr_ready'),
                         ('smg_dual_posing_1_l', 'dmr_ready'), ('smg_dual_posing_1_r', 'dmr_ready'),
                         ('smg_dual_posing_2_l', 'dmr_ready'), ('smg_dual_posing_2_r', 'dmr_ready'),
                         ('smg_dual_posing_3_l', 'dmr_ready'), ('smg_dual_posing_3_r', 'dmr_ready')),
        'graph_sound_dir': r'sound\weapons\smg' + '\\',
        'gain': {},
        'boost': {},
        'backup': r'E:\HaloBackups\H2EK_dmr_before_sounds',
        'graph_backup': r'E:\HaloBackups\H2EK_dmr_graphs_before_sounds',
    },

    # step 11 -- `python ai_firing_profile.py --h2-port dmr`: Reach's ai\generic DMR entry (m10) name for
    # name, over the H2 BR's (the donor)
    'firing_profile': {'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\dmr\\dmr',
                       'donor_weapon': BR + r'\battle_rifle'},

    # step 4b -- port_field_audit.py --port h2:dmr: the source pair (Reach's DMR vs Reach's sniper, the
    # yardstick) against the target pair (the port vs the H2 sniper)
    'field_audit': {
        'source_kit': 'HREK',
        'source': {'weapon': (DMR + r'\dmr.weapon', r'objects\weapons\rifle\sniper_rifle\sniper_rifle.weapon'),
                   'projectile': (DMR + r'\projectiles\dmr_bullet.projectile',
                                  r'objects\weapons\rifle\sniper_rifle\projectiles\sniper_rifle_bullet.projectile'),
                   'damage_effect': (DMR + r'\projectiles\dmr_bullet.damage_effect',
                                     r'objects\weapons\rifle\sniper_rifle\projectiles\sniper_rifle_bullet.damage_effect')},
        'target': {'weapon': (DMR + r'\dmr.weapon', SN + r'\sniper_rifle.weapon'),
                   'projectile': (DMR + r'\projectiles\dmr_bullet.projectile', SN + r'\projectiles\sniper_bullet.projectile'),
                   'damage_effect': (DMR + r'\damage_effects\dmr_bullet.damage_effect', SN + r'\damage_effects\sniper_rifle_bullet.damage_effect')},
    },

    # make_port_catalog_h2.py dmr: the sniper table's rows onto the port's own tags. Step 4a's decisions
    # as overrides. Reload: 72 fr (H2 sniper) x 68 / 86 (Reach DMR / sniper) = 56.9 over the built 68
    'catalog': {
        'table': 'balance_DMR_HaloReach_to_Halo2.json',
        'weapon_tag': DMR + r'\dmr',
        'port_tags': [(('weap', SN + r'\sniper_rifle'), DMR + r'\dmr'),
                      (('proj', SN + r'\projectiles\sniper_bullet'), DMR + r'\projectiles\dmr_bullet'),
                      (('jpt!', SN + r'\damage_effects\sniper_rifle_bullet'), DMR + r'\damage_effects\dmr_bullet')],
        'shared': [('jpt!', r'objects\weapons\damage_effects\strike_melee')],
        'value_overrides': {
            'Damage Lower Bound': {'value': 9.84375, 'note': 'the upper bound: the ratio has no leg (Reach sniper lower 0)'},
            'Rounds Inventory Maximum': {'value': 60, 'note': "Reach's 60 + 15 loaded = 75 total"},
            'Error Angle': {'value': 0.019, 'note': "the SIBLING rule (Halo 1's ruling): 0.25 x 0.15 / 2; the ratio inverts"},
            'Error Angle Max': {'value': 0.25, 'note': 'the sniper ratio: 0.5 x 2 / 4'},
            'Magnification Range': {'value': 3.0, 'note': "Reach's 3x (Halo 1's ruling)"},
            'Magnification Range Max': {'value': 3.0, 'note': "Reach's 3x (Halo 1's ruling)"},
            'Maximum Range': {'value': 40.0, 'note': "user 4a 2026-11-01: the BR via Halo 4 chain's 40, not the sniper ratio's 60"},
            'Initial Velocity': {'value': 400.0, 'note': "user 4a 2026-11-01: the BR via Halo 4 chain's 400, not the sniper ratio's 600"},
            'Final Velocity': {'value': 400.0, 'note': "user 4a 2026-11-01: the BR via Halo 4 chain's 400, not the sniper ratio's 600"}},
        'fp_animations': r'objects\characters\*\fp\weapons\rifle\fp_dmr\fp_dmr',
        'reload_mult': 0.838,
        'desc': ('%s carried from %s into Halo 2 with its own model, textures, sounds, scope and its own Reach '
                 'first-person animations for both species, balanced through the Sniper Rifle.'),
    },

    'sound_keeps': {},
    # rounds = a full carry (Mauler: the profile's second number is the TOTAL, loaded included)
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant', 'rounds': (15, 75)},
    'residency': {'levels': 'all', 'placements': False},
}
