r"""Make Halo 1's enemy-only Energy Sword and Fuel Rod pickable (HCEEK kit tags).

Halo 1 SHIPS both weapons -- the Elites' `weapons\energy sword\energy sword` and the
Grunts' `weapons\fuel rod gun\fuel rod` -- but as enemy-only items: each carries the weapon
flag `detonates_when_dropped` (the sword disperses, the fuel rod blows up 1.75-3 s after
landing), and neither has a first-person model, first-person animations or (the fuel rod)
a HUD. The user's call (2026-10-05): pick up the ORIGINAL weapons, behaviour unchanged --
the fuel rod keeps its 4-round magazine, 1.25 s charge and rod projectile.

What this writes, all idempotent, every stock tag backed up once as <tag>.before_pickable:

  weapon tag     detonates_when_dropped cleared; first-person model + animations named
                 (h1_fp_retarget.py builds those from Halo 3's FP animations); the fuel rod
                 gets its own HUD and its own melee damage (Halo 1: every weapon owns one)
  FP animations  melee key frames (Halo 3's primary_keyframe) and the stock Halo 1 sounds
                 that fit: the Elite's sword swing, the fuel rod's own melee, the PC fuel
                 rod's ready sound. Reload stays silent until the port's own sounds (step 10).
  fuel rod HUD   the PC fuel rod's (`weapons\plasma_cannon`: its crosshair and pickup icon)
                 with the Assault Rifle's magazine readout -- child `ui\hud\master rounds`
                 and a 4-tick meter from ammo_meter.py -- instead of its heat display
  player biped   `characters\cyborg\cyborg` is taught the two labels: `fr` from the PC fuel
                 rod's `pc` (plasmacannon class), `fb` from the oddball's `b` (pistol class).
                 Without the label the third-person pose has no animations (enemy AI in
                 the same case fell back to its default weapon, halo1-enemy-weapon-teaching).

The sword gets no HUD and no trigger -- exactly the oddball's setup (`weapons\ball\ball`:
no HUD interface, no triggers, own melee). Its FP model is its own world model; the
retarget poses that directly (h1_fp_retarget.py, 'same_space').

Maps must be REBUILT afterwards (h1_rebuild_all.py): every change here is a kit tag.

    python h1_pickable_weapons.py            # show what it would do
    python h1_pickable_weapons.py --write
"""
import argparse
import math
import copy
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.weap import weap_def  # noqa: E402
from reclaimer.hek.defs.antr import antr_def  # noqa: E402
from reclaimer.hek.defs.wphi import wphi_def  # noqa: E402
from reclaimer.hek.defs.proj import proj_def  # noqa: E402
from reclaimer.hek.defs.jpt_ import jpt__def  # noqa: E402
from reclaimer.hek.defs.actv import actv_def  # noqa: E402
from reclaimer.hek.defs.bitm import bitm_def  # noqa: E402
from reclaimer.hek.defs.ustr import ustr_def  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
BACKUP = '.before_pickable'
CYBORG = r'characters\cyborg\cyborg'

SWORD_SWING = r'sound\sfx\impulse\animations\elite\stand_sword_melee.mov'
SWORD_SOUNDS = 'sound\\weapons\\energy_sword_port\\'
ROD_SOUNDS = 'sound\\weapons\\fuel_rod_port\\'

