r"""Plasma Repeater into Halo 2 (H2_PORT_PLAN.md wave B (Reach), #B3) -- a phase-0 STUB (2026-10-20):
reservations, yardstick candidates, the proposed donor and the AI source. The port session fills
the pipeline sections (ports_h2/__init__.py; ports_h2/saw.py is the complete example) and sets
'status' to 'in progress' at its start, 'done' at its end.

The port (2026-11-21, alone): Reach's model, textures, Spartan + Elite FP animations and sounds on a clone of
Halo 2's PLASMA RIFLE (spew, heat + battery, its heat gauge shader, its overheat states and HUD), dual wield
cleared. Halo 2's Plasma Rifle skeleton (gun, rod_left / wing_left, rod_right / wing_right) is Reach's repeater's
by name, plus Reach's cylinder and cowl.
"""

RP = r'objects\weapons\rifle\plasma_repeater'       # the source's folder (HREK) AND the port's (H2EK)
PRW = r'objects\weapons\rifle\plasma_rifle'         # the donor and yardstick (H2EK)
FX = r'effects\objects\weapons\rifle\plasma_repeater'   # the reserved effects folder
PRFX = r'effects\objects\weapons\rifle\plasma_rifle'
R = 'reach:'                                        # an HREK path (reach_tags)
RM = R + RP + r'\plasma_repeater.render_model'
H2EK = r'F:\SteamLibrary\steamapps\common\H2EK'
NEW_HUD = r'ui\hud\bitmaps\new_hud'
RP_JMS = H2EK + r'\data' + '\\' + RP + r'\render\plasma_repeater.jms'   # the mesh the HUD art is drawn from
RS = r'data\sound\weapons'                          # source folders in MCC's haloreach sfx.fsb (.info)
# Reach's weapon nodes -> Halo 2's (the Plasma Rifle's names for the five it shares)
NODES = {'b_gun': 'gun', 'b_rod_left': 'rod_left', 'b_wing_left': 'wing_left', 'b_rod_right': 'rod_right',
         'b_wing_right': 'wing_right', 'b_cylinder': 'cylinder', 'b_cowl': 'cowl'}
NODES_JMS = dict((k, 'frame ' + v) for k, v in NODES.items())
HOLO = r'objects\weapons\support_high\plasma_launcher\bitmaps\plasma_launcher_holo.bitmap'   # Reach's display atlas
CC = r'objects\weapons\rifle\covenant_carbine'      # its .model: a Covenant weapon model with NO world graph
WP = RP + r'\plasma_repeater.weapon'
PJ = RP + r'\projectiles\plasma_repeater_bolt.projectile'
DM = RP + r'\damage_effects'
MAT = r'effects\materials\objects\weapons'
# the PR heat gauge's functions (h2 `data` blocks) and the port's (see `weapon` function_edits)
PR_ON_COLOR = '0220030000ff000000000000000000000000ff00000000000000803f000000000000803f'
RP_ON_COLOR = '02200300f4ff59000000000000000000' + '17b5ff00' + '000000000000803f000000000000803f'
PR_OFF_COLOR = '01200000ff6666ff0000000000000000000000000000803f0000803f'
RP_OFF_COLOR = '01200000656a26ff0000000000000000000000000000803f0000803f'
PR_OFF_OPACITY = '03000a000000003f83c02a3f00000000000000000000803f00000000000000000000803f0000803f00000000000000000000803f'
RP_OFF_OPACITY = '03000a000000003f0000003f00000000000000000000803f00000000000000000000803f0000803f00000000000000000000803f'
PR_METER_VALUE = '02000000000000000000803f0000000000000000000000000000803f000000000000803f'
RP_DISPLAY_VALUE = '020000000000803f0000803f0000000000000000000000000000803f000000000000803f'
PR_MAPS = {PRW + r'\bitmaps\plasma_rifle_bump_active_camo': RP + r'\bitmaps\plasma_repeater_bump',
           PRW + r'\bitmaps\plasma_rifle_bump': RP + r'\bitmaps\plasma_repeater_bump',
           PRW + r'\bitmaps\plasma_rifle': RP + r'\bitmaps\plasma_repeater'}
import os as _os

