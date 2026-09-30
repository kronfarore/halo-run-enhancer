"""Field the two SAW velocity candidates in Halo 3, one per map, without waiting for the
model port.

The question the two tables disagree on is how fast the ported SAW's bullets should fly:
16 measured against the Assault Rifle, or 75 against the Machine Gun. That is a balance
question, and it can be answered with the numbers alone -- so this writes the SAW's whole
Halo 3 balance onto the Assault Rifle's own tags, one variant per map, and the Assault
Rifle becomes the SAW for the length of the test.

    python saw_h3_bench.py --status
    python saw_h3_bench.py --apply          # 010_jungle = 16 (AR), 020_base = 75 (MG)
    python saw_h3_bench.py --restore

Restoring copies the pristine baseline back, so nothing here is permanent.
"""
import argparse, contextlib, io, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join('C:' + os.sep, 'Program Files (x86)', 'Steam', 'steamapps', 'common',
                    'Halo The Master Chief Collection', 'tool')
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he            # noqa: E402
import halo_patch as hp               # noqa: E402

B = os.sep
GAME = 'Halo 3'
# map -> (which table, a label for the log)
BASE = 'balance_SAW_Halo4_to_Halo3.json'          # destinations come from this one
PLAN = {'010_jungle': (None, 'Assault Rifle anchored (16)'),
        '020_base': ('balance_SAW_Halo4_to_Halo3_mgvel.json', 'Machine Gun anchored (75)')}
VELOCITY = ('Initial Velocity', 'Final Velocity', 'Minimum Velocity')


def rows_for(variant):
    """The table to write, always aimed at the Assault Rifle's own tags.

    A field measured against another weapon (velocity against the Machine Gun) carries
    THAT weapon's tag as its destination, because the destination is wherever the donor's
    card pointed. For a real port the catalog maps every donor tag onto the port's own;
    here the port IS the Assault Rifle, so the base table supplies the destinations and a
    variant only supplies values."""
    base = [r for r in json.load(open(os.path.join(HERE, BASE)))['rows']
            if r.get('dst_field') and r.get('balanced') is not None]
    if not variant:
        return base
    alt = {(r['card'], r['dst_field']): r.get('balanced')
           for r in json.load(open(os.path.join(HERE, variant)))['rows']
           if r.get('dst_field')}
    out = []
    for r in base:
        r = dict(r)
        key = (r['card'], r['dst_field'])
        if r['dst_field'] in VELOCITY and key in alt and alt[key] is not None:
            r['balanced'] = alt[key]
        out.append(r)
    return out
SHOW = [('proj', 'bullet', 'Initial Velocity', None),
        ('proj', 'bullet', 'Final Velocity', None),
        ('proj', 'bullet', 'Maximum Range', None),
        ('weap', '', 'Rounds Loaded Maximum', 'Magazines'),
        ('weap', '', 'Rounds Per Second', 'Barrels'),
        ('weap', '', 'Error Angle', 'Barrels'),
        ('jpt!', 'bullet', 'Damage Upper Bound', None)]


def live_path(mission):
    return os.path.join(he.mcc_root(), 'halo3', 'maps', mission + '.map')


def baseline_path(mission):
    return he.baseline_source(hp.default_map_path(he.mcc_root(), 'halo3', mission), GAME)


def registry():
    return hp.PluginRegistry(he.CONFIG.get('assembly_plugins_dir'),
                             he.CONFIG.get('plugin_subdirs_by_game', {}).get(GAME, []))


def snapshot(m, reg, rows):
    """A few readings per map, taken through the same tags the table writes."""
    out = []
    for cls, must, field, block in SHOW:
        tag = next((r['dst_tag'] for r in rows
                    if r.get('dst_class') == cls and must in (r.get('dst_tag') or '')), None)
        if not tag:
            continue
        try:
            nth = next((r.get('dst_nth', 0) or 0) for r in rows
                       if r.get('dst_field') == field) if any(
                           r.get('dst_field') == field for r in rows) else 0
            v = m.read_first(cls, tag, field, reg.get(cls), block, nth=nth)
        except Exception as e:
            v = 'ERR %s' % e
        out.append((field, v))
    return out


def apply_one(mission, table, label, write=True):
    rows = rows_for(table)
    live, base = live_path(mission), baseline_path(mission)
    if write:
        shutil.copy2(base, live)          # always start from pristine
    reg = registry()
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(live, GAME)
    before = snapshot(m, reg, rows)
    wrote = missing = 0
    reasons = {}
    for r in rows:
        plugin = reg.get(r['dst_class'])
        if plugin is None:
            missing += 1
            continue
        res = m.apply_field(r['dst_class'], r['dst_tag'], r['dst_field'], 'set',
                            r['balanced'], plugin, r.get('dst_block'),
                            r.get('dst_index', 0) or 0, nth=r.get('dst_nth', 0) or 0)
        for one in res:
            if one.get('ok'):
                wrote += 1
            else:
                missing += 1
                reasons[str(one.get('reason'))] = reasons.get(str(one.get('reason')), 0) + 1
    after = snapshot(m, reg, rows)
    print('== %s -- %s' % (mission, label))
    print('   %d field(s) written, %d not applied %s'
          % (wrote, missing, ('(%s)' % ', '.join('%d %s' % (n, r) for r, n in reasons.items()))
             if reasons else ''))
    for (f, a), (_f, b) in zip(before, after):
        fmt = lambda v: ('%.4g' % v) if isinstance(v, (int, float)) else str(v)
        print('   %-24s %-12s -> %s' % (f, fmt(a), fmt(b)))
    if write:
        m.save(live)
        print('   saved %s' % live)
    del m


def status():
    reg = registry()
    for mission, (table, label) in PLAN.items():
        rows = rows_for(table)
        live = live_path(mission)
        if not os.path.exists(live):
            print('%-12s MISSING' % mission)
            continue
        with contextlib.redirect_stdout(io.StringIO()):
            m = hp.open_map(live, GAME)
        vals = dict(snapshot(m, reg, rows))
        vel = vals.get('Initial Velocity')
        print('%-12s %-32s velocity now %s' % (mission, label, vel))
        del m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--restore', action='store_true')
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    he.load_settings()
    if a.restore:
        for mission in PLAN:
            shutil.copy2(baseline_path(mission), live_path(mission))
            print('restored %s' % mission)
        return
    if a.status:
        status()
        return
    for mission, (table, label) in PLAN.items():
        apply_one(mission, table, label, write=not a.dry_run)


if __name__ == '__main__':
    main()
