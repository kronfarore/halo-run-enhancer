r"""Binary Rifle (Halo 4, wave C6) on a copy of the Halo 1 SNIPER RIFLE, which is also the yardstick (step
4a, user 2026-10-16). The Halo 4 route of lightrifle.py (h4: paths, Foundry FP decode, the arms re-solved,
Wwise sounds, a CUI crosshair, a POLYART scope) on the sniper template of dmr.py; the bullet's look by the
BEAM RECIPE (focus_rifle.py / spartan_laser.py: a baked tracer texture on the sniper's contrail).

HALO 4 (h3_weapon_values --kit h4 + the export, 2026-10-16): ONE trigger, ONE barrel. 129 a shot
(storm_forerunner_sniper_rifle_bullet jpt, damage group `sniper`, instantaneous acceleration 0.5, a
`headshot` label, no detonation / aoe), 30/s with a 1.0 s fire recovery (= 1 shot a second); magazine 2
(6 / 8), reload 86 / 71 fr (empty / full, primary keyframe 42); 2799 wu/s instant, range 500, no gravity;
error 4 deg flat, minimum 0 -- barrel flags 512 = the H4 sniper's (error unzoomed only); zoom 2 levels
(4x, 10x); aim struct 1/10 4/14, the MODE block: mode 0 (unzoomed) none, modes 1-2 (zoomed) 1/25 1.6/25,
deviation 0.4; melee the shared strike_melee. The bullet OVERPENETRATES soft / tough organic / thin metal
/ thin shields / glass / plants / liquid in BOTH response tables (old + new, C5's trap); thick shields /
metal / terrain fizzle or bounce.

THE MATERIALS (H4EK .material values read from the tag bytes: tool export-tag-to-xml refuses .material):
_metal = srf_char_forerunner_andrew, NO colour map shipped (the material names _default_diff, which
exists nowhere -- the Suppressor's case), albedo tint 0.804 grey, control_map_spdfgl = _default_control,
diffuse intensity 0.23, specular 25; _metal_glow = srf_char_constant: si_color (1, 0.357, 0) x20, albedo
(1, 0.13, 0). m020 ships the same _default_ bitmaps (normal / control / cube / detail spec)."""
from ._common import B, reserved, row

H4 = 'h4:'                                          # an H4EK path (h4_tags)
SW = r'objects\weapons\rifle\storm_forerunner_sniper_rifle'
SFP = r'objects\characters\storm_fp\weapons\rifle\fp_forerunner_sniper_rifle\storm_fp_forerunner_sniper_rifle'
SBM = SW + r'\bitmaps\storm_forerunner_sniper_rifle_default' + B
BIUI = r'ui\hud\weapons\forerunner\attach_beam\bitmap' + B    # Halo 4's crosshair art (CUI attach_beam)
BI = 'weapons\\binary rifle\\'
SND = 'sound\\weapons\\binary_rifle_port\\'
SR = 'weapons\\sniper rifle\\'
AR = 'weapons\\assault rifle\\'
PP = 'weapons\\plasma pistol\\'
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']
# the diffuse (h4_standin_diffuse.py <control> <this>, channel mode, tint 0.804) in the port's data folder
STANDIN = r'F:\SteamLibrary\steamapps\common\HCEEK\data\weapons\binary rifle\source\bi_metal_diffuse.png'
# the scope's quadrant PNGs (h4_polyart_scope.py, in the port's own data folder) -- after the user's
# Halo 4 screenshot
SCOPE = r'F:\SteamLibrary\steamapps\common\HCEEK\data\weapons\binary rifle\scope' + B
# Forerunner hardlight orange (the glow material's si_color 1 / 0.357 / 0 -- a start; the user's Halo 4
# screenshot sets it, as on the Suppressor / LightRifle)
ORANGE = (1.0, 0.5, 0.08)

# the Storm Rifle's DROP list: every storm_fp graph shares the skeleton (checked 2026-10-16: this graph's
# 99 nodes = the same 80 arm / camera nodes + the render model's 19 gun bones)
from .storm_rifle import DROP  # noqa: E402

