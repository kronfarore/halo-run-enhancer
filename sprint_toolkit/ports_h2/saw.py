r"""The Halo 2 SAW -- the first Halo 2 port (Halo 4 storm_lmg, 2026-09-23/24, on the cut GPMG),
REWORKED 2026-10-23 to the Assault Rifle's recipe (user, 2026-10-20: 'remove its dependency on
existing weapons'): the H2 SMG's weapon tag (the yardstick's own) with the BR's world .model / HUD /
collision hull, Halo 4's own render model on its own skeleton, and Halo 4's OWN first-person
animations for both species (h2_port_fp_anims kind 'h4': Halo 1's Storm Rifle arm re-solve -- Halo 1's
arms are Halo 2's masterchief; the Dervish re-posed from the Chief's frames, the Flamethrower's way).
What the rework taught: H2_PORT_PLAN.md "SAW rework"; the recipe: PORTING.md "Halo 2: the SAW rework".

The GPMG (Bungie's cut weapon) stays as it shipped, in every palette; nothing of it is used now.
The pre-rework state: F:\HaloPortBackups\2026-10-23_saw-rework-pre (port_backup --game h2).
"""
B = '\\'
SAW = r'objects\weapons\rifle\saw'
SMG = r'objects\weapons\rifle\smg'                    # the donor = the yardstick (H2EK)
BR = r'objects\weapons\rifle\battle_rifle'            # the world .model / HUD / collision donor
FX = r'effects\objects\weapons\rifle\saw'             # the reserved effects folder
H4 = 'h4:'                                            # an H4EK path (h4_tags)
H4SAW = r'objects\weapons\rifle\storm_lmg'
H4FP = r'objects\characters\storm_fp\weapons\rifle\fp_lmg\storm_fp_lmg'
H2EK = r'F:\SteamLibrary\steamapps\common\H2EK'
H3EK = r'F:\SteamLibrary\steamapps\common\H3EK'
NEW_HUD = r'ui\hud\bitmaps\new_hud'

# the Halo 4 FP skeleton (82 nodes, h4_tags.h3_name) less what Halo 2's 37-node masterchief arms lack
# (= Halo 1's): the Halo 1 Storm Rifle's DROP list (ports_h1/storm_rifle.py), the same storm_fp rig
DROP = (['pedestal', 'aim_pitch', 'aim_yaw'] +
        ['%s_%s' % (s, n) for s in 'lr' for n in
         ('shoulder_helper1', 'shoulder_helper2', 'shoulder_helper3', 'shoulder_helper4',
          'shoulder_fixup', 'upperarm_fixup', 'forearm_helper1', 'forearm_helper2',
          'forearm_helper3', 'forearm_helper4', 'forearm_fixup', 'elbow_fixup', 'elbow_armor',
          'hand_twist', 'wrist_fixup', 'grip', 'pinky0')] +
        ['r_hand_helper1', 'r_hand_helper2', 'r_hand_helper3', 'r_hand_helper4',
         'l_hand_marker_offset'])

# the reload's Halo 4 cues (saw_port_foley.RELOAD: fly_a @0, mech_a @15, mech_b @30, fly_b @54, mech_c
# @66, fly_c + mech_d @90), one own sound each, cued at its frame (fp_anims source_events)
RELOAD_PIECES = [('saw_reload_a', '0'), ('saw_reload_b', '1'), ('saw_reload_c', '2'), ('saw_reload_d', '3'),
                 ('saw_reload_e', '4'), ('saw_reload_f', '5-6')]
RELOAD_CUES = [(n, f) for (n, _c), f in zip(RELOAD_PIECES, (0, 15, 30, 54, 66, 90))]
# the SMG seed graph's sound references (both species, this order) -> the SAW's own
SMG_GRAPH_SOUNDS = (('smg_melee1', 'saw_melee1'), ('smg_ready', 'saw_ready'), ('smg_reload', 'saw_reload_a'),
                    ('smg_reload_full', 'saw_reload_b'), ('smg_dual_ready', 'saw_reload_c'),
                    ('smg_dual_reload_left', 'saw_reload_d'), ('smg_dual_reload_right', 'saw_reload_e'),
                    ('smg_dual_posing_0_l', 'saw_reload_f'), ('smg_dual_posing_0_r', 'saw_melee2'),
                    ('smg_dual_posing_1_l', 'saw_pose1_a'), ('smg_dual_posing_1_r', 'saw_pose1_b'),
                    ('smg_dual_posing_2_l', 'saw_pose1_c'), ('smg_dual_posing_2_r', 'saw_pose2_a'),
                    ('smg_dual_posing_3_l', 'saw_pose2_b'), ('smg_dual_posing_3_r', 'saw_pose2_c'),
                    ('smg_posing_var0', 'saw_pose1_a'), ('smg_posing_var1', 'saw_pose2_a'))

