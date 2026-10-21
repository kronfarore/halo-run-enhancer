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
               model pool ONE path -- the AR, 2026-10-20); an EMPTY current path ('') FILLS an
               empty reference (h2_tagref.fill_reference -- the Spike Rifle's projectile model)
    shared     [(path, why)] -- what stays someone else's, on purpose (printed)
    string_ids {old: new} renamed through h2_stringid (adjacent string-id fields: the AR's
               3P label `rifle`/`smg` -> `rifle`/`br`), string_ids_done (field, value) its guard

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


def byte_edits(w):
    """`byte_edits` [(tag, old hex, new hex)] (the Spike Rifle's light volume colour, boot 1): a
    same-length byte run replaced everywhere it occurs in a cloned tag -- kept only if tool's
    export then differs from before in exactly the bytes replaced (function data `Value` rows,
    one per byte) and in nothing else; already applied = left alone."""
    import h2_tagfield as tf
    for tag, old, new in w.get('byte_edits', ()):
        path = os.path.join(TAGS, tag)
        a, b = bytes.fromhex(old), bytes.fromhex(new)
        d = open(path, 'rb').read()
        n = d.count(a)
        if not n:
            print('   %-34s %s -> %s %s' % (os.path.basename(tag), old, new,
                                           'already' if d.count(b) else 'NOT FOUND'))
            continue
        rows = tf.read_all(tf.export(path))
        open(path, 'wb').write(d.replace(a, b))
        x = tf.export(path)
        after = tf.read_all(x) if x else []
        moved = [i for i, (p, q) in enumerate(zip(rows, after)) if p[4] != q[4]]
        if (len(after) != len(rows) or len(moved) != n * len(a)
                or any(rows[i][2] != 'Value' for i in moved)):
            open(path, 'wb').write(d)
            raise SystemExit('%s: %s -> %s moved %d rows, not %d data bytes; restored'
                             % (tag, old, new, len(moved), n * len(a)))
        print('   %-34s %s -> %s  (%d place(s), tool: %d data bytes, nothing else)'
              % (os.path.basename(tag), old, new, n, len(moved)))


def wire(w):
    for row in w['wiring']:
        tag, cls, old, new, why = row[:5]
        opt = row[5] if len(row) > 5 else {}
        path = os.path.join(TAGS, tag)
        have = h2_tagref.references(path)
        if (cls, new) in have and (cls, old) not in have:
            print('   %-34s %s already points at the port' % (os.path.basename(tag), why))
            continue
        if old == '':
            # the clone's reference is EMPTY (the Spike Rifle's projectile model): filled,
            # tool-verified (h2_tagref.fill_reference)
            h2_tagref.fill_reference(path, cls, new)
            print('      (%s)' % why)
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
    for row in w.get('attachments', ()):
        # an object attachment the clone lacks (the Spike Rifle's light volume), tool-verified;
        # row: (tag, donor tag, class, donor element[, {'count_at', 'after'} hints])
        tag, donor, cls, element = row[:4]
        path = os.path.join(TAGS, tag)
        if any(r[0] == cls for r in h2_tagref.references(path)):
            print('   %-34s already has a %s attachment' % (os.path.basename(tag), cls))
            continue
        h2_tagref.add_attachment(path, os.path.join(TAGS, donor), cls, element,
                                 **(row[4] if len(row) > 4 else {}))
    if w.get('byte_edits'):
        print('byte edits in the clones:')
        byte_edits(w)
    print('wiring them together:')
    wire(w)
    if w.get('string_ids'):
        # the third-person LABEL (weapon class / weapon name: what the characters' 3P graphs
        # key on, H2_PORT_PLAN 0.3) -- a run of adjacent string ids, h2_stringid (any length,
        # tool-verified); skipped once `string_ids_done` (field, value) reads true
        import h2_stringid
        tag = os.path.join(TAGS, w['weapon'])
        field, want = w['string_ids_done']
        now = {n: v for _i, n, v in h2_stringid.string_ids(h2_stringid.export(tag))}
        if now.get(field) == want:
            print('   %-34s %s already %r' % (os.path.basename(tag), field, want))
        else:
            print('   ' + h2_stringid.rename(tag, w['string_ids'], write=True))
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
