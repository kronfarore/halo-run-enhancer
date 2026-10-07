r"""Halo 3's Sentinel Beam, a FULL PORT into Halo 1 (2026-10-06, 12 boots on c40): Halo 3
geometry, look, FP animations and sounds on a copy of the plasma rifle; dropped by
Sentinels. PORTING.md "Halo 1: the Sentinel Beam, a full HALO 3 port"."""
from ._common import B, H3_FP_GRAPHS, ANIMS, PR_SOUNDS, row

NAME = 'Sentinel Beam'
H3SG = r'objects\weapons\support_low\sentinel_gun'
SB = 'weapons\\sentinel beam\\'
SBS = 'sound\\weapons\\sentinel_beam_port\\'
SB_WEAP = B.join(['weapons', 'sentinel beam', 'sentinel beam'])
SB_BEAM = B.join(['weapons', 'sentinel beam', 'beam'])
SG = B.join(['sentinel_gun', 'sent_gun', ''])
OH = B.join(['sentinel_beam_overheat', 'beam_overheat', ''])

PORT = {
    'order': 3,
    'wave': 'pre-plan',
    'name': NAME,
    'source': 'Halo 3',
    'status': 'done',
    'reservations': {'messages': (51, 52), 'icon': 29, 'reticle': 18, 'label': 'sb',
                     'teach_from': 'pr', 'sound_dir': r'sound\weapons\sentinel_beam_port',
                     'weapon_dir': r'weapons\sentinel beam'},
    'yardstick': {
        'pick': 'Plasma Rifle (ratio rule) + Sentinel (DIRECT, default damage)',
        'reason': 'user, step 5b 2026-10-06: default damage 4.64/round = what an H1 Sentinel '
                  'needs to kill the Chief in as many rounds as an H3 Sentinel on Legendary; '
                  'every other number by the plasma-rifle ratio; balanced damage 11.6 = the '
                  'plasma-rifle ratio per second',
        'candidates': {'ratio': 'Plasma Rifle', 'direct': 'Sentinel (characters\\sentinel)',
                       'peers': ['Plasma Rifle', 'Assault Rifle', 'Flamethrower']}},

    # geometry + look (h1_h3_weapon_model.py)
    'model': {
        'dir': r'weapons\sentinel beam',
        'world': H3SG + r'\sentinel_gun.render_model',
        'fp': H3SG + r'\fp_sentinel_gun\fp_sentinel_gun.render_model',
        'world_name': 'sentinel beam',
        # shader name (= the JMS material) -> (base map, illum map or None)
        'shaders': {'sentinel_beam': (H3SG + r'\bitmaps\sentinel_beam.bitmap',
                                      H3SG + r'\bitmaps\sentinel_beam_illum.bitmap')},
        'template': r'weapons\plasma rifle\fp\shaders\gun',
    },

    # A FULL PORT, geometry and all (h1_h3_weapon_model.py): Halo 1's FP model IS Halo 3's
    # (h3_rm_to_jms keeps its nodes), so the models share one space exactly.
    'retarget': {
        'graph': H3_FP_GRAPHS + r'\support_low\fp_sentinel_beam\fp_sentinel_beam.model_animation_graph',
        'render_model': r'objects\weapons\support_low\sentinel_gun\fp_sentinel_gun'
                        r'\fp_sentinel_gun.render_model',
        'nodes': {n: 'frame ' + n.replace('_', ' ') for n in
                  ('gun', 'barrel', 'clamp_left', 'clamp_right', 'powercore', 'powercore2',
                   'shield')},
        'h1_dir': r'weapons\sentinel beam\fp',
        'h1_model': r'weapons\sentinel beam\fp\fp',
        'align': 'same_space',
        # test 1 (2026-10-06): 'a bit too forward, I can see into the arms' -- the rig was
        # pushed 1.5 units AWAY from the camera (wrong way: test 2 'still too far forward,
        # set it back another 3 units'); now 3 units back from that, 1.5 toward the camera
        # test 3: 'making progress, another 1 unit'
        # test 4: 'down 2 units'; test 5: 'another unit backwards'
        # test 6: 'another unit down'
        # test 7: 'one more unit down'
        # test 8: '0.25 back and down'
        'view_offset': (-0.0375, 0.0, -0.0425),
        # Halo 1 plays `overheated` (looped) after `overheating` while the weapon is still
        # hot -- the stock plasma rifle has one (50 frames). Without it the engine replayed
        # `overheating` (test 5: overheat sound twice, the pose jumping back mid-way).
        # Halo 3's graph has none: the last overheating frame, held
        'holds': {'first-person overheated': ('first_person:overheating', 50)},
        'anims': {
            'first_person:idle:var1': 'first-person idle',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:fire_1:var1': 'first-person fire-1',
            'first_person:melee_strike_1': 'first-person melee',
            'first_person:moving': 'first-person moving',
            'first_person:overlays': 'first-person overlays',
            'first_person:posing:var1': 'first-person posing',
            # 69 frames = Halo 3's whole overheat recovery, (0.9 - 0.1) / 0.35 per s = 2.3 s
            'first_person:overheating': 'first-person overheating',
            'first_person:o_h_exit': 'first-person o-h-exit',
            'first_person:throw_grenade': 'first-person throw-grenade',
            'first_person:throw_overheated': 'first-person throw-overheated',
        },
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py) on a COPY of the plasma rifle (`template`: a heat +
    # battery automatic, the closest Halo 1 weapon). Numbers by the PORTING step-4 RATIO
    # RULE, the plasma rifle as the yardstick both games have:
    #   H1 value = H1 plasma rifle x (H3 sentinel beam / H3 plasma rifle)
    #   damage / round   13 x 4 / 10            = 5.2   (156 dps; H1 PR ~110 -- x1.4, H3 x1.6)
    #   heat / round     0.08 x 0.04 / 0.15     = 0.0213 (overheats after ~2.6 s, H3 2.57 s)
    #   heat loss / s    0.3 x 0.8525 / 0.8525  = 0.3   (0.9 -> 0.25 in 2.2 s = H3's 69-frame vent)
    #   thresholds       overheat 1.0 x 0.9 / 1 = 0.9, recovery 0.25 x 0.1 / 0.1 = 0.25
    #   battery / round  0.005 x 0.003 / 0.0025 = 0.006 (167 rounds; H1 batteries are half H3's)
    #   aim assist Halo 3's (1/12, 9/18)
    # RATE: 30/s in the tag fired at ~15/s in game (test 1, 2026-10-06: a full battery
    # emptied with the heat bar just over half -- 167 x 0.0213 - 0.3 x 167 / r = ~0.55 gives
    # r = ~16.7; a 30-tick engine). Test 2 set 15/s and it fired at ~10/s (overheat after ~6 s
    # with 27% battery left: 61 rounds in 6 s). Both fit ONE rule: a shot every
    # floor(30 / rate) + 1 ticks -- 30 -> 15/s, 15 -> 10/s. So the tag keeps 30/s (= 15/s in
    # game) and every PER-ROUND value above is doubled (10.4 damage, 0.0426 heat, 0.012
    # battery): the per-second numbers hold (overheat after ~2.6 s, as Halo 3).
    # Every round is a tracer (Halo 1's Sentinel gun: 0 between) -- the template's 3 drew the
    # contrail on one round in four (test 1). Test 2: still no beam in view, but one in the
    # floor's REFLECTION -- the contrail is a viewer-facing ribbon and the round left from the
    # camera along the view axis, so it was seen exactly end-on (zero width). The trigger's
    # first-person offset (the rocket launcher has one: y -0.1) starts it at the gun instead.
    # The damage effect is a copy of the plasma rifle BOLT's (x2 on shields, x0.5 on armour --
    # the yardstick's, and Halo 3's beam is plasma-category); the projectile a copy of Halo
    # 1's own Sentinel beam (its contrail is the Sentinel look) with Halo 3's 120 wu range.
    'pickable': {
        'weapon': SB + 'sentinel beam',
        'template': r'weapons\plasma rifle\plasma rifle',
        'world_model': SB + 'sentinel beam',
        'fp_model': SB + 'fp\\fp',
        'fp_anims': SB + 'fp\\fp',
        'label': 'sb',
        'teach': ('sb', 'pr'),
        'keys': {'first-person melee': 5},
        # Halo 3's own (the Sentinel's) sounds, h1_port_sounds.py sentinel_beam. Halo 1's
        # plasma rifle cues its overheat from the FP overheating animation, so this does too
        'sounds': {'first-person ready': SBS + 'beam_ready',
                   'first-person posing': SBS + 'beam_pose',
                   'first-person melee': SBS + 'beam_melee',
                   'first-person overheating': SBS + 'beam_overheat'},
        # THE HUM: a sound_looping (a clone of the flamethrower's fire_ft: fade in/out) with
        # Halo 3's in / 0.5 s seamless loop / out, on the trigger's RATE OF FIRE: input C =
        # `primary rate of fire`, function 0 = 'one' scaled by it, the loop on A_out. That
        # input ramps up over the trigger's acceleration time while fire is held and down
        # over its deceleration time (0.1 s) after -- smooth, no per-round toggling. The rate
        # bounds differ (29..30) so the ramp is not 0/0 (both fire every 2nd tick = 15/s).
        # The record (2026-10-06):
        #   test 1  `primary firing on` (input C, function 3)          silent
        #   test 2  illumination, hold 0.15 s, 10 rounds/s, 4.3 s loop  plays, 'a bit long'
        #   test 3  illumination, hold 0.08 s, 15 rounds/s, 0.5 s loop  tail grows with hold
        #   test 4  per-shot grains in the firing effect                'static'
        #   test 5  `primary firing on` the flamethrower's exact way      silent
        #           (input B, its function 1, B_out) -- that input never reaches this weapon
        #   test 6  illumination, hold 0.15 s, 15 rounds/s, 0.5 s loop  persists again
        # So the illumination signal lingers whatever its hold: the rate of fire instead
        # The trigger keeps ramping while fire is HELD, so the hum must also go off when the
        # weapon cannot fire -- `turn off with` (a function is off when its value is 0, and
        # off with whatever its own turn-off function is off with: test 9 showed the chain
        # carries the battery link):
        #   test 7: an empty battery kept the hum going -> off with function 3 (the template's
        #           battery left, age inverted): WORKS (test 8)
        #   test 8: an overheat with fire held kept it going ->
        #     test 9  chain via `overheated` (inverted, function 1)         no effect
        #     test 10 off with the illumination function                    no effect; and
        #             it broke the battery case: illumination stays up while fire is HELD
        #             (silent on a fresh press with a dead battery) -- trigger-driven, like
        #             the rate of fire, not per round
        #   Inputs that never move here: `primary firing on`, `overheated`. Weapon-state
        #   inputs that do: age (battery), heat.
        #     test 11 chain via `ready` (function 1, off with 3)            battery yes,
        #             overheat no -- `ready` stays 1 through an overheat
        #     test 12 chain via `primary firing` (NOT `firing on`; the last untried input
        #             with a plausible meaning): 1 while the trigger is in its firing state
        #             would end the overheat hum; a once-per-round pulse would make the hum
        #             stutter/stack instead (then: back to test 11's wiring)
        # The template's heat-flare lights (blue plasma rifle flares, function 1) are gone
        'rewire': {'inputs': ('primary_firing', 'illumination', 'primary_rate_of_fire', 'age'),
                   'functions': {0: (2, 'C_in', 'fire loop', {'turn_off_with': 1}),
                                 1: (2, 'A_in', 'primary firing', {'turn_off_with': 3})},
                   'drop_attachments_on': ('B_out',)},
        'fire_loop': {'tag': SBS + 'beam_fire', 'like': r'sound\sfx\weapons\flamethrower\fire_ft',
                      'start': SBS + 'beam_fire_in', 'loop': SBS + 'beam_fire_loop',
                      'end': SBS + 'beam_fire_out', 'marker': 'primary trigger',
                      'scale': 'A_out'},
        # THE FIRING EFFECT (own, every round): the plasma rifle's flash particles only (no
        # smoke, no tracer, no sound), recoloured to the Sentinel gunlight's red, plus the
        # muzzle light. Test 5: a light/lens flare in the effect showed ABOVE THE RIGHT ARM
        # (effect lights spawn at the hidden third-person weapon), while the particles carry
        # `first person only` and spawn at the first-person muzzle -- the visible glow
        'fire_effect': {'from': r'weapons\plasma rifle\effects\plasma rifle upper fire',
                        'out': SB + 'effects\\fire', 'sound': '', 'light': SB + 'muzzle light',
                        # test 7: still blue-white -- not the colour source: five additive
                        # flash sprites, ~20 alive at 15 rounds/s, saturate to white (the
                        # plasma pistol's green flash IS an RGB tint on the same sprite). One
                        # sprite (`flash c generic` exactly), a deep red tint
                        'keep_particles': 'flash c generic', 'tint': (1.0, 1.0, 0.15, 0.05),
                        # test 8: red, right -- '0.25 units up and right on the muzzle'
                        # (wu, marker space: forward, left, up); test 9: right way, 0.5 more
                        'particle_offset': (0.0, -0.0075, 0.0075)},
        # test 6: the glow came out plasma rifle blue-white anyway -- the `c generic`
        # particles take the WEAPON's change colour A (the template wanders teal..blue), not
        # the effect's tint. Change colour A = the Sentinel gunlight's red (rgb, rgb)
        'change_color_a': ((1.0, 0.45, 0.4), (1.0, 0.3, 0.25)),
        # the light (lights the surroundings): test 2 used the Sentinel's own gunlight --
        # NOT dynamic (a 0.5 wu glow for the Sentinel's body). Own light = the plasma rifle
        # muzzle flash (dynamic) in the gunlight's colour, alive `duration` s per round; no
        # lens flare (test 5: it floated over the arm)
        'own_light': {'shape': r'weapons\plasma rifle\muzzle flash',
                      'look': r'characters\sentinel\gunlight', 'out': SB + 'muzzle light',
                      # test 3: still nothing to see -- gone HARD (radius x3, full alpha and
                      # brightness on both bounds), to be paddled back once it shows
                      'radius': 6.0, 'argb': (1.0, 1.0, 0.45, 0.4), 'duration': 0.1,
                      'no_flare': True},
        # Halo 1's overheat steam spawns at the plasma rifle's `vent` markers, which this
        # model lacks (test 5: no particles): own copy at `overheat`
        'overheated_effect': {'from': r'weapons\plasma rifle\effects\overheated',
                              'out': SB + 'effects\\overheated', 'locations': {'vent': 'overheat'}},
        # the template's misfire burst (a low-battery misfire) aims at `vent` too
        'misfire_effect': {'from': r'weapons\plasma rifle\effects\misfire',
                           'out': SB + 'effects\\misfire', 'locations': {'vent': 'overheat'}},
        'attach_swap': {r'weapons\plasma rifle\muzzle flash': SB + 'muzzle light'},
        # the template's attachments sit on plasma rifle markers this model lacks
        # THE DROP (user's option B): Halo 1's Sentinel carries no droppable weapon, so its
        # death effect spawns the beam as a weapon part beside the debris. `death` is the
        # coll's body DESTROYED effect, whose threshold is 0 -- it plays on every kill
        'death_drop': [r'characters\sentinel\effects\death'],
        # IN EVERY MAP: the death effect only brings the beam into levels with Sentinels (c10,
        # c20, c40, d40); the enhancer may offer it anywhere, so it is APPENDED to every
        # level's weapons palette, like the SAW / sword / fuel rod (a palette entry is enough
        # for tool to build the tag in; appending keeps every existing palette index)
        'palette_levels': ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40'],
        'attach_markers': {'secondary trigger': 'primary trigger', 'heat flare': 'overheat',
                           'heat flare1': 'overheat'},
        'melee': (r'weapons\plasma rifle\melee', SB + 'melee'),
        'melee_response': r'weapons\plasma rifle\melee_response',
        'messages': ('Picked up a sentinel beam', 'Picked up %d rounds for sentinel beam'),
        'icon': 'sentinel beam',
        'hud': {'donor': r'weapons\plasma rifle\plasma rifle', 'out': SB + 'sentinel beam',
                'reticle': ('hud_reticles', 21, 'sentinel beam')},
        'aiming': {'autoaim_angle': 1.0, 'autoaim_range': 12.0,
                   'magnetism_angle': 9.0, 'magnetism_range': 18.0},
        'beam': {'projectile': (r'characters\sentinel\beam', SB + 'beam'),
                 'damage': (r'weapons\plasma rifle\bolt', SB + 'beam'),
                 # DAMAGE (user, step 5b, 2026-10-06): the SENTINEL yardstick. Halo 3's
                 # Sentinels fire the player's own beam, so the H1 beam's base damage is what
                 # an H1 Sentinel would need to kill the Chief (150) in as many rounds as an
                 # H3 Sentinel kills the Master Chief (115): 4 x 150/115 x H3 scale / H1 scale
                 # -- Normal 4.04, LEGENDARY 4.64 (1.6 / 1.8), chosen. (Halo 1's real Sentinel
                 # beam is 1.0.) 11.6 (plasma-rifle ratio per second) is the BALANCED row
                 'range': 120.0, 'dmg': 4.64, 'acceleration': 0.05},
        'trigger': {'rounds_per_second': (29.0, 30.0), 'heat_generated_per_round': 0.0426,
                    'acceleration_time': 0.05, 'deceleration_time': 0.1,
                    'age_generated_per_round': 0.012, 'error_angle': (0.0, 0.0),
                    'rounds_between_tracers': 0,
                    # wu: right, down -- test 3: y -0.04 sat right of the muzzle ('further to
                    # the left'); test 4: 'a bit up and right', and the FP rig went 2 units down
                    # (the muzzle with it): y -0.03, z -0.035 + 0.01 - 0.02
                    # test 5: 'halfway back to the left and down'
                    # test 6: good -- then the FP rig went 1 unit down, the start with it
                    # test 7: rig 1 more unit down, the start with it
                    # test 8: rig 0.25 down, the start with it
                    'first_person_offset': (0.0, -0.025, -0.0725),
                    # the muzzle light's hold (the hum no longer follows it)
                    'illumination_recovery_time': 0.15},
        'heat': {'recovery_threshold': 0.25, 'overheated_threshold': 0.9,
                 'loss_per_second': 0.3},
    },

    # the Sentinel Beam (a full port): Halo 3's player weapon cues the Sentinel's own
    # sounds. The fire loop is a Halo 1 sound_looping (start/loop/end tracks), scaled by
    # the weapon's illumination; the overheat is in + loop + out as one 2.4 s one-shot on
    # the overheated effect (the vent is 2.2 s)
    'sounds': {
        'catalog': NAME,
        'dir': B.join(['sound', 'weapons', 'sentinel_beam_port']),
        'h3_dir': 'data\\sound\\characters\\sentinel\\',
        'sounds': {
            'beam_ready': (['sentinel_ready'], ANIMS + B + 'plasrifle_ready', -13.1),
            'beam_pose': (['sentinel_posing'], ANIMS + B + 'plasrifle_posing', -20.0),
            'beam_melee': (['sentinel_melee'], ANIMS + B + 'plasrifle_melee', -16.2),
            'beam_fire_in': ([SG + 'in'], PR_SOUNDS + B + 'fire', -16.0),
            'beam_fire_loop': ([SG + 'loop'], PR_SOUNDS + B + 'fire', -16.0),
            'beam_fire_grain': ([SG + 'loop'], PR_SOUNDS + B + 'fire', -19.0),
            'beam_fire_out': ([SG + 'out'], PR_SOUNDS + B + 'fire', -16.0),
            'beam_overheat': ([tuple(OH + k for k in ('in', 'loop', 'out'))],
                              PR_SOUNDS + B + 'overheat', -18.0),
        },
        # Halo 1 lets a looping sound finish its current pass before the end track: Halo
        # 3's 4.3 s loop hummed on for seconds after the trigger was let go (test 3)
        'loop_len': {'beam_fire_loop': 0.5},
        # test 4: the hum still lingered, LONGER the longer fire was held -- the loop
        # attachment toggled per round and queued its start/end tracks. The hum is now
        # per SHOT, like every stock weapon's fire sound: grains of the loop (seconds,
        # count -> permutations from spread offsets, faded ends), one per round at 15/s,
        # overlapping into a steady tone that ends with the last round
        'grains': {'beam_fire_grain': (0.13, 8)},
    },

    # a FULL PORT from Halo 3 (2026-10-06, tested on c40 over 12 boots): Halo 1's Sentinels
    # carry no droppable weapon, so their death effect drops it (user's option B) -- it is
    # obtainable on the levels with Sentinels. Built on a copy of the plasma rifle, whose
    # cards it takes. 'weap', 'tag_map', 'card_map', 'skip_cards' are the enhancer
    # session's (kept by the merge).
    'catalog': {
        'entry': {
            'weapon': NAME, 'source': 'Halo 3', 'donor': 'Plasma Rifle', 'default_on': False,
            'desc': "Halo 3's Sentinel Beam: its model, first-person animations and sounds. "
                    "Dropped by Sentinels when they die. A continuous beam on heat and battery.",
            'balance_desc': "11.6 damage per round instead of 4.64, Halo "
                            "1-style aim assist (1 deg / 25 wu autoaim, 12 deg / 25 wu "
                            "magnetism) and Halo 3's battery: 11 s of fire instead of 5.6 s.",
            'fp_animations': B.join(['weapons', 'sentinel beam', 'fp', 'fp']),
            # the weapon's own projectile exists only in the player build
            'requires': ['proj ' + B.join(['weapons', 'sentinel beam', 'beam'])],
            'anims': {},
            # step 5b (h1_role_compare.py sentinel_beam, user-chosen 2026-10-06). The default
            # keeps Halo 3's ABSOLUTE aim assist and a per-round battery ratio; balanced:
            'balance': [
                # the ratio rule on aim assist, plasma rifle yardstick (H1 5/25, 12/25; H3
                # 5/12, 9/18; H3 beam 1/12, 9/18): angle 5 x 1/5 = 1, range 25 x 12/12 = 25;
                # magnet 12 x 9/9 = 12, range 25 x 18/18 = 25 -- Halo 1's automatics reach 25
                row('weap', SB_WEAP, 'Autoaim Range', 25.0, 12.0, 'Aim assist'),
                row('weap', SB_WEAP, 'Magnetism Angle', 12.0, 9.0, 'Aim assist'),
                row('weap', SB_WEAP, 'Magnetism Range', 25.0, 18.0, 'Aim assist'),
                # Halo 3's battery TIME: 0.003 x 30/s = 333 rounds = 11.1 s; at Halo 1's real
                # 15/s that is 167 rounds = 0.006 per round (default 0.012 = 5.6 s)
                row('weap', SB_WEAP, 'Age Generated Per Round', 0.006, 0.012,
                    'Battery per round', block='Triggers'),
                # damage: the default 4.64/round = what an H1 Sentinel would need to kill the
                # Chief in as many rounds as an H3 Sentinel on Legendary; balanced = the
                # plasma-rifle ratio PER SECOND: H3 beam 120 / H3 plasma rifle 90 (10 x 9/s)
                # x H1 plasma rifle 130 (13 x 10/s) = 173/s, / the real 15/s = 11.6 per round
                row('jpt!', SB_BEAM, 'Damage Lower Bound', 11.6, 4.64, 'Beam damage'),
                row('jpt!', SB_BEAM, 'Damage Upper Bound', 11.6, 4.64, 'Beam damage'),
                row('jpt!', SB_BEAM, 'Damage Upper Bound Max', 11.6, 4.64, 'Beam damage'),
            ]},
    },

    # step 11: a same-game stand-in -- its label 'sb' has no other carrier; fire like
    # Halo 1's Sentinel, drop charged like the plasma-rifle Elite (PORTING step 11)
    'firing_profile': {
        'mode': 'same_game', 'donor_weapon': r'characters\sentinel\sentinel',
        'why': 'Sentinel Beam fires like the Sentinel whose beam it replaces',
        'set': ['0x1D8=0.7:Drop Weapon Loaded', '0x1DC=0.9:Drop Weapon Loaded Max']},

    # the dry test map it was proven on (12 boots), enemies swapped to Sentinels
    'test': {'level': 'c40', 'rounds': (0, 0),
             'grunt': r'characters\sentinel\sentinel', 'elite': None},
}
