r"""Railgun (Halo 4, wave C7): IN PROGRESS -- step 4a decided (user, 2026-10-16); the port sections
(model / retarget / pickable / sounds / catalog / test) follow.

HALO 4 (H4EK 2026-10-16, h3_weapon_values --kit h4 + h4_projectile_summary + h4_flag_names): the SOURCE is
the campaign tag `storm_rail_gun_pve` (user, over the MP tag). MP vs _pve: the charged (hold) time 0.5 vs
1.5 s, error 0.2 vs 0.15 -> 0.8, the projectile (MP impact 60 `bullet` + blast 120 explosion_large over 0.675
-> 1.0; _pve 120 `needle` + 180 explosion_small over 0.55 -> 1.0), _pve's ammo-box magazine entry and dry-fire
loop attachment, MP's pickup sound, abandonment times.
_pve: trigger `charge-with-magazine` -- charging 0.75 s, then held charged up to 1.5 s, 'discharge' after
(fires by itself); an early release fires barrel 0, which has NO projectile (nothing comes out); the charged
release fires barrel 1 (the slug). Recovery 0.6 s, 1 loaded / 4 / 6, every reload = reload_empty 82 fr
(reload_full 59 never plays on a 1-round magazine); heat 0.36 a round, loss 1/s (inert at one round a
reload); error 0.15 -> 0.8 (bloom decel 0.5); no zoom; aim assist mode 0 (unzoomed) 2.5/25 7.5/25 (the
struct 5/16 10/16); melee strike_melee. Flags (by name): weapon 'cannot fire at maximum age' (no age: inert),
'hide FP weapon when in iron sights', 'allows binoculars'; barrels 'only reload if all barrels idle' (barrel
0 also "don't clear fire bit after recovering").
THE SLUG (storm_rail_gun_bolt_pve): 100 wu/s flat, range 0 (unset), no gravity, 'oriented along velocity',
'disable instantaneous first tick'. Impact 120 (`needle`, accel 0.05) + detonation 0..180 explosion_small
over 0.55 -> 1.0, core 0.54 (accel 2.5, 'detonates explosives'); no aoe spike bump. Responses: the table
Halo 4 reads (`material response`, C5) = default ATTACH, energy_shield_invulnerable bounce; timer 0.2 s
'when at rest' + 'detonation max time if attached' = it STICKS and bursts 0.2 s later. No overpenetration."""
from ._common import B, reserved, row  # noqa: F401
from .storm_rifle import DROP

H4 = 'h4:'                                          # an H4EK path (h4_tags)
RG = 'weapons\\railgun\\'
SND = 'sound\\weapons\\railgun_port\\'
RL = 'weapons\\rocket launcher\\'
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']
SW = r'objects\weapons\rifle\storm_rail_gun'
SFP = r'objects\characters\storm_fp\weapons\rifle\fp_rail_gun\storm_fp_rail_gun'
SBM = SW + r'\bitmaps\storm_rail_gun_default' + B
SRC = r'F:\SteamLibrary\steamapps\common\HCEEK\data\weapons\railgun\source' + B
# Halo 4's display yellow (the bars material's albedo tint)
YELLOW = (1.0, 0.855, 0.0)
# the render model's 5 nodes, all animated by the FP graph (b_cover_01 / _02 = the barrel covers, b_bullet
# / b_cartridge = the loaded slug and its cartridge)
GUN_NODES = ('b_gun', 'b_cover_01', 'b_bullet', 'b_cartridge', 'b_cover_02')
RGUI = r'ui\hud\weapons\human\railgun\bitmap' + B   # Halo 4's crosshair art (CUI railgun)
# an own collision hull (the template's hides the world model, C1): the built JMS's extent (x -0.099..0.265,
# y +-0.012, z -0.012..0.092 wu) as one box
COLLISION = {'material': 'metal', 'boxes': [((-0.099, -0.012, -0.012), (0.265, 0.012, 0.092))]}
PP = 'weapons\\plasma pistol\\'
PR = 'weapons\\plasma rifle\\'
# Halo 4's railgun blue: grad_bluelight_1 near its top (the tracer palette) and the user's fully-charged
# screenshot (the arcs along the rail pale cyan-blue)
BLUE = (0.45, 0.75, 1.0)
# the trigger's first-person offset = the FP `primary trigger` in camera space, idle frame 0 (h1_fp_muzzle.py
# "weapons\railgun\fp\fp", 2026-10-16): the trail starts at the muzzle (C6)
FP_MUZZLE = (0.3559, -0.0365, -0.0196)
# Halo 1 material indices (the Sticky Detonator's / Plasma Launcher's): Halo 4's `material response` table
# = default ATTACH, energy_shield_invulnerable BOUNCE -> the force fields reflect, water passes
WATER, LEAVES = 28, 29
FORCE_FIELDS = [10, 18, 26, 32]      # force field, engineer force field, monitor, hunter shield
# LEAVES (the template diff, 2026-10-16): the rocket overpenetrates foliage with a potential `detonate` at
# skip 0.9 (its only set potential; the rest are the enum's 0) -- kept the rocket's (Halo 4's old table
# detonates on plants; a slug stuck in a leaf would burst in the canopy)
ATTACH = [i for i in range(33) if i not in [WATER, LEAVES] + FORCE_FIELDS]

# THE SLUG on a copy of Halo 1's ROCKET projectile (no gravity, its explosion chain; the yardstick's own).
# Halo 4: impact 120 + a blast 0..180 over 0.55 -> 1.0 (core 0.54), it STICKS and bursts 0.2 s later. Halo 1
# deals a projectile's ATTACHED damage to what it sticks to, at the stick (B6) -- that IS Halo 4's hit: the
# 120 as the attached damage (a copy of the rocket explosion's table, no radius), no impact damage (no
# double hit), the blast = the rocket's explosion effect x0.4 (1.0 / 2.5 wu) around an own copy of its
# damage, 0.2 s after it comes to rest (stuck = at rest: the Sticky Detonator's fuse). 100 wu/s flat, range 0
# (Halo 4's unset: unlimited, the fuel rod's 0), no gravity. The look: Halo 4's bolt model (an extra model),
# a blue light + flare, and THE TRACER (rg_firing_tracer_3p: an electrical_beam ribbon + plasma_energy
# wisps through grad_bluelight_1) by the beam recipe on the sniper's contrail (attachments_from the sniper
# bullet), from the FP muzzle
# THE HIT FLASH (Armed boot, user 2026-10-16: 'the hit flash needs to be intensified'): the rocket's
# damage tags carry NO screen flash (duration 0). Halo 4's own responses -- the hit impact_bullet_slow
# (0.2 s, early, shielded orange 1 / 0.3 / 0, unshielded red), the blast explosion_small_lowpass (0.25 s
# shielded, 0.75 unshielded, the same colours) -- Halo 1 has one flash a damage effect: the shielded
# orange at Halo 4's timing, at 0.5 / a 30 % wash (the LightRifle's approved 0.3 / 15 %, stronger for a
# power weapon). ARMED BOOT 3 (user: 'increase the hit flash duration', no boot): Halo 4's x2 -- the hit
# 0.4 s, the blast 0.5 s (Halo 4's unshielded blast flash 0.75 s)
HIT_FLASH = {'screen_flash.duration': 0.4, 'screen_flash.fade_function': 'early',
             'screen_flash.maximum_intensity': 0.5,
             'screen_flash.tint_lower_bound.a': 0.3, 'screen_flash.tint_lower_bound.r': 1.0,
             'screen_flash.tint_lower_bound.g': 0.3, 'screen_flash.tint_lower_bound.b': 0.0}
