# halo2_map.py — parser for Halo 2 MCC (.map) cache files.
#
# Halo 2 MCC is a *second-generation* Blam cache, fundamentally different from
# the Halo 1 MCC format in halo_map.py:
#   * The map body is zlib-compressed in chunks (h2mcc scheme).
#   * Tags are indexed via a meta header + tag table (no 'sgat').
#   * Pointers inside tag data are converted:  file = metaOffset + P - mask.
#
# The format details were taken from Assembly (XboxChaos/Assembly),
# src/Blamite/Blam/SecondGen/*.  Layout offsets match Assembly's
# Formats/Halo2MCC/LayoutsU1 (U1 header) + Layouts (Core meta/tag structs).
#
# STATUS: read path verified on 01a_tutorial.map (matg + scnr fields match
# known-good values). Tag lookup for the singleton globals/scenario tags is by
# datum index (no name table needed). Path-based lookup and save/recompress
# are not implemented yet (see NotImplementedError stubs).

import struct
import zlib

import halo_map as hm   # reuse Plugin, TYPE_FMT, FLOAT_TYPES, OP_FUNCS, split_tag


class Halo2Map:
    """Parsed Halo 2 MCC cache (decompressed in memory). Read-only for now."""

    HEADER_SIZE = 0x380

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

    def _cstr(self, o):
        end = self.data.index(b'\x00', o)
        return bytes(self.data[o:end]).decode('latin1')

    # --- decompression (h2mcc "Saber" chunked deflate) ---
    # Mirrors Assembly SecondGenSaberZLib.DecompressCache: the header stays raw,
    # then each chunk is [2-byte marker 0x1538][raw DEFLATE] and decompresses to
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

    def read_tag_field(self, tag_base, field, plugin, block=None, index=0):
        """Read a plugin field from a tag whose data starts at file `tag_base`."""
        fld = plugin.find(field, block)
        if not fld:
            return None
        try:
            base = self.follow(tag_base, fld['block_offsets'],
                               fld.get('block_sizes'), index)
            if base is None:
                return None
            fmt, _ = hm.TYPE_FMT[fld['type']]
            return struct.unpack_from(fmt, self.data, base + fld['offset'])[0]
        except Exception:
            return None

    def write_tag_field(self, tag_base, field, value, plugin, block=None, index=0):
        """Write a value into a tag's field (in memory; call save() to persist).
        Returns the previous value, or None if unresolved."""
        fld = plugin.find(field, block)
        if not fld:
            return None
        base = self.follow(tag_base, fld['block_offsets'],
                           fld.get('block_sizes'), index)
        if base is None:
            return None
        fmt, _ = hm.TYPE_FMT[fld['type']]
        off = base + fld['offset']
        old = struct.unpack_from(fmt, self.data, off)[0]
        value = float(value) if fld['type'] in hm.FLOAT_TYPES else int(round(value))
        struct.pack_into(fmt, self.data, off, value)
        return old

    def apply_tag_field(self, tag_base, field, op, value, plugin, block=None, index=0):
        """Apply an operator to a tag field. Returns a result dict mirroring
        halo_map.HaloMap.apply_field entries (ok/old/new or ok=False/reason)."""
        base_r = {'field': field}
        fld = plugin.find(field, block)
        if not fld:
            return {**base_r, 'ok': False, 'reason': 'field not found in plugin'}
        try:
            base = self.follow(tag_base, fld['block_offsets'],
                               fld.get('block_sizes'), index)
            if base is None:
                return {**base_r, 'ok': False, 'reason': 'empty block in this tag'}
            fmt, _ = hm.TYPE_FMT[fld['type']]
            off = base + fld['offset']
            old = struct.unpack_from(fmt, self.data, off)[0]
            new = hm.OP_FUNCS[op](old, value)
            new = float(new) if fld['type'] in hm.FLOAT_TYPES else int(round(new))
            struct.pack_into(fmt, self.data, off, new)
            return {**base_r, 'ok': True, 'old': old, 'new': new}
        except Exception as e:
            return {**base_r, 'ok': False, 'reason': str(e)}

    # --- checksum + save ---
    def update_checksum(self):
        """Recompute the header checksum (XOR of all u32 after the header) and
        write it back into the image at 0x2F8. Only valid for uncompressed maps."""
        body = self.data[self.HEADER_SIZE:]
        if len(body) % 4:
            body = bytes(body) + b'\x00' * (4 - len(body) % 4)
        cs = 0
        for i in range(0, len(body), 4):
            cs ^= struct.unpack_from('<I', body, i)[0]
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
        if path.endswith('*'):
            prefix = path[:-1]
            res = [(t['name'], t['base']) for t in self.tags
                   if t['class'] == cls and t['name'] and t['base'] is not None
                   and t['name'].startswith(prefix)]
            return sorted(res)
        for t in self.tags:
            if t['class'] == cls and t['name'] == path and t['base'] is not None:
                return [(t['name'], t['base'])]
        return []

    def read(self, cls, path, field, plugin, block=None, index=0):
        tags = self.find_tags(cls, path)
        return self.read_tag_field(tags[0][1], field, plugin, block, index) if tags else None

    def read_first(self, cls, path, field, plugin, block=None, index=0):
        return self.read(cls, path, field, plugin, block, index)

    def read_all(self, cls, path, field, plugin, block=None, index=0):
        out = []
        for tpath, base in self.find_tags(cls, path):
            v = self.read_tag_field(base, field, plugin, block, index)
            if v is not None:
                out.append((tpath, v))
        return out

    def apply_field(self, cls, path, field, op, value, plugin, block=None, index=0):
        ref = f"{cls} {path}"
        tags = self.find_tags(cls, path)
        if not tags:
            return [{'tag': ref, 'field': field, 'ok': False,
                     'reason': 'not present in this map'}]
        results = []
        for tpath, base in tags:
            r = self.apply_tag_field(base, field, op, value, plugin, block, index)
            r['tag'] = f"{cls} {tpath}"
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
