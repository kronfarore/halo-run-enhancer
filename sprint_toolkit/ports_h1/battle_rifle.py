r"""Battle Rifle (Halo 3, wave A2): a MAGAZINE port on a copy of the Halo 1 PISTOL (the
yardstick, step 4a). smg.py is the shape it copies; what is new here is the 3-round BURST
(Halo 1 has no burst trigger: the charge-and-spew approximation, option B) and the zoom."""
from ._common import B, H3_FP_GRAPHS, reserved, row

H3 = r'objects\weapons\rifle\battle_rifle'
BR = 'weapons\\battle rifle\\'
SND = 'sound\\weapons\\battle_rifle_port\\'
PISTOL = 'weapons\\pistol\\'

PORT = reserved(
    order=11, wave='A2', name='Battle Rifle', source='Halo 3',
    messages=(55, 56), icon=31, reticle=20, label='br', teach_from='ar',
    sound_dir='sound\\weapons\\battle_rifle_port', weapon_dir='weapons\\battle rifle',
    yardstick={
        # step 4a (user, 2026-10-07): h1_role_compare.py battle_rifle -- the pistol ratio is the
        # only candidate whose every value scales (AR: pickup 270 over a 225 maximum, spread
        # 3.0 -> 1.08 inverted; sniper: Flood combat forms take 33 s, the sniper bullet's
        # materials). Pistol ratio: 102/s against the H1 pistol's 88 (Halo 3: BR 44, magnum 38)
        'pick': 'Pistol',
        'reason': 'user, step 4a 2026-10-07: the magnum\'s role (semi-automatic precision, '
                  'mid range, 2x zoom = the H1 pistol\'s own); H1 value = H1 pistol x H3 BR / '
                  'H3 magnum. Per round and per burst CYCLE; the burst\'s shape (3 rounds, '
                  '15/s) has no yardstick and stays Halo 3\'s',
        # DEFAULT = Halo 3's own numbers (PORTING "Balance"); these are the BALANCED rows.
        # H3: BR / magnum. Burst cycle H3 BR 2/15 + 0.28 = 0.413 s (ASSUMED: the recovery
        # replaces the third interval), magnum 0.4 s
        'balanced': {
            'damage': 10.0,              # 25 x 6/15
            'burst_cycle_s': 0.295,      # 3.5/s x (2.42 / 2.5) = 3.39 bursts/s
            'magazine': 54,              # 12 x 36/8
            'rounds_total_initial': 202,  # 60 x 108/32 = 202.5
            'rounds_total_maximum': 360,  # 120 x 144/48 (not dual-wieldable: no carry rule)
            'ammo_pickup': 135,          # Halo 3's own 72 : 108 on the balanced 202 (SMG rule)
            'reload_s': 2.59,            # 67 fr x 58/50
            'error_deg': (0.06, 2.0),    # 0.2 x 0.15/0.5, 2.0 x 0.5/0.5; minimum 0 (H3 BR 0)
            'velocity': 300.0,           # 300 x 180/180
            'range': 60.0,               # 40 x 60/40
            'aim': (4.5, 34.0, 6.0, 31.5),  # 3 x 3/2, 30 x 17/15; 6 x 6/6, 30 x 21/20
            'zoom': 2.0,                 # magnum has none: Halo 3's own 2x (= the H1 pistol's)
            'melee': 55.0},              # H3 shares strike_melee: x1 = the H1 pistol's
        'measured': 'h1_role_compare.py battle_rifle',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\battle_rifle\\battle_rifle',
            'provisional': 'Pistol',
            'alternatives': ['Assault Rifle', 'Sniper Rifle'],
            'direct': None,
            'peers': ['Pistol', 'Assault Rifle', 'Sniper Rifle'],
            'why': "magazine, 2x scope, instant bullet: the H1 magnum's precision mid-range role",
            'lacks': '3-round burst'}},
    # step 11: the source game's ai\generic entry, laid over a base -- 'br' has no carrier
    # (smg.py's lesson): the pistol is the yardstick, but NO Halo 1 enemy carries it; the AR
    # has carriers (Marines, Flood combat Elites), as for the SMG
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\rifle\\battle_rifle\\battle_rifle',
                    'donor_weapon': 'weapons\\assault rifle\\assault rifle'},
)

