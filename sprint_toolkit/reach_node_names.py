r"""Rename a Reach render model's nodes back to the donor's, after tool has sorted them.

WHY THE NAMES ARE WRONG IN THE FIRST PLACE. `tool render` does two things to a node name
that nothing warns about:

  * it STRIPS a leading `b_`, and Reach's skeleton is entirely b_-prefixed, so an honest
    JMS produces a model whose nodes are called `gun`, `magazine`, ...;
  * it then SORTS what is left, alphabetically, whatever order the JMS declares.

The first cost an empty first-person model and a weapon that vanished when dropped,
because nothing that animates the weapon could find its nodes. The second is subtler and
is what this is for.

THE WORLD ANIMATION GRAPH CARRIES ITS OWN SKELETON, and its animation data indexes INTO
it. The Assault Rifle's is

    b_gun, b_switch, b_safety, b_magazine, b_ophandle

and alphabetical is

    b_gun, b_magazine, b_ophandle, b_safety, b_switch

so a port whose nodes came out sorted has indices 1..4 permuted against the graph that
poses it. A weapon HELD or DROPPED is posed through that graph; one placed by the
scenario sits at bind pose and draws, which is what makes this look like a rendering
fault rather than an ordering one. First person is unaffected: its graph is the 52-node
ARMS skeleton and the weapon hangs off it by MARKER, not by node index.

THE TRICK. Order cannot be asked for, so it is bought with a sort key and the key is
renamed away here. `saw_to_jms_h3.py` emits `b_a_gun`, `b_b_switch`, `b_c_safety`,
`b_d_magazine`, `b_e_ophandle`; tool strips the `b_` and sorts on `a_gun`, `b_switch`,
... which is the donor's order. This then renames `a_gun` to `b_gun` and so on.

Every rename is ONE CHARACTER FOR ONE CHARACTER, so each is an in-place byte swap in the
string-id chunk with no length to propagate -- unlike the Halo 3 region rename, which
grows the file. `b_switch` is already correct and is left alone.

Run it AFTER every `tool render`, like the region rename in Halo 3.

    python reach_node_names.py                  # report
    python reach_node_names.py --write
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                    # noqa: E402
import h3_kit                                                   # noqa: E402

B = os.sep
MODEL = h3_kit.SAW_WEAPON + '.render_model'
#: a node the sort key still marks, e.g. a_gun / c_safety / d_magazine
KEYED = re.compile(r'^[a-z]_([a-z_0-9]+)$')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--model', default=MODEL)
    a = ap.parse_args()
    if not h3_kit.IS_REACH:
        raise SystemExit('Reach only -- Halo 3 and ODST have unprefixed skeletons and '
                         'tool does not touch their names. Refusing to run against %s.'
                         % h3_kit.banner())

    path = os.path.join(h3_kit.TAGS, a.model)
    if not os.path.exists(path):
        raise SystemExit('no such model: %s' % path)
    tag = h3tag.Tag(path)

    # The node names live as `tgsi` string-id chunks. Read them straight off the tree so
    # this does not depend on an XML export or on where the nodes block sits.
    found = []
    for n in tag.nodes():
        if n.marker != 'tgsi' or n.length < 2:
            continue
        raw = bytes(tag.data[n.payload_at:n.payload_at + n.length])
        try:
            text = raw.decode('latin1')
        except Exception:
            continue
        m = KEYED.match(text.strip('\0'))
        if m and text.strip('\0')[0] in 'acde':
            found.append((n, text.strip('\0'), 'b_' + m.group(1)))

    if not found:
        print('%s: no keyed node names left -- already renamed, or rendered without '
              'the sort key' % os.path.basename(a.model))
        return

    print('%s' % h3_kit.banner())
    for _n, old, new in found:
        same = len(old) == len(new)
        print('   %-14s -> %-14s %s' % (old, new, 'same length' if same
                                        else 'LENGTH DIFFERS -- refusing'))
        if not same:
            raise SystemExit('a rename would change the chunk length; not written')

    if not a.write:
        print('\n(dry run -- pass --write)')
        return
    for n, old, new in found:
        tag.data[n.payload_at:n.payload_at + len(new)] = new.encode('latin1')
    ok, covered, total = tag.check()
    if not ok:
        raise SystemExit('the chunk tree no longer spans the file (%d of %d) -- NOT saved'
                         % (covered, total))
    tag.save(path)
    print('\nrenamed %d node(s); tree spans %d of %d; wrote %s'
          % (len(found), covered, total, os.path.basename(path)))


if __name__ == '__main__':
    main()
