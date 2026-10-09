r"""HALO 1 role comparison + time to kill: does a port (or a restored weapon) play like it
belongs between the Halo 1 weapons of its role? The Halo 1 counterpart of
port_role_compare.py / port_ttk.py (those read the Halo 4 / Reach kits through
`tool export-tag-to-xml` and Halo 4's damage tables; Halo 1 needs neither).

Everything is read from HCEEK tags with Reclaimer:
  weapon      trigger 0: rounds per second, charging time, projectiles / rounds per shot;
              magazine 0; aim assist; melee damage effect; first-person reload / ready
              animation lengths (30 fps)
  damage      the projectile's IMPACT damage effect plus every damage effect its detonation
              effect fires (the explosion); a damage effect's damage = the mean of its upper
              bounds (a direct hit), x its per-MATERIAL modifier, its radius = splash
  enemies     body / shield from the actor variant (when it overrides) else the collision
              model, x the globals' difficulty scales (normal 1.0, legendary 1.4 / 1.4 on
              vitality / shield); the shield takes the shield material's modifier, the
              overflow of the killing shot carries to the body at the body's
  time        charge + one interval per further shot + a reload whenever the magazine is
              empty (the reload animation's length). Melee: one swing per melee animation.

STATED ASSUMPTIONS: direct hits only (splash is listed, not simulated); no headshots; a
damage effect's lower bound (the far edge of splash) is ignored; Halo 1 shields recharge
is not simulated (a burst from cold).

    python h1_role_compare.py flak_cannon [--balanced]
    python h1_role_compare.py energy_blade [--balanced]
    python h1_role_compare.py sentinel_beam [--balanced]

A weapon entry may carry a 4th element {'rate': rounds/s}: the rate MEASURED in game,
used instead of the tag's (the Sentinel Beam's 30/s fires 15/s, PORTING.md). Stock
weapons keep their tag rate: the tick rule is an observation on one weapon, unverified on
the others. A weapon with heat or battery also gets a sustained-fire table.

--balanced applies the catalog's balance rows (weapon_ports_catalog.json, Halo 1) the
fields this tool knows -- what the enhancer's per-port Balanced box turns on.
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.weap import weap_def  # noqa: E402
from reclaimer.hek.defs.proj import proj_def  # noqa: E402
from reclaimer.hek.defs.jpt_ import jpt__def  # noqa: E402
from reclaimer.hek.defs.effe import effe_def  # noqa: E402
from reclaimer.hek.defs.actv import actv_def  # noqa: E402
from reclaimer.hek.defs.coll import coll_def  # noqa: E402
from reclaimer.hek.defs.antr import antr_def  # noqa: E402
from reclaimer.hek.defs.matg import matg_def  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
CATALOG = os.path.join(os.path.dirname(HERE), 'weapon_ports_catalog.json')
B = '\\'
W = 'weapons' + B

SETS = {
    # the restored fuel rod against the explosive power weapons of Halo 1
    'flak_cannon': {'port': 'Flak Cannon', 'weapons': [
        ('Fuel Rod (restored)', W + r'fuel rod gun\fuel rod', 'shot'),
        ('Rocket Launcher', W + r'rocket launcher\rocket launcher', 'shot'),
        ('PC Fuel Rod (MP)', W + r'plasma_cannon\plasma_cannon', 'shot'),
    ]},
    # the restored sword: its slash and lunge against every other way Halo 1 kills up close
    'energy_blade': {'port': 'Energy Blade', 'weapons': [
        ('Sword slash (restored)', W + r'energy sword\energy sword', 'melee'),
        ('Sword lunge (restored)', W + r'energy sword\energy sword', 'shot'),
        ('Shotgun', W + r'shotgun\shotgun', 'shot'),
        ('Shotgun melee', W + r'shotgun\shotgun', 'melee'),
        ('Assault Rifle melee', W + r'assault rifle\assault rifle', 'melee'),
        ('Rocket Launcher melee', W + r'rocket launcher\rocket launcher', 'melee'),
        ('Oddball melee', W + r'ball\ball', 'melee'),
    ]},
    # the Sentinel Beam (a full Halo 3 port) against Halo 1's SENTINEL GUN -- the direct
    # yardstick: Halo 3's Sentinels carry the player's own sentinel_gun, so the H1 player
    # beam = the H1 Sentinel gun x 1 for damage / rate / range -- and the automatics of
    # Halo 1. Both Sentinel weapons are tagged 30/s and fire 15/s (measured on the port).
    'sentinel_beam': {'port': 'Sentinel Beam', 'weapons': [
        ('Sentinel Beam (port)', W + r'sentinel beam\sentinel beam', 'shot', {'rate': 15.0}),
        ('Sentinel gun (H1 AI)', r'characters\sentinel\sentinel', 'shot', {'rate': 15.0}),
        ('Plasma Rifle', W + r'plasma rifle\plasma rifle', 'shot'),
        ('Assault Rifle', W + r'assault rifle\assault rifle', 'shot'),
        ('Needler', W + r'needler\needler', 'shot'),
        ('Pistol', W + r'pistol\pistol', 'shot'),
    ], 'enemies': [
        ('Flood combat (elite)', r'characters\floodcombat elite\floodcombat elite plasma rifle',
         'floodcombat elite'),
        ('Sentinel', r'characters\sentinel\sentinel', 'sentinel'),
        ('Sentinel (shielded)', r'characters\sentinel\sentinel_shielded', 'sentinel'),
    ]},
    # the SMG (wave A1), step 4a: each yardstick's RATIO-RULE candidate (H1 yard x H3 SMG /
    # H3 yard; Halo 3 values from H3EK, 2026-10-07) on the Halo 1 AR's bullet materials --
    # the port is built on an AR copy -- beside the step-5b peers. '@15' = the same per-round
    # damage at 15/s: Halo 1's tick rule (a round every floor(30/rate)+1 ticks, an
    # OBSERVATION on the Sentinel Beam) would fire every candidate rate in 15..30 at 15/s.
    # H3: SMG 5 x 15/s, mag 60, reload 50 fr; AR 7.5 x 10/s, 32, 58 fr; magnum 15 (0.4 s
    # recovery = 2.5/s), 8, 50 fr; plasma rifle 10 x 9/s, heat (no magazine)
    # the BUILT port (step 5b): its tags, and with --balanced its catalog rows. Halo 1 fires
    # it at 15/s at both the 15 and the balanced 22.5 tag (measured, magazine dumps)
    'smg': {'port': 'SMG', 'weapons': [
        ('SMG (port)', W + r'smg\smg', 'shot', {'rate': 15.0, 'cap': 15.0}),
        ('SMG = AR ratio', W + r'assault rifle\assault rifle', 'shot',
         {'dmg': 6.67, 'rate': 22.5, 'mag': 112, 'reload': 2.5}),
        ('SMG = AR ratio @15', W + r'assault rifle\assault rifle', 'shot',
         {'dmg': 6.67, 'rate': 15.0, 'mag': 112, 'reload': 2.5}),
        ('SMG = Pistol ratio', W + r'assault rifle\assault rifle', 'shot',
         {'dmg': 8.33, 'rate': 21.0, 'mag': 90, 'reload': 2.23}),
        ('SMG = Pistol ratio @15', W + r'assault rifle\assault rifle', 'shot',
         {'dmg': 8.33, 'rate': 15.0, 'mag': 90, 'reload': 2.23}),
        ('SMG = PR ratio', W + r'assault rifle\assault rifle', 'shot',
         {'dmg': 6.5, 'rate': 16.67, 'mag': 60, 'reload': 1.67}),
        ('SMG = PR ratio @15', W + r'assault rifle\assault rifle', 'shot',
         {'dmg': 6.5, 'rate': 15.0, 'mag': 60, 'reload': 1.67}),
        ('Assault Rifle', W + r'assault rifle\assault rifle', 'shot'),
        ('Plasma Rifle', W + r'plasma rifle\plasma rifle', 'shot'),
        ('Needler (no supercombine)', W + r'needler\needler', 'shot',
         {'damage_tags': [W + r'needler\detonation damage']}),
        ('Pistol', W + r'pistol\pistol', 'shot'),
    ]},
    # the BATTLE RIFLE (wave A2), step 4a: Halo 3's 3-round burst (shots per fire 3 at 15/s,
    # then 0.28 s fire recovery -> a burst every 2/15 + 0.28 = 0.413 s, ASSUMED: the recovery
    # replaces the third interval) as 'burst': (rounds, spacing, cycle). Each candidate keeps
    # the burst's shape (3 rounds, 2 ticks apart) and scales per-round damage and the burst
    # CYCLE by its yardstick's ratio, on that yardstick's bullet materials. H3 (H3EK
    # 2026-10-07): BR 6 x 3 per 0.413 s = 43.5/s, mag 36, reload 58 fr; magnum 15 per 0.4 s =
    # 37.5/s, 8, 50 fr; AR 7.5 x 10/s = 75/s, 32, 58 fr; sniper 80 per 0.7 s = 114/s, 4, 72 fr.
    # H1: pistol 25 x 3.5/s, 12, 67 fr; AR 10 x 15/s, 60, 87 fr; sniper 101 x 2/s, 4, 94 fr.
    'battle_rifle': {'port': 'Battle Rifle', 'weapons': [
        # the BUILT port (step 5b): its tags (+ --balanced rows). Its burst is the user's
        # (test 2): 3 rounds 0.1 s apart (10/s), one burst a trigger PULL with no recovery --
        # the cycle is the player's tapping; Halo 3's 0.413 s rhythm assumed here
        ('Battle Rifle (port)', W + r'battle rifle\battle rifle', 'shot',
         {'burst': (3, 0.1, 0.413)}),
        ('BR = Halo 3 own (pistol)', W + r'pistol\pistol', 'shot',
         {'dmg': 6.0, 'burst': (3, 1 / 15.0, 0.413), 'mag': 36, 'reload': 58 / 30.0}),
        ('BR = Halo 3 own (AR)', W + r'assault rifle\assault rifle', 'shot',
         {'dmg': 6.0, 'burst': (3, 1 / 15.0, 0.413), 'mag': 36, 'reload': 58 / 30.0}),
        # 25 x 6/15; cycle: 3.5/s x (2.42 / 2.5) = 3.39 bursts/s; 12 x 36/8; 67 fr x 58/50
        ('BR = Pistol ratio', W + r'pistol\pistol', 'shot',
         {'dmg': 10.0, 'burst': (3, 1 / 15.0, 0.295), 'mag': 54, 'reload': 2.59}),
        # 10 x 6/7.5; 15/s x (7.26 / 10) = 10.9 rounds/s = a burst every 0.275 s; 60 x 36/32
        ('BR = AR ratio', W + r'assault rifle\assault rifle', 'shot',
         {'dmg': 8.0, 'burst': (3, 1 / 15.0, 0.275), 'mag': 67, 'reload': 2.9}),
        # 101 x 6/80; 2/s x (2.42 / 1.43) = 3.39 bursts/s; 4 x 36/4; 94 fr x 58/72
        ('BR = Sniper ratio', W + r'sniper rifle\sniper rifle', 'shot',
         {'dmg': 7.58, 'burst': (3, 1 / 15.0, 0.295), 'mag': 36, 'reload': 2.52}),
        ('Pistol', W + r'pistol\pistol', 'shot'),
        ('Assault Rifle', W + r'assault rifle\assault rifle', 'shot'),
        ('Sniper Rifle', W + r'sniper rifle\sniper rifle', 'shot'),
    ]},
    # the COVENANT CARBINE (wave A3), step 4a: semi-auto, Halo 3 rate = 1 / fire recovery.
    # H3 (H3EK 2026-10-07): carbine 10 per 0.17 s = 5.88/s = 59/s, mag 18 (54 / 90), reload
    # 69 fr, damage group plasma_fast (NO shield bonus: energy_shield x1, unlike plasma_slow's
    # 1.5; shield_thick 0.5, sentinel 2); magnum 15 per 0.4 s = 2.5/s, 8 (32 / 48), 50 fr;
    # needler 4 x 10/s (7 -> 10 ramp), 19 (76 / 95), 44 fr; sniper 80 per 0.7 s = 1.43/s, 4
    # (12 / 24), 72 fr. H1: pistol 25 x 3.5/s, 12, 67 fr; needle 10 (detonation damage) x
    # 10/s, 20, 70 fr; sniper 101 x 2/s, 4, 94 fr. Each candidate on its yardstick's own
    # materials; Halo 3's own numbers on the pistol bullet AND the plasma rifle bolt to show
    # what the damage type does (Halo 3's plasma_fast behaves like a bullet on shields).
    'covenant_carbine': {'port': 'Covenant Carbine', 'weapons': [
        # the BUILT port (step 5b): its tags (+ --balanced rows). Semi-automatic: the rate is
        # the tag's cap (5.88/s, balanced 8.24/s) -- the player's tapping may be slower
        ('Covenant Carbine (port)', W + r'covenant carbine\covenant carbine', 'shot'),
        ('CC = H3 own (bullet mat)', W + r'pistol\pistol', 'shot',
         {'dmg': 10.0, 'rate': 1 / 0.17, 'mag': 18, 'reload': 69 / 30.0}),
        ('CC = H3 own (plasma mat)', W + r'pistol\pistol', 'shot',
         {'dmg': 10.0, 'rate': 1 / 0.17, 'mag': 18, 'reload': 69 / 30.0,
          'damage_tags': [W + r'plasma rifle\bolt']}),
        ('CC = Pistol ratio (plasma)', W + r'pistol\pistol', 'shot',
         {'dmg': 16.67, 'rate': 8.24, 'mag': 27, 'reload': 3.08,
          'damage_tags': [W + r'plasma rifle\bolt']}),
        # 25 x 10/15; 3.5/s x 5.88/2.5; 12 x 18/8; 67 fr x 69/50
        ('CC = Pistol ratio', W + r'pistol\pistol', 'shot',
         {'dmg': 16.67, 'rate': 8.24, 'mag': 27, 'reload': 3.08}),
        # 10 x 10/4; 10/s x 5.88/10; 20 x 18/19; 70 fr x 69/44 (needle materials)
        ('CC = Needler ratio', W + r'needler\needler', 'shot',
         {'dmg': 25.0, 'rate': 5.88, 'mag': 19, 'reload': 3.66,
          'damage_tags': [W + r'needler\detonation damage']}),
        # 101 x 10/80; 2/s x 5.88/1.43; 4 x 18/4; 94 fr x 69/72
        ('CC = Sniper ratio', W + r'sniper rifle\sniper rifle', 'shot',
         {'dmg': 12.63, 'rate': 8.24, 'mag': 18, 'reload': 3.0}),
        ('Pistol', W + r'pistol\pistol', 'shot'),
        ('Needler (no supercombine)', W + r'needler\needler', 'shot',
         {'damage_tags': [W + r'needler\detonation damage']}),
        ('Sniper Rifle', W + r'sniper rifle\sniper rifle', 'shot'),
        ('Plasma Rifle', W + r'plasma rifle\plasma rifle', 'shot'),
        ('Battle Rifle (port peer)', W + r'battle rifle\battle rifle', 'shot',
         {'burst': (3, 0.1, 0.413)}),
    ]},
    # the BEAM RIFLE (wave A4), step 4a. Halo 3 (H3EK 2026-10-08, h3_weapon_values): beam
    # rifle 80 (plasma_fast) per 0.4 s recovery = 2.5/s, heat 0.7 a round, overheated at 1,
    # loss 0.575/s (0.3/s while overheated) down to 0.1, battery: CAMPAIGN age 0.05 a round
    # = 20 shots (multiplayer 0.1 = 10), 1200 wu/s, range 500, zoom 2 (3.5, 9.5), aim 1/10
    # 4/14, error 0.5; sniper 80 (bullet_fast) per 0.7 s = 1.43/s, 4 (12 / 24), 72 fr, zoom
    # 2 (4, 9), otherwise the beam's numbers; plasma pistol 7 (plasma_slow), recovery 0.05
    # (TAPPED: a degenerate rate), heat 0.14, loss 0.6 / 0.45 to 0.1, age 0.002 (campaign),
    # 21 wu/s, range 40, aim 5/13.5 9/18; sentinel gun 4 (plasma_fast) x 30/s, heat 0.04,
    # loss 0.8525 / 0.35 to 0.1, overheated 0.9, age 0.003, 4000 wu/s, range 120, aim 1/12
    # 9/18. Halo 1: sniper 101 x 2/s, 4 (12 / 24), 1000 wu/s, range 1000, zoom 2 (2, 8),
    # aim 1/35 2/35, melee 55; plasma pistol 18 tapped (rate 0, charge 0.6 = the overcharge),
    # heat 0.16, loss 0.65 to 0.25, age 0.002, 25 wu/s, range 50; Sentinel Beam (port,
    # derived) 4.64 x 15/s measured, heat 0.0426, loss 0.3 to 0.25, overheated 0.9, age
    # 0.012. Ratio rule = H1 yardstick x H3 beam / H3 yardstick; a value the yardstick does not
    # have (the sniper's heat and battery) stays Halo 3's own. Halo 1 has ONE heat loss/s:
    # Halo 3's two (0.575 cooling, 0.3 overheated) are shown both ways.
    'beam_rifle': {'port': 'Beam Rifle', 'weapons': [
        # the BUILT port (step 5b): its tags (+ --balanced rows); tapped, so the overheat
        # pauses are simulated (heat 0.7, loss 0.4375 -- the user's average, test 1)
        ('Beam Rifle (port)', W + r'beam rifle\beam rifle', 'shot', {'heat_sim': True}),
        ('BmR = H3 own, loss .575', W + r'sniper rifle\sniper rifle', 'shot',
         {'speed': 1200.0, 'range': 500.0, 'aim': (1.0, 10.0, 4.0, 14.0),
          'dmg': 80.0, 'rate': 2.5, 'heat': (0.7, 1.0, 0.575, 0.1), 'age': 0.05,
          'nomag': True, 'heat_sim': True}),
        ('BmR = H3 own, loss .3', W + r'sniper rifle\sniper rifle', 'shot',
         {'speed': 1200.0, 'range': 500.0, 'aim': (1.0, 10.0, 4.0, 14.0),
          'dmg': 80.0, 'rate': 2.5, 'heat': (0.7, 1.0, 0.3, 0.1), 'age': 0.05,
          'nomag': True, 'heat_sim': True}),
        ('BmR = H3 own (2 losses)', W + r'sniper rifle\sniper rifle', 'shot',
         {'speed': 1200.0, 'range': 500.0, 'aim': (1.0, 10.0, 4.0, 14.0),
          'dmg': 80.0, 'rate': 2.5, 'heat': (0.7, 1.0, 0.575, 0.1, 0.3), 'age': 0.05,
          'nomag': True, 'heat_sim': True}),
        # Halo 3's plasma_fast differences Halo 1 has a material for (the Carbine's pair)
        ('BmR = H3 own, plasma diffs', W + r'sniper rifle\sniper rifle', 'shot',
         {'speed': 1200.0, 'range': 500.0, 'aim': (1.0, 10.0, 4.0, 14.0),
          'dmg': 80.0, 'rate': 2.5, 'heat': (0.7, 1.0, 0.575, 0.1), 'age': 0.05,
          'nomag': True, 'heat_sim': True,
          'mods': {'jackal_energy_shield': 0.5, 'sentinel': 2.0}}),
        # 101 x 80/80; 2/s x 2.5/1.43 = 3.5/s; heat + battery: Halo 3's own (no sniper heat)
        ('BmR = Sniper ratio', W + r'sniper rifle\sniper rifle', 'shot',
         {'dmg': 101.0, 'rate': 3.5, 'heat': (0.7, 1.0, 0.575, 0.1), 'age': 0.05,
          'nomag': True, 'heat_sim': True}),
        # 18 x 80/7; rate: both tapped -> Halo 3's 2.5; heat 0.16 x 5, loss 0.65 x 0.575/0.6,
        # recovery 0.25 x 1; age 0.002 x 25 = 0.05 (plasma bolt materials)
        ('BmR = Plasma Pistol ratio', W + r'plasma pistol\plasma pistol', 'shot',
         {'speed': 1428.6, 'range': 625.0, 'aim': (1.0, 14.8, 5.33, 15.6),
          'dmg': 205.7, 'rate': 2.5, 'charge': 0.0, 'heat': (0.8, 1.0, 0.623, 0.25),
          'age': 0.05, 'heat_sim': True}),
        # 4.64 x 80/4; 15/s (measured) x 2.5/30; heat 0.0426 x 17.5, overheated 0.9 x 1/0.9,
        # loss 0.3 x 0.575/0.8525, recovery 0.25; age 0.012 x 0.05/0.003 = 0.2 (5 shots)
        ('BmR = Sentinel Beam ratio', W + r'sentinel beam\sentinel beam', 'shot',
         {'speed': 1200.0, 'range': 500.0, 'aim': (1.0, 10.0, 4.0, 14.0),
          'dmg': 92.8, 'rate': 1.25, 'heat': (0.746, 1.0, 0.202, 0.25), 'age': 0.2,
          'heat_sim': True}),
        ('Sniper Rifle', W + r'sniper rifle\sniper rifle', 'shot'),
        # Halo 1's primary is tapped (rate 0; the 0.6 s charge is the overcharge): 5/s ASSUMED
        ('Plasma Pistol (tap 5/s)', W + r'plasma pistol\plasma pistol', 'shot',
         {'rate': 5.0, 'charge': 0.0, 'heat_sim': True}),
        ('Sentinel Beam (peer)', W + r'sentinel beam\sentinel beam', 'shot', {'rate': 15.0}),
        ('Pistol', W + r'pistol\pistol', 'shot'),
    ], 'enemies': [
        ('Sentinel', r'characters\sentinel\sentinel', 'sentinel'),
        ('Flood combat (elite)', r'characters\floodcombat elite\floodcombat elite plasma rifle',
         'floodcombat elite'),
    ]},
    # the SPIKE RIFLE (wave A5), step 4a. Halo 3 (H3EK 2026-10-08, h3_weapon_values): spiker
    # 9 (bullet_slow -- the AR's damage group) x 8/s = 72/s, ramp 1 s, mag 40 (120 / 160),
    # reload 56 fr, error 0 min, 0.5 -> 1.25, 25 -> 17.5 wu/s, air gravity 0.2, range 70, aim
    # 5/12 12/18, melee cut_melee 72; AR 7.5 x 10/s = 75/s, 32 (96 / 384), 58 fr, error 0.1,
    # 0.1 -> 3, 80 wu/s, gravity 0, range 40, aim 5/15 10/20, strike_melee 70; needler 4
    # (plasma_slow) x 7 -> 10/s = 40/s, 19 (76 / 95), 44 fr, error 0, 0 -> 3, 11 wu/s, range
    # 25, aim 4/14 6/21. Halo 1: AR 10 x 15/s, 60 (240 / 600), 87 fr, error 2 -> 6.5, 324,
    # gravity 1.0, range 40, aim 6/25 12/25, melee 55; needler 10 (detonation damage) x 3 ->
    # 10/s, 20 (80 / 80), 70 fr, error min 2, 4 -> 4, speed 4 (tag), guided, range 20; plasma
    # rifle 7 -> 10/s, heat. Ratio = H1 yardstick x H3 spiker / H3 yardstick.
    'brute_spiker': {'port': 'Spike Rifle', 'weapons': [
        # the BUILT port (step 5b): its tags (+ --balanced rows); 8/s and 12/s are under the
        # 15/s cap observation, so the tag rates stand (no measurement needed)
        ('Spike Rifle (port)', W + r'spiker\spiker', 'shot'),
        ('SpR = H3 own (AR bullet)', W + r'assault rifle\assault rifle', 'shot',
         {'dmg': 9.0, 'rate': 8.0, 'mag': 40, 'reload': 56 / 30.0, 'speed': 25.0, 'range': 70.0,
          'aim': (5.0, 12.0, 12.0, 18.0)}),
        ('SpR = H3 own (needle mat)', W + r'needler\needler', 'shot',
         {'dmg': 9.0, 'rate': 8.0, 'mag': 40, 'reload': 56 / 30.0, 'speed': 25.0, 'range': 70.0,
          'aim': (5.0, 12.0, 12.0, 18.0), 'damage_tags': [W + r'needler\detonation damage']}),
        # 10 x 9/7.5; 15/s x 8/10 (under the 15/s cap); 60 x 40/32; 87 fr x 56/58;
        # 324 x 25/80; range 40 x 70/40; aim 6 x 5/5, 25 x 12/15; 12 x 12/10, 25 x 18/20
        ('SpR = AR ratio', W + r'assault rifle\assault rifle', 'shot',
         {'dmg': 12.0, 'rate': 12.0, 'mag': 75, 'reload': 84 / 30.0, 'speed': 101.25,
          'range': 70.0, 'aim': (6.0, 20.0, 14.4, 22.5)}),
        # 10 x 9/4; 10/s x 8/10; 20 x 40/19; 70 fr x 56/44; 4 x 25/11; 20 x 70/25;
        # aim 6 x 5/4, 25 x 12/14; 12 x 12/6, 25 x 18/21 (needle materials)
        ('SpR = Needler ratio', W + r'needler\needler', 'shot',
         {'dmg': 22.5, 'rate': 8.0, 'mag': 42, 'reload': 89 / 30.0, 'speed': 9.09,
          'range': 56.0, 'aim': (7.5, 21.4, 24.0, 21.4),
          'damage_tags': [W + r'needler\detonation damage']}),
        ('Assault Rifle', W + r'assault rifle\assault rifle', 'shot'),
        ('Needler (no supercombine)', W + r'needler\needler', 'shot',
         {'damage_tags': [W + r'needler\detonation damage']}),
        ('Plasma Rifle', W + r'plasma rifle\plasma rifle', 'shot'),
        ('SMG (port peer)', W + r'smg\smg', 'shot', {'rate': 15.0, 'cap': 15.0}),
    ]},
    # the MAULER (wave A6), step 4a. Halo 3 (H3EK 2026-10-08, h3_weapon_values + the
    # projectiles' `conical spread` block -- the pellets are there, not on the barrel): mauler
    # 15 pellets (yaw 3 x pitch 5, 7.5 deg) x 7 (lower 1.5 over 2.5 -> 5 wu; bullet_slow),
    # recovery 0.75 s, mag 5 (10 / 25) whole-magazine reload 55 fr, 480 wu/s instant, range 8,
    # aim 8/7 16/7, cut_melee; shotgun the SAME 15 / 7.5 deg cone x 10 (lower 3 over 2 -> 4
    # wu; bullet_slow), 1.0 s, 6 (18 / 36) shell by shell (enter 14 + 16 a shell + exit 34),
    # range 6, aim 8/5.5 16/5.5, strike_melee; magnum 15 (lower 0) x 1/0.4 s, 8 (32 / 48),
    # 50 fr, range 40, aim 2/15 6/20. Halo 1: shotgun 15 pellets x 18..25 (lower 8 over 1.5
    # -> 3 wu; 'shotgun' table), 1/s, 12 (24 / 60) 0.4 s a shell, error 10 deg, 140 -> 100
    # wu/s, range 40, aim 6/15 12/15; pistol 25 x 3.5/s, 12 (60 / 120), 67 fr, error 0.2 ->
    # 2, 300 wu/s, range 40, aim 3/30 6/30. All pellets hit, at point blank (no falloff).
    'brute_mauler': {'port': 'Mauler', 'weapons': [
        # the BUILT port (step 5b): its tags (+ --balanced rows)
        ('Mauler (port)', W + r'mauler\mauler', 'shot'),
        ('Mau = H3 own (sg pellet)', W + r'shotgun\shotgun', 'shot',
         {'dmg': 7.0, 'rate': 1 / 0.75, 'mag': 5, 'reload': 55 / 30.0, 'speed': 480.0,
          'range': 8.0, 'aim': (8.0, 7.0, 16.0, 7.0)}),
        ('Mau = H3 own (pistol mat)', W + r'pistol\pistol', 'shot',
         {'per_shot': 15, 'dmg': 7.0, 'rate': 1 / 0.75, 'mag': 5, 'reload': 55 / 30.0,
          'speed': 480.0, 'range': 8.0, 'aim': (8.0, 7.0, 16.0, 7.0)}),
        # 21.5 x 7/10; 1/s x 1.0/0.75; 12 x 5/6; 12 shells (144 fr) x 55 / 144 (H3 shotgun
        # empty -> full: 14 + 6 x 16 + 34) = 55 fr; speed x1; 40 x 8/6; aim 6 x 8/8, 15 x
        # 7/5.5; 12 x 16/16, 15 x 7/5.5
        ('Mau = Shotgun ratio', W + r'shotgun\shotgun', 'shot',
         {'dmg': 15.05, 'rate': 4 / 3.0, 'mag': 10, 'reload': 55 / 30.0, 'speed': 140.0,
          'range': 53.3, 'aim': (6.0, 19.1, 12.0, 19.1)}),
        # 25 x 7/15 a pellet, 15 pellets (H3's own: the magnum has none); 3.5/s x 0.4/0.75;
        # 12 x 5/8; 67 fr x 55/50; 300 x 480/180; 40 x 8/40; aim 3 x 8/2, 30 x 7/15; 6 x
        # 16/6, 30 x 7/20
        ('Mau = Pistol ratio', W + r'pistol\pistol', 'shot',
         {'per_shot': 15, 'dmg': 11.67, 'rate': 1.867, 'mag': 8, 'reload': 73.7 / 30.0,
          'speed': 800.0, 'range': 8.0, 'aim': (12.0, 14.0, 16.0, 10.5)}),
        ('Shotgun', W + r'shotgun\shotgun', 'shot'),
        ('Pistol', W + r'pistol\pistol', 'shot'),
        ('Sword slash (restored)', W + r'energy sword\energy sword', 'melee'),
        ('Sword lunge (restored)', W + r'energy sword\energy sword', 'shot'),
        ('Shotgun melee', W + r'shotgun\shotgun', 'melee'),
        ('Pistol melee', W + r'pistol\pistol', 'melee'),
        ('Spike Rifle (blade peer)', W + r'spiker\spiker', 'melee'),
    ]},
    # the Brute Shot (wave A7), step 4a. Its damage is the grenade's DETONATION (no impact
    # damage): H3 shot_grenade_explosion 26..73, radius 0.3 -> 1.1 (core 0.3), 'bullet'
    # category / explosion_small. The grenade does NOT bounce in Halo 3: impact (detonate) on
    # every material (attach at chance 0), timer 0, arming 0, and it bursts in the air at its
    # 20 wu maximum range (airborne_detonation). H3: brute shot 0.3 s, 6 (18 / 18), 95 fr,
    # 16 -> 7 wu/s, gravity 0.05, aim 4/15 6/20, slice_melee 90; rocket 80..240, 0.9 -> 2,
    # 0.8 s, 2 (4 / 8), 116 fr, 8 -> 16, 0, 175, 5/25 10/25, smash 80; flak 30..60, 0.5 ->
    # 1.5, 0.4 s, 5 (20 / 30), 90 fr, 15 -> 6.5, 0.025, 80, 4/25 6/25, smash 80; frag
    # 60..160, 0.5 -> 1.75 (arming 1.3, 0.5 s after the first bounce). Halo 1: rocket 80..315,
    # 0.5 -> 2, 2.0 s, 2 (4 / 8), 4.17 s, 12 -> 10, 0, 128, 0/35 12/35, melee 55; fuel rod
    # 40..75, 0.5 -> 1.5, 1.25 s, 4 (12 / 24), 3.0 s, 14 -> 5, 1.0, -, 4/25 6/25, 55; frag
    # 80..120, 1.5 -> 2.5 (arming 1.5, 0.5 s after the first bounce)
    'brute_shot': {'port': 'Brute Shot', 'weapons': [
        ('BS = H3 own (RL mat)', W + r'rocket launcher\rocket launcher', 'shot',
         {'dmg': 73.0, 'radius': (0.3, 1.1), 'rate': 1 / 0.3, 'mag': 6, 'reload': 95 / 30.0,
          'speed': 16.0, 'range': 20.0, 'aim': (4.0, 15.0, 6.0, 20.0)}),
        ('BS = H3 own (FR mat)', W + r'fuel rod gun\fuel rod', 'shot',
         {'dmg': 73.0, 'radius': (0.3, 1.1), 'rate': 1 / 0.3, 'mag': 6, 'reload': 95 / 30.0,
          'speed': 16.0, 'range': 20.0, 'aim': (4.0, 15.0, 6.0, 20.0), 'charge': 0.0}),
        # 315 x 73/240; 0.5 x 0.3/0.9, 2 x 1.1/2; 2.0 s x 0.3/0.8; 2 x 6/2; 4.17 s x 95/116;
        # 12 x 16/8; 128 x 20/175; aim 0 x 4/5, 35 x 15/25; 12 x 6/10, 35 x 20/25
        ('BS = RL ratio', W + r'rocket launcher\rocket launcher', 'shot',
         {'dmg': 95.8, 'radius': (0.167, 1.1), 'rate': 1 / 0.75, 'mag': 6,
          'reload': 4.1667 * 95 / 116, 'speed': 24.0, 'range': 14.6,
          'aim': (0.0, 21.0, 7.2, 28.0)}),
        # 75 x 73/60; 0.5 x 0.3/0.5, 1.5 x 1.1/1.5; 1.25 s x 0.3/0.4; 4 x 6/5; 3.0 s x 95/90;
        # 14 x 16/15; aim 4 x 4/4, 25 x 15/25; 6 x 6/6, 25 x 20/25 (= Halo 3's own)
        ('BS = Fuel Rod ratio', W + r'fuel rod gun\fuel rod', 'shot',
         {'dmg': 91.25, 'radius': (0.3, 1.1), 'rate': 1 / 0.9375, 'mag': 5,
          'reload': 3.0 * 95 / 90, 'speed': 14.9, 'aim': (4.0, 15.0, 6.0, 20.0),
          'charge': 0.0}),
        # 120 x 73/160; 1.5 x 0.3/0.5, 2.5 x 1.1/1.75 (the frag table: hunter armour x0.25);
        # the rest is Halo 3's own (a thrown grenade has no rate, magazine or aim)
        ('BS = Frag ratio', W + r'rocket launcher\rocket launcher', 'shot',
         {'damage_tags': [W + r'frag grenade\explosion'], 'dmg': 54.75,
          'radius': (0.9, 1.57), 'rate': 1 / 0.3, 'mag': 6, 'reload': 95 / 30.0,
          'speed': 16.0, 'range': 20.0, 'aim': (4.0, 15.0, 6.0, 20.0)}),
        ('Rocket Launcher', W + r'rocket launcher\rocket launcher', 'shot'),
        ('Fuel Rod (restored)', W + r'fuel rod gun\fuel rod', 'shot'),
        ('Frag grenade (1/s)', W + r'rocket launcher\rocket launcher', 'shot',
         {'damage_tags': [W + r'frag grenade\explosion'], 'radius': (1.5, 2.5), 'rate': 1.0,
          'nomag': True, 'speed': 0.0, 'range': 0.0, 'aim': (0.0, 0.0, 0.0, 0.0)}),
        ('Rocket Launcher melee', W + r'rocket launcher\rocket launcher', 'melee'),
        ('Fuel Rod melee', W + r'fuel rod gun\fuel rod', 'melee'),
        ('Spike Rifle (blade peer)', W + r'spiker\spiker', 'melee'),
        ('Mauler (blade peer)', W + r'mauler\mauler', 'melee'),
        ('Sword slash (restored)', W + r'energy sword\energy sword', 'melee'),
    ]},
}

ENEMIES = [
    ('Grunt minor', r'characters\grunt\grunt minor plasma pistol', 'grunt'),
    ('Jackal (body)', r'characters\jackal\jackal minor plasma pistol', 'jackal'),
    ('Elite minor', r'characters\elite\elite minor\elite minor plasma rifle', 'elite'),
    ('Elite major', r'characters\elite\elite major\elite major plasma rifle', 'elite'),
    ('Elite commander', r'characters\elite\elite commander\elite commander plasma rifle', 'elite'),
    ('Hunter (armour)', r'characters\hunter\hunter', 'hunter'),
    ('Flood combat (human)', r'characters\floodcombat_human\floodcombat_human', 'floodcombat_human'),
]


def load(defn, rel, ext):
    p = os.path.join(TAGS, rel + ext)
    return defn.build(filepath=p).data.tagdata if os.path.exists(p) else None


def damage(rel):
    """{'dmg', 'radius', 'mods': {material: x}} of one damage effect."""
    j = load(jpt__def, rel, '.damage_effect')
    if j is None:
        return None
    up = j.damage.damage_upper_bound
    mods = {k: getattr(j.damage_modifiers, k) for k in j.damage_modifiers.desc['NAME_MAP']}
    return {'tag': rel, 'dmg': (up[0] + up[1]) / 2.0, 'radius': (j.radius[0], j.radius[1]),
            'mods': mods}


def projectile_damage(rel):
    """Every damage a projectile deals on a direct hit: impact + its detonation's parts."""
    p = load(proj_def, rel, '.projectile')
    if p is None:
        return [], None
    out = []
    ph = p.proj_attrs.physics
    if ph.impact_damage.filepath:
        out.append(damage(ph.impact_damage.filepath))
    eff = p.proj_attrs.detonation.effect.filepath
    if eff:
        e = load(effe_def, eff, '.effect')
        for ev in (e.events.STEPTREE if e else []):
            for part in ev.parts.STEPTREE:
                if part.type.tag_class.enum_name == 'damage_effect':
                    out.append(damage(part.type.filepath))
    # a 0-damage part (Halo 1's shared frag-grenade 'shock wave', radius 8) only shoves
    return [d for d in out if d and d['dmg'] > 0], p