WEAPONS = {
    'energy_sword': {
        'weapon': r'weapons\energy sword\energy sword',
        'fp_model': r'weapons\energy sword\energy sword',
        'fp_anims': r'weapons\energy sword\fp\fp',
        'teach': ('fb', 'b'),
        'keys': {'first-person melee': 5},
        # Halo 3's own sword sounds (h1_port_sounds.py energy_sword): the Elite's swing
        # (SWORD_SWING) is silent for 0.45 s and was heard 0.3 s late (user, 2026-10-06)
        'sounds': {'first-person melee': SWORD_SOUNDS + 'sword_melee',
                   'first-person fire-1': SWORD_SOUNDS + 'sword_lunge',
                   'first-person ready': SWORD_SOUNDS + 'sword_ready',
                   'first-person posing': SWORD_SOUNDS + 'sword_pose'},
        # Halo 3 plays the ignition from its blade_activate effect, 0.6 s after the sword
        # turns on (that event's delay) -- 18 frames into the ready (user: 'too early' at 0)
        'sound_frames': {'first-person ready': 18},
        # the hit: the melee damage effect's own sound (slash AND lunge strike use it)
        'hit_sound': SWORD_SOUNDS + 'sword_hit',
        # the hum: a sound_looping (the plasma rifle charge loop's shape) on the blade
        'hum': {'loop': SWORD_SOUNDS + 'sword_hum', 'tag': SWORD_SOUNDS + 'sword_hum',
                'like': r'sound\sfx\weapons\plasma rifle\charging', 'marker': 'flare'},
        # MCC's Halo 1 localization has no line for message 8 ("need string insert here"
        # in game, 2026-10-05): the sword gets its own appended pair, like the SAW's 47/48
        'messages': ('Picked up an energy sword', 'Picked up %d rounds for energy sword'),
        'icon': 'energy sword',                  # hud_msg_icons sequence (add_msg_icon.py)
        # the plasma pistol's HUD, whose BATTERY bar (age) is the sword's energy (the heat
        # half of `master plasma` stays empty: the sword makes no heat), with HALO 3's sword
        # reticle (hud_reticles #13) brought in by h1_add_reticle.py
        'hud': {'donor': r'weapons\plasma pistol\plasma pistol',
                'out': r'weapons\energy sword\energy sword',
                'reticle': ('hud_reticles', 13, 'energy sword')},
        # aim assist: Halo 3's sword (degrees, wu) -- the AI-only tag had none
        'aiming': {'autoaim_angle': 10.0, 'autoaim_range': 2.5,
                   'magnetism_angle': 10.0, 'magnetism_range': 6.0},
        # THE LUNGE (fire button), experimental: Halo 1 has no player lunge. A trigger
        # fires an invisible strike that dies after LUNGE_RANGE and does the sword's own
        # melee damage, and its firing damage on the wielder carries an instantaneous
        # acceleration -- the shove. Each lunge costs LUNGE_ENERGY of the battery (Halo 3
        # costs 0.1 per KILL, which Halo 1 cannot count); at full age it cannot fire.
        # Sword Elites keep their melee: their actor variants fire at rate 0.
        'lunge': {'template': r'weapons\plasma pistol\plasma pistol',
                  'strike': r'weapons\energy sword\lunge',          # projectile
                  'strike_from': r'weapons\assault rifle\bullet',
                  # the strike's OWN damage (step 3): a copy of the sword's melee damage, so a
                  # balance row (e.g. the balanced build's damage RADIUS) moves only the lunge,
                  # not the regular melee and not the Elites' sword
                  'strike_damage': r'weapons\energy sword\lunge strike',
                  'push': r'weapons\energy sword\lunge push',       # firing damage
                  'push_from': r'weapons\plasma pistol\trigger',
                  # first boot (2026-10-06): strike hit, shove did nothing with 0 damage
                  # and every material modifier 0 -- now a token 0.01 damage, modifiers 1.
                  # Second boot: +3 pushed the player BACK, a negative value forward; too
                  # much acceleration hurts the player (user tuned it live). Halo 3's
                  # aim assist stays the original; stronger lunge assist = balanced build.
                  # third boot: the user settled on -10 live
                  'range': 1.5, 'velocity': 60.0, 'acceleration': -10.0, 'push_damage': 0.01,
                  'energy': 0.1, 'rate': 1.0,
                  # the strike's HIT sound (user, 2026-10-06: the lunge hit silently -- a
                  # damage effect's sound plays for melee, not for a projectile's impact):
                  # a one-part impact effect, the AR's `impact dirt` without its decal,
                  # on every material response
                  'hit_effect': (r'weapons\assault rifle\effects\impact dirt',
                                 r'weapons\energy sword\effects\lunge hit')},
    },
    'fuel_rod': {
        'weapon': r'weapons\fuel rod gun\fuel rod',
        # a10 has no Grunt fuel rod (its palette carries only the Hunters'): palette entry
        # + resident-only placement there too, so the enhancer can offer it (user,
        # 2026-10-06); the other nine levels carry it already
        'palette_levels': ['a10'],
        'fp_model': r'weapons\fuel rod gun\fp\fp',
        'fp_anims': r'weapons\fuel rod gun\fp\fp',
        'teach': ('fr', 'pc'),
        'keys': {'first-person melee': 5},
        # Halo 3's own fuel rod sounds (h1_port_sounds.py fuel_rod), all cued at frame 0
        # as Halo 3 does; the original fuel rod never had first-person sounds
        'sounds': {'first-person melee': ROD_SOUNDS + 'rod_melee',
                   'first-person ready': ROD_SOUNDS + 'rod_ready',
                   'first-person reload-empty': ROD_SOUNDS + 'rod_reload',
                   'first-person reload-full': ROD_SOUNDS + 'rod_reload',
                   'first-person posing': ROD_SOUNDS + 'rod_pose',
                   'first-person fire-1': ROD_SOUNDS + 'rod_fire'},
        # Halo 1 rule (PORTING.md step 3): a weapon owns its melee damage tag. The PC fuel
        # rod's is the Chief-held fuel rod's melee; the response stays shared (feedback).
        'melee': (r'weapons\plasma_cannon\effects\plasma_cannon_melee',
                  r'weapons\fuel rod gun\melee'),
        'melee_response': r'weapons\plasma_cannon\effects\plasma_cannon_melee_response',
        # HUD (user, 2026-10-06): the PC fuel rod's own -- its crosshair is the right one --
        # on `master rounds`, with the RL's loaded-ammo elements drawing HALO 3's fuel rod
        # meter, four of its rods (h1_rocket_meter.py h3_rods)
        'hud': {'donor': r'weapons\plasma_cannon\plasma_cannon',
                'readout': r'weapons\rocket launcher\rocket_launcher',
                'out': r'weapons\fuel rod gun\fuel rod',
                'meter': r'weapons\fuel rod gun\bitmaps\fuel_rod_rods', 'art': 'h3_rods_row'},
        # the charge (vanilla: hold 1.25 s, it fires when full): the plasma pistol's own
        # charging loop, as the pistol plays it -- an attachment on `primary trigger`
        # scaled by an object function fed by the weapon's primary_charged (input B).
        # Halo 1 has no FP animation slot that plays DURING a charge (`overcharged` plays
        # once full, and the fuel rod fires at that instant).
        'charge_loop': {'sound': r'sound\sfx\weapons\plasma rifle\charging',
                        'marker': 'primary trigger', 'input': 'B_in',
                        # and a GLOW while charging (user, 2026-10-06: only the model's own
                        # self-illumination showed): the fuel rod folder's own light volume
                        # (the Hunter's arm glow) and light, which nothing attached
                        'glow': [r'weapons\fuel rod gun\hunter fuel rod',
                                 r'weapons\fuel rod gun\illumination']},
        # STEP 3 (PORTING.md): its OWN projectile and damage. The Grunts' fuel rod fired
        # `weapons\fuel rod gun\fuel rod`, the HUNTERS' projectile -- so the enhancer's
        # Hunter cards (Fuel Rod Range / Velocity / Gravity on the projectile, Hunter Fuel
        # Rod Damage on `explosion` through the detonation effect) moved the Grunts' and now
        # the player's fuel rod too. Same values, own tags; the Hunters keep the originals.
        'own_projectile': {
            'projectile': (r'weapons\fuel rod gun\fuel rod', r'weapons\fuel rod gun\grunt fuel rod'),
            'effect': (r'weapons\fuel rod gun\effects\explosion',
                       r'weapons\fuel rod gun\effects\grunt explosion'),
            'damage': (r'weapons\fuel rod gun\explosion', r'weapons\fuel rod gun\grunt explosion')},
        # the AI-only tag fired with rounds_per_shot 0 (never spent a round, never reloaded)
        # and had no aim assist; Halo 3's fuel rod values (degrees, wu)
        'rounds_per_shot': 1,
        'aiming': {'autoaim_angle': 4.0, 'autoaim_range': 25.0,
                   'magnetism_angle': 6.0, 'magnetism_range': 25.0},
        'icon': 'fuel rod',
        # the fuel rod Grunts dropped it EMPTY (actv drop_weapon_loaded 0..0, ammo 0..0 --
        # it detonated anyway); a plasma pistol Grunt drops 70-90%
        'drops': {r'characters\grunt\grunt specops fuel rod': ((0.5, 1.0), (2, 6)),
                  r'characters\grunt\grunt specops fuel rod airdef': ((0.5, 1.0), (2, 6))},
    },
}
# ---------------------------------------------------------------------------------------
# A FULL PORT, not a restoration: the Sentinel Beam, built from Halo 3 (geometry + look
# h1_h3_weapon_model.py, FP animations h1_fp_retarget.py) on a COPY of the plasma rifle
# (`template`: a heat + battery automatic, the closest Halo 1 weapon). Numbers by the
# PORTING step-4 RATIO RULE, the plasma rifle as the yardstick both games have:
#   H1 value = H1 plasma rifle x (H3 sentinel beam / H3 plasma rifle)
#   damage / round   13 x 4 / 10            = 5.2   (156 dps; H1 PR ~110 -- x1.4, H3 x1.6)
#   heat / round     0.08 x 0.04 / 0.15     = 0.0213 (overheats after ~2.6 s, H3 2.57 s)
#   heat loss / s    0.3 x 0.8525 / 0.8525  = 0.3   (0.9 -> 0.25 in 2.2 s = H3's 69-frame vent)
#   thresholds       overheat 1.0 x 0.9 / 1 = 0.9, recovery 0.25 x 0.1 / 0.1 = 0.25
#   battery / round  0.005 x 0.003 / 0.0025 = 0.006 (167 rounds; H1 batteries are half H3's)
#   aim assist Halo 3's (1/12, 9/18)
# RATE: 30/s in the tag fired at ~15/s in game (test 1, 2026-10-06: a full battery emptied
# with the heat bar just over half -- 167 x 0.0213 - 0.3 x 167 / r = ~0.55 gives r = ~16.7;
# a 30-tick engine). Test 2 set 15/s and it fired at ~10/s (overheat after ~6 s with 27%
# battery left: 61 rounds in 6 s). Both fit ONE rule: a shot every floor(30 / rate) + 1
# ticks -- 30 -> 15/s, 15 -> 10/s. So the tag keeps 30/s (= 15/s in game) and every
# PER-ROUND value above is doubled (10.4 damage, 0.0426 heat, 0.012 battery): the
# per-second numbers hold (overheat after ~2.6 s, as Halo 3).
# Every round is a tracer (Halo 1's Sentinel gun: 0 between) -- the template's 3 drew the
# contrail on one round in four (test 1). Test 2: still no beam in view, but one in the
# floor's REFLECTION -- the contrail is a viewer-facing ribbon and the round left from the
# camera along the view axis, so it was seen exactly end-on (zero width). The trigger's
# first-person offset (the rocket launcher has one: y -0.1) starts it at the gun instead.
# The damage effect is a copy of the plasma rifle BOLT's (x2 on shields, x0.5 on armour --
# the yardstick's, and Halo 3's beam is plasma-category); the projectile a copy of Halo 1's
# own Sentinel beam (its contrail is the Sentinel look) with Halo 3's 120 wu range.
SB = 'weapons\\sentinel beam\\'
SBS = 'sound\\weapons\\sentinel_beam_port\\'
WEAPONS['sentinel_beam'] = {
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
    # `primary rate of fire`, function 0 = 'one' scaled by it, the loop on A_out. That input ramps up over the
    # trigger's acceleration time while fire is held and down over its deceleration time
    # (0.1 s) after -- smooth, no per-round toggling. The rate bounds differ (29..30) so
    # the ramp is not 0/0 (both fire every 2nd tick = 15/s).
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
                  'end': SBS + 'beam_fire_out', 'marker': 'primary trigger', 'scale': 'A_out'},
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
             # an H1 Sentinel would need to kill the Chief (150) in as many rounds as an H3
             # Sentinel kills the Master Chief (115): 4 x 150/115 x H3 scale / H1 scale --
             # Normal 4.04, LEGENDARY 4.64 (1.6 / 1.8), chosen. (Halo 1's real Sentinel
             # beam is 1.0.) 11.6 (plasma-rifle ratio per second) is the BALANCED row
             'range': 120.0, 'dmg': 4.64, 'acceleration': 0.05},
    'trigger': {'rounds_per_second': (29.0, 30.0), 'heat_generated_per_round': 0.0426,
                'acceleration_time': 0.05, 'deceleration_time': 0.1,
                'age_generated_per_round': 0.012, 'error_angle': (0.0, 0.0),
                'rounds_between_tracers': 0,
                # wu: right, down -- test 3: y -0.04 sat right of the muzzle ('further to the left')
                # test 4: 'a bit up and right', and the FP rig went 2 units down (the
                # muzzle with it): y -0.03, z -0.035 + 0.01 - 0.02
                # test 5: 'halfway back to the left and down'
                # test 6: good -- then the FP rig went 1 unit down, the start with it
                # test 7: rig 1 more unit down, the start with it
                # test 8: rig 0.25 down, the start with it
                'first_person_offset': (0.0, -0.025, -0.0725),
                # the muzzle light's hold (the hum no longer follows it)
                'illumination_recovery_time': 0.15},
    'heat': {'recovery_threshold': 0.25, 'overheated_threshold': 0.9,
             'loss_per_second': 0.3},
}
MESSAGES = r'ui\hud\hud_item_messages'
STOCK_MESSAGES = 47       # entries 0..46 ship with the game; ports append (the SAW is 47/48)
ICONS = r'ui\hud\bitmaps\combined\hud_msg_icons'


