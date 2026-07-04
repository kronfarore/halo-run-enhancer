# halo_map.py — read Halo 1 (MCC) map files and resolve effect fields via
# Assembly plugin XML. READ-ONLY core; patching is layered on top separately.
#
# Pipeline (proven against a10.map):
#   map header -> tag index (magic) -> tag by (class, path) -> meta offset
#   Assembly plugin XML -> field name -> reflexive chain + leaf offset/type
#   follow reflexives from meta -> read/write the value
#
# This module has no GUI dependency so it can be tested headless.

import struct
import xml.etree.ElementTree as ET
from pathlib import Path

# Assembly plugin field type -> (struct format, size in bytes)
TYPE_FMT = {
    'float32': ('<f', 4), 'float': ('<f', 4), 'real': ('<f', 4),
    'int32': ('<i', 4), 'uint32': ('<I', 4), 'long': ('<i', 4), 'dword': ('<I', 4),
    'int16': ('<h', 2), 'uint16': ('<H', 2), 'short': ('<h', 2), 'word': ('<H', 2),
    'int8': ('<b', 1), 'uint8': ('<B', 1), 'byte': ('<B', 1), 'sbyte': ('<b', 1),
    'degree': ('<f', 4), 'angle': ('<f', 4),  # angles stored as float radians
}

FLOAT_TYPES = {'float32', 'float', 'real'}

# XML node tags that introduce a nested reflexive (block) in Halo 1 plugins.
BLOCK_TAGS = {'tagblock', 'reflexive', 'struct'}

# Operator applied to a field's current value.
OP_FUNCS = {
    'set': lambda old, v: v,
    'add': lambda old, v: old + v,
    'sub': lambda old, v: old - v,
    'mul': lambda old, v: old * v,
}
_OP_SIGNS = {'=': 'set', '+': 'add', '-': 'sub', '*': 'mul'}


def parse_operator(text):
    """Parse a compact edit like '+5', '-0.3', '*1.2', '=1' into (op, value).
    A bare number means 'set'. Returns None if unparseable."""
    if text is None:
        return None
    text = str(text).strip()
    if not text:
        return None
    op = _OP_SIGNS.get(text[0])
    body = text[1:] if op else text
    if op is None:
        op = 'set'
    try:
        return (op, float(body))
    except ValueError:
        return None


def split_tag(tag):
    """'matg globals\\globals' -> ('matg', 'globals\\globals')."""
    cls, _, path = tag.partition(' ')
    return cls, path


class Plugin:
    """Flattened view of an Assembly plugin: every leaf field with the reflexive
    offsets needed to reach it and its type."""

    def __init__(self, path):
        self.path = str(path)
        self.fields = []  # {name, block_chain, block_offsets, block_sizes, offset, type}
        root = ET.parse(path).getroot()
        bs = root.get('baseSize')
        self.base_size = int(bs, 16) if bs else None
        self._walk(root, [], [], [])

    def _walk(self, node, chain, offsets, sizes):
        for ch in node:
            t = ch.tag.lower()
            name = ch.get('name')
            off = ch.get('offset')
            if t in BLOCK_TAGS and off is not None:
                es = ch.get('elementSize')
                sz = int(es, 16) if es else 0
                self._walk(ch, chain + [name], offsets + [int(off, 16)], sizes + [sz])
            elif off is not None and name is not None and t in TYPE_FMT:
                self.fields.append({
                    'name': name,
                    'block_chain': list(chain),
                    'block_offsets': list(offsets),
                    'block_sizes': list(sizes),
                    'offset': int(off, 16),
                    'type': t,
                })
            elif off is not None and name is not None and t in ('rangef', 'range', 'ranged'):
                # A range is two floats (min, max). Expose both: '<name>' (min)
                # and '<name> Max' (max) so either bound can be targeted.
                o = int(off, 16)
                for suffix, delta in (('', 0), (' Max', 4)):
                    self.fields.append({
                        'name': name + suffix,
                        'block_chain': list(chain),
                        'block_offsets': list(offsets),
                        'block_sizes': list(sizes),
                        'offset': o + delta,
                        'type': 'float32',
                    })

    def find(self, field_name, block=None):
        """Locate a field by name (case-insensitive); if `block` is given, the
        field's innermost block must match it."""
        fl = field_name.lower()
        cands = [f for f in self.fields if f['name'].lower() == fl]
        if block:
            bl = block.lower()
            cands = [f for f in cands
                     if f['block_chain'] and f['block_chain'][-1].lower() == bl]
        return cands[0] if cands else None


