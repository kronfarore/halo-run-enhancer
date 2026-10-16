r"""Incineration Cannon (Halo 4, wave C9): IN PROGRESS -- step 4a decided (user, 2026-10-16); 4b next.

HALO 4 (H4EK 2026-10-16, h3_weapon_values --kit h4 + h4_projectile_summary + the effect exports): trigger
`latch`, no charge, recovery 0.8 s (rounds per second 30 = recovery-limited), 1 loaded / 4 / 6 (Ammopack 6 / 8),
rounds reloaded 2 (= 1 with one loaded), zoom 1 level 1.8x, aim (mode block = the weapon's) 5/60 10/25, error 0,
strike_melee. FP (Foundry, h4_fp_dump): fire_1 19, idle 99, ready 31 (ready_initial 29), put_away 5,
melee_strike_1 47 (primary keyframe 4), reload_empty 90 = reload_full 90, throw_grenade 44, posing var1 108 / var2
89 / var3 89, moving 21 / look 9 (overlays), first_time_pickup 75; 95 bones = the 80 arm / camera nodes + the
render model's 15 gun nodes.

THE SHELL (storm_forerunner_incineration_launcher.projectile): 21 wu/s flat, range 175, no gravity, timer
'immediately' 0, flag 'disable instantaneous first tick'; impact 200 `collision` (accel 1.5) + the burst 40..240
explosion_large over 0.75 -> 2.0 (core 0.75, accel 3) -- the Halo 4 ROCKET's own 200 + 240 (its burst 0.9 ->
2.5). `material response` (the table Halo 4 reads): default detonate, plants / liquid overpenetrate,
energy_shield_invulnerable bounce.
THE CLUSTER: the burst's effect fr_incin_main_detonation, event 6 `submunition`, 0.2 s after the burst: 5 parts
`submunition.projectile`, each 5 wu/s, pitched 45 deg off 'up' (flag 'face up regardless of location'), the
effect's conical distribution (1 yaw x 5 pitch, spread 33 deg, exponent 0.5). A bomblet: 5 -> 6 wu/s, gravity x5,
range 7, timer 'immediately' 0.6-1.0 s, minimum velocity 3; BOUNCES off the world (default_material 'never
against units', friction 0.1 / 0.1; invulnerable shields bounce) and DETONATES on a unit; impact 200 `collision`
(the shell's own impact tag) + 30..120 explosion_large over 0.61 -> 1.25 (core 0.6, accel 2.5). Flags 'oriented
along velocity', 'no impact effects on bounce'. NO BURN: no damage over time in the weapon, either projectile,
the three damage effects or the seven effects -- 'incineration' is the look.

THE APPROXIMATION (user, step 4a): option A, NATIVE BOMBLETS -- Halo 1's effect parts create projectiles too
(stock `effects\bursts\ar burst` fires 6 AR bullets): the shell's own burst effect gets an event 0.2 s after the
burst with 5 parts = an own bomblet projectile, 5 wu/s in a random cone round the surface normal
(h1_pickable_weapons `add_projectiles`, C9). LOST: the even 45 deg ring (random within a cone). TO CHECK on boot
1: an effect-made projectile's OWNER (kill credit, AI reactions).

THE WEAPON: a copy of the Halo 1 ROCKET LAUNCHER (two-handed heavy, 1-round template family, its HUD and melee;
the Brute Shot's explosive-on-a-rocket recipe) firing an own SHELL on the rocket's projectile around an own copy
of the rocket's damage table (the yardstick's, user), the bomblets on the FRAG GRENADE's projectile (it bounces)."""
import math  # noqa: F401

from ._common import B, reserved, row  # noqa: F401
from .storm_rifle import DROP

H4 = 'h4:'                                          # an H4EK path (h4_tags)
SW = r'objects\weapons\support_high\storm_forerunner_incineration_launcher'
SFP = (r'objects\characters\storm_fp\weapons\support_high\fp_forerunner_incineration_launcher'
       r'\storm_fp_forerunner_incineration_launcher')
ICUI = r'ui\hud\weapons\forerunner\forerunner_incineration_cannon\bitmap' + B   # Halo 4's crosshair art (CUI)
IC = 'weapons\\incineration cannon\\'
SND = 'sound\\weapons\\incineration_cannon_port\\'
RL = 'weapons\\rocket launcher\\'
FG = 'weapons\\frag grenade\\'
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']
# the scope's quadrant PNGs (h4_polyart_scope.py, from the user's Halo 4 zoom screenshot h4_zoom1.png, 2026-10-16)
SCOPE = r'F:\SteamLibrary\steamapps\common\HCEEK\data\weapons\incineration cannon\scope' + B
# the diffuse (h4_standin_diffuse.py <control> <this>, channel mode, tint 0.396 = the _metal material's albedo
# tint read from the tag bytes, h4_material_params) in the port's data folder
STANDIN = r'F:\SteamLibrary\steamapps\common\HCEEK\data\weapons\incineration cannon\source\ic_metal_diffuse.png'
# the glow material: srf_char_blinn_selfillum si_color (1, 0.208, 0) x15 -- RED in the user's idle screenshot
# (2026-10-16: the gun's lights read red-orange)
RED = (1.0, 0.21, 0.05)
# the shell / bomblets / flash: Forerunner hardlight orange (the Binary Rifle's approved value)
ORANGE = (1.0, 0.45, 0.2)
# the render model's 15 nodes (b_gun root), all in the FP graph
GUN = ('gun', 'low_hinge', 'r_bk_knob', 'l_low_flap', 'l_fr_top_flap', 'cylinder_a', 'r_bk_top_flap',
       'l_bk_top_flap', 'cylinder_b', 'r_fr_top_flap', 'r_cylinder', 'l_cylinder', 'r_low_flap', 'cylinder_c',
       'l_bk_knob')
# Halo 1 material indices (h1_role_compare H1_MATERIALS): Halo 4's bomblet bounces off the world and the
# invulnerable shields and DETONATES on a unit (its default_material bounce is 'never against units')
UNITS = [11, 12, 13, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 26, 30, 32]

# BOOT 1 (user: 'no projectile is visible'): a model-less projectile draws through its LIGHT-VOLUME WIDGET (Halo 1's
# plasma bolt: no model, a widget); the rocket / frag copies had none. Both projectiles now sit on Halo 1's FUEL ROD
# projectile (`grunt fuel rod`: its `hunter fuel rod` volume IS a glowing ball -- the Concussion Rifle's route, B5),
# its green look recoloured layer by layer (volume, tail contrail, sparks, light + flare, change colour, impacts), its
# rod mesh dropped. Its responses: detonate everywhere but water / plants (overpenetrate) and the Hunter shield
# (reflect); its POTENTIALS detonate everywhere but the Elite shield (#30 'disappear') -- Halo 1 applies an
# empty-window potential always (C8): #30 -> detonate on both, the bomblet's world potentials -> reflect
FR = 'weapons' + B + 'fuel rod gun' + B
FR_PROJ = FR + 'grunt fuel rod'
WORLD = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 18, 27, 31]
# BOOT 2 (user: 'the shell is a green ball'): the fuel rod ball's sprite `flares pr overcharge` is CYAN (red ~0.41) and a
# tint only multiplies -- the ball came out olive-green. The volume now draws the MONOCHROME `flares weapon lens` (64 x
# 64 y8; h1_pickable_weapons widget_tint `map`), which tints exactly: Halo 4's orange, the core (hither) whiter
ORB_MAP = B.join(['effects', 'particles', 'lens flare', 'bitmaps', 'flares weapon lens'])
ORB_HITHER = (0.8, 1.0, 0.8, 0.55)
ORB_YON = (0.8, 1.0, 0.45, 0.2)
# the fuel rod tail's `shadow beam contrail add` is a colour texture too: the trails draw the Binary Rifle port's baked
# Forerunner bolt (orange-white, its own beam core -- resident in every map), untinted
TRAIL_MAP = 'weapons' + B + 'binary rifle' + B + 'bitmaps' + B + 'bi_beam_core'

