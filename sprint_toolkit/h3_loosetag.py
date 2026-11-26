r"""Read, edit and rewrite Halo 3 / ODST Editing Kit tag files BY THEIR OWN LAYOUT.

`h3tag.py` treats a tag file as a tree of chunks and finds children by scanning for a
run of chunks that ends where the parent does. That is enough to swap a reference, but
not to ADD a block element: the raw field data and the child chunks of a block sit side
by side, and only the field definitions say where one stops.

Every EK tag file carries those definitions itself. The `blay` chunk holds a complete
layout -- strings, field types, fields, structs, blocks, arrays -- for the tag group at
the version it was saved with, so a file can be decoded without any outside plugin:

    0x00  0x40-byte header (group 4cc at 0x30, 'BLAM' at 0x3C)
    0x40  'tag!'
            'blay'  2      ff ff ff ff, layout GUID, then 14 u32:
                           version, ROOT BLOCK index, string bytes, string offsets,
                           string lists, custom search names, data defs, array defs,
                           field types, fields, structs, blocks, resources, interops
                    'tgly' 3  str* sz+x sz[] csbn dtnm arr! tgft gras blv2 rcv2 ]==[ stv2
            'bdat'  1      the root block

The body (`bdat`) is chunks too, each a reversed 4cc, a u32 and a u32 length:

  tgbl  a block.      payload: u32 count, u32 POD flag (1 when the element struct has
                      no field that needs a chunk), count x struct-size raw records,
                      then -- unless POD -- one `tgst` per element.
  tgst  a struct.     header u32 = its own length. Payload: one chunk per field that
                      needs one, in field order: struct -> tgst, block -> tgbl,
                      tag reference -> tgrf, string id -> tgsi, data -> tgda, ...
  tgrf  a reference.  payload: group 4cc (reversed) + path, no terminator; empty = null.
                      The 16 raw bytes in the record are group, 0, path length, -1.
  tgsi  a string id.  payload: the string, no terminator.  Raw record value: 0.

A block FIELD's 12 raw bytes in its parent's record are (count, 0, 0): growing a nested
block means rewriting the parent record too. The parser checks every one against its
tgbl, and `serialize()` writes them back from the element lists (`Struct.sync`).

Measured on the ODST kit (2026-11-26): every scenario and resource tag of h100 and sc150
round-trips byte for byte. One oddity: scenario_effect_scenery_block elements carry one
extra empty `tgst` after their last field; it is kept as-is (`Struct.extra`).

    t = LooseTag(path)
    pal = t.root['weapon palette']          # a Block
    t.save(path)                            # byte-identical when nothing changed
"""
import io
import os
import struct

HEADER = 0x40


def _chunk_at(d, p):
    mk = bytes(d[p:p + 4])[::-1].decode('latin1')
    a, ln = struct.unpack_from('<II', d, p + 4)
    return mk, a, ln


def _pack_chunk(marker, a, payload):
    return marker[::-1].encode('latin1') + struct.pack('<II', a, len(payload)) + payload


