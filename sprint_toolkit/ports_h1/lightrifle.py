r"""LightRifle (Halo 4, wave C4) on a copy of the Halo 1 PISTOL, which is also the yardstick (step 4a,
user 2026-10-15). The Halo 4 route of suppressor.py (h4: paths, Foundry FP decode, the arms re-solved,
Wwise sounds, a CUI crosshair) on the BURST + ZOOM shape of battle_rifle.py, with a SECOND TRIGGER as
in boltshot.py.

HALO 4 (h3_weapon_values --kit h4 + the export, 2026-10-15): ONE trigger, `latch-zoom` -- barrel 0
fires unzoomed, barrel 1 zoomed. UNSCOPED: a burst of 3 (shots per fire 3) at 30/s, recovery 0.3 s,
5.33 a round (`storm_forerunner_rifle` jpt, plasma_fast), error 0.15 flat; SCOPED: ONE shot of 23.5
(`storm_forerunner_rifle_combined`: its own projectile, damage, impact effects and the LARGE fly-by)
for 3 ROUNDS, 2.5/s (recovery 0.4), error 0.15 -> 0.5. Both 3000 wu/s, range 250, no gravity;
magazine 36 (108 / 144), reload 73 / 64 fr (empty / full); one zoom level, 3x; aim (MODE block)
2.25/20 5/20; melee the shared strike_melee.

THE MODES (step 4a, user: 'Try C, do A if it doesn't work out'): Halo 1's zoom cannot switch a
trigger. C = the burst on the right trigger (trigger 0, the Battle Rifle's charge + spew) and the
scoped single shot on the GRENADE key (trigger 1; Halo 1's weapon flag `secondary trigger overrides
grenades`, Bungie's own digsite\weapons\smg uses it) -- not tied to zoom, and no grenades while the
LightRifle is held. A (the fallback) = the burst on both zoom levels, the single shot lost.
Halo 1 hands a CHARGED trigger 0 to trigger 1 when a weapon has two (the plasma pistol, the Boltshot)
and the burst is a 1-tick charge: boot 1 tells whether the override flag keeps them apart (A rides
on the secondary for the same boot)."""
from ._common import B, reserved, row

H4 = 'h4:'                                          # an H4EK path (h4_tags)
SW = r'objects\weapons\rifle\storm_forerunner_rifle'
SFP = r'objects\characters\storm_fp\weapons\rifle\fp_forerunner_rifle\storm_fp_forerunner_rifle'
SBM = SW + r'\bitmaps\storm_forerunner_rifle_default' + B
LRUI = r'ui\hud\weapons\forerunner\forerunner_rifle\bitmap' + B    # Halo 4's crosshair art (CUI)
# the base map (Boltshot's colour mode): RGB = Halo 4's colour map (grey, solid alpha) x 1.0 (the body
# materials set no albedo_tint), A = the control map's R (specular) -- in the port's own data folder:
#   python h4_standin_diffuse.py <SBM>storm_forerunner_rifle_control.bitmap <BASE>lr_body_base.png
#          --mode color --color <SBM>storm_forerunner_rifle_diff.bitmap --tint 1.0
BASE = r'F:\SteamLibrary\steamapps\common\HCEEK\data\weapons\light rifle\source' + B
LR = 'weapons\\light rifle\\'
# the scope's quadrant PNGs (h4_polyart_scope.py, in the port's own data folder)
SCOPE = r'F:\SteamLibrary\steamapps\common\HCEEK\data\weapons\light rifle\scope' + B
SND = 'sound\\weapons\\light_rifle_port\\'
PISTOL = 'weapons\\pistol\\'
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']
# Forerunner hardlight orange: the glow material's si_color (1, 0.47, 0) x20 / albedo (1, 0.64, 0)
ORANGE = (1.0, 0.6, 0.1)

# the Storm Rifle's DROP list: every storm_fp graph shares the skeleton (checked 2026-10-15: this
# graph's 88 bones = the same 80 arm / camera nodes + the render model's 8 gun bones)
from .storm_rifle import DROP  # noqa: E402

# STEP 4b (port_field_audit --port lightrifle), the damage effects (both rounds): active camouflage
# damage by the ratio 0.45 x 1/0.5 = 0.9 (list 2); the BREAKING EFFECT a zero on one side (the Magnum's
# 0) -> Halo 4's own (list 3, the BR's rule). Flags: Halo 4 'can cause headshots' on both = the pistol
# bullet's own `headshot` (kept); 'ignores headshot obstructions', 'ignore seat scale', 'does not spill
# over' (the scoped round) have no Halo 1 field
JPT_FIELDS = {'damage.active_camouflage_damage': 0.9,
              'breaking_effect.forward_velocity': 35.0,
              'breaking_effect.forward_radius': 0.12,
              'breaking_effect.forward_exponent': 8.0,
              'breaking_effect.outward_velocity': 3.0,
              'breaking_effect.outward_radius': 0.5,
              'breaking_effect.outward_exponent': 0.2}

IMPACT_SOUNDS = {'match': (), 'rgb': None, 'out': 'weapons\\light rifle\\effects\\impact\\',
                 'sounds': {'sound\\sfx\\impulse\\impacts\\' + x: 'sound\\weapons\\light_rifle_port\\lr_impact'
                            for x in ('dirthits', 'granhit', 'metalhit', 'woodhit', 'snow_hits',
                                      'glass_hits', 'bullet_ricc', 'ice_hits')}}

# the render model's 8 nodes, all animated by the FP graph
GUN = ('gun', 'scope', 'cartridge', 'top_main', 'center', 'front_main', 'top', 'ammo')

