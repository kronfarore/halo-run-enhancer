r"""Brute Shot (Halo 3 -> Halo 1, wave A7) on a copy of the Halo 1 ROCKET LAUNCHER, which is also
the yardstick (step 4a, user 2026-10-09). brute_mauler.py is the shape it copies (a whole-
magazine reload, Halo 3 pips, shaped glow); what is new here: an EXPLOSIVE grenade on an
ARCING projectile (Halo 3's grenade detonates on impact -- it does NOT bounce), a heavy two-
hander (label `bs` taught from `rl`) and the blade melee on a smash-melee template."""
from ._common import B, H3_FP_GRAPHS, reserved, row

H3 = r'objects\weapons\support_low\brute_shot'
BS = 'weapons\\brute shot\\'
SND = 'sound\\weapons\\brute_shot_port\\'
RL = 'weapons\\rocket launcher\\'
# Halo 3's self-illum of the body shader: BGRA d7 57 2e in the function data = RGB 46 / 87 /
# 215, a blue, intensity 3 -> 1. The shiny shader names the GRAVITY HAMMER's illum map with no
# colour of its own (intensity 4); the dull one has none
BLUE = (46 / 255.0, 87 / 255.0, 215 / 255.0)
ILLUM = H3 + r'\bitmaps\brute_shot_illum.bitmap'
BASE = H3 + r'\bitmaps\brute_shot.bitmap'
BLUE_HOT = (0.45, 0.75, 1.0)