class Layout(object):
    """The field definitions a tag file carries in its `blay` chunk."""

    def __init__(self, d):
        if bytes(d[0x4C:0x50]) != b'yalb':
            raise ValueError('no blay chunk at 0x4C')
        p = 0x4C + 12
        vals = struct.unpack_from('<14I', d, p + 20)
        self.version, self.root_block = vals[0], vals[1]
        tg = p + 0x4C
        if bytes(d[tg:tg + 4]) != b'ylgt':
            raise ValueError('no tgly chunk')
        end = tg + 12 + struct.unpack_from('<I', d, tg + 8)[0]
        sub, q = {}, tg + 12
        while q < end:
            mk, a, ln = _chunk_at(d, q)
            sub[mk] = (q + 12, ln)
            q += 12 + ln
        so, sl = sub['str*']
        strings = bytes(d[so:so + sl])

        def s(o):
            return strings[o:strings.index(b'\0', o)].decode('latin1')

        def rows(mk, n):
            o, l = sub[mk]
            return [struct.unpack_from('<%dI' % n, d, o + i) for i in range(0, l, 4 * n)]
        self.types = [(s(a), b, c) for a, b, c in rows('tgft', 3)]      # name, size, needs chunk
        self.fields = [(s(a), b, c) for a, b, c in rows('gras', 3)]     # name, type, definition
        self.blocks = [(s(a), b, c) for a, b, c in rows('blv2', 3)]     # name, max count, struct
        self.arrays = [(s(a), b, c) for a, b, c in rows('arr!', 3)]     # name, count, struct
        o, l = sub['stv2']
        self.structs = [(s(struct.unpack_from('<I', d, o + i + 16)[0]),
                         struct.unpack_from('<I', d, o + i + 20)[0]) for i in range(0, l, 24)]
        offs = [r[0] for r in rows('sz+x', 1)]
        self.string_lists = [(s(a), [s(offs[c + k]) for k in range(b)])
                             for a, b, c in rows('sz[]', 3)]
        self._fields, self._size, self._pod = {}, {}, {}

    def struct_fields(self, si):
        """[(name, type name, type size, needs chunk, definition index)] of struct si."""
        out = self._fields.get(si)
        if out is None:
            out, j = [], self.structs[si][1]
            while True:
                nm, ti, di = self.fields[j]
                tn, tsz, flag = self.types[ti]
                if tn == 'terminator X':
                    break
                out.append((nm, tn, tsz, flag, di))
                j += 1
            self._fields[si] = out
        return out

    def field_size(self, f):
        nm, tn, tsz, flag, di = f
        if tn == 'struct':
            return self.struct_size(di)
        if tn == 'array':
            return self.arrays[di][1] * self.struct_size(self.arrays[di][2])
        if tn in ('pad', 'skip', 'useless pad'):
            return di
        return tsz

    def struct_size(self, si):
        if si not in self._size:
            self._size[si] = sum(self.field_size(f) for f in self.struct_fields(si))
        return self._size[si]

    def is_pod(self, si):
        """True when no field of the struct (directly) needs a chunk."""
        if si not in self._pod:
            self._pod[si] = not any(f[3] for f in self.struct_fields(si))
        return self._pod[si]

    def offset_of(self, si, name):
        off = 0
        for f in self.struct_fields(si):
            if f[0] == name:
                return off, f
            off += self.field_size(f)
        raise KeyError('%s has no field %r' % (self.structs[si][0], name))

    def block_index(self, name):
        hits = [i for i, b in enumerate(self.blocks) if b[0] == name]
        if len(hits) != 1:
            raise KeyError('block %r: %d matches' % (name, len(hits)))
        return hits[0]


class Chunk(object):
    """A chunk kept as bytes (tag reference, string id, data, anything opaque)."""
    __slots__ = ('marker', 'a', 'payload')

    def __init__(self, marker, a, payload):
        self.marker, self.a, self.payload = marker, a, bytes(payload)

    def serialize(self):
        return _pack_chunk(self.marker, self.a, self.payload)

    # tag reference helpers
    def ref(self):
        if self.marker != 'tgrf':
            raise TypeError('not a tag reference: %s' % self.marker)
        if not self.payload:
            return None, ''
        return self.payload[:4][::-1].decode('latin1'), self.payload[4:].decode('latin1')

    def text(self):
        return self.payload.decode('latin1')


