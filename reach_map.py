# reach_map.py — parser + patcher for Halo: Reach MCC (.map) cache files.
#
# Reach is a *fourth-generation* Blam cache, but on MCC it is close enough to the
# Halo 3 / ODST cache (halo3_map.Halo3Map) that this is a thin subclass. Verified
# empirically against all 12 shipped campaign maps (m05 .. m70_bonus) plus
# ff_unearthed. LITTLE-endian and header version 13, both shared with Halo 3.
#
# The FIVE divergences from Halo 3, and nothing else:
#
#   1. INDEX HEADER SIZE. Halo 3 puts the 'tags' magic at index_header+0x44; Reach
#      puts it at +0x48. The four (count, address) descriptor pairs sit at the same
#      offsets as Halo 3 (0x00/0x08, 0x10/0x18, 0x20/0x28, 0x30/0x38) but each count
#      is followed by a 4-byte '343i' guard word where Halo 3 has zero padding. That
#      guard is what pushes the checksum and magic 4 bytes later.
#
#   2. TAG-DATA ADDRESS BIAS. Both games store every tag memory address and every
#      internal reflexive / dataRef pointer as (realVA >> 2). Reach biases that space
#      down by a flat 0x5000_0000 before shifting, so:
#           realVA = (ptr << 2) + 0x5000_0000
#      Once biased back, the Halo 3 partition lookup resolves it unchanged. The
#      biased space always ends at 0x1_8000_0000, i.e. the stored u32 tops out just
#      under 0x6000_0000 — which is presumably the point of the bias.
#
#   3. THE STRING TABLES ARE PRESENT, JUST DISPLACED. Halo 3 retail zeroes/garbles
#      the tag-name and stringID tables, which is why Halo3Map has to go hunting for
#      them (`_recover_retail_names`, `_locate_stringids`). Reach ships all four
#      tables intact; only the four header pointers to them are stale, every one off
#      by the SAME constant K. Recover K once from the name blob and all four
#      (file table, file index, string table, string index) resolve exactly. This is
#      strictly better than the Halo 3 path — full stringID coverage, no anchors.
#
#   4. HEADER SIZE. 0xA000, not Halo 3's 0x4000 -- see HEADER_SIZE below. This one
#      used to be described here as shared with Halo 3, which was wrong in the worst
#      direction: update_checksum XORs from HEADER_SIZE to EOF, so the stale figure
#      writes a bad checksum into every patched map.
#
#   5. GROUP ENTRY / TAG ENTRY / PARTITIONS / CHECKSUM: byte-for-byte Halo 3. The
#      6-partition table @0x300, virt_base @0x2E0, index header VA @0x2E8, the
#      0x10-byte tag-group entry ([magic][parent][grandparent][stringid]), the 8-byte
#      tag-table entry ([group idx i16][salt u16][memaddr u32]) and the 0x360 XOR
#      checksum all read unchanged.
#
# Everything else — reflexives, tagRefs, field read/apply, checksum refresh, save() —
# is inherited. Value edits only; no structural growth.

import struct

from halo3_map import Halo3Map