PORT = reserved(
    order=16, wave='A7', name='Brute Shot', source='Halo 3',
    messages=(65, 66), icon=36, reticle=25, label='bs', teach_from='rl',
    sound_dir='sound\\weapons\\brute_shot_port', weapon_dir='weapons\\brute shot',
    yardstick={
        # step 4a (user, 2026-10-09): h3_weapon_values.py (brute_shot / rocket_launcher /
        # flak_cannon, FP graphs) + the projectiles' detonation blocks and damage effects
        # (tool export-tag-to-xml) + h1_role_compare.py brute_shot. The Brute Shot's damage is
        # its grenade's DETONATION (no impact damage): shot_grenade_explosion 26..73, radius
        # 0.3 -> 1.1 (AOE core 0.3), damage group explosion_small (the rocket's
        # explosion_large: Halo 3's table differs only on soft flood flesh x1 vs x2, solid
        # metal / terrain x0.25 vs x1 and solid shields x0 vs x1 -- hunters alike). The
        # grenade does NOT bounce in Halo 3: impact (detonate) on every material (its 'attach'
        # potential response has chance 0), timer 0, arming 0, and it bursts in the air at its
        # 20 wu maximum range (airborne_detonation effect)
        'pick': 'Rocket Launcher',
        'reason': "user, step 4a 2026-10-09: keeps Halo 3's relation (brute shot dps = 0.81 x "
                  "rocket launcher in both games: 243 vs 300 -> 128 vs 158), the rocket's "
                  "material table keeps Hunters killable as in Halo 3 (the fuel rod's makes "
                  "their armour immune), and the rocket is the pose donor (`bs` from `rl`). "
                  "Halo 3's no-bounce impact grenade in BOTH versions (user: a bounce is a later "
                  "enhancer option)",
        # DEFAULT = Halo 3's own numbers (PORTING "Balance"); these are the BALANCED rows.
        # H3: brute shot / rocket launcher. H1 rocket: explosion 80 lower, 300..330 upper
        # (mean 315), radius 0.5 -> 2.0, 2.0 s a shot (0.5/s), 2 (4 / 8), reload 4.17 s (125
        # fr), error 0, 12 -> 10 wu/s, gravity 0, range 128, aim 0/35 12/35, melee 55. Default
        # (H3 own): 26..73, 0.3 -> 1.1, 0.3 s, 6 (18 / 18), 95 fr, error 0.15 / 0.4, 16 -> 7
        # wu/s, gravity 0.05, range 20, aim 4/15 6/20, slice_melee 90. H3 rocket: 80..240,
        # 0.9 -> 2, 0.8 s, 2 (4 / 8), 116 fr, 8 -> 16, 0, 175, aim 5/25 10/25, smash_melee 80
        'balanced': {
            'damage': (91.25, 100.4),      # 300..330 x 73/240 (mean 95.8)
            'damage_lower': 26.0,          # 80 x 26/80
            'radius': (0.167, 1.1),        # 0.5 x 0.3/0.9, 2.0 x 1.1/2
            'fire_recovery_s': 0.75,       # 2.0 s x 0.3/0.8 (rounds_per_second 1.333)
            'magazine': 6,                 # 2 x 6/2
            'rounds_total_initial': 18,    # 4 x 18/4
            'rounds_total_maximum': 18,    # 8 x 18/8 (not dual-wieldable: no carry rule)
            'reload_s': 4.1667 * 95 / 116,  # 125 fr x 95/116 = 102 fr = 3.41 s (WHOLE magazine)
            # error: the rocket's 0 / 0 is degenerate -> Halo 3's own 0.15 / 0.4 (no ratio)
            'error_deg': (0.15, 0.4),
            'velocity': (24.0, 4.375),     # 12 x 16/8, 10 x 7/16
            'gravity': 0.05,               # the rocket has none (0 / 0): Halo 3's own
            'range': 14.6,                 # 128 x 20/175
            'aim': (0.0, 21.0, 7.2, 28.0),  # 0 x 4/5, 35 x 15/25; 12 x 6/10, 35 x 20/25
            'melee': 61.9},                # 55 x slice_melee 90 / smash_melee 80
        # Halo 1 materials: the rocket explosion's table (both versions), with Halo 3's one
        # difference that has a Halo 1 counterpart: soft flood flesh x1 (explosion_small) vs
        # x2 (explosion_large) -> flood_combat_form 2.0 x 1/2 = 1.0; flood_carrier_form 4
        # (brittle_flood x2 both) kept
        'materials': {'flood_combat_form': 1.0},
        # ratio table (h1_role_compare brute_shot): H3 own 243 dps, Elite minor 3 / 0.6 s
        # normal; RL ratio 128 dps (rocket 158), 3 / 1.5 s; Fuel Rod ratio 97 dps, Hunter
        # armour immune; Frag ratio 182 dps, Hunter armour x0.25 (17 hits)
        'measured': 'h1_role_compare.py brute_shot',
        'candidates': {
            'source_weapon': 'objects\\weapons\\support_low\\brute_shot\\brute_shot',
            'provisional': 'Rocket Launcher',
            'alternatives': ['Flak Cannon (H1 fuel rod)', 'Frag Grenade'],
            'direct': None,
            'peers': ['Rocket Launcher', 'Flak Cannon'],
            'why': 'magazine 6, explosive grenade projectile (16 -> 7 wu/s)',
            'lacks': 'blade melee (the rocket smashes)'}},
    # step 11: the source game's ai\generic entry (21 fields, verified 2026-10-07) laid over a
    # Halo 1 ROCKET LAUNCHER carrier ('bs' has no carrier). Halo 1's rocket carriers
    # (h1_weapon_carriers, 2026-10-09): the Flood combat Elite and human, both WDM 0.4 -- they
    # agree, no donor_variant. ARMED WDM RULE: base 0.4 x rocket 158 / brute shot dps --
    # default 73 x 3.33 = 243 (0.26), balanced 95.8 x 1.33 = 128 (0.49)
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\support_low\\brute_shot\\brute_shot',
                    'donor_weapon': 'weapons\\rocket launcher\\rocket launcher',
                    'wdm_rule': {'base': 0.4, 'yardstick_dps': 158.0, 'port_dps': 243.0,
                                 'balanced_port_dps': 128.0}},
)

