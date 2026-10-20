r"""Build the Halo 2 entry of weapon_ports_catalog.json from the chosen balance table.

Same shape as `make_port_catalog_h3.py`: every row of the table names the tag its value was
READ from -- the donor's -- so each has to be redirected onto the port's own tag.

Halo 2's redirections:

  * most rows are the SMG's, which is the donor the last hop measures against, and land on
    the SAW's own weapon, projectile and damage effect;
  * three rows are read from the ASSAULT RIFLE, because Halo 2 has no SMG equivalent of the
    field and the chain's first hop measured there. They still belong on the SAW's weapon;
  * the melee rows point at `objects\weapons\damage_effects\strike_melee`, which every Halo 2
    weapon shares. Writing there would retune the melee of the entire sandbox, so they are
    DROPPED -- a ported weapon has no business doing that. (The port's own tag references the
    same shared effect, which is correct: its melee should BE everyone's.)

Unlike Halo 3, the port owns its animation graphs, so `anims` is filled: the reload can be
scaled because retiming it cannot reach any live weapon.

    python make_port_catalog_h2.py [<key>] [--write]

PER PORT (H2_PORT_PLAN.md phase 0, 2026-10-20): <key> names a ports_h2 config (default 'saw');
its `catalog` section gives the table, the donor-tag -> port-tag redirections (`port_tags`), the
SHARED tags whose rows are dropped, the FP graph pattern, the reload multiplier and the entry's
description. Only that port's entry changes (others kept as read); the write holds the Halo 1
kit lock, which guards every shared record (weapon_ports_catalog.json is one file for all games).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
TABLE = os.path.join(HERE, 'balance_SAW_Halo4_to_Halo2.json')
OUT = os.path.join(TOOL, 'weapon_ports_catalog.json')
B = os.sep

SMG = B.join(['objects', 'weapons', 'rifle', 'smg'])
AR = B.join(['objects', 'weapons', 'rifle', 'assault_rifle'])
SAW = B.join(['objects', 'weapons', 'rifle', 'saw'])

#: donor tag -> the port's own tag, as h2_saw_weapon.py created it
PORT_TAGS = {
    ('weap', SMG + B + 'smg'): SAW + B + 'saw',
    ('weap', AR + B + 'assault_rifle'): SAW + B + 'saw',
    ('proj', SMG + B + 'projectiles' + B + 'smg_bullet'):
        SAW + B + 'projectiles' + B + 'saw_bullet',
    ('proj', AR + B + 'projectiles' + B + 'assault_rifle_bullet'):
        SAW + B + 'projectiles' + B + 'saw_bullet',
    ('jpt!', SMG + B + 'damage_effects' + B + 'smg_bullet'):
        SAW + B + 'damage_effects' + B + 'saw_bullet',
}
SHARED = {('jpt!', B.join(['objects', 'weapons', 'damage_effects', 'strike_melee']))}

#: The port's own first-person graphs, one per player species. `halo3_reload` matches jmad
#: tags by pattern, and these are the port's alone -- the sniper rifle they were cloned from
#: keeps its own, so scaling here cannot reach a live weapon.
FP_ANIMATIONS = B.join(['objects', 'characters', '*', 'fp', 'weapons', 'rifle',
                        'fp_saw', 'fp_saw'])

#: The reload is BUILT at the SAW's own 128 frames and the card takes it to the balanced
#: 109, because `scale_reload` can only shorten. Measured from each kit's own first-person
#: graphs: H4 SAW 128, H4 AR 68, H3 AR 58, H3 SMG 50, H2 SMG 50, so the chain is
#: 58/68 x 50/50 = 0.853. The Halo 3 port arrived at the same multiplier independently.
RELOAD_MULT = round(109.0 / 128.0, 6)
WEAPON_TAG = SAW + B + 'saw'
DESC = ('%s carried from %s into Halo 2, built on the cut GPMG and balanced through '
        'the Assault Rifle into Halo 3 and the SMG out of it. It owns its own '
        'first-person animations, so its reload can be retimed.')


def setup(key):
    """Point the module at one ports_h2 config's `catalog` section."""
    global TABLE, PORT_TAGS, SHARED, FP_ANIMATIONS, RELOAD_MULT, WEAPON_TAG, DESC
    sys.path.insert(0, HERE)
    import ports_h2
    c = ports_h2.get(key, 'catalog')
    TABLE = os.path.join(HERE, c['table'])
    PORT_TAGS = {tuple(k): v for k, v in c['port_tags']}
    SHARED = {tuple(x) for x in c.get('shared', ())}
    FP_ANIMATIONS, RELOAD_MULT = c['fp_animations'], c.get('reload_mult')
    WEAPON_TAG, DESC = c['weapon_tag'], c['desc']