PORT = reserved(
    order=29, wave='C4', name='LightRifle', source='Halo 4',
    messages=(91, 92), icon=49, reticle=38, label='lr', teach_from='ar',
    sound_dir='sound\\weapons\\light_rifle_port', weapon_dir='weapons\\light rifle',
    yardstick={
        # step 4a (user, 2026-10-15; h1_role_compare.py lightrifle)
        # BOOT 1 (user, a30, 2026-10-15): option C FAILED -- the right trigger never fired (its 1-tick
        # charge hands the shot to trigger 1, which the grenade key owns), the grenade key fired the
        # single shot (36 -> 33). Option A (burst only) from boot 2 (user: 'Try C, do A if it doesn't
        # work out')
        'pick': 'Pistol',
        'reason': ("user, step 4a 2026-10-15: the magnum's role (magazine precision, mid range) -- the "
                   "Battle Rifle's precedent. DEFAULT = Halo 4's own numbers, BALANCED = the PISTOL "
                   "ratio rows (H1 pistol x H4 LightRifle / H4 Magnum), per MODE: the burst per round "
                   "and per burst CYCLE (2/30 + 0.3 = 0.367 s, the BR's assumption), the scoped shot per "
                   "shot. The only candidate whose every value scales (Sniper: Flood combat forms 35 s "
                   "on the sniper bullet's table, the burst as strong as the AR; AR: 87 dps). Modes: C "
                   "(the scoped shot on the grenade key), A as the fallback"),
        # DEFAULT = Halo 4's own numbers; these are the BALANCED rows. Halo 4: LightRifle / Magnum (5.33
        # x3 a burst every 0.367 s, 23.5 a shot every 0.4 s / 15 every 0.2 s; 36 / 8; 108 / 24; 144 /
        # 40; 73 / 50 fr; 3000 / 3000 wu/s; 250 / 250; aim 2.25/20 5/20 both (mode blocks); error
        # 0.15 flat (burst), 0.15 -> 0.5 (scoped) / 0.15 -> 1.75)
        'balanced': {
            'damage': 8.89,              # 25 x 5.33/15 a burst round
            'damage_scoped': 39.17,      # 25 x 23.5/15
            'bursts_per_second': 1.91,   # 3.5/s x 2.727/5 (cycle 0.524 s)
            'scoped_per_second': 1.75,   # 3.5/s x 2.5/5
            'magazine': 54,              # 12 x 36/8
            'rounds_total_initial': 270,  # 60 x 108/24
            'rounds_total_maximum': 432,  # 120 x 144/40 (no dual wield in Halo 4: no x1.5)
            'reload_s': 3.26,            # 67 fr x 73/50
            'velocity': 300.0,           # 300 x 3000/3000
            'range': 40.0,               # 40 x 250/250
            'aim': (3.0, 30.0, 6.0, 30.0),   # x1: the same mode block both sides
            'zoom': 3.0,                 # the magnum 2x, the pistol 2x -> Halo 4's own 3x
            'melee': None},              # Halo 4 shares strike_melee: x1
        'measured': 'h1_role_compare.py lightrifle',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\storm_forerunner_rifle\\storm_forerunner_rifle',
            'provisional': 'Pistol',
            'alternatives': ['Sniper Rifle', 'Assault Rifle'],
            'direct': None,
            'peers': ['Pistol', 'Sniper Rifle', 'Assault Rifle', 'Battle Rifle (port)', 'DMR (port)'],
            'why': 'magazine 36, 3x zoom, near-instant precision; unscoped 3-burst, scoped 3-round single shot',
            'lacks': ("the scoped mode (Halo 4: ONE 23.5 shot for 3 rounds at 2.5/s when zoomed, its own "
                      "projectile and large fly-by) -- Halo 1's zoom cannot switch a trigger, and the "
                      "grenade-key trigger (option C) failed in boot 1; Halo 4's 0.3 s burst recovery "
                      "(tapping sets the cycle); sprint")}},
    # step 11 (filled at step 11): Halo 4's ai\generic LightRifle entry (m020) over a base
    firing_profile={'mode': 'source', 'from_game': 'Halo 4', 'from_map': 'halo4\\maps\\m020.map',
                    'from_weapon': 'objects\\weapons\\rifle\\storm_forerunner_rifle\\storm_forerunner_rifle'},
)

