r"""Build the Halo 4 entry of weapon_ports_catalog.json -- the H4 port kit's step 4/5.

First weapon: Reach's Focus Rifle, balanced through the PLASMA PISTOL (the one Covenant
energy weapon in both Reach and Halo 4 with heat AND battery age, which are the Focus
Rifle's defining numbers; the Concussion Rifle was tried and carries neither):

    python balance_port.py "Focus Rifle" "Halo Reach" "Halo 4" --hop "Plasma Pistol:Halo Reach>Halo 4"
    python make_port_catalog_h4.py [--write]

REDIRECTION. The table's rows name the donor's Halo 4 tags; each is moved onto the port's
own (h4_make_port_weapon.py made them):
    weap storm_plasma_pistol          -> focus_rifle\focus_rifle
    proj storm_plasma_pistol_bolt     -> focus_rifle\projectiles\focus_rifle_beam

KEPT AS THE PORT'S OWN where the donor has nothing to scale by. A ratio needs a donor
reading on both sides; the Plasma Pistol has no zoom (0 and 0), so the table converts the
Focus Rifle's two zoom levels and zoom time to 0. The port is built on the Beam Rifle,
which HAS a scope, so those rows keep the Focus Rifle's own values -- zoom is the same
unit in both games.

MEASURED: BEAM DAMAGE. The table has no Beam Damage rows (the Plasma Pistol's damage sits
under a different card), and it matters: the copied Sentinel "friendly" beam deals ZERO
in Halo 4, so without these rows the port does nothing. Scale by the same donor, read from
both kits' tags: Plasma Pistol bolt 16 in Reach, 14 in Halo 4 -> x0.875, and the Focus
Rifle's 3 per round becomes 2.625.

DROPPED: melee (globals\damage_effects\strike_melee is the whole sandbox's) and the fp
animation row (the port shares fp_beam_rifle with the Beam Rifle, so retiming it would
retime the Beam Rifle). No ammo pickup: an energy weapon.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
TABLE = os.path.join(HERE, 'balance_Focus_Rifle_HaloReach_to_Halo4.json')
OUT = os.path.join(TOOL, 'weapon_ports_catalog.json')
B = os.sep

PP = B.join(['objects', 'weapons', 'pistol', 'storm_plasma_pistol'])
FR = B.join(['objects', 'weapons', 'rifle', 'focus_rifle'])
PORT_WEAPON = FR + B + 'focus_rifle'
PORT_BEAM = FR + B + 'projectiles' + B + 'focus_rifle_beam'
PORT_TAGS = {
    ('weap', PP + B + 'storm_plasma_pistol'): PORT_WEAPON,
    ('proj', PP + B + 'projectiles' + B + 'storm_plasma_pistol_bolt'): PORT_BEAM,
}
SHARED = {('jpt!', B.join(['globals', 'damage_effects', 'strike_melee']))}
SKIP_CLASS = {'jmad': 'the port shares fp_beam_rifle with the Beam Rifle'}
#: Reach stores Shots Per Fire as 0; Halo 4's tag refuses 0 and keeps its minimum 1 --
#: the same single shot per trigger pull. Written as 0 into a map it would be neither.
SKIP_FIELDS = {'Shots Per Fire': 'Reach 0 = Halo 4 minimum 1; the tag keeps 1',
               'Shots Per Fire Max': 'Reach 0 = Halo 4 minimum 1; the tag keeps 1'}

#: Plasma Pistol bolt damage, Reach 16 -> Halo 4 14, read from both kits' tags
DAMAGE_SCALE = 14.0 / 16.0
FOCUS_DAMAGE = 3.0                    # Reach focus_rifle_beam.damage_effect, both bounds
MEASURED = [
    {'class': 'jpt!', 'tag': PORT_BEAM, 'field': f, 'block': None,
     'value': round(FOCUS_DAMAGE * DAMAGE_SCALE, 6), 'card': 'Beam Damage',
     'original': FOCUS_DAMAGE,
     'note': 'measured: Plasma Pistol bolt 16 (Reach) -> 14 (Halo 4)'}
    for f in ('Damage Lower Bound', 'Damage Upper Bound', 'Damage Upper Bound Max')
]

DST_GAME = 'Halo 4'


def no_donor_reading(r):
    return not r.get('donor_src') and not r.get('donor_dst')


def main():
    write = '--write' in sys.argv
    t = json.load(open(TABLE, encoding='utf-8'))
    rows, dropped, kept = [], [], []
    for r in t['rows']:
        key = (r.get('dst_class'), r.get('dst_tag'))
        if not r.get('dst_field') or (r.get('balanced') is None and r.get('original') is None):
            continue
        if r['dst_field'] in SKIP_FIELDS:
            dropped.append((r['card'], '%s (%s)' % (r['dst_field'], SKIP_FIELDS[r['dst_field']])))
            continue
        if key[0] in SKIP_CLASS:
            dropped.append((r['card'], '%s (%s)' % (r['dst_field'], SKIP_CLASS[key[0]])))
            continue
        if key in SHARED:
            dropped.append((r['card'], '%s (shared by the whole sandbox)' % r['dst_field']))
            continue
        if key not in PORT_TAGS:
            dropped.append((r['card'], '%s (no port tag for %s)' % (r['dst_field'], key)))
            continue
        value = r['balanced']
        if no_donor_reading(r) and r.get('original'):
            value = r['original']
            kept.append((r['card'], r['dst_field'], r['original']))
        if value is None:
            continue
        row = {'class': key[0], 'tag': PORT_TAGS[key], 'field': r['dst_field'],
               'block': r.get('dst_block'),
               'value': round(float(value), 6) if isinstance(value, float) else value,
               'card': r['card'], 'original': r.get('original')}
        if r.get('dst_nth'):
            row['nth'] = r['dst_nth']
        if r.get('dst_index'):
            row['index'] = r['dst_index']
        rows.append(row)
    rows.extend(MEASURED)

    entry = {'weapon': t['ported'], 'source': t['source'], 'donor': t['donor'],
             'default_on': True,
             'desc': '%s carried from %s into Halo 4: its own model, the Beam Rifle\'s '
                     'first-person animations and HUD, the Sentinel Beam\'s beam. Numbers '
                     'scaled through the Plasma Pistol.' % (t['ported'], t['source']),
             'balance': rows}

    print('%d balance row(s)' % len(rows))
    by_tag = {}
    for r in rows:
        by_tag[r['tag']] = by_tag.get(r['tag'], 0) + 1
    for tag, n in sorted(by_tag.items()):
        print('   %-60s %d' % (tag, n))
    print('\nkept as the port\'s own (no donor reading):')
    for card, field, v in kept:
        print('   %-20s %-26s %s' % (card, field, v))
    print('\nmeasured: Beam Damage %g -> %g' % (FOCUS_DAMAGE, FOCUS_DAMAGE * DAMAGE_SCALE))
    print('\n%d row(s) dropped:' % len(dropped))
    for card, why in dropped:
        print('   %-20s %s' % (card, why))
    if not write:
        print('\n(dry run -- pass --write)')
        return
    cat = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    cat.setdefault(DST_GAME, [])
    cat[DST_GAME] = ([e for e in cat[DST_GAME] if e.get('weapon') != entry['weapon']]
                     + [entry])
    json.dump(cat, open(OUT, 'w', encoding='utf-8'), indent=1)
    print('\nwrote %s' % OUT)


if __name__ == '__main__':
    main()
