r"""Plasma Launcher (Halo Reach -> Halo 1, wave B6). Yardstick: the PLASMA GRENADE (step 4a, user
2026-10-13); the weapon is a copy of the Halo 1 PLASMA PISTOL (its charged trigger PAIR, heat and
battery) firing plasma bolts built on the plasma grenade's projectile and explosion. What is new: a
multi-bolt CHARGE (Reach: 1..4 bolts) as the plasma pistol's pair -- a tap = one bolt, a full charge
= a 4-bolt SPEW --, Reach's LOCK-ON as the needler's homing on the charged volley, and a bolt that
STICKS to everything (the needle's attach) with a stuck detonation stronger than the free one.
Reach plumbing: grenade_launcher.py / concussion_rifle.py; the charged pair: grenade_launcher.py."""
import math

from ._common import B, reserved, row  # noqa: F401

R = 'reach:'                                       # an HREK path (reach_tags)
RW = r'objects\weapons\support_high\plasma_launcher'
RFP = r'objects\characters\spartans\fp\weapons\support_high\fp_plasma_launcher\fp_plasma_launcher'
PL = 'weapons\\plasma launcher\\'
SND = 'sound\\weapons\\plasma_launcher_port\\'
PP = 'weapons\\plasma pistol\\'
PG = 'weapons\\plasma grenade\\'
RL = 'weapons\\rocket launcher\\'
RS = 'data\\sound\\weapons\\'                      # Reach's bank folders
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']
TEX = R + RW + r'\bitmaps' + B
HOLO = TEX + 'plasma_launcher_holo.bitmap'
STATIC = r'weapons\needler\shaders\needler luminous'
GAUGE = r'weapons\plasma rifle\fp\shaders\gauge'
# Reach's bolt BLUE (reach_function_data, 2026-10-13): the light volume's profile colour 44 / 117 /
# 255, the projectile light 42 / 83 / 255 (intensity 5); its detonation = plasma_blue_large
BLUE = (44 / 255.0, 117 / 255.0, 1.0)
BLUE_LIGHT = (42 / 255.0, 83 / 255.0, 1.0)
# the Concussion Rifle's indicator blue (its user screenshot ~70 / 150 / 255; the same holo bitmap)
HOLO_BLUE = (0.3, 0.6, 1.0)
# the crosshair quadrant's offset (chud units): half the #31 sprite (47 x 44 px) x Reach's 1.2 x 1.25
# x its widget ORIGIN 0.945 -- the four copies OVERLAP 5.5 % (boot 2, user: 'the horizontal lines
# look mirrored and facing away' -- edge to edge, the halves' half-transparent edge rows left a seam)
# BOOT 3 (user): 'still a gap' -- h1_add_reticle applies a layer's `stretch` to its offset too:
# the offset is in SPRITE px (the 1.2 x 1.25 had been applied twice)
RQ = (47 / 2.0 * 0.945, 44 / 2.0 * 0.945)
# the FULLY CHARGED cue (boot 2, user: 'another fully charged identification would be good'):
# Reach's rear display turns RED-ORANGE at full charge (the user's fully-charged screenshot) ->
# the holo ring + screen slide blue -> red-orange at the top of the charge (D out = primary charged)
# BOOT 6 (user: 'the lights turn on later than 3 s'; h1_weapon_state_probe): Halo 1's exported
# PRIMARY CHARGED runs over the charge AND the hold (5 s: 0.50 at 3.0 s, 1.0 at the auto-discharge);
# a second word (+0xE4) reaches 1.0 at 3.0 s but is not an export -> the switch at 0.50..0.52
# BOOT 7 (user): 'the orange lights come online too early' (~2.5 s; boot 6's 0.97 came LATE, ~4.3 s):
# Halo 1 samples the ramp ~0.10 further along than the charge value (the lit shapes' own UVs x the
# 0.001 uv scale) -> the switch at 0.50 + 0.10
# BOOT 8 (user): 'still early, set it back 0.3 s' -> +0.06 on the 5 s scale
# BOOT 9 (user): 'push the charge lights back another 0.15 s' -> +0.03
# BOOT 10 (user): 'another 0.15 s' -> +0.03 (pips confirmed perfect)
# BOOT 11 (user): 'still early' -- the switch value moved +0.22 since boot 7 (~1.1 s on the 5 s
# scale) but the lights only ~0.3-0.4 s: Halo 1's sampling of this tiny ramp is not 'value + 0.1'.
# The ramp is no longer read against the charge: object function 0 (A out, the template's inverted
# age for the pistol's on-gun display -- unused here) = primary charged clipped and normalised to
# 0.495..0.505 = a 0 / 1 STEP at 3.0 s (the probe: 0.50 at 3.0 s); the ramp just blue below 0.3,
# red above 0.7 of that step
CHARGE_RAMP = [(0.0, HOLO_BLUE), (0.3, HOLO_BLUE), (0.7, (1.0, 0.32, 0.12)), (1.0, (1.0, 0.32, 0.12))]
# Halo 1 material indices (h1_role_compare.H1_MATERIALS order)
JACKAL_SHIELD, WATER = 16, 28
FORCE_FIELDS = [10, 18, 26, 32]      # force field, engineer force field, monitor, hunter shield
ATTACH = [i for i in range(33) if i not in [JACKAL_SHIELD, WATER] + FORCE_FIELDS]

