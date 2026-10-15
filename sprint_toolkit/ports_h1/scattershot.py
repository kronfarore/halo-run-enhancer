r"""Scattershot (Halo 4, wave C5): a Forerunner SHELL-BY-SHELL pellet gun whose shards RICOCHET, on a copy of
the Halo 1 SHOTGUN (also the yardstick, step 4a user 2026-10-15: its magazine, shell reload, HUD, melee,
two-handed pose). The Halo 4 route is the Storm Rifle's (storm_rifle.py: `h4:` paths, Foundry FP decode +
arm re-solve on the shared storm_fp skeleton); the pellet magazine shape is brute_mauler.py's, the ricochet
the Spike Rifle's / Needle Rifle's (`reflect` per Halo 1 material), the supercombine the Needle Rifle's.

HALO 4 (H4EK 2026-10-15, h3_weapon_values --kit h4 + the export): ONE trigger, latch; recovery 0.5 s; the
BARREL fires 6 shards (projectiles per shot 6, distribution point, error 4 -> 7 deg, error decel 0.25 s);
a shard 12 bullet_slow (no falloff), 75 -> 10 wu/s over its first 2-3 wu (acceleration range), a 0.15-0.5
s detonation timer started at the muzzle -> it dies at ~3.2-6.7 wu (range 26 is only a cap); it BOUNCES off
every world surface and Hunter armour (its newer `material response` table, step 4b) and sticks in every
other unit; 6 stuck in one target within 0.1 s super-detonate (250 attached + 40 area). Magazine 5 (15 / 20), ONE round reloaded at a time (FP reload_enter 14, reload_
continue_empty 21 a shell, chamber_1 39 after an empty one; no reload exit with rounds left), aim (mode
block) 6/7 12/6.5, strike_melee (shared).

THE APPROXIMATIONS (step 4a, user): Halo 1 slows a projectile LINEARLY over its whole maximum range with the
final velocity a floor (B4's probe) -- so the range is the death distance's top (6.7 wu: 75 -> 10 over it)
and the timer is RE-FITTED to Halo 4's death window: d(t) = 75/9.7 (1 - e^-9.7t) gives 3.2 wu at 0.055 s,
6.7 at 0.208 s -> timer 0.055 - 0.21 s (Halo 4: 3.2 - 6.7 wu over 0.15 - 0.5 s, mostly at 10 wu/s). Not
reproduced: the 10 wu/s drift of a late shard (Halo 1's shard is faster there), the super detonation's 0.1 s
window (Halo 1 counts stuck shards), Halo 4's finer materials."""
from ._common import B, reserved, row

H4 = 'h4:'                                          # an H4EK path (h4_tags)
SW = r'objects\weapons\rifle\storm_spread_gun'
SFP = r'objects\characters\storm_fp\weapons\rifle\fp_spread_gun\storm_fp_spread_gun'
SPR = r'ui\hud\weapons\forerunner\forerunner_spread_gun\bitmap' + B     # Halo 4's crosshair art (CUI)
SAM = r'ui\hud\weapons\forerunner\spread_gun\bitmap' + B                 # Halo 4's round pips
# the base maps: RGB = Halo 4's colour map x the material's albedo_tint, A = the control map's R
# (specular) -- h4_standin_diffuse.py `color` mode (the Boltshot's, C3), in the port's own data folder:
#   python h4_standin_diffuse.py <SBM>storm_spread_gun_control.bitmap <BASE>ss_body_base.png
#          --mode color --color <SBM>storm_spread_gun_diff.bitmap --tint 0.827   (metal: 0.634)
BASE = r'F:\SteamLibrary\steamapps\common\HCEEK\data\weapons\scattershot\source' + B
SS = 'weapons\\scattershot\\'
SND = 'sound\\weapons\\scattershot_port\\'
SG = 'weapons\\shotgun\\'
AR = 'weapons\\assault rifle\\'
N = 'weapons\\needler\\'
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']
# Forerunner orange (boot 1: the user's Halo 4 screenshots, 2026-10-15; the bars' si_color 1, 0.416, 0.2
# x5): the bars at rest (~250 / 120 / 20) = ORANGE, on a shot (~255 / 170 / 40, toward white in the cores)
# = FLASH, the shards' red-orange streaks with yellow heads = SHARD
ORANGE = (1.0, 0.47, 0.08)
FLASH = (1.0, 0.68, 0.16)
SHARD = (1.0, 0.36, 0.16)

# the Storm Rifle's DROP list: every storm_fp graph shares the skeleton (checked 2026-10-15: this graph's
# 91 bones = the 80 arm / camera nodes + the gun's 11)
from .storm_rifle import DROP  # noqa: E402

# the render model's 11 nodes, all animated by the FP graph
GUN_NODES = ('b_gun', 'b_end_top', 'b_end', 'b_end_low', 'b_cartridge', 'b_base_float', 'b_base_low',
             'b_mid', 'b_end_float', 'b_mid_top', 'b_base_top')

# Halo 1 material indices (proj material responses) mapped onto HALO 4's shard table. STEP 4b (2026-10-15):
# the shard carries TWO tables -- `old material responses` (16 rows: fizzles, 90-95 % bounces at 0-75/85
# deg, a 50 % soft bounce, Elite shields detonate -- what step 4a laid out) and the NEWER `material
# response` block (4 rows), the one Halo 4 reads (Halo 4's own shotgun bullet carries 10 rows there):
#   hard_metal_thick_for         bounce, chance 1, 0-90 deg, 0-100 wu/s, frictions 0.1 / 0.1
#   hard_metal_solid_cov_hunter  bounce, the same (Hunter armour: shards bounce off Hunters)
#   default_material             bounce, the same, NEVER against units  -> every world surface
#   default_material             attach, ONLY against units             -> every other unit, shields too
# -> world (incl. water / leaves / glass: no row of their own) = Halo 1 default `reflect`, frictions 0.1 /
# 0.1, no noise; Hunter armour / shield = reflect; every other unit material = attach
WORLD = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 27, 28, 29, 31]
HUNTER = [12, 32]
UNITS = [11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 30]