SLUG = {
    'projectile': (RL + 'rocket', RG + 'slug'),
    'damage': None, 'no_impact_damage': True,
    'attached': {'from': RL + 'explosion', 'out': RG + 'slug impact', 'dmg': 120.0,
                 # 4b (no field audit reads the attached tag): instantaneous acceleration by the ratio on the
                 # rocket explosion's 6 -- Halo 4 impact 0.05 / Halo 4 rocket impact 1.5 = 0.2
                 'fields': dict(HIT_FLASH, **{'radius': (0.0, 0.0),
                                             'damage.instantaneous_acceleration': 6.0 * 0.05 / 1.5})},
    'explosion': {'effect': (RL + 'effects' + B + 'rocket explosion', RG + 'effects' + B + 'slug explosion'),
                  'damage': (RL + 'explosion', RG + 'explosion'),
                  'scale': 0.4, 'out_dir': RG + 'effects' + B,
                  'lower': 0.0, 'upper': (180.0, 180.0), 'radius': (0.55, 1.0),
                  # STEP 4b list 2 (Halo 4 railgun / Halo 4 rocket onto the H1 rocket), no card covers them:
                  # acceleration 6 x 2.5/3 = 5, camo damage 1 x 1/0.9, the breaking effect's forward velocity 80 x
                  # 30/35, radius 1 x 2/0.5, exponent 2 x 0/0.5 = 0, outward velocity 16 x 15/6 (outward exponent:
                  # a zero on one side -> Halo 4's 0, list 3); aoe core = Halo 4's own 0.54 (the ratio's 0.432 is
                  # the balanced side of the radius rows); category kept the rocket's high_explosive (its table)
                  'fields': {**HIT_FLASH, 'screen_flash.duration': 0.5,
                             'damage.aoe_core_radius': 0.54,
                             'damage.instantaneous_acceleration': 6.0 * 2.5 / 3.0,
                             'damage.active_camouflage_damage': 1.0 / 0.9,
                             'breaking_effect.forward_velocity': 80.0 * 30 / 35.0,
                             'breaking_effect.forward_radius': 1.0 * 2.0 / 0.5,
                             'breaking_effect.forward_exponent': 0.0,
                             'breaking_effect.outward_velocity': 16.0 * 15 / 6.0,
                             'breaking_effect.outward_exponent': 0.0},
                  'swaps': {B.join(['sound', 'sfx', 'weapons', 'frag grenade', 'expl']): SND + 'rg_explode'}},
    'velocity': (100.0, 100.0), 'range': 0.0,
    'model': RG + 'slug' + B + 'slug',
    'proj_fields': {'proj_attrs.physics.air_gravity_scale': 0.0,
                    'proj_attrs.physics.water_gravity_scale': 0.0,
                    'proj_attrs.detonation.arming_time': 0.0,
                    'proj_attrs.detonation.timer': (0.2, 0.2),
                    'proj_attrs.detonation_timer_starts': 'when_at_rest',
                    'proj_attrs.detonation.minimum_velocity': 0.0,
                    'proj_attrs.physics.guided_angular_velocity': 0.0,
                    'proj_attrs.physics.flyby_sound.filepath': SND + 'rg_flyby',
                    'proj_attrs.collision_radius': 0.0,
                    # STEP 4b list 2: bounding radius 0.1 x 0/0.1 = 0; air damage range 0..100 x 60/150 = 0..40
                    'obje_attrs.bounding_radius': 0.0,
                    'proj_attrs.physics.air_damage_range': (0.0, 40.0),
                    'proj_attrs.flags.oriented_along_velocity': True,
                    'proj_attrs.flags.detonation_max_time_if_attached': False},
    'default_responses': {'attach': ATTACH, 'reflect': FORCE_FIELDS, 'overpenetrate': [WATER, LEAVES]},
    'clear_detonation_effects': True,
    'attachments_from': 'weapons\\sniper rifle\\sniper bullet',
    'contrail': {'from': 'weapons\\sniper rifle\\sniper', 'out': RG + 'tracer', 'no_physics': True,
                 'blend': 'add', 'bitmap': RG + 'bitmaps\\rg_tracer_core', 'sequence': (0, 0),
                 'repeats': (0.25, 1.0),
                 'states': [{'duration': (0.25, 0.3), 'transition': (0.2, 0.3),
                             'width': 0.1, 'argb': (1.0, 1.0, 1.0, 1.0)},
                            {'width': 0.08, 'argb': (0.0, 1.0, 1.0, 1.0)}],
                 'extra': [{'out': RG + 'tracer glow', 'blend': 'add',
                            'bitmap': RG + 'bitmaps\\rg_tracer_glow', 'sequence': (0, 0),
                            'repeats': (0.125, 1.0),
                            'states': [{'duration': (0.4, 0.5), 'transition': (0.3, 0.4),
                                        'width': 0.22, 'argb': (1.0, 1.0, 1.0, 1.0)},
                                       {'width': 0.18, 'argb': (0.0, 1.0, 1.0, 1.0)}]}]},
    'glow': {'light': ('weapons' + B + 'fuel rod gun' + B + 'fuel rod exhaust', RG + 'slug glow'),
             'flare': RG + 'slug glow', 'rgb': BLUE, 'flare_radius': 0.12, 'marker': ''},
    'triggers': [0],
}

# THE MUZZLE-FLASH RULE (check 10, before boot 1; h4_effect_particles / h1_effect_particles, 2026-10-16).
# Halo 4's firing.effect, FIRST PERSON at primary_trigger: plasma ring 0.106, flash ring 0.53, soft flare
# 0.085, muzzle smoke 0.214, blue sparks 0.057 / 0.41, the rail flare 0.042 at rail_charge (+ a light, a warp
# screen effect); third person 0.09-0.48 + long flashes 0.14-0.21; NO casing, NO back-blast. The rocket's: a
# `flash h ar` 0.07-0.1 at the muzzle AND a back-blast flash + 24-28 smoke at `primary ejection` (the railgun
# vents nothing backwards). -> the PLASMA PISTOL's bolt flash (Halo 1's own energy flash, green -- retinted: on-axis
# flashes 0.04-0.25 + white smoke; its two sideways flashes at +-2.09 rad dropped), x2 (0.08-0.5 = Halo 4's
# 0.085-0.53), tinted the railgun blue -- the smoke too (the template diff: the plasma pistol's smoke is
# GREEN, r 0.05 / b 0; Halo 4's shot carries blue plasma haze, plasma_blue_tiny up to 0.41 wu)
FIRE_FLASH = {'copy_from': PP + 'effects\\fire bolt', 'match': 'flash', 'drop_off_axis': 0.012,
              'scale': 2.0, 'tint': (1.0,) + BLUE}