def main():
    write = '--write' in sys.argv
    keys = [a for a in sys.argv[1:] if not a.startswith('--')]
    setup(keys[0] if keys else 'saw')
    t = json.load(open(TABLE, encoding='utf-8'))
    rows, dropped = [], []
    for r in t['rows']:
        key = (r.get('dst_class'), r.get('dst_tag'))
        if r.get('balanced') is None or not r.get('dst_field'):
            continue
        if key in SHARED:
            dropped.append((r['card'], '%s (shared with every weapon)' % r['dst_field']))
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

    # DERIVED (2026-10-05): Halo 2 keeps Rounds Total Maximum = Rounds Inventory Maximum +
    # Rounds Loaded Maximum (the Magazine card writes the inventory and DERIVES the total,
    # halo.json). Port balance rows are written field by field (apply_weapon_ports), never
    # derived, so without this row the balanced reserve sat beside the built total (288).
    have = {r['field']: r['value'] for r in rows if r.get('block') == 'Magazines'}
    parts = ('Rounds Inventory Maximum', 'Rounds Loaded Maximum')
    if all(isinstance(have.get(p), (int, float)) for p in parts):
        rows.append({'class': 'weap', 'tag': WEAPON_TAG, 'field': 'Rounds Total Maximum',
                     'block': 'Magazines', 'value': round(float(sum(have[p] for p in parts)), 6),
                     'card': 'Magazine', 'original': None,
                     'note': 'derived from %s' % ' + '.join(parts)})
    else:
        print('   Rounds Total Maximum: cannot derive (%s)' % {p: have.get(p) for p in parts})
    entry = {
        'weapon': t['ported'], 'source': t['source'], 'donor': t['donor'],
        'default_on': True,
        'desc': DESC % (t['ported'], t['source']) if '%s' in DESC else DESC,
        'balance': rows,
        'fp_animations': FP_ANIMATIONS,
    }
    if RELOAD_MULT is not None:
        entry['anims'] = {'reload': RELOAD_MULT}

    print('%d balance row(s)' % len(rows))
    by_tag = {}
    for r in rows:
        by_tag[r['tag']] = by_tag.get(r['tag'], 0) + 1
    for tag, n in sorted(by_tag.items()):
        print('   %-62s %d' % (tag, n))
    print('\nanimations: reload x%s, graphs %s' % (RELOAD_MULT, FP_ANIMATIONS))
    print('\n%d row(s) dropped:' % len(dropped))
    for card, why in dropped:
        print('   %-20s %s' % (card, why))

    if write:
        sys.path.insert(0, HERE)
        import kit_lock
        with kit_lock.held('make_port_catalog_h2 %s' % entry['weapon'], owner='catalog'):
            _write(entry)
    else:
        print('\n(dry run -- pass --write)')


def _write(entry):
    if True:
        cat = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
        cat.setdefault('Halo 2', [])
        for old in cat['Halo 2']:
            if old.get('weapon') == entry['weapon']:
                for k in ('ammo',):        # wired in separately; never drop it silently
                    if old.get(k) and not entry.get(k):
                        entry[k] = old[k]
        cat['Halo 2'] = ([e for e in cat['Halo 2'] if e.get('weapon') != entry['weapon']]
                         + [entry])
        json.dump(cat, open(OUT, 'w', encoding='utf-8'), indent=1)
        print('\nwrote %s' % OUT)


if __name__ == '__main__':
    main()
