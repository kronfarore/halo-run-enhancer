r"""Concussion Rifle into Halo 2 (H2_PORT_PLAN.md wave B (Reach), #B5, "Step 6", alone) -- IN PROGRESS (2026-11-26).

The port: Reach's model, textures, Spartan + Elite FP animations and sounds on a clone of Halo 2's FUEL ROD
(flak_cannon: latch, magazine 5 -> 6, an explosive plasma bolt, the Covenant HUD), the bolt on the fuel rod's
flak_bolt (its model, light volumes, trail and burst recoloured to Reach's violet: `python ports_h2\concussion_rifle.py
--recolour`), the COVENANT CARBINE's graph-less `.model` (the Plasma Repeater's). Yardstick the FUEL ROD (step 4a,
user 2026-11-26): reports/h2_concussion_rifle_4a.md.

REGENERATING FROM SCRATCH needs the step the pipeline does not run, after h2_port_weapon and h2_port_numbers:
    python ports_h2\concussion_rifle.py --recolour       the fuel rod's green -> Reach's violet (colour functions,
                                                         light colours), each edit proved by tool's export
"""

import os as _os

CR = r'objects\weapons\rifle\concussion_rifle'      # the source's folder (HREK) AND the port's (H2EK)
FC = r'objects\weapons\support_high\flak_cannon'    # the weapon + bolt donor, the yardstick (H2EK)
FCFX = r'effects\objects\weapons\support_high\flak_cannon'
FX = r'effects\objects\weapons\rifle\concussion_rifle'   # the reserved effects folder
CC = r'objects\weapons\rifle\covenant_carbine'      # its .model: a Covenant weapon model with NO world graph
PRW = r'objects\weapons\rifle\plasma_rifle'         # the shader seeds (the Plasma Repeater's, Covenant)
R = 'reach:'                                        # an HREK path (reach_tags)
RM = R + CR + r'\concussion_rifle.render_model'
WP = CR + r'\concussion_rifle.weapon'
PJ = CR + r'\projectiles\concussion_rifle_bolt.projectile'
DM = CR + r'\damage_effects'
MAT = r'effects\materials\objects\weapons'
RS = r'data\sound\weapons'                          # source folders in MCC's haloreach sfx.fsb (.info)
NEW_HUD = r'ui\hud\bitmaps\new_hud'
H2EK = r'F:\SteamLibrary\steamapps\common\H2EK'
CR_JMS = H2EK + r'\data' + '\\' + CR + r'\render\concussion_rifle.jms'   # the mesh the HUD art is drawn from
CR_GLOW = ('cr_gas', 'cr_indicator', 'cr_overheat')                      # left out of the drawings
HOLO = r'objects\weapons\support_high\plasma_launcher\bitmaps\plasma_launcher_holo.bitmap'   # Reach's display atlas
# Reach's weapon nodes -> Halo 2's (b_ dropped; the root is Halo 2's `gun`)
NODES = {'b_gun': 'gun', 'b_wing_left': 'wing_left', 'b_wing_right': 'wing_right', 'b_hatch': 'hatch',
         'b_drum': 'drum', 'b_drum_flap01': 'drum_flap01', 'b_drum_flap02': 'drum_flap02',
         'b_drum_flap03': 'drum_flap03', 'b_drum_flap04': 'drum_flap04', 'b_drum_flap05': 'drum_flap05',
         'b_drum_flap06': 'drum_flap06'}
NODES_JMS = dict((k, 'frame ' + v) for k, v in NODES.items())
CRB = CR + r'\bitmaps' + '\\'
PR_MAPS = {PRW + r'\bitmaps\plasma_rifle_bump_active_camo': CRB + 'concussion_rifle_bump',
           PRW + r'\bitmaps\plasma_rifle_bump': CRB + 'concussion_rifle_bump',
           PRW + r'\bitmaps\plasma_rifle': CRB + 'concussion_rifle'}
# Reach's indicator blue, read off the user's Reach screenshot for Halo 1's B5 (~70 / 150 / 255)
BLUE = (0.3, 0.6, 1.0)
# Reach's concussion PLASMA (Halo 1's B5 reading of HREK + the user's screenshot): the muzzle flare gradient black ->
# 50 / 46 / 174 -> 103 / 84 / 247 -> 199 / 148 / 255 -> white; the bolt a white-hot core in a PINK-MAGENTA glow (mid
# 168 / 125 / 151), violet-white sparks
VIOLET = (0.78, 0.58, 1.0)
VIOLET_DEEP = (0.40, 0.33, 0.97)
PINK = (1.0, 0.45, 0.75)