PORT.update({
    'status': 'in progress',

    # geometry + look (h1_h3_weapon_model.py; Halo 4 through h4_tags). ONE render model for world AND
    # first person: 8 nodes (b_gun root), regions `default` (mesh 0: 3463 verts) + `knight` (mesh 1: 9471
    # verts) -- both drawn on the player's gun; the sku / industrial skins are empty. Materials: body
    # (srf_char_blinn_reflection_selfillum: diff + control + normal + cube), body_alien
    # (srf_char_blinn_reflection, + a detail map), glow_blinn (self-illum: si (1, 0.47, 0) x20,
    # albedo (1, 0.64, 0) x5 -- Forerunner orange). The SHIPPED materials (h4_cache_refs m020): body /
    # body_alien name the H4EK maps; glow_blinn the sku_diff (a camo skin) -- the glow is drawn as
    # additive islands anyway. Markers: primary_trigger (Halo 1's 'primary trigger'), focus_port,
    # front / rear / scope hardlight, iris_blade ...
    'model': {
        'dir': r'weapons\light rifle',
        'world': H4 + SW + r'\storm_forerunner_rifle.render_model',
        'fp': H4 + SW + r'\storm_forerunner_rifle.render_model',
        'world_name': 'light rifle',
        'decimate': {'keep': 60.0, 'protect': 1.0, 'views': [((-0.0722, 0.0555, 0.0691), (0.9962, -0.0359, -0.0788), (0.0788, -0.0017, 0.9969), 1.0), ((-0.0725, 0.0551, 0.0696), (0.9967, -0.0366, -0.073), (0.0727, -0.0099, 0.9973), 1.0), ((-0.0722, 0.0555, 0.0691), (0.9962, -0.0359, -0.0788), (0.0788, -0.0017, 0.9969), 1.0), ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), 1.0), ((0.0, 0.0, 0.0), (1.0, 0.0076, -0.0063), (0.0064, -0.0128, 0.9999), 1.0), ((0.0, 0.0, 0.0), (1.0, -0.0026, 0.0031), (-0.0031, 0.0032, 1.0), 1.0), ((-0.0722, 0.0555, 0.0691), (0.9962, -0.036, -0.0788), (0.0788, -0.0018, 0.9969), 1.0), ((-0.0666, 0.055, 0.0691), (0.9955, -0.0276, -0.0907), (0.0908, 0.0039, 0.9959), 1.0), ((-0.0722, 0.0555, 0.0691), (0.9962, -0.036, -0.0788), (0.0788, -0.0018, 0.9969), 1.0), ((-0.0584, 0.065, 0.1224), (0.6784, -0.3657, 0.6372), (-0.6856, -0.0037, 0.7279), 0.5), ((-0.0574, 0.0527, 0.0722), (0.996, -0.0283, -0.0847), (0.0815, -0.0975, 0.9919), 0.5), ((-0.0584, 0.065, 0.1224), (0.6784, -0.3657, 0.6372), (-0.6856, -0.0037, 0.7279), 0.5), ((-0.0722, 0.0555, 0.0691), (0.9962, -0.0359, -0.0788), (0.0788, -0.0017, 0.9969), 0.5), ((-0.0371, 0.1266, 0.1093), (0.6865, -0.6955, -0.212), (-0.2586, -0.5061, 0.8228), 0.5), ((-0.0722, 0.0555, 0.0691), (0.9962, -0.0359, -0.0788), (0.0788, -0.0017, 0.9969), 0.5), ((-0.0824, 0.0556, 0.0709), (0.9985, -0.0485, -0.0235), (0.0225, -0.0213, 0.9995), 0.5), ((-0.0379, 0.1261, 0.1057), (0.6842, -0.697, -0.2145), (-0.2532, -0.5029, 0.8264), 0.5), ((-0.0824, 0.0556, 0.0709), (0.9985, -0.0485, -0.0235), (0.0225, -0.0213, 0.9995), 0.5), ((-0.0722, 0.0555, 0.0691), (0.9962, -0.0359, -0.0788), (0.0788, -0.0017, 0.9969), 0.5), ((-0.0901, -0.063, 0.1958), (-0.0677, 0.0492, -0.9965), (0.0117, -0.9987, -0.0501), 0.5), ((-0.0722, 0.0555, 0.0691), (0.9962, -0.0359, -0.0788), (0.0788, -0.0017, 0.9969), 0.5)]},
        # + the scope's hardlight marker (on b_scope): the node the display glow card rides on
        'markers': {'primary_trigger': 'primary trigger', 'scope_hardlight': 'scope hardlight'},
        'ground_point': 'auto',
        # an own hull (the template's hides the world model, C1): the render model's extent (x
        # -0.086..0.327, y +-0.017, z -0.014..0.091)
        'collision': {'material': 'metal',
                      'boxes': [((-0.086, -0.017, -0.014), (0.327, 0.017, 0.091))]},
        # Halo 1's `tool model` keeps 31 characters of a shader name (C1)
        'material_names': {'storm_forerunner_rifle_body': 'lr_body',
                           'storm_forerunner_rifle_body_alien': 'lr_alien',
                           'storm_forerunner_rifle_glow_blinn': 'lr_glow'},
        'shaders': {'lr_body': (BASE + 'lr_body_base.png', None),
                    'lr_alien': (BASE + 'lr_body_base.png', None)},
        'template': r'weapons\assault rifle\fp\shaders\gun',
        'glow': {},
        # the glow material: an additive glow per UV island in the Forerunner orange (the Boltshot's
        # tuned settings; `hot` off -- tiny islands saturate white)
        # BOOT 1 (user: 'the glow parts can be improved, reference the display of the boltshot'; the
        # user's Halo 4 idle screenshot: the scope's rear HEXAGON lit hard orange with a yellow core and
        # a wide bloom, the left-side strip lit end to end). The glow material's 23 islands (2026-10-15):
        # #8 = the scope's rear hexagon (x 4.09, z 8.38 cm, 0.76 x 0.34, facing the player), #0 = the
        # left-side strip (3.4 cm at x 9.8), small slits / rings / the muzzle iris discs the rest
        'glow_shaders': {'lr_glow': {'rgb': ORANGE, 'additive': True, 'islands': True,
                                     'islands_of': 'storm_forerunner_rifle_glow_blinn',
                                     'gain': 2.2, 'falloff': 0.35, 'radius': 1.3, 'hot': False},
                         # the halo (the Suppressor's bloom stand-in): a soft wide strip glow on cards
                         'lr_halo': {'rgb': ORANGE, 'additive': True, 'islands': True,
                                     'islands_of': 'storm_forerunner_rifle_glow_blinn',
                                     'strip': True, 'gain': 0.8, 'falloff': 1.5, 'radius': 1.0,
                                     'hot': False},
                         # the Boltshot's display glow: a static radial card in the hexagon's plane
                         'lr_display_glow': {'rgb': (1.0, 0.62, 0.15), 'additive': True, 'radial': True,
                                             'falloff': 1.6},
                         # BOOT 2 (user: 'like every Forerunner weapon it lights up when firing'): the
                         # same pieces again, hotter and wider, FADED by A out = the pistol template's
                         # firing ILLUMINATION (on per shot, back to 0 over the 0.08 s illumination
                         # recovery) -- the Boltshot's charge glow, keyed to the shot
                         'lr_fire_glow': {'rgb': (1.0, 0.75, 0.3), 'additive': True, 'islands': True,
                                          'islands_of': 'storm_forerunner_rifle_glow_blinn',
                                          'strip': True, 'gain': 2.0, 'falloff': 0.8, 'radius': 1.3,
                                          'hot': False, 'fade_source': 'A_out'},
                         'lr_fire_display': {'rgb': (1.0, 0.75, 0.3), 'additive': True, 'radial': True,
                                             'falloff': 1.2, 'fade_source': 'A_out'}},
        # ONE card 0.1 cm in front of the hexagon (normal -0.99 / 0 / -0.14), 1.3 cm: the lens + its
        # bloom; + the firing flare there, 2.4 cm, 0.05 cm further out
        'glow_points': [{'marker': 'scope hardlight', 'shader': 'lr_display_glow', 'size': 1.3,
                         'at': (3.99, 0.0, 8.37), 'normal': (-0.99, 0.0, -0.14)},
                        {'marker': 'scope hardlight', 'shader': 'lr_fire_display', 'size': 2.4,
                         'at': (3.94, 0.0, 8.36), 'normal': (-0.99, 0.0, -0.14)}],
        # halo cards x2 ACROSS each side strip / slit (the Suppressor's `along` 1.05); none on the
        # pieces facing along the barrel (the hexagon, rings, iris discs: +-x). The firing cards: EVERY
        # piece (the muzzle iris and rings light up too), x2.6
        'glow_cards': {'lr_halo': {'of': 'lr_glow', 'shader': 'lr_halo', 'scale': 2.0, 'along': 1.05,
                                   'lift': 0.05, 'skip_piece_normals': [(1.0, 0.0, 0.0), (-1.0, 0.0, 0.0)],
                                   'skip_piece_dot': 0.9, 'round_scale': 1.4},
                       'lr_fire': {'of': 'lr_glow', 'shader': 'lr_fire_glow', 'scale': 2.6, 'along': 1.1,
                                   'lift': 0.08, 'round_scale': 1.8}},
    },

    # FP animations (h1_fp_retarget.py): ROUTE (a), Halo 4's own storm_fp_forerunner_rifle (Foundry,
    # h4_fp_dump.py -> out\h4_fp), the arms RE-SOLVED. 25 animations (frames incl. the end key): fire_1
    # var1 / var2 19 (one per BURST in Halo 4), idle 101, posing var1 / var2 95, ready 25
    # (ready_initial 30), put_away 5, melee_strike_1 35 (primary keyframe 4) / _2 37, reload_full 65
    # (primary 44) / reload_empty 74 (primary 48), throw_grenade 45, moving 21 / look 10 (overlays),
    # first_time_pickup 133; sprint / jump / land / fall / acceleration_screens: no Halo 1 state.
    # NO zoomed fire (the scoped shot is not reproduced: option A, boot 2)
    'retarget': {
        'graph': H4 + SFP + '.model_animation_graph',
        'render_model': H4 + SW + r'\storm_forerunner_rifle.render_model',
        'nodes': {n: 'frame b ' + n.replace('_', ' ') for n in GUN},
        'drop_nodes': tuple(DROP),
        'h1_dir': r'weapons\light rifle\fp',
        'h1_model': r'weapons\light rifle\fp\fp',
        'align': 'same_space',
        # BOOT 1 (user: 'FP needs to go down 2 units'; 1 unit = 0.01 wu)
        'view_offset': (0.0, 0.0, -0.02),
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

    # Halo 4's own sounds (h1_port_sounds.py lightrifle, `bank` 'halo4'). The player bank
    # homing_rifle_player (the weapon's .sound tags name homing_rifle; the FP graph's frame_event_list
    # for the animation cues). fire = play_weapons_storm_homing_rifle_player_fire: 5 random rounds
    # (0.43-0.63 s) + a 33 ms haptic click (5: dropped) -- BOTH barrels fire it (one firing effect);
    # dry fire 1; zoom in / out 2 each; ready = wea_lightrifle_ready (3 variants); melee_strike_1 =
    # wea_lightrifle_melee_1; BOTH reloads play the reload_empty foley (Halo 4's reload_full names it
    # too); posing var1 = idle_b part 1 @0 + part 2 @60; the drop = wea_drop_rifle_shotgun_nonplayer
    # (in this bank). The ammo pickup event (homing_rifle_ammo_pickup) is in NO bank: the pistol's
    # kept (Boltshot). Levels = the stock Halo 1 PISTOL sound each stands in for (battle_rifle.py)
    'sounds': {
        'catalog': 'LightRifle',
        'bank': 'halo4',
        'wwise_bank': 'homing_rifle_player',
        'dir': B.join(['sound', 'weapons', 'light_rifle_port']),
        'sounds': {
            # BOOT 1 (user: 'the fire sound seems odd, is that the right sound?'): NO -- the event walk
            # reached only a quiet detail container (5 x 0.45 s at -25 dB rms). The fire event's real
            # sounds sit behind a SWITCH (0x2d68b28b, not followed) of two blends: A 0x16f8196 = a
            # random of 3 (0x243a38a5, 1.0-1.4 s) + a blend of a random of 3 (0x24703240) and a random of
            # 2 (0x25a3b2c9) + a 0.55 s crack (0x312206ad) -- the shorter, per-round set; C 0x286f00ae
            # (2.2-3.2 s layers, heavier: taken for the scoped shot, not ported). Eleven more targets
            # (four of A's sequence pieces) exist in no MCC bank. `obj_<id>` = every sound under one
            # container (h4_wwise.extract_object); the four entries are LAYERS, each a random
            'lr_fire': (['obj_243a38a5', 'obj_24703240', 'obj_25a3b2c9', 'obj_312206ad'],
                        'sound\\sfx\\weapons\\pistol\\fire', -12.8),
            'lr_dryfire': (['play_wea_light_rifle_player_dry_fire_empty'],
                           'sound\\sfx\\weapons\\pistol\\dryfire', -15.3),
            'lr_ready': (['play_wea_lightrifle_ready'],
                         'sound\\sfx\\weapons\\weapon_anims\\pistol_ready', -15.2),
            'lr_melee': (['play_wea_lightrifle_melee_1'],
                         'sound\\sfx\\weapons\\weapon_anims\\pistol_melee', -19.8),
            'lr_reload': (['play_npc_storm_fp_forerunner_rifle_foley_first_person_reload_empty'],
                          'sound\\sfx\\weapons\\weapon_anims\\pistol_reload', -19.0),
            'lr_pose': (['play_wea_lightrifle_idle_b_part_1', 'play_wea_lightrifle_idle_b_part_2'],
                        'sound\\sfx\\weapons\\weapon_anims\\pistol_posing', -26.5),
            'lr_zoom_in': (['play_weapons_storm_homing_rifle_player_zoom_in'],
                           'sound\\sfx\\weapons\\sniper rifle\\sniper_2x_zoom', -28.9),
            'lr_zoom_out': (['play_weapons_storm_homing_rifle_player_zoom_out'],
                            'sound\\sfx\\weapons\\sniper rifle\\sniper_10x_zoom', -29.2),
            'lr_drop': (['play_wea_drop_rifle_shotgun_nonplayer'],
                        'sound\\sfx\\impulse\\weapon_drops\\pistol_impact', -28.8),
            'lr_flyby': (['play_proj_forerunner_whizby_small@proj_forerunner_whizby_small'],
                         'sound\\sfx\\impulse\\impacts\\plasrif_projectile', -26.2),
            # the Suppressor's Forerunner impact (plasma impact + the forerunner sweetener)
            'lr_impact': (['play_wea_plasma_impact_dirt@plasma_impact_generic',
                           'play_wea_forerunner_impact_generic@forerunner_impact_sweetener'],
                          'sound\\sfx\\weapons\\plasma rifle\\plasmahit', -11.3),
            # the BALANCED reload's sound (the patcher retimes the reloads and swaps it in)
            'lr_reload_balanced': (['play_npc_storm_fp_forerunner_rifle_foley_first_person_reload_empty'],
                                   'sound\\sfx\\weapons\\weapon_anims\\pistol_reload', -19.0),
        },
        'offsets': {'lr_pose': [0.0, 60 / 30.0]},
        'stretch': {'lr_reload_balanced': 97.8 / 74.0},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only lightrifle) on a COPY of the Halo 1 PISTOL (the
    # yardstick: magazine, reload, zoom, HUD, melee, bullet materials) + a SECOND TRIGGER (a copy of
    # trigger 0, `add_triggers`; BOOT 1: dropped -- option A). DEFAULT = HALO 4's OWN NUMBERS; the pistol-ratio values are the
    # balance rows. STEP 6, the ammo pickup: the template's magazine names `powerups\pistol ammo`;
    # Halo 4 gives none (Forerunner ammo boxes: rounds 0) -> the H1 pistol's pickup : initial (the
    # Boltshot's 120 : 60) on Halo 4's 108 = 216
    'pickable': {
        'weapon': LR + 'light rifle',
        'template': PISTOL + 'pistol',
        'world_model': LR + 'light rifle',
        # ONE model tag for world AND first person (Halo 1's 32 MiB model buffer: plan 0.1)
        'fp_model': LR + 'light rifle',
        'fp_anims': LR + 'fp\\fp',
        'label': 'lr',
        'teach': ('lr', 'ar'),
        'keys': {'first-person melee': 4},          # Halo 4 melee_strike_1 primary keyframe 4
        'sounds': {'first-person ready': SND + 'lr_ready',
                   'first-person posing': SND + 'lr_pose',
                   'first-person melee': SND + 'lr_melee',
                   'first-person reload-empty': SND + 'lr_reload',
                   'first-person reload-full': SND + 'lr_reload'},
        # THE BURST ROUND (trigger 0): Halo 4 storm_forerunner_rifle 5.33 (lower = upper), plasma_fast
        # (= bullet_slow in Halo 4: the pistol bullet's table, C1), acceleration 0.2, 3000 wu/s flat,
        # range 250, no gravity
        'bullet': {'projectile': (PISTOL + 'bullet', LR + 'bolt'),
                   'damage': (PISTOL + 'bullet', LR + 'bolt'),
                   'dmg': 5.333, 'acceleration': 0.2, 'velocity': 3000.0, 'range': 250.0,
                   'proj_fields': {'proj_attrs.physics.flyby_sound.filepath': SND + 'lr_flyby'},
                   'fields': dict(JPT_FIELDS),
                   # every hard-surface impact the pistol bullet plays -> Halo 4's Forerunner impact
                   # (the Suppressor's: plasma impact + the forerunner sweetener); flesh, shield and
                   # water hits stay the game's
                   'impact_tint': IMPACT_SOUNDS,
                   # THE HIT-EFFECT RULE: a burst lands 3 rounds 1/30 s apart -> the tag rate 30/s
                   'impact_thin': {'materials': [22], 'out': LR + 'effects\\impact\\',
                                   'thin': {}, 'rate': 30.0},
                   },
        # THE BURST (the Battle Rifle's option B2, user 2026-10-07): charge 1 tick + discharge + spew,
        # one burst a pull (Halo 4's latch). Halo 4: 3 rounds 1/30 s apart -> 30/s; the BR's measured
        # rule (rounds = spew ticks / spacing ticks + 2) gives 3 rounds at a 1-tick spew. Halo 4's 0.3
        # s recovery is not reproduced (the BR: tapping sets the cycle)
        # BOOT 1 (the secondary, option A): 30/s with a 1-tick spew fired ONE round a pull, not 3.
        # BOOT 2 tested two spews in one boot at 30/s: 2 ticks fired 1 round, 3 ticks 2 rounds; the
        # user tuned it in game: spew 0.15 s = EXACTLY 3 rounds (the Battle Rifle's 0.15 at 10/s gave
        # 3 too -- OBSERVATION: the burst's round count follows the spew time more than the rate)
        'trigger': {'rounds_per_second': (30.0, 30.0), 'acceleration_time': 0.0,
                    'deceleration_time': 0.0,
                    'charging_time': 1 / 30.0, 'overcharged_action': 'discharge',
                    'spew_time': 0.15, 'does_not_repeat_automatically': True,
                    # Halo 4 bloom: deceleration 0.7 (acceleration none)
                    'error_acceleration_time': 0.0, 'error_deceleration_time': 0.7},
        # Halo 4: minimum error 0, error angle 0.15 flat (burst)
        'error_deg': {'minimum_error': 0.0, 'error_angle': (0.15, 0.15)},
        # Halo 4: 36 loaded, 108 at pickup, 144 most. Reload time: Halo 4 none (the animation's 73 fr
        # = 2.43 s) in the H1 pistol's shape (2.17 tag over its 2.23 s animation) = 2.37
        'magazine': {'rounds_loaded_maximum': 36, 'rounds_reloaded': 36,
                     'rounds_total_initial': 108, 'rounds_total_maximum': 144,
                     'reload_time': 2.43 * 2.17 / 2.23},
        # Halo 4 aim assist: the MODE block (the live one), absolute
        'aiming': {'autoaim_angle': 2.25, 'autoaim_range': 20.0,
                   'magnetism_angle': 5.0, 'magnetism_range': 20.0},
        'fields': {
            # Halo 4's 3x (the pistol's 2x)
            'weap_attrs.aiming.zoom_levels': 1,
            'weap_attrs.aiming.zoom_ranges': (3.0, 3.0),
            'weap_attrs.interface.zoom_in_sound.filepath': SND + 'lr_zoom_in',
            'weap_attrs.interface.zoom_out_sound.filepath': SND + 'lr_zoom_out',
            'item_attrs.collision_sound.filepath': SND + 'lr_drop',
            'weap_attrs.magazines.0.magazine_items.0.rounds': 216,
            'obje_attrs.collision_model.filepath': LR + 'light rifle',
            # STEP 4b list 2 (ratio onto the pistol): active camo ding 0.65 x 0.25/0.6 = 0.27,
            # illumination recovery 0.1 x 0.04/0.05 = 0.08 (both triggers); aim, magazine and error =
            # Halo 4's own (the default). List 3: deviation angle 0 kept (the template's: the
            # Suppressor's), sort order / ai scariness / falloff ranges no Halo 1 field
            'weap_attrs.interface.active_camo_ding': 0.65 * 0.25 / 0.6,
            'weap_attrs.triggers.0.misc.illumination_recovery_time': 0.08,
        },
        'sound_effects': {
            'firing_effect': (PISTOL + 'effects\\fire bullet', LR + 'effects\\fire bolt',
                              {r'sound\sfx\weapons\pistol\fire': SND + 'lr_fire'},
                              # THE MUZZLE-FLASH RULE (closing check 10, before boot 1). Halo 4's
                              # homingrifle_firing: NO flash sprite -- a lens flare + screen effect,
                              # a core_energy tracer and an orange muzzle_glow_1p light volume at
                              # primary_trigger, sparks at the hardlight markers; no smoke, no casing.
                              # The pistol's (h1_effect_particles): the on-axis FP centre flash
                              # 0.045-0.056 (KEPT, tinted orange: the glow's stand-in), two side
                              # flashes at +-0.023 (dropped), FP smoke (dropped), casing + eject
                              {'match': 'flash', 'drop_off_axis': 0.012, 'scale': 1.0,
                               'drop_particles': ('casing', 'smoke h fp'),
                               'drop_parts': (r'sound\sfx\weapons\pistol\eject',),
                               'tint': (1.0,) + ORANGE}),
            'empty_effect': (PISTOL + 'effects\\empty', LR + 'effects\\empty',
                             {r'sound\sfx\weapons\pistol\dryfire': SND + 'lr_dryfire'})},
        'melee': (PISTOL + 'melee', LR + 'melee'),
        'melee_response': PISTOL + 'melee_response',
        'messages': ('Picked up a light rifle', 'Picked up %d rounds for light rifle'),
        'icon': 'light rifle',
        'extra_sounds': [SND + 'lr_reload_balanced'],
        # the PISTOL's HUD with Halo 4's crosshair (forerunner_rifle.cui_screen, the visible widgets:
        # four `outer_l` corners 16 x 8 at opacity 0.85 -- top_left (-22, -14), top_right (6.5, -14)
        # flip x, bottom_left (-22, 7) flip x, bottom_right (6.5, 7) -- and `inner` top (-8, -8) /
        # bottom (-8, 0) flip y at 0.6; offsets = widget centres, the Suppressor's calibration). The
        # side / chip ticks are opacity 0 (animated in Halo 4, not drawn at rest). Boot 1: 'crosshair is
        # good'.
        # THE SCOPE (boot 2, user: 'orange overlays'): Halo 4's zoomed scope is POLYART (3D vector
        # frames, forerunner_rifle_scope), drawn orange with translucent panels and no darkening /
        # blur. h4_polyart_scope.py rasterized the pieces (wires 1.0, holo fills 0.6) and fitted them to
        # the user's zoomed 1080p screenshot (scale x 1.05 / y 0.975, 112 px up: the CUI's parallax /
        # zoom-in animation), cut into four 480 x 270 quadrants (a sheet px = 2 screen px):
        #   python h4_polyart_scope.py "<SCOPE>" ui\hud\weapons\forerunner\forerunner_rifle\polyart
        #     --wires main_wire,main_wire_inner,outer_holo_wires,inner_holo_wires,ring_wire,main_hatch_wire,
        #             ghost_wire_close,ghost_wire_mid,lower_accent_wire,upper_accent_wire,range_box
        #     --fills outer_holo,inner_holo,main_hatch_extrusion,hatch_a,hatch_b,hatch_c,range_box_ghost
        #     --fill-alpha 0.6 --xform 1.05,0.975,0,-112
        # Each quadrant = a coloured zoom glyph (the Needle Rifle's recipe) at the reserved hud_reticles
        # 68-71, registered at its inner corner (the screen centre), overlay x4 (0.5 screen px a sheet
        # px at x1). The mask: CLEAR (no chud), the pistol's zoom readouts dropped
        'hud': {'donor': PISTOL + 'pistol', 'out': LR + 'light rifle',
                'scope': {'out': LR + 'bitmaps\\scope_mask', 'size': 256, 'alpha': 0},
                'zoom_glyphs': [{'image': SCOPE + q + '.png', 'reg': reg, 'name': 'light rifle scope ' + q,
                                 'index': i, 'scale': (1.0, 1.0), 'overlay': 4.0, 'offset': (0, 0),
                                 'rgb': (255, 120, 30), 'alpha': 1.0}
                                for q, reg, i in (('tl', (480, 270), 68), ('tr', (0, 270), 69),
                                                  ('bl', (480, 0), 70), ('br', (0, 0), 71))],
                'reticle': (H4 + LRUI + 'outer_l', 0, 'light rifle'),
                'reticle_xform': {'offset': (-14.0, -10.0), 'gain': 0.85},
                'reticle_layers': [(H4 + LRUI + 'outer_l', 0, 1.0, {'flip_x': True, 'offset': (14.5, -10.0), 'gain': 0.85}),
                                   (H4 + LRUI + 'outer_l', 0, 1.0, {'flip_x': True, 'offset': (-14.0, 11.0), 'gain': 0.85}),
                                   (H4 + LRUI + 'outer_l', 0, 1.0, {'offset': (14.5, 11.0), 'gain': 0.85}),
                                   (H4 + LRUI + 'inner', 0, 1.0, {'offset': (0.0, -4.0), 'gain': 0.6}),
                                   (H4 + LRUI + 'inner', 0, 1.0, {'flip_y': True, 'offset': (0.0, 4.0), 'gain': 0.6})],
                'reticle_split': 1,
                'reticle_min_width': 2,
                'reticle_supersample': 2,
                'reticle_scale': 1.6, 'reticle_overlay': 1.5 / (123 / 97.0 * 1.6 * 2 * 0.75),
                'flash_base': 12,                # the pistol's low-ammo cutoff is of 12
                # BOOT 2 (user: '36 small ticks -- the Halo 4 art is 36, the rows just look different'):
                # Halo 4's three segment strips (top pointed, middle / bottom square; 12 columns), a
                # column = one 3-round shot (ammo_meter `rows`), at their native density
                'ammo_meter': {'sizes': (36, 54), 'base': LR + 'bitmaps\\light_rifle_ammo',
                               'art': {'rows': [(H4 + LRUI + 'ammo_lightrifle_top', 0),
                                                (H4 + LRUI + 'ammo_lightrifle_middle', 0),
                                                (H4 + LRUI + 'ammo_lightrifle_bottom', 0)],
                                       'native': True}}},
        'palette_levels': LEVELS,
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py lightrifle). DEFAULT = Halo 4's own
    # numbers in the tags; BALANCED = the PISTOL ratio per mode (step 4a, user 2026-10-15). Assembly
    # Halo1 units: angles in degrees, velocity in wu per TICK (3000 wu/s = 100; 300 = 10)
    'catalog': {
        'entry': {
            'weapon': 'LightRifle', 'source': 'Halo 4', 'donor': 'Pistol', 'default_on': False,
            'desc': "Halo 4's LightRifle: its model, first-person animations, sounds and numbers. A "
                    "36-round Forerunner rifle firing 3-round bursts, with a 3x zoom (Halo 4's "
                    "stronger scoped shot is not reproduced). Pistol ammo tops it up.",
            'balance_desc': "Measured against the Pistol, which both games have: 8.9 damage a burst "
                            "round, a 54 magazine, 270 at the start "
                            "/ 432 most, a 3.3 s reload, a slower bolt (300 wu/s), 40 wu range and "
                            "Halo 1-style aim assist.",
            # step 9: the balanced reload, H1 pistol 67 fr x 73/50 = 97.8 fr over the BUILT 74 (reload
            # empty; ONE multiplier) = x1.32; swap: H1 pistol ready 35 fr x 25/16 (Halo 4 LightRifle /
            # Magnum ready) = 54.7 over the built 25 = x2.19
            'anims': {'reload': 97.8 / 74.0, 'swap': 2.19},
            'anim_sounds': {'reload': [{'mult': 97.8 / 74.0, 'from': SND + 'lr_reload',
                                        'to': SND + 'lr_reload_balanced'}]},
            'balance': [
                row('jpt!', LR + 'bolt', 'Damage Lower Bound', 8.89, 5.333, 'Bullet Damage'),
                row('jpt!', LR + 'bolt', 'Damage Upper Bound', 8.89, 5.333, 'Bullet Damage'),
                row('jpt!', LR + 'bolt', 'Damage Upper Bound Max', 8.89, 5.333, 'Bullet Damage'),
                row('weap', LR + 'light rifle', 'Rounds Loaded Maximum', 54.0, 36.0, 'Magazine', block='Magazines'),
                row('weap', LR + 'light rifle', 'Rounds Reloaded', 54.0, 36.0, 'Magazine', block='Magazines'),
                row('weap', LR + 'light rifle', 'Rounds Total Initial', 270.0, 108.0, 'Magazine', block='Magazines'),
                row('weap', LR + 'light rifle', 'Rounds Total Maximum', 432.0, 144.0, 'Magazine', block='Magazines'),
                # STEP 6 balanced: the pistol's pickup : initial (2 : 1) on the balanced 270
                row('weap', LR + 'light rifle', 'Rounds', 540, 216, 'Ammo pickup', block='Magazines/Magazines'),
                # error (pistol 0.2 -> 2.0 x LightRifle / Magnum): the burst's 0.15 flat against 0.15 ->
                # 1.75 inverts the minimum -> the maximum's ratio (the Suppressor's rule): 0.017 -> 0.17
                dict(row('weap', LR + 'light rifle', 'Error Angle', 0.017, 0.15, 'Error Angle', block='Triggers'), index=0),
                dict(row('weap', LR + 'light rifle', 'Error Angle Max', 0.17, 0.15, 'Error Angle', block='Triggers'), index=0),
                row('proj', LR + 'bolt', 'Initial Velocity', 10.0, 100.0, 'Projectile'),
                row('proj', LR + 'bolt', 'Final Velocity', 10.0, 100.0, 'Projectile'),
                row('proj', LR + 'bolt', 'Maximum Range', 40.0, 250.0, 'Projectile'),
                row('weap', LR + 'light rifle', 'Autoaim Angle', 3.0, 2.25, 'Autoaim'),
                row('weap', LR + 'light rifle', 'Autoaim Range', 30.0, 20.0, 'Autoaim'),
                row('weap', LR + 'light rifle', 'Magnetism Angle', 6.0, 5.0, 'Magnetism'),
                row('weap', LR + 'light rifle', 'Magnetism Range', 30.0, 20.0, 'Magnetism'),
                # the 54 magazine's meter: light_rifle_ammo sequence 1 (ammo_meter 36 54), step 4;
                # low-ammo flash 12 of 36 -> 18 of 54 (the BR's)
                dict(row('wphi', LR + 'light rifle', 'Sequence Index', 1, 0, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', LR + 'light rifle', 'Alpha Multiplier', 4, 7, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', LR + 'light rifle', 'Sequence Index', 1, 0, 'Ammo display', block='Static Elements'), index=0),
                dict(row('wphi', LR + 'light rifle', 'Loaded Ammo Cutoff', 18, 12, 'Ammo display'), index=0),
            ]},
    },

    # step 4b (port_field_audit.py --port lightrifle): the source pair (Halo 4 LightRifle vs the
    # yardstick, Halo 4's Magnum) against the target pair (the H1 port vs its template = the H1 pistol)
    'field_audit': {
        'source_kit': 'H4EK',
        'source': {'weapon': (SW + r'\storm_forerunner_rifle.weapon',
                              r'objects\weapons\pistol\storm_magnum\storm_magnum.weapon'),
                   'projectile': (SW + r'\projectiles\storm_forerunner_rifle.projectile',
                                  r'objects\weapons\pistol\storm_magnum\projectiles\storm_magnum_bullet.projectile'),
                   'damage_effect': (SW + r'\projectiles\damage_effects\storm_forerunner_rifle.damage_effect',
                                     r'objects\weapons\pistol\storm_magnum\projectiles\storm_magnum_bullet.damage_effect')},
        'target': {'weapon': (LR + 'light rifle.weapon', PISTOL + 'pistol.weapon'),
                   'projectile': (LR + 'bolt.projectile', PISTOL + 'bullet.projectile'),
                   'damage_effect': (LR + 'bolt.damage_effect', PISTOL + 'bullet.damage_effect')}},

    # the dry test: a30 (this session's level, parallel pair 4), Halo 4's own loadout (36 + 108)
    'test': {'level': 'a30', 'rounds': (36, 108), 'grunt': None, 'elite': None},
})
