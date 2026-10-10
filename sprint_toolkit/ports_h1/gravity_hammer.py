r"""Gravity Hammer (Halo 3 -> Halo 1, wave A9) with the restored ENERGY SWORD as the yardstick (step
4a, user 2026-10-10). energy_sword.py is the example of a melee weapon with an energy (age) charge
per swing and a fire-button strike (`lunge`); spartan_laser.py of a new weapon on a copy of the
PLASMA PISTOL (battery HUD), its HUD and Armed-AI lessons. What is new here: a melee weapon whose
every swing sets off an AREA damage with knockback (Halo 3's gravity_hammer_explosion), which
Halo 1 does not have."""
from ._common import reserved

H3 = r'objects\weapons\melee\gravity_hammer'
GH = 'weapons\\gravity hammer\\'
SND = 'sound\\weapons\\gravity_hammer_port\\'

PORT = reserved(
    order=18, wave='A9', name='Gravity Hammer', source='Halo 3',
    messages=(69, 70), icon=38, reticle=27, label='gh', teach_from='f',
    sound_dir='sound\\weapons\\gravity_hammer_port', weapon_dir='weapons\\gravity hammer',
    yardstick={
        # step 4a (user, 2026-10-10): h3_weapon_values.py (gravity_hammer / energy_blade) + the
        # weapon, its damage effects and FP graph (tool export-tag-to-xml) + h1_role_compare.py
        # gravity_hammer. What h3_weapon_values does not print:
        #   SWING   1st / 2nd / 3rd hit = the SHARED `smash_melee` 80 (no radius; the same tag
        #           as Halo 3's rocket launcher and flak cannon melee), PLUS the hammer's own
        #           `gravity_hammer_explosion` 50..160 over 0.75 -> 1.5 wu (AOE core 0.75),
        #           instantaneous acceleration 3.5, category melee / explosion_small, AI stun
        #           4.5 wu, shake 10 wu, small screen flash. It is set off by an ANIMATION EFFECT
        #           (fp_gravity_hammer_impact on the FP strike / lunge at frame 4 = the primary
        #           keyframe; gravity_hammer_impact on the third-person one, marker
        #           hammer_detonation) -- on every swing, hit or not. Brutes swing their own
        #           `gravity_hammer_explosion_brute` (20..160, 0.6 -> 1.2). The `rumble` part is
        #           0 damage, acceleration 3, a shake
        #           -> a direct swing 80 + 160 = 240 (upper bounds, the Spartan Laser's rule),
        #           every melee_strike 38 fr = 1.27 s (189 dps)
        #   LUNGE   `crush_melee` 150 (collision) + the explosion = 310, melee_lunge 46 fr; flags
        #           'allows unaimed lunge', 'melee only', 'cannot fire at maximum age', 'use
        #           empty melee on empty'
        #   AOE SPIKE  none: aoe spike radius / bump 0 on all four damage effects (smash, crush,
        #           explosion, explosion_brute)
        #   ENERGY  campaign external aging 0.05 a swing (20 swings; multiplayer 0.0835): Halo 3
        #           ages the hammer from the damage routine for the attacker's CURRENT weapon
        #           whenever its explosion damage applies (memory halo-weapon-aging-energy)
        #   AIM     autoaim 10 deg / 1.75 wu (falloff 1.75), magnetism 10 deg / 6 wu
        # Ratio candidates (h1_role_compare.py gravity_hammer; H1 yardstick melee x H3 hammer /
        # H3 yardstick melee on both parts, interval x H1 / H3 melee animation, aim per field):
        #   Energy Sword  151/150 (dash_melee) -> 80.5 + 161.1, 1.27 s, aim = Halo 3's: x1.007
        #   Fuel Rod      55/80 (flak smash_melee) -> 55 + 110, 1.27 s, aim = Halo 3's
        #   Rocket L.     55/80 -> 55 + 110, 1.57 s, aim 0/2.45 12/8.4
        #   AR            55/70 (strike_melee) -> 62.9 + 125.7, 1.56 s, aim 12/2.92 12/7.5
        #   Oddball       80/150 (oneshot_melee) -> 42.7 + 85.3, 1.04 s, aim 0
        # Legendary hits to kill (H3 own / sword): Elite minor 2, major 2, commander 2, Hunter 2,
        # Flood 1; the Fuel Rod / RL ratios one more on majors and commanders
        'pick': 'Energy Sword',
        'reason': "user, step 4a 2026-10-10: the restored sword is Halo 1's only melee weapon in "
                  "the hammer's role and already carries Halo 3's own melee damage (151 vs "
                  "dash_melee 150) and aim assist, so the ratio is x1.007 -- BALANCED = DEFAULT in "
                  "practice (241.6 vs 240 a swing, the same 1.27 s and aim). Energy has no ratio "
                  "(Halo 3 ages the sword per KILL, the hammer per swing): the hammer keeps Halo "
                  "3's 0.05 a swing in both. The heavy-weapon reading (Fuel Rod / RL melee, "
                  "x0.69: Halo 3's hammer smash IS their smash_melee) was shown and not picked",
        # DEFAULT = Halo 3's own numbers (PORTING "Balance"); BALANCED = the sword ratio x1.007
        'balanced': {
            'smash': 80.53,                # 80 x 151/150
            'explosion': 161.07,           # 160 x 151/150 (lower bound 50 -> 50.3)
            'radius': (0.75, 1.5),         # the sword's melee radius 0.5 = Halo 3's dash 0.5: x1
            'interval_s': 38 / 30.0,       # 0.80 s / 24 fr: x1
            'aim': (10.0, 1.75, 10.0, 6.0),  # the H1 sword tag carries Halo 3's: x1
            'energy': 0.05},               # no ratio (per kill vs per swing)
        # Halo 1 materials: the smash on the sword's melee table (every material x1); the
        # explosion on the rocket explosion's (Halo 3 explosion_small = _large for Halo 1
        # except soft flood flesh x1 vs x2: the Brute Shot's finding) with Flood x1
        'materials': {'explosion': {'flood_combat_form': 1.0}},
        'measured': 'h1_role_compare.py gravity_hammer',
        'candidates': {
            'source_weapon': 'objects\\weapons\\melee\\gravity_hammer\\gravity_hammer',
            'provisional': 'Energy Blade',
            'alternatives': ['Fuel Rod melee', 'Rocket Launcher melee', 'Assault Rifle melee',
                             'Oddball'],
            'direct': None,
            'peers': ['Energy Blade', 'Shotgun'],
            'why': "pure melee, energy aging per swing like the sword (whose H1 numbers are Bungie's own)",
            'lacks': 'area knockback blast'}},
    # step 11: the source game's ai\generic entry (8 fields, verified 2026-10-07)
    firing_profile={'mode': 'source', 'from_game': 'Halo 3', 'from_map': 'halo3\\maps\\010_jungle.map', 'from_weapon': 'objects\\weapons\\melee\\gravity_hammer\\gravity_hammer'},
)
