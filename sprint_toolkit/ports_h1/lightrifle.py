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
SND = 'sound\\weapons\\light_rifle_port\\'
PISTOL = 'weapons\\pistol\\'
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']
# Forerunner hardlight orange: the glow material's si_color (1, 0.47, 0) x20 / albedo (1, 0.64, 0)
ORANGE = (1.0, 0.6, 0.1)

# the Storm Rifle's DROP list: every storm_fp graph shares the skeleton (checked 2026-10-15: this
# graph's 88 bones = the same 80 arm / camera nodes + the render model's 8 gun bones)
from .storm_rifle import DROP  # noqa: E402

# the render model's 8 nodes, all animated by the FP graph
GUN = ('gun', 'scope', 'cartridge', 'top_main', 'center', 'front_main', 'top', 'ammo')

PORT = reserved(
    order=29, wave='C4', name='LightRifle', source='Halo 4',
    messages=(91, 92), icon=49, reticle=38, label='lr', teach_from='ar',
    sound_dir='sound\\weapons\\light_rifle_port', weapon_dir='weapons\\light rifle',
    yardstick={
        # step 4a (user, 2026-10-15; h1_role_compare.py lightrifle)
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
            'lacks': ("the zoom-gated mode switch (C: the scoped shot on the grenade key, not on zoom; no "
                      "grenades while held), Halo 4's 0.3 s burst recovery (tapping sets the cycle), sprint")}},
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
        'markers': {'primary_trigger': 'primary trigger'},
        'ground_point': 'auto',
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
        'glow_shaders': {'lr_glow': {'rgb': ORANGE, 'additive': True, 'islands': True,
                                     'islands_of': 'storm_forerunner_rifle_glow_blinn',
                                     'gain': 2.2, 'falloff': 0.35, 'radius': 1.3, 'hot': False}},
    },

    # FP animations (h1_fp_retarget.py): ROUTE (a), Halo 4's own storm_fp_forerunner_rifle (Foundry,
    # h4_fp_dump.py -> out\h4_fp), the arms RE-SOLVED. 25 animations (frames incl. the end key): fire_1
    # var1 / var2 19 (one per BURST in Halo 4), idle 101, posing var1 / var2 95, ready 25
    # (ready_initial 30), put_away 5, melee_strike_1 35 (primary keyframe 4) / _2 37, reload_full 65
    # (primary 44) / reload_empty 74 (primary 48), throw_grenade 45, moving 21 / look 10 (overlays),
    # first_time_pickup 133; sprint / jump / land / fall / acceleration_screens: no Halo 1 state.
    # NO zoomed fire: the scoped shot (trigger 1) plays fire_1 var2 as Halo 1's fire-2
    'retarget': {
        'graph': H4 + SFP + '.model_animation_graph',
        'render_model': H4 + SW + r'\storm_forerunner_rifle.render_model',
        'nodes': {'b_' + n: 'frame b ' + n.replace('_', ' ') for n in GUN},
        'drop_nodes': tuple(DROP),
        'h1_dir': r'weapons\light rifle\fp',
        'h1_model': r'weapons\light rifle\fp\fp',
        'align': 'same_space',
        'anims': {
            'first_person:idle': 'first-person idle',
            'first_person:posing:var1': 'first-person posing',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:fire_1:var1': 'first-person fire-1',
            'first_person:fire_1:var2': 'first-person fire-2',
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
            'lr_fire': (['play_weapons_storm_homing_rifle_player_fire:0,1,2,3,4'],
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
            'lr_flyby_scoped': (['play_proj_forerunner_whizby_large@proj_forerunner_whizby_large'],
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
        'stretch': {'lr_reload_balanced': 67 / 50.0},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only lightrifle) on a COPY of the Halo 1 PISTOL (the
    # yardstick: magazine, reload, zoom, HUD, melee, bullet materials) + a SECOND TRIGGER (a copy of
    # trigger 0, `add_triggers`). DEFAULT = HALO 4's OWN NUMBERS; the pistol-ratio values are the
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
        'add_triggers': [0],
        # THE BURST ROUND (trigger 0): Halo 4 storm_forerunner_rifle 5.33 (lower = upper), plasma_fast
        # (= bullet_slow in Halo 4: the pistol bullet's table, C1), acceleration 0.2, 3000 wu/s flat,
        # range 250, no gravity
        'bullet': {'projectile': (PISTOL + 'bullet', LR + 'bolt'),
                   'damage': (PISTOL + 'bullet', LR + 'bolt'),
                   'dmg': 5.333, 'acceleration': 0.2, 'velocity': 3000.0, 'range': 250.0,
                   'proj_fields': {'proj_attrs.physics.flyby_sound.filepath': SND + 'lr_flyby'},
                   # THE HIT-EFFECT RULE: a burst lands 3 rounds 1/30 s apart -> the tag rate 30/s
                   'impact_thin': {'materials': [22], 'out': LR + 'effects\\impact\\',
                                   'thin': {}, 'rate': 30.0},
                   'triggers': [0]},
        # THE SCOPED SHOT (trigger 1): storm_forerunner_rifle_combined 23.5, the same flight, the large
        # fly-by
        'projectiles': [{
            'projectile': (PISTOL + 'bullet', LR + 'bolt scoped'),
            'damage': (PISTOL + 'bullet', LR + 'bolt scoped'),
            'dmg': 23.5, 'acceleration': 0.2, 'velocity': 3000.0, 'range': 250.0,
            'proj_fields': {'proj_attrs.physics.flyby_sound.filepath': SND + 'lr_flyby_scoped'},
            # THE HIT-EFFECT RULE: 2.5/s
            'impact_thin': {'materials': [22], 'out': LR + 'effects\\impact\\scoped ',
                            'thin': {}, 'rate': 2.5},
            'triggers': [1]}],
        # THE BURST (the Battle Rifle's option B2, user 2026-10-07): charge 1 tick + discharge + spew,
        # one burst a pull (Halo 4's latch). Halo 4: 3 rounds 1/30 s apart -> 30/s; the BR's measured
        # rule (rounds = spew ticks / spacing ticks + 2) gives 3 rounds at a 1-tick spew. Halo 4's 0.3
        # s recovery is not reproduced (the BR: tapping sets the cycle)
        'trigger': {'rounds_per_second': (30.0, 30.0), 'acceleration_time': 0.0,
                    'deceleration_time': 0.0,
                    'charging_time': 1 / 30.0, 'overcharged_action': 'discharge',
                    'spew_time': 1 / 30.0, 'does_not_repeat_automatically': True,
                    # Halo 4 bloom: deceleration 0.7 (acceleration none)
                    'error_acceleration_time': 0.0, 'error_deceleration_time': 0.7},
        # Halo 4: minimum error 0, error angle 0.15 flat (burst); the scoped 0.15 -> 0.5 in `fields`
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
            # MODE C: the grenade key fires trigger 1 (Bungie's digsite smg sets both flags)
            'weap_attrs.flags.secondary_trigger_overrides_grenades': True,
            'weap_attrs.flags.prevents_grenade_throwing': True,
            # THE SCOPED trigger: no charge, no spew, Halo 4's 2.5/s (recovery 0.4), 3 rounds a shot
            'weap_attrs.triggers.1.charging.charging_time': 0.0,
            'weap_attrs.triggers.1.charging.overcharged_action': 'none',
            'weap_attrs.triggers.1.charging.spew_time': 0.0,
            'weap_attrs.triggers.1.firing.rounds_per_second': (2.5, 2.5),
            'weap_attrs.triggers.1.firing.rounds_per_shot': 3,
            'weap_attrs.triggers.1.projectile.error_angle': (0.0026180, 0.0087266),   # 0.15 -> 0.5 deg
            # Halo 4's 3x (the pistol's 2x)
            'weap_attrs.aiming.zoom_levels': 1,
            'weap_attrs.aiming.zoom_ranges': (3.0, 3.0),
            'weap_attrs.interface.zoom_in_sound.filepath': SND + 'lr_zoom_in',
            'weap_attrs.interface.zoom_out_sound.filepath': SND + 'lr_zoom_out',
            'item_attrs.collision_sound.filepath': SND + 'lr_drop',
            'weap_attrs.magazines.0.magazine_items.0.rounds': 216,
            'obje_attrs.collision_model.filepath': LR + 'light rifle',
        },
        'sound_effects': {
            'firing_effect': (PISTOL + 'effects\\fire bullet', LR + 'effects\\fire bolt',
                              {r'sound\sfx\weapons\pistol\fire': SND + 'lr_fire'},
                              {'drop_parts': (r'sound\sfx\weapons\pistol\eject',),
                               'drop_particles': ('casing',)}),
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
        # side / chip ticks are opacity 0 (animated in Halo 4, not drawn at rest). PROVISIONAL until the
        # user's Halo 4 screenshot. Zoom: the pistol's mask until the scope from the screenshot
        'hud': {'donor': PISTOL + 'pistol', 'out': LR + 'light rifle',
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
                'ammo_meter': {'sizes': (36, 54), 'base': LR + 'bitmaps\\light_rifle_ammo'}},
        'palette_levels': LEVELS,
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