def path(rel, ext):
    return os.path.join(TAGS, rel + ext)


def backup(p):
    if os.path.exists(p) and not os.path.exists(p + BACKUP):
        shutil.copy2(p, p + BACKUP)


def save(tag, p, write):
    if write:
        backup(p)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tag.serialize(filepath=p, temp=False, backup=False)


def icon_sequence(name):
    """hud_msg_icons sequence index of a pickup icon added by add_msg_icon.py."""
    d = bitm_def.build(filepath=path(ICONS, '.bitmap')).data.tagdata
    names = [q.sequence_name for q in d.sequences.STEPTREE]
    if name not in names:
        raise SystemExit('no %r icon in hud_msg_icons -- run add_msg_icon.py first' % name)
    return names.index(name)


def message_index(lines, write):
    """Index of an appended pickup-message PAIR (Halo 1 reads index and index + 1),
    appending it once. Appending never moves an entry (h1_port_messages.py)."""
    t = ustr_def.build(filepath=path(MESSAGES, '.unicode_string_list'))
    strs = t.data.tagdata.strings.STEPTREE
    texts = [s.data for s in strs]
    for i in range(STOCK_MESSAGES, len(texts) - 1):     # never a stock line: MCC overrides those
        if texts[i] == lines[0] and texts[i + 1] == lines[1]:
            return i
    i = len(strs)
    for line in lines:
        strs.append()
        strs[-1].data = line
    save(t, path(MESSAGES, '.unicode_string_list'), write)
    return i