PORT = {
    'order': 10,
    'wave': 'B5',
    'name': 'Concussion Rifle',
    'source': 'Halo Reach',
    'status': 'in progress',
    'source_tag': 'objects\\weapons\\rifle\\concussion_rifle\\concussion_rifle',
    'reservations': {
        'message_prefix': 'cr2',
        'glyph': 0xE147,
        'weapon_dir': 'objects\\weapons\\rifle\\concussion_rifle',
        'effects_dir': 'effects\\objects\\weapons\\rifle\\concussion_rifle',
        'fp_graph': 'weapons\\rifle\\fp_concussion_rifle\\fp_concussion_rifle',
        'hud': 'ui\\hud\\concussion_rifle',
        'hud_bitmap_prefix': 'concussion_rifle_',
        'sound_dir': 'sound\\weapons\\concussion_rifle_port',
    },
    'donor': {'weapon': FC + r'\flak_cannon', 'message_prefix': 'fc',
              'projectile': FC + r'\projectiles\flak_bolt\flak_bolt',
              'why': ("the FUEL ROD (H2's flak_cannon): latch magazine (5 -> 6), an explosive plasma bolt with Reach's "
                      "acceleration-range flight, the Covenant HUD; zoom 1 -> 0. The yardstick's own tag, so most 4b "
                      "rows are Reach's or x1")},
    'yardstick': {
        # step 4a, user 2026-11-26 ('All approved with the recommended decisions'): reports/h2_concussion_rifle_4a.md
        # (h2_cr_ttk_4a.py).
        # REACH (HREK): latch, recovery 0.333 s, 6 / 18 / 30, reloads 6 (100 fr empty + full; primary keyframe 48,
        # allow interruption 63), error 0.15 min, 0.4 / 0.4, no zoom, autoaim 4/15, magnetism 8/15, strike_melee. The
        # bolt: 12 -> 16 wu/s over the acceleration range 6..15 wu, gravity 0.25 (air + water), range 100, minimum
        # velocity 11, timer immediately, collision radius 0.1, danger 0.5, oriented along velocity + AI ballistic
        # aim. IMPACT 21.5 `collision` (accel 0.75) + BLAST 0..21.5 over 1 -> 2 (core 0.8, `plasma_fast`, accel 2.5).
        # Reach fuel rod: 100 collision (accel 1) + 0..60 over 0.5 -> 2.25 (core 0.5, explosion_large, accel 1.5),
        # 0.4 s, 5 / 20 / 30, 90 fr, 15 -> 6.5 over 4.5..5, gravity 0.025, range 80, error 0 / 0..0.05, aim 4/25 8/25.
        # HALO 2 fuel rod: 100 explosion_large (accel 1) + 40..90 over 0.5 -> 1.5 (core 0.5, 'explosion_largw' --
        # Bungie's typo, no such group: x1 on everything --, accel 2.25), 0.4 s, 5 / 20 / 30, reload tag 5.0 s (FP
        # animation 90 fr), 15 -> 6.5 over 4.5..5, gravity 0.025, range 80, error 0 / 0..0.05, aim 4/25 6/25, zoom 2x.
        'pick': 'Flak Cannon (fuel rod)',
        'reason': ("user 2026-11-26, every recommendation: (1) the FUEL ROD -- Halo 2's is Reach's fuel rod in flight, "
                   "rate, magazine, error and aim, so the ratio keeps Reach's whole handling and moves the blast "
                   "(21.5 x 90/60 = 32.25), the push and the reload; (2) groups by REACH'S NAMES, impact `collision`, "
                   "blast `plasma_fast` (Halo 2's own groups: equal to Reach's on Elite / Brute / Grunt / Jackal; "
                   "HUNTERS armour-immune, skin x2 -- Halo 1's 'Reach's values for Hunters' cannot hold: Halo 2's "
                   "damage table is global; Flood combat forms x0.5, hard Flood immune); (3) KNOCKBACK Original "
                   "Reach's 2.5, Balanced the ratio 3.75 -- any tuning only after the user has seen 2.5 in game; "
                   "(4) Balanced RELOAD 5.56 s by the fuel rod's TAG time (the Grenade Launcher's rule). Legendary "
                   "direct hits: Elite minor 4 / 1.0 s Original, 3 / 0.67 s Balanced; Brute 6 / 5; Grunt 1; Jackal 2"),
        # DEFAULT = Reach's own numbers (PORTING "Balance"); these are the BALANCED rows (the catalog's), every one the
        # FUEL ROD ratio (H2 fuel rod x Reach CR / Reach fuel rod) unless said
        'balanced': {
            # the blast: 90 x 21.5/60; lower: Reach 0 / 0 -> the sibling rule 40 x 32.25/90; radius 0.5 x 1/0.5, 1.5 x
            # 2/2.25; core 0.5 x 0.8/0.5
            'damage': 32.25, 'damage_lower': 14.333, 'radius': (1.0, 1.333), 'core': 0.8,
            # the impact: 100 x 21.5/100; accel 1 x 0.75/1
            'impact': 21.5, 'impact_acceleration': 0.75,
            # THE KNOCKBACK: 2.25 x 2.5/1.5
            'acceleration': 3.75,
            # recovery 0.4 x 0.333/0.4; magazine 5 x 6/5, 20 x 18/20, 30 x 30/30 (Reach's own)
            'fire_recovery_s': 0.3333, 'magazine': 6, 'rounds_total_initial': 18, 'rounds_total_maximum': 30,
            # reload: Reach's 100 fr x H2's TAG 5.0 s / Reach's 90 fr (3.0 s) = 5.556 s
            'reload_s': 5.556,
            # flight, gravity, range, error, minimum velocity: x1 (both fuel rods alike) -> Reach's own
            'velocity': (12.0, 16.0), 'acceleration_range': (6.0, 15.0), 'gravity': 0.25, 'range': 100.0,
            'minimum_velocity': 11.0, 'error_deg': (0.15, 0.4, 0.4),
            # aim: autoaim 4 x 4/4, 25 x 15/25; magnetism 6 x 8/8 = 6, 25 x 15/25
            'autoaim': (4.0, 15.0), 'magnetism': (6.0, 15.0)},
        'candidates': {
            'provisional': 'Fuel Rod',
            'alternatives': ['Rocket Launcher'],
            'direct': 'none',
            # the h2_role_compare names (the Flak Cannon is its 'Fuel Rod')
            'peers': ['Fuel Rod', 'Rocket Launcher', 'Brute Shot'],
            'why': "magazine 6 latch explosive plasma; Reach's AND H2's fuel rods are both 5-round magazines (cleaner than H1's charge fuel rod)",
            'lacks': ("the Hunters' Reach values (Halo 2's plasma_fast leaves their armour immune), plants and liquid "
                      "letting the bolt through (Halo 2's one material response), the drum turning a shot (Reach's "
                      "barrel_spin overlay: no Halo 2 slot)"),
        },
    },

    # step 1 -- h2_port_geometry.py kind 'h3' with `reach:` paths (the DMR's route): Reach's ONE render model is world
    # AND first person; 11 nodes (b_gun; b_wing_left / _right; b_hatch > b_drum > six b_drum_flap0x), 1 mesh, 7
    # materials. Markers: primary_trigger (the bore: the fuel rod's firing effect, muzzle light and barrel name it);
    # the grip (right_hand, the origin) -> `flashlight` (Halo 2's FP light: the Arbiter-flashlight rule);
    # left_hand_spartan -> `left_hand_mc`. Dropped: vent x2, fx_reload_gas, weapon_stow_anchor, vehicle_root, the
    # brute / marine hand markers (no Halo 2 user)
    'geometry': {
        'kind': 'h3',
        'world_rm': RM, 'fp_rm': RM,
        'data_dir': CR,
        'world': 'concussion_rifle', 'fp': 'fp_concussion_rifle',
        'materials': {'concussion_rifle_inside': 'cr_inside', 'concussion_rifle_metal': 'cr_metal',
                      'concussion_rifle_rubber': 'cr_rubber', 'concussion_rifle_shell': 'cr_shell',
                      'concussion_rifle_gas_effect': 'cr_gas', 'concussion_rifle_indicator': 'cr_indicator',
                      'concussion_rifle_overheat': 'cr_overheat'},
        'world_permutation': 'default', 'world_region': 'default',   # the Carbine .model / render model's names
        'node_names': NODES_JMS,
        'markers': {'primary_trigger': 'primary_trigger', 'right_hand': 'flashlight', 'left_hand': 'left_hand',
                    'left_hand_elite': 'left_hand_elite', 'left_hand_spartan': 'left_hand_mc'},
        'muzzle_drop': 0.0,
        'ground_point': {'rot': (0.7071068883, -1.8e-09, -7.42e-08, -0.7071067095)},   # the SMG's (the AR's)
        'render': ['concussion_rifle', r'concussion_rifle\fp_concussion_rifle'],
        'fine_weld': True,                    # the DMR's boot 1: tool's 1/512 weld drops small triangles
    },

    # step 2 -- kind 'h3' with `reach:` bitmaps, 1024 -> 512 (the DMR's). Reach's inside / metal / rubber / shell all
    # sample ONE diffuse + one normal map; shaders reseeded from the Plasma Repeater's (Halo 2's Covenant plasma rifle
    # main / dull). Reach's metal names battle_rifle_illum as self-illum (another weapon's map): off, as the DMR's.
    # THE INDICATOR and THE OVERHEAT panel both sample Reach's plasma_launcher_holo (shape in R) -> lit static shapes
    # in Reach's blue on the indicator template (plasma_illum, additive), Halo 1's B5 look. THE GAS (the top vent
    # slots, a clouds halogram in Reach) dull off the diffuse, as Halo 1's
    'textures': {
        'kind': 'h3',
        'rel': CR + r'\bitmaps',
        'shaders_dir': CR + r'\shaders',
        'bump_gain': 1.0,
        'bitmaps': [(R + CRB + 'concussion_rifle_diffuse.bitmap', 'concussion_rifle', PRW + r'\bitmaps\plasma_rifle', 'color', (512, 512)),
                    (R + CRB + 'concussion_rifle_normal.bitmap', 'concussion_rifle_bump', PRW + r'\bitmaps\plasma_rifle_bump', 'bump', (512, 512)),
                    (R + HOLO, 'concussion_rifle_indicator', r'objects\weapons\rifle\shotgun\bitmaps\illum_sights',
                     ('tint', (0.5 * BLUE[0], 0.5 * BLUE[1], 0.5 * BLUE[2]), 0), None)],
        'shaders': [
            ('cr_metal', PRW + r'\shaders\plasma_rifle_main', PR_MAPS),
            ('cr_shell', PRW + r'\shaders\plasma_rifle_main', PR_MAPS),
            ('cr_inside', PRW + r'\shaders\plasma_rifle_dull', PR_MAPS),
            ('cr_rubber', PRW + r'\shaders\plasma_rifle_dull', PR_MAPS),
            ('cr_gas', PRW + r'\shaders\plasma_rifle_dull', PR_MAPS),
            ('cr_indicator', r'objects\weapons\fixed\plasma_cannon\shaders\plasma_illum',
             {r'objects\weapons\fixed\plasma_cannon\bitmaps\plasma_cannon': CRB + 'concussion_rifle_indicator'}),
            ('cr_overheat', r'objects\weapons\fixed\plasma_cannon\shaders\plasma_illum',
             {r'objects\weapons\fixed\plasma_cannon\bitmaps\plasma_cannon': CRB + 'concussion_rifle_indicator'}),
        ],
        'report_rows': [(CRB + 'concussion_rifle_bump', 'the port'), (PRW + r'\bitmaps\plasma_rifle_bump', 'Bungie Plasma Rifle')],
    },

    # step 3 -- h2_port_weapon.py: the FUEL ROD's weapon (latch, magazine, explosive bolt, its HUD) with its bolt,
    # impact / blast / firing damage, the firing effect, muzzle light, the bolt's light volumes, trail and armed
    # effect, the burst (Halo 2 fuel rod = the banshee bomb's detonation, and its light), both material effects
    # (weapon drops; the bolt's -- its `flak_expl` IS the fuel rod's explosion sound: the burst effect has none) and
    # the flight loop cloned. The .model the COVENANT CARBINE's graph-less one (the Plasma Repeater's)
    'weapon': {
        'weapon': WP,
        'clones': [(FC + r'\flak_cannon.weapon', WP),
                   (CC + r'\covenant_carbine.model', CR + r'\concussion_rifle.model'),
                   (FC + r'\projectiles\flak_bolt\flak_bolt.projectile', PJ),
                   (FC + r'\projectiles\flak_projectile.model', CR + r'\projectiles\concussion_rifle_bolt.model'),
                   (FC + r'\projectiles\flak_projectile.render_model', CR + r'\projectiles\concussion_rifle_bolt.render_model'),
                   (FC + r'\shaders\flak_bolt_luminous.shader', CR + r'\shaders\cr_bolt_luminous.shader'),
                   (FC + r'\damage_effects\flak_impact.damage_effect', DM + r'\concussion_rifle_impact.damage_effect'),
                   (FC + r'\damage_effects\flak_explosion.damage_effect', DM + r'\concussion_rifle_explosion.damage_effect'),
                   (FC + r'\damage_effects\flak_cannon_trigger.damage_effect', DM + r'\concussion_rifle_trigger.damage_effect'),
                   (FCFX + r'\flak_bolt_fire.effect', FX + r'\concussion_rifle_fire.effect'),
                   (FCFX + r'\muzzle_flash.light', FX + r'\concussion_rifle_muzzle_flash.light'),
                   (FCFX + r'\flak_bolt_armed.effect', FX + r'\bolt_armed.effect'),
                   (FCFX + r'\flak_bolt.light_volume', FX + r'\bolt.light_volume'),
                   (FCFX + r'\flak_bolt_armed.light_volume', FX + r'\bolt_armed.light_volume'),
                   (FCFX + r'\flak_bolt.contrail', FX + r'\bolt.contrail'),
                   (r'effects\impact\explosion_large\banshee_bomb\detonation.effect', FX + r'\detonation.effect'),
                   (FCFX + r'\flak_cannon_explosion.light', FX + r'\detonation.light'),
                   (MAT + r'\flak_cannon.material_effects', FX + r'\concussion_rifle.material_effects'),
                   (MAT + r'\flak_cannon.material_effects', FX + r'\bolt.material_effects'),
                   (r'sound\weapons\flak_cannon\flak_projectile_loop\flak_projectile_loop.sound_looping',
                    FX + r'\cr_projectile.sound_looping')],
        # THE 3P LABEL: the Fuel Rod's missile / fc (a shoulder stance) -> the Carbine's rifle / cb (the Plasma
        # Repeater's: a two-handed Covenant rifle; Reach files the Concussion Rifle as a rifle, Halo 1's 'two' hands)
        'string_ids': {'missile': 'rifle', 'fc': 'cb'},
        'string_ids_done': ('weapon name', 'cb'),
        # the groups by Reach's names (4a, user): the impact explosion_large -> collision, the blast Bungie's typo
        # explosion_largw -> plasma_fast
        'string_id_renames': [(DM + r'\concussion_rifle_impact.damage_effect', {'explosion_large': 'collision'}),
                              (DM + r'\concussion_rifle_explosion.damage_effect', {'explosion_largw': 'plasma_fast'})],
        'wiring': [
            (WP, 'hlmt', FC + r'\flak_cannon', CR + r'\concussion_rifle', 'world model', {'nth': 0}),
            (CR + r'\concussion_rifle.model', 'mode', CC + r'\covenant_carbine', CR + r'\concussion_rifle', 'the world render model', {'nth': 0}),
            (WP, 'mode', FC + r'\flak_cannon', CR + r'\fp_concussion_rifle\fp_concussion_rifle', 'first person model, Master Chief', {'nth': 0}),
            (WP, 'mode', FC + r'\flak_cannon', CR + r'\fp_concussion_rifle\fp_concussion_rifle', 'first person model, Dervish (one model)', {'nth': 0}),
            (WP, 'jmad', r'objects\characters\masterchief\fp\weapons\support_high\fp_flak_cannon\fp_flak_cannon',
             r'objects\characters\masterchief\fp\weapons\rifle\fp_concussion_rifle\fp_concussion_rifle', "Master Chief FP graph: Reach's own animations"),
            (WP, 'jmad', r'objects\characters\dervish\fp\weapons\support_high\fp_flak_cannon\fp_flak_cannon',
             r'objects\characters\dervish\fp\weapons\rifle\fp_concussion_rifle\fp_concussion_rifle', "Dervish FP graph: Reach's Elite animations"),
            (WP, 'foot', MAT + r'\flak_cannon', FX + r'\concussion_rifle', 'material effects (the weapon)'),
            (WP, 'ligh', FCFX + r'\muzzle_flash', FX + r'\concussion_rifle_muzzle_flash', 'the muzzle light (recoloured violet)'),
            (WP, 'nhdt', r'ui\hud\flak_cannon', r'ui\hud\concussion_rifle', 'its own HUD (step 7)'),
            (WP, 'proj', FC + r'\projectiles\flak_bolt\flak_bolt', PJ[:-len('.projectile')], 'barrel 0: the bolt'),
            (WP, 'effe', FCFX + r'\flak_bolt_fire', FX + r'\concussion_rifle_fire', 'firing effect, barrel 0'),
            (WP, 'jpt!', FC + r'\damage_effects\flak_cannon_trigger', DM + r'\concussion_rifle_trigger', 'firing damage, barrel 0'),
            # the bolt: its own model (render model + shader), glow, trail, armed effect, burst, damage, sounds
            (PJ, 'hlmt', FC + r'\projectiles\flak_projectile', CR + r'\projectiles\concussion_rifle_bolt', 'the bolt model'),
            (CR + r'\projectiles\concussion_rifle_bolt.model', 'mode', FC + r'\projectiles\flak_projectile',
             CR + r'\projectiles\concussion_rifle_bolt', 'the bolt render model'),
            (CR + r'\projectiles\concussion_rifle_bolt.render_model', 'shad', FC + r'\shaders\flak_bolt_luminous',
             CR + r'\shaders\cr_bolt_luminous', "the bolt's glow shader (recoloured)"),
            (PJ, 'foot', MAT + r'\flak_cannon', FX + r'\bolt', 'impact material effects (the explosion sound)'),
            (PJ, 'effe', FCFX + r'\flak_bolt_armed', FX + r'\bolt_armed', 'the armed effect (embers, smoke)'),
            (PJ, 'cont', FCFX + r'\flak_bolt', FX + r'\bolt', 'the trail'),
            (PJ, 'effe', r'effects\impact\explosion_large\banshee_bomb\detonation', FX + r'\detonation', 'detonation effects (air + ground)', {'every': True}),
            (PJ, 'jpt!', FC + r'\damage_effects\flak_explosion', DM + r'\concussion_rifle_explosion', 'the blast'),
            (PJ, 'jpt!', FC + r'\damage_effects\flak_impact', DM + r'\concussion_rifle_impact', 'the impact'),
            (PJ, 'lsnd', r'sound\weapons\flak_cannon\flak_projectile_loop\flak_projectile_loop', FX + r'\cr_projectile', 'the flight loop'),
            (PJ, 'lsnd', r'sound\weapons\flak_cannon\flak_projectlie_loop2\flak_projectlie_loop2', FX + r'\cr_projectile',
             "the fuel rod's second loop: the same own loop (Reach's bolt has one)"),
            (FX + r'\bolt_armed.effect', 'MGS2', FCFX + r'\flak_bolt', FX + r'\bolt', "the bolt's glow (light volume)"),
            (FX + r'\bolt_armed.effect', 'MGS2', FCFX + r'\flak_bolt_armed', FX + r'\bolt_armed', "the armed glow (light volume)"),
            (FX + r'\detonation.effect', 'ligh', FCFX + r'\flak_cannon_explosion', FX + r'\detonation', 'the burst light (recoloured)'),
            (FX + r'\cr_projectile.sound_looping', 'snd!', r'sound\weapons\flak_cannon\flak_projectile_loop\flak_proj\loop',
             r'sound\weapons\concussion_rifle_port\cr_proj', "the flight loop: Reach's (the Brute Shot's loop, as Reach's bolt)"),
        ],
        'shared': [(r'objects\weapons\damage_effects\smash_melee(_response)', "the Fuel Rod's (4a: Reach strike -> H2 smash, the GL's)"),
                   (r'effects\generic\* particles, effects\particle_physics\*', "Bungie's generic particles (coloured by the port's own emitters)"),
                   (r'effects\decals\bullet_holes\grenade_char', "the burst's scorch (Bungie's)"),
                   (r'effects\objects\weapons\grenade\plasma_grenade\plasma_grenade_explosion (lens)', "the burst light's flare (Bungie's)")],
    },

    # step 4 -- h2_port_numbers.py: REACH's OWN values (DEFAULT = Original, boot 1); the balanced rows are the catalog's
    'numbers': {
        'numbers': [
            # the magazine: 6 / 18 / 30, six a reload; reload time 0 = Reach's animation (100 fr) drives it (the DMR's)
            (WP, 'rounds loaded maximum', 'magazines', 0, 0, 6),
            (WP, 'rounds reloaded', 'magazines', 0, 0, 6),
            (WP, 'rounds total initial', 'magazines', 0, 0, 18),
            (WP, 'rounds total maximum', 'magazines', 0, 0, 30),
            (WP, 'reload time', 'magazines', 0, 0, 0.0),
            # recovery 0.333 (3/s), the error 0.15 / 0.4..0.4 (nth 1: the live struct)
            (WP, 'fire recovery time', 'barrels', 0, 0, 0.333333),
            (WP, 'minimum error', 'barrels', 0, 1, 0.15, {'anchor': ('projectiles per shot', 6)}),   # + distribution angle
            (WP, 'error angle', 'barrels', 0, 1, [0.4, 0.4]),
            # no zoom (the Fuel Rod's 2x)
            (WP, 'magnification levels', '', 0, 0, 0),
            (WP, 'autoaim angle', '', 0, 0, 4.0),
            (WP, 'autoaim range', '', 0, 0, 15.0),
            (WP, 'magnetism angle', '', 0, 1, 8.0),
            (WP, 'magnetism range', '', 0, 1, 15.0),
            (WP, 'first person weapon offset', '', 0, 0, [0.0, 0.0, 0.0]),
            # THE BOLT: 12 -> 16 wu/s over 6..15 wu (Halo 2 has Reach's acceleration range), gravity 0.25 / 0.25, range
            # 100, minimum velocity 11 (the bolt never flies under 12: 4a), timer immediately, no guidance (the fuel
            # rod's 6 deg/s), radii 0.1 / 0.5, Reach's flags (AI ballistic aim + oriented along velocity; the fuel rod's
            # ROBOTRON STEERING off), detonation noise loud, material effect radius 0.5
            (PJ, 'initial velocity', '', 0, 0, 12.0),
            (PJ, 'final velocity', '', 0, 0, 16.0),
            (PJ, 'acceleration range', '', 0, 0, [6.0, 15.0]),
            (PJ, 'air gravity scale', '', 0, 0, 0.25),
            (PJ, 'water gravity scale', '', 0, 0, 0.25),
            (PJ, 'maximum range', '', 0, 0, 100.0),
            (PJ, 'minimum velocity', '', 0, 0, 11.0, {'anchor': ('maximum range', -4)}),
            (PJ, 'detonation timer starts', '', 0, 0, 0),
            (PJ, 'guided angular velocity (lower)', '', 0, 0, 0.0),
            (PJ, 'guided angular velocity (upper)', '', 0, 0, 0.0),
            (PJ, 'collision radius', '', 0, 0, 0.1),
            (PJ, 'danger radius', '', 0, 0, 0.5),
            (PJ, 'flags', '', 0, 1, 3),
            (PJ, 'detonation noise', '', 0, 0, 2),
            (PJ, 'material effect radius', '', 0, 0, 0.5),
            # THE IMPACT: 21.5 `collision` (the group: `weapon` string_id_renames), accel 0.75, camo damage 1
            (DM + r'\concussion_rifle_impact.damage_effect', 'damage lower bound', '', 0, 0, 21.5),
            (DM + r'\concussion_rifle_impact.damage_effect', 'damage upper bound', '', 0, 0, [21.5, 21.5]),
            (DM + r'\concussion_rifle_impact.damage_effect', 'instantaneous acceleration', '', 0, 0, 0.75),
            (DM + r'\concussion_rifle_impact.damage_effect', 'active camouflage damage', '', 0, 0, 1.0),
            # THE BLAST: 0..21.5 over 1 -> 2 (core 0.8, `plasma_fast`), THE KNOCKBACK 2.5, camo damage 1, shake 7
            (DM + r'\concussion_rifle_explosion.damage_effect', 'damage lower bound', '', 0, 0, 0.0),
            (DM + r'\concussion_rifle_explosion.damage_effect', 'damage upper bound', '', 0, 0, [21.5, 21.5]),
            (DM + r'\concussion_rifle_explosion.damage_effect', 'radius', '', 0, 0, [1.0, 2.0]),
            (DM + r'\concussion_rifle_explosion.damage_effect', 'aoe core radius', '', 0, 0, 0.8),
            (DM + r'\concussion_rifle_explosion.damage_effect', 'instantaneous acceleration', '', 0, 0, 2.5),
            (DM + r'\concussion_rifle_explosion.damage_effect', 'active camouflage damage', '', 0, 0, 1.0),
            (DM + r'\concussion_rifle_explosion.damage_effect', 'shake radius', '', 0, 0, 7.0),
            # step 4b (port_field_audit --port h2:concussion_rifle, 2026-11-26), lists 2 / 3: Reach's own
            (WP, 'active camo ding', '', 0, 0, 0.75),
            (WP, 'illumination recovery time', 'barrels', 0, 0, 0.1),
            (WP, 'firing noise', 'barrels', 0, 0, 2),                   # Reach's loud (the Fuel Rod's shout)
            (PJ, 'targeted leading fraction', '', 0, 0, 0.0),           # Reach's 0 (no guidance)
            (DM + r'\concussion_rifle_explosion.damage_effect', 'ai stun radius', '', 0, 0, 0.0, {'anchor': ('shake radius', -12)}),
            (DM + r'\concussion_rifle_explosion.damage_effect', 'ai stun bounds', '', 0, 0, [0.0, 0.0], {'anchor': ('shake radius', -8)}),
            (DM + r'\concussion_rifle_explosion.damage_effect', 'rider minimum transfer damage scale', '', 0, 0, 1.0,
             {'anchor': ('instantaneous acceleration', 20)}),   # measured: accel, 8 pad bytes, direct 1, max 0.5, min 0
            # THE LOOK, the colours that are plain fields (the colour FUNCTIONS are `--recolour`'s): the trail's two
            # point states (alpha, r, g, b: the fuel rod's 0.26 / 0.89 / 0.58) -> Reach's violet (its contrail
            # gradient); the muzzle light (0.08 / 1 / 0.06) -> Reach's deep violet (the flare gradient); the burst light
            # (0.44 / 0.98 / 0.51) -> violet; the bolt's glow shader tint (0.12 / 0.94 / 0) and glancing tint (0 / 1 / 0)
            # -> Halo 1's final PINK (the screenshot's magenta glow around a white core)
            (FX + r'\bolt.contrail', 'color lower bound', 'point states', 0, 0, [1.0] + list(VIOLET)),
            (FX + r'\bolt.contrail', 'color upper bound', 'point states', 0, 0, [1.0] + list(VIOLET)),
            (FX + r'\bolt.contrail', 'color lower bound', 'point states', 1, 0, [0.0] + list(VIOLET)),
            (FX + r'\bolt.contrail', 'color upper bound', 'point states', 1, 0, [0.0] + list(VIOLET)),
            (FX + r'\concussion_rifle_muzzle_flash.light', 'diffuse upper bound', '', 0, 0, list(VIOLET_DEEP)),
            (FX + r'\concussion_rifle_muzzle_flash.light', 'specular upper bound', '', 0, 0, list(VIOLET_DEEP)),
            (FX + r'\detonation.light', 'diffuse upper bound', '', 0, 0, list(VIOLET)),
            (FX + r'\detonation.light', 'specular upper bound', '', 0, 0, list(VIOLET)),
            (CR + r'\shaders\cr_bolt_luminous.shader', 'const color', 'parameters', 5, 0, list(PINK)),
            (CR + r'\shaders\cr_bolt_luminous.shader', 'const color', 'parameters', 6, 0, [1.0, 0.3, 0.7]),
            # BOOT 1 (user, 2026-11-27): 'Bolt and explosion is probably too big' -> the trail's width x RESIZE (the
            # fuel rod's 0.1 -> 0.025; the glow and the burst particles are `--resize`'s)
            (FX + r'\bolt.contrail', 'width', 'point states', 0, 0, 0.1 * 0.5),
            (FX + r'\bolt.contrail', 'width', 'point states', 1, 0, 0.025 * 0.5),
        ],
        'skipped': [
            ('melee strike_melee', "the Fuel Rod's smash_melee (4a: Reach strike -> Halo 2 smash, the GL's)"),
            ('reload time', "Reach's animation (100 fr) drives it: the tag field 0"),
            ("Reach's material responses (plants / liquid overpenetrate)", "the fuel rod's one element: detonate on everything"),
        ],
    },

    # step 5 -- the Carbine's authored hull (its .model is the port's, the Plasma Repeater's) on the port's own skeleton
    'collision': {
        'donor': CC + r'\covenant_carbine',
        'port': CR + r'\concussion_rifle',
        'src': r'covenant_carbine\collision\collision.jms',
        'out': CR + r'\collision\concussion_rifle.jms',
        'port_render_jms': CR + r'\render\concussion_rifle.jms',
        'donor_render_jms': r'covenant_carbine\render\covenant_carbine_L5.jms',
        'max_growth': 1.25,
        'nodes_from_render': True,
    },

    # step 9 -- h2_port_fp_anims.py kind 'reach' (the DMR's route): Reach's OWN FP animations for BOTH species
    # (Spartan -> masterchief, Elite -> dervish), helpers dropped. Reach's CR graph: fire_1 x3, reload_empty /
    # reload_full 100 (primary keyframe 48, allow interruption 63), melee_strike_1 / 2 (5 / 30 / 35), posing x2,
    # ready / put_away, throw_grenade. Not reproduced: barrel_spin (the drum's turn a shot: an overlay with no Halo 2
    # slot), sprint / jump / land / fall / ready_initial / hero_ready, throw_equipment
    'fp_anims': {
        'kind': 'reach',
        'species': {
            'masterchief': {
                'graph': R + r'objects\characters\spartans\fp\weapons\rifle\fp_concussion_rifle\fp_concussion_rifle.model_animation_graph',
                'arms_rm': R + r'objects\characters\spartans\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_masterchief\fp_arms.jms',
                'source': r'objects\characters\masterchief\fp\weapons\rifle\fp_concussion_rifle',
                # the SMG for its 17 sound slots (the DMR's reason)
                'seed': r'objects\characters\masterchief\fp\weapons\rifle\fp_smg\fp_smg'},
            'dervish': {
                'graph': R + r'objects\characters\elite\fp\weapons\rifle\fp_concussion_rifle\fp_concussion_rifle.model_animation_graph',
                'arms_rm': R + r'objects\characters\elite\fp\fp.render_model',
                'arms': H2EK + r'\data\!extracted\fp_arms_dervish\dervish_fp_arms.jms',
                'source': r'objects\characters\dervish\fp\weapons\rifle\fp_concussion_rifle',
                'seed': r'objects\characters\dervish\fp\weapons\rifle\fp_smg\fp_smg'},
        },
        'weapon_dir': CR + r'\fp_concussion_rifle',
        'weapon_rm': RM,
        'weapon_nodes': sorted(NODES.values()),
        'node_names': NODES,
        'drop_nodes': ('pedestal', 'aim_pitch', 'aim_yaw', 'l_humerus', 'r_humerus', 'l_radius', 'r_radius',
                       'l_handguard', 'r_handguard'),
        'aliases': {'first_person:look': ['first_person:overlays', 'first_person:pitch_and_turn']},
        # the FP position: the GL's accepted (0.0075, -0.002, -0.041) less the GL's own Reach first-person offset
        # (0.0125, 0, 0) plus the Concussion Rifle's (Reach CR: 0, 0, 0 -- read at step 4b), the weapon field 0
        'model_offset': (-0.005, -0.002, -0.041),
        # the DMR's per-species hand corrections, judged with h2_fp_hand_check palm (idle, gun frame, JMS units, + = the
        # palm top BELOW the underside) before boot 1: no offset Chief -1.72, Arbiter -0.81; the DMR's accepted grips
        # -0.70 / -0.30 -> the left arm down 1.02 / 0.51 units
        'left_arm_offset': {'masterchief': {'*': (0.0, 0.0, -0.0102)},
                            'dervish': {'*': (0.0, 0.0, -0.0051)}},
        'skip': ['first_person:look', 'first_person:acceleration_screens', 'first_person:fall', 'first_person:jump',
                 'first_person:land_hard', 'first_person:land_soft', 'first_person:ready_initial',
                 'first_person:sprint_enter', 'first_person:sprint_exit', 'first_person:sprint_loop',
                 'first_person:sprint_loop_airborne', 'first_person:throw_equipment', 'first_person:barrel_spin',
                 'first_person:hero_ready'],
        'looping': ['first_person:idle', 'first_person:posing:var1', 'first_person:posing:var2'],
        'overlay_reference': 'first_person:idle',
        'weights': {'first_person:posing:var1': 0.5, 'first_person:posing:var2': 0.5},
        'drop_ik': ['masterchief'],
        'clear_sound_ref_flags': True,
        'clear_verify': True,
        # Reach's graph: one sound event an animation, at frame 0 (the DMR's measurement); the reloads ONE recording
        # (fp_cr_reload, both reloads) -> split before the Balanced boot (B1 rule 5): its three pieces cued at their
        # cut times x 30 (0.90 s = 27, 1.66 s = 50), so they move with the retimed reload
        'source_events': {'cues': {'first_person:melee_strike_1': [('cr_melee', 0)],
                                   'first_person:melee_strike_2': [('cr_melee', 0)],
                                   'first_person:posing:var1': [('cr_pose1', 0)],
                                   'first_person:posing:var2': [('cr_pose2', 0)],
                                   'first_person:ready': [('cr_ready', 0)],
                                   'first_person:reload_empty': [('cr_rl_1', 0), ('cr_rl_2', 27), ('cr_rl_3', 50)],
                                   'first_person:reload_full': [('cr_rl_1', 0), ('cr_rl_2', 27), ('cr_rl_3', 50)]},
                          # the round counts at Reach's ALLOW-INTERRUPTION frame (the GL's boot 3: the primary keyframe
                          # counts it in Halo 2; Reach lets the player fire again at 63 of 100)
                          'frames': {'first_person:reload_empty': [('primary keyframe', 63), ('allow interruption', 63)],
                                     'first_person:reload_full': [('primary keyframe', 63), ('allow interruption', 63)]}},
    },

    # step 10 -- h2_port_sounds.py: Reach's OWN sounds from MCC's haloreach sfx.fsb (the DMR's `bank`), layered as
    # Reach's effects layer them: FIRE = concussion_rifle_fire + brute_shot_tails_ext (Reach's firing effect, Halo 1's
    # mix), the far layer concussion_rifle_lod_far in fire_lod (every remastered sweetener on it: the Mauler's / Laser's
    # rule); the BURST = concussion_round_expl + expl_tail_outdoor on the bolt's material effects (the fuel rod's
    # explosion sound lives there: its burst effect has none); the flight loop Reach's bolt's (the Brute Shot's loop);
    # DROPS Reach's fuel rod's (Reach's CR has none of its own: Halo 1's). One Spartan FP set for both species (Reach's
    # fp_elite_cr unused, as the DMR's)
    'sounds': {
        'weapon': WP,
        'fire_fx': FX + r'\concussion_rifle_fire.effect',
        'bank': 'haloreach',
        'audio': _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'out', 'h2_sounds', 'concussion_rifle'),
        'audio_key': 'Concussion Rifle',
        'h3_bank': {'cr_fire': [RS + r'\concussion_rifle\concussion_rifle_fire', RS + r'\brute_shot\brute_shot_tails_ext'],
                    'cr_fire_lod': [RS + r'\concussion_rifle\concussion_rifle_lod_far'],
                    'cr_ready': [RS + r'\concussion_rifle\fp_concussion_rifle\fp_cr_ready'],
                    'cr_melee': [RS + r'\concussion_rifle\fp_concussion_rifle\fp_cr_melee1'],
                    'cr_pose1': [RS + r'\concussion_rifle\fp_concussion_rifle\fp_cr_posing1'],
                    'cr_pose2': [RS + r'\concussion_rifle\fp_concussion_rifle\fp_cr_posing2'],
                    'cr_reload': [RS + r'\concussion_rifle\fp_concussion_rifle\fp_cr_reload'],
                    'cr_expl': [RS + r'\concussion_rifle\concussion_round_expl', RS + r'\surround_tails\outdoor\expl_tail_outdoor'],
                    'cr_proj': [RS + r'\brute_shot\brute_shot_projectile\brute_shot_proj\loop'],
                    'cr_drop': [RS + r'\flak_cannon\flak_cannon_drop'],
                    'cr_drop_soft': [RS + r'\flak_cannon\flak_cannon_drop_soft']},
        # Reach's reload (3.5 s, one recording for both reloads) cut in the quiet gaps all three takes share (onsets
        # 0.00-0.87 | 0.95-1.60 | 1.73-3.42 s at -40 dB)
        'split': {'cr_rl_1': ('cr_reload', 0.0, 0.90), 'cr_rl_2': ('cr_reload', 0.90, 1.66),
                  'cr_rl_3': ('cr_reload', 1.66, None)},
        'sounds': {'cr_fire': ('cr_fire', 'weapon_fire'), 'cr_fire_lod': ('cr_fire_lod', 'weapon_fire'),
                   'cr_ready': ('cr_ready', 'weapon_ready'), 'cr_melee': ('cr_melee', 'weapon_melee'),
                   'cr_pose1': ('cr_pose1', 'weapon_animation'), 'cr_pose2': ('cr_pose2', 'weapon_animation'),
                   **{n: (n, 'weapon_reload') for n in ('cr_rl_1', 'cr_rl_2', 'cr_rl_3')},
                   'cr_expl': ('cr_expl', 'projectile_detonation'), 'cr_proj': ('cr_proj', 'projectile_flyby'),
                   'cr_drop': ('cr_drop', 'object_impacts'), 'cr_drop_soft': ('cr_drop_soft', 'object_impacts')},
        'repoint_fx': [(r'sound\weapons\flak_cannon\flak_fire', 'cr_fire'),
                       (r'sound_remastered\weapons\flak_cannon\flak_fire_lod', 'cr_fire_lod'),
                       (r'sound_remastered\weapons\flak_cannon\flakcannon_lfe', 'cr_fire_lod'),
                       (r'sound_remastered\weapons\flak_cannon\flak_fire_swtnr', 'cr_fire_lod')],
        # the Fuel Rod's zoom sounds: no zoom (magnification levels 0) -> the ready, so nothing is borrowed
        'repoint_weapon': [(r'sound\weapons\beam_rifle\beam_rifle_zoom_in', 'cr_ready'),
                           (r'sound\weapons\beam_rifle\beam_rifle_zoom_out', 'cr_ready')],
        'repoint_tags': [
            (FX + r'\bolt.material_effects', r'sound\weapons\flak_cannon\flak_expl', 'cr_expl'),
            (FX + r'\bolt.material_effects', r'sound\weapons\flak_cannon\flak_cannon_drop', 'cr_drop'),
            (FX + r'\bolt.material_effects', r'sound\weapons\flak_cannon\flak_cannon_drop_soft', 'cr_drop_soft'),
            (FX + r'\concussion_rifle.material_effects', r'sound\weapons\flak_cannon\flak_cannon_drop', 'cr_drop'),
            (FX + r'\concussion_rifle.material_effects', r'sound\weapons\flak_cannon\flak_cannon_drop_soft', 'cr_drop_soft'),
            (FX + r'\concussion_rifle.material_effects', r'sound\weapons\flak_cannon\flak_expl', 'cr_drop')],
        # the SMG seed's 17 references, all repointed; unused dual slots point at the ready
        'graph_sounds': (('smg_melee1', 'cr_melee'), ('smg_ready', 'cr_ready'), ('smg_reload', 'cr_rl_1'),
                         ('smg_reload_full', 'cr_rl_1'), ('smg_dual_ready', 'cr_ready'),
                         ('smg_posing_var0', 'cr_pose1'), ('smg_posing_var1', 'cr_pose2'),
                         ('smg_dual_reload_left', 'cr_rl_2'), ('smg_dual_reload_right', 'cr_rl_3'),
                         ('smg_dual_posing_0_l', 'cr_ready'), ('smg_dual_posing_0_r', 'cr_ready'),
                         ('smg_dual_posing_1_l', 'cr_ready'), ('smg_dual_posing_1_r', 'cr_ready'),
                         ('smg_dual_posing_2_l', 'cr_ready'), ('smg_dual_posing_2_r', 'cr_ready'),
                         ('smg_dual_posing_3_l', 'cr_ready'), ('smg_dual_posing_3_r', 'cr_ready')),
        'graph_sound_dir': r'sound\weapons\smg' + '\\',
        'gain': {},
        'boost': {},
        'backup': r'E:\HaloBackups\H2EK_concussion_rifle_before_sounds',
        'graph_backup': r'E:\HaloBackups\H2EK_concussion_rifle_graphs_before_sounds',
    },

    # step 7 -- the HUD: the FUEL ROD's (its plate, its bar meter, its crosshair widget) cloned by the meter step; the
    # weapon already names ui\hud\concussion_rifle. Halo 2's fuel rod meter is ONE bar of five hexagonal cells
    # (194 x 14, thresholds 245 / 193 / 129 / 61 / 4): six cells here, each the donor's cell (`tick_box`) squeezed to
    # 194 / 6 px. The zoomed meter (sequence 1) never draws: no zoom
    'meter': {
        'donor_meter': NEW_HUD + r'\meters\fuel_rod_meter',
        'rel': NEW_HUD + r'\meters',
        'name': 'concussion_rifle_meter',
        'donor_hud': r'ui\hud\flak_cannon',
        'port_hud': r'ui\hud\concussion_rifle',
        'weapon': WP,
        'rounds': 6, 'rows': 1,
        'canvas': (194, 14), 'tick_w': 32,
        'tick_box': (0, 0, 40, 14),
        'backpack': NEW_HUD + r'\backpack_weapons',
        'backpack_port': NEW_HUD + r'\concussion_rifle_backpack',
        'backpack_size': (62, 30),
        'model_3p': CR_JMS,
        'model_skip': CR_GLOW,
        'preview': 'concussion_rifle_meter_preview.png',
    },
    'hud_plate': {
        'rel': NEW_HUD + r'\backgrounds',
        'donor': NEW_HUD + r'\backgrounds\flak_cannon',
        'other': NEW_HUD + r'\backgrounds\brute_shot_bkd',
        'name': 'concussion_rifle_bkd',
        'hud': r'ui\hud\concussion_rifle',
        'model_3p': CR_JMS,
        'model_skip': CR_GLOW,
        'fallback_box': (105, 191, 5, 34),
        'stretch': 1.4,
        # the fuel rod plate: 4 images (0 / 1 bright, Chief / Arbiter corners; 2 / 3 their dim 'out' twins), every one
        # repainted (the GL's Brute Shot layout)
        'all_images': {'dim': {2: 0, 3: 1}},
    },
    # no zoom: the scope mask blanked (the SAW's)
    'scope': {
        'rel': NEW_HUD + r'\scope_masks',
        'donor': NEW_HUD + r'\scope_masks\carbine_scope_mask',
        'name': 'concussion_rifle_blank',
        'hud': r'ui\hud\concussion_rifle.new_hud_definition',
        'widgets': ('scope_mask',),
        'size': (8, 8),
    },
    # step 8 -- the pickup icon at the reserved U+E147, untinted (the H2 ICON RULE); fc_* -> cr2_*
    'glyph': {
        'box': (160, 62),
        'model_3p': CR_JMS,
        'model_skip': CR_GLOW,
        'tif': 'concussion_rifle_h2_glyph.tif',
        'colour': (255, 255, 255),
        'style': {'line': (255, 255, 255), 'body': (153, 153, 153), 'min_line': 14},   # the DMR's (Reach's dense mesh)
    },
    'messages': {
        'donor_prefix': 'fc', 'donor_icon': '&flak_cannon',
        'donor_name': 'Fuel Rod Cannon', 'port_name': 'Concussion Rifle',
        'names': [('rods for Fuel Rod Cannon', 'rounds for Concussion Rifle'),
                  ('rod for Fuel Rod Cannon', 'round for Concussion Rifle'),
                  ('a Fuel Rod Cannon', 'a Concussion Rifle')],
        'weapon': WP,
    },
    # Reach's crosshair (its chud `elite_shot`: hud_reticles #17 at (0.85, 1.0), 'mirror horizontal' -- the sprite is
    # ONE crescent + three HALF drop triangles at its right edge; Reach draws it with its right edge on the centre and
    # its mirror on the other side, the crescent on the aim point). SIZED FROM THE USER'S REACH SCREENSHOT (Halo 1's B5
    # record, 1080p): the two crescents 88 px wide -> ink 88 / 1.117 (Halo 2's px a bitmap px, the GL's) = 79
    'reticle': {
        'rel': NEW_HUD + r'\crosshairs',
        'donor': NEW_HUD + r'\crosshairs\hud_reticles',
        'donor_sequence': 45,                # the Fuel Rod's crosshair (the cloned HUD's)
        'name': 'concussion_rifle_reticle',
        'hud': r'ui\hud\concussion_rifle',
        'footprint': 1.0,
        'h3_art': {'sheet': R + r'ui\chud\bitmaps\hud_reticles', 'sequence': 17, 'yardstick': 17,
                   'mirror': {'stretch': 0.85, 'drop': 22.6}, 'target_ink': 84},
        'preview': 'concussion_rifle_reticle_preview.png',
    },

    # step 4b -- port_field_audit.py --port h2:concussion_rifle: the source pair (Reach's CR vs Reach's FUEL ROD: weapon,
    # bolt, blast) against the target pair (the port vs Halo 2's fuel rod)
    'field_audit': {
        'source_kit': 'HREK',
        'source': {'weapon': (CR + r'\concussion_rifle.weapon', FC + r'\flak_cannon.weapon'),
                   'projectile': (CR + r'\projectiles\concussion_rifle_grenade.projectile',
                                  FC + r'\projectiles\flak_bolt.projectile'),
                   'damage_effect': (CR + r'\projectiles\damage_effects\concussion_rifle_grenade_explosion.damage_effect',
                                     FC + r'\projectiles\damage_effects\flak_bolt_explosion.damage_effect')},
        'target': {'weapon': (WP, FC + r'\flak_cannon.weapon'),
                   'projectile': (PJ, FC + r'\projectiles\flak_bolt\flak_bolt.projectile'),
                   'damage_effect': (DM + r'\concussion_rifle_explosion.damage_effect',
                                     FC + r'\damage_effects\flak_explosion.damage_effect')},
        # the first run (2026-11-26, before boot 1): list 2 written as Reach's (camo ding 0.75, illumination recovery 0.1,
        # targeted leading fraction 0, AI stun 0 / 0, 0); list 3 written: firing noise loud, rider minimum transfer 1
        'decisions': {
            'magnification range 2,2 (source 0,0)': 'no zoom: magnification levels 0 makes the range unused',
            'magnetism angle / range (the FIRST pair) 1.0': "Halo 2's first pair is the MELEE magnetism (the fuel rod's 40 deg "
                                                           "/ 1 wu): no source counterpart (the audit matched it by name); "
                                                           "Reach's 8 / 15 went into the live pair (nth 1)",
            'reload time 0 (target 5)': "Reach's animation drives the reload (100 frames), the DMR's",
            'fire recovery / error / magnetism (list 5)': "Reach's own (Original); the ratio is the catalog's",
            'danger radius 0.5 (ratio 0.29)': "Reach's own (Original); an AI-only field with no card",
            'air damage range 0,150 (Reach 0,0)': "Reach's 0,0 is unset: the fuel rod's 0..150 kept (Halo 1's B5 reading)",
            'detonation timer starts immediately / collision radius 0.1': "Reach's (written at step 4)",
            'projectile flags 3 (AI ballistic, oriented along velocity)': "Reach's flags that exist in Halo 2; the fuel rod's "
                                                                          "ROBOTRON STEERING off (Reach's bolt is unguided)",
            'material responses (1 element: detonate on everything)': "the fuel rod's; Reach's plants / liquid "
                                                                       "overpenetrate and its shield bounce lost (no block insert)",
            'barrel prediction type none (Reach instant)': "the fuel rod's (a network prediction setting; campaign only)",
            'max movement / turning acceleration / velocity 20': "the Fuel Rod clone's (Reach's 0 = unset), the GL's",
            'first person weapon offset 0': "the position lives in fp_anims model_offset (Reach's CR offset 0, override "
                                            "0, 0, -0.015 unused: the DMR / GL built on the plain field)",
            'weapon type undefined / damage reporting type flak cannon': "Halo 2's enums have no concussion rifle",
            'damage category high explosive (Reach bullet)': "Halo 1's B5: Reach's 'bullet' only reports; kept",
            'damage lower bound 0 (target 40)': "Reach's own (Original); Balanced 14.33 by the sibling rule (catalog)",
            'no such field in Halo 2': 'functions / interpolation, acceleration scale per axis, unit scales, falloff '
                                       'ranges, zoom time, ai velocity scales, flyby response, guided error radius, '
                                       "Reach's newer material response block, soft ping",
        },
    },

    # step 11 -- `python ai_firing_profile.py --h2-port concussion_rifle`: Reach's ai\generic entry (m10) over the H2
    # FUEL ROD's (the donor and yardstick)
    'firing_profile': {'from_game': 'Halo Reach', 'from_map': r'haloreach\maps\m10.map',
                       'from_weapon': CR + r'\concussion_rifle',
                       'donor_weapon': FC + r'\flak_cannon',
                       # THE ARC (Armed boot 3, user: 'They do fire ballistically. Is that intended?'): yes, Reach's bolt
                       # carries 'AI must use ballistic aiming' (gravity 0.25). Reach keeps the arc on the WEAPON
                       # (ballistic arcing fraction bounds 0 / 0, '0 = low, fast, 1 = high, slow'); Halo 2 on the
                       # character's weapon entry with the scale REVERSED ('0 = high, slow, 1 = low, fast'), so the copied
                       # 0 / 0 was Halo 2's steepest lob -> 1 / 1 (Halo 2's Scarab gun and gun-tower mortar; its Brute
                       # Shot 0.7 -> 0.9). Reach's AI velocity scales (normal 0.7 / heroic 0.9 / legendary 1.1 x the
                       # bolt's speed) have no Halo 2 field
                       'set': ['Ballistic Fraction Bounds=1.0', 'Ballistic Fraction Bounds Max=1.0'],
                       'target': 'Halo 2 ai\\generic weapons properties + firing pattern properties (H2_PORT_PLAN 0.5)'},
    # BALANCED (step 4a, user 2026-11-26: reports/h2_concussion_rifle_4a.md, the FUEL ROD ratio). The table
    # (balance_port.py "Concussion Rifle" "Flak Cannon" "Halo Reach" "Halo 2") reads the maps' values (rate 30, the
    # blast's lower 40 not by the sibling rule): its rows are all dropped (no port_tags) and every row is written here
    # from the yardstick's `balanced`, `original` = the kit's (Reach's own). The weapon row FIRST (weapon_ports.weap_path
    # reads it). Melee: the shared smash_melee, no row
    'catalog': {
        'table': 'balance_Concussion_Rifle_HaloReach_to_Halo2.json',
        'weapon_tag': CR + r'\concussion_rifle',
        'port_tags': [],
        'shared': [('jpt!', r'objects\weapons\damage_effects\smash_melee')],
        'extra_rows': (
            [{'class': 'weap', 'tag': CR + r'\concussion_rifle', 'field': f, 'block': blk, 'value': v, 'card': card,
              'original': o, **({'nth': nth} if nth else {}), **({'index': 'all'} if blk == 'Barrels' else {}),
              'note': note}
             for f, blk, nth, v, o, card, note in (
                ('Autoaim Range', None, 0, 15.0, 15.0, 'Autoaim', "the fuel rod ratio x1 (25 / 25)"),
                ('Autoaim Angle', None, 0, 4.0, 4.0, 'Autoaim', "the fuel rod ratio x1 (4 / 4)"),
                ('Magnetism Angle', None, 1, 6.0, 8.0, 'Autoaim', "the fuel rod ratio: 8 x 6 / 8"),
                ('Magnetism Range', None, 1, 15.0, 15.0, 'Autoaim', "the fuel rod ratio x1 (25 / 25)"),
                ('Fire Recovery Time', 'Barrels', 0, 0.333333, 0.333333, 'Rate of Fire', "the fuel rod ratio x1 (0.4 / 0.4); 10 ticks"),
                ('Minimum Error', 'Barrels', 1, 0.15, 0.15, 'Accuracy', "both fuel rods 0: Reach's own"),
                ('Error Angle', 'Barrels', 1, 0.4, 0.4, 'Accuracy', "both fuel rods 0: Reach's own"),
                ('Error Angle Max', 'Barrels', 1, 0.4, 0.4, 'Accuracy', "the fuel rod ratio x1 (0.05 / 0.05)"),
                ('Rounds Loaded Maximum', 'Magazines', 0, 6, 6, 'Magazine', "the fuel rod ratio x1 (5 / 5)"),
                ('Rounds Reloaded', 'Magazines', 0, 6, 6, 'Magazine', "the fuel rod ratio x1"),
                ('Rounds Total Initial', 'Magazines', 0, 18, 18, 'Magazine', "the fuel rod ratio x1 (20 / 20)"),
                ('Rounds Inventory Maximum', 'Magazines', 0, 24, 24, 'Magazine', "30 total - 6 loaded (x1)"))]
            + [{'class': 'proj', 'tag': CR + r'\projectiles\concussion_rifle_bolt', 'field': f, 'block': None, 'value': v,
                'card': card, 'original': o, 'note': note}
               for f, v, o, card, note in (
                ('Initial Velocity', 12.0, 12.0, 'Projectile Velocity', 'both fuel rods 15 -> 6.5: x1'),
                ('Final Velocity', 16.0, 16.0, 'Projectile Velocity', 'x1'),
                ('Air Gravity Scale', 0.25, 0.25, 'Projectile Gravity', 'both fuel rods 0.025: x1'),
                ('Maximum Range', 100.0, 100.0, 'Projectile Range', 'both fuel rods 80: x1'),
                ('Minimum Velocity', 11.0, 11.0, 'Projectile Velocity',
                 "both fuel rods 0 (a zero on one side): Reach's own; the bolt never flies under 12 (4a)"))]
            + [{'class': 'jpt!', 'tag': DM + '\\' + dm, 'field': f, 'block': None, 'value': v, 'card': card,
                'original': o, 'note': note}
               for dm, f, v, o, card, note in (
                ('concussion_rifle_explosion', 'Damage Lower Bound', 14.333, 0.0, 'Explosion Damage',
                 "the sibling rule: 32.25 x Halo 2's fuel rod 40 / 90 (both Reach lowers 0)"),
                ('concussion_rifle_explosion', 'Damage Upper Bound', 32.25, 21.5, 'Explosion Damage', 'the fuel rod ratio: 21.5 x 90 / 60'),
                ('concussion_rifle_explosion', 'Damage Upper Bound Max', 32.25, 21.5, 'Explosion Damage', 'the fuel rod ratio'),
                ('concussion_rifle_explosion', 'Radius', 1.0, 1.0, 'Radius', 'the fuel rod ratio: 1 x 0.5 / 0.5'),
                ('concussion_rifle_explosion', 'Radius Max', 1.333, 2.0, 'Radius', 'the fuel rod ratio: 2 x 1.5 / 2.25'),
                ('concussion_rifle_explosion', 'Area Of Effect Core Radius', 0.8, 0.8, 'Radius', 'the fuel rod ratio x1 (0.5 / 0.5)'),
                ('concussion_rifle_explosion', 'Instantaneous Acceleration', 3.75, 2.5, 'Knockback',
                 "THE KNOCKBACK: the fuel rod ratio 2.5 x 2.25 / 1.5 (Original = Reach's own 2.5, user 4a)"),
                ('concussion_rifle_impact', 'Damage Lower Bound', 21.5, 21.5, 'Impact Damage', 'the fuel rod ratio x1 (100 / 100)'),
                ('concussion_rifle_impact', 'Damage Upper Bound', 21.5, 21.5, 'Impact Damage', 'x1'),
                ('concussion_rifle_impact', 'Damage Upper Bound Max', 21.5, 21.5, 'Impact Damage', 'x1'),
                ('concussion_rifle_impact', 'Instantaneous Acceleration', 0.75, 0.75, 'Knockback', 'x1 (1 / 1)'))]),
        'fp_animations': r'objects\characters\*\fp\weapons\rifle\fp_concussion_rifle\fp_concussion_rifle',
        # the reload by the fuel rod ratio: Reach's 100 fr (3.333 s) x H2 fuel rod's TAG 5.0 s / Reach fuel rod 90 fr
        # (3.0 s) = 5.556 s (4a, user: the GL's tag rule)
        'reload_mult': round(5.556 / (100 / 30.0), 6),
        'desc': ("Halo Reach's Concussion Rifle carried into Halo 2 with its own model, textures, sounds and its own "
                 "Reach first-person animations for both species: six violet plasma bolts a magazine, three a second, "
                 "each speeding up in flight and bursting on contact with a blast that throws what it hits. "
                 "Balanced through Halo 2's Fuel Rod."),
    },
    # rounds: The Arbiter's profile carries none for the port (boot 2: 6 loaded, nothing in reserve) -> Reach's 6 / 30
    'test': {'level': '03a_oldmombasa', 'dervish_level': '04a_gasgiant', 'rounds': (6, 30)},
    'residency': {'levels': 'all', 'placements': False},
}


