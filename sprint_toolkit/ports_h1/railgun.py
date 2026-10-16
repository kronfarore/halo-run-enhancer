r"""Railgun (Halo 4, wave C7): IN PROGRESS -- step 4a decided (user, 2026-10-16); the port sections
(model / retarget / pickable / sounds / catalog / test) follow.

HALO 4 (H4EK 2026-10-16, h3_weapon_values --kit h4 + h4_projectile_summary + h4_flag_names): the SOURCE is
the campaign tag `storm_rail_gun_pve` (user, over the MP tag). MP vs _pve: the charged (hold) time 0.5 vs
1.5 s, error 0.2 vs 0.15 -> 0.8, the projectile (MP impact 60 `bullet` + blast 120 explosion_large over 0.675
-> 1.0; _pve 120 `needle` + 180 explosion_small over 0.55 -> 1.0), _pve's ammo-box magazine entry and dry-fire
loop attachment, MP's pickup sound, abandonment times.
_pve: trigger `charge-with-magazine` -- charging 0.75 s, then held charged up to 1.5 s, 'discharge' after
(fires by itself); an early release fires barrel 0, which has NO projectile (nothing comes out); the charged
release fires barrel 1 (the slug). Recovery 0.6 s, 1 loaded / 4 / 6, every reload = reload_empty 82 fr
(reload_full 59 never plays on a 1-round magazine); heat 0.36 a round, loss 1/s (inert at one round a
reload); error 0.15 -> 0.8 (bloom decel 0.5); no zoom; aim assist mode 0 (unzoomed) 2.5/25 7.5/25 (the
struct 5/16 10/16); melee strike_melee. Flags (by name): weapon 'cannot fire at maximum age' (no age: inert),
'hide FP weapon when in iron sights', 'allows binoculars'; barrels 'only reload if all barrels idle' (barrel
0 also "don't clear fire bit after recovering").
THE SLUG (storm_rail_gun_bolt_pve): 100 wu/s flat, range 0 (unset), no gravity, 'oriented along velocity',
'disable instantaneous first tick'. Impact 120 (`needle`, accel 0.05) + detonation 0..180 explosion_small
over 0.55 -> 1.0, core 0.54 (accel 2.5, 'detonates explosives'); no aoe spike bump. Responses: the table
Halo 4 reads (`material response`, C5) = default ATTACH, energy_shield_invulnerable bounce; timer 0.2 s
'when at rest' + 'detonation max time if attached' = it STICKS and bursts 0.2 s later. No overpenetration."""
from ._common import B, reserved, row  # noqa: F401

H4 = 'h4:'                                          # an H4EK path (h4_tags)
SW = r'objects\weapons\rifle\storm_rail_gun'
SFP = r'objects\characters\storm_fp\weapons\rifle\fp_rail_gun\storm_fp_rail_gun'
RG = 'weapons\\railgun\\'
SND = 'sound\\weapons\\railgun_port\\'
RL = 'weapons\\rocket launcher\\'
LEVELS = ['a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40']