def anim_seconds(rel, names):
    a = load(antr_def, rel, '.model_animations') if rel else None
    if a is None:
        return None
    for anim in a.animations.STEPTREE:
        if anim.name in names:
            return anim.frame_count / 30.0
    return None


def weapon(label, rel, mode, overrides, extra=None):
    d = load(weap_def, rel, '.weapon')
    w = d.weap_attrs
    fp = w.interface.first_person_animations.filepath
    out = {'label': label, 'mode': mode,
           'aim': (math.degrees(w.aiming.autoaim_angle), w.aiming.autoaim_range,
                   math.degrees(w.aiming.magnetism_angle), w.aiming.magnetism_range)}
    if mode == 'melee':
        out['damage'] = [damage(w.melee.player_damage.filepath)] if w.melee.player_damage.filepath else []
        out['interval'] = anim_seconds(fp, ('first-person melee',)) or 1.0
        out['charge'], out['mag'], out['reload'], out['per_shot'] = 0.0, None, None, 1
        out['speed'] = out['range'] = None
    else:
        tr = w.triggers.STEPTREE[0]
        rps = tr.firing.rounds_per_second
        out['rps'] = max(rps[0], rps[1])
        out['charge'] = tr.charging.charging_time
        out['per_shot'] = tr.projectile.projectiles_per_shot or 1
        if extra and extra.get('per_shot'):  # a pellet CANDIDATE on a single-round tag
            out['per_shot'] = extra['per_shot']
        dmg, p = projectile_damage(tr.projectile.projectile.filepath)
        out['damage'] = dmg
        out['speed'] = p.proj_attrs.physics.initial_velocity if p else None
        out['range'] = p.proj_attrs.detonation.maximum_range if p else None
        out['interval'] = 1.0 / out['rps'] if out['rps'] else 0.0
        if out['charge']:                    # a charged shot cannot repeat faster than it charges
            out['interval'] = max(out['interval'], out['charge'])
        mags = w.magazines.STEPTREE
        out['mag'] = (mags[0].rounds_loaded_maximum if len(mags) and mags[0].rounds_loaded_maximum
                      else None)
        out['rounds_per_shot'] = tr.firing.rounds_per_shot
        out['reload'] = anim_seconds(fp, ('first-person reload-empty', 'first-person reload-full'))
        out['tag_rps'] = out['rps']
        if extra and extra.get('rate'):
            out['rps'] = extra['rate']
            out['interval'] = 1.0 / out['rps']
        # a CANDIDATE that has no tag yet (step 4a): the base tag's projectile materials
        # with the candidate's own per-round damage, magazine and reload
        # damage the projectile walk does not reach: Halo 1's needle has a 0 impact damage
        # and deals its 10 through `detonation damage` (the supercombine is `explosion`)
        if extra and extra.get('damage_tags'):
            out['damage'] = [damage(t) for t in extra['damage_tags']]
        if extra and extra.get('dmg') is not None:
            for d in out['damage']:
                d['dmg'] = extra['dmg']
        if extra and extra.get('mag'):
            out['mag'] = extra['mag']
        if extra and extra.get('reload'):
            out['reload'] = extra['reload']
        h = w.heat
        out['heat'] = (tr.misc.heat_generated_per_round, h.overheated_threshold,
                       h.loss_per_second, h.recovery_threshold)
        out['age'] = tr.misc.age_generated_per_round
        # a CANDIDATE's own heat / battery (step 4a, the Beam Rifle): heat = (per round,
        # overheated threshold, loss/s, recovery threshold[, loss/s while overheated --
        # Halo 3 has two, Halo 1 one]); 'nomag' = a battery weapon on a magazine tag
        if extra and extra.get('heat'):
            out['heat'] = tuple(extra['heat'])
        if extra and extra.get('age') is not None:
            out['age'] = extra['age']
        if extra and extra.get('nomag'):
            out['mag'] = out['reload'] = None
        if extra and extra.get('heat_sim'):  # time to kill waits out overheats (see kill)
            out['heat_sim'] = True
        if extra and extra.get('charge') is not None:
            out['charge'] = extra['charge']
            out['interval'] = 1.0 / out['rps'] if out['rps'] else 0.0
        for k in ('speed', 'range', 'aim'):  # a candidate's own projectile / aim assist
            if extra and extra.get(k) is not None:
                out[k] = tuple(extra[k]) if k == 'aim' else extra[k]
        if extra and extra.get('mods'):      # per-material modifiers over the base table
            for d in out['damage']:
                d['mods'].update(extra['mods'])
        if extra and extra.get('radius'):    # a candidate's own splash (inner, outer wu)
            for d in out['damage']:
                d['radius'] = tuple(extra['radius'])
    if extra and extra.get('cap'):
        out['cap'] = extra['cap']
    if extra and extra.get('burst'):         # (rounds, spacing s, cycle s): Halo 3's burst
        out['burst'] = extra['burst']
    apply_rows(out, overrides)
    return out


