r"""Name a ported render model's region the way the stock ones are named.

THIS IS THE STEP THAT MADE THE HALO 3 PORT VISIBLE WHEN DROPPED, and it had no tool --
it was done by hand once and nearly lost. Recording it here so the next port cannot skip
it.

`tool render` writes the region and permutation as **'default'** no matter what the JMS
declares. Every stock weapon says **'standard'**. First person does not care -- the weapon
tag reaches its first-person model directly -- but the WORLD model is drawn through the
model tag's variant system, which looks the permutation up BY NAME. With 'default' the
variant finds nothing and the weapon renders as thin air: correct in your hands, invisible
the moment you drop it or hand it to an ally.

Three things were tried and none of them worked, so do not repeat them:

  * declaring the region as `standard` in the JMS -- `tool` still writes 'default';
  * naming the permutation file standard.jms -- likewise;
  * patching the built MAP's string id (0x00000001 -> 0x0000095e). The cache builder
    BINDS regions at build time, so by then the name is one nothing reads any more. This
    was done twice and changed nothing in game.

It has to be in the TAG before the build. In a tag the name is a length-prefixed `tgsi`
chunk, so 'default' -> 'standard' GROWS the file by one byte and every enclosing chunk's
length has to grow with it -- which is what `h3tag.rename_stringid` does.

    python h3_region_name.py                            # report both models
    python h3_region_name.py --write
    PORT_EK=odst python h3_region_name.py --write
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                    # noqa: E402
import h3_kit                                                   # noqa: E402

B = os.sep
OLD, NEW = 'default', 'standard'
#: All FOUR of the port's render models: the two `tool render` writes, and the two COPIES
#: the wiring steps make at path lengths the weapon and model tags can be repointed to in
#: place. The copies are what the game actually loads, so renaming only the originals
#: fixes nothing -- and because the wiring steps RE-RENDER, this has to run LAST, after
#: h3_saw_world_model.py and h3_saw_wire_model.py, or a render puts 'default' back.
#:
#: The first-person pair does not strictly need it (the weapon reaches that model
#: directly, by path), but a model whose region disagrees with every other model in the
#: game is a trap left for somebody.
SAW = ['objects', 'weapons', 'rifle', 'saw']
MODELS = [B.join(SAW + ['saw']),
          B.join(['objects', 'weapons', 'rifle', 'saw_3p', 'saw_3p']),
          B.join(SAW + ['saw_world_model_h4_port']),
          B.join(SAW + ['fp_saw_port', 'fp_saw_port_h4_original_numbers'])]
EXT = '.render_model'


def names(tag):
    """Every `tgsi` string id in the tag, with its offset -- enough to see the region."""
    out = []
    for n in tag.nodes():
        if n.marker != 'tgsi':
            continue
        out.append((n.off, bytes(tag.data[n.payload_at:n.off + 12 + n.length])
                    .decode('latin-1')))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--old', default=OLD)
    ap.add_argument('--new', default=NEW)
    a = ap.parse_args()
    print(h3_kit.banner())

    for rel in MODELS:
        p = os.path.join(h3_kit.TAGS, rel + EXT)
        if not os.path.exists(p):
            print('   %-46s NOT BUILT YET' % (rel + EXT))
            continue
        t = h3tag.Tag(p)
        ok, cov, tot = t.check()
        got = [s for _off, s in names(t)]
        hits = got.count(a.old)
        print('   %-46s parses %s (%d/%d), string ids %s'
              % (os.path.basename(p), ok, cov, tot, got))
        if not ok:
            print('      refusing to touch a tag whose tree does not span the file')
            continue
        if not hits:
            print('      nothing named %r -- already %r?' % (a.old, a.new))
            continue
        if not a.write:
            print('      would rename %d x %r -> %r' % (hits, a.old, a.new))
            continue
        backup = p + '.before_rename'
        if not os.path.exists(backup):
            shutil.copy2(p, backup)
        before = len(t.data)
        n = t.rename_stringid(a.old, a.new)
        ok, cov, tot = t.check()
        grew = len(t.data) - before
        print('      renamed %d, file grew %d byte(s), parses %s (%d/%d)'
              % (n, grew, ok, cov, tot))
        if not ok or grew != n * (len(a.new) - len(a.old)):
            raise SystemExit('not saved: the rename did not add up')
        t.save(p)
        print('      wrote %s' % os.path.basename(p))

    if not a.write:
        print('\n(dry run -- pass --write)')


if __name__ == '__main__':
    main()
