r"""Give the Halo 3 SAW its own first-person model.

`tool render` built the SAW's geometry into objects\weapons\rifle\saw\saw.render_model,
on the Assault Rifle's first-person skeleton so the Assault Rifle's animations still
drive it. The weapon tag reaches its first-person model DIRECTLY -- a `mode` reference,
69 characters long -- so the render model is copied to a path of exactly that length and
the reference is overwritten in place. Nothing needs the tag-tree length maths that way.

The world (dropped) model is still the Assault Rifle's; it is a separate hlmt reference
and a separate step.

    python h3_saw_wire_model.py [--write]
"""
import argparse, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))  # balance tables live beside the JMS converters, see the port backup on F:
sys.path.insert(0, HERE)
import h3tag                                                    # noqa: E402

B = os.sep
TAGS = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK', 'tags')
AR_FP = B.join(['objects', 'weapons', 'rifle', 'assault_rifle', 'fp_assault_rifle',
                'fp_assault_rifle'])
BUILT = B.join(['objects', 'weapons', 'rifle', 'saw', 'saw'])
SAW_FP = B.join(['objects', 'weapons', 'rifle', 'saw', 'fp_saw_port',
                 'fp_saw_port_h4_original_numbers'])
WEAPON = B.join(['objects', 'weapons', 'rifle', 'saw', 'saw'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    print('the weapon reaches its first-person model by path, so lengths must match:')
    print('   %-72s %d' % (AR_FP, len(AR_FP)))
    print('   %-72s %d%s' % (SAW_FP, len(SAW_FP),
                             '' if len(SAW_FP) == len(AR_FP) else '   <== MUST MATCH'))
    if len(SAW_FP) != len(AR_FP):
        raise SystemExit('name lengths differ')

    src = os.path.join(TAGS, BUILT + '.render_model')
    dst = os.path.join(TAGS, SAW_FP + '.render_model')
    if not os.path.exists(src):
        raise SystemExit('run tool render first: missing ' + src)
    print('\nrender model %s -> %s' % (BUILT, SAW_FP))
    if a.write:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

    wp = os.path.join(TAGS, WEAPON + '.weapon')
    t = h3tag.Tag(wp)
    before = len(t.data)
    n = t.repoint_in_place(AR_FP, SAW_FP, group='mode') if a.write else 0
    if a.write:
        if len(t.data) != before:
            raise SystemExit('file size changed -- the overwrite was not in place')
        t.save()
    print('weapon first-person model reference: %d rewritten' % n)

    if a.write:
        d = open(wp, 'rb').read()
        print('\nreferences of saw.weapon now:')
        seen = set()
        for m in re.finditer(rb'([a-z!_ ]{4})((?:objects|globals|sound|effects|ui)[ -~]{5,}?)frgt', d):
            g, p = m.group(1).decode()[::-1].strip(), m.group(2).decode()
            if g in ('hlmt', 'mode', 'jmad') and (g, p) not in seen:
                seen.add((g, p))
                where = 'SAW' if B + 'saw' + B in p else 'assault rifle'
                print('   %-6s %-72s %s' % (g, p, where))
        print('\nNow rebuild 010_jungle so the new model reaches the cache.')
    else:
        print('\n(dry run -- pass --write)')


if __name__ == '__main__':
    main()