def make_hud(w, key, write):
    """The weapon's own HUD interface, from the donor named in its 'hud' entry."""
    h = w['hud']
    t = wphi_def.build(filepath=path(h['donor'], '.weapon_hud_interface'))
    d = t.data.tagdata
    if 'meter' in h:                     # fuel rod: magazine readout in the RL's frame
        import ammo_meter
        import h1_rocket_meter
        mag = 4
        ro = wphi_def.build(filepath=path(h['readout'], '.weapon_hud_interface')).data.tagdata
        d.child_hud.filepath = ro.child_hud.filepath              # master plasma -> rounds
        for name, field, suffix in (('static_elements', 'interface_bitmap', '_alphas'),
                                    ('meter_elements', 'meter_bitmap', '_meters')):
            dst = getattr(d, name).STEPTREE
            dst[:] = []
            for e in getattr(ro, name).STEPTREE:
                if e.state_attached_to.enum_name != 'loaded_ammo':
                    continue
                e = copy.deepcopy(e)
                getattr(e, field).filepath = h['meter'] + suffix
                e.sequence_index = h1_rocket_meter.SEQ
                if name == 'meter_elements':             # ammo_meter.plan: see saw_weapon
                    e.alpha_multiplier = ammo_meter.plan(mag)[3]
                    e.alpha_bias = 1
                    e.value_scale = 0
                dst.append(e)
        fc = d.flash_cutoffs
        fc.heat_cutoff = 0
        fc.loaded_ammo_cutoff = 1
        fc.total_ammo_cutoff = 4
        if write:
            h1_rocket_meter.build(mag, h['meter'], h.get('art', 'rockets'))
    if 'reticle' in h:                   # a Halo 3 reticle, into Halo 1's sheet
        import h1_add_reticle
        seq = h1_add_reticle.add(*h['reticle']) if write else -1
        for c in d.crosshairs.STEPTREE:
            if c.crosshair_type.enum_name == 'aim':
                for o in c.crosshair_overlays.STEPTREE:
                    o.sequence_index = seq
    d.messaging_information.sequence_index = icon_sequence(w['icon'])
    save(t, path(h['out'], '.weapon_hud_interface'), write)
    return h['out']


def make_lunge(w, a, write):
    """The sword's fire button: a magazine and trigger in the plasma pistol's shape, firing
    an invisible short strike with the sword's own melee damage, and shoving the wielder."""
    L = w['lunge']
    tmpl = weap_def.build(filepath=path(L['template'], '.weapon')).data.tagdata.weap_attrs
    # the strike: the AR bullet with everything visible or audible taken off
    pt = proj_def.build(filepath=path(L['strike_from'], '.projectile'))
    pd = pt.data.tagdata
    pd.obje_attrs.attachments.STEPTREE[:] = []
    ph = pd.proj_attrs.physics
    ph.initial_velocity = ph.final_velocity = L['velocity']
    ph.air_gravity_scale = 0.0
    ph.flyby_sound.filepath = ''
    if write:
        shutil.copy2(path(a.melee.player_damage.filepath, '.damage_effect'),
                     path(L['strike_damage'], '.damage_effect'))
    ph.impact_damage.filepath = L['strike_damage']                # = the melee's values
    pd.proj_attrs.detonation.maximum_range = L['range']
    hit = ''
    if L.get('hit_effect') and w.get('hit_sound'):
        from reclaimer.hek.defs.effe import effe_def
        src, hit = L['hit_effect']
        et = effe_def.build(filepath=path(src, '.effect'))
        parts = et.data.tagdata.events.STEPTREE[0].parts.STEPTREE
        for i in reversed(range(len(parts))):
            if parts[i].type.tag_class.enum_name != 'sound':
                parts.pop(i)
        if len(parts) != 1:
            raise SystemExit('%s: want exactly one sound part' % src)
        parts[0].type.filepath = w['hit_sound']
        save(et, path(hit, '.effect'), write)
    for m in pd.proj_attrs.material_responses.STEPTREE:     # no bullet holes; the sword's hit
        m.effect.filepath = hit
        m.potential_response.effect.filepath = ''
        m.detonation_effect.filepath = ''
    save(pt, path(L['strike'], '.projectile'), write)
    # the shove: a zero-damage firing effect whose instantaneous acceleration is the lunge
    jt = jpt__def.build(filepath=path(L['push_from'], '.damage_effect'))
    dm = jt.data.tagdata.damage
    dm.instantaneous_acceleration = L['acceleration']
    dm.damage_lower_bound = L['push_damage']
    dm.damage_upper_bound[0] = dm.damage_upper_bound[1] = L['push_damage']
    mods = jt.data.tagdata.damage_modifiers
    for k in mods.desc['NAME_MAP']:
        setattr(mods, k, 1.0)
    save(jt, path(L['push'], '.damage_effect'), write)
    mags = a.magazines.STEPTREE
    mags[:] = []
    mags.append(copy.deepcopy(tmpl.magazines.STEPTREE[0]))        # all zero: no ammo
    trs = a.triggers.STEPTREE
    trs[:] = []
    trs.append(copy.deepcopy(tmpl.triggers.STEPTREE[0]))
    tr = trs[0]
    tr.flags.data = 0
    tr.flags.does_not_repeat_automatically = True
    tr.firing.rounds_per_second.__setitem__(0, L['rate'])
    tr.firing.rounds_per_second.__setitem__(1, L['rate'])
    tr.firing.error.__setitem__(0, 0.0)
    tr.firing.error.__setitem__(1, 0.0)
    tr.charging.charging_time = 0.0
    tr.charging.charge_hold_time = 0.0
    tr.charging.overcharged_action.set_to('none')
    tr.charging.charged_illumination = 0.0
    # a sword swing is not a gunshot: the plasma pistol template fires `loud`, which every
    # AI in earshot reacts to
    tr.firing.firing_noise.set_to('silent')
    tr.projectile.projectile.filepath = L['strike']
    tr.projectile.error_angle.__setitem__(1, 0.0)
    tr.misc.heat_generated_per_round = 0.0
    tr.misc.age_generated_per_round = L['energy']
    tr.misc.illumination_recovery_time = 0.0
    for fe in tr.firing_effects.STEPTREE:
        fe.firing_effect.filepath = ''
        fe.misfire_effect.filepath = ''
        fe.empty_effect.filepath = ''
        fe.firing_damage.filepath = L['push']
        fe.misfire_damage.filepath = ''
        fe.empty_damage.filepath = ''
    a.flags.cannot_fire_at_maximum_age = True
    a.age.misfire_start = 0.0
    a.age.misfire_chance = 0.0