# ------------------------------------------------------------------------------------------------- the recolour
# THE LOOK (the brief's (4)): a borrowed Covenant look is green in places 4b does not show (Halo 1's B5). Halo 2 keeps
# an effect's colours in COLOUR FUNCTIONS (a `data` run: byte 0 the function type, byte 1 bit 0x20 = a colour function,
# two colours at +4 and +16 as B, G, R, A -- the Plasma Repeater's gauge measurement) on every particle emitter's
# `tint` and in light / light-volume / contrail colour fields. Every green or cyan colour of the port's own clones is
# turned to Reach's violet keeping its brightness; each edit goes through h2_port_weapon's byte_edits (kept only if
# tool's export differs in exactly the bytes replaced).
#: tag -> the hue (deg) its green turns to: Reach's VIOLET (265) for the flash, embers and burst; the bolt's two light
#: volumes (its glow ball) Halo 1's final PINK-MAGENTA (325: Reach's screenshot, mid 168 / 125 / 151)
RECOLOUR_TAGS = {FX + r'\concussion_rifle_fire.effect': 265.0, FX + r'\bolt_armed.effect': 265.0,
                 FX + r'\detonation.effect': 265.0, FX + r'\bolt.light_volume': 325.0,
                 FX + r'\bolt_armed.light_volume': 325.0}


