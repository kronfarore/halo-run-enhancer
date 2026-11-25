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
PJE = GL + r'\projectiles\grenade_launcher_emp_burst.projectile'        # spawned by the release burst: the EMP
DM = GL + r'\damage_effects'
RS = r'data\sound\weapons'                          # source folders in MCC's haloreach sfx.fsb (.info)
NEW_HUD = r'ui\hud\bitmaps\new_hud'
GL_JMS = r'F:\SteamLibrary\steamapps\common\H2EK\data' + '\\' + GL + r'\render\grenade_launcher.jms'   # the HUD art's mesh
GL_GLOW = ('gl_display', 'gl_display_status', 'gl_display_item', 'gl_digits', 'gl_glass')   # left out of the drawings
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
                     ('tint', TEAL, 0), None),
                    # BOOT 1 (user): 'the glass panel with the drawn crosshair is empty' -- Reach paints the holo
                    # sight's reticle into the diffuse's ALPHA (frame, ring, side bars, drop ticks): Halo 1's B4 reading,
                    # levels (140, 235) over a 0.12 floor, teal (0.45, 0.95, 1.0), drawn ADDITIVE (see-through). Full
                    # 1024: the glass UVs cover 7 x 18 % of the map
                    (RB + 'grenade_launcher_diffuse.bitmap', 'grenade_launcher_sight', r'objects\weapons\rifle\shotgun\bitmaps\illum_sights',
                     ('levels', 3, (140, 235), 0.12, (0.45, 0.95, 1.0)), None)],
        'shaders': [
            ('gl_metal', BR + r'\shaders\battle_rifle_metal', MAPS),
            ('gl_composite', BR + r'\shaders\battle_rifle_plastic', MAPS),
            ('gl_rubber', SMG + r'\shaders\smg_rubber_grip', SMG_MAPS),
            ('gl_metal_shiny', SMG + r'\shaders\smg_bare_metal', SMG_MAPS),
            # the glass = the holo SIGHT (boot 1): its reticle additive on the indicator template (was the BR's lens on grey)
            ('gl_glass', PCI + r'\shaders\plasma_illum', {PCI + r'\bitmaps\plasma_cannon': GLB + 'grenade_launcher_sight'}),
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
                   (r'effects\materials\objects\weapons\rocket_launcher.material_effects', FX + r'\grenade_launcher.material_effects'),
                   (r'effects\materials\objects\weapons\brute_shot.material_effects', FX + r'\grenade.material_effects'),
                   (r'effects\objects\weapons\support_low\brute_shot\projectile.light', FX + r'\grenade.light'),
                   (r'effects\objects\weapons\support_low\brute_shot\projectile.contrail', FX + r'\grenade.contrail'),
                   # the grenade's flight loop (the Brute Shot's) and THE CHARGE CUE (the Laser's way, A2: the plasma
                   # pistol's charging loop + its overcharge lights and their flares, scaled `primary_charged`)
                   (r'sound\weapons\brute_shot\brute_shot_projectile\brute_shot_projectile.sound_looping', FX + r'\gl_projectile.sound_looping'),
                   (r'sound\weapons\plasma_pistol\charging.sound_looping', FX + r'\gl_charging.sound_looping'),
                   (r'effects\generic_lights\overcharge.light', FX + r'\gl_charge.light'),
                   (r'effects\generic_lights\overcharge_fp.light', FX + r'\gl_charge_fp.light'),
                   (r'effects\objects\weapons\pistol\plasma_pistol\overcharge.lens_flare', FX + r'\gl_light_flare.lens_flare'),
                   (r'effects\objects\weapons\pistol\plasma_pistol\overcharge_fp.lens_flare', FX + r'\gl_light_flare_fp.lens_flare'),
                   # BOOT 2 (user): 'the EMP charge should have an added EMP explosion effect for clarity' -- Reach
                   # plays its emp_pulse (cyan-blue electric wisps) in the release burst; Halo 2's nearest stock look is
                   # the PLASMA GRENADE's airborne burst. Nesting an effect as a part of the frag burst FAILED: a Halo 2
                   # effect part cannot be an effect (tool: 'invalid type effect', the whole burst dropped from the map);
                   # boot 3 the release burst WAS the plasma grenade's -- user: 'the normal explosion should stay and the
                   # other effect on top of it; try the Tartarus Gravity Hammer explosion effect'. A part CAN be an OBJECT
                   # (Sentinel emp_death spawns its wreckage): the release burst = the frag burst again, its lod-sound part
                   # an object part spawning PJE, a grenade that bursts at once with TARTARUS's hammer impact (ring,
                   # distortion ripple, arcs) and the EMP as its detonation damage. The hammer's own blast part (tartarus_
                   # hammer_explosion, its knockback) made a silent sound part; its marker melee_effect -> up (a burst has
                   # only the engine's points: the Gravity Hammer's A5 finding)
                   (r'effects\impact\explosion_small\frag_grenade\airborne_detonation.effect', FX + r'\tethered_detonation.effect'),
                   (BS + r'\projectiles\grenade\grenade.projectile', PJE),
                   (r'effects\objects\characters\brute\tartarus_hammer_impact.effect', FX + r'\emp_burst.effect')],
        # the charge lights' flares carry a colour ANIMATION (the pistol's dark green -> green, BGR; the Laser's boot 6):
        # -> Reach's tethered arm-switch red (255, 37, 0; dark 80, 10, 0)
        'byte_edits': [(FX + r'\gl_light_flare.lens_flare', '0320090036481c00000000000000000000ff0000',
                        '03200900000a500000000000000000000025ff00'),
                       (FX + r'\gl_light_flare_fp.lens_flare', '0320090036481c00000000000000000000ff0000',
                        '03200900000a500000000000000000000025ff00')],
        # (tag, class, path, marker, like class, scale function): the charge cue on the bore
        'append_attachments': [
            (WP, 'lsnd', FX + r'\gl_charging', 'primary_trigger', 'ligh', 'primary_charged'),
            (WP, 'ligh', FX + r'\gl_charge', 'primary_trigger', 'ligh', 'primary_charged'),
            (WP, 'ligh', FX + r'\gl_charge_fp', 'primary_trigger', 'ligh', 'primary_charged'),
        ],
        # THE 3P LABEL: the Fuel Rod's missile / fc (a shoulder stance) -> the BR's rifle / br (the DMR's: Reach's GL is
        # held as a rifle; Marines and every Armed species took the DMR on it)
        'string_ids': {'missile': 'rifle', 'fc': 'br'},
        'string_ids_done': ('weapon name', 'br'),
        'string_id_renames': [(DM + r'\grenade_launcher_impact.damage_effect', {'bullet_fast': 'collision'}),
                              (FX + r'\emp_burst.effect', {'melee_effect': 'up'})],
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
            (PJC, 'effe', r'effects\impact\explosion_small\brute_shot\detonation', FX + r'\tethered_detonation', 'the release burst (air + ground)', {'every': True}),
            (PJC, 'jpt!', BS + r'\damage_effects\shot_grenade_explosion', DM + r'\grenade_launcher_tethered_explosion', 'the tethered blast'),
            (PJC, 'jpt!', BS + r'\damage_effects\grenade_impact', DM + r'\grenade_launcher_impact', 'the impact'),
            # THE EMP: the release burst's lod-sound part -> an OBJECT part spawning PJE
            (FX + r'\tethered_detonation.effect', 'snd!', r'sound_remastered\weapons\frag_grenade\frag_expl_lod',
             r'sound_remastered\weapons\frag_grenade\frag_expl_lod', 'the EMP spawner part (was the lod sound)', {'class': 'proj'}),
            (FX + r'\tethered_detonation.effect', 'proj', r'sound_remastered\weapons\frag_grenade\frag_expl_lod',
             PJE[:-len('.projectile')], 'the EMP grenade, spawned in the burst'),
            # PJE: bursts at once (numbers) with the Tartarus hammer impact and the EMP
            # boot 4 (user): 'the extra projectile is not invisible' -> Bungie's NULL model (the invisible script anchor)
            (PJE, 'hlmt', BS + r'\projectiles\grenade\grenade', r'scenarios\objects\special\null\null', 'invisible: the null model'),
            (PJE, 'foot', r'effects\materials\objects\weapons\brute_shot', FX + r'\grenade', 'material effects'),
            (PJE, 'ligh', r'effects\objects\weapons\support_low\brute_shot\projectile', FX + r'\grenade', 'the grenade light', {'nth': 0}),
            (PJE, 'cont', r'effects\objects\weapons\support_low\brute_shot\projectile', FX + r'\grenade', 'the grenade trail', {'nth': 0}),
            (PJE, 'lsnd', r'sound\weapons\brute_shot\brute_shot_projectile\brute_shot_projectile', FX + r'\gl_projectile', 'the flight loop'),
            (PJE, 'effe', r'effects\impact\explosion_small\brute_shot\detonation', FX + r'\emp_burst', 'the EMP look: Tartarus\'s hammer impact', {'every': True}),
            (PJE, 'jpt!', BS + r'\damage_effects\shot_grenade_explosion', DM + r'\grenade_launcher_emp', 'the EMP (Halo 2\'s emp group, the plasma pistol overcharge\'s)'),
            (PJE, 'jpt!', BS + r'\damage_effects\grenade_impact', DM + r'\grenade_launcher_emp', 'impact (none: it never flies)'),
            # the hammer impact's own blast part (knockback) -> a silent sound part
            (FX + r'\emp_burst.effect', 'jpt!', r'objects\characters\brute\damage_effects\tartarus_hammer_explosion',
             r'objects\characters\brute\damage_effects\tartarus_hammer_explosion', "the hammer's blast part, made a sound", {'class': 'snd!'}),
            (FX + r'\emp_burst.effect', 'snd!', r'objects\characters\brute\damage_effects\tartarus_hammer_explosion',
             r'sound\weapons\grenade_launcher_port\gl_charge', "silent (the charge cue's 0.3 s lead)"),
            # the flight loop: the port's lsnd, its track Reach's grenade_launcher_proj loop (step 10)
            (PJ, 'lsnd', r'sound\weapons\brute_shot\brute_shot_projectile\brute_shot_projectile', FX + r'\gl_projectile', 'the flight loop'),
            (PJC, 'lsnd', r'sound\weapons\brute_shot\brute_shot_projectile\brute_shot_projectile', FX + r'\gl_projectile', 'the flight loop'),
            (FX + r'\gl_projectile.sound_looping', 'snd!', r'sound\weapons\brute_shot\brute_shot_projectile\brute_shot_proj\loop',
             r'sound\weapons\grenade_launcher_port\gl_proj', "the flight loop: Reach's"),
            # the charge loop: Reach's landmine beep (Halo 1's B4 charge cue), in + loop; its remastered twin -> itself
            (FX + r'\gl_charging.sound_looping', 'snd!', r'sound\weapons\plasma_pistol\startcharge',
             r'sound\weapons\grenade_launcher_port\gl_charge', "the charge start: Reach's landmine beep in"),
            (FX + r'\gl_charging.sound_looping', 'snd!', r'sound\weapons\plasma_pistol\charge',
             r'sound\weapons\grenade_launcher_port\gl_charge_loop', "the charge loop: Reach's landmine beep loop"),
            (FX + r'\gl_charging.sound_looping', 'lsnd', r'sound_remastered\weapons\plasma_pistol\charging',
             FX + r'\gl_charging', 'its remastered twin: itself (no plasma pistol sound left)'),
            (FX + r'\gl_charge.light', 'lens', r'effects\objects\weapons\pistol\plasma_pistol\overcharge', FX + r'\gl_light_flare', "the light's own flare"),
            (FX + r'\gl_charge_fp.light', 'lens', r'effects\objects\weapons\pistol\plasma_pistol\overcharge_fp', FX + r'\gl_light_flare_fp', "the FP light's own flare"),
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
            # step 4b (port_field_audit --port h2:grenade_launcher), list 2 / 4 / 3: Reach's own
            (WP, 'active camo ding', '', 0, 0, 0.75),
            (WP, 'illumination recovery time', 'barrels', 0, 0, 0.1),
            (WP, 'illumination recovery time', 'barrels', 1, 0, 0.1),
            (WP, 'firing noise', 'barrels', 0, 0, 2),                   # Reach's loud (the Fuel Rod's shout)
            (PJ, 'impact noise', '', 0, 0, 1),                          # Reach's medium (the Brute Shot's quiet)
            (PJ, 'water damage range', '', 0, 0, [0.0, 0.0]),
            (PJC, 'impact noise', '', 0, 0, 1),
            (PJC, 'water damage range', '', 0, 0, [0.0, 0.0]),
            ] + [row for dm in ('grenade_launcher_explosion', 'grenade_launcher_tethered_explosion') for row in (
                (DM + '\\' + dm + '.damage_effect', 'shake radius', '', 0, 0, 8.0),
                (DM + '\\' + dm + '.damage_effect', 'ai stun radius', '', 0, 0, 4.5, {'anchor': ('shake radius', -12)}),
                (DM + '\\' + dm + '.damage_effect', 'ai stun bounds', '', 0, 0, [1.0, 0.5], {'anchor': ('shake radius', -8)}),
                (DM + '\\' + dm + '.damage_effect', 'rider minimum transfer damage scale', '', 0, 0, 1.0,
                 {'anchor': ('instantaneous acceleration', 12)}))] + [
            # the EMP grenade (boot 3), spawned at rest inside the release burst: bursts after 0.01 s, never flies
            (PJE, 'detonation timer starts', '', 0, 0, 0),             # immediately (the Brute Shot's: any surface)
            (PJE, 'timer', '', 0, 0, [0.01, 0.01]),
            (PJE, 'initial velocity', '', 0, 0, 0.0),
            (PJE, 'final velocity', '', 0, 0, 0.0),
            (PJE, 'air gravity scale', '', 0, 0, 0.0),
            # BOOT 1 (user): 'early ammo warning is always on' -- the Brute Shot HUD's low CLIP cutoff 1 (rounds loaded
            # <= 1 = low): a 1-round magazine is always low -> 0 (warns only empty, as the RL's 1 of 2 does at its last)
            (r'ui\hud\grenade_launcher.new_hud_definition', 'low clip cutoff', '', 0, 0, 0),
            # the charge cue: the pistol's green lights -> Reach's tethered arm-switch red (Halo 1's ARM_RED)
            (FX + r'\gl_charge.light', 'diffuse upper bound', '', 0, 0, [1.0, 0.15, 0.0]),
            (FX + r'\gl_charge.light', 'specular upper bound', '', 0, 0, [1.0, 0.15, 0.0]),
            (FX + r'\gl_charge_fp.light', 'diffuse upper bound', '', 0, 0, [1.0, 0.15, 0.0]),
            (FX + r'\gl_charge_fp.light', 'specular upper bound', '', 0, 0, [1.0, 0.15, 0.0]),
        ],
        'skipped': [
            ('the tether (hold detonates the grenade in flight)', '4a (user): the plasma pistol charged pair; the release fires a contact-burst EMP grenade'),
            ("Reach's newer material responses (8: units slow bounce, world 0-7 turn physical, steep 7.5-14 detonate)",
             "Halo 2 has no 'turn physical'; Reach's own old-style block (one element) carried instead"),
            ('melee strike_melee', "the Fuel Rod's smash_melee = the RL's (4a: Reach strike -> Halo 2 smash), both versions (Halo 1's B4)"),
            ('reload time', "Reach's animation (63 fr empty / 59 full) drives it: the tag field 0"),
        ],
    },

    # step 5 -- the BR's authored hull (its .model is the port's, the DMR's) on the port's own world skeleton
    'collision': {
        'donor': BR + r'\battle_rifle',
        'port': GL + r'\grenade_launcher',
        'src': r'battle_rifle\collision\battle_rifle_collision.jms',
        'out': GL + r'\collision\grenade_launcher.jms',
        'port_render_jms': GL + r'\render\grenade_launcher.jms',
        'donor_render_jms': r'battle_rifle\render\battle_rifle_L5.jms',
        'max_growth': 1.25,
        'nodes_from_render': True,
    },

    # step 9 -- h2_port_fp_anims.py kind 'reach' (the DMR's route): Reach's OWN FP animations for BOTH species
    # (Spartan -> masterchief, Elite -> dervish), helpers dropped. Reach's GL graph is the DMR's shape: fire_1 x3,
    # reload_empty 63 / reload_full 59 (Elite 63), melee_strike_1 / 2, posing x2, ready / put_away, throw_grenade.
    # Not reproduced: sprint / jump / land / fall / ready_initial (no Halo 2 slot), throw_equipment (Elite)
    'fp_anims': {
        'kind': 'reach',
        'species': {
            'masterchief': {
                'graph': R + r'objects\characters\spartans\fp\weapons\rifle\fp_grenade_launcher\fp_grenade_launcher.model_animation_graph',
                'arms_rm': R + r'objects\characters\spartans\fp\fp.render_model',
                'arms': r'F:\SteamLibrary\steamapps\common\H2EK\data\!extracted\fp_arms_masterchief\fp_arms.jms',
                'source': r'objects\characters\masterchief\fp\weapons\rifle\fp_grenade_launcher',
                # the SMG for its 17 sound slots (the DMR's reason)
                'seed': r'objects\characters\masterchief\fp\weapons\rifle\fp_smg\fp_smg'},
            'dervish': {
                'graph': R + r'objects\characters\elite\fp\weapons\rifle\fp_grenade_launcher\fp_grenade_launcher.model_animation_graph',
                'arms_rm': R + r'objects\characters\elite\fp\fp.render_model',
                'arms': r'F:\SteamLibrary\steamapps\common\H2EK\data\!extracted\fp_arms_dervish\dervish_fp_arms.jms',
                'source': r'objects\characters\dervish\fp\weapons\rifle\fp_grenade_launcher',
                'seed': r'objects\characters\dervish\fp\weapons\rifle\fp_smg\fp_smg'},
        },
        'weapon_dir': GL + r'\fp_grenade_launcher',
        'weapon_rm': RM,
        'weapon_nodes': sorted(NODES.values()),
        'node_names': NODES,
        'drop_nodes': ('pedestal', 'aim_pitch', 'aim_yaw', 'l_humerus', 'r_humerus', 'l_radius', 'r_radius',
                       'l_handguard', 'r_handguard'),
        'aliases': {'first_person:look': ['first_person:overlays', 'first_person:pitch_and_turn']},
        # the FP position: the DMR's accepted (-0.005, -0.002, -0.033) moved by the two Reach weapons' own first-person
        # offsets (GL 0.0125, 0, 0; DMR 0, 0, -0.002): x +0.0125, z +0.002. The weapon field 0 (the gun-only rule)
        # boot 1 (user): 'move FP one unit down' -> z -0.041
        'model_offset': (0.0075, -0.002, -0.041),
        # the DMR's per-species hand corrections (Halo 2's hand meshes sit on their bones unlike Reach's; observations
        # of one port): judged here with h2_fp_hand_check palm / ortho before boot 1
        # h2_fp_hand_check palm (idle, gun frame, JMS units, + = the palm top BELOW the underside) with the DMR's
        # offsets: Chief +0.68, Arbiter -0.91; the DMR's accepted grips -0.70 / -0.30 -> z +1.38 / -0.61 units
        'left_arm_offset': {'masterchief': {'*': (0.0, 0.0, 0.0063)},
                            'dervish': {'*': (0.0, 0.006, 0.0007)}},
        'skip': ['first_person:look', 'first_person:acceleration_screens', 'first_person:fall', 'first_person:jump',
                 'first_person:land_hard', 'first_person:land_soft', 'first_person:ready_initial',
                 'first_person:sprint_enter', 'first_person:sprint_exit', 'first_person:sprint_loop',
                 'first_person:sprint_loop_airborne', 'first_person:throw_equipment'],
        'looping': ['first_person:idle', 'first_person:posing:var1', 'first_person:posing:var2'],
        'overlay_reference': 'first_person:idle',
        'weights': {'first_person:posing:var1': 0.5, 'first_person:posing:var2': 0.5},
        'drop_ik': ['masterchief'],
        'clear_sound_ref_flags': True,
        'clear_verify': True,
        # Reach's graph: one sound event an animation, at frame 0 (the DMR's measurement); the reloads one recording
        # each until the Balanced boot (B1 rule 5: split before it)
        'source_events': {'cues': {'first_person:melee_strike_1': [('gl_melee1', 0)],
                                   'first_person:melee_strike_2': [('gl_melee2', 0)],
                                   'first_person:posing:var1': [('gl_pose1', 0)],
                                   'first_person:posing:var2': [('gl_pose2', 0)],
                                   'first_person:ready': [('gl_ready', 0)],
                                   # before the Balanced boot (B1 rule 5; Balanced retimes the reload x1.29): Reach's ONE
                                   # recording (the same for both reloads) cut in its quiet gaps, each piece at its frame
                                   'first_person:reload_empty': [('gl_rl1', 0), ('gl_rl2', 19), ('gl_rl3', 40)],
                                   'first_person:reload_full': [('gl_rl1', 0), ('gl_rl2', 19), ('gl_rl3', 40)]},
                          # BOOT 2 (user: 'the red light and beep can run before the reload animation is done; releasing
                          # fires the contact burst' -- 'does the reload animation set the point the gun counts as
                          # reloaded?'): yes -- Reach's primary keyframe (27 of 63, 33 of 59) counts the round in Halo 2.
                          # Bungie's own Halo 2 reloads carry NO frame events (BR, SMG, RL, Brute Shot): the same here,
                          # the round counted at the animation's end. No dll (user: H1 left it, so H2 does too)
                          # BOOT 3 (user): 'the reload is counted far too late now' -> the round counts at Reach's own
                          # ALLOW INTERRUPTION frame (where Reach lets the player fire again): reload_empty 48 of 63,
                          # reload_full 38 of 59 (was the primary keyframe 27 / 33)
                          'frames': {'first_person:reload_empty': [('primary keyframe', 48), ('allow interruption', 48)],
                                     'first_person:reload_full': [('primary keyframe', 38), ('allow interruption', 38)]}},
    },

    # step 10 -- h2_port_sounds.py: Reach's OWN sounds from MCC's haloreach sfx.fsb (the DMR's `bank`), layered as
    # Reach's effects layer them: FIRE = grenade_launcher_fire + brute_shot_tails_ext (Reach's firing effect; Halo
    # 1's mix), the far layer in fire_lod (every remastered sweetener on it: the Mauler's / Laser's rule); the BURST =
    # the projectile's detonation sound (grenade_launcher_expl + frag_close_layer) + the effect's first part
    # (frag_expl_lod_far) + its second (expl_tail_outdoor): Reach's airborne_detonation layers; BOUNCES Reach's frag
    # (frag_bnc_dirt / metal: its own material effects'); DROPS Reach's disintegrator_drop (the GL's own material
    # effects); the flight loop grenade_launcher_proj; the CHARGE CUE Reach's landmine beep (Halo 1's B4). One
    # Spartan FP set for both species (Reach's grenade_launcher_elite_fp unused, as the DMR's)
    'sounds': {
        'weapon': WP,
        'fire_fx': FX + r'\grenade_launcher_fire.effect',
        'bank': 'haloreach',
        'audio': _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'out', 'h2_sounds', 'grenade_launcher'),
        'audio_key': 'Grenade Launcher',
        'h3_bank': {'gl_fire': [RS + r'\grenade_launcher\grenade_launcher_fire', RS + r'\brute_shot\brute_shot_tails_ext'],
                    'gl_fire_lod': [RS + r'\grenade_launcher\grenade_launcher_fire_lod'],
                    'gl_ready': [RS + r'\grenade_launcher\grenade_launcher_fp\grenade_launcher_ready'],
                    'gl_melee1': [RS + r'\grenade_launcher\grenade_launcher_fp\grenade_launcher_melee1'],
                    'gl_melee2': [RS + r'\grenade_launcher\grenade_launcher_fp\grenade_launcher_melee2'],
                    'gl_pose1': [RS + r'\grenade_launcher\grenade_launcher_fp\grenade_launcher_pose1'],
                    'gl_pose2': [RS + r'\grenade_launcher\grenade_launcher_fp\grenade_launcher_pose2'],
                    'gl_reload_e': [RS + r'\grenade_launcher\grenade_launcher_fp\grenade_launcher_reload_empty'],
                    'gl_reload_f': [RS + r'\grenade_launcher\grenade_launcher_fp\grenade_launcher_reload_full'],
                    'gl_expl': [RS + r'\grenade_launcher\grenade_launcher_expl', RS + r'\frag_grenade\frag_close_layer'],
                    'gl_expl_far': [RS + r'\frag_grenade\frag_expl_lod_far'],
                    'gl_tail': [RS + r'\surround_tails\outdoor\expl_tail_outdoor'],
                    'gl_proj': [RS + r'\grenade_launcher\grenade_launcher_proj\grenade_launcher_proj\loop'],
                    'gl_bounce': [RS + r'\frag_grenade\frag_bnc_dirt'],
                    'gl_bounce_metal': [RS + r'\frag_grenade\frag_bnc_metal'],
                    'gl_drop': [RS + r'\disintegrator\disintegrator_drop'],
                    'gl_drop_soft': [RS + r'\disintegrator\disintegrator_drop_soft'],
                    # the beep's `in` track is 1 s of SILENCE (rendered: peak 0). BOOT 1 (user): 'the charge sound
                    # starts too early -- occasionally a normal shot starts it' -> the lsnd's START = 0.3 s of that
                    # silence (`split` below: Halo 1's 0.3 s lead), then the beep loop: a tap stays silent
                    'gl_charge_silence': [RS + r'\equipment\landmine\landmine_beep\track1\in'],
                    'gl_charge_loop': [RS + r'\equipment\landmine\landmine_beep\track1\loop']},
        'sounds': {'gl_fire': ('gl_fire', 'weapon_fire'), 'gl_fire_lod': ('gl_fire_lod', 'weapon_fire'),
                   'gl_ready': ('gl_ready', 'weapon_ready'), 'gl_melee1': ('gl_melee1', 'weapon_melee'),
                   'gl_melee2': ('gl_melee2', 'weapon_melee'), 'gl_pose1': ('gl_pose1', 'weapon_animation'),
                   'gl_pose2': ('gl_pose2', 'weapon_animation'), 'gl_rl1': ('gl_rl1', 'weapon_reload'),
                   'gl_rl2': ('gl_rl2', 'weapon_reload'), 'gl_rl3': ('gl_rl3', 'weapon_reload'),
                   'gl_expl': ('gl_expl', 'projectile_detonation'), 'gl_expl_far': ('gl_expl_far', 'projectile_detonation'),
                   'gl_tail': ('gl_tail', 'projectile_detonation'), 'gl_proj': ('gl_proj', 'projectile_flyby'),
                   'gl_bounce': ('gl_bounce', 'object_impacts'), 'gl_bounce_metal': ('gl_bounce_metal', 'object_impacts'),
                   'gl_drop': ('gl_drop', 'object_impacts'), 'gl_drop_soft': ('gl_drop_soft', 'object_impacts'),
                   'gl_charge': ('gl_charge', 'weapon_charge'), 'gl_charge_loop': ('gl_charge_loop', 'weapon_charge')},
        'repoint_fx': [(r'sound\weapons\brute_shot\brute_shot_fire', 'gl_fire'),
                       (r'sound_remastered\weapons\brute_shot\brute_shot_lod', 'gl_fire_lod'),
                       (r'sound_remastered\weapons\brute_shot\bruteshot_lfe', 'gl_fire_lod'),
                       (r'sound_remastered\weapons\brute_shot\brute_shot_fire_mech', 'gl_fire_lod')],
        # the Fuel Rod's zoom sounds: no zoom (magnification levels 0) -> the ready, so nothing is borrowed
        'repoint_weapon': [(r'sound\weapons\beam_rifle\beam_rifle_zoom_in', 'gl_ready'),
                           (r'sound\weapons\beam_rifle\beam_rifle_zoom_out', 'gl_ready')],
        # the release burst (the frag's, as the tap's): its explosion -> Reach's far layer (its lod part spawns the EMP
        # grenade); the EMP grenade's own detonation sound silent (the Tartarus hits play in its hammer impact: KEPT for
        # boot 4, the user's call)
        'repoint_tags': [(FX + r'\tethered_detonation.effect', r'sound\weapons\frag_grenade\frag_expl', 'gl_expl_far'),
                         (PJE, r'sound\weapons\brute_shot\brute_round_explode', 'gl_charge'),
                         (PJ, r'sound\weapons\brute_shot\brute_round_explode', 'gl_expl'),
                         (PJC, r'sound\weapons\brute_shot\brute_round_explode', 'gl_expl'),
                         (FX + r'\detonation.effect', r'sound\weapons\frag_grenade\frag_expl', 'gl_expl_far'),
                         (FX + r'\detonation.effect', r'sound_remastered\weapons\frag_grenade\frag_expl_lod', 'gl_tail'),
                         (FX + r'\grenade.material_effects', r'sound\weapons\brute_shot\brute_shot_bounce', 'gl_bounce'),
                         (FX + r'\grenade.material_effects', r'sound\weapons\brute_shot\brute_shot_drop', 'gl_bounce'),
                         (FX + r'\grenade.material_effects', r'sound\weapons\brute_shot\brute_shot_drop_soft', 'gl_bounce'),
                         (FX + r'\grenade.material_effects', r'sound\weapons\rocket_launcher\rocket_launcher_drop', 'gl_bounce_metal'),
                         (FX + r'\grenade_launcher.material_effects', r'sound\weapons\rocket_launcher\rocket_launcher_drop', 'gl_drop'),
                         (FX + r'\grenade_launcher.material_effects', r'sound\weapons\rocket_launcher\rocket_launcher_drop_soft', 'gl_drop_soft'),
                         (FX + r'\grenade_launcher.material_effects', r'sound\weapons\rocket_launcher\rocket_expl', 'gl_drop'),
                         (FX + r'\grenade_launcher.material_effects', r'sound_remastered\weapons\rocket_launcher\projectile_exp\lod', 'gl_drop')],
        # the SMG seed's 17 references, all repointed; unused dual slots point at the ready
        'graph_sounds': (('smg_melee1', 'gl_melee1'), ('smg_ready', 'gl_ready'), ('smg_reload', 'gl_rl1'),
                         ('smg_reload_full', 'gl_rl2'), ('smg_dual_ready', 'gl_melee2'),
                         ('smg_posing_var0', 'gl_pose1'), ('smg_posing_var1', 'gl_pose2'),
                         ('smg_dual_reload_left', 'gl_rl3'), ('smg_dual_reload_right', 'gl_ready'),
                         ('smg_dual_posing_0_l', 'gl_ready'), ('smg_dual_posing_0_r', 'gl_ready'),
                         ('smg_dual_posing_1_l', 'gl_ready'), ('smg_dual_posing_1_r', 'gl_ready'),
                         ('smg_dual_posing_2_l', 'gl_ready'), ('smg_dual_posing_2_r', 'gl_ready'),
                         ('smg_dual_posing_3_l', 'gl_ready'), ('smg_dual_posing_3_r', 'gl_ready')),
        'graph_sound_dir': r'sound\weapons\smg' + '\\',
        'split': {'gl_charge': ('gl_charge_silence', 0.0, 0.3),
                  # the reload's quiet gaps (40 ms envelope, all three takes): ~0.64 s (a -30 dB lull), 1.32 s (-41..-60)
                  'gl_rl1': ('gl_reload_e', 0.0, 0.64), 'gl_rl2': ('gl_reload_e', 0.64, 1.32),
                  'gl_rl3': ('gl_reload_e', 1.32, None)},
        'gain': {},
        'boost': {},
        'backup': r'E:\HaloBackups\H2EK_grenade_launcher_before_sounds',
        'graph_backup': r'E:\HaloBackups\H2EK_grenade_launcher_graphs_before_sounds',
    },

    # step 7 -- the HUD: the BRUTE SHOT's (Halo 2's own grenade launcher: its grenade pips, its plate) cloned by the
    # meter step; the weapon already names ui\hud\grenade_launcher. ONE pip for a 1-round magazine on a 31 x 37 canvas
    # (registration top-left: the pip sits where the Brute Shot's first one does); the donor's own grenade pip (Reach's
    # GL chud draws no ammo pips of its own)
    'meter': {
        'donor_meter': NEW_HUD + r'\meters\brute_shot_meter',
        'rel': NEW_HUD + r'\meters',
        'name': 'grenade_launcher_meter',
        'donor_hud': r'ui\hud\brute_shot',
        'port_hud': r'ui\hud\grenade_launcher',
        'weapon': WP,
        'rounds': 1, 'rows': 1,
        'canvas': (31, 37), 'tick_w': 25,
        # BOOT 1 (user): 'the single pip looks odd -- use the frag grenade icon as in H1': Reach's HUD frag
        # (grenade_scematics #0, ink 40 x 54) at 25 x 34 (its aspect), the donor pip's lit colour
        'tick_art': {'h3': (R + r'ui\chud\bitmaps\grenade_scematics', 0), 'h': 34},
        'backpack': NEW_HUD + r'\backpack_weapons',
        'backpack_port': NEW_HUD + r'\grenade_launcher_backpack',
        'backpack_size': (62, 30),
        'model_3p': GL_JMS,
        'model_skip': GL_GLOW,
        'preview': 'grenade_launcher_meter_preview.png',
    },
    # the Brute Shot plate: 4 images (0 / 1 bright single / out, 2 / 3 their dim twins), every one repainted
    'hud_plate': {
        'rel': NEW_HUD + r'\backgrounds',
        'donor': NEW_HUD + r'\backgrounds\brute_shot_bkd',
        'other': NEW_HUD + r'\backgrounds\rocket_launcher_bkd',
        'name': 'grenade_launcher_bkd',
        'hud': r'ui\hud\grenade_launcher',
        'model_3p': GL_JMS,
        'model_skip': GL_GLOW,
        'fallback_box': (105, 191, 5, 34),
        'stretch': 1.4,
        'all_images': {'dim': {2: 0, 3: 1}},
    },
    # step 8 -- the pickup icon at the reserved U+E146, untinted (the H2 ICON RULE); fc_* -> gl2_*
    'glyph': {
        'box': (160, 62),
        'model_3p': GL_JMS,
        'model_skip': GL_GLOW,
        'tif': 'grenade_launcher_h2_glyph.tif',
        'colour': (255, 255, 255),
        'style': {'line': (255, 255, 255), 'body': (153, 153, 153), 'min_line': 14},   # the DMR's (Reach's dense mesh)
    },
    'messages': {
        'donor_prefix': 'fc', 'donor_icon': '&flak_cannon',
        'donor_name': 'Fuel Rod Cannon', 'port_name': 'Grenade Launcher',
        'names': [('rods for Fuel Rod Cannon', 'grenades for Grenade Launcher'),
                  ('rod for Fuel Rod Cannon', 'grenade for Grenade Launcher'),
                  ('a Fuel Rod Cannon', 'a Grenade Launcher')],
        'weapon': WP,
    },
    # Reach's crosshair (its chud: hud_reticles #12 at scale 1.3 -- the circle, side ticks, drop marks and a dim frame
    # -- and the AUTO square, the grenade_launcher sheet #1 at 0.5 with its right edge 47 units left). Sized by
    # Reach's chud units (1 unit = 1 px at 1080p, the PR's screenshot reading) / 1.117 (Halo 2's px a bitmap px):
    # #12's 441 px / 3 per unit x 1.3 = 191 units tall -> ink 171. The AUTO layer (h3_hud_art.sprite hands back 1 px a
    # chud unit at widget scale 1): ratio 0.5 / 1.3 = 0.385; its centre 47 + 31 / 2 x 0.5 = 54.75 units left = 42.1
    # main-sprite px (1.3 units a px). Halo 1's
    # pitch ladder (falcon pitch, crop + stretch) left out: #12 carries its own drop marks.
    # SUPERSAMPLING (Halo 1's B4, memory h1-reticle-supersample): Halo 1 had to draw from the stock sheets at ~0.5
    # screen px a sheet px; Halo 2 draws the port's OWN one-image bitmap at ~1.1 screen px a px and its bitmap widgets
    # have no scale field -- a finer bitmap cannot be drawn smaller, so the art is downsampled once from Reach's
    # native density straight to its on-screen size (the recipe's point: no shrink-then-magnify)
    'reticle': {
        'rel': NEW_HUD + r'\crosshairs',
        'donor': NEW_HUD + r'\crosshairs\hud_reticles',
        'donor_sequence': 18,                # the Brute Shot's crosshair (the cloned HUD's)
        'name': 'grenade_launcher_reticle',
        'hud': r'ui\hud\grenade_launcher',
        'footprint': 1.0,
        # BOOT 1 (user): 'pretty good, only missing some of the finer lines from Reach' = the PITCH LADDER (falcon\pitch,
        # Halo 1's layer). SIZE from the user's Reach screenshot (Halo 1's B4 record): the frame 74 x 224 px at 1080p
        # -> ink 224 / 1.117 = 200 (was 171 from chud units: Reach draws 1.17 px a unit at 1080p). The ladder: 10 deg =
        # 70 ladder px = 29.5 screen px = 25.2 units = 19.4 #12 px (1.3 units a px) -> 0.277 a ladder row, x 1.6 / 0.7
        # across = 0.634; Halo 1's window rows 275..600 (+30 .. -10), the 0 row (519.5) on the centre; static (Reach
        # scrolls it with the aim)
        'h3_art': {'sheet': R + r'ui\chud\bitmaps\hud_reticles', 'sequence': 12, 'yardstick': 12,
                   'target_ink': 200,
                   'layers': [((R + r'ui\chud\bitmaps\grenade_launcher', 1), 0.385, {'offset': (-42.1, 0.0)}),
                              (R + r'ui\chud\bitmaps\falcon\pitch.bitmap', 1.0,
                               {'crop': (0, 275, 64, 600), 'stretch': (0.634, 0.277), 'at': (32.0, 244.5)})]},
        'preview': 'grenade_launcher_reticle_preview.png',
    },

    # step 4b -- port_field_audit.py --port h2:grenade_launcher: the source pair (Reach's GL vs Reach's yardstick: the
    # RL weapon for the holes, the FRAG's projectile and blast) against the target pair (the port vs Halo 2's)
    'field_audit': {
        'source_kit': 'HREK',
        'source': {'weapon': (GL + r'\grenade_launcher.weapon', RL + r'\rocket_launcher.weapon'),
                   'projectile': (GL + r'\projectiles\grenade_launcher_grenade.projectile',
                                  r'objects\weapons\grenade\frag_grenade\frag_grenade.projectile'),
                   'damage_effect': (GL + r'\projectiles\damage_effects\grenade_launcher_grenade_explosion.damage_effect',
                                     r'objects\weapons\grenade\frag_grenade\damage_effects\frag_grenade_explosion.damage_effect')},
        'target': {'weapon': (WP, RL + r'\rocket_launcher.weapon'),
                   'projectile': (PJ, r'objects\weapons\grenade\frag_grenade\frag_grenade.projectile'),
                   'damage_effect': (DM + r'\grenade_launcher_explosion.damage_effect',
                                     r'objects\weapons\grenade\frag_grenade\damage_effects\frag_grenade_explosion.damage_effect')},
        # the first run (2026-11-24, before boot 1): list 2 written as Reach's (camo ding 0.75, illumination recovery 0.1
        # both barrels, water damage range 0, shake radius 8; the rest of list 2 were 4a's rows); list 4 written (impact
        # noise medium, AI stun 4.5 / 1-0.5 from Reach's = the frag's); list 3 decided:
        'decisions': {
            'magnification range 2,2 (source 0,0)': 'no zoom: magnification levels 0 makes the range unused',
            'magazines rounds 0 (the ammo item)': "h2_tagfield cannot reach the nested magazines block (the DMR's); unused in campaign",
            'max movement / turning acceleration / velocity 20 (source 0)': "the Fuel Rod clone's (an object-movement field; "
                                                                            "Reach's 0 = unset)",
            'trigger prediction / autofire / secondary action / charging / charged illumination / flags':
                "the plasma pistol's charged pair (4a, user): Reach's latch-tether has no Halo 2 twin",
            'reload time 0 (target 5)': "Reach's animation drives the reload (63 / 59 frames), the DMR's",
            'shots per fire 0,0 both barrels': "the Fuel Rod's own (it fires as 1)",
            'barrel 1 flags 1537': "the Fuel Rod's (can't fire while barrel 0 fires / recovers, tracks the projectile)",
            'magnetism angle / range (the FIRST pair) 0': "Halo 2's first pair is the melee magnetism the Fuel Rod sets 0; "
                                                          "Reach's 8 / 15 went into the live pair (nth 1)",
            'deviation angle 0 (source 2)': "Halo 2's 0 (no ratio: a zero on one side; the RL's)",
            'firing noise loud': "written (Reach's)",
            'weapon type undefined': "Reach's (the RL's 'rocket launcher' is the yardstick's, not the port's)",
            'damage (effect) reporting type': "the Fuel Rod's / Brute Shot's / frag's: Halo 2's enum has no 'grenade launcher'",
            'first person weapon offset 0': 'the position lives in fp_anims model_offset',
            'projectile flags 3 (AI ballistic, oriented along velocity)': "Reach's flags that exist in Halo 2",
            'timer / gravity / velocity / range / acceleration range': "Reach's own (Original); the ratio is the catalog's",
            'material responses (1 element)': "Reach's own old-style block (4a): Halo 2 has no turn physical",
            'rider minimum transfer damage scale 1': "written (Reach's; a zero on one side)",
            'no such field in Halo 2': 'functions, water density, falloff ranges, target tracking, zoom / ready time, '
                                       'max latch time to arm, flyby response, ai velocity scales',
        },
    },

    # step 11 -- `python ai_firing_profile.py --h2-port grenade_launcher`: Reach's ai\generic entry (m10) over the H2
    # BRUTE SHOT's (Halo 2's own grenade launcher: its ballistic AI entry is the base)
    'firing_profile': {'from_game': 'Halo Reach', 'from_map': r'haloreach\maps\m10.map',
                       'from_weapon': GL + r'\grenade_launcher',
                       'donor_weapon': BS + r'\brute_shot',
                       'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    # BALANCED (step 4a, user 2026-11-24: reports/h2_grenade_launcher_4a.md, the FRAG + RL holes). The table
    # (balance_port.py "Grenade Launcher" "Rocket Launcher" "Halo Reach" "Halo 2") is the plain RL ratio, the 4a
    # ALTERNATIVE: its rows are all dropped (no port_tags) and every row is written here from the yardstick's
    # `balanced`, `original` = the kit's (Reach's own). The weapon row FIRST (weapon_ports.weap_path reads it).
    # Barrel rows on BOTH barrels (index 'all': the charged pair's barrel 1). Melee: the shared smash_melee, no row
    'catalog': {
        'table': 'balance_Grenade_Launcher_HaloReach_to_Halo2.json',
        'weapon_tag': GL + r'\grenade_launcher',
        'port_tags': [],
        'shared': [('jpt!', r'objects\weapons\damage_effects\smash_melee')],
        'extra_rows': (
            [{'class': 'weap', 'tag': GL + r'\grenade_launcher', 'field': f, 'block': blk, 'value': v, 'card': card,
              'original': o, **({'nth': nth} if nth else {}), **({'index': 'all'} if blk == 'Barrels' else {}),
              'note': note}
             for f, blk, nth, v, o, card, note in (
                ('Autoaim Range', None, 0, 11.25, 15.0, 'Autoaim', "the RL ratio: 15 x 45 / 60"),
                ('Autoaim Angle', None, 0, 4.0, 4.0, 'Autoaim', "the RL ratio x1"),
                ('Magnetism Angle', None, 1, 8.0, 8.0, 'Autoaim', "the RL ratio x1"),
                ('Magnetism Range', None, 1, 15.0, 15.0, 'Autoaim', "the RL ratio x1"),
                ('Fire Recovery Time', 'Barrels', 0, 0.5, 0.5, 'Rate of Fire', "the RL ratio x1 (0.8 / 0.8); 15 ticks"),
                ('Minimum Error', 'Barrels', 1, 0.15, 0.15, 'Accuracy', "the RL's 0 is degenerate: Reach's own"),
                ('Error Angle Max', 'Barrels', 1, 0.4, 0.4, 'Accuracy', "the RL's 0 is degenerate: Reach's own"),
                ('Rounds Loaded Maximum', 'Magazines', 0, 1, 1, 'Magazine', "the RL ratio x1 (2 / 2)"),
                ('Rounds Reloaded', 'Magazines', 0, 1, 1, 'Magazine', "the RL ratio x1"),
                ('Rounds Total Initial', 'Magazines', 0, 8, 8, 'Magazine', "the RL ratio x1 (4 / 4)"),
                ('Rounds Inventory Maximum', 'Magazines', 0, 15, 15, 'Magazine', "16 total - 1 loaded (the RL ratio x1)"))]
            + [{'class': 'proj', 'tag': GL + '\\projectiles\\' + pj, 'field': f, 'block': None, 'value': v, 'card': card,
                'original': o, 'note': note}
               for pj in ('grenade_launcher_grenade', 'grenade_launcher_tethered_grenade')
               for f, v, o, card, note in (
                ('Initial Velocity', 12.5, 12.5, 'Projectile Velocity', 'the throw speed: 10 wu/s in both games, x1'),
                ('Final Velocity', 7.5, 7.5, 'Projectile Velocity', 'x1'),
                ('Air Gravity Scale', 0.778, 0.7, 'Projectile Gravity', 'the frag ratio: 0.7 x 1.0 / 0.9'),
                ('Water Gravity Scale', 1.0, 0.75, 'Projectile Gravity', 'the frag ratio: 0.75 x 1.0 / 0.75'),
                ('Maximum Range', 100.0, 100.0, 'Projectile Range', 'the RL ratio x1 (175 / 175)'))]
            + [{'class': 'proj', 'tag': GL + r'\projectiles\grenade_launcher_grenade', 'field': f, 'block': None,
                'value': 0.4, 'card': 'Fuse', 'original': 0.5,
                'note': "the frag ratio: 0.5 x 0.5 / 0.625 (Reach's rule, after the first bounce off any surface)"}
               for f in ('Timer', 'Timer Max')]
            + [{'class': 'jpt!', 'tag': DM + '\\' + dm, 'field': f, 'block': None, 'value': v, 'card': card,
                'original': o, 'note': note}
               for dm, f, v, o, card, note in (
                ('grenade_launcher_explosion', 'Damage Lower Bound', 56.25, 60.0, 'Explosion Damage',
                 "the sibling rule: 168.75 x the frag's 50 / 150 (Reach's 0 is unset)"),
                ('grenade_launcher_explosion', 'Damage Upper Bound', 168.75, 180.0, 'Explosion Damage', 'the frag ratio: 180 x 150 / 160'),
                ('grenade_launcher_explosion', 'Damage Upper Bound Max', 168.75, 180.0, 'Explosion Damage', 'the frag ratio'),
                ('grenade_launcher_explosion', 'Radius', 0.833, 0.75, 'Radius', 'the frag ratio: 0.75 x 0.75 / 0.675'),
                ('grenade_launcher_explosion', 'Radius Max', 1.75, 2.25, 'Radius', 'the frag ratio: 2.25 x 1.75 / 2.25'),
                ('grenade_launcher_explosion', 'Area Of Effect Core Radius', 0.833, 0.6, 'Radius', 'the frag ratio: 0.6 x 0.75 / 0.54'),
                ('grenade_launcher_explosion', 'Shake Radius', 8.889, 8.0, 'Radius', 'the frag ratio: 8 x 10 / 9 (4b list 2)'),
                ('grenade_launcher_impact', 'Damage Lower Bound', 18.75, 25.0, 'Impact Damage', "the hole by the RL: 25 x 150 / 200"),
                ('grenade_launcher_impact', 'Damage Upper Bound', 18.75, 25.0, 'Impact Damage', 'the RL ratio'),
                ('grenade_launcher_impact', 'Damage Upper Bound Max', 18.75, 25.0, 'Impact Damage', 'the RL ratio'),
                ('grenade_launcher_tethered_explosion', 'Damage Lower Bound', 56.25, 60.0, 'Explosion Damage', 'the release: as the blast'),
                ('grenade_launcher_tethered_explosion', 'Damage Upper Bound', 168.75, 180.0, 'Explosion Damage', 'the release: the frag ratio'),
                ('grenade_launcher_tethered_explosion', 'Damage Upper Bound Max', 168.75, 180.0, 'Explosion Damage', 'the release: the frag ratio'),
                ('grenade_launcher_tethered_explosion', 'Radius', 0.0011, 0.001, 'Radius', 'the release: 0.001 x 0.75 / 0.675'),
                ('grenade_launcher_tethered_explosion', 'Radius Max', 0.778, 1.0, 'Radius', 'the release: 1 x 1.75 / 2.25'),
                ('grenade_launcher_tethered_explosion', 'Area Of Effect Core Radius', 0.278, 0.2, 'Radius', 'the release: 0.2 x 0.75 / 0.54'),
                ('grenade_launcher_emp', 'Damage Lower Bound', 0.5, 100.0, 'EMP',
                 "the plasma pistol overcharge ratio: 100 x H2 1 / Reach 200 (Halo 2's emp group: shields x500)"),
                ('grenade_launcher_emp', 'Damage Upper Bound', 0.5, 100.0, 'EMP', 'the overcharge ratio'),
                ('grenade_launcher_emp', 'Damage Upper Bound Max', 0.5, 100.0, 'EMP', 'the overcharge ratio'),
                ('grenade_launcher_emp', 'Radius', 0.278, 0.25, 'EMP', 'the frag radius ratio: 0.25 x 0.75 / 0.675'),
                ('grenade_launcher_emp', 'Radius Max', 1.944, 2.5, 'EMP', 'the frag radius ratio: 2.5 x 1.75 / 2.25'),
                ('grenade_launcher_emp', 'EMP Radius', 1.944, 2.5, 'EMP', "the vehicle-stall test's radius, as the EMP's"))]),
        'fp_animations': r'objects\characters\*\fp\weapons\rifle\fp_grenade_launcher\fp_grenade_launcher',
        # the reload by the RL ratio: Reach's 63 fr (2.1 s) x H2 RL 5.0 s / Reach RL 116 fr (3.867 s) = 2.716 s
        'reload_mult': round(2.716 / 2.1, 6),
        'desc': ("Halo Reach's Grenade Launcher carried into Halo 2 with its own model, textures, sounds and its own "
                 "Reach first-person animations for both species: a tap fires a bouncing grenade that bursts half a "
                 "second after its first bounce or on an enemy; hold for half a second and release to fire a grenade "
                 "that bursts on contact with an EMP that strips shields. One round, reloaded after every shot. "
                 "Balanced through the Frag Grenade and the Rocket Launcher."),
    },

    # the Arbiter / Balanced boot moves to Sacred Icon (user, boot 1: 'test the vehicle stall on a map like Sacred
    # Icon, that starts with vehicles later -- combined with the Arbiter test')
    # boot 3 (user): 'I said Sacred Icon, my mistake -- it's the next level: Quarantine Zone for the vehicle'
    'test': {'level': '03a_oldmombasa', 'dervish_level': '06b_floodzone'},
    'residency': {'levels': 'all', 'placements': False},
}

# BOOT LOG (CLASSIC)
#   boot 1 Outskirts ORIGINAL (2026-11-24, user): tap / hold fire the two grenades; bounce + any-surface fuse work; the
#     EMP strips the shield completely (tested on himself, god shield), the plain blast does nothing to it; animations,
#     world model, trade, pickup message + icon good. Fixed for boot 2: FP 1 unit down; the pip -> Reach's HUD frag
#     icon (Halo 1's); the crosshair + Reach's pitch ladder ('finer lines') at the screenshot's size; the holo sight
#     (diffuse alpha, additive teal); low clip cutoff 1 -> 0 (the warning was always on); the charge sound's 0.3 s
#     silent lead (a tap started it). Open: the charge during the RELOAD (user: 'reloading shouldn't allow the
#     charge'); the vehicle stall (Sacred Icon)


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