PORT = {
    'order': 0,
    'name': 'SAW',
    'source': 'Halo 4',
    'source_tag': H4SAW + r'\storm_lmg',
    # REWORK (user, 2026-10-20) in progress 2026-10-23 (this session): back to 'done' when finished
    'status': 'rework',
    'reservations': {
        'message_prefix': 'saw2',              # hud_messages ids saw2_* (h2_port_messages)
        'glyph': 0xE13D,                       # pickup icon codepoint, 8 English fonts
        'weapon_dir': SAW,
        'effects_dir': FX,
        'fp_graph': r'weapons\rifle\fp_saw\fp_saw',   # under objects\characters\<species>\fp\
        'hud': r'ui\hud\saw',
        'hud_bitmap_prefix': 'saw_',           # new_hud meters\saw_meter, backgrounds\saw_bkd, ...
        'sound_dir': r'sound\weapons\saw_port',
        'test_level': '03a_oldmombasa',
    },
    # REWORK decisions (user, 2026-10-23): the SMG clone (the AR's recipe) -- was the cut GPMG
    'donor': {'weapon': SMG + r'\smg', 'message_prefix': 'smg',
              'why': "the yardstick's own tag (spew, 1 magazine / 1 trigger / 1 barrel, ammo HUD), "
                     "as the AR; 'can be dual wielded' cleared. Before the rework: the cut GPMG"},
    'yardstick': {'pick': 'SMG',
                  'reason': 'user 2026-10-05: fields no card covers follow the SMG (the balance '
                            'chain H4 AR > H3 AR, H3 SMG > H2 SMG); balance_SAW_Halo4_to_Halo2.json',
                  'candidates': {}},

    # step 1 -- h2_port_geometry.py kind 'h3' (the H4 render model reads through the Halo 3 reader:
    # h4_tags exports Halo 3-shaped XML): Halo 4's ONE render model (world AND first person) on its
    # OWN skeleton (b_gun at the grip, b_magazine) -- Halo 4's own FP animations drive them
    'geometry': {
        'kind': 'h3',
        'world_rm': H4 + H4SAW + r'\storm_lmg.render_model',
        'fp_rm': H4 + H4SAW + r'\storm_lmg.render_model',
        'data_dir': SAW,
        'world': 'saw', 'fp': 'fp_saw',
        # the decals and the DEPLETED display (Halo 4 swaps it in when empty) dropped, as before
        'materials': {'storm_unsc_decals_graphics': None, 'storm_lmg_default': 'saw_gun',
                      'storm_lmg_display_depleted_diff': None, 'storm_lmg_display_diff': 'saw_display'},
        'world_permutation': 'base', 'world_region': 'gun',       # the BR .model's variants
        'node_names': {'b_gun': 'frame gun', 'b_magazine': 'frame magazine'},
        'markers': {'primary_trigger': 'primary_trigger', 'primary_ejection': 'primary_ejection',
                    'left_hand': 'left_hand', 'flashlight': 'flashlight'},
        'muzzle_drop': 0.0,                    # the AR's finding: no drop (markers are node-relative)
        'ground_point': {'rot': (0.7071068883, -1.8e-09, -7.42e-08, -0.7071067095)},   # the SMG's
        'render': ['saw', r'saw\fp_saw'],
    },

    # step 2 -- h2_saw_textures.py (Halo 4's own maps; unchanged by the rework)
    'textures': {
        'kind': 'h4',
        'src_dir': r'F:\SteamLibrary\steamapps\common\H4EK\tags\objects\weapons\rifle\storm_lmg'
                   r'\bitmaps\storm_lmg_default',
        'rel': SAW + r'\bitmaps',
        'shaders': SAW + r'\shaders',
        'seed_dir': r'objects\weapons\fixed\h_turret_mp\bitmaps',
        'bump_size': (512, 256),
        'bump_gain': 2.2,
        # (H4 tag, width, height, format, mips, what it becomes, which Bungie tag seeds it)
        'jobs': [('storm_lmg_diff', 2048, 1024, 'dxt1', 11, 'saw_gun', 'h_turret_mp_gun'),
                 ('storm_lmg_normal', 2048, 1024, 'dxn', 11, 'saw_gun_bump', 'h_turret_mp_gun_bump'),
                 ('storm_lmg_display_diff', 64, 128, 'dxt5', 1, 'saw_display', 'h_turret_mp_gun')],
        # (shader file, class, the bitmap it names now, the port's bitmap, every)
        'shader_refs': [('saw_gun.shader', r'objects\weapons\fixed\h_turret_mp\bitmaps\h_turret_mp_gun',
                         SAW + r'\bitmaps\saw_gun'),
                        ('saw_gun.shader', r'objects\weapons\fixed\h_turret_mp\bitmaps\h_turret_mp_gun_bump',
                         SAW + r'\bitmaps\saw_gun_bump')],
        # the self-illuminated display: a reseeded clone of the shotgun's lit sight
        'lit': {'shader': 'saw_display.shader',
                'seed': r'objects\weapons\rifle\shotgun\shaders\shotgun_light.shader',
                'seed_map': r'objects\weapons\rifle\shotgun\bitmaps\illum_sights',
                'map': SAW + r'\bitmaps\saw_display'},
        'report_rows': [(SAW + r'\bitmaps\saw_gun_bump', 'the port'),
                        (SMG + r'\bitmaps\smg_bump', 'Bungie SMG'),
                        (r'objects\weapons\fixed\h_turret_mp\bitmaps\h_turret_mp_gun_bump', 'Bungie turret')],
    },

    # step 3 -- h2_port_weapon.py: the H2 SMG's weapon, every tag a balance row or a look may touch
    # cloned (--force over the GPMG-era clones, 2026-10-23), the world .model from the BATTLE RIFLE's
    'weapon': {
        'weapon': SAW + r'\saw.weapon',
        'clones': [(SMG + r'\smg.weapon', SAW + r'\saw.weapon'),
                   (BR + r'\battle_rifle.model', SAW + r'\saw.model'),
                   (SMG + r'\projectiles\smg_bullet.projectile', SAW + r'\projectiles\saw_bullet.projectile'),
                   (SMG + r'\damage_effects\smg_bullet.damage_effect', SAW + r'\damage_effects\saw_bullet.damage_effect'),
                   (SMG + r'\damage_effects\smg_trigger.damage_effect', SAW + r'\damage_effects\saw_trigger.damage_effect'),
                   (r'effects\objects\weapons\rifle\smg\fire_bullet.effect', FX + r'\saw_fire.effect'),
                   (r'effects\objects\weapons\rifle\smg\smg_muzzle_flash.light', FX + r'\saw_muzzle_flash.light'),
                   (r'effects\materials\objects\weapons\smg.material_effects', FX + r'\saw_bullet.material_effects')],
        'wiring': [
            (SAW + r'\saw.weapon', 'hlmt', SMG + r'\smg', SAW + r'\saw', 'world model'),
            (SAW + r'\saw.model', 'mode', BR + r'\battle_rifle', SAW + r'\saw',
             'the world render model (it and the collision pool ONE path)', {'nth': 0}),
            (SAW + r'\saw.weapon', 'mode', SMG + r'\fp_smg\fp_smg', SAW + r'\fp_saw\fp_saw',
             'first person model, Master Chief', {'nth': 0}),
            (SAW + r'\saw.weapon', 'mode', SMG + r'\fp_smg\fp_smg', SAW + r'\fp_saw\fp_saw',
             'first person model, Dervish (one Halo 4 FP model)', {'nth': 0}),
            (SAW + r'\saw.weapon', 'jmad', r'objects\characters\masterchief\fp\weapons\rifle\fp_smg\fp_smg',
             r'objects\characters\masterchief\fp\weapons\rifle\fp_saw\fp_saw',
             "Master Chief FP graph: the SAW's own Halo 4 animations"),
            (SAW + r'\saw.weapon', 'jmad', r'objects\characters\dervish\fp\weapons\rifle\fp_smg\fp_smg',
             r'objects\characters\dervish\fp\weapons\rifle\fp_saw\fp_saw',
             "Dervish FP graph: the SAW's own Halo 4 animations, re-posed"),
            (SAW + r'\saw.weapon', 'proj', SMG + r'\projectiles\smg_bullet', SAW + r'\projectiles\saw_bullet', 'projectile'),
            (SAW + r'\projectiles\saw_bullet.projectile', 'jpt!', SMG + r'\damage_effects\smg_bullet',
             SAW + r'\damage_effects\saw_bullet', 'impact damage'),
            (SAW + r'\saw.weapon', 'jpt!', SMG + r'\damage_effects\smg_trigger', SAW + r'\damage_effects\saw_trigger',
             'firing damage'),
            (SAW + r'\saw.weapon', 'effe', r'effects\objects\weapons\rifle\smg\fire_bullet', FX + r'\saw_fire',
             'firing effect'),
            (SAW + r'\saw.weapon', 'ligh', r'effects\objects\weapons\rifle\smg\smg_muzzle_flash',
             FX + r'\saw_muzzle_flash', 'muzzle flash light'),
            (SAW + r'\saw.weapon', 'foot', r'effects\materials\objects\weapons\smg', FX + r'\saw_bullet',
             'material effects (the weapon)'),
            (SAW + r'\projectiles\saw_bullet.projectile', 'foot', r'effects\materials\objects\weapons\smg',
             FX + r'\saw_bullet', 'impact material effects'),
            # the HUD is the BR's clone (step 7: single, two-handed; the SMG's is dual-wield shaped)
            (SAW + r'\saw.weapon', 'nhdt', r'ui\hud\smg', r'ui\hud\saw', 'its own HUD (step 7)'),
        ],
        # the 3P label: the BATTLE RIFLE's (`rifle` / `br`), the AR's -- every character's 3P graph
        # holds the two-handed BR (the GPMG clone said rifle / `sr`, the sniper's)
        'string_ids': {'rifle': 'rifle', 'smg': 'br'},
        'string_ids_done': ('weapon name', 'br'),
        'shared': [(r'objects\weapons\damage_effects\*_melee', 'shared by every Halo 2 weapon'),
                   (r'effects\objects\weapons\pistol\needler\ready, ...\battle_rifle\reload',
                    "Bungie's own SMG names them (ready / reloading effects)"),
                   (r'objects\powerups\smg_ammo\smg_ammo', "the SMG's ammo pickup item (unused in campaign)"),
                   (r'objects\weapons\rifle\smg\damage_effects\smg_empty', "the SMG's empty-click damage effect"),
                   (r'the particles inside saw_fire + the weapon\'s predicted bitmaps (weapons_fire\fire_burst_*, '
                    r'smoke\smoke_warthog_gun)', "Bungie's SMG particle definitions and the bitmaps they draw "
                                                 "(user, 2026-10-23: the effect retuned toward Halo 4 with Bungie "
                                                 "particles -- Halo 4 particles do not port)"),
                   (r'sound\weapons\smg\smg_ammo', 'the ammo pickup sound: Halo 4 has none in any MCC bank '
                                                  '(user, 2026-10-23: keep a Bungie Halo 2 sound)')],
    },

    # step 4 -- h2_port_numbers.py: Halo 4's OWN values (DEFAULT; the balanced rows are the catalog's)
    'numbers': {
        'numbers': [
            # flags'': the SMG's minus 'can be dual wielded' (0x400000); 'loop fp firing animation' kept
            (SAW + r'\saw.weapon', 'flags', '', 0, 2, 131072),
            (SAW + r'\saw.weapon', 'rounds loaded maximum', 'magazines', 0, 0, 72),
            (SAW + r'\saw.weapon', 'rounds reloaded', 'magazines', 0, 0, 72),
            (SAW + r'\saw.weapon', 'rounds total initial', 'magazines', 0, 0, 216),
            (SAW + r'\saw.weapon', 'rounds total maximum', 'magazines', 0, 0, 288),
            (SAW + r'\saw.weapon', 'rounds per second', 'barrels', 0, 0, [20.0, 20.0]),
            # the rate ramp (nth 0) off: Halo 4's SAW fires a flat 20
            (SAW + r'\saw.weapon', 'acceleration time', 'barrels', 0, 0, 0.0),
            (SAW + r'\saw.weapon', 'deceleration time', 'barrels', 0, 0, 0.0),
            # the live cone (nth 1, the AR's 4b lesson: nth 2 is the DUAL ramp)
            (SAW + r'\saw.weapon', 'minimum error', 'barrels', 0, 1, 0.0),
            (SAW + r'\saw.weapon', 'error angle', 'barrels', 0, 1, [0.3, 2.75]),
            (SAW + r'\saw.weapon', 'deceleration time', 'barrels', 0, 1, 0.49),
            (SAW + r'\damage_effects\saw_bullet.damage_effect', 'damage lower bound', '', 0, 0, 7.5),
            (SAW + r'\damage_effects\saw_bullet.damage_effect', 'damage upper bound', '', 0, 0, [7.5, 7.5]),
            (SAW + r'\damage_effects\saw_bullet.damage_effect', 'instantaneous acceleration', '', 0, 0, 0.15),
            # Halo 4's own card-covered values (the DEFAULT side of the catalog rows, as the AR wrote
            # Halo 3's): aim assist, the bullet's speed and reach
            (SAW + r'\saw.weapon', 'autoaim angle', '', 0, 0, 5.0),
            (SAW + r'\saw.weapon', 'autoaim range', '', 0, 0, 16.0),
            (SAW + r'\saw.weapon', 'magnetism angle', '', 0, 1, 10.0),
            (SAW + r'\saw.weapon', 'magnetism range', '', 0, 1, 16.0),
            (SAW + r'\projectiles\saw_bullet.projectile', 'initial velocity', '', 0, 0, 300.0),
            (SAW + r'\projectiles\saw_bullet.projectile', 'final velocity', '', 0, 0, 300.0),
            (SAW + r'\projectiles\saw_bullet.projectile', 'maximum range', '', 0, 0, 75.0),
            # first-person placement: Halo 4's animations come through Halo 1's FP space (camera =
            # origin, the Flamethrower's), so start with none (the SMG's 0.02, 0, 0 is its own graph's)
            # boot 1 on 03a (user): 'move it down 3 units for starters' (1 unit = 0.01 wu)
            (SAW + r'\saw.weapon', 'first person weapon offset', '', 0, 0, [0.0, 0.0, -0.03]),
            # the HUD (the BR's clone) draws the BR's WEAK-SPOT / HEADSHOT indicators inside the
            # crosshair (the Flamethrower's Armed test): the SAW (the SMG's bullet) has neither -- each
            # widget's [N] condition = its own [Y] one (never shown). After the HUD steps (7)
            # CHECK 10, THE MUZZLE FLASH (2026-10-23, h2_effect_particles; user: 'retune toward Halo 4'):
            # Halo 4's FIRST-person flash is a round flash + SMOKE at primary_trigger, LONG flashes at
            # the brake (muzzle_flash markers) and a soft glow; the SMG clone draws only its round
            # centre burst in first person. Its third-person long burst (system 1) and smoke (system 2)
            # now draw in first person too (camera mode 3 = both, the Spike Rifle's way); the glow is
            # the muzzle light. Not ported: Halo 4's casing (the SMG ejects none; a system = a block insert)
            (FX + r'\saw_fire.effect', 'camera mode', 'particle systems', 1, 0, 3),
            (FX + r'\saw_fire.effect', 'camera mode', 'particle systems', 2, 0, 3),
            (r'ui\hud\saw.new_hud_definition', '[N] extra flags', 'bitmap widgets', 13, 0, 25),
            (r'ui\hud\saw.new_hud_definition', '[N] extra flags', 'bitmap widgets', 12, 0, 4,
             {'anchor': ('[Y] extra flags', 8)}),
        ],
        'skipped': [
            ('fire recovery time', '0.0666667 in Halo 4, which caps a weapon at 15 rounds a second -- '
                                   'it would fight the 20 this one is being given. Halo 2 paces automatic '
                                   'fire with rounds per second.'),
            ('melee damage', 'Halo 2 weapons share strike_melee / smash_melee: a row would move every weapon'),
            ('reload time', "the magazine's reload time does not drive the player's reload (the SAW, user): "
                            "Halo 4's own 128-frame animation does"),
        ],
    },

    # step 4b -- port_field_audit.py --port h2:saw: every field NO card covers where Halo 4's SAW differs
    # from Halo 4's AR (the yardstick chain's first game), ported by the chain's ratio -- list 2 must
    # say 0 to port
    'field_audit': {
        'source_kit': 'H4EK',
        'source': {'weapon': (H4SAW + r'\storm_lmg.weapon',
                              r'objects\weapons\rifle\storm_assault_rifle\storm_assault_rifle.weapon'),
                   'projectile': (H4SAW + r'\projectiles\storm_lmg_bullet.projectile',
                                  r'objects\weapons\rifle\storm_assault_rifle\projectiles\storm_assault_rifle_bullet.projectile'),
                   'damage_effect': (H4SAW + r'\projectiles\storm_lmg_bullet.damage_effect',
                                     r'objects\weapons\rifle\storm_assault_rifle\projectiles\storm_assault_rifle_bullet.damage_effect')},
        'target': {'weapon': (SAW + r'\saw.weapon', SMG + r'\smg.weapon'),
                   'projectile': (SAW + r'\projectiles\saw_bullet.projectile', SMG + r'\projectiles\smg_bullet.projectile'),
                   'damage_effect': (SAW + r'\damage_effects\saw_bullet.damage_effect',
                                     SMG + r'\damage_effects\smg_bullet.damage_effect')},
        'hops': [('H4EK', {'weapon': r'objects\weapons\rifle\storm_assault_rifle\storm_assault_rifle.weapon',
                           'projectile': r'objects\weapons\rifle\storm_assault_rifle\projectiles\storm_assault_rifle_bullet.projectile',
                           'damage_effect': r'objects\weapons\rifle\storm_assault_rifle\projectiles\storm_assault_rifle_bullet.damage_effect'},
                  'H3EK', {'weapon': r'objects\weapons\rifle\assault_rifle\assault_rifle.weapon',
                           'projectile': r'objects\weapons\rifle\assault_rifle\projectiles\assault_rifle_bullet.projectile',
                           'damage_effect': r'objects\weapons\rifle\assault_rifle\damage_effects\assault_rifle_bullet.damage_effect'}),
                 ('H3EK', {'weapon': r'objects\weapons\rifle\smg\smg.weapon',
                           'projectile': r'objects\weapons\rifle\smg\projectiles\smg_bullet.projectile',
                           'damage_effect': r'objects\weapons\rifle\smg\damage_effects\smg_bullet.damage_effect'},
                  'H2EK', {'weapon': SMG + r'\smg.weapon',
                           'projectile': SMG + r'\projectiles\smg_bullet.projectile',
                           'damage_effect': SMG + r'\damage_effects\smg_bullet.damage_effect'})],
        # the rework's run (2026-10-23, after the SMG re-clone): list 2 = 0 to port (weapon, projectile,
        # damage effect; the error ramp's 0.49 and the impulse 0.15 were already written). Decided:
        'decisions': {
            'barrels/[0]/acceleration / deceleration time (nth 0, list 4)': "0 / 0: Halo 4's SAW fires a flat 20 "
                                                                           "(the SMG's 1.0 / 0.2 rate ramp off)",
            "flags'' (list 5)": "the SMG's minus 'can be dual wielded' (Halo 4's SAW is two-handed)",
            'first person weapon offset': "0, 0, -0.03 (user, boot 1: down 3 units); started at 0: Halo 4's animations come through Halo 1's FP space (the "
                                          "Flamethrower's start) -- checked in game",
            'sweetener size / damage reporting type (weapon, projectile)': "the SMG's (enums; kill feed / medals only)",
            'attachments/#count (weapon)': "the SMG's one attachment kept",
            'secondary flags, aim-assist falloffs, low ammo threshold, ammopack rounds, barrel-error sync, '
            'reload penalty; projectile attachments / multiplayer object': 'no Halo 2 field',
            'air gravity scale': "0 = Halo 4's (the SMG's is 0 too)",
        }},

    # step 5 -- h2_port_collision.py: the BATTLE RIFLE's authored hull scaled per axis to the SAW's
    # render mesh, on the SAW's own world skeleton (was the GPMG's hull)
    'collision': {
        'donor': BR + r'\battle_rifle',
        'port': SAW + r'\saw',
        'src': r'battle_rifle\collision\battle_rifle_collision.jms',     # under data\!extracted
        'out': SAW + r'\collision\saw.jms',                               # under data
        'port_render_jms': SAW + r'\render\saw.jms',
        'donor_render_jms': r'battle_rifle\render\battle_rifle_L5.jms',
        'max_growth': 1.25,
        'nodes_from_render': True,
    },

    # step 7 -- the HUD: a clone of the BATTLE RIFLE's (was the GPMG's, itself a BR HUD), 72 ticks on
    # the BR meter's canvas (3 rows of 24), the plate / backpack from the SAW's mesh, Halo 4's crosshair
    'meter': {
        'donor_meter': NEW_HUD + r'\meters\battle_rifle_meter',
        'rel': NEW_HUD + r'\meters',
        'name': 'saw_meter',
        'donor_hud': r'ui\hud\battle_rifle',
        'port_hud': r'ui\hud\saw',
        'weapon': SAW + r'\saw.weapon',
        'rounds': 72, 'rows': 3,
        'canvas': (197, 34), 'tick_w': 6,
        'backpack': NEW_HUD + r'\backpack_weapons',
        'backpack_port': NEW_HUD + r'\saw_backpack',
        'backpack_size': (62, 30),
        'model_3p': H3EK + r'\saw_3p_rm.xml',             # the silhouette's geometry
        'preview': 'saw_meter_preview.png',
    },
    'hud_plate': {
        'rel': NEW_HUD + r'\backgrounds',
        'donor': NEW_HUD + r'\backgrounds\battle_rifle_bkd',
        'other': NEW_HUD + r'\backgrounds\smg_bkd',
        'name': 'saw_bkd',
        'hud': r'ui\hud\saw',
        'model_3p': H3EK + r'\saw_3p_rm.xml',
        'fallback_box': (105, 191, 5, 34),
        'stretch': 1.4,
    },
    # Halo 4's crosshair, own one-image bitmap
    'reticle': {
        'rel': NEW_HUD + r'\crosshairs',
        'donor': NEW_HUD + r'\crosshairs\hud_reticles',
        'donor_sequence': 16,
        'name': 'saw_reticle',
        'hud': r'ui\hud\saw',
        'footprint': 0.6,
        'h4_art': r'ui\hud\weapons\human\lmg\bitmap',
        'layout': [('img_saw_quarter', 4, 3, 32, 32, False, False, 1.0),
                   ('img_saw_quarter', 4, -35, 32, 32, False, True, 1.0),
                   ('img_saw_quarter', -36, 3, 32, 32, True, False, 1.0),
                   ('img_saw_quarter', -36, -35, 32, 32, True, True, 1.0),
                   ('vertical_tick', -4, 5, 8, 8, False, False, 0.55),
                   ('vertical_tick', -4, -13, 8, 8, False, False, 0.55),
                   ('horizontal_tick', -13, -4, 8, 8, False, False, 0.55),
                   ('horizontal_tick', 5, -4, 8, 8, False, False, 0.55)],
        'preview': 'saw_reticle_preview.png',
    },
    # the port does not zoom
    'scope': {
        'rel': NEW_HUD + r'\scope_masks',
        'donor': NEW_HUD + r'\scope_masks\battle_rifle_scope_mask',
        'name': 'saw_blank',
        'hud': r'ui\hud\saw.new_hud_definition',
        'widgets': ('scope_mask', 'left_crosshair', 'right_crosshair', 'bottom_crosshair',
                    'top_crosshair', '2x', 'distance_meter'),
        'size': (8, 8),
    },

    # step 8 -- the pickup icon at U+E13D, the H2 icon rule (user, 2026-10-22): UNTINTED, white lines
    # over a grey body, 160x62 (was the plain white drawing of 2026-09-24)
    'glyph': {
        'box': (160, 62),
        'model_3p': H3EK + r'\saw_3p_rm.xml',
        'tif': 'saw_h2_glyph.tif',
        'colour': (255, 255, 255),
        'style': {'line': (255, 255, 255), 'body': (153, 153, 153)},
    },
    # smg_* -> saw2_* (all seven lines, the dual three included, as the AR / Spiker / Flamethrower)
    'messages': {
        'donor_prefix': 'smg', 'donor_icon': '&smg',
        'donor_name': 'SMG', 'port_name': 'SAW',
        'weapon': SAW + r'\saw.weapon',
        # the article changes with the name ('Picked up an SMG')
        'names': [('an SMG', 'a SAW'), ('SMG', 'SAW')],
    },

    # step 9 -- h2_port_fp_anims.py kind 'h4': Halo 4's OWN FP animations (the Foundry dump
    # out\h4_fp\storm_fp_lmg.json, h4_fp_dump.py), the arms re-solved onto Halo 1's = Halo 2's
    # masterchief (h1_fp_retarget), the Dervish re-posed from the Chief's frames (the Flamethrower's
    # repose); graphs SEEDED from the H2 BR's (blend screen, sound references, events)
    'fp_anims': {
        'kind': 'h4',
        'retarget': {
            'graph': H4 + H4FP + '.model_animation_graph',
            'render_model': H4 + H4SAW + r'\storm_lmg.render_model',
            'nodes': {'gun': 'frame gun', 'magazine': 'frame magazine'},
            'drop_nodes': tuple(DROP),
        },
        'chief_arms': H2EK + r'\data\!extracted\fp_arms_masterchief\fp_arms.jms',
        'weapon_nodes': ['gun', 'magazine'],
        'clear_verify': True,
        # (Halo 4, Halo 2[, opt]): Halo 4's `look` = Halo 3's two 3x3 aim screens (overlays,
        # pitch_and_turn); no Halo 2 slot for sprint / jump / land / fall / melee_dash / ready_initial
        # / acceleration_screens
        'map': [('first_person:idle', 'first_person:idle', {'loop': True}),
                ('first_person:posing:var1', 'first_person:posing:var1', {'loop': True}),
                ('first_person:posing:var2', 'first_person:posing:var2', {'loop': True}),
                ('first_person:ready', 'first_person:ready'),
                ('first_person:put_away', 'first_person:put_away'),
                ('first_person:fire_1:var1', 'first_person:fire_1:var1'),
                ('first_person:fire_1:var2', 'first_person:fire_1:var2'),
                ('first_person:reload_empty', 'first_person:reload_empty'),
                ('first_person:reload_full', 'first_person:reload_full'),
                ('first_person:melee_strike_1', 'first_person:melee_strike_1'),
                ('first_person:melee_strike_2', 'first_person:melee_strike_2'),
                ('first_person:throw_grenade', 'first_person:throw_grenade'),
                ('first_person:moving', 'first_person:moving'),
                ('first_person:look', 'first_person:overlays'),
                ('first_person:look', 'first_person:pitch_and_turn')],
        'overlay_reference': 'first_person:idle',
        # Halo 4's own FRAME events (its .frame_event_list: melee hit 4, reload keyframe 67, grenade
        # release 8, allow interruption ...) and its SOUND cues, ONE SOUND PER CUE at Halo 4's frame
        # (boot 1 on 03a, user: 'is the reload sound timed correctly?' -- one whole-reload mix at frame
        # 0 runs at its own speed while Balanced rebuilds the reload at x0.852 (109 frames): the late
        # cues fell up to 13 frames behind the hands. A cue's frame scales with the animation). The
        # SMG seed has 17 sound references (the BR's 4 forced one mix per animation)
        'source_events': {'cues': {
            'first_person:reload_empty': RELOAD_CUES, 'first_person:reload_full': RELOAD_CUES,
            'first_person:ready': [('saw_ready', 0)],
            'first_person:melee_strike_1': [('saw_melee1', 0)],
            'first_person:melee_strike_2': [('saw_melee2', 0)],
            'first_person:posing:var1': [('saw_pose1_a', 0), ('saw_pose1_b', 40), ('saw_pose1_c', 80)],
            'first_person:posing:var2': [('saw_pose2_a', 0), ('saw_pose2_b', 40), ('saw_pose2_c', 80)]}},
        # the SMG seed's single-wield IK (the Chief's left hand pinned to the left_hand marker) dropped:
        # it would hold the hand on the grip through the reload (the Spike Rifle's drop_ik)
        'drop_ik': ['masterchief'],
        # boot 2 (user: 'the later reload parts, one melee and the fidget are mute'): the SMG seed's
        # dual-wield sound slots are flagged left / right arm only -- every slot's flags cleared
        'clear_sound_ref_flags': True,
        'species': {
            'masterchief': {
                'arms': H2EK + r'\data\!extracted\fp_arms_masterchief\fp_arms.jms',
                'source': r'objects\characters\masterchief\fp\weapons\rifle\fp_saw',
                'seed': r'objects\characters\masterchief\fp\weapons\rifle\fp_smg\fp_smg'},
            'dervish': {
                'arms': H2EK + r'\data\!extracted\fp_arms_dervish\dervish_fp_arms.jms',
                'source': r'objects\characters\dervish\fp\weapons\rifle\fp_saw',
                'seed': r'objects\characters\dervish\fp\weapons\rifle\fp_smg\fp_smg',
                'repose': True},
        },
        'weapon_dir': SAW + r'\fp_saw',
    },

    # step 10 -- h2_port_sounds.py: the SAW's own Halo 4 sounds (made 2026-10-03/04 from the Wwise
    # banks, out\h2_sounds\saw), now cued by the BR-seeded graphs
    'sounds': {
        'weapon': SAW + r'\saw.weapon',
        'fire_fx': FX + r'\saw_fire.effect',
        'audio_key': 'SAW',                                 # port_volume.MARKER_DB / saw_port_sounds
        'sounds': dict({'saw_fire': ('fire', 'weapon_fire'), 'saw_dryfire': ('dryfire', 'weapon_empty'),
                        'saw_ready': ('foley:READY', 'weapon_ready'),
                        'saw_melee1': ('foley:MELEE1', 'weapon_melee'), 'saw_melee2': ('foley:MELEE2', 'weapon_melee'),
                        # the remastered distance layer (was the SMG's fire_lod): Halo 4's own far tail
                        'saw_fire_lod': ('tail', 'weapon_fire')},
                       # ONE sound per Halo 4 cue (h2_port_sounds 'foley:LIST#a-b'), cued at its frame
                       **{n: ('foley:RELOAD#%s' % c, 'weapon_reload') for n, c in RELOAD_PIECES},
                       **{'saw_pose%d_%s' % (v, x): ('foley:POSE%d#%d' % (v, k), 'weapon_animation')
                          for v in (1, 2) for k, x in enumerate('abc')}),
        'repoint_fx': [(r'sound\weapons\smg\fire', 'saw_fire'),
                       (r'sound_remastered\weapons\smg\fire_lod', 'saw_fire_lod')],
        'repoint_weapon': [(r'sound\weapons\smg\dryfire', 'saw_dryfire')],
        # the SMG seed's 17 references, all repointed (the dual ones unused: a single-wield weapon)
        'graph_sounds': SMG_GRAPH_SOUNDS,
        'graph_sound_dir': r'sound\weapons\smg' + B,
        'gain': {'saw_fire': -3.0, 'saw_dryfire': -3.0},
        'boost': {},
        'backup': r'E:\HaloBackups\H2EK_saw_before_sounds',
        'graph_backup': r'E:\HaloBackups\H2EK_saw_graphs_before_foley',
    },

    # BORROWED sounds kept ON PURPOSE (port_sound_refs prints them KEEP): Halo 4's ammo pickup event is
    # in no MCC bank (the Halo 1 SAW's finding) -- user 2026-10-23: keep a Bungie Halo 2 sound
    'sound_keeps': {r'sound\weapons\smg\smg_ammo': "Halo 4's ammo pickup is in no MCC bank (user: keep the SMG's)"},

    # residency: palette entry in every level's weapons resource (h2_port_residency.py). The
    # SAW also has one resident-only placement per level (put there 2026-10-01..04, before the
    # 128-placement cap was measured) -- new ports take the PALETTE ONLY (H2_PORT_PLAN 0.1)
    'residency': {'levels': 'all', 'placements': True},

    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant', 'rounds': (72, 216)},

    # make_port_catalog_h2.py saw: every balance row names the tag it was READ from (the yardstick
    # chain's), redirected onto the port's own; melee rows (shared by every weapon) dropped
    'catalog': {
        'table': 'balance_SAW_Halo4_to_Halo2.json',
        'weapon_tag': SAW + r'\saw',
        'port_tags': [(('weap', SMG + r'\smg'), SAW + r'\saw'),
                      (('weap', r'objects\weapons\rifle\assault_rifle\assault_rifle'), SAW + r'\saw'),
                      (('proj', SMG + r'\projectiles\smg_bullet'), SAW + r'\projectiles\saw_bullet'),
                      (('proj', r'objects\weapons\rifle\assault_rifle\projectiles\assault_rifle_bullet'),
                       SAW + r'\projectiles\saw_bullet'),
                      (('jpt!', SMG + r'\damage_effects\smg_bullet'), SAW + r'\damage_effects\saw_bullet')],
        'shared': [('jpt!', r'objects\weapons\damage_effects\strike_melee')],
        # step-4a re-check (user, 2026-10-23, the rework): two chain rows were wrong since 2026-09-24
        'value_overrides': {
            **{f: {'value': 80.0,
                   'note': "user 2026-10-23: the chain's x0.0533 (H4 AR 1500 -> H3 AR 80; Halo 3's AR is 5x "
                           "slower than its SMG) gave 16 wu/s -> Halo 4's SAW / AR (300 / 1500) x the H2 SMG's "
                           "400 = 80 (the AR port's speed)"}
               for f in ('Initial Velocity', 'Final Velocity')},
            # the SIBLING ratio (the AR's rule): the raw ratios put the minimum error (the SMG's 1.0,
            # no ratio from Halo 4's 0) above the cone's lower bound 0.16 -> all three take the upper
            # bound's x1.25
            **{f: {'value': v, 'note': "user 2026-10-23: the sibling ratio (the AR's rule) -- Halo 4's "
                                       "0 / 0.3-2.75 x the cone's upper-bound ratio 1.25"}
               for f, v in (('Minimum Error', 0.0), ('Error Angle', 0.375), ('Error Angle Max', 3.4375))}},
        'fp_animations': r'objects\characters\*\fp\weapons\rifle\fp_saw\fp_saw',
        # built at Halo 4's own 128 frames, the card takes it to the balanced 109
        'reload_mult': round(109.0 / 128.0, 6),
        'desc': ('%s carried from %s into Halo 2 with its own model, textures, sounds and its own '
                 'Halo 4 first-person animations for both species, balanced through the Assault '
                 'Rifle into Halo 3 and the SMG out of it.'),
    },

    # step 11 -- `python ai_firing_profile.py --h2-port saw` (H2_PORT_PLAN 0.5b): Halo 4's storm_lmg
    # entry name-for-name over the H2 SMG's (the yardstick)
    'firing_profile': {'from_game': 'Halo 4', 'from_map': r'halo4\maps\m020.map',
                       'from_weapon': r'objects\weapons\rifle\storm_lmg\storm_lmg',
                       'donor_weapon': SMG + r'\smg'},

    'backup': {'trees': [SAW],
               'extra': [H3EK + r'\storm_lmg_rm.xml', H3EK + r'\saw_3p_rm.xml']},
}