PORT.update({
    'status': 'building',
    # geometry + look (h1_h3_weapon_model.py). Halo 3's materials: metal (base + illum),
    # rubber, lens, and the AMMO COUNTER digits `ones` / `tens` (numbers_plate; Halo 3
    # scrolls them by the ammo function -- here a static plate: NOT reproduced yet)
    'model': {
        'dir': r'weapons\battle rifle',
        'world': H3 + r'\battle_rifle.render_model',
        'fp': H3 + r'\fp_battle_rifle\fp_battle_rifle.render_model',
        'world_name': 'battle rifle',
        'shaders': {'battle_rifle_metal': (H3 + r'\bitmaps\battle_rifle.bitmap', H3 + r'\bitmaps\battle_rifle_illum.bitmap'),
                    'battle_rifle_rubber': (H3 + r'\bitmaps\battle_rifle.bitmap', None),
                    'battle_rifle_lens': (H3 + r'\bitmaps\battle_rifle.bitmap', None),
                    # the plate is ONE '0' glyph (32 px): a glowing static '00' for now
                    'ones': (H3 + r'\bitmaps\numbers_plate.bitmap', H3 + r'\bitmaps\numbers_plate.bitmap'),
                    'tens': (H3 + r'\bitmaps\numbers_plate.bitmap', H3 + r'\bitmaps\numbers_plate.bitmap')},
        'template': r'weapons\assault rifle\fp\shaders\gun',
        # THE AMMO COUNTER (user, test 1: 'see if we can make it work'): Halo 1's own numeric
        # shader, as the AR's display -- the H3 digit quads each map one glyph (u 0.16-0.84,
        # v 0-1), so the AR's 10-digit sequence fills them. Place 0 / 1 = the AR's two
        # permutations (which is ones is a GUESS: swap if the digits read reversed). Limit =
        # the magazine (the AR: 60); the weapon exports primary_ammunition on B as the AR does
        'numeric': {'from': r'weapons\assault rifle\fp\shaders\numbers', 'limit': 36,
                    'places': {'ones': 0, 'tens': 1}},
    },

    # FP animations (h1_fp_retarget.py). Halo 3 BR frames: ready 19, put_away 4, fire_1 6,
    # melee 30 (primary_keyframe 4), reload empty/full 58 each. NOT dual-wieldable: one
    # resource group expected (checked with --list against the graph's frame counts)
    'retarget': {
        'graph': H3_FP_GRAPHS + r'\rifle\fp_battle_rifle\fp_battle_rifle.model_animation_graph',
        'render_model': H3 + r'\fp_battle_rifle\fp_battle_rifle.render_model',
        'nodes': {n: 'frame ' + n for n in ('gun', 'magazine', 'ophandle', 'safety')},
        'h1_dir': r'weapons\battle rifle\fp',
        'h1_model': r'weapons\battle rifle\fp\fp',
        'align': 'same_space',
        # the SMG's tested placement (user's pick, H1_PORT_PLAN "Pilot A1"), tuned per weapon;
        # test 1 (2026-10-07, a30): 'move the FP position up 2 units' (1 unit = 0.01 wu);
        # test 2: 'back down a unit'
        'view_offset': (-0.0225, 0.0, -0.0225 + 0.01),
        # the H1 pistol's own names (per-shot `fire-1`, both reloads). The BR graph has NO
        # plain fire_1 / posing:var0: fire_1:var1..3 (6/6/5 fr, one per burst round in Halo
        # 3) and posing var1 / var2 (60 / 90 fr) -- var1 of each (--list, 2026-10-07)
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

    # Halo 3's own sounds (h1_port_sounds.py battle_rifle). Levels = the active RMS of the
    # stock Halo 1 PISTOL sound each stands in for (h1_stock_sound_levels.py, 2026-10-07):
    # fire -12.8, dryfire -15.3, pistol_reload -19.0, pistol_ready -15.2, pistol_melee
    # -19.8, pistol_posing -26.5, the pistol's zoom (sniper_2x_zoom) -28.9 / (10x) -29.2.
    # THE FIRE: Halo 3 plays ONE sound per burst (fire_burst_h3, 8 perms, 2.4-3.8 s, the
    # three shots fused -- no separable onsets); Halo 1 plays one per round. `shots`: round k
    # = the burst's k-th 1/15 s slice, then the burst's own tail from 0.2 s on, so the
    # three rounds of a spew burst put the burst sound back together (tails overlap: judge)
    'sounds': {
        'catalog': 'Battle Rifle',
        'dir': B.join(['sound', 'weapons', 'battle_rifle_port']),
        'h3_dir': 'data\\sound\\weapons\\battle_rifle\\',
        'sounds': {
            'br_fire': (['fire_burst_h3'], 'sound\\sfx\\weapons\\pistol\\fire', -12.8),
            'br_dryfire': (['dryfire'], 'sound\\sfx\\weapons\\pistol\\dryfire', -15.3),
            'br_reload_empty': (['battle_rifle_fp\\br_reload_empty'], 'sound\\sfx\\weapons\\weapon_anims\\pistol_reload', -19.0),
            'br_reload_full': (['battle_rifle_fp\\br_reload_full'], 'sound\\sfx\\weapons\\weapon_anims\\pistol_reload', -19.0),
            'br_ready': (['battle_rifle_fp\\br_ready'], 'sound\\sfx\\weapons\\weapon_anims\\pistol_ready', -15.2),
            'br_melee': (['battle_rifle_fp\\br_melee1'], 'sound\\sfx\\weapons\\weapon_anims\\pistol_melee', -19.8),
            'br_pose': (['battle_rifle_fp\\battle_rifle_pose_var1'], 'sound\\sfx\\weapons\\weapon_anims\\pistol_posing', -26.5),
            'br_zoom_in': (['battle_rifle_zoom_in'], 'sound\\sfx\\weapons\\sniper rifle\\sniper_2x_zoom', -28.9),
            'br_zoom_out': (['battle_rifle_zoom_out'], 'sound\\sfx\\weapons\\sniper rifle\\sniper_10x_zoom', -29.2),
            # the BALANCED reloads' sounds (the patcher retimes both reloads x1.34 and then
            # swaps these in: catalog anim_sounds, a LIST -- empty and full differ in Halo 3)
            'br_reload_empty_balanced': (['battle_rifle_fp\\br_reload_empty'], 'sound\\sfx\\weapons\\weapon_anims\\pistol_reload', -19.0),
            'br_reload_full_balanced': (['battle_rifle_fp\\br_reload_full'], 'sound\\sfx\\weapons\\weapon_anims\\pistol_reload', -19.0),
        },
        'stretch': {'br_reload_empty_balanced': 1.34, 'br_reload_full_balanced': 1.34},
        'shots': {'br_fire': {'period': 1 / 15.0, 'count': 3, 'tail': 'fire_burst_h3',
                              'tail_onset': 0.2 - 1 / 15.0, 'tail_len': 1.2}},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only battle_rifle) on a COPY of the Halo 1 PISTOL
    # (the yardstick: its zoom, magazine HUD and bullet materials). DEFAULT = HALO 3's OWN
    # NUMBERS; the ratio values are the balance rows (yardstick['balanced']).
    'pickable': {
        'weapon': BR + 'battle rifle',
        'template': PISTOL + 'pistol',
        'world_model': BR + 'battle rifle',
        'fp_model': BR + 'fp\\fp',
        'fp_anims': BR + 'fp\\fp',
        'label': 'br',
        'teach': ('br', 'ar'),
        'keys': {'first-person melee': 4},          # H3 melee_strike_1 primary_keyframe 4
        'sounds': {'first-person ready': SND + 'br_ready',
                   'first-person posing': SND + 'br_pose',
                   'first-person melee': SND + 'br_melee',
                   'first-person reload-empty': SND + 'br_reload_empty',
                   'first-person reload-full': SND + 'br_reload_full'},
        # own bullet + damage (step 3): H3 battle_rifle_bullet 6 damage, 180 wu/s, range 60
        # (magnum 15, 180, 40)
        'bullet': {'projectile': (PISTOL + 'bullet', BR + 'bullet'),
                   'damage': (PISTOL + 'bullet', BR + 'bullet'),
                   'dmg': 6.0, 'velocity': 180.0, 'range': 60.0,
                   # step 4b (port_field_audit list 2): screen flash 0.4 x 0.5/0.4 -- Halo 3
                   # has a shielded (0.5) and an unshielded (0.75) response, Halo 1 one: the
                   # SHIELDED one (the player is shielded). Wobble period (0 x ...) NOT written:
                   # Halo 1's wobble function here is 'one' (constant), the period does nothing
                   'fields': {'screen_flash.duration': 0.5}},
        # THE BURST, option B (user, 2026-10-07): Halo 1's charge-and-spew -- the kit's own
        # precedent is digsite\weapons\smg's second trigger (charge 1 tick, overcharged
        # action discharge, spew 0.2 s at 15/s = 3 rounds 2 ticks apart, Halo 3's spacing
        # exactly).
        # TEST 1 MEASURED (user, a30): spew 0.2 s fires FIVE rounds a burst; held, the bursts
        # repeat back to back -- 36 rounds in 2.18 s = 16.5/s, i.e. a 5-round burst every 9
        # ticks = 1 charge tick + 4 gaps of 2 ticks (no recovery at all); faster than Halo 3,
        # 'a small delay' felt. So rounds = 1 + spew ticks / 2 + 1 (6 ticks -> 5) and the
        # cycle = charge + 2 x (rounds - 1) ticks (OBSERVATIONS from this port).
        # TEST 2 (two variants in one boot, h1_port_test_map --secondary): B1 = spew 0.1 s +
        # the CHARGE (0.28 s) as Halo 3's recovery; B2 = charge 1 tick +
        # does_not_repeat_automatically (one burst a pull). USER PICKED B2 and tuned it
        # himself in game: 10 rounds/s, spew 0.15 s = EXACTLY 3 rounds, 'a similar feeling
        # to the original'. So rounds 3 ticks apart (Halo 3: 2 -- the spacing is the user's
        # feel call), a burst per trigger pull, NO recovery: tapping is limited by the
        # player only (Halo 3: 0.28 s) -- not reproduced, and so no burst-cycle balance row
        'trigger': {'rounds_per_second': (10.0, 10.0), 'acceleration_time': 0.0,
                    'deceleration_time': 0.0,
                    'charging_time': 1 / 30.0, 'overcharged_action': 'discharge',
                    'spew_time': 0.15, 'does_not_repeat_automatically': True,
                    # H3 bloom ramp 0.2 / 0.1 (magnum 0 / 0: no ratio, the source value)
                    'error_acceleration_time': 0.2, 'error_deceleration_time': 0.1},
        'fields': {
            # step 4b, list 2 (ratio vs the H3 magnum, onto the H1 pistol): bounding radius
            # 0.1 x 0.2/0.08, acceleration scale 2 x 1/1.25, active camo ding 0.65 x 0.25/0.4
            'obje_attrs.bounding_radius': 0.1 * 0.2 / 0.08,
            'obje_attrs.acceleration_scale': 2.0 * 1.0 / 1.25,
            'weap_attrs.interface.active_camo_ding': 0.65 * 0.25 / 0.4,
            # STEP 6: Halo 3's BR magazine item 72 (the pistol template's item is H1 pistol
            # ammo, which then tops the BR up -- as the AR's does the SMG)
            'weap_attrs.magazines.0.magazine_items.0.rounds': 72,
            # the on-gun counter's input (model 'numeric'): B exports the loaded fraction, as
            # on the AR (the pistol template exports nothing on B). TEST 2: the counter
            # jumped up on every shot and fell back to 0 -- the ILLUMINATION the pistol
            # template exports on A. Test 3 drops A: if the counter now counts the magazine,
            # it reads B (the AR's layout); if it stays at 00, it reads A (then A = ammo)
            # TEST 3: with A empty the counter stayed 00 -> the numeric shader reads A. So A =
            # the loaded fraction (the template's A illumination drove the test-2 jumps)
            'weap_attrs.A_in': 'primary_ammunition',
            'weap_attrs.B_in': 'primary_ammunition',
            # Halo 3's zoom sounds (the template names the sniper's)
            'weap_attrs.interface.zoom_in_sound.filepath': SND + 'br_zoom_in',
            'weap_attrs.interface.zoom_out_sound.filepath': SND + 'br_zoom_out',
        },
        # H3 single-wield: minimum error 0, error angle 0.15 -> 0.5 (H1 pistol 0, 0.2 -> 2.0)
        'error_deg': {'minimum_error': 0.0, 'error_angle': (0.15, 0.5)},
        # H3: 36 loaded, 108 at pickup, 144 most. Reload time: H3 BR and magnum both 0 (the
        # animation decides): 58 fr = 1.93 s, in the H1 pistol's shape (2.17 tag over its
        # 2.23 s animation) = 1.88
        'magazine': {'rounds_loaded_maximum': 36, 'rounds_reloaded': 36,
                     'rounds_total_initial': 108, 'rounds_total_maximum': 144,
                     'reload_time': 1.88},
        # H3 aim assist, absolute. Zoom: Halo 3's 1 level at 2x = the pistol template's own
        'aiming': {'autoaim_angle': 3.0, 'autoaim_range': 17.0,
                   'magnetism_angle': 6.0, 'magnetism_range': 21.0},
        'sound_effects': {
            'firing_effect': (PISTOL + 'effects\\fire bullet', BR + 'effects\\fire bullet',
                              {r'sound\sfx\weapons\pistol\fire': SND + 'br_fire'}),
            'empty_effect': (PISTOL + 'effects\\empty', BR + 'effects\\empty',
                             {r'sound\sfx\weapons\pistol\dryfire': SND + 'br_dryfire'})},
        'melee': (PISTOL + 'melee', BR + 'melee'),
        'melee_response': PISTOL + 'melee_response',
        'messages': ('Picked up a battle rifle', 'Picked up %d rounds for battle rifle'),
        'icon': 'battle rifle',
        'extra_sounds': [SND + 'br_reload_empty_balanced', SND + 'br_reload_full_balanced'],
        # the PISTOL's HUD with Halo 3's BR reticle (H3 hud_reticles #1; #24 is the headshot
        # cross, shown only on a headshot target: not reproduced) at the reserved 20, and a
        # magazine meter for 36 (default) and 54 (balanced). ZOOM (user, test 1): the zoom
        # HUD replaced ENTIRELY by Halo 3's -- the chud's zoom-only widgets (ring, rulers,
        # range meter, all drawn black) baked into the screen-effect mask (h1_h3_scope.py),
        # no blur, the pistol's zoom readouts dropped; the reticle stays (as in Halo 3)
        'hud': {'donor': PISTOL + 'pistol', 'out': BR + 'battle rifle',
                # test 2 (screenshot): the ring drew 435 x 322 px at 1920x1080 -- Halo 1 puts
                # the mask in a 4:3 box ~558 px tall. aspect 4/3 pre-squashes it round; span
                # 380 fits Halo 3's 369-unit ring into 97% of the texture (~50% of the
                # screen height; Halo 3 58%, Halo 1's pistol ~48%); 1024 px for crisp lines.
                # TEST 3: round, but the ring filled the WHOLE height -- the box is not fixed:
                # Halo 1 draws the mask ~1.09 px a TEXEL at 1080p (512 -> 558 px, 1024 -> ~1116).
                # So Halo 3's 58% (623 px) = 572 texels = 369 units -> span 1024 x 369/572 = 660.
                # Blur: radius 0 smeared it ('worse'; the pistol's is 'more gentle') -> the
                # donor's convolution kept, mask alpha 255 (test 4 tells what 255 means)
                'scope': {'chud': r'ui\chud\battle_rifle', 'out': BR + 'bitmaps\\scope_mask',
                          'size': 1024, 'span': 660.0, 'aspect': 4 / 3.0, 'alpha': 255},
                'reticle': ('hud_reticles', 1, 'battle rifle'),
                'reticle_thicken': 1,
                'flash_base': 12,                # the pistol's low-ammo cutoff is of 12
                'ammo_meter': {'sizes': (36, 54), 'base': BR + 'bitmaps\\battle_rifle_ammo'}},
        'palette_levels': ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40'],
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py battle_rifle). DEFAULT = Halo
    # 3's own numbers in the tags; BALANCED = the PISTOL ratio rule (step 4a, user
    # 2026-10-07). Assembly Halo1 units: angles in degrees, velocity in wu per TICK.
    # The burst CYCLE row (0.413 s default, 0.295 s balanced) waits for test 1's measurement
    'catalog': {
        'entry': {
            'weapon': 'Battle Rifle', 'source': 'Halo 3', 'donor': 'Pistol', 'default_on': False,
            'desc': "Halo 3's Battle Rifle: its model, first-person animations, sounds and "
                    "numbers. A 36-round, 3-round-burst rifle with a 2x zoom; Pistol ammo "
                    "tops it up.",
            'balance_desc': "Measured against the Pistol, which both games have: 10 damage "
                            "per round (30 a burst), a 54 magazine, 202 at pickup / 360 most, "
                            "a 2.6 s reload, a tighter spread, a faster bullet and Halo "
                            "1-style aim assist.",
            # step 9: the balanced reload, 67 fr x 58/50 = 2.59 s, against the BUILT 58
            # frames = x1.34; swap (ready + put-away, ONE multiplier in the patcher): ready
            # 35 x 19/22 = 30.2 frames over the built 19 = x1.59
            'anims': {'reload': 1.34, 'swap': 1.59},
            'anim_sounds': {'reload': [
                {'mult': 1.34, 'from': SND + 'br_reload_empty', 'to': SND + 'br_reload_empty_balanced'},
                {'mult': 1.34, 'from': SND + 'br_reload_full', 'to': SND + 'br_reload_full_balanced'}]},
            'balance': [
                row('jpt!', BR + 'bullet', 'Damage Lower Bound', 10.0, 6.0, 'Bullet Damage'),
                row('jpt!', BR + 'bullet', 'Damage Upper Bound', 10.0, 6.0, 'Bullet Damage'),
                row('jpt!', BR + 'bullet', 'Damage Upper Bound Max', 10.0, 6.0, 'Bullet Damage'),
                row('weap', BR + 'battle rifle', 'Rounds Loaded Maximum', 54.0, 36.0, 'Magazine', block='Magazines'),
                row('weap', BR + 'battle rifle', 'Rounds Reloaded', 54.0, 36.0, 'Magazine', block='Magazines'),
                row('weap', BR + 'battle rifle', 'Rounds Total Initial', 202.0, 108.0, 'Magazine', block='Magazines'),
                row('weap', BR + 'battle rifle', 'Rounds Total Maximum', 360.0, 144.0, 'Magazine', block='Magazines'),
                # STEP 6 balanced: Halo 3's own pickup : initial ratio (72 / 108) on 202
                row('weap', BR + 'battle rifle', 'Rounds', 135, 72, 'Ammo pickup', block='Magazines/Magazines'),
                row('weap', BR + 'battle rifle', 'Minimum Error', 0.0, 0.0, 'Error Angle', block='Triggers'),
                row('weap', BR + 'battle rifle', 'Error Angle', 0.06, 0.15, 'Error Angle', block='Triggers'),
                row('weap', BR + 'battle rifle', 'Error Angle Max', 2.0, 0.5, 'Error Angle', block='Triggers'),
                row('proj', BR + 'bullet', 'Initial Velocity', 10.0, 6.0, 'Projectile'),
                row('proj', BR + 'bullet', 'Final Velocity', 10.0, 6.0, 'Projectile'),
                row('weap', BR + 'battle rifle', 'Autoaim Angle', 4.5, 3.0, 'Autoaim'),
                row('weap', BR + 'battle rifle', 'Autoaim Range', 34.0, 17.0, 'Autoaim'),
                row('weap', BR + 'battle rifle', 'Magnetism Angle', 6.0, 6.0, 'Magnetism'),
                row('weap', BR + 'battle rifle', 'Magnetism Range', 31.5, 21.0, 'Magnetism'),
                # the 54 magazine's meter: battle_rifle_ammo sequence 1 (ammo_meter 36 54),
                # step 4; low-ammo flash 4 of 12 -> 18 of 54
                dict(row('wphi', BR + 'battle rifle', 'Sequence Index', 1, 0, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', BR + 'battle rifle', 'Alpha Multiplier', 4, 7, 'Ammo display', block='Meter Elements'), index=0),
                dict(row('wphi', BR + 'battle rifle', 'Sequence Index', 1, 0, 'Ammo display', block='Static Elements'), index=0),
                dict(row('wphi', BR + 'battle rifle', 'Loaded Ammo Cutoff', 18, 12, 'Ammo display'), index=0),
            ]},
    },

    # step 4b (port_field_audit.py --port battle_rifle): the source pair (H3 BR vs the
    # yardstick, H3 magnum) against the target pair (the H1 port vs its donor, the H1 pistol)
    'field_audit': {
        'source_kit': 'H3EK',
        'source': {'weapon': (H3 + r'\battle_rifle.weapon', r'objects\weapons\pistol\magnum\magnum.weapon'),
                   'projectile': (H3 + r'\projectiles\battle_rifle_bullet.projectile',
                                  r'objects\weapons\pistol\magnum\projectiles\magnum_bullet.projectile'),
                   'damage_effect': (H3 + r'\damage_effects\battle_rifle_bullet.damage_effect',
                                     r'objects\weapons\pistol\magnum\damage_effects\magnum_bullet.damage_effect')},
        'target': {'weapon': (BR + 'battle rifle.weapon', PISTOL + 'pistol.weapon'),
                   'projectile': (BR + 'bullet.projectile', PISTOL + 'bullet.projectile'),
                   'damage_effect': (BR + 'bullet.damage_effect', PISTOL + 'bullet.damage_effect')}},

    # the dry test: a30 (Covenant within seconds of the landing), the BR as the primary with
    # Halo 3's own loadout (36 loaded, 108 in all)
    'test': {'level': 'a30', 'rounds': (36, 108), 'grunt': None, 'elite': None},
})