def _violet(b, g, r, hue=265.0):
    """a green / cyan colour (hue 60..200 deg) -> `hue` (Reach's violet 265) with its saturation and value; else None"""
    import colorsys
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    if s < 0.08 or not (60.0 / 360 <= h <= 200.0 / 360):
        return None
    r2, g2, b2 = colorsys.hsv_to_rgb(hue / 360, s, v)
    return int(round(b2 * 255)), int(round(g2 * 255)), int(round(r2 * 255))


def recolour_rows():
    """[(tag, old hex, new hex)] for every green colour function in RECOLOUR_TAGS, read from tool's export."""
    import re
    import sys
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    import ttk_common as tc
    rows = []
    for tag, hue in RECOLOUR_TAGS.items():
        v = tc.flatten('H2EK', tag)
        runs = {}
        for k, (_t, x) in v.items():
            m = re.match(r"(.*)/data/\[(\d+)\]/value('*)$", k)
            if m:
                runs.setdefault((m.group(1), m.group(3)), []).append(int(x) & 255)
        seen = set()
        for (_own, _p), b in runs.items():
            if len(b) < 20 or not (b[1] & 0x20):
                continue
            new = bytearray(b)
            hit = False
            for at in (4, 16):
                c = _violet(b[at], b[at + 1], b[at + 2], hue)
                if c:
                    new[at:at + 3] = bytes(c)
                    hit = True
            old_hex, new_hex = bytes(b).hex(), bytes(new).hex()
            # a run tool's export pads: the muzzle flash's two colour functions are stored 20 bytes long (type, flags,
            # colour A, 1.0, 0, colour B) and the export shows 28 -- match the stored length
            raw = open(_os.path.join(r'F:\SteamLibrary\steamapps\common\H2EK\tags', tag), 'rb').read()
            if hit and bytes(b) not in raw and bytes(b[:20]) in raw:
                old_hex, new_hex = bytes(b[:20]).hex(), bytes(new[:20]).hex()
            if hit and old_hex not in seen:
                seen.add(old_hex)
                rows.append((tag, old_hex, new_hex))
    return rows


