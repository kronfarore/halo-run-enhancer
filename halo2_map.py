# halo2_map.py — parser for Halo 2 MCC (.map) cache files.
#
# Halo 2 MCC is a *second-generation* Blam cache, fundamentally different from
# the Halo 1 MCC format in halo_map.py:
#   * The campaign maps ship UNCOMPRESSED on disk; other maps (e.g. the
#     tutorial) use the "Saber" chunked-deflate scheme, which this handles too.
#   * Tags are indexed via a meta header + tag table (no 'sgat').
#   * Pointers inside tag data are converted:  file = metaOffset + P - mask.
#
# The format details were taken from Assembly (XboxChaos/Assembly),
# src/Blamite/Blam/SecondGen/*.  Layout offsets match Assembly's
# Formats/Halo2MCC/LayoutsU1 (U1 header) + Layouts (Core meta/tag structs).
#
# Read and write are both implemented: field read/apply, path-based tag lookup
# via the file-name table, and a checksum-refreshing save() for uncompressed
# maps (re-chunking/recompression for compressed maps is not implemented).

import array
import struct
import zlib

import halo_map as hm   # reuse Plugin, TYPE_FMT, FLOAT_TYPES, OP_FUNCS, split_tag


class Halo2Map:
    """Parsed Halo 2 MCC cache, decompressed in memory. Supports read, field
    edit, and (for uncompressed maps) save with a refreshed checksum."""

    HEADER_SIZE = 0x380
    SEGMENT_ALIGN = 0x1000   # tag-data / meta segment sizes must stay 0x1000-aligned

    def __init__(self, path):
        self.path = str(path)
        with open(path, 'rb') as f:
            raw = f.read()
        if raw[:4] != b'daeh':
            raise ValueError("Not a Halo map (missing 'head' magic)")
        if len(raw) < self.HEADER_SIZE:
            raise ValueError("File too small to be a Halo 2 map")
        self.compressed = self._is_compressed(raw)
        self.data = self._decompress(raw) if self.compressed else bytearray(raw)
        self._parse_header()
        self._parse_tags()

    # Detect compression the way Assembly's AnalyzeCache does: an uncompressed
    # map already has its meta header (magic 'tags') at the meta offset.
    TAGS_MAGIC = 0x74616773  # 'tags'

    @classmethod
    def _is_compressed(cls, raw):
        def u(o):
            return struct.unpack_from('<I', raw, o)[0]
        meta_off = u(0x10)
        if meta_off == 0 or meta_off + 0x20 > len(raw):
            return True
        return u(meta_off + 0x1C) != cls.TAGS_MAGIC

    # --- low-level (decompressed image) ---
    def u32(self, o):
        return struct.unpack_from('<I', self.data, o)[0]

    def i32(self, o):
        return struct.unpack_from('<i', self.data, o)[0]

    def resolve_stringid(self, sid):
        """Resolve a Halo 2 stringID to its string. H2 classic uses direct-index IDs
        (no namespaces): the low 16 bits are the global index into the string table,
        whose blob/count/index-array pointers are real file offsets in the header
        (count @0x30, blob @0x34, index array @0x3C). Returns None on failure."""
        if not hasattr(self, '_sid'):
            try:
                cnt = self.u32(0x30)
                blob = self.u32(0x34)
                idx = self.u32(0x3C)
                self._sid = (cnt, blob, idx) if (0 < idx < blob < len(self.data) and cnt > 0) else None
            except Exception:
                self._sid = None
        if not self._sid:
            return None
        cnt, blob, idx = self._sid
        i = sid & 0xFFFF
        if not (0 <= i < cnt):
            return None
        try:
            off = struct.unpack_from('<i', self.data, idx + i * 4)[0]
            if off < 0:
                return None
            p = blob + off
            return self.data[p:self.data.index(b'\x00', p)].decode('latin1')
        except (ValueError, struct.error):
            return None

    def _cstr(self, o):
        end = self.data.index(b'\x00', o)
        return bytes(self.data[o:end]).decode('latin1')

    # --- decompression (h2mcc "Saber" chunked deflate) ---
    # Mirrors Assembly SecondGenSaberZLib.DecompressCache: the header stays raw,
    # then each chunk is [2-byte marker 0x1528][raw DEFLATE] and decompresses to
    # up to 0x40000 bytes. A negative chunk size is "faux compression" (a raw
    # copy of -size bytes). Some maps (e.g. the tutorial) are plain zlib instead,
    # so we fall back to a zlib read at the chunk start.
    @classmethod
    def _decompress(cls, raw):
        def u(o):
            return struct.unpack_from('<I', raw, o)[0]
        decomp_size = u(0x8)
        chunk_size = u(0x308) or 0x40000
        tbl_off = u(0x310)
        tbl_cnt = u(0x314)
        if tbl_cnt == 0 or tbl_off == 0 or tbl_off >= len(raw):
            raise ValueError("Unsupported / uncompressed Halo 2 map header revision")
        out = bytearray(raw[:cls.HEADER_SIZE])       # header stays raw
        for i in range(tbl_cnt):
            csize, coff = struct.unpack_from('<ii', raw, tbl_off + i * 8)
            if csize == 0:
                break
            if csize < 0:                            # faux compression: raw copy
                out += raw[coff:coff - csize]
                continue
            blob = raw[coff:coff + csize]
            try:                                     # Saber: skip marker, raw deflate
                out += zlib.decompress(blob[2:], -15, chunk_size)
            except zlib.error:                       # fallback: plain zlib stream
                out += zlib.decompress(blob, 15, chunk_size)
        if len(out) < decomp_size:
            out += b'\x00' * (decomp_size - len(out))
        return bytearray(out[:decomp_size])

    # --- header (U1 layout) ---
    def _parse_header(self):
        self.file_size = self.u32(0x8)
        self.meta_offset = self.u32(0x10)
        self.meta_size = self.u32(0x14)
        self.internal_name = self._cstr(0xB0)
        self.scenario_name = self._cstr(0xD0)
        self.mask = self.u32(0x2D0)                  # meta offset mask (0 on MCC)
        self.tag_table_size = self.u32(0x2D4)        # size of the tag-index segment
        self.tag_data_size = self.u32(0x2D8)
        # tag data segment begins right after the tag index segment
        self.tag_data_offset = self.meta_offset + self.tag_table_size

    # --- pointer conversion: virtual P -> file offset in decompressed image ---
    def p2o(self, ptr):
        return (self.meta_offset + ptr - self.mask) & 0xFFFFFFFF

    # --- meta header + tag table ---
    def _parse_tags(self):
        mh = self.meta_offset
        self.tag_group_tbl = mh + self.u32(mh + 0x0)
        self.num_groups = self.i32(mh + 0x4)
        self.tag_tbl = mh + self.u32(mh + 0x8)
        self.scenario_index = self.u32(mh + 0xC) & 0xFFFF
        self.globals_index = self.u32(mh + 0x10) & 0xFFFF
        self.num_tags = self.i32(mh + 0x18)

        self.tags = []
        for i in range(self.num_tags):
            e = self.tag_tbl + i * 0x10
            gm = self.u32(e)
            cls = bytes([(gm >> 24) & 0xFF, (gm >> 16) & 0xFF,
                         (gm >> 8) & 0xFF, gm & 0xFF]).decode('latin1')
            addr = self.u32(e + 8)
            self.tags.append({
                'index': i, 'class': cls,
                'datum': self.u32(e + 4),
                'addr': addr,                        # pointer (P), not yet file off
                'base': self.p2o(addr) if addr not in (0, 0xFFFFFFFF) else None,
                'size': self.i32(e + 0xC),
                'name': None,
            })
        self._parse_tag_names()

    def _parse_tag_names(self):
        """Assign each tag its path from the file-name table: a blob of C-strings
        (`FileNameData`) indexed by a parallel int32 offset table, one per tag."""
        fn_count = self.u32(0x20)
        fn_data = self.u32(0x24)
        fn_index = self.u32(0x2C)
        if fn_data == 0 or fn_index == 0:
            return
        for i in range(min(fn_count, len(self.tags))):
            try:
                self.tags[i]['name'] = self._cstr(fn_data + self.u32(fn_index + i * 4))
            except Exception:
                pass

    # --- tag lookups ---
    def tag(self, index):
        return self.tags[index] if 0 <= index < len(self.tags) else None

    def scenario_tag(self):
        return self.tag(self.scenario_index)

    def globals_tag(self):
        return self.tag(self.globals_index)

    def tags_of_class(self, cls):
        return [t for t in self.tags if t['class'] == cls]

    # --- reflexive walk (mirrors halo_map.HaloMap.follow, magic via p2o) ---
    def follow(self, base, block_offsets, block_sizes=None, index=0):
        """Walk a reflexive chain to a leaf struct. Returns None if any block on
        the path is empty / too short for the requested element (H2 variant tags
        often have unpopulated blocks — reading those would yield garbage)."""
        cur = base
        n = len(block_offsets)
        for i, refl in enumerate(block_offsets):
            count = self.i32(cur + refl)             # [count@0][ptr@4]
            ptr = self.u32(cur + refl + 4)
            idx = index if i == n - 1 else 0
            if ptr == 0 or count <= idx:
                return None
            size = block_sizes[i] if block_sizes else 0
            cur = self.p2o(ptr) + idx * size
        return cur

    def follow_all(self, base, block_offsets, block_sizes=None, index=0):
        """Like `follow`, but returns EVERY leaf struct selected by `index` (an
        int, 'all', or a per-level list — see halo_map.normalize_index_spec).
        Enables reaching a doubly-nested field at every element, e.g. H2
        'Rate Of Fire' under Firing Pattern Properties[i] -> Firing Patterns[j].
        Returns [] when nothing is populated on the requested path."""
        n = len(block_offsets)
        if n == 0:
            return [base]
        sel = hm.normalize_index_spec(index, n)
        cur = [base]
        for i, refl in enumerate(block_offsets):
            size = block_sizes[i] if block_sizes else 0
            nxt = []
            for c in cur:
                count = self.i32(c + refl)
                ptr = self.u32(c + refl + 4)
                if ptr == 0 or count <= 0:
                    continue
                arr = self.p2o(ptr)
                s = sel[i]
                idxs = range(count) if s == 'all' else ([s] if 0 <= s < count else [])
                for idx in idxs:
                    nxt.append(arr + idx * size)
            cur = nxt
        return cur

    def read_tag_field(self, tag_base, field, plugin, block=None, index=0, nth=0):
        """Read a plugin field from a tag whose data starts at file `tag_base`.
        With an enumerating `index` ('all'/list) it reports the FIRST populated
        element (a representative value for display)."""
        fld = plugin.find(field, block, nth)
        if not fld:
            return None
        try:
            leaves = self.follow_all(tag_base, fld['block_offsets'],
                                     fld.get('block_sizes'), index)
            base = leaves[0] if leaves else None
            if base is None:
                return None
            fmt, _ = hm.TYPE_FMT[fld['type']]
            raw = struct.unpack_from(fmt, self.data, base + fld['offset'])[0]
            return hm.raw_to_display(fld['type'], raw)
        except Exception:
            return None

    def write_tag_field(self, tag_base, field, value, plugin, block=None, index=0, nth=0):
        """Write a value into a tag's field (in memory; call save() to persist).
        Returns the previous value, or None if unresolved / out of range."""
        fld = plugin.find(field, block, nth)
        if not fld:
            return None
        base = self.follow(tag_base, fld['block_offsets'],
                           fld.get('block_sizes'), index)
        if base is None:
            return None
        try:
            fmt, _ = hm.TYPE_FMT[fld['type']]
            ftype = fld['type']
            off = base + fld['offset']
            old = hm.raw_to_display(ftype, struct.unpack_from(fmt, self.data, off)[0])
            value = float(value) if (ftype in hm.FLOAT_TYPES or ftype in hm.ANGLE_TYPES) else int(round(value))
            struct.pack_into(fmt, self.data, off, hm.display_to_raw(ftype, value))
            return old
        except Exception:
            return None

    def apply_tag_field(self, tag_base, field, op, value, plugin, block=None, index=0, nth=0,
                        scale=1.0, offset=0.0, clamp_min=None, clamp_max=None):
        """Apply an operator to a tag field. Returns a result dict mirroring
        halo_map.HaloMap.apply_field entries (ok/old/new or ok=False/reason)."""
        base_r = {'field': field}
        fld = plugin.find(field, block, nth)
        if not fld:
            return {**base_r, 'ok': False, 'reason': 'field not found in plugin'}
        try:
            leaves = self.follow_all(tag_base, fld['block_offsets'],
                                     fld.get('block_sizes'), index)
            if not leaves:
                return {**base_r, 'ok': False, 'reason': 'empty block in this tag'}
            fmt, _ = hm.TYPE_FMT[fld['type']]
            ftype = fld['type']
            is_float = ftype in hm.FLOAT_TYPES or ftype in hm.ANGLE_TYPES
            first_old = first_new = None
            for base in leaves:                     # patch every selected element
                off = base + fld['offset']
                old = hm.raw_to_display(ftype, struct.unpack_from(fmt, self.data, off)[0])
                # operate in display units (deg for angles), in the MEANING the
                # magnitude is expressed in, then map back (see HaloMap.apply_field)
                meaning = hm.OP_FUNCS[op](scale * old + offset, value)
                # Clamp in MEANING units, exactly as HaloMap does. Without these the
                # bounds declared in halo.json applied to Halo 1 only, and passing them
                # to this class raised "unexpected keyword argument 'clamp_min'" --
                # which broke patching for Halo 2, Halo 3 and ODST outright.
                if clamp_min is not None:
                    meaning = max(meaning, clamp_min)
                if clamp_max is not None:
                    meaning = min(meaning, clamp_max)
                new = (meaning - offset) / scale
                new = float(new) if is_float else int(round(new))
                struct.pack_into(fmt, self.data, off, hm.display_to_raw(ftype, new))
                if first_old is None:
                    first_old, first_new = old, new
            r = {**base_r, 'ok': True, 'old': first_old, 'new': first_new}
            if len(leaves) > 1:
                r['elements'] = len(leaves)
            return r
        except Exception as e:
            return {**base_r, 'ok': False, 'reason': str(e)}

    def grow_block(self, tag_base, block_offset, elem_size, new_elems):
        """Append `new_elems` (a list of elem_size-byte blocks) to the reflexive at
        tag_base+block_offset, growing count M -> M+len(new_elems).

        The block is RELOCATED to end-of-image: the existing M elements are copied
        verbatim after EOF, the new ones follow, and the reflexive is repointed
        there with the higher count. Nothing in the middle of the tag data moves, so
        every other pointer stays valid; the old element bytes are simply orphaned.
        Element bytes are copied verbatim, so any tagRefs they embed keep their
        (map-global) datums, and any child reflexive pointers keep addressing the
        unmoved child data — callers copying a subtree must fix those up themselves.

        The tag-data / meta segments must stay SEGMENT_ALIGN (0x1000) aligned or MCC
        rejects the cache ("segment size is not aligned"), so the appended region is
        padded up to a whole alignment block. Header size fields (file_size@0x8,
        meta_size@0x14, tag_data_size@0x2D8) grow by that padded delta. Returns the
        new block's file offset. save()/update_checksum must follow.

        NOTE: this restructures the map (not just values); MCC must be verified to
        load a grown map in-game."""
        if self.compressed:
            raise NotImplementedError("cannot grow a compressed map")
        if any(len(e) != elem_size for e in new_elems):
            raise ValueError("every new element must be elem_size bytes")
        if not new_elems:
            raise ValueError("no elements to append")
        count = self.i32(tag_base + block_offset)
        old_ptr = self.u32(tag_base + block_offset + 4)
        existing = b'' if count == 0 else \
            bytes(self.data[self.p2o(old_ptr):self.p2o(old_ptr) + count * elem_size])
        blob = existing + b''.join(bytes(e) for e in new_elems)
        total = count + len(new_elems)
        delta = (len(blob) + self.SEGMENT_ALIGN - 1) & ~(self.SEGMENT_ALIGN - 1)
        new_off = len(self.data)
        self.data += blob + bytearray(delta - len(blob))
        ptr = (new_off - self.meta_offset + self.mask) & 0xFFFFFFFF
        struct.pack_into('<i', self.data, tag_base + block_offset, total)      # count
        struct.pack_into('<I', self.data, tag_base + block_offset + 4, ptr)    # ptr
        self.file_size += delta
        self.meta_size += delta
        self.tag_data_size += delta
        struct.pack_into('<I', self.data, 0x8, self.file_size)
        struct.pack_into('<I', self.data, 0x14, self.meta_size)
        struct.pack_into('<I', self.data, 0x2D8, self.tag_data_size)
        return new_off

    def append_block_element(self, tag_base, block_offset, elem_size, elem_bytes):
        """Back-compat: grow an EMPTY reflexive (count 0) to a single element.
        Delegates to grow_block; kept for the init_defaults seeder."""
        count = self.i32(tag_base + block_offset)
        if count != 0:
            raise ValueError("append_block_element only supports empty blocks (count 0)")
        return self.grow_block(tag_base, block_offset, elem_size, [elem_bytes])

    # --- checksum + save ---
    def update_checksum(self):
        """Recompute the header checksum (XOR of every u32 after the header,
        final block zero-padded) and write it back at 0x2F8. Uncompressed maps
        only. Uses an `array` over a memoryview to avoid copying the whole
        (~100 MB) body and to keep the XOR loop fast."""
        mv = memoryview(self.data)[self.HEADER_SIZE:]
        whole = len(mv) - (len(mv) % 4)
        words = array.array('I')
        words.frombytes(mv[:whole])
        if array.array('I', b'\x01\x00\x00\x00')[0] != 1:   # normalize to LE
            words.byteswap()
        cs = 0
        for x in words:
            cs ^= x
        if len(mv) % 4:                                      # zero-padded tail
            cs ^= int.from_bytes(bytes(mv[whole:]).ljust(4, b'\x00'), 'little')
        struct.pack_into('<I', self.data, 0x2F8, cs)
        return cs

    def save(self, out_path=None):
        """Persist the (possibly edited) image. Uncompressed maps are written
        directly with a refreshed checksum. Compressed maps are not supported
        yet (would need re-chunking + recompression)."""
        if self.compressed:
            raise NotImplementedError(
                "save() for compressed H2 maps needs recompression; the relevant "
                "campaign maps are uncompressed and save fine.")
        self.update_checksum()
        with open(out_path or self.path, 'wb') as f:
            f.write(self.data)

    # --- HaloMap-compatible path interface (drop-in for halo_patch/dialog) ---
    def find_tags(self, cls, path):
        """Resolve a tag reference to (path, base_offset) pairs, mirroring
        halo_map.HaloMap.find_tags: a trailing '*' is a variant prefix match,
        ' & ' joins several paths, an exact path returns 0 or 1 entry. The
        singleton globals (matg) and scenario (scnr) tags resolve via the meta
        header's datum indices, since their halo.json paths are nominal (e.g.
        H1's 'scnr levels\\*' does not match H2's 'scenarios\\...' name)."""
        if cls == 'matg':
            t = self.globals_tag()
            return [(path, t['base'])] if t and t['base'] is not None else []
        if cls == 'scnr':
            t = self.scenario_tag()
            return [(path, t['base'])] if t and t['base'] is not None else []
        if ' & ' in path:
            out, seen = [], set()
            for part in path.split(' & '):
                for p, o in self.find_tags(cls, part.strip()):
                    if p not in seen:
                        seen.add(p)
                        out.append((p, o))
            return out
        if '*' in path:
            match = hm._wildcard_matcher(path)
            res = [(t['name'], t['base']) for t in self.tags
                   if t['class'] == cls and t['name'] and t['base'] is not None
                   and match(t['name'])]
            return sorted(res)
        for t in self.tags:
            if t['class'] == cls and t['name'] == path and t['base'] is not None:
                return [(t['name'], t['base'])]
        return []

    def read(self, cls, path, field, plugin, block=None, index=0, nth=0):
        tags = self.find_tags(cls, path)
        return self.read_tag_field(tags[0][1], field, plugin, block, index, nth) if tags else None

    def read_first(self, cls, path, field, plugin, block=None, index=0, nth=0):
        return self.read(cls, path, field, plugin, block, index, nth)

    def read_all(self, cls, path, field, plugin, block=None, index=0, nth=0):
        out = []
        for tpath, base in self.find_tags(cls, path):
            v = self.read_tag_field(base, field, plugin, block, index, nth)
            if v is not None:
                out.append((tpath, v))
        return out

    def read_all_leaves(self, cls, path, field, plugin, block=None, index=0, nth=0):
        """(tag_path, [value per selected leaf]) per variant tag — every element the
        index spec picks (e.g. index='all'). Mirrors halo_map.HaloMap.read_all_leaves
        so the dialog can list a collapsed effect's full per-variant/per-index spread.
        Own-tag reads only (variants with empty blocks are omitted, same as read_all)."""
        fld = plugin.find(field, block, nth)
        if not fld:
            return []
        fmt, _ = hm.TYPE_FMT[fld['type']]
        out = []
        for tpath, base in self.find_tags(cls, path):
            vals = []
            for leaf in self.follow_all(base, fld['block_offsets'], fld.get('block_sizes'), index):
                try:
                    vals.append(hm.raw_to_display(fld['type'],
                                struct.unpack_from(fmt, self.data, leaf + fld['offset'])[0]))
                except Exception:
                    pass
            if vals:
                out.append((tpath, vals))
        return out

    # 'char' Parent Character tagRef: [class magic @0x4][datum index @0x8]. A
    # variant char with an empty block inherits that block from its parent, so
    # to affect the variant we must edit whichever ancestor actually holds the
    # data. Only 'char' tags have this; other classes have no parent chain.
    _PARENT_DATUM_OFFSET = 0x8
    _CHAR_MAGIC = 0x63686172  # 'char'

    def _parent_base(self, tag_base):
        """Base offset of a char tag's Parent Character, or None."""
        try:
            if self.u32(tag_base + 0x4) != self._CHAR_MAGIC:
                return None
            datum = self.u32(tag_base + self._PARENT_DATUM_OFFSET)
        except Exception:
            return None
        if datum in (0, 0xFFFFFFFF):
            return None
        row = datum & 0xFFFF
        t = self.tag(row)
        return t['base'] if (t and t['class'] == 'char') else None

    def _data_holder(self, tag_base, plugin, field, block, index, nth, allowed):
        """The tag (by base offset) that actually stores this field's block
        element for `tag_base` — itself if its block is populated, else the
        nearest Parent Character ancestor whose block is populated. Only walks
        ancestors within `allowed` (the effect's matched tag set) so a shared
        cross-enemy parent (e.g. ai\\generic) is never edited. None if no
        in-scope tag holds the data."""
        fld = plugin.find(field, block, nth)
        if not fld:
            return None
        cur, seen = tag_base, set()
        while cur is not None and cur not in seen:
            seen.add(cur)
            if self.follow_all(cur, fld['block_offsets'], fld.get('block_sizes'), index):
                return cur
            parent = self._parent_base(cur)
            if parent is None or (allowed is not None and parent not in allowed):
                return None
            cur = parent
        return None

    def apply_field(self, cls, path, field, op, value, plugin, block=None, index=0, nth=0,
                    scale=1.0, offset=0.0, clamp_min=None, clamp_max=None):
        ref = f"{cls} {path}"
        tags = self.find_tags(cls, path)
        if not tags:
            return [{'tag': ref, 'field': field, 'ok': False,
                     'reason': 'not present in this map'}]
        # char variants inherit empty blocks from a parent; resolve each variant
        # to the ancestor that holds the data (within this enemy's tag set) and
        # apply once per unique holder — inheriting variants are then covered.
        follow_parents = (cls == 'char')
        allowed = {b for _, b in tags} if follow_parents else None
        name_by_base = {b: t for t, b in tags}
        applied = {}   # holder base -> result dict (dedup physical writes)
        results = []
        for tpath, base in tags:
            holder = self._data_holder(base, plugin, field, block, index, nth, allowed) \
                if follow_parents else base
            if holder is None:
                r = self.apply_tag_field(base, field, op, value, plugin, block, index, nth,
                                          scale, offset, clamp_min, clamp_max)
                if cls == 'char' and not r.get('ok') and r.get('reason') == 'empty block in this tag':
                    # variant inherits this block from outside its own tag set (e.g. the
                    # shared ai\generic base) — not a failure, just nothing to write here.
                    r = {**r, 'ok': True, 'skip': True, 'reason': 'inherits from base'}
                r['tag'] = f"{cls} {tpath}"
                results.append(r)
                continue
            if holder not in applied:
                applied[holder] = self.apply_tag_field(holder, field, op, value, plugin,
                                                       block, index, nth,
                                                       scale, offset,
                                                       clamp_min, clamp_max)
            hr = applied[holder]
            r = dict(hr)
            r['tag'] = f"{cls} {tpath}"
            if holder != base and hr.get('ok'):
                r['inherited_from'] = name_by_base.get(holder, '')
            results.append(r)
        return results


