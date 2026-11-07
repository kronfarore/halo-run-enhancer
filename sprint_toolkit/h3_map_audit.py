r"""Audit the nine Halo 3 campaign maps for what the Run Enhancer relies on.

Three checks per map, all read-only:

  MARKERS      equipment placements named exactly `enhancer_marker1` / `enhancer_marker2`
               (player 1 / player 2 drop points). Any other placement name containing
               "enhancer" or "marker" is printed as a likely misspelling.
  DZ_ENHANCER  the scenario's designer zone `dz_enhancer` exists, and EVERY scenario
               zone set loads it: Zone Sets (scnr 0x58, elem 0x28) +0x10 is the loaded
               designer-zone mask, one bit per Designer Zones entry (scnr 0x6E4, 0xBC).
               Found 2026-11-06: on 020 the zone existed but no zone set loaded it, so
               its Gravity Hammer starting placement never appeared.
  START        every weapon, turret, equipment and grenade the enhancer can offer on
               Halo 3 (the union of halo.json's nine Halo 3 mission lists) is loadable from the level start: its
               tag is in the zone tag's GLOBAL set or in dz_enhancer (Required or
               Optional tag pool), with dz_enhancer loaded by all zone sets. The family's
               render model (`mode` tags in the weapon's folder) is checked the same way.

The tag-pool bits are a lead, not proof (h3_zone_pools.py docstring): sc150's shotgun
renders with its Required bit clear. The 020 hammer result matched the game, though.

    python h3_map_audit.py                 # the live maps (halo3\maps)
    python h3_map_audit.py --kit           # the kit's fresh builds (H3EK\maps)
    python h3_map_audit.py 020_base 050_floodvoi
    python h3_map_audit.py --json
"""
import argparse
import contextlib
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, TOOL)
sys.path.insert(0, HERE)
import halo_patch as HP              # noqa: E402
import h3_import_list as IL          # noqa: E402
import h3_zone_pools as Z            # noqa: E402

GAME = 'Halo 3'
LIVE = IL.MAPS
KIT = r'F:\SteamLibrary\steamapps\common\H3EK\maps'
LEVELS = IL.LEVELS
MARKERS = ('enhancer_marker1', 'enhancer_marker2')
DZ_NAME = 'dz_enhancer'
SCNR_DESIGNER_ZONES = (0x6E4, 0xBC)
SCNR_ZONE_SETS = (0x58, 0x28)
ZS_LOADED_DZ = 0x10
BS = chr(92)


def _sid(m, s):
    try:
        return m.resolve_stringid(s)
    except Exception:
        return None


def _block(m, base, off, es):
    n = max(0, m.i32(base + off))
    b = HP._block_base(m, base + off)
    return [b + i * es for i in range(n)] if b else []


def markers(m):
    """Named equipment placements: exact markers, near misses, and their state."""
    named = HP.reach_named_markers(m, GAME, prefix='') or {}
    scnr = HP._scnr_base(m)
    qoff, qes = HP._MAP_EQUIPMENT[GAME]['items']
    qbase = HP._block_base(m, scnr + qoff)
    out = {'found': {}, 'missing': [], 'suspect': []}
    for nm, pi in named.items():
        if nm in MARKERS:
            e = qbase + pi * qes
            out['found'][nm] = {
                'placement': pi,
                'pos': [round(v, 2) for v in struct.unpack_from('<fff', m.data, e + HP._EQ_POS)],
                'flags': struct.unpack_from('<I', m.data, e + HP._EQ_FLAGS)[0],
                'bsp_mask': struct.unpack_from('<I', m.data, e + 0x50)[0]}
        elif 'enhancer' in nm.lower() or 'marker' in nm.lower():
            out['suspect'].append(nm)
    out['missing'] = [k for k in MARKERS if k not in out['found']]
    return out


def dz_state(m):
    scnr = HP._scnr_base(m)
    names = [_sid(m, m.u32(e)) for e in _block(m, scnr, *SCNR_DESIGNER_ZONES)]
    idx = names.index(DZ_NAME) if DZ_NAME in names else None
    sets = [m.u32(e + ZS_LOADED_DZ) for e in _block(m, scnr, *SCNR_ZONE_SETS)]
    loaded = [i for i, mask in enumerate(sets) if idx is not None and mask >> idx & 1]
    return {'index': idx, 'zones': len(names), 'zone_sets': len(sets),
            'loaded_by': len(loaded),
            'not_loaded_in': [i for i in range(len(sets)) if i not in loaded]}


def _pools(m, zb):
    """{label: (req words, opt words)} for dz_enhancer and GLOBAL in the zone tag."""
    out = {}
    for label, e in Z.zonesets(m, zb):
        key = ('dz' if label.endswith(' ' + DZ_NAME) else
               'global' if label.startswith('GLOBAL') else None)
        if key and key not in out:
            out[key] = (Z._pool(m, e, Z.ZS_REQUIRED_TAG_POOL),
                        Z._pool(m, e, Z.ZS_OPTIONAL_TAG_POOL))
    return out


def _in(pools, key, row):
    p = pools.get(key)
    return bool(p) and (Z._has(p[0], row) or Z._has(p[1], row))