def own_projectile(a, o, write):
    """Clone projectile -> detonation effect -> damage effect and repoint the chain, so the
    weapon fires tags nothing else names (verify the BUILT map: port_refs_audit idea)."""
    from reclaimer.hek.defs.effe import effe_def
    (p_src, p_own), (e_src, e_own), (j_src, j_own) = o['projectile'], o['effect'], o['damage']
    if write:
        shutil.copy2(path(j_src, '.damage_effect'), path(j_own, '.damage_effect'))
    et = effe_def.build(filepath=path(e_src, '.effect'))
    n = 0
    for ev in et.data.tagdata.events.STEPTREE:
        for part in ev.parts.STEPTREE:
            if part.type.filepath.lower() == j_src.lower():
                part.type.filepath = j_own
                n += 1
    if n != 1:
        raise SystemExit('%s: %d parts name %s' % (e_src, n, j_src))
    save(et, path(e_own, '.effect'), write)
    pt = proj_def.build(filepath=path(p_src, '.projectile'))
    det = pt.data.tagdata.proj_attrs.detonation
    if det.effect.filepath.lower() != e_src.lower():
        raise SystemExit('%s detonates %s, not %s' % (p_src, det.effect.filepath, e_src))
    det.effect.filepath = e_own
    save(pt, path(p_own, '.projectile'), write)
    for tr in a.triggers.STEPTREE:
        if tr.projectile.projectile.filepath.lower() == p_src.lower():
            tr.projectile.projectile.filepath = p_own


def own_beam(a, b, write):
    """The weapon's own projectile (a copy of `projectile[0]`, range set) and its own
    impact damage (a copy of `damage[0]`, damage + instantaneous acceleration set)."""
    (p_src, p_own), (j_src, j_own) = b['projectile'], b['damage']
    jt = jpt__def.build(filepath=path(j_src, '.damage_effect'))
    dm = jt.data.tagdata.damage
    dm.damage_lower_bound = b['dmg']
    dm.damage_upper_bound[0] = dm.damage_upper_bound[1] = b['dmg']
    dm.instantaneous_acceleration = b['acceleration']
    save(jt, path(j_own, '.damage_effect'), write)
    pt = proj_def.build(filepath=path(p_src, '.projectile'))
    pd = pt.data.tagdata.proj_attrs
    pd.physics.impact_damage.filepath = j_own
    pd.detonation.maximum_range = b['range']
    save(pt, path(p_own, '.projectile'), write)
    for tr in a.triggers.STEPTREE:
        tr.projectile.projectile.filepath = p_own


def add_hum(d, h, write):
    """An always-on looping sound on the weapon: a sound_looping cloned from `like`,
    its loop track naming our sound, attached unscaled at `marker`."""
    from reclaimer.hek.defs.lsnd import lsnd_def
    lt = lsnd_def.build(filepath=path(h['like'], '.sound_looping'))
    ld = lt.data.tagdata
    tr = ld.tracks.STEPTREE[0]
    tr.start.filepath = ''
    tr.loop.filepath = h['loop']
    tr.end.filepath = ''
    while len(ld.tracks.STEPTREE) > 1:
        ld.tracks.STEPTREE.pop()
    save(lt, path(h['tag'], '.sound_looping'), write)
    atts = d.obje_attrs.attachments.STEPTREE
    if any(x.type.filepath == h['tag'] for x in atts):
        return
    atts.append(copy.deepcopy(atts[0]))
    x = atts[len(atts) - 1]
    x.type.tag_class.set_to('sound_looping')
    x.type.filepath = h['tag']
    x.marker = h['marker']
    x.primary_scale.set_to('none')
    x.secondary_scale.set_to('none')
    x.change_color.set_to('none')