if __name__ == '__main__':
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else \
        r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\halo2\h2_maps_win64_dx11\01a_tutorial.map"
    m = Halo2Map(p)
    print(f"internal={m.internal_name}  scenario={m.scenario_name}")
    print(f"image={len(m.data):#x} (hdr says {m.file_size:#x})  tags={m.num_tags}")
    print(f"tag data @ {m.tag_data_offset:#x}..{m.tag_data_offset + m.tag_data_size:#x} (EOF={len(m.data):#x})")

    PLUG = r"C:\Program Files (x86)\Steam\steamapps\common\HCEEK\Assembly-1-2023-11-29-1702446457\Plugins\Halo2MCC"
    g = m.globals_tag()
    matg_pl = hm.Plugin(PLUG + r"\matg.xml")
    print("\nmatg:", g['class'], f"base={g['base']:#x}")
    for d in ("Easy", "Normal", "Hard", "Impossible"):
        print(f"  {d:10} Enemy Damage =",
              m.read_tag_field(g['base'], f"{d} Enemy Damage", matg_pl, block="Difficulty"))
    print("  Walking Speed =", m.read_tag_field(g['base'], "Walking Speed", matg_pl, block="Player Information"))

    s = m.scenario_tag()
    scnr_pl = hm.Plugin(PLUG + r"\scnr.xml")
    print("\nscnr:", s['class'], f"base={s['base']:#x}")
    for f in ("Starting Health Damage", "Starting Shield Damage"):
        print(f"  {f} =", m.read_tag_field(s['base'], f, scnr_pl, block="Player Starting Profile"))