PORT.update({
    'status': 'in progress',
    # geometry + look (h1_h3_weapon_model.py). Halo 3's three materials all sample the same
    # `brute_shot` base map (+ bump): the body `brute_shot` (detail metal_dirty, self-illum
    # brute_shot_illum in BLUE at 3 -> 1), `brute_shot_dull` (rubber detail, no illum) and
    # `brute_shot_shiny` (chrome reflections). Template: the rocket launcher's body shader
    'model': {
        'dir': r'weapons\brute shot',
        'world': H3 + r'\brute_shot.render_model',
        'fp': H3 + r'\fp_brute_shot\fp_brute_shot.render_model',
        'world_name': 'brute shot',
        'shaders': {'brute_shot': (BASE, ILLUM),
                    'brute_shot_dull': (BASE, None),
                    'brute_shot_shiny': (BASE, None)},
        # the Mauler's recipe from the start (A6): Halo 1 has no bloom, so Halo 3's colour x
        # intensity 3 (46 / 87 / 215 -> 138 / 255 / 255 clipped) as a saturated BLUE_HOT base
        # self-illum, the lit texels grown 1 px. fp_material_view --illum (2026-10-09): 109
        # lit FP triangles, all `brute_shot`: a RING of 26 inward-facing windows (radius ~4.5
        # around the gun origin) + small side spots (glow_spot_list)
        'illum_dilate': 1,
        'glow': {'brute_shot': BLUE_HOT},
        # the GRENADE (Halo 3 projectiles\grenade: one node, the body shader, markers
        # fx_contrail / fx_glow): the projectile's own model; fx_contrail = the rocket's
        # `exhaust` marker its kept smoke contrail hangs on
        'extra_models': {'grenade': {'from': H3 + r'\projectiles\grenade\grenade.render_model',
                                     'dir': r'weapons\brute shot\grenade',
                                     'markers': {'fx_contrail': 'exhaust'}}},
        'template': RL + r'shaders\rocket launcher body',
    },

    # FP animations (h1_fp_retarget.py). Halo 3 brute shot frames (h3_weapon_values): ready
    # 19, put_away 5, fire_1 29, melee_strike_1 28, reload empty / full 95
    'retarget': {
        'graph': H3_FP_GRAPHS + r'\support_low\fp_brute_shot\fp_brute_shot.model_animation_graph',
        'render_model': H3 + r'\fp_brute_shot\fp_brute_shot.render_model',
        # Halo 1 node names: '_' -> ' ' (h3_rm_to_jms.h1_name)
        'nodes': {n: 'frame ' + n.replace('_', ' ')
                  for n in ('gun', 'body', 'ammo01', 'ammo_feeder', 'barrel', 'slide',
                            'ammo02', 'ammo_cap', 'handle', 'ammo03', 'ammo04')},
        'h1_dir': r'weapons\brute shot\fp',
        'h1_model': r'weapons\brute shot\fp\fp',
        'align': 'same_space',
        # the SMG's placement (user's pick, A1) as the start
        'view_offset': (-0.0225, 0.0, -0.0225),
        'anims': {
            'first_person:idle': 'first-person idle',
            'first_person:posing:var1': 'first-person posing',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:fire_1:var1': 'first-person fire-1',
            'first_person:melee_strike_1': 'first-person melee',
            'first_person:moving': 'first-person moving',
            'first_person:overlays': 'first-person overlays',
            'first_person:reload_empty': 'first-person reload-empty',
            'first_person:reload_full': 'first-person reload-full',
            'first_person:throw_grenade': 'first-person throw-grenade',
        },
    },

    # Halo 3's own sounds (h1_port_sounds.py brute_shot). Levels = the stock Halo 1 sound each
    # stands in for (h1_stock_sound_levels.py, MCC sounds_adpcm.fsb 2026-10-09): rocket
    # launcher fire -15.1 (2 perms -15.3 / -14.9), frag grenade expl -7.9 (the rocket's
    # explosion plays the frag grenade's), rl_projectile -19.9 (the rocket's flight loop),
    # rocket_reload_e -22.5, rocket_ready -18.3, rocket_melee -21.8, rocket_posing -22.1,
    # rlauncher_impact -23.0, rocket_ammo -28.8, AR dryfire -17.6 (the rocket's empty field
    # names the AR dry fire SOUND itself). Halo 3's brute shot names the BATTLE RIFLE's dry
    # fire as its empty effect: its own copy here. Single-wield FP cues: ready, melee, pose,
    # reload (both reloads)
    'sounds': {
        'catalog': 'Brute Shot',
        'dir': B.join(['sound', 'weapons', 'brute_shot_port']),
        'h3_dir': 'data\\sound\\weapons\\brute_shot\\',
        'sounds': {
            'bs_fire': (['brute_shot_fire_new'], 'sound\\sfx\\weapons\\rocket launcher\\fire', -15.1),
            'bs_explode': (['brute_round_explode'], 'sound\\sfx\\weapons\\frag grenade\\expl', -7.9),
            'bs_projectile': (['brute_shot_projectile\\brute_shot_proj\\loop'], 'sound\\sfx\\weapons\\rocket launcher\\rl_projectile', -19.9),
            'bs_reload': (['fp_brute_shot\\fp_brute_shot_reload'], 'sound\\sfx\\weapons\\weapon_anims\\rocket_reload_e', -22.5),
            'bs_reload_balanced': (['fp_brute_shot\\fp_brute_shot_reload'], 'sound\\sfx\\weapons\\weapon_anims\\rocket_reload_e', -22.5),
            'bs_ready': (['fp_brute_shot\\fp_brute_shot_ready'], 'sound\\sfx\\weapons\\weapon_anims\\rocket_ready', -18.3),
            'bs_melee': (['fp_brute_shot\\fp_brute_shot_melee'], 'sound\\sfx\\weapons\\weapon_anims\\rocket_melee', -21.8),
            'bs_pose': (['brute_shot_posing_var1'], 'sound\\sfx\\weapons\\weapon_anims\\rocket_posing', -22.1),
            'bs_drop': (['brute_shot_drop'], 'sound\\sfx\\impulse\\weapon_drops\\rlauncher_impact', -23.0),
            'bs_ammo': (['brute_shot_ammo'], 'sound\\sfx\\weapons\\weapon_pickup_ammo\\rocket_ammo', -28.8),
            'bs_dryfire': (['data\\sound\\weapons\\battle_rifle\\dryfire'], 'sound\\sfx\\weapons\\assault rifle\\dryfire', -17.6),
        },
        # step 9: the balanced reload, H1 rocket reload-empty 125 fr x 95/116 = 102 fr over
        # the built 95 = x1.07
        'stretch': {'bs_reload_balanced': 1.07},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only brute_shot) on a COPY of the Halo 1 Rocket
    # Launcher. DEFAULT = HALO 3's OWN NUMBERS (PORTING "Balance"); the ratio values are the
    # balance rows (yardstick['balanced']). The rocket's magazine already reloads WHOLE (2
    # loaded, 2 reloaded): no shell loop to undo (the Mauler's trap does not apply)
    'pickable': {
        'weapon': BS + 'brute shot',
        'template': RL + 'rocket launcher',
        'world_model': BS + 'brute shot',
        'fp_model': BS + 'fp\\fp',
        'fp_anims': BS + 'fp\\fp',
        'label': 'bs',
        # two-handed HEAVY: Halo 1's rocket pose (user, step 4a 2026-10-09)
        'teach': ('bs', 'rl'),
        'keys': {'first-person melee': 5},          # H3 melee_strike_1 primary_keyframe 5
        'sounds': {'first-person ready': SND + 'bs_ready',
                   'first-person posing': SND + 'bs_pose',
                   'first-person melee': SND + 'bs_melee',
                   'first-person reload-empty': SND + 'bs_reload',
                   'first-person reload-full': SND + 'bs_reload'},
        'extra_sounds': [SND + 'bs_reload_balanced'],      # unused until the balanced retime
        # own GRENADE (step 3) on a copy of the rocket. Halo 3's damage is the DETONATION's
        # (no impact damage): the rocket's `rocket explosion` effect + `explosion` damage
        # copied (h1_pickable_weapons `explosion`), Halo 3's 26..73 over 0.3 -> 1.1 wu, the
        # material table the rocket's with flood combat forms x1 (step 4a). The explosion
        # SOUND = Halo 3's brute_round_explode (the rocket plays the frag grenade's). Flight:
        # 16 -> 7 wu/s, air gravity 0.05, range 20 (Halo 3 bursts in the air there), oriented
        # along velocity + AI ballistic aiming (Halo 3's flags; Halo 1's fuel rod has both).
        # The rocket's detonation timer (on first bounce, 0) is KEPT: Halo 3's 'immediately'
        # with timer 0 could read as a zero timer in Halo 1 -- every response detonates, so
        # nothing bounces either way (the Spiker's trap, checked first). Visible: Halo 3's
        # grenade model; the rocket's smoke CONTRAIL kept (Halo 3 trails soft smoke), its
        # exhaust flame + particle system dropped, Halo 3's flight loop as an own loop
        'bullet': {'projectile': (RL + 'rocket', BS + 'grenade'),
                   'damage': None,
                   'explosion': {'effect': (RL + 'effects\\rocket explosion', BS + 'effects\\grenade explosion'),
                                 'damage': (RL + 'explosion', BS + 'explosion'),
                                 'lower': 26.0, 'upper': (73.0, 73.0), 'radius': (0.3, 1.1),
                                 'mods': {'flood_combat_form': 1.0},
                                 'swaps': {'sound\\sfx\\weapons\\frag grenade\\expl': SND + 'bs_explode'},
                                 # STEP 4b list 2 (ratio vs the H3 rocket onto the H1 rocket,
                                 # before boot 1): aoe core 0.6 x 0.3/0.5; camo damage 1 x
                                 # 0.3/0.9; instantaneous acceleration 6 x 2/3; shake 0.0349 x
                                 # 0.05/0.075; breaking effect 80 x 30/35, 1 x 2/0.5, 2 x 0/0.5,
                                 # 16 x 15/6. List 3: the camera impulse (H1 rocket 0: the
                                 # ratio is 0), category high_explosive kept (Halo 3's
                                 # 'bullet' on an explosion only reports), flags no Halo 1
                                 # counterpart by name
                                 'fields': {'damage.aoe_core_radius': 0.36,
                                            'damage.active_camouflage_damage': 1 / 3.0,
                                            'damage.instantaneous_acceleration': 4.0,
                                            'camera_shaking.random_translation': 0.0349066 * 0.05 / 0.075,
                                            'breaking_effect.forward_velocity': 80 * 30 / 35.0,
                                            'breaking_effect.forward_radius': 4.0,
                                            'breaking_effect.forward_exponent': 0.0,
                                            'breaking_effect.outward_velocity': 40.0}},
                   'velocity': (16.0, 7.0), 'range': 20.0,
                   'model': BS + 'grenade\\grenade',
                   # 4b list 2: water gravity 0.4 x 0.25/0.4. Air damage range KEPT 0..100
                   # (Halo 3: brute shot 0,0 = unset, rocket 0,150 -- a ratio on an unset
                   # field is degenerate; the grenade has no impact damage it would scale).
                   # List 3: minimum velocity 11 (the H3 rocket's 0: no ratio -> Halo 3's
                   # own; Halo 3's grenade falls 16 -> 7 over 6..15 wu, so it is slower than
                   # 11 from ~11 wu -- WATCH where it bursts in game); danger radius,
                   # acceleration scale: the H1 rocket's 0 (the ratio is 0)
                   'proj_fields': {'proj_attrs.physics.air_gravity_scale': 0.05,
                                   'proj_attrs.physics.water_gravity_scale': 0.25,
                                   'proj_attrs.detonation.minimum_velocity': 11.0,
                                   'proj_attrs.flags.oriented_along_velocity': True,
                                   'proj_attrs.flags.ai_must_use_ballistic_aiming': True},
                   # rocket attachments: 0 exhaust effect, 1 smoke contrail, 2 rocket exhaust
                   # particle system, 3 the rl_projectile loop
                   'keep_attachments': (1,),
                   'hum': {'like': 'sound\\sfx\\weapons\\rocket launcher\\rl_projectile',
                           'loop': SND + 'bs_projectile', 'tag': SND + 'bs_projectile',
                           'marker': ''}},
        # H3: fire recovery 0.3 s (rounds per second 0 = recovery-limited) = 3.33/s
        'trigger': {'rounds_per_second': (1 / 0.3, 1 / 0.3),
                    # 4b list 3: first person offset -- H3 brute shot 0,-0.025,-0.02 vs
                    # rocket 0,-0.05,0 onto the H1 rocket's 0,-0.1,0: y -0.1 x 0.5 = -0.05,
                    # z (the H3 rocket's 0: no ratio) Halo 3's own -0.02
                    'first_person_offset': (0.0, -0.05, -0.02),
                    # 4b list 2: illumination recovery 0.3 x 0.1/0.2
                    'illumination_recovery_time': 0.15},
        # H3: minimum error 0.15, error angle 0.4 / 0.4 (the rocket 0 / 0)
        'error_deg': {'minimum_error': 0.15, 'error_angle': (0.4, 0.4)},
        # H3: 6 loaded, 18 at pickup, 18 most, all 6 reloaded at once (95 fr; reload time 0
        # = the animation's -- Halo 1 needs a number: 3.2 s)
        'magazine': {'rounds_loaded_maximum': 6, 'rounds_reloaded': 6,
                     'rounds_total_initial': 18, 'rounds_total_maximum': 18,
                     'reload_time': 3.2},
        # H3 aim assist, absolute (balanced = the ratio rule)
        'aiming': {'autoaim_angle': 4.0, 'autoaim_range': 15.0,
                   'magnetism_angle': 6.0, 'magnetism_range': 20.0},
        'fields': {
            # STEP 4b list 2 (ratio vs the H3 rocket onto the H1 rocket; before boot 1):
            # bounding radius 0.2875 x 0.316/0.25; active camo ding 1 x 0.75/1. The reload time
            # stays 3.2 s on purpose (Halo 3's 0 = the animation's length; Halo 1 needs a
            # number). List 3: bounding offset the H1 rocket's 0 (the ratio is 0); weapon type
            # 'undefined' both (Halo 3's rocket says 'rocket launcher', the brute shot not);
            # firing noise loud both; the H1 flags 0 both
            'obje_attrs.bounding_radius': 0.2875 * 0.316 / 0.25,
            'weap_attrs.interface.active_camo_ding': 0.75,
            # Halo 3's brute shot has NO zoom (zoom levels 0); the rocket's 2x goes
            'weap_attrs.aiming.zoom_levels': 0,
            # the rocket's trigger names the AR dry fire SOUND as its empty effect: the brute
            # shot's own (Halo 3: the battle rifle's dry fire)
            'weap_attrs.triggers.0.firing_effects.0.empty_effect.filepath': SND + 'bs_dryfire',
            'weap_attrs.interface.pickup_sound.filepath': SND + 'bs_ammo',
            'item_attrs.collision_sound.filepath': SND + 'bs_drop'},
        'sound_effects': {
            # Halo 3's brute shot flash: muzzle_flash_long + round, glow_soft, fiery sparks,
            # a light -- the rocket's smoke + flash kept, its fire sound swapped
            'firing_effect': (RL + 'effects\\fire rocket', BS + 'effects\\fire grenade',
                              {r'sound\sfx\weapons\rocket launcher\fire': SND + 'bs_fire'})},
        # the BLADE (Halo 3 slice_melee 90; the rocket's 55 smash): DEFAULT = Halo 3's 90 as
        # the copy's mean (the rocket's spread kept); balanced 61.9 (55 x 90/80)
        'melee': (RL + 'melee', BS + 'melee'),
        'melee_dmg': 90.0,
        'melee_response': RL + 'melee_response',
        'messages': ('Picked up a brute shot', 'Picked up %d rounds for brute shot'),
        'icon': 'brute shot',
        # the rocket's HUD with Halo 3's brute shot reticle (H3 hud_reticles #17) at the
        # reserved 25 and Halo 3's own round icons (chud brute_shot: ballistic_meters #6),
        # 6 a row; low-ammo flash: the rocket's 1 of 2 -> 3 of 6
        'hud': {'donor': RL + 'rocket_launcher', 'out': BS + 'brute shot',
                'reticle': ('hud_reticles', 17, 'brute shot'),
                'reticle_thicken': 1,
                'ammo_meter': {'sizes': (6,), 'base': BS + 'bitmaps\\brute_shot_ammo',
                               'art': {'h3': ('ballistic_meters', 6)}},
                'flash_base': 2},
        'palette_levels': ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40'],
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py brute_shot). DEFAULT = Halo 3's
    # own numbers in the tags; BALANCED = the ROCKET LAUNCHER ratio rule (step 4a, user
    # 2026-10-09). Assembly Halo1 units: angles in degrees, velocity in wu per TICK
    'catalog': {
        'entry': {
            'weapon': 'Brute Shot', 'source': 'Halo 3', 'donor': 'Rocket Launcher', 'default_on': False,
            'desc': "Halo 3's Brute Shot: its model, first-person animations, sounds and "
                    "numbers. A 6-round Brute grenade launcher firing arcing grenades that "
                    "explode on impact, with a blade for melee.",
            'balance_desc': "Measured against the Rocket Launcher, which both games have: "
                            "91-100 damage per grenade over 1.1 m, one shot every 0.75 s, a "
                            "3.4 s reload, faster grenades with a shorter reach, a heavier "
                            "blade, and Halo 1-style aim assist.",
            # step 9: the balanced reload = H1 rocket 125 fr x 95/116 = 102 fr over the built
            # 95 = x1.07 (stretched sound); swap (ONE multiplier, the ready's): H1 rocket ready
            # 22 fr x 19/26 = 16 fr over the built 19 = x0.85
            'anims': {'reload': 1.07, 'swap': 0.85},
            'anim_sounds': {'reload': {'mult': 1.07, 'from': SND + 'bs_reload',
                                       'to': SND + 'bs_reload_balanced'}},
            'balance': [
                row('jpt!', BS + 'explosion', 'Damage Upper Bound', 91.25, 73.0, 'Grenade Damage'),
                row('jpt!', BS + 'explosion', 'Damage Upper Bound Max', 100.4, 73.0, 'Grenade Damage'),
                row('jpt!', BS + 'explosion', 'Radius', 0.167, 0.3, 'Grenade Damage'),
                row('weap', BS + 'brute shot', 'Rounds Per Second', 1 / 0.75, 1 / 0.3, 'More Shooting', block='Triggers'),
                row('weap', BS + 'brute shot', 'Rounds Per Second Max', 1 / 0.75, 1 / 0.3, 'More Shooting', block='Triggers'),
                row('proj', BS + 'grenade', 'Initial Velocity', 24.0 / 30, 16.0 / 30, 'Projectile'),
                row('proj', BS + 'grenade', 'Final Velocity', 4.375 / 30, 7.0 / 30, 'Projectile'),
                row('proj', BS + 'grenade', 'Maximum Range', 14.6, 20.0, 'Projectile'),
                row('weap', BS + 'brute shot', 'Autoaim Angle', 0.0, 4.0, 'Autoaim'),
                row('weap', BS + 'brute shot', 'Autoaim Range', 21.0, 15.0, 'Autoaim'),
                row('weap', BS + 'brute shot', 'Magnetism Angle', 7.2, 6.0, 'Magnetism'),
                row('weap', BS + 'brute shot', 'Magnetism Range', 28.0, 20.0, 'Magnetism'),
                # the blade: 55 x 90/80 = 61.9 as the copy's mean (the rocket's 40 / 50..60
                # spread x 61.9/55); default Halo 3's 90 (x 90/55: 65.45 / 81.82..98.18)
                row('jpt!', BS + 'melee', 'Damage Lower Bound', 45.02, 65.45, 'Melee Damage'),
                row('jpt!', BS + 'melee', 'Damage Upper Bound', 56.27, 81.82, 'Melee Damage'),
                row('jpt!', BS + 'melee', 'Damage Upper Bound Max', 67.53, 98.18, 'Melee Damage'),
            ]},
    },

    # step 4b (port_field_audit.py --port brute_shot): the source pair (H3 brute shot vs the
    # yardstick, H3 rocket launcher) against the target pair (the H1 port vs its template =
    # the H1 rocket launcher)
    'field_audit': {
        'source_kit': 'H3EK',
        'source': {'weapon': (H3 + r'\brute_shot.weapon', r'objects\weapons\support_high\rocket_launcher\rocket_launcher.weapon'),
                   'projectile': (H3 + r'\projectiles\grenade\grenade.projectile',
                                  r'objects\weapons\support_high\rocket_launcher\projectiles\rocket.projectile'),
                   'damage_effect': (H3 + r'\damage_effects\shot_grenade_explosion.damage_effect',
                                     r'objects\weapons\support_high\rocket_launcher\damage_effects\rocket_launcher_explosion.damage_effect'),
                   'melee': (r'objects\weapons\damage_effects\slice_melee.damage_effect',
                             r'objects\weapons\damage_effects\smash_melee.damage_effect')},
        'target': {'weapon': (BS + 'brute shot.weapon', RL + 'rocket launcher.weapon'),
                   'projectile': (BS + 'grenade.projectile', RL + 'rocket.projectile'),
                   'damage_effect': (BS + 'explosion.damage_effect', RL + 'explosion.damage_effect'),
                   'melee': (BS + 'melee.damage_effect', RL + 'melee.damage_effect')}},

    # the dry test: a30 (Covenant within seconds of the landing), the brute shot as the
    # primary with Halo 3's own loadout (6 loaded, 18 in all)
    'test': {'level': 'a30', 'rounds': (6, 18), 'grunt': None, 'elite': None},
})
