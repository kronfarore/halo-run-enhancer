r"""Build the Halo 4 entry of weapon_ports_catalog.json -- the H4 port kit's step 4/5.

First weapon: Reach's Focus Rifle, balanced through the SNIPER RIFLE -- the user's call
after the first boot: balance-wise the Focus Rifle is a sniper that happens to be a laser.
(The Plasma Pistol was tried first for its heat and battery; the Concussion Rifle carries
neither.) The Sniper Rifle is in both games and scales zoom, rate and velocity:

    python balance_port.py "Focus Rifle" "Halo Reach" "Halo 4" --hop "Sniper Rifle:Halo Reach>Halo 4"
    python make_port_catalog_h4.py [--write]

REDIRECTION. The table's rows name the donor's Halo 4 tags; each is moved onto the port's
own (h4_make_port_weapon.py made them):
    weap storm_sniper_rifle           -> focus_rifle\focus_rifle
    proj storm_sniper_rifle_bullet    -> focus_rifle\projectiles\focus_rifle_beam

THE PORT'S OWN, where the donor has nothing to scale by. The Sniper Rifle has no heat and
no battery, so those rows are absent from the table -- and they are the Focus Rifle's
defining numbers. They are carried as its own Reach values (OWN below): heat is a
fraction and age a fraction per round in both games, so no unit changes. Rows whose donor
reads 0 on both sides keep the port's own value too.

MEASURED: BEAM DAMAGE. The table has no Beam Damage rows, and it matters: the copied
Sentinel "friendly" beam deals ZERO in Halo 4, so without these rows the port does
nothing. Scaled by the same donor, read from both kits' tags: the sniper round is 80 in
Reach and 80 in Halo 4 -> x1.0, so the Focus Rifle's 3 per round stays 3.

DROPPED: melee (globals\damage_effects\strike_melee is the whole sandbox's), the fp
animation row (the port shares fp_beam_rifle with the Beam Rifle, so retiming it would
retime the Beam Rifle), and Shots Per Fire (Reach 0 = Halo 4's minimum 1). No ammo
pickup: an energy weapon.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
TABLE = os.path.join(HERE, 'balance_Focus_Rifle_HaloReach_to_Halo4.json')
OUT = os.path.join(TOOL, 'weapon_ports_catalog.json')
B = os.sep

SN = B.join(['objects', 'weapons', 'rifle', 'storm_sniper_rifle'])
FR = B.join(['objects', 'weapons', 'rifle', 'focus_rifle'])
PORT_WEAPON = FR + B + 'focus_rifle'
PORT_BEAM = FR + B + 'projectiles' + B + 'focus_rifle_beam'
PORT_TAGS = {
    ('weap', SN + B + 'storm_sniper_rifle'): PORT_WEAPON,
    ('proj', SN + B + 'projectiles' + B + 'storm_sniper_rifle_bullet'): PORT_BEAM,
}
SHARED = {('jpt!', B.join(['globals', 'damage_effects', 'strike_melee']))}
SKIP_CLASS = {'jmad': 'the port shares fp_beam_rifle with the Beam Rifle'}
#: Reach stores Shots Per Fire as 0; Halo 4's tag refuses 0 and keeps its minimum 1 --
#: the same single shot per trigger pull. Written as 0 into a map it would be neither.
SKIP_FIELDS = {'Shots Per Fire': 'Reach 0 = Halo 4 minimum 1; the tag keeps 1',
               'Shots Per Fire Max': 'Reach 0 = Halo 4 minimum 1; the tag keeps 1'}

#: sniper round damage, Reach 80 -> Halo 4 80, read from both kits' tags
DAMAGE_SCALE = 80.0 / 80.0
FOCUS_DAMAGE = 3.0                    # Reach focus_rifle_beam.damage_effect, both bounds
MEASURED = [
    {'class': 'jpt!', 'tag': PORT_BEAM, 'field': f, 'block': None,
     'value': round(FOCUS_DAMAGE * DAMAGE_SCALE, 6), 'card': 'Beam Damage',
     'original': FOCUS_DAMAGE,
     'note': 'measured: sniper round 80 (Reach) -> 80 (Halo 4)'}
    for f in ('Damage Lower Bound', 'Damage Upper Bound', 'Damage Upper Bound Max')
]

#: the Focus Rifle's own heat and battery (Reach), which the Sniper Rifle cannot scale
OWN = [
    {'class': 'weap', 'tag': PORT_WEAPON, 'field': f, 'block': blk, 'value': v,
     'card': card, 'original': v, 'note': "the port's own; the donor has none"}
    for card, f, blk, v in (
        ('Heat Threshold', 'Heat Recovery Threshold', None, 0.1),
        ('Heat Loss', 'Heat Loss Per Second', None, 0.35),
        ('Heat Loss', 'Overheated Heat Loss Per Second', None, 0.23),
        ('Heat Per Round', 'Heat Generated Per Round', 'Barrels', 0.025),
        ('Age Per Round', 'Age Generated Per Round', 'Barrels', 0.0016125))
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
    rows.extend(OWN)

    entry = {'weapon': t['ported'], 'source': t['source'], 'donor': t['donor'],
             'default_on': True,
             'desc': '%s carried from %s into Halo 4: its own model, the Beam Rifle\'s '
                     'first-person animations and HUD, the Sentinel Beam\'s beam. Numbers '
                     'scaled through the Sniper Rifle.' % (t['ported'], t['source']),
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
