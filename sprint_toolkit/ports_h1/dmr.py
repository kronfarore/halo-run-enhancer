r"""DMR (Halo Reach, wave B1, the REACH PILOT): a MAGAZINE semi-automatic with a 3x zoom on a
copy of the Halo 1 SNIPER RIFLE (the yardstick and its bullet materials, step 4a). The
Battle Rifle (battle_rifle.py) is the nearest shape; what is new is the SOURCE GAME: Reach's
geometry, animations, textures, sounds and chud, read through reach_tags.py behind the
`reach:` path prefix (the route this pilot proves for wave B)."""
from ._common import B, reserved, row

R = 'reach:'                                       # an HREK path (reach_tags)
RW = r'objects\weapons\rifle\dmr'
RFP = r'objects\characters\spartans\fp\weapons\rifle\fp_dmr\fp_dmr'
DMR = 'weapons\\dmr\\'
SND = 'sound\\weapons\\dmr_port\\'
SR = 'weapons\\sniper rifle\\'
AR = 'weapons\\assault rifle\\'
RS = 'data\\sound\\weapons\\'                      # Reach's bank folders
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']

PORT = reserved(
    order=19, wave='B1', name='DMR', source='Halo Reach',
    messages=(71, 72), icon=39, reticle=28, label='dm', teach_from='ar',
    sound_dir='sound\\weapons\\dmr_port', weapon_dir='weapons\\dmr',
    yardstick={
        # step 4a (user, 2026-10-10): h1_role_compare.py dmr, the Reach side from
        # h3_weapon_values.py --kit reach. Reach: DMR 17.5 (bullet_fast, headshots) per 0.33 s
        # = 3.0/s, 15 (45 / 75), reload 68 / 59 fr, error 0.15 -> 2, 3x, 3000 wu/s, range 250,
        # aim 2.25/20 5/20; Reach sniper 80 per 0.75 s = 1.33/s, 4 (12 / 24), 86 / 72 fr, error
        # 0.08 -> 4, zoom (4, 10), 6000, 500, aim 0.8/20 1.6/20. H1 sniper 101 x 2/s, 4 (12 /
        # 24), 94 / 83 fr, error 0.5 flat, zoom (2, 8), 1000 wu/s, range 1000, aim 1/35 2/35.
        # Shown beside it: the pistol ratio (25 x 2.0/s = 50 dps, 22 rounds, every value
        # scaling) -- the user chose the sniper.
        'pick': 'Sniper Rifle',
        'reason': 'user, step 4a 2026-10-10: the DMR as Halo 1\'s long-range precision rifle; '
                  'H1 value = H1 sniper x Reach DMR / Reach sniper (99 dps balanced against the '
                  'H1 sniper\'s 202 and pistol\'s 88). Bullet MATERIALS = the H1 sniper bullet\'s '
                  '(user: Elite shields x2, Flood combat forms x0.05 -- Flood take ~26 s, as '
                  'with the sniper), so the template is the H1 sniper rifle. Spread: the sniper '
                  'ratio inverts (Reach sniper minimum 0.08 near zero) -> the SIBLING RULE in '
                  'Reach\'s shape (user). Zoom: Reach\'s own 3x in both (user)',
        # DEFAULT = Reach's own numbers (wave rule kept for wave B, user 2026-10-10); these are
        # the BALANCED rows (Reach DMR / Reach sniper onto the H1 sniper)
        'balanced': {
            'damage': 22.09,             # 101 x 17.5/80
            'rate': 4.5,                 # 2/s x 3.0 / 1.333 (both semi-automatic: 1 / recovery)
            'magazine': 15,              # 4 x 15/4
            'rounds_total_initial': 45,  # 12 x 45/12
            'rounds_total_maximum': 75,  # 24 x 75/24 (not dual-wieldable: no carry rule)
            'reload_s': 2.48,            # 94 fr x 68/86 (reload empty; full: 83 fr x 59/72 = 68 fr)
            # SIBLING RULE (user): the maximum by its ratio, 0.5 x 2/4 = 0.25; the minimum in
            # Reach's DMR shape, 0.25 x 0.15/2 = 0.019 (the plain ratio inverts: 0.5 x 0.15/0.08 = 0.94)
            'error_deg': (0.019, 0.25),
            'velocity': 500.0,           # 1000 x 3000/6000
            'range': 500.0,              # 1000 x 250/500
            'aim': (2.81, 35.0, 6.25, 35.0),  # 1 x 2.25/0.8, 35 x 20/20; 2 x 5/1.6, 35 x 20/20
            'zoom': 3.0,                 # user: Reach's own 3x (the ratio gave 1.5x / 2.4x)
            'melee': 55.0},              # Reach shares strike_melee: x1 = the H1 sniper's
        'measured': 'h1_role_compare.py dmr',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\dmr\\dmr',
            'provisional': 'Pistol',
            'alternatives': ['Sniper Rifle'],
            'direct': None,
            'peers': ['Pistol', 'Sniper Rifle', 'Battle Rifle'],
            'why': "semi-auto magazine 15, 3x zoom, near-instant bullet: the H1 magnum's role",
            'lacks': ''}},
    # step 11: Reach's ai\generic DMR entry (m10, 26 fields) over a base -- 'dm' has no carrier.
    # Halo 1's carriers of the yardstick (h1_weapon_carriers, 2026-10-10): the Flood combat
    # Elite sniper (WDM 0.4, actor flags: moveswitch_stay_with_friends only) and the armoured
    # Marine snipers (0.6, prefer_passenger_seat) -- they disagree: the Flood Elite for EVERY
    # slot (user; the Beam Rifle's pick). ARMED WDM RULE (user: applied as is, the first
    # WDM above 1.0): 0.4 x Sniper 202 / DMR 52.5 = 1.54 default, / 99.4 = 0.81 balanced
    # (h1_role_compare dmr, the built port, 5b)
    firing_profile={'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map',
                    'from_weapon': 'objects\\weapons\\rifle\\dmr\\dmr',
                    'donor_weapon': 'weapons\\sniper rifle\\sniper rifle',
                    'donor_variant': 'characters\\floodcombat elite\\floodcombat elite sniper rifle',
                    'wdm_rule': {'base': 0.4, 'yardstick_dps': 202.0, 'port_dps': 52.5,
                                 'balanced_port_dps': 99.4}},
)