class ReachMap(Halo3Map):
    """Parsed Halo: Reach MCC cache. See the module docstring for the four ways it
    differs from Halo3Map; every other behaviour is inherited unchanged."""

    # Reach's header is 0xA000, not Halo 3's 0x4000 — the 'foot' terminator sits at
    # 0x9FFC where Halo 3 and ODST put it at 0x3FFC, and the region between is
    # near-entirely zero padding. This matters because `update_checksum` XORs from
    # HEADER_SIZE to EOF: with 0x4000 the recomputed value does NOT reproduce a
    # shipped map's stored checksum, and with 0xA000 it reproduces it exactly on
    # every campaign map. Getting this wrong writes a wrong checksum into every
    # patched map, which is the sort of thing that only shows up in game.
    HEADER_SIZE = 0xA000
    TAGS_MAGIC_OFF = 0x48       # Halo 3 uses 0x44
    DATA_BIAS = 0x50000000      # realVA = (ptr << 2) + DATA_BIAS

    # --- index header ---
    def _locate_index_header(self):
        """Same search as Halo 3, with the 'tags' magic 4 bytes further into the
        header. The flat-delta fast path Halo 3 uses does not hold on Reach (its
        tag_buffer_offset is not the index-space anchor), so scan for the magic and
        validate the descriptor pairs behind it — including the '343i' guard, which
        is what distinguishes a real Reach index header from a stray 'sgat'."""
        m = self.TAGS_MAGIC_OFF
        start = 0
        while True:
            i = self.data.find(b'sgat', start)
            if i < 0:
                break
            ioff = i - m
            if ioff >= 0:
                ng = struct.unpack_from('<i', self.data, ioff)[0]
                nt = struct.unpack_from('<i', self.data, ioff + 0x10)[0]
                ta = self.u64(ioff + 0x18)
                ga = self.u64(ioff + 0x8)
                if (0 < ng < 1000 and 0 < nt < 40000
                        and ta > 0x100000000 and ga > 0x100000000
                        and self.data[ioff + 0x4:ioff + 0x8] == b'343i'):
                    self.index_header_off = ioff
                    return
            start = i + 1
        raise ValueError("Halo Reach index header ('tags' magic) not found")

    # --- the >>2 tag-data pointer model, biased ---
    def data2off(self, ptr):
        """Tag-data pointer (stored (realVA - 0x5000_0000) >> 2) -> file offset."""
        if ptr in (0, 0xFFFFFFFF):
            return None
        va = (ptr << 2) + self.DATA_BIAS
        i = self._part_of(va)
        if i is None or self.partitions[i][2] is None:
            return None
        return self.partitions[i][2] + (va - self.partitions[i][0])

    def off2data(self, off):
        """Inverse of data2off, or None if the offset has no representable pointer.

        The bias is what makes the None matter here. Halo3Map cannot produce a wrong
        answer -- with no subtraction its result is always a real address -- but an
        address below DATA_BIAS makes this one go negative, and `>> 2` on a negative
        floors toward -inf before `& 0xFFFFFFFF` wraps it into a perfectly
        plausible-looking pointer. Nineteen of this method's twenty callers feed the
        result straight into struct.pack_into, so a wrapped value would be written
        into a map as a block pointer with nothing raised anywhere.

        Shipped maps should never reach it: the biased space starts at DATA_BIAS by
        construction. That is the reason to fail loudly rather than the reason to
        skip the check -- if it ever does go low, something is wrong upstream and a
        corrupt map is the worst way to find out.
        """
        for la, sz, fb in self.partitions:
            if fb is not None and fb <= off < fb + sz:
                va = la + (off - fb)
                if va < self.DATA_BIAS:
                    return None
                return ((va - self.DATA_BIAS) >> 2) & 0xFFFFFFFF
        return None

    # --- the four string tables ---
    #
    # Header fields 0x20..0x3C describe them, but as addresses in a space biased away
    # from the file by a constant K:
    #     file_offset = header_value - K
    # K is the same for all four, so one anchor recovers the lot. The anchor is the
    # name blob itself: its physical start is found by the `ugh!` tag's joke name
    # (present in every Bungie-built cache a few strings in), with a walk-back from
    # the scenario name as fallback, then confirmed by checking that the recovered
    # index really does map the globals and scenario rows to their known names.

    _NAME_BLOB_SENTINEL = b"i've got a lovely bunch of coconuts\x00"

    def _parse_tag_names(self):
        self.names_stripped = False
        self.names_recovered = False
        self.table_bias = None
        if self._recover_table_bias():
            self._populate_reach_names()
        else:
            self.names_stripped = True

    def _blob_candidates(self):
        """Plausible physical starts for the tag-name blob, best guess first. The
        sentinel is a few bytes into the blob and the exact lead-in (empty strings for
        the unnamed `draw`/`gpix`/... rows) varies, so offer a small window rather
        than a single guess and let verification pick."""
        d = self.data
        out = []
        p = d.find(self._NAME_BLOB_SENTINEL, 0x1000)
        if p > 0:
            out.extend(p - k for k in range(1, 9) if p - k >= 0)
        if self.scenario_name:
            q = d.find(self.scenario_name.encode('latin1') + b'\x00', 0x1000)
            if q > 0:
                r = q
                while r > 1:
                    prev = d.rfind(b'\x00', 0, r - 1)
                    if prev < 0:
                        break
                    s = d[prev + 1:r - 1]
                    if not s or not all(32 <= c < 127 for c in s):
                        break
                    r = prev + 1
                out.extend(r - k for k in range(0, 9) if r - k >= 0)
        seen, uniq = set(), []
        for o in out:
            if o not in seen:
                seen.add(o)
                uniq.append(o)
        return uniq

    def _recover_table_bias(self):
        """Solve K and cache the four resolved table offsets. Returns True on
        success."""
        matg, scnr = self._singleton('matg'), self._singleton('scnr')
        if not (matg and scnr and self.scenario_name) or self.file_tbl_count <= 0:
            return False
        want = ((matg['index'], 'globals\\globals'),
                (scnr['index'], self.scenario_name))
        for blob in self._blob_candidates():
            k = self.file_tbl_offset - blob
            idx = self.file_idx_offset - k
            if not (0 <= idx and idx + self.file_tbl_count * 4 <= len(self.data)):
                continue
            if not (0 <= blob and blob + self.file_tbl_size <= len(self.data)):
                continue
            if all(self._name_at(idx, blob, row) == name for row, name in want):
                self.table_bias = k
                self.name_idx_off = idx
                self.name_blob_off = blob
                self.sid_idx_off = self.str_idx_offset - k
                self.sid_blob_off = self.str_tbl_offset - k
                return True
        return False

    def _name_at(self, idx_base, blob_base, row):
        try:
            e = struct.unpack_from('<i', self.data, idx_base + row * 4)[0]
        except Exception:
            return None
        if not 0 <= e < self.file_tbl_size:
            return None
        p = blob_base + e
        try:
            return self.data[p:self.data.index(b'\x00', p)].decode('latin1')
        except ValueError:
            return None

    def _populate_reach_names(self):
        for t in self.tags:
            t['name'] = self._name_at(self.name_idx_off, self.name_blob_off, t['index'])
        self.names_recovered = True

    # --- stringIDs ---
    #
    # Halo3Map hunts for these with a static-string anchor and then rebuilds a tail
    # that retail stripped. Reach needs neither: the same K that placed the tag names
    # places the stringID index and blob exactly, complete, so resolve_stringid()
    # works for every namespace instead of only namespace 0.

    def _locate_stringids(self):
        if hasattr(self, '_sid_ok'):
            return self._sid_ok
        self._sid_ok = False
        self._sid_blob = self._sid_idx = 0
        if self.table_bias is None or self.str_tbl_count <= 0:
            return False
        idx, blob = self.sid_idx_off, self.sid_blob_off
        if not (0 <= idx and idx + self.str_tbl_count * 4 <= len(self.data)):
            return False
        if not (0 <= blob and blob + self.str_tbl_size <= len(self.data)):
            return False
        self._sid_offs = list(struct.unpack_from('<%di' % self.str_tbl_count,
                                                 self.data, idx))
        self._sid_blob, self._sid_idx, self._sid_strip = blob, idx, 0
        self._sid_ok = True
        return True

    def resolve_stringid(self, sid):
        """Reach keeps the whole stringID set, so this is a straight index lookup —
        no namespace restriction and no stripped-tail rebuild."""
        if not self._locate_stringids():
            return None
        return self._string_at(sid & 0xFFFF)
