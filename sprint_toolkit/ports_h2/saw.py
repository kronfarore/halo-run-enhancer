r"""The Halo 2 SAW -- the first Halo 2 port (Halo 4 storm_lmg on the cut GPMG, 2026-09-23/24),
DONE. Every constant the old h2_saw_*.py scripts carried lives here now; the h2_port_*.py tools
read it and regenerate the SAW's files byte-identically (H2_PORT_PLAN.md 0.2, the proof).
The complete example of a Halo 2 port config.
"""
B = '\\'
SAW = r'objects\weapons\rifle\saw'
H2EK = r'F:\SteamLibrary\steamapps\common\H2EK'
H3EK = r'F:\SteamLibrary\steamapps\common\H3EK'
NEW_HUD = r'ui\hud\bitmaps\new_hud'

PORT = {
    'order': 0,
    'name': 'SAW',
    'source': 'Halo 4',
    'status': 'done',
    'reservations': {
        'message_prefix': 'saw2',              # hud_messages ids saw2_* (h2_port_messages)
        'glyph': 0xE13D,                       # pickup icon codepoint, 8 English fonts
        'weapon_dir': SAW,
        'effects_dir': r'effects\objects\weapons\rifle\saw',
        'fp_graph': r'weapons\rifle\fp_saw\fp_saw',   # under objects\characters\<species>\fp\
        'hud': r'ui\hud\saw',
        'hud_bitmap_prefix': 'saw_',           # new_hud meters\saw_meter, backgrounds\saw_bkd, ...
        'sound_dir': r'sound\weapons\saw_port',
        'test_level': '03a_oldmombasa',
    },
    'donor': {'weapon': r'objects\weapons\rifle\gpmg\gpmg',
              'why': 'the cut GPMG: in no scenario, own FP model / HUD / message ids, an LMG'},
    'yardstick': {'pick': 'SMG',
                  'reason': 'user 2026-10-05: fields no card covers follow the SMG (the balance '
                            'chain H4 AR > H3 AR, H3 SMG > H2 SMG); balance_SAW_Halo4_to_Halo2.json',
                  'candidates': {}},

    # step 1 -- saw_to_jms_h2.py: the H4 render dump onto the GPMG's authored JMS
    'geometry': {
        'kind': 'h4_dump',
        'dump': H3EK + r'\storm_lmg_rm.xml',
        'data_dir': SAW,                       # data\<data_dir>\render\<world>.jms etc.
        'world': 'saw', 'fp': 'fp_saw',
        'donor_fp_jms': r'fp_gpmg\render\fp_gpmg.jms',      # under data\!extracted
        'donor_world_jms': r'gpmg\render\L5_gpmg.jms',
        'scale': 1.0,
        'part_material': {0: None, 1: 'saw_gun', 2: None, 3: 'saw_display'},
        'node_map': {0: 'frame gun', 1: 'frame magazine'},  # source skinned bone -> donor node
        'lift': None,                          # None = measured (FP mesh band onto the donor's)
        'fp_nudge': (0.0, 0.5, -1.0),          # Halo axes: X forward, Y left, Z up
        'muzzle_drop': 1.40,                   # the borrowed SMG effect's marker-below-bore
        'marker_from': {'primary_trigger': 'primary_trigger',
                        'primary ejection': 'primary_ejection'},
        'min_tris': 1000,
        # a SECOND first-person model per species (PORTING "one FP MODEL per species")
        'fp_species': {'dervish': {'sub': 'fp_saw_dervish', 'nudge': (0.0, 0.0, -0.75)}},
        'render': ['saw', r'saw\fp_saw', r'saw\fp_saw_dervish'],   # tool render <parent>\<x>
    },

    # step 2 -- h2_saw_textures.py
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
                        (r'objects\weapons\rifle\smg\bitmaps\smg_bump', 'Bungie SMG'),
                        (r'objects\weapons\fixed\h_turret_mp\bitmaps\h_turret_mp_gun_bump', 'Bungie turret')],
    },

    # step 3 -- h2_saw_weapon.py
    'weapon': {
        'weapon': SAW + r'\saw.weapon',
        'clones': [(r'objects\weapons\rifle\gpmg\gpmg.weapon', SAW + r'\saw.weapon'),
                   (r'objects\vehicles\h_turret_ap\weapon\h_turret_ap_bullet.projectile',
                    SAW + r'\projectiles\saw_bullet.projectile'),
                   (r'objects\vehicles\h_turret_ap\damage_effects\h_turret_ap_bullet.damage_effect',
                    SAW + r'\damage_effects\saw_bullet.damage_effect'),
                   (r'objects\vehicles\h_turret_ap\damage_effects\h_turret_ap_trigger.damage_effect',
                    SAW + r'\damage_effects\saw_trigger.damage_effect'),
                   (r'effects\objects\weapons\rifle\smg\fire_bullet.effect',
                    r'effects\objects\weapons\rifle\saw\saw_fire.effect')],
        # (tag, class, the path it names now, what it should name, why)
        'wiring': [
            (SAW + r'\saw.weapon', 'hlmt', r'objects\weapons\rifle\gpmg\gpmg', SAW + r'\saw', 'world model'),
            (SAW + r'\saw.weapon', 'mode', r'objects\weapons\rifle\gpmg\fp_gpmg\fp_gpmg',
             SAW + r'\fp_saw\fp_saw', 'first person model, Master Chief'),
            (SAW + r'\saw.weapon', 'mode', r'objects\weapons\rifle\sniper_rifle\fp_sniper_rifle\fp_sniper_rifle',
             SAW + r'\fp_saw\fp_saw', 'first person model, Dervish -- the donor pointed this at the SNIPER RIFLE'),
            (SAW + r'\saw.weapon', 'proj', r'objects\vehicles\h_turret_ap\weapon\h_turret_ap_bullet',
             SAW + r'\projectiles\saw_bullet', 'projectile'),
            (SAW + r'\saw.weapon', 'jpt!', r'objects\vehicles\h_turret_ap\damage_effects\h_turret_ap_trigger',
             SAW + r'\damage_effects\saw_trigger', 'firing damage'),
            (SAW + r'\projectiles\saw_bullet.projectile', 'jpt!',
             r'objects\vehicles\h_turret_ap\damage_effects\h_turret_ap_bullet',
             SAW + r'\damage_effects\saw_bullet', 'impact damage'),
            (SAW + r'\saw.weapon', 'effe', r'effects\objects\weapons\rifle\gpmg\gpmg_gun_fire',
             r'effects\objects\weapons\rifle\saw\saw_fire', 'firing effect -- was the Warthog chaingun, far too big'),
            (SAW + r'\saw.weapon', 'ligh', r'objects\vehicles\h_turret_ap\weapon\muzzle_flash_turret_ap',
             r'effects\objects\weapons\rifle\smg\smg_muzzle_flash', 'muzzle flash light -- the turret one lit up the room'),
        ],
        'shared': [(r'ui\hud\gpmg', 'the donor HUD -- the reason this donor was chosen'),
                   ('the SMG particles inside saw_fire', "the effect tag is the port's, the particles in it are the SMG's"),
                   (r'objects\weapons\damage_effects\*_melee', 'shared by every Halo 2 weapon'),
                   (r'sound\weapons\sniper_rifle\sniper_ammo', 'pickup sound')],
    },

    # step 4 -- h2_saw_numbers.py: (tag, field, block, element, nth, value)
    'numbers': {
        'numbers': [
            (SAW + r'\saw.weapon', 'rounds loaded maximum', 'magazines', 0, 0, 72),
            (SAW + r'\saw.weapon', 'rounds reloaded', 'magazines', 0, 0, 72),
            (SAW + r'\saw.weapon', 'rounds total initial', 'magazines', 0, 0, 216),
            (SAW + r'\saw.weapon', 'rounds total maximum', 'magazines', 0, 0, 288),
            (SAW + r'\saw.weapon', 'rounds per second', 'barrels', 0, 0, [20.0, 20.0]),
            (SAW + r'\saw.weapon', 'minimum error', 'barrels', 0, 1, 0.0),
            (SAW + r'\saw.weapon', 'error angle', 'barrels', 0, 1, [0.3, 2.75]),
            (SAW + r'\damage_effects\saw_bullet.damage_effect', 'damage lower bound', '', 0, 0, 7.5),
            (SAW + r'\damage_effects\saw_bullet.damage_effect', 'damage upper bound', '', 0, 0, [7.5, 7.5]),
            (SAW + r'\saw.weapon', 'deceleration time', 'barrels', 0, 1, 0.49),
            (SAW + r'\damage_effects\saw_bullet.damage_effect', 'instantaneous acceleration', '', 0, 0, 0.15),
        ],
        'skipped': [
            ('fire recovery time', '0.0666667 in Halo 4, which caps a weapon at 15 rounds a second -- '
                                   'it would fight the 20 this one is being given. Halo 2 paces automatic '
                                   'fire with rounds per second.'),
            ('maximum range 75', "Halo 2 does it with the projectile's air damage range, already 0..80 -- "
                                 'near enough that changing it is noise.'),
            ('damage reporting type', 'still says "human turret", which decides which medal a kill counts '
                                      'as. Cosmetic, and it belongs with the HUD work rather than here.'),
        ],
    },

    # step 4b -- h2_saw_yardstick.py (the SMG yardstick, user 2026-10-05): kept in the old
    # script's own form; it is a one-time move whose guards make a re-run a no-op
    'yardstick_fields': {'script': 'h2_saw_yardstick.py', 'yardstick_weapon': r'objects\weapons\rifle\smg\smg'},

    # step 5 -- h2_saw_collision.py
    'collision': {
        'donor': r'objects\weapons\rifle\gpmg\gpmg',
        'port': SAW + r'\saw',
        'src': r'gpmg\collision\collision.JMS',          # under data\!extracted
        'out': SAW + r'\collision\saw.jms',               # under data
        'port_render_jms': SAW + r'\render\saw.jms',
        'donor_render_jms': r'gpmg\render\L5_gpmg.jms',   # under data\!extracted
        'max_growth': 1.25,
    },

    # step 7 -- h2_saw_meter.py (+ the backpack icon)
    'meter': {
        'donor_meter': NEW_HUD + r'\meters\battle_rifle_meter',
        'rel': NEW_HUD + r'\meters',
        'name': 'saw_meter',
        'donor_hud': r'ui\hud\gpmg',
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

    # step 7 -- h2_saw_hud_plate.py
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

    # step 7 -- h2_saw_reticle.py (Halo 4's crosshair, own one-image bitmap)
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

    # step 7 -- h2_saw_scope.py (the port does not zoom)
    'scope': {
        'rel': NEW_HUD + r'\scope_masks',
        'donor': NEW_HUD + r'\scope_masks\battle_rifle_scope_mask',
        'name': 'saw_blank',
        'hud': r'ui\hud\saw.new_hud_definition',
        'widgets': ('scope_mask', 'left_crosshair', 'right_crosshair', 'bottom_crosshair',
                    'top_crosshair', '2x', 'distance_meter'),
        'size': (8, 8),
    },

    # step 8 -- h2_saw_glyph.py
    'glyph': {
        'box': (160, 62),
        'model_3p': H3EK + r'\saw_3p_rm.xml',
        'tif': 'saw_h2_glyph.tif',
    },

    # step 8 -- h2_port_messages.py (gpmg_* -> saw2_*; the GPMG keeps its own lines)
    'messages': {
        'donor_prefix': 'gpmg', 'donor_icon': '&sentinel_grenade_weapon',
        'donor_name': 'GPMG', 'port_name': 'SAW',
        'weapon': SAW + r'\saw.weapon',
    },

    # step 9 -- h2_saw_animations.py
    'animations': {
        'weapon': SAW + r'\saw.weapon',
        'graphs': [(sp, r'objects\characters\%s\fp\weapons\rifle\fp_sniper_rifle\fp_sniper_rifle' % sp,
                    r'objects\characters\%s\fp\weapons\rifle\fp_saw\fp_saw' % sp)
                   for sp in ('masterchief', 'dervish')],
        'sounds': [(r'sound\weapons\sniper_rifle\sniper_reload', r'sound\weapons\smg\smg_reload'),
                   (r'sound\weapons\sniper_rifle\sniper_ready', r'sound\weapons\smg\smg_ready'),
                   (r'sound\weapons\sniper_rifle\sniper_posing', r'sound\weapons\smg\smg_posing_var0'),
                   (r'sound\weapons\sniper_rifle\sniper_melee_first', r'sound\weapons\smg\smg_melee1')],
        'untouched': r'objects\weapons\rifle\sniper_rifle\sniper_rifle.weapon',
    },
    # step 9 -- h2_anim_retime.py, as it was run (2026-09-24): the reload BUILT at the SAW's
    # own 128 frames (the card shortens it to 109); Chief interpolated, Dervish held translations
    'retime': {'runs': [(r'objects\characters\masterchief\fp\weapons\rifle\fp_saw\fp_saw', 'reloads', 128),
                        (r'objects\characters\dervish\fp\weapons\rifle\fp_saw\fp_saw', 'reloads', 128)]},

    # step 10 -- h2_saw_sounds.py
    'sounds': {
        'weapon': SAW + r'\saw.weapon',
        'fire_fx': r'effects\objects\weapons\rifle\saw\saw_fire.effect',
        'audio_key': 'SAW',                                 # port_volume.MARKER_DB / saw_port_sounds
        'sounds': {'saw_fire': ('fire', 'weapon_fire'), 'saw_dryfire': ('dryfire', 'weapon_empty'),
                   'saw_reload': ('foley:RELOAD', 'weapon_reload'), 'saw_ready': ('foley:READY', 'weapon_ready'),
                   'saw_melee1': ('foley:MELEE1', 'weapon_melee'),
                   'saw_pose1': ('foley:POSE1@%.6f' % (70 / 90.0), 'weapon_animation')},
        'repoint_fx': (r'sound\weapons\smg\fire', 'saw_fire'),
        'repoint_weapon': (r'sound\weapons\battle_rifle\dryfire', 'saw_dryfire'),
        'graph_sounds': (('smg_reload', 'saw_reload'), ('smg_ready', 'saw_ready'),
                         ('smg_melee1', 'saw_melee1'), ('smg_posing_var0', 'saw_pose1')),
        'graph_sound_dir': r'sound\weapons\smg' + B,
        'gain': {'saw_fire': -3.0, 'saw_dryfire': -3.0},
        'boost': {},
        'backup': r'E:\HaloBackups\H2EK_saw_before_sounds',
        'graph_backup': r'E:\HaloBackups\H2EK_saw_graphs_before_foley',
    },

    # residency: palette entry in every level's weapons resource (h2_port_residency.py). The
    # SAW also has one resident-only placement per level (put there 2026-10-01..04, before the
    # 128-placement cap was measured) -- new ports take the PALETTE ONLY (H2_PORT_PLAN 0.1)
    'residency': {'levels': 'all', 'placements': True},

    'test': {'level': '03a_oldmombasa'},

    # make_port_catalog_h2.py saw: every balance row names the tag it was READ from (the yardstick
    # chain's), redirected onto the port's own; melee rows (shared by every weapon) dropped
    'catalog': {
        'table': 'balance_SAW_Halo4_to_Halo2.json',
        'weapon_tag': SAW + r'\saw',
        'port_tags': [(('weap', r'objects\weapons\rifle\smg\smg'), SAW + r'\saw'),
                      (('weap', r'objects\weapons\rifle\assault_rifle\assault_rifle'), SAW + r'\saw'),
                      (('proj', r'objects\weapons\rifle\smg\projectiles\smg_bullet'), SAW + r'\projectiles\saw_bullet'),
                      (('proj', r'objects\weapons\rifle\assault_rifle\projectiles\assault_rifle_bullet'),
                       SAW + r'\projectiles\saw_bullet'),
                      (('jpt!', r'objects\weapons\rifle\smg\damage_effects\smg_bullet'), SAW + r'\damage_effects\saw_bullet')],
        'shared': [('jpt!', r'objects\weapons\damage_effects\strike_melee')],
        'fp_animations': r'objects\characters\*\fp\weapons\rifle\fp_saw\fp_saw',
        # built at the SAW's own 128 frames, the card takes it to the balanced 109
        'reload_mult': round(109.0 / 128.0, 6),
        'desc': ('%s carried from %s into Halo 2, built on the cut GPMG and balanced through '
                 'the Assault Rifle into Halo 3 and the SMG out of it. It owns its own '
                 'first-person animations, so its reload can be retimed.'),
    },

    'firing_profile': None,          # no Halo 2 Armed card yet (H2_PORT_PLAN 0.5)

    'backup': {'trees': [r'objects\weapons\rifle\saw'],
               'extra': [H3EK + r'\storm_lmg_rm.xml']},
}