def start_items(m, cat, dz):
    zb = IL.zone_base(m)
    pools = _pools(m, zb) if zb else {}
    rows = {}
    for t in m.tags:
        if t.get('name'):
            rows.setdefault((t.get('class'), str(t['name']).lower()), t['index'])
    dz_live = dz['index'] is not None and not dz['not_loaded_in'] and dz['zone_sets'] > 0
    items = []
    lists = [('weapon', 'weap', cat['weapons']), ('turret', 'weap', cat['turrets']),
             ('equipment', 'eqip', cat['equipment']),
             ('grenade', 'eqip', {n: IL.GRENADE_EQIP.get(n) for n in cat['grenades']})]
    for kind, cls, d in lists:
        for name, path in sorted(d.items()):
            rec = {'kind': kind, 'name': name, 'tag': path}
            if path is None:
                rec['verdict'] = 'offered, but halo.json has no Halo 3 tag for it'
                items.append(rec)
                continue
            row = rows.get((cls, path.lower()))
            if row is None:
                rec['verdict'] = 'NOT IN MAP'
                items.append(rec)
                continue
            g, z = _in(pools, 'global', row), _in(pools, 'dz', row)
            folder = path.lower().rsplit(BS, 1)[0] + BS
            models = [r for (c, n), r in rows.items() if c == 'mode' and n.startswith(folder)]
            mg = any(_in(pools, 'global', r) for r in models)
            mz = any(_in(pools, 'dz', r) for r in models)
            if g or (z and dz_live):
                verdict = 'ok'
            elif z:
                verdict = 'dz_enhancer only, and it is not loaded everywhere'
            else:
                verdict = 'NOT IN GLOBAL OR dz_enhancer'
            if verdict == 'ok' and models and not (mg or (mz and dz_live)):
                verdict = 'tag ok, but its render model is in neither set'
            rec.update(global_=g, dz=z, verdict=verdict)
            items.append(rec)
    return items


def halo3_catalogue():
    """IL.catalogue() cut down to what Halo 3's mission lists offer, all nine together.

    The run carries weapons from level to level, so every level is checked for the whole
    union. catalogue() alone also returns Reach / Halo 4 weapons whose halo.json tag is a
    plain string (those resolve in every game -- [[halo-weap-tag-wrong-game]])."""
    cat = IL.catalogue()
    kinds = ('weapons', 'turrets', 'equipment', 'grenades')
    offered = set()
    for mis in cat['missions'].values():
        for k in kinds:
            offered |= {IL.ALIASES.get(n, n) for n in (mis.get(k) or [])}
    # Classified by the CATALOGUE, not by the list that offers it: 040 lists the
    # Missile Pod under `weapons`, the catalogue files it with the turrets.
    out = {k: {n: v for n, v in cat[k].items() if n in offered} for k in kinds}
    known = set().union(*(out[k] for k in kinds))
    for n in sorted(offered - known):
        out['weapons'][n] = None        # offered by a mission, no Halo 3 tag at all
    out['missions'] = cat['missions']
    return out


def audit(path):
    with contextlib.redirect_stdout(io.StringIO()):
        m = HP.open_map(path, GAME)
    cat = halo3_catalogue()
    dz = dz_state(m)
    return {'map': path, 'markers': markers(m), 'dz': dz,
            'items': start_items(m, cat, dz)}


def report(lvl, r):
    mk, dz, items = r['markers'], r['dz'], r['items']
    bad = [i for i in items if i['verdict'] != 'ok']
    ok_all = not mk['missing'] and not mk['suspect'] and dz['index'] is not None \
        and not dz['not_loaded_in'] and not bad
    print('%s  %s' % (lvl, 'ALL OK' if ok_all else 'PROBLEMS'))
    for nm, v in sorted(mk['found'].items()):
        print('   %-18s placement %d at %s, flags %#x, BSP mask %#x'
              % (nm, v['placement'], tuple(v['pos']), v['flags'], v['bsp_mask']))
    for nm in mk['missing']:
        print('   %-18s MISSING' % nm)
    if mk['suspect']:
        print('   misnamed?          %s' % ', '.join(sorted(mk['suspect'])))
    if dz['index'] is None:
        print('   dz_enhancer        MISSING (%d designer zones)' % dz['zones'])
    else:
        print('   dz_enhancer        zone %d, loaded by %d/%d zone sets%s'
              % (dz['index'], dz['loaded_by'], dz['zone_sets'],
                 '' if not dz['not_loaded_in'] else
                 ' -- NOT in %s' % dz['not_loaded_in']))
    n = {k: sum(1 for i in items if i['kind'] == k) for k in
         ('weapon', 'turret', 'equipment', 'grenade')}
    nb = {k: sum(1 for i in bad if i['kind'] == k) for k in n}
    print('   from the start     ' + ', '.join('%s %d/%d' % (k + 's', n[k] - nb[k], n[k])
                                               for k in n))
    for i in bad:
        print('      %-9s %-18s %s' % (i['kind'], i['name'], i['verdict']))
    return ok_all


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('levels', nargs='*')
    ap.add_argument('--kit', action='store_true', help="read the kit's builds (H3EK\\maps)")
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    root = KIT if a.kit else LIVE
    res, good = {}, 0
    for lvl in a.levels or LEVELS:
        p = os.path.join(root, lvl + '.map')
        if not os.path.exists(p):
            print('%s  no map at %s' % (lvl, p))
            continue
        res[lvl] = audit(p)
        if not a.json:
            good += report(lvl, res[lvl])
    if a.json:
        print(json.dumps(res, indent=1))
    else:
        print('\n%d/%d maps ALL OK (%s)' % (good, len(res), root))
    return 0 if good == len(res) else 1


if __name__ == '__main__':
    sys.exit(main())