class HaloMap:
    """Parsed Halo 1 (MCC) map with tag lookup and field read/write."""

    def __init__(self, path):
        self.path = str(path)
        with open(path, 'rb') as f:
            self.data = bytearray(f.read())
        self._parse_index()

    # --- low-level ---
    def u32(self, o):
        return struct.unpack_from('<I', self.data, o)[0]

    def _cstr(self, o):
        end = self.data.index(b'\x00', o)
        return bytes(self.data[o:end]).decode('latin1')

    def _parse_index(self):
        if self.data[:4] != b'daeh':
            raise ValueError("Not a Halo map (missing 'head' magic)")
        self.version = self.u32(4)
        self.index_off = self.u32(0x10)
        io = self.index_off
        self.tag_array_ptr = self.u32(io)
        self.scenario_id = self.u32(io + 0x08)
        self.tag_count = self.u32(io + 0x0C)
        if self.data[io + 0x24:io + 0x28] != b'sgat':
            raise ValueError("Tag index 'tags' magic missing — unexpected map format")
        self.tag_array_off = io + 0x28
        self.magic = (self.tag_array_ptr - self.tag_array_off) & 0xFFFFFFFF
        self.tags = {}
        for i in range(self.tag_count):
            b = self.tag_array_off + i * 32
            cls = bytes(self.data[b:b + 4][::-1]).decode('latin1')
            name_ptr = self.u32(b + 0x10)
            meta_ptr = self.u32(b + 0x14)
            try:
                name = self._cstr((name_ptr - self.magic) & 0xFFFFFFFF)
            except Exception:
                continue
            self.tags[(cls, name)] = (meta_ptr - self.magic) & 0xFFFFFFFF

    # --- resolution ---
    def get_tag_meta(self, cls, path):
        return self.tags.get((cls, path))

    def find_tags(self, cls, path):
        """Resolve a tag reference to (path, meta_off) pairs. A trailing '*' is a
        VARIANT match — e.g. 'characters\\elite\\*' hits every elite variant
        present in this map. ' & ' joins several paths of the same group. An
        exact path returns 0 or 1 entry."""
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
            return sorted((p, off) for (c, p), off in self.tags.items()
                          if c == cls and p.startswith(prefix))
        off = self.tags.get((cls, path))
        return [(path, off)] if off is not None else []

    def apply_field(self, cls, path, field, op, value, plugin, block=None, index=0):
        """Apply an operator to a field across every tag matching (cls, path).
        Never raises for missing tags/fields — returns a list of result dicts
        (ok/old/new or ok=False/reason) so a summary can be shown at the end."""
        ref = f"{cls} {path}"
        tags = self.find_tags(cls, path)
        if not tags:
            return [{'tag': ref, 'field': field, 'ok': False,
                     'reason': 'not present in this map'}]
        fld = plugin.find(field, block)
        if not fld:
            return [{'tag': ref, 'field': field, 'ok': False,
                     'reason': 'field not found in plugin'}]
        fmt, _ = TYPE_FMT[fld['type']]
        is_float = fld['type'] in FLOAT_TYPES
        results = []
        for tpath, meta in tags:
            try:
                base = self.follow(meta, fld['block_offsets'], fld.get('block_sizes'), index)
                off = base + fld['offset']
                old = struct.unpack_from(fmt, self.data, off)[0]
                new = OP_FUNCS[op](old, value)
                new = float(new) if is_float else int(round(new))
                struct.pack_into(fmt, self.data, off, new)
                results.append({'tag': f"{cls} {tpath}", 'field': field,
                                'ok': True, 'old': old, 'new': new})
            except Exception as e:
                results.append({'tag': f"{cls} {tpath}", 'field': field,
                                'ok': False, 'reason': str(e)})
        return results

    def follow(self, meta_off, block_offsets, block_sizes=None, index=0):
        """Walk a reflexive chain from a tag's meta to a leaf struct. Each H1
        reflexive is [count:i32][ptr:u32]. `index` selects the element of the
        INNERMOST block (outer blocks always use element 0); it needs the block's
        element size, so pass block_sizes (parallel to block_offsets)."""
        cur = meta_off
        n = len(block_offsets)
        for i, refl in enumerate(block_offsets):
            ptr = self.u32(cur + refl + 4)
            base = (ptr - self.magic) & 0xFFFFFFFF
            idx = index if i == n - 1 else 0
            size = block_sizes[i] if block_sizes else 0
            cur = base + idx * size
        return cur

    def resolve(self, cls, path, field, plugin, block=None, index=0):
        """Return (base_offset, field_dict) for a field, or None."""
        meta = self.get_tag_meta(cls, path)
        if meta is None:
            return None
        fld = plugin.find(field, block)
        if not fld:
            return None
        base = self.follow(meta, fld['block_offsets'], fld.get('block_sizes'), index)
        return base, fld

    def read(self, cls, path, field, plugin, block=None, index=0):
        r = self.resolve(cls, path, field, plugin, block, index)
        if r is None:
            return None
        base, fld = r
        fmt, _ = TYPE_FMT[fld['type']]
        return struct.unpack_from(fmt, self.data, base + fld['offset'])[0]

    def read_first(self, cls, path, field, plugin, block=None, index=0):
        """Read a field from the first tag matching (cls, path); handles the
        variant '*' form. Returns None if unresolved."""
        tags = self.find_tags(cls, path)
        if not tags:
            return None
        fld = plugin.find(field, block)
        if not fld:
            return None
        try:
            base = self.follow(tags[0][1], fld['block_offsets'], fld.get('block_sizes'), index)
            fmt, _ = TYPE_FMT[fld['type']]
            return struct.unpack_from(fmt, self.data, base + fld['offset'])[0]
        except Exception:
            return None

    def read_all(self, cls, path, field, plugin, block=None, index=0):
        """(tag_path, value) for every tag matching (cls, path) — one entry per
        variant. Skips any that don't resolve. Empty if the field is unknown."""
        fld = plugin.find(field, block)
        if not fld:
            return []
        fmt, _ = TYPE_FMT[fld['type']]
        out = []
        for tpath, meta in self.find_tags(cls, path):
            try:
                base = self.follow(meta, fld['block_offsets'], fld.get('block_sizes'), index)
                out.append((tpath, struct.unpack_from(fmt, self.data, base + fld['offset'])[0]))
            except Exception:
                pass
        return out

    def write(self, cls, path, field, plugin, value, block=None, index=0):
        """Write a value into the in-memory buffer (call save() to persist).
        Returns the previous value, or None if unresolved."""
        r = self.resolve(cls, path, field, plugin, block, index)
        if r is None:
            return None
        base, fld = r
        fmt, _ = TYPE_FMT[fld['type']]
        off = base + fld['offset']
        old = struct.unpack_from(fmt, self.data, off)[0]
        if fld['type'] in ('float32', 'float', 'real'):
            value = float(value)
        else:
            value = int(value)
        struct.pack_into(fmt, self.data, off, value)
        return old

    def save(self, out_path):
        with open(out_path, 'wb') as f:
            f.write(self.data)


if __name__ == '__main__':
    import sys
    map_path = sys.argv[1] if len(sys.argv) > 1 else \
        r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\halo1\maps\a10.map"
    plugin_path = sys.argv[2] if len(sys.argv) > 2 else \
        r"C:\Program Files (x86)\Steam\steamapps\common\HCEEK\Assembly-1-2023-11-29-1702446457\Plugins\Halo1\matg.xml"
    m = HaloMap(map_path)
    print(f"map={Path(map_path).name} version={m.version} tags={m.tag_count} magic={m.magic:#x}")
    pl = Plugin(plugin_path)
    print(f"plugin fields parsed: {len(pl.fields)}")
    for diff in ('Easy', 'Normal', 'Hard', 'Impossible'):
        v = m.read('matg', 'globals\\globals', f'{diff} Enemy Damage', pl, block='Difficulty')
        print(f"  {diff} Enemy Damage = {v}")
