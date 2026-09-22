r"""Create the Halo 3 SAW tags in the Editing Kit, ready to place in Sapien.

The SAW starts as the Assault Rifle: a copy of its weapon tag already carries every
weapon-level number independently (magazine, rate of fire, spread, magnetism, melee),
because those live in the weapon tag itself. What it does NOT get for free is its own
bullet -- velocity and bullet damage live in the projectile and damage_effect tags, and
a plain copy still points at the Assault Rifle's, so changing them would change the
Assault Rifle too.

So the projectile and its damage effect are cloned as well, and the references are
repointed. Every clone is named to be EXACTLY as long as the path it replaces, which
makes each repoint an in-place byte overwrite: no chunk length changes, no ancestor
lengths to correct, nothing that can desynchronise the tag tree. The names are ugly for
that reason and can be tidied once length propagation is proven.

Geometry and animations stay the Assault Rifle's for now -- the port's own model is a
separate step, and this build is about proving tags, placement and residency.

    python h3_make_saw.py [--write]
"""
import argparse, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))  # balance tables live beside the JMS converters, see the port backup on F:
sys.path.insert(0, HERE)
import h3tag                                                   # noqa: E402

B = os.sep
EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK')
TAGS = os.path.join(EK, 'tags')
AR_DIR = B.join(['objects', 'weapons', 'rifle', 'assault_rifle'])
SAW_DIR = B.join(['objects', 'weapons', 'rifle', 'saw'])

AR_WEAPON = AR_DIR + B + 'assault_rifle'
AR_PROJ = AR_DIR + B + 'projectiles' + B + 'assault_rifle_bullet'
AR_DMG = AR_DIR + B + 'damage_effects' + B + 'assault_rifle_bullet'

# Same length as what each replaces, so a repoint never changes a chunk's size.
SAW_WEAPON = SAW_DIR + B + 'saw'                               # free: nothing points at it
SAW_PROJ = SAW_DIR + B + 'projectiles' + B + 'saw_bullet_h4_original_numbers'
SAW_DMG = SAW_DIR + B + 'damage_effects' + B + 'saw_bullet_h4_original_numbers'

CLONES = [  # (source tag, destination tag, extension)
    (AR_WEAPON, SAW_WEAPON, '.weapon'),
    (AR_PROJ, SAW_PROJ, '.projectile'),
    (AR_DMG, SAW_DMG, '.damage_effect'),
]
# (which clone, old path, new path) -- rewritten inside the destination tag
REPOINTS = [
    (SAW_WEAPON + '.weapon', AR_PROJ, SAW_PROJ),
    (SAW_PROJ + '.projectile', AR_DMG, SAW_DMG),
]


def full(rel, ext=''):
    return os.path.join(TAGS, rel + ext)


def check_lengths():
    ok = True
    for old, new in ((AR_PROJ, SAW_PROJ), (AR_DMG, SAW_DMG)):
        same = len(old) == len(new)
        ok = ok and same
        print('   %-3s %-72s %d' % ('' if same else '!!', old, len(old)))
        print('   %-3s %-72s %d%s' % ('', new, len(new),
                                      '' if same else '   <== MUST MATCH'))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    print('path lengths (a repoint overwrites in place, so these must match):')
    if not check_lengths():
        raise SystemExit('name lengths differ -- fix the names before writing')

    print('\nclones:')
    for src, dst, ext in CLONES:
        s, d = full(src, ext), full(dst, ext)
        if not os.path.exists(s):
            raise SystemExit('missing source tag: ' + s)
        print('   %-52s -> %s' % (src + ext, dst + ext))
        if a.write:
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)

    if not a.write:
        print('\n(dry run -- pass --write to create the tags)')
        return

    print('\nrepoints:')
    for tag_rel, old, new in REPOINTS:
        t = h3tag.Tag(full(tag_rel))
        before = len(t.data)
        n = t.repoint_in_place(old, new)
        ok, covered, total = t.check()
        if len(t.data) != before:
            raise SystemExit('file size changed -- the overwrite was not in place')
        t.save()
        print('   %-46s %d reference(s) -> %s' % (os.path.basename(tag_rel), n, new))
        print('      tree still spans the file: %s (%d of %d)' % (ok, covered, total))

    print('\nverify -- every reference of every new tag must resolve to a real file:')
    for _src, dst, ext in CLONES:
        p = full(dst, ext)
        d = open(p, 'rb').read()
        bad = 0
        for m in re.finditer(rb'([a-z!_ ]{4})((?:objects|globals|sound|effects|ui)[ -~]{5,}?)frgt', d):
            grp, path = m.group(1).decode()[::-1].strip(), m.group(2).decode()
            hits = [f for f in os.listdir(os.path.dirname(full(path)))
                    if f.startswith(os.path.basename(path) + '.')] \
                if os.path.isdir(os.path.dirname(full(path))) else []
            if not hits:
                bad += 1
                print('      MISSING  %-6s %s' % (grp, path))
        print('   %-52s %s' % (os.path.basename(p), 'all references resolve' if not bad
                               else '%d missing' % bad))
    print('\nNext: place %s in Sapien on 010_jungle, then build the map.' % SAW_WEAPON)


if __name__ == '__main__':
    main()