PORT = reserved(
    order=32, wave='C7', name='Railgun', source='Halo 4',
    messages=(97, 98), icon=52, reticle=41, label='rg', teach_from='rl',
    sound_dir='sound\\weapons\\railgun_port', weapon_dir='weapons\\railgun',
    yardstick={
        # step 4a (user, 2026-10-16; h1_role_compare.py railgun)
        'pick': 'Rocket Launcher',
        'reason': ("user, step 4a 2026-10-16: source = the _pve tag; the ROCKET LAUNCHER's role (a 1-round "
                   "power weapon with a blast; 2 hits on an Elite major / commander / Hunter on Legendary, "
                   "as Halo 4's own). DEFAULT = Halo 4's own numbers, BALANCED = the ROCKET ratio rows (H1 "
                   "rocket x H4 railgun / H4 rocket, the direct hit 300 / 440 with Halo 4's split). The "
                   "slug's hit AND blast on the ROCKET's damage table (both versions: the rows change damage "
                   "only). Detonation (user): STICK + a 0.2 s fuse at rest (Halo 4's attach + 'detonation max "
                   "time if attached'; the Sticky Detonator's recipe). Rejected: the Fuel Rod ratio (140.6, "
                   "Hunters immune on its table), the Sniper ratio (378.8 at 35.7 wu/s, Flood 6-9 hits)"),
        # DEFAULT = Halo 4's own numbers; these are the BALANCED rows. Halo 4 railgun / rocket: direct 120 +
        # 180 = 300 / 200 + 240 = 440 (no aoe spike in either); blast radius 0.55 -> 1.0 / 0.9 -> 2.5;
        # recovery 0.6 / 0.8 s; 1 / 2 loaded, 4 / 4, 6 / 6; reload 82 / 116 fr; 100 flat / 10 -> 20 wu/s;
        # range 0 (unset) / 175; aim (mode 0) 2.5/25 7.5/25 / 5/60 10/25; error 0.15 -> 0.8 / 0; no zoom /
        # 1.8x. H1 rocket: 315 (all blast) over 0.5 -> 2.0, 2.0 s, 2 / 4 / 8, 125 fr, 12 -> 10 wu/s, 128,
        # aim 0/35 12/35, error 0, zoom 2x, melee 55
        'balanced': {
            'damage': 214.8,             # 315 x 300/440
            'impact': 85.9,              # Halo 4's split: x 120/300
            'blast': 128.9,              #                 x 180/300
            'radius': (0.306, 0.8),      # 0.5 x 0.55/0.9, 2.0 x 1.0/2.5
            'charge_s': 0.75,            # KEPT: no rocket charges (the Plasma Launcher's 'charge kept')
            'charge_hold_s': 1.5,        # KEPT, likewise
            'fire_recovery_s': 1.5,      # 2.0 x 0.6/0.8 (moot on a 1-round magazine)
            'magazine': 1,               # 2 x 1/2
            'rounds_total_initial': 4,   # 4 x 4/4
            'rounds_total_maximum': 8,   # 8 x 6/6
            'reload_fr': 88.4,           # 125 x 82/116
            'velocity': 120.0,           # 12 x 100/10 (initial; flat -- the rocket's 12 -> 10 vs 10 -> 20
                                         # would give a decelerating slug, 120 -> 50)
            'range': None,               # Halo 4's 0 = unset: no row (unlimited both ways)
            'aim': (2.5, 14.6, 9.0, 35.0),  # 0 x 2.5/5 degenerate -> the source angle (C8 rule), 35 x
                                            # 25/60; 12 x 7.5/10, 35 x 25/25
            'error_deg': None,           # both yardsticks 0: no ratio -> Halo 4's own 0.15 -> 0.8
            'zoom': None,                # Halo 4: no zoom (the rocket's 1.8x / 2x has no railgun side)
            'melee': None},              # Halo 4 shares strike_melee: x1 = the H1 rocket's 55
        'measured': 'h1_role_compare.py railgun',
        'candidates': {
            'source_weapon': 'objects\\weapons\\rifle\\storm_rail_gun\\storm_rail_gun_pve',
            'provisional': 'Rocket Launcher',
            'alternatives': ['Flak Cannon (H1 fuel rod: charge-to-fire)', 'Sniper Rifle'],
            'direct': None,
            'peers': ['Rocket Launcher', 'Sniper Rifle', 'Flak Cannon', 'Spartan Laser (port)',
                      'Binary Rifle (port)'],
            'why': '1-round magazine, 0.75 s charge, slug with impact + explosion damage',
            'lacks': "Halo 4's sprint; the heat (inert); the 'allows binoculars' flag"}},
    # step 11: NO source entry found (phase 0; re-checked at step 11 under the _pve tag)
    firing_profile={'mode': 'same_game', 'donor_weapon': None, 'why': 'no ai\\generic entry for objects\\weapons\\rifle\\storm_rail_gun\\storm_rail_gun found in Halo 4 maps -- pick a Halo 1 stand-in'},
)

PORT.update({
    'status': 'in progress',
})
