r"""Plasma Repeater (Halo Reach, wave B3): a HEAT automatic plasma rifle on a battery, on a copy of
the Halo 1 PLASMA RIFLE (the yardstick, step 4a: its heat / battery HUD, its gauge, its bolt). The
Needle Rifle (needle_rifle.py) is the nearest shape for the Reach plumbing; the Beam Rifle
(beam_rifle.py) for heat + battery and glow.

REACH'S HEAT LIVES IN THE WEAPON FUNCTIONS (step 4a, 2026-10-11 -- ManagedBlam's own function
Evaluate; field semantics from the tooltips in HREK tool.exe): `heat generated per round function`
= 0.03 a TICK the barrel fires (the per-round field reads 0): fully hot after ~1.1 s / 12 rounds;
rate 15 -> 3 by heat^1.5 (`heat_driven_rate_of_fire`); NEVER overheats (heat stops at 1, the gun
keeps firing at 3/s; `auto_venting` at 0.971 only drives a steam effect); passive loss = the
`heat_loss` function 0.25/s cold -> 0.06/s hot (overrides the 0.0333 field); MANUAL vent on
reload, 2.5 s to heat 0, can be cut short. Halo 1 has one heat loss, a rate that changes with the
HELD time only, and no manual vent: approximation B (user) -- the OVERHEAT stands in for the vent,
the ramp fitted so the rate at each heat follows Reach's."""
from ._common import B, reserved, row

R = 'reach:'                                       # an HREK path (reach_tags)
RW = r'objects\weapons\rifle\plasma_repeater'
RFP = r'objects\characters\spartans\fp\weapons\rifle\fp_plasma_repeater\fp_plasma_repeater'
RP = 'weapons\\plasma repeater\\'
SND = 'sound\\weapons\\plasma_repeater_port\\'
PR = 'weapons\\plasma rifle\\'
RS = 'data\\sound\\weapons\\'                      # Reach's bank folders
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']
# the heat colour of the on-gun lights (Reach's meter_color_on): teal cold (B out's floor 0.1),
# Reach's 255, 181, 23 orange-yellow midway, red hot
HEAT_RAMP = [(0.0, (89 / 255.0, 1.0, 244 / 255.0)), (0.05, (89 / 255.0, 1.0, 244 / 255.0)),
             (0.5, (1.0, 181 / 255.0, 23 / 255.0)), (0.95, (1.0, 0.16, 0.08)), (1.0, (1.0, 0.16, 0.08))]

PORT = reserved(
    order=21, wave='B3', name='Plasma Repeater', source='Halo Reach',
    messages=(75, 76), icon=41, reticle=30, label='rp', teach_from='pr',
    sound_dir='sound\\weapons\\plasma_repeater_port', weapon_dir='weapons\\plasma repeater',
    yardstick={
        # step 4a (user, 2026-10-11; h1_role_compare.py plasma_repeater)
        'pick': 'Plasma Rifle',
        'reason': ("the heat automatic plasma rifle of both games (Reach HAS a plasma rifle, and "
                   "the Elite carries it in both). The plasma pistol is tapped: its rate gives no "
                   "ratio, so it barely moves Reach's numbers. Halo 1 approximation B (user): the "
                   "OVERHEAT stands in for Reach's manual vent and the rate decline follows the "
                   "heat -- Halo 1's trigger ramps the rate over the HELD time, fitted so its rate "
                   "at each heat is within ~1/s of Reach's (default: heat 1/12 a round = Reach's "
                   "12 rounds to full heat, ramp 15 -> 3 over 1.4 s; balanced 1/22, 15 -> 3.33 over "
                   "2.65 s); deceleration time = the vent, so rate and heat recover together. "
                   "Materials (user): the H1 plasma rifle bolt's table in the DEFAULT; BALANCED = "
                   "that table x Reach's plasma_fast / plasma_slow for the armour class of the "
                   "matching Reach model (Elite shield x0.625, Elite BODY hard_metal_thin x2.5, "
                   "player the same pair, Hunter armour x2, Jackal shield x0.5, Marine armour x2, "
                   "metal x2-2.5)"),
        # DEFAULT = Reach's own numbers (wave rule); these are the BALANCED rows (H1 plasma rifle x
        # Reach repeater / Reach plasma rifle). Reach: repeater 5.834 -> 7 plasma_fast (mean 6.42),
        # 15 -> 3/s by heat, 0.03 heat a tick (hot in 1.1 s), loss 0.25 -> 0.06/s, vent 2.5 s,
        # battery 0.005 (200), error 0.4 -> 3, 25 -> 35 wu/s, range 100, aim 5/15 10/20; plasma
        # rifle 10 plasma_slow, 6 -> 9/s, heat 0.15 a round, loss 0.8525 / 0.35 overheated,
        # battery 0.0025, error 1.3 -> 3.5, 25 wu/s, range 40, aim 5/12 9/18. H1 plasma rifle 13,
        # 7 -> 10/s over 1.8 s held, heat 0.08, loss 0.3, recovery 0.25, battery 0.005, error
        # 0.5 -> 5, 50 wu/s, aim 5/25 12/25
        'balanced': {
            'damage': 8.34,              # 13 x 6.42/10
            'rate': (15.0, 3.333),       # 7 x 15/6 = 17.5 -> Halo 1's 15/s cap; 10 x 3/9 (4b's positional pairing)
            'heat_per_round': 0.077,     # 0.03 x 0.08/0.15 = 0.016 a tick: hot after 22 rounds (H1 cools while firing)
            'ramp_s': 2.6,               # fitted under Halo 1's fire rule (the probe; Reach hot in 1.95 s)
            'vent_s': 2.9,               # 2.5 x 0.35/0.3 (overheated losses) -> loss 1/2.9
            'battery': 0.01,             # 0.005 x 0.005/0.0025 (100 rounds)
            'velocity': (50.0, 70.0),    # 50 x 25/25, 35/25
            'error': (0.15, 4.3),        # 0.5 x 0.4/1.3, 5 x 3/3.5
            'aim': (5.0, 31.25, 13.3, 27.8),  # 5 x 5/5, 25 x 15/12; 12 x 10/9, 25 x 20/18
            'materials': 'x plasma_fast / plasma_slow (RP_FAST_SLOW in h1_role_compare)',
            'melee': None},              # Reach shares strike_melee: x1 = the plasma rifle's own
        'measured': 'h1_role_compare.py plasma_repeater',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\plasma_repeater\\plasma_repeater',
            'provisional': 'Plasma Rifle',
            'alternatives': ['Plasma Pistol'],
            'direct': 'Elite (carries the Plasma Rifle in both games: same as the provisional)',
            'peers': ['Plasma Rifle', 'Assault Rifle', 'Needler'],
            'why': 'heat-based automatic plasma bolt, rate falls with heat',
            'lacks': "the manual vent (and venting part-way), a rate tied to HEAT (Halo 1: to the "
                     "held time), firing on at 3/s when hot (Halo 1 overheats instead), Reach's "
                     "slow passive cooling (one loss = the vent's)"}},
    # step 11: Reach's ai\generic Plasma Repeater entry over a base -- 'rp' has no carrier. Halo 1's
    # PLASMA RIFLE carriers (h1_weapon_carriers, 2026-10-11): Elite minor / major / stealth 0.5,
    # commander / spec-ops 0.6, Flood combat (both) 0.4, Marines 0.5, armoured Marines 0.6. The
    # yardstick's own carrier = the ELITE MINOR plasma rifle (the Needle Rifle's choice: one
    # donor for every slot). WDM RULE: 0.5 x plasma rifle 13 x 10/s = 130 / the port's dps
    # (h1_role_compare plasma_repeater, the table's fastest rate: default 6.42 x 15 = 96,
    # balanced 8.34 x 15 = 125) -- re-measured on the BUILT port at 5b
    firing_profile={'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map',
                    'from_weapon': 'objects\\weapons\\rifle\\plasma_repeater\\plasma_repeater',
                    'donor_weapon': 'weapons\\plasma rifle\\plasma rifle',
                    'donor_variant': 'characters\\elite\\elite minor\\elite minor plasma rifle',
                    'wdm_rule': {'base': 0.5, 'yardstick_dps': 130.0, 'port_dps': 96.0,
                                 'balanced_port_dps': 125.0}},
)

