r"""Covenant Carbine (Halo 3 -> Halo 1, wave A3) on a copy of the Halo 1 PISTOL (the
yardstick, step 4a). battle_rifle.py is the shape it copies (zoomed, pistol template);
what is new here: the scope from a COLLECTION-state chud (h1_h3_scope inherits the
collection's zoom state; per-widget decisions), a Covenant look on a bullet template (the
plasma pistol's green fire effect, bolt light and impacts) and a semi-automatic trigger."""
from ._common import B, H3_FP_GRAPHS, reserved, row

H3 = r'objects\weapons\rifle\covenant_carbine'
CC = 'weapons\\covenant carbine\\'
SND = 'sound\\weapons\\covenant_carbine_port\\'
PISTOL = 'weapons\\pistol\\'
PP = 'weapons\\plasma pistol\\'

PORT = reserved(
    order=12, wave='A3', name='Covenant Carbine', source='Halo 3',
    messages=(57, 58), icon=32, reticle=21, label='cc', teach_from='ar',
    sound_dir='sound\\weapons\\covenant_carbine_port', weapon_dir='weapons\\covenant carbine',
    yardstick={
        # step 4a (user, 2026-10-07): h1_role_compare.py covenant_carbine -- the pistol ratio
        # is the only candidate whose every value scales (needler ratio: the needle's 65 wu/s
        # and degenerate error carry over, no zoom; sniper ratio: zoom 2 x 2/4 = 1x, Flood
        # combat forms take 36 s on the sniper bullet's materials). Pistol ratio: 137/s
        # against the H1 pistol's 88 (Halo 3: carbine 59, magnum 38 -- the same 1.57).
        'pick': 'Pistol',
        'reason': "user, step 4a 2026-10-07: the magnum's role (semi-automatic precision, mid "
                  "range, 2x zoom = the H1 pistol's own); H1 value = H1 pistol x H3 carbine / "
                  "H3 magnum. Rate = 1 / fire recovery (carbine 0.17 s, magnum 0.4 s). "
                  "Material table (user, same day): the H1 pistol bullet's -- Halo 3's "
                  "plasma_fast has NO shield bonus (energy_shield x1, unlike plasma_slow's 1.5) "
                  "-- with Halo 3's two differences Halo 1 has a material for: Jackal shield "
                  "0 -> 0.5 (energy_shield_thick 0.5), Sentinel 0.2 -> 2.0",
        # DEFAULT = Halo 3's own numbers (PORTING "Balance"); these are the BALANCED rows.
        # H3: carbine / magnum. H1 pistol: 25 dmg, 3.5/s, 12 / 60 / 120, 67 fr reload,
        # error 0.2 -> 2.0, 300 wu/s, range 40, aim 3/30 6/30, melee 55
        'balanced': {
            'damage': 16.67,             # 25 x 10/15
            'rate': 8.24,                # 3.5/s x (5.88 / 2.5)
            'magazine': 27,              # 12 x 18/8
            'rounds_total_initial': 101,  # 60 x 54/32 = 101.25
            'rounds_total_maximum': 225,  # 120 x 90/48 (not dual-wieldable: no carry rule)
            'ammo_pickup': 67,           # the default's 36 : 54 on the balanced 101 (SMG rule)
            'reload_s': 3.08,            # 67 fr x 69/50 = 92.5 fr
            'error_deg': (0.12, 2.4),    # 0.2 x 0.3/0.5, 2.0 x 0.6/0.5; minimum 0 (H3 carbine 0)
            'velocity': 300.0,           # 300 x 180/180
            'range': 60.0,               # 40 x 60/40
            'aim': (4.5, 34.0, 6.0, 31.5),  # 3 x 3/2, 30 x 17/15; 6 x 6/6, 30 x 21/20
            'zoom': 2.0,                 # magnum has none: Halo 3's own 2x (= the H1 pistol's)
            'melee': 55.0},              # H3 shares strike_melee: x1 = the H1 pistol's
        'measured': 'h1_role_compare.py covenant_carbine',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\covenant_carbine\\covenant_carbine',
            'provisional': 'Pistol',
            'alternatives': ['Needler', 'Sniper Rifle'],
            'direct': None,
            'peers': ['Pistol', 'Sniper Rifle', 'Needler'],
            'why': 'semi-auto magazine (18), 2x zoom, instant slug: the Covenant precision rifle',
            'lacks': ''}},
    # step 11: the source game's ai\generic entry (26 fields, verified 2026-10-07), laid over
    # a base -- 'cc' has no carrier (smg.py's lesson): the AR's carriers, as the SMG / BR
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\rifle\\covenant_carbine\\covenant_carbine',
                    'donor_weapon': 'weapons\\assault rifle\\assault rifle'},
)

