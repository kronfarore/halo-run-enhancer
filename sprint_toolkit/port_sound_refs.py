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
    # a kit build that is not deployed yet (h1_port_test_map's HCEEK\maps\port_test copy)
    ap.add_argument('--map')
    ap.add_argument('--weapon', help='only this catalog weapon')
    p = ap.parse_args()
    cat = json.load(open(os.path.join(a.TOOL, 'weapon_ports_catalog.json'), encoding='utf-8'))
    # borrows the user kept ON PURPOSE (a Halo 1 port's `sound_keeps`, ports_h1/<key>.py):
    # printed KEEP, not BORROW -- the close-out rule is "no BORROW"
    import ports_h1
    keeps = {('Halo 1', P['name']): {k.lower() for k in P.get('sound_keeps', {})}
             for _k, P in ports_h1.all_ports()}
    for game, v in cat.items():
        if p.game and game != p.game:
            continue
        for e in (v if isinstance(v, list) else [v]):
            if p.weapon and e.get('weapon') != p.weapon:
                continue
            weap = e.get('weap') or next((r['tag'] for r in e.get('balance', [])
                                          if r['class'] == 'weap'), None)
            if not weap:
                continue
            own_dir = weap.rsplit(chr(92), 1)[0].lower()
            # Halo 1 ports keep their sounds in sound\weapons\<x>_port (never sound\sfx)
            port_dir = 'sound' + chr(92) + 'weapons' + chr(92) + own_dir.rsplit(chr(92), 1)[-1].replace(' ', '_') + '_port'
            for mp in ([p.map] if p.map else [os.path.join(a.MCC, x) for x in a.MAPS.get(game, [])]):
                if not os.path.exists(mp):
                    continue
                m = a.hp.open_map(mp, game)
                hit = m.find_tags('weap', weap)
                if not hit:
                    continue
                datum = a.hp._tagref_datum(m)
                rows = sounds_of(m, game, 'weap', hit[0][1], datum)
                same = os.path.splitdrive(mp)[0].lower() == os.path.splitdrive(a.MCC)[0].lower()
                print('== %s %s  (%s)' % (game, e['weapon'], os.path.relpath(mp, a.MCC) if same else mp))
                for field, cls, name in rows:
                    nm = str(name).lower()
                    own = nm.startswith(own_dir + chr(92)) or nm.startswith(port_dir.lower() + chr(92))
                    tag = 'OWN' if own else ('KEEP' if nm in keeps.get((game, e['weapon']), ()) else 'BORROW')
                    print('   %-6s %-60s %s' % (tag, field[-60:], name))
                break


if __name__ == '__main__':
    main()
