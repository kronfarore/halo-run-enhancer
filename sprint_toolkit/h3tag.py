r"""Read and rewrite Halo 3 Editing Kit tag files.

An EK tag file opens with a small header -- group 4cc at 0x30, then 'BLAM' -- and from
0x40 it is a tree of chunks. Each chunk is a 4cc marker stored reversed ('tgrf' on disk
reads 'frgt'), a u32 of flags, a u32 LENGTH, then that many payload bytes, and a chunk's
payload may hold more chunks: 'tag!' wraps the whole tag, 'blay' carries the embedded
field definitions, and the tag's own data lives in 'tgst' (struct) / 'tgbl' (block) /
'tgrf' (tag reference) nodes.

A tag reference's payload is the referenced group's 4cc followed by its path, with no
terminator. The length is explicit, so a path can be swapped for one of a different size
-- as long as every ANCESTOR's length is corrected by the same delta, which is what
`repoint` does. Get that wrong and the file still opens in a hex editor but no longer
parses, so `check()` re-walks the tree afterwards.

    t = Tag(path);  t.references();  t.repoint(old, new);  t.save(dst)
"""
import io, os, struct

HEADER = 0x40                      # where the chunk tree starts
# 'want' and 'info' close Editing Kit tags and were both missing, which is what made big
# tags mis-parse: the real chain at 0x40 is 'tag!' then 'want' and/or 'info', and with
# either unknown that chain was rejected, so the forward scan fell through to a
# coincidental run near the end of the file -- and then reported a complete parse.
# Surveyed over 2000 tags (the 500 largest plus a random 1500), walking the top level of
# every one: tag! in all, want in 974, info in 245, nothing else. 'tgda' holds a block's
# raw data (an animation's frames, for one) and is nested, so the top-level survey never
# saw it -- without it a member chunk looks childless and its payload cannot be replaced.
MARKERS = {'tag!', 'blay', 'bdat', 'tgst', 'tgbl', 'tgrf', 'tgsi', 'tgsr',
           'tgdt', 'tghd', 'tgcs', 'bdpd', 'tbfd', 'want', 'info', 'tgda'}


class Node(object):
    __slots__ = ('off', 'marker', 'length', 'parent', 'children')

    def __init__(self, off, marker, length, parent):
        self.off, self.marker, self.length = off, marker, length
        self.parent, self.children = parent, []

    @property
    def payload_at(self):
        return self.off + 12

    def __repr__(self):
        return '<%s @%#x len %d>' % (self.marker, self.off, self.length)


