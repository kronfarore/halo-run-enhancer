r"""Grenade Launcher into Halo 2 (H2_PORT_PLAN.md wave B (Reach), #B4, "Step 5", alone) -- IN PROGRESS
(2026-11-24).

The port: Reach's model, textures, Spartan + Elite FP animations and sounds on a clone of Halo 2's FUEL ROD
(flak_cannon: latch, magazine, an explosive shot and a SECOND, unused barrel), firing grenades built on the
BRUTE SHOT's grenade (ballistic AI aim, the 'after first bounce off any surface' fuse). The charged pair is the
plasma pistol's ONE trigger: latch-autofire, secondary action charge, secondary barrel 1.
"""

import os as _os

GL = r'objects\weapons\rifle\grenade_launcher'      # the source's folder (HREK) AND the port's (H2EK)
FC = r'objects\weapons\support_high\flak_cannon'    # the weapon donor (H2EK)
BS = r'objects\weapons\support_low\brute_shot'      # the projectile donor (H2EK)
FX = r'effects\objects\weapons\rifle\grenade_launcher'   # the reserved effects folder
R = 'reach:'                                        # an HREK path (reach_tags)
RM = R + GL + r'\grenade_launcher.render_model'
WP = GL + r'\grenade_launcher.weapon'
PJ = GL + r'\projectiles\grenade_launcher_grenade.projectile'          # barrel 0: the bouncing grenade
PJC = GL + r'\projectiles\grenade_launcher_tethered_grenade.projectile'  # barrel 1: the charged release
DM = GL + r'\damage_effects'
# Reach's weapon nodes -> Halo 2's (b_ dropped; the root is Halo 2's `gun`)
NODES = {'b_gun': 'gun', 'b_chamber': 'chamber', 'b_handle': 'handle', 'b_ironsight': 'ironsight', 'b_grenade': 'grenade'}
NODES_JMS = dict((k, 'frame ' + v) for k, v in NODES.items())
# the DMR's shader seeds (Halo 2's human rifles)
BR = r'objects\weapons\rifle\battle_rifle'
SMG = r'objects\weapons\rifle\smg'
RL = r'objects\weapons\support_high\rocket_launcher'
PCI = r'objects\weapons\fixed\plasma_cannon'       # plasma_illum: the Needle Rifle's / PR's indicator template
RB = R + GL + r'\bitmaps' + '\\'
# Reach's display (shaders display / item / display_status / ones, Halo 1's B4 reading): self_illum_color RGB 14 /
# 152 / 193, intensity 3, albedo black -- a teal LCD. Halo 2 has no bloom: colour x intensity clipped (Halo 1's)
TEAL = (min(1.0, 3 * 14 / 255.0), min(1.0, 3 * 152 / 255.0), min(1.0, 3 * 193 / 255.0))
GLB = GL + r'\bitmaps' + '\\'
MAPS = {BR + r'\bitmaps\battle_rifle': GLB + 'grenade_launcher', BR + r'\bitmaps\battle_rifle_bump': GLB + 'grenade_launcher_bump',
        BR + r'\bitmaps\battle_rifle_bump_active_camo': GLB + 'grenade_launcher_bump'}
SMG_MAPS = {SMG + r'\bitmaps\smg': GLB + 'grenade_launcher', SMG + r'\bitmaps\smg_bump': GLB + 'grenade_launcher_bump',
            SMG + r'\bitmaps\smg_bump_active_camo': GLB + 'grenade_launcher_bump'}

