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
            # the fuse: 0.5 x 0.5/0.6, 0.5 x 0.5/0.65 -> 0.4 (mean); arming 1.5 x 0/1.4 = 0
            'timer': 0.4, 'arming': 0.0,
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
    # step 11: the source game's ai\generic entry (19 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo Reach', 'from_map': 'haloreach\\maps\\m10.map', 'from_weapon': 'objects\\weapons\\rifle\\grenade_launcher\\grenade_launcher'},
)