# the render model's 19 nodes (b_gun root), all in the FP graph
GUN = ('gun', 'left_spinner_01', 'right_spinner_02', 'scope', 'right_spinner_01', 'left_flap_01',
       'left_flap_03', 'right_flap_01', 'upper_barrel', 'left_barrel_vent', 'ammo', 'right_flap_02',
       'lower_barrel', 'spin', 'left_spinner_02', 'right_barrel_vent', 'left_flap_02', 'right_flap_03',
       'cover')

PORT = reserved(
    order=31, wave='C6', name='Binary Rifle', source='Halo 4',
    messages=(95, 96), icon=51, reticle=40, label='bi', teach_from='sr',
    sound_dir='sound\\weapons\\binary_rifle_port', weapon_dir='weapons\\binary rifle',
    yardstick={
        # step 4a (user, 2026-10-16; h1_role_compare.py binary_rifle)
        'pick': 'Sniper Rifle',
        'reason': ("user, step 4a 2026-10-16: the sniper's role (a magazine sniper, two zooms, one-hit "
                   "Grunts / Jackals on Legendary). DEFAULT = Halo 4's own numbers, BALANCED = the SNIPER "
                   "ratio rows (H1 sniper x H4 Binary Rifle / H4 sniper). Rocket Launcher ratio rejected: "
                   "92.4 at 0.4/s = 37 dps, weaker than the plain sniper (a bullet against an explosive's "
                   "direct hit), its speed and aim degenerate. ERROR (user): Halo 4's own 4 deg unzoomed "
                   "in both (the ratio 0.5 x 4/0.05 = 40 deg degenerates)"),
        # DEFAULT = Halo 4's own numbers; these are the BALANCED rows. Halo 4: Binary Rifle / sniper (129
        # / 80 a shot; recovery 1.0 / 0.767 s; 2 / 4; 6 / 12; 8 / 20; 86 / 86 fr empty, 71 / 72 full;
        # 2799 / 2799 wu/s; 500 / 500; zoom (4, 10) / (4, 9); aim (mode blocks, zoomed) 1/25 1.6/25 /
        # 1/25 2/25; error 4 / 0.05). H1 sniper: 101, 2/s, 4 (12 / 24), 94 / 83 fr, 1000 wu/s, range
        # 1000, zoom (2, 8), aim 1/35 2/35, error 0.5 (unzoomed), melee 55
        'balanced': {
            'damage': 162.9,             # 101 x 129/80
            'rate': 1.533,               # 2/s x 0.767/1.0 (both semi-automatic: 1 / recovery)
            'magazine': 2,               # 4 x 2/4
            'rounds_total_initial': 6,   # 12 x 6/12
            'rounds_total_maximum': 10,  # 24 x 8/20 = 9.6 (not dual-wieldable: no carry rule)
            'reload_s': 94 / 30.0,       # 94 fr x 86/86 (reload empty; full: 83 fr x 71/72 = 81.8 fr)
            'velocity': 1000.0,          # 1000 x 2799/2799
            'range': 1000.0,             # 1000 x 500/500
            'aim': (1.0, 35.0, 1.6, 35.0),  # 1 x 1/1, 35 x 25/25; 2 x 1.6/2, 35 x 25/25
            'zoom': (2.0, 8.89),         # (2, 8) x (4/4, 10/9)
            'error_deg': None,           # user: Halo 4's own 4 deg (unzoomed) in both
            'melee': None},              # Halo 4 shares strike_melee: x1 = the H1 sniper's 55
        'measured': 'h1_role_compare.py binary_rifle',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\storm_forerunner_sniper_rifle\\storm_forerunner_sniper_rifle',
            'provisional': 'Sniper Rifle',
            'alternatives': ['Rocket Launcher'],
            'direct': None,
            'peers': ['Sniper Rifle', 'Rocket Launcher', 'Beam Rifle (port)', 'Spartan Laser (port)'],
            'why': 'magazine 2, two zoom levels, near-instant: a one-hit-kill sniper',
            'lacks': ("Halo 4's headshot bonus (Halo 1 has no per-weapon headshot multiplier beyond the "
                      "sniper bullet's own); sprint; the scoped-beam glare effect on the 3P model")}},
    # step 11: the source game's ai\generic entry (25 fields, verified 2026-10-07) -- filled at step 11
    firing_profile={'mode': 'source', 'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map',
                    'from_weapon': 'objects\\weapons\\rifle\\storm_forerunner_sniper_rifle\\storm_forerunner_sniper_rifle'},
)

