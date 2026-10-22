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
               empty reference (h2_tagref.fill_reference -- the Spike Rifle's projectile model);
               {'class': X} changes the reference's CLASS, the path kept (h2_tagref.set_class --
               the Flamethrower's flame: a contrail attachment made an attached effect)
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
    for row in w.get('byte_edits', ()):
        # an optional 4th value names the FIELDS the edit may move instead of function data
        # `Value` rows (the Flamethrower's emitter size input: an `Input Variable` enum, boot 12);
        # as a dict {'fields': (...), 'before' / 'after': anchor hex}: ONE occurrence only, the
        # nearest before / after a UNIQUE anchor run (the Spike Rifle's sparks, check 10: one
        # emitter's functions, byte-identical to other emitters', found beside its unique size)
        tag, old, new = row[:3]
        opt = row[3] if len(row) > 3 else ('Value',)
        opt = opt if isinstance(opt, dict) else {'fields': opt}
        fields = tuple(opt.get('fields') or ('Value',))
        path = os.path.join(TAGS, tag)
        a, b = bytes.fromhex(old), bytes.fromhex(new)
        d = open(path, 'rb').read()
        anchor = opt.get('before') or opt.get('after')
        if anchor:
            k = bytes.fromhex(anchor)
            if d.count(k) != 1:
                print('   %-34s %s... %s' % (os.path.basename(tag), new[:16],
                                             'already (anchor gone)' if d.count(b) else
                                             'ANCHOR %s found %d times' % (anchor[:16], d.count(k))))
                continue
            q = d.rfind(a, 0, d.find(k)) if opt.get('before') else d.find(a, d.find(k) + len(k))
            if q < 0:
                print('   %-34s %s... NOT FOUND beside the anchor' % (os.path.basename(tag), old[:16]))
                continue
            n, out = 1, d[:q] + b + d[q + len(a):]
        else:
            n = d.count(a)
            if not n:
                print('   %-34s %s -> %s %s' % (os.path.basename(tag), old, new,
                                               'already' if d.count(b) else 'NOT FOUND'))
                continue
            out = d.replace(a, b)
        rows = tf.read_all(tf.export(path))
        open(path, 'wb').write(out)
        x = tf.export(path)
        after = tf.read_all(x) if x else []
        moved = [i for i, (p, q) in enumerate(zip(rows, after)) if p[4] != q[4]]
        # the bytes that DIFFER between old and new (a colour keeps a channel: the Flamethrower's
        # blue pilot keeps the white tint's blue byte)
        diff = sum(x != y for x, y in zip(a, b))
        if fields != ('Value',):
            diff = len(fields)                 # one moved row a named field
        if (len(a) != len(b) or len(after) != len(rows) or len(moved) != n * diff
                or any(rows[i][2] not in fields for i in moved)):
            open(path, 'wb').write(d)
            raise SystemExit('%s: %s -> %s moved %d rows, not %d data bytes; restored'
                             % (tag, old, new, len(moved), n * diff))
        print('   %-34s %s -> %s  (%d place(s), tool: %d data bytes, nothing else)'
              % (os.path.basename(tag), old, new, n, len(moved)))


def function_edits(w):
    """`function_edits` [(tag, old hex, new hex)] -- a whole FUNCTION (a `data` block of 1-byte
    elements) replaced by one of ANOTHER length (the Flamethrower's digits, boot 7: Halo 2's
    function type 1 is CONSTANT -- it ignores its input -- and type 2, the transition Bungie's PR
    heat gauge uses, is 36 bytes, not 28). `old` must be the block's whole content and unique; its
    chunk count and the owning element's count field are rewritten, the owner found by trial
    (every u32 equal to the old length); kept only when tool's export reads every row as before
    except that block's bytes, which read `new`. Already applied = left alone."""
    import struct
    import h2_tagfield as tf
    for tag, old, new in w.get('function_edits', ()):
        path = os.path.join(TAGS, tag)
        a, b = bytes.fromhex(old), bytes.fromhex(new)
        d = open(path, 'rb').read()
        if d.count(a) != 1:
            print('   %-34s %s... %s' % (os.path.basename(tag), new[:16],
                                         'already' if d.count(b) else 'NOT FOUND (%d)' % d.count(a)))
            continue
        q = d.find(a)
        if d[q - 16:q - 12] != b'dfbt' or struct.unpack_from('<II', d, q - 8) != (len(a), 1):
            raise SystemExit('%s: %s is not a whole data block' % (tag, old[:16]))
        rows = tf.read_all(tf.export(path))

        def split(rr, run):
            # the rows minus the first run of `data` Value rows equal to `run`
            vals = [int(r[4]) & 255 if r[2] == 'Value' else -1 for r in rr]
            for i in range(len(rr) - len(run) + 1):
                if vals[i:i + len(run)] == list(run):
                    return rr[:i] + rr[i + len(run):]
            return None
        rest = split(rows, a)
        done = False
        for p in range(q - 20, -1, -1):           # every byte: a loose tag's structs are unaligned
            if struct.unpack_from('<I', d, p)[0] != len(a):
                continue
            out = bytearray(d)
            out[q:q + len(a)] = b
            struct.pack_into('<I', out, q - 8, len(b))
            struct.pack_into('<I', out, p, len(b))
            open(path, 'wb').write(bytes(out))
            x = tf.export(path)
            if x and split(tf.read_all(x), b) == rest:
                print('   %-34s function %d -> %d bytes (count at 0x%X), tool: every other row as before'
                      % (os.path.basename(tag), len(a), len(b), p))
                done = True
                break
        if not done:
            open(path, 'wb').write(d)
            raise SystemExit('%s: no count field made the function read %s -- restored' % (tag, new[:16]))


def marker_renames(w):
    """`string_id_renames` [(tag, {old id: new id})] -- string ids in a cloned tag renamed through
    h2_stringid (any length, tool-verified; the Flamethrower's pilot effect: its location marker
    `exhaust` -> `pilot`); already renamed = left alone."""
    import h2_stringid
    for tag, ren in w.get('string_id_renames', ()):
        path = os.path.join(TAGS, tag)
        now = [v for _i, _n, v in h2_stringid.string_ids(h2_stringid.export(path))]
        if not any(old in now for old in ren):
            print('   %-34s %s already renamed' % (os.path.basename(tag), ', '.join(ren.values())))
            continue
        print('   ' + h2_stringid.rename(path, ren, write=True))
    for row in w.get('string_id_fills', ()):
        # an EMPTY string id given a value (h2_stringid.fill_empty, tool-verified): the
        # Flamethrower's digit colour animations read `primary_ammunition_tens`; opt {'after': text}
        # places the string after that unique pooled text (an element past the first)
        tag, name, block, index, nth, value = row[:6]
        after = row[6].get('after') if len(row) > 6 else None
        print('   %-34s %s' % (os.path.basename(tag), h2_stringid.fill_empty(
            os.path.join(TAGS, tag), name, block, index, nth, value,
            after=after.encode('latin-1') if after else None)))


def wire(w):
    for row in w['wiring']:
        tag, cls, old, new, why = row[:5]
        opt = row[5] if len(row) > 5 else {}
        path = os.path.join(TAGS, tag)
        have = h2_tagref.references(path)
        if opt.get('class'):
            # {'class': X}: the reference's CLASS changes, its path stays (old == new) -- the
            # Flamethrower's flame: its contrail attachment becomes an attached effect
            if (cls, old) not in have:
                print('   %-34s %s already a %s' % (os.path.basename(tag), why, opt['class']))
            else:
                h2_tagref.set_class(path, cls, old, opt['class'], nth=opt.get('nth') or 0)
                print('      (%s)' % why)
            continue
        if (cls, new) in have and (cls, old) not in have:
            print('   %-34s %s already points at the port' % (os.path.basename(tag), why))
            continue
        if old == '':
            # the clone's reference is EMPTY (the Spike Rifle's projectile model): filled,
            # tool-verified (h2_tagref.fill_reference)
            # {'field': name}: WHICH empty reference (the Flamethrower's `overheated` effect)
            h2_tagref.fill_reference(path, cls, new, field=opt.get('field'))
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
    for tag, cls, new, marker, like in w.get('append_attachments', ()):
        # an attachment APPENDED beside the clone's own (the Flamethrower's pilot flame);
        # h2_tagref.append_attachment, tool-verified
        path = os.path.join(TAGS, tag)
        if (cls, new) in h2_tagref.references(path):
            print('   %-34s already has %s' % (os.path.basename(tag), new.split('\\')[-1]))
            continue
        h2_tagref.append_attachment(path, cls, new, marker, like)
    if w.get('byte_edits'):
        print('byte edits in the clones:')
        byte_edits(w)
    if w.get('function_edits'):
        print('functions replaced in the clones:')
        function_edits(w)
    if w.get('string_id_renames') or w.get('string_id_fills'):
        print('string ids renamed in the clones:')
        marker_renames(w)
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