# THE BOMBLET (approximation A, user 4a): Halo 4's own numbers; built with no trigger (`triggers` []) -- the shell's
# burst effect creates it. BOUNCES off the world (Halo 4 friction 0.1 / 0.1), DETONATES on a unit
BOMBLET = {
    'projectile': (FR_PROJ, IC + 'bomblet'),
    # the IMPACT on a unit: Halo 4's 200 `collision` (the shell's own impact tag; user 4a: kept in default) --
    # the same own copy the shell names
    'damage': (RL + 'explosion', IC + 'impact'),
    'dmg': 200.0, 'acceleration': 1.5,
    'fields': {'radius': (0.0, 0.0)},
    # THE BOMBLET'S BURST: Halo 4 30..120 explosion_large over 0.61 -> 1.25 (core 0.6, accel 2.5) on an own copy
    # of the ROCKET's table (the yardstick's); the frag grenade's effect x0.625 (the Brute Shot's tuned 0.55 for
    # 1.1 wu, x 1.25/1.1)
    'explosion': {'effect': (FG + 'effects' + B + 'explosion', IC + 'effects' + B + 'bomblet explosion'),
                  'part': FG + 'explosion',
                  'scale': 0.625, 'out_dir': IC + 'effects' + B,
                  'damage': (RL + 'explosion', IC + 'bomblet explosion'),
                  'lower': 30.0, 'upper': (120.0, 120.0), 'radius': (0.61, 1.25),
                  # STEP 4b: Halo 4's own knockback 2.5 (the rocket copy's 6; balanced 6 x 2.5/3 = 5)
                  'fields': {'damage.aoe_core_radius': 0.6, 'damage.instantaneous_acceleration': 2.5,
                             # BOOT 2: a small orange flash per bomblet (Halo 4's submunition has its own area
                             # screen effect; the rocket copy's lasted 0 s)
                             'screen_flash.duration': 0.3,
                             'screen_flash.maximum_intensity': 0.3,
                             'screen_flash.tint_lower_bound.r': 1.0,
                             'screen_flash.tint_lower_bound.g': 0.33,
                             'screen_flash.tint_lower_bound.b': 0.08},
                  'swaps': {B.join(['sound', 'sfx', 'weapons', 'frag grenade', 'expl']): SND + 'ic_bomblet_explode'}},
    # BOOT 7, MEASURED (h1_projectile_probe, 3 shots): every bomblet lived ~1.2 s at a steady 5.5-6 wu/s and burst at
    # its 7 wu RANGE, never at rest -- Halo 4's final 6 is a SPEED FLOOR in Halo 1 (B4): it kept being pushed back up
    # after each bounce -> final 0: the speed falls with distance to 0 at 7 wu, it rests, the at-rest fuse runs
    'velocity': (5.0, 0.0), 'range': 7.0,
    'proj_fields': {'proj_attrs.physics.air_gravity_scale': 5.0,
                    'proj_attrs.detonation.arming_time': 0.0,
                    # BOOT 4 (user: 'bomblets visible now, they detonate before reaching the ground'): Halo 4's
                    # 0.6-1.0 s from creation ran out mid-air (Halo 1's gravity keeps them up longer) -> the fuse
                    # 'on first bounce', which in Halo 1 runs from REST (the Grenade Launcher's probe, B4): land,
                    # settle (perpendicular friction 0.8), burst 0.1-0.3 s later; a unit hit still detonates at once
                    'proj_attrs.detonation.timer': (0.1, 0.3),
                    'proj_attrs.detonation_timer_starts': 'when_at_rest',  # BOOT 6 (user: 'bounce, then explode in the air'): 'on first bounce' started at the FIRST bounce -> 'when at rest' (the Sticky Detonator's)
                    # BOOT 1 (user: 'the cluster explosion mainly is in the air'): Halo 4's minimum velocity 3 is
                    # an at-rest threshold there, but in HALO 1 IT DETONATES (A7): a bomblet launched up at 5 wu/s
                    # under x5 gravity passed 3 wu/s near its apex and burst mid-air -> 0, the timer decides
                    'proj_attrs.detonation.minimum_velocity': 0.0,
                    'proj_attrs.flags.oriented_along_velocity': True,
                    # STEP 4b list 2 (H4 submunition vs the H4 frag onto the H1 frag): danger radius 2.25 x 3/2.5,
                    # air damage range 0..10 x 500/10, water gravity 1 x 0/0.75. List 3 (a zero on one side: the
                    # source value): bounding radius 0.5, collision radius 0.1. Timer (0.5-0.77 by the ratio) and
                    # gravity (5.56) are BALANCED rows; default Halo 4's own
                    'proj_attrs.detonation.danger_radius': 2.25 * 3 / 2.5,
                    'proj_attrs.physics.air_damage_range': (0.0, 500.0),
                    'proj_attrs.physics.water_gravity_scale': 0.0,
                    'obje_attrs.bounding_radius': 0.5,
                    'proj_attrs.collision_radius': 0.1},
    'default_responses': {'reflect': WORLD, 'detonate': UNITS, 'overpenetrate': [28, 29]},
    # BOOT 2 (user: 'the bomblets are unchanged' -- still bursting in the air): Halo 1's friction is the fraction of
    # speed REMOVED (the frag: parallel 0.7-0.8, perpendicular 0.8-0.9), so Halo 4's 0.1 / 0.1 bounced near-elastic --
    # a bomblet launched up hopped high and its 0.6-1.0 s fuse ran out mid-hop. Perpendicular 0.8 (the frag's: a low
    # bounce), parallel 0.3 (some of Halo 4's slide)
    'reflect': [{'materials': WORLD, 'response': 'reflect', 'angle_deg': (0.0, 0.0),
                 'parallel_friction': 0.3, 'perpendicular_friction': 0.8, 'effect_from_default': False},
                {'materials': [30], 'response': 'detonate', 'angle_deg': (0.0, 0.0), 'effect_from_default': False}],
    # per-material DETONATION effects would replace the burst on contact (the GL's trap)
    'clear_detonation_effects': True,
    # 4b template diff: Halo 4's flag 'no impact effects on bounce' -> every response effect cleared (a unit hit
    # shows the burst); the frag effect's `shock wave` part (0 damage: camera shake + a physics push to 8 wu) stays
    'clear_response_effects': True,
    # Halo 4's bomblet: a small orange ball with a short trail -- the fuel rod's ball x0.4, its tail contrail
    # recoloured and narrower, its light + flare orange; the sparks dropped
    'model': '',
    'keep_attachments': (0,),
    # BOOT 2 (user: 'no visible projectiles on the bomblets'): the ball was x0.4 (0.008 - 0.04 wu) and olive -> x0.7 on
    # the orange sprite, the flare 0.06 -> 0.1
    # BOOT 8 (user: 'the trail keeps bouncing and changing angles'): the fuel rod tail's long ribbon kinked at every
    # bounce -> a SHORT thin streak (points live 0.08-0.1 s, 0.04 -> 0.02 wu), the Binary Rifle's state form
    'contrail': {'from': FR + 'tail', 'out': IC + 'bomblet trail', 'rgb': (1.0, 1.0, 1.0),
                 'bitmap': TRAIL_MAP, 'sequence': (0, 0),
                 'states': [{'duration': (0.08, 0.1), 'transition': (0.05, 0.08), 'width': 0.04,
                             'argb': (1.0, 1.0, 1.0, 1.0)},
                            {'width': 0.02, 'argb': (0.0, 1.0, 1.0, 1.0)}]},
    'widget_tint': {'out': IC + 'bomblet volume', 'hither': ORB_HITHER, 'yon': ORB_YON, 'radius': 0.7, 'map': ORB_MAP},
    'glow': {'light': (FR + 'fuel rod exhaust', IC + 'bomblet glow'),
             'flare': IC + 'bomblet glow', 'rgb': ORANGE, 'flare_radius': 0.1, 'marker': 'contrail'},
    'change_color': {'from': 'weapons' + B + 'plasma pistol' + B + 'bolt', 'rgb': ORANGE},
    'triggers': [],
}

