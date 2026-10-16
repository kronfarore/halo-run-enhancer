r"""Sticky Detonator (Halo 4, wave C8): IN PROGRESS -- step 4a decided (user, 2026-10-16); the port
sections (model / retarget / pickable / sounds / catalog / test) follow.

HALO 4 (H4EK 2026-10-16, h3_weapon_values --kit h4 + the exports): the SOURCE is the campaign tag
`storm_sticky_detonator_pve` (user, over the MP tag). The two weapons are identical but for the
projectile (and abandonment 10 vs 12 s, the pickup sound): MP 10 -> 15 wu/s, burst 75..240
explosion_large (falloff exponent 6.5) over 0.4 -> 2.5, attached the same + accel 2.5; _pve 24 -> 10
wu/s, burst 75..500 explosion_small (exponent 1.5) over 0.4 -> 2.5, attached 50..500 over 0.4 -> 2.0, no
super attached damage, no holiday 'celebration' attachment. Trigger `double-latch-tether`: the press
fires, the NEXT press detonates the charge (stuck or in flight; `tether transition to linked` 0.3 s,
`max latch time to arm` 0.1 s); `max latch time to detonate` 30 s = the fallback after sticking.
Responses (`material response`, the table Halo 4 reads): default_material ATTACH (everything),
energy_shield_thick / _invulnerable BOUNCE -> the 'after first bounce' timer 0..1e-6 bursts it at once,
liquid overpenetrate. 1 loaded / 4 / 6, reloads 1 (FP reload_empty 58, reload_full 51), recovery 1.0 s,
error 0.15 / 0 -> 0.4, aim 4/15 8/15, gravity 0.25, range 20, impact 5 `collision` (accel 0.5),
strike_melee. Its ai\generic: none in any Halo 4 map (phase 0).

THE APPROXIMATION (user, step 4a): A = STICK + FUSE -- the Plasma Launcher's sticky recipe (attach on
every material, Jackal shields reflect), the fuse 0.5 s once at rest (stuck = at rest; Halo 4's fastest
detonation ~ arm 0.1 + tether 0.3 s); the FREE burst only (Halo 1 deals attached damage at the stick,
B6). Not reproduced: choosing when it bursts (trap a doorway, wait for a group), the mid-air burst,
the 30 s wait, the stuck burst's own 2.0 wu radius.

THE WEAPON: a copy of the Halo 1 PISTOL (one-handed, a magazine + reload, its HUD and melee; the
Boltshot's / LightRifle's Halo 4 sidearm route) firing a CHARGE built on the Halo 1 PLASMA GRENADE's
projectile (the Plasma Launcher's sticky bolt: plasma_launcher.py BOLT) with the FRAG GRENADE's
explosion effect (Halo 4's burst is a human fireball, sgl_*) around an own copy of the plasma grenade's
damage table (the yardstick's table, user)."""
from ._common import B, reserved, row  # noqa: F401
from .storm_rifle import DROP

H4 = 'h4:'                                          # an H4EK path (h4_tags)
SW = r'objects\weapons\pistol\storm_sticky_detonator'
SFP = r'objects\characters\storm_fp\weapons\pistol\fp_sticky_detonator\storm_fp_sticky_detonator'
STK = r'ui\hud\weapons\human\sticky\bitmap' + B    # Halo 4's crosshair / screen art (CUI)
# the base map: RGB = Halo 4's colour map x 0.9 (diffuse_intensity; the material has no albedo tint),
# A = the control map's R (specular) -- h4_standin_diffuse.py `color` mode (the Boltshot's):
#   python h4_standin_diffuse.py <BM>storm_sticky_detonator_control.bitmap <BASE>sd_body_base.png
#          --mode color --color <BM>storm_sticky_detonator_diff.bitmap --tint 0.9
BASE = r'F:\SteamLibrary\steamapps\common\HCEEK\data\weapons\sticky detonator\source' + B
SD = 'weapons\\sticky detonator\\'
SND = 'sound\\weapons\\sticky_detonator_port\\'
PISTOL = 'weapons\\pistol\\'
PG = 'weapons\\plasma grenade\\'
FG = 'weapons\\frag grenade\\'
AR = 'weapons\\assault rifle\\'
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']
# Halo 4's charge light (the user's screenshot 2026-10-16: the stuck charge an orange-white dot)
ORANGE = (1.0, 0.5, 0.18)
# the render model's 3 nodes, all animated by the FP graph (b_sight = the flip-up screen, b_grenade =
# the loaded charge)
GUN_NODES = ('b_gun', 'b_sight', 'b_grenade')
# Halo 1 material indices: Halo 4's `material response` table -- default ATTACH (everything),
# energy_shield_thick / _invulnerable BOUNCE with the 'after first bounce' 1e-6 s timer = burst at once
# (-> Halo 1 DETONATE on the Jackal shield and the force fields), liquid overpenetrate
JACKAL_SHIELD, WATER = 16, 28
FORCE_FIELDS = [10, 18, 26, 32]      # force field, engineer force field, monitor, hunter shield
ATTACH = [i for i in range(33) if i not in [JACKAL_SHIELD, WATER] + FORCE_FIELDS]

