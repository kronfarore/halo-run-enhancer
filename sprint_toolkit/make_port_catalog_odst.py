r"""Build the Halo 3: ODST entry of weapon_ports_catalog.json from its balance table.

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

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join('C:' + os.sep, 'Program Files (x86)', 'Steam', 'steamapps', 'common',
                    'Halo The Master Chief Collection', 'tool')
TABLE = os.path.join(HERE, 'balance_SAW_Halo4_to_Halo3ODST_mgvel.json')
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

#: The port's OWN first-person graph. Unlike Halo 3 -- where the SAW shares the Assault
#: Rifle's and `anims` therefore has to ship empty -- this port was given its own clone,
#: so retiming it cannot reach a live weapon. ODST names ONE species graph where Halo 3
#: names two, and the port's clone keeps that shape.
FP_ANIMATIONS = B.join(['objects', 'weapons', 'rifle', 'saw', 'fp', 'fp_saw_*'])

#: The reload is BUILT at the SAW's own 128 frames and the card takes it to the balanced
#: 109, because `scale_reload` can only shorten. Measured from each kit's own graphs:
#: H4 SAW 128, H4 AR 68, ODST AR 58 -- so 58 x 128/68 = 109. ODST's Assault Rifle turns
#: out to be frame for frame Halo 3's (reload 58, ready 20, put_away 5), so this is the
#: same multiplier the Halo 3 port arrived at, reached independently.
RELOAD_MULT = round(109.0 / 128.0, 6)


# Rounds Total Maximum = Rounds Inventory Maximum + Rounds Loaded Maximum, measured on
# the Halo 3 Assault Rifle (352 + 32 = 384) and declared by the card's `derived` key.
DERIVED = [('Rounds Total Maximum', 'Magazines', 'weap',
            ['Rounds Inventory Maximum', 'Rounds Loaded Maximum'])]


# FIELDS NO CARD CAN CARRY INTO ODST, measured straight from the donor's tags instead.
# (field, block, class, which tag role it lives on)
#
# Two kinds, and the second is an ODST-only gap worth knowing about:
#   * Air / Water Gravity Scale -- the Assault Rifle's card does not target them in
#     Halo 3 either, so the Halo 3 catalog measures them the same way;
#   * Autoaim / Magnetism Falloff Range and Impact / Detonation Noise -- these targets
#     are allow-listed to ['Halo 3', 'Halo Reach', 'Halo 4'] in halo.json and ODST is
#     NOT in the list, although the fields exist there. target_applies does not inherit
#     (only the CARD level does), so the patcher genuinely will not write them in ODST
#     for any weapon. That is a halo.json question for the whole ODST card set and is
#     deliberately not changed from here; the port carries its own copies instead.
MEASURED = [('Air Gravity Scale', None, 'proj', 'proj'),
            ('Water Gravity Scale', None, 'proj', 'proj'),
            ('Impact Noise', None, 'proj', 'proj'),
            ('Detonation Noise', None, 'proj', 'proj'),
            ('Autoaim Falloff Range', None, 'weap', 'weap'),
            ('Magnetism Falloff Range', None, 'weap', 'weap')]
SRC_GAME, DST_GAME = 'Halo 4', 'Halo 3: ODST'
LMG = B.join(['objects', 'weapons', 'rifle', 'storm_lmg'])
S_AR = B.join(['objects', 'weapons', 'rifle', 'storm_assault_rifle'])
TAGS_BY_GAME = {
    'Halo 4': {'proj': S_AR + B + 'projectiles' + B + 'storm_assault_rifle_bullet',
               'weap': S_AR + B + 'storm_assault_rifle',
               'port_proj': LMG + B + 'projectiles' + B + 'storm_lmg_bullet',
               'port_weap': LMG + B + 'storm_lmg'},
    'Halo 3: ODST': {'proj': AR + B + 'projectiles' + B + 'assault_rifle_bullet',
                     'weap': AR + B + 'assault_rifle'},
}
#: where a measured row is written: the port's own tag of that class
MEASURED_DST = {
    'proj': (('proj', AR + B + 'projectiles' + B + 'assault_rifle_bullet')),
    'weap': (('weap', AR + B + 'assault_rifle')),
}
MISSIONS = {'Halo 4': ('halo4', 'm10_crash'),
            'Halo 3: ODST': ('halo3odst', 'sc100')}


def measured_rows():
    """Rows whose ratio is read from the donor's tags rather than through a card."""
    import contextlib, io as _io, sys
    sys.path.insert(0, TOOL)
    os.chdir(TOOL)
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    import halo_enhancer as he
    import halo_patch as hp
    he.load_settings()
    read = {}
    for game in (SRC_GAME, DST_GAME):
        folder, mission = MISSIONS[game]
        src = he.baseline_source(hp.default_map_path(he.mcc_root(), folder, mission), game)
        with contextlib.redirect_stdout(_io.StringIO()):
            m = hp.open_map(src, game)
        reg = hp.PluginRegistry(he.CONFIG.get('assembly_plugins_dir'),
                                he.CONFIG.get('plugin_subdirs_by_game', {}).get(game, []))
        for field, block, cls, role in MEASURED:
            for which in (role, 'port_' + role):
                tag = TAGS_BY_GAME[game].get(which)
                if not tag:
                    continue
                try:
                    read[(game, which, field)] = m.read_first(cls, tag, field,
                                                              reg.get(cls), block)
                except Exception:
                    read[(game, which, field)] = None
        del m
    out = []
    for field, block, cls, role in MEASURED:
        d_src = read.get((SRC_GAME, role, field))
        d_dst = read.get((DST_GAME, role, field))
        port = read.get((SRC_GAME, 'port_' + role, field))
        if not all(isinstance(v, (int, float)) for v in (d_src, d_dst, port)):
            print('   %-26s cannot measure (%s / %s / %s)' % (field, port, d_src, d_dst))
            continue
        value = port * (d_dst / float(d_src)) if d_src else (d_dst if port == d_src else port)
        print('   %-26s port %g, donor %g -> %g, gives %g'
              % (field, port, d_src, d_dst, value))
        out.append({'class': cls, 'tag': PORT_TAGS[MEASURED_DST[role]],
                    'field': field, 'block': block, 'value': round(float(value), 6),
                    'card': 'Projectile' if role == 'proj' else 'Autoaim',
                    'original': port,
                    'note': 'measured from the donor tags: no card target in ' + DST_GAME})
    return out


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
             'desc': '%s carried from %s into Halo 3: ODST, built on the Assault Rifle. '
                     'Bullet speed is measured against the Machine Gun rather than the '
                     'Assault Rifle, which is 1500 in Halo 4 and 100 here. It owns its '
                     'own first-person animations, so its reload can be retimed.'
                     % (t['ported'], t['source']),
             'balance': rows,
             'fp_animations': FP_ANIMATIONS,
             'anims': {'reload': RELOAD_MULT}}
    print('\nfields the cards cannot reach, measured from the donor tags:')
    rows.extend(measured_rows())
    print('\nderived totals (nothing else recomputes these in ODST):')
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
        cat.setdefault(DST_GAME, [])
        # Keep whatever this entry carries that the balance table does not produce --
        # the ammo-pickup choices are wired in separately, and regenerating the numbers
        # must not silently drop them (which is how Halo 1's went missing).
        for old in cat[DST_GAME]:
            if old.get('weapon') == entry['weapon']:
                for k in ('ammo',):
                    if old.get(k) and not entry.get(k):
                        entry[k] = old[k]
        cat[DST_GAME] = ([e for e in cat[DST_GAME] if e.get('weapon') != entry['weapon']]
                         + [entry])
        json.dump(cat, open(OUT, 'w', encoding='utf-8'), indent=1)
        print('\nwrote %s' % OUT)
    else:
        print('\n(dry run -- pass --write)')


if __name__ == '__main__':
    main()
