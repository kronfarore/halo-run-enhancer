r"""Prepare an ODST map for the enhancer: rebuild it, then bake in everything the
restored weapons need. One command per level.

WHAT THIS BAKES, AND WHY IT IS ONE-TIME
`apply_run` patches FROM `<map>.bak` and saves the whole buffer, so anything written
into the baseline survives every future patch -- verified by round-tripping a prepared
map through the same open/save cycle. So none of this belongs in the patcher:

  1. rebuild with the Editing Kit      (brings the tags AND their resources in)
  2. residency for every weapon        (object_new silently refuses a tag whose bit is
                                        clear in the zone tag's Required Tag Pool)
  3. HUD repoint for weapons whose     (ODST never shipped ui\chud\magnum or \smg, so
     chud ODST never shipped            they come back with a NULL HUD Interface)
  4. optional palette slots            (placements index the palette; grants do not)

WHAT YOU MUST DO FIRST, ONCE PER LEVEL, IN GUERILLA
Open `tags\levels\atlas\<map>\<map>.scenario` and give each cut weapon a Player
Starting Profile whose Primary Weapon is that weapon. A placeholder row the level never
reads is fine, and adding new rows is fine. Without that, `tool` pulls the weapon's tags
in but NOT its geometry, and the map black-screens when the tag is marked resident --
which this script checks for and refuses to ship.

    python prepare_map.py sc150
    python prepare_map.py --all
    python prepare_map.py sc150 --verify-only
    python prepare_map.py sc150 --placeable battle_rifle

MCC MUST BE CLOSED: it holds the map files open and every write fails.
"""
import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import halo_patch as HP                                          # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h3_zone_pools as Z                                        # noqa: E402
import h3_raw_residency as R                                     # noqa: E402
import odst_ek_build as EK                                       # noqa: E402
import map_vault as V                                            # noqa: E402

GAME = 'Halo 3: ODST'
WEAP_HUD = 0x418                    # weap "HUD Interface" tagRef; datum at +0xC

# Weapons ODST cut that a scenario edit can bring back. Only the ones actually present
# in the built map are acted on, so an unedited level simply reports them as absent.
RESTORABLE = ('battle_rifle', 'plasma_rifle', 'energy_blade', 'magnum',
              'sniper_rifle', 'smg')
# ODST ships no chud for these, so they return from Halo 3 with a NULL HUD Interface
# and no ammo counter or reticle. Nearest sibling that ODST does ship.
HUD_FALLBACK = {'magnum': 'automag', 'smg': 'smg_silenced'}


def _weap(m, base):
    """The weap tag whose filename is exactly `base`."""
    return next((t for t in m.tags if t.get('class') == 'weap' and t.get('name')
                 and str(t['name']).rsplit('\\', 1)[-1].lower() == base.lower()), None)


def geometry(m, zone_base, base):
    """(mode chunks, jmad chunks) owned by this weapon's family.

    A weapon whose model and animation own no chunks has no geometry in the map: the
    scenario references it but `tool` never gathered it. Marking such a tag resident is
    what black-screens the game, so this is the gate everything else hangs off.
    """
    owned = Z.chunks_by_tag(m, zone_base)
    mode = jmad = 0
    # Match a whole path segment, not a substring: `smg` must not sweep in
    # `smg_silenced`, which is a different weapon that is always present.
    want = {base.lower(), 'fp_' + base.lower(), 'lod_' + base.lower()}
    for t in m.tags:
        nm = (t.get('name') or '').lower()
        if not (want & set(nm.split('\\'))):
            continue
        n = len(owned.get(t['index'], []))
        if t['class'] == 'mode':
            mode += n
        elif t['class'] == 'jmad':
            jmad += n
    return mode, jmad


def present(m, zone_base):
    """Restorable weapons that are in this map WITH geometry, and ones that are not."""
    ok, missing, absent = [], [], []
    for w in RESTORABLE:
        if not _weap(m, w):
            absent.append(w)
            continue
        mode, jmad = geometry(m, zone_base, w)
        (ok if (mode and jmad) else missing).append(w)
    return ok, missing, absent