# THE CHARGE (approximation A, user 4a): the plasma grenade's projectile, Halo 4's own numbers
CHARGE = {
    'projectile': (PG + 'plasma grenade', SD + 'charge'),
    # the IMPACT: Halo 4's 5 `collision` (accel 0.5). BOOT 1 (user: 'the impact / attaching does damage,
    # which is weird -- shift all damage to the actual explosion'): no impact damage, its 5 into the burst
    'damage': None, 'no_impact_damage': True,
    # THE BURST: Halo 4 _pve 75..500 over 0.4 -> 2.5 (AOE core 0.4, explosion_small, accel 2 = Halo 4's
    # plasma grenade's 2: x1 -> the grenade's own 4); the frag grenade's fireball effect, its damage
    # part repointed to an own copy of the PLASMA GRENADE's table (the yardstick's, user); the screen
    # flash yellow + short (A7: an explosion's flash is yellow; B6: a copy's 1 s flash is too much)
    'explosion': {'effect': (FG + 'effects' + B + 'explosion', SD + 'effects' + B + 'charge explosion'),
                  'part': FG + 'explosion',
                  'out_dir': SD + 'effects' + B,
                  'damage': (PG + 'explosion', SD + 'explosion'),
                  'lower': 80.0, 'upper': (505.0, 505.0), 'radius': (0.4, 2.5),
                  'fields': {'damage.aoe_core_radius': 0.4,
                             'screen_flash.duration': 0.25,
                             'screen_flash.maximum_intensity': 0.3,
                             'screen_flash.tint_lower_bound.r': 1.0,
                             'screen_flash.tint_lower_bound.g': 0.85,
                             'screen_flash.tint_lower_bound.b': 0.4},
                  'swaps': {B.join(['sound', 'sfx', 'weapons', 'frag grenade', 'expl']): SND + 'sd_explode'}},
    'velocity': (24.0, 10.0), 'range': 20.0,
    'model': SD + 'charge' + B + 'charge',
    # STEP 4b list 2 (port_field_audit: H4 charge vs H4 plasma grenade onto the H1 grenade): the engine's
    # gravity by the ratio -- air 1.0 x 0.25/0.9 = 0.278, water 1.0 x 0.25/0.75 = 0.333; danger radius
    # 2.25 x 1/2 = 1.125. Kept: the air damage range (Halo 4 0,0 = unset -> the range, the PL's), the
    # timer (the user's 0.5 s fuse, 4a)
    'proj_fields': {'proj_attrs.physics.air_gravity_scale': 1.0 * 0.25 / 0.9,
                    'proj_attrs.physics.water_gravity_scale': 1.0 * 0.25 / 0.75,
                    'proj_attrs.detonation.arming_time': 0.0,
                    # THE FUSE (user, 4a): 0.5 s once at rest -- stuck = at rest (B6)
                    'proj_attrs.detonation.timer': (0.5, 0.5),
                    'proj_attrs.detonation_timer_starts': 'when_at_rest',
                    'proj_attrs.detonation.danger_radius': 2.25 * 1.0 / 2.0,
                    'proj_attrs.detonation.minimum_velocity': 0.0,
                    'proj_attrs.physics.air_damage_range': (0.0, 20.0),
                    'proj_attrs.physics.guided_angular_velocity': 0.0,
                    # Halo 1 deals ATTACHED damage at the stick (B6, boot 1) -> none: the burst alone
                    'proj_attrs.physics.attached_detonation_damage.filepath': '',
                    'proj_attrs.collision_radius': 0.0,
                    'proj_attrs.flags.oriented_along_velocity': True,
                    'proj_attrs.flags.detonation_max_time_if_attached': False},
    'default_responses': {'attach': ATTACH, 'detonate': [JACKAL_SHIELD] + FORCE_FIELDS,
                          'overpenetrate': [WATER]},
    # the grenade's per-material DETONATION effects would replace the burst (the GL's trap)
    'clear_detonation_effects': True,
    # the grenade's blue light + armed light dropped; Halo 4's orange charge light (a light + flare)
    'keep_attachments': (),
    'glow': {'light': ('weapons' + B + 'fuel rod gun' + B + 'fuel rod exhaust', SD + 'charge glow'),
             'flare': SD + 'charge glow', 'rgb': ORANGE, 'flare_radius': 0.08, 'marker': ''},
    # the fuse start (stuck / at rest): the grenade's `detonation start` with Halo 4's attach beep
    # BOOT 1 (user: 'the attached grenade has leftover plasma grenade effects'): the grenade's particles
    # dropped (green energy smoke, shield flash, plasma electric bolts, stealth flares) -- Halo 4's stick
    # is the beep + the charge's own light; the water bubbles kept
    'started_effect': {'from': PG + 'effects' + B + 'detonation start', 'out': SD + 'effects' + B + 'stuck',
                       'drop_particles': ('smoke c generic', 'flash h shield impact', 'plasma electric bolts',
                                          'flare h stealth cannon'),
                       'swaps': {B.join(['sound', 'sfx', 'impulse', 'impacts', 'dirthits']): SND + 'sd_stick'}},
    'impact_tint': {'match': (), 'rgb': None, 'out': SD + 'effects' + B + 'impact' + B,
                    'drop_particles': ('smoke c generic', 'flash h shield impact'),
                    'sounds': {B.join(['sound', 'sfx', 'impulse', 'impacts', 'dirthits']): SND + 'sd_stick'}},
}