def recolour():
    import sys
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    import h2_port_weapon
    rows = recolour_rows()
    for tag, old, new in rows:
        print('   %-40s %s -> %s' % (_os.path.basename(tag), old[8:14] + '/' + old[32:38], new[8:14] + '/' + new[32:38]))
    h2_port_weapon.byte_edits({'byte_edits': rows})


# ------------------------------------------------------------------------------------------------- the resize
# BOOT 1 (user, 2026-11-27): 'The bolt looks nice. Bolt and explosion is probably too big' (Halo 1's B5 boot 2 said the
# same). The fuel rod's look is the banshee bomb's burst (burst_additive 0.25 -> 1.5 wu, flare_large 0.5 -> 2 wu) and a
# glow ball of sprites 0.25 -> 0.3 wu wide strung over 1.5 wu; Reach's detonation is one explosive_flash (bounding
# 0.73 wu) and its bolt glow ~0.35 -> Halo 1's rule x0.5 on everything that draws a size. Halo 2 keeps a size in a
# FUNCTION (EXPLOSION_VISUAL_SCALE.md 5a: byte 0 type, byte 1 flags, the output range at +4 / +8): an emitter's
# Particle Size (function 4 of 9) and Emission Radius (7); a light volume's Offset (0) and Radius (1). The rows are
# read from the CLONE'S SOURCE tag (Bungie's, never resized), so a second run finds them 'already'; a run byte-equal
# to a run the edit must not touch (byte_edits replaces every occurrence) is refused.
RESIZE = 0.5
RESIZE_TAGS = {FX + r'\detonation.effect': r'effects\impact\explosion_large\banshee_bomb\detonation.effect',
               FX + r'\bolt_armed.effect': FCFX + r'\flak_bolt_armed.effect',
               FX + r'\bolt.light_volume': FCFX + r'\flak_bolt.light_volume',
               FX + r'\bolt_armed.light_volume': FCFX + r'\flak_bolt_armed.light_volume'}


