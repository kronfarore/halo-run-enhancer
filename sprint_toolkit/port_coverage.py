r"""Does a port carry every field it should, in the game it landed in?

Two questions, per game:

  ORIGINAL   with the balance switched off the port is supposed to play like the weapon
             it came from, which means its tags must hold the SOURCE game's numbers. The
             Halo 1 port had them written in at build time; a port built by cloning a
             donor tag starts out holding the DONOR's numbers instead, so every field
             whose original differs from what the map currently reads is a field the
             player would never feel.
  BALANCED   what the patcher writes on top.

Anything the cards cannot reach in the target game shows up as a gap rather than
silently keeping the donor's value.

    python port_coverage.py "Halo 3" [--map 010_jungle]
"""
import argparse, contextlib, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join('C:' + os.sep, 'Program Files (x86)', 'Steam', 'steamapps', 'common',
                    'Halo The Master Chief Collection', 'tool')
sys.path.insert(0, TOOL)
os.chdir(TOOL)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_enhancer as he      # noqa: E402
import halo_patch as hp         # noqa: E402

B = os.sep
MAPS = {'Halo 1': ('halo1', 'a10'), 'Halo 3': ('halo3', '010_jungle')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('game', nargs='?', default='Halo 3')
    ap.add_argument('--map')
    ap.add_argument('--weapon', default='SAW')
    ap.add_argument('--built', action='store_true',
                    help='read the map straight out of the Editing Kit, before the '
                         'patcher has touched it -- that is what the TAGS hold')
    a = ap.parse_args()
    he.load_settings()
    folder, default_map = MAPS[a.game]
    mission = a.map or default_map
    live = os.path.join(he.mcc_root(), folder, 'maps', mission + '.map')
    if a.built:
        ek = {'Halo 3': 'H3EK', 'Halo 1': 'HCEEK'}[a.game]
        live = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', ek,
                            'maps', mission + '.map')
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(live, a.game)
    reg = hp.PluginRegistry(he.CONFIG.get('assembly_plugins_dir'),
                            he.CONFIG.get('plugin_subdirs_by_game', {}).get(a.game, []))
    cat = json.load(open(os.path.join(TOOL, 'weapon_ports_catalog.json'), encoding='utf-8'))
    entry = next((e for e in cat.get(a.game, []) if e.get('weapon') == a.weapon), None)
    if entry is None:
        raise SystemExit('no %s port for %s' % (a.weapon, a.game))

    rows = entry['balance']
    print('%s / %s: %d balance row(s)\n' % (a.game, a.weapon, len(rows)))
    print('%-26s %-10s %-10s %-10s %s'
          % ('field', 'in map', 'original', 'balanced', 'note'))
    missing_original = []
    for r in sorted(rows, key=lambda r: (r.get('card') or '', r['field'])):
        plugin = reg.get(r['class'])
        try:
            cur = m.read_first(r['class'], r['tag'], r['field'], plugin, r.get('block'),
                               nth=r.get('nth', 0) or 0)
        except Exception:
            cur = None
        orig, bal = r.get('original'), r.get('value')
        fmt = lambda v: '-' if v is None else ('%.4g' % v if isinstance(v, float) else str(v))
        note = ''
        if orig is None:
            note = 'no original recorded'
        elif isinstance(cur, (int, float)) and isinstance(orig, (int, float)) \
                and abs(cur - orig) > max(1e-6, abs(orig) * 1e-4):
            note = '<== tag does NOT hold the original'
            missing_original.append((r['field'], cur, orig))
        print('%-26s %-10s %-10s %-10s %s'
              % (r['field'][:26], fmt(cur), fmt(orig), fmt(bal), note))
    print('\n%d field(s) whose ORIGINAL is not in the tags -- with the balance off, the '
          'port plays like the donor there' % len(missing_original))


if __name__ == '__main__':
    main()