AIM = ('Autoaim Angle', 'Autoaim Range', 'Magnetism Angle', 'Magnetism Range')


def apply_rows(out, rows):
    """Catalog balance rows over one computed weapon, for the fields that change a time to
    kill or the role table: trigger rate / charge, aim assist, damage, splash, per-material
    modifiers. (Energy, ammo, animation rows do not enter the simulation.)"""
    aim = list(out['aim'])
    for r in rows:
        f, v = r['field'], r['value']
        if r['class'] == 'weap':
            if f == 'Charging Time':
                out['charge'] = v
            elif f in ('Rounds Per Second', 'Rounds Per Second Max'):
                out['rps'] = v if f == 'Rounds Per Second Max' else max(v, out.get('rps') or 0)
            elif f == 'Rounds Loaded Maximum':          # a magazine row (the SMG's 112)
                out['mag'] = int(v)
            elif f in AIM:
                aim[AIM.index(f)] = v
            elif f == 'Age Generated Per Round':
                out['age'] = v
        elif r['class'] == 'jpt!':
            for d in out['damage']:
                if d['tag'].lower() != r['tag'].lower():
                    continue
                if f == 'Radius':
                    d['radius'] = (v, d['radius'][1])
                elif f == 'Radius Max':
                    d['radius'] = (d['radius'][0], v)
                elif f in ('Damage Upper Bound', 'Damage Upper Bound Max'):
                    # the two bounds of the random range, kept apart: damage = their mean
                    # (the Mauler's balanced pellet 12.6..17.5; earlier ports wrote both alike)
                    d.setdefault('up', [d['dmg'], d['dmg']])[f.endswith('Max')] = v
                    d['dmg'] = sum(d['up']) / 2.0
                else:
                    key = f.lower().replace(' ', '_')
                    if key in d['mods']:
                        d['mods'][key] = v
    out['aim'] = tuple(aim)
    if out['mode'] != 'melee':
        # a MEASURED engine cap wins over a balanced rate row (SMG: the 22.5 row fires 15/s)
        if out.get('cap') and out.get('rps'):
            out['rps'] = min(out['rps'], out['cap'])
        out['interval'] = 1.0 / out['rps'] if out.get('rps') else 0.0
        if out['charge']:
            out['interval'] = max(out['interval'], out['charge'])
        if out.get('burst'):                 # the mean interval: a burst's rounds per cycle
            out['interval'] = out['burst'][2] / out['burst'][0]
            out['tag_rps'] = None            # not a measured rate: no '*'


