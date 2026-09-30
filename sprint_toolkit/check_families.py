"""Check port_families.json against the card database: every named weapon must have
cards AND actually appear in that game's missions."""
import contextlib, io, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import balance_compare as bc  # noqa: sets up the tool path
import halo_enhancer as he

GAMES = ['Halo 1', 'Halo 2', 'Halo 3', 'Halo 3: ODST', 'Halo Reach', 'Halo 4']


def main():
    he.load_settings()
    with contextlib.redirect_stdout(io.StringIO()):
        db = he.ModifierDatabase()
    sw = db.data['Player Modifiers']['Specific Weapon Modifier']
    miss = db.data['Missions']
    cfg = json.load(open(os.path.join(HERE, 'port_families.json'), encoding='utf-8'))
    bad = []
    for fam, table in cfg['families'].items():
        print(fam)
        for g in GAMES:
            w = table.get(g)
            if w is None:
                print('   %-14s (none)' % g)
                continue
            has_cards = w in sw
            in_missions = any(w in (v.get('weapons') or []) for v in (miss.get(g) or {}).values())
            # Only missing CARDS is fatal: a donor is read from its card targets. Not
            # being in any mission list just means players do not find it there, which
            # does not stop it being the yardstick for that game.
            flag = '' if has_cards else '   <-- no cards, cannot be a donor'
            if not has_cards:
                bad.append((fam, g, w))
            elif not in_missions:
                flag = '   (not in that game\'s mission lists)'
            print('   %-14s %-18s%s' % (g, w, flag))
    print('\n%d entry(s) to fix' % len(bad))
    if bad:
        # what names DO exist, to pick from
        print('weapons with cards:', ', '.join(sorted(sw)))


if __name__ == '__main__':
    main()