PORT.update({
    # 2026-10-10: tested on a30 over 4 boots (dry default, fixes, balanced, Armed) -- everything
    # confirmed by the user; the ten-map rebuild is BATCHED (wave B, on the user's go)
    'status': 'done',

    # geometry + look (h1_h3_weapon_model.py; Reach through reach_tags). Reach has ONE model
    # for world AND first person (the weapon's own render model; the FP graph moves it).
    # Route research (2026-10-10): 1 region / permutation, no LODs, 16,286 triangles, four
    # bones b_gun (root, NOT tilted: x forward, z up, grip at the origin) / b_magazine /
    # b_safety / b_ophandle, 15 marker groups incl. primary_trigger (Armed fires from it).
    # Shaders: self-illumination OFF in every DMR shader (the illum bitmaps they name are not
    # even in HREK) -> multipurpose G 0; R = the diffuse alpha (Reach's specular mask)
    'model': {
        'dir': r'weapons\dmr',
        'world': R + RW + r'\dmr.render_model',
        'fp': R + RW + r'\dmr.render_model',
        'world_name': 'dmr',
        'markers': {'primary_ejection': 'primary ejection', 'left_hand': 'left hand'},
        'shaders': {'dmr_metal': (R + RW + r'\bitmaps\dmr_diffuse.bitmap', None),
                    'dmr_metal_shiny': (R + RW + r'\bitmaps\dmr_diffuse.bitmap', None),
                    'dmr_composite': (R + RW + r'\bitmaps\dmr_diffuse.bitmap', None),
                    'dmr_rubber': (R + RW + r'\bitmaps\dmr_diffuse.bitmap', None),
                    'dmr_lens': (R + RW + r'\bitmaps\dmr_diffuse.bitmap', None),
                    'unsc_decals_fp': (R + r'objects\bitmaps\decals\bitmaps\unsc_decals_diffuse.bitmap', None),
                    'ones_dmr': (R + r'objects\weapons\rifle\assault_rifle\bitmaps\numbers_plate.bitmap',
                                 R + r'objects\weapons\rifle\assault_rifle\bitmaps\numbers_plate.bitmap'),
                    'tens_dmr': (R + r'objects\weapons\rifle\assault_rifle\bitmaps\numbers_plate.bitmap',
                                 R + r'objects\weapons\rifle\assault_rifle\bitmaps\numbers_plate.bitmap')},
        'template': r'weapons\assault rifle\fp\shaders\gun',
        # the UNSC stencils keep Reach's alpha (an alpha-blended decal shader, the Spartan
        # Laser's recipe); the scope's GLASS (Reach: alpha blend over a grey 50% map + a
        # cubemap) has no Halo 1 shader_model equivalent -> dropped, the lens body stays
        'decals': ('unsc_decals_fp',),
        'drop_materials': ('dmr_lens_glass',),
        # the ON-GUN COUNTER (the BR's recipe): Halo 1's numeric chicago shader, limit = 15
        'numeric': {'from': r'weapons\assault rifle\fp\shaders\numbers', 'limit': 15,
                    'places': {'ones_dmr': 0, 'tens_dmr': 1}},
    },

    # FP animations (h1_fp_retarget.py): ROUTE (a), Reach's OWN fp_dmr retargeted (user
    # 2026-10-10). Reach's Spartan arms = Halo 1's 37 nodes + 10 helpers, dropped here; the
    # r_hand bind differs by a 4.3 deg roll (not corrected yet: judge in game). Reach's arms sit
    # ~2.5 JMS units further forward than Halo 3's -> the BR's tested view_offset minus 0.025 x
    'retarget': {
        'graph': R + RFP + '.model_animation_graph',
        'render_model': R + RW + r'\dmr.render_model',
        'nodes': {'b_gun': 'frame b gun', 'b_magazine': 'frame b magazine',
                  'b_ophandle': 'frame b ophandle', 'b_safety': 'frame b safety'},
        'drop_nodes': ('pedestal', 'aim_pitch', 'aim_yaw', 'l_humerus', 'r_humerus',
                       'l_radius', 'r_radius', 'l_handguard', 'r_handguard'),
        'h1_dir': r'weapons\dmr\fp',
        'h1_model': r'weapons\dmr\fp\fp',
        'align': 'same_space',
        'view_offset': (-0.0225 - 0.025, 0.0, -0.0125),
        # Reach fp_dmr (25 animations, reach_tags --pose): fire_1 var1-3 (18 fr), idle 100,
        # posing var1 60 / var2 90, ready 19, put_away 4, reload empty 68 / full 59, melee 34
        # (primary keyframe 5), throw_grenade 44, overlays moving 20 and `look` 9 (the aim
        # overlay = Halo 1's 9-frame `overlays`)
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

    # Reach's own sounds (h1_port_sounds.py dmr, bank = Reach's sfx.fsb). Levels = the active
    # RMS of the stock Halo 1 SNIPER sound each stands in for (h1_stock_sound_levels.py,
    # 2026-10-10): fire -12.4, dryfire (the sniper uses the AR's) -17.6, reload empty -17.4 /
    # full -16.7, ready -21.6, melee -21.5, posing -19.1, zoom 2x -28.9 / 10x -29.2, ammo
    # -30.5, drop (shotgun_impact) -20.7. THE FIRE: Reach's firing effect plays
    # marksman_rifle_fire + an exterior / interior TAIL + a far LOD; Halo 1 plays one sound a
    # round -> the shot and the exterior tail MIXED, permutation k with k
    'sounds': {
        'catalog': 'DMR',
        'bank': 'haloreach',
        'dir': B.join(['sound', 'weapons', 'dmr_port']),
        'h3_dir': RS + 'dmr\\',
        'sounds': {
            'dm_fire': ([RS + 'marksman_rifle\\marksman_rifle_fire', RS + 'marksman_rifle\\marksman_tail_ext'],
                        'sound\\sfx\\weapons\\sniper rifle\\fire', -12.4),
            'dm_dryfire': ([RS + 'battle_rifle\\dryfire'], 'sound\\sfx\\weapons\\assault rifle\\dryfire', -17.6),
            'dm_reload_empty': (['dmr_reload_empty'], 'sound\\sfx\\weapons\\weapon_anims\\sniper_reload_empty', -17.4),
            'dm_reload_full': (['dmr_reload_full'], 'sound\\sfx\\weapons\\weapon_anims\\sniper_reload_full', -16.7),
            'dm_ready': (['dmr_ready'], 'sound\\sfx\\weapons\\weapon_anims\\sniper_ready', -21.6),
            'dm_melee': (['dmr_melee_1'], 'sound\\sfx\\weapons\\weapon_anims\\sniper_melee', -21.5),
            'dm_pose': (['dmr_pose_1'], 'sound\\sfx\\weapons\\weapon_anims\\sniper_posing', -19.1),
            'dm_zoom_in': ([RS + 'battle_rifle\\battle_rifle_zoom_in'], 'sound\\sfx\\weapons\\sniper rifle\\sniper_2x_zoom', -28.9),
            'dm_zoom_out': ([RS + 'battle_rifle\\battle_rifle_zoom_out'], 'sound\\sfx\\weapons\\sniper rifle\\sniper_10x_zoom', -29.2),
            'dm_ammo': ([RS + 'battle_rifle\\battle_rifle_ammo'], 'sound\\sfx\\weapons\\weapon_pickup_ammo\\sniper_ammo', -30.5),
            # the casing (TEST 1: the flash now starts from the BR's effect, which ejects one;
            # Reach's DMR plays eject_br too), at the BR port's eject level
            'dm_eject': ([RS + 'battle_rifle\\eject_br'], 'sound\\sfx\\weapons\\pistol\\eject', -17.0),
            'dm_drop': ([RS + 'battle_rifle\\battle_rifle_drop'], 'sound\\sfx\\impulse\\weapon_drops\\shotgun_impact', -20.7),
            # the BALANCED reloads (the patcher retimes both x1.12, then swaps these in)
            'dm_reload_empty_balanced': (['dmr_reload_empty'], 'sound\\sfx\\weapons\\weapon_anims\\sniper_reload_empty', -17.4),
            'dm_reload_full_balanced': (['dmr_reload_full'], 'sound\\sfx\\weapons\\weapon_anims\\sniper_reload_full', -16.7),
        },
        'stretch': {'dm_reload_empty_balanced': 1.12, 'dm_reload_full_balanced': 1.12},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only dmr) on a COPY of the Halo 1 SNIPER RIFLE (the
    # yardstick: its bullet materials, zoom screen effect, magazine HUD). DEFAULT = REACH's OWN
    # NUMBERS; the ratio values are the balance rows. Template inspection (the BR's trap):
    # exports A illumination / B ready; functions 0 muzzle flash (A in -> A out -> the muzzle
    # light attachment), 1 scope activity (B in -> B out: the sniper's own FP screen shaders,
    # which the DMR's model does not use) -> the AR's layout, as the BR
    'pickable': {
        'weapon': DMR + 'dmr',
        'template': SR + 'sniper rifle',
        'world_model': DMR + 'dmr',
        'fp_model': DMR + 'fp\\fp',
        'fp_anims': DMR + 'fp\\fp',
        'label': 'dm',
        'teach': ('dm', 'ar'),
        'keys': {'first-person melee': 5},          # Reach melee_strike_1 primary keyframe 5
        'sounds': {'first-person ready': SND + 'dm_ready',
                   'first-person posing': SND + 'dm_pose',
                   'first-person melee': SND + 'dm_melee',
                   'first-person reload-empty': SND + 'dm_reload_empty',
                   'first-person reload-full': SND + 'dm_reload_full'},
        # own bullet + damage (step 3): Reach dmr_bullet 17.5, 3000 wu/s, range 250, on the
        # sniper bullet's materials (user, step 4a)
        'bullet': {'projectile': (SR + 'sniper bullet', DMR + 'bullet'),
                   'damage': (SR + 'sniper bullet', DMR + 'bullet'),
                   'dmg': 17.5, 'velocity': 3000.0, 'range': 250.0,
                   # STEP 4b (port_field_audit --port dmr, before boot 1). List 2 (no card
                   # covers it -> the ratio vs Reach's sniper onto the H1 sniper): active camo
                   # damage 1 x 0.75/1, breaking forward radius 0.25 x 0.12/0.1. The forward
                   # EXPONENT degenerates (10 x 8/0.2 = 400): Reach's own 8 (the BR / Beam Rifle
                   # rule). List 3 (a zero on one side -> the source value): outward 3 / 0.5 /
                   # 0.2, instantaneous acceleration 0.4 (the H1 sniper 0). Flags: Reach's
                   # 'can cause headshots / does not spill over' have no Halo 1 jpt flag (0 kept)
                   'fields': {'damage.active_camouflage_damage': 0.75,
                              'damage.instantaneous_acceleration': 0.4,
                              'breaking_effect.forward_radius': 0.3,
                              'breaking_effect.forward_exponent': 8.0,
                              'breaking_effect.outward_velocity': 3.0,
                              'breaking_effect.outward_radius': 0.5,
                              'breaking_effect.outward_exponent': 0.2},
                   # list 2 on the projectile: the AIR damage range (Reach 0, 40 / sniper 0, 120
                   # onto the H1 sniper's 1000, 1000) -- the lower bound's ratio degenerates
                   # (0/0) and the tool's 1000 would invert the pair -> the SIBLING RULE, both
                   # by the upper's 40/120: 333.3, 333.3. Water 0, 10 x (-, 10/20) = 0, 5.
                   # Noise enums kept (sniper bullet medium / silent; the DMR is the quieter of
                   # the source pair). Reach's material response table has no Halo 1 field
                   'proj_fields': {'proj_attrs.physics.air_damage_range': (333.333, 333.333),
                                   'proj_attrs.physics.water_damage_range': (0.0, 5.0)},
                   # THE HIT-EFFECT RULE: max(default 3.0, balanced 4.5) = 4.5/s
                   'impact_thin': {'materials': [22], 'out': DMR + 'effects\\impact\\',
                                   'thin': {}, 'rate': 4.5}},
        # semi-automatic (Reach: latch, 3/s, recovery 0.33 s); the sniper's trigger otherwise
        'trigger': {'rounds_per_second': (3.0, 3.0), 'does_not_repeat_automatically': True,
                    # the sniper's 'use error when unzoomed' (error ONLY unzoomed): Reach's DMR
                    # blooms zoomed too (4b template diff, before boot 1)
                    'use_error_when_unzoomed': False,
                    # Reach blooms by a firing-penalty function (decay 0.7 s); Halo 1's ramp:
                    # full error after ~1 s of fire (3 shots), Reach's 0.7 s decay
                    'error_acceleration_time': 1.0, 'error_deceleration_time': 0.7,
                    # Reach's 'force contrails to come from weapon barrel': the sniper trail
                    # starts at the FP muzzle (the FP `primary trigger` in the idle pose, camera
                    # space forward / left / up wu, view offset included -- computed from the
                    # retarget, 2026-10-10), the Beam Rifle's test-1 fix
                    'first_person_offset': (0.288, -0.0378, -0.0269)},
        'error_deg': {'minimum_error': 0.0, 'error_angle': (0.15, 2.0)},
        # Reach: 15 loaded, 45 at pickup, 75 most; reload time 0 (the animation, as the sniper)
        'magazine': {'rounds_loaded_maximum': 15, 'rounds_reloaded': 15,
                     'rounds_total_initial': 45, 'rounds_total_maximum': 75,
                     'reload_time': 0.0},
        # (step 4b list 3: deviation angle 2.25 -- the H1 sniper's 0, a zero on one side)
        'aiming': {'autoaim_angle': 2.25, 'autoaim_range': 20.0,
                   'magnetism_angle': 5.0, 'magnetism_range': 20.0, 'deviation_angle': 2.25,
                   'zoom_levels': 1, 'zoom_ranges': (3.0, 3.0)},
        'sound_effects': {
            # TEST 1 (user): 'the muzzle flash feels too big and wide'. The sniper template's
            # flash = two SIDEWAYS fans of 15-20 `flash h sniper muzzle break` sprites (yaw
            # +-115 deg, radius to 0.125 wu) + a forward fan + side smoke + a warthog casing.
            # Reach's DMR first-person flash is small and AT the muzzle: long_brake / long_soft
            # on the four muzzle_flash markers (+-6 mm round the bore), a round flash and glow
            # (emitter bounds 0.06-0.11 wu), a BR casing. Nearest tested Halo 1 look = the BR
            # port's (the pistol's sprites: centre 0.045-0.056 wu + two small sides at +-0.023;
            # user-approved in A2) and its casing -> the copy starts from the BR's effect
            'firing_effect': (SR + 'effects\\fire bullet', DMR + 'effects\\fire bullet',
                              {'sound\\weapons\\battle_rifle_port\\br_fire': SND + 'dm_fire',
                               'sound\\weapons\\battle_rifle_port\\br_eject': SND + 'dm_eject'},
                              {'copy_from': 'weapons\\battle rifle\\effects\\fire bullet'})},
        'fields': {
            # the sniper's EMPTY field names a SOUND directly (the AR's dryfire; the Mauler trap)
            'weap_attrs.triggers.0.firing_effects.0.empty_effect.filepath': SND + 'dm_dryfire',
            'weap_attrs.interface.zoom_in_sound.filepath': SND + 'dm_zoom_in',
            'weap_attrs.interface.zoom_out_sound.filepath': SND + 'dm_zoom_out',
            'weap_attrs.interface.pickup_sound.filepath': SND + 'dm_ammo',
            'item_attrs.collision_sound.filepath': SND + 'dm_drop',
            # the sniper's integrated night vision: not the DMR's
            'weap_attrs.flags.enables_integrated_night_vision': False,
            # Reach: the SNIPER 'magnetizes only when zoomed', the DMR does not -> Halo 1's
            # aim_assists_only_when_zoomed off (the source pair differs: the port's own)
            'weap_attrs.flags.aim_assists_only_when_zoomed': False,
            # STEP 4b list 2 (ratio vs Reach's sniper onto the H1 sniper): camo ding 0.55 x
            # 0.75/1, ejection port recovery 0.15 x 0/0.15, illumination recovery 0.1 x 0.03/0.05
            'weap_attrs.interface.active_camo_ding': 0.55 * 0.75 / 1.0,
            'weap_attrs.triggers.0.misc.ejection_port_recovery_time': 0.0,
            'weap_attrs.triggers.0.misc.illumination_recovery_time': 0.06,
            # STEP 6: Reach's DMR has no per-weapon pickup count (its ammo box gives 0 -- Reach
            # tops up from dropped weapons), so the wave rule (the source's pickup count; the
            # BR: Halo 3's 72) has nothing to read. User (test 1, 2026-10-10): the YARDSTICK's
            # pickup : initial ratio instead -- H1 sniper 16 : 12 on Reach's 45 = 60. Balanced
            # initial is 45 too, so no balanced row (boot 1 had 15, one magazine)
            'weap_attrs.magazines.0.magazine_items.0.rounds': 60,
            # the on-gun counter (model 'numeric'): the AR's export layout (the BR)
            'weap_attrs.A_in': 'illumination',
            'weap_attrs.B_in': 'primary_ammunition',
        },
        'obje_functions': [{'from': AR + 'assault rifle', 'index': 0},
                           {'from': AR + 'assault rifle', 'index': 1,
                            'set': {'scale_function_by': 'A_in'}}],
        'attachment_scales': {0: ('B_out', 'none')},       # the muzzle-flash light
        'melee': (SR + 'melee', DMR + 'melee'),
        'melee_response': SR + 'melee_response',
        'messages': ('Picked up a DMR', 'Picked up %d rounds for DMR'),
        'icon': 'dmr',
        'extra_sounds': [SND + 'dm_reload_empty_balanced', SND + 'dm_reload_full_balanced'],
        # the SNIPER's HUD (its screen effect + magazine readout) with Reach's DMR reticle
        # (Reach hud_reticles #14, 'triple sized', chud scale 0.9) at the reserved 28; ZOOM =
        # Reach's scope (ui\chud\dmr `scope_mask`: Reach's battle_rifle_scope ring, mirrored,
        # extend border; the range ruler, crosshairs, distance gauge, '10' markers, the slider)
        'hud': {'donor': SR + 'sniper rifle', 'out': DMR + 'dmr',
                'screen_effect_clear': ('night_vision', 'desaturation'),
                'scope': {'chud': R + r'ui\chud\dmr', 'out': DMR + 'bitmaps\\scope_mask',
                          # span 660 / aspect 4:3 (the BR's) put Reach's ring at Reach's own
                          # 77% of the screen height (h1_h3_scope --screen, 2026-10-10). The
                          # magnification ARC (scope_distance_meter: scale 0, animated) and its
                          # SLIDER (animated by dmr_zoom along the arc) cannot be a static mask:
                          # dropped for boot 1 (user decides after seeing it)
                          # TEST 1 (user): 'shrink it to mirror the original size' -> Reach's
                          # 1152x640 HUD canvas read as its 90% SAFE AREA of 1280x720 (user's
                          # pick, 2026-10-10): span 660 / 0.9 = 733.3 -> the ring at 69% of the
                          # screen height. The ARC (scale 0 in the tag, animated) at scale 1 in
                          # Reach's own placement, and the SLIDER (animated along it by dmr_zoom)
                          # STATIC at the 3.0x end -- the DMR's one zoom level (user: 'add them
                          # as a static picture for a test'); its spot read off the art
                          'size': 1024, 'span': 660.0 / 0.9, 'aspect': 4 / 3.0, 'alpha': 'outside',
                          'per_widget': {'scope_distance_meter': {'scale': (1.0, 1.0)},
                                         'distance_slider': {'origin': (0.0, 0.0),
                                                             'offset': (141.0, -186.0)}}},
                # the SNIPER HUD's layout (4b template diff, before boot 1): its zoom overlays
                # are AIM-typed crosshairs with zoom-only overlays (type 6/5) -- crosshairs2,
                # _sm, caption -- + two zoom crosshairs: all but #0 dropped (Reach's scope
                # replaces them); its reticle draws from its OWN sheet (hud_reticles_scope) ->
                # the shared hud_reticles; its dont_scale_size (2) -> 0 as the pistol / BR; the
                # zoom angle ticks (static, on `age`) and distance / elevation numbers dropped
                'drop_crosshairs': [1, 2, 3, 4, 5],
                'reticle_bitmap': r'ui\hud\bitmaps\combined\hud_reticles',
                'reticle_scaling': 0,
                'drop_elements': {'static': ['age'],
                                  'number': ['distance_to_target', 'elevation_to_target']},
                'reticle': (R + r'ui\chud\bitmaps\hud_reticles', 14, 'dmr'),
                'reticle_min_width': 3,
                'ammo_meter': {'sizes': (15,), 'base': DMR + 'bitmaps\\dmr_ammo'}},
        'palette_levels': LEVELS,
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py dmr). DEFAULT = Reach's own
    # numbers in the tags; BALANCED = the SNIPER ratio rule (step 4a, user 2026-10-10).
    # Assembly Halo1 units: angles in degrees, velocity in wu per TICK
    'catalog': {
        'entry': {
            'weapon': 'DMR', 'source': 'Halo Reach', 'donor': 'Sniper Rifle', 'default_on': False,
            'desc': "Halo Reach's DMR: its model, first-person animations, sounds, scope and "
                    "numbers. A 15-round semi-automatic marksman rifle with a 3x zoom; Sniper "
                    "Rifle ammo tops it up.",
            'balance_desc': "Measured against the Sniper Rifle, which both games have: 22 "
                            "damage per round at up to 4.5 rounds a second, a tight spread, a "
                            "slower bullet with a longer reach and Halo 1-style aim assist; the "
                            "magazine, carry and zoom stay Reach's.",
            # step 9: ONE reload multiplier in the patcher for both reloads -- balanced empty 94
            # fr x 68/86 = 74.3 over the built 68 (x1.094), full 83 x 59/72 = 68.0 over 59
            # (x1.153): the mean x1.12 (user to confirm). Swap (ready + put-away, ONE
            # multiplier): H1 sniper ready 29 fr x Reach DMR 19 / Reach sniper 21 = 26.2 over
            # the built 19 = x1.38
            'anims': {'reload': 1.12, 'swap': 1.38},
            'anim_sounds': {'reload': [
                {'mult': 1.12, 'from': SND + 'dm_reload_empty', 'to': SND + 'dm_reload_empty_balanced'},
                {'mult': 1.12, 'from': SND + 'dm_reload_full', 'to': SND + 'dm_reload_full_balanced'}]},
            'balance': [
                row('jpt!', DMR + 'bullet', 'Damage Lower Bound', 22.09, 17.5, 'Bullet Damage'),
                row('jpt!', DMR + 'bullet', 'Damage Upper Bound', 22.09, 17.5, 'Bullet Damage'),
                row('jpt!', DMR + 'bullet', 'Damage Upper Bound Max', 22.09, 17.5, 'Bullet Damage'),
                row('weap', DMR + 'dmr', 'Rounds Per Second', 4.5, 3.0, 'More Shooting', block='Triggers'),
                row('weap', DMR + 'dmr', 'Rounds Per Second Max', 4.5, 3.0, 'More Shooting', block='Triggers'),
                row('weap', DMR + 'dmr', 'Minimum Error', 0.0, 0.0, 'Error Angle', block='Triggers'),
                row('weap', DMR + 'dmr', 'Error Angle', 0.019, 0.15, 'Error Angle', block='Triggers'),
                row('weap', DMR + 'dmr', 'Error Angle Max', 0.25, 2.0, 'Error Angle', block='Triggers'),
                row('proj', DMR + 'bullet', 'Initial Velocity', 16.667, 100.0, 'Projectile'),
                row('proj', DMR + 'bullet', 'Final Velocity', 16.667, 100.0, 'Projectile'),
                row('proj', DMR + 'bullet', 'Maximum Range', 500.0, 250.0, 'Projectile'),
                row('weap', DMR + 'dmr', 'Autoaim Angle', 2.81, 2.25, 'Autoaim'),
                row('weap', DMR + 'dmr', 'Autoaim Range', 35.0, 20.0, 'Autoaim'),
                row('weap', DMR + 'dmr', 'Magnetism Angle', 6.25, 5.0, 'Magnetism'),
                row('weap', DMR + 'dmr', 'Magnetism Range', 35.0, 20.0, 'Magnetism'),
            ]},
    },

    # step 4b (port_field_audit.py --port dmr): the source pair (Reach DMR vs the yardstick,
    # Reach's sniper) against the target pair (the H1 port vs its template, the H1 sniper)
    'field_audit': {
        'source_kit': 'HREK',
        'source': {'weapon': (RW + r'\dmr.weapon', r'objects\weapons\rifle\sniper_rifle\sniper_rifle.weapon'),
                   'projectile': (RW + r'\projectiles\dmr_bullet.projectile',
                                  r'objects\weapons\rifle\sniper_rifle\projectiles\sniper_rifle_bullet.projectile'),
                   'damage_effect': (RW + r'\projectiles\dmr_bullet.damage_effect',
                                     r'objects\weapons\rifle\sniper_rifle\projectiles\sniper_rifle_bullet.damage_effect')},
        'target': {'weapon': (DMR + 'dmr.weapon', SR + 'sniper rifle.weapon'),
                   'projectile': (DMR + 'bullet.projectile', SR + 'sniper bullet.projectile'),
                   'damage_effect': (DMR + 'bullet.damage_effect', SR + 'sniper bullet.damage_effect')}},

    # the dry test: a30 (Covenant within seconds of the landing), Reach's own loadout
    'test': {'level': 'a30', 'rounds': (15, 45), 'grunt': None, 'elite': None},
})