class Tag(object):
    def __init__(self, path):
        self.path = path
        self.data = bytearray(io.open(path, 'rb').read())
        self._cache = None
        self.group = bytes(self.data[0x30:0x34])[::-1].decode('latin1')

    # --- parsing ---
    def _marker(self, off):
        if off + 12 > len(self.data):
            return None
        mk = bytes(self.data[off:off + 4])[::-1].decode('latin1', 'replace')
        return mk if mk in MARKERS else None

    def _chain(self, start, end):
        """Parse chunks from `start`; return the offsets if the chain lands exactly on
        `end`, else None. Used to tell a real run of chunks from a coincidence."""
        off, found = start, []
        while off + 12 <= end:
            mk = self._marker(off)
            if mk is None:
                return None
            length = struct.unpack_from('<I', self.data, off + 8)[0]
            if off + 12 + length > end:
                return None
            found.append((off, mk, length))
            off += 12 + length
        return found if off == end and found else None

    def _walk(self, start, end, parent, out):
        """A chunk's payload is its own field data FIRST and any child chunks packed at
        the tail, so children are found by scanning forward for a run of chunks that
        ends exactly where the parent does."""
        for at in range(start, max(start, end - 11)):
            chain = self._chain(at, end)
            if chain is None:
                continue
            for off, mk, length in chain:
                node = Node(off, mk, length, parent)
                out.append(node)
                if parent is not None:
                    parent.children.append(node)
                if mk != 'tgrf':
                    self._walk(node.payload_at, node.payload_at + length, node, out)
            return end
        return start

    def nodes(self):
        if getattr(self, '_cache', None) is not None:
            return self._cache
        out = []
        self.covered = self._walk(HEADER, len(self.data), None, out)
        # Where the OUTERMOST chain actually began. At the top level a chunk has no field
        # data of its own, so anything other than HEADER means the scan skipped a region
        # and locked onto a coincidental run -- which is exactly how a 366 KB graph once
        # reported a complete parse off a chain in its last 1.4 KB.
        self.root_at = min([n.off for n in out if n.parent is None], default=None)
        self._cache = out
        return out

    def _dirty(self):
        self._cache = None

    def check(self):
        """(ok, covered, total) -- the tree must span the file exactly AND start at the
        header. Both halves matter: covering to the end says nothing if the walk began
        somewhere in the middle."""
        self.nodes()
        ok = self.covered == len(self.data) and self.root_at == HEADER
        return ok, self.covered, len(self.data)

    # --- references ---
    def references(self):
        out = []
        for n in self.nodes():
            if n.marker != 'tgrf' or n.length < 4:
                continue
            grp = bytes(self.data[n.payload_at:n.payload_at + 4])[::-1].decode('latin1')
            path = bytes(self.data[n.payload_at + 4:n.payload_at + n.length]).decode('latin1')
            out.append((n.off, grp.strip(), path))
        return out

    def repoint(self, old, new, group=None):
        """Point references to `old` at `new`. Rewrites the reference's length and every
        ancestor's, so the tree still spans the file."""
        changed = 0
        while True:
            target = None
            for n in self.nodes():
                if n.marker != 'tgrf' or n.length < 4:
                    continue
                grp = bytes(self.data[n.payload_at:n.payload_at + 4])[::-1].decode('latin1')
                path = bytes(self.data[n.payload_at + 4:n.payload_at + n.length]).decode('latin1')
                if path == old and (group is None or grp.strip() == group):
                    target = n
                    break
            if target is None:
                return changed
            delta = len(new) - len(old)
            at = target.payload_at + 4
            self.data[at:at + len(old)] = new.encode('latin1')
            struct.pack_into('<I', self.data, target.off + 8, target.length + delta)
            up = target.parent
            while up is not None:                      # every ancestor grows too
                struct.pack_into('<I', self.data, up.off + 8, up.length + delta)
                up = up.parent
            changed += 1
            self._dirty()


    def repoint_in_place(self, old, new, group=None):
        """Swap a reference path for one of the SAME length, found by its chunk header
        rather than by walking the tree.

        A 'tgrf' chunk is a 12-byte header whose length covers the group 4cc plus the
        path, so a candidate is only accepted when a header sits exactly 12 bytes before
        the match AND its length equals 4 + len(path). That is what separates a real
        reference from the same text appearing in the embedded field definitions. Equal
        lengths mean nothing else in the file has to move.
        """
        if len(old) != len(new):
            raise ValueError('lengths differ (%d vs %d); use repoint()' % (len(old), len(new)))
        want = old.encode('latin1')
        out, at = 0, 0
        while True:
            at = self.data.find(want, at)
            if at < 0:
                return out
            head = at - 4 - 12                      # 4cc of the referenced group, then header
            if head >= 0 and bytes(self.data[head:head + 4])[::-1].decode('latin1', 'replace') == 'tgrf':
                length = struct.unpack_from('<I', self.data, head + 8)[0]
                grp = bytes(self.data[head + 12:head + 16])[::-1].decode('latin1').strip()
                if length == 4 + len(old) and (group is None or grp == group):
                    self.data[at:at + len(old)] = new.encode('latin1')
                    self._dirty()
                    out += 1
            at += 1


    def _chain_to(self, target, start=HEADER, end=None):
        """The chunks enclosing `target`, outermost first.

        A full tree walk is unreliable here because a chunk's payload mixes its own field
        data with child chunks, so this descends only along the branch that matters: at
        each level, scan for a chunk header whose range CONTAINS the target and whose end
        stays inside the parent, then descend into it.
        """
        end = len(self.data) if end is None else end
        out, lo, hi = [], start, end
        while True:
            found = None
            off = lo
            while off + 12 <= hi:
                mk = self._marker(off)
                if mk is not None:
                    length = struct.unpack_from('<I', self.data, off + 8)[0]
                    stop = off + 12 + length
                    if stop <= hi and off <= target < stop:
                        found = (off, mk, length, stop)
                        break
                off += 1
            if found is None:
                return out
            off, mk, length, stop = found
            out.append((off, mk, length))
            if off + 12 == target:          # the target chunk itself
                return out
            lo, hi = off + 12, stop

    def replace_payload(self, node, blob):
        """Swap one chunk's payload for `blob`, of any length.

        The chunk's own length is rewritten and so is every ANCESTOR's, because a chunk
        contains its children: grow a leaf and each enclosing chunk has to grow by the
        same delta or the tree stops spanning the file. `check()` afterwards is the
        proof. Returns the delta.

        Ancestors are read off the cached tree BEFORE the data moves, since the offsets
        of anything after this chunk shift by the delta.
        """
        at, old_len = node.payload_at, node.length
        chain = []
        up = node
        while up is not None:
            chain.append((up.off, up.length))
            up = up.parent
        delta = len(blob) - old_len
        self.data[at:at + old_len] = bytes(blob)
        for off, length in chain:
            struct.pack_into('<I', self.data, off + 8, length + delta)
        self._dirty()
        return delta

    def rename_stringid(self, old, new):
        """Rename every `tgsi` string id, growing the chunk and each of its ancestors.

        The name is length-prefixed, so 'default' -> 'standard' is one byte longer and
        every enclosing chunk has to grow with it or the file stops parsing.
        """
        want, changed = old.encode('latin1'), 0
        while True:
            at, target = 0, None
            while True:
                at = self.data.find(want, at)
                if at < 0:
                    break
                head = at - 12
                if head >= 0 and self._marker(head) == 'tgsi'                         and struct.unpack_from('<I', self.data, head + 8)[0] == len(old):
                    target = head
                    break
                at += 1
            if target is None:
                return changed
            delta = len(new) - len(old)
            chain = self._chain_to(target + 12)
            self.data[target + 12:target + 12 + len(old)] = new.encode('latin1')
            struct.pack_into('<I', self.data, target + 8, len(new))
            for off, _mk, length in chain[:-1] if chain and chain[-1][0] == target else chain:
                if off != target:
                    struct.pack_into('<I', self.data, off + 8, length + delta)
            self._dirty()
            changed += 1

    def save(self, path=None):
        path = path or self.path
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        io.open(path, 'wb').write(bytes(self.data))
        return path


if __name__ == '__main__':
    import sys
    t = Tag(sys.argv[1])
    ok, covered, total = t.check()
    ns = t.nodes()
    kinds = {}
    for n in ns:
        kinds[n.marker] = kinds.get(n.marker, 0) + 1
    print('%s  group %r  %d bytes' % (os.path.basename(t.path), t.group, total))
    print('tree spans the file: %s (%d of %d)' % (ok, covered, total))
    print('chunks: %s' % kinds)
    refs = t.references()
    print('%d reference(s):' % len(refs))
    for off, grp, path in refs:
        print('   %#08x  %-6s %s' % (off, grp, path))
