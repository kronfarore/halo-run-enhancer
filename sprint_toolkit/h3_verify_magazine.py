r"""Check every magazine field of the ported SAW, end to end.

For each field: what the Halo 4 SAW holds, what the donor Assault Rifle holds in each
game (which is the ratio), what the balance table says, and what the installed Halo 3 map
actually reads -- for the SAW and for the Assault Rifle, so a value that leaked between
them is visible.

    python h3_verify_magazine.py
"""
import contextlib, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join('C:' + os.sep, 'Program Files (x86)', 'Steam', 'steamapps', 'common',
                    'Halo The Master Chief Collection', 'tool')
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he      # noqa: E402
import halo_patch as hp         # noqa: E402

B = os.sep
FIELDS = ['Rounds Recharged', 'Rounds Total Initial', 'Rounds Inventory Maximum',
          'Rounds Total Maximum', 'Rounds Loaded Maximum', 'Rounds Reloaded']
# Halo 3 keeps the ceiling in Rounds Inventory Maximum -- the Magazine card's field is a
# per-game dict and Halo 3 inherits Halo 2's spelling. Rounds Total Maximum is that
# ceiling PLUS the loaded magazine (Assault Rifle: 352 + 32 = 384), so it has no ratio of
# its own and checking it against one would always look wrong.
DERIVED = {'Rounds Total Maximum': ('Rounds Inventory Maximum', 'Rounds Loaded Maximum')}
SAW_H3 = B.join(['objects', 'weapons', 'rifle', 'saw', 'saw'])
AR_H3 = B.join(['objects', 'weapons', 'rifle', 'assault_rifle', 'assault_rifle'])
AR_H4 = B.join(['objects', 'weapons', 'rifle', 'storm_assault_rifle', 'storm_assault_rifle'])
SAW_H4 = B.join(['objects', 'weapons', 'rifle', 'storm_lmg', 'storm_lmg'])


def read_game(game, folder, mission, tags):
    src = he.baseline_source(hp.default_map_path(he.mcc_root(), folder, mission), game)
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(src, game)
    reg = hp.PluginRegistry(he.CONFIG.get('assembly_plugins_dir'),
                            he.CONFIG.get('plugin_subdirs_by_game', {}).get(game, []))
    p = reg.get('weap')
    out = {}
    for label, tag in tags.items():
        vals = {}
        for f in FIELDS:
            try:
                vals[f] = m.read_first('weap', tag, f, p, 'Magazines')
            except Exception:
                vals[f] = None
        out[label] = vals
    del m
    return out


def main():
    he.load_settings()
    h4 = read_game('Halo 4', 'halo4', 'm10_crash', {'SAW (H4)': SAW_H4, 'AR (H4)': AR_H4})
    h3v = read_game('Halo 3', 'halo3', '010_jungle', {'AR (H3 vanilla)': AR_H3})

    live = os.path.join(he.mcc_root(), 'halo3', 'maps', '010_jungle.map')
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(live, 'Halo 3')
    reg = hp.PluginRegistry(he.CONFIG.get('assembly_plugins_dir'),
                            he.CONFIG.get('plugin_subdirs_by_game', {}).get('Halo 3', []))
    p = reg.get('weap')
    got = {}
    for label, tag in (('SAW (installed)', SAW_H3), ('AR (installed)', AR_H3)):
        got[label] = {f: m.read_first('weap', tag, f, p, 'Magazines') for f in FIELDS}

    cat = json.load(open(os.path.join(TOOL, 'weapon_ports_catalog.json'), encoding='utf-8'))
    rows = {r['field']: r for e in cat.get('Halo 3', []) for r in e['balance']
            if r.get('block') == 'Magazines'}

    def n(v):
        return '-' if v is None else ('%g' % v if isinstance(v, (int, float)) else str(v))

    print('%-22s %-9s %-9s %-9s %-11s %-9s %-9s %s'
          % ('field', 'SAW H4', 'AR H4', 'AR H3', 'ratio', 'expected', 'in map', 'AR now'))
    for f in FIELDS:
        saw4 = h4['SAW (H4)'][f]
        ar4 = h4['AR (H4)'][f]
        ar3 = h3v['AR (H3 vanilla)'][f]
        ratio = (ar3 / float(ar4)) if isinstance(ar3, (int, float)) and ar4 else None
        expect = (saw4 * ratio) if (ratio is not None and isinstance(saw4, (int, float))) else None
        row = rows.get(f)
        got_saw, got_ar = got['SAW (installed)'][f], got['AR (installed)'][f]
        if f in DERIVED:
            parts = [got['SAW (installed)'][x] for x in DERIVED[f]]
            expect = sum(parts) if all(isinstance(v, (int, float)) for v in parts) else None
            ratio = None
        flag = ''
        if f in DERIVED:
            flag = '   derived: %s' % ' + '.join(DERIVED[f])
        elif row is None:
            flag = '   NO BALANCE ROW -- keeps the tag value'
        elif expect is not None and isinstance(got_saw, (int, float)) \
                and abs(round(expect) - got_saw) > 0.51:
            flag = '   <== MISMATCH'
        if isinstance(got_ar, (int, float)) and isinstance(ar3, (int, float)) and got_ar != ar3:
            flag += '   AR CHANGED (was %g)' % ar3
        print('%-22s %-9s %-9s %-9s %-11s %-9s %-9s %s%s'
              % (f, n(saw4), n(ar4), n(ar3), ('x%.4g' % ratio) if ratio else '-',
                 n(round(expect, 2) if expect is not None else None),
                 n(got_saw), n(got_ar), flag))

    print('\nwhat the Magazine card targets in each game (why a row can be missing):')
    with contextlib.redirect_stdout(io.StringIO()):
        db = he.ModifierDatabase()
    card = db.data['Player Modifiers']['Specific Weapon Modifier']['Assault Rifle'].get('Magazine')
    for t in (card or {}).get('targets', []):
        fld = t.get('field')
        print('   %-26s block %s' % (fld if isinstance(fld, str) else fld, t.get('block')))


if __name__ == '__main__':
    main()
