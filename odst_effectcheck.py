r"""Which effects, now that ODST inherits Halo 3's, would target a field ODST removed?

ODST reuses Halo 3's effects via CONFIG['game_inherits'], which is safe only where
the fields still exist. ODST dropped some -- Cover Properties>Cover Chance,
weap Magazines>Reload Time, the 1st/2nd/3rd Hit Melee Damage set, most of eqip's
Halo 3 equipment blocks -- and an inherited effect aimed at one of those would fail
at patch time rather than at review time.

This resolves every effect the way the patcher will and reports the ones that break,
so they can be excluded explicitly in halo.json.

    python odst_effectcheck.py            # only the failures
    python odst_effectcheck.py --all      # every effect and its verdict
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PLUGINS = (r"C:\Program Files (x86)\Steam\steamapps\common\HCEEK"
           r"\Assembly-1-2023-11-29-1702446457\Plugins")
SUBDIRS_BY_GAME = {
    'Halo 3: ODST': ['ODSTMCC', 'ODST'],
    'Halo 3': ['Halo3MCC', 'Halo3'],
    'Halo 2': ['Halo2MCC', 'Halo2'],
}


def _resolve(value, game, order):
    """Mirror of halo_enhancer.resolve_gamed: exact match, else nearest EARLIER game."""
    if not isinstance(value, dict):
        return value
    if game in value:
        return value[game]
    if 'default' in value:
        return value['default']
    if game in order:
        for g in reversed(order[:order.index(game)]):
            if g in value:
                return value[g]
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--game', default='Halo 3: ODST')
    a = ap.parse_args(argv)
    GAME = a.game
    SUBDIRS = SUBDIRS_BY_GAME[GAME]

    import halo_map as hm
    from halo_patch import PluginRegistry, apply_difficulty

    data = json.load(open('halo.json', encoding='utf-8'))
    order = list(data['Missions'])
    reg = PluginRegistry(PLUGINS, SUBDIRS)

    sections = [('General modifiers', {'(general)': data['Enemy modifiers']['General modifiers']}),
                ('Specific Enemy modifier', data['Enemy modifiers']['Specific Enemy modifier']),
                ('Boss enemy modifier', data['Enemy modifiers']['Boss enemy modifier'])]

    ok = skipped = broken = 0
    problems = []
    for sec, group in sections:
        for who, effects in group.items():
            for name, eff in effects.items():
                games = eff.get('game')
                games = [games] if isinstance(games, str) else (games or [])
                # what the new inheritance makes reachable in ODST
                if games and GAME not in games and 'Halo 3' not in games:
                    skipped += 1
                    continue
                tag = _resolve(eff.get('tag'), GAME, order)
                if not tag:
                    skipped += 1
                    continue
                cls = tag.split(' ', 1)[0]
                plugin = reg.get(cls)
                if plugin is None:
                    problems.append((sec, who, name, cls, ['<no ODST plugin for %s>' % cls]))
                    broken += 1
                    continue
                targets = _resolve(eff.get('targets'), GAME, order) or []
                missing = []
                for t in targets:
                    if not isinstance(t, dict):
                        continue
                    # Target-level `games` is matched EXACTLY, with no inheritance
                    # (halo_enhancer.py:935) -- unlike the mod-level `game` above.
                    # Emulating inheritance here made correctly-excluded targets
                    # still look reachable.
                    tg = t.get('games')
                    if tg and GAME not in tg:
                        continue
                    fld = _resolve(t.get('field'), GAME, order)
                    if not fld:
                        continue
                    # `block` is per-game too, not just `field` and `tag`
                    blk = _resolve(t.get('block'), GAME, order)
                    # A difficulty target's real field name is decorated at patch
                    # time ("Heroic Enemy Damage", "Accuracy Bounds (Legendary)"...).
                    # Checking the bare name reports every one of them as missing --
                    # in Halo 3 too, which is how this checker's first version was
                    # caught being wrong rather than ODST being broken. Any tier
                    # resolving is enough; tiers that do not exist are skipped by
                    # the patcher by design.
                    tiers = ['Normal', 'Heroic', 'Legendary', 'Easy', 'Impossible']
                    if any(t.get(k) for k in ('difficulty', 'diff_suffix',
                                              'diff_prefix', 'diff_prefix_nl')):
                        if any(plugin.find(apply_difficulty(fld, t, d), blk)
                               for d in tiers):
                            continue
                        missing.append('%s / %s (all difficulty tiers)' % (blk or '-', fld))
                        continue
                    if plugin.find(fld, blk) is None:
                        missing.append('%s / %s' % (blk or '-', fld))
                if missing:
                    problems.append((sec, who, name, cls, missing))
                    broken += 1
                else:
                    ok += 1
                    if a.all:
                        print('  ok      %-22s %-26s %s' % (who, name, cls))

    print('\n%d effect(s) resolve cleanly in ODST, %d would hit a missing field, '
          '%d not applicable' % (ok, broken, skipped))
    if problems:
        print('\nEFFECTS THAT NEED AN EXPLICIT ODST EXCLUSION:')
        for sec, who, name, cls, missing in problems:
            print('  %-22s %-26s [%s]' % (who, name, cls))
            for m in missing:
                print('        missing: %s' % m)
    return 0


if __name__ == '__main__':
    sys.exit(main())