PORT.update({
    'status': 'building',
    # geometry + look (h1_h3_weapon_model.py). Halo 3's five materials (render model order:
    # carbine, carbine_dull, carbine_tint_map, carbine_display, carbine_switch): the metal
    # and its dull and striped variants share the base map + illum (glow = the illum map's own
    # cyan, 0.4% of its texels lit: Halo 3's carbine glows mostly from the two METERS).
    # TEST 1 (user): 'a flat square on the weapon at the glowy part' -- carbine_display and
    # carbine_switch are Halo 3 METER shaders (meter_map, meter_value <- ammo), first built as
    # opaque shader_models. Now Halo 1 shader_transparent_meters (`meters`, channels swapped,
    # see h1_h3_weapon_model.meters): the display = the 18-step ammo bar (its alpha), the
    # switch (the round symbol) lit while a round is loaded. Template: the plasma rifle's FP
    # gun shader (Covenant metal, as the Sentinel Beam)
    'model': {
        'dir': r'weapons\covenant carbine',
        'world': H3 + r'\covenant_carbine.render_model',
        'fp': H3 + r'\fp_covenant_carbine\fp_covenant_carbine.render_model',
        'world_name': 'covenant carbine',
        'shaders': {'carbine': (H3 + r'\bitmaps\covenant_carbine.bitmap', H3 + r'\bitmaps\covenant_carbine_illum.bitmap'),
                    'carbine_dull': (H3 + r'\bitmaps\covenant_carbine.bitmap', H3 + r'\bitmaps\covenant_carbine_illum.bitmap'),
                    'carbine_tint_map': (H3 + r'\bitmaps\covenant_carbine.bitmap', H3 + r'\bitmaps\covenant_carbine_illum.bitmap'),
                    },
        'template': r'weapons\plasma rifle\fp\shaders\gun',
        # the meters' colour: the illum map's lit mean (24, 211, 247) normalized; 'off' a
        # quarter of it (Halo 3's meter_color_off sits in unreadable function data)
        'meters': {'carbine_display': {'map': H3 + r'\bitmaps\covenant_carbine_display_illum.bitmap',
                                       'from': r'weapons\plasma rifle\fp\shaders\gauge',
                                       'gradient': 'alpha', 'value': 'A_out',
                                       'color': (0.097, 0.854, 1.0)},
                   'carbine_switch': {'map': H3 + r'\bitmaps\covenant_carbine_switch_illum.bitmap',
                                      'from': r'weapons\plasma rifle\fp\shaders\gauge',
                                      'gradient': 0.0, 'value': 'A_out',
                                      'color': (0.097, 0.854, 1.0)}},
    },

    # FP animations (h1_fp_retarget.py). Halo 3 carbine frames: ready 19, put_away 4, fire_1
    # var1..3 9 each, melee 30 (primary_keyframe 4), reload empty/full 69 each (primary 48),
    # posing var1 / var2 94. NOT dual-wieldable: one resource group expected (--list)
    'retarget': {
        'graph': H3_FP_GRAPHS + r'\rifle\fp_covenant_carbine\fp_covenant_carbine.model_animation_graph',
        'render_model': H3 + r'\fp_covenant_carbine\fp_covenant_carbine.render_model',
        'nodes': {n: 'frame ' + n for n in ('gun', 'barrel', 'battery', 'hood', 'display')},
        'h1_dir': r'weapons\covenant carbine\fp',
        'h1_model': r'weapons\covenant carbine\fp\fp',
        'align': 'same_space',
        # the BR's tested placement (user, A2), tuned per weapon in test 1
        'view_offset': (-0.0225, 0.0, -0.0125),
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

    # Halo 3's own sounds (h1_port_sounds.py covenant_carbine). Levels = the active RMS of the
    # stock Halo 1 PISTOL sound each stands in for (the BR's measurements, h1_stock_sound_
    # levels.py 2026-10-07). The carbine fires ONE shot a pull: no `shots` slicing. Halo 3's
    # graph cues reload_empty on BOTH reloads; no casing eject (the slug has no casing)
    'sounds': {
        'catalog': 'Covenant Carbine',
        'dir': B.join(['sound', 'weapons', 'covenant_carbine_port']),
        'h3_dir': 'data\\sound\\weapons\\covenant_carbine\\',
        'sounds': {
            'cc_fire': (['carbine_fire'], 'sound\\sfx\\weapons\\pistol\\fire', -12.8),
            'cc_dryfire': (['carbine_misfire'], 'sound\\sfx\\weapons\\pistol\\dryfire', -15.3),
            'cc_reload': (['reload_empty'], 'sound\\sfx\\weapons\\weapon_anims\\pistol_reload', -19.0),
            'cc_ready': (['ready'], 'sound\\sfx\\weapons\\weapon_anims\\pistol_ready', -15.2),
            'cc_melee': (['carbine_fp_melee_1'], 'sound\\sfx\\weapons\\weapon_anims\\pistol_melee', -19.8),
            'cc_pose': (['carbine_posing1'], 'sound\\sfx\\weapons\\weapon_anims\\pistol_posing', -26.5),
            'cc_zoom_in': (['carbine_zoom_in'], 'sound\\sfx\\weapons\\sniper rifle\\sniper_2x_zoom', -28.9),
            'cc_zoom_out': (['carbine_zoom_out'], 'sound\\sfx\\weapons\\sniper rifle\\sniper_10x_zoom', -29.2),
            'cc_ammo': (['carbine_ammo_pickup'], 'sound\\sfx\\weapons\\weapon_pickup_ammo\\pistol_ammo', -28.4),
            'cc_drop': (['carbine_drop'], 'sound\\sfx\\impulse\\weapon_drops\\pistol_impact', -28.8),
            # the BALANCED reload's sound (the patcher retimes both reloads x1.34, then swaps
            # this in -- one sound for both, as Halo 3)
            'cc_reload_balanced': (['reload_empty'], 'sound\\sfx\\weapons\\weapon_anims\\pistol_reload', -19.0),
        },
        'stretch': {'cc_reload_balanced': 1.34},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only covenant_carbine) on a COPY of the Halo 1
    # PISTOL (the yardstick: its zoom, magazine HUD and bullet materials). DEFAULT = HALO 3's
    # OWN NUMBERS; the ratio values are the balance rows (yardstick['balanced']).
    'pickable': {
        'weapon': CC + 'covenant carbine',
        'template': PISTOL + 'pistol',
        'world_model': CC + 'covenant carbine',
        'fp_model': CC + 'fp\\fp',
        'fp_anims': CC + 'fp\\fp',
        'label': 'cc',
        'teach': ('cc', 'ar'),
        'keys': {'first-person melee': 4},          # H3 melee_strike_1 primary_keyframe 4
        'sounds': {'first-person ready': SND + 'cc_ready',
                   'first-person posing': SND + 'cc_pose',
                   'first-person melee': SND + 'cc_melee',
                   'first-person reload-empty': SND + 'cc_reload',
                   'first-person reload-full': SND + 'cc_reload'},
        # own slug + damage (step 3): H3 carbine_slug 10 damage, 180 wu/s, range 60 (magnum
        # 15, 180, 40). Materials (user, step 4a): the pistol bullet's + Jackal shield 0.5,
        # Sentinel 2.0. The LOOK is Covenant: Halo 3's slug is a green glowing bolt with a
        # contrail and plasma impacts -- the plasma pistol bolt's green light and its impact
        # effects per material (the H1 pistol bullet has no visible projectile)
        'bullet': {'projectile': (PISTOL + 'bullet', CC + 'slug'),
                   'damage': (PISTOL + 'bullet', CC + 'slug'),
                   'dmg': 10.0, 'velocity': 180.0, 'range': 60.0,
                   'fields': {'damage_modifiers.jackal_energy_shield': 0.5,
                              'damage_modifiers.sentinel': 2.0,
                              # step 4b list 2 (ratio vs the H3 magnum bullet, onto the H1
                              # pistol bullet): active camo damage 0.45 x 0.2/0.15; screen
                              # flash 0.4 x 0.5/0.4 (Halo 1 has one response: the SHIELDED
                              # one, as the BR). Wobble period (0 x ...) NOT written: Halo 1's
                              # wobble function here is 'one' (constant), as the BR.
                              # list 3 (the BR's rules): fade function linear (Halo 3's
                              # shielded; magnum early), breaking effect = Halo 3's own where
                              # the magnum has 0. NOT ported: wobble function jitter (as BR)
                              'damage.active_camouflage_damage': 0.45 * 0.2 / 0.15,
                              'screen_flash.duration': 0.5,
                              'screen_flash.fade_function': 'linear',
                              'breaking_effect.forward_velocity': 35.0,
                              'breaking_effect.forward_radius': 0.12,
                              'breaking_effect.forward_exponent': 8.0,
                              'breaking_effect.outward_velocity': 3.0,
                              'breaking_effect.outward_radius': 0.5,
                              'breaking_effect.outward_exponent': 0.2},
                   'attachments_from': PP + 'bolt',
                   'material_responses_from': PP + 'bolt'},
        # SEMI-AUTOMATIC (Halo 3 'latch-zoom' primary): one round a pull at most 1 / 0.17 s =
        # 5.88/s (Halo 1 pistol: automatic at 3.5/s). H3 bloom ramp 1.0 / 0.5 (magnum 0 / 0:
        # no ratio, the source value)
        'trigger': {'rounds_per_second': (1 / 0.17, 1 / 0.17), 'acceleration_time': 0.0,
                    'deceleration_time': 0.0, 'does_not_repeat_automatically': True,
                    'error_acceleration_time': 1.0, 'error_deceleration_time': 0.5},
        'fields': {
            # step 4b, list 2 (ratio vs the H3 magnum, onto the H1 pistol): bounding radius
            # 0.1 x 0.225/0.08, acceleration scale 2 x 1/1.25, active camo ding 0.65 x
            # 0.25/0.4, illumination recovery 0.1 x 0.1/0.05
            'obje_attrs.bounding_radius': 0.1 * 0.225 / 0.08,
            'obje_attrs.acceleration_scale': 2.0 * 1.0 / 1.25,
            'weap_attrs.interface.active_camo_ding': 0.65 * 0.25 / 0.4,
            'weap_attrs.triggers.0.misc.illumination_recovery_time': 0.1 * 0.1 / 0.05,
            # list 3 (zero on one side -> Halo 3's own): bounding offset (magnum 0)
            'obje_attrs.bounding_offset.x': 0.075,
            # STEP 6 (user): pistol ammo tops it up (the template's item). Halo 3 has NO
            # carbine magazine item (only dropped carbines refill it): its family's pickup :
            # initial (BR 72 : 108, SMG 120 : 180 = 2/3) on 54 = 36, two magazines
            'weap_attrs.magazines.0.magazine_items.0.rounds': 36,
            # Halo 3's zoom / ammo pickup / drop sounds (the template names the pistol's)
            'weap_attrs.interface.zoom_in_sound.filepath': SND + 'cc_zoom_in',
            'weap_attrs.interface.zoom_out_sound.filepath': SND + 'cc_zoom_out',
            'weap_attrs.interface.pickup_sound.filepath': SND + 'cc_ammo',
            'item_attrs.collision_sound.filepath': SND + 'cc_drop',
            # the muzzle-flash LIGHT: the pistol template's is the AR's (orange); Halo 3's
            # carbine flash is green -> the plasma pistol's green flash light, same slot
            'obje_attrs.attachments.0.type.filepath': PP + 'muzzle flash',
            # the METERS' input (model `meters`, value A out): the BR's lesson -- the pistol's
            # ONE function (A illumination) also scales the muzzle-flash light, so the AR's
            # layout: exports A illumination / B loaded fraction; out A = ammo (meters), out
            # B = muzzle flash (the light, attachment_scales)
            'weap_attrs.A_in': 'illumination',
            'weap_attrs.B_in': 'primary_ammunition',
        },
        'obje_functions': [{'from': r'weapons\assault rifle\assault rifle', 'index': 0},
                           {'from': r'weapons\assault rifle\assault rifle', 'index': 1,
                            'set': {'scale_function_by': 'A_in'}}],
        'attachment_scales': {0: ('B_out', 'none')},       # the muzzle-flash light
        # H3 single-wield: minimum error 0, error angle 0.3 -> 0.6 (H1 pistol 0, 0.2 -> 2.0)
        'error_deg': {'minimum_error': 0.0, 'error_angle': (0.3, 0.6)},
        # H3: 18 loaded, 54 at pickup, 90 most. Reload: H3 0 (the animation decides): 69 fr =
        # 2.3 s, in the H1 pistol's shape (2.17 tag over its 2.23 s animation) = 2.24
        'magazine': {'rounds_loaded_maximum': 18, 'rounds_reloaded': 18,
                     'rounds_total_initial': 54, 'rounds_total_maximum': 90,
                     'reload_time': 2.24},
        # H3 aim assist, absolute. Zoom: Halo 3's 1 level at 2x = the pistol template's own
        'aiming': {'autoaim_angle': 3.0, 'autoaim_range': 17.0,
                   'magnetism_angle': 6.0, 'magnetism_range': 21.0},
        'sound_effects': {
            # the plasma pistol's green flash (no casing), Halo 3's fire sound
            'firing_effect': (PISTOL + 'effects\\fire bullet', CC + 'effects\\fire slug',
                              {r'sound\sfx\weapons\plasma rifle\fire': SND + 'cc_fire'},
                              {'copy_from': PP + 'effects\\fire bolt'}),
            'empty_effect': (PISTOL + 'effects\\empty', CC + 'effects\\empty',
                             {r'sound\sfx\weapons\pistol\dryfire': SND + 'cc_dryfire'})},
        'melee': (PISTOL + 'melee', CC + 'melee'),
        'melee_response': PISTOL + 'melee_response',
        'messages': ('Picked up a covenant carbine', 'Picked up %d rounds for covenant carbine'),
        'icon': 'covenant carbine',
        'extra_sounds': [SND + 'cc_reload_balanced'],
        # the PISTOL's HUD with Halo 3's carbine reticle (H3 hud_reticles #4; the headshot
        # cross not reproduced) at the reserved 21, a magazine meter for 18 / 27. ZOOM = Halo
        # 3's scope (the standard): ui\chud\carbine's `scope_bitmaps` collection (zoom lvl 1)
        # baked into the mask -- the honeycomb lens and side cells (`scope`, 4 mirrored
        # copies), the four needle wedges (scale 0 in the chud, 1.0 from their 'active'
        # .chad; their small slide not reproduced), both static blips; `scope_blur`
        # (carbine_distortion, a refraction over the two SIDE cells): user, 2026-10-07 --
        # 'gentle blur in its hex': Halo 1's blur at half strength there. Span: Halo 3's lens
        # is 384 of 640 units tall (60%) = 648 px at 1080 = 594 texels -> 1024 x 384/594 = 662
        'hud': {'donor': PISTOL + 'pistol', 'out': CC + 'covenant carbine',
                'scope': {'chud': r'ui\chud\carbine', 'out': CC + 'bitmaps\\scope_mask',
                          # TEST 1 (user): masks good; 'reduce the size, it's stretched
                          # horizontally while the original looks 1:1'. The baked honeycomb
                          # cells are 1.25 wide : 1 tall where a regular hexagon is 1.155 ->
                          # test 2 variant A (this config): x squashed by 1.155/1.25 (aspect
                          # 4/3 / 0.924 = 1.443), 80% size (span 662 / 0.8 = 828); variant B
                          # (a test-only secondary): squashed 0.8 (aspect 1.667), same size
                          'size': 1024, 'span': 828.0, 'aspect': 1.443, 'alpha': 'outside',
                          'per_widget': {'scope_crosshairs1': {'scale': (1.0, 1.0)},
                                         'scope_crosshairs2': {'scale': (1.0, 1.0)},
                                         'scope_crosshairs3': {'scale': (1.0, 1.0)},
                                         'scope_crosshairs4': {'scale': (1.0, 1.0)},
                                         'scope_blur': {'blur': 0.5}}},
                'reticle': ('hud_reticles', 4, 'covenant carbine'),
                'reticle_thicken': 1,
                'flash_base': 12,                # the pistol's low-ammo cutoff is of 12
                'ammo_meter': {'sizes': (18, 27), 'base': CC + 'bitmaps\\carbine_ammo'}},
        'palette_levels': ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40'],
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py covenant_carbine). DEFAULT =
    # Halo 3's own numbers in the tags; BALANCED = the PISTOL ratio rule (step 4a, user
    # 2026-10-07). Assembly Halo1 units: angles in degrees, velocity in wu per TICK.
    'catalog': {
        'entry': {
            'weapon': 'Covenant Carbine', 'source': 'Halo 3', 'donor': 'Pistol', 'default_on': False,
            'desc': "Halo 3's Covenant Carbine: its model, first-person animations, sounds, "
                    "scope and numbers. An 18-round semi-automatic rifle with a 2x zoom; "
                    "Pistol ammo tops it up.",
            'balance_desc': "Measured against the Pistol, which both games have: 16.7 damage "
                            "per round, up to 8.2 rounds a second, a 27 magazine, 101 at "
                            "pickup / 225 most, a 3.1 s reload, a wider spread when held, "
                            "a faster slug and Halo 1-style aim assist.",
            # step 9: the balanced reload, 67 fr x 69/50 = 92.5 fr, against the BUILT 69
            # frames = x1.34; swap (ready + put-away, ONE multiplier in the patcher): ready
            # 35 x 19/22 = 30.2 frames over the built 19 = x1.59
            'anims': {'reload': 1.34, 'swap': 1.59},
            'anim_sounds': {'reload': [
                {'mult': 1.34, 'from': SND + 'cc_reload', 'to': SND + 'cc_reload_balanced'}]},
            'balance': [
                row('jpt!', CC + 'slug', 'Damage Lower Bound', 16.67, 10.0, 'Bullet Damage'),
                row('jpt!', CC + 'slug', 'Damage Upper Bound', 16.67, 10.0, 'Bullet Damage'),
                row('jpt!', CC + 'slug', 'Damage Upper Bound Max', 16.67, 10.0, 'Bullet Damage'),
                row('weap', CC + 'covenant carbine', 'Rounds Per Second', 8.24, 5.88, 'More Shooting', block='Triggers'),
                row('weap', CC + 'covenant carbine', 'Rounds Per Second Max', 8.24, 5.88, 'More Shooting', block='Triggers'),
                row('weap', CC + 'covenant carbine', 'Rounds Loaded Maximum', 27.0, 18.0, 'Magazine', block='Magazines'),
                row('weap', CC + 'covenant carbine', 'Rounds Reloaded', 27.0, 18.0, 'Magazine', block='Magazines'),
                row('weap', CC + 'covenant carbine', 'Rounds Total Initial', 101.0, 54.0, 'Magazine', block='Magazines'),
                row('weap', CC + 'covenant carbine', 'Rounds Total Maximum', 225.0, 90.0, 'Magazine', block='Magazines'),
                # STEP 6 balanced: the default's pickup : initial (36 / 54) on 101
                row('weap', CC + 'covenant carbine', 'Rounds', 67, 36, 'Ammo pickup', block='Magazines/Magazines'),
                row('weap', CC + 'covenant carbine', 'Minimum Error', 0.0, 0.0, 'Error Angle', block='Triggers'),
                row('weap', CC + 'covenant carbine', 'Error Angle', 0.12, 0.3, 'Error Angle', block='Triggers'),
                row('weap', CC + 'covenant carbine', 'Error Angle Max', 2.4, 0.6, 'Error Angle', block='Triggers'),
                row('proj', CC + 'slug', 'Initial Velocity', 10.0, 6.0, 'Projectile'),
                row('proj', CC + 'slug', 'Final Velocity', 10.0, 6.0, 'Projectile'),
                row('weap', CC + 'covenant carbine', 'Autoaim Angle', 4.5, 3.0, 'Autoaim'),
                row('weap', CC + 'covenant carbine', 'Autoaim Range', 34.0, 17.0, 'Autoaim'),
                row('weap', CC + 'covenant carbine', 'Magnetism Angle', 6.0, 6.0, 'Magnetism'),
                row('weap', CC + 'covenant carbine', 'Magnetism Range', 31.5, 21.0, 'Magnetism'),
                # the 27 magazine's meter: carbine_ammo sequence 1 (ammo_meter 18 27, step 9 /
                # multiplier 9 vs 14), low-ammo flash 4 of 12 -> 6 of 18, 9 of 27
                dict(row('wphi', CC + 'covenant carbine', 'Sequence Index', 1, 0, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', CC + 'covenant carbine', 'Alpha Multiplier', 9, 14, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', CC + 'covenant carbine', 'Sequence Index', 1, 0, 'Ammo display', block='Static Elements'), index=0),
                dict(row('wphi', CC + 'covenant carbine', 'Loaded Ammo Cutoff', 9, 6, 'Ammo display'), index=0),
            ]},
    },

    # step 4b (port_field_audit.py --port covenant_carbine): the source pair (H3 carbine vs
    # the yardstick, H3 magnum) against the target pair (the H1 port vs its donor, the pistol)
    'field_audit': {
        'source_kit': 'H3EK',
        'source': {'weapon': (H3 + r'\covenant_carbine.weapon', r'objects\weapons\pistol\magnum\magnum.weapon'),
                   'projectile': (H3 + r'\projectiles\carbine_slug\carbine_slug.projectile',
                                  r'objects\weapons\pistol\magnum\projectiles\magnum_bullet.projectile'),
                   'damage_effect': (H3 + r'\damage_effects\carbine_slug.damage_effect',
                                     r'objects\weapons\pistol\magnum\damage_effects\magnum_bullet.damage_effect')},
        'target': {'weapon': (CC + 'covenant carbine.weapon', PISTOL + 'pistol.weapon'),
                   'projectile': (CC + 'slug.projectile', PISTOL + 'bullet.projectile'),
                   'damage_effect': (CC + 'slug.damage_effect', PISTOL + 'bullet.damage_effect')}},

    # the dry test: a30 (Covenant within seconds of the landing), Halo 3's own loadout
    'test': {'level': 'a30', 'rounds': (18, 54), 'grunt': None, 'elite': None},
})
