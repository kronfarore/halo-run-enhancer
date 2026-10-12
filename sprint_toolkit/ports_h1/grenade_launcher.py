r"""Grenade Launcher (Halo Reach -> Halo 1, wave B4). Yardstick: the FRAG GRENADE, its holes
filled by the ROCKET LAUNCHER (step 4a, user 2026-10-12). What is new: a BOUNCING grenade with a
fuse (Halo 1's frag grenade projectile, Reach's bounce / detonate rules as per-material responses)
and Reach's hold-to-detonate + EMP approximated by the plasma pistol's CHARGED PAIR (a tap fires the
bouncing grenade; held past the charge and released, a 'tethered' grenade that bursts on contact
with a shield-only EMP). Reach plumbing: plasma_repeater.py / needle_rifle.py; the explosion
chain: brute_shot.py."""
from ._common import B, reserved, row  # noqa: F401

R = 'reach:'                                       # an HREK path (reach_tags)
RW = r'objects\weapons\rifle\grenade_launcher'
RFP = r'objects\characters\spartans\fp\weapons\rifle\fp_grenade_launcher\fp_grenade_launcher'
GL = 'weapons\\grenade launcher\\'
SND = 'sound\\weapons\\grenade_launcher_port\\'
RL = 'weapons\\rocket launcher\\'
FG = 'weapons\\frag grenade\\'
RS = 'data\\sound\\weapons\\'                      # Reach's bank folders
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']

PORT = reserved(
    order=22, wave='B4', name='Grenade Launcher', source='Halo Reach',
    messages=(77, 78), icon=42, reticle=31, label='gl', teach_from='sg',
    sound_dir='sound\\weapons\\grenade_launcher_port', weapon_dir='weapons\\grenade launcher',
    yardstick={
        # STEP 4a (user, 2026-10-12): h3_weapon_values.py --kit reach (grenade_launcher /
        # rocket_launcher / flak_cannon, FP graphs) + the HREK exports of the projectiles and
        # damage effects + h1_role_compare.py grenade_launcher (new set).
        # REACH'S GRENADE (HREK): trigger `latch-tether`, recovery 0.5 s, 1 / 8 / 16, reloads 1
        # (63 fr empty, 59 full), error 0.15 min, 0 -> 0.4, 12.5 -> 7.5 wu/s, air gravity 0.7,
        # water 0.75, range 100 (airborne_detonation there), arming 0, minimum velocity 0, danger
        # radius 2.5. Damage: IMPACT 25 (`collision`, accel 0.5) + DETONATION 0..180 over 0.75 ->
        # 2.25 (AOE core 0.6, `explosion_small`, accel 2, no aoe spike bump). Responses in order:
        # units at 0-5 wu/s bounce; units otherwise DETONATE (only when not tethered); world 0-7
        # wu/s 'turn physical' (rolls); world at 75-90 deg AND 7.5-14 wu/s DETONATES (only when
        # not tethered); else BOUNCE (frictions 0.42 / 0.42); liquid overpenetrate; the fuse:
        # timer 0.5 s 'after first bounce off any surface'.
        # HOLD-TO-DETONATE: held, the impact rules are off (tethered); RELEASED: the super
        # detonation -- `grenade_launcher_tethered_grenade_explosion` 180 over 0.001 -> 1
        # (core 0.2, accel 3) + the EMP `grenade_launcher_tethered_grenade_emp` 100 `emp` over
        # 0.25 -> 2.5 (side effect emp: vehicles stall). Reach's `emp` group: shields only --
        # energy_shield_thin x0.5 (Elite, Spartan), _thick x0.25 (Jackal), flesh / armour 0.
        # Yardsticks (Reach): frag 0..160 over 0.675 -> 2.25 (explosion_small), timer 0.6-0.65
        # after first bounce off FLOOR, arming 1.4, gravity 0.9, thrown at 10 wu/s (spartans
        # biped); rocket 200 impact + 0..240 over 0.75 -> 2.5 (explosion_large, no bump), 0.8 s,
        # 2 / 4 / 8, 116 fr, 8 -> 16, 0.02, 175, aim 5/60 10/25; fuel rod 100 + 0..60.
        # Halo 1: frag 80..120 over 1.5 -> 2.5 (cat grenade), timer 0.5 on first bounce, arming
        # 1.5, gravity 1.0, thrown at 10 wu/s (cyborg); rocket 80..300-330 over 0.5 -> 2.0, no
        # impact, 2.0 s, 2 / 4 / 8, 125 fr, 12 -> 10, gravity 0, range 128, aim 0/35 12/35,
        # melee 55; restored fuel rod 40..75 over 0.5 -> 1.5, Hunter armour IMMUNE.
        'pick': 'Frag Grenade',
        'reason': "user, step 4a 2026-10-12: 'Frag Grenade and fill the holes with Rocket "
                  "Launcher information for ratio'. The frag is the same damage family (Reach "
                  "explosion_small both; Halo 1 category grenade) with the same fuse rule (timer on "
                  "the first bounce); a thrown grenade has no rate, magazine, reload, range, aim or "
                  "melee, and no impact damage -- those come from the RL ratio. Materials (user): "
                  "the FRAG table in both versions + Reach's group difference in balanced -- the "
                  "GL and the frag are both explosion_small, so the difference is x1. Hunter "
                  "armour takes x0.25 (frag table): 5 direct hits default, 7 balanced (normal). "
                  "Hold + EMP (user): the plasma pistol's CHARGED PAIR.",
        # DEFAULT = Reach's own numbers (PORTING "Balance"); these are the BALANCED rows.
        'balanced': {
            # FRAG ratio. 120 x 180/160; lower: Reach 0 / 0 (unset) -> the sibling rule, 80 x
            # 135/120; radius 1.5 x 0.75/0.675, 2.5 x 2.25/2.25
            'damage': 135.0, 'damage_lower': 90.0, 'radius': (1.667, 2.5),
            # the impact is a HOLE (the frag has none) -> RL: H1 rocket impact 0 x 25/200 = 0.
            # A source value on the other side of a zero goes to zero in balanced (the Needle
            # Rifle's rule)
            'impact': 0.0,
            # the fuse: 0.5 x 0.5/0.6, 0.5 x 0.5/0.65 -> 0.4 (mean) after the first bounce; since boot
            # 5 (user) a fuse from LAUNCH: the typical first bounce 0.7 s + 0.4 = 1.1 (default 1.2);
            # arming 1.5 x 0/1.4 = 0
            'timer': 1.1, 'arming': 0.0,
            # flight: the throw speed is 10 wu/s in both games (biped grenade velocity) -> x1:
            # Reach's own 12.5 -> 7.5; gravity 1.0 x 0.7/0.9, water 1.0 x 0.75/0.75
            'velocity': (12.5, 7.5), 'gravity': 0.778, 'water_gravity': 1.0,
            # HOLES -> the RL ratio: 2.0 s x 0.5/0.8; 2 x 1/2 (4 x 8/4, 8 x 16/8 = Reach's own);
            # 125 fr x 63/116 = 67.9 fr; 128 x 100/175; aim 0 x 4/5, 35 x 15/60; 12 x 8/10, 35 x
            # 15/25; melee strike_melee both -> the rocket's 55 (x1)
            'fire_recovery_s': 1.25,
            'magazine': 1, 'rounds_total_initial': 8, 'rounds_total_maximum': 16,
            'reload_s': 4.1667 * 63 / 116,
            'range': 73.1,
            'aim': (0.0, 8.75, 9.6, 21.0),
            'melee': 55.0,
            # error: the rocket's 0 / 0 is degenerate -> Reach's own 0.15 / 0..0.4 (no ratio)
            'error_deg': (0.15, 0.0, 0.4),
            # the RELEASE (charge pair): the tethered explosion by the frag ratio 120 x 180/160 =
            # 135 over 1.5 x 0.001/0.675, 2.5 x 1/2.25; the EMP by the plasma pistol OVERCHARGE
            # (Halo 1 70 x Reach EMP 100 / Reach overcharge 200 `emp`) = 35 on the overcharge's
            # SHIELD modifiers (elite 1.5, cyborg 0.6, jackal 1; the rest 0 as Reach's emp) over
            # 1.5 x 0.25/0.675, 2.5 x 2.5/2.25
            'release_damage': 135.0, 'release_radius': (0.002, 1.11),
            'emp': 35.0, 'emp_radius': (0.556, 2.78)},
        # DEFAULT (Reach's own) for the record: explosion 180 over 0.75 -> 2.25 (lower 0 ->
        # the sibling rule onto the frag's 80/120: 120), impact 25, fuse 0.5, arming 0, 12.5 ->
        # 7.5, gravity 0.7 / water 0.75, recovery 0.5, 1 / 8 / 16, reload 63 fr, range 100, aim
        # 4/15 8/15, error 0.15 / 0..0.4, melee: Reach strike_melee onto the rocket's 55;
        # release 180 over 0.001 -> 1 + EMP 100 on Reach's emp table (elite / cyborg shield 0.5,
        # jackal shield 0.25, the rest 0) over 0.25 -> 2.5
        # Time to kill (h1_role_compare grenade_launcher, direct hits, normal; a 1-round magazine
        # = reload-paced): default 180+25 every 2.6 s (79 dps sustained) -- Elite minor 1, major
        # / commander 2, Hunter 5 (frag table); balanced 135 every 3.51 s (38 dps) -- Elite 2 / 2
        # / 3, Hunter 7; rocket 102 sustained, Brute Shot port 243 / 70, frag (1/s) 120
        'measured': 'h1_role_compare.py grenade_launcher',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\grenade_launcher\\grenade_launcher',
            'provisional': 'Rocket Launcher',
            'alternatives': ['Frag Grenade', 'Flak Cannon'],
            'direct': None,
            'peers': ['Rocket Launcher', 'Flak Cannon', 'Brute Shot'],
            'why': '1-round magazine, bouncing explosive grenade (gravity 0.7)',
            # what Halo 1 cannot do (user, 4a: the charge pair): the release fires the
            # grenade instead of detonating one in flight (no choosing WHERE it bursts), no
            # rolling while held ('turn physical': Halo 1 reflects with friction), no vehicle
            # stall (emp side effect); the AI only taps (Spartan Laser finding)
            'lacks': 'release-to-detonate in flight (approximated: hold + release fires a '
                     'contact-burst EMP grenade), rolling, the EMP vehicle stall'}},
    # step 11: the source game's ai\generic entry (19 fields, verified 2026-10-07) laid over a Halo
    # 1 ROCKET LAUNCHER carrier ('gl' has no carrier; the frag yardstick is thrown, so the RL fills
    # the hole). Halo 1's rocket carriers (h1_weapon_carriers, 2026-10-12): the Flood combat Elite
    # and human, both WDM 0.4, no actor flags -- they agree, no donor_variant. ARMED WDM RULE: base
    # 0.4 x rocket 158 / GL dps (h1_role_compare's dps column: default 205 x 2/s = 410 -> 0.154,
    # balanced 135 x 0.8/s = 108 -> 0.585). User 2026-10-12: 'keep the usual WDM' -- the column
    # (reloads ignored on both sides, as every port), not the sustained 0.52 / 1.07 (the 1-round
    # magazine reloads every shot: rocket 102, GL 79 / 38 with reloads)
    # BALANCED DROP (user 2026-10-12, every weapon): H1 yardstick x source port / source yardstick,
    # the source values read from its MAP (m10): the frag has no carrier -> the RL fills the hole.
    # H1 RL carriers loaded 0 / 0 (no ratio), ammo 2-2 and 2-4 (tie: 2-3, the Brute Shot's); Reach
    # GL 0.25-0.4 / 6-9, Reach RL 0.25-0.5 / 2-2 -> ammo 2 x 6/2 = 6, 3 x 9/2 = 13.5 -> 13
    firing_profile={'balanced_set': ['0x1E0=h6:Drop Weapon Ammo', '0x1E2=h13:Drop Weapon Ammo Max'],
                    'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\grenade_launcher\\grenade_launcher',
                    'donor_weapon': 'weapons\\rocket launcher\\rocket launcher',
                    'wdm_rule': {'base': 0.4, 'yardstick_dps': 158.0, 'port_dps': 410.0,
                                 'balanced_port_dps': 108.0}},
)