PORT = {
    'order': 9,
    'wave': 'B4',
    'name': 'Grenade Launcher',
    'source': 'Halo Reach',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\rifle\\grenade_launcher\\grenade_launcher',
    'reservations': {
        'message_prefix': 'gl2',
        'glyph': 0xE146,
        'weapon_dir': 'objects\\weapons\\rifle\\grenade_launcher',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\grenade_launcher',
        'fp_graph': 'weapons\\rifle\\fp_grenade_launcher\\fp_grenade_launcher',
        'hud': 'ui\\hud\\grenade_launcher',
        'hud_bitmap_prefix': 'grenade_launcher_',
        'sound_dir': 'sound\\weapons\\grenade_launcher_port',
    },
    # The phase-0 proposal was the BRUTE SHOT (latch magazine, arcing explosive grenade, ballistic AI aim) under the
    # rule 'same block shape as the port (magazines, barrels) -- the expensive byte edit is a block insert'. The
    # charged pair (4a, user) needs TWO barrels; the Brute Shot has ONE, so the weapon is the FUEL ROD's (H2's
    # flak_cannon: latch, 1 magazine, explosive, weapon type undefined, no tracking, no world graph in its .model,
    # barrel 1 present and unused: secondary barrel -1). The Brute Shot keeps its part: its GRENADE is the
    # projectile template (ballistic AI aim, the fuse rule)
    'donor': {'weapon': FC + r'\flak_cannon', 'message_prefix': 'fc',
              'projectile': BS + r'\projectiles\grenade\grenade',
              'why': ("the charged pair needs two barrels: the Fuel Rod's weapon (latch, magazine 5 -> 1, a free barrel 1) "
                      "+ the Brute Shot's grenade (ballistic AI aim, 'after first bounce off any surface')")},
    'yardstick': {
        # step 4a, user 2026-11-24: reports/h2_grenade_launcher_4a.md (scratch gl4a_dump / gl4a_table / gl4a_ttk).
        # REACH (HREK, Halo 1's B4 reading): latch-tether, recovery 0.5 s, 1 / 8 / 16, reloads 1 (63 fr empty, 59
        # full), error 0.15 min, 0 -> 0.4, 12.5 -> 7.5 wu/s, gravity 0.7 / water 0.75, range 100, arming 0, minimum
        # velocity 0. IMPACT 25 `collision` (accel 0.5) + DETONATION 0..180 over 0.75 -> 2.25 (core 0.6,
        # `explosion_small`, accel 2); fuse 0.5 s 'after first bounce off any surface'; units > 5 wu/s detonate; world
        # 0-7 wu/s turn physical; world 75-90 deg at 7.5-14 wu/s detonates; else bounce, friction 0.42 / 0.42.
        # Release: 180 over 0.001 -> 1 (core 0.2, accel 3) + EMP 100 `emp` over 0.25 -> 2.5 (side effect emp).
        # Reach frag 0..160 over 0.675 -> 2.25, timer 0.6-0.65, arming 1.4, gravity 0.9, throw 10; Reach RL 200 +
        # 0..240 over 0.75 -> 2.5, 0.8 s, 2 / 4 / 8, 116 fr, 8 -> 16, 175, aim 5/60 10/25; Reach PP overcharge 200 emp.
        # HALO 2 (H2EK): frag 50..150 over 0.75 -> 1.75 (explosion_small, core 0.75, accel 2.25), timer 0.5 after
        # first bounce, arming 1.5, gravity 1.0 / 1.0, throw 10 (both bipeds), frictions 0.5 / 0.7; RL impact 150 +
        # 75..200 over 1 -> 2 (explosion_large), 0.8 s, 2 / 4 / 8, reload 5.0 s, 8 -> 20, range 175, autoaim 5/45,
        # magnetism 10/25, smash_melee; Fuel Rod 100 + 40..90 over 0.5 -> 1.5, 0.4 s, 5 / 20 / 30; Brute Shot 20
        # (bullet_fast) + 25..50 over 0.75 -> 1.5, 0.3 s, 4 / 12 / 16, fuse 0.2 any surface; PP overcharge 1 `emp`
        # (matg emp: shields x500, sentinel x500, enforcer x50, metal x1, flesh 0).
        'pick': 'Frag Grenade + Rocket Launcher for the holes',
        'reason': ("user 2026-11-24 (Halo 1's pick): the frag is the same damage family in both games (explosion_small; "
                   "Halo 2's own group by Reach's name); a thrown grenade's holes (rate, magazine, reload, range, aim, "
                   "melee, impact) by the Rocket Launcher ratio. The Brute Shot is Halo 2's role twin but cannot be a "
                   "ratio yardstick (Reach has none): a 5b peer, and it shows Halo 2 has Reach's own fuse rule. "
                   "HOLD + EMP (user): the plasma pistol's CHARGED PAIR, native in Halo 2 (one trigger: latch-autofire, "
                   "secondary action charge, barrel 1). FUSE (user): Reach's own 0.5 s after the first bounce off any "
                   "surface (Halo 1 had to use a fuse from launch). VEHICLE STALL (user): test Halo 2's unused damage "
                   "`side effect` emp + `emp radius` on the release. Legendary direct hits: Elite minor 2, Brute minor "
                   "2, Grunt / Jackal 1 (Original and Balanced alike); one shot every 2.6 s (Original) / 3.2 s"),
        # DEFAULT = Reach's own numbers (PORTING "Balance"); these are the BALANCED rows (the catalog's)
        'balanced': {
            # FRAG ratio: 180 x 150/160; lower: Reach 0 (unset) -> the sibling rule, 168.75 x 50/150; radius 0.75 x
            # 0.75/0.675, 2.25 x 1.75/2.25; core 0.6 x 0.75/0.6 (the frag's core = its inner radius)
            'damage': 168.75, 'damage_lower': 56.25, 'radius': (0.833, 1.75),
            # the impact is a HOLE (the frag has none) -> RL: 25 x 150/200
            'impact': 18.75,
            # the fuse, Reach's rule: 0.5 x 0.5/0.625 (the Reach frag's 0.6-0.65 mean); arming 0 x 1.5/1.4 = 0
            'timer': 0.4, 'arming': 0.0,
            # flight: the throw speed is 10 wu/s in both games -> x1; gravity 0.7 x 1.0/0.9, water 0.75 x 1.0/0.75
            'velocity': (12.5, 7.5), 'gravity': 0.778, 'water_gravity': 1.0,
            # HOLES -> the RL ratio: recovery 0.5 x 0.8/0.8; magazine 1 x 2/2, 8 x 4/4, 16 x 8/8; reload 63 fr x
            # 5.0 s / 116 fr (3.867 s) = 2.716 s; range 100 x 175/175; autoaim 4 x 5/5, 15 x 45/60; magnetism 8 x
            # 10/10, 15 x 25/25; melee Reach strike -> H2's smash_melee (the RL's)
            'fire_recovery_s': 0.5, 'magazine': 1, 'rounds_total_initial': 8, 'rounds_total_maximum': 16,
            'reload_s': 2.716, 'range': 100.0, 'autoaim': (4.0, 11.25), 'magnetism': (8.0, 15.0),
            # error: the RL's 0 / 0 is degenerate -> Reach's own 0.15 / 0..0.4 (no ratio)
            'error_deg': (0.15, 0.0, 0.4),
            # friction: Reach's 0.42 / 0.42 in both (no ratio: Halo 1's user pick)
            'friction': (0.42, 0.42),
            # the RELEASE (charged pair): the tethered blast by the frag ratio 168.75 over 0.001 x 0.75/0.675, 1 x
            # 1.75/2.25; the EMP by the plasma pistol OVERCHARGE (H2 1 x Reach EMP 100 / Reach overcharge 200) = 0.5
            # `emp` with `only hurts shields` (250 on any shield: strips every one), over 0.25 x 0.75/0.675, 2.5 x
            # 1.75/2.25
            'release_damage': 168.75, 'release_radius': (0.0011, 0.778),
            'emp': 0.5, 'emp_radius': (0.278, 1.944),
            'charge_s': 0.5},
        'candidates': {
            'provisional': 'Frag Grenade + Rocket Launcher for the holes',
            'alternatives': ['Rocket Launcher', 'Flak Cannon'],
            'direct': 'none',
            # the h2_role_compare names (the Flak Cannon is its 'Fuel Rod')
            'peers': ['Brute Shot', 'Rocket Launcher', 'Fuel Rod'],
            'why': "1-round latch-tether, bouncing grenade (H1 pick). H2 has no tether trigger (approximate as in H1); the Brute Shot is H2's own grenade launcher -- a peer only (no Reach Brute Shot)",
            'lacks': ("detonating a grenade already in flight (the release fires a contact-burst EMP grenade instead), "
                      "rolling ('turn physical': Halo 2's responses have none), the vehicle stall unless Halo 2's unused "
                      "`side effect` emp works (to test)"),
        },
    },
    # step 1 -- h2_port_geometry.py kind 'h3' with `reach:` paths (the DMR's route): Reach's ONE render model is world
    # AND first person; 5 nodes (b_gun; b_chamber turned 90 deg about z, its children b_handle / b_ironsight /
    # b_grenade), 1 mesh, 23 parts, 16 materials. Markers: primary_trigger (the bore); Reach's five muzzle_flash
    # (on b_chamber, at the bore) -> the first as `muzzle_flash`; the grip (right_hand, the origin) -> `flashlight`
    # (Halo 2's FP light: the Arbiter-flashlight rule); left_hand_spartan -> `left_hand_mc`. The skull counter
    # (skull_ones / skull_switch) dropped: no Halo 2 source for the skull count (Halo 1's B4)
    'geometry': {
        'kind': 'h3',
        'world_rm': RM, 'fp_rm': RM,
        'data_dir': GL,
        'world': 'grenade_launcher', 'fp': 'fp_grenade_launcher',
        # the ARM SWITCH (6 + 48 triangles): Reach colours it by a function (yellow at rest, red tethered) with no
        # map -- painted metal here; the charge cue is the attachments' (the Laser's way)
        'materials': {'grenade_launcher_composite': 'gl_composite', 'grenade_launcher_metal': 'gl_metal',
                      'grenade_launcher_metal_shiny': 'gl_metal_shiny', 'grenade_launcher_rubber': 'gl_rubber',
                      'unsc_decals_fp': 'gl_decals', 'arm_switch': 'gl_metal_shiny',
                      'arm_switch_projectile': 'gl_metal_shiny', 'display': 'gl_display',
                      'display_status': 'gl_display_status', 'grenade_launcher_glass': 'gl_glass',
                      'hundreds': 'gl_digits', 'tens': 'gl_digits', 'ones': 'gl_digits', 'item': 'gl_display_item',
                      'skull_ones': None, 'skull_switch': None},
        'world_permutation': 'base', 'world_region': 'gun',          # the BR .model's variants (the DMR's)
        'node_names': NODES_JMS,
        'markers': {'primary_trigger': 'primary_trigger', 'muzzle_flash': ['muzzle_flash', None, None, None, None],
                    'right_hand': 'flashlight', 'left_hand': 'left_hand', 'left_hand_elite': 'left_hand_elite',
                    'left_hand_spartan': 'left_hand_mc'},
        'muzzle_drop': 0.0,
        'ground_point': {'rot': (0.7071068883, -1.8e-09, -7.42e-08, -0.7071067095)},   # the SMG's (the AR's)
        'render': ['grenade_launcher', r'grenade_launcher\fp_grenade_launcher'],
        'fine_weld': True,                    # the DMR's boot 1: tool's 1/512 weld drops small triangles
    },

    # step 2 -- kind 'h3' with `reach:` bitmaps, 1024 -> 512 (the DMR's). Reach's composite / metal / shiny / rubber
    # all sample ONE diffuse + one DXN normal (zbump); shaders reseeded as the DMR's (BR metal / plastic, SMG bare
    # metal / rubber grip, BR lens on grey for the glass, the RL decal). Self-illum maps (dmr_illum /
    # battle_rifle_illum) are other weapons' -- off, as the DMR's. THE LCD (display_bg frame, gl_display_status
    # READY, gl_display_details_diffuse item, `numbers` 0 on hundreds / tens / ones): static, each tinted Reach's
    # teal on the indicator template (plasma_illum, additive) -- Halo 1's B4 look; the tether readout has no source
    'textures': {
        'kind': 'h3',
        'rel': GL + r'\bitmaps',
        'shaders_dir': GL + r'\shaders',
        'bump_gain': 1.0,
        'bitmaps': [(RB + 'grenade_launcher_diffuse.bitmap', 'grenade_launcher', BR + r'\bitmaps\battle_rifle', 'color', (512, 512)),
                    (RB + 'grenade_launcher_zbump.bitmap', 'grenade_launcher_bump', BR + r'\bitmaps\battle_rifle_bump', 'bump', (512, 512)),
                    (R + r'objects\bitmaps\decals\bitmaps\unsc_decals_diffuse.bitmap', 'grenade_launcher_decals',
                     RL + r'\bitmaps\rocket_launcher_decal', 'color', (512, 512)),
                    (RB + 'display_bg.bitmap', 'grenade_launcher_display', r'objects\weapons\rifle\shotgun\bitmaps\illum_sights',
                     ('tint', TEAL, 0), None),
                    (RB + 'gl_display_status.bitmap', 'grenade_launcher_display_status', r'objects\weapons\rifle\shotgun\bitmaps\illum_sights',
                     ('tint', TEAL, 0), None),
                    (RB + 'gl_display_details_diffuse.bitmap', 'grenade_launcher_display_item', r'objects\weapons\rifle\shotgun\bitmaps\illum_sights',
                     ('tint', TEAL, 0), None),
                    (RB + 'numbers.bitmap', 'grenade_launcher_digits', r'objects\weapons\rifle\shotgun\bitmaps\illum_sights',
                     ('tint', TEAL, 0), None)],
        'shaders': [
            ('gl_metal', BR + r'\shaders\battle_rifle_metal', MAPS),
            ('gl_composite', BR + r'\shaders\battle_rifle_plastic', MAPS),
            ('gl_rubber', SMG + r'\shaders\smg_rubber_grip', SMG_MAPS),
            ('gl_metal_shiny', SMG + r'\shaders\smg_bare_metal', SMG_MAPS),
            # Reach's glass (vehicle_glass env over the diffuse) = the BR's lens look on flat grey (the DMR's)
            ('gl_glass', BR + r'\shaders\battle_rifle_lens',
             {BR + r'\bitmaps\battle_rifle': r'shaders\default_bitmaps\bitmaps\gray_50_percent',
              BR + r'\bitmaps\battle_rifle_bump': r'shaders\default_bitmaps\bitmaps\default_vector'}),
            ('gl_decals', RL + r'\shaders\rocket_launcher_decal',
             {RL + r'\bitmaps\rocket_launcher_decal': GLB + 'grenade_launcher_decals'}),
            ('gl_display', PCI + r'\shaders\plasma_illum', {PCI + r'\bitmaps\plasma_cannon': GLB + 'grenade_launcher_display'}),
            ('gl_display_status', PCI + r'\shaders\plasma_illum', {PCI + r'\bitmaps\plasma_cannon': GLB + 'grenade_launcher_display_status'}),
            ('gl_display_item', PCI + r'\shaders\plasma_illum', {PCI + r'\bitmaps\plasma_cannon': GLB + 'grenade_launcher_display_item'}),
            ('gl_digits', PCI + r'\shaders\plasma_illum', {PCI + r'\bitmaps\plasma_cannon': GLB + 'grenade_launcher_digits'}),
        ],
        'report_rows': [(GLB + 'grenade_launcher_bump', 'the port'), (BR + r'\bitmaps\battle_rifle_bump', 'Bungie BR')],
    },

    # step 3 -- h2_port_weapon.py: the FUEL ROD's weapon (latch, magazine, barrel 1 free: the charged pair's), the BR's
    # graph-less human .model (the DMR's), two grenades on the BRUTE SHOT's (ballistic AI aim, the any-surface fuse)
    # with the FRAG's projectile model and detonation look; the impact the Brute Shot's (bullet_fast -> collision); the
    # EMP the plasma pistol OVERCHARGE's damage (Halo 2's `emp` group) as a PART of the release's detonation effect
    # (the frag detonation's lod-sound part made a jpt!: Halo 2 effects carry damage parts, Tartarus's hammer). An
    # effect part has NO OWNER (the Hammer's finding): the EMP strips the wielder's shield too when within its radius
    'weapon': {
        'weapon': WP,
        'clones': [(FC + r'\flak_cannon.weapon', WP),
                   (BR + r'\battle_rifle.model', GL + r'\grenade_launcher.model'),
                   (BS + r'\projectiles\grenade\grenade.projectile', PJ),
                   (BS + r'\projectiles\grenade\grenade.projectile', PJC),
                   (BS + r'\damage_effects\shot_grenade_explosion.damage_effect', DM + r'\grenade_launcher_explosion.damage_effect'),
                   (BS + r'\damage_effects\shot_grenade_explosion.damage_effect', DM + r'\grenade_launcher_tethered_explosion.damage_effect'),
                   (BS + r'\damage_effects\grenade_impact.damage_effect', DM + r'\grenade_launcher_impact.damage_effect'),
                   (r'objects\weapons\pistol\plasma_pistol\damage_effects\plasma_pistol_overcharge_bolt.damage_effect',
                    DM + r'\grenade_launcher_emp.damage_effect'),
                   (FC + r'\damage_effects\flak_cannon_trigger.damage_effect', DM + r'\grenade_launcher_trigger.damage_effect'),
                   (r'effects\objects\weapons\support_low\brute_shot\firing.effect', FX + r'\grenade_launcher_fire.effect'),
                   (r'effects\objects\weapons\rifle\battle_rifle\muzzle_flash.light', FX + r'\grenade_launcher_muzzle_flash.light'),
                   (r'effects\impact\explosion_small\frag_grenade\airborne_detonation.effect', FX + r'\detonation.effect'),
                   (r'effects\impact\explosion_small\frag_grenade\airborne_detonation.effect', FX + r'\tethered_detonation.effect'),
                   (r'effects\materials\objects\weapons\rocket_launcher.material_effects', FX + r'\grenade_launcher.material_effects'),
                   (r'effects\materials\objects\weapons\brute_shot.material_effects', FX + r'\grenade.material_effects'),
                   (r'effects\objects\weapons\support_low\brute_shot\projectile.light', FX + r'\grenade.light'),
                   (r'effects\objects\weapons\support_low\brute_shot\projectile.contrail', FX + r'\grenade.contrail')],
        # THE 3P LABEL: the Fuel Rod's missile / fc (a shoulder stance) -> the BR's rifle / br (the DMR's: Reach's GL is
        # held as a rifle; Marines and every Armed species took the DMR on it)
        'string_ids': {'missile': 'rifle', 'fc': 'br'},
        'string_ids_done': ('weapon name', 'br'),
        'string_id_renames': [(DM + r'\grenade_launcher_impact.damage_effect', {'bullet_fast': 'collision'})],
        'wiring': [
            (WP, 'hlmt', FC + r'\flak_cannon', GL + r'\grenade_launcher', 'world model', {'nth': 0}),
            (GL + r'\grenade_launcher.model', 'mode', BR + r'\battle_rifle', GL + r'\grenade_launcher', 'the world render model', {'nth': 0}),
            (WP, 'mode', FC + r'\flak_cannon', GL + r'\fp_grenade_launcher\fp_grenade_launcher', 'first person model, Master Chief', {'nth': 0}),
            (WP, 'mode', FC + r'\flak_cannon', GL + r'\fp_grenade_launcher\fp_grenade_launcher', 'first person model, Dervish (one model)', {'nth': 0}),
            (WP, 'jmad', r'objects\characters\masterchief\fp\weapons\support_high\fp_flak_cannon\fp_flak_cannon',
             r'objects\characters\masterchief\fp\weapons\rifle\fp_grenade_launcher\fp_grenade_launcher', "Master Chief FP graph: Reach's own animations"),
            (WP, 'jmad', r'objects\characters\dervish\fp\weapons\support_high\fp_flak_cannon\fp_flak_cannon',
             r'objects\characters\dervish\fp\weapons\rifle\fp_grenade_launcher\fp_grenade_launcher', "Dervish FP graph: Reach's Elite animations"),
            (WP, 'foot', r'effects\materials\objects\weapons\flak_cannon', FX + r'\grenade_launcher', 'material effects (the weapon)'),
            (WP, 'ligh', r'effects\objects\weapons\support_high\flak_cannon\muzzle_flash', FX + r'\grenade_launcher_muzzle_flash', 'the muzzle light (the BR\'s, not the fuel rod\'s green)'),
            (WP, 'nhdt', r'ui\hud\flak_cannon', r'ui\hud\grenade_launcher', 'its own HUD (step 7)'),
            (WP, 'proj', FC + r'\projectiles\flak_bolt\flak_bolt', PJ[:-len('.projectile')], 'barrel 0: the bouncing grenade'),
            (WP, 'proj', FC + r'\projectiles\flak_bolt', PJC[:-len('.projectile')], 'barrel 1: the charged release (the fuel rod\'s stale path)'),
            (WP, 'effe', r'effects\objects\weapons\support_high\flak_cannon\flak_bolt_fire', FX + r'\grenade_launcher_fire', 'firing effect, barrel 0'),
            (WP, 'jpt!', FC + r'\damage_effects\flak_cannon_trigger', DM + r'\grenade_launcher_trigger', 'firing damage, barrel 0'),
            # the two grenades: the frag's model, the port's detonations / damage / bounce effects
            (PJ, 'hlmt', BS + r'\projectiles\grenade\grenade', r'objects\weapons\grenade\frag_grenade\frag_grenade_projectile', 'the frag projectile model'),
            (PJ, 'foot', r'effects\materials\objects\weapons\brute_shot', FX + r'\grenade', 'bounce / impact material effects'),
            (PJ, 'ligh', r'effects\objects\weapons\support_low\brute_shot\projectile', FX + r'\grenade', 'the grenade light', {'nth': 0}),
            (PJ, 'cont', r'effects\objects\weapons\support_low\brute_shot\projectile', FX + r'\grenade', 'the grenade trail', {'nth': 0}),
            (PJ, 'effe', r'effects\impact\explosion_small\brute_shot\detonation', FX + r'\detonation', 'detonation effects (air + ground)', {'every': True}),
            (PJ, 'jpt!', BS + r'\damage_effects\shot_grenade_explosion', DM + r'\grenade_launcher_explosion', 'the blast'),
            (PJ, 'jpt!', BS + r'\damage_effects\grenade_impact', DM + r'\grenade_launcher_impact', 'the impact'),
            (PJC, 'hlmt', BS + r'\projectiles\grenade\grenade', r'objects\weapons\grenade\frag_grenade\frag_grenade_projectile', 'the frag projectile model'),
            (PJC, 'foot', r'effects\materials\objects\weapons\brute_shot', FX + r'\grenade', 'impact material effects'),
            (PJC, 'ligh', r'effects\objects\weapons\support_low\brute_shot\projectile', FX + r'\grenade', 'the grenade light', {'nth': 0}),
            (PJC, 'cont', r'effects\objects\weapons\support_low\brute_shot\projectile', FX + r'\grenade', 'the grenade trail', {'nth': 0}),
            (PJC, 'effe', r'effects\impact\explosion_small\brute_shot\detonation', FX + r'\tethered_detonation', 'the release burst + EMP (air + ground)', {'every': True}),
            (PJC, 'jpt!', BS + r'\damage_effects\shot_grenade_explosion', DM + r'\grenade_launcher_tethered_explosion', 'the tethered blast'),
            (PJC, 'jpt!', BS + r'\damage_effects\grenade_impact', DM + r'\grenade_launcher_impact', 'the impact'),
            # THE EMP: the release burst's lod-sound part -> a jpt! part, then the port's EMP
            (FX + r'\tethered_detonation.effect', 'snd!', r'sound_remastered\weapons\frag_grenade\frag_expl_lod',
             r'sound_remastered\weapons\frag_grenade\frag_expl_lod', 'the EMP part (was the lod sound)', {'class': 'jpt!'}),
            (FX + r'\tethered_detonation.effect', 'jpt!', r'sound_remastered\weapons\frag_grenade\frag_expl_lod',
             DM + r'\grenade_launcher_emp', 'the EMP (Halo 2\'s emp group, the plasma pistol overcharge\'s)'),
        ],
        # barrel 1's firing effect + firing damage are EMPTY in the fuel rod: filled by `python ports_h2\grenade_launcher.py
        # --barrel1` (the n-th `firing effects` chunk: wiring's record_from finds the first block of a name only)
        'shared': [(r'objects\weapons\damage_effects\smash_melee(_response)', "the Fuel Rod's = the RL's melee (4a: Reach strike -> H2 smash)"),
                   (r'objects\weapons\grenade\frag_grenade\frag_grenade_projectile', "the frag's projectile model (Bungie's)"),
                   (r'effects\objects\weapons\support_low\brute_shot\muzzle_flash', "the Brute Shot's muzzle light in its firing effect"),
                   (r'effects\objects\weapons\grenade\frag_grenade\smoke_trail', "the grenade smoke trail (the Brute Shot's)")],
    },

    # step 4 -- h2_port_numbers.py: REACH's OWN values (DEFAULT = Original, boot 1); the balanced rows are the catalog's.
    # THE CHARGED PAIR = the plasma pistol's trigger (latch-autofire, prediction charge, autofire 0.0667 / throw 0.5,
    # secondary action charge, secondary barrel 1, charging 0.5 s (Halo 1's B4), overcharged none, charged illumination
    # 1, trigger flags 0) on the Fuel Rod's trigger (latch, 'autofire single action only'); the zero fields placed from
    # the secondary barrel (the Laser's offsets, A2). THE BOUNCE: Reach's grenade carries an `old material responses`
    # block in Halo 2's own shape (default impact (detonate); potential bounce, never against units, chance 1, between
    # 0-70 deg, and 5-30 wu/s, frictions 0.3 / 0.55) -- its rule here, the friction 0.42 / 0.42 of 4a (Halo 1's pick
    # from Reach's newer block; 0.3 / 0.55 is the bounce boot's alternative). Velocity 12.5 -> 7.5 over acceleration
    # range 1 -> 10 wu (Reach's), fuse 0.5 s after the first bounce off any surface, range 100. The release grenade:
    # impact (detonate) on everything (units too)
    'numbers': {
        'numbers': [
            (WP, 'behavior', 'new triggers', 0, 0, 2),                                       # latch -> latch-autofire
            (WP, 'secondary barrel', 'new triggers', 0, 0, 1, {'anchor': ('behavior', 4)}),   # -1 -> 1
            (WP, 'prediction', 'new triggers', 0, 0, 2, {'anchor': ('secondary barrel', 2)}),  # none -> charge
            (WP, 'autofire time', 'new triggers', 0, 0, 0.06667, {'anchor': ('secondary barrel', 6)}),
            (WP, 'autofire throw', 'new triggers', 0, 0, 0.5, {'anchor': ('secondary barrel', 10)}),
            (WP, 'secondary action', 'new triggers', 0, 0, 1, {'anchor': ('secondary barrel', 14)}),   # fire -> charge
            (WP, 'charging time', 'new triggers', 0, 0, 0.5, {'anchor': ('secondary barrel', 18)}),
            (WP, 'charged illumination', 'new triggers', 0, 0, 1.0, {'anchor': ('secondary barrel', 30)}),
            (WP, 'flags', 'new triggers', 0, 0, 0),                                          # the plasma pistol's
            # the magazine: 1 / 8 / 16, one a reload; reload time 0 = Reach's animation (63 fr) drives it (the DMR's)
            (WP, 'rounds loaded maximum', 'magazines', 0, 0, 1),
            (WP, 'rounds reloaded', 'magazines', 0, 0, 1),
            (WP, 'rounds total initial', 'magazines', 0, 0, 8),
            (WP, 'rounds total maximum', 'magazines', 0, 0, 16),
            (WP, 'reload time', 'magazines', 0, 0, 0.0),
            # both barrels: recovery 0.5, the error 0.15 / 0 -> 0.4 (nth 1: the live struct)
            (WP, 'fire recovery time', 'barrels', 0, 0, 0.5),
            (WP, 'fire recovery time', 'barrels', 1, 0, 0.5),
            (WP, 'rounds per second', 'barrels', 1, 0, [0.0, 0.0]),
            (WP, 'minimum error', 'barrels', 0, 1, 0.15, {'anchor': ('projectiles per shot', 6)}),   # + distribution angle
            (WP, 'error angle', 'barrels', 0, 1, [0.0, 0.4]),
            (WP, 'minimum error', 'barrels', 1, 1, 0.15, {'anchor': ('projectiles per shot', 6)}),   # + distribution angle
            (WP, 'error angle', 'barrels', 1, 1, [0.0, 0.4]),
            # no zoom (the Fuel Rod's 2x)
            (WP, 'magnification levels', '', 0, 0, 0),
            (WP, 'autoaim angle', '', 0, 0, 4.0),
            (WP, 'autoaim range', '', 0, 0, 15.0),
            (WP, 'magnetism angle', '', 0, 1, 8.0),
            (WP, 'magnetism range', '', 0, 1, 15.0),
            (WP, 'first person weapon offset', '', 0, 0, [0.0, 0.0, 0.0]),
            # the bouncing grenade
            (PJ, 'timer', '', 0, 0, [0.5, 0.5]),
            (PJ, 'maximum range', '', 0, 0, 100.0, {'anchor': ('timer', 12)}),   # timer, minimum velocity, range
            (PJ, 'material effect radius', '', 0, 0, 0.35),
            (PJ, 'air gravity scale', '', 0, 0, 0.7),
            (PJ, 'water gravity scale', '', 0, 0, 0.75),
            (PJ, 'initial velocity', '', 0, 0, 12.5),
            (PJ, 'final velocity', '', 0, 0, 7.5),
            (PJ, 'acceleration range', '', 0, 0, [1.0, 10.0]),
                        (PJ, 'response', 'material responses', 0, 1, 4),           # potential: bounce
            (PJ, 'chance fraction', 'material responses', 0, 0, 1.0),
            (PJ, 'between', 'material responses', 0, 0, [0.0, 70.0]),
            (PJ, 'and', 'material responses', 0, 0, [5.0, 30.0], {'anchor': ('between', 8)}),
            (PJ, 'parallel friction', 'material responses', 0, 0, 0.42),
            (PJ, 'perpendicular friction', 'material responses', 0, 0, 0.42),
            # the release: the same flight, bursts on contact with anything
            (PJC, 'maximum range', '', 0, 0, 100.0, {'anchor': ('timer', 12)}),
            (PJC, 'material effect radius', '', 0, 0, 0.35),
            (PJC, 'air gravity scale', '', 0, 0, 0.7),
            (PJC, 'water gravity scale', '', 0, 0, 0.75),
            (PJC, 'initial velocity', '', 0, 0, 12.5),
            (PJC, 'final velocity', '', 0, 0, 7.5),
            (PJC, 'acceleration range', '', 0, 0, [1.0, 10.0]),
            (PJC, 'flags', 'material responses', 0, 1, 0),
            (PJC, 'response', 'material responses', 0, 1, 0),           # potential bounce -> impact (detonate)             # 'never against units' off: units burst it too
            # the blast: Reach 0..180 over 0.75 -> 2.25 (core 0.6, accel 2); lower 0 is unset -> the frag's sibling 1/3
            (DM + r'\grenade_launcher_explosion.damage_effect', 'damage lower bound', '', 0, 0, 60.0),
            (DM + r'\grenade_launcher_explosion.damage_effect', 'damage upper bound', '', 0, 0, [180.0, 180.0]),
            (DM + r'\grenade_launcher_explosion.damage_effect', 'radius', '', 0, 0, [0.75, 2.25]),
            (DM + r'\grenade_launcher_explosion.damage_effect', 'aoe core radius', '', 0, 0, 0.6),
            (DM + r'\grenade_launcher_explosion.damage_effect', 'instantaneous acceleration', '', 0, 0, 2.0),
            # the tethered blast: 180 over 0.001 -> 1 (core 0.2, accel 3)
            (DM + r'\grenade_launcher_tethered_explosion.damage_effect', 'damage lower bound', '', 0, 0, 60.0),
            (DM + r'\grenade_launcher_tethered_explosion.damage_effect', 'damage upper bound', '', 0, 0, [180.0, 180.0]),
            (DM + r'\grenade_launcher_tethered_explosion.damage_effect', 'radius', '', 0, 0, [0.001, 1.0]),
            (DM + r'\grenade_launcher_tethered_explosion.damage_effect', 'aoe core radius', '', 0, 0, 0.2),
            (DM + r'\grenade_launcher_tethered_explosion.damage_effect', 'instantaneous acceleration', '', 0, 0, 3.0),
            # the impact: 25 collision (the group: `weapon` string_id_renames), accel 0.5
            (DM + r'\grenade_launcher_impact.damage_effect', 'damage lower bound', '', 0, 0, 25.0),
            (DM + r'\grenade_launcher_impact.damage_effect', 'damage upper bound', '', 0, 0, [25.0, 25.0]),
            # THE EMP: Reach's 100 on Halo 2's `emp` group over 0.25 -> 2.5, `only hurts shields` (flags bit 6); the
            # vehicle-stall test (user 4a): side effect emp (3) + emp radius 2.5
            (DM + r'\grenade_launcher_emp.damage_effect', 'damage lower bound', '', 0, 0, 100.0),
            (DM + r'\grenade_launcher_emp.damage_effect', 'damage upper bound', '', 0, 0, [100.0, 100.0]),
            (DM + r'\grenade_launcher_emp.damage_effect', 'radius', '', 0, 0, [0.25, 2.5]),
            (DM + r'\grenade_launcher_emp.damage_effect', 'flags', '', 0, 1, 64, {'anchor': ('damage lower bound', -8)}),
            (DM + r'\grenade_launcher_emp.damage_effect', 'side effect', '', 0, 0, 3, {'anchor': ('damage lower bound', -12)}),
            (DM + r'\grenade_launcher_emp.damage_effect', 'emp radius', '', 0, 0, 2.5, {'anchor': ('damage lower bound', 76)}),   # shake radius + 4
        ],
        'skipped': [
            ('the tether (hold detonates the grenade in flight)', '4a (user): the plasma pistol charged pair; the release fires a contact-burst EMP grenade'),
            ("Reach's newer material responses (8: units slow bounce, world 0-7 turn physical, steep 7.5-14 detonate)",
             "Halo 2 has no 'turn physical'; Reach's own old-style block (one element) carried instead"),
            ('melee strike_melee', "the Fuel Rod's smash_melee = the RL's (4a: Reach strike -> Halo 2 smash), both versions (Halo 1's B4)"),
            ('reload time', "Reach's animation (63 fr empty / 59 full) drives it: the tag field 0"),
        ],
    },

    'firing_profile': {'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\grenade_launcher\\grenade_launcher', 'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}


def barrel1():
    """Fill barrel 1's EMPTY firing effect + firing damage (the Fuel Rod's barrel 1 carries a `firing effects`
    element with both references empty). h2_port_weapon's record_from finds the FIRST block of a name, which is
    barrel 0's; here the record is placed in the SECOND `firing effects` chunk at the same element offset as barrel
    0's filled one (chunks are written depth first in the order tool prints the blocks), and h2_tagref.fill_reference
    proves it with tool."""
    import re
    import struct
    import sys
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    import h2_tagref as R
    import h2_tagfield as tf
    path = _os.path.join(R.H2EK, 'tags', WP)
    for cls, new, field in (('effe', FX + r'\grenade_launcher_fire', 'firing effect'),
                            ('jpt!', DM + r'\grenade_launcher_trigger', 'firing damage')):
        x = tf.export(path)
        names = re.findall(r'<block name="([^"]*)"', x)
        which = [k + 1 for k, n in enumerate(names) if n == 'firing effects']   # chunk numbers (root = 0)
        if len(which) < 2:
            raise SystemExit('fewer than two firing effects blocks')
        data = open(path, 'rb').read()
        ch = tf.arrays(data)
        (a0, e0), (a1, e1) = ch[which[0]], ch[which[1]]
        want = cls.encode('latin-1')[::-1]
        rel = None
        for i in range(a0, e0 - 15, 4):
            if data[i:i + 4] == want and struct.unpack_from('<I', data, i + 8)[0] == len(new):
                rel = i - a0
                break
        if rel is None:
            raise SystemExit('barrel 0 has no %s record of the port\'s length' % cls)
        rec = a1 + rel
        n = struct.unpack_from('<I', data, rec + 8)[0]
        if n:
            print('   barrel 1 %s already filled (%d chars)' % (field, n))
            continue
        R.fill_reference(path, cls, new, field=field, record=rec)
        print('      (barrel 1 %s)' % field)


if __name__ == '__main__':
    import sys as _sys
    if '--barrel1' in _sys.argv:
        barrel1()
