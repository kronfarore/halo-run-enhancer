r"""Build the Halo Reach entry of weapon_ports_catalog.json from its balance table.

Every row of the table names the tag its value was READ from -- the donor's -- so each is
redirected onto the port's own tag. Reach's redirection is the simplest of the four
games, for two reasons:

  * bullet speed is measured against the ASSAULT RIFLE, not a turret. Reach's Assault
    Rifle is exactly twice Halo 4's (3000 against 1500), a clean game scale, so there is
    no Machine Gun detour and no `_mgvel` table the way Halo 3 and ODST need;
  * the damage effect lives BESIDE the projectile and shares its path, so one entry in
    PORT_TAGS serves both classes.

WHAT IS DROPPED, and why each is right:

  * the MELEE rows, which point at `globals\damage_effects\strike_melee`. Every weapon in
    the game shares it. A ported weapon has no business retuning the whole sandbox's
    melee, so the three rows go.
  * the ANIMATION row. The table cannot compute it (it carries no value), so the reload
    comes from FP_ANIMATIONS / RELOAD_MULT below instead, as in ODST: the port owns both
    species' graphs (step 9), so retiming them cannot reach the Assault Rifle.

WHAT REACH DOES NOT NEED. ODST's catalog carries six `MEASURED` rows for fields no card
can reach there -- Air/Water Gravity Scale, Impact/Detonation Noise, Autoaim/Magnetism
Falloff Range. All six ARE card-reachable in Reach and come through the table normally,
so there is no measuring step here at all.

    python make_port_catalog_reach.py [--write]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
TABLE = os.path.join(HERE, 'balance_SAW_Halo4_to_HaloReach.json')
OUT = os.path.join(TOOL, 'weapon_ports_catalog.json')
B = os.sep

AR = B.join(['objects', 'weapons', 'rifle', 'assault_rifle'])
SAW = B.join(['objects', 'weapons', 'rifle', 'saw'])
AR_BULLET = AR + B + 'projectiles' + B + 'assault_rifle_bullet'
SAW_BULLET = SAW + B + 'projectiles' + B + 'saw_bullet_h4_original_numbers'

#: donor tag -> the port's own, as h3_make_saw.py created it under PORT_EK=reach.
#: The projectile and the damage effect share a path in Reach, so they share a key shape
#: and differ only by class.
PORT_TAGS = {
    ('weap', AR + B + 'assault_rifle'): SAW + B + 'saw',
    ('proj', AR_BULLET): SAW_BULLET,
    ('jpt!', AR_BULLET): SAW_BULLET,
}
#: tags the whole sandbox shares -- never written by a port
SHARED = {('jpt!', B.join(['globals', 'damage_effects', 'strike_melee']))}
#: classes this catalog does not carry at all, with the reason printed once
SKIP_CLASS = {'jmad': 'no value in the table -- carried by FP_ANIMATIONS/RELOAD_MULT'}

#: The port's OWN first-person graphs, one per species, as reach_foundry_fp_retime.py
#: wrote them: saw\fp_saw_spartans\fp_saw_spartans and saw\fp_saw_elite\fp_saw_elite.
#: The '*' matches both and NOT the Assault Rifle-timed originals left in saw\fp\.
FP_ANIMATIONS = SAW + B + 'fp_saw_*'

#: The reload is BUILT at the Halo 4 SAW's 128 frames. Balanced = the Reach AR's reload
#: x (H4 SAW / H4 AR) = 68 x 128/68 = 128: Reach's Assault Rifle reloads in exactly Halo
#: 4's 68 frames (reload_empty; reload_full 59), so the multiplier is 1.0 and the port
#: ships at its built timing. It is still carried so the reload and swap CARDS reach the
#: port's own graphs. Only reload: the ready (24 built) has no measured H4 AR count.
RELOAD_MULT = round(68.0 * 128.0 / 68.0 / 128.0, 6)

DST_GAME = 'Halo Reach'

#: Totals the game stores and nothing recomputes (halo_patch._apply_derived is Halo 2
#: only), so a balanced ceiling would otherwise sit beside a stale total.
#:
#: MEASURED on Reach's own Assault Rifle, and it is exact: the tag's `rounds total
#: maximum` reads 320 while the plugin's "Rounds Inventory Maximum" reads 288 and
#: "Rounds Loaded Maximum" 32 -- 288 + 32 = 320. The two are the same quantity at
#: different levels, which is also why reach_saw_tag_numbers writes the port's as
#: 216 + 72 = 288.
DERIVED = [('Rounds Total Maximum', 'Magazines', 'weap',
            ['Rounds Inventory Maximum', 'Rounds Loaded Maximum'])]

#: STEP 6, the ammo pickup. MEASURED on a built m20, not assumed: the plugin puts the
#: Magazines/Magazines element at 20 bytes with `Rounds` i16 at +0, and the equipment tag
#: reference's 4CC ('piqe', eqip backwards) sits at +4 -- so `ref_offset` is 4 and the
#: patcher writes the datum at ref_offset + 0xC, exactly as in ODST.
#:
#: REACH HAS THREE, where ODST has eight. It consolidated ammo into one generic box and
#: kept specials only for the two weapons that need them, so there is no assault-rifle or
#: pistol ammo to choose -- and no per-map `maps` key either, because all three are on all
#: ten missions.
AMMO_BLOCK = 'Magazines/Magazines'
AMMO_ANCHOR = 'Rounds'
AMMO_REF_OFFSET = 4
GEAR = B.join(['objects', 'gear', 'human', 'military'])
AMMO_DEFAULT = GEAR + B + 'ammo_box' + B + 'ammo_box'
AMMO_CHOICES = [
    (AMMO_DEFAULT, 'Ammo Box'),
    (GEAR + B + 'rocket_launcher_ammo' + B + 'rocket_launcher_ammo', 'Rocket Launcher Ammo'),
    (GEAR + B + 'sniper_rifle_ammo' + B + 'sniper_rifle_ammo', 'Sniper Rifle Ammo'),
]
AMMO_MISSIONS = 10


def ammo_block():
    return {'class': 'weap', 'tag': PORT_TAGS[('weap', AR + B + 'assault_rifle')],
            'block': AMMO_BLOCK, 'anchor_field': AMMO_ANCHOR,
            'ref_offset': AMMO_REF_OFFSET, 'item_class': 'eqip',
            'default': AMMO_DEFAULT, 'maps_total': AMMO_MISSIONS,
            'choices': [{'tag': t, 'label': l} for t, l in AMMO_CHOICES]}


def derived_rows(rows):
    have = {r['field']: r['value'] for r in rows if r.get('block') == 'Magazines'}
    out = []
    for field, block, cls, parts in DERIVED:
        vals = [have.get(p) for p in parts]
        if any(v is None for v in vals):
            print('   %-24s cannot derive: missing %s'
                  % (field, [p for p, v in zip(parts, vals) if v is None]))
            continue
        total = sum(vals)
        print('   %-24s %s = %s' % (field, ' + '.join('%s %g' % (p, v)
                                                      for p, v in zip(parts, vals)),
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
        if key[0] in SKIP_CLASS:
            dropped.append((r['card'], '%s (%s)' % (r['dst_field'], SKIP_CLASS[key[0]])))
            continue
        if key in SHARED:
            dropped.append((r['card'], '%s (shared by the whole sandbox)' % r['dst_field']))
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

    print('derived totals (nothing else recomputes these in Reach):')
    rows.extend(derived_rows(rows))

    entry = {'weapon': t['ported'], 'source': t['source'], 'donor': t['donor'],
             'default_on': True,
             'desc': '%s carried from %s into Halo Reach, built on the Assault Rifle. '
                     'Bullet speed is measured against the Assault Rifle, which Reach '
                     'runs at exactly twice Halo 4\'s. It has its own first-person '
                     'animations, so its reload can be retimed.'
                     % (t['ported'], t['source']),
             'balance': rows,
             'ammo': ammo_block(),
             'fp_animations': FP_ANIMATIONS,
             'anims': {'reload': RELOAD_MULT}}

    print('\n%d balance row(s)' % len(rows))
    by_tag = {}
    for r in rows:
        by_tag[r['tag']] = by_tag.get(r['tag'], 0) + 1
    for tag, n in sorted(by_tag.items()):
        print('   %-70s %d' % (tag, n))
    print('\n%d row(s) dropped:' % len(dropped))
    for card, why in dropped:
        print('   %-20s %s' % (card, why))

    if not write:
        print('\n(dry run -- pass --write)')
        return
    cat = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    cat.setdefault(DST_GAME, [])
    # Keep whatever the existing entry carries that the balance table does not produce --
    # the ammo-pickup choices are wired in separately, and regenerating the numbers must
    # not silently drop them (which is how Halo 1's went missing once).
    for old in cat[DST_GAME]:
        if old.get('weapon') == entry['weapon']:
            for k in ('ammo', 'fp_animations', 'anims'):
                if old.get(k) and not entry.get(k):
                    entry[k] = old[k]
    cat[DST_GAME] = ([e for e in cat[DST_GAME] if e.get('weapon') != entry['weapon']]
                     + [entry])
    json.dump(cat, open(OUT, 'w', encoding='utf-8'), indent=1)
    print('\nwrote %s' % OUT)


if __name__ == '__main__':
    main()