# Reach's display colour (shaders\display / item / display_status / ones, ManagedBlam function
# data): self_illum_color BGRA c1 98 0e = RGB 14 / 152 / 193, intensity 3, albedo black -- a teal
# LCD. Halo 1 has no bloom: colour x intensity clipped (the Brute Shot's BLUE_HOT recipe)
TEAL = (min(1.0, 3 * 14 / 255.0), min(1.0, 3 * 152 / 255.0), min(1.0, 3 * 193 / 255.0))
# the ARM SWITCH (arm_switch.shader): albedo = self-illum colour by `tether_indicator` over 4
# colours (BGRA 00 ff ff / 00 00 00 / 00 25 ff / 00 00 ff = yellow, black, orange 255 / 37 / 0,
# red), intensity 5 -> 1: YELLOW at rest; a tethered grenade turns it red
ARM_YELLOW = (1.0, 1.0, 0.0)
ARM_RED = (1.0, 0.15, 0.0)
# the grenade's flare (fx\projectile.lens_flare): colour 1 / 0.538 / 0.435, radius 0.15
EMBER = (1.0, 0.538, 0.435)
DISPLAY = R + RW + r'\bitmaps' + B
STATIC = r'weapons\needler\shaders\needler luminous'
GAUGE = r'weapons\plasma rifle\fp\shaders\gauge'
# Halo 1 material indices (the projectile's 33 responses): the UNITS Reach detonates on (its
# 'only against units' rules); the rest is world (28 water overpenetrates, as Reach's liquid)
UNITS = [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 30, 32]
WORLD = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 27, 31]           # 29 leaves: the frag's overpenetrate kept


def _emp_test(rgb, out=None, bitmap=None, copy=False, small=False, rgb2=None):
    """One EMP diagnostic particle (boots 9-13): the plasma grenade's shield flash entry at the
    surface ('normal'), all at once, tinted `rgb`; `out` an own particle copy (Reach's timing) with
    an own sprite (`bitmap`: Reach's emp_mask, see h1_pickable_weapons) or the stock sprite copied."""
    eff = B.join(['weapons', 'plasma grenade', 'effects', 'detonation start'])
    e = {'from': eff, 'match': 'flash h shield impact', 'location': 1, 'env': 'any_environment',
         'distribution': 'start', 'tint_bounds': ((1.0,) + tuple(rgb), (1.0,) + tuple(rgb2 or rgb))}
    if small:
        e['radius'] = (0.25, 0.5)
        return e
    # BOOT 16 (user): 'better -- double the rings as a test; I perceive one normal explosion and
    # one big mostly white flash' -> 6 a burst (was 3)
    e.update({'count': 6, 'radius': (1.2, 1.5), 'spin': (-90.0, 90.0)})
    # BOOT 15 (user): 'it's there, but it doesn't last long enough' -- 0.35-0.45 s -> 0.8-1.0 s, a
    # 0.6 s fade, growing to x1.1
    q = {'out': GL + 'effects' + B + out, 'lifespan': (0.8, 1.0), 'fade_out': 0.6,
         'radius_animation': (0.6, 1.1),
         'flags': {'random_horizontal_mirroring': True, 'random_vertical_mirroring': True,
                   'animate_once_per_frame': False}}
    if bitmap:
        q['bitmap'] = dict({'mask': R + B.join(['fx', 'bitmaps', 'plasma', 'emp_mask.bitmap']), 'size': bitmap.get('size', 32)},
                           **dict(bitmap, out=GL + 'effects' + B + 'bitmaps' + B + bitmap['out']))
    if copy:
        q['bitmap_copy'] = (B.join(['effects', 'particles', 'flash', 'bitmaps', 'flash h shield impact']),
                            GL + 'effects' + B + 'bitmaps' + B + 'flash copy')
    e['particle'] = q
    return e


def _lcd(bitmap):
    """One display element of the on-gun LCD as a lit static shape (the Needle Rifle's recipe)."""
    return {'map': DISPLAY + bitmap, 'from': GAUGE, 'shape': 'r', 'gradient': 0.0,
            'static': STATIC, 'color': TEAL}