# THE SHELL, Halo 4's own numbers (on the fuel rod projectile: BOOT 1, above)
SHELL = {
    'projectile': (FR_PROJ, IC + 'shell'),
    'damage': (RL + 'explosion', IC + 'impact'),
    'dmg': 200.0, 'acceleration': 1.5,
    'fields': {'radius': (0.0, 0.0)},
    # THE BURST: Halo 4 40..240 explosion_large over 0.75 -> 2.0 (core 0.75, accel 3) on an own copy of the
    # rocket's table; the rocket's own explosion effect (a fireball, 2.0 wu = the rocket's), the screen flash
    # yellow + short (A7; the Sticky Detonator's approved 0.25 s / 0.3); + THE CLUSTER
    'explosion': {'effect': (RL + 'effects' + B + 'rocket explosion', IC + 'effects' + B + 'shell explosion'),
                  'out_dir': IC + 'effects' + B,
                  'damage': (RL + 'explosion', IC + 'explosion'),
                  'lower': 40.0, 'upper': (240.0, 240.0), 'radius': (0.75, 2.0),
                  # STEP 4b: Halo 4's own knockback 3 (the rocket copy's 6; balanced 6 x 3/3 = 6)
                  'fields': {'damage.aoe_core_radius': 0.75, 'damage.instantaneous_acceleration': 3.0,
                             # BOOT 2 (user: 'the screen flash is underwhelming -- increase it and fit the gun's
                             # theme'): Halo 4's detonation area screen effect = exposure boost 5-6 over 0.6 / 1.0 s, a
                             # red-orange colour replace (1, 0.12, 0) x0.8 and an orange filter (0.81, 0.33, 0.08) ->
                             # 0.8 s, intensity 0.6, the filter's orange (was the Sticky Detonator's 0.25 s / 0.3 yellow)
                             'screen_flash.priority': 'medium',
                             'screen_flash.duration': 0.8,
                             'screen_flash.maximum_intensity': 0.6,
                             'screen_flash.tint_lower_bound.r': 1.0,
                             'screen_flash.tint_lower_bound.g': 0.33,
                             'screen_flash.tint_lower_bound.b': 0.08},
                  'swaps': {B.join(['sound', 'sfx', 'weapons', 'frag grenade', 'expl']): SND + 'ic_explode'},
                  # THE CLUSTER (option A): 5 bomblets 0.2 s after the burst at the 'normal' location, 5 wu/s, a
                  # random cone (Halo 4: 45 deg off the surface + a 33 deg spread -> 60 deg, judged in game)
                  # BOOT 3, MEASURED (h1_projectile_probe, the user's 5 shots): the bomblets left at ~154 wu/s and
                  # burst after 0.03-0.2 s at <= 7 wu (their maximum range) -- Halo 1 reads an effect PART's velocity
                  # PER TICK (5 x 30.9), unlike a projectile's (Reclaimer per second) -> 5 wu/s = 5 / 30 a tick
                  'add_projectiles': [{'projectile': IC + 'bomblet', 'count': 5, 'velocity': (5.0 / 30, 5.0 / 30),
                                       'cone_deg': 60.0, 'delay': 0.2, 'location': 1}]},
    'velocity': (21.0, 21.0), 'range': 175.0,
    # the fuel rod's timer (on first bounce, 0) kept: every response detonates (the Brute Shot's note)
    'proj_fields': {'proj_attrs.physics.air_gravity_scale': 0.0,
                    'proj_attrs.detonation.minimum_velocity': 0.0,
                    'proj_attrs.flags.oriented_along_velocity': True,
                    # STEP 4b list 2 (H4 shell vs the H4 rocket onto the H1 rocket): bounding radius 0.1 x 0.5/0.1,
                    # air damage range 0..100 x 50/150, water gravity 0.4 x 0/0.4; COLLISION RADIUS 0.1 x 0.1/0.02
                    # = 0.5 by the ratio (Halo 4's own 0.1 -- for the user: a near miss within 0.5 wu hits)
                    'obje_attrs.bounding_radius': 0.5,
                    'proj_attrs.physics.air_damage_range': (0.0, 100 * 50 / 150.0),
                    'proj_attrs.physics.water_gravity_scale': 0.0,
                    'proj_attrs.collision_radius': 0.5},
    # Halo 4's shell detonates on everything but invulnerable shields: the Hunter shield too (the fuel rod reflects)
    'default_responses': {'detonate': [32]},
    'reflect': [{'materials': [30], 'response': 'detonate', 'angle_deg': (0.0, 0.0), 'effect_from_default': False}],
    'clear_detonation_effects': True,
    # Halo 4's shell: an orange orb with an energy trail and sparks -- the fuel rod's ball, tail contrail and tail
    # sparks recoloured, its light + flare orange, its rod mesh dropped (Halo 4's projectile loops are empty in MCC,
    # C1: no flight sound); the impact particles orange (the Concussion Rifle's `impact_tint`)
    'model': '',
    'keep_attachments': (0, 1),
    'contrail': {'from': FR + 'tail', 'out': IC + 'shell trail', 'rgb': (1.0, 1.0, 1.0),
                 'bitmap': TRAIL_MAP, 'sequence': (0, 0)},
    'set_attachments': {1: {'class': 'effect', 'type': FR + 'effects' + B + 'fuel rod tail sparks',
                            'copy': {'out': IC + 'effects' + B + 'shell sparks', 'tint': (1.0,) + ORANGE,
                                     'scale': 1.0, 'count': 1.0}}},
    'widget_tint': {'out': IC + 'shell volume', 'hither': ORB_HITHER, 'yon': ORB_YON, 'map': ORB_MAP},
    'glow': {'light': (FR + 'fuel rod exhaust', IC + 'shell glow'), 'flare': IC + 'shell glow',
             'rgb': ORANGE, 'flare_radius': 0.12, 'marker': 'contrail'},
    'change_color': {'from': 'weapons' + B + 'plasma pistol' + B + 'bolt', 'rgb': ORANGE},
    # BOOT 2 (user: 'the ground splash has the plasma burn and impact as well -- fit it to the weapon'): the fuel rod's
    # per-material impact effects (plasma splash + burn decal) cleared; the burst is the rocket's fireball with its own
    # scorch (`grenade char`)
    'clear_response_effects': True,
    'triggers': [0],
}

PORT = reserved(
    order=34, wave='C9', name='Incineration Cannon', source='Halo 4',
    messages=(101, 102), icon=54, reticle=43, label='ic', teach_from='pc',
    sound_dir='sound\\weapons\\incineration_cannon_port', weapon_dir='weapons\\incineration cannon',
    yardstick={
        # step 4a (user, 2026-10-16; h3_weapon_values --kit h4 + h4_projectile_summary + h1_role_compare
        # incineration_cannon). Halo 4: rocket 200 impact + 240 explosion_large over 0.9 -> 2.5, 0.8 s, 2 / 4 / 6,
        # 116 fr, 10 -> 20 wu/s, gravity 0.02, 175, aim 5/60 10/25; fuel rod 100 + 60 over 0.5 -> 2.25, 0.4 s, 5 /
        # 15 / 20, 90 fr, 19.5 -> 8.45, 80, aim 4/25 8/25. Halo 1: rocket 315 over 0.5 -> 2.0, 2.0 s, 2 / 4 / 8,
        # reload tag 5.0 s over a 125 fr animation, 12 -> 10, 128, zoom 2.0, aim 0/35 12/35; restored fuel rod 75
        # over 0.5 -> 1.5 (Hunters immune).
        'pick': 'Rocket Launcher',
        'reason': ("user, step 4a 2026-10-16: the ROCKET LAUNCHER -- Halo 4's shell IS its rocket's damage (200 + "
                   "240), so the ratio 315/440 is clean; the Fuel Rod ratio came out weak (82 dps) with Hunters "
                   "immune. The cluster: option A, native bomblets in a random cone; the bomblet's 200 impact on a "
                   "unit kept in default (Halo 4's own). DEFAULT = Halo 4's own numbers on the rocket's table."),
        # DEFAULT = Halo 4's own; these are the BALANCED rows (the ROCKET ratio by the direct hit, 315/440):
        'balanced': {
            'impact': 143.2,                 # 200 x 315/440
            'damage': 171.8,                 # 240 x 315/440 (lower 40 -> 28.6)
            'radius': (0.417, 1.6),          # 0.75 x 0.5/0.9, 2.0 x 2.0/2.5
            'bomblet_damage': 85.9,          # 120 x 315/440 (lower 30 -> 21.5)
            'bomblet_radius': (0.339, 1.0),  # 0.61 x 0.5/0.9, 1.25 x 2.0/2.5
            'fire_recovery_s': 2.0,          # 0.8 x 2.0/0.8
            'magazine': 1,                   # 1 x 2/2
            'rounds_total_initial': 4,       # 4 x 4/4
            'rounds_total_maximum': 8,       # 6 x 8/6
            'reload_s': 125 * 90 / 116.0 / 30.0,   # 125 fr x 90/116 = 97 fr
            'velocity': (25.2, 10.5),        # 12 x 21/10, 10 x 21/20
            'range': 128.0,                  # 128 x 175/175
            'aim': (5.0, 35.0, 12.0, 35.0)},  # the source angle 5 KEPT (the rocket's 0: C8's rule), 35 x 60/60;
                                              # 12 x 10/10, 35 x 25/25
        # Time to kill (h1_role_compare incineration_cannon, direct hits): default 440 at 1.25/s = 550 dps (+2
        # bomblets 850, +5 1300) -- one shell everything, Legendary too; balanced 315 at 0.5/s = 158 (= the
        # rocket), + 5 bomblets 372; Legendary Elite major / commander 2 shells without bomblets
        'measured': 'h1_role_compare.py incineration_cannon',
        'not_reproduced': ("the cluster's even 45 deg ring (Halo 1: a random cone round the surface normal)"),
        'candidates': {
            'source_weapon': 'objects\\weapons\\support_high\\storm_forerunner_incineration_launcher\\storm_forerunner_incineration_launcher',
            'provisional': 'Rocket Launcher',
            'alternatives': ['Flak Cannon'],
            'direct': None,
            'peers': ['Rocket Launcher', 'Flak Cannon'],
            'why': 'a rocket-launcher-type weapon, 1-round magazine, explosive projectile, 1.8x zoom',
            'lacks': 'the cluster (native bomblets, approximated: a random cone); no burn exists in Halo 4'}},
    # step 11: the source game's ai\generic entry (24 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map',
                    'from_weapon': 'objects\\weapons\\support_high\\storm_forerunner_incineration_launcher\\storm_forerunner_incineration_launcher'},
)