def balanced_anims(port):
    """The port's catalog animation multipliers ({'reload': x, 'swap': x})."""
    cat = json.load(open(CATALOG, encoding='utf-8'))
    e = next((x for x in cat.get('Halo 1', []) if x['weapon'] == port), None)
    return (e or {}).get('anims') or {}


def balanced_overrides(port):
    """The port's catalog balance rows (Halo 1)."""
    cat = json.load(open(CATALOG, encoding='utf-8'))
    e = next((x for x in cat.get('Halo 1', []) if x['weapon'] == port), None)
    return e.get('balance', []) if e else []


def scales():
    g = load(matg_def, r'globals\globals', '.globals')
    es = g.difficulties.STEPTREE[0].enemy_scales
    return {'normal': (es.vitality[1], es.shield[1]), 'legendary': (es.vitality[3], es.shield[3])}


def enemy(path, char):
    a = load(actv_def, path, '.actor_variant')
    c = load(coll_def, os.path.join('characters', char, char), '.model_collision_geometry')
    body = (a.unit_properties.body_vitality if a and a.unit_properties.body_vitality else
            c.body.maximum_body_vitality)
    shield = (a.unit_properties.shield_vitality if a and a.unit_properties.shield_vitality else
              c.shield.maximum_shield_vitality)
    body_mat = c.materials.STEPTREE[0].material_type.enum_name if len(c.materials.STEPTREE) else ''
    shield_mat = c.shield.shield_material_type.enum_name
    if char == 'jackal':                     # the hand shield is a separate target
        shield = 0
    return body, shield, body_mat, shield_mat