PORT = reserved(
    order=32, wave='C7', name='Railgun', source='Halo 4',
    messages=(97, 98), icon=52, reticle=41, label='rg', teach_from='rl',
    sound_dir='sound\\weapons\\railgun_port', weapon_dir='weapons\\railgun',
    yardstick={
        # step 4a (user, 2026-10-16; h1_role_compare.py railgun)
        'pick': 'Rocket Launcher',
        'reason': ("user, step 4a 2026-10-16: source = the _pve tag; the ROCKET LAUNCHER's role (a 1-round "
                   "power weapon with a blast; 2 hits on an Elite major / commander / Hunter on Legendary, "
                   "as Halo 4's own). DEFAULT = Halo 4's own numbers, BALANCED = the ROCKET ratio rows (H1 "
                   "rocket x H4 railgun / H4 rocket, the direct hit 300 / 440 with Halo 4's split). The "
                   "slug's hit AND blast on the ROCKET's damage table (both versions: the rows change damage "
                   "only). Detonation (user): STICK + a 0.2 s fuse at rest (Halo 4's attach + 'detonation max "
                   "time if attached'; the Sticky Detonator's recipe). Rejected: the Fuel Rod ratio (140.6, "
                   "Hunters immune on its table), the Sniper ratio (378.8 at 35.7 wu/s, Flood 6-9 hits)"),
        # DEFAULT = Halo 4's own numbers; these are the BALANCED rows. Halo 4 railgun / rocket: direct 120 +
        # 180 = 300 / 200 + 240 = 440 (no aoe spike in either); blast radius 0.55 -> 1.0 / 0.9 -> 2.5;
        # recovery 0.6 / 0.8 s; 1 / 2 loaded, 4 / 4, 6 / 6; reload 82 / 116 fr; 100 flat / 10 -> 20 wu/s;
        # range 0 (unset) / 175; aim (mode 0) 2.5/25 7.5/25 / 5/60 10/25; error 0.15 -> 0.8 / 0; no zoom /
        # 1.8x. H1 rocket: 315 (all blast) over 0.5 -> 2.0, 2.0 s, 2 / 4 / 8, 125 fr, 12 -> 10 wu/s, 128,
        # aim 0/35 12/35, error 0, zoom 2x, melee 55
        'balanced': {
            'damage': 214.8,             # 315 x 300/440
            'impact': 85.9,              # Halo 4's split: x 120/300
            'blast': 128.9,              #                 x 180/300
            'radius': (0.306, 0.8),      # 0.5 x 0.55/0.9, 2.0 x 1.0/2.5
            'charge_s': 0.75,            # KEPT: no rocket charges (the Plasma Launcher's 'charge kept')
            'charge_hold_s': 0.0,        # boot 2 (user, option 1): no hold in either version
            'fire_recovery_s': 1.5,      # 2.0 x 0.6/0.8 (moot on a 1-round magazine)
            'magazine': 1,               # 2 x 1/2
            'rounds_total_initial': 4,   # 4 x 4/4
            'rounds_total_maximum': 8,   # 8 x 6/6
            'reload_fr': 88.4,           # 125 x 82/116
            'velocity': 120.0,           # 12 x 100/10 (initial; flat -- the rocket's 12 -> 10 vs 10 -> 20
                                         # would give a decelerating slug, 120 -> 50)
            'range': None,               # Halo 4's 0 = unset: no row (unlimited both ways)
            'aim': (2.5, 14.6, 9.0, 35.0),  # 0 x 2.5/5 degenerate -> the source angle (C8 rule), 35 x
                                            # 25/60; 12 x 7.5/10, 35 x 25/25
            'error_deg': None,           # both yardsticks 0: no ratio -> Halo 4's own 0.15 -> 0.8
            'zoom': None,                # Halo 4: no zoom (the rocket's 1.8x / 2x has no railgun side)
            'melee': None},              # Halo 4 shares strike_melee: x1 = the H1 rocket's 55
        'measured': 'h1_role_compare.py railgun',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\storm_rail_gun\\storm_rail_gun_pve',
            'provisional': 'Rocket Launcher',
            'alternatives': ['Flak Cannon (H1 fuel rod: charge-to-fire)', 'Sniper Rifle'],
            'direct': None,
            'peers': ['Rocket Launcher', 'Sniper Rifle', 'Flak Cannon', 'Spartan Laser (port)',
                      'Binary Rifle (port)'],
            'why': '1-round magazine, 0.75 s charge, slug with impact + explosion damage',
            'lacks': "Halo 4's sprint; the heat (inert); the 'allows binoculars' flag"}},
    # step 11 (2026-10-16): phase 0 searched only the MP tag. The _pve tag HAS a Halo 4 ai\generic entry in nine
    # campaign maps (ai_firing_entry.py; m020 #37): max firing distance 20, error 0.039, first burst 1.0-1.25 s,
    # surprise 1.0, desired range 10-15, tracking 0.95 / leading 0.7, burst 2.6 s every 4-6 s, drop 0.6-0.9
    # (m020; 0.3-0.45 m30/m40, 0.66-0.99 m70/m90). No rate of fire: the base's would ride along -- the
    # SPARTAN LASER's lesson (A8): a charging AI needs Rate Of Fire 0 (it HOLDS for the burst) and a burst
    # longer than the charge (2.6 s > 0.75 s: one slug a burst). Base donor: Halo 1's ROCKET LAUNCHER carriers
    # (h1_weapon_carriers: the Flood combat Elite and human, both WDM 0.4, no actor flags; the Elite's rate
    # 0.25, the human's 1.0 -- set to 0 here). ARMED WDM RULE (user 2026-10-16: 'Rule: 0.575 / 0.867'): 0.4 x
    # rocket 158 / the railgun's HELD cycle (one slug a reload: the charge restarts during it) -- default 300
    # / 2.733 s = 109.8 (0.575), balanced 214.8 / 2.947 s = 72.9 (0.867). Against the player: Normal 1 hit
    # (172 / 186), Legendary 1 (310 / 335); the stock rocket Flood 0.4 (Normal 2). Balanced drop: Halo 1's
    # rocket carriers drop 0 / 0 (a zero on one side): no row
    firing_profile={'mode': 'source', 'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map',
                    'from_weapon': 'objects\\weapons\\rifle\\storm_rail_gun\\storm_rail_gun_pve',
                    'donor_weapon': 'weapons\\rocket launcher\\rocket launcher',
                    'set': ['0x78=0.0:Rate Of Fire'],
                    'wdm_rule': {'base': 0.4, 'yardstick_dps': 158.0, 'port_dps': 300.0 / (82 / 30.0),
                                 'balanced_port_dps': 214.8 / (88.4 / 30.0)},
                    'species_skill': True},
)

