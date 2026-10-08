r"""Beam Rifle (Halo 3 -> Halo 1, wave A4) on a copy of the Halo 1 PLASMA PISTOL (heat + battery,
no magazine: the role table's template) with the SNIPER RIFLE as the yardstick (step 4a).
covenant_carbine.py is the zoomed shape it copies, sentinel_beam.py the heat one; what is new
here: a TAPPED heat weapon (two quick shots overheat it), a scope chud with a fullscreen and
a split-screen widget set (h1_h3_scope reads the window state), the template's charged
trigger dropped, and the zoom screen effect taken from the sniper's HUD."""
from ._common import B, H3_FP_GRAPHS, reserved, row

H3 = r'objects\weapons\rifle\beam_rifle'
BM = 'weapons\\beam rifle\\'
SND = 'sound\\weapons\\beam_rifle_port\\'
PP = 'weapons\\plasma pistol\\'
SR = 'weapons\\sniper rifle\\'
OH = 'beam_rifle_overheat\\beam_rifle_overheat\\'
# Halo 3's beam is pink-magenta (its colours sit in function data: a start, tuned in game)
PINK = (1.0, 0.45, 0.85)

PORT = reserved(
    order=13, wave='A4', name='Beam Rifle', source='Halo 3',
    messages=(59, 60), icon=33, reticle=22, label='bm', teach_from='sr',
    sound_dir='sound\\weapons\\beam_rifle_port', weapon_dir='weapons\\beam rifle',
    yardstick={
        # step 4a (user, 2026-10-08): h3_weapon_values.py (+ heat / CAMPAIGN battery / zoom
        # rows) and h1_role_compare.py beam_rifle (+ a heat simulation: the time to kill waits
        # out overheats). The sniper ratio is the only candidate whose every value scales:
        # plasma pistol ratio 205.7 damage (one-shots every Elite: the pistol's 7 is tiny),
        # its rate degenerate (both pistols tapped); Sentinel Beam ratio = two derivations
        # chained, a 5-shot battery, 37 dps sustained. Halo 3: beam 80 per 0.4 s, sniper 80
        # per 0.7 s -- the same damage, speed, range and aim; rate, heat, battery and the
        # damage group differ
        'pick': 'Sniper Rifle',
        'reason': "user, step 4a 2026-10-08: the sniper's role (one-hit precision, two zooms); "
                  "H1 value = H1 sniper x H3 beam rifle / H3 sniper. Rate = 1 / fire recovery "
                  "(beam 0.4 s, sniper 0.7 s). Heat and battery have no sniper counterpart: "
                  "Halo 3's own in both versions. Battery (user): Halo 3's CAMPAIGN age 0.05 a "
                  "shot = 20 shots (the plain field, 0.1, is multiplayer). Materials (user): "
                  "the H1 sniper bullet's table + Halo 3's plasma_fast differences Halo 1 has a "
                  "material for (the Carbine's pair): Jackal shield 0 -> 0.5, Sentinel 0.2 -> "
                  "2.0; Flood stays 0.05 (Halo 3's bullet_fast and plasma_fast treat Flood "
                  "alike: the 0.05 is Halo 1's sniper design). Heat loss: Halo 1 has ONE (Halo 3: "
                  "0.575 cooling, 0.3 overheated); Bungie's own pair splits (H1 plasma rifle 0.3 = "
                  "H3's overheated loss, vents match; H1 plasma pistol 0.65 = H3's cooling loss, "
                  "vents faster) -- user: both in one boot (0.3 the gun, 0.575 the variant), then "
                  "test 1: 'A too slow, B never overheats if played right: the average' = 0.4375",
        # DEFAULT = Halo 3's own numbers (PORTING "Balance"); these are the BALANCED rows.
        # H1 sniper: 101 dmg, 2/s, 1000 wu/s, range 1000, zoom 2 (2, 8), aim 1/35 2/35,
        # error 0.5, melee 55; H3 sniper 80, 1 / 0.7 s, 1200, 500, zoom (4, 9), aim 1/10 4/14
        'balanced': {
            'damage': 101.0,             # 101 x 80/80
            'rate': 3.5,                 # 2/s x (2.5 / 1.43)
            'velocity': 1000.0,          # 1000 x 1200/1200
            'range': 1000.0,             # 1000 x 500/500
            'zoom': (1.75, 8.44),        # (2, 8) x (3.5/4, 9.5/9)
            'aim': (1.0, 35.0, 2.0, 35.0),  # x1 each (Halo 3's beam = its sniper)
            'error_deg': 0.5,            # 0.5 x 0.5/0.5
            'heat': None,                # no sniper heat: Halo 3's own (0.7 a shot; loss 0.4375, test 1)
            'battery': None,             # no sniper battery: Halo 3's campaign 20 shots
            'melee': 55.0},              # H3 shares strike_melee: x1 = the H1 sniper's 55
        'measured': 'h1_role_compare.py beam_rifle',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\beam_rifle\\beam_rifle',
            'provisional': 'Sniper Rifle',
            'alternatives': ['Plasma Pistol', 'Sentinel Beam'],
            'direct': None,
            'peers': ['Sniper Rifle'],
            'why': 'instant beam, two zoom levels, heat-limited fire + battery',
            'lacks': ''}},
    # step 11: the source game's ai\generic entry (17 fields, verified 2026-10-07); 'bm' has
    # no carrier -- donor_weapon and the ARMED WDM RULE are chosen with the user (step 11)
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\rifle\\beam_rifle\\beam_rifle'},
)