PORT.update({
    'status': 'in_progress',

    # geometry + look (h1_h3_weapon_model.py; Halo 4 through h4_tags). ONE render model for world AND first
    # person: 19 nodes (b_gun root), regions `default` (mesh 0) + `knight_arm` (mesh 1) -- both drawn on the
    # player's gun; 15571 verts / 19078 triangles; extent x -0.119..0.506, y +-0.021, z -0.022..0.108 wu.
    # Materials: _metal (srf_char_forerunner_andrew) + _metal_glow (srf_char_constant, self-illum x20).
    # Markers: primary_trigger (Halo 1's 'primary trigger'), primary_ejection, vent, cylinder, the plates,
    # scope_* (the scoped-beam glare), night_vision
    'model': {
        'dir': r'weapons\binary rifle',
        'world': H4 + SW + r'\storm_forerunner_sniper_rifle.render_model',
        'fp': H4 + SW + r'\storm_forerunner_sniper_rifle.render_model',
        'world_name': 'binary rifle',
        'ground_point': 'auto',
        # an own hull (the template's hides the world model, C1): the render model's extent
        'collision': {'material': 'metal',
                      'boxes': [((-0.119, -0.021, -0.022), (0.506, 0.021, 0.108))]},
        # Halo 1's `tool model` keeps 31 characters of a shader name (C1)
        'material_names': {'storm_forerunner_sniper_rifle_default_metal': 'bi_metal',
                           'storm_forerunner_sniper_rifle_default_metal_glow': 'bi_glow'},
        'shaders': {'bi_metal': (STANDIN, None)},
        'template': AR + r'fp\shaders\gun',
        'glow': {},
        # the glow material: an additive glow per UV island in the Forerunner orange (the LightRifle's
        # tuned settings; `hot` off -- tiny islands saturate white)
        'glow_shaders': {'bi_glow': {'rgb': ORANGE, 'additive': True, 'islands': True,
                                     'islands_of': 'storm_forerunner_sniper_rifle_default_metal_glow',
                                     'gain': 2.2, 'falloff': 0.35, 'radius': 1.3, 'hot': False}},
        # the beam's textures (THE BEAM RECIPE, B7): Halo 4's tracer profiles x their palettes, baked --
        # the core = the lance's fr_sniper_tracer through grad_forerunner_muzzle_smg, the glow = glow_red's
        # fr_rifle_tracer_glow through grad_forerunner_muzzle_spread; both additive (premultiplied)
        'baked_textures': {'bi_beam_core': {'profile': H4 + r'fx\bitmaps\2d\tracer\fr_sniper_tracer.bitmap',
                                            'palette': H4 + r'fx\bitmaps\gradient\grad_forerunner_muzzle_smg.bitmap',
                                            'premultiply': True},
                           'bi_beam_glow': {'profile': H4 + r'fx\bitmaps\2d\tracer\fr_rifle_tracer_glow.bitmap',
                                            'palette': H4 + r'fx\bitmaps\gradient\grad_forerunner_muzzle_spread.bitmap',
                                            'premultiply': True}},
    },

    # FP animations (h1_fp_retarget.py): ROUTE (a), Halo 4's own storm_fp_forerunner_sniper_rifle (Foundry,
    # h4_fp_dump.py -> out\h4_fp, 2026-10-16), the arms RE-SOLVED. 24 animations (frames): fire_1 var1 /
    # var2 24, idle 100, posing var1 70 / var2 89, ready 21 (ready_initial 29), put_away 6, melee_strike_1
    # 34 (primary keyframe 4), reload_full 71 / reload_empty 86 (primary 42), throw_grenade 44, moving 20
    # / look 9 (overlays), first_time_pickup 77; sprint / jump / land / fall / acceleration_screens: no
    # Halo 1 state
    'retarget': {
        'graph': H4 + SFP + '.model_animation_graph',
        'render_model': H4 + SW + r'\storm_forerunner_sniper_rifle.render_model',
        'nodes': {n: 'frame b ' + n.replace('_', ' ') for n in GUN},
        'drop_nodes': tuple(DROP),
        'h1_dir': r'weapons\binary rifle\fp',
        'h1_model': r'weapons\binary rifle\fp\fp',
        'align': 'same_space',
        # C5: a long FP gun -- start at Halo 4's own placement (offset 0) and judge through
        # h1_fp_camera_render before a boot
        'view_offset': (0.0, 0.0, 0.0),
        'anims': {
            'first_person:idle': 'first-person idle',
            'first_person:posing:var1': 'first-person posing',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:fire_1:var1': 'first-person fire-1',
            'first_person:melee_strike_1': 'first-person melee',
            'first_person:moving': 'first-person moving',
            'first_person:look': 'first-person overlays',
            'first_person:reload_empty': 'first-person reload-empty',
            'first_person:reload_full': 'first-person reload-full',
            'first_person:throw_grenade': 'first-person throw-grenade',
        },
    },

    # Halo 4's own sounds (h1_port_sounds.py binary_rifle, `bank` 'halo4'). The player bank
    # forerunner_sniper_player (h4_sound_research event, 2026-10-16); FP cues from the frame_event_list
    # (h4_sound_research cues). fire = play_wea_forerunner_sniper_player_fire: 6 layers, every target in
    # the bank (no switch); posing var1 = part a @0 + part b @14; the drop = wea_drop_rifle_shotgun_nonplayer
    # (homing_rifle_player, the LightRifle's); the flyby = the projectile's proj_forerunner_whizby_large.
    # Levels = the stock Halo 1 SNIPER sound each stands in for (dmr.py's h1_stock_sound_levels)
    'sounds': {
        'catalog': 'Binary Rifle',
        'bank': 'halo4',
        'wwise_bank': 'forerunner_sniper_player',
        'dir': B.join(['sound', 'weapons', 'binary_rifle_port']),
        'sounds': {
            'bi_fire': (['play_wea_forerunner_sniper_player_fire'],
                        'sound\\sfx\\weapons\\sniper rifle\\fire', -12.4),
            'bi_dryfire': (['play_wea_forerunner_sniper_player_dry_fire'],
                           'sound\\sfx\\weapons\\assault rifle\\dryfire', -17.6),
            'bi_ready': (['play_storm_fp_forerunner_sniper_rifle_ready'],
                         'sound\\sfx\\weapons\\weapon_anims\\sniper_ready', -21.6),
            'bi_melee': (['play_storm_fp_forerunner_sniper_rifle_melee_strike'],
                         'sound\\sfx\\weapons\\weapon_anims\\sniper_melee', -21.5),
            'bi_reload_empty': (['play_storm_fp_forerunner_sniper_rifle_reload_empty'],
                                'sound\\sfx\\weapons\\weapon_anims\\sniper_reload_empty', -17.4),
            'bi_reload_full': (['play_storm_fp_forerunner_sniper_rifle_reload_full'],
                               'sound\\sfx\\weapons\\weapon_anims\\sniper_reload_full', -16.7),
            'bi_pose': (['play_sniper_first_person_posing_var1_player_a',
                         'play_sniper_first_person_posing_var1_player_b'],
                        'sound\\sfx\\weapons\\weapon_anims\\sniper_posing', -19.1),
            'bi_zoom_in': (['play_wea_forerunner_sniper_player_zoom_in'],
                           'sound\\sfx\\weapons\\sniper rifle\\sniper_2x_zoom', -28.9),
            'bi_zoom_out': (['play_wea_forerunner_sniper_player_zoom_out'],
                            'sound\\sfx\\weapons\\sniper rifle\\sniper_10x_zoom', -29.2),
            'bi_drop': (['play_wea_drop_rifle_shotgun_nonplayer@homing_rifle_player'],
                        'sound\\sfx\\impulse\\weapon_drops\\shotgun_impact', -20.7),
            'bi_flyby': (['play_proj_forerunner_whizby_large@proj_forerunner_whizby_large'],
                         'sound\\sfx\\impulse\\impacts\\plasrif_projectile', -26.2),
            # the Suppressor's / LightRifle's Forerunner impact (plasma impact + the forerunner sweetener)
            'bi_impact': (['play_wea_plasma_impact_dirt@plasma_impact_generic',
                           'play_wea_forerunner_impact_generic@forerunner_impact_sweetener'],
                          'sound\\sfx\\weapons\\plasma rifle\\plasmahit', -11.3),
            # the BALANCED reloads (the patcher retimes both x1.12, then swaps these in)
            'bi_reload_empty_balanced': (['play_storm_fp_forerunner_sniper_rifle_reload_empty'],
                                         'sound\\sfx\\weapons\\weapon_anims\\sniper_reload_empty', -17.4),
            'bi_reload_full_balanced': (['play_storm_fp_forerunner_sniper_rifle_reload_full'],
                                        'sound\\sfx\\weapons\\weapon_anims\\sniper_reload_full', -16.7),
        },
        'offsets': {'bi_pose': [0.0, 14 / 30.0]},
        'stretch': {'bi_reload_empty_balanced': 1.12, 'bi_reload_full_balanced': 1.12},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only binary_rifle) on a COPY of the Halo 1 SNIPER RIFLE (the
    # yardstick: magazine, two zooms, bullet materials incl. overpenetration, zoomed-only aim assist,
    # error only unzoomed). DEFAULT = HALO 4's OWN NUMBERS; the sniper-ratio values are the balance rows.
    # STEP 6, the ammo pickup: Halo 4 has none -> the H1 sniper's pickup : initial (16 : 12, the DMR's) on
    # Halo 4's 6 = 8; the balanced initial is 6 too: no row
    'pickable': {
        'weapon': BI + 'binary rifle',
        'template': SR + 'sniper rifle',
        'world_model': BI + 'binary rifle',
        # ONE model tag for world AND first person (Halo 1's 32 MiB model buffer: plan 0.1)
        'fp_model': BI + 'binary rifle',
        'fp_anims': BI + 'fp\\fp',
        'label': 'bi',
        'teach': ('bi', 'sr'),
        'keys': {'first-person melee': 4},          # Halo 4 melee_strike_1 primary keyframe 4
        'sounds': {'first-person ready': SND + 'bi_ready',
                   'first-person posing': SND + 'bi_pose',
                   'first-person melee': SND + 'bi_melee',
                   'first-person reload-empty': SND + 'bi_reload_empty',
                   'first-person reload-full': SND + 'bi_reload_full'},
        # own bullet + damage (step 3): Halo 4 129 (sniper group = the H1 sniper bullet's table, user 4a),
        # acceleration 0.5, 2799 wu/s flat, range 500
        'bullet': {'projectile': (SR + 'sniper bullet', BI + 'bullet'),
                   'damage': (SR + 'sniper bullet', BI + 'bullet'),
                   'dmg': 129.0, 'acceleration': 0.5, 'velocity': 2799.0, 'range': 500.0,
                   'proj_fields': {'proj_attrs.physics.flyby_sound.filepath': SND + 'bi_flyby'},
                   # THE BEAM RECIPE (B7): Halo 4's tracer = 4 aligned ribbons (lance 0.25 s + lance_large on
                   # fr_sniper_tracer, glow_red 0.6 s + glow_orange on fr_rifle_tracer_glow, palettes
                   # grad_forerunner_muzzle_smg / _spread) -> the sniper's contrail with no physics (its
                   # vapour drifts with the wind), the baked core texture, a wider glow layer
                   'contrail': {'from': SR + 'sniper', 'out': BI + 'beam', 'no_physics': True,
                                'blend': 'add', 'bitmap': BI + 'bitmaps\\bi_beam_core',
                                'sequence': (0, 0),
                                'states': [{'duration': (0.2, 0.25), 'transition': (0.2, 0.3),
                                            'width': 0.08, 'argb': (1.0, 1.0, 1.0, 1.0)},
                                           {'width': 0.06, 'argb': (0.0, 1.0, 1.0, 1.0)}],
                                'extra': [{'out': BI + 'beam glow', 'blend': 'add',
                                           'bitmap': BI + 'bitmaps\\bi_beam_glow', 'sequence': (0, 0),
                                           'states': [{'duration': (0.4, 0.6), 'transition': (0.3, 0.4),
                                                       'width': 0.25, 'argb': (1.0, 1.0, 1.0, 1.0)},
                                                      {'width': 0.2, 'argb': (0.0, 1.0, 1.0, 1.0)}]}]},
                   # every hard-surface impact the sniper bullet plays -> Halo 4's Forerunner impact
                   'impact_tint': {'match': (), 'rgb': None, 'out': BI + 'effects\\impact\\',
                                   'sounds': {'sound\\sfx\\impulse\\impacts\\' + x: SND + 'bi_impact'
                                              for x in ('dirthits', 'granhit', 'metalhit', 'woodhit',
                                                        'snow_hits', 'glass_hits', 'bullet_ricc', 'ice_hits')}},
                   # THE HIT-EFFECT RULE: max(default 1.0, balanced 1.53)/s -- under 3.5/s: x1 (no thinning)
                   'impact_thin': {'materials': [22], 'out': BI + 'effects\\impact\\', 'thin': {}, 'rate': 1.533}},
        # semi-automatic (Halo 4: 1.0 s recovery); the sniper's trigger otherwise (use error when
        # unzoomed: Halo 4's barrel flag 512 = the H4 sniper's)
        'trigger': {'rounds_per_second': (1.0, 1.0), 'does_not_repeat_automatically': True},
        # Halo 4: minimum error 0, error angle 4 flat (unzoomed only: the sniper's flag)
        'error_deg': {'minimum_error': 0.0, 'error_angle': (4.0, 4.0)},
        # Halo 4: 2 loaded, 6 at pickup, 8 most; reload time 0 (the animation, as the sniper)
        'magazine': {'rounds_loaded_maximum': 2, 'rounds_reloaded': 2,
                     'rounds_total_initial': 6, 'rounds_total_maximum': 8, 'reload_time': 0.0},
        # Halo 4 aim assist: the zoomed MODE blocks (mode 0, unzoomed, is empty = the H1 sniper's
        # 'aim assists only when zoomed', kept); deviation 0.4 (the H1 sniper's 0: a zero on one side)
        'aiming': {'autoaim_angle': 1.0, 'autoaim_range': 25.0,
                   'magnetism_angle': 1.6, 'magnetism_range': 25.0, 'deviation_angle': 0.4,
                   'zoom_levels': 2, 'zoom_ranges': (4.0, 10.0)},
        'fields': {
            # the sniper's EMPTY field names a SOUND directly (the AR's dryfire; the Mauler trap)
            'weap_attrs.triggers.0.firing_effects.0.empty_effect.filepath': SND + 'bi_dryfire',
            'weap_attrs.interface.zoom_in_sound.filepath': SND + 'bi_zoom_in',
            'weap_attrs.interface.zoom_out_sound.filepath': SND + 'bi_zoom_out',
            'item_attrs.collision_sound.filepath': SND + 'bi_drop',
            # the sniper's integrated night vision: not the Binary Rifle's
            'weap_attrs.flags.enables_integrated_night_vision': False,
            # STEP 6: the H1 sniper's pickup : initial (16 : 12) on Halo 4's 6
            'weap_attrs.magazines.0.magazine_items.0.rounds': 8,
            'obje_attrs.collision_model.filepath': BI + 'binary rifle',
        },
        'sound_effects': {
            # THE MUZZLE-FLASH RULE (check 10, before boot 1): see the close-out below once compared
            'firing_effect': (SR + 'effects\\fire bullet', BI + 'effects\\fire bullet',
                              {'sound\\sfx\\weapons\\sniper rifle\\fire': SND + 'bi_fire'},
                              {'match': 'flash', 'tint': (1.0,) + ORANGE})},
        'melee': (SR + 'melee', BI + 'melee'),
        'melee_response': SR + 'melee_response',
        'messages': ('Picked up a binary rifle', 'Picked up %d rounds for binary rifle'),
        'icon': 'binary rifle',
        'extra_sounds': [SND + 'bi_reload_empty_balanced', SND + 'bi_reload_full_balanced'],
        # the SNIPER's HUD (screen effect + magazine readout) with Halo 4's crosshair (attach_beam.cui_screen,
        # at rest: four `outer` brackets 24 x 32 at opacity 0.9 -- top_left centre (-47, -38), top_right
        # (45, -38) flip x, bottom_left (-47, 39) flip y, bottom_right flip x+y (Halo 4's tag puts it at
        # left 83: mirrored here, (45, 39)) -- and four `inner_2` scope ticks 16 x 16 at opacity 0.2 at
        # (-69, -12) flip x, (66, -12), (-69, 14) flip x+y, (65, 14) flip y; the inner blooms opacity 0;
        # widget centres, the LightRifle's calibration)
        'hud': {'donor': SR + 'sniper rifle', 'out': BI + 'binary rifle',
                'screen_effect_clear': ('night_vision', 'desaturation'),
                # the polyart scope comes with the user's Halo 4 screenshot; until then a CLEAR mask with
                # the H1 blur outside the lens (the LightRifle's boot-4 values)
                'scope': {'out': BI + 'bitmaps\\scope_mask', 'size': 1024, 'alpha': 0,
                          'blur_outside': (244, 315), 'blur_edge': 14},
                # the SNIPER HUD's zoom overlays (crosshairs2, _sm, caption, two zoom crosshairs): all but
                # #0 dropped (the DMR's); its reticle draws from its OWN sheet -> the shared hud_reticles;
                # the zoom angle ticks / distance / elevation numbers dropped
                'drop_crosshairs': [1, 2, 3, 4, 5],
                'reticle_bitmap': r'ui\hud\bitmaps\combined\hud_reticles',
                'reticle_scaling': 0,
                'drop_elements': {'static': ['age'],
                                  'number': ['distance_to_target', 'elevation_to_target']},
                'reticle': (H4 + BIUI + 'outer', 0, 'binary rifle'),
                'reticle_xform': {'offset': (-47.0, -38.0), 'gain': 0.9},
                'reticle_layers': [(H4 + BIUI + 'outer', 0, 1.0, {'flip_x': True, 'offset': (45.0, -38.0), 'gain': 0.9}),
                                   (H4 + BIUI + 'outer', 0, 1.0, {'flip_y': True, 'offset': (-47.0, 39.0), 'gain': 0.9}),
                                   (H4 + BIUI + 'outer', 0, 1.0, {'flip_x': True, 'flip_y': True, 'offset': (45.0, 39.0), 'gain': 0.9}),
                                   (H4 + BIUI + 'inner_2', 0, 1.0, {'flip_x': True, 'offset': (-69.0, -12.0), 'gain': 0.2}),
                                   (H4 + BIUI + 'inner_2', 0, 1.0, {'offset': (66.0, -12.0), 'gain': 0.2}),
                                   (H4 + BIUI + 'inner_2', 0, 1.0, {'flip_x': True, 'flip_y': True, 'offset': (-69.0, 14.0), 'gain': 0.2}),
                                   (H4 + BIUI + 'inner_2', 0, 1.0, {'flip_y': True, 'offset': (65.0, 14.0), 'gain': 0.2})],
                'reticle_split': 1,
                'reticle_min_width': 2,
                'reticle_supersample': 2,
                'reticle_scale': 1.6, 'reticle_overlay': 1.5 / (123 / 97.0 * 1.6 * 2 * 0.75),
                # Halo 4's own round shards (ammo_forerunnersniper: 2 in a row), one a round, native density
                'ammo_meter': {'sizes': (2,), 'base': BI + 'bitmaps\\binary_rifle_ammo',
                               'art': {'h3': (H4 + BIUI + 'ammo_forerunnersniper', 0), 'native': True}}},
        'palette_levels': LEVELS,
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py binary_rifle). DEFAULT = Halo 4's own numbers
    # in the tags; BALANCED = the SNIPER ratio (step 4a, user 2026-10-16). Assembly Halo1 units: angles in
    # degrees, velocity in wu per TICK (2799 wu/s = 93.3; 1000 = 33.33)
    'catalog': {
        'entry': {
            'weapon': 'Binary Rifle', 'source': 'Halo 4', 'donor': 'Sniper Rifle', 'default_on': False,
            'desc': "Halo 4's Binary Rifle: its model, first-person animations, sounds and numbers. A "
                    "Forerunner sniper with two shots a magazine and 4x / 10x zoom: 129 damage a shot, "
                    "one a second, through soft targets. Sniper Rifle ammo tops it up.",
            'balance_desc': "Measured against the Sniper Rifle, which both games have: 163 damage a shot at "
                            "1.5 a second, 10 rounds most, a 1000 wu/s bullet with a 1000 wu reach, 2x / "
                            "8.9x zoom and Halo 1-style aim assist.",
            # step 9: ONE reload multiplier for both reloads -- balanced empty 94 fr x 86/86 = 94 over the
            # built 86 (x1.093), full 83 x 71/72 = 81.8 over 71 (x1.153): the mean x1.12. Swap: H1 sniper
            # ready 29 fr x Halo 4 Binary 21 / Halo 4 sniper 25 = 24.4 over the built 21 = x1.16
            'anims': {'reload': 1.12, 'swap': 1.16},
            'anim_sounds': {'reload': [
                {'mult': 1.12, 'from': SND + 'bi_reload_empty', 'to': SND + 'bi_reload_empty_balanced'},
                {'mult': 1.12, 'from': SND + 'bi_reload_full', 'to': SND + 'bi_reload_full_balanced'}]},
            'balance': [
                row('jpt!', BI + 'bullet', 'Damage Lower Bound', 162.9, 129.0, 'Bullet Damage'),
                row('jpt!', BI + 'bullet', 'Damage Upper Bound', 162.9, 129.0, 'Bullet Damage'),
                row('jpt!', BI + 'bullet', 'Damage Upper Bound Max', 162.9, 129.0, 'Bullet Damage'),
                row('weap', BI + 'binary rifle', 'Rounds Per Second', 1.533, 1.0, 'More Shooting', block='Triggers'),
                row('weap', BI + 'binary rifle', 'Rounds Per Second Max', 1.533, 1.0, 'More Shooting', block='Triggers'),
                row('weap', BI + 'binary rifle', 'Rounds Total Maximum', 10.0, 8.0, 'Magazine', block='Magazines'),
                row('proj', BI + 'bullet', 'Initial Velocity', 33.333, 93.3, 'Projectile'),
                row('proj', BI + 'bullet', 'Final Velocity', 33.333, 93.3, 'Projectile'),
                row('proj', BI + 'bullet', 'Maximum Range', 1000.0, 500.0, 'Projectile'),
                row('weap', BI + 'binary rifle', 'Autoaim Angle', 1.0, 1.0, 'Autoaim'),
                row('weap', BI + 'binary rifle', 'Autoaim Range', 35.0, 25.0, 'Autoaim'),
                row('weap', BI + 'binary rifle', 'Magnetism Angle', 1.6, 1.6, 'Magnetism'),
                row('weap', BI + 'binary rifle', 'Magnetism Range', 35.0, 25.0, 'Magnetism'),
                row('weap', BI + 'binary rifle', 'Magnification Range', 2.0, 4.0, 'Zoom'),
                row('weap', BI + 'binary rifle', 'Magnification Range Max', 8.89, 10.0, 'Zoom'),
            ]},
    },

    # step 4b (port_field_audit.py --port binary_rifle): the source pair (Halo 4 Binary Rifle vs the
    # yardstick, Halo 4's sniper) against the target pair (the H1 port vs its template, the H1 sniper)
    'field_audit': {
        'source_kit': 'H4EK',
        'source': {'weapon': (SW + r'\storm_forerunner_sniper_rifle.weapon',
                              r'objects\weapons\rifle\storm_sniper_rifle\storm_sniper_rifle.weapon'),
                   'projectile': (SW + r'\projectiles\storm_forerunner_sniper_rifle_bullet.projectile',
                                  r'objects\weapons\rifle\storm_sniper_rifle\projectiles\storm_sniper_rifle_bullet.projectile'),
                   'damage_effect': (SW + r'\projectiles\storm_forerunner_sniper_rifle_bullet.damage_effect',
                                     r'objects\weapons\rifle\storm_sniper_rifle\projectiles\storm_sniper_rifle_bullet.damage_effect')},
        'target': {'weapon': (BI + 'binary rifle.weapon', SR + 'sniper rifle.weapon'),
                   'projectile': (BI + 'bullet.projectile', SR + 'sniper bullet.projectile'),
                   'damage_effect': (BI + 'bullet.damage_effect', SR + 'sniper bullet.damage_effect')}},

    # the dry test: a30 (this session's level, parallel pair 5), Halo 4's own loadout (2 + 6)
    'test': {'level': 'a30', 'rounds': (2, 6), 'grunt': None, 'elite': None},
})