def fix_huds(m, weapons):
    """Point a NULL HUD Interface at the nearest sibling ODST does ship."""
    done = []
    for w in weapons:
        wt = _weap(m, w)
        chud = HUD_FALLBACK.get(w)
        if not wt or not chud:
            continue
        if m.u32(wt['base'] + WEAP_HUD + 0xC) != 0xFFFFFFFF:
            continue                                   # already has one
        ct = next((t for t in m.tags if t.get('class') == 'chdt' and t.get('name')
                   and str(t['name']).rsplit('\\', 1)[-1].lower() == chud), None)
        if not ct:
            print('    !! no ui\\chud\\%s in this map; %s keeps a null HUD' % (chud, w))
            continue
        datum = HP._h3_tag_datum(m, 'chdt', str(ct['name']))
        struct.pack_into('<I', m.data, wt['base'] + WEAP_HUD + 0xC, datum)
        print('    HUD  %-14s NULL -> ui\\chud\\%s' % (w, chud))
        done.append(w)
    return done


def make_placeable(m, weapons):
    """Point unused Weapon Palette slots at weapons that are not in the palette.

    Placements index the palette, so a weapon absent from it cannot be placed even
    though a starting profile can still grant it. `tool` prunes palette entries no
    placement references, which is why a restored weapon is missing from it after a
    rebuild. Overwriting a slot the level never places costs one tagRef and no block
    growth.
    """
    lay = HP._MAP_WEAPONS[GAME]
    scnr = HP._scnr_base(m)
    poff, pes = lay['palette']
    pc, pbase = max(0, m.i32(scnr + poff)), HP._block_base(m, scnr + poff)
    names = [str(HP._tag_name_by_id(m, m.u32(pbase + i * pes + 0xC)) or '')
             .rsplit('\\', 1)[-1].lower() for i in range(pc)]
    woff, wes = lay['weapons']
    used = set()
    wn, wbase = m.i32(scnr + woff), HP._block_base(m, scnr + woff)
    for i in range(max(0, wn)):
        used.add(struct.unpack_from('<h', m.data, wbase + i * wes)[0])
    spare = [i for i in range(pc) if i not in used]
    done = []
    for w in weapons:
        if w.lower() in names:
            print('    palette %-14s already present' % w)
            continue
        if not spare:
            print('    !! no unused palette slot left for %s' % w)
            continue
        wt = _weap(m, w)
        if not wt:
            continue
        i = spare.pop(0)
        datum = HP._h3_tag_datum(m, 'weap', str(wt['name']))
        struct.pack_into('<I', m.data, pbase + i * pes + 0xC, datum)
        print('    palette[%d] %s -> %s' % (i, names[i] or '(empty)', w))
        done.append(w)
    return done


def report(m, zone_base, weapons):
    """The table to read before shipping a map."""
    g = [e for lab, e in Z.zonesets(m, zone_base) if lab.startswith('GLOBAL')][0]
    pool = Z._pool(m, g, Z.ZS_REQUIRED_TAG_POOL)
    lay = HP._MAP_WEAPONS[GAME]
    scnr = HP._scnr_base(m)
    poff, pes = lay['palette']
    pc, pbase = max(0, m.i32(scnr + poff)), HP._block_base(m, scnr + poff)
    pal = {str(HP._tag_name_by_id(m, m.u32(pbase + i * pes + 0xC)) or '')
           .rsplit('\\', 1)[-1].lower() for i in range(pc)}
    print('    %-14s %-9s %-10s %-6s %s' % ('weapon', 'geometry', 'resident', 'HUD', 'palette'))
    allgood = True
    for w in weapons:
        wt = _weap(m, w)
        if not wt:
            print('    %-14s ABSENT' % w)
            allgood = False
            continue
        mode, jmad = geometry(m, zone_base, w)
        res = Z._has(pool, wt['index'])
        hud = m.u32(wt['base'] + WEAP_HUD + 0xC) != 0xFFFFFFFF
        good = bool(mode and jmad and res and hud)
        allgood &= good
        print('    %-14s %-9s %-10s %-6s %s   %s'
              % (w, 'm%d/a%d' % (mode, jmad), 'yes' if res else 'NO',
                 'ok' if hud else 'NULL', 'yes' if w.lower() in pal else 'no',
                 '' if good else '<-- check'))
    return allgood