PORT.update({
    'status': 'in progress',

    # geometry + look (h1_h3_weapon_model.py; Halo 4 through h4_tags). ONE render model for world AND first
    # person: 5 nodes (b_gun root, b_cover_01 / _02, b_bullet, b_cartridge), 1 region / mesh. Markers:
    # primary_trigger, secondary_trigger, muzzle_flash, rail_charge (the charge effect), fx_display_light,
    # primary_ejection, flashlight, the hands. Materials (H4 .material, 2026-10-16): default = colour map
    # storm_railgun_diff (shipped, a real UNSC colour map) x diffuse 0.903, control_map_spglrf, specular 9;
    # screen = the yellow display texture (PHASE / FAULT, CAPACITOR, two CELL columns); bars = white strips
    # x albedo (1, 0.855, 0), self-illum 4; ok / na = 32 px yellow icons; the UNSC eagle crest decal
    'model': {
        'dir': r'weapons\railgun',
        'world': H4 + SW + r'\storm_rail_gun.render_model',
        'fp': H4 + SW + r'\storm_rail_gun.render_model',
        'world_name': 'railgun',
        'decimate': {'keep': 80.0, 'protect': 1.0, 'lock': ('rg_crest',), 'views': [((-0.1082, 0.047, 0.0842), (0.9988, -0.0295, -0.0384), (0.0384, -0.0011, 0.9993), 1.0), ((-0.1088, 0.0464, 0.0835), (0.9991, -0.0291, -0.0317), (0.0314, -0.0102, 0.9995), 1.0), ((-0.1082, 0.047, 0.0842), (0.9988, -0.0295, -0.0384), (0.0384, -0.0011, 0.9993), 1.0), ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), 1.0), ((0.0002, 0.0012, 0.0003), (1.0, -0.0076, -0.0012), (0.001, -0.0263, 0.9997), 1.0), ((-0.0001, -0.0, 0.0), (1.0, -0.005, 0.0026), (-0.0025, 0.007, 1.0), 1.0), ((-0.1082, 0.047, 0.0842), (0.9988, -0.0295, -0.0384), (0.0384, -0.0011, 0.9993), 1.0), ((-0.0702, 0.0463, 0.0765), (0.9996, -0.0141, -0.0261), (0.0262, 0.007, 0.9996), 1.0), ((-0.1082, 0.047, 0.0842), (0.9988, -0.0295, -0.0384), (0.0384, -0.0011, 0.9993), 1.0), ((-0.1555, 0.0203, 0.0482), (0.3288, -0.247, 0.9115), (-0.9439, -0.117, 0.3088), 0.5), ((-0.1084, 0.0548, 0.0703), (0.9958, -0.0807, -0.0426), (0.0571, 0.1867, 0.9807), 0.5), ((-0.1555, 0.0203, 0.0482), (0.3288, -0.247, 0.9115), (-0.9439, -0.117, 0.3088), 0.5), ((-0.1082, 0.047, 0.0842), (0.9988, -0.0295, -0.0384), (0.0384, -0.0011, 0.9993), 0.5), ((-0.0866, 0.1095, 0.0989), (0.7212, -0.6881, -0.0795), (-0.4083, -0.5151, 0.7536), 0.5), ((-0.1082, 0.047, 0.0842), (0.9988, -0.0295, -0.0384), (0.0384, -0.0011, 0.9993), 0.5), ((-0.0775, 0.0372, 0.073), (1.0, 0.0017, 0.0001), (-0.0001, 0.0002, 1.0), 0.5), ((-0.1191, 0.1095, 0.0804), (0.5392, -0.5663, -0.6233), (0.8385, 0.43, 0.3347), 0.5), ((-0.0775, 0.0372, 0.073), (1.0, 0.0017, 0.0001), (-0.0001, 0.0002, 1.0), 0.5), ((-0.0775, 0.0372, 0.073), (1.0, 0.0016, 0.0002), (-0.0002, 0.0001, 1.0), 0.5), ((-0.0997, -0.0592, 0.178), (-0.0258, 0.0717, -0.9971), (0.0017, -0.9974, -0.0718), 0.5), ((-0.0775, 0.0372, 0.073), (1.0, 0.0016, 0.0002), (-0.0002, 0.0001, 1.0), 0.5)]},
        'markers': {'primary_trigger': 'primary trigger', 'left_hand': 'left hand',
                    'rail_charge': 'rail charge'},
        'ground_point': 'auto',
        # an own hull (the template's hides the world model, C1): set from the built JMS's extent
        'collision': COLLISION,
        # the SLUG's model: Halo 4's bolt render model (1 material = the gun's body)
        'extra_models': {'slug': {'from': H4 + SW + r'\projectiles\storm_rail_gun_bolt.render_model',
                                  'dir': RG + 'slug',
                                  'material_names': {'storm_rail_gun_default': 'rg_body'}}},
        # THE CHARGE (the user's fully-charged screenshot: blue electric arcs along the left rail, the gun
        # tinted blue; Halo 4's charging.effect at rail_charge: rail_electricity, a magnet ring, a flare, a
        # light): Halo 1 draws weapon attachments at the hidden third-person gun in first person (A8), so a
        # glow BUILT INTO the model -- a star of radial cards at `rail charge` whose additive shader fades with
        # B out = primary charged (the Spartan Laser's charge glow)
        'glow_points': [{'marker': 'rail charge', 'shader': 'rg_charge_glow', 'size': 5.0, 'forward': 1.0}],
        'glow_shaders': {'rg_charge_glow': {'rgb': BLUE, 'additive': True, 'radial': True,
                                            'hot': True, 'falloff': 1.4, 'fade_source': 'B_out'}},
        # the TRACER's textures (THE BEAM RECIPE, B7 / C6): Halo 4's rg_firing_tracer_3p profiles through its
        # palette grad_bluelight_1 -- the core = electrical_beam (512 x 64, its length kept and tiled), the
        # glow = plasma_energy_diff (1024 x 64); both additive (premultiplied)
        'baked_textures': {'rg_tracer_core': {'profile': H4 + r'fx\bitmaps\2d\tracer\electrical_beam.bitmap',
                                              'palette': H4 + r'fx\bitmaps\gradient\grad_bluelight_1.bitmap',
                                              'premultiply': True, 'gain': 1.5, 'size': (512, 64)},
                           'rg_tracer_glow': {'profile': H4 + r'fx\bitmaps\2d\tracer\plasma_energy_diff.bitmap',
                                              'palette': H4 + r'fx\bitmaps\gradient\grad_bluelight_1.bitmap',
                                              'premultiply': True, 'gain': 1.5, 'size': (1024, 64)}},
        # Halo 1's `tool model` keeps 31 characters of a shader name (C1)
        'material_names': {'storm_rail_gun_default': 'rg_body', 'storm_rail_gun_screen': 'rg_screen',
                           'storm_rail_gun_bars': 'rg_bars', 'storm_rail_gun_ok': 'rg_ok',
                           'storm_rail_gun_na': 'rg_na', 'storm_unsc_decals_eagle_crest': 'rg_crest'},
        # the base map: RGB = Halo 4's colour map x 0.903 (diffuse_intensity; no albedo tint), A = the
        # control map's R (specular) -- h4_standin_diffuse.py `color` mode (the Boltshot's / Sticky's):
        #   python h4_standin_diffuse.py <BM>storm_railgun_control.bitmap <SRC>rg_body_base.png
        #          --mode color --color <BM>storm_railgun_diff.bitmap --tint 0.903
        'shaders': {'rg_body': (SRC + 'rg_body_base.png', None),
                    'rg_crest': (H4 + r'objects\bitmaps\storm_decals\bitmaps\storm_unsc_decals_eagle_crest_diff.bitmap', None)},
        'decals': ('rg_crest',),
        'glow': {},
        # THE ON-GUN DISPLAY. BOOT 1 (user: 'the yellow display does not look that good -- in the original it
        # also charges up on the charge up'): as textured self-illuminated shader_models it drew PALE with GREEN
        # bars (the bars' texture is a meter map: R = the shape, G a constant 227, A = the fill gradient). Halo
        # 4: the bars (srf_constant_meter-like, albedo (1, 0.855, 0), si 4) CLIP by `primary_charged` against
        # their alpha -- they fill bottom-up as the gun charges; ok / na carry a primary_charged function too.
        # -> the Storm Rifle's display recipe: the BARS a Halo 1 meter on B out (= primary charged, the GL's
        # object function), shape R, the alpha gradient inverted (bright = the bottom = lit first:
        # `gradient_range` (1, 0)); the SCREEN and the OK / NA icons static lit shapes in Halo 4's yellow
        'meters': {
            'rg_bars': {'map': H4 + SBM + 'storm_rail_gun_bars.bitmap', 'from': PR + r'fp\shaders\gauge',
                        # BOOT 4 (user, reaction time): full at 2/3 of the charge (0.5 s of 0.75)
                        'shape': 'r', 'gradient': 'alpha', 'gradient_range': (0.667, 0.0), 'value': 'B_out',
                        'color': YELLOW, 'color_off': (0.12, 0.1, 0.0)},
            'rg_screen': {'map': H4 + SBM + 'storm_rail_gun_screen.bitmap', 'from': PR + r'fp\shaders\gauge',
                          'gradient': 0.0, 'static': r'weapons\needler\shaders\needler luminous',
                          'color': YELLOW},
            'rg_ok': {'map': H4 + SBM + 'storm_rail_gun_ok.bitmap', 'from': PR + r'fp\shaders\gauge',
                      'gradient': 0.0, 'static': r'weapons\needler\shaders\needler luminous',
                      'color': YELLOW},
            'rg_na': {'map': H4 + SBM + 'storm_rail_gun_na.bitmap', 'from': PR + r'fp\shaders\gauge',
                      'gradient': 0.0, 'static': r'weapons\needler\shaders\needler luminous',
                      'color': YELLOW}},
        # the AR's gun shader (the Suppressor's / Boltshot's / Sticky's, user-approved)
        'template': r'weapons\assault rifle\fp\shaders\gun',
    },

    # FP animations (h1_fp_retarget.py): ROUTE (a), Halo 4's own storm_fp_rail_gun (Foundry, h4_fp_dump.py ->
    # out\h4_fp, 2026-10-16), the arms RE-SOLVED. 25 animations, 85 bones (the 80 storm_fp arm / camera nodes
    # + the render model's 5): fire_2 23 (the charged shot; there is no fire_1), overcharged 35 (the charged
    # HOLD), idle 101, posing var1 94 / var2 112, ready 21 (ready_initial 31), put_away 6, melee_strike_1 35
    # (/_2 37, dash 41), reload_empty 83 / reload_full 60, throw_grenade 45, moving 21 / look 10 (overlays);
    # sprint / jump / land / fall / acceleration_screens: no Halo 1 state
    'retarget': {
        'graph': H4 + SFP + '.model_animation_graph',
        'render_model': H4 + SW + r'\storm_rail_gun.render_model',
        'nodes': {n[2:]: 'frame ' + n.replace('_', ' ') for n in GUN_NODES},
        'drop_nodes': tuple(DROP),
        'h1_dir': r'weapons\railgun\fp',
        'h1_model': r'weapons\railgun\fp\fp',
        'align': 'same_space',
        'view_offset': (0.0, 0.0, 0.0),
        'anims': {
            'first_person:idle': 'first-person idle',
            'first_person:posing:var1': 'first-person posing',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            # the fuel rod's ONE trigger: the discharge plays fire-1
            'first_person:fire_2': 'first-person fire-1',
            # the charged hold: Halo 1's plasma pistol plays `overcharged` while its trigger is charged
            'first_person:overcharged': 'first-person overcharged',
            'first_person:melee_strike_1': 'first-person melee',
            'first_person:moving': 'first-person moving',
            'first_person:look': 'first-person overlays',
            'first_person:throw_grenade': 'first-person throw-grenade',
            'first_person:reload_empty': 'first-person reload-empty',
            'first_person:reload_full': 'first-person reload-full',
        },
        # BOOT 1 (user: 'the charge animation restarts in the middle of the animation partly'): Halo 1 LOOPS
        # `overcharged` while the trigger stays charged; Halo 4's is 35 fr (1.17 s) and the _pve hold is 1.5 s
        # -> retimed to 45 fr (1.5 s) for boot 2. BOOT 2 (user: 'I can't release the shot after the charge, I
        # need to keep holding until it fires on its own'): Halo 1's one-trigger charge fires ONLY by its
        # discharge (a release while charged fires nothing) -> charge hold 0 (option 1, user: fires the moment
        # the 0.75 s charge completes); with no hold the retime has no purpose: Halo 4's own 35 fr again.
        # BOOT 3 (user: 'the charge animation needs to fit the new charge time'): it plays during the CHARGE
        # and was cut by the shot -> 35 -> 23 fr (0.75 s: the shot lands on its last frame)
        # BOOT 4 (user: 'the charge meter and animation should signify full load before it is actually fully
        # charged, for human reaction times'): the motion in 0.5 s (15 fr), its last pose held 8 fr more = 0.75 s
        'resample': {'first-person overcharged': 15},
        'pad_end': {'first-person overcharged': 8},
    },

    # Halo 4's own sounds (h1_port_sounds.py railgun, `bank` 'halo4'): the player bank railgun_player
    # (h4_sound_research event, 2026-10-16); FP cues from the frame_event_list (h4_sound_research cues).
    # fire = play_wea_railgun_player_fire: 5 actions = LAYERS (h4_event_layers: randoms 0x092245df (3),
    # 0x3c95a894 (3), 0x37bf198d (2), 0x0c243376 (4) + the single 0x36bb6e1a); charge = a 3-way random
    # (0x0472a183); ready = switchto_mech + switchto_fly @0; reload = mech_a @1, fly_a @30, mech_b @36,
    # fly_b + mech_c @54 (both reloads); posing = idle_a @5 + idle_b @50; the explosion / flyby in
    # proj_railgun; the impact events ship in no bank (the burst covers the hit). Levels = the stock Halo 1
    # ROCKET sound each stands in for (h1_stock_sound_levels)
    'sounds': {
        'catalog': 'Railgun',
        'bank': 'halo4',
        'wwise_bank': 'railgun_player',
        'dir': B.join(['sound', 'weapons', 'railgun_port']),
        'sounds': {
            'rg_fire': (['obj_092245df', 'obj_3c95a894', 'obj_36bb6e1a', 'obj_37bf198d', 'obj_0c243376'],
                        'sound\\sfx\\weapons\\rocket launcher\\fire', -15.1),
            'rg_charge': (['play_wea_railgun_player_charge'],
                          'sound\\sfx\\weapons\\plasma rifle\\startcharge', -12.0),
            'rg_dryfire': (['play_wea_rail_gun_player_dry_fire'],
                           'sound\\sfx\\weapons\\assault rifle\\dryfire', -17.6),
            'rg_ready': (['play_wea_rail_gun_switchto_mech_player', 'play_wea_rail_gun_switchto_fly_player'],
                         'sound\\sfx\\weapons\\weapon_anims\\rocket_ready', -18.3),
            'rg_melee': (['play_wea_railgun1_foley_melee_player'],
                         'sound\\sfx\\weapons\\weapon_anims\\rocket_melee', -21.8),
            'rg_reload': (['play_wea_rail_gun_reload_mech_a', 'play_wea_rail_gun_reload_fly_a',
                           'play_wea_rail_gun_reload_mech_b', 'play_wea_rail_gun_reload_fly_b',
                           'play_wea_rail_gun_reload_mech_c'],
                          'sound\\sfx\\weapons\\weapon_anims\\rocket_reload_e', -22.5),
            'rg_pose': (['play_wea_rail_gun_idle_player_a', 'play_wea_rail_gun_idle_player_b'],
                        'sound\\sfx\\weapons\\weapon_anims\\rocket_posing', -22.1),
            'rg_ammo': (['play_weapon_ammo_pickup_fallback@weapon_sync'],
                        'sound\\sfx\\weapons\\weapon_pickup_ammo\\sniper_ammo', -30.5),
            'rg_drop': (['play_wea_drop_rifle_shotgun_nonplayer@homing_rifle_player'],
                        'sound\\sfx\\impulse\\weapon_drops\\shotgun_impact', -20.7),
            'rg_flyby': (['play_proj_railgun_whizby@proj_railgun'],
                         'sound\\sfx\\impulse\\impacts\\plasrif_projectile', -26.2),
            'rg_explode': (['play_wea_railgun_explosion@proj_railgun'],
                           'sound\\sfx\\weapons\\frag grenade\\expl', -7.9),
            # the BALANCED reload (the patcher retimes it x1.078, then swaps this in)
            'rg_reload_balanced': (['play_wea_rail_gun_reload_mech_a', 'play_wea_rail_gun_reload_fly_a',
                                    'play_wea_rail_gun_reload_mech_b', 'play_wea_rail_gun_reload_fly_b',
                                    'play_wea_rail_gun_reload_mech_c'],
                                   'sound\\sfx\\weapons\\weapon_anims\\rocket_reload_e', -22.5),
        },
        'offsets': {'rg_ready': [0.0, 0.0],
                    'rg_reload': [1 / 30.0, 30 / 30.0, 36 / 30.0, 54 / 30.0, 54 / 30.0],
                    'rg_reload_balanced': [1 / 30.0, 30 / 30.0, 36 / 30.0, 54 / 30.0, 54 / 30.0],
                    'rg_pose': [5 / 30.0, 50 / 30.0]},
        'stretch': {'rg_reload_balanced': 88.4 / 82.0},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only railgun) on a COPY of the Halo 1 ROCKET LAUNCHER (the
    # yardstick: two-handed heavy, a magazine + reload, the rocket's HUD, melee and explosion table) with the
    # FUEL ROD's ONE-TRIGGER CHARGE (A8: charge, then 'discharge'; an early release fires nothing) -- Halo
    # 4's charge-with-magazine: charging 0.75 s, then it fires by itself (no hold: boot 2). DEFAULT = HALO
    # 4's OWN NUMBERS; the rocket-ratio values are the balance rows. STEP 6, the ammo pickup: the rocket's
    # ammo box (Halo 4's _pve names a UNSC ammo box with 0 rounds: Halo 4 has no ammo pickups), its 2 rounds
    # x Halo 4 carry 6 / H1 rocket 8 -> 1 slug a box (the Brute Shot's rule)
    'pickable': {
        'weapon': RG + 'railgun',
        'template': RL + 'rocket launcher',
        'world_model': RG + 'railgun',
        # ONE model tag for world AND first person (Halo 1's 32 MiB model buffer: plan 0.1)
        'fp_model': RG + 'railgun',
        'fp_anims': RG + 'fp\\fp',
        'label': 'rg',
        # two-handed HEAVY: Halo 1's rocket pose (the reserved donor)
        'teach': ('rg', 'rl'),
        'keys': {'first-person melee': 4,            # Halo 4 melee_strike_1 primary keyframe 4
                 'first-person reload-empty': 36,    # reload_empty primary keyframe 36
                 'first-person reload-full': 36},
        'sounds': {'first-person ready': SND + 'rg_ready',
                   'first-person posing': SND + 'rg_pose',
                   'first-person melee': SND + 'rg_melee',
                   'first-person reload-empty': SND + 'rg_reload',
                   'first-person reload-full': SND + 'rg_reload'},
        'extra_sounds': [SND + 'rg_reload_balanced'],
        'bullet': SLUG,
        # the fuel rod's trigger (A8): rounds per second 10, 'does not repeat automatically' -- one slug a
        # charge; Halo 4's 0.6 s recovery is moot on a 1-round magazine (the reload follows)
        # the trail from the FP muzzle (C6): the trigger's first-person offset = the FP `primary trigger` in
        # camera space, idle frame 0 (h1_fp_muzzle.py; set after the first model build)
        'trigger': {'rounds_per_second': (10.0, 10.0), 'acceleration_time': 0.0,
                    'deceleration_time': 0.0, 'first_person_offset': FP_MUZZLE},
        # Halo 4: minimum error 0, error 0.15 -> 0.8 (the bloom never builds at one round a reload)
        'error_deg': {'minimum_error': 0.0, 'error_angle': (0.15, 0.8)},
        # BOOT 3 (user: 'a guaranteed overheat after firing, timed out exactly at the reload'): heat 1.0 a round,
        # back at 0.1, loss 0.9 / 2.733 s. BOOT 4 (user: 'the heat does nothing, revert it'; the probe: heat
        # word +0x204 1.0 -> 0 over ~4.5 s, but Halo 1 keeps CHARGING through the reload and the overheat -- the
        # charge word +0xE4 restarts 0.07 s after the shot while the trigger stays held -- and the discharge
        # fires the moment the gun is ready: shots CHAIN while held, the Spartan Laser's case). Reverted; the
        # chaining is accepted for now (a halo1.dll patch is the candidate fix, user)
        # Halo 4: 1 loaded, 4 at pickup, 6 most, 1 reloaded; reload = reload_empty 82 fr (Halo 1 needs a
        # number: the animation's 82 / 30)
        'magazine': {'rounds_loaded_maximum': 1, 'rounds_reloaded': 1,
                     'rounds_total_initial': 4, 'rounds_total_maximum': 6,
                     'reload_time': 82 / 30.0},
        # Halo 4 aim assist: the MODE block's mode 0 (unzoomed; the railgun has no zoom)
        'aiming': {'autoaim_angle': 2.5, 'autoaim_range': 25.0,
                   'magnetism_angle': 7.5, 'magnetism_range': 25.0},
        # THE CHARGE as an object function (the GL's): out 0 = the rocket's function 0, out 1 = the plasma
        # pistol's function 3 (`one` x B in) with weapon B in = primary charged -> B out = the charge
        'obje_functions': [{'from': RL + 'rocket launcher', 'index': 0},
                           {'from': 'weapons\\plasma pistol\\plasma pistol', 'index': 3}],
        # the CHARGE SOUND: Halo 4's charge (a one-shot whir) as the start of a sound_looping at the muzzle
        # scaled by B out -- it plays from the press while the charge builds (the GL's charge cue)
        'fire_loop': {'like': B.join(['sound', 'sfx', 'weapons', 'plasma rifle', 'charging']),
                      'start': SND + 'rg_charge', 'loop': '', 'end': '',
                      'tag': SND + 'rg_charging', 'marker': 'primary trigger', 'scale': 'B_out'},
        # THE CHARGE-UP SEEN ON ENEMIES (Armed boot, user 2026-10-16: 'no visible charge-up on the enemy' --
        # 'enemies should show the charge-up like Halo 4'): the model's charge glow (glow_points) is a 5 cm
        # star, lost at range. Halo 4 draws charging_3p (a light volume + a cheap light) at rail_charge; Halo 1
        # shows a held weapon's ATTACHMENTS on the third-person gun -- the Jackals' charged plasma pistol glow
        # is its attachment 2, light weapons\plasma rifle\overcharge (radius 1.5, a lens flare to 0.175 wu)
        # on its charge output. The same light, the railgun blue, on B out (= primary charged). User (Armed
        # boot 2): 'no charge at the MUZZLE of the enemies, only the normal charge up visible' (the rail glow
        # does show) -- Halo 4's charging.effect draws at rail_charge AND primary_trigger -> at the muzzle
        'charge_light': [{'from': 'weapons\\plasma rifle\\overcharge', 'out': RG + 'charge light',
                          'rgb': BLUE, 'marker': 'primary trigger', 'scale': 'B_out'}],
        'fields': {
            'weap_attrs.B_in': 'primary_charged',
            # THE TRIGGER (the fuel rod's way): charge 0.75 s, then DISCHARGE. Halo 4 holds the charge 1.5 s
            # (_pve) and fires on release; Halo 1's one trigger fires ONLY by its discharge (boot 2: a release
            # while charged fired nothing, the shot came 2.25 s after the press) -> hold 0 (user, option 1:
            # it fires the moment the charge completes; an early release still cancels). Lost: choosing the
            # moment of release. Rejected: the plasma pistol's charged pair (Halo 4's release, but Halo 1's AI
            # only taps a pair -- A8: Armed enemies would never fire the slug)
            'weap_attrs.triggers.0.charging.charging_time': 0.75,
            'weap_attrs.triggers.0.charging.charge_hold_time': 0.0,
            'weap_attrs.triggers.0.charging.overcharged_action': 'discharge',
            'weap_attrs.triggers.0.flags.does_not_repeat_automatically': True,
            'weap_attrs.triggers.0.flags.projectile_is_client_side_only': False,
            # Halo 4's railgun has NO zoom: the rocket's 2x goes, and its zoom sounds with it
            'weap_attrs.aiming.zoom_levels': 0,
            'weap_attrs.interface.zoom_in_sound.filepath': '',
            'weap_attrs.interface.zoom_out_sound.filepath': '',
            # STEP 6: the rocket's ammo box, 1 slug (2 x 6 / 8 = 1.5 -> 1)
            'weap_attrs.magazines.0.magazine_items.0.rounds': 1,
            'weap_attrs.triggers.0.firing_effects.0.empty_effect.filepath': SND + 'rg_dryfire',
            'weap_attrs.interface.pickup_sound.filepath': SND + 'rg_ammo',
            'item_attrs.collision_sound.filepath': SND + 'rg_drop',
            'obje_attrs.collision_model.filepath': RG + 'railgun',
            # STEP 4b list 2 (Halo 4 railgun / Halo 4 rocket onto the H1 rocket): active camo ding 1 x 0.75/1,
            # illumination recovery 0.3 x 0.05/0.2; list 3: error deceleration Halo 4's 0.5 (the rocket's 0: a
            # zero on one side); the heat 0.36 a round NOT written (Halo 4's loss 1/s: inert at one round a
            # reload; Halo 1 would draw no meter for it on the rocket HUD either)
            'weap_attrs.interface.active_camo_ding': 0.75,
            'weap_attrs.triggers.0.misc.illumination_recovery_time': 0.3 * 0.05 / 0.2,
            'weap_attrs.triggers.0.firing.error_deceleration_time': 0.5,
        },
        # THE MUZZLE-FLASH RULE (check 10, before boot 1): see SLUG / the firing effect below
        'sound_effects': {
            'firing_effect': (RL + 'effects' + B + 'fire rocket', RG + 'effects' + B + 'fire slug',
                              {B.join(['sound', 'sfx', 'weapons', 'plasma rifle', 'fire']): SND + 'rg_fire'},
                              FIRE_FLASH)},
        # Halo 4 shares strike_melee with its rocket: x1 = the H1 rocket's own melee (copied)
        # THE CHARGE LATCH (halo1.dll h1_charge_latch.py v2, bc1a3d9; user 2026-10-16: 'fire, let go, hold
        # again fires a quick second shot'): a held trigger fires one slug, and a press during the reload
        # charges in full -- weapon flags bit 30 (the patch is an enhancer option; without it the bit is
        # inert). Live probes on a30: v1 missed the press-during-reload case, v2 confirmed (both cases)
        'charge_needs_release': True,
        'melee': (RL + 'melee', RG + 'melee'),
        'melee_response': RL + 'melee_response',
        'messages': ('Picked up a railgun', 'Picked up %d rounds for railgun'),
        'icon': 'railgun',
        # the ROCKET's HUD with Halo 4's crosshair (railgun.cui_screen, at rest): `u_shape` = rail_halfcircle
        # 64 x 32 at (-32, -8) -> centre (0, 8); `inner_ring` = rail_circle 32 x 32 at (-16, -16) x1.1,
        # opacity 0.3; `reticule_tick_bottom` = a white pixel 2 x 9 at (-1.1, 18) -> centre (-0.1, 22.5); the
        # `charge_l` / `charge_r` arcs (rail_charge through a meter shader on the charge) are the CHARGE
        # display -- Halo 1's charge crosshair never draws in MCC (A8): not reproduced. Sized on the user's
        # idle screenshot (2026-10-16, 1080p): the U 86 px for its 64 units = 1.34 px a unit (the Sticky
        # Detonator's calibration formula)
        'hud': {'donor': RL + 'rocket_launcher', 'out': RG + 'railgun',
                'reticle': (H4 + RGUI + 'rail_halfcircle', 0, 'railgun'),
                'reticle_xform': {'offset': (0.0, 8.0)},
                'reticle_layers': [(H4 + RGUI + 'rail_circle', 0, 1.1, 0.5),
                                   (H4 + r'ui\cui\common\white_pix', 0, 1.0,
                                    {'stretch': (6.0, 27.0), 'offset': (-0.1 / 6.0, 22.5 / 27.0)})],
                'reticle_min_width': 2,
                'reticle_supersample': 2,
                'reticle_scale': 2.8, 'reticle_overlay': 1.34 / (123 / 97.0 * 2.8 * 2 * 0.75),
                'fields': {'flash_cutoffs.total_ammo_cutoff': 1},
                # BOOT 5 (user: 'get the original ammo meter in'): Halo 4's `bitmap_ammo_ticks` (railgun.cui_screen:
                # 49 x 20 at (143, 60)) draws ammo_railgun -- a silhouette of the gun, one a round -- at native
                # density (the Binary Rifle's shard route)
                'ammo_meter': {'sizes': (1,), 'base': RG + 'bitmaps\\railgun_ammo',
                               'art': {'h3': (H4 + RGUI + 'ammo_railgun', 0), 'native': True}}},
        'palette_levels': LEVELS,
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py railgun). DEFAULT = Halo 4's own numbers in the
    # tags; BALANCED = the ROCKET ratio (step 4a, user 2026-10-16). Assembly Halo1 units: angles in degrees,
    # velocity in wu per TICK (100 wu/s = 3.333; 120 = 4.0)
    'catalog': {
        'entry': {
            'weapon': 'Railgun', 'source': 'Halo 4', 'donor': 'Rocket Launcher', 'default_on': False,
            'desc': "Halo 4's Railgun: its model, first-person animations, sounds and numbers. Hold the "
                    "trigger for 0.75 s and it fires (let go earlier to cancel); "
                    "the slug sticks and bursts: 120 + 180 damage. One round, then a reload. Rocket "
                    "Launcher ammo tops it up.",
            'balance_desc': "Measured against the Rocket Launcher, which both games have: 86 + 129 damage "
                            "a slug over a 0.8 wu blast, 8 rounds most, a 120 wu/s slug, a slower reload "
                            "and Halo 1-style aim assist.",
            # step 9: the balanced reload 125 fr x 82/116 = 88.4 over the built 82 (x1.078). Swap: H1 rocket
            # ready 22 fr x Halo 4 railgun 21 / Halo 4 rocket 26 = 17.8 over the built 21 (x0.846)
            'anims': {'reload': 1.078, 'swap': 0.846},
            'anim_sounds': {'reload': [
                {'mult': 1.078, 'from': SND + 'rg_reload', 'to': SND + 'rg_reload_balanced'}]},
            'balance': [
                row('jpt!', RG + 'slug impact', 'Damage Lower Bound', 85.9, 120.0, 'Projectile Damage'),
                row('jpt!', RG + 'slug impact', 'Damage Upper Bound', 85.9, 120.0, 'Projectile Damage'),
                row('jpt!', RG + 'slug impact', 'Damage Upper Bound Max', 85.9, 120.0, 'Projectile Damage'),
                row('jpt!', RG + 'explosion', 'Damage Upper Bound', 128.9, 180.0, 'Explosion Damage'),
                row('jpt!', RG + 'explosion', 'Damage Upper Bound Max', 128.9, 180.0, 'Explosion Damage'),
                row('jpt!', RG + 'explosion', 'Radius From', 0.306, 0.55, 'Explosion Radius'),
                row('jpt!', RG + 'explosion', 'Radius To', 0.8, 1.0, 'Explosion Radius'),
                row('weap', RG + 'railgun', 'Rounds Total Maximum', 8.0, 6.0, 'Magazine', block='Magazines'),
                row('proj', RG + 'slug', 'Initial Velocity', 4.0, 3.333, 'Projectile'),
                row('proj', RG + 'slug', 'Final Velocity', 4.0, 3.333, 'Projectile'),
                row('weap', RG + 'railgun', 'Autoaim Range', 14.6, 25.0, 'Autoaim'),
                row('weap', RG + 'railgun', 'Magnetism Angle', 9.0, 7.5, 'Magnetism'),
                row('weap', RG + 'railgun', 'Magnetism Range', 35.0, 25.0, 'Magnetism'),
            ]},
    },

    # step 4b (port_field_audit.py --port railgun): the source pair (Halo 4 railgun _pve vs the yardstick,
    # Halo 4's rocket launcher) against the target pair (the H1 port vs its template, the H1 rocket)
    'field_audit': {
        'source_kit': 'H4EK',
        'source': {'weapon': (SW + r'\storm_rail_gun_pve.weapon',
                              r'objects\weapons\support_high\storm_rocket_launcher\storm_rocket_launcher.weapon'),
                   'projectile': (SW + r'\projectiles\storm_rail_gun_bolt_pve.projectile',
                                  r'objects\weapons\support_high\storm_rocket_launcher\projectiles\storm_rocket_launcher_rocket.projectile'),
                   'damage_effect': (SW + r'\projectiles\damage_effects\storm_rail_gun_bolt_explosion_pve.damage_effect',
                                     r'objects\weapons\support_high\storm_rocket_launcher\projectiles\damage_effects\storm_rocket_launcher_rocket_explosion.damage_effect')},
        'target': {'weapon': (RG + 'railgun.weapon', RL + 'rocket launcher.weapon'),
                   'projectile': (RG + 'slug.projectile', RL + 'rocket.projectile'),
                   'damage_effect': (RG + 'explosion.damage_effect', RL + 'explosion.damage_effect')}},

    # the dry test: a30 (this session's level, parallel pair 6), Halo 4's own loadout (1 + 4)
    'test': {'level': 'a30', 'rounds': (1, 4), 'grunt': None, 'elite': None},
})