# THE BOLT (both triggers; the volley's adds the guidance) on a copy of Halo 1's PLASMA GRENADE
# projectile (the yardstick: sticks, its fuse runs from rest, an attached damage slot). Reach's
# damage: impact 2 (`collision`, accel 0.1) on a copy of the grenade explosion's table with no
# radius; the free burst 17.5..175 over 0.6 -> 1.8 = the grenade's own explosion effect around an
# own damage copy (core 0.4 x 0.48/0.432, accel 4 x 1.75/2: 4b list 2, Reach PL / Reach PG onto the
# H1 PG); STUCK: Reach's 300 -- Halo 1 deals attached damage at the STICK (boot 1), so none: the
# burst alone. Flight: Reach's own 11 -> 7 wu/s (Halo 1 changes speed over the whole range:
# slower than Reach's 1..20 wu acceleration range -- the probe), gravity 0.1, water 0.5, range 180;
# fuse 'when at rest' 0.25..2.5 s, arming 1 s (what Halo 1's arming does to a bolt stuck early:
# the probe), danger radius 2. Responses: Reach's table -- attach everywhere (the needle's DEFAULT
# 'attach'; the grenade's own 'attach' is a potential response with empty conditions), the Jackal
# shield and the force fields reflect, water passes
BOLT = {
    'damage': (PG + 'explosion', PL + 'impact'),
    'dmg': 2.0, 'acceleration': 0.1,
    'fields': {'radius': (0.0, 0.0)},
    'explosion': {'effect': (PG + 'effects' + B + 'explosion', PL + 'effects' + B + 'bolt explosion'),
                  'part': PG + 'explosion',
                  'out_dir': PL + 'effects' + B,
                  'damage': (PG + 'explosion', PL + 'explosion'),
                  'lower': 17.5, 'upper': (175.0, 175.0), 'radius': (0.6, 1.8),
                  'fields': {'damage.aoe_core_radius': 0.4 * 0.48 / 0.432,
                             'damage.instantaneous_acceleration': 4.0 * 1.75 / 2.0},
                  'swaps': {B.join(['sound', 'sfx', 'weapons', 'plasma grenade', 'plasmagrenexpl']): SND + 'pl_explode'}},
    'velocity': (11.0, 7.0), 'range': 180.0,
    'model': PL + 'bolt' + B + 'bolt',
    'proj_fields': {'proj_attrs.physics.air_gravity_scale': 0.1,
                    'proj_attrs.physics.water_gravity_scale': 0.5,
                    'proj_attrs.detonation.arming_time': 1.0,
                    'proj_attrs.detonation.timer': (0.25, 2.5),
                    'proj_attrs.detonation_timer_starts': 'when_at_rest',
                    'proj_attrs.detonation.danger_radius': 2.0,
                    'proj_attrs.detonation.minimum_velocity': 0.0,
                    # Reach 0,0 = unset -> the range (the GL's / Brute Shot's)
                    'proj_attrs.physics.air_damage_range': (0.0, 180.0),
                    'proj_attrs.physics.guided_angular_velocity': 0.0,
                    # BOOT 1 (user): 'the impact kills targets a lot of times, before the explosion
                    # even happens -- shift all damage to the explosion': Halo 1 deals the ATTACHED
                    # damage when the bolt sticks, not when it bursts -> none (the grenade's own
                    # `attached` is cleared too); the stuck bonus (Reach 300 against 175) is lost
                    'proj_attrs.physics.attached_detonation_damage.filepath': '',
                    # 4b list 3: the grenade's 0 (a zero on one side) -> Reach's own 0.02
                    'proj_attrs.collision_radius': 0.02,
                    'proj_attrs.flags.oriented_along_velocity': True,
                    # the grenade's 'detonation max time if attached' (a stuck grenade waits the
                    # whole timer): Reach has none -> off, the fuse picks in 0.25..2.5 s
                    'proj_attrs.flags.detonation_max_time_if_attached': False},
    'default_responses': {'attach': ATTACH, 'reflect': [JACKAL_SHIELD] + FORCE_FIELDS,
                          'overpenetrate': [WATER]},
    # the grenade's per-material DETONATION effects would replace the bolt's own burst (the GL's
    # trap: a frag copy's dirt sound / empty stone effect)
    'clear_detonation_effects': True,
    # the grenade's blue light kept, its armed-light effect dropped (BOOT 1, user: 'our bolt in
    # flight is pure white'; Reach's: a white core in a BLUE halo -- its light volume 44 / 117 /
    # 255); its sound loop -> Reach's (hum, appended); a blue glow (light + flare) at the origin
    'keep_attachments': (1,),
    'glow': {'light': ('weapons' + B + 'fuel rod gun' + B + 'fuel rod exhaust', PL + 'bolt glow'),
             'flare': PL + 'bolt glow', 'rgb': BLUE, 'flare_radius': 0.15, 'marker': ''},
    'hum': {'like': B.join(['sound', 'sfx', 'weapons', 'plasma grenade', 'plasma_projectile']),
            'loop': SND + 'pl_projectile', 'tag': SND + 'pl_projectile', 'marker': ''},
    # the fuse start (stuck / at rest): the grenade's `detonation start` (electric bolts, flares)
    # without its dirt-hit sound (the beep plays at the impact, below)
    # BOOT 2 (user): 'I can't hear a beep still' (on the impact effects, -15) -> the beep HERE as
    # well: Halo 1 plays this effect when the fuse starts (the bolt at rest = stuck)
    'started_effect': {'from': PG + 'effects' + B + 'detonation start', 'out': PL + 'effects' + B + 'stuck',
                       'swaps': {B.join(['sound', 'sfx', 'impulse', 'impacts', 'dirthits']): SND + 'pl_stick'}},
    # the IMPACTS: every response plays the grenade's `bounce` (its sound the stock dirthits: a
    # BORROW in the hand check). Reach's impact.effect has no sound (a flash light) and its stick
    # beep plays when the bolt ATTACHES -- in Halo 1 the impact itself -> own copies of the bounce
    # effects with Reach's beep
    'impact_tint': {'match': (), 'rgb': None, 'out': PL + 'effects' + B + 'impact' + B,
                    'sounds': {B.join(['sound', 'sfx', 'impulse', 'impacts', 'dirthits']): SND + 'pl_stick'}},
}

