# halo3_map.py — parser + patcher for Halo 3 MCC (.map) cache files.
#
# Halo 3 MCC is a *third-generation* Blam cache, different again from H1
# (halo_map.py) and H2 (halo2_map.py). Confirmed on 010_jungle (both the shipped
# map and the "Cortana Begone" toolset rebuild). Format details taken from
# Assembly (XboxChaos/Assembly) Formats/Halo3MCC/LayoutsU13 + base Layouts, and
# verified empirically against the maps. LITTLE-endian on PC MCC.
#
# KEY format facts (see project_halo3_map_format memory for the full writeup):
#   * Header size 0x4000 (version 13 / Update-6+ builds). Magic 'daeh' @0.
#   * TWO address spaces:
#       - Index space (index header, tag-group table, tag table): full 64-bit
#         VAs, converted by a single delta  file = VA - idx_delta.
#       - Tag-data space (tag memory addresses AND every internal reflexive /
#         dataRef pointer): stored as (realVA >> 2). Resolve by  realVA = ptr<<2,
#         pick the memory partition containing realVA, then
#         file = partition.file_base + (realVA - partition.load). The 6 partitions
#         are contiguous in file, in order; bases are anchored off the partition
#         that holds the index header. Works for both shipped (partition-packed)
#         and toolset (near-flat) maps.
#   * Reflexive (tag block) = [count:i32][ptr:u32] (ptr is a >>2 data address).
#   * tagRef 0x10: group magic @0, datum index @0xC (low 16 bits = tag row).
#   * RETAIL maps STRIP the tag-name + stringID string tables (zeroed on disk).
#     matg/scnr still resolve (by tag-group magic); by-name tag lookup only works
#     on maps that keep names (all toolset rebuilds, incl. the Cortana Begone set).
#   * Checksum @0x360 = XOR of every u32 from 0x4000 (header end) to EOF. The
#     checksum word itself sits in the header, so it is NOT part of the XOR.
#
# Read + write are both implemented. Scalar field edits don't change layout, so
# data2off stays valid; save() refreshes the checksum. Reflexive GROWTH is not
# implemented (H3 partition/segment fixups would be involved) — value edits only.

import array
import struct

import halo_map as hm   # reuse Plugin, TYPE_FMT, FLOAT/ANGLE types, OP_FUNCS, raw/display