PORT = reserved(
    order=33, wave='C8', name='Sticky Detonator', source='Halo 4',
    messages=(99, 100), icon=53, reticle=42, label='sd', teach_from='hp',
    sound_dir='sound\\weapons\\sticky_detonator_port', weapon_dir='weapons\\sticky detonator',
    yardstick={
        # step 4a (user, 2026-10-16; h3_weapon_values --kit h4 storm_sticky_detonator(_pve) /
        # storm_rocket_launcher / storm_fuel_rod_cannon + the projectile / damage exports + h1_role_compare
        # sticky_detonator). Halo 4: rocket 200 impact + 240 explosion_large over 0.9 -> 2.5, 0.8 s, 2 / 4 /
        # 6, 116 fr, 10 -> 20 wu/s, gravity 0.02, 175, aim 5/60 10/25; fuel rod 100 + 60 over 0.5 ->
        # 2.25, 0.4 s, 5 / 15 / 20, 90 fr; plasma grenade free 250 over 0.3 -> 1.45 (25 lower), attached
        # 350 (35 lower), fuse 0.9-0.95 at rest. Halo 1: rocket 315 over 0.5 -> 2.0, 2.0 s, 2 / 4 / 8,
        # 125 fr, 12 -> 10, range 128, aim 0/35 12/35; plasma grenade 120 + attached 120 over 0.5 -> 2.0,
        # fuse 2.0 at rest; restored fuel rod 75 over 0.5 -> 1.5 (Hunters immune).
        'pick': 'Plasma Grenade',
        'reason': ("user, step 4a 2026-10-16: the PLASMA GRENADE by the STUCK kill (the sticky family; "
                   "the Plasma Launcher's precedent), its holes (rate, magazine, reload, flight, range, "
                   "aim, melee) by the ROCKET ratio (the GL's precedent), the grenade's table in both "
                   "versions. Halo 1 stuck 240 (120 area + 120 attached) vs Halo 4 attached 350: 500 x "
                   "240/350 = 342.9 as the burst alone (Halo 1's attached damage lands at the stick). "
                   "Fuse 0.5 s in both (user)."),
        # DEFAULT = Halo 4's own; these are the BALANCED rows:
        'balanced': {
            'damage': 342.9,                 # 500 x 240/350 (the stuck kill)
            'radius': (0.667, 3.45),         # 0.4 x 0.5/0.3, 2.5 x 2.0/1.45
            'impact': 0.0,                   # the grenade has none (Halo 4's 2 -> 5 x 0/2)
            'fuse_s': 0.5,                   # user (both versions)
            'fire_recovery_s': 2.5,          # RL: 1.0 x 2.0/0.8
            'magazine': 1,                   # RL: 1 x 2/2
            'rounds_total_initial': 4,       # RL: 4 x 4/4
            'rounds_total_maximum': 8,       # RL: 6 x 8/6
            'reload_s': 4.1667 * 58 / 116,   # RL: 125 fr x 58/116
            'velocity': (28.8, 5.0),         # RL: 24 x 12/10, 10 x 10/20
            'range': 14.6,                   # RL: 128 x 20/175
            'aim': (4.0, 8.75, 9.6, 21.0),   # RL: 35 x 15/60; 12 x 8/10, 35 x 15/25; the angle KEPT
                                             # Halo 4's 4 (the rocket's 0: balanced boot, user)
            'gravity': 0.25,                 # the rocket's 0 vs 0.02: near-zero, no ratio -> Halo 4's
            'error_deg': (0.15, 0.0, 0.4),   # the rocket's 0 / 0 degenerate -> Halo 4's own
            'melee': 55.0},                  # strike_melee both -> the rocket's 55 (x1)
        # Time to kill (h1_role_compare sticky_detonator, direct hits): default 500+5 (PG table) 505 dps
        # column -- one charge for every Elite on legendary, Hunter 2-3; balanced 342.9 at 0.4/s 137 --
        # one charge every Elite, Hunter 3 (normal) / 4 (legendary); RL 158, PG stuck 240 (1/s), GL port
        # 410, PL tap 186, Brute Shot 243
        'measured': 'h1_role_compare.py sticky_detonator',
        'not_reproduced': ("the second-press detonation (stick + a 0.5 s fuse), the mid-air burst, the "
                           "30 s fallback, the stuck burst's 2.0 wu radius (the free 2.5 everywhere); "
                           "Halo 4's idle_empty (the charge gone from the muzzle): Halo 1 has no empty "
                           "idle, so after the LAST charge (no reserve) the loaded charge shows again -- "
                           "the `first-person ammunition` overlay would hide it but also hide the charge "
                           "for the whole reload (Halo 1 counts the round at its end): kept as is (user, "
                           "boot 1)"),
        'candidates': {
            'source_weapon': 'objects\\weapons\\pistol\\storm_sticky_detonator\\storm_sticky_detonator_pve',
            'provisional': 'Rocket Launcher',
            'alternatives': ['Plasma Grenade', 'Flak Cannon'],
            'direct': None,
            'peers': ['Rocket Launcher', 'Flak Cannon'],
            'why': '1-round magazine, arcing sticky explosive (gravity 0.25)',
            'lacks': 'remote detonation (approximated: stick + a 0.5 s fuse), the mid-air burst'}},
    # step 11: NO source entry found
    # step 11: NO ai\generic entry for the Sticky Detonator in any Halo 4 map, under either name
    # (re-checked 2026-10-16 with the _pve tag first: m020, m10-m90, ff91 / ff92; the _pve tag ships in
    # every campaign map) -> a same-game stand-in, chosen with the user before the Armed boot
    # (user, 2026-10-16): donor = the ROCKET LAUNCHER -- the yardstick (the plasma grenade) is thrown, so the
    # rocket fills the hole (the Grenade Launcher's precedent). Halo 1's rocket carriers (h1_weapon_carriers
    # 2026-10-16): the Flood combat Elite and human rocket launcher variants, both WDM 0.4, no actor flags
    # -- they agree, no donor_variant. ARMED WDM RULE: 0.4 x rocket 158 / the port's dps column (default
    # 505 x 1/s = 505 -> 0.125; balanced 346.3 x 0.4/s = 138.5 -> 0.456). THE BALANCED DROP RULE: no
    # Halo 4 Sticky Detonator ai entry (a zero on the source side) -> no balanced drop rows
    firing_profile={'mode': 'same_game', 'donor_weapon': 'weapons\\rocket launcher\\rocket launcher',
                    'why': 'no ai\\generic entry for the Sticky Detonator (_pve or MP) in any Halo 4 map; '
                           'fires like the Halo 1 rocket launcher carriers (user, 2026-10-16)',
                    'wdm_rule': {'base': 0.4, 'yardstick_dps': 158.0, 'port_dps': 505.0,
                                 'balanced_port_dps': 138.5},
                    'species_skill': True},
)