def rewire(d, r):
    """Re-lay a template's export inputs and object functions: `inputs` A..D, functions
    {new index: (source, scale by, usage)} -- source a template function index, or
    (weapon tag, index) to copy another weapon's -- and attachment scales renamed."""
    o = d.obje_attrs
    old = [copy.deepcopy(f) for f in o.functions.STEPTREE]
    for slot, inp in zip('ABCD', r['inputs']):
        getattr(d.weap_attrs, slot + '_in').set_to(inp)
    for i, (src, by, usage, *extra) in r['functions'].items():
        if isinstance(src, tuple):
            other = weap_def.build(filepath=path(src[0], '.weapon')).data.tagdata
            fn = copy.deepcopy(other.obje_attrs.functions.STEPTREE[src[1]])
        else:
            fn = copy.deepcopy(old[src])
        fn.scale_function_by.set_to(by)
        fn.usage = usage
        for k, v in (extra[0] if extra else {}).items():
            if k == 'turn_off_with':
                fn.turn_off_with = v
            else:
                setattr(fn.flags, k, v)
        o.functions.STEPTREE[i] = fn
    atts = o.attachments.STEPTREE
    for i in range(len(atts) - 1, -1, -1):
        sc = atts[i].primary_scale.enum_name
        if sc in r.get('drop_attachments_on', ()):
            atts.pop(i)
        elif sc in r.get('attach_scale', {}):
            atts[i].primary_scale.set_to(r['attach_scale'][sc])


def add_fire_loop(d, f, write):
    """A start/loop/end sound_looping (cloned from `like`) at `marker`, its primary scale
    the weapon's existing object function output `scale` (it plays while that is up)."""
    from reclaimer.hek.defs.lsnd import lsnd_def
    lt = lsnd_def.build(filepath=path(f['like'], '.sound_looping'))
    ld = lt.data.tagdata
    tr = ld.tracks.STEPTREE[0]
    tr.start.filepath, tr.loop.filepath, tr.end.filepath = f['start'], f['loop'], f['end']
    tr.gain = 1.0                 # the flamethrower's fire_ft says 0.0; the charging loop
                                  # that played in tests 2-3 says 1.0
    while len(ld.tracks.STEPTREE) > 1:
        ld.tracks.STEPTREE.pop()
    save(lt, path(f['tag'], '.sound_looping'), write)
    atts = d.obje_attrs.attachments.STEPTREE
    atts.append(copy.deepcopy(atts[0]))
    x = atts[len(atts) - 1]
    x.type.tag_class.set_to('sound_looping')
    x.type.filepath = f['tag']
    x.marker = f['marker']
    x.primary_scale.set_to(f['scale'])
    x.secondary_scale.set_to('none')
    x.change_color.set_to('none')


def add_charge_loop(d, c):
    """A looping sound attachment whose scale follows the weapon's charge."""
    o = d.obje_attrs
    funcs, atts = o.functions.STEPTREE, o.attachments.STEPTREE
    if any(a.type.filepath == c['sound'] for a in atts):
        return
    if len(funcs) >= 4:
        raise SystemExit('no free object function for the charge loop')
    tmpl = weap_def.build(filepath=path(r'weapons\plasma pistol\plasma pistol', '.weapon'))
    td = tmpl.data.tagdata.obje_attrs
    funcs.append(copy.deepcopy(td.functions.STEPTREE[3]))      # 'one' scaled by an input
    f = funcs[len(funcs) - 1]
    f.scale_function_by.set_to(c['input'])
    out = 'ABCD'[len(funcs) - 1] + '_out'
    loop = [a for a in td.attachments.STEPTREE if a.type.filepath == c['sound']][0]
    for ref in [c['sound']] + c.get('glow', []):
        atts.append(copy.deepcopy(loop))
        a = atts[len(atts) - 1]
        if ref != c['sound']:
            ext = 'light_volume' if os.path.exists(path(ref, '.light_volume')) else 'light'
            a.type.tag_class.set_to(ext)
        a.type.filepath = ref
        a.marker = c['marker']
        a.primary_scale.set_to(out)