PORT.update({
    'status': 'building',
    # geometry + look (h1_h3_weapon_model.py). Halo 3's five materials: beam_rifle and
    # beam_rifle2 (the metal: base + illum map), beam_rifle_rubber (base only), and two with
    # no Halo 1 maps of their own -- `beam_rifle_glass` (a dark reflective lens) and
    # `beam_rifle_luminous` (an animated energy field on Halo 3 multiplayer bitmaps): copies
    # of stock Halo 1 shaders (`shader_copies`). No Halo 3 METER shader on this gun.
    # Template: the plasma rifle's FP gun shader (Covenant metal, as the Carbine)
    'model': {
        'dir': r'weapons\beam rifle',
        'world': H3 + r'\beam_rifle.render_model',
        'fp': H3 + r'\fp_beam_rifle\fp_beam_rifle.render_model',
        'world_name': 'beam rifle',
        'shaders': {'beam_rifle': (H3 + r'\bitmaps\beam_rifle.bitmap', H3 + r'\bitmaps\beam_rifle_illum.bitmap'),
                    'beam_rifle2': (H3 + r'\bitmaps\beam_rifle.bitmap', H3 + r'\bitmaps\beam_rifle_illum.bitmap'),
                    'beam_rifle_rubber': (H3 + r'\bitmaps\beam_rifle.bitmap', None)},
        'shader_copies': {'beam_rifle_glass': r'weapons\plasma rifle\fp\shaders\dull.shader_model',
                          'beam_rifle_luminous': r'weapons\plasma rifle\fp\shaders\luminous.shader_model'},
        'template': r'weapons\plasma rifle\fp\shaders\gun',
        # TEST 1 (user): 'no glow on the gun at all' -- Halo 3's illum map is a GREYSCALE mask
        # (its colour is the shader's self_illum_color, function data), 1% of texels lit in
        # thin lines Halo 3 blooms: the Carbine's fix, lines thickened 1 px each way and a set
        # colour (the beam's pink, judged in test 2)
        # TEST 2 (user): still no visible glow -- every lit texel maps to 66 triangles of
        # `beam_rifle` that all FACE DOWN (z normal < -0.3, none up), on the underside of the
        # upper body just above the grip (x 1..6 of -11..50 cm): out of sight from the
        # first-person camera, as in Halo 3. Kept (it shows on a dropped gun from below)
        'illum_dilate': 1,
        'glow': PINK,
        # the template's overheat steam / misfire burst spawn at a marker: Halo 3's vent
        'markers': {'fx_vent': 'overheat'},
    },

    # FP animations (h1_fp_retarget.py). Halo 3 beam rifle frames: ready 22, put_away 6,
    # fire_1 var1..3 19 each, melee 29 (primary_keyframe 4), overheating 59, overheated 59
    # (Halo 3 HAS the looped hold the Sentinel Beam lacked), o_h_exit 24, posing var1 89 /
    # var2 157. Not dual-wieldable: one resource group expected (--list)
    'retarget': {
        'graph': H3_FP_GRAPHS + r'\rifle\fp_beam_rifle\fp_beam_rifle.model_animation_graph',
        'render_model': H3 + r'\fp_beam_rifle\fp_beam_rifle.render_model',
        'nodes': {n: 'frame ' + n.replace('_', ' ') for n in ('gun', 'ammo', 'barrel', 'scope_link')},
        'h1_dir': r'weapons\beam rifle\fp',
        'h1_model': r'weapons\beam rifle\fp\fp',
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
            'first_person:overheating': 'first-person overheating',
            'first_person:overheated': 'first-person overheated',
            'first_person:o_h_exit': 'first-person o-h-exit',
            'first_person:throw_grenade': 'first-person throw-grenade',
            'first_person:throw_overheated': 'first-person throw-overheated',
        },
    },

    # Halo 3's own sounds (h1_port_sounds.py beam_rifle). Levels = the active RMS of the stock
    # Halo 1 SNIPER sound each stands in for (the yardstick's role; h1_stock_sound_levels.py
    # 2026-10-08): fire -12.4, ready -21.6, melee -21.5, posing -19.1, zooms -28.9 / -29.2;
    # the overheat = the plasma rifle's overheat (-19.5), the drop the plasma impact (-18.7).
    # Halo 3's fire is ONE shot a pull (the first-person fire sound). The overheat: Halo 3's
    # in and out on Halo 1's FP overheat animations (see bm_overheat)
    'sounds': {
        'catalog': 'Beam Rifle',
        'dir': B.join(['sound', 'weapons', 'beam_rifle_port']),
        'h3_dir': 'data\\sound\\weapons\\beam_rifle\\',
        'sounds': {
            # TEST 1 (user): 'the firing sound is missing' -- beam_rifle_first_person_fire is
            # only Halo 3's first-person LAYER (silent 0.3 s, then two clicks); the SHOT is
            # beam_rifle_fire (2.9 s), and Halo 3 plays both: mixed, permutation k with k
            'bm_fire': (['beam_rifle_fire', 'beam_rifle_first_person_fire'], 'sound\\sfx\\weapons\\sniper rifle\\fire', -12.4),
            'bm_dryfire': (['beam_rifle_misfire'], 'sound\\sfx\\weapons\\plasma rifle\\overheat', -19.5),
            'bm_ready': (['fp_beam_rifle\\fp_beam_ready'], 'sound\\sfx\\weapons\\weapon_anims\\sniper_ready', -21.6),
            'bm_melee': (['fp_beam_rifle\\fp_beam_melee1'], 'sound\\sfx\\weapons\\weapon_anims\\sniper_melee', -21.5),
            'bm_pose': (['fp_beam_rifle\\fp_beam_posing_var1'], 'sound\\sfx\\weapons\\weapon_anims\\sniper_posing', -19.1),
            'bm_zoom_in': (['beam_rifle_zoom_in'], 'sound\\sfx\\weapons\\sniper rifle\\sniper_2x_zoom', -28.9),
            'bm_zoom_out': (['beam_rifle_zoom_out'], 'sound\\sfx\\weapons\\sniper rifle\\sniper_10x_zoom', -29.2),
            'bm_drop': (['beam_rifle_drop'], 'sound\\sfx\\impulse\\weapon_drops\\plasma_impact', -18.7),
            # Halo 3's overheat = in 2.7 s + loop 2.9 s + out 1.2 s (6.85 s as one piece,
            # longer than the 3.0 s vent): 'in' on the FP overheating animation, 'out' on
            # o-h-exit (Halo 1's own overheat states); the loop left out
            'bm_overheat': ([OH + 'in'], 'sound\\sfx\\weapons\\plasma rifle\\overheat', -19.5),
            # TEST 1 (user): 'the venting is a bit too quiet' -> +6 dB
            'bm_overheat_out': ([OH + 'out'], 'sound\\sfx\\weapons\\plasma rifle\\overheat', -13.5),
        },
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only beam_rifle) on a COPY of the Halo 1 PLASMA
    # PISTOL: the role table is heat + battery with no magazine (the sniper would need its
    # magazine, HUD and readout replaced). The sniper still gives the damage table, the
    # bullet and the zoom screen effect. DEFAULT = HALO 3's OWN NUMBERS; the ratio values
    # are the balance rows (yardstick['balanced']). Template inspection (the BR's trap):
    # exports A heat / B primary charged / C illumination / D age; functions 0 age inverted
    # (A out), 1 heat (B out: the two heat flares), 2 illumination (C out: the muzzle
    # light), 3 primary charged (D out: the charged shot's flare + charging sound -- both
    # attachments dropped with trigger 1; function 3 stays, constant 0)
    'pickable': {
        'weapon': BM + 'beam rifle',
        'template': PP + 'plasma pistol',
        'world_model': BM + 'beam rifle',
        'fp_model': BM + 'fp\\fp',
        'fp_anims': BM + 'fp\\fp',
        'label': 'bm',
        'teach': ('bm', 'sr'),
        'keys': {'first-person melee': 4},          # H3 melee_strike_1 primary_keyframe 4
        'sounds': {'first-person ready': SND + 'bm_ready',
                   'first-person posing': SND + 'bm_pose',
                   'first-person melee': SND + 'bm_melee',
                   'first-person overheating': SND + 'bm_overheat',
                   'first-person o-h-exit': SND + 'bm_overheat_out'},
        # the plasma pistol's charged shot (trigger 1) and its two charge attachments
        # (`overcharge` flare, `charging` sound) do not exist on the beam rifle. TEST 1 (user):
        # a green glow off the muzzle, also while zoomed = the plasma pistol's two HEAT FLARES
        # (light + lens flare, B out): lights and flares draw at the hidden THIRD-PERSON
        # weapon (the Sentinel Beam's finding) and a Halo 1 lens flare has no first-person or
        # zoom switch; Halo 3's beam rifle has none (its one attachment is the overheat
        # loop) -> dropped too. Kept: the muzzle light (attachment 0, C out = illumination)
        'keep_triggers': 1,
        'drop_attachments': [1, 2, 3, 4],
        # own beam + damage (step 3): Halo 3's beam_rifle_beam = 1200 wu/s, range 500, 80
        # damage (the sniper's own speed, range and damage). Materials (user, step 4a): the
        # H1 sniper bullet's + Jackal shield 0.5, Sentinel 2.0. The LOOK: the sniper's trail
        # recoloured pink (Halo 3's is a pink-magenta beam), the plasma pistol bolt's impact
        # effects per material (plasma, not bullet sparks)
        'bullet': {'projectile': (SR + 'sniper bullet', BM + 'beam'),
                   'damage': (SR + 'sniper bullet', BM + 'beam'),
                   'dmg': 80.0, 'velocity': 1200.0, 'range': 500.0,
                   'fields': {'damage_modifiers.jackal_energy_shield': 0.5,
                              'damage_modifiers.sentinel': 2.0},
                   # TEST 2 (user): 'once shot it travels to the right' -- the H1 sniper's own
                   # behaviour: its trail points ride SMOKE point physics (cold / hot smoke
                   # cloud, lightweight particle) and drift with the level's wind; Halo 3's
                   # beam does not -> no point physics
                   'contrail': {'from': SR + 'sniper', 'out': BM + 'beam', 'rgb': PINK,
                                'no_physics': True},
                   'material_responses_from': PP + 'bolt'},
        # TAPPED, like Halo 3's (fire recovery 0.4 s = 2.5/s, one shot a pull); the plasma
        # pistol's 0.6 s charge (its overcharge) off. Heat 0.7 a shot, battery 0.05 (Halo 3
        # CAMPAIGN) = 20 shots
        'trigger': {'rounds_per_second': (2.5, 2.5), 'acceleration_time': 0.0,
                    'deceleration_time': 0.0, 'does_not_repeat_automatically': True,
                    'charging_time': 0.0, 'charge_hold_time': 0.0,
                    'heat_generated_per_round': 0.7, 'age_generated_per_round': 0.05,
                    # TEST 1 (user): 'the beam trail seems offset from the impact' -- the
                    # round left from the camera; it now starts at the FP muzzle (the
                    # `primary trigger` marker in the idle pose, camera space: forward,
                    # left, up wu -- fp_render), the Sentinel Beam's fix
                    'first_person_offset': (0.58, -0.0668, -0.0449)},
        # Halo 3: overheated at 1.0, back to firing at 0.1; Halo 1 has ONE loss. TEST 1 (user,
        # 0.3 vs 0.575 in one boot): 'A is too slow to be useful, B too fast -- played right it
        # never overheats; take the average' = 0.4375 (a 2.06 s vent)
        'heat': {'recovery_threshold': 0.1, 'overheated_threshold': 1.0, 'loss_per_second': 0.4375},
        # the template's overheat steam aims at its vent_* markers
        'overheated_effect': {'from': PP + 'effects\\overheated', 'out': BM + 'effects\\overheated',
                              'locations': {'vent_rear': 'overheat', 'vent_mid': 'overheat',
                                            'vent_front': 'overheat'}},
        # H3 error 0.5 / 0.5 (= the H1 sniper's): the plasma pistol's 0
        'error_deg': {'minimum_error': 0.0, 'error_angle': (0.5, 0.5)},
        # H3 aim assist, absolute; zoom = Halo 3's two levels 3.5x / 9.5x
        'aiming': {'autoaim_angle': 1.0, 'autoaim_range': 10.0,
                   'magnetism_angle': 4.0, 'magnetism_range': 14.0,
                   'zoom_levels': 2, 'zoom_ranges': (3.5, 9.5)},
        'sound_effects': {
            # the plasma pistol's flash, tinted pink, with Halo 3's fire sound
            'firing_effect': (PP + 'effects\\fire bolt', BM + 'effects\\fire beam',
                              {r'sound\sfx\weapons\plasma rifle\fire': SND + 'bm_fire'},
                              {'tint': (1.0,) + PINK})},
        # the muzzle light: the plasma pistol's (green) in pink
        'own_light': {'shape': PP + 'muzzle flash', 'look': PP + 'muzzle flash',
                      'out': BM + 'muzzle light', 'argb': (1.0,) + PINK},
        'attach_swap': {PP + 'muzzle flash': BM + 'muzzle light'},
        'fields': {
            # the empty / dead-battery click: the plasma pistol's is a SOUND reference
            'weap_attrs.triggers.0.firing_effects.0.empty_effect.filepath': SND + 'bm_dryfire',
            'weap_attrs.interface.zoom_in_sound.filepath': SND + 'bm_zoom_in',
            'weap_attrs.interface.zoom_out_sound.filepath': SND + 'bm_zoom_out',
            'item_attrs.collision_sound.filepath': SND + 'bm_drop',
            # Halo 3's beam rifle never misfires on a low battery (age misfire start /
            # chance 0 / 0); the plasma pistol template's 0.9 / 0.5 would
            'weap_attrs.age.misfire_start': 0.0,
            'weap_attrs.age.misfire_chance': 0.0,
            # ... so no misfire effect either (its sound was the plasma rifle's overheat: a
            # BORROW in port_sound_refs on the test copy, 2026-10-08)
            'weap_attrs.triggers.0.firing_effects.0.misfire_effect.filepath': '',
        },
        'melee': (PP + 'melee', BM + 'melee'),
        'melee_response': PP + 'melee_response',
        'messages': ('Picked up a beam rifle', 'Picked up %d rounds for beam rifle'),
        'icon': 'beam rifle',
        # the PLASMA PISTOL's HUD (heat + battery meters, `master plasma`) with Halo 3's beam
        # reticle (H3 hud_reticles #5; the headshot cross not reproduced) at the reserved 22.
        # ZOOM = Halo 3's scope (the standard): ui\chud\beam_rifle's FULLSCREEN set (`scope`,
        # scale 1.2; `scope_quarterscreen` 0.85 is split-screen, skipped by window state).
        # The plasma pistol's HUD has no screen effect: the sniper's (mask replaced).
        # User (2026-10-08): the static meter FRAME baked, the heat / battery fills (meter
        # shaders, garbage as a mask) and the four warning flashes (hidden until a warning)
        # dropped -- the Halo 1 HUD's own heat / battery meters show while zoomed.
        # `scope_mask_blur` (distortion and blur, mirrored, extend border) covers everything
        # outside the lens = Halo 1's outside blur: baked as blur x1 (the lens outside is ~90%
        # dark, so write()'s grey flood fill would find no vignette)
        'hud': {'donor': PP + 'plasma pistol', 'out': BM + 'beam rifle',
                'screen_effect_from': SR + 'sniper rifle',
                'scope': {'chud': r'ui\chud\beam_rifle', 'out': BM + 'bitmaps\\scope_mask',
                          # the Carbine's picked size and shape (80%, x squashed 0.8);
                          # the BR's 4/3 on the test variant. TEST 1 (user): A (this) looks
                          # good; the empty meter frames stay (a mask cannot fill them, and
                          # Halo 1 HUD meters have no zoom state)
                          'size': 1024, 'span': 828.0, 'aspect': (4 / 3.0) / 0.8, 'alpha': 'outside',
                          'per_widget': {'overheat_flash_scope': {'drop': True},
                                         'lowbatt_flash_scope': {'drop': True},
                                         'meter_heat': {'drop': True},
                                         'meter_batt': {'drop': True},
                                         'meter_lowbatt_flash_left': {'drop': True},
                                         'meter_overheat_flash_right': {'drop': True},
                                         'scope_mask_blur': {'blur': 1.0}}},
                'reticle': ('hud_reticles', 5, 'beam rifle'),
                'reticle_thicken': 1},
        'palette_levels': ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40'],
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py beam_rifle). DEFAULT = Halo
    # 3's own numbers in the tags; BALANCED = the SNIPER ratio rule (step 4a, user
    # 2026-10-08). Assembly Halo1 units: angles in degrees, velocity in wu per TICK.
    'catalog': {
        'entry': {
            'weapon': 'Beam Rifle', 'source': 'Halo 3', 'donor': 'Sniper Rifle', 'default_on': False,
            'desc': "Halo 3's Beam Rifle: its model, first-person animations, sounds, scope and "
                    "numbers. A Covenant marksman rifle on heat and battery: two quick shots "
                    "overheat it, 20 shots a battery, 3.5x / 9.5x zoom.",
            'balance_desc': "Measured against the Sniper Rifle, which both games have: 101 "
                            "damage per shot, up to 3.5 shots a second, Halo 1's 2x / 8x-style "
                            "zoom (1.75x / 8.4x), a longer reach and Halo 1-style aim assist; "
                            "heat and battery stay Halo 3's.",
            # step 9 (swap = ready + put-away, ONE multiplier): H1 sniper ready 29 fr x H3
            # beam 22 / H3 sniper 21 = 30.4 frames over the built 22 = x1.38; no reload
            'anims': {'swap': 1.38},
            'balance': [
                row('jpt!', BM + 'beam', 'Damage Lower Bound', 101.0, 80.0, 'Beam damage'),
                row('jpt!', BM + 'beam', 'Damage Upper Bound', 101.0, 80.0, 'Beam damage'),
                row('jpt!', BM + 'beam', 'Damage Upper Bound Max', 101.0, 80.0, 'Beam damage'),
                row('weap', BM + 'beam rifle', 'Rounds Per Second', 3.5, 2.5, 'More Shooting', block='Triggers'),
                row('weap', BM + 'beam rifle', 'Rounds Per Second Max', 3.5, 2.5, 'More Shooting', block='Triggers'),
                row('proj', BM + 'beam', 'Initial Velocity', 33.333, 40.0, 'Projectile'),
                row('proj', BM + 'beam', 'Final Velocity', 33.333, 40.0, 'Projectile'),
                row('proj', BM + 'beam', 'Maximum Range', 1000.0, 500.0, 'Projectile'),
                row('weap', BM + 'beam rifle', 'Magnification Range', 1.75, 3.5, 'Zoom'),
                row('weap', BM + 'beam rifle', 'Magnification Range Max', 8.44, 9.5, 'Zoom'),
                row('weap', BM + 'beam rifle', 'Autoaim Range', 35.0, 10.0, 'Autoaim'),
                row('weap', BM + 'beam rifle', 'Magnetism Angle', 2.0, 4.0, 'Magnetism'),
                row('weap', BM + 'beam rifle', 'Magnetism Range', 35.0, 14.0, 'Magnetism'),
            ]},
    },

    # step 4b (port_field_audit.py --port beam_rifle): the source pair (H3 beam rifle vs the
    # yardstick, H3 sniper) against the target pair (the H1 port vs the H1 sniper; the
    # template is the plasma pistol -- the full field diff covers it)
    'field_audit': {
        'source_kit': 'H3EK',
        'source': {'weapon': (H3 + r'\beam_rifle.weapon', r'objects\weapons\rifle\sniper_rifle\sniper_rifle.weapon'),
                   'projectile': (H3 + r'\projectiles\beam_rifle_beam.projectile',
                                  r'objects\weapons\rifle\sniper_rifle\projectiles\sniper_bullet.projectile'),
                   'damage_effect': (H3 + r'\damage_effects\beam_rifle_impact.damage_effect',
                                     r'objects\weapons\rifle\sniper_rifle\damage_effects\sniper_rifle_bullet.damage_effect')},
        'target': {'weapon': (BM + 'beam rifle.weapon', SR + 'sniper rifle.weapon'),
                   'projectile': (BM + 'beam.projectile', SR + 'sniper bullet.projectile'),
                   'damage_effect': (BM + 'beam.damage_effect', SR + 'sniper bullet.damage_effect')}},

    # the dry test: a30 (Covenant within seconds of the landing; Jackal shields), a battery
    # weapon spawns charged (rounds 0 / 0, as the Sentinel Beam)
    'test': {'level': 'a30', 'rounds': (0, 0), 'grunt': None, 'elite': None},
})
