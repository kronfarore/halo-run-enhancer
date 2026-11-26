r"""Prepare the ODST KIT BUILDS and ship them as the enhancer's baselines.

prepare_map.prepare()'s one-time steps -- residency for every weapon and equipment piece
with geometry, the HUD repoint for weapons ODST never shipped a chud for, and a palette
slot for every weapon -- run on `H3ODSTEK\maps\<map>.map` and the result is written to
the baseline store (E:\HaloBaselines\halo3odst\maps) and its F: copy
(F:\HaloBaselines\halo3odst). The live map in halo3odst\maps is never opened or
written: the next patch writes it from the baseline. First used 2026-11-13 (from a
scratchpad), again 2026-11-26 after odst_dz_enhancer.py filled every level.

The prepared map is saved to a temp folder and checked (prepare_map.report +
equipment_report) BEFORE anything is copied, so a map that is not READY never replaces
a baseline. `--write` backs the current baselines up first (E:\HaloBackups).

    python odst_prepare_baselines.py --compare h100 sc100      old baseline vs kit build
    python odst_prepare_baselines.py --write h100 sc100 ...    prepare, back up, ship
    python odst_prepare_baselines.py --write --all
"""
import argparse
import contextlib
import datetime
import io
import os
import shutil
import sys

TK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TK)
sys.path.insert(0, os.path.dirname(TK))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import prepare_map as P                                    # noqa: E402

HP, Z, EK, V = P.HP, P.Z, P.EK, P.V
F_DIR = r'F:\HaloBaselines\halo3odst'
OUT = r'F:\HaloBaselines\_odst_prepared_tmp'
BACKUP_ROOT = r'E:\HaloBackups'
LEVELS = ('h100', 'sc100', 'sc110', 'sc120', 'sc130', 'sc140', 'sc150', 'l200', 'l300')


def kit(name):
    return os.path.join(EK.EK, 'maps', name + '.map')


def baseline(name):
    return V.baseline_for(P.GAME, os.path.join(EK.GAME, name + '.map'))


def f_copy(name):
    """The F: copy, matched case-insensitively (F: holds `L200.map`)."""
    want = os.path.basename(baseline(name)).lower()
    if os.path.isdir(F_DIR):
        for fn in os.listdir(F_DIR):
            if fn.lower() == want:
                return os.path.join(F_DIR, fn)
    return os.path.join(F_DIR, os.path.basename(baseline(name)))


def summary(path):
    with contextlib.redirect_stdout(io.StringIO()):
        m = HP.open_map(path, P.GAME)
    zb = Z._zone_tag(m)['base']
    ok, missing = P.present(m, zb)
    return m, zb, sorted(ok), sorted(missing)


def prepare(name):
    """prepare_map.prepare()'s steps on the kit build -> (temp path, READY?)."""
    m, zb, ok, missing = summary(kit(name))
    print('  kit build: %d weapons with geometry, %d without %s'
          % (len(ok), len(missing), missing))
    lay = HP._MAP_WEAPONS[P.GAME]
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
    owned = Z.chunks_by_tag(m, zb)
    eqip = []
    for t in m.tags:
        if t.get('class') != 'eqip' or not t.get('name'):
            continue
        base = str(t['name']).rsplit('\\', 1)[-1]
        stem = base[:-10] if base.endswith('_equipment') else base
        models = [x for x in m.tags if x['class'] == 'mode'
                  and stem.lower() in (x.get('name') or '').lower()]
        if any(owned.get(x['index']) for x in models):
            eqip.append(base)
    for e in sorted(set(eqip)):
        r = Z.load_always(m, zb, e, only_resolved=True, cls='eqip')
        added += r.get('tags_added', 0) if r.get('ok') else 0
    print('  residency: %d weapon(s), %d equipment, %d tag bit(s) added'
          % (len(wanted), len(set(eqip)), added))
    P.fix_huds(m, ok, None)
    P.make_placeable(m, ok)
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, name + '.map')
    m.save(out)
    m2, zb2, ok2, miss2 = summary(out)
    good = P.report(m2, zb2, ok2)
    eq_ok, _ = P.equipment_report(m2, zb2)
    good = good and eq_ok and not miss2
    print('  %s: %s' % (name, 'READY' if good else 'NEEDS ATTENTION'))
    return out, good


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--compare', action='store_true')
    g.add_argument('--write', action='store_true')
    ap.add_argument('maps', nargs='*')
    ap.add_argument('--all', action='store_true', help='all nine levels')
    a = ap.parse_args(argv)
    names = list(LEVELS) if a.all else a.maps
    if not names:
        ap.error('name at least one map, or pass --all')
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    bdir = os.path.join(BACKUP_ROOT, 'odst_baselines_before_%s' % stamp)
    results = {}
    for n in names:
        print('=== %s ===' % n)
        if a.compare:
            _, _, ok_old, miss_old = summary(baseline(n))
            _, _, ok_new, miss_new = summary(kit(n))
            print('  old baseline: %d with geometry; kit build: %d'
                  % (len(ok_old), len(ok_new)))
            print('  only in old:', sorted(set(ok_old) - set(ok_new)))
            print('  only in kit:', sorted(set(ok_new) - set(ok_old)))
            print('  missing geometry (old / kit):', miss_old, miss_new)
            results[n] = True
            continue
        out, good = prepare(n)
        results[n] = good
        if not good:
            print('  NOT written to the baselines (left at %s)' % out)
            continue
        dst, fdst = baseline(n), f_copy(n)
        for src, sub in ((dst, 'E'), (fdst, 'F')):
            if os.path.exists(src):
                os.makedirs(os.path.join(bdir, sub), exist_ok=True)
                shutil.copy2(src, os.path.join(bdir, sub, os.path.basename(src)))
        shutil.copy2(out, dst)
        print('  baseline ->', dst)
        os.makedirs(F_DIR, exist_ok=True)
        shutil.copy2(out, fdst)
        print('  F: copy  ->', fdst)
        os.remove(out)
    if a.write:
        print('\nold baselines backed up to %s' % bdir)
    print('summary: ' + ', '.join('%s %s' % (n, 'ready' if g else 'NEEDS ATTENTION')
                                  for n, g in results.items()))
    return 0 if all(results.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