def edit_weapon(key, write):
    w = WEAPONS[key]
    p = path(w['weapon'], '.weapon')
    if w.get('template'):                    # a NEW weapon: always rebuilt from its template
        src = path(w['template'], '.weapon')
    else:
        src = p + BACKUP if os.path.exists(p + BACKUP) else p
    t = weap_def.build(filepath=src)
    d = t.data.tagdata
    a = d.weap_attrs
    print('%s: flags before %s' % (key, [f for f in a.flags.NAME_MAP if a.flags.get(f)]))
    a.flags.detonates_when_dropped = False
    a.interface.first_person_model.filepath = w['fp_model']
    a.interface.first_person_animations.filepath = w['fp_anims']
    if 'melee' in w:
        donor, own = w['melee']
        if write:
            backup(path(own, '.damage_effect'))
            shutil.copy2(path(donor, '.damage_effect'), path(own, '.damage_effect'))
        a.melee.player_damage.filepath = own
        a.melee.player_response.filepath = w['melee_response']
    if 'messages' in w:
        d.item_attrs.message_index = message_index(w['messages'], write)
    if 'hud' in w:
        a.interface.hud_interface.filepath = make_hud(w, key, write)
    if 'lunge' in w:
        make_lunge(w, a, write)
    if 'own_projectile' in w:
        own_projectile(a, w['own_projectile'], write)
    if w.get('world_model'):
        d.obje_attrs.model.filepath = w['world_model']
    if w.get('label'):
        a.label = w['label']
    if 'beam' in w:
        own_beam(a, w['beam'], write)
    for k, v in w.get('trigger', {}).items():
        for tr in a.triggers.STEPTREE:
            if k == 'rounds_per_second':
                lo, hi = v if isinstance(v, tuple) else (v, v)
                tr.firing.rounds_per_second[0], tr.firing.rounds_per_second[1] = lo, hi
            elif k == 'error_angle':
                tr.projectile.error_angle[0], tr.projectile.error_angle[1] = v
            elif k == 'first_person_offset':
                o = tr.projectile.first_person_offset
                o.x, o.y, o.z = v
            else:                            # whichever trigger struct holds the field
                sub = [s for s in tr if hasattr(s, 'NAME_MAP') and k in s.NAME_MAP]
                if not sub:
                    raise SystemExit('trigger field %s not found' % k)
                setattr(sub[0], k, v)
    for k, v in w.get('heat', {}).items():
        setattr(a.heat, k, v)
    if 'overheated_effect' in w:
        from reclaimer.hek.defs.effe import effe_def
        O = w['overheated_effect']
        et = effe_def.build(filepath=path(O['from'], '.effect'))
        for loc in et.data.tagdata.locations.STEPTREE:
            loc.marker_name = O['locations'].get(loc.marker_name, loc.marker_name)
        save(et, path(O['out'], '.effect'), write)
        a.heat.overheated.filepath = O['out']
    if 'misfire_effect' in w:                 # same marker fix for the misfire burst
        from reclaimer.hek.defs.effe import effe_def
        M = w['misfire_effect']
        et = effe_def.build(filepath=path(M['from'], '.effect'))
        for loc in et.data.tagdata.locations.STEPTREE:
            loc.marker_name = M['locations'].get(loc.marker_name, loc.marker_name)
        save(et, path(M['out'], '.effect'), write)
        for tr in a.triggers.STEPTREE:
            for fe in tr.firing_effects.STEPTREE:
                if fe.misfire_effect.filepath == M['from']:
                    fe.misfire_effect.filepath = M['out']
    if 'rewire' in w:
        rewire(d, w['rewire'])
    if 'change_color_a' in w:
        cc = d.obje_attrs.change_colors.STEPTREE[0]
        cc.flags.blend_in_hsv = False
        for b, rgb in zip((cc.color_lower_bound, cc.color_upper_bound), w['change_color_a']):
            b.r, b.g, b.b = rgb
    if 'own_light' in w:
        from reclaimer.hek.defs.ligh import ligh_def
        L = w['own_light']
        lt = ligh_def.build(filepath=path(L['shape'], '.light'))
        look = ligh_def.build(filepath=path(L['look'], '.light')).data.tagdata
        lt.data.tagdata.color = look.color
        lt.data.tagdata.lens_flare.filepath = look.lens_flare.filepath
        if 'radius' in L:
            lt.data.tagdata.shape.radius = L['radius']
        for bound in (lt.data.tagdata.color.color_lower_bound,
                      lt.data.tagdata.color.color_upper_bound):
            if 'argb' in L:
                bound.a, bound.r, bound.g, bound.b = L['argb']
        if 'duration' in L:
            lt.data.tagdata.effect_parameters.duration = L['duration']
        if L.get('no_flare'):
            lt.data.tagdata.lens_flare.filepath = ''
        if 'flare' in L:
            from reclaimer.hek.defs.lens import lens_def
            fl = L['flare']
            ft = lens_def.build(filepath=path(fl['from'], '.lens_flare'))
            for r in ft.data.tagdata.reflections.STEPTREE:
                r.radius[0] = r.radius[1] = fl['radius']
                r.brightness_scaled_by.set_to('none')
            save(ft, path(fl['out'], '.lens_flare'), write)
            lt.data.tagdata.lens_flare.filepath = fl['out']
        save(lt, path(L['out'], '.light'), write)
    if 'fire_effect' in w:
        from reclaimer.hek.defs.effe import effe_def
        F = w['fire_effect']
        et = effe_def.build(filepath=path(F['from'], '.effect'))
        evs = et.data.tagdata.events.STEPTREE
        while len(evs) > 1:                       # one event
            evs.pop()
        ev = evs[0]
        keep = F.get('keep_particles')            # particle tags whose path holds this
        pts = ev.particles.STEPTREE
        for i in range(len(pts) - 1, -1, -1):
            if not keep or not pts[i].particle_type.filepath.endswith(keep):
                pts.pop(i)
        for x in pts:
            if 'tint' in F:
                x.flags.tint_as_hsv = False
                for b in (x.tint_lower_bound, x.tint_upper_bound):
                    b.a, b.r, b.g, b.b = F['tint']
            if 'particle_offset' in F:
                o = x.relative_offset
                o.i, o.j, o.k = F['particle_offset']
        parts = ev.parts.STEPTREE
        if F['sound']:
            parts[0].type.filepath = F['sound']
            parts.append(copy.deepcopy(parts[0]))
        lp = parts[len(parts) - 1]
        lp.type.tag_class.set_to('light')
        lp.type.filepath = F['light']
        save(et, path(F['out'], '.effect'), write)
        for tr in a.triggers.STEPTREE:
            for fe in tr.firing_effects.STEPTREE:
                fe.firing_effect.filepath = F['out']
    if 'charge_loop' in w:
        add_charge_loop(d, w['charge_loop'])
    if 'hum' in w:
        add_hum(d, w['hum'], write)
    if 'fire_loop' in w:
        add_fire_loop(d, w['fire_loop'], write)
    for x in d.obje_attrs.attachments.STEPTREE:
        x.marker = w.get('attach_markers', {}).get(x.marker, x.marker)
        x.type.filepath = w.get('attach_swap', {}).get(x.type.filepath, x.type.filepath)
    if 'hit_sound' in w:
        jp = path(a.melee.player_damage.filepath, '.damage_effect')
        jt = jpt__def.build(filepath=jp + BACKUP if os.path.exists(jp + BACKUP) else jp)
        jt.data.tagdata.sound.filepath = w['hit_sound']
        save(jt, jp, write)
    if 'rounds_per_shot' in w:
        for tr in a.triggers.STEPTREE:
            tr.firing.rounds_per_shot = w['rounds_per_shot']
    for k, v in w.get('aiming', {}).items():
        setattr(a.aiming, k, math.radians(v) if k.endswith('_angle') else v)
    print('   -> flags %s | fp %s | anims %s | hud %s | melee %s | message %d | triggers %d'
          % ([f for f in a.flags.NAME_MAP if a.flags.get(f)],
             a.interface.first_person_model.filepath,
             a.interface.first_person_animations.filepath,
             a.interface.hud_interface.filepath, a.melee.player_damage.filepath,
             d.item_attrs.message_index, len(a.triggers.STEPTREE)))
    t.filepath = p
    save(t, p, write)


