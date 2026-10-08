r"""SMG (Halo 3, wave A1): PHASE-0 STUB -- reservations, yardstick candidates and the step-11
source. The port session fills in model / retarget / pickable / sounds / catalog / test
(see sentinel_beam.py for a complete config) and starts with step 4a: the yardstick is
picked WITH the user, then recorded in yardstick['pick'] / ['reason']."""
from ._common import B, H3_FP_GRAPHS, reserved, row

H3 = r'objects\weapons\rifle\smg'
SMG = 'weapons\\smg\\'
SND = 'sound\\weapons\\smg_port\\'

PORT = reserved(
    order=10, wave='A1', name='SMG', source='Halo 3',
    messages=(53, 54), icon=30, reticle=19, label='sm', teach_from='ar',
    sound_dir='sound\\weapons\\smg_port', weapon_dir='weapons\\smg',
    yardstick={
        # step 4a (user, 2026-10-07): h1_role_compare.py smg -- the AR ratio gives 150/s,
        # the Halo 1 AR's own per-second damage (H3 SMG and AR are both 75/s), and kills
        # like it; pistol ratio 175/s, plasma-rifle ratio 108/s with nothing to scale ammo
        'pick': 'Assault Rifle',
        'reason': 'user, step 4a 2026-10-07: same role and damage type (magazine full-auto '
                  'bullet); H1 value = H1 AR x H3 SMG / H3 AR. Values where that ratio is '
                  'degenerate (spread minimum, reserve) are decided separately',
        # DEFAULT = Halo 3's own numbers (PORTING "Balance"); these are the BALANCED rows
        # (step 4a, user 2026-10-07). H3: SMG / AR.
        'balanced': {
            'damage': 6.67,              # 10 x 5/7.5
            # 15 x 15/10. MEASURED (test 3): fires 15/s (112 rounds in 7.5 s) -- Halo 1 caps
            # this weapon at 15/s, so balanced = 6.67 x 15 = 100/s; user: ACCEPT 100/s
            'rounds_per_second': 22.5,
            'magazine': 112,             # 60 x 60/32 = 112.5
            'rounds_total_initial': 450,  # 240 x 180/96
            # DUAL-WIELD CARRY RULE (user): a port its source game let you dual wield gets
            # x1.5 on the carry ratio -- 600 x (240/384 = 0.625) x 1.5 = 562.5 (a short: 562)
            'rounds_total_maximum': 562,
            'reload_s': 2.5,             # 2.9 x 50/58 frames
            'error_min_deg': 1.83,       # 2 x 2.75/3.0 (the min's own ratio 1.25/0.1 -> 25)
            # the BARREL CLIMB approximated (user, test 3, option A): +1.6 deg in Halo 3 terms
            # (0.4 deg/shot x 4 shots = one 0.25 s correction window at 15/s) on the
            # full-bloom cone, through the ratio: (2.75 + 1.6) x 6.5/3.0 = 9.43
            'error_max_deg': 9.43,       # was 6.5 x 2.75/3.0 = 5.96 -- step 5b: widen to approximate
                                         # H3's barrel climb (0 -> 0.4 deg/shot, no H1 field)
            'velocity': 1620.0,          # 324 x 400/80 (user: keep)
            'aim': (6.0, 20.0, 14.4, 22.5),  # autoaim deg/wu, magnetism deg/wu
            'melee': 55.0},              # H3 shares strike_melee: x1 = the H1 AR's
        'measured': 'h1_role_compare.py smg',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\smg\\smg',
            'provisional': 'Assault Rifle',
            'alternatives': ['Pistol', 'Plasma Rifle'],
            'direct': None,
            'peers': ['Assault Rifle', 'Plasma Rifle', 'Needler'],
            'why': 'magazine full-auto bullet, a non-instant projectile in H3 like the H3 AR',
            'lacks': 'dual wield'}},
    # step 11: the source game's ai\generic entry (24 fields, verified 2026-10-07), laid
    # over the H1 AR's carriers -- the SMG's own label 'sm' has no carrier to find a base by
    # Armed WDM (user, 2026-10-08, Rule B -- ai_firing_profile.wdm_rule, measured on the
    # Carbine): 0.4 (the AR carriers) x AR 150 / SMG 75 = 0.80, balanced / 100 = 0.60
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\rifle\\smg\\smg',
                    'donor_weapon': 'weapons\\assault rifle\\assault rifle',
                    'wdm_rule': {'base': 0.4, 'yardstick_dps': 150.0, 'port_dps': 75.0,
                                 'balanced_port_dps': 100.0}},
)

