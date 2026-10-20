r"""Assault Rifle into Halo 2 (H2_PORT_PLAN.md wave A (Halo 3), #A1) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

AR = r'objects\weapons\rifle\assault_rifle'      # the source's folder (H3EK) AND the port's (H2EK)
SMG = r'objects\weapons\rifle\smg'                # the donor (H2EK)
FX = r'effects\objects\weapons\rifle\assault_rifle'   # the reserved effects folder
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
                      'compass': 'assault_rifle_compass', 'tens': 'assault_rifle_tens',
                      'ones': 'assault_rifle_ones'},
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
        'bump_gain': 1.6,                      # 2.2 (the SAW's) measured 28.7 vs the SMG's 20.6
        'bitmaps': [(AR + r'\bitmaps\assault_rifle.bitmap', 'assault_rifle', SMG + r'\bitmaps\smg', 'color', None),
                    (AR + r'\bitmaps\assault_rifle_bump.bitmap', 'assault_rifle_bump', SMG + r'\bitmaps\smg_bump',
                     'bump_snorm', None),
                    (AR + r'\bitmaps\display.bitmap', 'assault_rifle_display',
                     r'objects\weapons\rifle\shotgun\bitmaps\illum_sights', 'color', None),
                    (AR + r'\bitmaps\compass.bitmap', 'assault_rifle_compass',
                     r'objects\weapons\rifle\shotgun\bitmaps\illum_sights', 'color', None)],
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
            ('assault_rifle_display', r'objects\weapons\rifle\shotgun\shaders\shotgun_light',
             {r'objects\weapons\rifle\shotgun\bitmaps\illum_sights': AR + r'\bitmaps\assault_rifle_display'}),
            ('assault_rifle_compass', r'objects\weapons\rifle\shotgun\shaders\shotgun_light',
             {r'objects\weapons\rifle\shotgun\bitmaps\illum_sights': AR + r'\bitmaps\assault_rifle_compass'}),
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
        ],
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
        ],
        'skipped': [
            ('melee damage 70', 'Halo 2 weapons share strike_melee / smash_melee: a row would move every weapon'),
            ('reload time', "the magazine's reload time does not drive the player's reload (the SAW, user): "
                            "the AR's own 58-frame animation does"),
            ('first person weapon offset', "Halo 3's is 0,0,0 against the SMG's 0.02 forward -- left the "
                                           "SMG's until the first look in game"),
        ],
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

    'firing_profile': {'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\rifle\\assault_rifle\\assault_rifle', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}