class Struct(object):
    """One struct instance: its raw record (a view into the owner's raw bytes) and its
    chunk children in field order. `owner_raw` is the bytearray the record lives in."""

    def __init__(self, tag, si, owner_raw, at):
        self.tag, self.si, self.owner_raw, self.at = tag, si, owner_raw, at
        self.subs = {}          # field name -> Struct | Block | Chunk
        self.order = []         # field names that carry a chunk, in order
        self.extra = []         # trailing chunks the layout does not name
        self.a = None

    @property
    def L(self):
        return self.tag.layout

    @property
    def name(self):
        return self.L.structs[self.si][0]

    @property
    def size(self):
        return self.L.struct_size(self.si)

    def raw(self):
        return bytes(self.owner_raw[self.at:self.at + self.size])

    def __getitem__(self, name):
        if name in self.subs:
            return self.subs[name]
        return self.get(name)

    def field(self, name):
        return self.L.offset_of(self.si, name)

    def get(self, name):
        off, f = self.field(name)
        tn = f[1]
        p = self.at + off
        fmt = {'short block index': '<h', 'custom short block index': '<h', 'short integer': '<h',
               'long integer': '<i', 'long block index': '<i', 'char block index': '<b',
               'char integer': '<b', 'real': '<f', 'long flags': '<I', 'word flags': '<H',
               'byte flags': '<B', 'long enum': '<i', 'short enum': '<h', 'char enum': '<b',
               'word block flags': '<H', 'long block flags': '<I', 'string id': '<I',
               'tag': '<4s', 'real fraction': '<f', 'angle': '<f'}.get(tn)
        if fmt:
            v = struct.unpack_from(fmt, self.owner_raw, p)[0]
            return v[::-1].decode('latin1') if tn == 'tag' else v
        if tn in ('real point 3d', 'real euler angles 3d', 'real vector 3d'):
            return struct.unpack_from('<3f', self.owner_raw, p)
        if tn in ('string', 'long string'):
            b = bytes(self.owner_raw[p:p + f[2]])
            return b.split(b'\0', 1)[0].decode('latin1')
        raise TypeError('no reader for %s %s' % (tn, name))

    def set(self, name, value):
        off, f = self.field(name)
        tn = f[1]
        fmt = {'short block index': '<h', 'custom short block index': '<h', 'short integer': '<h',
               'long integer': '<i', 'long block index': '<i', 'char block index': '<b',
               'char integer': '<b', 'real': '<f', 'long flags': '<I', 'word flags': '<H',
               'byte flags': '<B', 'long enum': '<i', 'short enum': '<h', 'char enum': '<b',
               'word block flags': '<H', 'long block flags': '<I'}.get(tn)
        if fmt is None:
            raise TypeError('no writer for %s %s' % (tn, name))
        struct.pack_into(fmt, self.owner_raw, self.at + off, value)

    def set_ref(self, name, group, path):
        """Point the tag reference field `name` at group/path (raw record AND chunk)."""
        off, f = self.field(name)
        if f[1] != 'tag reference':
            raise TypeError('%s is a %s' % (name, f[1]))
        p = self.at + off
        if group is None:
            struct.pack_into('<4sIii', self.owner_raw, p, b'\xff\xff\xff\xff', 0, 0, -1)
            self.subs[name] = Chunk('tgrf', 0, b'')
        else:
            g = group.encode('latin1')[::-1]
            struct.pack_into('<4sIii', self.owner_raw, p, g, 0, len(path), -1)
            self.subs[name] = Chunk('tgrf', 0, g + path.encode('latin1'))

    def sync(self):
        """Write each nested block's element count into this record (a block field's
        12 raw bytes are count, 0, 0), all the way down."""
        for n in self.order:
            sub = self.subs[n]
            if isinstance(sub, Block):
                off, f = self.field(n)
                struct.pack_into('<I', self.owner_raw, self.at + off, len(sub.elements))
                for e in sub.elements:
                    e.sync()
            elif isinstance(sub, Struct):
                sub.sync()

    def serialize(self):
        body = b''.join(self.subs[n].serialize() for n in self.order)
        body += b''.join(c.serialize() for c in self.extra)
        return _pack_chunk('tgst', len(body), body)


class Block(object):
    """A block: a list of Struct elements whose raw records live in `self.raw`."""

    def __init__(self, tag, bi):
        self.tag, self.bi = tag, bi
        self.raw = bytearray()
        self.elements = []
        self.pod_flag = None

    @property
    def L(self):
        return self.tag.layout

    @property
    def name(self):
        return self.L.blocks[self.bi][0]

    @property
    def si(self):
        return self.L.blocks[self.bi][2]

    @property
    def max_count(self):
        return self.L.blocks[self.bi][1]

    def __len__(self):
        return len(self.elements)

    def __iter__(self):
        return iter(self.elements)

    def __getitem__(self, i):
        return self.elements[i]

    def _rebind(self):
        size = self.L.struct_size(self.si)
        for i, e in enumerate(self.elements):
            e.owner_raw, e.at = self.raw, i * size
            e._rebind_children()

    def append_copy(self, template):
        """Append a deep copy of `template` (an element of a block with the same
        definition, possibly in another tag) and return it."""
        if len(self.elements) >= self.max_count:
            raise ValueError('%s is full (%d)' % (self.name, self.max_count))
        if template.L.structs[template.si][0] != self.L.structs[self.si][0] or \
                template.size != self.L.struct_size(self.si):
            raise ValueError('template %s does not fit %s' % (template.name, self.name))
        self.raw += template.raw()
        e = _clone_struct(template, self.tag, self.si, self.raw, len(self.raw) - template.size)
        self.elements.append(e)
        return e

    def append_new(self):
        """Append a DEFAULT element: zeroed record, null tag references, empty string
        ids and blocks -- the shape a fresh Guerilla row has -- and return it."""
        if len(self.elements) >= self.max_count:
            raise ValueError('%s is full (%d)' % (self.name, self.max_count))
        size = self.L.struct_size(self.si)
        at = len(self.raw)
        self.raw += bytes(size)
        e = _default_struct(self.tag, self.si, self.raw, at)
        self.elements.append(e)
        return e

    def serialize(self):
        pod = self.L.is_pod(self.si)
        flag = self.pod_flag if self.pod_flag is not None else int(pod)
        body = struct.pack('<II', len(self.elements), flag) + bytes(self.raw)
        if not pod:
            body += b''.join(e.serialize() for e in self.elements)
        return _pack_chunk('tgbl', 0, body)