PORT.update({
    # 2026-10-07: tested on a30 over 4 boots (dry default, dry balanced, Armed Grunts +
    # Elites) -- everything confirmed by the user; the ten-map rebuild waits for the go
    'status': 'done',
    # geometry + look (h1_h3_weapon_model.py): both H3 shaders sample the same `smg` base
    # map; only the metal one self-illuminates (smg_illum)
    'model': {
        'dir': r'weapons\smg',
        'world': H3 + r'\smg.render_model',
        'fp': H3 + r'\fp_smg\fp_smg.render_model',
        'world_name': 'smg',
        'shaders': {'smg_metal': (H3 + r'\bitmaps\smg.bitmap', H3 + r'\bitmaps\smg_illum.bitmap'),
                    'smg_rubber': (H3 + r'\bitmaps\smg.bitmap', None)},
        'template': r'weapons\assault rifle\fp\shaders\gun',
    },

    # FP animations (h1_fp_retarget.py): Halo 1's FP model IS Halo 3's (same space)
    'retarget': {
        'graph': H3_FP_GRAPHS + r'\rifle\fp_smg\fp_smg.model_animation_graph',
        'render_model': H3 + r'\fp_smg\fp_smg.render_model',
        'nodes': {n: 'frame ' + n.replace('_', ' ') for n in
                  ('gun', 'charging_handle', 'magazine', 'stock')},
        'h1_dir': r'weapons\smg\fp',
        'h1_model': r'weapons\smg\fp\fp',
        'align': 'same_space',
        # START from the Sentinel Beam's in-game result (8 tests): if Halo 3's FP rig sits
        # too close in Halo 1 for every H3 weapon (view / FOV), the beam's correction fits
        # here too -- an OBSERVATION from one port, this test checks it
        # test 1 (2026-10-07, a30): user moves it 'forward 1.5 and up 2 units' (1 unit =
        # 0.01 wu, the beam's) to check whether the beam's 'see into the arms' is general
        # test 2: 'still looking good' -> test 3: NO offset at all (Halo 3's own placement)
        # test 3: 'nothing I shouldn't see, but test 2 looked better' -> back to test 2's.
        # So the beam's 'see into the arms' was the BEAM's, not general (observation)
        'view_offset': (-0.0375 + 0.015, 0.0, -0.0425 + 0.02),
        # Halo 1's AR names its auto-fire `firing` and has no reload-empty; the pistol and
        # the Sentinel Beam (30/s auto, tested) use the per-shot `fire-1`, which matches
        # H3's 5-frame fire_1. Halo 3 SMG frames: idle 89, posing 129, ready 19, put_away 5,
        # fire_1 5, melee 26 (primary_keyframe 3), reload empty/full 50 each, grenade 41
        'anims': {
            'first_person:idle': 'first-person idle',
            'first_person:posing:var0': 'first-person posing',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:fire_1': 'first-person fire-1',
            'first_person:melee_strike_1': 'first-person melee',
            'first_person:moving': 'first-person moving',
            'first_person:overlays': 'first-person overlays',
            'first_person:reload_empty': 'first-person reload-empty',
            'first_person:reload_full': 'first-person reload-full',
            'first_person:throw_grenade': 'first-person throw-grenade',
        },
    },

    # Halo 3's own sounds (h1_port_sounds.py smg). Levels = the active RMS of the stock
    # Halo 1 sound each stands in for, measured from MCC's sounds_adpcm.fsb (2026-10-07):
    # AR fire -13.1/-12.2/-13.0/-13.8 (4 perms, 0.6-0.8 s), dryfire -17.6, ar_reload
    # -20.9, ar_melee -16.7/-15.6, AR weapon ready -13.1, pistol_posing -26.5.
    # Every single-wield H3 FP cue is ONE sound at frame 0 (both reloads: smg_reload).
    # THE FIRE: Halo 3 fires the SMG through a loop (smg_loop in/loop/out; the loop is
    # 15.2 shots/s, a 66 ms period); Halo 1 plays a whole shot per round. `shots`: the
    # loop's first 4 periods, each followed by Halo 3's release tail (`out`, onset 0.02 s)
    'sounds': {
        'catalog': 'SMG',
        'dir': B.join(['sound', 'weapons', 'smg_port']),
        'h3_dir': 'data\\sound\\weapons\\smg\\',
        'sounds': {
            'smg_fire': (['smg_loop\\smg_loop\\loop'], 'sound\\sfx\\weapons\\assault rifle\\fire', -13.0),
            'smg_dryfire': (['dryfire'], 'sound\\sfx\\weapons\\assault rifle\\dryfire', -17.6),
            'smg_reload': (['smg_fp\\smg_reload'], 'sound\\sfx\\weapons\\weapon_anims\\ar_reload', -20.9),
            # the BALANCED reload's sound (the patcher retimes the reload x1.5 and then swaps
            # this in: catalog anim_sounds) -- every click moved to onset x 1.5, unpitched
            'smg_reload_balanced': (['smg_fp\\smg_reload'], 'sound\\sfx\\weapons\\weapon_anims\\ar_reload', -20.9),
            'smg_ready': (['smg_fp\\smg_ready'], 'sound\\sfx\\weapons\\assault rifle\\weapon ready', -13.1),
            'smg_melee': (['smg_fp\\smg_melee_strike'], 'sound\\sfx\\weapons\\weapon_anims\\ar_melee', -16.2),
            'smg_pose': (['smg_fp\\smg_posing0'], 'sound\\sfx\\weapons\\weapon_anims\\pistol_posing', -26.5),
            # sound close-out (2026-10-08, port_sound_refs BORROW): Halo 3's own drop and
            # ammo pickup over the AR's (assault_impact -20.7, ar_ammo -24.9, measured)
            'smg_drop': (['smg_drop'], 'sound\\sfx\\impulse\\weapon_drops\\assault_impact', -20.7),
            'smg_ammo': (['smg_ammo'], 'sound\\sfx\\weapons\\weapon_pickup_ammo\\ar_ammo', -24.9),
        },
        'stretch': {'smg_reload_balanced': 1.5},
        'shots': {'smg_fire': {'period': 0.066, 'count': 4, 'tail': 'smg_loop\\smg_loop\\out',
                               'tail_onset': 0.02, 'tail_len': 0.7}},
    },

    # BORROWED sounds kept ON PURPOSE (user, 2026-10-08 sound close-out): Halo 3's SMG has
    # no flashlight sound and no casing eject, so the AR's flashlight and the pistol's eject
    # (in the copied `fire bullet`) stay. port_sound_refs.py prints these as KEEP
    'sound_keeps': {r'sound\sfx\weapons\assault rifle\flashlight': 'Halo 3 SMG has no flashlight sound',
                    r'sound\sfx\weapons\pistol\eject': 'Halo 3 SMG has no casing eject'},

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only smg) on a COPY of the Halo 1 Assault Rifle.
    # DEFAULT = HALO 3's OWN NUMBERS (PORTING "Balance"); the ratio values are the balance
    # rows (yardstick['balanced']). Where Halo 3's SMG and AR AGREE the field keeps the H1
    # AR's value (step 4b: instantaneous acceleration 0.125 both -> AR's 0; range 40 both;
    # the shared strike_melee -> the AR's melee, 55, in an own copy).
    # STEP 6, the ammo pickup: the template's magazine names `powerups\assault rifle ammo`,
    # so Halo 1's AR ammo tops the SMG up (a port inherits the donor's pickup item).
    'pickable': {
        'weapon': SMG + 'smg',
        'template': r'weapons\assault rifle\assault rifle',
        'world_model': SMG + 'smg',
        'fp_model': SMG + 'fp\\fp',
        'fp_anims': SMG + 'fp\\fp',
        'label': 'sm',
        'teach': ('sm', 'ar'),
        'keys': {'first-person melee': 3},          # H3 melee_strike_1 primary_keyframe 3
        'sounds': {'first-person ready': SND + 'smg_ready',
                   'first-person posing': SND + 'smg_pose',
                   'first-person melee': SND + 'smg_melee',
                   'first-person reload-empty': SND + 'smg_reload',
                   'first-person reload-full': SND + 'smg_reload'},
        # own bullet + damage (step 3): H3 smg_bullet 5 damage, 400 wu/s (AR 7.5, 80)
        'bullet': {'projectile': (r'weapons\assault rifle\bullet', SMG + 'bullet'),
                   'damage': (r'weapons\assault rifle\bullet', SMG + 'bullet'),
                   'dmg': 5.0, 'velocity': 400.0},
        # H3: 15/s (= the H1 AR), rate ramp 1.0 / 0.2 s (H3 AR 0: no ratio, the source value).
        # Error ramp: NO card covers it, so step 4b's ratio goes in outright -- H1 AR 0.6 x
        # 1.0/0.5 = 1.2 s to bloom, 1.0 x 0.2/0.5 = 0.4 s to settle (port_field_audit)
        'trigger': {'rounds_per_second': (15.0, 15.0), 'acceleration_time': 1.0,
                    'deceleration_time': 0.2, 'error_acceleration_time': 1.2,
                    'error_deceleration_time': 0.4},
        # step 4b, the rest of list 2 (ratio vs H3 AR, onto the H1 AR): bounding radius
        # 0.6 x 0.11/0.175, acceleration scale 2 x 1.9/1, active camo ding 0.25 x 0.18/0.2
        'fields': {'obje_attrs.bounding_radius': 0.6 * 0.11 / 0.175,
                   'obje_attrs.acceleration_scale': 2.0 * 1.9 / 1.0,
                   'weap_attrs.interface.active_camo_ding': 0.25 * 0.18 / 0.2,
                   # STEP 6, how much one pickup gives: Halo 3's SMG magazine item 120 (the
                   # H3 AR has none: no ratio) -- the source value; the H1 AR's gives 240
                   'weap_attrs.magazines.0.magazine_items.0.rounds': 120,
                   # sound close-out (2026-10-08): its own drop and ammo pickup
                   'weap_attrs.interface.pickup_sound.filepath': SND + 'smg_ammo',
                   'item_attrs.collision_sound.filepath': SND + 'smg_drop'},
        # H3 single-wield: minimum error 0.25, error angle 1.25 -> 2.75 (H1 AR 0, 2 -> 6.5)
        # + the BARREL CLIMB Halo 1 lacks (H3: 0 -> 0.4 deg/shot, 'very late', arriving over
        # ~1.1 s -- Halo 1's error ramp here is 1.2 s): +1.6 deg on the full-bloom cone, the
        # drift of 4 shots between a player's corrections (user, test 3: 2.75 -> 4.35)
        'error_deg': {'minimum_error': 0.25, 'error_angle': (1.25, 2.75 + 1.6)},
        # H3: 60 loaded, 180 at pickup, 240 most. Reload time: H3 SMG 2.0, H3 AR 0 (its
        # animation decides) -> no ratio, the source value (step 4b). 2.0 over the 1.67 s
        # animation is the H1 AR's own shape (3.4 over 2.9 s)
        'magazine': {'rounds_loaded_maximum': 60, 'rounds_reloaded': 60,
                     'rounds_total_initial': 180, 'rounds_total_maximum': 240,
                     'reload_time': 2.0},
        # H3 aim assist, absolute (the beam's precedent; balanced = the ratio rule)
        'aiming': {'autoaim_angle': 5.0, 'autoaim_range': 12.0,
                   'magnetism_angle': 12.0, 'magnetism_range': 18.0},
        'sound_effects': {
            # test 1: 'the AR's flash -- move it up and forward, shrink it'. Halo 3's SMG flash
            # is on-axis only (round + long + glow, no muzzle brake): the AR's off-axis ring
            # sprites dropped, the rest x0.6, 1 unit forward and 0.5 up (eyeballed, test 2)
            'firing_effect': (r'weapons\assault rifle\effects\fire bullet', SMG + 'effects\\fire bullet',
                              {r'sound\sfx\weapons\assault rifle\fire': SND + 'smg_fire'},
                              # test 2: 'move 0.5 units up, revert the size'
                              {'match': 'flash', 'drop_off_axis': 0.012, 'scale': 1.0,
                               'shift': (0.01, 0.0, 0.01)}),
            'empty_effect': (r'weapons\assault rifle\effects\empty', SMG + 'effects\\empty',
                             {r'sound\sfx\weapons\assault rifle\dryfire': SND + 'smg_dryfire'})},
        'melee': (r'weapons\assault rifle\melee', SMG + 'melee'),
        'melee_response': r'weapons\assault rifle\melee_response',
        'messages': ('Picked up an SMG', 'Picked up %d rounds for SMG'),
        'icon': 'smg',
        'extra_sounds': [SND + 'smg_reload_balanced'],      # unused until the balanced retime
        # the AR's HUD with Halo 3's SMG reticle (H3 hud_reticles #3) at the reserved 19 and
        # a magazine meter drawn for 60 (default) and 112 (balanced)
        'hud': {'donor': r'weapons\assault rifle\assault rifle', 'out': SMG + 'smg',
                'reticle': ('hud_reticles', 3, 'smg'),
                # test 1: 'pixels missing' -- the strokes grown 1 px a side; the ring's
                # diagonal gaps are Halo 3's design and stay (user)
                'reticle_thicken': 1,
                'ammo_meter': {'sizes': (60, 112), 'base': SMG + 'bitmaps\\smg_ammo'}},
        'palette_levels': ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40'],
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py smg). DEFAULT = Halo 3's own
    # numbers in the tags; BALANCED = the AR ratio rule (yardstick, step 4a, user
    # 2026-10-07). Assembly Halo1 units: angles in degrees, velocity in wu per TICK.
    'catalog': {
        'entry': {
            'weapon': 'SMG', 'source': 'Halo 3', 'donor': 'Assault Rifle', 'default_on': False,
            'desc': "Halo 3's SMG: its model, first-person animations, sounds and numbers. "
                    "A 60-round automatic; Assault Rifle ammo tops it up.",
            'balance_desc': "Measured against the Assault Rifle, which both games have: 6.67 "
                            "damage per round (Halo 1 fires it at 15 rounds/s), a 112 "
                            "magazine, 450 at pickup / 562 most, a 2.5 s reload, a wider "
                            "spray in long bursts, a faster bullet and Halo 1-style aim assist.",
            # step 9: the balanced reload, 2.9 x 50/58 = 2.5 s, against the BUILT 50 frames
            # swap (ready + put-away, ONE multiplier in the patcher): ready 29 x 19/20 =
            # 27.55 frames over the built 19 = x1.45 (put-away's own would be 11 x 5/5 / 5 =
            # x2.2; the SAW also took the ready's)
            'anims': {'reload': 1.5, 'swap': 1.45},
            # the patcher points the retimed reloads at the stretched sound
            # (port_sounds.retimed_anim_sound; the SAW's recipe)
            'anim_sounds': {'reload': {'mult': 1.5, 'from': SND + 'smg_reload',
                                       'to': SND + 'smg_reload_balanced'}},
            'balance': [
                row('jpt!', SMG + 'bullet', 'Damage Lower Bound', 6.67, 5.0, 'Bullet Damage'),
                row('jpt!', SMG + 'bullet', 'Damage Upper Bound', 6.67, 5.0, 'Bullet Damage'),
                row('jpt!', SMG + 'bullet', 'Damage Upper Bound Max', 6.67, 5.0, 'Bullet Damage'),
                row('weap', SMG + 'smg', 'Rounds Per Second', 22.5, 15.0, 'More Shooting', block='Triggers'),
                row('weap', SMG + 'smg', 'Rounds Per Second Max', 22.5, 15.0, 'More Shooting', block='Triggers'),
                row('weap', SMG + 'smg', 'Rounds Loaded Maximum', 112.0, 60.0, 'Magazine', block='Magazines'),
                row('weap', SMG + 'smg', 'Rounds Reloaded', 112.0, 60.0, 'Magazine', block='Magazines'),
                row('weap', SMG + 'smg', 'Rounds Total Initial', 450.0, 180.0, 'Magazine', block='Magazines'),
                # the DUAL-WIELD CARRY RULE: 600 x 240/384 x 1.5 = 562.5 (a short)
                row('weap', SMG + 'smg', 'Rounds Total Maximum', 562.0, 240.0, 'Magazine', block='Magazines'),
                # STEP 6 balanced (user, test 2): Halo 3's own pickup : initial ratio (120 /
                # 180) on the balanced initial 450 = 300. (Halo 1's ratio, 240/240 x 450 =
                # 450, refilled nearly the whole 562 carry: rejected.) Default: Halo 3's 120
                row('weap', SMG + 'smg', 'Rounds', 300, 120, 'Ammo pickup', block='Magazines/Magazines'),
                # the minimum's own ratio is degenerate (H3 AR 0.1): the maximum's 2.75/3.0
                row('weap', SMG + 'smg', 'Minimum Error', 0.0, 0.25, 'Error Angle', block='Triggers'),
                row('weap', SMG + 'smg', 'Error Angle', 1.83, 1.25, 'Error Angle', block='Triggers'),
                # with the barrel-climb approximation: (2.75 + 1.6) x 6.5/3.0 (user, option A)
                row('weap', SMG + 'smg', 'Error Angle Max', 9.43, 4.35, 'Error Angle', block='Triggers'),
                row('proj', SMG + 'bullet', 'Initial Velocity', 54.0, 400.0 / 30, 'Projectile'),
                row('proj', SMG + 'bullet', 'Final Velocity', 54.0, 400.0 / 30, 'Projectile'),
                row('weap', SMG + 'smg', 'Autoaim Angle', 6.0, 5.0, 'Autoaim'),
                row('weap', SMG + 'smg', 'Autoaim Range', 20.0, 12.0, 'Autoaim'),
                row('weap', SMG + 'smg', 'Magnetism Angle', 14.4, 12.0, 'Magnetism'),
                row('weap', SMG + 'smg', 'Magnetism Range', 22.5, 18.0, 'Magnetism'),
                # the 112 magazine's meter: smg_ammo sequence 1 (ammo_meter.py 60 112),
                # one tick per round at step 2 (bias stays 1: one round per tick)
                dict(row('wphi', SMG + 'smg', 'Sequence Index', 1, 0, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', SMG + 'smg', 'Alpha Multiplier', 2, 4, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', SMG + 'smg', 'Sequence Index', 1, 0, 'Ammo display', block='Static Elements'), index=0),
                dict(row('wphi', SMG + 'smg', 'Loaded Ammo Cutoff', 19, 10, 'Ammo display'), index=0),
            ]},
    },

    # step 4b (port_field_audit.py --port smg): the source pair (H3 SMG vs the yardstick,
    # H3 AR) against the target pair (the H1 port vs its donor, the H1 AR)
    'field_audit': {
        'source_kit': 'H3EK',
        'source': {'weapon': (H3 + r'\smg.weapon', r'objects\weapons\rifle\assault_rifle\assault_rifle.weapon'),
                   'projectile': (H3 + r'\projectiles\smg_bullet.projectile',
                                  r'objects\weapons\rifle\assault_rifle\projectiles\assault_rifle_bullet.projectile'),
                   'damage_effect': (H3 + r'\damage_effects\smg_bullet.damage_effect',
                                     r'objects\weapons\rifle\assault_rifle\damage_effects\assault_rifle_bullet.damage_effect')},
        'target': {'weapon': (SMG + 'smg.weapon', r'weapons\assault rifle\assault rifle.weapon'),
                   'projectile': (SMG + 'bullet.projectile', r'weapons\assault rifle\bullet.projectile'),
                   'damage_effect': (SMG + 'bullet.damage_effect', r'weapons\assault rifle\bullet.damage_effect')}},

    # the dry test: a30 (Covenant within seconds of the landing), the SMG as the primary
    # with Halo 3's own loadout (60 loaded, 180 in all)
    'test': {'level': 'a30', 'rounds': (60, 180), 'grunt': None, 'elite': None},
})