PORT = {
    'order': 8,
    'wave': 'B3',
    'name': 'Plasma Repeater',
    'source': 'Halo Reach',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\rifle\\plasma_repeater\\plasma_repeater',
    'reservations': {
        'message_prefix': 'rp2',
        'glyph': 0xE145,
        'weapon_dir': 'objects\\weapons\\rifle\\plasma_repeater',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\plasma_repeater',
        'fp_graph': 'weapons\\rifle\\fp_plasma_repeater\\fp_plasma_repeater',
        'hud': 'ui\\hud\\plasma_repeater',
        'hud_bitmap_prefix': 'plasma_repeater_',
        'sound_dir': 'sound\\weapons\\plasma_repeater_port',
    },
    # PROPOSED (h2_phase0/h2_phase0_yardsticks.md): same block shape as the port (magazines,
    # barrels) -- the expensive byte edit is a block insert; fields are cheap
    'donor': {'weapon': 'objects\\weapons\\rifle\\plasma_rifle\\plasma_rifle', 'message_prefix': 'pr',
              'why': 'spew heat automatic + battery + rate ramp; clear dual wield. Alt: brute_plasma_rifle (bpr)'},
    'yardstick': {
        # step 4a, user 2026-11-21: reports/h2_plasma_repeater_4a.md; balance_Plasma_Repeater_HaloReach_to_Halo2.json
        # (balance_port.py "Plasma Repeater" "Plasma Rifle" "Halo Reach" "Halo 2")
        'pick': 'Plasma Rifle',
        'reason': ("user 2026-11-21: the Plasma Rifle -- Halo 2's carries Reach's Plasma Rifle tag numbers (rate 6 -> 9 / "
                   "0.8 s, heat 0.15, loss 0.8525 / 0.35, recovery 0.1, 6-10, battery 0.0025, range 40, magnetism 9 / "
                   "18), so the ratio is x1 on every heat, rate, damage, battery and range row. Balanced = Reach's own "
                   "but bolt speed 25 -> 35 x0.56 = 14 -> 19.6, single-wield error 0.4-3 x0.19 / 0.21 = 0.077-0.64 "
                   "(min 0), autoaim angle 5 x1.2 = 6. HEAT, approximation A (user): the OVERHEAT stands in for "
                   "Reach's manual vent (no dll vent: user), the rate falls 15 -> 3 over 1.6 s HELD (fitted: every "
                   "shot within 0.1 s of Reach's heat^1.5 curve to full heat), heat 0.0915 a round with loss 0.25 "
                   "(Reach's cold loss) -> overheats on round 15 at 1.48 s (Reach full on 14-15), overheated loss "
                   "0.36 to recovery 0.1 = Reach's 2.5 s vent, deceleration 3.6 s (the meter drains with the rate). "
                   "MATERIALS (user): Halo 2's own plasma_fast group, Reach's group by name. Melee Halo 2's "
                   "strike_melee. Legendary: Elite 24 / 4.53 s, Brute 39 / 8.52 s, Grunt 7 / 0.45 s, Jackal 10 / "
                   "0.73 s (Plasma Rifle 4.76 / 10.87 / 0.46 / 0.71). Halo 2's per-tick fire rule is unmeasured: "
                   "probe it on boot 1 before any re-fit"),
        # BOOT 1 (2026-11-22, Outskirts Original): no overheat at 1.5 s; battery 100 -> 78 = 44 rounds to the overheat.
        # HALO 2 FIRES LIKE HALO 1 (reports/h2_fire_rule.jsonl): rate/30 a 30 Hz tick in float32, a shot when the sum
        # reaches 1, the sum RESET (15/s fires 10/s); that rule simulates the overheat on round 44 exactly. Refit under it
        # (Halo 1's B3 trigger): 20 -> 3.05 over 1.5 s = 15 -> 3/s, Reach's round count to 1 s / 1.58 s (12 / 15); loss
        # 0.09 (Reach's loss at mid heat, 0.08-0.09; its cold 0.25 left the 3/s tail at +0.026/s: x0.93 heat = round 57)
        # and heat 0.076 -> overheat on round 15 at 1.53 s, rounds 14-17 for heat x1.07 / x0.93 (tail +0.138/s)
        'heat': {'rate': (20.0, 3.05), 'accel': 1.5, 'decel': 3.6, 'heat_per_round': 0.076, 'heat_loss': 0.09,
                 'overheated_loss': 0.36, 'recovery': 0.1, 'overheated_threshold': 1.0},
        'candidates': {
            'provisional': 'Plasma Rifle',
            'alternatives': ['Plasma Pistol'],
            'direct': 'Elite: carries the Plasma Rifle in both (= the provisional)',
            'peers': ['Plasma Rifle', 'Brute Plasma Rifle', 'SMG', 'Needler'],
            'why': "heat automatic plasma + battery, rate 15 -> 3 with heat (H1 pick). H2's trigger RAMPS over held time (6 -> 9) like Halo 1: H1's approximation B carries over",
            'lacks': ("the manual vent (and venting part-way), a rate tied to HEAT (Halo 2: to the held time), firing "
                      "on at 3/s when hot (Halo 2 overheats instead), Reach's slow hot cooling (0.06/s; one loss 0.25)"),
        },
    },
    # step 1 -- h2_port_geometry.py kind 'h3' with `reach:` paths (the DMR's route): Reach's ONE render model is world
    # AND first person; 7 nodes, 1 mesh, 12 parts, 7 materials. Markers onto the Plasma Rifle's names (its effects
    # and attachments name them): Reach's two STAGGERED muzzles (z 0.005 first, 0.048 second) -> the PR's lower
    # `primary_trigger1` (lower_fire) and upper `primary_trigger` (upper_fire); fx_vent x2 -> `vent` (the
    # overheated effect); firing_light -> `muzzle_flash` (the PR's light attachment); the grip (right_hand, the
    # origin) -> `flashlight` (Halo 2's FP light hangs on the FP model's marker: the Arbiter-flashlight rule);
    # left_hand_spartan -> the PR's `left_hand_mc`. No `heat_flare` markers: Reach has no lens flares there
    'geometry': {
        'kind': 'h3',
        'world_rm': RM, 'fp_rm': RM,
        'data_dir': RP,
        'world': 'plasma_repeater', 'fp': 'fp_plasma_repeater',
        'materials': {'plasma_repeater_metal': 'plasma_repeater_metal', 'plasma_repeater_rubber': 'plasma_repeater_rubber',
                      'plasma_repeater_shell': 'plasma_repeater_shell', 'plasma_repeater_indicator': 'plasma_repeater_indicator',
                      'plasma_repeater_display': 'plasma_repeater_display', 'plasma_repeater_gauge': 'plasma_repeater_gauge',
                      'plasma_repeater_pilot': 'plasma_repeater_pilot'},
        'world_permutation': 'default', 'world_region': 'default',   # the PR .model / render model's names
        'node_names': NODES_JMS,
        'markers': {'primary_trigger': ['primary_trigger1', 'primary_trigger'], 'fx_vent': 'vent',
                    'firing_light': 'muzzle_flash', 'right_hand': 'flashlight',
                    'left_hand': 'left_hand', 'left_hand_elite': 'left_hand_elite', 'left_hand_spartan': 'left_hand_mc'},
        'muzzle_drop': 0.0,
        'ground_point': {'rot': (0.7071068883, -1.8e-09, -7.42e-08, -0.7071067095)},   # the SMG's (the AR's)
        'render': ['plasma_repeater', r'plasma_repeater\fp_plasma_repeater'],
        'fine_weld': True,                    # the DMR's boot 1: tool's 1/512 weld drops small triangles
    },

    # step 2 -- kind 'h3' with `reach:` bitmaps, 1024 -> 512 (the DMR's). Reach's materials: metal (heat-tinted:
    # no Halo 2 twin, the PR's carapace env instead), shell (its illum map plasma_repeater_illum is NOT in HREK:
    # off, Halo 1's reading), rubber, the GAUGE (a meter: fill + colour by heat), the DISPLAY (holo lines whose
    # colour follows heat), the INDICATOR (teal halogram) and the PILOT (a noise halogram flame).
    # THE GAUGE = Halo 2's own Plasma Rifle heat gauge (meter_active_camo: meter value AND on-colour by `heat`,
    # what Halo 1 had to build from a ramp + a multiply copy). Its fill order lives in the METER map's alpha, its
    # shape in the ALPHA map (the Flamethrower's boot 23): the meter map a linear u ramp over Reach's lit window
    # (its own alpha ramp is 0 over the left half: Halo 1's gradient_range 0.02..0.95), the shape Reach's gauge RGB.
    # THE DISPLAY = the same template held fully lit (meter value 1: `weapon` function_edits), shape the holo
    # atlas (plasma_launcher_holo, the display's UVs cover it), so only its colour moves with heat (Halo 1's look)
    'textures': {
        'kind': 'h3',
        'rel': RP + r'\bitmaps',
        'shaders_dir': RP + r'\shaders',
        'bump_gain': 1.0,
        'bitmaps': [(R + RP + r'\bitmaps\plasma_repeater_diffuse.bitmap', 'plasma_repeater', PRW + r'\bitmaps\plasma_rifle', 'color', (512, 512)),
                    (R + RP + r'\bitmaps\plasma_repeater_normal.bitmap', 'plasma_repeater_bump', PRW + r'\bitmaps\plasma_rifle_bump', 'bump', (512, 512)),
                    (None, 'plasma_repeater_gauge_meter', PRW + r'\bitmaps\plasma_rifle_heat_gauge',
                     ('gradient', 'u', False, (0.02, 0.95), 'alpha'), (128, 32)),
                    # BOOT 1 ('the dim light is not completely filling the entire bar; the overheat bar doesn't reach
                    # the maximum'): Reach's gauge RGB is only its OUTLINE strokes (0 inside the panel) -- as the shape
                    # it lit the strokes alone. The gauge MESH is the bar: the shape fully opaque (a ramp clipped
                    # above its window = 1 everywhere), Halo 1's reading (its fill lit the whole quad)
                    (None, 'plasma_repeater_gauge_alpha', PRW + r'\bitmaps\plasma_rifle_heat_gauge_alpha',
                     ('gradient', 'u', False, (-2.0, -1.0), 'alpha'), (16, 16)),
                    # the display's meter map: alpha 0 everywhere (a ramp clipped below its window) -- lit at value 1
                    (None, 'plasma_repeater_display_meter', PRW + r'\bitmaps\plasma_rifle_heat_gauge',
                     ('gradient', 'u', False, (2.0, 3.0), 'alpha'), (16, 16)),
                    (R + HOLO, 'plasma_repeater_display_alpha', PRW + r'\bitmaps\plasma_rifle_heat_gauge_alpha',
                     ('alpha_from', R + HOLO, 3), None),
                    # the indicator: the Needle Rifle's indicator recipe (the holo tinted Reach's teal 114, 255, 215 at
                    # 1/4, Halo 1's level), additive
                    (R + HOLO, 'plasma_repeater_indicator', r'objects\weapons\rifle\shotgun\bitmaps\illum_sights',
                     ('tint', (0.25 * 114 / 255.0, 0.25, 0.25 * 215 / 255.0), 0), None)],
        'shaders': [
            ('plasma_repeater_metal', PRW + r'\shaders\plasma_rifle_main', PR_MAPS),
            ('plasma_repeater_shell', PRW + r'\shaders\plasma_rifle_main', PR_MAPS),
            ('plasma_repeater_rubber', PRW + r'\shaders\plasma_rifle_dull', PR_MAPS),
            # the alpha FIRST (the Flamethrower's: a repoint refuses two records of one length)
            ('plasma_repeater_gauge', PRW + r'\shaders\plasma_rifle_gauge',
             {PRW + r'\bitmaps\plasma_rifle_heat_gauge_alpha': RP + r'\bitmaps\plasma_repeater_gauge_alpha',
              PRW + r'\bitmaps\plasma_rifle_heat_gauge': RP + r'\bitmaps\plasma_repeater_gauge_meter'}),
            ('plasma_repeater_display', PRW + r'\shaders\plasma_rifle_gauge',
             {PRW + r'\bitmaps\plasma_rifle_heat_gauge_alpha': RP + r'\bitmaps\plasma_repeater_display_alpha',
              PRW + r'\bitmaps\plasma_rifle_heat_gauge': RP + r'\bitmaps\plasma_repeater_display_meter'}),
            ('plasma_repeater_indicator', r'objects\weapons\fixed\plasma_cannon\shaders\plasma_illum',
             {r'objects\weapons\fixed\plasma_cannon\bitmaps\plasma_cannon': RP + r'\bitmaps\plasma_repeater_indicator'}),
            # the pilot: Bungie's own plasma current (animated noise, the PR's arc), Reach's halogram noise flame
            ('plasma_repeater_pilot', PRW + r'\shaders\plasma_rifle_current', {}),
        ],
        'report_rows': [(RP + r'\bitmaps\plasma_repeater_bump', 'the port'), (PRW + r'\bitmaps\plasma_rifle_bump', 'Bungie Plasma Rifle')],
    },

    # step 3 -- h2_port_weapon.py: the H2 PLASMA RIFLE's weapon (spew, heat + battery, its overheat effect and FP
    # overheat states, its HUD) with its bolt, firing / misfire / overheat damage, both firing effects, the trail,
    # the muzzle light and the material effects cloned. The .model is the COVENANT CARBINE's: the PR's names a
    # world graph whose 1-frame idle holds ITS rods near the origin -- the repeater shares the node names (rod_left
    # ...) but Reach's rods sit 12 cm forward, so that idle would tear them off; the Carbine's .model has no graph
    # (as the Needle Rifle's, DMR's, Laser's). The PR's two prong LENS FLARES (`heat_flare` markers Reach has none
    # of) scale by `ready`, used by nothing else in the tag -> `primary_charged` (0 on a spew trigger): off
    'weapon': {
        'weapon': WP,
        'clones': [(PRW + r'\plasma_rifle.weapon', WP),
                   (CC + r'\covenant_carbine.model', RP + r'\plasma_repeater.model'),
                   (PRW + r'\projectiles\plasma_rifle_bolt.projectile', PJ),
                   (PRW + r'\damage_effects\plasma_rifle_bolt.damage_effect', DM + r'\plasma_repeater_bolt.damage_effect'),
                   (PRW + r'\damage_effects\plasma_rifle_upper_trigger.damage_effect', DM + r'\plasma_repeater_upper_trigger.damage_effect'),
                   (PRW + r'\damage_effects\plasma_rifle_lower_trigger.damage_effect', DM + r'\plasma_repeater_lower_trigger.damage_effect'),
                   (PRW + r'\damage_effects\plasma_rifle_misfire.damage_effect', DM + r'\plasma_repeater_misfire.damage_effect'),
                   (PRW + r'\damage_effects\plasma_rifle_overheat.damage_effect', DM + r'\plasma_repeater_overheat.damage_effect'),
                   (PRFX + r'\upper_fire.effect', FX + r'\upper_fire.effect'),
                   (PRFX + r'\lower_fire.effect', FX + r'\lower_fire.effect'),
                   (PRFX + r'\overheated.effect', FX + r'\overheated.effect'),
                   (PRFX + r'\plasma_streak.contrail', FX + r'\plasma_repeater_streak.contrail'),
                   (PRFX + r'\plasma_streak.light_volume', FX + r'\plasma_repeater_streak.light_volume'),
                   (PRW + r'\plasma_rifle_muzzle_flash.light', RP + r'\plasma_repeater_muzzle_flash.light'),
                   (MAT + r'\plasma_rifle.material_effects', FX + r'\plasma_repeater.material_effects'),
                   (MAT + r'\plasma_rifle.material_effects', FX + r'\plasma_repeater_bolt.material_effects'),
                   # its own HUD (step 7): the PR's -- battery count, heat meter, plate, reticle, backpack
                   (r'ui\hud\pr_hud.new_hud_definition', r'ui\hud\plasma_repeater.new_hud_definition')],
        # step 4a (user): the bolt is Reach's plasma_fast -- Halo 2 has that group (its own rows)
        # CHECK 10 (the muzzle-flash rule): the PR's flash_c_generic_med fans two sprites SIDEWAYS (+-0.06 wu, +-120 deg,
        # both trigger effects, first and third person); Reach's five flash systems all sit at the bore -> the pair
        # turned onto the bore axis (offset -0.02, 0, 0, direction 0): every sprite forward, as Reach's
        'byte_edits': [(FX + r'\%s.effect' % fx, old, '0ad7a3bc00000000000000000000000000000000',
                        ('translational offset', 'relative direction'))
                       for fx in ('upper_fire', 'lower_fire')
                       for old in ('0ad7a3bc000000008fc2753d00000000920a0640',      # +0.06 wu, +120 deg
                                   '0ad7a3bc000000008fc275bd00000000920a06c0')],    # -0.06 wu, -120 deg
        'string_id_renames': [(WP, {'ready': 'primary_charged'}),
                              (DM + r'\plasma_repeater_bolt.damage_effect', {'plasma_slow': 'plasma_fast'})],
        # THE GAUGE AND THE DISPLAY'S COLOURS (the cloned PR gauge's functions, both shaders): meter_on_color, a
        # transition by heat (slot 0 = input 0, slot 3 = input 1, BGRA), Bungie's green -> red -> Reach's
        # meter_color_on teal 89, 255, 244 -> orange 255, 181, 23; meter_off_color Bungie's constant pale blue ->
        # Reach's meter_color_off 77, 212, 203 at half; meter_off_opacity Bungie's 0.5-0.67 pulse -> a steady 0.5.
        # The DISPLAY's meter_value (a transition by heat, 0 -> 1) -> 1 at every heat: fully lit, only its colour
        # follows heat (Halo 1's display look)
        'function_edits': [(RP + r'\shaders\%s.shader' % sh, old, new)
                           for sh in ('plasma_repeater_gauge', 'plasma_repeater_display')
                           for old, new in ((PR_ON_COLOR, RP_ON_COLOR), (PR_OFF_COLOR, RP_OFF_COLOR),
                                            (PR_OFF_OPACITY, RP_OFF_OPACITY))]
                          + [(RP + r'\shaders\plasma_repeater_display.shader', PR_METER_VALUE, RP_DISPLAY_VALUE)],
        'wiring': [
            (WP, 'hlmt', PRW + r'\plasma_rifle', RP + r'\plasma_repeater', 'world model'),
            (RP + r'\plasma_repeater.model', 'mode', CC + r'\covenant_carbine', RP + r'\plasma_repeater', 'the world render model', {'nth': 0}),
            (WP, 'mode', PRW + r'\fp_plasma_rifle\fp_plasma_rifle', RP + r'\fp_plasma_repeater\fp_plasma_repeater',
             'first person model, Master Chief', {'nth': 0}),
            (WP, 'mode', PRW + r'\fp_plasma_rifle\fp_plasma_rifle', RP + r'\fp_plasma_repeater\fp_plasma_repeater',
             'first person model, Dervish (one model)', {'nth': 0}),
            (WP, 'jmad', r'objects\characters\masterchief\fp\weapons\rifle\fp_plasma_rifle\fp_plasma_rifle',
             r'objects\characters\masterchief\fp\weapons\rifle\fp_plasma_repeater\fp_plasma_repeater', "Master Chief FP graph: Reach's own animations"),
            (WP, 'jmad', r'objects\characters\dervish\fp\weapons\rifle\fp_plasma_rifle\fp_plasma_rifle',
             r'objects\characters\dervish\fp\weapons\rifle\fp_plasma_repeater\fp_plasma_repeater', "Dervish FP graph: Reach's Elite animations"),
            (WP, 'proj', PRW + r'\projectiles\plasma_rifle_bolt', RP + r'\projectiles\plasma_repeater_bolt', 'the bolt'),
            (WP, 'jpt!', PRW + r'\damage_effects\plasma_rifle_upper_trigger', DM + r'\plasma_repeater_upper_trigger', 'firing damage (upper)'),
            (WP, 'jpt!', PRW + r'\damage_effects\plasma_rifle_lower_trigger', DM + r'\plasma_repeater_lower_trigger', 'firing damage (lower)'),
            # two copies, and a third record of the same length: one at a time (`every` refuses)
            (WP, 'jpt!', PRW + r'\damage_effects\plasma_rifle_misfire', DM + r'\plasma_repeater_misfire', 'misfire damage (upper)', {'nth': 0}),
            (WP, 'jpt!', PRW + r'\damage_effects\plasma_rifle_misfire', DM + r'\plasma_repeater_misfire', 'misfire damage (lower)', {'nth': 0}),
            (WP, 'effe', PRFX + r'\upper_fire', FX + r'\upper_fire', 'firing effect, upper muzzle'),
            (WP, 'effe', PRFX + r'\lower_fire', FX + r'\lower_fire', 'firing effect, lower muzzle'),
            (WP, 'effe', PRFX + r'\overheated', FX + r'\overheated', 'the overheat (the vent)'),
            (WP, 'ligh', PRW + r'\plasma_rifle_muzzle_flash', RP + r'\plasma_repeater_muzzle_flash', 'the muzzle light'),
            (WP, 'foot', MAT + r'\plasma_rifle', FX + r'\plasma_repeater', 'material effects (the weapon)'),
            (WP, 'nhdt', r'ui\hud\pr_hud', r'ui\hud\plasma_repeater', 'its own HUD (step 7)'),
            (FX + r'\overheated.effect', 'jpt!', PRW + r'\damage_effects\plasma_rifle_overheat', DM + r'\plasma_repeater_overheat', 'overheat damage'),
            (PJ, 'jpt!', PRW + r'\damage_effects\plasma_rifle_bolt', DM + r'\plasma_repeater_bolt', 'impact damage'),
            (PJ, 'foot', MAT + r'\plasma_rifle', FX + r'\plasma_repeater_bolt', 'impact material effects (the bolt)'),
            # the trail and the light volume pool ONE path (two classes): each by nth, tool-verified
            (PJ, 'cont', PRFX + r'\plasma_streak', FX + r'\plasma_repeater_streak', 'the trail', {'nth': 0}),
            (PJ, 'MGS2', PRFX + r'\plasma_streak', FX + r'\plasma_repeater_streak', 'the light volume', {'nth': 0}),
        ],
        'shared': [(r'effects\lens_flares\plasma_rifle', "the PR's prong flares: kept, scaled by primary_charged (0) = off"),
                   (r'effects\objects\weapons\pistol\plasma_pistol\misfire', "the PR's misfire effect (Bungie's)"),
                   (r'objects\weapons\damage_effects\strike_melee, smash_melee(_response)',
                    "Reach names strike_melee too: Halo 2's own, shared by every weapon"),
                   (r'effects\impact\plasma_slow\*', "the bolt's per-material detonation effects (Bungie's, until the look step)")],
    },

    # step 4 -- h2_port_numbers.py: REACH's OWN values (DEFAULT = Original, boot 1) through approximation A (the heat
    # rows: Reach x the Plasma Rifle ratio 1, so the same in Balanced); the balanced rows are the catalog's.
    # h3_weapon_values.py --kit reach rifle\plasma_repeater\plasma_repeater
    'numbers': {
        'numbers': [
            # the rate FALLS over the held time (approximation A, refit after boot 1 under Halo 2's MEASURED fire
            # rule -- the yardstick's `heat`): 20 -> 3.05 fires Reach's 15 -> 3/s (shot gaps 2,2,2,2,2,2,3,3,3,3,4,4,5,8,10 ticks)
            (WP, 'rounds per second', 'barrels', 0, 0, [20.0, 3.05]),
            (WP, 'acceleration time', 'barrels', 0, 0, 1.5),
            (WP, 'deceleration time', 'barrels', 0, 0, 3.6),
            # heat: overheats on round 15 at 1.53 s held (rounds 14-17 for heat +-7%); the overheat = Reach's 2.5 s vent
            (WP, 'heat generated per round', 'barrels', 0, 0, 0.076),
            (WP, 'heat loss per second', '', 0, 0, 0.09),
            (WP, 'overheated heat loss per second', '', 0, 0, 0.36),
            # the battery: 200 rounds (Reach 0.005)
            (WP, 'age generated per round', 'barrels', 0, 0, 0.005),
            # the single-wield cone (nth 1; the dual copy is unused once dual wield is cleared)
            (WP, 'error angle', 'barrels', 0, 1, [0.4, 3.0]),
            (WP, 'autoaim angle', '', 0, 0, 5.0),
            (WP, 'autoaim range', '', 0, 0, 15.0),
            (WP, 'magnetism angle', '', 0, 1, 10.0),
            (WP, 'magnetism range', '', 0, 1, 20.0),
            # flags'': `can be dual wielded` (bit 22) cleared -- Reach's repeater is two-handed; `cannot fire at
            # maximum age` + `loop fp firing animation` kept (4327424 -> 133120)
            (WP, 'flags', '', 0, 2, 133120),
            # the bolt: 25 -> 35 wu/s, range 100
            (PJ, 'initial velocity', '', 0, 0, 25.0),
            (PJ, 'final velocity', '', 0, 0, 35.0),
            (PJ, 'maximum range', '', 0, 0, 100.0),
            # 5.834 -> 7 plasma_fast (the group: `weapon` string_id_renames), instantaneous acceleration 0.125
            (DM + r'\plasma_repeater_bolt.damage_effect', 'damage lower bound', '', 0, 0, 5.834),
            (DM + r'\plasma_repeater_bolt.damage_effect', 'damage upper bound', '', 0, 0, [5.834, 7.0]),
            (DM + r'\plasma_repeater_bolt.damage_effect', 'instantaneous acceleration', '', 0, 0, 0.125),
            (WP, 'first person weapon offset', '', 0, 0, [0.0, 0.0, 0.0]),
            # step 4b, list 2 / 3: Reach's own (heat illumination 0: its muzzle light does not glow with heat)
            (WP, 'heat illumination', '', 0, 0, 0.0),
            (WP, 'illumination recovery time', 'barrels', 0, 0, 0.1),
            (WP, 'active camo ding', '', 0, 0, 0.25),
        ],
        'skipped': [
            ('heat generated per round function (0.03 a tick)', "Reach's heat lives in functions: approximation A's per-round heat"),
            ('heat_driven_rate_of_fire (15 -> 3 by heat^1.5)', 'Halo 2 ramps by the held time: the 1.6 s ramp'),
            ('heat_loss function (0.25 -> 0.06/s)', "one Halo 2 loss: Reach's cold 0.25"),
            ('manual vent (reload, 2.5 s)', 'no Halo 2 vent (user 4a: no dll vent) -- the overheat stands in'),
            ('fire recovery time 0.05', 'a 20/s ceiling above the 15/s rate: no effect'),
        ],
    },

    # step 5 -- the Carbine's authored hull (its .model is the port's) on the port's own world skeleton
    'collision': {
        'donor': CC + r'\covenant_carbine',
        'port': RP + r'\plasma_repeater',
        'src': r'covenant_carbine\collision\collision.jms',
        'out': RP + r'\collision\plasma_repeater.jms',
        'port_render_jms': RP + r'\render\plasma_repeater.jms',
        'donor_render_jms': r'covenant_carbine\render\covenant_carbine_L5.jms',
        'max_growth': 1.25,
        'nodes_from_render': True,
    },

    # step 9 -- h2_port_fp_anims.py kind 'reach' (the DMR's route): Reach's OWN FP animations for BOTH species
    # (Spartan -> masterchief, Elite -> dervish), helpers dropped. THE VENT: Reach's vent_enter 21 / vent_loop 30 /
    # vent_exit 13 = Halo 2's Plasma Rifle overheat states overheating / overheated / o_h_exit (Halo 1's mapping;
    # whether Halo 2 loops `overheated` through the 2.5 s overheat: boot 1); throw_vent (with events) =
    # throw_overheated; the ready also as ready_overheated (the PR has one). Not reproduced: barrel_spin (an
    # overlay driven by the rate -- no Halo 2 slot), flaps, melee_strike_vent, overheated:melee_strike_1, sprint /
    # jump / land / fall, ready_initial, Reach's own throw_overheated (no events: throw_vent carries them)
    'fp_anims': {
        'kind': 'reach',
        'species': {
            'masterchief': {
                'graph': R + r'objects\characters\spartans\fp\weapons\rifle\fp_plasma_repeater\fp_plasma_repeater.model_animation_graph',
                'arms_rm': R + r'objects\characters\spartans\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_masterchief\fp_arms.jms',
                'source': r'objects\characters\masterchief\fp\weapons\rifle\fp_plasma_repeater',
                # the SMG for its 17 sound slots (the DMR's reason)
                'seed': r'objects\characters\masterchief\fp\weapons\rifle\fp_smg\fp_smg'},
            'dervish': {
                'graph': R + r'objects\characters\elite\fp\weapons\rifle\fp_plasma_repeater\fp_plasma_repeater.model_animation_graph',
                'arms_rm': R + r'objects\characters\elite\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_dervish\dervish_fp_arms.jms',
                'source': r'objects\characters\dervish\fp\weapons\rifle\fp_plasma_repeater',
                'seed': r'objects\characters\dervish\fp\weapons\rifle\fp_smg\fp_smg'},
        },
        'weapon_dir': RP + r'\fp_plasma_repeater',
        'weapon_rm': RM,
        'weapon_nodes': sorted(NODES.values()),
        'node_names': NODES,
        'drop_nodes': ('pedestal', 'aim_pitch', 'aim_yaw', 'l_humerus', 'r_humerus', 'l_radius', 'r_radius',
                       'l_handguard', 'r_handguard'),
        'aliases': {'first_person:look': ['first_person:overlays', 'first_person:pitch_and_turn'],
                    'first_person:ready': ['first_person:ready', 'first_person:ready_overheated']},
        'rename': {'first_person:vent_enter': 'first_person:overheating',
                   'first_person:vent_loop': 'first_person:overheated',
                   'first_person:vent_exit': 'first_person:o_h_exit',
                   'first_person:throw_vent': 'first_person:throw_overheated'},
        # the FP position: the DMR's tested placement to start (Reach's repeater sits at the DMR's height: its
        # first-person weapon offset z -0.002 = the DMR's); the weapon field 0 (the gun-only rule)
        # boot 1 (user): 'move it down a unit' -> z -0.043
        'model_offset': (-0.005, -0.002, -0.043),
        'skip': ['first_person:look', 'first_person:accelration_screens', 'first_person:barrel_spin', 'first_person:fall',
                 'first_person:flaps', 'first_person:jump', 'first_person:land_hard', 'first_person:land_soft',
                 'first_person:ready_initial', 'first_person:melee_strike_vent', 'first_person:overheated:melee_strike_1',
                 'first_person:throw_overheated', 'first_person:sprint_enter', 'first_person:sprint_exit',
                 'first_person:sprint_loop', 'first_person:sprint_loop_airborne',
                 # the ELITE graph also ships its own overheating 59 / overheated 30 / o_h_exit 37 (the names the vent
                 # is renamed to: they collided, the vent won by sort order) -- the vent for both species, Reach's
                 # manual vent; pill_fix_idle / throw_equipment have no Halo 2 slot
                 'first_person:overheating', 'first_person:overheated', 'first_person:o_h_exit',
                 'first_person:pill_fix_idle', 'first_person:throw_equipment'],
        'looping': ['first_person:idle', 'first_person:posing:var1', 'first_person:posing:var2', 'first_person:vent_loop'],
        'overlay_reference': 'first_person:idle',
        'weights': {'first_person:posing:var1': 0.5, 'first_person:posing:var2': 0.5},
        'drop_ik': ['masterchief'],
        'clear_sound_ref_flags': True,
        'clear_verify': True,
        # Reach's graph cues one sound an animation at frame 0 (the DMR's measurement); the vent's: Halo 1's reading.
        # Keys are the Halo 2 names (after `rename`)
        'source_events': {'cues': {'first_person:melee_strike_1': [('rp_melee1', 0)],
                                   'first_person:melee_strike_2': [('rp_melee2', 0)],
                                   'first_person:posing:var1': [('rp_pose1', 0)],
                                   'first_person:posing:var2': [('rp_pose2', 0)],
                                   'first_person:ready': [('rp_ready', 0)],
                                   # boot 1 (user: 'check on the overheat venting sound'): the loop cued on EVERY
                                   # 1 s `overheated` loop overlapped itself (its takes run 0.95-2.16 s) -> one vent
                                   # sound at the start (rp_vent: the loop mixed in), none per loop
                                   'first_person:overheating': [('rp_vent', 0)],
                                   'first_person:o_h_exit': [('rp_vent_exit', 0)]}},
    },

    # step 10 -- h2_port_sounds.py: Reach's OWN sounds from MCC's haloreach sfx.fsb (the DMR's `bank`). Reach's
    # firing effect plays the shot + the plasma rifle's exterior tail: mixed (Halo 1's B3); the far layer in the
    # fire_lod slot and every remastered sweetener (lfe, mech, bottom) on it (the Mauler's / Laser's rule). One
    # Spartan set for both species (Reach's elite_plasrepeater_* unused, as the DMR's). THE VENT (Halo 1's): the
    # overheat cue + the manual vent's `in` mixed, its loop on every `overheated` loop, the exit
    'sounds': {
        'weapon': WP,
        'fire_fx': FX + r'\upper_fire.effect',
        'bank': 'haloreach',
        'audio': _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'out', 'h2_sounds', 'plasma_repeater'),
        'audio_key': 'Plasma Repeater',
        'h3_bank': {'rp_fire': [RS + r'\plasma_repeater\plas_repeater_fire', RS + r'\plasma_rifle\plasma_rifle_tails_ext'],
                    'rp_fire_lod': [RS + r'\plasma_repeater\plas_repeater_lod_far'],
                    'rp_dryfire': [RS + r'\plasma_pistol\plasma_dryfire'],
                    'rp_ready': [RS + r'\plasma_repeater\plasrepeater_ready'],
                    'rp_melee1': [RS + r'\plasma_repeater\plasrepeater_melee1'],
                    'rp_melee2': [RS + r'\plasma_repeater\plasrepeater_melee2'],
                    'rp_pose1': [RS + r'\plasma_repeater\plasrepeater_pose1'],
                    'rp_pose2': [RS + r'\plasma_repeater\plasrepeater_pose2'],
                    'rp_vent': [RS + r'\plasma_repeater\plasrepeater_oh', RS + r'\plasma_repeater\plasrepeater_manvent\track_1\in',
                                RS + r'\plasma_repeater\plasrepeater_manvent\track_1\loop'],
                    'rp_vent_loop': [RS + r'\plasma_repeater\plasrepeater_manvent\track_1\loop'],
                    'rp_vent_exit': [RS + r'\plasma_repeater\plasrepeater_oh_exit'],
                    'rp_drop': [RS + r'\plasma_rifle\plasma_rifle_drop'],
                    'rp_drop_soft': [RS + r'\plasma_rifle\plasma_rifle_drop_soft'],
                    'rp_flyby': [RS + r'\impacts_riccs\plasma_flyby_reach'],
                    'rp_impact': [RS + r'\impacts_riccs\plasma_impacts_reach']},
        'sounds': {'rp_fire': ('rp_fire', 'weapon_fire'), 'rp_fire_lod': ('rp_fire_lod', 'weapon_fire'),
                   'rp_dryfire': ('rp_dryfire', 'weapon_empty'), 'rp_ready': ('rp_ready', 'weapon_ready'),
                   'rp_melee1': ('rp_melee1', 'weapon_melee'), 'rp_melee2': ('rp_melee2', 'weapon_melee'),
                   'rp_pose1': ('rp_pose1', 'weapon_animation'), 'rp_pose2': ('rp_pose2', 'weapon_animation'),
                   'rp_vent': ('rp_vent', 'weapon_overheat'), 'rp_vent_loop': ('rp_vent_loop', 'weapon_overheat'),
                   'rp_vent_exit': ('rp_vent_exit', 'weapon_overheat'),
                   'rp_drop': ('rp_drop', 'object_impacts'), 'rp_drop_soft': ('rp_drop_soft', 'object_impacts'),
                   'rp_flyby': ('rp_flyby', 'projectile_flyby'), 'rp_impact': ('rp_impact', 'projectile_impact')},
        'repoint_fx': [(r'sound\weapons\plasma_rifle\plas_rifle_fire', 'rp_fire'),
                       (r'sound_remastered\weapons\plasma_rifle\plasma_rifle_fire_lod', 'rp_fire_lod'),
                       (r'sound_remastered\weapons\plasma_rifle\plasmarifle_lfe', 'rp_fire_lod'),
                       (r'sound_remastered\weapons\plasma_rifle\plas_fire_mech_swtnr', 'rp_fire_lod')],
        'repoint_weapon': [],
        'repoint_tags': [(FX + r'\lower_fire.effect', r'sound\weapons\plasma_rifle\plasma_rifle_fire', 'rp_fire'),
                         (FX + r'\lower_fire.effect', r'sound_remastered\weapons\plasma_rifle\plas_rifle_fire_bottom', 'rp_fire_lod'),
                         (FX + r'\lower_fire.effect', r'sound_remastered\weapons\plasma_rifle\plasma_rifle_fire_lod', 'rp_fire_lod'),
                         (FX + r'\lower_fire.effect', r'sound_remastered\weapons\plasma_rifle\plasmarifle_lfe', 'rp_fire_lod'),
                         (FX + r'\lower_fire.effect', r'sound_remastered\weapons\plasma_rifle\plas_fire_mech_swtnr', 'rp_fire_lod'),
                         (PJ, r'sound\weapons\plasma_rifle\plasma_proj', 'rp_flyby'),
                         (FX + r'\plasma_repeater.material_effects', r'sound\weapons\plasma_rifle\plasma_rifle_drop', 'rp_drop'),
                         (FX + r'\plasma_repeater.material_effects', r'sound\weapons\plasma_rifle\plasma_rifle_drop_soft', 'rp_drop_soft'),
                         (FX + r'\plasma_repeater.material_effects', r'sound\weapons\plasma_rifle\plasma_hit', 'rp_impact'),
                         (FX + r'\plasma_repeater_bolt.material_effects', r'sound\weapons\plasma_rifle\plasma_rifle_drop', 'rp_drop'),
                         (FX + r'\plasma_repeater_bolt.material_effects', r'sound\weapons\plasma_rifle\plasma_rifle_drop_soft', 'rp_drop_soft'),
                         (FX + r'\plasma_repeater_bolt.material_effects', r'sound\weapons\plasma_rifle\plasma_hit', 'rp_impact')],
        # the SMG seed's 17 references, all repointed; unused dual slots point at the ready
        'graph_sounds': (('smg_melee1', 'rp_melee1'), ('smg_ready', 'rp_ready'), ('smg_reload', 'rp_vent'),
                         ('smg_reload_full', 'rp_vent_exit'), ('smg_dual_ready', 'rp_melee2'),
                         ('smg_posing_var0', 'rp_pose1'), ('smg_posing_var1', 'rp_pose2'),
                         ('smg_dual_reload_left', 'rp_vent_loop'), ('smg_dual_reload_right', 'rp_ready'),
                         ('smg_dual_posing_0_l', 'rp_ready'), ('smg_dual_posing_0_r', 'rp_ready'),
                         ('smg_dual_posing_1_l', 'rp_ready'), ('smg_dual_posing_1_r', 'rp_ready'),
                         ('smg_dual_posing_2_l', 'rp_ready'), ('smg_dual_posing_2_r', 'rp_ready'),
                         ('smg_dual_posing_3_l', 'rp_ready'), ('smg_dual_posing_3_r', 'rp_ready')),
        'graph_sound_dir': r'sound\weapons\smg' + '\\',
        'gain': {},
        'boost': {},
        'backup': r'E:\HaloBackups\H2EK_plasma_repeater_before_sounds',
        'graph_backup': r'E:\HaloBackups\H2EK_plasma_repeater_graphs_before_sounds',
    },

    # step 7 -- the PR's battery count + heat meter stay as they are (a battery weapon: no ammo pips); only the
    # stowed (backpack) icon is the port's. The plate: the PR's, its symbol repainted from the port's mesh (the
    # glow parts left out of the drawing)
    'meter': {
        'backpack_only': True,
        'port_hud': r'ui\hud\plasma_repeater',
        'backpack': NEW_HUD + r'\backpack_weapons',
        'backpack_port': NEW_HUD + r'\plasma_repeater_backpack',
        'backpack_size': (62, 30),
        'model_3p': RP_JMS,
        'model_skip': ('plasma_repeater_indicator', 'plasma_repeater_display', 'plasma_repeater_gauge', 'plasma_repeater_pilot'),
    },
    'hud_plate': {
        'rel': NEW_HUD + r'\backgrounds',
        'donor': NEW_HUD + r'\backgrounds\plasma_rifle_bkd',
        'other': NEW_HUD + r'\backgrounds\plasma_pistol_bkd',
        'name': 'plasma_repeater_bkd',
        'hud': r'ui\hud\plasma_repeater',
        'model_3p': RP_JMS,
        'model_skip': ('plasma_repeater_indicator', 'plasma_repeater_display', 'plasma_repeater_gauge', 'plasma_repeater_pilot'),
        'fallback_box': (105, 191, 5, 34),
        'stretch': 1.4,
        # the PR plate is the SMG's shape: 8 images, 0-3 bright (right / left / right out / left out), 4-7 dim
        'all_images': {'dim': {4: 0, 5: 1, 6: 2, 7: 3}},
    },
    # step 8 -- the pickup icon at the reserved U+E145, untinted (the H2 ICON RULE); pr_* -> rp2_*
    'glyph': {
        'box': (160, 62),
        'model_3p': RP_JMS,
        'model_skip': ('plasma_repeater_indicator', 'plasma_repeater_display', 'plasma_repeater_gauge', 'plasma_repeater_pilot'),
        'tif': 'plasma_repeater_h2_glyph.tif',
        'colour': (255, 255, 255),
        # Reach's dense mesh creases into speck lines inside the body: the DMR's min_line 14
        'style': {'line': (255, 255, 255), 'body': (153, 153, 153), 'min_line': 14},
    },
    'messages': {
        'donor_prefix': 'pr', 'donor_icon': '&plasma_rifle',
        'donor_name': 'Plasma Rifle', 'port_name': 'Plasma Repeater',
        'names': [('a Plasma Rifle', 'a Plasma Repeater')],
        'weapon': WP,
    },

    # step 7 -- the HUD: the PR's clone (`weapon` clones; battery count, heat meter, plate). Reach's reticle (the
    # plasma_carbine chud's crosshair): hud_reticles #3 = the TOP-LEFT QUARTER of a faint ring (alpha peak 85, its
    # centre at the sprite's bottom right: 35.7, 34.6 sprite px -- Halo 1's 0.965 / 0.962) mirrored four ways, plus
    # four #33 wedges on the diagonals at 0.56 of its scale, pointing in, centres 24.5 sprite px out (Halo 1's B3
    # layers). The ring half transparent (alpha x1.5 = 0.5: the user's Halo 1 boot 2 'a half-transparent ring').
    # Size: Reach's ring ~88 px across at 1080p (the user's Reach screenshot, Halo 1's B3) / 1.117 = target_ink 79
    'reticle': {
        'rel': NEW_HUD + r'\crosshairs',
        'donor': NEW_HUD + r'\crosshairs\hud_reticles',
        'donor_sequence': 4,                 # the PR's crosshair (the cloned HUD's)
        'name': 'plasma_repeater_reticle',
        'hud': r'ui\hud\plasma_repeater',
        'footprint': 1.0,
        'h3_art': {'sheet': R + r'ui\chud\bitmaps\hud_reticles', 'sequence': 3, 'yardstick': 3,
                   'quad': (35.7, 34.6, 1.5), 'spokes': [(33, 0.56, 24.5, [225, 315, 45, 135])],
                   # the wedges reach ~4/88 past the ring each side: the whole ink 79 x 96 / 88
                   'target_ink': 86},
        'preview': 'plasma_repeater_reticle_preview.png',
    },

    # step 4b -- port_field_audit.py --port h2:plasma_repeater: the source pair (Reach's repeater vs Reach's plasma
    # rifle, the yardstick) against the target pair (the port vs the H2 plasma rifle)
    'field_audit': {
        'source_kit': 'HREK',
        'source': {'weapon': (RP + r'\plasma_repeater.weapon', PRW + r'\plasma_rifle.weapon'),
                   'projectile': (RP + r'\projectiles\plasma_repeater_bolt.projectile', PRW + r'\projectiles\plasma_rifle_bolt.projectile'),
                   'damage_effect': (RP + r'\projectiles\plasma_repeater_bolt.damage_effect',
                                     PRW + r'\projectiles\plasma_rifle_bolt.damage_effect')},
        'target': {'weapon': (WP, PRW + r'\plasma_rifle.weapon'),
                   'projectile': (PJ, PRW + r'\projectiles\plasma_rifle_bolt.projectile'),
                   'damage_effect': (DM + r'\plasma_repeater_bolt.damage_effect', PRW + r'\damage_effects\plasma_rifle_bolt.damage_effect')},
        'decisions': {
            'heat recovery threshold 0.1 (source 0)': "approximation A: Reach never overheats (its 0 means nothing); 0 "
                                                      "would never leave the overheat (Halo 1's measure) -- the PR's 0.1",
            'heat loss 0.25 / overheated loss 0.36 / heat 0.0915 / rate ramp 1.6 / 3.6 s (source 0.0333 / 0 / 0 / 0)':
                "approximation A (user 4a): Reach's heat lives in functions; fitted, see the yardstick",
            'barrels deceleration time (nth 1) 0.6 (ratio 1.06)': "Reach's own bloom decay (the PR's is the same 0.6)",
            'barrels error angle (nth 0) 1.5-3 (ratio 0.46-2.57)': 'the DUAL-wield copy: unused, dual wield cleared',
            'barrels illumination recovery time 0.1 (ratio 0.17)': "Reach's own (Original)",
            'water gravity scale 0.2 (source 0)': "the PR's: a zero on one side",
            'bounding radius 0.2 (source 0.135)': "the PR clone's (the world model's size)",
            'barrel spin scale 1 / rounds between tracers 1 / fire recovery 0.05': "no Halo 2 barrel_spin animation; no "
                                                                               "tracer; recovery above the rate",
            'flags 133120': "can be dual wielded cleared (Reach's two-handed); the rest the PR's",
            'first person weapon offset': '0 -- the position lives in fp_anims model_offset',
            'functions / attachments / interpolation / falloff / accuracy penalties / venting time / heat warning':
                'no such field in Halo 2 (heat venting 2.5 s = the overheat, approximation A)',
        },
    },

    # step 11 -- `python ai_firing_profile.py --h2-port plasma_repeater`: Reach's ai\generic entry (m10) over the H2
    # Plasma Rifle's (the donor; the Elites carry it in both games -- the Elite rows read directly)
    'firing_profile': {'from_game': 'Halo Reach', 'from_map': r'haloreach\maps\m10.map',
                       'from_weapon': RP + r'\plasma_repeater',
                       'donor_weapon': PRW + r'\plasma_rifle'},
    # BALANCED (step 4a, user 2026-11-21: reports/h2_plasma_repeater_4a.md). The table reads the PLASMA RIFLE's tags,
    # each redirected onto the port's own; the ratio is x1 on every heat / rate / damage / battery / range row, so
    # Balanced differs from Original in bolt speed (14 -> 19.6), the single-wield cone (0.077-0.64) and autoaim (6).
    # The heat rows are approximation A's (the table reads Reach's per-round FIELDS, which its functions override);
    # melee rows dropped (strike_melee is everyone's)
    'catalog': {
        'table': 'balance_Plasma_Repeater_HaloReach_to_Halo2.json',
        'weapon_tag': RP + r'\plasma_repeater',
        'port_tags': [(('weap', PRW + r'\plasma_rifle'), RP + r'\plasma_repeater'),
                      (('proj', PRW + r'\projectiles\plasma_rifle_bolt'), RP + r'\projectiles\plasma_repeater_bolt'),
                      (('jpt!', PRW + r'\damage_effects\plasma_rifle_bolt'), DM + r'\plasma_repeater_bolt')],
        'shared': [('jpt!', r'objects\weapons\damage_effects\strike_melee')],
        # 'original' too: the Original box writes each row's original (the table's are Reach's overridden fields)
        'value_overrides': {
            'Heat Recovery Threshold': {'value': 0.1, 'original': 0.1, 'note': "approximation A (user 4a): Reach's 0 never leaves an overheat"},
            'Heat Loss Per Second': {'value': 0.09, 'original': 0.09, 'note': "approximation A refit after boot 1: Reach's mid-heat loss (its function; the 0.0333 field is overridden)"},
            'Overheated Heat Loss Per Second': {'value': 0.36, 'original': 0.36, 'note': "approximation A: the overheat = Reach's 2.5 s vent (0.9 / 0.36)"},
            'Heat Generated Per Round': {'value': 0.076, 'original': 0.076, 'note': "approximation A refit after boot 1 (Halo 2's reset fire rule): overheats on round 15 at 1.53 s"},
            # the trigger under Halo 2's reset fire rule (boot 1): 20 -> 3.05 fires Reach's 15 -> 3/s
            'Rounds Per Second': {'value': 20.0, 'original': 20.0, 'note': "fires 15/s under Halo 2's reset fire rule (Reach's 15)"},
            'Rounds Per Second Max': {'value': 3.05, 'original': 3.05, 'note': "fires 3/s under Halo 2's reset fire rule (Reach's 3)"},
            # Reach's firing noise 4 is its 'loud'; Halo 2 numbers its enum differently (4 = quiet): the PR's loud (2)
            'Firing Noise': {'value': 2, 'original': 2, 'note': "Halo 2's loud (Reach's 4 is another enum)"},
        },
        'fp_animations': r'objects\characters\*\fp\weapons\rifle\fp_plasma_repeater\fp_plasma_repeater',
        'reload_mult': None,
        'desc': ('%s carried from %s into Halo 2 with its own model, textures, sounds and its own Reach first-person '
                 'animations for both species; its rate falls as it heats and an overheat stands in for the manual '
                 'vent. Balanced through the Plasma Rifle.'),
    },

    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant'},
    'residency': {'levels': 'all', 'placements': False},
}