PORT = reserved(
    order=24, wave='B6', name='Plasma Launcher', source='Halo Reach',
    messages=(81, 82), icon=44, reticle=33, label='pl', teach_from='rl',
    sound_dir='sound\\weapons\\plasma_launcher_port', weapon_dir='weapons\\plasma launcher',
    yardstick={
        # STEP 4a (user, 2026-10-13): h3_weapon_values.py --kit reach (plasma_launcher / flak_cannon
        # / rocket_launcher, FP graphs), reach_tag_fields.py of the weapon, the bolt, its damage
        # effects and Reach's plasma grenade, h1_role_compare.py plasma_launcher (new set, 516b93a).
        # REACH'S PLASMA LAUNCHER (HREK): trigger behaviour `charge`, charging time 3.0 s, fire
        # fractions 0.25 / 0.5 / 0.75 / 1 = one bolt more every 0.75 s up to 4 (user: 'need to hold
        # 0.75 s, not quite a tap, to fire one bolt'), 'can fire from partial charge', charged time
        # 2.0 s then overcharged action DISCHARGE, cancelled by a throw; 4.75 rounds/s (0.21 s
        # apart), fire recovery 0.2, error 0.3 / 0.8 (min 0); NO magazine: heat 0.4 a bolt,
        # overheated 1.0, loss 0.85/s (also overheated), recovery 0.1 -> a full volley overheats
        # (~1.2 after the 4th, a ~1.3 s vent); battery 0.0833333 a bolt (12 bolts, campaign the
        # same), 'cannot fire at maximum age'; zoom 1 level (3x), aim 3/30 6/30 (falloff 15,
        # deviation 3), melee strike_melee. TARGET TRACKING: bipeds, flying and ground vehicles,
        # acquire 0.5 s, grace 0.5, decay 0.5; 'AI cannot fire tracking projectiles'.
        # The BOLT plasma_launcher_grenade: 11 -> 7 wu/s over the acceleration range 1..20 wu, air
        # gravity 0.1 (water 0.5), range 180, collision radius 0.02, arming 1 s, danger radius 2,
        # TIMER 0.25..2.5 s 'when at rest' (stuck = at rest), GUIDED 45 deg/s (at rest too),
        # targeted leading 1, AI guidance x0.0001 (unguided); flags oriented along velocity,
        # dangerous when inactive. Responses: default_material ATTACH (chance 1: every surface and
        # unit), energy_shield_thick (Jackal) BOUNCE, invulnerable shields bounce, liquid
        # overpenetrate. Damage: impact 2 (`collision`, accel 0.1) + the free detonation 17.5..175
        # over 0.6 -> 1.8 (core 0.48, `explosion_small`, accel 1.75) = 177; STUCK: attached
        # detonation 30..300 over the same radius (accel 2, flaming death) INSTEAD of the free one.
        # Yardsticks (Reach): plasma grenade (the same family: explosion_small, sticky) 2 + 25..250
        # over 0.54 -> 1.8 (core 0.432, accel 2), stuck 35..350 (accel 2.5), timer 0.9-0.95 at
        # rest, arming 1.4, gravity 0.9; fuel rod (flak_cannon) 100 + 0..60 (explosion_large) = 160,
        # 0.4 s, 5 / 20 / 30, 15 -> 6.5, range 80, aim 4/25 8/25; rocket 200 + 240 = 440, 0.8 s,
        # 2 / 4 / 8, 8 -> 16, range 175, aim 5/60 10/25.
        # Halo 1: plasma grenade explosion 120 over 0.5 -> 2.0 (Elite shield x4, Jackal shield x1.5,
        # Hunter armour x0.25 / skin x0.5, Flood x2 / x4, Sentinel x4) + ATTACHED 120 (direct; Elite
        # shield x4, Hunter armour x0.2, world x0), timer 2 s when at rest, arming 0; the needle's
        # homing 90 deg/s (1.5708 rad/s) on the autoaim target; the plasma pistol's charged pair;
        # rocket 315 over 0.5 -> 2.0, 2.0 s, 2 / 4 / 8, 12 -> 10, range 128, aim 0/35 12/35; the
        # restored fuel rod 40..75 over 0.5 -> 1.5, 1.25 s charge.
        # THE APPROXIMATIONS (user, 4a):
        #  - CHARGE: the plasma pistol's PAIR -- a tap fires ONE bolt (trigger 0, unguided), paced at
        #    Reach's single-bolt cycle 0.75 s hold + 0.2 s recovery = 0.95 s (1.05/s); a full charge
        #    (Reach's 3.0 s) released -- or held 2.0 s more (charge hold + discharge) -- fires trigger
        #    1: a 4-bolt SPEW at Reach's spacing. Lost: the 0.75 s wait before a single bolt, the 2-
        #    and 3-bolt levels, an early release firing nothing.
        #  - LOCK-ON: the charged volley's bolt homes at Reach's 45 deg/s on the autoaim target at
        #    release (the needler's mechanism); the tap bolt is unguided (Reach: no lock in a tap,
        #    AI bolts unguided -- Halo 1's AI only taps a pair). Lost: the lock TIME (0.5 s acquire,
        #    grace, decay) and a lock indicator unless the HUD can show one.
        #  - STICKING: Reach's table as default responses (attach everywhere, the Jackal shield
        #    reflects, water passes), the fuse 'when at rest' 0.25..2.5 s, arming 1.
        #  - STUCK DAMAGE: Halo 1 adds the attached damage to the area explosion -> 125 DIRECT on the
        #    victim + the 175 area = Reach's 300 on the victim. Lost: bystanders take 175, not 300.
        'pick': 'Plasma Grenade',
        'reason': "user, step 4a 2026-10-13: 'Plasma Grenade, charge kept' + 'the yardstick's table' "
                  "for default. The plasma grenade is the bolt's own family (Reach explosion_small "
                  "both, 175 / 300 against 250 / 350 over the same 1.8 wu) and the only candidate "
                  "with a free AND a stuck burst in both games, so the stuck damage has a real ratio. "
                  "A thrown grenade has no rate, flight, range or aim: those HOLES by the Rocket ratio "
                  "(the GL's precedent). No Reach yardstick charges: the 0.75 s hold and the 3.0 s "
                  "charge have no counterpart and stay Reach's in both versions; only the recovery "
                  "and the spew spacing take the time ratio. Materials: the plasma grenade's table in "
                  "both (no group offset: explosion_small both; Hunters x0.25 / x0.2 by the table).",
        # DEFAULT = Reach's own numbers (PORTING "Balance"); these are the BALANCED rows
        'balanced': {
            # the free burst: 120 x 177/252 = 84.3 (all area: Halo 1's grenade has no impact; a zero
            # on one side -> the impact 0); lower 80 x 17.5/25 = 56
            'damage': 84.29, 'damage_lower': 56.0, 'impact': 0.0,
            # radius 0.5 x 0.6/0.54, 2.0 x 1.8/1.8
            'radius': (0.556, 2.0),
            # stuck: Halo 1 240 (120 + 120 attached) x 302/352 = 205.9 -> attached 205.9 - 84.3
            'attached': 121.6,
            # fuse: 2.0 x 0.25/0.9, 2.0 x 2.5/0.95 (from rest, both); arming 0 x 1/1.4 = 0
            'timer': (0.556, 5.263), 'arming': 0.0,
            # holes by the RL ratio (2.0 s / 0.8 s = x2.5) on the TIMES that have a counterpart:
            # the recovery 0.2 x 2.5 = 0.5 -> a single bolt 0.75 + 0.5 = 1.25 s; the spew spacing
            # 0.21 x 2.5 = 0.526 s (1.9/s); the charge 3.0 s / hold 2.0 s Reach's (no counterpart)
            'single_bolt_s': 1.25, 'spew_rate': 1.9,
            # flight 12 x 11/8 = 16.5, 10 x 7/16 = 4.4; range 128 x 180/175 = 131.7; gravity: the
            # rocket's 0 (a zero on one side) -> Reach's own 0.1
            'velocity': (16.5, 4.4), 'range': 131.7, 'gravity': 0.1,
            # aim 0 x 3/5 = 0, 35 x 30/60 = 17.5; 12 x 6/10 = 7.2, 35 x 30/25 = 42
            'aim': (0.0, 17.5, 7.2, 42.0),
            # EXCEPT the autoaim ANGLE (user, 2026-10-13, approved after boot 1): Reach's 3 in both
            # -- the RL ratio's 0 would also turn off the volley's homing (Halo 1 homes on the
            # autoaim target)
            # heat / battery: no yardstick has either (the grenade, the rocket) -> Reach's own
            'heat': 'reach', 'battery': 'reach'},
        # Time to kill (h1_role_compare plasma_launcher, direct hits, normal): Reach's own 177 a bolt
        # every 0.95 s (186 dps; stuck 302 = 318 dps), a volley 4 x 177 after 3 s every 3.63 s (195
        # dps) -- Elites 2 bolts, 1 stuck, Hunter 6; balanced (PG ratio, charge kept) 84.3 every 1.25
        # s (67 dps; stuck 206 = 165), a volley every 4.58 s (74) -- Elites 2 / 2 / 2, 1 stuck, Hunter
        # 11 (5 stuck); fuel rod 60, rocket 158, plasma grenade 120 / stuck 240
        'measured': 'h1_role_compare.py plasma_launcher',
        'candidates': {
            'source_weapon': 'objects\\weapons\\support_high\\plasma_launcher\\plasma_launcher',
            'provisional': 'Flak Cannon (H1 fuel rod)',
            'alternatives': ['Plasma Grenade', 'Rocket Launcher'],
            'direct': None,
            'peers': ['Rocket Launcher', 'Flak Cannon', 'Plasma Grenade'],
            'why': 'charge-to-fire sticky explosive plasma; heat + battery, no magazine',
            'lacks': "the 0.75 s hold before a single bolt, the 2- and 3-bolt charge levels "
                     "(approximated: tap = 1 bolt, full charge = a 4-bolt spew), the lock TIME "
                     "(0.5 s acquire / grace / decay -- approximated: the volley homes on the "
                     "autoaim target at release), the stuck bonus (Halo 1 deals attached damage at the "
                     "stick: the burst alone, 175 -- boot 1), the volley's 0.21 s spacing (one shot: "
                     "the pair fires trigger 1 once, its spew never runs -- probe), the volley's battery "
                     "check (Halo 1 checks only that the battery is not empty: a volley fires 4 bolts "
                     "from one bolt left -- user, boot 8: accept), Reach's rising charge 'in' (the loop "
                     "is its sustain), the charge pips round the crosshair, the lock rings and the "
                     "scope's charge bar (no HUD input / live meter)"}},
    # step 11: the source game's ai\generic entry (24 fields, verified 2026-10-07) laid over a Halo 1
    # FUEL ROD carrier ('pl' has no carrier; the grenade yardstick is thrown). Halo 1's carriers
    # (h1_weapon_carriers, 2026-10-13): fuel rod -- grunt specops fuel rod (+ airdef), both WDM 0.5,
    # they agree (the CR's donor); rocket -- the Flood combat Elite / human (0.4); plasma pistol --
    # 29 (Grunts, Jackals, Flood, enhancer slots). WDM rule / balanced drop: after 5b on the built port
    firing_profile={'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\support_high\\plasma_launcher\\plasma_launcher',
                    'donor_weapon': 'weapons\\fuel rod gun\\fuel rod'},
)

