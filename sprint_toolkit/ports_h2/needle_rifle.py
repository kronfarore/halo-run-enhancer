r"""Needle Rifle into Halo 2 (H2_PORT_PLAN.md wave B (Reach), #B2) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

NR = r'objects\weapons\rifle\needle_rifle'           # the source's folder (HREK) AND the port's (H2EK)
CC = r'objects\weapons\rifle\covenant_carbine'       # the donor (H2EK)
ND = r'objects\weapons\pistol\needler'               # the yardstick: its needle projectile + damage
DM = NR + r'\damage_effects'
PR = NR + r'\projectiles\needle_rifle_shard.projectile'
FX = r'effects\objects\weapons\rifle\needle_rifle'   # the reserved effects folder
NFX = r'effects\objects\weapons\pistol\needler'
XP = r'effects\impact\explosion_small\needler'
MAT = r'effects\materials\objects\weapons'
WP = NR + r'\needle_rifle.weapon'
TRAIL = FX + r'\needle_rifle_shard.contrail'
R = 'reach:'                                        # an HREK path (reach_tags)
RM = R + NR + r'\needle_rifle.render_model'
H2EK = r'F:\SteamLibrary\steamapps\common\H2EK'
NEW_HUD = r'ui\hud\bitmaps\new_hud'
NR_JMS = H2EK + r'\data' + '\\' + NR + r'\render\needle_rifle.jms'   # the mesh the HUD art is drawn from
NR_GLYPHS = R + r'ui\chud\bitmaps\scopes\nr_glyphs'
# widget_simple_flash_red's normal_color (the HUD blue: Chief 117, 186, 255 / Elite 237, 166, 255 by hud_elite),
# BGR bytes each. Boot 1: scope_masks' meter_empty_color is NOT what its black texels draw (they stayed black)
NORMAL = '00200000%s000000000000000000%s00'
RS = r'data\sound\weapons'                           # source folders in MCC's haloreach sfx.fsb (.info)
import os as _os
HOLO = r'objects\weapons\support_high\plasma_launcher\bitmaps\plasma_launcher_holo.bitmap'
CARBINE_MAPS = {CC + r'\bitmaps\covenant_carbine': NR + r'\bitmaps\needle_rifle',
                CC + r'\bitmaps\covenant_carbine_bump': NR + r'\bitmaps\needle_rifle_bump',
                CC + r'\bitmaps\covenant_carbine_bump_active_camo': NR + r'\bitmaps\needle_rifle_bump'}
# Reach's weapon nodes -> Halo 2's (b_l_needle1-6 / b_r_needle1-6 = Bungie's needle_01-12)
NODES = dict([('b_gun', 'gun'), ('b_scope', 'scope'), ('b_shell', 'shell')]
             + [('b_%s_needle%d' % (s, i), 'needle_%02d' % (k * 6 + i)) for k, s in enumerate('lr') for i in range(1, 7)])
NODES_JMS = dict((k, 'frame ' + v) for k, v in NODES.items())

PORT = {
    'order': 7,
    'wave': 'B2',
    'name': 'Needle Rifle',
    'source': 'Halo Reach',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\rifle\\needle_rifle\\needle_rifle',
    'reservations': {
        'message_prefix': 'nr2',
        'glyph': 0xE144,
        'weapon_dir': 'objects\\weapons\\rifle\\needle_rifle',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\needle_rifle',
        'fp_graph': 'weapons\\rifle\\fp_needle_rifle\\fp_needle_rifle',
        'hud': 'ui\\hud\\needle_rifle',
        'hud_bitmap_prefix': 'needle_rifle_',
        'sound_dir': 'sound\\weapons\\needle_rifle_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\covenant_carbine\\covenant_carbine', 'message_prefix': 'cc',
              'why': 'Covenant semi-auto magazine, latch-zoom 2x, 1/1/2; projectile from the needler (supercombine)'},
    'yardstick': {
        # step 4a, user 2026-11-01: reports/h2_needle_rifle_4a.md; balance_Needle_Rifle_HaloReach_to_Halo2.json
        # (balance_port.py "Needle Rifle" "Needler" "Halo Reach" "Halo 2")
        'pick': 'Needler',
        'reason': ("user 2026-11-01: the Needler for every needle-shaped value; Reach has no Carbine and the chain "
                   "through Halo 3 breaks on the needle rows, so the Carbine (the role twin) answers ACCURACY only: "
                   "the Needler's cone means nothing on a homing shot. Balanced: needle 3 on impact (Halo 2's real "
                   "1 + 2; the tool's 2 reads the detonation alone), 4/s + recovery 0.25, 26 / 78 / 105, reload "
                   "Reach's 82 fr (the ratio's 119 is nearly double the Carbine), error 0.3-1.0 min 0, 2x, velocity "
                   "818, range 231 / air 40, autoaim 1.97 / 19.2, magnetism 2.81 / 19.2, count 3 (Reach's; the "
                   "ratio's 3.5 is no count), timer 1.5-2.1 s (stock x 6/2 shot gaps: the third needle must "
                   "land inside it), minimum velocity 3, attached 400 + area 50 (the Needler's), radius 0.2-0.5, "
                   "melee Halo 2's strike_melee. Legendary: 3 needles = any minor at 0.50 s; needles alone "
                   "Elite 67 / 21.4 s (Carbine 2.57 s)"),
        'supercombine': ("no dll patch: Halo 2's projectile carries `super det. projectile count` (needler 7) and its "
                         "own super detonation tags; the needler is the only stock user, so boot 1 proves a 3"),
        'candidates': {
            'provisional': 'Needler',
            'alternatives': ['Pistol', 'Sniper Rifle'],
            'direct': 'none',
            'peers': ['Covenant Carbine', 'Needler', 'Battle Rifle'],
            'why': '21-round semi-auto 4/s, 2x zoom, supercombining needle (H1 pick). The Carbine is its H2 role twin but Reach has none and there is no bridge',
        },
    },
    # step 1 -- h2_port_geometry.py kind 'h3' with `reach:` paths (the DMR's route): Reach's ONE render
    # model is world AND first person. 15 weapon nodes: b_gun, b_scope, b_shell under it, the 12 stowed needles
    # (Bungie's own needle_01.. names: Reach's `ammunition_needles` = Halo 2's `first_person:ammunition`).
    # The halogram reload shimmer has no Halo 2 shader: dropped (Halo 1's call)
    'geometry': {
        'kind': 'h3',
        'world_rm': RM, 'fp_rm': RM,
        'data_dir': NR,
        'world': 'needle_rifle', 'fp': 'fp_needle_rifle',
        'materials': {'needle_rifle_metal': 'needle_rifle_metal', 'needle_rifle_shell': 'needle_rifle_shell',
                      'needle_rifle_glass': 'needle_rifle_glass', 'needle_holes': 'needle_rifle_holes',
                      'needler_crystal_solid': 'needle_rifle_crystal', 'needle_rifle_display': 'needle_rifle_display',
                      'needle_rifle_illum_indicator': 'needle_rifle_indicator', 'needle_rifle_reload_effect': None},
        'world_permutation': 'base', 'world_region': 'gun',          # the Carbine's render model's names
        'node_names': NODES_JMS,
        'markers': {'primary_trigger': 'primary_trigger', 'primary_ejection': 'primary_ejection',
                    'left_hand': 'left_hand', 'left_hand_elite': 'left_hand_elite', 'flashlight': 'flashlight'},
        'muzzle_drop': 0.0,
        'ground_point': {'rot': (0.7071068883, -1.8e-09, -7.42e-08, -0.7071067095)},   # the SMG's (the AR's)
        'render': ['needle_rifle', r'needle_rifle\fp_needle_rifle'],
        # the DMR's boot 1 (2f302b6): tool's 1/512-of-the-model weld dropped small triangles (6,811 -> 5,741)
        'fine_weld': True,
    },

    # step 2 -- kind 'h3' with `reach:` bitmaps: 1024 -> 512 (the DMR's). Shaders reseeded from the Carbine (its
    # carapace-shell env on the metal, gun metal on the shell). Halo 2 has no bloom and draws a self_illum_map as
    # it is, so a lit shader's colour goes into the map: Reach's colour x its intensity, clamped (crystal 160 / 33
    # / 248 x 3, holes 174 / 27 / 255 x 2). The screens are Bungie's additive plasma_illum (the AR's holo): the
    # red ring icons and the blue frames of plasma_launcher_holo, Halo 1's approved colours
    'textures': {
        'kind': 'h3',
        'rel': NR + r'\bitmaps',
        'shaders_dir': NR + r'\shaders',
        'bump_gain': 1.0,
        'bitmaps': [(R + NR + r'\bitmaps\needle_rifle_diffuse.bitmap', 'needle_rifle', CC + r'\bitmaps\covenant_carbine', 'color', (512, 512)),
                    (R + NR + r'\bitmaps\needle_rifle_normal.bitmap', 'needle_rifle_bump', CC + r'\bitmaps\covenant_carbine_bump', 'bump', (512, 512)),
                    (R + ND + r'\bitmaps\needler_crystal_illum.bitmap', 'needle_rifle_crystal', ND + r'\bitmaps\needler_needles_3p',
                     ('tint', (1.0, 0.39, 1.0), 0), None),
                    (R + r'objects\vehicles\covenant\phantom\bitmaps\phantom_illum.bitmap', 'needle_rifle_holes', ND + r'\bitmaps\needler_needles_3p',
                     ('tint', (1.0, 0.21, 1.0), 0), None),
                    (R + HOLO, 'needle_rifle_display', r'objects\weapons\rifle\shotgun\bitmaps\illum_sights',
                     ('tint', (1.0, 0.0, 6 / 255.0), 0), None),
                    (R + HOLO, 'needle_rifle_indicator', r'objects\weapons\rifle\shotgun\bitmaps\illum_sights',
                     ('tint', (0.25 * 22 / 105.0, 0.25 * 37 / 105.0, 0.25), 0), None)],
        'shaders': [
            ('needle_rifle_metal', CC + r'\shaders\carbine_shiny', CARBINE_MAPS),
            ('needle_rifle_glass', CC + r'\shaders\carbine_shiny', CARBINE_MAPS),
            ('needle_rifle_shell', CC + r'\shaders\carbine_dull', CARBINE_MAPS),
            ('needle_rifle_crystal', ND + r'\shaders\needler_luminous_3p',
             {ND + r'\bitmaps\needler_needles_3p': NR + r'\bitmaps\needle_rifle_crystal'}),
            ('needle_rifle_holes', ND + r'\shaders\needler_luminous_3p',
             {ND + r'\bitmaps\needler_needles_3p': NR + r'\bitmaps\needle_rifle_holes'}),
            ('needle_rifle_display', r'objects\weapons\fixed\plasma_cannon\shaders\plasma_illum',
             {r'objects\weapons\fixed\plasma_cannon\bitmaps\plasma_cannon': NR + r'\bitmaps\needle_rifle_display'}),
            ('needle_rifle_indicator', r'objects\weapons\fixed\plasma_cannon\shaders\plasma_illum',
             {r'objects\weapons\fixed\plasma_cannon\bitmaps\plasma_cannon': NR + r'\bitmaps\needle_rifle_indicator'}),
        ],
        'report_rows': [(NR + r'\bitmaps\needle_rifle_bump', 'the port'), (CC + r'\bitmaps\covenant_carbine_bump', 'Bungie Carbine')],
    },

    # step 3 -- h2_port_weapon.py: the H2 COVENANT CARBINE's weapon (latch-zoom magazine, 2x, Covenant, 3P label
    # rifle / cb -- Reach's own weapon names `cb` too) with the NEEDLER's needle as the projectile: its
    # model, light volume, contrail, attach response, `has super combining explosion` and its own
    # super detonation tags. Halo 2's needle has a `detonation damage` (2) Reach's does not: own
    # zero-damage clone in both of its references (a reference cannot be emptied by h2_tagref)
    'weapon': {
        'weapon': WP,
        'clones': [(CC + r'\covenant_carbine.weapon', WP),
                   (CC + r'\covenant_carbine.model', NR + r'\needle_rifle.model'),
                   (ND + r'\projectiles\needler_shard\needler_shard.projectile', PR),
                   (ND + r'\damage_effects\needler_shard_impact.damage_effect', DM + r'\needle_rifle_shard_impact.damage_effect'),
                   (ND + r'\damage_effects\needler_shard_detonation.damage_effect', DM + r'\needle_rifle_shard_detonation.damage_effect'),
                   (ND + r'\damage_effects\needler_shard_super_detonation.damage_effect', DM + r'\needle_rifle_shard_super_detonation.damage_effect'),
                   (ND + r'\damage_effects\needler_shard_attached_super_detonation.damage_effect', DM + r'\needle_rifle_shard_attached_super_detonation.damage_effect'),
                   (CC + r'\damage_effects\carbine_trigger.damage_effect', DM + r'\needle_rifle_trigger.damage_effect'),
                   (NFX + r'\firing.effect', FX + r'\needle_rifle_fire.effect'),
                   (NFX + r'\empty.effect', FX + r'\needle_rifle_empty.effect'),
                   # the needler's empty `ready` effect: the Carbine's throws a spent clip, Reach's rifle has none
                   (NFX + r'\ready.effect', FX + r'\needle_rifle_reloading.effect'),
                   (NFX + r'\projectile.contrail', FX + r'\needle_rifle_shard.contrail'),
                   (NFX + r'\needle.light_volume', FX + r'\needle_rifle_shard.light_volume'),
                   (XP + r'\standard_detonation.effect', FX + r'\standard_detonation.effect'),
                   (XP + r'\airborne_detonation.effect', FX + r'\airborne_detonation.effect'),
                   (XP + r'\super_detonation.effect', FX + r'\super_detonation.effect'),
                   (MAT + r'\covenant_carbine.material_effects', FX + r'\needle_rifle.material_effects'),
                   (MAT + r'\needler.material_effects', FX + r'\needle_rifle_shard.material_effects'),
                   # boot 1: clones of the reticle's widget_simple_flash_red (colour from the shader, shape from the
                   # alpha) -- the scope_masks clones drew black
                   (r'ui\hud\shaders\widget_simple_flash_red.shader', r'ui\hud\needle_rifle_glyph_red.shader'),
                   (r'ui\hud\shaders\widget_simple_flash_red.shader', r'ui\hud\needle_rifle_glyph_teal.shader'),
                   (r'ui\hud\shaders\widget_simple_flash_red.shader', r'ui\hud\needle_rifle_scope_art.shader')],
        # boot 1: 'a single press fires two needles' -- the Carbine's barrel flag `don't clear fire bit after
        # recovering` (2048; Halo 2 sets it on its LATCH triggers) re-fires the spew trigger once after the recovery:
        # 3584 -> 1536, barrel 0 found by its flags + 4/s (h2_port_numbers cannot write a CDATA-printed flags field)
        'byte_edits': [(WP, '000e00000000804000008040', '000600000000804000008040', ('flags',)),
                       # step 4b's melee pyramid 20 x 10 -> Reach's 15 x 15 deg (radians; h2_port_numbers cannot
                       # write a `real euler angles 2d`: the numbers row printed FAILED until boot 1)
                       (WP, 'c2b8b23ec2b8323e', '920a863e920a863e', ('damage pyramid angles',))],
        # the needler's smoke marker: Reach's rifle has none, its flash sits on primary_trigger
        'string_id_renames': [(FX + r'\needle_rifle_fire.effect', {'smoke': 'primary_trigger'})],
        # the three colours (the `scope` section), both species: red 220, 45, 45 and teal 60, 200, 200 Halo 1's, the
        # art a light slate 170, 180, 195 (Reach's ticks read ~160 grey over its tinted lens)
        'function_edits': [(r'ui\hud\needle_rifle_glyph_red.shader', NORMAL % ('ffba75', 'ffa6ed'), NORMAL % ('2d2ddc', '2d2ddc')),
                           (r'ui\hud\needle_rifle_glyph_teal.shader', NORMAL % ('ffba75', 'ffa6ed'), NORMAL % ('c8c83c', 'c8c83c')),
                           (r'ui\hud\needle_rifle_scope_art.shader', NORMAL % ('ffba75', 'ffa6ed'), NORMAL % ('c3b4aa', 'c3b4aa'))],
        'wiring': [
            (WP, 'hlmt', CC + r'\covenant_carbine', NR + r'\needle_rifle', 'world model'),
            (NR + r'\needle_rifle.model', 'mode', CC + r'\covenant_carbine', NR + r'\needle_rifle', 'the world render model', {'nth': 0}),
            (WP, 'mode', CC + r'\fp_covenant_carbine\fp_covenant_carbine', NR + r'\fp_needle_rifle\fp_needle_rifle',
             'first person model, Master Chief', {'nth': 0}),
            (WP, 'mode', CC + r'\fp_covenant_carbine\fp_covenant_carbine', NR + r'\fp_needle_rifle\fp_needle_rifle',
             'first person model, Dervish (one model)', {'nth': 0}),
            (WP, 'jmad', r'objects\characters\masterchief\fp\weapons\rifle\fp_covenant_carbine\fp_covenant_carbine',
             r'objects\characters\masterchief\fp\weapons\rifle\fp_needle_rifle\fp_needle_rifle', "Master Chief FP graph: Reach's own animations"),
            (WP, 'jmad', r'objects\characters\dervish\fp\weapons\rifle\fp_covenant_carbine\fp_covenant_carbine',
             r'objects\characters\dervish\fp\weapons\rifle\fp_needle_rifle\fp_needle_rifle', "Dervish FP graph: Reach's Elite animations"),
            (WP, 'proj', CC + r'\projectiles\carbine_slug\carbine_slug', NR + r'\projectiles\needle_rifle_shard',
             'the needle (both barrels)', {'every': True}),
            (WP, 'jpt!', CC + r'\damage_effects\carbine_trigger', DM + r'\needle_rifle_trigger', 'firing damage'),
            (WP, 'effe', r'effects\objects\weapons\rifle\covenant_carbine\firing', FX + r'\needle_rifle_fire',
             "firing effect (both barrels; the needler's violet burst)", {'every': True}),
            (WP, 'effe', r'effects\objects\weapons\rifle\covenant_carbine\reloading', FX + r'\needle_rifle_reloading', 'reloading effect'),
            (WP, 'effe', '', FX + r'\needle_rifle_empty', "the dry fire (the Carbine names none)",
             {'field': 'empty effect', 'record_from': ('shot count lower bound', 'firing effects', 0, 36)}),
            (WP, 'foot', MAT + r'\covenant_carbine', FX + r'\needle_rifle', 'material effects (the weapon)'),
            (PR, 'jpt!', ND + r'\damage_effects\needler_shard_impact', DM + r'\needle_rifle_shard_impact', 'impact damage'),
            (PR, 'jpt!', ND + r'\damage_effects\needler_shard_detonation', DM + r'\needle_rifle_shard_detonation',
             'detonation damage: zero, as Reach', {'nth': 0}),
            (PR, 'jpt!', ND + r'\damage_effects\needler_shard_detonation', DM + r'\needle_rifle_shard_detonation',
             'attached detonation damage: zero, as Reach', {'nth': 0}),
            (PR, 'jpt!', ND + r'\damage_effects\needler_shard_super_detonation', DM + r'\needle_rifle_shard_super_detonation', 'super detonation damage'),
            (PR, 'jpt!', ND + r'\damage_effects\needler_shard_attached_super_detonation', DM + r'\needle_rifle_shard_attached_super_detonation', 'super attached detonation damage'),
            (PR, 'effe', XP + r'\airborne_detonation', FX + r'\airborne_detonation', 'detonation effect (airborne)'),
            (PR, 'effe', XP + r'\standard_detonation', FX + r'\standard_detonation', 'detonation effect (ground)'),
            (PR, 'effe', XP + r'\super_detonation', FX + r'\super_detonation', 'super detonation'),
            (PR, 'foot', MAT + r'\needler', FX + r'\needle_rifle_shard', 'impact material effects (the needle)'),
            (PR, 'cont', NFX + r'\projectile', FX + r'\needle_rifle_shard', 'the trail'),
            (PR, 'MGS2', NFX + r'\needle', FX + r'\needle_rifle_shard', 'the light volume'),
        ],
        'shared': [(ND + r'\projectiles\needler_shard\needler_shard', "the needle's mesh, until the look step"),
                   (r'objects\weapons\damage_effects\strike_melee, smash_melee(_response)',
                    "Reach names strike_melee too: Halo 2's own, shared by every weapon")],
    },

    # step 4 -- h2_port_numbers.py: REACH's OWN values (DEFAULT; the balanced rows are the catalog's, step
    # 4a's Needler table). h3_weapon_values.py --kit reach rifle\needle_rifle\needle_rifle
    'numbers': {
        'numbers': [
            # THE LIVE BARREL. The Carbine's trigger names barrel 1 for both primary and secondary (barrel 0 is
            # idle), and every card and catalog row addresses barrel 0: the trigger is pointed at barrel 0
            (WP, 'primary barrel', 'new triggers', 0, 0, 0),
            (WP, 'secondary barrel', 'new triggers', 0, 0, 0),
            # Reach's trigger is SPEW (hold = 4/s; its DMR is latch): Halo 1's record called it latch
            (WP, 'behavior', 'new triggers', 0, 0, 0),
            (WP, 'rounds per second', 'barrels', 0, 0, [4.0, 4.0]),
            (WP, 'shots per fire', 'barrels', 0, 0, [1, 1]),
            (WP, 'fire recovery time', 'barrels', 0, 0, 0.25),
            (WP, 'soft recovery fraction', 'barrels', 0, 0, 0.2),
            (WP, 'error angle', 'barrels', 0, 1, [0.15, 2.0]),
            # Reach blooms by a firing-penalty function, decay 0.9 s: Halo 1's ramp reading (its B2)
            (WP, 'acceleration time', 'barrels', 0, 1, 1.0),
            (WP, 'deceleration time', 'barrels', 0, 1, 0.9),
            (WP, 'illumination recovery time', 'barrels', 0, 0, 0.1),
            (WP, 'rounds loaded maximum', 'magazines', 0, 0, 21),
            (WP, 'rounds reloaded', 'magazines', 0, 0, 21),
            (WP, 'rounds total initial', 'magazines', 0, 0, 63),
            (WP, 'rounds total maximum', 'magazines', 0, 0, 105),
            (WP, 'autoaim angle', '', 0, 0, 2.25),
            (WP, 'autoaim range', '', 0, 0, 25.0),
            (WP, 'magnetism angle', '', 0, 1, 5.0),
            (WP, 'magnetism range', '', 0, 1, 25.0),
            (WP, 'deviation angle', '', 0, 0, 2.25, {'anchor': ('autoaim range', 12)}),
            (WP, 'active camo ding', '', 0, 0, 0.75),
            (WP, 'AI scariness', '', 0, 0, 5.0),
            # the needle: straight, fast, unguided
            (PR, 'initial velocity', '', 0, 0, 1500.0),
            (PR, 'final velocity', '', 0, 0, 1500.0),
            (PR, 'guided angular velocity (lower)', '', 0, 0, 0.0),
            (PR, 'guided angular velocity (upper)', '', 0, 0, 0.0),
            (PR, 'maximum range', '', 0, 0, 250.0),
            (PR, 'air damage range', '', 0, 0, [0.0, 40.0]),
            (PR, 'water gravity scale', '', 0, 0, 0.2, {'anchor': ('air damage range', 8)}),
            (PR, 'minimum velocity', '', 0, 0, 9.0),
            # Reach: 0-4 s + `detonation max time if attached`. Halo 2 has no such flag; only a stuck needle
            # rests, so one timer at Reach's maximum says the same
            (PR, 'timer', '', 0, 0, [4.0, 4.0]),
            # boot 2: 3 combined on the 4th needle (one needle a press): Halo 2 detonates when MORE than the count
            # are stuck, so the field holds Reach's count - 1 (an observation on this port; boot 3 checks 2 -> 3)
            (PR, 'super det. projectile count', '', 0, 0, 2),
            # THE RESPONSES BY NAME. A Halo 2 element holds two responses (Reach has a list): default_material
            # stays ATTACH (Reach's bipeds) + bounce 0-30 at chance 1, never against units
            (PR, 'chance fraction', 'material responses', 0, 0, 1.0),
            (PR, 'between', 'material responses', 0, 0, [0.0, 30.0]),
            (PR, 'angular noise', 'material responses', 0, 0, 2.0),
            (PR, 'perpendicular friction', 'material responses', 0, 0, 0.0),
            (PR, 'chance fraction', 'material responses', 3, 0, 0.5),      # energy_shield_thick
            (PR, 'chance fraction', 'material responses', 4, 0, 0.8),      # hard_metal_solid
            (PR, 'between', 'material responses', 4, 0, [0.0, 85.0]),
            # damage: 6 on impact, a headshot (flags: below, once H2's flag rows are read)
            (DM + r'\needle_rifle_shard_impact.damage_effect', 'damage lower bound', '', 0, 0, 6.0),
            (DM + r'\needle_rifle_shard_impact.damage_effect', 'damage upper bound', '', 0, 0, [6.0, 6.0]),
            (DM + r'\needle_rifle_shard_impact.damage_effect', 'instantaneous acceleration', '', 0, 0, 0.2),
            # flags 8194, the Carbine slug's: can cause headshots + ignore seat scale (Reach's needle has both)
            (DM + r'\needle_rifle_shard_impact.damage_effect', 'flags', '', 0, 1, 8194, {'anchor': ('category', 2)}),
            (DM + r'\needle_rifle_shard_detonation.damage_effect', 'damage lower bound', '', 0, 0, 0.0),
            (DM + r'\needle_rifle_shard_detonation.damage_effect', 'damage upper bound', '', 0, 0, [0.0, 0.0]),
            (DM + r'\needle_rifle_shard_detonation.damage_effect', 'instantaneous acceleration', '', 0, 0, 0.0),
            # the area blast: 10-40 over 0.375-1.25 wu, core 0.3
            (DM + r'\needle_rifle_shard_super_detonation.damage_effect', 'radius', '', 0, 0, [0.375, 1.25]),
            (DM + r'\needle_rifle_shard_super_detonation.damage_effect', 'AOE core radius', '', 0, 0, 0.3),
            (DM + r'\needle_rifle_shard_super_detonation.damage_effect', 'damage lower bound', '', 0, 0, 10.0),
            (DM + r'\needle_rifle_shard_super_detonation.damage_effect', 'damage upper bound', '', 0, 0, [40.0, 40.0]),
            (DM + r'\needle_rifle_shard_super_detonation.damage_effect', 'instantaneous acceleration', '', 0, 0, 2.0),
            (DM + r'\needle_rifle_shard_super_detonation.damage_effect', 'shake radius', '', 0, 0, 2.0),
            # the attached blast: 35-350
            (DM + r'\needle_rifle_shard_attached_super_detonation.damage_effect', 'damage lower bound', '', 0, 0, 35.0),
            (DM + r'\needle_rifle_shard_attached_super_detonation.damage_effect', 'damage upper bound', '', 0, 0, [350.0, 350.0]),
            # the same radii (Reach's attached blast has them; the stock one none): placed from the area blast's layout
            (DM + r'\needle_rifle_shard_attached_super_detonation.damage_effect', 'radius', '', 0, 0, [0.375, 1.25],
             {'anchor': ('damage lower bound', -28)}),
            (DM + r'\needle_rifle_shard_attached_super_detonation.damage_effect', 'AOE core radius', '', 0, 0, 0.3,
             {'anchor': ('damage lower bound', -4)}),
            # step 4b: list 2 by the Needler's ratio; the forward exponent's ratio degenerates (Halo 1's B2: Reach's 8)
            # (the melee pyramid 15 x 15: a `byte_edits` row in `weapon`)
            (PR, 'targeted leading fraction', '', 0, 0, 0.0),
            (DM + r'\needle_rifle_shard_impact.damage_effect', 'active camouflage damage', '', 0, 0, 0.165),
            (DM + r'\needle_rifle_shard_impact.damage_effect', 'forward exponent', '', 0, 0, 8.0),
            # THE TRAIL. The needler's 10 points a second = one every 150 wu at 1500 wu/s: nothing in flight (Halo 1's
            # B2, boot 1) -> the sniper bullet's 300, no point speed. Reach's profile: 0.15 s, 0.03 -> 0.01 wu,
            # pink 237, 94, 237 -> violet 122, 43, 244 fading out (Halo 1's boot 4)
            (TRAIL, 'point generation rate', '', 0, 0, 300.0),
            (TRAIL, 'point velocity', '', 0, 0, [0.0, 0.0]),
            (TRAIL, 'duration', 'point states', 0, 0, [0.0, 0.0]),
            (TRAIL, 'transition duration', 'point states', 0, 0, [0.15, 0.15]),
            (TRAIL, 'width', 'point states', 0, 0, 0.03),
            (TRAIL, 'color lower bound', 'point states', 0, 0, [1.0, 0.929, 0.369, 0.929]),
            (TRAIL, 'color upper bound', 'point states', 0, 0, [1.0, 0.929, 0.369, 0.929]),
            (TRAIL, 'width', 'point states', 1, 0, 0.01, {'anchor': ('color lower bound', -4)}),
            (TRAIL, 'color lower bound', 'point states', 1, 0, [0.0, 0.478, 0.169, 0.957]),
            (TRAIL, 'color upper bound', 'point states', 1, 0, [0.0, 0.478, 0.169, 0.957]),
            # first-person placement: the DMR's -0.005, 0, -0.004 to start; boot 1: 'the rifle needs to go much
            # further down' (its scope sat ~500 px high at 1080p: ~0.035 wu at the scope's distance) -> -0.04;
            # boot 2: 'one more unit down'
            (WP, 'first person weapon offset', '', 0, 0, [-0.005, 0.0, -0.05]),
            # the scope's widgets (h2_port_scope `art`): the picture centred, a glyph's centre +-345 units (385 px)
            (r'ui\hud\needle_rifle.new_hud_definition', 'fullscreen offset', 'bitmap widgets', 7, 0, [-512, -512]),
            # boot 2 (screenshot): the glyphs' centres at -390 / +384 px, the side cutouts' at +-354 px: moved
            # 36 / 30 px in (/ 1.117 px a unit)
            (r'ui\hud\needle_rifle.new_hud_definition', 'fullscreen offset', 'bitmap widgets', 4, 0, [-352, -27]),
            (r'ui\hud\needle_rifle.new_hud_definition', 'fullscreen offset', 'bitmap widgets', 5, 0, [274, -27]),   # boot 3: 9 px left; Oracle boot: 4 px right (centre of the cutout lobes)
            # boot 3: 'the teal glyph is mirrored' -- the Carbine's right_crosshair flips its (shared) sprite
            # horizontally; the port's has its own
            (r'ui\hud\needle_rifle.new_hud_definition', 'flags', 'bitmap widgets', 5, 0, 0),
        ],
        'skipped': [
            ('reload time', "the magazine's reload time does not drive the player's reload: Reach's own animation does"),
            ('super det. time', "Reach's 0.05 s delay: no Halo 2 field, the blast is immediate"),
            ('super detonation object types', "Reach's biped only: no Halo 2 field, a vehicle combines as the stock needler does"),
        ],
    },

    # step 5 -- the Carbine's authored hull on the port's own world skeleton (the Spike Rifle's nodes_from_render)
    'collision': {
        'donor': CC + r'\covenant_carbine',
        'port': NR + r'\needle_rifle',
        'src': r'covenant_carbine\collision\collision.jms',
        'out': NR + r'\collision\needle_rifle.jms',
        'port_render_jms': NR + r'\render\needle_rifle.jms',
        'donor_render_jms': r'covenant_carbine\render\covenant_carbine_L5.jms',
        'max_growth': 1.25,
        'nodes_from_render': True,
    },

    # step 7 -- the HUD: the Carbine's clone. Reach's own pill (its chud's ballistic_meters), one per round:
    # sequence 0 Original's 21, sequence 1 Balanced's 26 (a meter is a fraction reveal: the Mauler's rule)
    'meter': {
        'donor_meter': NEW_HUD + r'\meters\carbine_meter',
        'rel': NEW_HUD + r'\meters',
        'name': 'needle_rifle_meter',
        'donor_hud': r'ui\hud\carbine',
        'port_hud': r'ui\hud\needle_rifle',
        'weapon': WP,
        'rounds': 26, 'rows': 1,
        'sequences': [{'rounds': 21, 'tick_w': 7}, {'rounds': 26}],
        'canvas': (196, 26), 'tick_w': 6,
        'tick_art': {'h3': (R + r'ui\chud\bitmaps\ballistic_meters', 0), 'h': 24},
        'backpack': NEW_HUD + r'\backpack_weapons',
        'backpack_port': NEW_HUD + r'\needle_rifle_backpack',
        'backpack_size': (62, 30),
        'model_3p': NR_JMS,
        'model_skip': ('needle_rifle_indicator', 'needle_rifle_display'),
        'preview': 'needle_rifle_meter_preview.png',
    },
    'hud_plate': {
        'rel': NEW_HUD + r'\backgrounds',
        'donor': NEW_HUD + r'\backgrounds\carbine_bkd',
        'other': NEW_HUD + r'\backgrounds\smg_bkd',
        'name': 'needle_rifle_bkd',
        'hud': r'ui\hud\needle_rifle',
        'model_3p': NR_JMS,
        'fallback_box': (105, 191, 5, 34),
        'stretch': 1.4,
        'all_images': {'dim': {1: 0}},       # the Carbine's bright + out-of-ammo plates
    },
    # Reach's reticle: one arc (hud_reticles #4, 11 x 27) on four widgets at +-14: a 50-unit ring. 1 chud unit
    # = 1.157 px at 1080p (Halo 1's B2 screenshot: the lens's 590 px), 1.117 screen px a bitmap px (the AR)
    'reticle': {
        'rel': NEW_HUD + r'\crosshairs',
        'donor': NEW_HUD + r'\crosshairs\hud_reticles',
        'donor_sequence': 57,
        'name': 'needle_rifle_reticle',
        'hud': r'ui\hud\needle_rifle',
        'footprint': 1.0,
        # boot 1: 'missing the inner small circle' -- Reach's zoomed screenshot: an ~11 px ring inside the ~50 px
        # one (radii 5 / 24), a rounded square: the arc at 0.45, 1.5 units out (offline radii 4-8 / 22-30)
        'h3_art': {'sheet': R + r'ui\chud\bitmaps\hud_reticles', 'sequence': 4, 'yardstick': 4, 'ring': 14, 'target_ink': 52,
                   'inner': (1.5, 0.45)},
        'preview': 'needle_rifle_reticle_preview.png',
    },
    # Reach's scope (carbine_scope ring at 1.4 x 1, needle_rifle_focus hatches, the two word strips): h2_port_scope
    # `art`, the DMR's shape with Halo 1's lens (a Reach screenshot: 865 x 590 px at 1080p, span 933.4; the DMR's
    # 711 was 1.27x too big there). THE COLOURED GLYPHS (h1-coloured-scope-glyphs, an observation of Halo 1): boot 1
    # showed scope_masks clones with a new meter_empty_color still drawing black, so each colour is a clone of the
    # reticle's widget_simple_flash_red, its normal_color edited (function_edits in `weapon`), on flat-blue art
    # (`rgb`, the reticle's convention). Halo 1's approved colours, alpha 0.55, gamma 1.6,
    # 88 x 60 px at 1080p each, centres +-385 px (numbers: their offsets). Picture and glyphs centred by the offsets
    'scope': {
        'rel': NEW_HUD + r'\scope_masks',
        'donor': NEW_HUD + r'\scope_masks\carbine_scope_mask',
        'name': 'needle_rifle_scope_blank',
        'hud': r'ui\hud\needle_rifle.new_hud_definition',
        'widgets': ('scope_mask', 'left_crosshair', 'right_crosshair', 'covenant_2xa', 'covenant_2xb'),
        'size': (8, 8),
        'art': {'chud': R + r'ui\chud\needle_rifle',
                'ring': ('scope', 'scope_mask', 'needle_rifle_scope_mask'), 'ring_size': 512,
                'span': 933.4, 'aspect': 16.0 / 9.0,
                # boot 1: the 512 quarter showed unstretched (480 x 610 px, Reach's 865 x 590): baked at the
                # picture's scale, the screen quarter's size (960 x 540 / 1.117); the lens is clear, Halo 2's
                # scope_masks only darkens (the 'white' was the sky)
                'ring_quarter': (860, 484),
                'rgb': (0, 0, 199),
                'picture': ('covenant_2xa', 'needle_rifle_scope_art'), 'picture_size': 1024,
                'px_per_unit': 1080.0 / 933.4 / 1.117,
                'per_widget': {'blip1': {'drop': True}, 'blip2': {'drop': True}},
                'glyphs': [('left_crosshair', 'needle_rifle_glyph_l', (NR_GLYPHS, 1), (79, 54), 0.55, 1.6),
                           ('right_crosshair', 'needle_rifle_glyph_r', (NR_GLYPHS, 0), (79, 54), 0.55, 1.6)],
                'shaders': {'left_crosshair': r'ui\hud\needle_rifle_glyph_red',
                            'right_crosshair': r'ui\hud\needle_rifle_glyph_teal',
                            'covenant_2xa': r'ui\hud\needle_rifle_scope_art'}},
    },

    # step 8 -- the pickup icon at the reserved U+E144, untinted (the H2 ICON RULE); cc_* -> nr2_*
    'glyph': {
        'box': (160, 62),
        'model_3p': NR_JMS,
        'tif': 'needle_rifle_h2_glyph.tif',
        'colour': (255, 255, 255),
        'style': {'line': (255, 255, 255), 'body': (153, 153, 153)},
    },
    'messages': {
        'donor_prefix': 'cc', 'donor_icon': '&carbine',
        'donor_name': 'Covenant Carbine', 'port_name': 'Needle Rifle',
        'names': [('a Covenant Carbine', 'a Needle Rifle'), ('rounds for Carbine', 'needles for Needle Rifle'),
                  ('round for Carbine', 'needle for Needle Rifle')],
        'weapon': WP,
    },

    # step 9 -- h2_port_fp_anims.py kind 'reach' (the DMR's route): Reach's OWN FP animations for BOTH
    # species (Spartan -> masterchief, Elite -> dervish), helpers dropped. Reach's `ammunition_needles`
    # (a replacement on the 12 needle nodes, 0 = empty, last = full; a spent needle at scale 0.01) is
    # Halo 2's `first_person:ammunition` (the stock needler's, also a replacement): `node_scale`
    'fp_anims': {
        'kind': 'reach',
        'species': {
            'masterchief': {
                'graph': R + r'objects\characters\spartans\fp\weapons\rifle\fp_needle_rifle\fp_needle_rifle.model_animation_graph',
                'arms_rm': R + r'objects\characters\spartans\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_masterchief\fp_arms.jms',
                'source': r'objects\characters\masterchief\fp\weapons\rifle\fp_needle_rifle',
                # the SMG for its 17 sound slots (the DMR's reason)
                'seed': r'objects\characters\masterchief\fp\weapons\rifle\fp_smg\fp_smg'},
            'dervish': {
                'graph': R + r'objects\characters\elite\fp\weapons\rifle\fp_needle_rifle\fp_needle_rifle.model_animation_graph',
                'arms_rm': R + r'objects\characters\elite\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_dervish\dervish_fp_arms.jms',
                'source': r'objects\characters\dervish\fp\weapons\rifle\fp_needle_rifle',
                'seed': r'objects\characters\dervish\fp\weapons\rifle\fp_smg\fp_smg'},
        },
        'weapon_dir': NR + r'\fp_needle_rifle',
        'weapon_rm': RM,
        'weapon_nodes': sorted(NODES.values()),
        'node_names': NODES,
        'drop_nodes': ('pedestal', 'aim_pitch', 'aim_yaw', 'l_humerus', 'r_humerus', 'l_radius', 'r_radius',
                       'l_handguard', 'r_handguard'),
        'aliases': {'first_person:look': ['first_person:overlays', 'first_person:pitch_and_turn']},
        # boot 2: Reach's `ammunition_needles` (renamed first_person:ammunition, node_scale) put the 12 needles
        # OFFSCREEN except in reload / melee, and the user called the world model's DIMMING needles (the needler
        # shader's ammo function, no animation) the more correct look: dropped, the FP needles dim the same way
        # no Halo 2 slot for Reach's sprint / jump / land / fall / ready_initial / equipment (the SAW's list)
        'skip': ['first_person:ammunition_needles', 'first_person:look', 'first_person:acceleration_screens', 'first_person:fall', 'first_person:jump',
                 'first_person:land_hard', 'first_person:land_soft', 'first_person:ready_initial',
                 'first_person:sprint_enter', 'first_person:sprint_exit', 'first_person:sprint_loop',
                 'first_person:sprint_loop_airborne', 'first_person:throw_equipment'],
        'looping': ['first_person:idle', 'first_person:posing:var1', 'first_person:posing:var2'],
        'overlay_reference': 'first_person:idle',
        'weights': {'first_person:posing:var1': 0.5, 'first_person:posing:var2': 0.5},
        'drop_ik': ['masterchief'],
        'clear_sound_ref_flags': True,
        'clear_verify': True,
        # Reach's graph cues one sound an animation at frame 0 (the DMR's measurement): checked in the sounds step
        'source_events': {'cues': {'first_person:melee_strike_1': [('nr_melee', 0)],
                                   'first_person:melee_strike_2': [('nr_melee', 0)],
                                   'first_person:posing:var1': [('nr_pose1', 0)],
                                   'first_person:posing:var2': [('nr_pose2', 0)],
                                   'first_person:ready': [('nr_ready', 0)],
                                   'first_person:reload_empty': [('nr_reload', 0)],
                                   'first_person:reload_full': [('nr_reload', 0)]}},
    },

    # step 10 -- h2_port_sounds.py: Reach's OWN sounds from MCC's haloreach sfx.fsb (the DMR's `bank`). Reach's
    # firing effect plays the shot + an exterior tail: mixed, Halo 1's B2; the far layer in the fire_lod slot.
    # One Spartan set for both species. The needle: its own attach, ricochet, burst and fly-by; the
    # supercombine and the drops are Reach's needler's (Reach's rifle has none of its own)
    'sounds': {
        'weapon': WP,
        'fire_fx': FX + r'\needle_rifle_fire.effect',
        'bank': 'haloreach',
        'audio': _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'out', 'h2_sounds', 'needle_rifle'),
        'audio_key': 'Needle Rifle',
        'h3_bank': {'nr_fire': [RS + r'\needle_rifle\needle_rifle_fire', RS + r'\needle_rifle\n_rifle_tails_ext'],
                    'nr_fire_lod': [RS + r'\needle_rifle\n_rifle_lod_far'],
                    'nr_dryfire': [RS + r'\needler\dryfire'],
                    'nr_reload': [RS + r'\needle_rifle\needle_rifle_fp\needle_rifle_reload'],
                    'nr_ready': [RS + r'\needle_rifle\needle_rifle_fp\needle_rifle_ready'],
                    'nr_melee': [RS + r'\needle_rifle\needle_rifle_fp\needle_rifle_melee'],
                    'nr_pose1': [RS + r'\needle_rifle\needle_rifle_fp\needle_rifle_posing1'],
                    'nr_pose2': [RS + r'\needle_rifle\needle_rifle_fp\needle_rifle_posing2'],
                    'nr_zoom_in': [RS + r'\needle_rifle\needle_rifle_zoom\needle_rifle_zoom_in'],
                    'nr_zoom_out': [RS + r'\needle_rifle\needle_rifle_zoom\needle_rifle_zoom_out'],
                    'nr_ammo': [RS + r'\needle_rifle\needle_rifle_powerup'],
                    'nr_drop': [RS + r'\needler\needler_drop'],
                    'nr_drop_soft': [RS + r'\needler\needler_drop_soft'],
                    'nr_flyby': [RS + r'\needle_rifle\needle_rifle_bolt_by'],
                    'nr_attach': [RS + r'\needle_rifle\n_rifle_bolt_attach'],
                    'nr_ricc': [RS + r'\needle_rifle\n_rifle_ricc'],
                    'nr_burst': [RS + r'\needle_rifle\needle_rifle_bolt_expl'],
                    'nr_super': [RS + r'\needler\needler_super_expl']},
        'sounds': {'nr_fire': ('nr_fire', 'weapon_fire'), 'nr_fire_lod': ('nr_fire_lod', 'weapon_fire'),
                   'nr_dryfire': ('nr_dryfire', 'weapon_empty'), 'nr_reload': ('nr_reload', 'weapon_reload'),
                   'nr_ready': ('nr_ready', 'weapon_ready'), 'nr_melee': ('nr_melee', 'weapon_melee'),
                   'nr_pose1': ('nr_pose1', 'weapon_animation'), 'nr_pose2': ('nr_pose2', 'weapon_animation'),
                   'nr_zoom_in': ('nr_zoom_in', 'weapon_ready'), 'nr_zoom_out': ('nr_zoom_out', 'weapon_ready'),
                   'nr_ammo': ('nr_ammo', 'weapon_reload'), 'nr_drop': ('nr_drop', 'object_impacts'),
                   'nr_drop_soft': ('nr_drop_soft', 'object_impacts'), 'nr_flyby': ('nr_flyby', 'projectile_flyby'),
                   'nr_attach': ('nr_attach', 'projectile_impact'), 'nr_ricc': ('nr_ricc', 'projectile_impact'),
                   'nr_burst': ('nr_burst', 'projectile_detonation'), 'nr_super': ('nr_super', 'projectile_detonation')},
        'repoint_fx': [(r'sound\weapons\needler\fire', 'nr_fire'),
                       (r'sound_remastered\weapons\needler\fire_lod', 'nr_fire_lod')],
        'repoint_weapon': [(r'sound\weapons\beam_rifle\beam_rifle_zoom_in', 'nr_zoom_in'),
                           (r'sound\weapons\beam_rifle\beam_rifle_zoom_out', 'nr_zoom_out'),
                           (r'sound\weapons\covenant_carbine\carbine_ammo_pickup', 'nr_ammo')],
        'repoint_tags': [(FX + r'\needle_rifle_empty.effect', r'sound\weapons\needler\dryfire', 'nr_dryfire'),
                         (PR, r'sound\weapons\needler\needler_flyby', 'nr_flyby'),
                         (FX + r'\airborne_detonation.effect', r'sound\weapons\needler\expl', 'nr_burst'),
                         (FX + r'\standard_detonation.effect', r'sound\weapons\needler\expl', 'nr_burst'),
                         (FX + r'\super_detonation.effect', r'sound\weapons\needler\needler_super_expl', 'nr_super'),
                         (FX + r'\needle_rifle.material_effects', r'sound\weapons\covenant_carbine\carbine_drop', 'nr_drop'),
                         (FX + r'\needle_rifle.material_effects', r'sound\weapons\covenant_carbine\carbine_drop_soft', 'nr_drop_soft'),
                         (FX + r'\needle_rifle_shard.material_effects', r'sound\weapons\needler\needler_drop', 'nr_drop'),
                         (FX + r'\needle_rifle_shard.material_effects', r'sound\weapons\needler\needler_drop_soft', 'nr_drop_soft'),
                         (FX + r'\needle_rifle_shard.material_effects', r'sound\weapons\needler\needler_granite', 'nr_attach'),
                         (FX + r'\needle_rifle_shard.material_effects', r'sound\weapons\needler\needle_ricc', 'nr_ricc')],
        # the SMG seed's 17 references, all repointed; unused dual slots point at the ready
        'graph_sounds': (('smg_melee1', 'nr_melee'), ('smg_ready', 'nr_ready'), ('smg_reload', 'nr_reload'),
                         ('smg_reload_full', 'nr_reload'), ('smg_dual_ready', 'nr_melee'),
                         ('smg_posing_var0', 'nr_pose1'), ('smg_posing_var1', 'nr_pose2'),
                         ('smg_dual_reload_left', 'nr_ready'), ('smg_dual_reload_right', 'nr_ready'),
                         ('smg_dual_posing_0_l', 'nr_ready'), ('smg_dual_posing_0_r', 'nr_ready'),
                         ('smg_dual_posing_1_l', 'nr_ready'), ('smg_dual_posing_1_r', 'nr_ready'),
                         ('smg_dual_posing_2_l', 'nr_ready'), ('smg_dual_posing_2_r', 'nr_ready'),
                         ('smg_dual_posing_3_l', 'nr_ready'), ('smg_dual_posing_3_r', 'nr_ready')),
        'graph_sound_dir': r'sound\weapons\smg' + '\\',
        'gain': {},
        'boost': {},
        'backup': r'E:\HaloBackups\H2EK_needle_rifle_before_sounds',
        'graph_backup': r'E:\HaloBackups\H2EK_needle_rifle_graphs_before_sounds',
    },

    # step 11 -- `python ai_firing_profile.py --h2-port needle_rifle`: Reach's ai\generic entry (m10) over the
    # H2 Carbine's (the donor)
    'firing_profile': {'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\needle_rifle\\needle_rifle',
                       'donor_weapon': CC + r'\covenant_carbine'},
    # step 4b -- port_field_audit.py --port h2:needle_rifle: the source pair (Reach's rifle vs Reach's needler,
    # the yardstick) against the target pair (the port vs the H2 needler)
    'field_audit': {
        'source_kit': 'HREK',
        'source': {'weapon': (NR + r'\needle_rifle.weapon', ND + r'\needler.weapon'),
                   'projectile': (NR + r'\projectiles\needle_rifle_shard.projectile', ND + r'\projectiles\needler_shard.projectile'),
                   'damage_effect': (NR + r'\projectiles\damage_effects\needle_rifle_shard_impact.damage_effect',
                                     ND + r'\projectiles\damage_effects\needler_shard_impact.damage_effect')},
        'target': {'weapon': (WP, ND + r'\needler.weapon'),
                   'projectile': (PR, ND + r'\projectiles\needler_shard\needler_shard.projectile'),
                   'damage_effect': (DM + r'\needle_rifle_shard_impact.damage_effect', ND + r'\damage_effects\needler_shard_impact.damage_effect')},
    },

    # BALANCED (step 4a, user 2026-11-01: reports/h2_needle_rifle_4a.md). The table reads the NEEDLER's tags: each
    # redirected onto the port's own; the needle's damage row (the Needler's detonation) lands on the port's IMPACT
    # (Reach's needle is one impact hit). Melee rows dropped (strike_melee is everyone's); the FP anim rows have no
    # port tag (Reach's own 82-frame reload kept, reload_mult None)
    'catalog': {
        'table': 'balance_Needle_Rifle_HaloReach_to_Halo2.json',
        'weapon_tag': WP[:-len('.weapon')],
        'port_tags': [(('weap', ND + r'\needler'), NR + r'\needle_rifle'),
                      (('proj', ND + r'\projectiles\needler_shard\needler_shard'), NR + r'\projectiles\needle_rifle_shard'),
                      (('jpt!', ND + r'\damage_effects\needler_shard_attached_super_detonation'),
                       DM + r'\needle_rifle_shard_attached_super_detonation'),
                      (('jpt!', ND + r'\damage_effects\needler_shard_super_detonation'), DM + r'\needle_rifle_shard_super_detonation')],
        # the needle's damage (the table's needler_shard_detonation rows, 2) is NOT redirected: an override by field
        # name would hit the attached blast's Damage rows too -- its 3 is three extra rows on the port's impact
        'shared': [('jpt!', r'objects\weapons\damage_effects\strike_melee')],
        'value_overrides': dict([
            ('Super Detonation Projectile Count', {'value': 2, 'note': "user 4a: 3 needles; Halo 2 combines ABOVE the count "
                                                                         "(boot 3: 2 -> 3 needles)"}),
            ('Timer', {'value': 1.5, 'note': 'user 4a: the stock 0.5 x 6/2 shot gaps -- the third needle lands inside it'}),
            ('Timer Max', {'value': 2.1, 'note': 'user 4a: the stock 0.7 x 6/2 shot gaps'}),
            ('Minimum Error', {'value': 0.0, 'note': "user 4a: the Carbine answers accuracy -- Reach's min 0"}),
            ('Error Angle', {'value': 0.3, 'note': "user 4a: the Carbine's 0.3"}),
            ('Error Angle Max', {'value': 1.0, 'note': 'user 4a: 0.3-1.0'}),
            ('Magnification Levels', {'value': 1, 'note': "Reach's 2x (the Needler has no zoom: its ratio reads 0)"}),
            ('Magnification Range', {'value': 2.0, 'note': "Reach's 2x"}),
            ('Magnification Range Max', {'value': 2.0, 'note': "Reach's 2x"}),
            ('Rounds Total Initial', {'value': 78, 'note': 'user 4a: 26 / 78 / 105'}),
            ('Rounds Inventory Maximum', {'value': 79, 'note': 'user 4a: 105 total - 26 loaded'}),
            ('Rounds Loaded Maximum', {'value': 26, 'note': 'user 4a: 26'}),
            ('Rounds Reloaded', {'value': 26, 'note': 'user 4a: 26'}),
            ('Rounds Per Second Max', {'value': 4.0, 'note': 'user 4a: 4/s (the max row inverts to 2.67)'}),
            ('Shots Per Fire', {'value': 1, 'note': "Reach's 1 (the Needler's 0 = no recovery)"}),
            ('Shots Per Fire Max', {'value': 1, 'note': "Reach's 1"}),
            ('Fire Recovery Time', {'value': 0.25, 'note': 'user 4a: 4/s + recovery 0.25'})]),
        'extra_rows': [
            {'class': 'jpt!', 'tag': DM + r'\needle_rifle_shard_impact', 'field': f, 'block': None, 'value': 3.0,
             'card': 'Projectile Damage', 'original': 6.0,
             'note': "user 4a: Halo 2's real needle 1 + 2 = 3, on impact (the tool read the detonation alone)"}
            for f in ('Damage Lower Bound', 'Damage Upper Bound', 'Damage Upper Bound Max')] + [
            # the area blast: the Needler's own 30-50 (user 4a: 'attached 400 + area 50, the Needler's')
            {'class': 'jpt!', 'tag': DM + r'\needle_rifle_shard_super_detonation', 'field': f, 'block': None, 'value': v,
             'card': 'Projectile Damage', 'original': o, 'note': "user 4a: the Needler's area blast"}
            for f, v, o in (('Damage Lower Bound', 30.0, 10.0), ('Damage Upper Bound', 50.0, 40.0),
                            ('Damage Upper Bound Max', 50.0, 40.0))] + [
            # the attached blast as the Needler's: the stuck target alone (no radius; Reach's 0.375-1.25 is Original's)
            {'class': 'jpt!', 'tag': DM + r'\needle_rifle_shard_attached_super_detonation', 'field': f, 'block': None,
             'value': 0.0, 'card': 'Projectile Damage', 'original': o,
             'note': "the Needler's attached blast has no radius: 400 to the stuck target alone"}
            for f, o in (('Radius', 0.375), ('Radius Max', 1.25), ('Area Of Effect Core Radius', 0.3))] + [
            # the meter's 26-pip art (sequence 1) for the 26-round Balanced magazine; Original keeps sequence 0's 21
            {'class': 'nhdt', 'tag': r'ui\hud\needle_rifle', 'field': '%s Sequence Index' % scr, 'block': 'Bitmap Widgets',
             'index': 2, 'value': 1, 'card': None, 'original': 0,
             'note': 'ammo meter: the 26-pip art for the 26-round Balanced magazine'}
            for scr in ('Fullscreen', 'Halfscreen')],
        'fp_animations': r'objects\characters\*\fp\weapons\rifle\fp_needle_rifle\fp_needle_rifle',
        'reload_mult': None,
        'desc': ('%s carried from %s into Halo 2 with its own model, textures, sounds, scope and its own Reach '
                 'first-person animations for both species; its needles supercombine at three. Balanced through '
                 'the Needler, its accuracy through the Covenant Carbine.'),
    },

    'test': {'level': '05a_deltaapproach', 'dervish_level': '04b_floodlab', 'rounds': (21, 105)},
    'residency': {'levels': 'all', 'placements': False},
}
