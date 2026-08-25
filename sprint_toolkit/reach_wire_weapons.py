r"""reach_wire_weapons.py -- give Reach's weapons their halo.json cards.

161 of the 164 cards belonging to weapons Reach actually fields stop at Halo 3 or
ODST: no "Halo Reach" in the card's `game` list or `tag` dict. Because resolve_gamed
falls back to the nearest EARLIER game, such a card is not merely absent -- it can
resolve a Halo 3 tag path that Reach happens to share and then fail on a field Reach
moved or dropped, which is the silent no-op this project keeps digging out.

So the wiring is checked, not assumed. For each card this resolves the tag it would
inherit, then asks two questions against the real Reach maps and the Reach plugin:

    does the TAG exist in Reach?      (union of every campaign map's tag names)
    do the FIELDS resolve on it?      (plugin.find, honouring block / nth /
                                       diff_prefix_nl, exactly as the patcher does)

Only a card that passes both gets a Reach entry. Everything else is reported with the
reason, because those are the cards that need real work -- a moved block (melee went
into Melee Damage Parameters), a renamed field, or a mechanic Reach dropped.

    python sprint_toolkit/reach_wire_weapons.py              # report only
    python sprint_toolkit/reach_wire_weapons.py --apply
    python sprint_toolkit/reach_wire_weapons.py --show-ok
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import assembly_plugins                               # noqa: E402
import halo_patch                                     # noqa: E402
import reach_census as rc                             # noqa: E402

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HALO_JSON = os.path.join(TOOL, 'halo.json')
PLUGINS = assembly_plugins.plugins_dir()
SEP = chr(92)
GAME = 'Halo Reach'
SUBDIRS = ['ReachMCC', 'Reach']
# Difficulty prefixes a diff_prefix_nl target can take, so the check matches what the
# patcher will actually ask the plugin for.
DIFF_PREFIXES = ('Normal ', 'Legendary ')


def reach_tags():
    """{(class, lowercased name)} across every Reach campaign map."""
    have = set()
    for mid in rc.CAMPAIGN:
        m = halo_patch.open_map(os.path.join(rc.MAPS, mid + '.map'), GAME)
        for t in m.tags:
            if t.get('name'):
                have.add((t['class'], t['name'].lower()))
    return have


def resolve(value, game, order):
    """halo_enhancer.resolve_gamed, kept local so this tool needs no GUI import."""
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


def field_names(target, order):
    """Every field name this target could ask the plugin for."""
    f = resolve(target.get('field'), GAME, order)
    if not isinstance(f, str):
        return []
    return [p + f for p in DIFF_PREFIXES] if target.get('diff_prefix_nl') else [f]


def check(card, have, registry, order):
    """(ok, reason). ok means every tag exists in Reach and every field resolves."""
    tag = resolve(card.get('tag'), GAME, order)
    if not isinstance(tag, str) or ' ' not in tag:
        return False, 'no tag to inherit'
    cls, _, rest = tag.partition(' ')
    paths = [p.strip() for p in rest.split('&')]
    missing = [p for p in paths
               if '*' not in p and (cls, p.lower()) not in have]
    present = [p for p in paths if p not in missing]
    if missing and not present:
        return False, 'tag absent in Reach: ' + ', '.join(
            p.rsplit(SEP, 1)[-1] for p in missing)
    if missing:
        # A multi-tag card whose inherited value names a variant Reach does not have.
        # ODST is the usual culprit -- it writes `magnum & automag` and
        # `plasma_rifle & plasma_rifle_red`, and Reach has the plain half of each but
        # neither variant. Keeping only the paths that exist is what the card means in
        # Reach; inheriting the pair made 18 cards resolve to nothing at all.
        tag = cls + ' ' + ' & '.join(present)
    plugin = registry.get(cls)
    if plugin is None:
        return False, 'no %s plugin for Reach' % cls
    targets = resolve(card.get('targets'), GAME, order) or []
    if not targets:
        return False, 'no targets for Reach'
    bad = []
    for t in targets:
        if not isinstance(t, dict):
            continue
        blk = resolve(t.get('block'), GAME, order)
        # nth can itself be per-game (Halo 2 often needs a different barrel), so it
        # has to be resolved before it is handed to plugin.find.
        nth = resolve(t.get('nth'), GAME, order) or 0
        names = field_names(t, order)
        if not names:
            bad.append('(unnamed field)')
            continue
        if not any(plugin.find(n, blk, nth) for n in names):
            bad.append(names[0] + (' in %s' % blk if blk else ''))
    if bad:
        return False, 'field absent: ' + '; '.join(bad)
    return True, tag


def _span(lines, i):
    """(start, end) line indices of the brace block opened on or after line i."""
    depth, started = 0, False
    for j in range(i, len(lines)):
        depth += lines[j].count('{') - lines[j].count('}')
        if '{' in lines[j]:
            started = True
        if started and depth <= 0:
            return i, j
    return i, len(lines) - 1


def _find(lines, pred, lo, hi):
    for j in range(lo, hi + 1):
        if pred(lines[j]):
            return j
    return None


def _indent(line):
    return line[:len(line) - len(line.lstrip())]


def wire_card(lines, weapon, card, tag, order):
    """Add Halo Reach to one card. Returns True if anything changed."""
    w = _find(lines, lambda l: l.strip() == '"%s": {' % weapon, 0, len(lines) - 1)
    if w is None:
        return False
    ws, we = _span(lines, w)
    c = _find(lines, lambda l: l.strip() == '"%s": {' % card, ws, we)
    if c is None:
        return False
    cs, ce = _span(lines, c)
    changed = False

    # --- game: add Reach to the allow list (absent list = every game, leave alone)
    g = _find(lines, lambda l: l.strip().startswith('"game":'), cs, ce)
    if g is not None:
        if 'Halo Reach' not in lines[g]:
            if '[' not in lines[g]:
                # a BARE STRING game ("game": "Halo 3"), not a list -- promote it
                head, _, rest = lines[g].partition(':')
                val = rest.strip().rstrip(',')
                lines[g] = '%s: [%s, "Halo Reach"]%s' % (
                    head, val, ',' if rest.rstrip().endswith(',') else '')
            elif lines[g].rstrip().endswith('],') or lines[g].rstrip().endswith(']'):
                lines[g] = lines[g].replace(']', ', "Halo Reach"]', 1)
            else:                       # a multi-line list: find its close
                ge = _find(lines, lambda l: l.strip().startswith(']'), g, ce)
                lines[ge - 1] = lines[ge - 1].rstrip() + ','
                lines.insert(ge, _indent(lines[ge - 1]) + '"Halo Reach"')
                ce += 1
            changed = True

    # --- tag: only a per-game dict needs an entry; a plain string already applies
    t = _find(lines, lambda l: l.strip().startswith('"tag":'), cs, ce)
    if t is not None and lines[t].rstrip().endswith('{'):
        ts, te = _span(lines, t)
        if not any('"Halo Reach"' in lines[k] for k in range(ts, te + 1)):
            lines[te - 1] = lines[te - 1].rstrip() + ','
            lines.insert(te, _indent(lines[te - 1]) + '"Halo Reach": '
                         + json.dumps(tag, ensure_ascii=False))
            ce += 1
            changed = True

    # --- targets: mirror the inherited game's array when targets are per-game
    tg = _find(lines, lambda l: l.strip().startswith('"targets":'), cs, ce)
    if tg is not None and lines[tg].rstrip().endswith('{'):
        gs, ge2 = _span(lines, tg)
        if not any('"Halo Reach"' in lines[k] for k in range(gs, ge2 + 1)):
            src = None
            for g2 in reversed(order[:order.index('Halo Reach')]):
                k = _find(lines, lambda l, gg=g2: l.strip().startswith('"%s": [' % gg),
                          gs, ge2)
                if k is not None:
                    src = k
                    break
            if src is not None:
                se = _find(lines, lambda l: l.strip().startswith(']'), src, ge2)
                body = [ln for ln in lines[src:se + 1]]
                body[0] = body[0].replace('"%s": [' % order[order.index('Halo Reach') - 1],
                                          '"Halo Reach": [', 1)
                if not body[0].strip().startswith('"Halo Reach"'):
                    ind = _indent(body[0])
                    body[0] = ind + '"Halo Reach": ['
                if not body[-1].rstrip().endswith(','):
                    body[-1] = body[-1].rstrip() + ','
                lines[src:src] = body
                changed = True
    return changed


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', action='store_true', help='write the Reach entries')
    ap.add_argument('--show-ok', action='store_true', help='list the cards that pass too')
    a = ap.parse_args()

    doc = json.load(open(HALO_JSON, encoding='utf-8'))
    order = list(doc['Missions'])
    sw = doc['Player Modifiers']['Specific Weapon Modifier']
    reach_weapons = set()
    for mm in doc['Missions'][GAME].values():
        for k in ('weapons', 'turret', 'grenades'):
            reach_weapons |= set(mm.get(k) or [])
    alias = {'Magnum': 'Pistol'}
    reach_weapons = {alias.get(w, w) for w in reach_weapons}

    print('resolving Reach tags across %d campaign maps...' % len(rc.CAMPAIGN))
    have = reach_tags()
    registry = halo_patch.PluginRegistry(PLUGINS, SUBDIRS)

    ok, bad = [], []
    for weapon in sorted(reach_weapons & set(sw)):
        for name, card in sw[weapon].items():
            if not isinstance(card, dict):
                continue
            g = card.get('game')
            gl = [g] if isinstance(g, str) else list(g or [])
            # No `game` restriction AND a plain-string tag means the card already
            # applies in every game -- there is nothing to wire, and reporting it as
            # pending made the backlog look bigger than it is.
            already = (GAME in gl) or (isinstance(card.get('tag'), dict)
                                       and GAME in card['tag'])                 or (not gl and isinstance(card.get('tag'), str))
            if already:
                continue
            good, why = check(card, have, registry, order)
            (ok if good else bad).append((weapon, name, why))

    print('\n=== would wire (%d) ===' % len(ok))
    if a.show_ok:
        for w, n, tag in ok:
            print('   %-16s %-24s %s' % (w, n, tag.split(' ', 1)[1][:70]))
    else:
        byw = {}
        for w, n, _ in ok:
            byw.setdefault(w, []).append(n)
        for w in sorted(byw):
            print('   %-16s %d: %s' % (w, len(byw[w]), ', '.join(sorted(byw[w]))))

    print('\n=== needs real work (%d) ===' % len(bad))
    byreason = {}
    for w, n, why in bad:
        byreason.setdefault(why.split(':')[0], []).append('%s/%s' % (w, n))
    for r in sorted(byreason):
        print('   %-22s %d  e.g. %s' % (r, len(byreason[r]), ', '.join(byreason[r][:4])))
    print()
    for w, n, why in bad:
        print('   %-16s %-24s %s' % (w, n, why))

    if not a.apply:
        print('\n(report only -- pass --apply to write the Reach entries)')
        return
    lines = open(HALO_JSON, encoding='utf-8').read().split('\n')
    written = 0
    for w, n, tag in ok:
        if wire_card(lines, w, n, tag, order):
            written += 1
    out = '\n'.join(lines)
    json.loads(out)                      # refuse to write anything unparseable
    open(HALO_JSON, 'w', encoding='utf-8', newline='').write(out)
    print('\nwired %d card(s) into halo.json' % written)


if __name__ == '__main__':
    main()
