r"""Step 3 of a Halo 2 port: a weapon tag of its own, and a projectile / damage / firing effect
nothing else uses -- clone, then wire (generalized from h2_saw_weapon.py, the SAW 2026-09-23).

A port that shares a tag with a live weapon changes that weapon when it is tuned (the SAW's donor
borrowed the Warthog turret's bullet), so every tag a balance row may touch is CLONED and the
clones are wired together; nothing Bungie shipped is edited. The config's `weapon` section:

    weapon     the port's .weapon (kit-relative, with extension)
    clones     [(source tag file, the port's copy)] -- copied once (--force replaces)
    wiring     [(tag file, class, the path it names now, what it should name, why[, opt])] --
               h2_tagref edits, each proved by tool's re-export; already-wired is a no-op;
               opt {'every': True} moves identical references together (a weapon's two FP
               models), {'nth': k} the k-th of them (a .model whose render model and collision
               model pool ONE path -- the AR, 2026-10-20)
    shared     [(path, why)] -- what stays someone else's, on purpose (printed)

    python h2_port_weapon.py <key> [--force]
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_tagref  # noqa: E402
import ports_h2  # noqa: E402

TAGS = os.path.join(h2_tagref.H2EK, 'tags')


def clone(w, force):
    for src, dest in w['clones']:
        s, d = os.path.join(TAGS, src), os.path.join(TAGS, dest)
        if os.path.exists(d) and not force:
            print('   %-34s exists, left alone' % os.path.basename(dest))
            continue
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy(s, d)
        print('   %-34s <- %s' % (os.path.basename(dest), src))


def wire(w):
    for row in w['wiring']:
        tag, cls, old, new, why = row[:5]
        opt = row[5] if len(row) > 5 else {}
        path = os.path.join(TAGS, tag)
        have = h2_tagref.references(path)
        if (cls, new) in have and (cls, old) not in have:
            print('   %-34s %s already points at the port' % (os.path.basename(tag), why))
            continue
        h2_tagref.set_reference(path, cls, old, new, every=opt.get('every', False),
                                nth=opt.get('nth'))
        print('      (%s)' % why)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('-'):
        raise SystemExit(__doc__)
    key = argv[0]
    w = ports_h2.get(key, 'weapon')
    own = ports_h2.load(key)['reservations']['weapon_dir']
    print('cloning the tags the port would otherwise share:')
    clone(w, '--force' in argv)
    print('wiring them together:')
    wire(w)
    print('still pointing at somebody else, on purpose:')
    for path, why in w.get('shared', ()):
        print('   %-52s %s' % (path, why))
    print('what the port now owns:')
    for _src, dest in w['clones']:
        print('   %s' % dest)
        for cls, path in h2_tagref.references(os.path.join(TAGS, dest)):
            mark = '  <- own' if path.startswith(own) else ''
            print('      %-6s %s%s' % (cls, path, mark))


if __name__ == '__main__':
    main()
