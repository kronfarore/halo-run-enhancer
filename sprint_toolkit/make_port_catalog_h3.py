r"""Build the Halo 3 entry of weapon_ports_catalog.json from the chosen balance table.

Every row of the table names the tag its value was READ from -- the donor's -- so each
has to be redirected onto the port's own tag. Two redirections are less obvious than the
rest:

  * the velocity rows point at the MACHINE GUN TURRET's projectile, because bullet speed
    is measured against the Machine Gun (see port_families field_overrides), not the
    Assault Rifle. They still belong on the SAW's own bullet.
  * the melee rows point at objects\weapons\damage_effects\strike_melee, which every
    Halo 3 weapon shares. Writing there would change the melee of the entire sandbox, so
    they are DROPPED: a ported weapon has no business retuning everyone's melee.

Animations are left alone as well. The Halo 3 SAW still uses the Assault Rifle's
animation graph, so retiming it would retime the Assault Rifle too.

    python make_port_catalog_h3.py [--write]
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))  # balance tables live beside the JMS converters, see the port backup on F:
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE = os.path.join(HERE, 'balance_SAW_Halo4_to_Halo3_mgvel.json')
OUT = os.path.join(TOOL, 'weapon_ports_catalog.json')
B = os.sep

AR = B.join(['objects', 'weapons', 'rifle', 'assault_rifle'])
MG = B.join(['objects', 'weapons', 'turret', 'machinegun_turret'])
SAW = B.join(['objects', 'weapons', 'rifle', 'saw'])

# donor tag -> the port's own tag (as h3_make_saw.py created it)
PORT_TAGS = {
    ('weap', AR + B + 'assault_rifle'): SAW + B + 'saw',
    ('proj', AR + B + 'projectiles' + B + 'assault_rifle_bullet'):
        SAW + B + 'projectiles' + B + 'saw_bullet_h4_original_numbers',
    ('proj', MG + B + 'projectiles' + B + 'machinegun_turret_bullet'):
        SAW + B + 'projectiles' + B + 'saw_bullet_h4_original_numbers',
    ('jpt!', AR + B + 'damage_effects' + B + 'assault_rifle_bullet'):
        SAW + B + 'damage_effects' + B + 'saw_bullet_h4_original_numbers',
}
SHARED = {('jpt!', B.join(['objects', 'weapons', 'damage_effects', 'strike_melee']))}


# Rounds Total Maximum = Rounds Inventory Maximum + Rounds Loaded Maximum, measured on
# the Halo 3 Assault Rifle (352 + 32 = 384) and declared by the card's `derived` key.
DERIVED = [('Rounds Total Maximum', 'Magazines', 'weap',
            ['Rounds Inventory Maximum', 'Rounds Loaded Maximum'])]


def derived_rows(rows):
    """Totals the game stores but nothing recomputes: halo_patch._apply_derived is Halo 2
    only, so a balanced ceiling would otherwise sit beside a stale total."""
    have = {}
    for r in rows:
        if r.get('block') == 'Magazines':
            have[r['field']] = r['value']
    out = []
    for field, block, cls, parts in DERIVED:
        vals = [have.get(pp) for pp in parts]
        if any(v is None for v in vals):
            print('   %-24s cannot derive: missing %s'
                  % (field, [pp for pp, v in zip(parts, vals) if v is None]))
            continue
        total = sum(vals)
        print('   %-24s %s = %s' % (field, ' + '.join('%s %g' % (pp, v)
                                                      for pp, v in zip(parts, vals)),
                                    round(total, 2)))
        out.append({'class': cls, 'tag': PORT_TAGS[(cls, AR + B + 'assault_rifle')],
                    'field': field, 'block': block, 'value': round(float(total), 6),
                    'card': 'Magazine', 'original': None,
                    'note': 'derived from %s' % ' + '.join(parts)})
    return out


def main():
    write = '--write' in sys.argv
    t = json.load(open(TABLE, encoding='utf-8'))
    rows, dropped = [], []
    for r in t['rows']:
        key = (r.get('dst_class'), r.get('dst_tag'))
        if r.get('balanced') is None or not r.get('dst_field'):
            continue
        if key in SHARED:
            dropped.append((r['card'], r['dst_field']))
            continue
        if key not in PORT_TAGS:
            dropped.append((r['card'], '%s (no port tag for %s)' % (r['dst_field'], key[1])))
            continue
        row = {'class': key[0], 'tag': PORT_TAGS[key], 'field': r['dst_field'],
               'block': r.get('dst_block'),
               'value': round(float(r['balanced']), 6) if isinstance(r['balanced'], float)
                        else r['balanced'],
               'card': r['card'], 'original': r.get('original')}
        if r.get('dst_nth'):
            row['nth'] = r['dst_nth']
        if r.get('dst_index'):
            row['index'] = r['dst_index']
        rows.append(row)

    entry = {'weapon': t['ported'], 'source': t['source'], 'donor': t['donor'],
             'default_on': True,
             'desc': '%s carried from %s into Halo 3, built on the Assault Rifle. Bullet '
                     'speed is measured against the Machine Gun rather than the Assault '
                     'Rifle, which is 1500 in Halo 4 and 80 here.' % (t['ported'], t['source']),
             'balance': rows,
             'anims': {}}
    print('\nderived totals (nothing else recomputes these in Halo 3):')
    rows.extend(derived_rows(rows))

    entry['balance'] = rows
    print('\n%d balance row(s)' % len(rows))
    by_tag = {}
    for r in rows:
        by_tag[r['tag']] = by_tag.get(r['tag'], 0) + 1
    for tag, n in sorted(by_tag.items()):
        print('   %-70s %d' % (tag, n))
    print('\n%d row(s) dropped:' % len(dropped))
    for card, why in dropped:
        print('   %-20s %s' % (card, why))
    if write:
        cat = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
        cat.setdefault('Halo 3', [])
        cat['Halo 3'] = [e for e in cat['Halo 3'] if e.get('weapon') != entry['weapon']] + [entry]
        json.dump(cat, open(OUT, 'w', encoding='utf-8'), indent=1)
        print('\nwrote %s' % OUT)
    else:
        print('\n(dry run -- pass --write)')


if __name__ == '__main__':
    main()