PORT = reserved(
    order=30, wave='C5', name='Scattershot', source='Halo 4',
    messages=(93, 94), icon=50, reticle=39, label='ss', teach_from='sg',
    sound_dir='sound\\weapons\\scattershot_port', weapon_dir='weapons\\scattershot',
    yardstick={
        # step 4a (user, 2026-10-15; h3_weapon_values --kit h4 storm_spread_gun / storm_shotgun /
        # storm_energy_sword + the shard export + h1_role_compare.py scattershot)
        'pick': 'Shotgun',
        'reason': ("user, step 4a 2026-10-15: Halo 4's shotgun is the same family (bullet_slow pellets, "
                   "shell-by-shell magazine, strike_melee): H1 value = H1 shotgun x Scattershot / H4 "
                   "shotgun; keeps Halo 4's relation (144 vs 157.5 dps -> 295 vs 322). The sword ratio "
                   "maps damage only (87 dps). Kept Halo 4's own in BOTH versions (no counterpart): the "
                   "shard's speed + life (75 -> 10 wu/s, timer 0.15-0.5 s from the muzzle = dies at "
                   "~3.2-6.7 wu; the ratio's 22 wu/s would crawl), the ricochet responses, and the SUPER "
                   "DETONATION (user: 'port it'): 6 stuck shards -> 250 (Halo 4's attached super "
                   "detonation), through h1_supercombine_count's per-projectile count 6"),
        # Halo 4 (H4EK 2026-10-15): the 6 shards are the BARREL's (projectiles per shot 6, error 4 -> 7
        # deg, distribution point; the shard has NO conical spread -- unlike the Mauler / Boltshot),
        # 12 a shard bullet_slow, no falloff (flag 3 off; air damage range inert), recovery 0.5 s,
        # 5 (15 / 20) shell by shell (FP enter 14, continue_empty 21, chamber 39 fr), aim mode 6/7
        # 12/6.5, strike_melee 70. Shard flags 0x20020805: oriented along velocity, detonation max
        # time if attached, AI minor tracking threat, disable instantaneous first tick, no super
        # combine across bursts. Responses: hard metal / terrain fizzle, bounce 90-95 % at 0-75/85
        # deg (perp friction 0.7, noise 4); energy_shield_thick_cov bounce (noise 20); energy_shield
        # _thin impact (detonate); default_material attach, bounce 50 % under 55 deg never against
        # units; liquids / fences / plants overpenetrate. Super: 6 within 0.1 s; 40 (10 lower) area
        # / 250 (35 lower) attached, high explosive explosion_small, radius 0.375 -> 1.25.
        # H4 shotgun: 15 x 10.5 (lower 3 over 1.5 -> 3.75), 5 x 3 grid 3 deg, 1.0 s, 6 (18 / 24),
        # 480 wu/s, range 6.5, aim 6/5.5 12/5.5, FP enter 14 / continue 16 / chamber 34.
        # H1 shotgun: 15 x 18..25 (lower 8 over 1.5 -> 3), 1/s, 12 (24 / 60), 0.4 s a shell, error
        # 10, 140 -> 100 wu/s, range 40, aim 6/15 12/15, melee 55.
        # DEFAULT = Halo 4's own; these are the BALANCED rows (shotgun ratio):
        'balanced': {
            'pellets': 6,                    # 15 x 6/15
            'damage': 24.57,                 # 21.5 x 12/10.5 (upper 18..25 -> 20.57..28.57)
            'falloff': None,                 # Halo 4 has none (lower = upper)
            'fire_recovery_s': 0.5,          # 1.0 x 0.5/1.0
            'magazine': 10,                  # 12 x 5/6
            'rounds_total_initial': 20,      # 24 x 15/18
            'rounds_total_maximum': 50,      # 60 x 20/24
            'shell_s': 0.525,                # 0.4 x 21/16, shell by shell (both)
            'error_deg': (13.3, 23.3),       # 10 x 4/3, 10 x 7/3 (random cone both)
            'velocity': (75.0, 10.0),        # Halo 4's own (ratio degenerate)
            'timer': (0.15, 0.5),            # Halo 4's own (Halo 1: re-fitted, see the docstring)
            'aim': (6.0, 19.1, 12.0, 17.7),  # 6 x 6/6, 15 x 7/5.5; 12 x 12/12, 15 x 6.5/5.5
            'melee': 'x1',                   # strike_melee both: 55
            'super': (6, 250.0)},            # Halo 4's own (no shotgun counterpart)
        'measured': 'h1_role_compare.py scattershot',
        'not_reproduced': ("the deceleration 75 -> 10 over 2-3 wu (Halo 1 slows linearly over the whole "
                           "range: the timer re-fitted to the death window), 'detonation max time if "
                           "attached' kept as Halo 1's flag, the super detonation's 0.1 s window (Halo 1 "
                           "counts stuck shards only), Halo 4's finer material split folded onto Halo 1's "
                           "33"),
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\storm_spread_gun\\storm_spread_gun',
            'provisional': 'Shotgun',
            'alternatives': ['Energy Blade'],
            'direct': None,
            'peers': ['Shotgun', 'Energy Blade', 'Flamethrower'],
            'why': 'magazine 5, 6 projectiles per shot, close range',
            'lacks': 'ricocheting shards'}},
    # step 11: Halo 4's ai\generic Scattershot entry (m020, verified 2026-10-07) over a Halo 1 SHOTGUN
    # carrier ('ss' has no carrier). Halo 1's shotgun carriers (h1_weapon_carriers, 2026-10-15): Flood combat
    # Elite / human (WDM 0.15; their actor ALREADY has always_charge_in_attacking_mode), Marine plain /
    # anchor and armoured Marine major (0.6) -- no Covenant one; the Mauler's split. PROVISIONAL (the user
    # picks): the Mauler's pinned donor, the Flood combat Elite, base 0.15. ARMED WDM RULE: 0.15 x shotgun
    # 322 / Scattershot dps -- default 6 x 12 x 2 = 144 (0.335), balanced 6 x 24.57 x 2 = 295 (0.164).
    # Short range (6.7 wu: the AI judges reach by the projectile's maximum range): Armed slots keep their
    # own species' actor (no charge) -- the Mauler (range 8) passed its Armed boot without one; the
    # enhancer's `actor_flags` charge (the Gravity Hammer's) if the Armed boot shows them hanging back
    firing_profile={'mode': 'source', 'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map',
                    'from_weapon': 'objects\\weapons\\rifle\\storm_spread_gun\\storm_spread_gun',
                    'donor_weapon': 'weapons\\shotgun\\shotgun',
                    'donor_variant': 'characters\\floodcombat elite\\floodcombat elite shotgun',
                    'wdm_rule': {'base': 0.15, 'yardstick_dps': 322.0, 'port_dps': 144.0,
                                 'balanced_port_dps': 295.0}},
)

