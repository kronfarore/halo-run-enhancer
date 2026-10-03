r"""Which sounds does each ported weapon play TODAY? Reads the deployed map (as
port_refs_audit.py does): the weapon's sound references, the sounds inside the effects it
names (firing, empty, ...), and the sounds its first-person animation graphs carry
(reload, ready, ...). Each is OWN (under the port's folder) or BORROWED (the donor's) --
the starting list for giving a port its own audio.

    python port_sound_refs.py [--game "Halo Reach"]
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_refs_audit as a                                       # noqa: E402

SOUND = ('snd!', 'lsnd')


def sounds_of(m, game, group, base, datum, depth=0, seen=None):
    """[(path, class, name)] of sounds under a tag, following effects one level deep."""
    seen = seen if seen is not None else set()
    px = a.plugin_xml(game, group)
    if px is None:
        return []
    out = []
    for field, (cls, name) in a.refs(m, base, px, datum):
        if cls in SOUND:
            out.append((field, cls, name))
        elif cls in ('effe', 'jmad') and depth < 1 and (cls, name) not in seen:
            seen.add((cls, name))
            hit = m.find_tags(cls, name)
            if hit:
                for f2, c2, n2 in sounds_of(m, game, cls, hit[0][1], datum, depth + 1, seen):
                    out.append(('%s -> %s' % (name.rsplit(chr(92), 1)[-1], f2), c2, n2))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game')
    p = ap.parse_args()
    cat = json.load(open(os.path.join(a.TOOL, 'weapon_ports_catalog.json'), encoding='utf-8'))
    for game, v in cat.items():
        if p.game and game != p.game:
            continue
        for e in (v if isinstance(v, list) else [v]):
            weap = next((r['tag'] for r in e.get('balance', []) if r['class'] == 'weap'), None)
            own_dir = weap.rsplit(chr(92), 1)[0].lower()
            for mp in [os.path.join(a.MCC, x) for x in a.MAPS.get(game, [])]:
                if not os.path.exists(mp):
                    continue
                m = a.hp.open_map(mp, game)
                hit = m.find_tags('weap', weap)
                if not hit:
                    continue
                datum = a.hp._tagref_datum(m)
                rows = sounds_of(m, game, 'weap', hit[0][1], datum)
                print('== %s %s  (%s)' % (game, e['weapon'], os.path.relpath(mp, a.MCC)))
                for field, cls, name in rows:
                    own = str(name).lower().startswith(own_dir + chr(92))
                    print('   %-6s %-60s %s' % ('OWN' if own else 'BORROW', field[-60:], name))
                break


if __name__ == '__main__':
    main()