def _rebind_children(self):
    for n in self.order:
        sub = self.subs[n]
        if isinstance(sub, Struct):
            off, f = self.field(n)
            sub.owner_raw, sub.at = self.owner_raw, self.at + off
            sub._rebind_children()


Struct._rebind_children = _rebind_children


def _default_struct(tag, si, owner_raw, at):
    L = tag.layout
    e = Struct(tag, si, owner_raw, at)
    off = 0
    for f in L.struct_fields(si):
        nm, tn, tsz, flag, di = f
        if tn == 'struct':
            e.subs[nm] = _default_struct(tag, di, owner_raw, at + off)
            e.order.append(nm)
        elif tn == 'block':
            b = Block(tag, di)
            e.subs[nm] = b
            e.order.append(nm)
        elif tn == 'tag reference':
            struct.pack_into('<4sIii', owner_raw, at + off, b'\xff\xff\xff\xff', 0, 0, -1)
            e.subs[nm] = Chunk('tgrf', 0, b'')
            e.order.append(nm)
        elif tn == 'string id':
            e.subs[nm] = Chunk('tgsi', 0, b'')
            e.order.append(nm)
        elif flag:
            raise TypeError('no default for a %s field (%s.%s)' % (tn, L.structs[si][0], nm))
        off += L.field_size(f)
    return e


def _clone_struct(src, tag, si, owner_raw, at):
    e = Struct(tag, si, owner_raw, at)
    e.order = list(src.order)
    e.extra = [Chunk(c.marker, c.a, c.payload) for c in src.extra]
    for n in src.order:
        sub = src.subs[n]
        if isinstance(sub, Struct):
            off, f = src.field(n)
            e.subs[n] = _clone_struct(sub, tag, f[4], owner_raw, at + off)
        elif isinstance(sub, Block):
            b = Block(tag, tag.layout.block_index(sub.name))
            b.pod_flag = sub.pod_flag
            b.raw = bytearray(sub.raw)
            size = sub.L.struct_size(sub.si)
            for i, el in enumerate(sub.elements):
                b.elements.append(_clone_struct(el, tag, b.si, b.raw, i * size))
            e.subs[n] = b
        else:
            e.subs[n] = Chunk(sub.marker, sub.a, sub.payload)
    return e