PORT.update({
    'status': 'in progress',
    # BORROWED sounds kept ON PURPOSE (port_sound_refs prints these as KEEP)
    'sound_keeps': {r'sound\sfx\weapons\assault rifle\flashlight': "the flashlight rule: the game's own",
                    r'sound\sfx\weapons\weapon_pickup_ammo\shotgun_ammo':
                        "Halo 4's ammo pickup tag (ammo_pickup_generic) is empty (the Boltshot's finding)"},

    # geometry + look (h1_h3_weapon_model.py; Halo 4 through h4_tags). Halo 4's ONE render model for world
    # AND first person: 11 nodes (b_gun root); two regions with data, 'default' (mesh 0: 1128 verts) and
    # 'knight_arm' (mesh 1: 10814 verts -- the Suppressor's split). Materials (H4EK .material; the m020
    # cache names the same diff / normal / control / cube for the body): mainbody + metal
    # (srf_char_blinn_reflection, the colour map x albedo tint 0.827 / 0.634), energy_bar
    # (srf_constant_illumscroll: a scrolling gradient, si 1, 0.416, 0.2 x5 -- the glow). Markers:
    # primary_trigger 0.258 / 0 / 0.039 (the muzzle: the shards' spawn), secondary_trigger x6 (the
    # muzzle rim), vent x2, rails / slides (the firing sparkles), left_hand, ground_point
    'model': {
        'dir': r'weapons\scattershot',
        'world': H4 + SW + r'\storm_spread_gun.render_model',
        'fp': H4 + SW + r'\storm_spread_gun.render_model',
        'world_name': 'scattershot',
        # DECIMATION (h1_decimate; THE MODEL BUFFER BUDGET, parallel pair 4: <= 0.6 MiB): 40 / 50 / 60 lost
        # the long side panel's lines (merged rails, smeared shading), 70 keeps the outline (max error 1.12
        # mm; the soft shading streak shows at 80 too) -> 15452 -> 10815 triangles, 0.731 -> 0.536 MiB
        'decimate': {'keep': 70.0, 'protect': 1.0, 'views': [((-0.0974, 0.0455, 0.0962), (0.9999, 0.002, -0.0165), (0.0165, 0.0012, 0.9999), 1.0), ((-0.0987, 0.0448, 0.0959), (1.0, 0.002, -0.0028), (0.0028, -0.0065, 1.0), 1.0), ((-0.0974, 0.0455, 0.0962), (0.9999, 0.002, -0.0165), (0.0165, 0.0012, 0.9999), 1.0), ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), 1.0), ((0.0, 0.0, 0.0), (1.0, -0.0062, -0.0038), (0.0037, -0.0134, 0.9999), 1.0), ((0.0, 0.0, 0.0), (1.0, 0.0027, 0.0031), (-0.0031, 0.0043, 1.0), 1.0), ((-0.0974, 0.0455, 0.0962), (0.9999, 0.002, -0.0165), (0.0165, 0.0012, 0.9999), 1.0), ((-0.0398, 0.0418, 0.0953), (0.9768, -0.0165, -0.2136), (0.2138, 0.0093, 0.9768), 1.0), ((-0.0974, 0.0455, 0.0962), (0.9999, 0.002, -0.0165), (0.0165, 0.0012, 0.9999), 1.0), ((-0.174, 0.0478, 0.1045), (0.5639, -0.2061, 0.7997), (-0.8169, 0.0032, 0.5768), 0.5), ((-0.1125, 0.0578, 0.0851), (0.994, -0.0476, -0.0989), (0.1069, 0.2168, 0.9703), 0.5), ((-0.174, 0.0478, 0.1045), (0.5639, -0.2061, 0.7997), (-0.8169, 0.0032, 0.5768), 0.5), ((-0.0594, 0.0397, 0.1366), (0.9758, -0.062, -0.2095), (0.1951, -0.1848, 0.9632), 0.5), ((-0.0709, 0.044, 0.1268), (0.9895, -0.0686, -0.1273), (0.1161, -0.1479, 0.9822), 0.5), ((-0.0594, 0.0397, 0.1366), (0.9758, -0.062, -0.2095), (0.1951, -0.1848, 0.9632), 0.5), ((-0.0974, 0.0455, 0.0962), (0.9998, 0.002, -0.0173), (0.0173, 0.0011, 0.9998), 0.5), ((-0.0238, -0.0868, 0.1591), (-0.2051, 0.2116, -0.9556), (-0.0479, -0.9774, -0.2061), 0.5), ((-0.0974, 0.0455, 0.0962), (0.9998, 0.002, -0.0173), (0.0173, 0.0011, 0.9998), 0.5)]},
        'markers': {'primary_trigger': 'primary trigger', 'left_hand': 'left hand', 'vent': 'vent'},
        'ground_point': 'auto',
        # an own hull (the template's hides the world model, C1): the built JMS's extent (x -0.099..0.280,
        # y +-0.018, z -0.024..0.087 wu) as body + grip
        'collision': {'material': 'metal',
                      'boxes': [((-0.099, -0.018, 0.0), (0.28, 0.018, 0.087)),
                                ((-0.03, -0.012, -0.024), (0.01, 0.012, 0.0))]},
        # Halo 1's `tool model` keeps 31 characters of a shader name (C1)
        'material_names': {'storm_spread_gun_mainbody_default': 'ss_body',
                           'storm_spread_gun_metal_default': 'ss_metal',
                           'storm_spread_gun_energy_bar_default': 'ss_glow'},
        'shaders': {'ss_body': (BASE + 'ss_body_base.png', None),
                    'ss_metal': (BASE + 'ss_metal_base.png', None)},
        # the AR's gun shader (the Suppressor's / Boltshot's, user-approved)
        'template': AR + r'fp\shaders\gun',
        'glow': {},
        # the energy bars: an additive glow per UV island (the Boltshot's tuned settings, no white-hot
        # centre). BOOT 1 (user: 'glow can be improved -- the Boltshot's glowing display is a good example;
        # the original also lights up on every shot'; the Halo 4 screenshots: the bars lit orange at rest,
        # the whole bar set flaring yellow-orange on a shot): two layers on the bars --
        #   ss_glow   the bar itself, a STRIP glow (falls off across the bar, the Suppressor's B) with a
        #             narrow pale core
        #   ss_flash  the SHOT: each bar copied x3 across, bright and hot, its brightness = A out (the
        #             template's primary EJECTION PORT function: 1 on a shot, back to 0 over the ejection
        #             port recovery time -- Halo 4's own 1.0 s; Halo 4 drives its flare from the same
        #             `eject_port` function)
        'glow_shaders': {'ss_glow': {'rgb': ORANGE, 'additive': True, 'islands': True,
                                     'islands_of': 'storm_spread_gun_energy_bar_default',
                                     'strip': True, 'gain': 1.8, 'falloff': 0.45, 'radius': 1.2,
                                     'hot': True, 'core': 3.0, 'hot_rgb': (1.0, 0.85, 0.5)},
                         'ss_flash': {'rgb': FLASH, 'additive': True, 'islands': True,
                                      'islands_of': 'storm_spread_gun_energy_bar_default',
                                      'strip': True, 'gain': 2.5, 'falloff': 0.8, 'radius': 1.2,
                                      'hot': True, 'core': 2.0, 'hot_rgb': (1.0, 0.95, 0.75),
                                      'fade_source': 'A_out'}},
        # THE MODEL BUFFER BUDGET (0.6 MiB): a card layer copies each bar triangle (891 a layer) -- both
        # layers made 0.67 MiB -> the halo cards dropped (ss_halo unused for now), the flash kept: 0.60 MiB
        'glow_cards': {'ss_flash': {'of': 'ss_glow', 'shader': 'ss_flash', 'scale': 3.0, 'along': 1.1,
                                    'lift': 0.06, 'round_scale': 1.6,
                                    'skip_piece_normals': [(1.0, 0.0, 0.0), (-1.0, 0.0, 0.0)],
                                    'skip_piece_dot': 0.9}},
    },

    # FP animations (h1_fp_retarget.py): ROUTE (a), Halo 4's OWN storm_fp_spread_gun (Foundry, h4_fp_dump.py
    # -> out\h4_fp, 25 animations, 91 bones), the arms RE-SOLVED. fire_1 var1 24 (its shell-pump-like
    # motion: Halo 4 plays the shotgun's cocking effect at 7), idle 100, posing var1 / var2 89, ready 21
    # (ready_initial 29), put_away 7, melee_strike_1 35 (primary keyframe 5) / _2 37, reload_enter 14,
    # reload_continue_empty 21 (ONE shell), chamber_1 39 (after an empty magazine), throw_grenade 44,
    # moving 20 / look 9 (overlays), acceleration_screens 9 (an overlay: no Halo 1 state), sprint / jump /
    # land / fall / first_time_pickup (no Halo 1 state). Halo 1's SHOTGUN states (the template): enter ->
    # reload-empty a shell -> exit-empty (was empty) / exit-full (rounds left)
    'retarget': {
        'graph': H4 + SFP + '.model_animation_graph',
        'render_model': H4 + SW + r'\storm_spread_gun.render_model',
        'nodes': {n[2:]: 'frame ' + n.replace('_', ' ') for n in GUN_NODES},
        'drop_nodes': tuple(DROP),
        'h1_dir': r'weapons\scattershot\fp',
        'h1_model': r'weapons\scattershot\fp\fp',
        'align': 'same_space',
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
            'first_person:reload_enter': 'first-person enter',
            'first_person:reload_continue_empty': 'first-person reload-empty',
        },
        # Halo 4 has no reload exit with rounds left (its graph: enter, continue_empty, chamber_1) ->
        # Halo 1's exit-full = reload_enter played BACKWARDS (back to the idle grip)
        # BOOT 1 (user: 'reloading doesn't reload each shell separately' -- empty: 3 shell animations, the
        # last two shells during the exit; 4 missing: 2; 3: 1; 2 and 1: 0). HALO 1's RULE (fits all five):
        # the reload timer runs from the enter's start, and before each shell the exit starts once the time
        # left is under the EXIT's length -- the 1.33 s chamber_1 ate two 0.7 s shells. Every shell shows
        # only when enter + exit < one shell. User's pick ('every shell shown'): reload_enter at 2x (7 fr),
        # BOTH exits = the enter reversed in 6 fr; chamber_1 (the pump after an empty magazine) dropped --
        # fire_1 has the cocking motion. Balanced shell 0.525 s: 0.233 + 0.2 still fits
        'reverse': {'first-person exit-full': 'first_person:reload_enter',
                    'first-person exit-empty': 'first_person:reload_enter'},
        'resample': {'first-person enter': 7, 'first-person exit-full': 6, 'first-person exit-empty': 6},
        # BOOT 1 (user: 'part of the rifle is missing'): the start (the Suppressor's 2 units down) swept the
        # gun's REAR top -- 0-0.1 wu in front of the eye on this long gun -- down out of the view (the muzzle,
        # far away, barely moved). Halo 4's own placement (the gun bone matches it exactly at 0): no offset
        'view_offset': (0.0, 0.0, 0.0),
        # BOOT 1 (user: 'melee: move FP 1 unit lower'): the melee alone, ramped in / out (the Boltshot's)
        'view_offset_anims': {'first_person:melee_strike_1': {'offset': (0.0, 0.0, -0.01),
                                                              'ramp': {'in': 4, 'out': 8}}},
    },

    # Halo 4's own sounds (h1_port_sounds.py scattershot, `bank` 'halo4'). The player bank spread_gun_player
    # (the FP frame_event_list's player events; the legacy sg_fire1 / sg_* shotgun cues are EMPTY in MCC).
    # HIRC (2026-10-15): fire = a random crack of 4 [0-3] + 4 single layers [4, 5, 6, 7] + a random tail of
    # 4 [8-11]; reload_loop = three random layers [0-2] [3-5] [6-11]; reload_enter / reload_exit / ready /
    # melee = random of 3 / 2 / 4 / 3 (reload_exit = chamber_1's: dropped with it, boot 1); posing var1 = idle_b part 1 @0, 2 @40, 3 @70; dry fire 1; the drop
    # (spread_gun_player) random of 3; the shard's end (sg_detonate: proj_spreadgun) random of 7. Levels =
    # the active RMS of the stock Halo 1 sound each stands in for (h1_stock_sound_levels 2026-10-15):
    # shotgun fire -16.7, shotgun_ready -15.3, shotgun_melee -13.5, shotgun_posing -23.0, shotgun_reload1_1
    # (enter) -19.9..-24.0 -> -22.0, shotgun_reload2_1 (a shell) -20.0..-23.4 -> -21.9, the AR dry fire (the shotgun's EMPTY plays it) -17.6, shotgun_impact -20.7;
    # impacts the Suppressor's (-11.3)
    'sounds': {
        'catalog': 'Scattershot',
        'bank': 'halo4',
        'wwise_bank': 'spread_gun_player',
        'dir': B.join(['sound', 'weapons', 'scattershot_port']),
        'sounds': {
            'ss_fire': (['play_weapons_storm_spreadgun_fire_player:0,1,2,3',
                         'play_weapons_storm_spreadgun_fire_player:4',
                         'play_weapons_storm_spreadgun_fire_player:5',
                         'play_weapons_storm_spreadgun_fire_player:6',
                         'play_weapons_storm_spreadgun_fire_player:7',
                         'play_weapons_storm_spreadgun_fire_player:8,9,10,11'],
                        'sound\\sfx\\weapons\\shotgun\\fire', -16.7),
            'ss_dryfire': (['play_wea_spreadgun_player_dry_fire_empty'],
                           'sound\\sfx\\weapons\\assault rifle\\dryfire', -17.6),
            'ss_ready': (['play_wea_spreadgun_ready:0,1,2,3'],
                         'sound\\sfx\\weapons\\weapon_anims\\shotgun_ready', -15.3),
            'ss_melee': (['play_wea_spread1_foley_melee_player:0,1,2'],
                         'sound\\sfx\\weapons\\weapon_anims\\shotgun_melee', -13.5),
            'ss_pose': (['play_wea_spreadgun_idle_b_part_1', 'play_wea_spreadgun_idle_b_part_2',
                         'play_wea_spreadgun_idle_b_part_3'],
                        'sound\\sfx\\weapons\\weapon_anims\\shotgun_posing', -23.0),
            'ss_reload_enter': (['play_wea_spreadgun_player_reload_enter:0,1,2'],
                                'sound\\sfx\\weapons\\weapon_anims\\shotgun_reload1_1', -22.0),
            'ss_reload': (['play_wea_spreadgun_player_reload_loop:0,1,2',
                           'play_wea_spreadgun_player_reload_loop:3,4,5',
                           'play_wea_spreadgun_player_reload_loop:6,7,8,9,10,11'],
                          'sound\\sfx\\weapons\\weapon_anims\\shotgun_reload2_1', -21.9),
            'ss_drop': (['play_wea_drop_rifle_fr_spread_gun_nonplayer:0,1,2'],
                        'sound\\sfx\\impulse\\weapon_drops\\shotgun_impact', -20.7),
            # the shard's end (Halo 4 sg_detonate's spreadgun_proj_explode); six end at once: the level of
            # the needle burst it replaces is set at the first boot
            'ss_burst': (['play_wea_spreadgun_proj_detonate@proj_spreadgun'],
                         'sound\\sfx\\weapons\\needler\\expl', -24.0),
            # the shard's hard-surface hits (Halo 4's material effects: plasma impact + the forerunner
            # sweetener, the Suppressor's pair)
            'ss_impact': (['play_wea_plasma_impact_dirt@plasma_impact_generic',
                           'play_wea_forerunner_impact_generic@forerunner_impact_sweetener'],
                          'sound\\sfx\\weapons\\plasma rifle\\plasmahit', -11.3),
            # the BALANCED shell (the patcher retimes reload-empty x0.75 and swaps this in)
            'ss_reload_balanced': (['play_wea_spreadgun_player_reload_loop:0,1,2',
                                    'play_wea_spreadgun_player_reload_loop:3,4,5',
                                    'play_wea_spreadgun_player_reload_loop:6,7,8,9,10,11'],
                                   'sound\\sfx\\weapons\\weapon_anims\\shotgun_reload2_1', -21.9),
        },
        'offsets': {'ss_pose': [0.0, 40 / 30.0, 70 / 30.0]},
        'stretch': {'ss_reload_balanced': 0.75},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only scattershot) on a COPY of the Halo 1 SHOTGUN (the yardstick:
    # shell magazine, HUD, melee, two-handed pose). DEFAULT = HALO 4's OWN NUMBERS; the shotgun-ratio values
    # are the balance rows. The shotgun's 15 pellets -> Halo 4's 6 (the barrel's, a random 'point' cone: the
    # same shape on both sides)
    'pickable': {
        'weapon': SS + 'scattershot',
        'template': SG + 'shotgun',
        'world_model': SS + 'scattershot',
        # ONE model tag for world AND first person (the 32 MiB model-buffer rule, C2)
        'fp_model': SS + 'scattershot',
        'fp_anims': SS + 'fp\\fp',
        'label': 'ss',
        'teach': ('ss', 'sg'),
        'keys': {'first-person melee': 5},          # Halo 4 melee_strike_1 primary keyframe 5
        'sounds': {'first-person ready': SND + 'ss_ready',
                   'first-person posing': SND + 'ss_pose',
                   'first-person melee': SND + 'ss_melee',
                   'first-person enter': SND + 'ss_reload_enter',
                   'first-person reload-empty': SND + 'ss_reload'},
        # THE SHARD (on a copy of the shotgun PELLET; bullet_slow / shotgun both sides: the pellet's table)
        'bullet': {'projectile': (SG + 'pellet', SS + 'shard'),
                   'damage': (SG + 'pellet', SS + 'shard'),
                   'dmg': 12.0, 'acceleration': 0.06, 'velocity': (75.0, 10.0), 'range': 6.7,
                   # no falloff (Halo 4): lower = upper. STEP 4b list 2 (H4 shard vs H4 shotgun bullet onto
                   # the H1 pellet): active camouflage 0.18 x 0.2/0.4; breaking effect forward radius 0.8 x
                   # 0.12/0.5, exponent 2 x 0.2/0.3, outward velocity 0.5 x 3/5, radius 0.2 x 0.5/0.35;
                   # list 3 (a zero on one side -> the source value): outward exponent 0.2. Instantaneous
                   # acceleration 0.06 (list 3, the source's: `acceleration`)
                   'fields': {'damage.damage_lower_bound': 12.0,
                              'damage.active_camouflage_damage': 0.09,
                              'breaking_effect.forward_radius': 0.192,
                              'breaking_effect.forward_exponent': 1.333,
                              'breaking_effect.outward_velocity': 0.3,
                              'breaking_effect.outward_radius': 0.286,
                              'breaking_effect.outward_exponent': 0.2},
                   'proj_fields': {
                       # STEP 4b list 2: water gravity 0.4 x 0/0.2 = 0, water damage range 0..1 x 10/1;
                       # the air damage range is INERT on both Halo 4 sides (no distance flag) and on
                       # Halo 1 with lower = upper: the template's kept
                       'proj_attrs.physics.water_gravity_scale': 0.0,
                       'proj_attrs.physics.water_damage_range': (0.0, 10.0),
                       # the life (the docstring's re-fit), started at the muzzle (Halo 4 'immediately'; the
                       # template pellet's 'on first bounce' with timer 0 would end every ricochet -- A5)
                       'proj_attrs.detonation_timer_starts': 'immediately',
                       'proj_attrs.detonation.timer': (0.055, 0.21),
                       'proj_attrs.detonation.minimum_velocity': 5.0,
                       'proj_attrs.flags.oriented_along_velocity': True,
                       'proj_attrs.flags.detonation_max_time_if_attached': True,
                       # THE SUPERCOMBINE (user, 4a): the needle's flag; count 6 = the catalog row
                       # (h1_supercombine_count's per-projectile field; off = the engine's 7)
                       'proj_attrs.flags.has_super_combining_explosion': True},
                   # Halo 4's NEW response table (above): a DEFAULT reflect on the world and Hunter armour
                   # (chance 1, any angle / speed), frictions 0.1 / 0.1 there (their potential response
                   # switched off: skip 1); attach in every other unit
                   'default_responses': {'reflect': WORLD + HUNTER, 'attach': UNITS},
                   'reflect': [{'materials': WORLD + HUNTER, 'angle_deg': (0.0, 0.0), 'skip': 1.0,
                                'parallel_friction': 0.1, 'perpendicular_friction': 0.1, 'noise_deg': 0.0,
                                # the potential never fires: no (borrowed) effect on it
                                'effect_from_default': False}],
                   # the shard's end: the needle's burst (the Boltshot's / Spike Rifle's recipe), debris /
                   # smoke / decal dropped, tinted, small (6 at once), Halo 4's own burst sound
                   'detonation_effect': {'from': N + 'effects\\needle detonate',
                                         'out': SS + 'effects\\shard burst',
                                         'drop_particles': ('debris', 'smoke'),
                                         'drop_parts': (r'effects\decals\bullet holes\dirt pistol',),
                                         'swaps': {'sound\\sfx\\weapons\\needler\\expl': SND + 'ss_burst'},
                                         'tint_match': ('flash h pistol detonate', 'flare h stealth cannon'),
                                         'tint': ORANGE, 'scale': 0.25},
                   # THE SUPERCOMBINE: Halo 4 attached 35 -> 250 + area 10 -> 40 (r 0.375-1.25) = ONE Halo 1
                   # damage 45 -> 290 over that radius (the Needle Rifle's merge); the needler explosion's
                   # materials; Halo 4's super effect has NO sound -> the needle's dropped; tinted
                   'super_explosion': {'effect': (N + 'effects\\explosion', SS + 'effects\\supercombine'),
                                       'damage': (N + 'explosion', SS + 'supercombine'),
                                       'lower': 45.0, 'upper': (290.0, 290.0), 'radius': (0.375, 1.25),
                                       'drop_parts': ('sound\\sfx\\impulse\\impacts\\needler_super_expl',),
                                       'particle_tint': ORANGE, 'tint_match': ('',),
                                       # the needle explosion's pink light -> an own orange copy (its
                                       # particle system stays the needler's: judged at the boot)
                                       'light': {'rgb': FLASH, 'out': SS + 'effects\\supercombine light'}},
                   # the LOOK: Halo 4's shard = a glowing energy ball (flare + light + trail) -> the AR
                   # tracer's contrail recoloured + the Suppressor's glow (fuel rod exhaust light + flare)
                   'attachments_from': AR + 'bullet',
                   'contrail': {'from': AR + 'bullet', 'out': SS + 'shard trail', 'rgb': SHARD},
                   'glow': {'light': (r'weapons\fuel rod gun\fuel rod exhaust', SS + 'shard glow'),
                            'flare': SS + 'shard glow', 'rgb': FLASH, 'flare_radius': 0.06,
                            'marker': ''},
                   # every response effect that plays the pellet's bullet impacts -> the shard's own
                   'impact_tint': {'match': (), 'rgb': None, 'out': SS + 'effects\\impact\\',
                                   'sounds': {'sound\\sfx\\impulse\\impacts\\' + s: SND + 'ss_impact'
                                              for s in ('dirthits', 'granhit', 'metalhit', 'woodhit',
                                                        'snow_hits', 'glass_hits', 'bullet_ricc',
                                                        'ice_hits')}}},
        # THE HIT-EFFECT RULE counts SHOTS (the Mauler, user): 2/s is under 3.5/s -> x1, no impact_thin
        # Halo 4: recovery 0.5 s = 2 shots / s; error 4 -> 7 deg, at once (acceleration 0), back in 0.25 s
        'trigger': {'rounds_per_second': (2.0, 2.0), 'acceleration_time': 0.0, 'deceleration_time': 0.0,
                    'error_acceleration_time': 0.0, 'error_deceleration_time': 0.25,
                    'rounds_between_tracers': 0,
                    # BOOT 1: the shot flash fades with A out = the ejection port function (glow
                    # `ss_flash`): Halo 4's own ejection port recovery, 1.0 s (the H1 shotgun's 0.15)
                    'ejection_port_recovery_time': 1.0},
        'error_deg': {'minimum_error': 0.0, 'error_angle': (4.0, 7.0)},
        # Halo 4: 5 loaded, 15 at pickup, 20 most, ONE round a reload cycle; the cycle = reload_continue
        # _empty's 21 fr (0.7 s; Halo 1's shotgun: 0.4 s = its 12 fr shell); chamber time 0 (the H4 shotgun
        # 1.167 -> the H1 shotgun's 0 x 0 / 1.167)
        'magazine': {'rounds_loaded_maximum': 5, 'rounds_reloaded': 1,
                     'rounds_total_initial': 15, 'rounds_total_maximum': 20,
                     'reload_time': 0.7},
        # Halo 4 aim assist: the MODE block, absolute; no zoom (the shotgun has none)
        'aiming': {'autoaim_angle': 6.0, 'autoaim_range': 7.0,
                   'magnetism_angle': 12.0, 'magnetism_range': 6.5},
        'fields': {
            # weapon type 'shotgun' and magazine 'every round must be chambered': Halo 4's Scattershot and
            # shotgun agree (shotgun / 0) -> the yardstick's own (the template's) kept
            # the shotgun's EMPTY field names the AR dry fire SOUND and `shotgun empty` sits on MISFIRE (the
            # Mauler's trap): empty = the port's own dry fire, misfire cleared
            'weap_attrs.triggers.0.projectile.projectiles_per_shot': 6,
            'weap_attrs.triggers.0.firing_effects.0.empty_effect.filepath': SND + 'ss_dryfire',
            'weap_attrs.triggers.0.firing_effects.0.misfire_effect.filepath': '',
            'item_attrs.collision_sound.filepath': SND + 'ss_drop',
            # STEP 6: the template's magazine names `powerups\shotgun ammo` (60 a box). Halo 4 gives no
            # pickup amount (Forerunner ammo boxes) -> the YARDSTICK's pickup : initial (60 : 24) on Halo
            # 4's initial 15 = 37.5 -> 38
            'weap_attrs.magazines.0.magazine_items.0.rounds': 38},
        'sound_effects': {
            # THE MUZZLE-FLASH RULE (closing check 10, before boot 1). Halo 4's FIRST-PERSON firing
            # (fx\firing\sg_firing): at primary_trigger (the muzzle) two muzzle_flash_large 0.092 / 0.110
            # wu + muzzle bits 0.011 / 0.084, ON-AXIS; at the muzzle rim (secondary_trigger) rings 0.014,
            # a glow 0.049, a streak 0.012; small rings / bits at the vents; sparkles on the rails / slides
            # (0.05-0.17, markers Halo 1's model does not carry); a forward light-volume flash; NO smoke,
            # no casing. The shotgun's (h1_effect_particles): flash h generic 0.100-0.125 at +0.025 on-axis
            # (~ Halo 4's two large flashes: kept, x1), sparks trail 6-9 x 0.008-0.016 (~ the muzzle bits:
            # kept), smoke h fp 12-18 x 0.125-0.375 (Halo 4 none: dropped), the shell casing (Halo 4 none:
            # dropped) -> tinted Forerunner orange. Shifted by the Boltshot's tuned start on the same
            # storm_fp setup (2 units forward, 3.5 up)
            'firing_effect': (SG + 'effects\\shotgun firing', SS + 'effects\\fire shards',
                              {r'sound\sfx\weapons\shotgun\fire': SND + 'ss_fire'},
                              {'match': 'particles', 'shift': (0.02, 0.0, 0.035),
                               'drop_particles': ('casing', 'smoke'),
                               'tint': (1.0,) + ORANGE})},
        'melee': (SG + 'melee', SS + 'melee'),
        'melee_response': SG + 'melee_response',
        'messages': ('Picked up a scattershot', 'Picked up %d rounds for scattershot'),
        'extra_sounds': [SND + 'ss_reload_balanced'],
        'icon': 'scattershot',
        # the SHOTGUN's HUD; the crosshair from Halo 4's CUI (ui\hud\weapons\forerunner\spread_gun names
        # forerunner_spread_gun\bitmap\spread: ONE ring with seven tick marks and a notch, 384 px = 128
        # units at Halo 4's 3 px a unit) -- PROVISIONAL scale until the user's Halo 4 screenshot. Halo 4's
        # own round pips (ammo_spreadgun: 5 in a row) read at their own density (`native`, the Boltshot's)
        'hud': {'donor': SG + 'shotgun', 'out': SS + 'scattershot',
                'reticle': (H4 + SPR + 'spread', 0, 'scattershot'),
                'reticle_split': 1,
                'reticle_min_width': 2,
                'reticle_supersample': 2,
                'reticle_scale': 1.0, 'reticle_overlay': 1.5 / (123 / 97.0 * 1.0 * 2 * 0.75),
                'flash_base': 12,                # the shotgun's low-ammo cutoff is of 12
                'ammo_meter': {'sizes': (5, 10), 'base': SS + 'bitmaps\\scattershot_ammo',
                               'art': {'h3': (H4 + SAM + 'ammo_spreadgun', 0), 'native': True}}},
        'palette_levels': LEVELS,
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py scattershot). DEFAULT = Halo 4's own numbers
    # in the tags; BALANCED = the SHOTGUN ratio (step 4a, user 2026-10-15). Assembly Halo1 units: angles in
    # degrees, velocity in wu per TICK
    'catalog': {
        'entry': {
            'weapon': 'Scattershot', 'source': 'Halo 4', 'donor': 'Shotgun', 'default_on': False,
            'desc': "Halo 4's Scattershot: its model, first-person animations, sounds and numbers. A "
                    "Forerunner shotgun firing 6 glowing shards that bounce off hard surfaces and fade "
                    "out a few metres away; six shards stuck in one target burst. 5 shells, loaded one "
                    "at a time; Shotgun ammo tops it up.",
            'balance_desc': "Measured against the Shotgun, which both games have: 24.6 damage a shard, "
                            "a 10-shell magazine, 20 at pickup / 50 most, faster shells, a wider cone and "
                            "Halo 1-style aim assist. The shards keep Halo 4's speed, bounce and range.",
            # step 9: the balanced shell = 0.4 s x 21/16 = 0.525 s over the built 21 fr = x0.75 (the
            # patcher retimes 'reload' animations: reload-empty, the shell); swap = the H1 shotgun's ready
            # 23 fr x 21/23 (Halo 4 shotgun ready 23) = 21 fr, the built 21: x1.0
            'anims': {'reload': 0.75},
            'anim_sounds': {'reload': [
                {'mult': 0.75, 'from': SND + 'ss_reload', 'to': SND + 'ss_reload_balanced'}]},
            'balance': [
                # 21.5 x 12/10.5 a shard (the pellet's table); no falloff (lower = upper)
                row('jpt!', SS + 'shard', 'Damage Lower Bound', 24.57, 12.0, 'Shard Damage'),
                row('jpt!', SS + 'shard', 'Damage Upper Bound', 24.57, 12.0, 'Shard Damage'),
                row('jpt!', SS + 'shard', 'Damage Upper Bound Max', 24.57, 12.0, 'Shard Damage'),
                # magazine 12 x 5/6, initial 24 x 15/18, maximum 60 x 20/24; ONE shell a cycle both
                row('weap', SS + 'scattershot', 'Rounds Loaded Maximum', 10.0, 5.0, 'Magazine', block='Magazines'),
                row('weap', SS + 'scattershot', 'Rounds Total Initial', 20.0, 15.0, 'Magazine', block='Magazines'),
                row('weap', SS + 'scattershot', 'Rounds Total Maximum', 50.0, 20.0, 'Magazine', block='Magazines'),
                # the shell: 0.4 x 21/16
                row('weap', SS + 'scattershot', 'Reload Time', 0.525, 0.7, 'Magazine', block='Magazines'),
                # STEP 6 balanced: the shotgun's pickup : initial (60 : 24) on the balanced 20
                row('weap', SS + 'scattershot', 'Rounds', 50, 38, 'Ammo pickup', block='Magazines/Magazines'),
                # the cone: 10 x 4/3, 10 x 7/3 (Halo 4's shotgun grid 3 deg)
                row('weap', SS + 'scattershot', 'Error Angle', 13.33, 4.0, 'Error Angle', block='Triggers'),
                row('weap', SS + 'scattershot', 'Error Angle Max', 23.33, 7.0, 'Error Angle', block='Triggers'),
                # aim: 6 x 6/6, 15 x 7/5.5; 12 x 12/12, 15 x 6.5/5.5
                row('weap', SS + 'scattershot', 'Autoaim Angle', 6.0, 6.0, 'Autoaim'),
                row('weap', SS + 'scattershot', 'Autoaim Range', 19.1, 7.0, 'Autoaim'),
                row('weap', SS + 'scattershot', 'Magnetism Angle', 12.0, 12.0, 'Magnetism'),
                row('weap', SS + 'scattershot', 'Magnetism Range', 17.7, 6.5, 'Magnetism'),
                # THE SUPERCOMBINE count (h1_supercombine_count's per-projectile field: off = the
                # engine's 7): Halo 4's 6 both (no shotgun counterpart)
                row('proj', SS + 'shard', 'Super Detonation Projectile Count', 6, 6, 'Supercombine Shard Count'),
                # the 10 magazine's meter: scattershot_ammo sequence 1 (ammo_meter 5 10), step 25 (default
                # 50: the top threshold below 255); flash at 2 x 10/12 = 2 (default 1)
                dict(row('wphi', SS + 'scattershot', 'Sequence Index', 1, 0, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', SS + 'scattershot', 'Alpha Multiplier', 25, 50, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', SS + 'scattershot', 'Sequence Index', 1, 0, 'Ammo display', block='Static Elements'), index=0),
                dict(row('wphi', SS + 'scattershot', 'Loaded Ammo Cutoff', 2, 1, 'Ammo display'), index=0),
            ]},
    },

    # step 4b (port_field_audit.py --port scattershot): the source pair (Halo 4 Scattershot vs the yardstick,
    # Halo 4's shotgun) against the target pair (the H1 port vs its template = the H1 shotgun)
    'field_audit': {
        'source_kit': 'H4EK',
        'source': {'weapon': (SW + r'\storm_spread_gun.weapon',
                              r'objects\weapons\rifle\storm_shotgun\storm_shotgun.weapon'),
                   'projectile': (SW + r'\projectiles\storm_spread_gun_shard.projectile',
                                  r'objects\weapons\rifle\storm_shotgun\projectiles\storm_shotgun_bullet.projectile'),
                   'damage_effect': (SW + r'\projectiles\damage_effects\storm_spread_gun_shard_impact.damage_effect',
                                     r'objects\weapons\rifle\storm_shotgun\projectiles\storm_shotgun_bullet.damage_effect')},
        'target': {'weapon': (SS + 'scattershot.weapon', SG + 'shotgun.weapon'),
                   'projectile': (SS + 'shard.projectile', SG + 'pellet.projectile'),
                   'damage_effect': (SS + 'shard.damage_effect', SG + 'pellet.damage_effect')}},

    # the dry test: b30 (this session's level, parallel pair 4), Halo 4's own loadout (5 + 15)
    'test': {'level': 'b30', 'rounds': (5, 15), 'grunt': None, 'elite': None},
})