class Halo3Map:
    """Parsed Halo 3 MCC cache. Supports tag lookup, field read/apply, and a
    checksum-refreshing save() (value edits only; no structural growth)."""

    HEADER_SIZE = 0x4000        # version 13 (Update 6+/U9/U12/U13). v11 flights use 0x3000.
    CHECKSUM_OFF = 0x360

    def __init__(self, path):
        self.path = str(path)
        with open(path, 'rb') as f:
            self.data = bytearray(f.read())
        if self.data[:4] != b'daeh':
            raise ValueError("Not a Halo map (missing 'head' magic)")
        self._parse_header()
        self._parse_partitions()
        self._parse_index()
        self._parse_tag_names()

    # --- low-level ---
    def u32(self, o):
        return struct.unpack_from('<I', self.data, o)[0]

    def i32(self, o):
        return struct.unpack_from('<i', self.data, o)[0]

    def u64(self, o):
        return struct.unpack_from('<Q', self.data, o)[0]

    def i16(self, o):
        return struct.unpack_from('<h', self.data, o)[0]

    def _cstr(self, o):
        end = self.data.index(b'\x00', o)
        return bytes(self.data[o:end]).decode('latin1')

    # --- header ---
    def _parse_header(self):
        self.version = self.u32(0x4)
        self.file_size = self.u32(0x8)
        self.tag_buffer_offset = self.u32(0x10)
        self.virtual_size = self.u32(0x14)
        self.virt_base = self.u64(0x2E0)
        self.index_header_va = self.u64(0x2E8)
        self.build = self._cstr(0xA0)
        self.internal_name = self._cstr(0xC0)
        self.scenario_name = self._cstr(0xE0)
        self.file_tbl_count = self.i32(0x20)
        self.file_tbl_offset = self.i32(0x24)
        self.file_tbl_size = self.i32(0x28)
        self.file_idx_offset = self.i32(0x2C)
        self.str_tbl_count = self.i32(0x30)
        self.str_tbl_offset = self.i32(0x34)
        self.str_tbl_size = self.i32(0x38)
        self.str_idx_offset = self.i32(0x3C)

    # --- partitions & the >>2 tag-data pointer model ---
    def _parse_partitions(self):
        self.partitions = []
        for i in range(6):
            la = self.u64(0x300 + i * 0x10)
            sz = self.u64(0x300 + i * 0x10 + 8)
            self.partitions.append([la, sz, None])
        self._locate_index_header()
        self.idx_delta = self.index_header_va - self.index_header_off
        ap = self._part_of(self.index_header_va)
        if ap is not None:
            fbase_ap = self.index_header_off - (self.index_header_va - self.partitions[ap][0])
            pre = sum(self.partitions[j][1] for j in range(ap))
            cur = fbase_ap - pre
            for i in range(6):
                self.partitions[i][2] = cur
                cur += self.partitions[i][1]

    def _locate_index_header(self):
        # index header magic 'tags' (LE bytes 'sgat') sits at index_header+0x44.
        flat_delta = self.virt_base - self.tag_buffer_offset
        cand = self.index_header_va - flat_delta
        if 0 <= cand < len(self.data) - 0x48 and self.data[cand + 0x44:cand + 0x48] == b'sgat':
            self.index_header_off = cand
            return
        start = 0
        while True:
            i = self.data.find(b'sgat', start)
            if i < 0:
                break
            ioff = i - 0x44
            if ioff >= 0:
                ng = struct.unpack_from('<i', self.data, ioff)[0]
                nt = struct.unpack_from('<i', self.data, ioff + 0x10)[0]
                ta = self.u64(ioff + 0x18)
                if 0 < ng < 1000 and 0 < nt < 30000 and ta > 0x100000000:
                    self.index_header_off = ioff
                    return
            start = i + 1
        raise ValueError("Halo 3 index header ('tags' magic) not found")

    def _part_of(self, va):
        for i, (la, sz, _) in enumerate(self.partitions):
            if sz > 0 and la <= va < la + sz:
                return i
        return None

    def data2off(self, ptr):
        """Tag-data pointer (stored realVA>>2) -> file offset, or None if null/oob."""
        if ptr in (0, 0xFFFFFFFF):
            return None
        va = ptr << 2
        i = self._part_of(va)
        if i is None or self.partitions[i][2] is None:
            return None
        return self.partitions[i][2] + (va - self.partitions[i][0])

    def off2data(self, off):
        """Inverse of data2off: file offset -> stored (realVA>>2) pointer. For
        rewriting a reflexive pointer after relocation (unused by value edits)."""
        for la, sz, fb in self.partitions:
            if fb is not None and fb <= off < fb + sz:
                return ((la + (off - fb)) >> 2) & 0xFFFFFFFF
        return None

    def va2off(self, va):
        """Index-space (full 64-bit VA) -> file offset."""
        return va - self.idx_delta

    # --- index header / tag table ---
    def _parse_index(self):
        io = self.index_header_off
        self.n_groups = self.i32(io + 0x0)
        grp_addr = self.u64(io + 0x8)
        self.n_tags = self.i32(io + 0x10)
        tag_addr = self.u64(io + 0x18)
        # tag groups: 0x10 each — magic(4cc)@0, parent, grandparent, stringid
        go = self.va2off(grp_addr)
        self.groups = [struct.pack('>I', self.u32(go + i * 0x10)).decode('latin1')
                       for i in range(self.n_groups)]
        # tag table: 0x8 each — group idx i16@0, salt u16@2, memaddr u32@4
        to = self.va2off(tag_addr)
        self.tags = []
        for i in range(self.n_tags):
            gi = self.i16(to + i * 8)
            memaddr = self.u32(to + i * 8 + 4)
            cls = self.groups[gi] if 0 <= gi < self.n_groups else None
            self.tags.append({
                'index': i, 'class': cls, 'memaddr': memaddr,
                'base': self.data2off(memaddr), 'name': None,
            })

    # --- tag names (file/path table) ---
    def _parse_tag_names(self):
        """Populate each tag's `name` from the file/path table. Toolset maps keep it
        where the header points. Retail maps are trickier: the header's file-table
        pointer is a VIRTUAL address that on disk lands on garbage (not zeros), and
        the real table sits at a low physical offset — recovered via `_recover_retail
        _names`. If neither yields valid names, `names_stripped` is set."""
        self.names_stripped = False
        self.names_recovered = False
        blob_o = self.file_tbl_offset
        end = blob_o + self.file_tbl_size
        header_ok = not (end > len(self.data)
                         or self.data[blob_o:blob_o + 0x40] == b'\x00' * 0x40)
        if header_ok:
            idx_o = self.file_idx_offset
            for i in range(min(self.file_tbl_count, len(self.tags))):
                try:
                    so = struct.unpack_from('<i', self.data, idx_o + i * 4)[0]
                    if 0 <= so < self.file_tbl_size:
                        self.tags[i]['name'] = self._cstr(blob_o + so)
                except Exception:
                    pass
        if not self._names_look_valid():
            for t in self.tags:            # discard header-table garbage
                t['name'] = None
            if not self._recover_retail_names():
                self.names_stripped = True

    def _names_look_valid(self):
        """Retail maps leave garbage (not zeros) in the header-pointed table, so a
        zero-check isn't enough. True only if most resolved names look like real
        `objects\\...` paths (printable ASCII with a backslash)."""
        good = tot = 0
        for t in self.tags:
            if t['name'] is not None:
                tot += 1
                nm = t['name']
                if nm and '\\' in nm and all(32 <= ord(c) < 127 for c in nm):
                    good += 1
        return tot > 0 and good / tot > 0.5

    def _recover_retail_names(self):
        """Recover a retail map's real tag-name table (at a low, header-unpointed
        physical offset) via two anchors whose tag rows are known: the globals and
        scenario tag names. Solving `idx[scnr_row] - idx[matg_row] == scen_off -
        glob_off` for a candidate index-table base pins (idx_base, blob_base); then
        every tag name is read. Returns True on success."""
        d = self.data
        scnr = self._singleton('scnr')
        matg = self._singleton('matg')
        if not (scnr and matg) or not self.scenario_name or not self.internal_name:
            return False
        scnr_row, matg_row = scnr['index'], matg['index']
        scen = self.scenario_name.encode('latin1')
        glob = b'globals\\globals\x00'
        scen_occ = self._find_all(scen, 0x1000)     # skip the header copies (< 0x1000)
        glob_occ = self._find_all(glob, 0x1000)
        off_words = scnr_row - matg_row
        for gp in glob_occ:
            for sp in scen_occ:
                delta = sp - gp
                base = self._scan_index_table(gp, sp, off_words, delta, matg_row)
                if base is not None:
                    idx_base, blob_base = base
                    if self._verify_names(idx_base, blob_base, scnr_row, matg_row):
                        self._populate_names(idx_base, blob_base)
                        self.names_recovered = True
                        return True
        return False

    def _find_all(self, needle, min_off):
        out, start = [], 0
        while True:
            i = self.data.find(needle, start)
            if i < 0:
                break
            if i >= min_off:
                out.append(i)
            start = i + 1
        return out

    def _scan_index_table(self, gp, sp, off_words, delta, matg_row):
        """Scan a window for an int32 index-table position q where
        idx[q + off_words] - idx[q] == delta and idx[q] is a plausible blob offset.
        Returns (idx_base, blob_base) or None. Uses an int32 array for speed."""
        import array
        d = self.data
        L = len(d)
        lo = max(0, min(gp, sp) - 0x1000)
        lo -= lo % 4
        hi = min(L, max(gp, sp) + 0x200000)
        seg = array.array('i')
        seg.frombytes(d[lo:hi - ((hi - lo) % 4)])
        if array.array('i', b'\x01\x00\x00\x00')[0] != 1:
            seg.byteswap()
        n = len(seg)
        aoff = abs(off_words)
        for k in range(n - aoff):
            a = seg[k]
            if 0 <= a < 0x08000000 and seg[k + off_words] - a == delta:
                idx_base = lo + (k - matg_row) * 4
                blob_base = gp - a
                if idx_base >= 0 and blob_base >= 0:
                    return idx_base, blob_base
        return None

    def _verify_names(self, idx_base, blob_base, scnr_row, matg_row):
        d = self.data
        try:
            def nm(row):
                e = struct.unpack_from('<i', d, idx_base + row * 4)[0]
                if e < 0:
                    return None
                p = blob_base + e
                return d[p:d.index(b'\x00', p)].decode('latin1')
            if nm(matg_row) != 'globals\\globals' or nm(scnr_row) != self.scenario_name:
                return False
            ok = sum(1 for r in (0, 1, 100, 500, 1000, self.n_tags // 2)
                     if (nm(r) or '') and '\\' in (nm(r) or ''))
            return ok >= 3
        except Exception:
            return False

    def _populate_names(self, idx_base, blob_base):
        d = self.data
        for i in range(len(self.tags)):
            try:
                e = struct.unpack_from('<i', d, idx_base + i * 4)[0]
                if e >= 0:
                    p = blob_base + e
                    self.tags[i]['name'] = d[p:d.index(b'\x00', p)].decode('latin1')
            except Exception:
                pass

    # --- stringID blob (the debug-string table; separate from tag names) ---
    _SID_ANCHOR = b'default\x00reload_1\x00reload_2\x00chamber_1\x00chamber_2\x00'

    def _locate_stringids(self):
        """Find the stringID index array + string blob on retail maps (header
        pointers @0x34/0x3C are virtual garbage). The blob always opens with the
        engine's static set (`default\\0reload_1\\0...`), and the int32 offset array
        sits immediately before it: idx_base = blob_base - count*4. Also rebuilds the
        stripped static tail (retail zeroes those index entries but keeps the strings
        at the head of the blob). Returns True on success; caches on the instance."""
        if hasattr(self, '_sid_blob'):
            return self._sid_ok
        self._sid_ok = False
        d = self.data
        cnt = self.str_tbl_count
        p = d.find(self._SID_ANCHOR)
        if p < 1 or cnt <= 0:
            self._sid_blob = self._sid_idx = 0
            return False
        blob = p - 1                              # the leading NUL == empty string
        idx = blob - cnt * 4
        if idx < 0 or idx % 4 != 0:
            self._sid_blob = self._sid_idx = 0
            return False
        offs = list(struct.unpack_from('<%di' % cnt, d, idx))
        # trailing zeros == stripped static set; rebuild from the blob head
        strip = cnt
        while strip > 0 and offs[strip - 1] == 0:
            strip -= 1
        first_real = min((o for o in offs if o > 0), default=1)
        k, q = 0, 1
        while q < first_real and strip + k < cnt:
            offs[strip + k] = q
            q = d.index(b'\x00', blob + q) - blob + 1
            k += 1
        self._sid_blob, self._sid_idx = blob, idx
        self._sid_offs, self._sid_strip = offs, strip
        self._sid_ok = True
        return True

    def _string_at(self, gidx):
        if not self._locate_stringids() or not (0 <= gidx < self.str_tbl_count):
            return None
        off = self._sid_offs[gidx]
        p = self._sid_blob + off
        try:
            return self.data[p:self.data.index(b'\x00', p)].decode('latin1')
        except ValueError:
            return None

    def resolve_stringid(self, sid):
        """Resolve a stringID value to its string. Handles namespace 0 (the engine's
        static set — where animation-action labels like `reload_empty` live) by mapping
        its index into the rebuilt stripped tail. Returns None for other namespaces or
        on failure."""
        if not self._locate_stringids():
            return None
        namespace = (sid >> 16) & 0xFF
        index = sid & 0xFFFF
        if namespace != 0:
            return None
        return self._string_at(self._sid_strip + index - 1)

    # --- tag lookups ---
    def tag(self, index):
        return self.tags[index] if 0 <= index < len(self.tags) else None

    def _singleton(self, cls):
        for t in self.tags:
            if t['class'] == cls and t['base'] is not None:
                return t
        return None

    def scenario_tag(self):
        return self._singleton('scnr')

    def globals_tag(self):
        return self._singleton('matg')

    def find_tags(self, cls, path):
        """Resolve a tag reference to (path, base_offset) pairs, mirroring
        Halo1/2 find_tags. matg/scnr resolve via their (unique) tag-group magic
        so they work even on retail maps whose names are stripped. Other classes
        match by name: exact, trailing/'*'-anywhere wildcard, or ' & '-joined —
        which requires the map to retain tag names (all toolset rebuilds do)."""
        if cls == 'matg':
            t = self.globals_tag()
            return [(path, t['base'])] if t else []
        if cls == 'scnr':
            t = self.scenario_tag()
            return [(path, t['base'])] if t else []
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
            return sorted((t['name'], t['base']) for t in self.tags
                          if t['class'] == cls and t['name'] and t['base'] is not None
                          and match(t['name']))
        for t in self.tags:
            if t['class'] == cls and t['name'] == path and t['base'] is not None:
                return [(t['name'], t['base'])]
        return []

    # --- reflexive walk (mirrors halo_map.follow / follow_all; ptr via data2off) ---
    def follow(self, base, block_offsets, block_sizes=None, index=0):
        cur = base
        n = len(block_offsets)
        for i, refl in enumerate(block_offsets):
            count = self.i32(cur + refl)
            ptr = self.u32(cur + refl + 4)
            idx = index if i == n - 1 else 0
            arr = self.data2off(ptr)
            if arr is None or count <= idx:
                return None
            size = block_sizes[i] if block_sizes else 0
            cur = arr + idx * size
        return cur

    def follow_all(self, base, block_offsets, block_sizes=None, index=0):
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
                arr = self.data2off(ptr)
                if arr is None or count <= 0:
                    continue
                s = sel[i]
                idxs = range(count) if s == 'all' else ([s] if 0 <= s < count else [])
                for idx in idxs:
                    nxt.append(arr + idx * size)
            cur = nxt
        return cur

    # --- per-tag field read/write/apply (mirror Halo2Map) ---
    def read_tag_field(self, tag_base, field, plugin, block=None, index=0, nth=0):
        fld = plugin.find(field, block, nth)
        if not fld:
            return None
        try:
            leaves = self.follow_all(tag_base, fld['block_offsets'], fld.get('block_sizes'), index)
            if not leaves:
                return None
            fmt, _ = hm.TYPE_FMT[fld['type']]
            raw = struct.unpack_from(fmt, self.data, leaves[0] + fld['offset'])[0]
            return hm.raw_to_display(fld['type'], raw)
        except Exception:
            return None

    def write_tag_field(self, tag_base, field, value, plugin, block=None, index=0, nth=0):
        fld = plugin.find(field, block, nth)
        if not fld:
            return None
        base = self.follow(tag_base, fld['block_offsets'], fld.get('block_sizes'), index)
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
                        scale=1.0, offset=0.0, clamp_min=None, clamp_max=None,
                        zero_is=None):
        base_r = {'field': field}
        fld = plugin.find(field, block, nth)
        if not fld:
            return {**base_r, 'ok': False, 'reason': 'field not found in plugin'}
        try:
            leaves = self.follow_all(tag_base, fld['block_offsets'], fld.get('block_sizes'), index)
            if not leaves:
                return {**base_r, 'ok': False, 'reason': 'empty block in this tag'}
            fmt, _ = hm.TYPE_FMT[fld['type']]
            ftype = fld['type']
            is_float = ftype in hm.FLOAT_TYPES or ftype in hm.ANGLE_TYPES
            first_old = first_new = None
            for base in leaves:
                off = base + fld['offset']
                old = hm.raw_to_display(ftype, struct.unpack_from(fmt, self.data, off)[0])
                if zero_is is not None and not old:
                    old = zero_is        # placeholder 0; see HaloMap.apply_field
                # operate in the MEANING the magnitude is expressed in, then map back
                # (see HaloMap.apply_field); defaults are the identity
                meaning = hm.OP_FUNCS[op](scale * old + offset, value)
                # Clamp in MEANING units, exactly as HaloMap does. These were added to
                # Halo 1 and to the halo_patch call site but not here, so every Halo 3
                # and ODST patch raised "unexpected keyword argument 'clamp_min'".
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

    def apply_field(self, cls, path, field, op, value, plugin, block=None, index=0, nth=0,
                    scale=1.0, offset=0.0, clamp_min=None, clamp_max=None,
                    zero_is=None):
        """Apply an operator to a field across every tag matching (cls, path).
        Plain per-tag (no char parent-inheritance walk yet — H3 AI mapping is TBD;
        add a _data_holder like halo2_map if H3 char variants need it)."""
        ref = f"{cls} {path}"
        tags = self.find_tags(cls, path)
        if not tags:
            return [{'tag': ref, 'field': field, 'ok': False, 'reason': 'not present in this map'}]
        results = []
        for tpath, base in tags:
            r = self.apply_tag_field(base, field, op, value, plugin, block, index, nth,
                                          scale, offset, clamp_min, clamp_max, zero_is)
            if cls == 'char' and not r.get('ok') and r.get('reason') == 'empty block in this tag':
                # char variant with an empty block inherits it from its base — not a
                # failure; the base variant in this same set carries (and gets) the edit.
                r = {**r, 'ok': True, 'skip': True, 'reason': 'inherits from base'}
            r['tag'] = f"{cls} {tpath}"
            results.append(r)
        return results

    # --- HaloMap-compatible path reads ---
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

    # --- checksum + save ---
    def update_checksum(self):
        """XOR of every u32 from HEADER_SIZE to EOF, written at CHECKSUM_OFF.
        The checksum word is in the header (< HEADER_SIZE) so it's excluded."""
        mv = memoryview(self.data)[self.HEADER_SIZE:]
        whole = len(mv) - (len(mv) % 4)
        words = array.array('I')
        words.frombytes(mv[:whole])
        if array.array('I', b'\x01\x00\x00\x00')[0] != 1:   # normalize to LE
            words.byteswap()
        cs = 0
        for x in words:
            cs ^= x
        if len(mv) % 4:
            cs ^= int.from_bytes(bytes(mv[whole:]).ljust(4, b'\x00'), 'little')
        struct.pack_into('<I', self.data, self.CHECKSUM_OFF, cs)
        return cs

    def save(self, out_path=None):
        self.update_checksum()
        with open(out_path or self.path, 'wb') as f:
            f.write(self.data)


if __name__ == '__main__':
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else \
        r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\halo3\maps\010_jungle.map"
    m = Halo3Map(p)
    print(f"build={m.build!r} internal={m.internal_name} scenario={m.scenario_name}")
    print(f"version={m.version} tags={m.n_tags} groups={m.n_groups} names_stripped={m.names_stripped}")
    print(f"index header @ {m.index_header_off:#x}")
    for i, (la, sz, fb) in enumerate(m.partitions):
        print(f"  P{i} load={la:#x} size={sz:#x} file={fb:#x}" if fb is not None else f"  P{i} load={la:#x} size={sz:#x}")
    s = m.scenario_tag(); g = m.globals_tag()
    print("scnr base", hex(s['base']) if s else None, "| matg base", hex(g['base']) if g else None)
    cs = m.u32(m.CHECKSUM_OFF); calc = m.update_checksum()
    print(f"checksum stored={cs:#010x} recomputed={calc:#010x} match={cs == calc}")
