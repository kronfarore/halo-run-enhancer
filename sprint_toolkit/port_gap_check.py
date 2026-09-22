r"""For every field a port could NOT carry into a game, does that field even exist there?

A gap is only acceptable when the target game has no such field. If the field exists and
the port simply missed it -- because the donor's card does not target it in that game --
then the port is quietly leaving the donor's number in place, which is the bug that hid
Rounds Total Maximum in Halo 3 until it was measured.

Each gap comes out as one of:
  ABSENT      no such field in that game's plugin, nothing to carry
  FIXABLE     the field is there; measure it from the donor tags and add a row
  UNKNOWN     the plugin has it but under a class this table did not record

    python port_gap_check.py [table.json ...]
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

DEFAULT = ['balance_SAW_Halo4_to_Halo1.json', 'balance_SAW_Halo4_to_Halo3_mgvel.json']
CLASSES = ('weap', 'proj', 'jpt!')


def main():
    he.load_settings()
    for table in (sys.argv[1:] or DEFAULT):
        path = os.path.join(HERE, table)
        if not os.path.exists(path):
            continue
        d = json.load(open(path, encoding='utf-8'))
        game = d['target']
        reg = hp.PluginRegistry(he.CONFIG.get('assembly_plugins_dir'),
                                he.CONFIG.get('plugin_subdirs_by_game', {}).get(game, []))
        gaps = [r for r in d['rows'] if not r.get('dst_field')]
        print('== %s: %d gap(s)' % (game, len(gaps)))
        counts = {}
        for r in gaps:
            field = r.get('field')
            where = []
            for cls in CLASSES:
                p = reg.get(cls)
                if p is None:
                    continue
                for block in (None, 'Triggers', 'Barrels', 'Magazines'):
                    if p.find(field, block) is not None:
                        where.append('%s/%s' % (cls, block or '-'))
                        break
            verdict = 'ABSENT' if not where else 'FIXABLE'
            counts[verdict] = counts.get(verdict, 0) + 1
            print('   %-9s %-32s %-40s %s'
                  % (verdict, (field or '')[:32], (r.get('note') or '')[:40],
                     ','.join(where[:2])))
        print('   -> %s\n' % ', '.join('%d %s' % (n, k) for k, n in sorted(counts.items())))


if __name__ == '__main__':
    main()