PORT.update({
    'status': 'in_progress',
    # user, boot 1 reply (2026-10-13): 'keep the water splash' -- a bolt into water plays the
    # grenade's `bounce water` (Reach's launcher has no water sound of its own)
    'sound_keeps': {B.join(['sound', 'sfx', 'impulse', 'impacts', 'med_splash']):
                    "user: keep the water splash (Reach's launcher has none)"},

    # geometry + look (h1_h3_weapon_model.py; Reach through reach_tags). Reach's ONE model for world
    # AND first person. plasma_launcher.render_model: b_gun (root, identity: not tilted) > b_vent_1..4,
    # b_header_upper / _lower, b_halogram, b_barrel_main > b_barrel_main01 + b_barrel_1..4 > b_barrel_
    # front_1..4 (the four barrels open with the charge: Reach's flapN_open functions); markers
    # left_hand (+ per-species variants), primary_trigger (0.161 / 0 / 0.061), right_hand,
    # weapon_stow_anchor -- no primary_ejection. Materials: plasma_launcher_metal / _shell (diffuse),
    # emitter_beam, circular_indicator (halogram), plasma_launcher_display
    'model': {
        'dir': r'weapons\plasma launcher',
        'world': R + RW + r'\plasma_launcher.render_model',
        'fp': R + RW + r'\plasma_launcher.render_model',
        'world_name': 'plasma launcher',
        'ground_point': 'auto',
        'markers': {'left_hand': 'left hand'},
        # every material needs a shader or `tool model` ASKS for a type and loops (the CR's 50 min)
        'shaders': {'plasma_launcher_metal': (TEX + 'plasma_launcher_diffuse.bitmap', None),
                    'plasma_launcher_shell': (TEX + 'plasma_launcher_diffuse.bitmap', None),
                    'circular_indicator': (TEX + 'plasma_launcher_diffuse.bitmap', None),
                    'plasma_launcher_display': (TEX + 'plasma_launcher_diffuse.bitmap', None)},
        'template': r'weapons\plasma rifle\fp\shaders\gun',
        # GLOW (fp_material_view, 2026-10-13): the gun's REAR faces the player -- a holo ring
        # (circular_indicator: a halogram on plasma_launcher_holo + data_stream, 226 tris), the
        # centre screen (plasma_launcher_display: Reach's plasma pistol display + the holo meter
        # map, 42 tris) and the emitter ring between them (emitter_beam, 16 tris). Boot 1: the
        # Concussion Rifle's static lit shapes off the holo map in its indicator blue; the emitter
        # an additive glow in Reach's bolt blue
        'meters': {'circular_indicator': {'map': HOLO, 'from': GAUGE, 'shape': 'r',
                                          'gradient': 0.0, 'static': STATIC, 'color': HOLO_BLUE,
                                          'ramp': CHARGE_RAMP, 'ramp_source': 'A_out'},
                   'plasma_launcher_display': {'map': HOLO, 'from': GAUGE, 'shape': 'r',
                                               'gradient': 0.0, 'static': STATIC, 'color': HOLO_BLUE,
                                               'ramp': CHARGE_RAMP, 'ramp_source': 'A_out'}},
        # THE BOLT'S MODEL: Reach's own plasma_launcher_grenade (one node; materials
        # plasma_nade_metal / plasma_launcher_projectile -- the CR's bolt materials) glowing
        # ADDITIVELY (the CR's boot 3: a solid glow shader_model draws the template's reflection
        # tint) in Reach's bolt blue, a white-hot core
        # BOOT 1 (user): 'our bolt in flight is pure white' (screenshot: Reach's = a white core in
        # a blue halo) -> the core a pale blue (and a blue glow flare on the bolt, pickable)
        # THE CHARGE GLOW (boot 1, user: 'a charging energy effect at the muzzle when holding it';
        # the screenshot: a blue sphere in front of the barrels at full charge). Halo 1 draws
        # weapon attachments at the hidden third-person gun in first person -> the Spartan Laser's
        # recipe: a star of radial cards at the muzzle built INTO the model, its additive shader
        # FADING with D out = primary charged (`fade_source`)
        'glow_shaders': {'emitter_beam': {'rgb': BLUE, 'additive': True},
                         'plasma_nade_metal': {'rgb': BLUE, 'additive': True},
                         'plasma_launcher_projectile': {'rgb': (0.55, 0.75, 1.0), 'additive': True},
                         'pl_charge_glow': {'rgb': BLUE, 'additive': True, 'radial': True,
                                            'hot': True, 'falloff': 1.4, 'fade_source': 'D_out'}},
        'glow_points': [{'marker': 'primary trigger', 'shader': 'pl_charge_glow', 'size': 7.0,
                         'forward': 1.0}],
        'extra_models': {'bolt': {'from': R + RW + r'\projectiles\plasma_launcher_grenade.render_model',
                                  'dir': PL + 'bolt'}},
        'collision': {'material': 'metal',
                      # the world model's bounds (JMS, wu): x -0.188..0.169, y -0.029..0.033, z -0.034..0.122
                      'boxes': [((-0.188, -0.029, -0.034), (0.169, 0.033, 0.122))]},
    },

    # FP animations (h1_fp_retarget.py): ROUTE (a), Reach's own fp_plasma_launcher (the DMR's recipe).
    # 65 nodes (the first Reach FP graph above 64: its node masks are 12 bytes -- reach_tags._masks)
    # and one group chunk the length of a member (h3_anim_decode.blobs now requires the tgda proof).
    # One resource group of bases + one of overlays. idle 99, posing var1 108 / var2 89, ready 26
    # (ready_initial 34), put_away 5, fire_1 var1-3 24, melee_strike_1 47 (primary 5) / _2 37,
    # throw_grenade 44 (primary 8), moving 21, look 9, OVERCHARGED 79 (the held full charge =
    # Halo 1's `overcharged` slot); reload_empty / _full 90 (events at 80 / 100 past the end: a
    # leftover -- no magazine, not mapped); NO overheat animation (Halo 1's overheating / overheated /
    # o-h-exit slots stay empty: the template's would be the plasma pistol's arms). Not reproduced:
    # the charge_up overlay (60 fr) and the flapN_open / _close / flaps overlays (Reach drives the four
    # barrels open by the charge FUNCTIONS -- Halo 1 has no function-driven FP overlay), sprint, jump,
    # land, fall, acceleration_screens
    'retarget': {
        'graph': R + RFP + '.model_animation_graph',
        'render_model': R + RW + r'\plasma_launcher.render_model',
        'nodes': {n: 'frame ' + n.replace('_', ' ') for n in (
            'b_gun', 'b_barrel_main', 'b_halogram', 'b_header_lower', 'b_header_upper', 'b_vent_1',
            'b_vent_2', 'b_vent_3', 'b_vent_4', 'b_barrel_1', 'b_barrel_2', 'b_barrel_3', 'b_barrel_4',
            'b_barrel_main01', 'b_barrel_front_1', 'b_barrel_front_2', 'b_barrel_front_3',
            'b_barrel_front_4')},
        'drop_nodes': ('pedestal', 'aim_pitch', 'aim_yaw', 'l_humerus', 'r_humerus',
                       'l_radius', 'r_radius', 'l_handguard', 'r_handguard'),
        'h1_dir': r'weapons\plasma launcher\fp',
        'h1_model': r'weapons\plasma launcher\fp\fp',
        'align': 'same_space',
        # the DMR's tested placement (user-approved, B1; the repeater, the GL and the CR kept it)
        'view_offset': (-0.0225 - 0.025, 0.0, -0.0125),
        'anims': {
            'first_person:idle': 'first-person idle',
            'first_person:posing:var1': 'first-person posing',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            # the tap (trigger 0) and the volley (trigger 1): Reach plays fire_1 a bolt
            'first_person:fire_1:var1': 'first-person fire-1',
            'first_person:fire_1:var2': 'first-person fire-2',
            'first_person:overcharged': 'first-person overcharged',
            'first_person:melee_strike_1': 'first-person melee',
            'first_person:moving': 'first-person moving',
            'first_person:look': 'first-person overlays',
            'first_person:throw_grenade': 'first-person throw-grenade',
        },
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only plasma_launcher) on a COPY of the Halo 1 PLASMA
    # PISTOL: heat + battery, no magazine, and Halo 1's CHARGED TRIGGER PAIR -- trigger 0 charges;
    # released early it fires its own bolt, fully charged (released, or held past the hold) it fires
    # trigger 1. DEFAULT = REACH's OWN NUMBERS; the plasma grenade ratio = the balance rows.
    # Template layout (the Beam Rifle's / Spartan Laser's reading): exports A heat / B primary
    # charged / C illumination / D age; functions 0 age inverted (A out), 1 heat (B out), 2
    # illumination (C out), 3 primary charged (D out); attachments 0 muzzle light (C), 1 / 4 heat
    # flares (B), 2 overcharge flare (D), 3 the charging loop (D)
    'pickable': {
        'weapon': PL + 'plasma launcher',
        'template': PP + 'plasma pistol',
        'world_model': PL + 'plasma launcher',
        'fp_model': PL + 'fp' + B + 'fp',
        'fp_anims': PL + 'fp' + B + 'fp',
        'label': 'pl',
        # the reserved pose donor: the rocket (Reach files the launcher as weapon class 'missile':
        # a two-handed heavy -- Armed Grunts keep their full rate, Jackals lose the shield)
        'teach': ('pl', 'rl'),
        'keys': {'first-person melee': 5},          # Reach melee_strike_1 primary keyframe 5
        'sounds': {'first-person ready': SND + 'pl_ready',
                   'first-person posing': SND + 'pl_pose',
                   'first-person melee': SND + 'pl_melee'},
        # every template attachment goes: lights / flares draw at the hidden THIRD-PERSON gun in
        # first person (Sentinel Beam, Beam Rifle); the muzzle light moves into the firing effect;
        # the plasma rifle's charging loop is replaced by Reach's (fire_loop)
        'drop_attachments': [0, 1, 2, 3, 4],
        # Reach's charge (plas_launcher_charge: a 5 s `in` that rises over the whole charge + hold,
        # then the loop) while the trigger charges: the template's charge function (D out = primary
        # charged) scales it
        'fire_loop': {'like': B.join(['sound', 'sfx', 'weapons', 'plasma rifle', 'charging']),
                      # BOOT 2 (user): 'swapping to the weapon plays the initial charge up sound' --
                      # a sound_looping's START plays when it is attached (on ready), not when the
                      # charge begins -> no start; the steady loop scaled by the charge. Lost:
                      # Reach's rising 'in' (5 s, the whole charge + hold)
                      'start': '', 'loop': SND + 'pl_charge_loop', 'end': '',
                      'tag': SND + 'pl_charging', 'marker': 'primary trigger', 'scale': 'D_out'},
        'bullet': dict(BOLT, projectile=(PG + 'plasma grenade', PL + 'bolt'), triggers=[0]),
        # THE VOLLEY (trigger 1): the same bolt, GUIDED at Reach's 45 deg/s on the autoaim target at
        # release (the needler's homing: Halo 1 steers a projectile at its weapon's target)
        'projectiles': [dict(BOLT, projectile=(PG + 'plasma grenade', PL + 'bolt guided'),
                             proj_fields=dict(BOLT['proj_fields'],
                                              **{'proj_attrs.physics.guided_angular_velocity': math.radians(45.0)}),
                             triggers=[1])],
        # Reach: illumination recovery 0.5 s; first person offset (0, -0.1, 0) single wield
        # 4b list 2 / 3: Reach's first person offset (0, -0.1, 0) (the balanced ratio -0.2 is aiming
        # geometry, not balance: no row)
        'trigger': {'illumination_recovery_time': 0.5, 'first_person_offset': (0.0, -0.1, 0.0)},
        # Reach: heat 0.4 a bolt, overheated at 1.0, back at 0.1, loss 0.85/s (also overheated:
        # Halo 1's one loss)
        'heat': {'recovery_threshold': 0.1, 'overheated_threshold': 1.0, 'loss_per_second': 0.85},
        # Reach: minimum error 0, error angle 0.3 -> 0.8
        'error_deg': {'minimum_error': 0.0, 'error_angle': (0.3, 0.8)},
        # Reach aim assist, absolute (falloff / near falloff: no Halo 1 field); zoom 1 level 3x
        'aiming': {'autoaim_angle': 3.0, 'autoaim_range': 30.0,
                   'magnetism_angle': 6.0, 'magnetism_range': 30.0,
                   'deviation_angle': 3.0,
                   'zoom_levels': 1, 'zoom_ranges': (3.0, 3.0)},
        # THE FIRING EFFECT (the muzzle-flash rule, closing check 10). Reach's FIRST-PERSON flash
        # (fx\firing.effect, `1st_person`): muzzle_flash_round + flash_large (bounding 0.106 wu),
        # spark_ember (0.68: a spray of embers) and smoke_fiery_small (0.07), all at primary_trigger.
        # The template's (plasma pistol `fire bolt`): `flash c generic` 0.04-0.05, two sideways `med`
        # fins at +-0.04, the front `med` 0.065-0.08, `small` 0.15-0.25, smoke. Boot 1: the Spartan
        # Laser's fire_effect recipe -- only the round `flash c generic` (Reach's flash is round; the
        # fins, small flash and smoke go), tinted Reach's bolt blue, Reach's fire sound, a blue muzzle
        # light 0.1 s (Reach's firing_1p light). Not reproduced yet: Reach's larger flash (0.106 wu
        # against 0.05) and its ember sparks -- judged in boot 1
        # BOOT 1 (user): 'muzzle flash needs to be improved'. Now the Concussion Rifle's copy of
        # the pistol's whole `fire bolt` (both events): the side fins dropped (off axis > 0.02 wu:
        # Reach's flash is round), the flashes x1.5 (Reach 0.106 wu against the pistol's ~0.07),
        # every particle Reach's bolt blue (its smoke too), the light part appended. Still not
        # reproduced: the ember sparks (no Halo 1 plasma ember)
        'sound_effects': {
            'firing_effect': (PP + 'effects' + B + 'fire bolt', PL + 'effects' + B + 'fire bolt',
                              {B.join(['sound', 'sfx', 'weapons', 'plasma rifle', 'fire']): SND + 'pl_fire'},
                              {'match': 'flash c generic', 'drop_off_axis': 0.02, 'scale': 1.5,
                               'tint': (1.0,) + BLUE_LIGHT, 'light': PL + 'muzzle light'}),
            # trigger 1 names the plasma rifle's charged-bolt flash: the same copy
            'firing_effect@1': ('weapons' + B + 'plasma rifle' + B + 'effects' + B + 'charged bolt fire',
                                PL + 'effects' + B + 'fire bolt',
                                {B.join(['sound', 'sfx', 'weapons', 'plasma rifle', 'fire']): SND + 'pl_fire'},
                                {'copy_from': PP + 'effects' + B + 'fire bolt',
                                 'match': 'flash c generic', 'drop_off_axis': 0.02, 'scale': 1.5,
                                 'tint': (1.0,) + BLUE_LIGHT, 'light': PL + 'muzzle light'})},
        'own_light': {'shape': PP + 'muzzle flash', 'look': PP + 'muzzle flash',
                      'out': PL + 'muzzle light', 'argb': (1.0,) + BLUE_LIGHT, 'duration': 0.1},
        'fields': {
            # THE CHARGED PAIR (user, 4a): trigger 0 = the tap, paced at Reach's single-bolt cycle
            # 0.95 s (1.05/s); it charges Reach's 3.0 s, holds 2.0 s, then DISCHARGES trigger 1
            # BOOT 1 PROBE: 1.0526/s fired every 1.03-1.04 s (31 ticks: Halo 1 rounds the interval
            # up ~2 ticks, the B3 rule) -> 1.13/s for Reach's 0.95 s (~28.5 ticks)
            'weap_attrs.triggers.0.firing.rounds_per_second': (1.13, 1.13),
            'weap_attrs.triggers.0.charging.charging_time': 3.0,
            'weap_attrs.triggers.0.charging.charge_hold_time': 2.0,
            'weap_attrs.triggers.0.charging.overcharged_action': 'discharge',
            # THE FULL-CHARGE STEP (boot 11): A out = 1 from primary charged 0.50 (= 3.0 s) on
            'obje_attrs.functions.0.flags.invert': False,
            'obje_attrs.functions.0.function': 'one',
            'obje_attrs.functions.0.scale_function_by': 'B_in',
            'obje_attrs.functions.0.bounds_mode': 'clip_and_normalize',
            # BOOT 12 (user): the step at 0.50 showed at ~2.25 s (not the probe's 3.0) -> scaled
            # by 3.0 / 2.25: 0.667
            # BOOT 13 (user): 'try 3.3 s' -> 0.667 x 3.3 / 3.0 = 0.733
            # BOOT 14 (user): 'close, still early, another 0.3 s' -> 3.6 s: 0.800
            'obje_attrs.functions.0.bounds': (0.795, 0.805),
            'obje_attrs.functions.0.usage': 'charged',
            # 4b list 3: Reach's charged illumination 0.5 (the rocket's 0: a zero on one side)
            'weap_attrs.triggers.0.charging.charged_illumination': 0.5,
            # trigger 1 = the VOLLEY. BOOT 1 PROBE: a spew time on trigger 1 fires ONE bolt (the
            # pair's discharge fires trigger 1 once; its own spew never runs) -> 4 PROJECTILES PER
            # SHOT in a horizontal fan of 4 deg (Reach's 4 bolts leave 0.21 s apart along one line:
            # here together, side by side -- the homing pulls them onto the target). The spew
            # recipe (trigger 1 charging 1 tick + discharge + spew) is boot 2's test SECONDARY
            'weap_attrs.triggers.1.firing.rounds_per_second': (4.75, 4.75),
            'weap_attrs.triggers.1.charging.charging_time': 0.0,
            'weap_attrs.triggers.1.charging.charge_hold_time': 0.0,
            'weap_attrs.triggers.1.charging.spew_time': 0.0,
            'weap_attrs.triggers.1.charging.overcharged_action': 'none',
            # BOOT 3 (user): 'adjust the spread on the volley, it's currently two pairs of two
            # bolts' (the 4 deg fan) -> no fan: each bolt its own random error in a small cone
            # (min 1, up to 2 deg; Reach's error grows 0.3 -> 0.8 over a volley) -- a loose
            # cluster that the homing pulls onto the target
            'weap_attrs.triggers.1.projectile.projectiles_per_shot': 4,
            'weap_attrs.triggers.1.projectile.distribution_function': 'point',
            'weap_attrs.triggers.1.projectile.distribution_angle': 0.0,
            # BOOT 4 (user): 'increase the initial volley spread a little bit' -> min 1.5, 2 -> 2.5
            'weap_attrs.triggers.1.projectile.minimum_error': math.radians(1.5),
            'weap_attrs.triggers.1.projectile.error_angle': (math.radians(2.0), math.radians(2.5)),
            # heat 0.4 a bolt: the volley's one round = 4 bolts = 1.6 (overheats: Reach's 1.6 minus
            # ~0.5 cooling while it spews still overheats)
            'weap_attrs.triggers.0.misc.heat_generated_per_round': 0.4,
            'weap_attrs.triggers.1.misc.heat_generated_per_round': 1.6,
            # BATTERY 12 bolts: Reach's 0.0833333 (just below 1/12: the display shows whole
            # steps) + the Spartan Laser's age MISFIRE at 0.9999, chance 1 (a 13th bolt fired
            # without it)
            'weap_attrs.triggers.0.misc.age_generated_per_round': 0.0833333,
            # the volley's one round = 4 bolts of battery
            'weap_attrs.triggers.1.misc.age_generated_per_round': 4 * 0.0833333,
            'weap_attrs.age.misfire_start': 0.9999,
            'weap_attrs.age.misfire_chance': 1.0,
            'weap_attrs.triggers.0.firing_effects.0.misfire_effect.filepath': '',
            'weap_attrs.triggers.0.firing_effects.0.misfire_damage.filepath': '',
            # the template's empty effect is a SOUND (plasma rifle\overheat): Reach's own
            'weap_attrs.triggers.0.firing_effects.0.empty_effect.filepath': SND + 'pl_empty',
            # trigger 1's empty field is an EFFECT reference (the template's is blank; trigger 0's
            # holds the sound): the pair's empty click comes from trigger 0 -- left blank (build 1
            # failed on a 'pl_empty.effect')
            # Reach has NO overheat / vent effect (its fx folder: attached, charging, detonation,
            # firing, impact, projectile, empty) -> none (the template's green vent + its sound
            # would be a borrow)
            'weap_attrs.heat.overheated.filepath': '',
            'item_attrs.collision_sound.filepath': SND + 'pl_drop',
            'obje_attrs.collision_model.filepath': PL + 'plasma launcher',
            # Reach's active camo ding 1 (the template's)
        },
        # Reach's strike_melee is shared with its rocket: x1 = the H1 rocket's own melee (the GL's)
        'melee': (RL + 'melee', PL + 'melee'),
        'melee_response': PP + 'melee_response',
        'messages': ('Picked up a plasma launcher', 'Picked up %d rounds for plasma launcher'),
        'icon': 'plasma launcher',
        # the PLASMA PISTOL's HUD (heat + battery meters) with Reach's crosshair at the reserved 33.
        # Reach's chud `plasma_launcher`: `crosshair` = hud_reticles #31 at (1.2, 1.25), 'mirror
        # horizontal, mirror vertical' -- the sprite is ONE QUADRANT (a corner bracket + a tick
        # pointing at the centre), drawn four times with its corner on the centre (the Plasma
        # Repeater's quarter-ring layout); a charge meter ring (plasma_launcher_meter, external
        # input `weapon charge`), a ghost reticle and the LOCK rings (locking / locked) -- Halo 1's
        # HUD has no charge or lock input: not reproduced. PROVISIONAL SIZE (no screenshot yet):
        # the CR's screenshot-measured #17 (88 px for 2 x 0.85 x 46 sprite px) -> 1.125 1080p px a
        # sprite px: ~127 x 124 px; supersampled x2 at scale 1.3 -> overlay 0.455
        'hud': {'donor': PP + 'plasma pistol', 'out': PL + 'plasma launcher',
                # THE ZOOM (Reach's one 3x level): the scope recipe (h1_h3_scope) on Reach's chud
                # `plasma_launcher`, its `scope` collection. Its state data did not decode (every
                # widget reads zoom 0) -> named (`zoom`); the central LENS `scope_mask` (a hex
                # quarter, mirrored both ways, border extended = the dim outside) is animated
                # (scale 0) -> its size fitted to the user's screenshot; `scope_mask_left` /
                # `_right` share the top cell's placement and are turned +-120 deg by the chud's
                # animation (the screenshot's lower cells) -> `rotate`. COLOURED widgets cannot be a
                # mask (it only darkens): the blue rings (outer / inner_crosshair), the four bolt
                # pips (outer_pips) and the charge bar (meter_new) -- dropped here; glyphs later
                # (the reserved sequences 52-53). The pistol HUD has no screen effect: the sniper's
                'screen_effect_from': 'weapons\\sniper rifle\\sniper rifle',
                'screen_effect_clear': ('night_vision', 'desaturation'),
                'scope': {'chud': R + r'ui\chud\plasma_launcher', 'out': PL + 'bitmaps\\scope_mask',
                          'size': 1024, 'span': 931.1, 'aspect': 1.25, 'alpha': 'outside',
                          'per_widget': {'scope_mask': {'zoom': True, 'scale': (1.0, 1.0)},
                                         'scope_mask_top': {'zoom': True},
                                         'scope_mask_left': {'zoom': True, 'rotate': 120.0},
                                         'scope_mask_right': {'zoom': True, 'rotate': -120.0},
                                         'scope_mask_sm_bottom': {'zoom': True, 'mirror_local': True},
                                         'scope_mask_sm_left': {'zoom': True, 'mirror_local': True},
                                         'scope_mask_sm_right': {'zoom': True, 'mirror_local': True},
                                         'outer_crosshair': {'drop': True},
                                         'inner_crosshair': {'drop': True},
                                         'meter_new': {'drop': True},
                                         'outer_pips': {'drop': True},
                                         'lowbatt_flash_scope': {'drop': True}}},
                'reticle': (R + r'ui\chud\bitmaps\hud_reticles', 31, 'plasma launcher'),
                'reticle_xform': {'stretch': (1.2, 1.25), 'offset': (-RQ[0], -RQ[1])},
                'reticle_layers': [(R + r'ui\chud\bitmaps\hud_reticles', 31, 1.0,
                                    {'flip_x': True, 'stretch': (1.2, 1.25), 'offset': (RQ[0], -RQ[1])}),
                                   (R + r'ui\chud\bitmaps\hud_reticles', 31, 1.0,
                                    {'flip_y': True, 'stretch': (1.2, 1.25), 'offset': (-RQ[0], RQ[1])}),
                                   (R + r'ui\chud\bitmaps\hud_reticles', 31, 1.0,
                                    {'flip_x': True, 'flip_y': True, 'stretch': (1.2, 1.25),
                                     'offset': (RQ[0], RQ[1])})],
                # THE SCOPE'S BLUE RINGS (boot 2, user: 'a couple symbols missing'): the coloured-glyph
                # recipe (memory h1-coloured-scope-glyphs: a zoom crosshair, empty sprite 0 + the
                # glyph as sprite 1) at the reserved extras 52 / 53. Reach stores them white with the
                # shape in alpha. Sizes from the user's scope screenshot (1080p): the outer ring
                # (scope_bits, 504 px art) ~312 px across, the inner (scope_bits2 #0, 159 px) ~200 px;
                # a cell sprite draws ~0.5 screen px a sheet px -> the art x0.5 / x1.5 in the 256 cell
                # and the overlay x2.48 / x1.68 (`overlay`). Not reproduced (no sequence left): the
                # four bolt pips and the charge bar
                # BOOT 3 (user): 'the rings in the middle seem mirrored' -- against the screenshot
                # they are turned 180 deg (Reach's open side upper right, ours lower left): `flip`
                'zoom_glyphs': [{'art': (R + r'ui\chud\bitmaps\scopes\plasma_launcher_scope_bits.bitmap', None),
                                 'name': 'plasma launcher ring outer', 'index': 52, 'scale': (0.5, 0.5),
                                 'overlay': 312 / (504 * 0.5 * 0.5), 'alpha': 0.55, 'offset': (0, 0),
                                 'rgb': (110, 190, 245), 'normalize': True, 'gamma': 1.6,
                                 'flip': 'xy'},
                                {'art': (R + r'ui\chud\bitmaps\scopes\plasma_launcher_scope_bits2', 0),
                                 'name': 'plasma launcher ring inner', 'index': 53, 'scale': (1.5, 1.5),
                                 'overlay': 200 / (159 * 1.5 * 0.5), 'alpha': 0.55, 'offset': (0, 0),
                                 'rgb': (110, 190, 245), 'normalize': True, 'gamma': 1.6,
                                 'flip': 'xy'},
                                # BOOT 4 (user: hud_reticles 58-59 granted by the coordinating
                                # session): the four BOLT PIPS (`outer_pips`: scope_bits2 #1, a 54 x 43
                                # three-streak icon, unflipped upper right, 'mirror horizontal, vertical')
                                # in ONE glyph (`mirror4`); the user's scope screenshot: ~55 px each at
                                # (+-268, -167 / +165) px -> 1.02 screen px an art px, the copies at
                                # (263, -164) art px, art x0.38 in the cell, overlay 1.02 / (0.38 x 0.5).
                                # 59 stays free: the diagonal charge bar is a live meter (no static art)
                                {'art': (R + B.join(['ui', 'chud', 'bitmaps', 'scopes', 'plasma_launcher_scope_bits2']), 1),
                                 # BOOT 8 (user): 'the pips have shrunk' (dots near the centre): the wider
                                 # upper row made the art 2 px wider than the 256 px cell -> a 512 frame,
                                 # drawn at another scale -> art x0.37 (fits), overlay / anchor recomputed
                                 # (the anchor kept: boot 7's lower pips were exact)
                                 'name': 'plasma launcher pips', 'index': 58, 'scale': (0.37, 0.37),
                                 # BOOT 5 (user screenshot): drawn at (+-304, -355 / +25) px -- x1.13 too
                                 # wide and 165 px too HIGH (Halo 1 centres the overlay on the sprite's
                                 # CELL, 256 x 256 here, not on its registration: the rings' cells are
                                 # square-ish) -> overlay x268/304, the anchor 165 x 0.88 px down at
                                 # ~1.11 px a unit (the Needle Rifle's calibration)
                                 # BOOT 7: the upper pair 20 px further out. BOOT 8: this comment had
                                 # swallowed the overlay and alpha keys (the pips drew tiny)
                                 'mirror4': (263 + round(20 / 1.02), -164, 263),
                                 'overlay': 1.02 / (0.37 * 0.5) * 268 / 304, 'alpha': 0.85,
                                 # BOOT 9 (user): the pips ~10 px right of centre -> 9 units left
                                 'offset': (round(35 / 1.11) - 9, round(165 * 268 / 304 / 1.11)), 'rgb': (110, 190, 245), 'normalize': True,
                                 'gamma': 1.0}],
                # BOOT 3: the offsets fixed (RQ) drew the art ~10 % narrower (345 against 382 cell px) ->
                # the overlay x382/345 keeps the size the user called close
                'reticle_scale': 1.3, 'reticle_overlay': 0.455 * 382 / 345,
                'reticle_supersample': 2,
                'reticle_min_width': 2},
        'palette_levels': LEVELS,
    },

    # Reach's own sounds (h1_port_sounds.py plasma_launcher, Reach's sfx.fsb: data\sound\weapons\
    # plasma_launcher\). Levels = the active RMS of the stock Halo 1 sound each stands in for
    # (h1_stock_sound_levels.py, 2026-10-13): the plasma pistol's fire (plasma rifle\fire) -9.3,
    # chargefire -8.7, startcharge -12.0, charge loop -11.2, plasma grenade explosion -9.3, its
    # projectile loop -25.0, plaspistol ready -24.6 / melee -19.4 / posing -23.5, the pistol's empty
    # (plasma rifle\overheat) -21.6, rlauncher_impact -23.0. Reach's cues: firing.effect =
    # plas_launcher_fire + pl_lod_far + rocket_launcher_tails_ext / _int (Halo 1 plays one sound a
    # round: fire + the exterior tail MIXED, the CR / GL way); detonation.effect = pl_proj_expl (its
    # `detonation` sound) + expl tails; the charge = plas_launcher_charge in + loop; the bolt's
    # loop plas_launcher_proj_loop; stuck: pl_proj_stick_beep (once) + pl_attached_lp; the empty
    # effect plaslauncher_empty; FP plaslauncher_ready / _melee / _pose1. No drop sound of its own
    # (Reach's flak_cannon_drop stands in, the CR's) and NO overheat / vent sound in Reach's folder
    'sounds': {
        'catalog': 'Plasma Launcher',
        'bank': 'haloreach',
        'dir': B.join(['sound', 'weapons', 'plasma_launcher_port']),
        'h3_dir': RS + 'plasma_launcher' + B,
        'slice': {'pl_charge_loop': (3.0, 4.5)},
        'loop_len': {'pl_charge_loop': 1.4},
        'sounds': {
            'pl_fire': (['plas_launcher_fire', RS + 'rocket_launcher' + B + 'rocket_launcher_tails_ext'],
                        B.join(['sound', 'sfx', 'weapons', 'plasma rifle', 'fire']), -9.3),
            'pl_explode': (['pl_proj_expl'],
                           B.join(['sound', 'sfx', 'weapons', 'plasma grenade', 'plasmagrenexpl']), -9.3),
            # BOOT 3 (user): 'the charge sound is gone entirely' -- Reach's charge LOOP decodes
            # SILENT (rms -180 dB: the GL's frag_armed lesson); what boots 1-2 played was the 5 s
            # 'in' as the loop's start (on ready). The loop is now the 'in''s full-charge SUSTAIN
            # (3.0 - 4.5 s: -9..-12 dB after the rising part), crossfaded seamless (`slice`,
            # `loop_len`), scaled by the charge -- it swells as the charge builds
            'pl_charge_loop': (['plas_launcher_charge' + B + 'plas_launcher_charge' + B + 'in'],
                               B.join(['sound', 'sfx', 'weapons', 'plasma rifle', 'charge']), -11.2),
            'pl_projectile': (['plas_launcher_proj_loop' + B + 'pl_proj_loop' + B + 'loop'],
                              B.join(['sound', 'sfx', 'weapons', 'plasma grenade', 'plasma_projectile']), -25.0),
            'pl_stick': (['pl_proj_stick_beep'],
                         B.join(['sound', 'sfx', 'weapons', 'plasma grenade', 'plasma_projectile']), -15.0),  # BOOT 1 (user): 'I don't hear a beeping' at the projectile loop's -25
            'pl_ready': (['plaslauncher_fp' + B + 'plaslauncher_ready'],
                         B.join(['sound', 'sfx', 'weapons', 'weapon_anims', 'plaspistol_ready']), -24.6),
            'pl_melee': (['plaslauncher_fp' + B + 'plaslauncher_melee'],
                         B.join(['sound', 'sfx', 'weapons', 'weapon_anims', 'plaspistol_melee']), -19.4),
            'pl_pose': (['plaslauncher_fp' + B + 'plaslauncher_pose1'],
                        B.join(['sound', 'sfx', 'weapons', 'weapon_anims', 'plaspistol_posing']), -23.5),
            'pl_empty': (['plaslauncher_empty'],
                         B.join(['sound', 'sfx', 'weapons', 'plasma rifle', 'overheat']), -21.6),
            'pl_drop': ([RS + 'flak_cannon' + B + 'flak_cannon_drop'],
                        B.join(['sound', 'sfx', 'impulse', 'weapon_drops', 'rlauncher_impact']), -23.0),
        },
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py plasma_launcher). DEFAULT = Reach's
    # own numbers in the tags; BALANCED = the PLASMA GRENADE ratio, its holes by the ROCKET ratio,
    # Reach's charge kept (step 4a, user 2026-10-13). Assembly Halo1 units: angles in degrees,
    # velocity in wu per TICK
    'catalog': {
        'entry': {
            'weapon': 'Plasma Launcher', 'source': 'Halo Reach', 'donor': 'Plasma Pistol', 'default_on': False,
            'desc': "Halo Reach's Plasma Launcher: its model, first-person animations, sounds and "
                    "numbers. A tap fires one sticky plasma bolt; hold the trigger three seconds and "
                    "release for a volley of four that homes on your target. Bolts stick to whatever "
                    "they hit and burst a moment later. Twelve bolts a battery; a volley overheats it.",
            'balance_desc': "Measured against the Plasma Grenade: a weaker burst (84, 206 when stuck), "
                            "single bolts every 1.25 s, a slower volley, faster bolts and Halo 1-style "
                            "aim assist; the charge, heat and battery stay Reach's.",
            'balance': [
                # the free burst: 120 x 177/252 = 84.3; lower 80 x 17.5/25 = 56; radius 0.5 x
                # 0.6/0.54, 2.0 x 1.8/1.8
                row('jpt!', PL + 'explosion', 'Damage Lower Bound', 56.0, 17.5, 'Explosion Damage'),
                row('jpt!', PL + 'explosion', 'Damage Upper Bound', 84.29, 175.0, 'Explosion Damage'),
                row('jpt!', PL + 'explosion', 'Damage Upper Bound Max', 84.29, 175.0, 'Explosion Damage'),
                row('jpt!', PL + 'explosion', 'Radius', 0.556, 0.6, 'Explosion Damage'),
                row('jpt!', PL + 'explosion', 'Radius Max', 2.0, 1.8, 'Explosion Damage'),
                # the stuck burst: none since boot 1 (Halo 1 deals attached damage at the stick)
                # the impact: Halo 1's grenade has none -> 0 (a zero on one side)
                row('jpt!', PL + 'impact', 'Damage Lower Bound', 0.0, 2.0, 'Bolt Damage'),
                row('jpt!', PL + 'impact', 'Damage Upper Bound', 0.0, 2.0, 'Bolt Damage'),
                row('jpt!', PL + 'impact', 'Damage Upper Bound Max', 0.0, 2.0, 'Bolt Damage'),
                # the single bolt: Reach's 0.75 s hold (no counterpart) + 0.2 x 2.0/0.8 = 1.25 s =
                # 37.5 ticks -> 0.845/s (Halo 1 rounds ~2 ticks up: the boot 1 probe). The volley
                # leaves in one shot since boot 1: no spacing row
                dict(row('weap', PL + 'plasma launcher', 'Rounds Per Second', 0.845, 1.13, 'More Shooting', block='Triggers'), index=0),
                dict(row('weap', PL + 'plasma launcher', 'Rounds Per Second Max', 0.845, 1.13, 'More Shooting', block='Triggers'), index=0),
                # flight 12 x 11/8 = 16.5, 10 x 7/16 = 4.4; range 128 x 180/175 = 131.7; fuse 2.0 x
                # 0.25/0.9, 2.0 x 2.5/0.95; arming 0 x 1/1.4 = 0 -- on BOTH bolts
            ] + [r for proj in ('bolt', 'bolt guided') for r in (
                row('proj', PL + proj, 'Initial Velocity', 16.5 / 30, 11.0 / 30, 'Projectile'),
                row('proj', PL + proj, 'Final Velocity', 4.4 / 30, 7.0 / 30, 'Projectile'),
                row('proj', PL + proj, 'Maximum Range', 131.7, 180.0, 'Projectile'),
                row('proj', PL + proj, 'Timer', 0.556, 0.25, 'Projectile'),
                row('proj', PL + proj, 'Timer Max', 5.263, 2.5, 'Projectile'),
                row('proj', PL + proj, 'Arming Time', 0.0, 1.0, 'Projectile'),
                # 4b list 2: gravity 1 x 0.1/0.9, water 1 x 0.5/0.75 (the grenade's flight)
                row('proj', PL + proj, 'Air Gravity Scale', 0.111, 0.1, 'Projectile'),
                row('proj', PL + proj, 'Water Gravity Scale', 0.667, 0.5, 'Projectile'))] + [
                # aim (RL ratio): 0 x 3/5, 35 x 30/60; 12 x 6/10, 35 x 30/25. The autoaim ANGLE stays
                # Reach's 3 (user, boot 1 reply: the RL's 0 would turn off the volley's homing --
                # Halo 1 homes on the autoaim target): no row
                row('weap', PL + 'plasma launcher', 'Autoaim Range', 17.5, 30.0, 'Autoaim'),
                row('weap', PL + 'plasma launcher', 'Magnetism Angle', 7.2, 6.0, 'Magnetism'),
                row('weap', PL + 'plasma launcher', 'Magnetism Range', 42.0, 30.0, 'Magnetism'),
            ]},
    },

    # step 4b (port_field_audit.py --port plasma_launcher): the source pair (Reach plasma launcher vs
    # the yardstick -- the weapon's holes by the RL, the bolt / bursts by Reach's plasma grenade)
    # against the target pair (the H1 port vs the H1 rocket / plasma grenade)
    'field_audit': {
        'source_kit': 'HREK',
        'source': {'weapon': (RW + r'\plasma_launcher.weapon', r'objects\weapons\support_high\rocket_launcher\rocket_launcher.weapon'),
                   'projectile': (RW + r'\projectiles\plasma_launcher_grenade.projectile',
                                  r'objects\weapons\grenade\plasma_grenade\plasma_grenade.projectile'),
                   'damage_effect': (RW + r'\projectiles\damage_effects\plasma_launcher_grenade_detonation.damage_effect',
                                     r'objects\weapons\grenade\plasma_grenade\damage_effects\plasma_grenade_explosion.damage_effect'),
                   'attached': (RW + r'\projectiles\damage_effects\plasma_launcher_grenade_attached_detonation.damage_effect',
                                r'objects\weapons\grenade\plasma_grenade\damage_effects\plasma_grenade_attached_explosion.damage_effect')},
        'target': {'weapon': (PL + 'plasma launcher.weapon', RL + 'rocket launcher.weapon'),
                   'projectile': (PL + 'bolt.projectile', PG + 'plasma grenade.projectile'),
                   'damage_effect': (PL + 'explosion.damage_effect', PG + 'explosion.damage_effect'),
                   'attached': (PL + 'attached.damage_effect', PG + 'attached.damage_effect')}},

    # the dry test: a30, Reach's own battery (no magazine)
    'test': {'level': 'a30', 'rounds': (0, 0), 'grunt': None, 'elite': None},
})