class LooseTag(object):
    def __init__(self, path):
        self.path = path
        d = io.open(path, 'rb').read()
        self.header = d[:HEADER]
        self.group = d[0x30:0x34][::-1].decode('latin1')
        self.layout = Layout(d)
        mk, self.tag_a, ln = _chunk_at(d, HEADER)
        if mk != 'tag!' or HEADER + 12 + ln > len(d):
            raise ValueError('%s: no tag! chunk at 0x40' % path)
        tag_end = HEADER + 12 + ln
        q = HEADER + 12
        mk, a, ln = _chunk_at(d, q)
        if mk != 'blay':
            raise ValueError('blay expected, got %r' % mk)
        self.blay = d[q:q + 12 + ln]
        q += 12 + ln
        mk, self.bdat_a, ln = _chunk_at(d, q)
        if mk != 'bdat':
            raise ValueError('bdat expected, got %r' % mk)
        bend = q + 12 + ln
        self._d = d
        self.root_block, e = self._block(q + 12, self.layout.root_block)
        if e != bend:
            raise ValueError('root block ends %#x, bdat %#x' % (e, bend))
        if bend != tag_end:
            raise ValueError('bdat ends %#x, tag! %#x' % (bend, tag_end))
        # Chunks AFTER tag! ('want' on tags untouched since 2009; a Sapien / Guerilla
        # save drops it) are kept as they are.
        self.tail = []
        q = tag_end
        while q < len(d):
            mk, a, ln = _chunk_at(d, q)
            self.tail.append(Chunk(mk, a, d[q + 12:q + 12 + ln]))
            q += 12 + ln
        if q != len(d):
            raise ValueError('trailing chunks overrun the file')
        del self._d
        self.root = self.root_block[0]

    # --- parsing ---
    def _block(self, p, bi):
        d = self._d
        mk, a, ln = _chunk_at(d, p)
        if mk != 'tgbl':
            raise ValueError('tgbl expected at %#x, got %r' % (p, mk))
        pay, end = p + 12, p + 12 + ln
        cnt, flag = struct.unpack_from('<II', d, pay)
        b = Block(self, bi)
        b.pod_flag = flag
        si = b.si
        size = self.layout.struct_size(si)
        b.raw = bytearray(d[pay + 8:pay + 8 + cnt * size])
        if len(b.raw) != cnt * size or pay + 8 + cnt * size > end:
            raise ValueError('%s: %d x %d raw overflows at %#x' % (b.name, cnt, size, p))
        q = pay + 8 + cnt * size
        pod = self.layout.is_pod(si)
        for i in range(cnt):
            e = Struct(self, si, b.raw, i * size)
            if not pod:
                q = self._struct(q, e)
            b.elements.append(e)
        if q != end:
            raise ValueError('%s at %#x: children end %#x, block %#x' % (b.name, p, q, end))
        return b, end

    def _struct(self, p, st):
        d = self._d
        mk, a, ln = _chunk_at(d, p)
        if mk != 'tgst':
            raise ValueError('tgst expected at %#x for %s, got %r' % (p, st.name, mk))
        st.a = a
        q, end = p + 12, p + 12 + ln
        off = 0
        for f in self.layout.struct_fields(st.si):
            nm, tn, tsz, flag, di = f
            fs = self.layout.field_size(f)
            if tn == 'struct':
                sub = Struct(self, di, st.owner_raw, st.at + off)
                q = self._struct(q, sub)
                st.subs[nm] = sub
                st.order.append(nm)
            elif tn == 'block':
                sub, q = self._block(q, di)
                rawn = struct.unpack_from('<I', st.owner_raw, st.at + off)[0]
                if rawn != len(sub.elements):
                    raise ValueError('%s.%s: record says %d elements, block has %d'
                                     % (st.name, nm, rawn, len(sub.elements)))
                st.subs[nm] = sub
                st.order.append(nm)
            elif tn == 'array':
                if not self.layout.is_pod(self.layout.arrays[di][2]):
                    raise ValueError('array %s of a non-POD struct: not decoded yet' % nm)
            elif flag:
                mk2, a2, ln2 = _chunk_at(d, q)
                want = {'tag reference': 'tgrf', 'string id': 'tgsi'}.get(tn)
                if want and mk2 != want:
                    raise ValueError('%s.%s (%s): %r at %#x' % (st.name, nm, tn, mk2, q))
                st.subs[nm] = Chunk(mk2, a2, d[q + 12:q + 12 + ln2])
                st.order.append(nm)
                q += 12 + ln2
            off += fs
        while q < end:
            mk2, a2, ln2 = _chunk_at(d, q)
            st.extra.append(Chunk(mk2, a2, d[q + 12:q + 12 + ln2]))
            q += 12 + ln2
        if q != end:
            raise ValueError('%s at %#x: ends %#x, chunk %#x' % (st.name, p, q, end))
        return end

    # --- writing ---
    def serialize(self):
        for e in self.root_block.elements:
            e.sync()
        bdat = _pack_chunk('bdat', self.bdat_a, self.root_block.serialize())
        return (self.header + _pack_chunk('tag!', self.tag_a, self.blay + bdat)
                + b''.join(c.serialize() for c in self.tail))

    def save(self, path=None):
        path = path or self.path
        data = self.serialize()
        tmp = path + '.tmp_h3lt'
        io.open(tmp, 'wb').write(data)
        LooseTag(tmp)                       # must parse back before it replaces anything
        os.replace(tmp, path)
        return path


def roundtrip(path):
    """True when parse + serialize gives the file back byte for byte."""
    with io.open(path, 'rb') as fh:
        orig = fh.read()
    return LooseTag(path).serialize() == orig


if __name__ == '__main__':
    import sys
    for p in sys.argv[1:]:
        t = LooseTag(p)
        ok = t.serialize() == io.open(p, 'rb').read()
        print('%-60s %s  root %s  round trip %s' % (os.path.basename(p), t.group,
                                                    t.root.name, 'OK' if ok else 'DIFFERS'))
