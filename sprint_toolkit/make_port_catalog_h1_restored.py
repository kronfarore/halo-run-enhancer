r"""weapon_ports_catalog.json entries for Halo 1's RESTORED weapons -- the Elites' Energy
Sword and the Grunts' fuel rod made pickable (h1_pickable_weapons.py, PORTING.md "Halo 1:
enemy-only weapons made pickable").

They are not carried from another game: 'source' is Halo 1, the weapon tags keep their
stock paths. The STOCK baselines carry the AI-only versions under those same paths, so
each entry names `requires` -- a tag only the player build has -- and the enhancer counts
the port as present on a level only when its weap AND every `requires` tag are in the map
(the enhancer session's rule, cb8413d).

The fuel rod is catalogued as 'Flak Cannon', the name halo.json already uses for the fuel
rod in Halo 2-4, so a run carries it across games; its H1 cards derive from the donor
(Rocket Launcher, port_cards.py).

BALANCE rows (shape of the SAW's: class / tag / field / block / value / original, Assembly
Halo1 plugin units, a range field as `<field>` + `<field> Max`). The values are the
enhancer session's PROPOSAL put to the user (2026-10-06); 'original' is the shipped tag:
  Flak Cannon   Triggers 'Charging Time' 1.25 -> 0 -- instant fire. The Grunts carry the
                same weapon tag, so their fuel rods fire instantly too.
  Energy Sword  aim assist 10 deg / 2.5 wu, 10 deg / 6 wu -> 15 / 3.5, 15 / 8 (Halo 3's
                values are the original); the lunge strike's own damage radius
                (`lunge strike`, split from the sword's melee so nothing else moves)
                0.5 / 0.5 -> 1.0 / 1.0.

    python make_port_catalog_h1_restored.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
OUT = os.path.join(TOOL, 'weapon_ports_catalog.json')
B = '\\'
SWORD = B.join(['weapons', 'energy sword', 'energy sword'])
STRIKE = B.join(['weapons', 'energy sword', 'lunge strike'])
ROD = B.join(['weapons', 'fuel rod gun', 'fuel rod'])
ROD_BLAST = B.join(['weapons', 'fuel rod gun', 'grunt explosion'])
GRUNT_ROD = B.join(['characters', 'grunt', 'grunt specops fuel rod'])
SB = B.join(['weapons', 'sentinel beam', 'sentinel beam'])


RENAMED = ('Energy Sword',)
# NOT emitted here, on purpose: keys the enhancer session owns survive the merge -- the
# Flak Cannon's 'tag_map'; its 'skip_cards' was removed (user: the Zoom card GIVES the
# fuel rod a zoom), so do not add it back.


def row(cls, tag, field, value, original, card, block=None):
    return {'class': cls, 'tag': tag, 'field': field, 'block': block, 'value': value,
            'card': card, 'original': original}


ENTRIES = [
    # 'Energy Blade', not 'Energy Sword' (user, 2026-10-06): halo.json's H2-H4 sword entry,
    # so a run carries ONE sword across games
    {'weapon': 'Energy Blade', 'source': 'Halo 1', 'donor': None, 'default_on': False,
     'desc': "The Elites' energy sword, made pickable: Halo 3's first-person animations "
             "and sounds, Halo 1's own sword. Fire lunges (costs energy), melee slashes.",
     'balance_desc': 'One lunge kills an Elite (420 damage), 20 lunges per charge, stronger '
                     'lunge aim assist (15 deg / 3.5 wu, 15 deg / 8 wu) and a wider lunge hit.',
     'fp_animations': B.join(['weapons', 'energy sword', 'fp', 'fp']),
     # the lunge strike exists only in the player build
     'requires': ['proj ' + B.join(['weapons', 'energy sword', 'lunge'])],
     'anims': {},
     'balance': [
         row('weap', SWORD, 'Autoaim Angle', 15.0, 10.0, 'Lunge aim assist'),
         row('weap', SWORD, 'Autoaim Range', 3.5, 2.5, 'Lunge aim assist'),
         row('weap', SWORD, 'Magnetism Angle', 15.0, 10.0, 'Lunge aim assist'),
         row('weap', SWORD, 'Magnetism Range', 8.0, 6.0, 'Lunge aim assist'),
         row('jpt!', STRIKE, 'Radius', 1.0, 0.5, 'Lunge damage radius'),
         row('jpt!', STRIKE, 'Radius Max', 1.0, 0.5, 'Lunge damage radius'),
         # step 5b (h1_role_compare.py energy_blade, user-approved 2026-10-06): the lunge
         # kills like Halo 3's -- 420 is one lunge through an Elite commander on legendary
         # (280 shield + 140 body; every material x1); the slash stays 151
         row('jpt!', STRIKE, 'Damage Lower Bound', 420.0, 151.0, 'Lunge damage'),
         row('jpt!', STRIKE, 'Damage Upper Bound', 420.0, 151.0, 'Lunge damage'),
         row('jpt!', STRIKE, 'Damage Upper Bound Max', 420.0, 151.0, 'Lunge damage'),
         # Halo 1 charges energy per swing where Halo 3 charges per kill: 20 lunges, not 10
         row('weap', SWORD, 'Age Generated Per Round', 0.05, 0.1, 'Energy per lunge',
             block='Triggers'),
     ]},
    {'weapon': 'Flak Cannon', 'source': 'Halo 1', 'donor': 'Rocket Launcher', 'default_on': False,
     'desc': "The Grunts' fuel rod, made pickable: Halo 3's first-person animations and "
             "sounds on the original gun. Hold fire to charge; it fires when full.",
     'balance_desc': 'Instant fire at 2.5 rods/s and it hurts Hunters (the Grunts\' fuel '
                     'rods too; they fire two rods per burst instead of one).',
     'fp_animations': B.join(['weapons', 'fuel rod gun', 'fp', 'fp']),
     # its own projectile (step 3) exists only in the player build
     'requires': ['proj ' + B.join(['weapons', 'fuel rod gun', 'grunt fuel rod'])],
     'anims': {},
     'balance': [
         row('weap', ROD, 'Charging Time', 0.0, 1.25, 'Charging Time', block='Triggers'),
         # step 5b (h1_role_compare.py flak_cannon, user-approved 2026-10-06): charge 0 alone
         # leaves the AI tag's 10 rounds/s -- as fast as one can click; Halo 3's fuel rod
         # fires at most every 0.4 s
         row('weap', ROD, 'Rounds Per Second', 2.5, 10.0, 'Rate of Fire', block='Triggers'),
         row('weap', ROD, 'Rounds Per Second Max', 2.5, 10.0, 'Rate of Fire', block='Triggers'),
         # the explosion does x0 to Hunters (Bungie's guard against Grunts hurting them);
         # the rocket launcher does x1. Grunts' fuel rods can then hurt Hunters too.
         row('jpt!', ROD_BLAST, 'Hunter Armor', 1.0, 0.0, 'Hunter damage'),
         row('jpt!', ROD_BLAST, 'Hunter Skin', 1.0, 0.0, 'Hunter damage'),
         # THE GRUNTS (a50 test 2026-10-06, user: "without the charge time they get to spam"):
         # their actor variants hold the trigger (Rate Of Fire 0) through 2.2 s bursts every
         # ~5 s. Vanilla, the 1.25 s charge allowed ONE rod per burst (~12/min); balanced,
         # the weapon's 2.5/s allows six (~46-69/min). 0.75 pulls/s = TWO rods per burst
         # (~23/min, twice vanilla) -- AI only, the player's fuel rod keeps 2.5/s.
         row('actv', GRUNT_ROD, 'Rate Of Fire', 0.75, 0.0, 'Grunt fuel rod rate'),
         row('actv', GRUNT_ROD + ' airdef', 'Rate Of Fire', 0.75, 0.0, 'Grunt fuel rod rate'),
     ]},
    # a FULL PORT from Halo 3 (2026-10-06, tested on c40 over 12 boots): Halo 1's Sentinels
    # carry no droppable weapon, so their death effect drops it (user's option B) -- it is
    # obtainable on the levels with Sentinels. Built on a copy of the plasma rifle, whose
    # cards it takes.
    {'weapon': 'Sentinel Beam', 'source': 'Halo 3', 'donor': 'Plasma Rifle', 'default_on': False,
     'desc': "Halo 3's Sentinel Beam: its model, first-person animations and sounds. "
             "Dropped by Sentinels when they die. A continuous beam on heat and battery.",
     'balance_desc': "Halo 1-style aim assist (1 deg / 25 wu autoaim, 12 deg / 25 wu "
                     "magnetism) and Halo 3's battery: 11 s of fire instead of 5.6 s.",
     'fp_animations': B.join(['weapons', 'sentinel beam', 'fp', 'fp']),
     # the weapon's own projectile exists only in the player build
     'requires': ['proj ' + B.join(['weapons', 'sentinel beam', 'beam'])],
     'anims': {},
     # step 5b (h1_role_compare.py sentinel_beam, user-chosen 2026-10-06). The default
     # keeps Halo 3's ABSOLUTE aim assist and a per-round battery ratio; balanced:
     'balance': [
         # the ratio rule on aim assist, plasma rifle yardstick (H1 5/25, 12/25; H3 5/12,
         # 9/18; H3 beam 1/12, 9/18): angle 5 x 1/5 = 1, range 25 x 12/12 = 25; magnet
         # 12 x 9/9 = 12, range 25 x 18/18 = 25 -- Halo 1's automatics reach 25 wu
         row('weap', SB, 'Autoaim Range', 25.0, 12.0, 'Aim assist'),
         row('weap', SB, 'Magnetism Angle', 12.0, 9.0, 'Aim assist'),
         row('weap', SB, 'Magnetism Range', 25.0, 18.0, 'Aim assist'),
         # Halo 3's battery TIME: 0.003 x 30/s = 333 rounds = 11.1 s; at Halo 1's real
         # 15/s that is 167 rounds = 0.006 per round (default 0.012 = 5.6 s)
         row('weap', SB, 'Age Generated Per Round', 0.006, 0.012, 'Battery per round',
             block='Triggers'),
     ]},
]


def main():
    cat = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    h1 = cat.setdefault('Halo 1', [])
    h1[:] = [e for e in h1 if e.get('weapon') not in RENAMED]   # entries under an old name
    for entry in ENTRIES:
        old = next((e for e in h1 if e.get('weapon') == entry['weapon']), {})
        merged = dict(old, **entry)              # keep what other tools added (e.g. 'ammo')
        h1[:] = [e for e in h1 if e.get('weapon') != entry['weapon']] + [merged]
        print('Halo 1 / %-12s %d balance row(s), requires %s'
              % (entry['weapon'], len(entry['balance']), entry['requires']))
    json.dump(cat, open(OUT, 'w', encoding='utf-8'), indent=1)
    print('wrote %s' % OUT)


if __name__ == '__main__':
    main()
