r"""Assault Rifle into Halo 2 (H2_PORT_PLAN.md wave A (Halo 3), #A1) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

AR = r'objects\weapons\rifle\assault_rifle'      # the source's folder (H3EK) AND the port's (H2EK)
SMG = r'objects\weapons\rifle\smg'                # the donor (H2EK)
FX = r'effects\objects\weapons\rifle\assault_rifle'   # the reserved effects folder
NEW_HUD = r'ui\hud\bitmaps\new_hud'
import os as _os
# the Halo 3 world render model's export (h1_fp_retarget.export_xml's cache; regenerable): the
# silhouette the HUD plate, backpack icon and pickup glyph are drawn from
H3_RM_XML = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'out', 'h3_export',
                          'objects~weapons~rifle~assault_rifle~assault_rifle.render_model.xml')
H3SND = r'data\sound\weapons'           # source folders in MCC's halo3 sfx.fsb (.info)
H2EK = r'F:\SteamLibrary\steamapps\common\H2EK'

PORT = {
    'order': 1,
    'wave': 'A1',
    'name': 'Assault Rifle',
    'source': 'Halo 3',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\rifle\\assault_rifle\\assault_rifle',
    'reservations': {
        'message_prefix': 'ar2',
        'glyph': 0xE13E,
        'weapon_dir': 'objects\\weapons\\rifle\\assault_rifle',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\assault_rifle',
        'fp_graph': 'weapons\\rifle\\fp_assault_rifle\\fp_assault_rifle',
        'hud': 'ui\\hud\\assault_rifle',
        'hud_bitmap_prefix': 'assault_rifle_',
        'sound_dir': 'sound\\weapons\\assault_rifle_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\smg\\smg', 'message_prefix': 'smg',
              'why': 'spew magazine bullet 1/1/1, ammo HUD; clear can-be-dual-wielded. Alt: battle_rifle (br), two-handed non-dual'},
    'yardstick': {
        # step 4a, user 2026-10-20: the SMG; balance_Assault_Rifle_Halo3_to_Halo2.json
        # (balance_port.py "Assault Rifle" "Halo 3" "Halo 2" --hop "SMG:Halo 3>Halo 2")
        'pick': 'SMG',
        'reason': ('user 2026-10-20: same role (magazine full-auto bullet projectile), the clone '
                   'donor, ONE hop. Halo 2 scale ~= Halo 3 (most ratios x1): balanced damage '
                   '7.125 (x0.95), autoaim 6, rider 0.75 / 0.75, melee 20-60, velocity 80, ammo '
                   '32 / 96 / 384 and reload 58 frames unchanged (x1; the dual-wield carry rule '
                   'does not run SMG -> AR). SPREAD by the SIBLING ratio (user): the raw ratios '
                   'put minimum error 0.4 above the cone lower bound 0.08 (x4 / x0.8), so all '
                   'three take the upper bound x1: 0.1 / 0.1-3 = Halo 3 own spread. Elite minor '
                   'legendary TTK 2.10 s (default 1.90; H2 SMG 2.07, BR 3.15, PR 4.76, SAW 0.95)'),
        'spread_override': {'Minimum Error': 0.1, 'Error Angle': 0.1, 'Error Angle Max': 3.0},
        'candidates': {
            'provisional': 'SMG',
            'alternatives': ['Battle Rifle', 'Plasma Rifle'],
            'direct': 'none (no AR in Halo 2; the family table maps the automatic rifle to the SMG)',
            'peers': ['SMG', 'Battle Rifle', 'Plasma Rifle', 'Brute Plasma Rifle', 'SAW (port)'],
            'why': 'magazine 32 full-auto bullet projectile (10/s) = the SMG role; the SMG is in H3 AND H2: ONE hop (balance_SMG_Halo3_to_Halo2.json exists). AR is not dual-wieldable: watch the carry (H2 SMG 240 vs H3 AR 384)',
        },
    },
    # step 1 -- h2_port_geometry.py kind 'h3': the Halo 3 render models on their OWN skeleton
    # (gun, magazine, ophandle, safety [, switch in first person]) -- the AR's own FP animations
    # drive them (H2_PORT_PLAN 0.4: Halo 3's FP arms ARE Halo 2's)
    'geometry': {
        'kind': 'h3',
        'world_rm': AR + r'\assault_rifle.render_model',
        'fp_rm': AR + r'\fp_assault_rifle\fp_assault_rifle.render_model',
        'data_dir': AR,
        'world': 'assault_rifle', 'fp': 'fp_assault_rifle',
        # Halo 3 shader basename -> Halo 2 material (= the shader tag's name in shaders\); the
        # *_pbr ones are MCC's remastered set, unused by any part
        'materials': {'assault_rifle': 'assault_rifle', 'assault_rifle_rubber': 'assault_rifle_rubber',
                      'assault_rifle_env': 'assault_rifle_env', 'display': 'assault_rifle_display',
                      'compass': 'assault_rifle_compass',
                      # Bungie's BR counter digits are `tens=?` / `ones=?` (no shadow, two-sided
                      # transparent); the shader is the name without the symbols
                      'tens': 'assault_rifle_tens=?', 'ones': 'assault_rifle_ones=?'},
        # the world .model is the BR's clone: its variants name permutation `base`, region `gun`
        # (battle_rifle_L5.jms '(1) L5 base gun'); the FP render model is used directly
        'world_permutation': 'base', 'world_region': 'gun',
        # Bungie's case (the BR's render, FP and collision JMS: `frame OpHandle`; its graphs say
        # `ophandle` -- tool matches without case)
        'node_names': {'ophandle': 'frame OpHandle'},
        'markers': {'primary_trigger': 'primary_trigger', 'primary_ejection': 'primary_ejection',
                    'left_hand': 'left_hand', 'flashlight': 'flashlight', 'muzzle_flash': 'muzzle_flash'},
        # the SAW's 1.40 was measured against the SMG's effect -- but the SMG's `frame gun` node
        # itself sits 1.40 up and markers are node-relative (L5_smg.jms), so it may be that node's
        # offset, not the effect's: the AR's gun node is at the origin, start with none (check in game)
        'muzzle_drop': 0.0,
        'ground_point': {'rot': (0.7071068883, -1.8e-09, -7.42e-08, -0.7071067095)},   # the SMG's
        'render': ['assault_rifle', r'assault_rifle\fp_assault_rifle'],
    },

    # step 2 -- h2_port_textures.py kind 'h3': Halo 3's own maps; shaders reseeded from Bungie's
    # Halo 2 SMG (the same templates: tex_bump_active_camo, tex_bump_env), the shotgun's lit sight
    # (tex_bump_illum) for the two displays, the BR's on-gun counter (illum_detail, its digit plate)
    'textures': {
        'kind': 'h3',
        'rel': AR + r'\bitmaps',
        'shaders_dir': AR + r'\shaders',
        'bump_gain': 1.0,                      # slope = Bungie's SMG (user boot 1: 'world texture a little rough' at 1.6)
        'bitmaps': [(AR + r'\bitmaps\assault_rifle.bitmap', 'assault_rifle', SMG + r'\bitmaps\smg', 'color', None),
                    (AR + r'\bitmaps\assault_rifle_bump.bitmap', 'assault_rifle_bump', SMG + r'\bitmaps\smg_bump',
                     'bump_snorm', None),
                    # the holo layers ADDITIVE (boot 2, user: 'the layers have clear squares'): the
                    # colour premultiplied by Halo 3's alpha, so what was transparent adds nothing
                    (AR + r'\bitmaps\display.bitmap', 'assault_rifle_display',
                     r'objects\weapons\rifle\shotgun\bitmaps\illum_sights', 'color_premul', None),
                    (AR + r'\bitmaps\compass.bitmap', 'assault_rifle_compass',
                     r'objects\weapons\rifle\shotgun\bitmaps\illum_sights', 'color_premul', None)],
        'shaders': [
            ('assault_rifle', SMG + r'\shaders\smg_painted_metal',
             {SMG + r'\bitmaps\smg': AR + r'\bitmaps\assault_rifle',
              SMG + r'\bitmaps\smg_bump': AR + r'\bitmaps\assault_rifle_bump',
              SMG + r'\bitmaps\smg_bump_active_camo': AR + r'\bitmaps\assault_rifle_bump'}),
            ('assault_rifle_rubber', SMG + r'\shaders\smg_rubber_grip',
             {SMG + r'\bitmaps\smg': AR + r'\bitmaps\assault_rifle',
              SMG + r'\bitmaps\smg_bump': AR + r'\bitmaps\assault_rifle_bump',
              SMG + r'\bitmaps\smg_bump_active_camo': AR + r'\bitmaps\assault_rifle_bump'}),
            ('assault_rifle_env', SMG + r'\shaders\smg_bare_metal',
             {SMG + r'\bitmaps\smg': AR + r'\bitmaps\assault_rifle',
              SMG + r'\bitmaps\smg_bump': AR + r'\bitmaps\assault_rifle_bump',
              SMG + r'\bitmaps\smg_bump_active_camo': AR + r'\bitmaps\assault_rifle_bump'}),
            # the holo display + compass: Bungie's ADDITIVE self-illumination (the plasma cannon's
            # plasma_illum, transparent\two_add_env_illum) -- the shotgun's lit sight is opaque
            # (tex_bump_illum) and drew every layer's square (boot 2)
            ('assault_rifle_display', r'objects\weapons\fixed\plasma_cannon\shaders\plasma_illum',
             {r'objects\weapons\fixed\plasma_cannon\bitmaps\plasma_cannon': AR + r'\bitmaps\assault_rifle_display'}),
            ('assault_rifle_compass', r'objects\weapons\fixed\plasma_cannon\shaders\plasma_illum',
             {r'objects\weapons\fixed\plasma_cannon\bitmaps\plasma_cannon': AR + r'\bitmaps\assault_rifle_compass'}),
            # the counter: the BR's own digit plate + detail map, Bungie's (an H2 counter's look)
            ('assault_rifle_tens', r'objects\weapons\rifle\battle_rifle\shaders\tens', {}),
            ('assault_rifle_ones', r'objects\weapons\rifle\battle_rifle\shaders\ones', {}),
        ],
        'report_rows': [(AR + r'\bitmaps\assault_rifle_bump', 'the port'),
                        (SMG + r'\bitmaps\smg_bump', 'Bungie SMG')],
    },

    # step 3 -- h2_port_weapon.py: the H2 SMG's weapon (the yardstick's own tag: spew, 1 magazine /
    # 1 trigger / 1 barrel, ammo HUD), every tag a balance row or a look may touch cloned; the world
    # .model from the BATTLE RIFLE's (two-handed, no world-model graph -- the SMG's names one for
    # its own charging handle)
    'weapon': {
        'weapon': AR + r'\assault_rifle.weapon',
        'clones': [(SMG + r'\smg.weapon', AR + r'\assault_rifle.weapon'),
                   (r'objects\weapons\rifle\battle_rifle\battle_rifle.model', AR + r'\assault_rifle.model'),
                   (SMG + r'\projectiles\smg_bullet.projectile', AR + r'\projectiles\assault_rifle_bullet.projectile'),
                   (SMG + r'\damage_effects\smg_bullet.damage_effect', AR + r'\damage_effects\assault_rifle_bullet.damage_effect'),
                   (SMG + r'\damage_effects\smg_trigger.damage_effect', AR + r'\damage_effects\assault_rifle_trigger.damage_effect'),
                   (r'effects\objects\weapons\rifle\smg\fire_bullet.effect', FX + r'\assault_rifle_fire.effect'),
                   (r'effects\objects\weapons\rifle\smg\smg_muzzle_flash.light', FX + r'\assault_rifle_muzzle_flash.light'),
                   (r'effects\materials\objects\weapons\smg.material_effects', FX + r'\assault_rifle_bullet.material_effects')],
        'wiring': [
            (AR + r'\assault_rifle.weapon', 'hlmt', SMG + r'\smg', AR + r'\assault_rifle', 'world model'),
            (AR + r'\assault_rifle.model', 'mode', r'objects\weapons\rifle\battle_rifle\battle_rifle',
             AR + r'\assault_rifle', 'the world render model (it and the collision pool ONE path)', {'nth': 0}),
            (AR + r'\assault_rifle.weapon', 'mode', SMG + r'\fp_smg\fp_smg',
             AR + r'\fp_assault_rifle\fp_assault_rifle', 'first person model, Master Chief', {'nth': 0}),
            # the same path again (every=True refuses: a third record has that path's length)
            (AR + r'\assault_rifle.weapon', 'mode', SMG + r'\fp_smg\fp_smg',
             AR + r'\fp_assault_rifle\fp_assault_rifle', 'first person model, Dervish (one Halo 3 FP model)',
             {'nth': 0}),
            (AR + r'\assault_rifle.weapon', 'jmad', r'objects\characters\masterchief\fp\weapons\rifle\fp_smg\fp_smg',
             r'objects\characters\masterchief\fp\weapons\rifle\fp_assault_rifle\fp_assault_rifle',
             'Master Chief FP graph: the AR\'s own Halo 3 animations'),
            (AR + r'\assault_rifle.weapon', 'jmad', r'objects\characters\dervish\fp\weapons\rifle\fp_smg\fp_smg',
             r'objects\characters\dervish\fp\weapons\rifle\fp_assault_rifle\fp_assault_rifle',
             'Dervish FP graph: the AR\'s own Halo 3 animations'),
            (AR + r'\assault_rifle.weapon', 'proj', SMG + r'\projectiles\smg_bullet',
             AR + r'\projectiles\assault_rifle_bullet', 'projectile'),
            (AR + r'\projectiles\assault_rifle_bullet.projectile', 'jpt!', SMG + r'\damage_effects\smg_bullet',
             AR + r'\damage_effects\assault_rifle_bullet', 'impact damage'),
            (AR + r'\assault_rifle.weapon', 'jpt!', SMG + r'\damage_effects\smg_trigger',
             AR + r'\damage_effects\assault_rifle_trigger', 'firing damage'),
            (AR + r'\assault_rifle.weapon', 'effe', r'effects\objects\weapons\rifle\smg\fire_bullet',
             FX + r'\assault_rifle_fire', 'firing effect'),
            (AR + r'\assault_rifle.weapon', 'ligh', r'effects\objects\weapons\rifle\smg\smg_muzzle_flash',
             FX + r'\assault_rifle_muzzle_flash', 'muzzle flash light'),
            (AR + r'\assault_rifle.weapon', 'foot', r'effects\materials\objects\weapons\smg',
             FX + r'\assault_rifle_bullet', 'material effects (the weapon)'),
            (AR + r'\projectiles\assault_rifle_bullet.projectile', 'foot', r'effects\materials\objects\weapons\smg',
             FX + r'\assault_rifle_bullet', 'impact material effects'),
            # the HUD is the BR's clone (step 7: single, two-handed; the SMG's is dual-wield shaped)
            (AR + r'\assault_rifle.weapon', 'nhdt', r'ui\hud\smg', r'ui\hud\assault_rifle', 'its own HUD (step 7)'),
        ],
        # the 3P label: the BATTLE RIFLE's (`rifle` / `br`) -- every character's 3P graph holds the
        # two-handed BR; the SMG's `smg` is a one-handed (dual-wield) hold. A stock label, no new 3P
        # animations (H2_PORT_PLAN 0.3); Halo 3's own is `rifle` / `ar`, which no Halo 2 graph has
        'string_ids': {'rifle': 'rifle', 'smg': 'br'},
        'string_ids_done': ('weapon name', 'br'),
        'shared': [(r'the particles inside assault_rifle_fire', "the SMG's (Halo 3 particles do not port)"),
                   (r'objects\weapons\damage_effects\*_melee', 'shared by every Halo 2 weapon'),
                   (r'effects\objects\weapons\pistol\needler\ready, ...\battle_rifle\reload',
                    "Bungie's own SMG names them (ready / reloading effects)"),
                   (r'objects\powerups\smg_ammo\smg_ammo', "the SMG's ammo pickup item (unused in campaign)"),
                   (r'effects\bitmaps\weapons_fire\*, smoke_warthog_gun', "the SMG's own weapon bitmaps")],
    },

    # step 4 -- h2_port_numbers.py: Halo 3's OWN values (DEFAULT; the balanced rows are the
    # catalog's, step 4a's SMG table). h3_weapon_values.py rifle\assault_rifle\assault_rifle
    'numbers': {
        'numbers': [
            # flags'': the SMG's minus 'can be dual wielded' (0x400000); 'loop fp firing animation' kept
            (AR + r'\assault_rifle.weapon', 'flags', '', 0, 2, 131072),
            (AR + r'\assault_rifle.weapon', 'autoaim angle', '', 0, 0, 5.0),
            (AR + r'\assault_rifle.weapon', 'autoaim range', '', 0, 0, 15.0),
            (AR + r'\assault_rifle.weapon', 'magnetism angle', '', 0, 1, 10.0),
            (AR + r'\assault_rifle.weapon', 'magnetism range', '', 0, 1, 20.0),
            (AR + r'\assault_rifle.weapon', 'rounds loaded maximum', 'magazines', 0, 0, 32),
            (AR + r'\assault_rifle.weapon', 'rounds reloaded', 'magazines', 0, 0, 32),
            (AR + r'\assault_rifle.weapon', 'rounds total initial', 'magazines', 0, 0, 96),
            (AR + r'\assault_rifle.weapon', 'rounds total maximum', 'magazines', 0, 0, 384),
            (AR + r'\assault_rifle.weapon', 'rounds per second', 'barrels', 0, 0, [10.0, 10.0]),
            # the rate ramp (nth 0) off: Halo 3's AR fires a flat 10
            (AR + r'\assault_rifle.weapon', 'acceleration time', 'barrels', 0, 0, 0.0),
            (AR + r'\assault_rifle.weapon', 'deceleration time', 'barrels', 0, 0, 0.0),
            # the bloom ramp (nth 2): Halo 3 0.5 / 0.5
            (AR + r'\assault_rifle.weapon', 'acceleration time', 'barrels', 0, 2, 0.5),
            (AR + r'\assault_rifle.weapon', 'deceleration time', 'barrels', 0, 2, 0.5),
            (AR + r'\assault_rifle.weapon', 'minimum error', 'barrels', 0, 1, 0.1),
            (AR + r'\assault_rifle.weapon', 'error angle', 'barrels', 0, 1, [0.1, 3.0]),
            # Halo 3's AR has no barrel climb (the SMG's 0..0.7 'late')
            (AR + r'\assault_rifle.weapon', 'angle change per shot', 'barrels', 0, 0, [0.0, 0.0]),
            (AR + r'\projectiles\assault_rifle_bullet.projectile', 'initial velocity', '', 0, 0, 80.0),
            (AR + r'\projectiles\assault_rifle_bullet.projectile', 'final velocity', '', 0, 0, 80.0),
            (AR + r'\projectiles\assault_rifle_bullet.projectile', 'maximum range', '', 0, 0, 40.0),
            (AR + r'\damage_effects\assault_rifle_bullet.damage_effect', 'damage upper bound', '', 0, 0, [7.5, 7.5]),
            (AR + r'\damage_effects\assault_rifle_bullet.damage_effect', 'instantaneous acceleration', '', 0, 0, 0.125),
            # first-person placement (user, boot 1 on 03b: 'move it back and down 3 units', 1 unit =
            # 0.01 wu): the SMG's 0.02, 0, 0 -> -0.01, 0, -0.03
            # boot 2: 'one forward and 2 down' (0, 0, -0.05) -- boot 3: 'revert to the last boot'
            (AR + r'\assault_rifle.weapon', 'first person weapon offset', '', 0, 0, [-0.01, 0.0, -0.03]),
        ],
        'skipped': [
            ('melee damage 70', 'Halo 2 weapons share strike_melee / smash_melee: a row would move every weapon'),
            ('reload time', "the magazine's reload time does not drive the player's reload (the SAW, user): "
                            "the AR's own 58-frame animation does"),
        ],
    },

    # step 5 -- h2_port_collision.py: the BATTLE RIFLE's authored hull (the world .model's donor,
    # the closest two-handed rifle) scaled per axis to the AR's render mesh
    'collision': {
        'donor': r'objects\weapons\rifle\battle_rifle\battle_rifle',
        'port': AR + r'\assault_rifle',
        'src': r'battle_rifle\collision\battle_rifle_collision.jms',     # under data\!extracted
        'out': AR + r'\collision\assault_rifle.jms',                     # under data
        'port_render_jms': AR + r'\render\assault_rifle.jms',
        'donor_render_jms': r'battle_rifle\render\battle_rifle_L5.jms',
        'max_growth': 1.25,
    },

    # step 7 -- the HUD: a clone of the BATTLE RIFLE's (single, two-handed; the SMG's is dual-wield
    # shaped: its plate x4, meter x2), 32 ticks on the BR meter's canvas, the plate and backpack
    # drawn from the AR's own mesh, Halo 3's crosshair (chud hud_reticles #0), the scope widgets
    # blanked (the AR does not zoom)
    'meter': {
        'donor_meter': NEW_HUD + r'\meters\battle_rifle_meter',
        'rel': NEW_HUD + r'\meters',
        'name': 'assault_rifle_meter',
        'donor_hud': r'ui\hud\battle_rifle',
        'port_hud': r'ui\hud\assault_rifle',
        'weapon': AR + r'\assault_rifle.weapon',
        'rounds': 32, 'rows': 2,             # Halo 3's AR counter: 2 rows of 16
        'canvas': (197, 34), 'tick_w': 6,
        'backpack': NEW_HUD + r'\backpack_weapons',
        'backpack_port': NEW_HUD + r'\assault_rifle_backpack',
        'backpack_size': (62, 30),
        'model_3p': H3_RM_XML,
        'preview': 'assault_rifle_meter_preview.png',
    },
    'hud_plate': {
        'rel': NEW_HUD + r'\backgrounds',
        'donor': NEW_HUD + r'\backgrounds\battle_rifle_bkd',
        'other': NEW_HUD + r'\backgrounds\smg_bkd',
        'name': 'assault_rifle_bkd',
        'hud': r'ui\hud\assault_rifle',
        'model_3p': H3_RM_XML,
        'fallback_box': (105, 191, 5, 34),
        'stretch': 1.4,
    },
    'reticle': {
        'rel': NEW_HUD + r'\crosshairs',
        'donor': NEW_HUD + r'\crosshairs\hud_reticles',
        'donor_sequence': 17,                # the BR's fullscreen crosshair (140 px)
        'name': 'assault_rifle_reticle',
        'hud': r'ui\hud\assault_rifle',
        'footprint': 1.0,
        # the ratio rule on the art: H3 AR sprite #0 x (H2 BR crosshair ink / H3 BR sprite #1 ink),
        # both H3 sprites drawn at the same chud widget scale 0.59
        'h3_art': {'sheet': 'hud_reticles', 'sequence': 0, 'yardstick': 1,
                   # boot 2 (user's Halo 3 screenshot): Halo 3 draws the AR crosshair 72 px across
                   # at 1080p, ours drew 162 (145 ink px x 1.117 screen px a bitmap px) -- 'too
                   # big': Halo 3's ON-SCREEN size, 72 / 1.117 = 64 ink px (the ratio gave 145)
                   'target_ink': 64},
        'preview': 'assault_rifle_reticle_preview.png',
    },
    'scope': {
        'rel': NEW_HUD + r'\scope_masks',
        'donor': NEW_HUD + r'\scope_masks\battle_rifle_scope_mask',
        'name': 'assault_rifle_blank',
        'hud': r'ui\hud\assault_rifle.new_hud_definition',
        'widgets': ('scope_mask', 'left_crosshair', 'right_crosshair', 'bottom_crosshair',
                    'top_crosshair', '2x', 'distance_meter'),
        'size': (8, 8),
    },

    # step 8 -- the pickup icon at U+E13E, the messages (smg_* -> ar2_*: a SHORTER prefix than the
    # donor's, h2_stringid -- the first in game)
    'glyph': {
        'box': (160, 62),
        'model_3p': H3_RM_XML,
        'tif': 'assault_rifle_h2_glyph.tif',
        # Halo 2's HUD blue (user, boot 1: 'the pickup icon is white, the H2 icons are blue'),
        # sampled from the classic HUD in the user's 03b screenshot (meter ticks / ammo digits)
        'colour': (110, 171, 233),
        # boot 2 (user: 'missing the fine lines every vanilla weapon has', the BR's icon beside it):
        # Halo 2's look -- translucent body (dithered), outline + the mesh's feature lines in the
        # BR icon's line colour (sampled: 134,202,255); h2_port_glyph.h2_style
        # the body SOLID (boot 3: the dithered body sheared in game), a darker blue = the BR icon's
        # body as it reads over the level (sampled 4.png ~ 80..96,112,144)
        'style': {'line': (134, 202, 255), 'body': (72, 118, 172)},
    },
    'messages': {
        'donor_prefix': 'smg', 'donor_icon': '&smg',
        'donor_name': 'SMG', 'port_name': 'Assault Rifle',
        'weapon': AR + r'\assault_rifle.weapon',
    },

    # step 10 -- h2_port_sounds.py: Halo 3's OWN sounds from MCC's halo3 sfx.fsb (render_h3_bank,
    # 48 kHz at their native level), classic Opus. Halo 3's AR fires a per-shot sound (ar_fire, 3
    # permutations -- no loop to cut, unlike its SMG) and dry-fires Halo 3's BR dryfire.
    # The seeded graphs (the BR's) cue the BR's four: reload, ready, melee 1, reload_half
    'sounds': {
        'weapon': AR + r'\assault_rifle.weapon',
        'fire_fx': FX + r'\assault_rifle_fire.effect',
        'audio': _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'out',
                               'h2_sounds', 'assault_rifle'),
        'audio_key': 'Assault Rifle',
        'h3_bank': {'ar_fire': [H3SND + r'\assault_rifle\ar_fire'],
                    'ar_dryfire': [H3SND + r'\battle_rifle\dryfire'],
                    'ar_reload': [H3SND + r'\assault_rifle\ar_reload'],
                    'ar_ready': [H3SND + r'\assault_rifle\ar_ready'],
                    'ar_melee1': [H3SND + r'\assault_rifle\ar_melee1']},
        'sounds': {'ar_fire': ('ar_fire', 'weapon_fire'), 'ar_dryfire': ('ar_dryfire', 'weapon_empty'),
                   'ar_reload': ('ar_reload', 'weapon_reload'), 'ar_ready': ('ar_ready', 'weapon_ready'),
                   'ar_melee1': ('ar_melee1', 'weapon_melee')},
        'repoint_fx': (r'sound\weapons\smg\fire', 'ar_fire'),
        'repoint_weapon': (r'sound\weapons\smg\dryfire', 'ar_dryfire'),
        'graph_sounds': (('battle_rifle_reload', 'ar_reload'), ('battle_rifle_ready', 'ar_ready'),
                         ('br_melee_strike_1', 'ar_melee1'), ('battle_rifle_reload_half', 'ar_reload')),
        'graph_sound_dir': r'sound\weapons\battle_rifle' + '\\',
        'gain': {},
        'boost': {},
        'backup': r'E:\HaloBackups\H2EK_assault_rifle_before_sounds',
        'graph_backup': r'E:\HaloBackups\H2EK_assault_rifle_graphs_before_sounds',
    },

    # step 9 -- h2_port_fp_anims.py: Halo 3's OWN FP animations, both species, through
    # `tool fp-model-animations` (the arms JMS = Bungie's, tool extract-render-data; the dervish's
    # is version 8209)
    'fp_anims': {
        'species': {
            'masterchief': {
                'graph': r'objects\characters\masterchief\fp\weapons\rifle\fp_assault_rifle\fp_assault_rifle.model_animation_graph',
                'arms_rm': r'objects\characters\masterchief\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_masterchief\fp_arms.jms',
                'source': r'objects\characters\masterchief\fp\weapons\rifle\fp_assault_rifle',
                # the blend screen + events + sound refs survive the import (h2_port_fp_anims)
                'seed': r'objects\characters\masterchief\fp\weapons\rifle\fp_battle_rifle\fp_battle_rifle'},
            'dervish': {
                'graph': r'objects\characters\dervish\fp\weapons\rifle\fp_assault_rifle\fp_assault_rifle.model_animation_graph',
                'arms_rm': r'objects\characters\dervish\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_dervish\dervish_fp_arms.jms',
                'source': r'objects\characters\dervish\fp\weapons\rifle\fp_assault_rifle',
                'seed': r'objects\characters\dervish\fp\weapons\rifle\fp_battle_rifle\fp_battle_rifle'},
        },
        'weapon_dir': AR + r'\fp_assault_rifle',
        'weapon_rm': AR + r'\fp_assault_rifle\fp_assault_rifle.render_model',
        'weapon_nodes': ['gun', 'magazine', 'ophandle', 'safety', 'switch'],
        # Halo 2 has no equipment (throw_equipment is Halo 3's deployable)
        'skip': ['first_person:throw_equipment'],
        'looping': ['first_person:idle', 'first_person:posing:var1', 'first_person:posing:var2'],
        'overlay_reference': 'first_person:idle',
    },

    # step 11 -- `python ai_firing_profile.py --h2-port assault_rifle`: Halo 3's ai\generic AR entry
    # (010_jungle) name-for-name into H2EK ai\generic, over the H2 SMG's (the yardstick)
    'firing_profile': {'from_game': 'Halo 3', 'from_map': r'halo3\maps\010_jungle.map',
                       'from_weapon': r'objects\weapons\rifle\assault_rifle\assault_rifle',
                       'donor_weapon': r'objects\weapons\rifle\smg\smg'},
    # 03a is the SAW's Armed test level (h2-armed-cards session, staged 2026-10-20 18:08): the
    # AR's Chief test runs on 03b (one test level per session)
    'test': {'level': '03b_newmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}