def prepare(name, do_build=True, placeable=(), verify_only=False):
    path = os.path.join(EK.GAME, name + '.map')
    if not verify_only:
        if do_build:
            print('  building %s (this takes ~4 minutes and is quiet for long '
                  'stretches)' % name)
            if not EK.build(name):
                print('  !! build failed; leaving %s alone' % name)
                return False
        EK.install(name)                       # also repoints .bak and prunes copies

    m = HP.open_map(path, GAME)
    zb = Z._zone_tag(m)['base']
    ok, missing, absent = present(m, zb)
    print('  restorable weapons: %d with geometry, %d without, %d not in this map'
          % (len(ok), len(missing), len(absent)))
    for w in missing:
        print('    !! %s has NO geometry -- its scenario profile is missing, so it '
              'would black-screen if marked resident' % w)
    if verify_only:
        report(m, zb, ok + missing)
        return not missing

    # Residency: every palette weapon, plus the restored ones (which are not in the
    # palette). --only-resolved is what keeps a tag with a dead chunk out of the pool.
    lay = HP._MAP_WEAPONS[GAME]
    scnr = HP._scnr_base(m)
    poff, pes = lay['palette']
    pc, pbase = max(0, m.i32(scnr + poff)), HP._block_base(m, scnr + poff)
    wanted = [str(HP._tag_name_by_id(m, m.u32(pbase + i * pes + 0xC)) or '')
              .rsplit('\\', 1)[-1] for i in range(pc)]
    wanted = [w for w in wanted if w] + list(ok)
    added = 0
    for w in wanted:
        r = Z.load_always(m, zb, w, only_resolved=True)
        added += r.get('tags_added', 0) if r.get('ok') else 0
    print('    residency: %d weapon(s), %d tag bit(s) added' % (len(wanted), added))

    fix_huds(m, ok)
    if placeable:
        make_placeable(m, [w for w in placeable if w in ok])

    m.save(path)
    # .bak must carry the same preparation, or the first patch rebuilds without it.
    import shutil
    shutil.copy2(path, path + '.bak')
    print('    saved, and .bak updated to match')

    m2 = HP.open_map(path, GAME)
    good = report(m2, Z._zone_tag(m2)['base'], ok)
    print('  %s: %s' % (name, 'READY' if good and not missing else 'NEEDS ATTENTION'))
    return good and not missing


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('maps', nargs='*', help='map basenames, e.g. sc150')
    ap.add_argument('--all', action='store_true', help='every ODST level in halo.json')
    ap.add_argument('--skip-build', action='store_true',
                    help='the map is already built and installed')
    ap.add_argument('--verify-only', action='store_true', help='report, change nothing')
    ap.add_argument('--placeable', help='comma list: also give these a palette slot, '
                                        'so they can be placed as well as granted')
    a = ap.parse_args(argv)
    names = V.maps_for(GAME) if a.all else a.maps
    if not names:
        ap.error('name at least one map, or pass --all')
    placeable = [w.strip() for w in a.placeable.split(',')] if a.placeable else []
    results = {}
    for n in names:
        print('\n=== %s ===' % n)
        try:
            results[n] = prepare(n, not a.skip_build, placeable, a.verify_only)
        except Exception as e:
            print('  !! %s' % e)
            results[n] = False
    print('\nsummary')
    for n, good in results.items():
        print('  %-8s %s' % (n, 'ready' if good else 'needs attention'))
    return 0 if all(results.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