PORT.update({
    'status': 'in progress',
    # BORROWED sounds kept ON PURPOSE (port_sound_refs prints these as KEEP)
    'sound_keeps': {r'sound\sfx\impulse\weapon_drops\rlauncher_impact':
                    "Halo 4's own drop (wea_drop_launcher_fr_incinerator_nonplayer) ships in no MCC bank: "
                    "the rocket launcher's kept",
                    r'sound\sfx\weapons\weapon_pickup_ammo\rocket_ammo':
                    "Halo 4 has no Incineration Cannon ammo pickup sound: the rocket launcher's kept (user, boot 2)"},

    # geometry + look (h1_h3_weapon_model.py; Halo 4 through h4_tags). Halo 4's ONE render model for world AND
    # first person: 15 nodes (b_gun root; low hinge, cylinders, top / low flaps, knobs), regions default (mesh 0:
    # the body, 4,971 vertices) and knight_arm (meshes 1-2, 8,638: the flaps / cylinders over the front -- NOT an
    # arm, and the .model's default variant draws both regions: all kept); materials _default_metal
    # (srf_char_forerunner_andrew, NO colour map: the control-map stand-in) and _default_glow
    # (srf_char_blinn_selfillum, si_color (1, 0.208, 0) x15). Markers: primary_trigger, left_hand(_spartan_fp),
    # barrel, vent, plates (the firing / reload effects' locations), flashlight
    'model': {
        'dir': r'weapons\incineration cannon',
        'world': H4 + SW + r'\storm_forerunner_incineration_launcher.render_model',
        'fp': H4 + SW + r'\storm_forerunner_incineration_launcher.render_model',
        'world_name': 'incineration cannon',
        'decimate': {'keep': 60.0, 'protect': 1.0, 'views': [((-0.1529, 0.0779, 0.0466), (0.9988, -0.0434, 0.021), (-0.0211, -0.0028, 0.9998), 1.0), ((-0.1522, 0.0775, 0.049), (0.9983, -0.0477, 0.0336), (-0.034, -0.008, 0.9994), 1.0), ((-0.1529, 0.0779, 0.0466), (0.9988, -0.0434, 0.021), (-0.0211, -0.0028, 0.9998), 1.0), ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), 1.0), ((0.0, 0.0, 0.0), (1.0, -0.0036, 0.0047), (-0.0047, 0.0059, 1.0), 1.0), ((0.0, 0.0, 0.0), (1.0, 0.0026, -0.0027), (0.0027, -0.0089, 1.0), 1.0), ((-0.1529, 0.0779, 0.0466), (0.9989, -0.0431, 0.021), (-0.0211, -0.0026, 0.9998), 1.0), ((-0.0879, 0.0763, 0.053), (0.9889, -0.0346, -0.1443), (0.1447, 0.0102, 0.9894), 1.0), ((-0.1529, 0.0779, 0.0466), (0.9989, -0.0431, 0.021), (-0.0211, -0.0026, 0.9998), 1.0), ((-0.1775, 0.1166, 0.001), (0.6862, 0.1976, 0.7001), (-0.7022, 0.4312, 0.5666), 0.5), ((-0.1727, 0.077, 0.044), (0.9975, -0.0462, -0.0538), (0.0575, 0.0826, 0.9949), 0.5), ((-0.1775, 0.1166, 0.001), (0.6862, 0.1976, 0.7001), (-0.7022, 0.4312, 0.5666), 0.5), ((-0.1529, 0.0779, 0.0466), (0.9988, -0.0433, 0.0212), (-0.0213, -0.0026, 0.9998), 0.5), ((-0.1881, 0.0949, 0.0317), (0.9596, -0.1751, 0.2203), (-0.2353, -0.0695, 0.9694), 0.5), ((-0.1529, 0.0779, 0.0466), (0.9988, -0.0433, 0.0212), (-0.0213, -0.0026, 0.9998), 0.5), ((-0.1529, 0.0779, 0.0466), (0.9988, -0.0433, 0.0212), (-0.0213, -0.0026, 0.9998), 0.5), ((-0.1881, 0.0957, 0.0321), (0.9589, -0.1792, 0.2198), (-0.2354, -0.0711, 0.9693), 0.5), ((-0.1529, 0.0779, 0.0466), (0.9988, -0.0433, 0.0212), (-0.0213, -0.0026, 0.9998), 0.5), ((-0.1529, 0.0779, 0.0466), (0.9989, -0.043, 0.021), (-0.0212, -0.0027, 0.9998), 0.5), ((-0.1862, 0.1083, -0.0066), (0.8341, -0.3901, 0.3899), (-0.4487, -0.0691, 0.891), 0.5), ((-0.1529, 0.0779, 0.0466), (0.9989, -0.043, 0.021), (-0.0212, -0.0027, 0.9998), 0.5)]},
        'ground_point': 'auto',
        'markers': {'primary_trigger': 'primary trigger', 'left_hand': 'left hand'},
        # an own hull (the template's hides the world model, C1): the render model's extent (all three meshes: x
        # -0.233..0.21, y +-0.033, z -0.019..0.114 wu)
        'collision': {'material': 'metal',
                      'boxes': [((-0.233, -0.033, -0.019), (0.21, 0.033, 0.114))]},
        # Halo 1's `tool model` keeps 31 characters of a shader name (C1)
        'material_names': {'storm_forerunner_incineration_launcher_default_metal': 'ic_metal',
                           'storm_forerunner_incineration_launcher_default_glow': 'ic_glow'},
        'shaders': {'ic_metal': (STANDIN, None)},
        'template': 'weapons\\assault rifle\\' + r'fp\shaders\gun',
        'glow': {},
        # the glow material: an additive glow per UV island in Halo 4's red (the Binary Rifle's tuned settings)
        'glow_shaders': {'ic_glow': {'rgb': RED, 'additive': True, 'islands': True,
                                     'islands_of': 'storm_forerunner_incineration_launcher_default_glow',
                                     'gain': 3.0, 'falloff': 0.35, 'radius': 1.5, 'hot': False},  # BOOT 1 (user: 'improve the glow'): 2.2 / 1.3 -> 3.0 / 1.5
                         # Halo 4's hardlight plate LIGHT-UPS per shot (the muzzle-flash rule below): the Binary
                         # Rifle's firing glow -- the glow pieces again, hotter orange and wider, FADED by A out =
                         # the rocket template's firing ILLUMINATION (on per shot, back to 0 over its 0.3 s
                         # recovery)
                         'ic_fire_glow': {'rgb': (1.0, 0.65, 0.25), 'additive': True, 'islands': True,
                                          'islands_of': 'storm_forerunner_incineration_launcher_default_glow',
                                          'strip': True, 'gain': 3.0, 'falloff': 0.6, 'radius': 1.8,  # BOOT 1 ('pop even more when firing'): hotter, wider
                                          'hot': False, 'fade_source': 'A_out',
                                          # BOOT 4 (user: one tile still unlit in FP, screenshot): glow piece 12
                                          # (x -1.1, y +1.9, z 8.0 -- the HIGHEST) faces INTO the gun (its twin 13
                                          # faces out); the card copies its winding and was back-face culled
                                          'two_sided': True},
                         # BOOT 4 (user: 'try the empty-chamber glow for the reload instead of the rings'): Halo 4's
                         # reload lights the gun up as it draws energy in -- Halo 1 has no reload state to read, but
                         # PRIMARY AMMUNITION is 0 from the shot until the reload has loaded the round: the glow pieces
                         # again, Halo 4's red-orange, FADED by B out = B in (primary ammunition) INVERTED (`obje_functions`
                         # function 1) -- lit from the shot through the reload, off once loaded
                         'ic_reload_glow': {'rgb': (1.0, 0.3, 0.08), 'additive': True, 'islands': True,
                                            'islands_of': 'storm_forerunner_incineration_launcher_default_glow',
                                            'strip': True, 'gain': 2.6, 'falloff': 0.7, 'radius': 1.6,
                                            'hot': False, 'fade_source': 'B_out', 'two_sided': True}},
        # BOOT 3 (user: 'the firing glow is not aligned with the glowing parts; the highest glow part has none, in FP'):
        # the Binary Rifle's `skip_piece_normals` (+-x) skipped every piece facing along the barrel -- the muzzle-end
        # bars nearest the view (h1_gbxmodel_render: no card there, nor on one rear square) -> no skips; the cards
        # back to the Binary Rifle's x2.0 / round 1.6 so they hug the strips (boot 2's x2.6 / 2.0 stood off them)
        'glow_cards': {'ic_fire': {'of': 'ic_glow', 'shader': 'ic_fire_glow', 'scale': 2.0, 'along': 1.1,
                                   'lift': 0.08, 'round_scale': 1.6},
                       'ic_reload': {'of': 'ic_glow', 'shader': 'ic_reload_glow', 'scale': 2.4, 'along': 1.15,
                                     'lift': 0.1, 'round_scale': 1.8},
                       # BOOT 6 (user: 'still missing the last flagged part'; two-sided did not do it): piece 12 sits
                       # in a slot and faces INTO the gun -- its card hid behind the slot wall. Its own card, lifted
                       # 0.5 cm against that inward normal (= outward; `near` its centre, x -1.1 y +1.9 z 8.0 cm)
                       'ic_fire_slot': {'of': 'ic_glow', 'shader': 'ic_fire_glow', 'near': ((-1.1, 1.9, 8.0), 0.6),
                                        'scale': 2.0, 'along': 1.1, 'lift': -0.2, 'round_scale': 1.6}},  # BOOT 7 (user: the tile's card floats off the gun): -0.5 -> -0.2
    },

    # FP animations (h1_fp_retarget.py): ROUTE (a), Halo 4's own storm_fp_forerunner_incineration_launcher
    # (Foundry, h4_fp_dump.py -> out\h4_fp 2026-10-16: 25 animations, 95 bones), the arms RE-SOLVED
    'retarget': {
        'graph': H4 + SFP + '.model_animation_graph',
        'render_model': H4 + SW + r'\storm_forerunner_incineration_launcher.render_model',
        'nodes': {n: 'frame b ' + n.replace('_', ' ') for n in GUN},
        'drop_nodes': tuple(DROP),
        'h1_dir': r'weapons\incineration cannon\fp',
        'h1_model': r'weapons\incineration cannon\fp\fp',
        'align': 'same_space',
        # C5: a long FP gun -- start at Halo 4's own placement and judge through h1_fp_camera_render
        # BOOT 1 (user: 'lower the FP by 2 units'; 1 unit = 0.01 wu, the Suppressor's)
        'view_offset': (0.0, 0.0, -0.02),
        # BOOT 2 (user: 'after a melee the left arm lingers lower than idle before reverting'): Halo 4's
        # melee_strike_1 ends with the left wrist ~4 cm low / 6 cm aside of idle's first pose and Halo 4 BLENDS;
        # Halo 1 snaps -> its last 12 frames (0.4 s, the recovery) eased into idle frame 0
        'blend_end': {'first-person melee': ('first_person:idle', 0, 12)},
        'anims': {
            'first_person:idle': 'first-person idle',
            'first_person:posing:var1': 'first-person posing',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:fire_1:var1': 'first-person fire-1',
            'first_person:melee_strike_1': 'first-person melee',
            'first_person:moving': 'first-person moving',
            'first_person:look': 'first-person overlays',
            'first_person:throw_grenade': 'first-person throw-grenade',
            'first_person:reload_empty': 'first-person reload-empty',
            'first_person:reload_full': 'first-person reload-full',
        },
    },

    # Halo 4's own sounds (h1_port_sounds.py incineration_cannon, `bank` 'halo4'): the player bank
    # forerunner_incineration_launcher_player (one event per FP animation: play_weapons_incinerator_player_<anim>;
    # the fire / dry fire events), the projectile bank proj_forerunner_incinerator (the shell's and the bomblet's
    # explosions; the sound tags name `proj_incinerator_launcher`, which ships nowhere -- found by the events' FNV
    # ids in the shipped banks, the name by its FNV). The DROP event (wea_drop_launcher_fr_incinerator_nonplayer)
    # ships in NO bank: the rocket's own drop sound kept (`sound_keeps`, the Sticky Detonator's ammo-pickup
    # precedent -- for the user at close-out). Levels = the stock Halo 1 sound each stands in for (the Brute Shot's measurements, 2026-10-09):
    # rocket fire -15.1, frag expl -7.9, rocket_reload_e -22.5, rocket_ready -18.3, rocket_melee -21.8,
    # rocket_posing -22.1, rlauncher_impact -23.0, rocket_ammo -28.8, AR dryfire -17.6
    'sounds': {
        'catalog': 'Incineration Cannon',
        'bank': 'halo4',
        'wwise_bank': 'forerunner_incineration_launcher_player',
        'dir': B.join(['sound', 'weapons', 'incineration_cannon_port']),
        'sounds': {
            # fire = 4 layers (h4_event_layers): a random of 3 (the main, 3.5-5.4 s), a random of 2 (the low body,
            # 200-370 Hz), a 0.46 s punch (99 Hz), a 0.76 s sub (-19.6 dB)
            'ic_fire': (['play_wea_forerunner_incineration_launcher_player_fire:0,1,2',
                         'play_wea_forerunner_incineration_launcher_player_fire:3,4',
                         'play_wea_forerunner_incineration_launcher_player_fire:5',
                         'play_wea_forerunner_incineration_launcher_player_fire:6'],
                        'sound\\sfx\\weapons\\rocket launcher\\fire', -15.1),
            'ic_explode': (['play_wea_forerunner_incinerator_proj_explosion@proj_forerunner_incinerator'],
                           'sound\\sfx\\weapons\\frag grenade\\expl', -7.9),
            # a bomblet: smaller than the shell's burst (Halo 4's own event; level by ear at boot 1)
            'ic_bomblet_explode': (['play_wea_forerunner_incinerator_submunition_proj_explode@proj_forerunner_incinerator'],
                                   'sound\\sfx\\weapons\\frag grenade\\expl', -10.9),
            'ic_dryfire': (['play_wea_forerunner_incinerator_player_dry_fire'],
                           'sound\\sfx\\weapons\\assault rifle\\dryfire', -17.6),
            'ic_ready': (['play_weapons_incinerator_player_ready'],
                         'sound\\sfx\\weapons\\weapon_anims\\rocket_ready', -18.3),
            'ic_melee': (['play_weapons_incinerator_player_melee_strike1'],
                         'sound\\sfx\\weapons\\weapon_anims\\rocket_melee', -21.8),
            'ic_reload': (['play_weapons_incinerator_player_reload_empty'],
                          'sound\\sfx\\weapons\\weapon_anims\\rocket_reload_e', -22.5),
            'ic_reload_balanced': (['play_weapons_incinerator_player_reload_empty'],
                                   'sound\\sfx\\weapons\\weapon_anims\\rocket_reload_e', -22.5),
            # posing var1: the graph's per-animation event plays nothing in the bank; its cues are the separate
            # posing_var1_player a / b / c events (frame events @0, @33, @79). fire1_var1 (the FP fire cue) ships in
            # no bank: none (the fire sound plays from the firing effect)
            'ic_pose': (['play_incinerator_first_person_posing_var1_player_a',
                         'play_incinerator_first_person_posing_var1_player_b',
                         'play_incinerator_first_person_posing_var1_player_c'],
                        'sound\\sfx\\weapons\\weapon_anims\\rocket_posing', -22.1),
            # 4b (the sound fields by hand): Halo 4's own zoom sounds over the rocket template's sniper ones (levels:
            # the Binary Rifle's measurements of sniper_2x / 10x_zoom)
            'ic_zoom_in': (['play_wea_forerunner_incineration_launcher_player_zoom_in'],
                           'sound\\sfx\\weapons\\sniper rifle\\sniper_2x_zoom', -28.9),
            'ic_zoom_out': (['play_wea_forerunner_incineration_launcher_player_zoom_out'],
                            'sound\\sfx\\weapons\\sniper rifle\\sniper_10x_zoom', -29.2),
        },
        # the BALANCED reload's sound (the patcher swaps it in with the retimed reload: catalog anim_sounds)
        'stretch': {'ic_reload_balanced': 97.0 / 90.0},
        'offsets': {'ic_pose': [0.0, 33 / 30.0, 79 / 30.0]},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only incineration_cannon) on a COPY of the Halo 1 ROCKET LAUNCHER
    # firing the SHELL above; the BOMBLET built beside it. DEFAULT = HALO 4's OWN NUMBERS; the ratio values are
    # the balance rows
    'pickable': {
        'weapon': IC + 'incineration cannon',
        'template': RL + 'rocket launcher',
        'world_model': IC + 'incineration cannon',
        # ONE model tag for world AND first person (the 32 MiB model buffer, H1_PORT_PLAN 0.1)
        'fp_model': IC + 'incineration cannon',
        'fp_anims': IC + 'fp' + B + 'fp',
        'label': 'ic',
        # two-handed HEAVY (reserved: 'ic' taught from the plasma cannon's 'pc')
        'teach': ('ic', 'pc'),
        'keys': {'first-person melee': 4},          # Halo 4 melee_strike_1 primary keyframe 4
        'sounds': {'first-person ready': SND + 'ic_ready',
                   'first-person posing': SND + 'ic_pose',
                   'first-person melee': SND + 'ic_melee',
                   'first-person reload-empty': SND + 'ic_reload',
                   'first-person reload-full': SND + 'ic_reload'},
        'extra_sounds': [SND + 'ic_reload_balanced'],
        # the bomblet FIRST (no trigger), then the shell whose burst effect names it
        'projectiles': [BOMBLET],
        'bullet': SHELL,
        # Halo 4: recovery 0.8 s = 1.25/s
        'trigger': {'rounds_per_second': (1 / 0.8, 1 / 0.8), 'acceleration_time': 0.0,
                    'deceleration_time': 0.0,
                    # BOOT 1 (user: 'make it pop even more when firing'): the firing light-up (A out) fades
                    # over the illumination recovery -- the rocket's 0.3 s -> 0.5 s (Halo 4's shot cycle 0.8 s)
                    'illumination_recovery_time': 0.5,
                    # BOOT 8: the reload glow fades over the ejection port recovery = the reload (90 fr x 1.2 = 3.6 s)
                    'ejection_port_recovery_time': 3.6},
        # Halo 4: error 0 / 0 (the rocket's 0 / 0)
        'error_deg': {'minimum_error': 0.0, 'error_angle': (0.0, 0.0)},
        # Halo 4: 1 loaded, 4 at pickup, 6 most, 1 reloaded. Reload: Halo 4 none (reload_empty 90 fr = 3.0 s) in
        # the H1 rocket's shape (5.0 tag over its 125 fr = 4.17 s animation: x1.2)
        'magazine': {'rounds_loaded_maximum': 1, 'rounds_reloaded': 1,
                     'rounds_total_initial': 4, 'rounds_total_maximum': 6,
                     'reload_time': 90 / 30.0 * 5.0 / (125 / 30.0)},
        # Halo 4 aim assist (the mode block, = the weapon's): 5/60 10/25
        'aiming': {'autoaim_angle': 5.0, 'autoaim_range': 60.0,
                   'magnetism_angle': 10.0, 'magnetism_range': 25.0},
        'fields': {
            # Halo 4: one zoom level, 1.8x (the rocket's 2.0)
            'weap_attrs.aiming.zoom_levels': 1,
            'weap_attrs.aiming.zoom_ranges': (1.8, 1.8),
            'obje_attrs.collision_model.filepath': IC + 'incineration cannon',
            'weap_attrs.triggers.0.firing_effects.0.empty_effect.filepath': SND + 'ic_dryfire',
            # BOOT 2 (user: 'no change on a shot'): the firing glow fades by A out, and the ROCKET's weapon input A
            # is `integrated_light` (the flashlight); the sniper / LightRifle templates' is `illumination` (per shot)
            'weap_attrs.A_in': 'illumination',
            # BOOT 4: B in = primary ammunition (inverted by function 1 = B out: the reload glow)
            'weap_attrs.B_in': 'primary_ejection_port',  # BOOT 8: the reload glow's fade (was primary_ammunition, inverted)
            'weap_attrs.interface.zoom_in_sound.filepath': SND + 'ic_zoom_in',
            'weap_attrs.interface.zoom_out_sound.filepath': SND + 'ic_zoom_out',
            # STEP 4b list 2: first person offset Halo 4 0 vs its rocket's -0.05 onto the H1 rocket's -0.1 -> 0
            'weap_attrs.triggers.0.projectile.first_person_offset': (0.0, 0.0, 0.0),
        },
        # THE MUZZLE-FLASH RULE (check 10, before boot 1). Halo 4's fr_incin_firing, FIRST PERSON (camera 'only in
        # first person'): firing_muzzle_flash_1p (bounding 0.078 wu) + firing_energy_wave_1p 0.084 / 0.074 (+ one wide
        # 0.49 wave) at primary_trigger, muzzle rings 0.009 / 0.027 at secondary_trigger, and hardlight LIGHT-UPS on
        # the gun (back plate 0.045, barrel 0.032, barrel slide 0.079, top plate 0.057, top plate slide 0.089, vent
        # 0.010); NO smoke, NO casing; third person the same + energy waves 1.5-2.5 wu. The rocket's (h1_effect_
        # particles): one `flash h ar` 0.07-0.10 at primary trigger, a second at PRIMARY EJECTION (the back-blast;
        # the port's model has no such marker) and 24-28 FP smoke puffs there (+ 9-12 third-person) -- Halo 4 has
        # neither back-blast nor smoke -> the copy starts from the LIGHTRIFLE port's Forerunner flash (user-approved,
        # C4; the Binary Rifle's route: the on-axis centre flash 0.045-0.056, 3P flashes 0.053-0.141, no casing /
        # smoke) x1.5 (FP 0.068-0.084 = Halo 4's flash / wave), tinted orange. The plate light-ups: the firing GLOW
        # (glow cards faded by A out, the Binary Rifle's recipe). Not reproduced: the 0.49 wave, the tiny rings,
        # third person's 1.5-2.5 wu waves
        'sound_effects': {
            'firing_effect': (RL + 'effects\\fire rocket', IC + 'effects\\fire shell',
                              {'sound\\weapons\\light_rifle_port\\lr_fire': SND + 'ic_fire'},
                              {'copy_from': 'weapons\\light rifle\\effects\\fire bolt',
                               # BOOT 3 (user: 'the muzzle flash can be a bit more pompous'): x1.5 -> x2.2 and
                               # living x1.6 (an own particle copy: the Boltshot's / Sticky Detonator's recipe)
                               # BOOT 4 (user: 'muzzle flash is absent now'): the own longer-living particle copy
                               # is the only change since boot 3's visible flash -> dropped; x2.2 kept
                               # BOOT 7 (user: 'no muzzle flash still'): the model's primary trigger sits at x 17.0 cm, 3.8 cm
                               # INSIDE the barrel (the muzzle face, glow pieces 10 / 11 / 28, at x 20.6-20.8): the flash
                               # (+2.5 cm) was buried in the gun -> shifted 5 cm forward (x 24.5: ~4 cm past the face), x1.8
                               # BOOT 8 (user: 'barely visible now -- enhance it from this position'): x1.8 -> x3.0
                               'match': 'flash', 'scale': 3.0, 'shift': (0.05, 0.0, 0.0),
                               'tint': (1.0,) + ORANGE})},
        # BOOT 2-3: the magazine's RELOADING EFFECT (three contracting rings, also drawn first person) never showed in
        # classic first person -- REMOVED (user, boot 4); the reload glow (B out, the model's `ic_reload_glow`) instead
        # BOOT 8 (user: 'let the glow fade out over the reload -- otherwise it stays lit with no ammunition left at
        # all'): B in = the PRIMARY EJECTION PORT (1 on each shot, back to 0 over the trigger's ejection port recovery:
        # the Scattershot's per-shot glow), not inverted; the recovery = the reload (3.6 s) -> lit at the shot, fading
        # across the reload, dark when nothing is left to load (boot 7's inverted ammunition stayed lit)
        'obje_functions': [{'from': RL + 'rocket launcher', 'index': 0},
                           {'from': RL + 'rocket launcher', 'index': 0, 'set': {'scale_function_by': 'B_in'}}],
        'melee': (RL + 'melee', IC + 'melee'),
        'melee_response': RL + 'melee_response',
        'messages': ('Picked up an incineration cannon', 'Picked up %d rounds for incineration cannon'),
        'icon': 'incineration cannon',
        # the ROCKET's HUD; the crosshair from Halo 4's CUI (incinerationcannon.cui_screen, 3 art px a unit, widget
        # centres = left + width/2, top + height/2): `top_l` incin_middle 32 x 32 at (-25, -16) = the base, then
        # top_r (25, -16) flip x, bottom_l (-25, 17) flip y, bottom_r (25, 17) flip x+y; `top` / `bottom` incin_top
        # 64 x 16 at (0, -28) / (0, 28) flip y, opacity 0.65; `range_top` / `range_bottom` incin_range at (0, -12) /
        # (0, 12) flip y, 0.3; the outer brackets incin_outer 16 x 32 at opacity 0.1 and the white_pix middle
        # ticks 0.2 left out (barely visible). SIZE from the user's idle screenshot (1080p, 2026-10-16): the octagon
        # ~110 px across 72 units, ~102 px over 68 = 1.5 px a unit (the Boltshot's). SUPERSAMPLE (memory
        # h1-reticle-supersample; sheet px a unit = 123/97 x scale x F): F 2, the 42-unit half-span at scale 2.25 =
        # 240 of the 256 half-cell; overlay = 1.5 / (123/97 x 2.25 x 2 x 0.75) = 0.351
        'hud': {'donor': RL + 'rocket_launcher', 'out': IC + 'incineration cannon',
                'reticle': (H4 + ICUI + 'incin_middle', 0, 'incineration cannon'),
                'reticle_xform': {'offset': (-25.0, -16.0)},
                'reticle_layers': [(H4 + ICUI + 'incin_middle', 0, 1.0, {'flip_x': True, 'offset': (25.0, -16.0)}),
                                   (H4 + ICUI + 'incin_middle', 0, 1.0, {'flip_y': True, 'offset': (-25.0, 17.0)}),
                                   (H4 + ICUI + 'incin_middle', 0, 1.0, {'flip_x': True, 'flip_y': True,
                                                                          'offset': (25.0, 17.0)}),
                                   (H4 + ICUI + 'incin_top', 0, 1.0, {'gain': 0.65, 'offset': (0.0, -28.0)}),
                                   (H4 + ICUI + 'incin_top', 0, 1.0, {'gain': 0.65, 'flip_y': True,
                                                                       'offset': (0.0, 28.0)}),
                                   (H4 + ICUI + 'incin_range', 0, 1.0, {'gain': 0.3, 'offset': (0.0, -12.0)}),
                                   (H4 + ICUI + 'incin_range', 0, 1.0, {'gain': 0.3, 'flip_y': True,
                                                                         'offset': (0.0, 12.0)})],
                'reticle_split': 100,
                'reticle_min_width': 2,
                'reticle_supersample': 2,
                'reticle_scale': 2.25, 'reticle_overlay': 1.5 / (123 / 97.0 * 2.25 * 2 * 0.75),
                'flash_base': 2,
                # BOOT 1 (user: 'zoom hud is missing'): THE SCOPE (C4's POLYART recipe). Halo 4's
                # incinerationcannon_scope draws 3D vector frames; h4_polyart_scope.py rasterized the wires + holo
                # fills and was checked against the user's zoom screenshot (h4_zoom1.png) by overlay: the fitted
                # run (all pieces, overlap 0.175) squashed the round ring (x 0.85) under the ghost layers and the
                # EXTRUSION shards (they spread past the orange band) -- without ghosts / extrusions, at Halo 4's
                # own scale x 0.95, 20 px up, the band and notches sit on Halo 4's:
                #   python h4_polyart_scope.py "<SCOPE>" ui\hud\weapons\forerunner\forerunner_incineration_cannon\polyart
                #     --wires a_primary_wire,a_secondary_wire,b_primary_wire,b_secondary_wire01,b_secondary_wire02,
                #             b_secondary_wire03,a_inner_ring
                #     --fills a_primary_holo,a_secondary_holo,b_primary_holo,b_secondary_holo --fill-alpha 0.45
                #     --xform 1.0,1.0,0,-103 --pad 200
                #   python h1_scope_quadrants.py "<SCOPE>" --mirror left --fade 0  (the right quadrants = the left mirrored)
                # BOOT 8 (user: 'cut off at the bottom and not centered -- the same mistakes again'): MEASURED, not guessed
                # (band centre-lines through x 600-700, the user's Halo 4 zoom shot vs the raw raster): Halo 4 top 150 /
                # bottom 915 -> centre 532, half-height 383; the raw raster (x1.0) 255 / 1015 -> 635, 380; the half-widths
                # match too (506). So the SIZE was right at x1.0 all along (boots 3-4's 0.95 / 0.9 and boot 7's 0.88 were
                # wrong) -- only a -103 px shift. Every earlier shift cut the frame because h4_polyart_scope moved FINISHED
                # pixels (art below the 1080 px canvas never existed) -> `--pad 200`: rasterized 200 px beyond each edge,
                # the screen cut out after the move. Check on the composite before staging: top band rows 60-240 (Halo 4
                # 70-230), bottom 840-970 (830-1000), art to every screen edge
                # A CLEAR mask (no chud) with the H1 blur outside the lens and the dark top / bottom bands (the
                # LightRifle's / Binary Rifle's approved values); a donor without a zoom screen effect borrows the
                # sniper's (the Beam Rifle's route), its night vision / desaturation cleared
                'screen_effect_from': 'weapons\\sniper rifle\\sniper rifle',
                'screen_effect_clear': ('night_vision', 'desaturation'),
                'scope': {'out': IC + 'bitmaps\\scope_mask', 'size': 1024, 'alpha': 0,
                          'blur_outside': (244, 315), 'blur_edge': 14,
                          'dark_bands': (275, 110, 0.5)},
                # each quadrant a coloured zoom glyph at the reserved hud_reticles 88-91 (pair 6), the LightRifle's
                # calibration (crop pinned to the full 480 x 270, placed by `offset`)
                'zoom_glyphs': [{'image': SCOPE + q + '.png', 'reg': reg, 'name': 'incineration cannon scope ' + q,
                                 'index': i, 'scale': (1.0, 1.0), 'overlay': 3.604, 'offset': off,
                                 # BOOT 2 (user: 'not symmetrical, and a bit less transparent'): the right
                                 # quadrants = the left ones MIRRORED (tr = tl, br = bl flipped; the fitted
                                 # run kept as *_fit.png), alpha 0.6 -> 0.9, coverage gamma 1.6 -> 1.2
                                 'rgb': (255, 110, 30), 'alpha': 0.9, 'normalize': True, 'gamma': 1.2}
                                # BOOT 3 moved the glyphs 81 units up -- BOOT 4 (user: 'cut off again, repeating the past
                                # mistakes'): the hard edges were the SPRITES' own borders (bottom at y 920, sides at x
                                # 77 / 1835): each quadrant must cover exactly its screen quarter (the LightRifle's
                                # calibration) -- position goes INTO THE RASTER, the offsets stay calibrated. Measured on
                                # the boot-4 shot by the orange band profiles: the same 1.2 : 1 ring as Halo 4's at 0.89x
                                # its size, centred at y 507 vs Halo 4's 531 -> raster x1.0, shifted -95 px
                                for q, reg, i, off in (('tl', (480, 270), 88, (-407, -29)),
                                                       ('tr', (0, 270), 89, (458, -29)),
                                                       ('bl', (480, 0), 90, (-407, 458)),
                                                       ('br', (0, 0), 91, (458, 458)))],
                # (the rocket HUD's two zoom-typed crosshairs, the sniper scope reticle, go with the scope step's
                # zoom-type drop: Halo 4 keeps its normal crosshair inside the polyart frame)
                # BOOT 1 (user: 'it uses the generic ammo tick meter -- import its own'): Halo 4's CUI
                # `bitmap_ammo_ticks` = ammo_incinerator (177 x 54 px = 59 x 18 units: ONE shell a round), at its
                # native density
                'ammo_meter': {'sizes': (1,), 'base': IC + 'bitmaps\\incineration_cannon_ammo',
                               'art': {'h3': (H4 + ICUI + 'ammo_incinerator', 0), 'native': True}}},
        'palette_levels': LEVELS,
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py incineration_cannon). DEFAULT = Halo 4's own numbers
    # in the tags; BALANCED = the ROCKET LAUNCHER ratio by the direct hit, 315/440 (step 4a, user). Assembly Halo1
    # units: angles in degrees, velocity in wu per TICK
    'catalog': {
        'entry': {
            'weapon': 'Incineration Cannon', 'source': 'Halo 4', 'donor': 'Rocket Launcher', 'default_on': False,
            'desc': "Halo 4's Incineration Cannon: its model, first-person animations, sounds and numbers. A "
                    "one-shot Forerunner launcher whose slow shell bursts and scatters five bomblets that "
                    "bounce off the ground and explode on anything they touch.",
            'balance_desc': "Measured against the Rocket Launcher, which both games have: a 315 hit "
                            "(143 impact + 172 burst) over 1.6 m, 86 per bomblet, one shot every 2 s, a "
                            "faster shell, up to 8 rounds and Halo 1-style aim assist.",
            # step 9: the balanced reload = the H1 rocket's 125 fr x 90/116 = 97 over the built 90; swap (ready +
            # put-away, ONE multiplier): the rocket's ready 22 x 31/26 = 26.2 over the built 31
            'anims': {'reload': 97.0 / 90.0, 'swap': 22 * 31 / 26.0 / 31.0},
            'anim_sounds': {'reload': [
                {'mult': 97.0 / 90.0, 'from': SND + 'ic_reload', 'to': SND + 'ic_reload_balanced'}]},
            'balance': [
                # the shell: impact 200 x 315/440, the burst 240 (lower 40) x 315/440 over 0.75 x 0.5/0.9, 2.0 x
                # 2.0/2.5; AOE core 0.75 x 0.6/0.75 (4b: the rockets' cores)
                row('jpt!', IC + 'impact', 'Damage Lower Bound', 143.18, 200.0, 'Shell Damage'),
                row('jpt!', IC + 'impact', 'Damage Upper Bound', 143.18, 200.0, 'Shell Damage'),
                row('jpt!', IC + 'impact', 'Damage Upper Bound Max', 143.18, 200.0, 'Shell Damage'),
                row('jpt!', IC + 'explosion', 'Damage Lower Bound', 28.64, 40.0, 'Shell Damage'),
                row('jpt!', IC + 'explosion', 'Damage Upper Bound', 171.82, 240.0, 'Shell Damage'),
                row('jpt!', IC + 'explosion', 'Damage Upper Bound Max', 171.82, 240.0, 'Shell Damage'),
                row('jpt!', IC + 'explosion', 'Radius', 0.417, 0.75, 'Shell Damage'),
                row('jpt!', IC + 'explosion', 'Radius Max', 1.6, 2.0, 'Shell Damage'),
                row('jpt!', IC + 'explosion', 'AOE Core Radius', 0.6, 0.75, 'Shell Damage'),
                # a bomblet: 120 (lower 30) x 315/440 over 0.61 x 0.5/0.9, 1.25 x 2.0/2.5; core 0.6 x 0.6/0.75 (4b)
                row('jpt!', IC + 'bomblet explosion', 'Damage Lower Bound', 21.48, 30.0, 'Bomblet Damage'),
                row('jpt!', IC + 'bomblet explosion', 'Damage Upper Bound', 85.91, 120.0, 'Bomblet Damage'),
                row('jpt!', IC + 'bomblet explosion', 'Damage Upper Bound Max', 85.91, 120.0, 'Bomblet Damage'),
                row('jpt!', IC + 'bomblet explosion', 'Radius', 0.339, 0.61, 'Bomblet Damage'),
                row('jpt!', IC + 'bomblet explosion', 'Radius Max', 1.0, 1.25, 'Bomblet Damage'),
                row('jpt!', IC + 'bomblet explosion', 'AOE Core Radius', 0.48, 0.6, 'Bomblet Damage'),
                # 4b list 2: knockback by the rockets' 6/3 (default Halo 4's own 3 / 2.5)
                row('jpt!', IC + 'explosion', 'Instantaneous Acceleration i', 6.0, 3.0, 'Shell Damage'),
                row('jpt!', IC + 'bomblet explosion', 'Instantaneous Acceleration i', 5.0, 2.5, 'Bomblet Damage'),
                # 4b list 2, the bomblet vs the frags: timer 0.6-1.0 x 0.5/(0.6-0.65); gravity 5 x 1/0.9
                row('proj', IC + 'bomblet', 'Timer', 0.5, 0.6, 'Projectile'),
                row('proj', IC + 'bomblet', 'Timer Max', 0.769, 1.0, 'Projectile'),
                row('proj', IC + 'bomblet', 'Air Gravity Scale', 5.556, 5.0, 'Projectile'),
                # the RL ratio: 0.8 s x 2.0/0.8 = 2.0 s (0.5/s); 6 x 8/6 = 8 most (4 x 4/4 = 4 kept)
                row('weap', IC + 'incineration cannon', 'Rounds Per Second', 0.5, 1.25, 'More Shooting', block='Triggers'),
                row('weap', IC + 'incineration cannon', 'Rounds Per Second Max', 0.5, 1.25, 'More Shooting', block='Triggers'),
                row('weap', IC + 'incineration cannon', 'Rounds Total Maximum', 8.0, 6.0, 'Magazine', block='Magazines'),
                # flight: 12 x 21/10 = 25.2, 10 x 21/20 = 10.5 wu/s; range 128 x 175/175
                row('proj', IC + 'shell', 'Initial Velocity', 25.2 / 30.0, 21.0 / 30.0, 'Projectile'),
                row('proj', IC + 'shell', 'Final Velocity', 10.5 / 30.0, 21.0 / 30.0, 'Projectile'),
                row('proj', IC + 'shell', 'Maximum Range', 128.0, 175.0, 'Projectile'),
                # aim: the angle KEPT Halo 4's 5 (the rocket's 0: C8's rule), 35 x 60/60; 12 x 10/10, 35 x 25/25
                row('weap', IC + 'incineration cannon', 'Autoaim Angle', 5.0, 5.0, 'Autoaim'),
                row('weap', IC + 'incineration cannon', 'Autoaim Range', 35.0, 60.0, 'Autoaim'),
                row('weap', IC + 'incineration cannon', 'Magnetism Angle', 12.0, 10.0, 'Magnetism'),
                row('weap', IC + 'incineration cannon', 'Magnetism Range', 35.0, 25.0, 'Magnetism'),
            ]},
    },

    # step 4b (port_field_audit.py --port incineration_cannon): the source pairs (Halo 4's Incineration Cannon vs
    # its yardstick, the Halo 4 rocket launcher -- weapon, shell, burst, impact, melee; the bomblet vs the Halo 4
    # frag grenade, its burst vs the rocket's explosion) against the target pairs (the H1 port vs its templates:
    # the rocket launcher, its rocket, its explosion; the bomblet vs the H1 frag grenade)
    'field_audit': {
        'source_kit': 'H4EK',
        'source': {'weapon': (SW + r'\storm_forerunner_incineration_launcher.weapon',
                              r'objects\weapons\support_high\storm_rocket_launcher\storm_rocket_launcher.weapon'),
                   'projectile': (SW + r'\projectiles\storm_forerunner_incineration_launcher.projectile',
                                  r'objects\weapons\support_high\storm_rocket_launcher\projectiles\storm_rocket_launcher_rocket.projectile'),
                   'damage_effect': (SW + r'\projectiles\damage_effects\storm_forerunner_incineration_launcher_explosion.damage_effect',
                                     r'objects\weapons\support_high\storm_rocket_launcher\projectiles\damage_effects\storm_rocket_launcher_rocket_explosion.damage_effect'),
                   'impact': (SW + r'\projectiles\damage_effects\storm_forerunner_incineration_launcher_impact.damage_effect',
                              r'objects\weapons\support_high\storm_rocket_launcher\projectiles\damage_effects\storm_rocket_launcher_rocket_impact.damage_effect'),
                   'bomblet': (SW + r'\projectiles\submunition.projectile',
                               r'objects\weapons\grenade\storm_frag_grenade\storm_frag_grenade.projectile'),
                   'bomblet_damage': (SW + r'\projectiles\damage_effects\storm_forerunner_incineration_launcher_submunition.damage_effect',
                                      r'objects\weapons\support_high\storm_rocket_launcher\projectiles\damage_effects\storm_rocket_launcher_rocket_explosion.damage_effect')},
        'target': {'weapon': (IC + 'incineration cannon.weapon', RL + 'rocket launcher.weapon'),
                   'projectile': (IC + 'shell.projectile', FR_PROJ + '.projectile'),
                   'damage_effect': (IC + 'explosion.damage_effect', RL + 'explosion.damage_effect'),
                   'impact': (IC + 'impact.damage_effect', RL + 'explosion.damage_effect'),
                   'bomblet': (IC + 'bomblet.projectile', FR_PROJ + '.projectile'),
                   'bomblet_damage': (IC + 'bomblet explosion.damage_effect', RL + 'explosion.damage_effect')}},

    # the dry test: b30 (this session's level, parallel pair 6), Halo 4's own loadout (1 loaded, 4 in all)
    'test': {'level': 'b30', 'rounds': (1, 4), 'grunt': None, 'elite': None},
})