def edit_palettes(key, write):
    """The weapon appended to each `palette_levels` scenario's weapons palette."""
    from reclaimer.hek.defs.scnr import scnr_def
    w = WEAPONS[key]
    for lvl in w.get('palette_levels', []):
        p = path('levels\\%s\\%s' % (lvl, lvl), '.scenario')
        t = scnr_def.build(filepath=p)
        pal = t.data.tagdata.weapons_palette.STEPTREE
        names = [e.name.filepath.lower() for e in pal]
        if w['weapon'].lower() in names:
            idx = names.index(w['weapon'].lower())
        else:
            pal.append()
            pal[-1].name.filepath = w['weapon']
            idx = len(pal) - 1
        # a palette entry ALONE is not built in (a10 test, 2026-10-06): tool keeps only
        # what a placement uses. Like the SAW: ONE placement, `not placed: automatically`
        # (never spawns, only makes the tag resident for the enhancer's own placements),
        # a copy of the SAW's
        places = t.data.tagdata.weapons.STEPTREE
        if any(x.type == idx for x in places):
            print('   %s: palette #%d + placement already there' % (lvl, idx))
            continue
        saw = names.index(r'weapons\saw\saw')
        src = [x for x in places if x.type == saw and x.not_placed.automatically]
        if not src:
            raise SystemExit('%s: no resident-only SAW placement to copy' % lvl)
        places.append(copy.deepcopy(src[0]))
        x = places[len(places) - 1]
        x.type = idx
        x.rounds_left = x.rounds_loaded = 0
        print('   %s: palette #%d + resident-only placement (the SAW\'s, at %s)'
              % (lvl, idx, tuple(round(c, 1) for c in x.position)))
        t.filepath = p
        save(t, p, write)


def edit_death_drop(key, write):
    """The weapon as a part of event 0 of each `death_drop` effect (an enemy that has no
    weapon to drop leaves one when it dies). The part copies the event's first part
    (location, velocity, cone), its type the weapon."""
    from reclaimer.hek.defs.effe import effe_def
    w = WEAPONS[key]
    for rel in w.get('death_drop', []):
        p = path(rel, '.effect')
        src = p + BACKUP if os.path.exists(p + BACKUP) else p
        t = effe_def.build(filepath=src)
        parts = t.data.tagdata.events.STEPTREE[0].parts.STEPTREE
        parts.append(copy.deepcopy(parts[0]))
        x = parts[len(parts) - 1]
        x.type.tag_class.set_to('weapon')
        x.type.filepath = w['weapon']
        x.angular_velocity_bounds[0] = x.angular_velocity_bounds[1] = 0.0
        print('   %s: + weapon part %s (%d parts)' % (rel, w['weapon'], len(parts)))
        t.filepath = p
        save(t, p, write)


def edit_drops(key, write):
    """What the enemies that carry it drop: (loaded fraction range, reserve rounds range)."""
    for rel, ((l0, l1), (a0, a1)) in WEAPONS[key].get('drops', {}).items():
        p = path(rel, '.actor_variant')
        src = p + BACKUP if os.path.exists(p + BACKUP) else p
        t = actv_def.build(filepath=src)
        it = t.data.tagdata.items
        print('   %s: drop loaded %s..%s ammo %s..%s -> %s..%s / %s..%s'
              % (rel, it.drop_weapon_loaded[0], it.drop_weapon_loaded[1],
                 it.drop_weapon_ammo[0], it.drop_weapon_ammo[1], l0, l1, a0, a1))
        it.drop_weapon_loaded[0], it.drop_weapon_loaded[1] = l0, l1
        it.drop_weapon_ammo[0], it.drop_weapon_ammo[1] = a0, a1
        t.filepath = p
        save(t, p, write)


def edit_fp_anims(key, write):
    """Melee key frames and sounds on the compiled FP animation tag. Recompiling it with
    `tool animations` resets both, so run this after every h1_fp_retarget --write."""
    w = WEAPONS[key]
    p = path(w['fp_anims'], '.model_animations')
    t = antr_def.build(filepath=p)
    d = t.data.tagdata
    refs = d.sound_references.STEPTREE
    have = [r.sound.filepath for r in refs]
    for a in d.animations.STEPTREE:
        if a.name in w['keys']:
            a.key_frame_index = w['keys'][a.name]
        snd = w['sounds'].get(a.name)
        if snd:
            if snd not in have:
                refs.append()
                refs[-1].sound.filepath = snd
                have.append(snd)
            a.sound = have.index(snd)
            a.sound_frame_index = w.get('sound_frames', {}).get(a.name, 0)
        print('   %-30s key %2d sound %s' % (a.name, a.key_frame_index,
                                              have[a.sound] if a.sound >= 0 else '-'))
    save(t, p, write)


def teach_cyborg(write):
    """Append `fr` (from `pc`) and `fb` (from `b`) wherever the donor label exists."""
    p = path(CYBORG, '.model_animations')
    src = p + BACKUP if os.path.exists(p + BACKUP) else p
    t = antr_def.build(filepath=src)
    added = []
    for u in t.data.tagdata.units.STEPTREE:
        for wc in u.weapons.STEPTREE:
            wt = wc.weapon_types.STEPTREE
            labels = [x.label for x in wt]
            for w in WEAPONS.values():
                new, donor = w['teach']
                if donor in labels and new not in labels:
                    e = copy.deepcopy(wt[labels.index(donor)])
                    e.label = new
                    wt.append(e)
                    labels.append(new)
                    added.append('%s/%s %s<-%s' % (u.label, wc.name, new, donor))
    print('cyborg: %d label(s) taught: %s' % (len(added), ', '.join(added)))
    t.filepath = p
    save(t, p, write)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    for key in WEAPONS:
        edit_weapon(key, a.write)
        edit_drops(key, a.write)
        edit_death_drop(key, a.write)
        edit_palettes(key, a.write)
        if os.path.exists(path(WEAPONS[key]['fp_anims'], '.model_animations')):
            edit_fp_anims(key, a.write)
        else:
            print('   (no FP animation tag yet: python h1_fp_retarget.py %s --write, then '
                  'tool animations)' % key)
    teach_cyborg(a.write)
    if not a.write:
        print('\n(dry run -- --write to save)')


if __name__ == '__main__':
    main()