PORT.update({
    'status': 'in_progress',

    # geometry + look (h1_h3_weapon_model.py; Halo 4 through h4_tags). Halo 4's ONE render model for world
    # AND first person: 3 nodes (b_gun root, b_sight = the flip-up screen, b_grenade = the loaded charge),
    # one region; materials storm_sticky_detonator_default (srf_char_blinn_reflection: diff + control
    # spglrf + normal, specular 15, diffuse 0.9; the m020 cache names the same shader) and _hud
    # (srf_constant, white: Halo 4 draws its sticky_launcher_motion_sensor CUI there -- the screen).
    # Markers: primary_trigger, primary_ejection, left_hand(_spartan_fp), magazine_marker, flashlights
    'model': {
        'dir': r'weapons\sticky detonator',
        'world': H4 + SW + r'\storm_sticky_detonator.render_model',
        'fp': H4 + SW + r'\storm_sticky_detonator.render_model',
        'world_name': 'sticky detonator',
        'decimate': {'keep': 80.0, 'protect': 1.0, 'views': [((-0.2094, 0.0689, 0.0631), (0.9964, -0.063, -0.0575), (0.0571, -0.0082, 0.9983), 1.0), ((-0.2105, 0.0694, 0.0603), (0.9971, -0.0645, -0.0399), (0.0397, -0.0054, 0.9992), 1.0), ((-0.2094, 0.0689, 0.0631), (0.9964, -0.063, -0.0575), (0.0571, -0.0082, 0.9983), 1.0), ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), 1.0), ((-0.0002, -0.0, -0.0002), (0.9999, -0.0065, -0.0097), (0.0095, -0.0308, 0.9995), 1.0), ((0.0001, -0.0001, -0.0002), (1.0, 0.0051, 0.0017), (-0.0016, -0.0009, 1.0), 1.0), ((-0.2094, 0.0689, 0.0631), (0.9964, -0.063, -0.0575), (0.0571, -0.0082, 0.9983), 1.0), ((-0.2037, 0.0669, 0.0668), (0.9962, -0.058, -0.0652), (0.0644, -0.0161, 0.9978), 1.0), ((-0.2094, 0.0689, 0.0631), (0.9964, -0.063, -0.0575), (0.0571, -0.0082, 0.9983), 1.0), ((-0.1904, 0.1408, -0.1652), (-0.3159, -0.2767, 0.9075), (-0.9476, 0.1395, -0.2873), 0.5), ((-0.2043, 0.118, 0.0678), (0.944, -0.2511, -0.2141), (0.2974, 0.3662, 0.8817), 0.5), ((-0.1904, 0.1408, -0.1652), (-0.3159, -0.2767, 0.9075), (-0.9476, 0.1395, -0.2873), 0.5), ((-0.2094, 0.0689, 0.0631), (0.9963, -0.0631, -0.0575), (0.0571, -0.0083, 0.9983), 0.5), ((0.0201, 0.1818, 0.1568), (0.3315, -0.6693, -0.6649), (0.8687, -0.0583, 0.4918), 0.5), ((-0.2094, 0.0689, 0.0631), (0.9963, -0.0631, -0.0575), (0.0571, -0.0083, 0.9983), 0.5), ((-0.2094, 0.0689, 0.0631), (0.9964, -0.063, -0.0575), (0.0571, -0.0082, 0.9983), 0.5), ((-0.1454, 0.1691, 0.0603), (0.7192, -0.6352, -0.2816), (0.6178, 0.399, 0.6776), 0.5), ((-0.2094, 0.0689, 0.0631), (0.9964, -0.063, -0.0575), (0.0571, -0.0082, 0.9983), 0.5), ((-0.2094, 0.0689, 0.0631), (0.9964, -0.063, -0.0575), (0.0571, -0.0082, 0.9983), 0.5), ((-0.1679, 0.0169, 0.1192), (0.7691, -0.0797, 0.6341), (-0.6269, -0.2872, 0.7242), 0.5), ((-0.2094, 0.0689, 0.0631), (0.9964, -0.063, -0.0575), (0.0571, -0.0082, 0.9983), 0.5)]},
        'markers': {'primary_trigger': 'primary trigger', 'left_hand': 'left hand'},
        'ground_point': 'auto',
        'material_names': {'storm_sticky_detonator_default': 'sd_body',
                           'storm_sticky_detonator_hud': 'sd_screen'},
        'shaders': {'sd_body': (BASE + 'sd_body_base.png', None)},
        # the AR's gun shader (the Suppressor's / Boltshot's / Scattershot's, user-approved)
        'template': AR + r'fp\shaders\gun',
        'glow': {},
        # THE SCREEN (the user's screenshot 2026-10-16, a charge out: a dark blue display with a ring for
        # the charge): a static lit blue display for the first build
        'glow_shaders': {'sd_screen': {'rgb': (0.25, 0.75, 1.0), 'additive': True}},
        'extra_models': {'charge': {'from': H4 + SW + r'\projectiles\storm_sticky_detonator_grenade.render_model',
                                    'dir': SD + 'charge',
                                    'material_names': {'storm_sticky_detonator_default': 'sd_body'}}},
        # an own hull (the template's hides the world model, C1): the built JMS's extent (x -0.064..0.109,
        # y +-0.020, z -0.023..0.060 wu) as body + grip
        'collision': {'material': 'metal',
                      'boxes': [((-0.064, -0.02, 0.005), (0.109, 0.02, 0.06)),
                                ((-0.04, -0.012, -0.023), (0.0, 0.012, 0.005))]},
    },

    # FP animations (h1_fp_retarget.py): ROUTE (a), Halo 4's OWN storm_fp_sticky_detonator (Foundry,
    # h4_fp_dump.py -> out\h4_fp: 27 animations, 83 bones = the 80 arm / camera nodes + gun / sight /
    # grenade). fire_1 var1 30 (the shot; the screen opens at frame 10: lens_open), fire_2 18 (the
    # DETONATE press: trigger click at 0, the screen closes at 15), idle 99 / idle_empty 99 (the screen
    # open, a charge out), screen_open (overlay, 1 fr), ammunition (replacement 2 fr: the loaded charge),
    # ready 21 (ready_initial 26), put_away 4, melee_strike_1 36 (primary 4) / _2 37, reload_empty 58,
    # reload_full 51, throw_grenade 44, moving 20 / look 9 (overlays), posing var1 124 / var2 99,
    # acceleration_screens, sprint / jump / land / fall: no Halo 1 state.
    # APPROXIMATION A in first person: Halo 1's fire-1 = fire_1 + fire_2 (the shot, the screen up, the
    # press at 1.0 s -- ~ where a 24 wu/s charge sticks at 10 wu and bursts 0.5 s later -- the screen
    # down); a 1-round magazine reloads after every shot (reload-empty)
    'retarget': {
        'graph': H4 + SFP + '.model_animation_graph',
        'render_model': H4 + SW + r'\storm_sticky_detonator.render_model',
        'nodes': {n[2:]: 'frame ' + n.replace('_', ' ') for n in GUN_NODES},
        'drop_nodes': tuple(DROP),
        'h1_dir': r'weapons\sticky detonator\fp',
        'h1_model': r'weapons\sticky detonator\fp\fp',
        'align': 'same_space',
        'anims': {
            'first_person:idle': 'first-person idle',
            'first_person:posing:var1': 'first-person posing',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:melee_strike_1': 'first-person melee',
            'first_person:moving': 'first-person moving',
            'first_person:look': 'first-person overlays',
            'first_person:throw_grenade': 'first-person throw-grenade',
            'first_person:reload_empty': 'first-person reload-empty',
            'first_person:reload_full': 'first-person reload-full',
        },
        'sequence': {'first-person fire-1': ['first_person:fire_1:var1', 'first_person:fire_2']},
        'view_offset': (0.0, 0.0, 0.0),
    },

    # Halo 4's own sounds (h1_port_sounds.py sticky_detonator, `bank` 'halo4'). The player bank
    # sticky_detonator_player (the weapon's Player sound bank; the FP frame_event_list for the cues), the
    # projectile's proj_sticky_detonator. HIRC (2026-10-16): fire = 10 layers -- random [0-3], [4, 5],
    # [6, 7] (4-5 s tails), 8 (a 30 ms haptic click: dropped), [9-11], 12, 13, [14-16], [17, 18], 19.
    # BOOT 1 (user: 'the firing sound is the wrong kind of sound'; of seven candidate mixes the user picked
    # the player mix WITHOUT 12 / 13 -- the two loud short layers, -5.6 / -19.5 dB, the same recordings as
    # the nonplayer event's 9 / 10);
    # trigger (the detonate press) = random [0-2] + 3; mech_reload_a = [0, 1] + [2, 3], _b / _c / _d
    # random of 2 (reload_empty / _full: a @3, b @21, c @36, d @45); lens_open / _close random of 2
    # (fire_1 @10 / fire_2 @15; ready @0); switchto_mech random of 2 (ready @0); idle_player a @0, b @60,
    # c @88 (posing var1). Levels = the active RMS of the stock Halo 1 sound each stands in for
    # (h1_stock_sound_levels 2026-10-16): pistol fire -12.8, dryfire -15.3, pistol_ready -15.2,
    # pistol_reload -19.0, pistol_melee -19.8, pistol_posing -26.5, frag expl -7.2..-8.3, plasma
    # projectile -25.0, pistol drop -28.8
    'sounds': {
        'catalog': 'Sticky Detonator',
        'bank': 'halo4',
        'wwise_bank': 'sticky_detonator_player',
        'dir': B.join(['sound', 'weapons', 'sticky_detonator_port']),
        'sounds': {
            'sd_fire': (['play_weapons_storm_sticky_detonator_player_fire:0,1,2,3',
                         'play_weapons_storm_sticky_detonator_player_fire:4,5',
                         'play_weapons_storm_sticky_detonator_player_fire:6,7',
                         'play_weapons_storm_sticky_detonator_player_fire:9,10,11',
                         'play_weapons_storm_sticky_detonator_player_fire:14,15,16',
                         'play_weapons_storm_sticky_detonator_player_fire:17,18',
                         'play_weapons_storm_sticky_detonator_player_fire:19'],
                        # BOOT 2 (user: 'could use a bit more oomph'; of three files the user picked
                        # BOTH +6 dB below 150 Hz (`low_shelf`) and +3 dB) -> -12.8 + 3
                        # BOOT 3 (user: 'unchanged'): the +3 dB went into the soft limiter (-13.8 ->
                        # -12.2 active, peaks at the ceiling) -> the stock level again and the TAG's gain
                        # modifier 0.5 -> 1.0 (+6 dB above the PCM ceiling, `gain` below)
                        'sound\\sfx\\weapons\\pistol\\fire', -12.8),
            # fire-1's own cues (fire_1 + fire_2): the screen up @10, the detonate press @30, down @45
            'sd_fire_anim': (['play_wea_sticky_det_mech_lens_open:0,1',
                              'play_weapons_storm_sticky_detonator_player_trigger:0,1,2',
                              'play_weapons_storm_sticky_detonator_player_trigger:3',
                              'play_wea_sticky_det_mech_lens_close:0,1'],
                             'sound\\sfx\\weapons\\weapon_anims\\pistol_ready', -15.2),
            'sd_dryfire': (['play_weapons_storm_sticky_detonator_player_dry_fire'],
                           'sound\\sfx\\weapons\\pistol\\dryfire', -15.3),
            'sd_ready': (['play_wea_sticky_det_switchto_mech_player:0,1',
                          'play_wea_sticky_det_mech_lens_open:0,1'],
                         'sound\\sfx\\weapons\\weapon_anims\\pistol_ready', -15.2),
            'sd_melee': (['play_wea_sticky_det_foley_melee_1_player'],
                         'sound\\sfx\\weapons\\weapon_anims\\pistol_melee', -19.8),
            'sd_reload': (['play_wea_sticky_det_mech_reload_a:0,1',
                           'play_wea_sticky_det_mech_reload_a:2,3',
                           'play_wea_sticky_det_mech_reload_b:0,1',
                           'play_wea_sticky_det_mech_reload_c:0,1',
                           'play_wea_sticky_det_mech_reload_d:0,1'],
                          'sound\\sfx\\weapons\\weapon_anims\\pistol_reload', -19.0),
            'sd_reload_balanced': (['play_wea_sticky_det_mech_reload_a:0,1',
                                    'play_wea_sticky_det_mech_reload_a:2,3',
                                    'play_wea_sticky_det_mech_reload_b:0,1',
                                    'play_wea_sticky_det_mech_reload_c:0,1',
                                    'play_wea_sticky_det_mech_reload_d:0,1'],
                                   'sound\\sfx\\weapons\\weapon_anims\\pistol_reload', -19.0),
            'sd_pose': (['play_wea_sticky_det_idle_player_a', 'play_wea_sticky_det_idle_player_b',
                         'play_wea_sticky_det_idle_player_c'],
                        'sound\\sfx\\weapons\\weapon_anims\\pistol_posing', -26.5),
            # the burst: the projectile bank's NONPLAYER event (no player one ships): play [0-2], a STOP
            # on [3-5] (the flight loop), play [6-8], play [9-11] (no media found: dropped)
            'sd_explode': (['play_proj_storm_sticky_detonator_nonplayer_explosion@proj_sticky_detonator:0,1,2',
                            'play_proj_storm_sticky_detonator_nonplayer_explosion@proj_sticky_detonator:6,7,8'],
                           'sound\\sfx\\weapons\\frag grenade\\expl', -7.8),
            'sd_stick': (['play_stick_det_proj_attach@proj_sticky_detonator'],
                         'sound\\sfx\\weapons\\plasma grenade\\plasma_projectile', -15.0),
            'sd_drop': (['play_wea_drop_pistol_sticky_det_nonplayer'],
                        'sound\\sfx\\impulse\\weapon_drops\\pistol_impact', -28.8),
        },
        'low_shelf': {'sd_fire': (150.0, 6.0)},
        'gain': {'sd_fire': 1.0},
        # the BALANCED reload's sound (the patcher retimes the reload by the catalog's `anims` and swaps
        # it in: catalog anim_sounds; the Boltshot's recipe)
        'stretch': {'sd_reload_balanced': 62.5 / 59.0},
        'offsets': {'sd_fire_anim': [10 / 30.0, 30 / 30.0, 30 / 30.0, 45 / 30.0],
                    'sd_ready': [0.0, 0.0],
                    'sd_reload': [3 / 30.0, 3 / 30.0, 21 / 30.0, 36 / 30.0, 45 / 30.0],
                    'sd_reload_balanced': [3 / 30.0, 3 / 30.0, 21 / 30.0, 36 / 30.0, 45 / 30.0],
                    'sd_pose': [0.0, 60 / 30.0, 88 / 30.0]},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only sticky_detonator) on a COPY of the Halo 1 PISTOL firing the
    # CHARGE above. DEFAULT = HALO 4's OWN NUMBERS; the ratio values are the balance rows
    'pickable': {
        'weapon': SD + 'sticky detonator',
        'template': PISTOL + 'pistol',
        'world_model': SD + 'sticky detonator',
        # ONE model tag for world AND first person (the 32 MiB model buffer, H1_PORT_PLAN 0.1)
        'fp_model': SD + 'sticky detonator',
        'fp_anims': SD + 'fp' + B + 'fp',
        'label': 'sd',
        'teach': ('sd', 'hp'),
        'keys': {'first-person melee': 4},          # Halo 4 melee_strike_1 primary keyframe 4
        'sounds': {'first-person ready': SND + 'sd_ready',
                   'first-person posing': SND + 'sd_pose',
                   'first-person melee': SND + 'sd_melee',
                   'first-person fire-1': SND + 'sd_fire_anim',
                   'first-person reload-empty': SND + 'sd_reload',
                   'first-person reload-full': SND + 'sd_reload'},
        'bullet': dict(CHARGE, triggers=[0]),
        # Halo 4: recovery 1.0 s (rounds per second 30 = recovery-limited) = 1/s
        'trigger': {'rounds_per_second': (1.0, 1.0), 'acceleration_time': 0.0,
                    'deceleration_time': 0.0},
        # Halo 4: minimum error 0.15, error angle 0 -> 0.4
        'error_deg': {'minimum_error': 0.15, 'error_angle': (0.0, 0.4)},
        # Halo 4: 1 loaded, 4 at pickup, 6 most, 1 reloaded. Reload: Halo 4 none (reload_empty 58 fr =
        # 1.93 s) in the H1 pistol's shape (2.17 tag over its 2.23 s animation)
        'magazine': {'rounds_loaded_maximum': 1, 'rounds_reloaded': 1,
                     'rounds_total_initial': 4, 'rounds_total_maximum': 6,
                     'reload_time': 58 / 30.0 * 2.17 / 2.23},
        # Halo 4 aim assist (the mode block, = the weapon's): 4/15 8/15; no zoom
        'aiming': {'autoaim_angle': 4.0, 'autoaim_range': 15.0,
                   'magnetism_angle': 8.0, 'magnetism_range': 15.0},
        'fields': {
            'weap_attrs.aiming.zoom_levels': 0,
            # STEP 4b list 2 (H4 Sticky Detonator vs H4 rocket onto the H1 pistol): camo ding 0.65 x 0.75/1
            # = 0.4875, illumination recovery 0.1 x 0.1/0.2 = 0.05
            'weap_attrs.interface.active_camo_ding': 0.65 * 0.75 / 1.0,
            'weap_attrs.triggers.0.misc.illumination_recovery_time': 0.1 * 0.1 / 0.2,
            'weap_attrs.interface.zoom_in_sound.filepath': '',
            'weap_attrs.interface.zoom_out_sound.filepath': '',
            'item_attrs.collision_sound.filepath': SND + 'sd_drop',
            'obje_attrs.collision_model.filepath': SD + 'sticky detonator',
            # STEP 6 (user, boot 1, 2026-10-16: 'plasma grenades'): the yardstick's own item -- a plasma
            # grenade picked up gives one charge (the GL's frag precedent: it gives the grenade too). The
            # template's `pistol ammo` would have given 120
            'weap_attrs.magazines.0.magazine_items.0.equipment.filepath':
                r'weapons\plasma grenade\plasma grenade',
            'weap_attrs.magazines.0.magazine_items.0.rounds': 1,
        },
        # THE MUZZLE-FLASH RULE (check 10, before boot 1). Halo 4's FIRST-PERSON particles (fx\sgl_firing,
        # camera mode 'only in first person', all at primary_trigger, on-axis): muzzle_flash_round (bounding
        # 0.035 wu) + glow_soft 0.080 + fiery sparks (missile_pod spark_fiery, 0.78: a spray) + muzzle smoke
        # 0.27; a cheap light (sgl_firing). The pistol's (h1_effect_particles): two SIDE flashes 0.035-0.05
        # at +-0.023 wu angled 65 deg, a centre 0.045-0.056, smoke 26-35 x 0.08-0.135, a casing -> side
        # flashes dropped (`drop_off_axis`), the centre kept x1 (~ Halo 4's round + glow), the smoke KEPT
        # (Halo 4 smokes in first person too), the casing and its eject sound dropped (a grenade
        # launcher: none), tinted Halo 4's orange. Not reproduced: the spark spray (no Halo 1 pistol part)
        'sound_effects': {
            'firing_effect': (PISTOL + 'effects\\fire bullet', SD + 'effects\\fire charge',
                              {r'sound\sfx\weapons\pistol\fire': SND + 'sd_fire'},
                              # BOOT 1 (user: 'muzzle flash could be a bit more intense'): the centre
                              # flash x1.5 (the Boltshot's) and living x1.6 (0.12 s, the Boltshot's boot 5)
                              {'match': 'flash', 'drop_off_axis': 0.012, 'scale': 1.5,
                               'own_particles': {'out': SD + 'effects' + B + 'particles' + B + 'charge ',
                                                 'lifespan': 1.6, 'fade_out': 0.04},
                               'drop_particles': ('casing',),
                               'drop_parts': [r'sound\sfx\weapons\pistol\eject'],
                               'tint': (1.0,) + ORANGE, 'tint_match': ('flash',)}),
            'empty_effect': (PISTOL + 'effects\\empty', SD + 'effects\\empty',
                             {r'sound\sfx\weapons\pistol\dryfire': SND + 'sd_dryfire'})},
        'melee': (PISTOL + 'melee', SD + 'melee'),
        'melee_response': PISTOL + 'melee_response',
        'messages': ('Picked up a sticky detonator', 'Picked up %d rounds for sticky detonator'),
        'extra_sounds': [SND + 'sd_reload_balanced'],
        'icon': 'sticky detonator',
        # the PISTOL's HUD; the crosshair from Halo 4's CUI (sticky_launcher.cui_screen, 3 art px a unit):
        # `lt` = img_circle 64 x 64 units at (-32, -34) -- the open-bottomed ring, centre (0, -2); the
        # lines = sticky_lines 21 x 31 at (-11, -2) -- the bar + two brackets below the centre, centre
        # (-0.5, 13.5); both at opacity 1 at rest (the user's idle screenshot 2026-10-16). The armed
        # look (a side bracket + the charge icon) is not reproduced: Halo 1's crosshair is static and the
        # charge bursts 0.5 s after sticking. SIZE from the screenshot (1080p): the ring (~44 units) ~62 px
        # across = 1.41 px a unit (the Boltshot's 1.5). SUPERSAMPLE recipe (memory h1-reticle-supersample;
        # sheet px a unit = 123/97 x scale x F): F 2, the 34-unit half-span at scale 2.8 = 241 of the 256
        # half-cell (a ~15 px margin); overlay = 1.41 / (123/97 x 2.8 x 2 x 0.75) = 0.264
        'hud': {'donor': PISTOL + 'pistol', 'out': SD + 'sticky detonator',
                'reticle': (H4 + STK + 'img_circle', 0, 'sticky detonator'),
                'reticle_xform': {'offset': (0.0, -2.0)},
                'reticle_layers': [(H4 + STK + 'sticky_lines', 0, 1.0, {'offset': (-0.5, 13.5)})],
                'reticle_split': 100,
                'reticle_min_width': 2,
                'reticle_supersample': 2,
                'reticle_scale': 2.8, 'reticle_overlay': 1.41 / (123 / 97.0 * 2.8 * 2 * 0.75),
                'flash_base': 12,
                # BOOT 1 (user: 'low ammo warning is active with 6 remaining, on the ammo total'): the
                # pistol's total-ammo flash cutoff 13 -> the rocket launcher's 1
                'fields': {'flash_cutoffs.total_ammo_cutoff': 1},
                'ammo_meter': {'sizes': (1,), 'base': SD + 'bitmaps\\sticky_detonator_ammo'}},
        'palette_levels': LEVELS,
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py sticky_detonator). DEFAULT = Halo 4's own
    # numbers in the tags; BALANCED = the PLASMA GRENADE ratio by the stuck kill for the burst, the ROCKET
    # ratio for the holes (step 4a, user). Assembly Halo1 units: angles in degrees, velocity in wu per TICK
    'catalog': {
        'entry': {
            'weapon': 'Sticky Detonator', 'source': 'Halo 4', 'donor': 'Pistol', 'default_on': False,
            'desc': "Halo 4's Sticky Detonator: its model, first-person animations, sounds and numbers. "
                    "A one-shot launcher whose charge sticks to whatever it hits -- walls, floors, "
                    "enemies -- and explodes half a second later; on a Jackal's shield it explodes "
                    "at once. Halo 1 has no remote detonation: the fuse replaces the second trigger "
                    "press. Plasma grenades top up its charges.",
            'balance_desc': "Measured against the Plasma Grenade stuck to its target, with the Rocket "
                            "Launcher for the rest: a 346 burst over 3.4 m, one charge every 2.5 s, "
                            "a faster, shorter arc, up to 8 charges and Halo 1-style aim assist.",
            # step 9: the balanced reload = the H1 rocket's 125 fr x 58/116 = 62.5 over the built 59 =
            # x1.059; swap (ready + put-away, ONE multiplier): the rocket's ready 22 x 21/26 = 17.8 over
            # the built 22 = x0.808
            'anims': {'reload': 62.5 / 59.0, 'swap': 22 * 21 / 26.0 / 22.0},
            'anim_sounds': {'reload': [
                {'mult': 62.5 / 59.0, 'from': SND + 'sd_reload', 'to': SND + 'sd_reload_balanced'}]},
            'balance': [
                # the burst: 505 x 240/350 (the stuck kill), lower 80 x 240/350; radius 0.4 x 0.5/0.3,
                # 2.5 x 2.0/1.45; AOE core 0.4 x 0.4/0.25 (4b list 2)
                row('jpt!', SD + 'explosion', 'Damage Lower Bound', 54.86, 80.0, 'Charge Damage'),
                row('jpt!', SD + 'explosion', 'Damage Upper Bound', 346.29, 505.0, 'Charge Damage'),
                row('jpt!', SD + 'explosion', 'Damage Upper Bound Max', 346.29, 505.0, 'Charge Damage'),
                row('jpt!', SD + 'explosion', 'Radius', 0.667, 0.4, 'Charge Damage'),
                row('jpt!', SD + 'explosion', 'Radius Max', 3.448, 2.5, 'Charge Damage'),
                row('jpt!', SD + 'explosion', 'AOE Core Radius', 0.64, 0.4, 'Charge Damage'),
                # the RL ratio: 1.0 s x 2.0/0.8 = 2.5 s (0.4/s); 6 x 8/6 = 8 most (4 x 4/4 = 4 kept)
                row('weap', SD + 'sticky detonator', 'Rounds Per Second', 0.4, 1.0, 'More Shooting', block='Triggers'),
                row('weap', SD + 'sticky detonator', 'Rounds Per Second Max', 0.4, 1.0, 'More Shooting', block='Triggers'),
                row('weap', SD + 'sticky detonator', 'Rounds Total Maximum', 8.0, 6.0, 'Magazine', block='Magazines'),
                # flight: 24 x 12/10 = 28.8, 10 x 10/20 = 5 wu/s; range 20 x 128/175 = 14.6
                row('proj', SD + 'charge', 'Initial Velocity', 28.8 / 30.0, 24.0 / 30.0, 'Projectile'),
                row('proj', SD + 'charge', 'Final Velocity', 5.0 / 30.0, 10.0 / 30.0, 'Projectile'),
                row('proj', SD + 'charge', 'Maximum Range', 14.6, 20.0, 'Projectile'),
                # aim: 0 x 4/5, 35 x 15/60; 12 x 8/10, 35 x 15/25
                # BALANCED BOOT (user: 'aim assist never activates, the crosshair is never red'): the
                # rocket's 0 deg switched it off -> the angle KEPT Halo 4's 4 (the Plasma Launcher's rule:
                # a zero on one side is not a ratio), the ranges by the ratio (user)
                row('weap', SD + 'sticky detonator', 'Autoaim Angle', 4.0, 4.0, 'Autoaim'),
                row('weap', SD + 'sticky detonator', 'Autoaim Range', 8.75, 15.0, 'Autoaim'),
                row('weap', SD + 'sticky detonator', 'Magnetism Angle', 9.6, 8.0, 'Magnetism'),
                row('weap', SD + 'sticky detonator', 'Magnetism Range', 21.0, 15.0, 'Magnetism'),
            ]},
    },

    # step 4b (port_field_audit.py --port sticky_detonator): the source pair (Halo 4's Sticky Detonator
    # _pve vs its yardsticks: the rocket launcher for the weapon -- the holes --, the plasma grenade for
    # the charge and its burst) against the target pair (the H1 port vs its templates: the pistol, the
    # plasma grenade's projectile, the plasma grenade's explosion)
    'field_audit': {
        'source_kit': 'H4EK',
        'source': {'weapon': (SW + r'\storm_sticky_detonator_pve.weapon',
                              r'objects\weapons\support_high\storm_rocket_launcher\storm_rocket_launcher.weapon'),
                   'projectile': (SW + r'\projectiles\storm_sticky_detonator_grenade_pve.projectile',
                                  r'objects\weapons\grenade\storm_plasma_grenade\storm_plasma_grenade.projectile'),
                   'damage_effect': (SW + r'\projectiles\damage_effects\storm_sticky_detonator_grenade_explosion_pve.damage_effect',
                                     r'objects\weapons\grenade\storm_plasma_grenade\damage_effects\storm_plasma_grenade_explosion.damage_effect')},
        'target': {'weapon': (SD + 'sticky detonator.weapon', PISTOL + 'pistol.weapon'),
                   'projectile': (SD + 'charge.projectile', PG + 'plasma grenade.projectile'),
                   'damage_effect': (SD + 'explosion.damage_effect', PG + 'explosion.damage_effect')}},

    # the dry test: b30 (this session's level, parallel pair 5)
    'test': {'level': 'b30', 'rounds': (1, 6), 'grunt': None, 'elite': None},
})
