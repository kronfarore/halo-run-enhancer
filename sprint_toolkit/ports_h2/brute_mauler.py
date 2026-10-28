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
            # first-person placement: the AR's (Halo 3's own animations still need Halo 2's offset,
            # A1 observation 4) -- check in game
            (MA + r'\excavator.weapon', 'first person weapon offset', '', 0, 0, [-0.01, 0.0, -0.03]),
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
        ],
        'skipped': [
            ('reload time', "the magazine's reload time does not drive the player's reload (the SAW, user): "
                            "the Mauler's own Halo 3 animation does"),
        ],
    },
    'firing_profile': {'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\pistol\\excavator\\excavator', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '05b_deltatowers', 'dervish_level': '08a_deltacliffs'},   # parallel step 2
    'residency': {'levels': 'all', 'placements': False},
}