def resize_rows(scale=RESIZE):
    """[(tag, old hex, new hex)]: every size function of RESIZE_TAGS' sources with its output range x `scale`"""
    import re
    import struct
    import sys
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    import ttk_common as tc
    rows = []
    for tag, src in RESIZE_TAGS.items():
        v = tc.flatten('H2EK', src)
        runs, order = {}, []
        for k, (_t, x) in v.items():
            m = re.match(r"(.*)/data/\[(\d+)\]/value('*)$", k)
            if m:
                key = (m.group(1), len(m.group(3)))
                if key not in runs:
                    runs[key] = {}
                    order.append(key)
                runs[key][int(m.group(2))] = int(x) & 255
        want = (4, 7) if tag.endswith('.effect') else (0, 1)
        raw = open(_os.path.join(r'F:\SteamLibrary\steamapps\common\H2EK\tags', tag), 'rb').read()
        hit, other = {}, set()
        for key in order:
            d = runs[key]
            b = bytes(d[i] for i in range(max(d) + 1))
            target = ('/emitters/' in key[0] if tag.endswith('.effect')
                      else re.match(r'volumes/\[\d+\]$', key[0])) and key[1] in want
            if not target or (b[1] & 0x20):
                other.add(b)
                continue
            new = bytearray(b)
            for at in (4, 8):
                struct.pack_into('<f', new, at, struct.unpack_from('<f', b, at)[0] * scale)
            if bytes(new) == b:
                continue
            # the stored length (a run tool's export pads 20 -> 28: the recolour's finding)
            n = len(b) if b in raw or bytes(new) in raw else 20
            hit[b[:n]] = bytes(new[:n])
        for old, new in hit.items():
            if any(o.startswith(old) for o in other):
                print('   REFUSED %s %s: the same bytes are a run the resize must not touch' % (_os.path.basename(tag), old.hex()[:24]))
                continue
            rows.append((tag, old.hex(), new.hex()))
    return rows


def resize():
    import struct
    import sys
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    import h2_port_weapon
    rows = resize_rows()
    for tag, old, new in rows:
        o, n = bytes.fromhex(old), bytes.fromhex(new)
        print('   %-26s %s -> %s' % (_os.path.basename(tag), [round(struct.unpack_from('<f', o, i)[0], 4) for i in (4, 8)],
                                     [round(struct.unpack_from('<f', n, i)[0], 4) for i in (4, 8)]))
    h2_port_weapon.byte_edits({'byte_edits': rows})


if __name__ == '__main__':
    import sys as _sys
    if '--resize' in _sys.argv:
        resize()
    elif '--resize-dry' in _sys.argv:
        for _row in resize_rows():
            print(_row)
    elif '--recolour' in _sys.argv:
        recolour()
    elif '--recolour-dry' in _sys.argv:
        for _row in recolour_rows():
            print(_row)