PORT.update({
    'status': 'building',

    # geometry + look (h1_h3_weapon_model.py; Reach through reach_tags). Reach's ONE model for
    # world AND first person. plasma_repeater.render_model: 7 nodes -- b_gun (root, identity: not
    # tilted), b_rod_left / b_rod_right, b_cylinder, b_cowl, b_wing_left / b_wing_right; 1 mesh,
    # 12 parts; primary_trigger x2 (stagger fire), fx_vent x2, firing_light. Materials:
    # plasma_repeater_metal / _rubber (diffuse), _shell (Covenant carapace; its illum map
    # plasma_repeater_illum is NOT in HREK -> illum off, the DMR's case), _display (a METER
    # shader: illum plasma_pistol_display, meter plasma_launcher_holo, value = ammo, colour red),
    # _gauge (a METER: meter plasma_repeater_gauge, value = HEAT, off (77, 212, 203) -> on teal
    # (89, 255, 244) -> orange (255, 181, 23)), _indicator (halogram, plasma_launcher_holo, teal
    # 114, 255, 215), _pilot (halogram flame, white -> blue 8, 16, 82, by manual_venting / age)
    'model': {
        'dir': r'weapons\plasma repeater',
        'world': R + RW + r'\plasma_repeater.render_model',
        'fp': R + RW + r'\plasma_repeater.render_model',
        'world_name': 'plasma repeater',
        # fx_vent (x2, Reach's venting gas) = the plasma rifle template's `vent` (its overheat
        # steam); Reach's two STAGGERED primary_trigger muzzles (z 0.005 first, 0.048 second) =
        # the plasma rifle's lower `primary trigger1` and upper `primary trigger` (its two
        # firing effects; h3_rm_to_jms names list entries per instance)
        'markers': {'left_hand': 'left hand', 'fx_vent': 'vent',
                    'primary_trigger': ['primary trigger1', 'primary trigger']},
        # BOOT 5 (A/B with the stock plasma rifle's model: it bounced, ours sank): every stock Halo 1
        # weapon has ONE `ground point` marker -- on its side surface near the balance point (plasma
        # rifle 0.017 / -0.021 / 0.001 of a +-0.030 wide gun, AR 0.057 / -0.014 / 0.032 of +-0.015),
        # turned 90 deg about x (stored 0.707, 0.707, 0, 0: its axis = into the gun) -- the dropped
        # item rests on it; no port had one. The repeater's: the left side surface (y -0.016) at
        # the middle of the gun (x 0.06, z 0.02), the plasma rifle's rotation
        # BOOT 6 (user): 'this is the dropping issue fix' -> placed by the tool now, as on every port
        'ground_point': 'auto',
        'shaders': {'plasma_repeater_metal': (R + RW + r'\bitmaps\plasma_repeater_diffuse.bitmap', None),
                    'plasma_repeater_rubber': (R + RW + r'\bitmaps\plasma_repeater_diffuse.bitmap', None),
                    'plasma_repeater_shell': (R + RW + r'\bitmaps\plasma_repeater_diffuse.bitmap', None),
                    'plasma_repeater_indicator': (R + RW + r'\bitmaps\plasma_repeater_diffuse.bitmap', None)},
        'template': PR + r'fp\shaders\gun',
        'glow': {},
        # Own hull (h1_box_collision.py) from the world model's cross-section (x -0.093..0.226, y
        # +-0.016, z -0.037..0.077): body + grip -- what projectiles hit (the plasma rifle's hull
        # has other nodes). BOOT 2 tested Halo CE's pathfinding spheres against the sinking:
        # NO effect (removed); the cause was the missing `ground point` (extra_markers, below)
        'collision': {'material': 'metal',
                      'boxes': [((-0.093, -0.016, 0.0), (0.226, 0.016, 0.077)),
                                ((-0.02, -0.012, -0.037), (0.05, 0.012, 0.0))]},
        # THE HEAT GAUGE (the big panel on top in first person) and the DISPLAY (the lights low on
        # the gun). BOOT 1 (user, Reach screenshots cold / hot): both are FULLY LIT shapes whose
        # COLOUR follows heat -- teal cold, through yellow, red hot (Reach's meter_color_on: 89,
        # 255, 244 -> 255, 181, 23 -> red); the boot-1 meter only FILLED (Reach's gradient is 0
        # over the left half: half lit from cold). BOOT 2: a shader_model lit through a CHANGE
        # COLOUR stayed BLACK (Halo 1's change colour = a colour picked at creation, its `scale
        # by` a BRIGHTNESS). BOOT 3: a meter with its `gradient` SOURCE = heat stayed one colour
        # (a meter colours lit texels by their PLACE only). The probe (h1_weapon_state_probe):
        # B out = heat floored at 0.1, live from spawn. BOOT 4: the Needle Rifle's lit shape
        # (additive chicago, white shape) x a colour RAMP sampled at one point slid by B out
        # (`ramp`: the map's u-animation source) -- teal to 0.1, yellow at 0.55, red at 1
        # BOOT 4 (user): the ramp works ('both change colours from teal to red') -- REMEMBER IT as
        # the backup -- but Reach's gauge FILLS: 'initially blue, fills up with heat, slowly
        # turning red on the way; the plasma rifle already shows how' (its meter: lit texels by
        # value, coloured by PLACE). And 'the overheat colour isn't held' -> both read A OUT =
        # heat + OVERHEATED (function 0, pickable `fields`: C in = overheated, `add`): full / red
        # through the whole vent. BOOT 5: the gauge a meter again -- Reach's alpha gradient
        # stretched to 0.02..0.95 (`gradient_range`: boot 1 lit half of it from cold), unlit = a
        # dim teal (Reach's meter_color_off 77, 212, 203 at half), lit teal -> red along the
        # bar; the display keeps the ramp
        'meters': {
            # BOOT 5 (user): 'fills like imagined, but the colours don't shift as expected -- teal, then
            # red towards the end' (min -> max colours the fill by PLACE). BOOT 6: the fill one teal
            # (min = max) and the meter's FLASH colour (red) with its brightness = A out (heat +
            # overheated): the whole fill turning red with heat, if flash blends by brightness
            'plasma_repeater_gauge': {
                'map': R + RW + r'\bitmaps\plasma_repeater_gauge.bitmap',
                'from': PR + r'fp\shaders\gauge', 'value': 'A_out', 'gradient_range': (0.02, 0.95),
                'color': (89 / 255.0, 1.0, 244 / 255.0), 'color_max': (89 / 255.0, 1.0, 244 / 255.0),
                'color_off': (0.5 * 77 / 255.0, 0.5 * 212 / 255.0, 0.5 * 203 / 255.0),
                'flash': (1.0, 0.16, 0.08), 'flash_source': 'A_out'},
            'plasma_repeater_display': {
                'map': R + r'objects\weapons\support_high\plasma_launcher\bitmaps\plasma_launcher_holo.bitmap',
                'from': PR + r'fp\shaders\gauge', 'shape': 'r', 'gradient': 0.0,
                'static': r'weapons\needler\shaders\needler luminous', 'color': (1.0, 1.0, 1.0),
                'ramp': HEAT_RAMP, 'ramp_source': 'A_out'},
            # the INDICATOR halogram (plasma_launcher_holo, teal 114, 255, 215): the Needle
            # Rifle's indicator recipe, its 1/4 level
            'plasma_repeater_indicator': {
                'map': R + r'objects\weapons\support_high\plasma_launcher\bitmaps\plasma_launcher_holo.bitmap',
                'from': PR + r'fp\shaders\gauge', 'shape': 'r', 'gradient': 0.0,
                'static': r'weapons\needler\shaders\needler luminous',
                'color': (0.25 * 114 / 255.0, 0.25, 0.25 * 215 / 255.0)}},
        # the PILOT flame (8 triangles; Reach: a halogram of plasma noise, white -> blue 8, 16, 82):
        # an additive radial glow per UV island (the Spike Rifle's / Beam Rifle's gems)
        'glow_shaders': {'plasma_repeater_pilot': {'rgb': (0.55, 0.65, 1.0), 'additive': True,
                                                   'islands': True}},
    },

    # FP animations (h1_fp_retarget.py): ROUTE (a), Reach's OWN fp_plasma_repeater retargeted (the
    # DMR's recipe). fp_plasma_repeater (reach_tags --pose): fire_1 var1-3 (10 fr), idle 100,
    # posing var1 90 / var2 109, ready 20 (ready_initial 29), put_away 5, melee_strike_1 34
    # (primary 5), throw_grenade 44 (primary 8), throw_vent 44, moving 20, look 9; THE VENT:
    # vent_enter 21 / vent_loop 30 / vent_exit 13 = Halo 1's overheating / overheated / o-h-exit
    # (the plasma rifle template's own overheat states). Not reproduced: barrel_spin (21, an
    # overlay driven by the rate), accelration_screens (9), melee_strike_vent, sprint, jump/land
    'retarget': {
        'graph': R + RFP + '.model_animation_graph',
        'render_model': R + RW + r'\plasma_repeater.render_model',
        'nodes': {'b_gun': 'frame b gun', 'b_rod_left': 'frame b rod left',
                  'b_cylinder': 'frame b cylinder', 'b_cowl': 'frame b cowl',
                  'b_rod_right': 'frame b rod right', 'b_wing_left': 'frame b wing left',
                  'b_wing_right': 'frame b wing right'},
        'drop_nodes': ('pedestal', 'aim_pitch', 'aim_yaw', 'l_humerus', 'r_humerus',
                       'l_radius', 'r_radius', 'l_handguard', 'r_handguard'),
        'h1_dir': r'weapons\plasma repeater\fp',
        # BOOT 1 (user): 'hold the venting animation as long as overheat is going on' -- Halo 1
        # plays `overheated` once: vent_loop (1 s) x3 = 3 s; with vent_enter 0.7 s the overheat
        # states run 3.7 s (the stock plasma rifle's 3.6 s against its 2.5 s vent)
        'repeat': {'first-person overheated': 3},
        'h1_model': r'weapons\plasma repeater\fp\fp',
        'align': 'same_space',
        # the DMR's tested placement (user-approved, B1)
        'view_offset': (-0.0225 - 0.025, 0.0, -0.0125),
        'anims': {
            'first_person:idle': 'first-person idle',
            'first_person:posing:var1': 'first-person posing',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:fire_1:var1': 'first-person fire-1',
            'first_person:melee_strike_1': 'first-person melee',
            'first_person:moving': 'first-person moving',
            'first_person:look': 'first-person overlays',
            'first_person:vent_enter': 'first-person overheating',
            'first_person:vent_loop': 'first-person overheated',
            'first_person:vent_exit': 'first-person o-h-exit',
            'first_person:throw_grenade': 'first-person throw-grenade',
            'first_person:throw_vent': 'first-person throw-overheated',
        },
    },

    # Reach's own sounds (h1_port_sounds.py plasma_repeater, Reach's sfx.fsb). Levels = the active
    # RMS of the stock Halo 1 PLASMA RIFLE sound each stands in for (h1_stock_sound_levels.py,
    # 2026-10-11): fire -9.3 (5 perms -7.9 .. -10.0), overheat / dry -20.9, melee -11.4, oh_exit
    # -20.0, overheating -26.7, posing -30.5, ready -21.2, drop (plasma_impact) -18.7, flyby
    # (plasrif_projectile) -26.2. Reach's cues: firing.effect plays plas_repeater_fire + the
    # plasma rifle's exterior / interior TAILS (Halo 1 plays one sound a round -> the shot and the
    # exterior tail MIXED, the DMR); the FP graph: vent_enter -> plasrepeater_oh, vent_exit ->
    # plasrepeater_oh_exit, ready -> plasrepeater_ready (ready_initial -> _ready_hero: Halo 1 has
    # no first draw), melee / pose 1; the manual vent's attachment = plasrepeater_manvent in +
    # loop (scaled by manual_venting); the bolt's flyby = plasma_flyby_reach; the dry fire =
    # Reach's plasma_pistol dryfire effect (plasma_dryfire)
    'sounds': {
        'catalog': 'Plasma Repeater',
        'bank': 'haloreach',
        'dir': B.join(['sound', 'weapons', 'plasma_repeater_port']),
        'h3_dir': RS + 'plasma_repeater\\',
        'sounds': {
            'rp_fire': (['plas_repeater_fire', RS + 'plasma_rifle\\plasma_rifle_tails_ext'],
                        'sound\\sfx\\weapons\\plasma rifle\\fire', -9.3),
            'rp_dryfire': ([RS + 'plasma_pistol\\plasma_dryfire'], 'sound\\sfx\\weapons\\plasma rifle\\overheat', -20.9),
            'rp_ready': (['plasrepeater_ready'], 'sound\\sfx\\weapons\\weapon_anims\\plasrifle_ready', -21.2),
            'rp_melee': (['plasrepeater_melee1'], 'sound\\sfx\\weapons\\weapon_anims\\plasrifle_melee', -11.4),
            'rp_pose': (['plasrepeater_pose1'], 'sound\\sfx\\weapons\\weapon_anims\\plasrifle_posing', -30.5),
            # THE VENT (Halo 1's overheat): the vent_enter cue + the manual vent's start, mixed
            'rp_vent': (['plasrepeater_oh', 'plasrepeater_manvent\\track_1\\in'],
                        'sound\\sfx\\weapons\\weapon_anims\\plasrifle_overheat', -26.7),
            'rp_vent_loop': (['plasrepeater_manvent\\track_1\\loop'],
                             'sound\\sfx\\weapons\\weapon_anims\\plasrifle_overheat', -26.7),
            'rp_vent_exit': (['plasrepeater_oh_exit'], 'sound\\sfx\\weapons\\weapon_anims\\plasrifle_oh_exit', -20.0),
            'rp_drop': ([RS + 'plasma_rifle\\plasma_rifle_drop'], 'sound\\sfx\\impulse\\weapon_drops\\plasma_impact', -18.7),
            # the bolt's own FLYBY (port_sound_refs does not read projectile sound fields: by hand)
            'rp_flyby': ([RS + 'impacts_riccs\\plasma_flyby_reach'], 'sound\\sfx\\impulse\\impacts\\plasrif_projectile', -26.2),
            # BOOT 1 (user): 'its own plasma impact sound' -- Reach's material effects
            # (fx\material_effects\weapons\plasma_repeater) play plasma_impacts_reach; Halo 1's bolt
            # plays plasma rifle\plasmahit (-11.3) in 21 of its response effects
            'rp_impact': ([RS + 'impacts_riccs\\plasma_impacts_reach'], 'sound\\sfx\\weapons\\plasma rifle\\plasmahit', -11.3),
        },
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only plasma_repeater) on a COPY of the Halo 1 PLASMA
    # RIFLE (the yardstick = the template: its heat + battery HUD, gauge, bolt, overheat states).
    # DEFAULT = REACH's OWN NUMBERS through approximation B (top of the file); the ratio values
    # are the balance rows. Template layout: inputs A heat / B illumination / D age; functions 0
    # wander colour, 1 lens flare scale (A in = heat -> B out: the GAUGE), 2 muzzle flash, 3 age
    'pickable': {
        'weapon': RP + 'plasma repeater',
        'template': PR + 'plasma rifle',
        'world_model': RP + 'plasma repeater',
        'fp_model': RP + 'fp\\fp',
        'fp_anims': RP + 'fp\\fp',
        'label': 'rp',
        'teach': ('rp', 'pr'),
        'keys': {'first-person melee': 5},          # Reach melee_strike_1 primary keyframe 5
        'sounds': {'first-person ready': SND + 'rp_ready',
                   'first-person posing': SND + 'rp_pose',
                   'first-person melee': SND + 'rp_melee',
                   'first-person overheating': SND + 'rp_vent',
                   'first-person overheated': SND + 'rp_vent_loop',
                   'first-person o-h-exit': SND + 'rp_vent_exit'},
        # own bolt + damage (step 3). Reach: plasma_repeater_bolt 5.834 -> 5.834-7 (plasma_fast),
        # instantaneous acceleration 0.125, 25 -> 35 wu/s, range 100. Materials: the H1 plasma
        # rifle bolt's table (user, DEFAULT); balanced rows x plasma_fast / plasma_slow
        'bullet': {'projectile': (PR + 'bolt', RP + 'bolt'),
                   'damage': (PR + 'bolt', RP + 'bolt'),
                   # STEP 4b list 4: instantaneous acceleration -- both Reach weapons 0.125 (the source
                   # pair agrees) -> the plasma rifle's 0 (the template's, no key)
                   'dmg': 5.834, 'velocity': (25.0, 35.0), 'range': 100.0,
                   'fields': {'damage.damage_upper_bound': (5.834, 7.0)},
                   'proj_fields': {'proj_attrs.physics.flyby_sound.filepath': SND + 'rp_flyby'},
                   # BOOT 1: every response effect that plays plasmahit -> an own copy playing rp_impact
                   # (impact_tint with no particle match: the sound swap only)
                   'impact_tint': {'match': (), 'rgb': None, 'out': RP + 'effects\\impact\\',
                                   'sounds': {'sound\\sfx\\weapons\\plasma rifle\\plasmahit': SND + 'rp_impact'}},
                   # THE HIT-EFFECT RULE: a 15/s weapon (max(default 15, balanced 15))
                   'impact_thin': {'materials': [22], 'out': RP + 'effects\\impact\\',
                                   'thin': {}, 'rate': 15.0}},
        # APPROXIMATION B (user, step 4a): rate 15 -> 3 over 1.4 s HELD (fitted to Reach's
        # heat^1.5 at 12 rounds to full heat), back over 2.5 s (= the vent); heat 1/12 a round;
        # battery 0.005 (Reach's campaign = multiplayer); the FP muzzle = the MEAN of Reach's two
        # staggered primary_trigger markers in the idle pose (camera space: 0.291 / -0.037 /
        # -0.064 and 0.285 / -0.037 / -0.021; Halo 1 has one offset)
        # BOOT 1 (user): 'doesn't build up enough heat' -- Halo 1 COOLS WHILE FIRING (the one
        # loss, 0.4/s, every tick). BOOT 2: still no overheat. THE PROBE (h1_weapon_state_probe,
        # 3 bursts, heat = weapon +0x204): shot gaps 3,3,3,3,3,4,4,5,6,11 ticks -- Halo 1 adds
        # rate/30 a tick and fires when the sum REACHES 1, then RESETS it: a rate a hair under
        # 15 takes 3 ticks (10/s), exactly 3/s takes 11 (2.7/s); the ramp ran ~1.17x faster than
        # the tag (1.2 s for 1.4). Heat peaked at 0.78. REFIT under that rule (h1_role_compare
        # h1_ticks): start 20 (the first six shots every 2 ticks = 15/s, Reach's), ramp 1.35 s,
        # floor 3.05 (10 ticks = 3/s), heat 0.12 a round -- the first 12 shot times within a
        # tick of Reach's, overheat on the 12th round at 1.03 s (Reach full heat 12 / 1.0 s)
        'trigger': {'rounds_per_second': (20.0, 3.05), 'acceleration_time': 1.35,
                    'deceleration_time': 2.5, 'heat_generated_per_round': 0.12,
                    'age_generated_per_round': 0.005,
                    'first_person_offset': (0.288, -0.0373, -0.0422)},
        # Reach's vent: 2.5 s to heat 0 -> overheated at 1, back at 0, one loss 0.4/s
        # TEMPLATE DIFF (before boot 1): Halo 1's heat `illumination` = Reach's `heat illumination`
        # (4b listed it as Reach-only by name): repeater 0, Reach plasma rifle 1 -> 1 x 0/1 = 0
        # BOOT 1 (user): 'it never exits the overheated state' -- the heat must fall BELOW the
        # recovery threshold, and it stops at 0: 0.01 (1 -> 0.01 at 0.4/s = 2.475 s)
        'heat': {'recovery_threshold': 0.01, 'overheated_threshold': 1.0, 'loss_per_second': 0.4,
                 'illumination': 0.0},
        # the template's overheat steam aims at its `vent` (Reach's fx_vent, mapped in the model)
        'overheated_effect': {'from': PR + 'effects\\overheated', 'out': RP + 'effects\\overheated',
                              'locations': {}},
        # Reach's own spread (minimum error 0)
        'error_deg': {'minimum_error': 0.0, 'error_angle': (0.4, 3.0)},
        # Reach aim assist, absolute
        'aiming': {'autoaim_angle': 5.0, 'autoaim_range': 15.0,
                   'magnetism_angle': 10.0, 'magnetism_range': 20.0},
        # THE MUZZLE-FLASH RULE (closing check 10, before boot 1). Reach's FIRST-PERSON flash
        # (fx\firing.effect, 'only in first person'): five particle systems ALL at primary_trigger,
        # no offsets -- muzzle_flash_round (bounds 0.046 wu), flash_large 0.035, glow_soft 0.021,
        # muzzle_flash_plasma 0.074, plasma_blue_small 0.035; blue (firing_1p light 62, 70, 255).
        # The plasma rifle's (h1_effect_particles, both effects alike): centre flash 0.06-0.075,
        # a VERTICAL pair pitched +-120 deg (0.05-0.06) at +-0.04 wu that Reach lacks -> dropped
        # (`drop_off_axis`, the SMG / Needle Rifle recipe), forward 0.075-0.125 at +0.05 / +0.1,
        # smoke 6-10; size kept (judged in game), the tracer kept
        'sound_effects': {
            # the plasma rifle's TWO firing effects (upper at `primary trigger`, lower at `primary
            # trigger1`); Reach's two staggered muzzles
            'firing_effect': (PR + 'effects\\plasma rifle upper fire', RP + 'effects\\fire upper',
                              {'sound\\sfx\\weapons\\plasma rifle\\fire': SND + 'rp_fire'},
                              {'match': 'flash', 'drop_off_axis': 0.012}),
            'firing_effect@1': (PR + 'effects\\plasma rifle lower fire', RP + 'effects\\fire lower',
                                {'sound\\sfx\\weapons\\plasma rifle\\fire': SND + 'rp_fire'},
                                {'match': 'flash', 'drop_off_axis': 0.012})},
        'fields': {
            # the dead-battery click: the plasma rifle's empty is a SOUND reference
            'weap_attrs.triggers.0.firing_effects.0.empty_effect.filepath': SND + 'rp_dryfire',
            # Reach misfires (start 0.9, chance 0.25) with NO misfire effect
            'weap_attrs.age.misfire_chance': 0.25,
            # BOOT 5 (probe: battery 58-72 % used): the template's AGE penalties (rate -20 %, heat
            # +20 % at an empty battery) slowed the trigger so it never overheated; Reach's repeater
            # has 0 / 0 (and the rate fit assumes none) -> 0 in both versions
            'weap_attrs.age.heat_penalty': 0.0,
            'weap_attrs.age.rate_of_fire_penalty': 0.0,
            'weap_attrs.triggers.0.firing_effects.1.misfire_effect.filepath': '',
            'item_attrs.collision_sound.filepath': SND + 'rp_drop',
            # BOOT 4 (user): 'the overheat colour isn't held' -- the lights read A OUT = heat +
            # OVERHEATED: C in = overheated, function 0 (the template's colour wander on A out,
            # used by nothing of the port's) = 'one' x heat + C in -> 1+ through the vent
            'weap_attrs.C_in': 'overheated',
            'obje_attrs.functions.0.function': 'one',
            'obje_attrs.functions.0.period': 0.0,
            'obje_attrs.functions.0.scale_function_by': 'A_in',
            'obje_attrs.functions.0.add': 'C_in',
            # the own hull (model['collision']) and a bounding radius over the model (the
            # template's 0.2 < the farthest vertex, ~0.24 wu)
            'obje_attrs.collision_model.filepath': RP + 'plasma repeater',
            'obje_attrs.bounding_radius': 0.25,
            # STEP 4b (before boot 1). List 2 (the ratio vs Reach's plasma rifle onto the H1 plasma
            # rifle): camo ding 0.3 x 0.25/0.4, illumination recovery 0.15 x 0.1/0.03. List 3: rounds
            # between tracers -- Reach 1, its plasma rifle 0 (a zero on one side: the source value);
            # bounding radius -- Reach's plasma rifle 0 (automatic): the template's 0.2 kept
            'weap_attrs.interface.active_camo_ding': 0.1875,
            'weap_attrs.triggers.0.misc.illumination_recovery_time': 0.5,
            'weap_attrs.triggers.0.firing.rounds_between_tracers': 1,
        },
        'melee': (PR + 'melee', RP + 'melee'),
        'melee_response': PR + 'melee_response',
        'messages': ('Picked up a plasma repeater', 'Picked up %d rounds for plasma repeater'),
        'icon': 'plasma repeater',
        # the PLASMA RIFLE's HUD (heat + battery meters) with Reach's reticle: the plasma_carbine
        # chud's `crosshair` = hud_reticles #3, ONE ring quarter (37 x 36, its registration at the
        # centre; chud origin 0.965 / 0.962 = the ring's centre at the sprite's bottom right)
        # mirrored both ways -> four layers at +-17.2 / +-16.6 sprite px. Reach's sprite peaks at
        # alpha 85: BOOT 1's x2.9 lift made a solid ring -- the user's Reach screenshot shows it
        # ALMOST TRANSPARENT: its own level (gain 1; `reticle_split` 1 normalises each layer for
        # the stroke growth, then puts the layer's peak back, else grow_to's threshold 96 erased
        # it). THE WEDGES (user, Reach screenshot, 1080p: ring ~88 px across, four bright wedges
        # on the DIAGONALS, ~35 px long, tips ~13 px from the centre): #33 (50 x 14, tip at +x)
        # at 0.56 of the ring sprite's scale (chud 0.6 / 0.7 vs 1.15 -> 28 sprite px long), each
        # turned to point at the centre, its centre 10.5 + 14 = 24.5 px out along its diagonal
        # (17.3 / 17.3); the little heat meter under the crosshair: Halo 1's HUD meters show heat
        'hud': {'donor': PR + 'plasma rifle', 'out': RP + 'plasma repeater',
                'reticle': (R + r'ui\chud\bitmaps\hud_reticles', 3, 'plasma repeater'),
                'reticle_xform': {'offset': (-17.2, -16.6), 'gain': 0.5},
                'reticle_layers': [(R + r'ui\chud\bitmaps\hud_reticles', 3, 1.0, {'flip_x': True, 'offset': (17.2, -16.6), 'gain': 0.5}),
                                   (R + r'ui\chud\bitmaps\hud_reticles', 3, 1.0, {'flip_y': True, 'offset': (-17.2, 16.6), 'gain': 0.5}),
                                   (R + r'ui\chud\bitmaps\hud_reticles', 3, 1.0, {'flip_x': True, 'flip_y': True, 'offset': (17.2, 16.6), 'gain': 0.5}),
                                   (R + r'ui\chud\bitmaps\hud_reticles', 33, 0.56, {'rotate': -45, 'offset': (-17.3, -17.3)}),
                                   (R + r'ui\chud\bitmaps\hud_reticles', 33, 0.56, {'rotate': -135, 'offset': (17.3, -17.3)}),
                                   (R + r'ui\chud\bitmaps\hud_reticles', 33, 0.56, {'rotate': 135, 'offset': (17.3, 17.3)}),
                                   (R + r'ui\chud\bitmaps\hud_reticles', 33, 0.56, {'rotate': 45, 'offset': (-17.3, 17.3)})],
                'reticle_split': 1,
                'reticle_min_width': 3,
                # BOOT 2 (user): 'the right shape; slightly bigger; can we draw a half-transparent
                # ring?' -- the overlay x1.15 (reticle_scale 1: the art as drawn), the ring's four
                # quarters at half their level (Reach's faint ring)
                # BOOT 3 (user): '30% bigger' -> x1.15 x 1.3 = x1.5
                'reticle_scale': 1.0, 'reticle_overlay': 1.5},
        'palette_levels': LEVELS,
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py plasma_repeater). DEFAULT = Reach's
    # own numbers in the tags (approximation B); BALANCED = the PLASMA RIFLE ratio (step 4a, user
    # 2026-10-11). Assembly Halo1 units: angles in degrees, velocity in wu per TICK
    'catalog': {
        'entry': {
            'weapon': 'Plasma Repeater', 'source': 'Halo Reach', 'donor': 'Plasma Rifle', 'default_on': False,
            'desc': "Halo Reach's Plasma Repeater: its model, first-person animations, sounds and "
                    "numbers. A Covenant automatic on heat and battery: it starts at 15 bolts a "
                    "second and slows as it heats; a full gun vents for 2.5 s (Reach's manual vent, "
                    "here the overheat). 200 shots a battery.",
            'balance_desc': "Measured against the Plasma Rifle, which both games have: 8.3 damage a "
                            "bolt (the plasma rifle's family, faster on armour and slower on "
                            "shields, as Reach's fast plasma), 15 down to 3.3 bolts a second over "
                            "22 shots, a 2.9 s vent, 100 shots a battery, a faster bolt and Halo "
                            "1-style aim assist.",
            # step 9 (swap, ONE multiplier): the H1 plasma rifle's ready 29 fr x Reach repeater 20
            # / Reach plasma rifle 20 = 29 over the built ready (no reload: a battery weapon)
            'anims': {'swap': 29 / 21.0},
            'balance': [
                # damage: x 13/10 (the plasma rifles' mean damage) on Reach's bounds 5.834 / 5.834-7
                row('jpt!', RP + 'bolt', 'Damage Lower Bound', 7.584, 5.834, 'Bolt Damage'),
                row('jpt!', RP + 'bolt', 'Damage Upper Bound', 7.584, 5.834, 'Bolt Damage'),
                row('jpt!', RP + 'bolt', 'Damage Upper Bound Max', 9.1, 7.0, 'Bolt Damage'),
                # materials (user): the plasma rifle bolt's table x Reach plasma_fast / plasma_slow
                # per armour class of the matching Reach model (h1_role_compare RP_FAST_SLOW)
                row('jpt!', RP + 'bolt', 'Elite Energy Shield', 1.25, 2.0, 'Bolt materials'),
                row('jpt!', RP + 'bolt', 'Elite', 2.5, 1.0, 'Bolt materials'),
                row('jpt!', RP + 'bolt', 'Cyborg Energy Shield', 1.25, 2.0, 'Bolt materials'),
                row('jpt!', RP + 'bolt', 'Cyborg', 1.25, 0.5, 'Bolt materials'),
                row('jpt!', RP + 'bolt', 'Hunter Armor', 1.0, 0.5, 'Bolt materials'),
                row('jpt!', RP + 'bolt', 'Jackal Energy Shield', 0.5, 1.0, 'Bolt materials'),
                row('jpt!', RP + 'bolt', 'Armored Human', 2.0, 1.0, 'Bolt materials'),
                row('jpt!', RP + 'bolt', 'Metal (Hollow)', 0.625, 0.25, 'Bolt materials'),
                row('jpt!', RP + 'bolt', 'Metal (Thin)', 0.625, 0.25, 'Bolt materials'),
                row('jpt!', RP + 'bolt', 'Metal (Thick)', 0.5, 0.25, 'Bolt materials'),
                # rate (4b's positional pairing): 15 (Halo 1's cap; 7 x 15/6 = 17.5) -> 10 x 3/9 = 3.33, the ramp fitted to
                # 22 rounds (heat 0.016 a tick x Reach's), the deceleration = the vent
                # (the probe's fire rule: floor 3.4 = 9 ticks = 3.33/s; the ramp refitted 2.6 s)
                row('weap', RP + 'plasma repeater', 'Rounds Per Second Max', 3.4, 3.05, 'More Shooting', block='Triggers'),
                row('weap', RP + 'plasma repeater', 'Acceleration Time', 2.6, 1.35, 'More Shooting', block='Triggers'),
                row('weap', RP + 'plasma repeater', 'Deceleration Time', 2.9, 2.5, 'More Shooting', block='Triggers'),
                # (the probe's fire rule: refitted to overheat on the 22nd round, 1.97 s; Reach 1.95)
                row('weap', RP + 'plasma repeater', 'Heat Generated Per Round', 0.077, 0.12, 'Heat', block='Triggers'),
                # the vent: 2.5 x 0.35/0.3 = 2.9 s from 1 to 0
                row('weap', RP + 'plasma repeater', 'Heat Loss Per Second', 1 / 2.9, 0.4, 'Heat'),
                # battery: 0.005 x 0.005/0.0025 = 0.01 (100 rounds)
                row('weap', RP + 'plasma repeater', 'Age Generated Per Round', 0.01, 0.005, 'Battery', block='Triggers'),
                # spread: 0.5 x 0.4/1.3, 5 x 3/3.5
                row('weap', RP + 'plasma repeater', 'Error Angle', 0.154, 0.4, 'Error Angle', block='Triggers'),
                row('weap', RP + 'plasma repeater', 'Error Angle Max', 4.29, 3.0, 'Error Angle', block='Triggers'),
                # bolt: 50 x 25/25 = 50, 50 x 35/25 = 70 wu/s (per tick); range: the H1 plasma rifle
                # bolt has none (0) -- a zero on one side: Reach's 100 kept
                row('proj', RP + 'bolt', 'Initial Velocity', 50 / 30.0, 25 / 30.0, 'Projectile'),
                row('proj', RP + 'bolt', 'Final Velocity', 70 / 30.0, 35 / 30.0, 'Projectile'),
                # aim: 5 x 5/5 (no row), 25 x 15/12; 12 x 10/9, 25 x 20/18
                row('weap', RP + 'plasma repeater', 'Autoaim Range', 31.25, 15.0, 'Autoaim'),
                row('weap', RP + 'plasma repeater', 'Magnetism Angle', 13.33, 10.0, 'Magnetism'),
                row('weap', RP + 'plasma repeater', 'Magnetism Range', 27.78, 20.0, 'Magnetism'),
            ]},
    },

    # step 4b (port_field_audit.py --port plasma_repeater): the source pair (Reach repeater vs the
    # yardstick, Reach's plasma rifle) against the target pair (the H1 port vs its template = the
    # yardstick, the H1 plasma rifle)
    'field_audit': {
        'source_kit': 'HREK',
        'source': {'weapon': (RW + r'\plasma_repeater.weapon', r'objects\weapons\rifle\plasma_rifle\plasma_rifle.weapon'),
                   'projectile': (RW + r'\projectiles\plasma_repeater_bolt.projectile',
                                  r'objects\weapons\rifle\plasma_rifle\projectiles\plasma_rifle_bolt.projectile'),
                   'damage_effect': (RW + r'\projectiles\plasma_repeater_bolt.damage_effect',
                                     r'objects\weapons\rifle\plasma_rifle\projectiles\plasma_rifle_bolt.damage_effect')},
        'target': {'weapon': (RP + 'plasma repeater.weapon', PR + 'plasma rifle.weapon'),
                   'projectile': (RP + 'bolt.projectile', PR + 'bolt.projectile'),
                   'damage_effect': (RP + 'bolt.damage_effect', PR + 'bolt.damage_effect')}},

    # the dry test: a30 (Covenant within seconds of the landing), a battery weapon spawns charged
    'test': {'level': 'a30', 'rounds': (0, 0), 'grunt': None, 'elite': None},
})