def heat_times(wpn, shots):
    """Times of `shots` rounds fired as fast as the rate and HEAT allow (a semi-automatic
    tapped at its cap): the heat falls by loss/s in each gap; a round that reaches the
    overheated threshold locks the trigger until the heat is back at the recovery threshold
    (Halo 3: at the overheated loss/s). ASSUMED for Halo 1: a tapped weapon cools between
    taps (the Sentinel Beam's 'cools only while not firing' was a HELD trigger)."""
    hpr, oh, loss, rec = wpn['heat'][:4]
    loss_oh = wpn['heat'][4] if len(wpn['heat']) > 4 else loss
    t, heat, out = 0.0, 0.0, []
    for k in range(shots):
        if k:
            if heat >= oh:                       # overheated: wait for the recovery threshold
                wait = max(wpn['interval'], (heat - rec) / loss_oh if loss_oh else 1e9)
                heat = max(0.0, heat - wait * loss_oh)
            else:
                wait = wpn['interval']
                heat = max(0.0, heat - wait * loss)
            t += wait
        heat += hpr
        out.append(t)
    return out


def kill(wpn, body, shield, bmat, smat):
    """(shots, seconds) for a burst from cold."""
    per = []
    for d in wpn['damage']:
        per.append((d['dmg'] * d['mods'].get(smat, 1.0), d['dmg'] * d['mods'].get(bmat, 1.0)))
    if not per:
        return None, None
    s_hit = sum(p[0] for p in per) * wpn['per_shot']
    b_hit = sum(p[1] for p in per) * wpn['per_shot']
    if b_hit <= 0:
        return None, None
    shots, sh, bo = 0, shield, body
    while bo > 0 and shots < 500:
        shots += 1
        if sh > 0 and s_hit > 0:
            if s_hit >= sh:                  # the killing shot's overflow reaches the body
                frac = 1 - sh / s_hit
                sh = 0
                bo -= b_hit * frac
            else:
                sh -= s_hit
        else:
            bo -= b_hit
    if wpn.get('burst'):                     # whole cycles, then the spacing inside the last burst
        n, spacing, cycle = wpn['burst']
        t = wpn['charge'] + ((shots - 1) // n) * cycle + ((shots - 1) % n) * spacing
    else:
        t = wpn['charge'] + (shots - 1) * wpn['interval']
    if wpn.get('heat_sim'):
        t = wpn['charge'] + heat_times(wpn, shots)[-1]
    if wpn.get('mag') and wpn.get('reload'):
        per_mag = max(1, wpn['mag'] // max(1, wpn.get('rounds_per_shot') or 1))
        t += ((shots - 1) // per_mag) * wpn['reload']
    return shots, t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('set', choices=sorted(SETS))
    ap.add_argument('--balanced', action='store_true')
    a = ap.parse_args()
    s = SETS[a.set]
    over = balanced_overrides(s['port']) if a.balanced else []
    rows = [weapon(e[0], e[1], e[2], over if '(restored)' in e[0] or '(port)' in e[0] else [],
                   e[3] if len(e) > 3 else None)
            for e in s['weapons']]
    if a.balanced:                       # the catalog's reload retime (anims) too
        mult = balanced_anims(s['port']).get('reload')
        for r, e in zip(rows, s['weapons']):
            if mult and r.get('reload') and ('(restored)' in e[0] or '(port)' in e[0]):
                r['reload'] *= mult
    enemies = ENEMIES + s.get('enemies', [])
    print('%s%s\n' % (s['port'], '  -- BALANCED rows applied' if a.balanced else ''))
    print('%-26s %8s %7s %8s %6s %6s %5s %6s %6s %6s  %s' % (
        'weapon', 'damage', 'splash', 'interval', 'rate', 'dps', 'mag', 'reload', 'speed',
        'range', 'aim assist (deg/wu auto, magnet)'))
    for r in rows:
        dmg = '+'.join('%g' % round(d['dmg'], 1) for d in r['damage']) or '-'
        spl = max((d['radius'][1] for d in r['damage']), default=0)
        rate = 1.0 / r['interval'] if r['interval'] else 0
        dps = sum(d['dmg'] for d in r['damage']) * r['per_shot'] * rate
        tag = r.get('tag_rps')
        rtxt = ('%g' % rate) + ('*' if tag and abs(tag - rate) > 0.01 else '')
        print('%-26s %8s %7s %7.2fs %6s %6.0f %5s %6s %6s %6s  %4.1f/%-4g %4.1f/%-4g'
              % (r['label'], dmg, '%.2f' % spl if spl else '-', r['interval'], rtxt, dps,
                 r.get('mag') or '-', '%.1fs' % r['reload'] if r.get('reload') else '-',
                 '%g' % r['speed'] if r.get('speed') else '-',
                 '%g' % r['range'] if r.get('range') else '-', *r['aim']))
    if any(r.get('tag_rps') and abs(r['tag_rps'] - 1.0 / r['interval']) > 0.01 for r in rows
           if r['interval']):
        print('  * measured in game, not the tag rate (tag: %s)' % ', '.join(
            '%s %g/s' % (r['label'], r['tag_rps']) for r in rows
            if r.get('tag_rps') and r['interval'] and abs(r['tag_rps'] - 1.0 / r['interval']) > 0.01))
    hot = [r for r in rows if r.get('heat') and (r['heat'][0] or r.get('age'))]
    if hot:
        print('\nSUSTAINED FIRE (heat / battery)')
        print('%-26s %9s %9s %9s %10s %8s %10s %9s' % ('weapon', 'heat/rnd', 'overheat', 'loss/s',
                                                      'to overheat', 'vent', 'battery', 'per batt'))
        for r in hot:
            hpr, oh, loss, rec = r['heat'][:4]
            rate = 1.0 / r['interval']
            net = hpr * rate - loss
            t_oh = ('%.1fs' % (oh / net)) if hpr and net > 0 else 'never'
            vent = ('%.1fs' % ((oh - rec) / loss)) if hpr and loss else '-'
            rounds = (1.0 / r['age']) if r.get('age') else 0
            if r.get('heat_sim'):            # a tapped weapon: count rounds, vent at its own loss
                loss_oh = r['heat'][4] if len(r['heat']) > 4 else loss
                n, heat = 0, 0.0
                while heat < oh and n < 999:
                    heat = max(0.0, heat - (r['interval'] * loss if n else 0)) + hpr
                    n += 1
                t_oh = '%d rnds' % n if n < 999 else 'never'
                vent = '%.1fs' % ((oh - rec) / loss_oh) if loss_oh else '-'
                times = heat_times(r, 400)
                in10 = sum(1 for x in times if x < 10.0)
                dmg = sum(d['dmg'] for d in r['damage']) * r['per_shot']
                extra = '  10 s: %d rnds = %.0f dps' % (in10, in10 * dmg / 10.0)
            else:
                extra = ''
            print('%-26s %9.4f %9g %9g %10s %8s %10s %9s%s'
                  % (r['label'], hpr, oh, loss, t_oh, vent,
                     ('%d rnds' % rounds) if rounds else '-',
                     ('%.1fs' % (rounds / rate)) if rounds else '-', extra))
    sc = scales()
    for diff in ('normal', 'legendary'):
        vs, ss = sc[diff]
        print('\nTIME TO KILL, %s (shots / seconds, burst from cold, direct hits)' % diff)
        print('%-26s' % 'weapon' + ''.join('%-17s' % e[0][:16] for e in enemies))
        stats = [(lbl,) + enemy(p, ch) for lbl, p, ch in enemies]
        for r in rows:
            line = '%-26s' % r['label']
            for _l, body, shield, bm, sm in stats:
                n, t = kill(r, body * vs, shield * ss, bm, sm)
                line += '%-17s' % ('-' if n is None else '%d / %.2fs' % (n, t))
            print(line)
    print('\nenemies: ' + '; '.join('%s %g/%g (%s, %s)' % (st[0], st[1], st[2], st[3], st[4])
                                    for st in stats))


if __name__ == '__main__':
    main()
