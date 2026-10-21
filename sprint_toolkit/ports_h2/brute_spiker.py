r"""Spike Rifle into Halo 2 (H2_PORT_PLAN.md wave A (Halo 3), #A3) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.
"""

SR = r'objects\weapons\rifle\spike_rifle'        # the source's folder (H3EK) AND the port's (H2EK)
SMG = r'objects\weapons\rifle\smg'                # the donor (H2EK)
FX = r'effects\objects\weapons\rifle\spike_rifle'  # the reserved effects folder
NEW_HUD = r'ui\hud\bitmaps\new_hud'
import os as _os
# the Halo 3 world render model's export (h1_fp_retarget.export_xml's cache; regenerable): the
# silhouette the HUD plate, backpack icon and pickup glyph are drawn from
H3_RM_XML = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'out', 'h3_export',
                          'objects~weapons~rifle~spike_rifle~spike_rifle.render_model.xml')
H3SND = r'data\sound\weapons'           # source folders in MCC's halo3 sfx.fsb (.info)
H2EK = r'F:\SteamLibrary\steamapps\common\H2EK'

PORT = {
    'order': 3,
    'wave': 'A3',
    'name': 'Spike Rifle',
    'source': 'Halo 3',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\rifle\\spike_rifle\\spike_rifle',
    'reservations': {
        'message_prefix': 'spk2',
        'glyph': 0xE540,           # was 0xE140 (boot 1: above U+E3FF so Halo 2 tints it)
        'weapon_dir': 'objects\\weapons\\rifle\\spike_rifle',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\spike_rifle',
        'fp_graph': 'weapons\\rifle\\fp_spike_rifle\\fp_spike_rifle',
        'hud': 'ui\\hud\\brute_spiker',
        'hud_bitmap_prefix': 'brute_spiker_',
        'sound_dir': 'sound\\weapons\\brute_spiker_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\smg\\smg', 'message_prefix': 'smg',
              'why': 'spew magazine 1/1/1 AND dual-wieldable -- keep the flag'},
    'yardstick': {
        # step 4a, user 2026-10-21: the SMG; balance_Spike_Rifle_Halo3_to_Halo2.json
        # (balance_port.py "Spike Rifle" "Halo 3" "Halo 2" --hop "SMG:Halo 3>Halo 2");
        # TTK h2_spiker_ttk_4a.py h2_spiker_ttk_4a_variants.json
        'pick': 'SMG',
        'reason': ('user 2026-10-21: one hop, same role, both dual-wield; nearly every ratio x1: '
                   'balanced damage 8.55 (x0.95), rate 8, ammo 40 / 120 / 160, velocity 25 / 17.5, '
                   'spread 0 / 0.4-1.25, autoaim 6 / 12, magnetism 12 / 18, rider 0.75, dual wield '
                   'damage scale 0.667, dual error 0.25 / 0.75-1.5 (x1). Elite minor legendary TTK '
                   '2.12 s (default 2.00; H2 SMG 2.07, AR port 1.90, PR 4.76, BPR 4.60). '
                   'Alternatives: Plasma Rifle (spike 14 / 9.8, no ammo rows), Needler (no damage '
                   'row, magazine 63, contradictory rate ratios)'),
        # the user's picks beside the yardstick (2026-10-21):
        'melee': ('own clone of strike_melee x Halo 3 cut_melee 72 / strike_melee 70 '
                  '(20.57-61.71; the blades)'),
        'projectile': "Halo 3's own air gravity 0.2 (no SMG card row) AND minimum velocity 12 (user: "
                      "not the SMG rule's 0)",
        'candidates': {
            'provisional': 'SMG',
            'alternatives': ['Needler', 'Plasma Rifle'],
            'direct': 'none (H2 Brutes never carry a spiker)',
            'peers': ['SMG', 'Needler', 'Brute Plasma Rifle', 'Plasma Rifle'],
            'why': 'magazine 40 auto 8/s, slow arcing projectile, dual-wieldable like the SMG (both dual -> no x1.5 carry fudge); the Brute Plasma Rifle has NO H3 card, so cannot be the yardstick',
        },
    },
    # step 1 -- h2_port_geometry.py kind 'h3': the Halo 3 render models on their OWN skeletons
    # (world: gun, barrel, bullet, magazine, slide, safety; FP: gun, ammo_drum, barrel_1,
    # barrel_2, clamp_left, clamp_right, slide) -- the Spiker's own FP animations drive them
    'geometry': {
        'kind': 'h3',
        'world_rm': SR + r'\spike_rifle.render_model',
        'fp_rm': SR + r'\fp_spike_rifle\fp_spike_rifle.render_model',
        'data_dir': SR,
        'world': 'spike_rifle', 'fp': 'fp_spike_rifle',
        # Halo 3's three shaders all sample `brute_bolter` (+ bump, + the illum mask): the body,
        # the dull grip, the shiny blades (Halo 1's A5). `shaders\invalid` = 20 FP triangles
        # Halo 3 never draws (the barrel end caps): dropped
        'materials': {'bolt_thrower': 'spike_rifle', 'bolt_thrower_dull': 'spike_rifle_dull',
                      'bolt_thrower_shiny': 'spike_rifle_shiny'},
        # the world .model is the BR's clone (the AR's shape: no world-model graph): its
        # variants name permutation `base`, region `gun`
        'world_permutation': 'base', 'world_region': 'gun',
        # no ejection port (spikes); Halo 3's muzzle_brake / fx_reload / weapon_stow_anchor unused
        'markers': {'primary_trigger': 'primary_trigger', 'left_hand': 'left_hand',
                    'flashlight': 'flashlight'},
        'muzzle_drop': 0.0,
        'ground_point': {'rot': (0.7071068883, -1.8e-09, -7.42e-08, -0.7071067095)},   # the SMG's
        'render': ['spike_rifle', r'spike_rifle\fp_spike_rifle'],
        # boot 1 (user): the dual LEFT gun was upside down -- Halo 2 mirrors it across the FP
        # root's local y, and Halo 3 binds the Spiker's FP `gun` turned 180 deg (local y = up)
        'fp_root_identity': True,
    },

    # step 2 -- h2_port_textures.py kind 'h3': Halo 3's own maps; shaders reseeded from Bungie's
    # BRUTE weapons: the gravity hammer's `hammer` (tex_bump_env_illum: bump, detail, base, env,
    # a SEPARATE self_illum_map) for the lit body and blades, the Brute Shot's own (tex_bump_env,
    # metal_dirty) for the dull grip. Halo 3's illum map is a grey mask of 68 texels coloured per
    # shader (body blue 2f/31/d8 x6, dull + shiny amber ff/cd/57 x3, read by bloom): Halo 2 draws
    # its self_illum_map as it is, so the mask is TINTED here -- Halo 1's A5 colours (PALE for the
    # blue: Halo 3's x6 + bloom reads pale; AMBER), lines grown 2 px (no bloom)
    'textures': {
        'kind': 'h3',
        'rel': SR + r'\bitmaps',
        'shaders_dir': SR + r'\shaders',
        'bump_gain': 1.0,                      # the AR's (user: 1.6 read 'rough')
        'bitmaps': [(SR + r'\bitmaps\brute_bolter.bitmap', 'spike_rifle',
                     r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot', 'color', None),
                    (SR + r'\bitmaps\brute_bolter_bump.bitmap', 'spike_rifle_bump',
                     r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot_bump', 'bump_snorm', None),
                    (SR + r'\bitmaps\brute_bolter_illum.bitmap', 'spike_rifle_illum_blue',
                     r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_illum',
                     ('tint', (0.75, 0.78, 1.0), 2), None),
                    (SR + r'\bitmaps\brute_bolter_illum.bitmap', 'spike_rifle_illum_amber',
                     r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_illum',
                     ('tint', (1.0, 205 / 255.0, 87 / 255.0), 2), None)],
        'shaders': [
            ('spike_rifle', r'objects\weapons\melee\gravity_hammer\shaders\hammer',
             {r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer': SR + r'\bitmaps\spike_rifle',
              r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_bump': SR + r'\bitmaps\spike_rifle_bump',
              r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_illum': SR + r'\bitmaps\spike_rifle_illum_blue'}),
            ('spike_rifle_shiny', r'objects\weapons\melee\gravity_hammer\shaders\hammer',
             {r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer': SR + r'\bitmaps\spike_rifle',
              r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_bump': SR + r'\bitmaps\spike_rifle_bump',
              r'objects\weapons\melee\gravity_hammer\bitmaps\gravity_hammer_illum': SR + r'\bitmaps\spike_rifle_illum_amber'}),
            ('spike_rifle_dull', r'objects\weapons\support_low\brute_shot\shaders\brute_shot',
             {r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot': SR + r'\bitmaps\spike_rifle',
              r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot_bump': SR + r'\bitmaps\spike_rifle_bump',
              r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot_bump_active_camo': SR + r'\bitmaps\spike_rifle_bump'}),
        ],
        'report_rows': [(SR + r'\bitmaps\spike_rifle_bump', 'the port'),
                        (r'objects\weapons\support_low\brute_shot\bitmaps\brute_shot_bump', 'Bungie Brute Shot')],
    },

    # step 3 -- h2_port_weapon.py: the H2 SMG's weapon (the yardstick's own tag: spew, 1 magazine
    # / 1 trigger / 1 barrel, ammo HUD, DUAL-WIELDABLE -- kept), every tag a balance row or a look
    # may touch cloned; the world .model from the BATTLE RIFLE's (the AR's shape: no world-model
    # graph -- the SMG's names one for its own charging handle). NEW: the BLADE melee, an own clone
    # of strike_melee (user, step 4a) named by both of the weapon's strike_melee references
    'weapon': {
        'weapon': SR + r'\spike_rifle.weapon',
        'clones': [(SMG + r'\smg.weapon', SR + r'\spike_rifle.weapon'),
                   (r'objects\weapons\rifle\battle_rifle\battle_rifle.model', SR + r'\spike_rifle.model'),
                   (SMG + r'\projectiles\smg_bullet.projectile', SR + r'\projectiles\spike_rifle_spike.projectile'),
                   (SMG + r'\damage_effects\smg_bullet.damage_effect', SR + r'\damage_effects\spike_rifle_spike.damage_effect'),
                   (SMG + r'\damage_effects\smg_trigger.damage_effect', SR + r'\damage_effects\spike_rifle_trigger.damage_effect'),
                   (r'objects\weapons\damage_effects\strike_melee.damage_effect', SR + r'\damage_effects\spike_rifle_melee.damage_effect'),
                   (r'effects\objects\weapons\rifle\smg\fire_bullet.effect', FX + r'\spike_rifle_fire.effect'),
                   (r'effects\objects\weapons\rifle\smg\smg_muzzle_flash.light', FX + r'\spike_rifle_muzzle_flash.light'),
                   (r'effects\materials\objects\weapons\smg.material_effects', FX + r'\spike_rifle_spike.material_effects')],
        'wiring': [
            (SR + r'\spike_rifle.weapon', 'hlmt', SMG + r'\smg', SR + r'\spike_rifle', 'world model'),
            (SR + r'\spike_rifle.model', 'mode', r'objects\weapons\rifle\battle_rifle\battle_rifle',
             SR + r'\spike_rifle', 'the world render model (it and the collision pool ONE path)', {'nth': 0}),
            (SR + r'\spike_rifle.weapon', 'mode', SMG + r'\fp_smg\fp_smg',
             SR + r'\fp_spike_rifle\fp_spike_rifle', 'first person model, Master Chief', {'nth': 0}),
            (SR + r'\spike_rifle.weapon', 'mode', SMG + r'\fp_smg\fp_smg',
             SR + r'\fp_spike_rifle\fp_spike_rifle', 'first person model, Dervish (one Halo 3 FP model)',
             {'nth': 0}),
            (SR + r'\spike_rifle.weapon', 'jmad', r'objects\characters\masterchief\fp\weapons\rifle\fp_smg\fp_smg',
             r'objects\characters\masterchief\fp\weapons\rifle\fp_spike_rifle\fp_spike_rifle',
             "Master Chief FP graph: the Spiker's own Halo 3 animations (single + dual)"),
            (SR + r'\spike_rifle.weapon', 'jmad', r'objects\characters\dervish\fp\weapons\rifle\fp_smg\fp_smg',
             r'objects\characters\dervish\fp\weapons\rifle\fp_spike_rifle\fp_spike_rifle',
             "Dervish FP graph: the Spiker's own Halo 3 animations (single + dual)"),
            (SR + r'\spike_rifle.weapon', 'proj', SMG + r'\projectiles\smg_bullet',
             SR + r'\projectiles\spike_rifle_spike', 'projectile'),
            (SR + r'\projectiles\spike_rifle_spike.projectile', 'jpt!', SMG + r'\damage_effects\smg_bullet',
             SR + r'\damage_effects\spike_rifle_spike', 'impact damage'),
            (SR + r'\spike_rifle.weapon', 'jpt!', SMG + r'\damage_effects\smg_trigger',
             SR + r'\damage_effects\spike_rifle_trigger', 'firing damage'),
            # both strike_melee references (the weapon names it twice, each beside its response)
            (SR + r'\spike_rifle.weapon', 'jpt!', r'objects\weapons\damage_effects\strike_melee',
             SR + r'\damage_effects\spike_rifle_melee', 'the blade melee (own, x72/70)', {'every': True}),
            (SR + r'\spike_rifle.weapon', 'effe', r'effects\objects\weapons\rifle\smg\fire_bullet',
             FX + r'\spike_rifle_fire', 'firing effect'),
            (SR + r'\spike_rifle.weapon', 'ligh', r'effects\objects\weapons\rifle\smg\smg_muzzle_flash',
             FX + r'\spike_rifle_muzzle_flash', 'muzzle flash light'),
            (SR + r'\spike_rifle.weapon', 'foot', r'effects\materials\objects\weapons\smg',
             FX + r'\spike_rifle_spike', 'material effects (the weapon)'),
            (SR + r'\projectiles\spike_rifle_spike.projectile', 'foot', r'effects\materials\objects\weapons\smg',
             FX + r'\spike_rifle_spike', 'impact material effects'),
            # the HUD is the SMG's clone (step 7: dual-wield shaped -- plate x4, meter x2 -- kept)
            (SR + r'\spike_rifle.weapon', 'nhdt', r'ui\hud\smg', r'ui\hud\brute_spiker', 'its own HUD (step 7)'),
        ],
        # the 3P label: the SMG's own `rifle` / `smg`, kept (no rename). Halo 3's is `pistol` /
        # `spr`, which no Halo 2 graph has; `smg` is a type of the masterchief / elite `dual`
        # class (their dual-wield stance), of every rifle-class graph's (marine, flood combat,
        # masterchief), and `rifle` / `any` is the Brute's (rifle: pr, sg) and the taught Grunt's
        'shared': [(r'the particles inside spike_rifle_fire', "the SMG's (Halo 3 particles do not port)"),
                   (r'objects\weapons\damage_effects\strike_melee_response, smash_melee(_response)',
                    "the melee's responses + the second hit, shared by every Halo 2 weapon"),
                   (r'objects\weapons\rifle\smg\damage_effects\smg_empty', "the SMG's dry-fire damage (none)"),
                   (r'effects\objects\weapons\pistol\needler\ready, ...\battle_rifle\reload',
                    "Bungie's own SMG names them (ready / reloading effects)"),
                   (r'objects\powerups\smg_ammo\smg_ammo', "the SMG's ammo pickup item (unused in campaign)"),
                   (r'sound\weapons\impacts_riccs\bullet_flyby_short', "the projectile's fly-by"),
                   (r'effects\bitmaps\weapons_fire\*, smoke_warthog_gun', "the SMG's own weapon bitmaps")],
    },

    # step 4 -- h2_port_numbers.py: Halo 3's OWN values (DEFAULT; the balanced rows are the
    # catalog's, step 4a's SMG table). h3_weapon_values.py rifle\spike_rifle\spike_rifle
    'numbers': {
        'numbers': [
            # flags'': the SMG's, 'can be dual wielded' KEPT (Halo 3's Spiker is dual-wieldable)
            (SR + r'\spike_rifle.weapon', 'autoaim angle', '', 0, 0, 5.0),
            (SR + r'\spike_rifle.weapon', 'autoaim range', '', 0, 0, 12.0),
            (SR + r'\spike_rifle.weapon', 'magnetism angle', '', 0, 1, 12.0),
            (SR + r'\spike_rifle.weapon', 'magnetism range', '', 0, 1, 18.0),
            (SR + r'\spike_rifle.weapon', 'rounds loaded maximum', 'magazines', 0, 0, 40),
            (SR + r'\spike_rifle.weapon', 'rounds reloaded', 'magazines', 0, 0, 40),
            (SR + r'\spike_rifle.weapon', 'rounds total initial', 'magazines', 0, 0, 120),
            (SR + r'\spike_rifle.weapon', 'rounds total maximum', 'magazines', 0, 0, 160),
            (SR + r'\spike_rifle.weapon', 'rounds per second', 'barrels', 0, 0, [8.0, 8.0]),
            # Halo 2's barrel: nth 0 = the rate ramp, nth 1 = the ERROR ramp, nth 2 = the
            # DUAL-weapon error ramp, nth 3 = the barrel climb (the AR's 4b audit). Halo 3's
            # Spiker: rate ramp 1 / 0.2 (moot at a flat 8), bloom ramp 1 / 0.2
            (SR + r'\spike_rifle.weapon', 'acceleration time', 'barrels', 0, 0, 1.0),
            (SR + r'\spike_rifle.weapon', 'deceleration time', 'barrels', 0, 0, 0.2),
            (SR + r'\spike_rifle.weapon', 'acceleration time', 'barrels', 0, 1, 1.0),
            (SR + r'\spike_rifle.weapon', 'deceleration time', 'barrels', 0, 1, 0.2),
            # single-wield spread (nth 1) and the DUAL error (nth 0, Halo 3's dual weapon error)
            (SR + r'\spike_rifle.weapon', 'minimum error', 'barrels', 0, 1, 0.0),
            (SR + r'\spike_rifle.weapon', 'error angle', 'barrels', 0, 1, [0.5, 1.25]),
            (SR + r'\spike_rifle.weapon', 'minimum error', 'barrels', 0, 0, 0.25),
            (SR + r'\spike_rifle.weapon', 'error angle', 'barrels', 0, 0, [0.75, 1.5]),
            (SR + r'\spike_rifle.weapon', 'dual wield damage scale', 'barrels', 0, 0, 0.8),
            # Halo 3's Spiker has no barrel climb (the SMG's 0..0.7 'late')
            (SR + r'\spike_rifle.weapon', 'angle change per shot', 'barrels', 0, 0, [0.0, 0.0]),
            # the slow ARCING spike (user, 4a: gravity 0.2 AND minimum velocity 12, Halo 3's own)
            (SR + r'\projectiles\spike_rifle_spike.projectile', 'initial velocity', '', 0, 0, 25.0),
            (SR + r'\projectiles\spike_rifle_spike.projectile', 'final velocity', '', 0, 0, 17.5),
            (SR + r'\projectiles\spike_rifle_spike.projectile', 'minimum velocity', '', 0, 0, 12.0),
            (SR + r'\projectiles\spike_rifle_spike.projectile', 'air gravity scale', '', 0, 0, 0.2),
            (SR + r'\projectiles\spike_rifle_spike.projectile', 'maximum range', '', 0, 0, 70.0),
            (SR + r'\projectiles\spike_rifle_spike.projectile', 'air damage range', '', 0, 0, [0.0, 60.0]),
            (SR + r'\projectiles\spike_rifle_spike.projectile', 'water damage range', '', 0, 0, [0.0, 10.0]),
            (SR + r'\damage_effects\spike_rifle_spike.damage_effect', 'damage upper bound', '', 0, 0, [9.0, 9.0]),
            (SR + r'\damage_effects\spike_rifle_spike.damage_effect', 'instantaneous acceleration', '', 0, 0, 0.125),
            # the BLADE (user, 4a): own melee, Halo 3's cut_melee 72 flat (strike_melee 70 / H2 20-60)
            (SR + r'\damage_effects\spike_rifle_melee.damage_effect', 'damage lower bound', '', 0, 0, 72.0),
            (SR + r'\damage_effects\spike_rifle_melee.damage_effect', 'damage upper bound', '', 0, 0, [72.0, 72.0]),
            # first-person placement: the AR's (Halo 3's own animations still need Halo 2's offset,
            # A1 observation 4) -- check in game
            (SR + r'\spike_rifle.weapon', 'first person weapon offset', '', 0, 0, [-0.01, 0.0, -0.03]),
        ] + [
            # step 4b (port_field_audit.py --port h2:brute_spiker, list 2: the ratio H3 Spiker /
            # H3 SMG x the H2 SMG). The audit names Halo 3's DUAL error ramp (Spiker 0 / 0, SMG
            # 1.1 / 0.3) by name only; Halo 2's dual ramp is nth 2 -> 0 / 0
            (SR + r'\spike_rifle.weapon', 'bounding radius', '', 0, 0, 0.163636),
            (SR + r'\spike_rifle.weapon', 'bounding offset', '', 0, 0, [0.075, 0.0, 0.0]),
            (SR + r'\spike_rifle.weapon', 'acceleration scale', '', 0, 0, 0.657895),
            (SR + r'\spike_rifle.weapon', 'rounds between tracers', 'barrels', 0, 0, 0),
            (SR + r'\spike_rifle.weapon', 'acceleration time', 'barrels', 0, 2, 0.0),
            (SR + r'\spike_rifle.weapon', 'deceleration time', 'barrels', 0, 2, 0.0),
            (SR + r'\projectiles\spike_rifle_spike.projectile', 'water gravity scale', '', 0, 0, 0.4),
            (SR + r'\projectiles\spike_rifle_spike.projectile', 'bounding radius', '', 0, 0, 0.5),
            # Halo 3's spike: `oriented along velocity` (Halo 2's bit 0, the needler shard's; H3's
            # bit 18 has no Halo 2 name), the timer starts WHEN AT REST, 1 s (a stuck spike goes)
            (SR + r'\projectiles\spike_rifle_spike.projectile', 'flags', '', 0, 1, 1),
            (SR + r'\projectiles\spike_rifle_spike.projectile', 'detonation timer starts', '', 0, 0, 2),
            (SR + r'\projectiles\spike_rifle_spike.projectile', 'timer', '', 0, 0, [1.0, 1.0]),
            (SR + r'\projectiles\spike_rifle_spike.projectile', 'acceleration range', '', 0, 0, [0.0, 6.0]),
        ] + [
            # THE RICOCHET: the material responses BY MATERIAL NAME (the audit pairs them by index;
            # Halo 3 has 16, the SMG clone 10). Halo 2's enum = Halo 3's (0 impact, 1 fizzle,
            # 2 overpenetrate, 4 bounce); nth 0 the default response, nth 1 the potential one
            (SR + r'\projectiles\spike_rifle_spike.projectile', f, 'material responses', i, nth, v)
            for i, rows in (
                # 0 default_material = H3 default_material: impact, never bounces (chance 0)
                (0, [('response', 1, 4), ('between', 0, [0.0, 30.0]), ('and', 0, [20.0, 30.0])]),
                # 1 liquid_thin, 2 liquid_thick: already Halo 3's (overpenetrate 0.5 / 5, 0.75 / 2.5)
                # 3 hard_metal_thick = H3: impact, bounce at 0-60 deg, 20-30 wu/s, chance 1
                (3, [('response', 0, 0), ('response', 1, 4), ('chance fraction', 0, 1.0),
                     ('between', 0, [0.0, 60.0]), ('and', 0, [20.0, 30.0])]),
                # 4 hard_metal_solid = H3: fizzle, bounce chance 1
                (4, [('response', 1, 4), ('chance fraction', 0, 1.0),
                     ('between', 0, [0.0, 60.0]), ('and', 0, [20.0, 30.0])]),
                # 5 hard_floodflesh: Halo 3 has none (falls to default) -- Halo 2's fizzle kept
                # 6 hard_terrain = H3: impact, bounce chance 1
                (6, [('response', 0, 0), ('response', 1, 4), ('chance fraction', 0, 1.0),
                     ('between', 0, [0.0, 60.0]), ('and', 0, [20.0, 30.0])]),
                # 7 brittle_glass = H3: fizzle (the SMG overpenetrates 5)
                (7, [('response', 0, 1), ('response', 1, 4), ('maximum distance', 0, 0.0),
                     ('between', 0, [0.0, 60.0]), ('and', 0, [20.0, 30.0])]),
                # 8 energy_shield_thick = H3: fizzle, bounce chance 0
                (8, [('response', 1, 4), ('between', 0, [0.0, 30.0]), ('and', 0, [20.0, 30.0])]),
                # 9 soft_organic: Halo 3 none (default: impact) -- the audit's 0 distance
                (9, [('maximum distance', 0, 0.0)]),
            )
            for f, nth, v in rows
        ] + [
            # every bouncing response: Halo 3's angular noise 4, friction 0.35 / 0.7
            (SR + r'\projectiles\spike_rifle_spike.projectile', f, 'material responses', i, 0, v)
            for i in (0, 3, 4, 6, 7, 8)
            for f, v in (('angular noise', 4.0), ('parallel friction', 0.35), ('perpendicular friction', 0.7))
        ],
        'skipped': [
            ('reload time', "the magazine's reload time does not drive the player's reload (the SAW, user): "
                            "the Spiker's own 56-frame animation does"),
        ],
    },

    # step 5 -- h2_port_collision.py: the BATTLE RIFLE's authored hull (the world .model's donor)
    # scaled per axis to the Spiker's render mesh
    'collision': {
        'donor': r'objects\weapons\rifle\battle_rifle\battle_rifle',
        'port': SR + r'\spike_rifle',
        'src': r'battle_rifle\collision\battle_rifle_collision.jms',     # under data\!extracted
        'out': SR + r'\collision\spike_rifle.jms',                       # under data
        'port_render_jms': SR + r'\render\spike_rifle.jms',
        'donor_render_jms': r'battle_rifle\render\battle_rifle_L5.jms',
        'max_growth': 1.25,
        # the BR hull's nodes (gun, magazine, OpHandle, safety) are not the Spiker's own world
        # skeleton (gun, barrel, bullet, magazine, slide, safety): the hull takes the render's
        'nodes_from_render': True,
    },

    # step 7 -- the HUD: a clone of the SMG's (DUAL-WIELD shaped: the plate named x4 --
    # right / left / right_out / left_out, sequences 0-3 of an 8-image plate --, the meter x2),
    # 40 ticks (2 rows of 20) on the SMG meter's canvas, the plate's EVERY image repainted
    # (h2_port_hud_plate all_images), the backpack drawn from the Spiker's own mesh, Halo 3's
    # crosshair (chud hud_reticles #2). The SMG does not zoom: no scope widgets
    'meter': {
        'donor_meter': NEW_HUD + r'\meters\smg_meter',
        'rel': NEW_HUD + r'\meters',
        'name': 'brute_spiker_meter',
        'donor_hud': r'ui\hud\smg',
        'port_hud': r'ui\hud\brute_spiker',
        'weapon': SR + r'\spike_rifle.weapon',
        'rounds': 40, 'rows': 2,             # the SMG's 3 rows of 20 -> 2 rows of 20
        'canvas': (198, 42), 'tick_w': 6,
        # boot 1 (user: 'the pips look different from the original'): Halo 3's OWN round -- chud
        # ballistic_meters #9, a tab 8x20 with a slanted foot at a 15 px pitch; scaled by the
        # pitch (9.9 / 15): 6 wide, 15 tall
        'tick_art': {'h3': ('ballistic_meters', 9), 'h': 15},
        'backpack': NEW_HUD + r'\backpack_weapons',
        'backpack_port': NEW_HUD + r'\brute_spiker_backpack',
        'backpack_size': (62, 30),
        'model_3p': H3_RM_XML,
        'preview': 'brute_spiker_meter_preview.png',
    },
    'hud_plate': {
        'rel': NEW_HUD + r'\backgrounds',
        'donor': NEW_HUD + r'\backgrounds\smg_bkd',
        'other': NEW_HUD + r'\backgrounds\magnum_bkd',     # the other dual plate: same 8 shapes
        'name': 'brute_spiker_bkd',
        'hud': r'ui\hud\brute_spiker',
        'model_3p': H3_RM_XML,
        'fallback_box': (105, 191, 5, 34),
        'stretch': 1.4,
        # the dual-wield plate: all 8 images (4 shapes, each bright + dim '_out'), written into
        # Bungie's own colour plate; the dim ones from their bright twins
        'all_images': {'dim': {4: 0, 5: 1, 6: 2, 7: 3}},
    },
    'reticle': {
        'rel': NEW_HUD + r'\crosshairs',
        'donor': NEW_HUD + r'\crosshairs\hud_reticles',
        'donor_sequence': 0,                 # the SMG's fullscreen crosshair (half / quarter 23)
        'name': 'brute_spiker_reticle',
        'hud': r'ui\hud\brute_spiker',
        'footprint': 1.0,
        # Halo 3's ON-SCREEN size (the AR's rule, user boot 2): the AR's sprite #0 (ink 110) drew
        # 72 px at 1080p = target_ink 64; the Spiker's #2 (ink 156) at the same chud widget scale
        # -> 64 x 156 / 110 = 91 (derived from the AR's measurement -- check in game)
        'h3_art': {'sheet': 'hud_reticles', 'sequence': 2, 'yardstick': 3, 'target_ink': 91},
        'preview': 'brute_spiker_reticle_preview.png',
    },

    # step 8 -- the pickup icon at U+E540, the messages (smg_* -> spk2_*: a LONGER prefix than
    # the donor's -- the first length-changing rename in game; the dual lines included)
    # BOOT 1 (user: 'all icons are violet on the Arbiter'): halo2.dll's text renderer draws a glyph
    # in the line's colour (HUD blue / Arbiter violet) for U+E112-E12B (Bungie's weapon icons) and
    # for anything OUTSIDE U+E000-E3FF; every other codepoint in E000-E3FF is forced WHITE and drawn
    # x0.72 (VA 0x1807552E1, the scale at 0x180B1B878). User: move the ports above U+E3FF (E140 ->
    # E540: +0x400), drawn WHITE like Bungie's, at 0.72 of 160x62 so the on-screen size stays
    'glyph': {
        'box': (115, 45),
        'model_3p': H3_RM_XML,
        'tif': 'spike_rifle_h2_glyph.tif',
        # white like Bungie's (the renderer tints it); the AR's two-tone look kept as luminance:
        # lines white, the solid body at the AR's body / line ratio (~0.6)
        'colour': (255, 255, 255),
        'style': {'line': (255, 255, 255), 'body': (153, 153, 153)},
    },
    'messages': {
        'donor_prefix': 'smg', 'donor_icon': '&smg',
        'donor_name': 'SMG', 'port_name': 'Spike Rifle',
        # the article changes with the name ('Picked up an SMG')
        'names': [('an SMG', 'a Spike Rifle'), ('SMG', 'Spike Rifle')],
        'weapon': SR + r'\spike_rifle.weapon',
    },

    # step 10 -- h2_port_sounds.py: Halo 3's OWN sounds from MCC's halo3 sfx.fsb (render_h3_bank,
    # 48 kHz at their native level), classic Opus. Halo 3's Spiker: a one-shot fire (6
    # permutations) + its far-distance layer, single AND DUAL (left / right) ready, reload and
    # posing, melee, ammo pickup; its empty names Halo 3's SMG dry fire. The seeded graphs (the
    # H2 SMG's) cue the SMG's 17 graph sounds -- each gets the Spiker's own
    'sounds': {
        'weapon': SR + r'\spike_rifle.weapon',
        'fire_fx': FX + r'\spike_rifle_fire.effect',
        'audio': _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'out',
                               'h2_sounds', 'brute_spiker'),
        'audio_key': 'Spike Rifle',
        'h3_bank': {'spk_fire': [H3SND + r'\spike_rifle\spike_rifle_fire'],
                    'spk_fire_lod': [H3SND + r'\spike_rifle\spike_lod_far'],
                    'spk_dryfire': [H3SND + r'\smg\dryfire'],
                    'spk_reload': [H3SND + r'\spike_rifle\fp_spike_rifle\fp_spike_rifle_reload_full'],
                    'spk_ready': [H3SND + r'\spike_rifle\fp_spike_rifle\fp_spike_rifle_ready'],
                    'spk_melee1': [H3SND + r'\spike_rifle\fp_spike_rifle\fp_spike_rifle_melee'],
                    'spk_posing': [H3SND + r'\spike_rifle\fp_spike_rifle\fp_spike_rifle_posing_var1'],
                    'spk_ammo': [H3SND + r'\spike_rifle\spike_rifle_ammo'],
                    'spk_dual_ready': [H3SND + r'\spike_rifle\fp_spike_rifle\fp_spike_rifle_dual_ready_right'],
                    'spk_dual_reload_left': [H3SND + r'\spike_rifle\fp_spike_rifle\fp_spike_rifle_dual_reload_full_left'],
                    'spk_dual_reload_right': [H3SND + r'\spike_rifle\fp_spike_rifle\fp_spike_rifle_dual_reload_full_right'],
                    'spk_dual_posing_1_l': [H3SND + r'\spike_rifle\fp_spike_rifle\fp_spike_rifle_posing_dual_var1\fp_spike_rifle_posing_dual_var1_left'],
                    'spk_dual_posing_1_r': [H3SND + r'\spike_rifle\fp_spike_rifle\fp_spike_rifle_posing_dual_var1\fp_spike_rifle_posing_dual_var1_right'],
                    'spk_dual_posing_2_l': [H3SND + r'\spike_rifle\fp_spike_rifle\fp_spike_rifle_posing_dual_var2\fp_spike_rifle_posing_dual_var2_left'],
                    'spk_dual_posing_2_r': [H3SND + r'\spike_rifle\fp_spike_rifle\fp_spike_rifle_posing_dual_var2\fp_spike_rifle_posing_dual_var2_right']},
        'sounds': {'spk_fire': ('spk_fire', 'weapon_fire'), 'spk_fire_lod': ('spk_fire_lod', 'weapon_fire'),
                   'spk_dryfire': ('spk_dryfire', 'weapon_empty'),
                   'spk_reload': ('spk_reload', 'weapon_reload'), 'spk_ready': ('spk_ready', 'weapon_ready'),
                   'spk_melee1': ('spk_melee1', 'weapon_melee'), 'spk_posing': ('spk_posing', 'weapon_ready'),
                   'spk_ammo': ('spk_ammo', 'weapon_reload'),              # the SMG's smg_ammo class
                   'spk_dual_ready': ('spk_dual_ready', 'weapon_ready'),
                   'spk_dual_reload_left': ('spk_dual_reload_left', 'weapon_reload'),
                   'spk_dual_reload_right': ('spk_dual_reload_right', 'weapon_reload'),
                   'spk_dual_posing_1_l': ('spk_dual_posing_1_l', 'weapon_ready'),
                   'spk_dual_posing_1_r': ('spk_dual_posing_1_r', 'weapon_ready'),
                   'spk_dual_posing_2_l': ('spk_dual_posing_2_l', 'weapon_ready'),
                   'spk_dual_posing_2_r': ('spk_dual_posing_2_r', 'weapon_ready')},
        'repoint_fx': [(r'sound\weapons\smg\fire', 'spk_fire'),
                       (r'sound_remastered\weapons\smg\fire_lod', 'spk_fire_lod')],
        'repoint_weapon': [(r'sound\weapons\smg\dryfire', 'spk_dryfire'),
                           (r'sound\weapons\smg\smg_ammo', 'spk_ammo')],
        # the SMG's four dual posing variants (0-3) onto Halo 3's two (var1 / var2)
        'graph_sounds': (('smg_melee1', 'spk_melee1'), ('smg_ready', 'spk_ready'),
                         ('smg_reload', 'spk_reload'), ('smg_reload_full', 'spk_reload'),
                         ('smg_dual_ready', 'spk_dual_ready'),
                         ('smg_dual_reload_left', 'spk_dual_reload_left'),
                         ('smg_dual_reload_right', 'spk_dual_reload_right'),
                         ('smg_dual_posing_0_l', 'spk_dual_posing_1_l'), ('smg_dual_posing_0_r', 'spk_dual_posing_1_r'),
                         ('smg_dual_posing_1_l', 'spk_dual_posing_2_l'), ('smg_dual_posing_1_r', 'spk_dual_posing_2_r'),
                         ('smg_dual_posing_2_l', 'spk_dual_posing_1_l'), ('smg_dual_posing_2_r', 'spk_dual_posing_1_r'),
                         ('smg_dual_posing_3_l', 'spk_dual_posing_2_l'), ('smg_dual_posing_3_r', 'spk_dual_posing_2_r'),
                         ('smg_posing_var0', 'spk_posing'), ('smg_posing_var1', 'spk_posing')),
        'graph_sound_dir': r'sound\weapons\smg' + '\\',
        'gain': {},
        'boost': {},
        'backup': r'E:\HaloBackups\H2EK_brute_spiker_before_sounds',
        'graph_backup': r'E:\HaloBackups\H2EK_brute_spiker_graphs_before_sounds',
    },

    # step 9 -- h2_port_fp_anims.py: Halo 3's OWN FP animations, both species, single AND DUAL
    # (Halo 3 ships `first_person:dual:*` -- Halo 2's own SMG graph uses the same names), through
    # `tool fp-model-animations`. Seeded from Bungie's H2 SMG graphs (dual blend screens, the
    # SMG's sound refs / events for same-name animations)
    'fp_anims': {
        'species': {
            'masterchief': {
                'graph': r'objects\characters\masterchief\fp\weapons\rifle\fp_spike_rifle\fp_spike_rifle.model_animation_graph',
                'arms_rm': r'objects\characters\masterchief\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_masterchief\fp_arms.jms',
                'source': r'objects\characters\masterchief\fp\weapons\rifle\fp_spike_rifle',
                'seed': r'objects\characters\masterchief\fp\weapons\rifle\fp_smg\fp_smg'},
            'dervish': {
                'graph': r'objects\characters\dervish\fp\weapons\rifle\fp_spike_rifle\fp_spike_rifle.model_animation_graph',
                'arms_rm': r'objects\characters\dervish\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_dervish\dervish_fp_arms.jms',
                'source': r'objects\characters\dervish\fp\weapons\rifle\fp_spike_rifle',
                'seed': r'objects\characters\dervish\fp\weapons\rifle\fp_smg\fp_smg'},
        },
        'weapon_dir': SR + r'\fp_spike_rifle',
        'weapon_rm': SR + r'\fp_spike_rifle\fp_spike_rifle.render_model',
        'weapon_nodes': ['gun', 'ammo_drum', 'barrel_1', 'barrel_2', 'clamp_left', 'clamp_right', 'slide'],
        # Halo 2 has no equipment (throw_equipment is Halo 3's deployable)
        'skip': ['first_person:throw_equipment'],
        'looping': ['first_person:idle', 'first_person:posing:var1',
                    'first_person:dual:idle:var1', 'first_person:dual:idle:var2', 'first_person:dual:idle:var3',
                    'first_person:dual:posing:var1', 'first_person:dual:posing:var2'],
        'overlay_reference': 'first_person:idle',
        'root_identity': 'gun',       # with geometry fp_root_identity (boot 1: the dual left gun)
        # Halo 3 names the one single-wield reload / the Chief's one fire `:var1`; Halo 2's SMG
        # (the seed: its events and sounds stay on same-name animations) names them plain
        'rename': {'first_person:reload_empty:var1': 'first_person:reload_empty',
                   'first_person:reload_full:var1': 'first_person:reload_full',
                   'first_person:fire_1:var1': 'first_person:fire_1'},
    },

    # step 4b -- port_field_audit.py --port brute_spiker: every field NO card covers where the
    # Halo 3 Spiker differs from the Halo 3 SMG (the yardstick) -- list 2 must say 0 to port
    'field_audit': {
        'source_kit': 'H3EK',
        'source': {'weapon': (SR + r'\spike_rifle.weapon', r'objects\weapons\rifle\smg\smg.weapon'),
                   'projectile': (SR + r'\projectiles\spike_shard\spike_shard.projectile',
                                  r'objects\weapons\rifle\smg\projectiles\smg_bullet.projectile'),
                   'damage_effect': (SR + r'\damage_effects\spike_rifle_spike.damage_effect',
                                     r'objects\weapons\rifle\smg\damage_effects\smg_bullet.damage_effect')},
        'target': {'weapon': (SR + r'\spike_rifle.weapon', SMG + r'\smg.weapon'),
                   'projectile': (SR + r'\projectiles\spike_rifle_spike.projectile',
                                  SMG + r'\projectiles\smg_bullet.projectile'),
                   'damage_effect': (SR + r'\damage_effects\spike_rifle_spike.damage_effect',
                                     SMG + r'\damage_effects\smg_bullet.damage_effect')},
        # 2026-10-21 (run as --port h2:brute_spiker: the key exists in ports_h1 too, and a bare
        # key reads Halo 1's). After the numbers' 4b rows, list 2 still prints rows the audit
        # PAIRS WRONGLY -- every one decided:
        'decisions': {
            'barrels minimum error / error angle (list 2)': "the audit pairs Halo 3's SINGLE spread with "
                "Halo 2's nth 0 = the DUAL error; written: single (nth 1) 0 / 0.5-1.25, dual (nth 0) "
                "0.25 / 0.75-1.5 (Halo 3's dual weapon error)",
            'barrels acceleration / deceleration time (list 2)': "Halo 3's DUAL error ramp (Spiker 0 / 0) "
                "-> Halo 2's dual ramp nth 2 = 0 / 0 (the audit names nth 0, the rate ramp: Halo 3's 1 / 0.2)",
            'dual wield damage scale': "Halo 3's 0.8 (DEFAULT); the balanced 0.667 is the SMG table's row",
            'material responses (lists 2 / 4 / 5)': "paired BY MATERIAL NAME, not index (Halo 3 16, the SMG "
                "clone 10): default_material impact (bounce chance 0), hard_metal_thick / hard_terrain "
                "impact + BOUNCE chance 1 at 0-60 deg / 20-30 wu/s, hard_metal_solid fizzle + bounce 1, "
                "brittle_glass fizzle, energy_shield_thick fizzle; angular noise 4, friction 0.35 / 0.7; "
                "liquid_thin / thick = Halo 3's already; hard_floodflesh (no Halo 3 entry) Halo 2's fizzle; "
                "soft_organic overpenetrate distance 0 (Halo 3: default = impact)",
            "projectile flags'": "Halo 3 262145 = bit 0 'oriented along velocity' (Halo 2's bit 0) + bit 18 "
                "(no Halo 2 name): 1",
            'detonation timer starts / timer': "Halo 3's 'when at rest', 1 s (Halo 2's enum 2)",
            'bounding offset': "the source's 0.075, 0, 0 (a 0 on the yardstick: no ratio)",
            'lightmap shadow mode': "Halo 2's (the SMG's 'default'; an enum)",
            'damage reporting type': "the SMG's kept (kill feed / medals only)",
            'active camo ding': "Halo 2's 0 (every H2 automatic carries 0)",
            'attachments / functions / font icons / ground / fp offset blocks / change colors':
                'no Halo 2 counterpart (the icon is step 8)',
            'ZERO-VALUED FIELDS': "h2_tagfield cannot probe a field reading 0: their offsets were found by "
                "probing a COPY (a byte flip / a float at each offset, tool's export says which field "
                "moved) and seeded in the per-tag cache; every write still proved by tool (one field)",
        }},

    # make_port_catalog_h2.py brute_spiker: the SMG table's rows (read from the H2 SMG's weapon /
    # projectile / damage effect) onto the Spiker's own; the MELEE rows onto its OWN blade melee
    # (strike_melee's rows x72/70, user 4a -- not dropped: the port names its own clone);
    # reload built = balanced (56 = 56 x 50/50)
    'catalog': {
        'table': 'balance_Spike_Rifle_Halo3_to_Halo2.json',
        'weapon_tag': SR + r'\spike_rifle',
        'port_tags': [(('weap', SMG + r'\smg'), SR + r'\spike_rifle'),
                      (('proj', SMG + r'\projectiles\smg_bullet'), SR + r'\projectiles\spike_rifle_spike'),
                      (('jpt!', SMG + r'\damage_effects\smg_bullet'), SR + r'\damage_effects\spike_rifle_spike'),
                      (('jpt!', r'objects\weapons\damage_effects\strike_melee'), SR + r'\damage_effects\spike_rifle_melee')],
        'shared': [],
        # user 4a: the spike keeps Halo 3's minimum velocity 12 (the SMG rule gave 0)
        'value_overrides': {'Minimum Velocity': 12.0},
        'fp_animations': r'objects\characters\*\fp\weapons\rifle\fp_spike_rifle\fp_spike_rifle',
        'reload_mult': None,
        'desc': ('%s carried from %s into Halo 2 with its own model, textures, sounds, blade melee and '
                 'its own Halo 3 first-person animations for both species -- dual wield included -- '
                 'balanced through the SMG.'),
    },

    # step 11 -- `python ai_firing_profile.py --h2-port brute_spiker`: Halo 3's ai\generic spike
    # rifle entry (010_jungle) name-for-name into H2EK ai\generic, over the H2 SMG's (the yardstick)
    'firing_profile': {'from_game': 'Halo 3', 'from_map': r'halo3\maps\010_jungle.map',
                       'from_weapon': r'objects\weapons\rifle\spike_rifle\spike_rifle',
                       'donor_weapon': r'objects\weapons\rifle\smg\smg'},
    'test': {'level': '08a_deltacliffs', 'dervish_level': '04b_floodlab', 'rounds': (40, 120)},   # parallel pair 1
    'residency': {'levels': 'all', 'placements': False},
}