PORT.update({
    'status': 'in progress',

    # geometry + look (h1_h3_weapon_model.py; Reach through reach_tags). Reach's ONE model for world
    # AND first person. grenade_launcher.render_model: 5 nodes -- b_gun (root, identity: not tilted),
    # b_chamber (the break-open barrel) > b_handle, b_ironsight, b_grenade (the loaded round); 1
    # mesh; markers primary_trigger (0.243 / 0 / 0.057), 5 x muzzle_flash, left_hand(s),
    # weapon_stow_anchor -- no primary_ejection. Bounds x -0.025..0.230, y -0.031..0.026, z
    # -0.011..0.097. 16 materials: _composite / _metal / _metal_shiny / _rubber (the diffuse; their
    # illum maps dmr_illum / battle_rifle_illum are NOT in HREK -> illum off, the DMR's case),
    # unsc_decals_fp (alpha decal), _glass (no Halo 1 equivalent: dropped), and the ON-GUN DISPLAY
    # driven entirely by the TETHER (no Halo 1 counterpart): display (bg frame), item (ARM / ID
    # NOBLE6 / P R X), display_status (READY; tether_state), hundreds / tens / ones (the tethered
    # grenade's DISTANCE), skull_switch + skull_ones (the Jolly Roger + bipeds in range of it),
    # arm_switch (the tether indicator light), arm_switch_projectile (grey 0e0e0e)
    'model': {
        'dir': r'weapons\grenade launcher',
        'world': R + RW + r'\grenade_launcher.render_model',
        'fp': R + RW + r'\grenade_launcher.render_model',
        'world_name': 'grenade launcher',
        'ground_point': 'auto',
        'markers': {'left_hand': 'left hand'},
        'shaders': {'grenade_launcher_composite': (DISPLAY + 'grenade_launcher_diffuse.bitmap', None),
                    'grenade_launcher_metal': (DISPLAY + 'grenade_launcher_diffuse.bitmap', None),
                    'grenade_launcher_metal_shiny': (DISPLAY + 'grenade_launcher_diffuse.bitmap', None),
                    'grenade_launcher_rubber': (DISPLAY + 'grenade_launcher_diffuse.bitmap', None),
                    'arm_switch_projectile': (DISPLAY + 'grenade_launcher_diffuse.bitmap', None),
                    'unsc_decals_fp': (R + r'objects\bitmaps\decals\bitmaps\unsc_decals_diffuse.bitmap', None)},
        'template': r'weapons\assault rifle\fp\shaders\gun',
        'decals': ('unsc_decals_fp',),
        # DISPLAY, boot 1: STATIC (Halo 1 has no tether) -- the frame, ARM / READY and the digits
        # at 0 lit teal as Reach shows them untethered; the skull + its count off (Reach: intensity
        # by bipeds in range of a TETHERED grenade = 0) -> dropped with the glass
        # THE HOLO SIGHT (user's Reach screenshot: the glass above the barrel shows the sight's own
        # ring + drop ticks): Reach paints them into the diffuse under the glass UVs (u 0.53-0.60,
        # v 0.45-0.62: a pale teal panel with a faint ring and ticks); Reach's glass shader blends
        # it over a 50% grey self-illum. Halo 1: a DIM additive lit shape of the diffuse's green
        # channel -- see-through, the painted reticle darker than the panel (judge in game)
        'drop_materials': ('skull_switch', 'skull_ones'),
        # BOOT 1 (user): 'the holographic sight does not have the crosshair on it' -- the green
        # channel's lines are a few levels off the panel. The sight's reticle (frame, ring, side
        # bars, drop ticks = the HUD crosshair's design) is clean in the diffuse's ALPHA: lines
        # ~200-242 over a ~132 panel -> `levels` (140, 235), a faint panel `floor` 0.12, teal
        'meters': {'grenade_launcher_glass': {'map': DISPLAY + 'grenade_launcher_diffuse.bitmap', 'from': GAUGE,
                                              'shape': 'a', 'levels': (140, 235), 'floor': 0.12,
                                              'gradient': 0.0, 'static': STATIC,
                                              'color': (0.45, 0.95, 1.0)},
                   'display': _lcd('display_bg.bitmap'),
                   'item': _lcd('gl_display_details_diffuse.bitmap'),
                   'display_status': _lcd('gl_display_status.bitmap'),
                   'hundreds': _lcd('numbers.bitmap'),
                   'tens': _lcd('numbers.bitmap'),
                   'ones': _lcd('numbers.bitmap')},
        # the ARM SWITCH light (Reach: solid yellow at rest, red when tethered): an additive glow per
        # UV island (the Plasma Repeater's pilot recipe), yellow; the CHARGED cue comes later
        # BOOT 1 (user): 'the yellow light is always on -- maybe only when it charges' -> faded by B
        # OUT = primary charged (pickable: weapon B in + the plasma pistol's `one x B in` function):
        # dark at rest, lit as the hold charges (Reach: lit at rest, red when tethered)
        'glow_shaders': {'arm_switch': {'rgb': ARM_YELLOW, 'additive': True, 'islands': True,
                                        'fade_source': 'B_out'}},
        # own hull (h1_box_collision.py) over the world model's bounds
        'collision': {'material': 'metal',
                      'boxes': [((-0.025, -0.026, -0.011), (0.230, 0.026, 0.097))]},
        # the GRENADE (projectiles\grenade_launcher_grenade.render_model: one node, metal /
        # metal_shiny / arm_switch, markers contrail / dynamic_light) = the projectile's model;
        # contrail = `smoke` (the frag grenade's smoke-trail marker), dynamic_light = `glow`
        'extra_models': {'grenade': {'from': R + RW + r'\projectiles\grenade_launcher_grenade.render_model',
                                     'dir': r'weapons\grenade launcher\grenade',
                                     'markers': {'contrail': 'smoke', 'dynamic_light': 'glow'}}},
    },

    # FP animations (h1_fp_retarget.py): ROUTE (a), Reach's own fp_grenade_launcher (the DMR's
    # recipe). One resource group (not dual-wieldable). fire_1 var1-3 17 fr (allow interruption 14),
    # idle 100, posing var1 94 / var2 89, ready 21 (ready_initial 29), put_away 6, reload_empty 63
    # (primary 27) / reload_full 59 (primary 33), melee_strike_1 35 (primary 5), throw_grenade 44
    # (primary 8), moving 20, look 9; sprint / jump / land / fall / acceleration_screens not
    # reproduced. THE CHARGE PAIR's release = Halo 1's `fire-2` (the plasma pistol's charged shot):
    # Reach's fire_1 var2 (Reach plays nothing extra on a tethered release)
    'retarget': {
        'graph': R + RFP + '.model_animation_graph',
        'render_model': R + RW + r'\grenade_launcher.render_model',
        'nodes': {'b_gun': 'frame b gun', 'b_chamber': 'frame b chamber', 'b_handle': 'frame b handle',
                  'b_ironsight': 'frame b ironsight', 'b_grenade': 'frame b grenade'},
        'drop_nodes': ('pedestal', 'aim_pitch', 'aim_yaw', 'l_humerus', 'r_humerus',
                       'l_radius', 'r_radius', 'l_handguard', 'r_handguard'),
        'h1_dir': r'weapons\grenade launcher\fp',
        'h1_model': r'weapons\grenade launcher\fp\fp',
        'align': 'same_space',
        # the DMR's tested placement (user-approved, B1; the repeater kept it)
        'view_offset': (-0.0225 - 0.025, 0.0, -0.0125),
        'anims': {
            'first_person:idle': 'first-person idle',
            'first_person:posing:var1': 'first-person posing',
            'first_person:ready': 'first-person ready',
            'first_person:put_away': 'first-person put-away',
            'first_person:fire_1:var1': 'first-person fire-1',
            'first_person:fire_1:var2': 'first-person fire-2',
            'first_person:melee_strike_1': 'first-person melee',
            'first_person:moving': 'first-person moving',
            'first_person:look': 'first-person overlays',
            'first_person:reload_empty': 'first-person reload-empty',
            'first_person:reload_full': 'first-person reload-full',
            'first_person:throw_grenade': 'first-person throw-grenade',
        },
    },

    # Reach's own sounds (h1_port_sounds.py grenade_launcher, Reach's sfx.fsb). Levels = the active
    # RMS of the stock Halo 1 sound each stands in for (h1_stock_sound_levels.py, 2026-10-12):
    # rocket fire -15.3 / -14.9, frag expl -7.2 / -8.1 / -8.3, bouncedirt -21.3, bouncemetal -17.3,
    # rocket_reload_e / _f -22.5; the Brute Shot's measured ready -18.3, melee -21.8, posing -22.1,
    # rlauncher_impact -23.0, rocket_ammo -28.8, AR dryfire -17.6, rl_projectile -19.9.
    # Reach's cues: firing.effect = grenade_launcher_fire + brute_shot_tails_ext / _int (Halo 1
    # plays one sound a round: the shot and the exterior tail MIXED, the DMR); detonation.effect =
    # frag_close_layer + the explosion tails (+ grenade_launcher_expl in the AIR detonation) -> the
    # explosion = grenade_launcher_expl + frag_close_layer MIXED; the grenade's material effects
    # bounce frag_bnc_dirt / _stone / _metal; flight loop grenade_launcher_proj; pickup sound
    # brute_shot_ammo; the empty effect = the BR's dry fire (as Reach's brute shot)
    'sounds': {
        'catalog': 'Grenade Launcher',
        'bank': 'haloreach',
        'dir': B.join(['sound', 'weapons', 'grenade_launcher_port']),
        'h3_dir': RS + 'grenade_launcher' + B,
        'sounds': {
            'gl_fire': (['grenade_launcher_fire', RS + 'brute_shot' + B + 'brute_shot_tails_ext'],
                        B.join(['sound', 'sfx', 'weapons', 'rocket launcher', 'fire']), -15.1),
            'gl_explode': (['grenade_launcher_expl', RS + 'frag_grenade' + B + 'frag_close_layer'],
                           B.join(['sound', 'sfx', 'weapons', 'frag grenade', 'expl']), -7.9),
            'gl_bounce': ([RS + 'frag_grenade' + B + 'frag_bnc_dirt'],
                          B.join(['sound', 'sfx', 'weapons', 'frag grenade', 'bouncedirt']), -21.3),
            'gl_bounce_metal': ([RS + 'frag_grenade' + B + 'frag_bnc_metal'],
                                B.join(['sound', 'sfx', 'weapons', 'frag grenade', 'bouncemetal']), -17.3),
            'gl_projectile': ([B.join(['grenade_launcher_proj', 'grenade_launcher_proj', 'loop'])],
                              B.join(['sound', 'sfx', 'weapons', 'rocket launcher', 'rl_projectile']), -19.9),
            'gl_reload_empty': (['grenade_launcher_fp' + B + 'grenade_launcher_reload_empty'],
                                B.join(['sound', 'sfx', 'weapons', 'weapon_anims', 'rocket_reload_e']), -22.5),
            'gl_reload_full': (['grenade_launcher_fp' + B + 'grenade_launcher_reload_full'],
                               B.join(['sound', 'sfx', 'weapons', 'weapon_anims', 'rocket_reload_f']), -22.5),
            'gl_ready': (['grenade_launcher_fp' + B + 'grenade_launcher_ready'],
                         B.join(['sound', 'sfx', 'weapons', 'weapon_anims', 'rocket_ready']), -18.3),
            'gl_melee': (['grenade_launcher_fp' + B + 'grenade_launcher_melee1'],
                         B.join(['sound', 'sfx', 'weapons', 'weapon_anims', 'rocket_melee']), -21.8),
            'gl_pose': (['grenade_launcher_fp' + B + 'grenade_launcher_pose1'],
                        B.join(['sound', 'sfx', 'weapons', 'weapon_anims', 'rocket_posing']), -22.1),
            'gl_ammo': ([RS + 'brute_shot' + B + 'brute_shot_ammo'],
                        B.join(['sound', 'sfx', 'weapons', 'weapon_pickup_ammo', 'rocket_ammo']), -28.8),
            'gl_dryfire': ([RS + 'battle_rifle' + B + 'dryfire'],
                           B.join(['sound', 'sfx', 'weapons', 'assault rifle', 'dryfire']), -17.6),
            'gl_drop': ([B.join([RS + 'frag_grenade', 'frag_drops', 'frag_drop'])],
                        B.join(['sound', 'sfx', 'impulse', 'weapon_drops', 'rlauncher_impact']), -23.0),
            # BOOT 3 (user): 'another charge indicator, ideally a small sound cue for the charge
            # up' -- Reach's grenade launcher has no tether sound; its FRAG's arming (frag_armed:
            # an 'in' click + the armed beep loop) as the hold's cue, at the plasma rifle charge's
            # level (-12.0 / -11.2, the Spartan Laser's measurement) less 2 dB for a beep
            # BOOT 4 (user): 'plays on a normal shot as well or not at all' -- the frag_armed LOOP
            # is pure silence (peak 0), its 'in' click played at every press (a tap charges too).
            # Now NO start sound and Reach's LANDMINE beep loop (one clear beep each 0.5 s: the
            # first lands inside the 0.5 s charge); its volume follows the charge
            'gl_charge_loop': ([B.join([RS + 'equipment', 'landmine', 'landmine_beep', 'track1', 'loop'])],
                               B.join(['sound', 'sfx', 'weapons', 'plasma rifle', 'charge']), -14.0),
            # the BALANCED reloads (the patcher retimes both, then swaps these in): H1 rocket
            # reload-empty 125 fr x 63/116 = 67.9 over the built 63 (x1.078), reload-full 111 x
            # 59/116 = 56.5 over 59 (x0.957) -> ONE patcher multiplier (the DMR's): x1.02
            'gl_reload_empty_balanced': (['grenade_launcher_fp' + B + 'grenade_launcher_reload_empty'],
                                         B.join(['sound', 'sfx', 'weapons', 'weapon_anims', 'rocket_reload_e']), -22.5),
            'gl_reload_full_balanced': (['grenade_launcher_fp' + B + 'grenade_launcher_reload_full'],
                                        B.join(['sound', 'sfx', 'weapons', 'weapon_anims', 'rocket_reload_f']), -22.5),
        },
        'stretch': {'gl_reload_empty_balanced': 1.02, 'gl_reload_full_balanced': 1.02},
        # BOOT 5 (user): 'push the first beep further back so an instant shot doesn't play it' --
        # 0.3 s of silence before the beep: the first beep at 0.3 s, then every 0.8 s while held
        # (a tap releases sooner; full charge at 0.5 s)
        'lead': {'gl_charge_loop': 0.3},
    },

    # ---------------------------------------------------------------------------------------
    # The weapon (h1_pickable_weapons.py --only grenade_launcher) on a COPY of the Halo 1 ROCKET
    # LAUNCHER (the hole-filler of the ratio: a one-at-a-time explosive launcher, its magazine,
    # reload, HUD and melee; the Brute Shot's template) firing GRENADES built on Halo 1's FRAG
    # GRENADE projectile (the yardstick: it bounces on every material, its timer starts on the
    # first bounce, it trails smoke, its explosion is the frag's). DEFAULT = REACH's OWN NUMBERS;
    # the ratio values are the balance rows.
    # THE CHARGE PAIR (user, 4a): trigger 1 = a copy of trigger 0 (`add_triggers`); trigger 0
    # charges (the plasma pistol's: charge hold 45 s, overcharged action none) -- an early release
    # fires trigger 0 (the bouncing grenade), a full charge fires trigger 1 on release (the
    # 'tethered' grenade: bursts on contact, Reach's tethered blast + the EMP)
    'pickable': {
        'weapon': GL + 'grenade launcher',
        'template': RL + 'rocket launcher',
        'world_model': GL + 'grenade launcher',
        'fp_model': GL + 'fp' + B + 'fp',
        'fp_anims': GL + 'fp' + B + 'fp',
        'label': 'gl',
        # the reserved pose donor: the shotgun (a two-handed rifle-class launcher, not the rocket's
        # shoulder pose; Reach's grenade launcher is a rifle)
        'teach': ('gl', 'sg'),
        'keys': {'first-person melee': 5},          # Reach melee_strike_1 primary keyframe 5
        'sounds': {'first-person ready': SND + 'gl_ready',
                   'first-person posing': SND + 'gl_pose',
                   'first-person melee': SND + 'gl_melee',
                   'first-person reload-empty': SND + 'gl_reload_empty',
                   'first-person reload-full': SND + 'gl_reload_full'},
        'extra_sounds': [SND + 'gl_reload_empty_balanced', SND + 'gl_reload_full_balanced'],
        'add_triggers': [0],
        # PENDING (user, boot 7): 'the grenade launcher needs to be hooked into the NO OVERCHARGE
        # SOUND WHEN EMPTY patch later' -- a charged pair (the plasma pistol's mechanism) charges
        # (and beeps, fire_loop on B out) with an empty magazine; that patch (not written yet) must
        # list this weapon
        # THE GRENADE (trigger 0, a tap). Reach: impact 25 (`collision`, accel 0.5) + the explosion
        # 0..180 over 0.75 -> 2.25. The impact on a copy of the frag explosion's table with no
        # radius (an impact deals its damage to what it hits); the explosion = the frag's effect
        # (x0.9 = 2.25 / 2.5 wu) around an own copy of the frag's damage, lower bound by the
        # sibling rule (Reach 0 / unset: 80 x 180/120 = 120). Flight 12.5 -> 7.5 wu/s, air gravity
        # 0.7, water 0.75, range 100, arming 0 (the frag's 1.5: Reach 0), timer 0.5 s on the
        # first bounce (the frag's rule = Reach's 'after first bounce off any surface'), oriented
        # along velocity (Reach's flag; the frag tumbles)
        'bullet': {'projectile': (FG + 'frag grenade', GL + 'grenade'),
                   'damage': (FG + 'explosion', GL + 'impact'),
                   'dmg': 25.0, 'acceleration': 0.5,
                   'fields': {'radius': (0.0, 0.0)},
                   'explosion': {'effect': (FG + 'effects' + B + 'explosion', GL + 'effects' + B + 'grenade explosion'),
                                 'part': FG + 'explosion',
                                 'scale': 0.9, 'out_dir': GL + 'effects' + B,
                                 'damage': (FG + 'explosion', GL + 'explosion'),
                                 'lower': 120.0, 'upper': (180.0, 180.0), 'radius': (0.75, 2.25),
                                 # 4b list 2 (Reach GL / Reach frag onto the H1 frag): aoe core
                                 # 0.4 x 0.6/0.54, instantaneous acceleration 4 x 2/2.25
                                 'fields': {'damage.aoe_core_radius': 0.4 * 0.6 / 0.54,
                                            'damage.instantaneous_acceleration': 4 * 2 / 2.25},
                                 'swaps': {B.join(['sound', 'sfx', 'weapons', 'frag grenade', 'expl']): SND + 'gl_explode'}},
                   # BOOT 2 PROBE (h1_projectile_probe): in flight the speed falls with DISTANCE
                   # (initial -> final over the 100 wu range: 12.26 at 4.95 wu); the first bounce
                   # cut it to ~7.4, then it SLID at a constant 7.4 wu/s for 12 s and burst at the
                   # range (99.5 wu) -- the 0.5 s 'on first bounce' fuse never ran (variant B, no
                   # range: 27-38 s). BOOT 3 (probe): final 0 -> it slows, settles, and bursts ~0.45 s
                   # after settling; the test variant's fuse from launch ('immediately' 1.5 s) burst
                   # at 1.47 s exactly -- not taken (it would burst mid-air on long lobs)
                   # final velocity 0 (a final above 0 is a speed floor: no rest, no fuse); the flight
                   # slows with distance over the range (12.5 -> 0 over 100 wu; Reach 12.5 -> 7.5
                   # over its 1-10 wu acceleration range) -- the long-lob speed is the cost
                   'velocity': (12.5, 0.0), 'range': 100.0,
                   'model': GL + 'grenade' + B + 'grenade',
                   'proj_fields': {'proj_attrs.physics.air_gravity_scale': 0.7,
                                   'proj_attrs.physics.water_gravity_scale': 0.75,
                                   'proj_attrs.detonation.arming_time': 0.0,
                                   # THE FUSE (boot 5, user's pick): from LAUNCH -- Halo 1 runs an 'on
                                   # first bounce' fuse only from rest (boot 3 probe). Reach: 0.5 s
                                   # after the first bounce; a typical first bounce comes at ~0.7 s
                                   # (the probes: 0.43-0.73 s) -> 1.2 s from launch (measured 1.47 s
                                   # for a 1.5 s fuse: exact). Lost: a long lob bursts in the air
                                   'proj_attrs.detonation_timer_starts': 'immediately',
                                   'proj_attrs.detonation.timer': (1.2, 1.2),
                                   # 4b list 2: Reach 0,0 = unset (a ratio on it degenerates):
                                   # 0..100 = the range (the Brute Shot's)
                                   'proj_attrs.physics.air_damage_range': (0.0, 100.0),
                                   'proj_attrs.detonation.minimum_velocity': 0.0,
                                   'proj_attrs.flags.oriented_along_velocity': True},
                   # REACH'S RULES as Halo 1 responses: units DETONATE (Reach: 'only against
                   # units' detonate, except a slow roll under 5 wu/s that bounces); the world
                   # REFLECTS (the frag's) and detonates on a steep fast hit (Reach: 75-90 deg AND
                   # 7.5-14 wu/s). Halo 1's angle convention is UNVERIFIED (0 = grazing assumed,
                   # as Reach's 'between'): boot 1 checks it
                   'default_responses': {'detonate': UNITS},
                   'reflect': [{'materials': UNITS, 'angle_deg': (0.0, 90.0), 'velocity': (0.0, 5.0),
                                'effect_from_default': False},
                               {'materials': WORLD, 'response': 'detonate', 'angle_deg': (75.0, 90.0),
                                'velocity': (7.5, 14.0), 'effect_from_default': False,
                                # BOOT 4 (user): 'no bounce at all now' (the frag's 0.8 / 0.9 keep
                                # ~10 %). BOOT 5 A/B: middle friction 0.6 (a few hops, the fuse after
                                # it settles) vs Reach's 0.42 + a fuse from LAUNCH -- the user took
                                # the latter ('works well, if that is the normal bounciness')
                                'parallel_friction': 0.42, 'perpendicular_friction': 0.42}],
                   # contact detonations play the projectile's OWN explosion (boot 5: the frag's
                   # per-material ones -- a dirt sound, an empty stone effect -- stood in for it)
                   'clear_detonation_effects': True,
                   # BOOT 3 PROBE + USER (2026-10-12): Halo 1's 'on first bounce' fuse runs from when
                   # the grenade COMES TO REST (0.45 s after it settled), and a FINAL VELOCITY is a
                   # speed floor (boot 2: slid at 7.4 wu/s for 12 s, never at rest, never fused).
                   # Reach's 0.42 friction (boot 3) bounced for 2-3 s -> burst 2.6-3.5 s after
                   # launch; Reach bursts 0.5 s after the FIRST bounce. User: 'Frag friction' --
                   # the frag's own frictions (one bounce keeps ~10 % of the speed: the frag burst
                   # ~0.8 s after its first bounce); Reach's few hops are lost
                   # the frag's smoke trail kept (attachment 0 at `smoke`), its own light dropped:
                   # Reach's flare instead (EMBER, 0.15 wu) at `glow`
                   'keep_attachments': (0,),
                   'glow': {'light': (r'weapons\fuel rod gun\fuel rod exhaust', GL + 'grenade glow'),
                            'flare': GL + 'grenade glow', 'rgb': EMBER, 'flare_radius': 0.15,
                            'marker': 'glow'},
                   'hum': {'like': B.join(['sound', 'sfx', 'weapons', 'rocket launcher', 'rl_projectile']),
                           'loop': SND + 'gl_projectile', 'tag': SND + 'gl_projectile', 'marker': ''},
                   # the BOUNCES: the frag's reflection effects as own copies playing Reach's
                   # frag_bnc (impact_tint with no particle match: the sound swap only)
                   'impact_tint': {'match': (), 'rgb': None, 'out': GL + 'effects' + B + 'impact' + B,
                                   'sounds': {B.join(['sound', 'sfx', 'weapons', 'frag grenade', 'bouncedirt']): SND + 'gl_bounce',
                                              B.join(['sound', 'sfx', 'weapons', 'frag grenade', 'bouncemetal']): SND + 'gl_bounce_metal'}},
                   'triggers': [0]},
        # THE RELEASE (trigger 1, held past the charge): Reach's tethered blast 0..180 over 0.001
        # -> 1 (lower: the sibling rule, 120) + the EMP 100 `emp` over 0.25 -> 2.5 on Reach's emp
        # table (energy_shield_thin x0.5: Elite + cyborg shields; _thick x0.25: Jackal; the rest
        # 0) -- bursts on CONTACT with anything (no bounce: Reach's release IS the detonation)
        'projectiles': [{
            'projectile': (FG + 'frag grenade', GL + 'grenade release'),
            'damage': None,
            # BOOT 1 (user): 'explosion looks the same for both -- if the second type is smaller it
            # should be smaller, and add some effect to resemble the EMP (electric would be perfect)'.
            # Visual x0.45 (Reach's tethered blast 1 wu against 2.25) + Halo 1's own electric burst:
            # the plasma grenade's `detonation start` (60 `plasma electric bolts` 0.35-0.45 + 60
            # blue `flash h shield impact`), at location 0 (boot 2: none showed at `normal`; the frag draws all at 0)
            'explosion': {'effect': (FG + 'effects' + B + 'explosion', GL + 'effects' + B + 'release explosion'),
                          'part': FG + 'explosion',
                          'scale': 0.45, 'out_dir': GL + 'effects' + B + 'release' + B,
                          # BOOT 6 (user): 'the blast is smaller, still no sparks'. Boot 7 found the
                          # placement by colour: particles at 'normal' (location 1, the surface)
                          # created all at once ('start') show; 'gravity' and location 0 never did.
                          # USER after boot 7: 'the EMP explosion didn't look good yet' (the borrowed
                          # plasma-grenade bolts + flash). REACH'S EMP (fx\airborne_super_detonation
                          # `emp` event, 0.15 s): blast_radius is 'disabled for debugging', so only
                          # EMP_PULSE draws -- a globe emitter (bounding ~1.48 wu) of fx\particles\
                          # plasma\emp_pulse: Reach's emp_mask (a RING of electric wisps, alpha)
                          # coloured over its life by the emp gradient (pale cyan 162 / 226 / 252 at
                          # birth -> 87 / 195 / 240 -> 33 / 150 / 199 -> deep blue 13 / 85 / 116),
                          # random rotation + mirroring, scrolling plasma clouds. HALO 1: an own
                          # particle (the camera-facing shield flash copied) with its OWN sprite =
                          # Reach's emp_mask (white, the mask in alpha), 3 a burst, 1.2-1.5 wu growing
                          # x0.6 -> x1 over 0.35-0.45 s while it fades, random mirroring + spin, a
                          # random tint between Reach's birth and mid colours (Halo 1 has no colour
                          # over life). Not reproduced: the scrolling clouds, the colour over life
                          # BOOTS 9-12 (user): green + red seen, never blue -- the raw a8r8g8b8 sprite, then DXT5,
                          # then the stock headers, then 32 px DXT1: no blue; a byte COPY of the stock flash under an
                          # own path DID draw (red, boot 12). Decoded, the stock flash is OPAQUE (alpha 255, the shape
                          # on black); ours colour-keyed 37 % of its texels transparent -- and the blue entry was
                          # always the event's FIRST added particle. BOOT 13, by colour: GREEN control first, BLUE the
                          # keyed ring second, YELLOW the ring OPAQUE on black (the stock form), RED the stock copy
                          # BOOTS 9-14 (user): a particle sprite draws ONLY from a stock sheet's own tag layout --
                          # every rebuilt sheet (raw a8r8g8b8, DXT5, stock headers, 32 px DXT1 keyed or opaque, the
                          # first or a later slot) failed; a byte copy of the stock flash drew, and Reach's ring
                          # SPLICED into it (pixels only) drew (boot 14: 'a green and blue explosion'). FINAL: the
                          # ring opaque on black spliced into the 128 px `shield charge rings` sheet (one full-frame
                          # sprite), the release explosion's own visuals back, the green control gone
                          'add_particles': [_emp_test((162 / 255.0, 226 / 255.0, 252 / 255.0), out='emp pulse',
                                                      rgb2=(87 / 255.0, 195 / 255.0, 240 / 255.0),
                            bitmap={'compile': 'splice', 'opaque': True, 'out': 'emp pulse',
                                                              'size': 128,
                                                              'container': B.join(['effects', 'particles', 'flash', 'bitmaps',
                                                                                   'shield charge rings'])})],
                          'damage': (FG + 'explosion', GL + 'release explosion'),
                          'lower': 120.0, 'upper': (180.0, 180.0), 'radius': (0.001, 1.0),
                          # the same ratio on Reach's tethered blast (core 0.2, acceleration 3)
                          'fields': {'damage.aoe_core_radius': 0.4 * 0.2 / 0.54,
                                     'damage.instantaneous_acceleration': 4 * 3 / 2.25},
                          'swaps': {B.join(['sound', 'sfx', 'weapons', 'frag grenade', 'expl']): SND + 'gl_explode'},
                          'add_damage': [{'from': FG + 'explosion', 'out': GL + 'emp',
                                          'lower': 0.0, 'upper': (100.0, 100.0), 'radius': (0.25, 2.5),
                                          'zero': True,
                                          # Reach's EMP has no shove (acceleration 0), core 0.6
                                          'fields': {'damage.aoe_core_radius': 0.4 * 0.6 / 0.54,
                                                     'damage.instantaneous_acceleration': 0.0},
                                          'mods': {'elite_energy_shield': 0.5, 'cyborg_energy_shield': 0.5,
                                                   'jackal_energy_shield': 0.25}}]},
            'velocity': (12.5, 0.0), 'range': 100.0,            # the tap's flight (above)
            'model': GL + 'grenade' + B + 'grenade',
            'proj_fields': {'proj_attrs.physics.air_gravity_scale': 0.7,
                            'proj_attrs.physics.water_gravity_scale': 0.75,
                            'proj_attrs.detonation.arming_time': 0.0,
                            'proj_attrs.detonation.timer': (0.0, 0.0),
                            'proj_attrs.physics.air_damage_range': (0.0, 100.0),
                            'proj_attrs.detonation.minimum_velocity': 0.0,
                            'proj_attrs.flags.oriented_along_velocity': True},
            'default_responses': {'detonate': UNITS + WORLD},
            'clear_detonation_effects': True,
            # the frag's reflection effects ride along on every response: own bounce sounds too
            # (port_sound_refs does not read a projectile's responses -- found by hand)
            'impact_tint': {'match': (), 'rgb': None, 'out': GL + 'effects' + B + 'impact' + B,
                            'sounds': {B.join(['sound', 'sfx', 'weapons', 'frag grenade', 'bouncedirt']): SND + 'gl_bounce',
                                       B.join(['sound', 'sfx', 'weapons', 'frag grenade', 'bouncemetal']): SND + 'gl_bounce_metal'}},
            'keep_attachments': (0,),
            'glow': {'light': (r'weapons\fuel rod gun\fuel rod exhaust', GL + 'grenade release glow'),
                     'flare': GL + 'grenade release glow', 'rgb': ARM_RED, 'flare_radius': 0.15,
                     'marker': 'glow'},
            'hum': {'like': B.join(['sound', 'sfx', 'weapons', 'rocket launcher', 'rl_projectile']),
                    'loop': SND + 'gl_projectile', 'tag': SND + 'gl_projectile', 'marker': ''},
            'triggers': [1]}],
        # Reach: fire recovery 0.5 s (rounds per second 0 = recovery-limited) = 2/s
        # 4b list 2 (Reach GL / Reach RL onto the H1 RL): first person offset 0,0,0 (Reach's GL 0,
        # its RL -0.05: a zero on one side), illumination recovery 0.3 x 0.1/0.2
        'trigger': {'rounds_per_second': (2.0, 2.0), 'first_person_offset': (0.0, 0.0, 0.0),
                    'illumination_recovery_time': 0.15},
        # Reach: minimum error 0.15, error angle 0 -> 0.4
        'error_deg': {'minimum_error': 0.15, 'error_angle': (0.0, 0.4)},
        # Reach: 1 loaded, 8 at pickup, 16 most, 1 reloaded (63 fr empty, 59 full; reload time 0 =
        # the animation's -- Halo 1 needs a number: 2.1 s)
        'magazine': {'rounds_loaded_maximum': 1, 'rounds_reloaded': 1,
                     'rounds_total_initial': 8, 'rounds_total_maximum': 16,
                     'reload_time': 2.1},
        # Reach aim assist, absolute
        'aiming': {'autoaim_angle': 4.0, 'autoaim_range': 15.0,
                   'magnetism_angle': 8.0, 'magnetism_range': 15.0,
                   # 4b list 3: Reach GL 2 deg, its RL 0 (a zero on one side: the source value)
                   'deviation_angle': 2.0},
        # the CHARGE as an object function (the arm light): out 0 = the rocket's muzzle flash (A in =
        # integrated light), out 1 = the plasma pistol's function 3 (`one` x B in) with weapon B in =
        # primary charged -> B out = the charge
        # the CHARGE CUE (boot 3, user): a start / loop sound_looping at the muzzle, scaled by B out
        # (the charge): it plays from the press while the charge builds and holds (a tap blips)
        'fire_loop': {'like': B.join(['sound', 'sfx', 'weapons', 'plasma rifle', 'charging']),
                      'start': '', 'loop': SND + 'gl_charge_loop', 'end': '',
                      'tag': SND + 'gl_charging', 'marker': 'primary trigger', 'scale': 'B_out'},
        'obje_functions': [{'from': RL + 'rocket launcher', 'index': 0},
                           {'from': 'weapons' + B + 'plasma pistol' + B + 'plasma pistol', 'index': 3}],
        'fields': {
            'weap_attrs.B_in': 'primary_charged',
            # 4b list 2: active camo ding 1 x 0.75/1
            'weap_attrs.interface.active_camo_ding': 0.75,
            # THE CHARGE: trigger 0 charges 0.5 s (no Reach number: the tether starts at the press;
            # 0.5 s = Reach's fire recovery, a tap stays a tap) and holds the charge 45 s (the
            # plasma pistol's); trigger 1 fires the release, never charges itself
            'weap_attrs.triggers.0.charging.charging_time': 0.5,
            'weap_attrs.triggers.0.charging.charge_hold_time': 45.0,
            'weap_attrs.triggers.0.charging.overcharged_action': 'none',
            'weap_attrs.triggers.1.charging.charging_time': 0.0,
            'weap_attrs.triggers.1.charging.charge_hold_time': 0.0,
            # Reach's grenade launcher has NO zoom (zoom levels 0); the rocket's 2x goes, and its
            # zoom sounds with it (the Brute Shot)
            'weap_attrs.aiming.zoom_levels': 0,
            'weap_attrs.interface.zoom_in_sound.filepath': '',
            'weap_attrs.interface.zoom_out_sound.filepath': '',
            # STEP 6: the rocket's ammo box tops it up RATIO-SCALED (the Brute Shot): 2 x carry
            # 16/8 = 4 (the same in both versions: the carry is 16 default and balanced)
            'weap_attrs.magazines.0.magazine_items.0.rounds': 1,
            # BOOT 4 (user): 'this will come up later -- try setting the ammo pickup to frag
            # grenades': the magazine item = Halo 1's FRAG GRENADE equipment, 1 round a grenade
            # (TEST: does the pickup still also give the grenade?)
            'weap_attrs.magazines.0.magazine_items.0.equipment.filepath': FG + 'frag grenade',
            # the rocket's empty effect is the AR dry fire SOUND: the GL's own (Reach: the BR's)
            'weap_attrs.triggers.0.firing_effects.0.empty_effect.filepath': SND + 'gl_dryfire',
            'weap_attrs.triggers.1.firing_effects.0.empty_effect.filepath': SND + 'gl_dryfire',
            'weap_attrs.interface.pickup_sound.filepath': SND + 'gl_ammo',
            'item_attrs.collision_sound.filepath': SND + 'gl_drop',
            'obje_attrs.collision_model.filepath': GL + 'grenade launcher',
            'obje_attrs.bounding_radius': 0.24},
        # THE MUZZLE-FLASH RULE (closing check 10, before boot 1). Reach's FIRST-PERSON flash
        # (fx\firing.effect, set `1st_person`): muzzle_flash_round (bounding radius 0.053 wu),
        # glow_soft (0.133) and muzzle_smoke (0.785), all at primary_trigger, no offsets, no
        # sparks, no casing (+ the firing_1p light). The rocket's (h1_effect_particles): ONE
        # `flash h ar` 0.07-0.1 at the muzzle + smoke 0.12-0.15 + a back-blast flash and 24-28
        # smoke at `primary ejection` (the GL has no such marker). -> the SHOTGUN family (the Brute
        # Shot's): `flash h generic` 0.10-0.125 (~ Reach's glow), smoke 0.125-0.375; its sparks
        # trail (Reach has none) and casing dropped, the fire sound kept once (event 0)
        'sound_effects': {
            'firing_effect': (RL + 'effects' + B + 'fire rocket', GL + 'effects' + B + 'fire grenade',
                              {B.join(['sound', 'sfx', 'weapons', 'shotgun', 'fire']): SND + 'gl_fire'},
                              {'copy_from': r'weapons\shotgun\effects\shotgun firing',
                               'drop_particles': ('casing', 'sparks'),
                               'drop_event_parts': {1: [B.join(['sound', 'sfx', 'weapons', 'shotgun', 'fire'])]}})},
        # Reach shares strike_melee with its rocket: x1 = the H1 rocket's own melee (copied)
        'melee': (RL + 'melee', GL + 'melee'),
        'melee_response': RL + 'melee_response',
        'messages': ('Picked up a grenade launcher', 'Picked up %d rounds for grenade launcher'),
        'icon': 'grenade launcher',
        # the ROCKET's HUD with Reach's grenade launcher crosshair at the reserved 31; one tick for
        # the one round. Reach's chud: `crosshair` = hud_reticles #12 at 1.3 (the frame box, the two
        # arcs, the drop ticks), `pitch` = falcon\pitch (a whole 64 x 1024 bitmap, 140 deg, a label
        # every 70 px = 10 deg, 0 deg at row ~519) at (1.6, 0.7), `auto` = grenade_launcher #1 at 0.5
        # right-aligned at -47. SIZED FROM THE USER'S REACH SCREENSHOT (1080p, 2026-10-12): the frame
        # 74 x 224 px, the ring ~80 px, 10 deg = 29.5 px, labels 30 .. -10 inside the frame (plain
        # ticks below), the AUTO square ~70 px left of the centre. Halo 1: 1080p px = sheet px x 0.75
        # x the overlay (the Plasma Repeater's calibration) -> the frame 182 sheet px x 0.75 x 1.6 =
        # 218 px; the ladder stretched 0.642 x 0.281 (29.5 / 70 px a degree; the chud's 1.6 : 0.7),
        # its window rows 275..600 (+30 .. -10), the 0 mark on the centre (offset -7); `split` 100:
        # Reach's frame (alpha ~51) and drop ticks (~71) grow in their own band (one band left them
        # under grow_to's threshold 96 -- erased in the simulation). STATIC: the ladder at 0 deg
        # (it scrolls with the aim in Reach; Halo 1's HUD cannot), AUTO lit (Halo 1 has no MANUAL
        # mode to switch to); not reproduced: the tether triangle and the MANUAL icon
        'hud': {'donor': RL + 'rocket_launcher', 'out': GL + 'grenade launcher',
                'reticle': (R + r'ui\chud\bitmaps\hud_reticles', 12, 'grenade launcher'),
                'reticle_layers': [(R + r'ui\chud\bitmaps\falcon\pitch.bitmap', None, 1.0,
                                    {'crop': (0, 275, 64, 600), 'stretch': (0.642, 0.281),
                                     'offset': (0.0, -7.0)}),
                                   (R + r'ui\chud\bitmaps\grenade_launcher', 1, 0.385,
                                    {'offset': (-46.0, 0.0)})],
                'reticle_split': 100,
                # BOOT 1 (user): 'size is good, but looks pretty bad compared to the original' -- the
                # art was drawn small in the sheet and magnified x1.6 (blur, unreadable labels). Drawn
                # x1.35 in the sheet (the frame ~246 of 256 px) and magnified 1.6 / 1.35 = x1.185: the
                # same on-screen size; the simulation resolves the labels, pitch and drop ticks
                # BOOT 2 (user): 'better, but still not good enough -- it's just an image, can we
                # copy it like the Needle Rifle's glyphs?' -- MCC draws crosshairs only from the
                # stock sheets (~0.5 screen px a sheet px), so the cell is the limit: SUPERSAMPLED x2
                # (a 512 px cell, Reach's sprites at their NATIVE 4K density -- not shrunk to Halo
                # 3's and magnified back), drawn at 1.6 / 1.35 / 2 = x0.59: the same on-screen size
                # from finer pixels; strokes grown to 2 px of the 512 cell (~0.9 screen px). The
                # 1080p simulation against the user's Reach screenshot: the closest of 3
                # BOOT 3 (user): 'the best crosshair so far -- remember this setting; a small blue
                # pixel at the top left corner of the box' -- the frame touched the cell's top edge
                # (rows 0-1; bilinear edge bleed): x1.3 (a ~10 px margin), the overlay x1.6 / 1.3 / 2
                'reticle_scale': 1.3, 'reticle_overlay': 1.6 / 1.3 / 2,
                'reticle_supersample': 2,
                'reticle_min_width': 2,
                'ammo_meter': {'sizes': (1,), 'base': GL + 'bitmaps' + B + 'grenade_launcher_ammo'},
                'flash_base': 2},
        'palette_levels': LEVELS,
    },

    # weapon_ports_catalog.json (make_port_catalog_h1_ports.py grenade_launcher). DEFAULT = Reach's
    # own numbers in the tags; BALANCED = the FRAG ratio, its holes by the RL ratio (step 4a, user
    # 2026-10-12). Assembly Halo1 units: angles in degrees, velocity in wu per TICK
    'catalog': {
        'entry': {
            'weapon': 'Grenade Launcher', 'source': 'Halo Reach', 'donor': 'Rocket Launcher', 'default_on': False,
            'desc': "Halo Reach's Grenade Launcher: its model, first-person animations, sounds and "
                    "numbers. A single-shot launcher: a tap fires a grenade that explodes on "
                    "enemies or a hard hit and otherwise bounces, bursting half a second after the "
                    "first bounce. Hold the trigger and release to fire a grenade that bursts on "
                    "contact with an EMP that strips shields.",
            'balance_desc': "Measured against the Frag Grenade, with the Rocket Launcher for what a "
                            "thrown grenade lacks: 135 damage over 2.5 m (the frag's family), a "
                            "0.4 s fuse, one shot every 1.25 s, a shorter reach, a smaller EMP and "
                            "Halo 1-style aim assist.",
            # step 9: the balanced reload = H1 rocket reload-empty 125 fr x 63/116 = 67.9 over the
            # built 63 (x1.078), reload-full 111 x 59/116 = 56.5 over 59 (x0.957): ONE multiplier
            # (the DMR's) x1.02, stretched sounds; swap (ONE multiplier, the ready's): H1 rocket
            # ready 22 fr x Reach GL 21 / Reach rocket 26 = 17.8 over the built 21 = x0.85
            'anims': {'reload': 1.02, 'swap': 0.85},
            'anim_sounds': {'reload': {'mult': 1.02, 'from': SND + 'gl_reload_empty',
                                       'to': SND + 'gl_reload_empty_balanced'}},
            'balance': [
                # the grenade's explosion: 120 x 180/160 (frag), lower 80 x 135/120 (the sibling
                # rule: Reach's lower bounds are 0 / unset); radius 1.5 x 0.75/0.675, 2.5 x 2.25/2.25
                row('jpt!', GL + 'explosion', 'Damage Lower Bound', 90.0, 120.0, 'Grenade Damage'),
                row('jpt!', GL + 'explosion', 'Damage Upper Bound', 135.0, 180.0, 'Grenade Damage'),
                row('jpt!', GL + 'explosion', 'Damage Upper Bound Max', 135.0, 180.0, 'Grenade Damage'),
                row('jpt!', GL + 'explosion', 'Radius', 1.667, 0.75, 'Grenade Damage'),
                row('jpt!', GL + 'explosion', 'Radius Max', 2.5, 2.25, 'Grenade Damage'),
                # the impact: a hole (the frag has none) -> RL 0 x 25/200 = 0 (a zero on one side ->
                # zero in balanced, the Needle Rifle's rule)
                row('jpt!', GL + 'impact', 'Damage Lower Bound', 0.0, 25.0, 'Grenade Damage'),
                row('jpt!', GL + 'impact', 'Damage Upper Bound', 0.0, 25.0, 'Grenade Damage'),
                row('jpt!', GL + 'impact', 'Damage Upper Bound Max', 0.0, 25.0, 'Grenade Damage'),
                # the release: the tethered blast by the frag ratio (135, lower 90, radius 1.5 x
                # 0.001/0.675, 2.5 x 1/2.25) + the EMP by the plasma pistol overcharge (H1 70 x
                # Reach EMP 100 / Reach overcharge 200) = 35 on the overcharge's shield modifiers
                row('jpt!', GL + 'release explosion', 'Damage Lower Bound', 90.0, 120.0, 'Grenade Damage'),
                row('jpt!', GL + 'release explosion', 'Damage Upper Bound', 135.0, 180.0, 'Grenade Damage'),
                row('jpt!', GL + 'release explosion', 'Damage Upper Bound Max', 135.0, 180.0, 'Grenade Damage'),
                row('jpt!', GL + 'release explosion', 'Radius', 0.002, 0.001, 'Grenade Damage'),
                row('jpt!', GL + 'release explosion', 'Radius Max', 1.11, 1.0, 'Grenade Damage'),
                row('jpt!', GL + 'emp', 'Damage Upper Bound', 35.0, 100.0, 'EMP'),
                row('jpt!', GL + 'emp', 'Damage Upper Bound Max', 35.0, 100.0, 'EMP'),
                row('jpt!', GL + 'emp', 'Radius', 0.556, 0.25, 'EMP'),
                row('jpt!', GL + 'emp', 'Radius Max', 2.78, 2.5, 'EMP'),
                row('jpt!', GL + 'emp', 'Elite Energy Shield', 1.5, 0.5, 'EMP'),
                row('jpt!', GL + 'emp', 'Cyborg Energy Shield', 0.6, 0.5, 'EMP'),
                row('jpt!', GL + 'emp', 'Jackal Energy Shield', 1.0, 0.25, 'EMP'),
                # flight: the throw speed x1 (no velocity rows); gravity 1.0 x 0.7/0.9, water 1.0 x
                # 0.75/0.75; the fuse 0.5 x 0.5/0.625 (Reach frag 0.6-0.65); range: a hole -> RL
                # 128 x 100/175 (the release has no fuse: it bursts on contact)
                row('proj', GL + 'grenade', 'Air Gravity Scale', 0.778, 0.7, 'Projectile'),
                row('proj', GL + 'grenade', 'Water Gravity Scale', 1.0, 0.75, 'Projectile'),
                # the fuse from launch (boot 5): the typical first bounce 0.7 s + the frag ratio's
                # 0.4 (Reach 0.5 x H1 frag 0.5 / Reach frag 0.625) = 1.1 (default 0.7 + 0.5)
                row('proj', GL + 'grenade', 'Timer', 1.1, 1.2, 'Projectile'),
                row('proj', GL + 'grenade', 'Timer Max', 1.1, 1.2, 'Projectile'),
                row('proj', GL + 'grenade', 'Maximum Range', 73.1, 100.0, 'Projectile'),
                row('proj', GL + 'grenade release', 'Air Gravity Scale', 0.778, 0.7, 'Projectile'),
                row('proj', GL + 'grenade release', 'Water Gravity Scale', 1.0, 0.75, 'Projectile'),
                row('proj', GL + 'grenade release', 'Maximum Range', 73.1, 100.0, 'Projectile'),
                # holes -> the RL ratio: 2.0 s x 0.5/0.8 = 1.25 s (both triggers)
                row('weap', GL + 'grenade launcher', 'Rounds Per Second', 0.8, 2.0, 'More Shooting', block='Triggers'),
                row('weap', GL + 'grenade launcher', 'Rounds Per Second Max', 0.8, 2.0, 'More Shooting', block='Triggers'),
                # aim: 0 x 4/5, 35 x 15/60; 12 x 8/10, 35 x 15/25
                row('weap', GL + 'grenade launcher', 'Autoaim Angle', 0.0, 4.0, 'Autoaim'),
                row('weap', GL + 'grenade launcher', 'Autoaim Range', 8.75, 15.0, 'Autoaim'),
                row('weap', GL + 'grenade launcher', 'Magnetism Angle', 9.6, 8.0, 'Magnetism'),
                row('weap', GL + 'grenade launcher', 'Magnetism Range', 21.0, 15.0, 'Magnetism'),
            ]},
    },

    # step 4b (port_field_audit.py --port grenade_launcher): the source pair against the target
    # pair; the yardstick is the FRAG for the grenade and its damage, the ROCKET for the weapon
    # (the frag is thrown -- no weapon tag)
    'field_audit': {
        'source_kit': 'HREK',
        'source': {'weapon': (RW + r'\grenade_launcher.weapon', r'objects\weapons\support_high\rocket_launcher\rocket_launcher.weapon'),
                   'projectile': (RW + r'\projectiles\grenade_launcher_grenade.projectile',
                                  r'objects\weapons\grenade\frag_grenade\frag_grenade.projectile'),
                   'damage_effect': (RW + r'\projectiles\damage_effects\grenade_launcher_grenade_explosion.damage_effect',
                                     r'objects\weapons\grenade\frag_grenade\damage_effects\frag_grenade_explosion.damage_effect')},
        'target': {'weapon': (GL + 'grenade launcher.weapon', RL + 'rocket launcher.weapon'),
                   'projectile': (GL + 'grenade.projectile', FG + 'frag grenade.projectile'),
                   'damage_effect': (GL + 'explosion.damage_effect', FG + 'explosion.damage_effect')}},

    # the dry test: a30 (Covenant within seconds of the landing), Reach's own loadout (1 + 8)
    'test': {'level': 'a30', 'rounds': (1, 8), 'grunt': None, 'elite': None},
})
