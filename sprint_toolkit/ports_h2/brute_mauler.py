r"""Mauler into Halo 2 (H2_PORT_PLAN.md wave A (Halo 3), #A4) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

MA = r'objects\weapons\pistol\excavator'       # the source's folder (H3EK) AND the port's (H2EK)
MAG = r'objects\weapons\pistol\magnum'          # the donor (H2EK)
SG = r'objects\weapons\rifle\shotgun'           # the yardstick (H2EK): its pellet projectile + damage
FX = r'effects\objects\weapons\pistol\excavator'   # the reserved effects folder
NEW_HUD = r'ui\hud\bitmaps\new_hud'
import os as _os
# the Halo 3 world render model's export (h1_fp_retarget.export_xml's cache; regenerable): the
# silhouette the HUD plate, backpack icon and pickup glyph are drawn from
H3_RM_XML = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'out', 'h3_export',
                          'objects~weapons~pistol~excavator~excavator.render_model.xml')
H3SND = r'data\sound\weapons'           # source folders in MCC's halo3 sfx.fsb (.info)
H2EK = r'F:\SteamLibrary\steamapps\common\H2EK'
# Halo 3's self-illumination colour of the body / metal shaders: 191 / 60 / 30 (orange-red, x8 ->
# 4 with bloom; Halo 1's A6 read it white-hot at the windows). Halo 2 draws its self_illum_map as
# it is, so the grey mask is TINTED (the Spiker's rule) in Halo 1's glow orange
ORANGE = (1.0, 0.45, 0.18)

PORT = {
    'order': 4,
    'wave': 'A4',
    'name': 'Mauler',
    'source': 'Halo 3',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\pistol\\excavator\\excavator',
    'reservations': {
        'message_prefix': 'mau2',
        'glyph': 0xE141,
        'weapon_dir': 'objects\\weapons\\pistol\\excavator',
        'effects_dir': 'effects\\objects\\weapons\\pistol\\excavator',
        'fp_graph': 'weapons\\pistol\\fp_excavator\\fp_excavator',
        'hud': 'ui\\hud\\brute_mauler',
        'hud_bitmap_prefix': 'brute_mauler_',
        'sound_dir': 'sound\\weapons\\brute_mauler_port',
    },
    # step 4a (user, 2026-10-28): the H2 MAGNUM, not the stub's shotgun. The block shape decides:
    # pellets and the error cone are FIELDS (written onto any barrel), the dual structures are not
    # -- the shotgun has none (no dual HUD / messages / animations, two-handed, plus the shell
    # baggage Halo 1 stripped: 'every round must be chambered', weapon type 'shotgun'). The SMG
    # (the Spiker's) has them but spews and its FP graph carries the single-wield left-hand IK
    # (drop_ik). The magnum: latch, ONE magazine reloaded whole (rounds reloaded = loaded), one-
    # handed, 'can be dual wielded', a dual HUD, and fp_magnum has NO IK block (drop_ik n/a)
    'donor': {'weapon': 'objects\\weapons\\pistol\\magnum\\magnum', 'message_prefix': 'magnum',
              'why': ("latch, whole-magazine reload, one-handed, dual flag + dual HUD + dual lines, "
                      "fp_magnum has no left-hand IK; pellets / error = fields (the shotgun pellet's "
                      "numbers written on); user 4a 2026-10-28")},
    'yardstick': {
        # step 4a, user 2026-10-28: balance_Mauler_Halo3_to_Halo2.json (balance_port.py Mauler
        # "Halo 3" "Halo 2" --hop "Shotgun:Halo 3>Halo 2"); TTK: the session's mauler_ttk_4a
        # (h2_spiker_ttk_4a's method on the H2 shotgun's damage groups)
        'pick': 'Shotgun',
        'reason': ("user 2026-10-28: the same projectile family in Halo 3 (15-pellet 7.5 deg cone, "
                   "bullet_slow, distance falloff: 15 x 7 vs 15 x 10) -- the Pistol has no pellets, "
                   "cone or falloff (its rows degenerate: 1 x 3.73 at 5.3/s). Balanced: 10 pellets "
                   "(the H2 shotgun's 10 x 15/15) x 11.55 = 115.5 a shot (H2 shotgun 165 x 0.7), lower "
                   "2.5 over 6.25 -> 10 wu, recovery 0.75 s, magazine 10 / initial 20 / maximum 50 "
                   "(the ratio's 33 x1.5: the DUAL-WIELD CARRY RULE, the yardstick cannot be dual "
                   "wielded), the reload Halo 3's whole magazine (shell 0.4 = 0.4: x1), error 10-12 / "
                   "min 4 (both cones 7.5), velocity 120, range 10.67, autoaim 8 / 7.64, magnetism "
                   "40 / 1.27, dual wield damage scale 0.7 x 0.833 (the SMG's H3 -> H2, as the Spiker) "
                   "= 0.583. Legendary TTK (body, every pellet): Elite 2 shots 0.75 s, Brute 5 / 3.0 s "
                   "(H2 shotgun 1 / 4-3.0 s, magnum 1.80 / 6.2 s)"),
        'pellets': "user: 10 x 11.55 (the ratio's count), not Halo 3's 15 x 7.7",
        'dual': 'user: x1.5 carry (33 -> 50) + dual wield damage scale 0.583',
        'melee': ('own clone of strike_melee x Halo 3 cut_melee 72 / strike_melee 70 (20.57-61.71; '
                  "the blade -- the Spiker's rule)"),
        'candidates': {
            'provisional': 'Shotgun',
            'alternatives': ['Pistol'],
            'direct': 'none',
            'peers': ['Shotgun', 'Energy Blade', 'Magnum'],
            'why': 'magazine 5 latch, pellets, dual-wieldable one-hand shotgun (H1 pick)',
        },
    },
    # step 1 -- h2_port_geometry.py kind 'h3': the Halo 3 render models on their OWN skeletons
    # (world: gun alone; FP: gun, barrel, drum, piston) -- the Mauler's own FP animations drive them.
    # DUAL CHECK (the Spiker's fp_root_identity): Halo 3 binds fp_excavator's root `gun` AT IDENTITY
    # already (rotation 0,0,0,-1; the Spiker's turned 180 deg), so the left gun mirrors right as is
    'geometry': {
        'kind': 'h3',
        'world_rm': MA + r'\excavator.render_model',
        'fp_rm': MA + r'\fp_excavator\fp_excavator.render_model',
        'data_dir': MA,
        'world': 'excavator', 'fp': 'fp_excavator',
        # Halo 3's four shaders all sample `excavator` (+ bump, + the illum mask): the body, the
        # metal drum (lit windows), the chrome blade (shiny), the rubber grip (dull) -- Halo 1's A6
        'materials': {'excavator': 'mauler', 'excavator_metal': 'mauler_metal',
                      'excavator_shiny': 'mauler_shiny', 'excavator_dull': 'mauler_dull'},
        # the world .model is the BR's clone (the AR / Spiker shape: no world-model graph -- the
        # magnum's names one for its own slide): its variants name permutation `base`, region `gun`
        'world_permutation': 'base', 'world_region': 'gun',
        # Halo 3 has no ejection port, no left_hand (one-handed: left_hand_cyborg is its 3P grip),
        # no flashlight marker (Halo 2's flashlight is the biped's); stow anchor unused
        'markers': {'primary_trigger': 'primary_trigger'},
        'muzzle_drop': 0.0,
        'ground_point': {'rot': (0.7071068883, -1.8e-09, -7.42e-08, -0.7071067095)},   # the SMG's
        'render': ['excavator', r'excavator\fp_excavator'],
    },

    # step 2 -- h2_port_textures.py kind 'h3': Halo 3's own maps; shaders reseeded from Bungie's
    # BRUTE weapons (the Spiker's seeds): the gravity hammer's `hammer` (tex_bump_env_illum, a
    # SEPARATE self_illum_map) for the lit body / drum / blade, the Brute Shot's own (tex_bump_env)
    # for the grip. The grey illum mask TINTED orange, soft glows (the Spiker's Armed-boot rule)
    'textures': {
        'kind': 'h3',
        'rel': MA + r'\bitmaps',
        'shaders_dir': MA + r'\shaders',
        'bump_gain': 1.0,                      # the AR's (user: 1.6 read 'rough')
        'bitmaps': [(MA + r'\bitmaps\excavator.bitmap', 'mauler',
                     r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot', 'color', None),
                    (MA + r'\bitmaps\excavator_bump.bitmap', 'mauler_bump',
                     r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot_bump', 'bump_snorm', None),
                    (MA + r'\bitmaps\excavator_illum.bitmap', 'mauler_illum',
                     r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_illum',
                     ('tint', ORANGE, 0, 1.5), None)],
        'shaders': [
            (name, r'objects\weapons\melee\gravity_hammer\shaders\hammer',
             {r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer': MA + r'\bitmaps\mauler',
              r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_bump': MA + r'\bitmaps\mauler_bump',
              r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_illum': MA + r'\bitmaps\mauler_illum'})
            for name in ('mauler', 'mauler_metal', 'mauler_shiny')] + [
            ('mauler_dull', r'objects\weapons\support_low\brute_shot\shaders\brute_shot',
             {r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot': MA + r'\bitmaps\mauler',
              r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot_bump': MA + r'\bitmaps\mauler_bump',
              r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot_bump_active_camo': MA + r'\bitmaps\mauler_bump'})],
        'report_rows': [(MA + r'\bitmaps\mauler_bump', 'the port'),
                        (r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot_bump', 'Bungie Brute Shot')],
    },

    # step 3 -- h2_port_weapon.py: the H2 MAGNUM's weapon (step 4a's donor: latch, one magazine
    # reloaded whole, DUAL-WIELDABLE, 3P class `pistol` -- Halo 3's own -- kept), the world .model
    # from the BATTLE RIFLE's (the AR / Spiker shape: no world-model graph -- the magnum's names
    # one for its slide). The PELLET is the yardstick SHOTGUN's projectile + impact damage (10
    # pellets a shot are a barrel field), its blast the shotgun's firing effect / light / trigger
    # damage. The BLADE melee: an own clone of strike_melee named by both of its references
    'weapon': {
        'weapon': MA + r'\excavator.weapon',
        'clones': [(MAG + r'\magnum.weapon', MA + r'\excavator.weapon'),
                   (r'objects\weapons\rifle\battle_rifle\battle_rifle.model', MA + r'\excavator.model'),
                   (SG + r'\projectiles\shotgun_bullet.projectile', MA + r'\projectiles\excavator_shard.projectile'),
                   (SG + r'\damage_effects\shotgun_bullet.damage_effect', MA + r'\damage_effects\excavator_shard.damage_effect'),
                   (SG + r'\damage_effects\shotgun_trigger.damage_effect', MA + r'\damage_effects\excavator_trigger.damage_effect'),
                   (r'objects\weapons\damage_effects\strike_melee.damage_effect', MA + r'\damage_effects\excavator_melee.damage_effect'),
                   (r'effects\objects\weapons\rifle\shotgun\shotgun_firing.effect', FX + r'\excavator_fire.effect'),
                   (r'effects\objects\weapons\rifle\shotgun\muzzle_flash.light', FX + r'\excavator_muzzle_flash.light'),
                   (r'effects\materials\objects\weapons\magnum.material_effects', FX + r'\excavator.material_effects'),
                   (r'effects\materials\objects\weapons\shotgun.material_effects', FX + r'\excavator_shard.material_effects')],
        # BOOT 1 (user, 05b: 'the glowing lights slowly come online ... and then fade back out'): the
        # seed (Tartarus's hammer shader) animates self_illum_color as a COSINE over 8 s through four
        # colours (BGRA 77 3c 00 dark blue, black, black, ff c1 84 light blue) -- from dark. Halo 3's
        # Mauler: self_illum_intensity periodic WANDER between 4 and 8 over 8 s (always lit, 50-100 %),
        # its colour constant. Halo 2's function (type 3 periodic, byte 2 = the periodic shape, 10 =
        # wander, as Halo 3's) -> wander, colour 0 half grey, 1-3 white: whichever pair it blends, the
        # (already orange-tinted) mask reads 50-100 %. In the three lit shaders; the textures step
        # RESEEDS them -- run this step after it
        'byte_edits': [(MA + r'\shaders\%s.shader' % s,
                        '03200200773c00000000000000000000ffc18400',
                        '03200a0080808000ffffff00ffffff00ffffff00')
                       for s in ('mauler', 'mauler_metal', 'mauler_shiny')],
        'wiring': [
            (MA + r'\excavator.weapon', 'hlmt', MAG + r'\magnum', MA + r'\excavator', 'world model'),
            (MA + r'\excavator.model', 'mode', r'objects\weapons\rifle\battle_rifle\battle_rifle',
             MA + r'\excavator', 'the world render model (it and the collision pool ONE path)', {'nth': 0}),
            (MA + r'\excavator.weapon', 'mode', MAG + r'\fp_magnum\fp_magnum',
             MA + r'\fp_excavator\fp_excavator', 'first person model, Master Chief', {'nth': 0}),
            (MA + r'\excavator.weapon', 'mode', MAG + r'\fp_magnum\fp_magnum',
             MA + r'\fp_excavator\fp_excavator', 'first person model, Dervish (one Halo 3 FP model)', {'nth': 0}),
            (MA + r'\excavator.weapon', 'jmad', r'objects\characters\masterchief\fp\weapons\pistol\fp_magnum\fp_magnum',
             r'objects\characters\masterchief\fp\weapons\pistol\fp_excavator\fp_excavator',
             "Master Chief FP graph: the Mauler's own Halo 3 animations (single + dual)"),
            (MA + r'\excavator.weapon', 'jmad', r'objects\characters\dervish\fp\weapons\pistol\fp_magnum\fp_magnum',
             r'objects\characters\dervish\fp\weapons\pistol\fp_excavator\fp_excavator',
             "Dervish FP graph: the Mauler's own Halo 3 animations (single + dual)"),
            (MA + r'\excavator.weapon', 'proj', MAG + r'\projectiles\magnum_bullet',
             MA + r'\projectiles\excavator_shard', 'projectile (the shotgun pellet clone)'),
            (MA + r'\projectiles\excavator_shard.projectile', 'jpt!', SG + r'\damage_effects\shotgun_bullet',
             MA + r'\damage_effects\excavator_shard', 'impact damage'),
            (MA + r'\excavator.weapon', 'jpt!', MAG + r'\damage_effects\magnum_trigger',
             MA + r'\damage_effects\excavator_trigger', "firing damage (the shotgun's kick)"),
            (MA + r'\excavator.weapon', 'jpt!', r'objects\weapons\damage_effects\strike_melee',
             MA + r'\damage_effects\excavator_melee', 'the blade melee (own, x72/70)', {'every': True}),
            (MA + r'\excavator.weapon', 'effe', r'effects\objects\weapons\pistol\magnum\fire_bullet',
             FX + r'\excavator_fire', "firing effect (the shotgun's blast)"),
            (MA + r'\excavator.weapon', 'ligh', r'effects\objects\weapons\pistol\magnum\muzzle_flash',
             FX + r'\excavator_muzzle_flash', 'muzzle flash light'),
            (MA + r'\excavator.weapon', 'foot', r'effects\materials\objects\weapons\magnum',
             FX + r'\excavator', 'material effects (the weapon: drops)'),
            (MA + r'\projectiles\excavator_shard.projectile', 'foot', r'effects\materials\objects\weapons\shotgun',
             FX + r'\excavator_shard', 'impact material effects (the pellet)'),
            # the HUD is the magnum's clone (step 7: dual-wield shaped)
            (MA + r'\excavator.weapon', 'nhdt', r'ui\hud\magnum', r'ui\hud\brute_mauler', 'its own HUD (step 7)'),
        ],
        'shared': [(r'the particles inside excavator_fire', "the shotgun's (Halo 3 particles do not port)"),
                   (r'objects\weapons\damage_effects\strike_melee_response, smash_melee(_response)',
                    "the melee's responses + the second hit, shared by every Halo 2 weapon"),
                   (r'objects\powerups\pistol_ammo\pistol_ammo', "the magnum's ammo pickup item (unused in campaign)"),
                   (r'sound\weapons\impacts_riccs\bullet_flyby_long', "the pellet's fly-by (until step 10)"),
                   (r'effects\bitmaps\*', "the magnum's own weapon bitmaps")],
    },

    # step 4 -- h2_port_numbers.py: Halo 3's OWN values (DEFAULT; the balanced rows are the
    # catalog's, step 4a's Shotgun table). h3_weapon_values.py pistol\excavator\excavator
    'numbers': {
        'numbers': [
            # flags'': the magnum's, 'can be dual wielded' KEPT (Halo 3's Mauler is dual-wieldable)
            (MA + r'\excavator.weapon', 'autoaim angle', '', 0, 0, 8.0),
            (MA + r'\excavator.weapon', 'autoaim range', '', 0, 0, 7.0),
            (MA + r'\excavator.weapon', 'magnetism angle', '', 0, 1, 16.0),
            (MA + r'\excavator.weapon', 'magnetism range', '', 0, 1, 7.0),
            (MA + r'\excavator.weapon', 'rounds loaded maximum', 'magazines', 0, 0, 5),
            (MA + r'\excavator.weapon', 'rounds reloaded', 'magazines', 0, 0, 5),     # the WHOLE magazine
            (MA + r'\excavator.weapon', 'rounds total initial', 'magazines', 0, 0, 10),
            (MA + r'\excavator.weapon', 'rounds total maximum', 'magazines', 0, 0, 25),
            # rate 0 / 0 paced by the fire recovery (the magnum's 0.1, Halo 3's 0.75)
            (MA + r'\excavator.weapon', 'fire recovery time', 'barrels', 0, 0, 0.75),
            # PELLETS: Halo 3 keeps them on the PROJECTILE (conical spread 3 x 5 = 15, 7.5 deg);
            # Halo 2 on the BARREL (projectiles per shot) spread by the barrel's error cone. The
            # cone: Halo 3's 7.5 = its shotgun's 7.5, so Halo 2's own shotgun cone (min 4, 10-12) --
            # on the SINGLE (nth 1) AND the DUAL error (nth 0): Halo 3's dual weapon error (0) is a
            # barrel error, the pellets' cone sits on the projectile and holds in both hands
            # the zero fields (the magnum reads 0 there) pinned by their non-zero neighbour: Halo 2's
            # barrel runs dual wield damage scale, distribution function (2), projectiles per shot (2),
            # distribution angle, minimum error', error angle' -- the dual error before it
            (MA + r'\excavator.weapon', 'projectiles per shot', 'barrels', 0, 0, 15),
            (MA + r'\excavator.weapon', 'minimum error', 'barrels', 0, 1, 4.0, {'anchor': ('projectiles per shot', 6)}),
            (MA + r'\excavator.weapon', 'error angle', 'barrels', 0, 1, [10.0, 12.0]),
            (MA + r'\excavator.weapon', 'minimum error', 'barrels', 0, 0, 4.0, {'anchor': ('projectiles per shot', -18)}),
            (MA + r'\excavator.weapon', 'error angle', 'barrels', 0, 0, [10.0, 12.0], {'anchor': ('projectiles per shot', -14)}),
            (MA + r'\excavator.weapon', 'dual wield damage scale', 'barrels', 0, 0, 0.7, {'anchor': ('projectiles per shot', -6)}),
            # first-person placement: the AR's -0.01, 0, -0.03 (A1 observation 4); boot 1 on 05b (user):
            # '2 units down, 0.5 units to the right' (1 unit = 0.01 wu; +y is left)
            (MA + r'\excavator.weapon', 'first person weapon offset', '', 0, 0, [-0.01, -0.005, -0.05]),
            # the pellet: 480 wu/s, range 8, falloff 2.5 -> 5 (to the lower bound)
            (MA + r'\projectiles\excavator_shard.projectile', 'initial velocity', '', 0, 0, 480.0),
            (MA + r'\projectiles\excavator_shard.projectile', 'final velocity', '', 0, 0, 480.0),
            (MA + r'\projectiles\excavator_shard.projectile', 'maximum range', '', 0, 0, 8.0),
            (MA + r'\projectiles\excavator_shard.projectile', 'air damage range', '', 0, 0, [2.5, 5.0]),
            (MA + r'\damage_effects\excavator_shard.damage_effect', 'damage lower bound', '', 0, 0, 1.5),
            (MA + r'\damage_effects\excavator_shard.damage_effect', 'damage upper bound', '', 0, 0, [7.0, 7.0]),
            (MA + r'\damage_effects\excavator_shard.damage_effect', 'instantaneous acceleration', '', 0, 0, 0.1),
            # the BLADE (user, 4a): own melee, Halo 3's cut_melee 72 flat (strike_melee 70 / H2 20-60)
            (MA + r'\damage_effects\excavator_melee.damage_effect', 'damage lower bound', '', 0, 0, 72.0),
            (MA + r'\damage_effects\excavator_melee.damage_effect', 'damage upper bound', '', 0, 0, [72.0, 72.0]),
        ] + [
            # step 4b (port_field_audit.py --port h2:brute_mauler, list 2: the ratio H3 Mauler / H3
            # Shotgun x the H2 Shotgun; list 4: both Halo 3 weapons agree -> the H2 Shotgun's)
            (MA + r'\excavator.weapon', 'bounding radius', '', 0, 0, 0.177778),            # 0.2 / 0.225 x 0.2
            (MA + r'\excavator.weapon', 'illumination recovery time', 'barrels', 0, 0, 0.1),   # both 0.1
        ] + [
            # THE DUAL READY's ARM FLAGS (after step 9: a re-import keeps them, a --reseed resets them).
            # Halo 3's dual ready cues a LEFT and a RIGHT sound; Halo 2 plays a dual animation once per
            # arm and filters each sound reference by its flags. The plasma pistol seed has three left
            # / three right slots (all taken: dual reload + two dual posings) -- the dual ready pair sits
            # on two unflagged single slots (4 overheat_exit, 14 dual_ready), so each gets its arm.
            # Elements are 20 bytes; anchored on a neighbour's non-zero flags (pin anchor_index)
            (r'objects\characters\%s\fp\weapons\pistol\fp_excavator\fp_excavator.model_animation_graph' % sp,
             'flags', 'sound references', slot, 0, arm, {'anchor': ('flags', delta, neighbour)})
            for sp in ('masterchief', 'dervish')
            for slot, arm, delta, neighbour in ((4, 2, -20, 5), (14, 4, 20, 13))
        ] + [
            # the HUD (the magnum's clone, step 7 -- run this step after a HUD rebuild) draws the
            # magnum's HEADSHOT (widget 7, [Y] autoaim-headshot) and WEAK-SPOT (8, [Y] autoaim-
            # vulnerable) indicators inside the crosshair: a pellet weapon has neither (Halo 3's
            # Mauler) -- each widget's [N] condition = its own [Y] one, never shown (the Flamethrower's)
            (r'ui\hud\brute_mauler.new_hud_definition', '[N] extra flags', 'bitmap widgets', 8, 0, 25),
            (r'ui\hud\brute_mauler.new_hud_definition', '[N] extra flags', 'bitmap widgets', 7, 0, 4,
             {'anchor': ('[Y] extra flags', 8)}),
        ],
        'skipped': [
            ('reload time', "the magazine's reload time does not drive the player's reload (the SAW, user): "
                            "the Mauler's own Halo 3 animation does"),
        ],
    },
    # step 5 -- h2_port_collision.py: the BATTLE RIFLE's authored hull (the world .model's donor)
    # scaled per axis to the Mauler's render mesh; the hull's nodes (gun, magazine, OpHandle,
    # safety) are not the Mauler's (gun alone): the hull takes the render's
    'collision': {
        'donor': r'objects\weapons\rifle\battle_rifle\battle_rifle',
        'port': MA + r'\excavator',
        'src': r'battle_rifle\collision\battle_rifle_collision.jms',     # under data\!extracted
        'out': MA + r'\collision\excavator.jms',                         # under data
        'port_render_jms': MA + r'\render\excavator.jms',
        'donor_render_jms': r'battle_rifle\render\battle_rifle_L5.jms',
        'max_growth': 1.25,
        'nodes_from_render': True,
    },

    # step 7 -- the HUD: a clone of the MAGNUM's (DUAL-WIELD shaped: the plate named x4, the meter
    # x2; it also carries the magnum's headshot / weak-spot crosshair widgets -- switched off in step
    # 4, the Flamethrower's rule), Halo 3's own five pips (chud excavator: ballistic_meters #13, a
    # 36 x 58 tab at a 65 px pitch -- Halo 1's A6) on the magnum meter's 198 x 28 canvas, 16 x 26 so
    # the tabs fit its height; TEN pips (boot 1, user: 'why 5 and not 10?' -- 5 was Halo 3's DEFAULT
    # magazine; Balanced holds 10, a pip a round; Original's 5 rounds = 2 pips a round), the plate's
    # every image repainted, Halo 3's crosshair (hud_reticles #12)
    'meter': {
        'donor_meter': NEW_HUD + r'\meters\magnum_meter',
        'rel': NEW_HUD + r'\meters',
        'name': 'brute_mauler_meter',
        'donor_hud': r'ui\hud\magnum',
        'port_hud': r'ui\hud\brute_mauler',
        'weapon': MA + r'\excavator.weapon',
        'rounds': 10, 'rows': 1,
        'canvas': (198, 28), 'tick_w': 16,
        'tick_art': {'h3': ('ballistic_meters', 13), 'h': 26},
        'backpack': NEW_HUD + r'\backpack_weapons',
        'backpack_port': NEW_HUD + r'\brute_mauler_backpack',
        'backpack_size': (62, 30),
        'model_3p': H3_RM_XML,
        'preview': 'brute_mauler_meter_preview.png',
    },
    'hud_plate': {
        'rel': NEW_HUD + r'\backgrounds',
        'donor': NEW_HUD + r'\backgrounds\magnum_bkd',
        'other': NEW_HUD + r'\backgrounds\smg_bkd',        # the other dual plate: same 8 shapes
        'name': 'brute_mauler_bkd',
        'hud': r'ui\hud\brute_mauler',
        'model_3p': H3_RM_XML,
        'fallback_box': (105, 191, 5, 34),
        'stretch': 1.4,
        'all_images': {'dim': {4: 0, 5: 1, 6: 2, 7: 3}},
    },
    'reticle': {
        'rel': NEW_HUD + r'\crosshairs',
        'donor': NEW_HUD + r'\crosshairs\hud_reticles',
        'donor_sequence': 8,                 # the magnum's fullscreen crosshair (half / quarter 30)
        'name': 'brute_mauler_reticle',
        'hud': r'ui\hud\brute_mauler',
        'footprint': 1.0,
        # Halo 3's ON-SCREEN size (the AR's rule, user boot 2): the AR's sprite #0 (ink 110) drew
        # 72 px at 1080p = target_ink 64; the Mauler's #12 (ink 160) -> 64 x 160 / 110 = 93
        'h3_art': {'sheet': 'hud_reticles', 'sequence': 12, 'yardstick': 3, 'target_ink': 93},
        'preview': 'brute_mauler_reticle_preview.png',
    },

    # step 8 -- the pickup icon at U+E141 by the H2 ICON RULE (untinted: white lines over a grey
    # body, Bungie's 160 x 62), and the messages (the magnum's mp_* -> mau2_*: a longer prefix, the
    # dual lines included; 'a Magnum' -> 'a Mauler')
    'glyph': {
        # boot 1 (user: 'a lot of free space in the icon from the text'): the Mauler is short and tall,
        # so at Bungie's 62 px height its ink spans 76 of the 160 px advance -- the box hugs it
        'box': (84, 62),
        'model_3p': H3_RM_XML,
        'tif': 'mauler_h2_glyph.tif',
        'colour': (255, 255, 255),
        'style': {'line': (255, 255, 255), 'body': (153, 153, 153)},
    },
    'messages': {
        'donor_prefix': 'mp', 'donor_icon': '&magnum',
        'donor_name': 'Magnum', 'port_name': 'Mauler',
        'names': [('a Magnum', 'a Mauler'), ('Magnum', 'Mauler')],
        'weapon': MA + r'\excavator.weapon',
    },

    # step 10 -- h2_port_sounds.py: Halo 3's OWN sounds from MCC's halo3 sfx.fsb (render_h3_bank,
    # 48 kHz at their native level), classic Opus. Halo 3's Mauler: a one-shot fire (3 permutations)
    # + its far layer; single AND DUAL (left / right) ready, reload, posing; melee. Its pickup, dry
    # fire and drops are Halo 3's MAGNUM's (the Mauler names them) -- rendered as the port's own; its
    # pellets fly by on Halo 3's bullet_flyby_long. The graph (plasma pistol seed) cues 15 slots
    'sounds': {
        'weapon': MA + r'\excavator.weapon',
        'fire_fx': FX + r'\excavator_fire.effect',
        'audio': _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'out',
                               'h2_sounds', 'brute_mauler'),
        'audio_key': 'Mauler',
        'h3_bank': {'mau_fire': [H3SND + r'\excavator\excavator_fire'],
                    'mau_fire_lod': [H3SND + r'\excavator\excavator_lod_far'],
                    'mau_dryfire': [H3SND + r'\magnum\magnum_dryfire'],
                    'mau_ammo': [H3SND + r'\magnum\magnum_ammo'],
                    'mau_reload': [H3SND + r'\excavator\excavator_fp\excavator_reload'],
                    'mau_ready': [H3SND + r'\excavator\excavator_fp\excavator_ready'],
                    'mau_melee': [H3SND + r'\excavator\excavator_fp\excavator_melee'],
                    'mau_pose': [H3SND + r'\excavator\excavator_fp\excavator_pose'],
                    'mau_dual_ready_l': [H3SND + r'\excavator\excavator_fp\excavator_dual_ready_left'],
                    'mau_dual_ready_r': [H3SND + r'\excavator\excavator_fp\excavator_dual_ready_right'],
                    'mau_dual_reload_l': [H3SND + r'\excavator\excavator_fp\excavator_dual_reload_left'],
                    'mau_dual_reload_r': [H3SND + r'\excavator\excavator_fp\excavator_dual_reload_right'],
                    'mau_dual_pose_1_l': [H3SND + r'\excavator\excavator_fp\excavator_dual_pose_left_var1'],
                    'mau_dual_pose_1_r': [H3SND + r'\excavator\excavator_fp\excavator_dual_pose_right_var1'],
                    'mau_dual_pose_2_l': [H3SND + r'\excavator\excavator_fp\excavator_dual_pose_left_var2'],
                    'mau_dual_pose_2_r': [H3SND + r'\excavator\excavator_fp\excavator_dual_pose_right_var2'],
                    'mau_flyby': [H3SND + r'\impacts_riccs\bullet_flyby_long'],
                    'mau_drop': [H3SND + r'\magnum\magnum_drop'],
                    'mau_drop_soft': [H3SND + r'\magnum\magnum_drop_soft']},
        'sounds': {'mau_fire': ('mau_fire', 'weapon_fire'), 'mau_fire_lod': ('mau_fire_lod', 'weapon_fire'),
                   'mau_dryfire': ('mau_dryfire', 'weapon_empty'),
                   'mau_ammo': ('mau_ammo', 'weapon_reload'),
                   'mau_reload': ('mau_reload', 'weapon_reload'), 'mau_ready': ('mau_ready', 'weapon_ready'),
                   'mau_melee': ('mau_melee', 'weapon_melee'), 'mau_pose': ('mau_pose', 'weapon_ready'),
                   'mau_dual_ready_l': ('mau_dual_ready_l', 'weapon_ready'),
                   'mau_dual_ready_r': ('mau_dual_ready_r', 'weapon_ready'),
                   'mau_dual_reload_l': ('mau_dual_reload_l', 'weapon_reload'),
                   'mau_dual_reload_r': ('mau_dual_reload_r', 'weapon_reload'),
                   'mau_dual_pose_1_l': ('mau_dual_pose_1_l', 'weapon_ready'),
                   'mau_dual_pose_1_r': ('mau_dual_pose_1_r', 'weapon_ready'),
                   'mau_dual_pose_2_l': ('mau_dual_pose_2_l', 'weapon_ready'),
                   'mau_dual_pose_2_r': ('mau_dual_pose_2_r', 'weapon_ready'),
                   'mau_flyby': ('mau_flyby', 'projectile_flyby'),
                   'mau_drop': ('mau_drop', 'object_impacts'),
                   'mau_drop_soft': ('mau_drop_soft', 'object_impacts')},
        'repoint_tags': [(FX + r'\excavator.material_effects', r'sound\weapons\magnum\magnum_drop', 'mau_drop'),
                         (FX + r'\excavator.material_effects', r'sound\weapons\magnum\magnum_drop_soft', 'mau_drop_soft'),
                         (MA + r'\projectiles\excavator_shard.projectile',
                          r'sound\weapons\impacts_riccs\bullet_flyby_long', 'mau_flyby')],
        # the shotgun blast's remastered LFE layer: Halo 3 has none -- the far layer takes its slot
        # (one slot of the cloned effect, no block delete)
        'repoint_fx': [(r'sound\weapons\shotgun\fire', 'mau_fire'),
                       (r'sound_remastered\weapons\shotgun\fire_lod', 'mau_fire_lod'),
                       (r'sound_remastered\weapons\shotgun\shotgun_lfe', 'mau_fire_lod')],
        'repoint_weapon': [(r'sound\weapons\magnum\magnum_dryfire', 'mau_dryfire'),
                           (r'sound\weapons\magnum\magnum_ammo', 'mau_ammo')],
        # the plasma pistol seed's 15 slots onto Halo 3's 12 sounds (each a distinct slot at least once)
        'graph_sounds': (('plaspistol_melee_one', 'mau_melee'), ('plaspistol_melee_toidle', 'mau_melee'),
                         ('plaspistol_melee_two', 'mau_melee'), ('plaspistol_overheat', 'mau_reload'),
                         ('plaspistol_overheat_exit', 'mau_dual_ready_l'),
                         ('plaspistol_posing_one', 'mau_pose'), ('plaspistol_posing_zero', 'mau_pose'),
                         ('plaspistol_ready', 'mau_ready'),
                         ('plaspistol_dual_overheat_exit_l', 'mau_dual_reload_l'),
                         ('plaspistol_dual_overheat_exit_r', 'mau_dual_reload_r'),
                         ('plaspistol_dual_overheat_l', 'mau_dual_pose_2_l'),
                         ('plaspistol_dual_overheat_r', 'mau_dual_pose_2_r'),
                         ('plaspistol_dual_posing_l', 'mau_dual_pose_1_l'),
                         ('plaspistol_dual_posing_r', 'mau_dual_pose_1_r'),
                         ('plaspistol_dual_ready', 'mau_dual_ready_r')),
        'graph_sound_dir': r'sound\weapons\plasma_pistol' + '\\',
        'gain': {},
        'boost': {},
        'backup': r'E:\HaloBackups\H2EK_brute_mauler_before_sounds',
        'graph_backup': r'E:\HaloBackups\H2EK_brute_mauler_graphs_before_sounds',
    },

    # step 9 -- h2_port_fp_anims.py: Halo 3's OWN FP animations, both species, single AND DUAL,
    # through `tool fp-model-animations`. Seeded from Bungie's H2 PLASMA PISTOL graphs: one-handed,
    # dual blend screens, NO single-wield IK entry (drop_ik not needed -- the Spiker's SMG seed had
    # one), and 15 sound-reference SLOTS in BOTH species -- Halo 3 cues 12 sounds; the magnum's graphs
    # (first seed, 2026-10-28) have 10 (Chief) / 7 (Dervish): the Arbiter's posing would be mute
    'fp_anims': {
        'species': {
            'masterchief': {
                'graph': r'objects\characters\masterchief\fp\weapons\pistol\fp_excavator\fp_excavator.model_animation_graph',
                'arms_rm': r'objects\characters\masterchief\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_masterchief\fp_arms.jms',
                'source': r'objects\characters\masterchief\fp\weapons\pistol\fp_excavator',
                'seed': r'objects\characters\masterchief\fp\weapons\pistol\fp_plasma_pistol\fp_plasma_pistol'},
            'dervish': {
                'graph': r'objects\characters\dervish\fp\weapons\pistol\fp_excavator\fp_excavator.model_animation_graph',
                'arms_rm': r'objects\characters\dervish\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_dervish\dervish_fp_arms.jms',
                'source': r'objects\characters\dervish\fp\weapons\pistol\fp_excavator',
                'seed': r'objects\characters\dervish\fp\weapons\pistol\fp_plasma_pistol\fp_plasma_pistol'},
        },
        'weapon_dir': MA + r'\fp_excavator',
        'weapon_rm': MA + r'\fp_excavator\fp_excavator.render_model',
        'weapon_nodes': ['gun', 'barrel', 'drum', 'piston'],
        # Halo 2 has no equipment (throw_equipment is Halo 3's deployable)
        'skip': ['first_person:throw_equipment'],
        # Halo 3 names its single-wield idle in three variants (var1 99 / var2 124 / var3 74 frames);
        # the magnum seed (and every Halo 2 single-wield graph) has a plain `first_person:idle` --
        # var1 becomes it (the overlays' reference pose), var2 / var3 stay variants
        'rename': {'first_person:idle:var1': 'first_person:idle'},
        'looping': ['first_person:idle', 'first_person:idle:var2', 'first_person:idle:var3',
                    'first_person:posing:var1',
                    'first_person:dual:idle:var1', 'first_person:dual:idle:var2', 'first_person:dual:idle:var3',
                    'first_person:dual:posing:var1', 'first_person:dual:posing:var2'],
        'overlay_reference': 'first_person:idle:var1',
        # Halo 3's OWN frame + sound events per animation (the Spiker's rule): its 12 sounds onto the
        # graph's own slots (step 10 repointed the seed's 15)
        'source_events': {'sounds': {
            'excavator_melee': 'mau_melee', 'excavator_ready': 'mau_ready', 'excavator_reload': 'mau_reload',
            'excavator_pose': 'mau_pose',
            'excavator_dual_ready_left': 'mau_dual_ready_l', 'excavator_dual_ready_right': 'mau_dual_ready_r',
            'excavator_dual_reload_left': 'mau_dual_reload_l', 'excavator_dual_reload_right': 'mau_dual_reload_r',
            'excavator_dual_pose_left_var1': 'mau_dual_pose_1_l', 'excavator_dual_pose_right_var1': 'mau_dual_pose_1_r',
            'excavator_dual_pose_left_var2': 'mau_dual_pose_2_l', 'excavator_dual_pose_right_var2': 'mau_dual_pose_2_r'}},
        # THE SPIKER'S CHECKS (dual-wield port #2, 2026-10-28): drop_ik n/a (the magnum seed has no
        # IK block); rest_left_arm n/a -- Halo 3's Mauler animator keeps the left hand LOW in every
        # single-wield animation of BOTH species (3.8, 9.2, -26 cm, the Arbiter-like rest the Spiker had
        # to build), raising it only in the reloads (25, 8, -8 at mid-reload); root_identity n/a
        # (fp_excavator's root binds at identity, see geometry)
    },

    # step 4b -- port_field_audit.py --port h2:brute_mauler: every field NO card covers where the
    # Halo 3 Mauler differs from the Halo 3 Shotgun (the yardstick) -- list 2 must say 0 to port
    'field_audit': {
        'source_kit': 'H3EK',
        'source': {'weapon': (MA + r'\excavator.weapon', r'objects\weapons\rifle\shotgun\shotgun.weapon'),
                   'projectile': (MA + r'\projectiles\excavator_shard.projectile',
                                  r'objects\weapons\rifle\shotgun\projectiles\shotgun_bullet.projectile'),
                   'damage_effect': (MA + r'\damage_effects\excavator_shard.damage_effect',
                                     r'objects\weapons\rifle\shotgun\damage_effects\shotgun_bullet.damage_effect')},
        'target': {'weapon': (MA + r'\excavator.weapon', SG + r'\shotgun.weapon'),
                   'projectile': (MA + r'\projectiles\excavator_shard.projectile',
                                  SG + r'\projectiles\shotgun_bullet.projectile'),
                   'damage_effect': (MA + r'\damage_effects\excavator_shard.damage_effect',
                                     SG + r'\damage_effects\shotgun_bullet.damage_effect')},
        # 2026-10-28, first run: list 2 = the card-covered rows (aim assist, magazines, range, falloff,
        # damage, rider: the catalog's balanced rows; 'port already' = Halo 3's own DEFAULT) + bounding
        # radius (written by the ratio). Every other row decided:
        'decisions': {
            'magnetism angle / range (nth 0) + throttle magnitude / minimum distance / maximum adjustment':
                "Halo 2's MELEE aim assist (the lunge): the shotgun 40 / 1.0 / 0.9 / 0.1 / 20, the magnum 0. "
                "The audit pairs Halo 3's WEAPON magnetism (16) with it by name; Halo 3 has no per-weapon melee "
                "magnetism (a global for every weapon) -> the one-handed magnum's 0 kept (the shotgun's lunge "
                "is the H2 shotgun's own); the weapon magnetism is nth 1 (Halo 3's 16 / 7)",
            'active camo ding': "the magnum's 0 (Halo 3 both 1, the H2 shotgun 1; the Spiker kept 0): a zero "
                "between zeros and tag references -- no anchor to pin it by; firing does not cost camo",
            'barrels projectiles per shot (list 4)': "Halo 3 keeps the pellets on the PROJECTILE (conical spread "
                "3 x 5): Halo 3's 15 (DEFAULT), the balanced 10 = the H2 shotgun's (user 4a)",
            'barrels minimum error / error angle (lists 5)': "the pellet cone: Halo 3's 7.5 = its shotgun's -> "
                "the H2 shotgun's 4 / 10-12, on the single (nth 1) AND the dual error (nth 0)",
            'barrels illumination recovery time': 'both Halo 3 weapons 0.1 = the H2 shotgun 0.1: written',
            'dual wield damage scale': "Halo 3's 0.7 (DEFAULT); the balanced 0.583 is user 4a's (0.7 x the "
                "SMG's 0.833)",
            'initial / final velocity (list 4)': "Halo 3's 480 (DEFAULT); balanced 120 (the card)",
            'first person weapon offset': "the AR's -0.01, 0, -0.03 (A1 observation 4) -- checked in game",
            'old message index / sort order / on-ground scales / predicted bitmaps / flags\'\'': "the magnum's "
                "(the donor's item fields; 'can be dual wielded' kept)",
            'weapon type / magazine flags': "Halo 3 'undefined' / 0 = the magnum's: none of the shotgun's "
                "shell baggage (Halo 1's A6 finding)",
            'damage reporting type': "the magnum's (kill feed / medals only; Halo 2 has no mauler entry)",
            'weapon attachments (Halo 3 2) / projectile attachments (Halo 3 1)': "the look: check 10 / step 3 "
                "(Halo 3's lens flare and the pellet's tracer effect)",
            'barrels deceleration time\' (shotgun 0.25)': "Halo 3's Mauler 0 = the port's 0",
            'font icons / ground scales / falloff ranges / fp offset override': 'no Halo 2 counterpart '
                '(the icon is step 8)',
        },
    },
    # make_port_catalog_h2.py brute_mauler: the SHOTGUN table's rows (read from the H2 shotgun's
    # weapon / pellet / damage effect) onto the Mauler's own; the MELEE rows onto its OWN blade melee
    # (strike_melee's rows x72/70, user 4a); the user's 4a decisions as overrides / extra rows
    'catalog': {
        'table': 'balance_Mauler_Halo3_to_Halo2.json',
        'weapon_tag': MA + r'\excavator',
        'port_tags': [(('weap', SG + r'\shotgun'), MA + r'\excavator'),
                      (('proj', SG + r'\projectiles\shotgun_bullet'), MA + r'\projectiles\excavator_shard'),
                      (('jpt!', SG + r'\damage_effects\shotgun_bullet'), MA + r'\damage_effects\excavator_shard'),
                      (('jpt!', r'objects\weapons\damage_effects\strike_melee'), MA + r'\damage_effects\excavator_melee')],
        'shared': [],
        'value_overrides': {
            # the table reads Halo 3's pellets off the BARREL (1); they sit on the projectile (15)
            'Projectiles Per Shot': {'value': 10, 'note': "user 4a 2026-10-28: the H2 shotgun's 10 x 15/15 "
                                                          "(Halo 3 keeps 15 pellets on the projectile)"},
            # the shotgun reloads a shell (1): the Mauler a WHOLE magazine
            'Rounds Reloaded': {'value': 10, 'note': "Halo 3's whole-magazine reload (rounds reloaded = "
                                                     "loaded; the shotgun's 1 a shell does not apply)"},
            # DUAL-WIELD CARRY RULE: inventory 24 + 10 loaded = 34 (the ratio's 33.3) x1.5 -> total 50
            'Rounds Inventory Maximum': {'value': 40, 'note': "user 4a 2026-10-28: the dual-wield carry "
                                                              "rule x1.5 (the Shotgun yardstick cannot be dual "
                                                              "wielded) -> 40 + 10 loaded = 50"}},
        'extra_rows': [{'class': 'weap', 'tag': MA + r'\excavator', 'field': 'Dual Wield Damage Scale',
                        'block': 'Barrels', 'value': 0.583333, 'card': 'Dual Weapon Damage', 'original': 0.7,
                        'note': "user 4a 2026-10-28: Halo 3's 0.7 x the SMG's H3 -> H2 0.833 (the Spiker's "
                                "route; the shotgun has no dual row)"}],
        'fp_animations': r'objects\characters\*\fp\weapons\pistol\fp_excavator\fp_excavator',
        'reload_mult': None,
        'desc': ('%s carried from %s into Halo 2 with its own model, textures, sounds, blade melee and '
                 'its own Halo 3 first-person animations for both species -- dual wield included -- '
                 'balanced through the Shotgun.'),
    },

    # port_backup.py --game h2: the owned folders are derived; these are the Mauler's other edits
    'backup': {'extra': [H2EK + r'\data\!extracted\magnum', H2EK + r'\data\!extracted\fp_magnum']},

    # step 11 -- `python ai_firing_profile.py --h2-port brute_mauler`: Halo 3's ai\generic Mauler
    # entry (010_jungle) name-for-name into H2EK ai\generic, over the H2 SHOTGUN's (the yardstick:
    # a close-range pellet weapon's ranges)
    'firing_profile': {'from_game': 'Halo 3', 'from_map': r'halo3\maps\010_jungle.map',
                       'from_weapon': r'objects\weapons\pistol\excavator\excavator',
                       'donor_weapon': SG + r'\shotgun'},
    # 05b (Chief, Brutes) + 08a (Arbiter, Brutes): parallel step 2; rounds = a FULL carry so a whole
    # reload can be tested (boot 2, user: 'only has 10 total'): Balanced 10 loaded + 40 (the default
    # build); an --original boot passes --rounds 5,20 (Halo 3's 5 loaded + 20 = its 25)
    'test': {'level': '05b_deltatowers', 'dervish_level': '08a_deltacliffs', 'rounds': (10, 40)},
    'residency': {'levels': 'all', 'placements': False},
}
