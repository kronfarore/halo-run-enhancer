# halo_map.py — read Halo 1 (MCC) map files and resolve effect fields via
# Assembly plugin XML. READ-ONLY core; patching is layered on top separately.
#
# Pipeline (proven against a10.map):
#   map header -> tag index (magic) -> tag by (class, path) -> meta offset
#   Assembly plugin XML -> field name -> reflexive chain + leaf offset/type
#   follow reflexives from meta -> read/write the value
#
# This module has no GUI dependency so it can be tested headless.

import math
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
    'enum16': ('<H', 2), 'enum8': ('<B', 1), 'enum32': ('<I', 4),  # option index (see Plugin._walk)
}

FLOAT_TYPES = {'float32', 'float', 'real'}

# Angle fields are stored as float RADIANS on disk but Assembly (and the user)
# work in DEGREES. Convert at the read/write boundary so displayed values and
# typed operators match Assembly. `ranged` (a degree range) flattens to two
# 'degree' halves below, so its bounds convert too. Multiply/divide are
# scale-invariant (conversion cancels); set/add/subtract are the ones that
# would otherwise be off by the 180/pi factor.
ANGLE_TYPES = {'degree', 'angle'}


def raw_to_display(field_type, v):
    """On-disk value -> value shown/edited in the UI (radians -> degrees for angles)."""
    return math.degrees(v) if field_type in ANGLE_TYPES else v


def display_to_raw(field_type, v):
    """UI value -> on-disk value (degrees -> radians for angles)."""
    return math.radians(v) if field_type in ANGLE_TYPES else v

# Assembly range types -> (sub-field struct type, byte width of each half).
# rangef/range/ranged are two float32s; range16 is two int16s.
# Two-component fields, flattened into a pair of leaves so either half can be
# targeted. (sub_type, width, (suffix_a, suffix_b)).
#
# Ranges are a (min, max) pair and take '' / ' Max'. `degree2` is NOT a range: it is a
# yaw/pitch angle pair, so it takes ' y' / ' p' -- calling its halves min and max would
# read as a bound when it is a direction. It went unsupported until Reach's
# `Damage Pyramid Angles` needed it, and an unsupported type is invisible rather than
# an error: the field simply never appears in Plugin.fields, so a card naming it finds
# nothing.
RANGE_TYPES = {
    'rangef': ('float32', 4, ('', ' Max')), 'range': ('float32', 4, ('', ' Max')),
    'ranged': ('degree', 4, ('', ' Max')),   # range of DEGREES; halves get angle conversion
    'range16': ('int16', 2, ('', ' Max')),
    'degree2': ('degree', 4, (' y', ' p')),
}

# XML node tags that introduce a nested reflexive (block) in Halo 1 plugins.
BLOCK_TAGS = {'tagblock', 'reflexive', 'struct'}


def _wildcard_matcher(pattern):
    """Return a predicate matching a tag name against a '*' wildcard. A single '*'
    is a fast prefix+suffix test (so 'a\\*' = startswith, '*z' = endswith,
    'a\\*z' = both); multiple '*' fall back to fnmatch. Literal, case-sensitive."""
    if pattern.count('*') == 1:
        pre, suf = pattern.split('*')
        return lambda name: (name.startswith(pre) and name.endswith(suf)
                             and len(name) >= len(pre) + len(suf))
    import fnmatch
    return lambda name: fnmatch.fnmatchcase(name, pattern)


def normalize_index_spec(spec, n):
    """Return a per-block-level list (length `n`, OUTER->INNER) of element
    selectors for a reflexive chain. Each selector is an int (a specific element)
    or the string 'all' (every populated element at that level). Accepts:
      None / 0    -> [0]*n           (single leaf; legacy default)
      int i       -> innermost = i, all outer levels = 0 (legacy single-index)
      'all'       -> ['all']*n       (full cross-product over every level)
      list/tuple  -> per-level (outer->inner); left-padded with 0 to length n,
                     each entry an int or 'all' (e.g. [0, 'all'])
    This is what lets a doubly-nested field like H2 'Rate Of Fire'
    (Firing Pattern Properties[i] -> Firing Patterns[j]) be reached at every
    (i, j), which the legacy single-innermost-index `follow` could not do."""
    if n <= 0:
        return []
    if spec is None:
        return [0] * n
    if isinstance(spec, str):
        return (['all'] * n) if spec.strip().lower() == 'all' else [0] * n
    if isinstance(spec, bool):            # bool is an int subclass — guard first
        return [0] * n
    if isinstance(spec, int):
        return [0] * (n - 1) + [spec]
    if isinstance(spec, (list, tuple)):
        s = [(x.strip().lower() if isinstance(x, str) else x) for x in spec]
        if len(s) < n:
            s = [0] * (n - len(s)) + s
        return list(s[-n:])
    return [0] * n

# Operator applied to a field's current value.
OP_FUNCS = {
    'set': lambda old, v: v,
    'add': lambda old, v: old + v,
    'sub': lambda old, v: old - v,
    'mul': lambda old, v: old * v,
}
_OP_SIGNS = {'=': 'set', '+': 'add', '-': 'sub', '*': 'mul', 'x': 'mul', 'X': 'mul'}


def parse_operator(text):
    """Parse a compact edit like '+5', '-0.3', '*1.2' / 'x1.2', '=1' into
    (op, value). A bare number means 'set'. Both '.' and ',' work as the decimal
    separator. Returns None if unparseable."""
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
        return (op, float(body.replace(',', '.')))
    except ValueError:
        return None


def normalize_op_text(text):
    """Canonical form of an operator entry: '*.5' -> '*0.5', 'x,5' -> '*0.5', '2.' -> '2'.

    parse_operator already ACCEPTS all of these -- this is purely so the entry the user
    looks at (and the magnitude remembered for it, and the one shared with a co-op
    partner) reads the same way whichever shorthand was typed.

    Unparseable text is returned unchanged rather than blanked: a half-typed entry is
    the user's to finish, and silently eating it would lose the edit.
    """
    raw = (text or '').strip()
    if not raw:
        return ''
    parsed = parse_operator(raw)
    if parsed is None:
        return raw
    op, val = parsed
    # A bare number already means 'set'; leave it bare so normalizing never adds an
    # operator the user didn't type.
    sign = '' if (op == 'set' and raw[0] != '=') else {'set': '=', 'add': '+',
                                                       'sub': '-', 'mul': '*'}[op]
    if abs(val) >= 1e15:
        return raw                      # beyond fixed-point formatting; leave it alone
    num = ('%.10f' % val).rstrip('0').rstrip('.')
    if not num or num in ('-', '0', '-0'):
        # Rounded away to nothing (a value smaller than 1e-10). Keep what was typed
        # rather than rewriting it to a zero that means something else entirely.
        return raw if val else num or '0'
    return sign + num


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
                fld = {
                    'name': name,
                    'block_chain': list(chain),
                    'block_offsets': list(offsets),
                    'block_sizes': list(sizes),
                    'offset': int(off, 16),
                    'type': t,
                }
                if t.startswith('enum'):
                    # Capture the option list so a value can be given by NAME
                    # (e.g. "Overcharge" -> 1) as well as by raw number.
                    opts = {}
                    for opt in ch:
                        if opt.tag.lower() == 'option' and opt.get('name') is not None:
                            try:
                                opts[opt.get('name').strip().lower()] = int(opt.get('value', '0'), 16)
                            except ValueError:
                                pass
                    if opts:
                        fld['options'] = opts
                self.fields.append(fld)
            elif off is not None and name is not None and t in RANGE_TYPES:
                # Two leaves, named by the type's own suffixes: '' / ' Max' for a
                # range, ' y' / ' p' for a degree2 angle pair. Width/type depends on
                # the kind — rangef/ranged are two float32s, range16 two int16s.
                sub_type, width, suffixes = RANGE_TYPES[t]
                o = int(off, 16)
                for suffix, delta in zip(suffixes, (0, width)):
                    self.fields.append({
                        'name': name + suffix,
                        'block_chain': list(chain),
                        'block_offsets': list(offsets),
                        'block_sizes': list(sizes),
                        'offset': o + delta,
                        'type': sub_type,
                    })

    def find(self, field_name, block=None, nth=0):
        """Locate a field by name (case-insensitive); if `block` is given, the
        field's innermost block must match it. `nth` picks among duplicate
        same-named fields in document order (e.g. H2's Barrels block has two
        'Error Angle' fields — the dual-wield one first, the normal one second)."""
        fl = field_name.lower()
        cands = [f for f in self.fields if f['name'].lower() == fl]
        if block:
            # `block` matches against the field's block chain. A single name matches
            # the INNERMOST block (back-compat). A '/'-separated path (outer/.../inner)
            # matches that SUFFIX of the chain — used to disambiguate a field that
            # appears under two different parents but the same innermost block name,
            # e.g. H2 'Rate Of Fire' under both 'Weapons Properties/Firing Patterns'
            # and 'Firing Pattern Properties/Firing Patterns'.
            parts = [p.strip().lower() for p in block.split('/')]
            k = len(parts)
            cands = [f for f in cands
                     if len(f['block_chain']) >= k
                     and [b.lower() for b in f['block_chain']][-k:] == parts]
        return cands[nth] if 0 <= nth < len(cands) else None


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

    def i32(self, o):
        return struct.unpack_from('<i', self.data, o)[0]

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
        """Resolve a tag reference to (path, meta_off) pairs. A '*' is a wildcard:
        'characters\\elite\\*' (prefix) hits every elite variant, and it may also
        appear mid/leading — e.g. 'characters\\grunt\\*plasma pistol' hits only the
        plasma-pistol grunt variants (endswith). ' & ' joins several paths of the
        same group. An exact path returns 0 or 1 entry."""
        if ' & ' in path:
            out, seen = [], set()
            for part in path.split(' & '):
                for p, o in self.find_tags(cls, part.strip()):
                    if p not in seen:
                        seen.add(p)
                        out.append((p, o))
            return out
        if '*' in path:
            match = _wildcard_matcher(path)
            return sorted((p, off) for (c, p), off in self.tags.items()
                          if c == cls and match(p))
        off = self.tags.get((cls, path))
        return [(path, off)] if off is not None else []

    def apply_field(self, cls, path, field, op, value, plugin, block=None, index=0, nth=0,
                    scale=1.0, offset=0.0, clamp_min=None, clamp_max=None,
                    zero_is=None):
        """Apply an operator to a field across every tag matching (cls, path).
        Never raises for missing tags/fields — returns a list of result dicts
        (ok/old/new or ok=False/reason) so a summary can be shown at the end.

        `scale`/`offset` map the STORED value onto the units the typed magnitude is
        expressed in — meaning = scale * stored + offset — and map back afterwards.
        The same setting can be stored differently per game: Halo 1's Starting Health
        *Modifier* is 1 when normal and rises, Halo 2's Starting Health *Damage* is 0
        when normal and falls, so meaning = -stored + 1 there (scale -1, offset 1).
        Doing it as a mapping rather than by flipping the magnitude is what makes '*'
        and '=' come out right: on the base-0 field '*2' was multiplying 0 and
        therefore doing nothing at all. Defaults are the identity, so every other
        field behaves exactly as before.

        `zero_is` covers a different case: a stored 0 that is a PLACEHOLDER rather
        than a real zero, so the operator belongs on what it stands for. Halo 2
        ships Rounds Per Second at 0 on every weapon that fires one round per
        trigger pull where Halo 3 ships 30, and the two behave the same in game;
        Shots Per Fire is 0 on automatic weapons and 1 on the rest. Without this a
        multiply on either is a guaranteed no-op, and the number shown beside the
        field contradicts its Halo 3 counterpart for no reason. Only a value of
        exactly 0 is substituted — a real reading is never touched."""
        ref = f"{cls} {path}"
        tags = self.find_tags(cls, path)
        if not tags:
            return [{'tag': ref, 'field': field, 'ok': False,
                     'reason': 'not present in this map'}]
        fld = plugin.find(field, block, nth)
        if not fld:
            return [{'tag': ref, 'field': field, 'ok': False,
                     'reason': 'field not found in plugin'}]
        fmt, _ = TYPE_FMT[fld['type']]
        ftype = fld['type']
        is_float = ftype in FLOAT_TYPES or ftype in ANGLE_TYPES
        results = []
        # Two tag paths can resolve to the SAME block, and writing both would apply
        # the operator twice to one struct (*2 landing as *4). Track the byte offsets
        # actually written and skip a tag whose data another has already covered.
        # Deduping by tag base does not catch it -- the bases differ, only the leaf
        # does not.
        written = set()
        for tpath, meta in tags:
            try:
                leaves = self.follow_all(meta, fld['block_offsets'],
                                         fld.get('block_sizes'), index)
                if not leaves:
                    results.append({'tag': f"{cls} {tpath}", 'field': field,
                                    'ok': False, 'reason': 'no populated block element'})
                    continue
                fresh = [b for b in leaves if (b + fld['offset']) not in written]
                if not fresh:
                    results.append({'tag': f"{cls} {tpath}", 'field': field,
                                    'ok': True, 'skip': True,
                                    'reason': 'shares this data with a variant '
                                              'already patched'})
                    continue
                written.update(b + fld['offset'] for b in fresh)
                leaves = fresh
                first_old = first_new = None
                for base in leaves:                 # patch every selected element
                    off = base + fld['offset']
                    old = raw_to_display(ftype, struct.unpack_from(fmt, self.data, off)[0])
                    # A placeholder 0 stands for zero_is (see the docstring). Done
                    # before the mapping below so the reported `old` is the value the
                    # operator actually worked on, not the stored 0.
                    if zero_is is not None and not old:
                        old = zero_is
                    # operate in display units (deg for angles), in the MEANING the
                    # magnitude is expressed in, then map back (see the docstring)
                    meaning = OP_FUNCS[op](scale * old + offset, value)
                    # Clamp in MEANING units, not stored units — a field declared
                    # 0..1 is a probability whatever the tag happens to store, and
                    # on an inverted mapping (scale -1) the stored bounds are the
                    # other way round. Clamping is silent by design: the point is a
                    # chance of 1.4 or -0.2 never reaching the map, and the summary
                    # already reports the value that was actually written.
                    if clamp_min is not None:
                        meaning = max(meaning, clamp_min)
                    if clamp_max is not None:
                        meaning = min(meaning, clamp_max)
                    new = (meaning - offset) / scale
                    new = float(new) if is_float else int(round(new))
                    struct.pack_into(fmt, self.data, off, display_to_raw(ftype, new))
                    if first_old is None:
                        first_old, first_new = old, new
                r = {'tag': f"{cls} {tpath}", 'field': field, 'ok': True,
                     'old': first_old, 'new': first_new}
                if len(leaves) > 1:
                    r['elements'] = len(leaves)
                results.append(r)
            except Exception as e:
                results.append({'tag': f"{cls} {tpath}", 'field': field,
                                'ok': False, 'reason': str(e)})
        return results

    def follow(self, meta_off, block_offsets, block_sizes=None, index=0):
        """Walk a reflexive chain from a tag's meta to a leaf struct. Each H1
        reflexive is [count:i32][ptr:u32]. `index` selects the element of the
        INNERMOST block (outer blocks always use element 0); it needs the block's
        element size, so pass block_sizes (parallel to block_offsets)."""
        if not isinstance(index, int):
            # 'all' (or a per-level list) is a follow_all spec. This walker only
            # understands an int, and multiplying a string by the element size used
            # to throw -- swallowed by the callers' except, so every blocked Halo 1
            # field declared `index: "all"` read back as no value at all. A single
            # reader wants one value, so hand back the first populated leaf.
            leaves = self.follow_all(meta_off, block_offsets, block_sizes, index)
            if not leaves:
                raise IndexError('no populated element for index %r' % (index,))
            return leaves[0]
        cur = meta_off
        n = len(block_offsets)
        for i, refl in enumerate(block_offsets):
            ptr = self.u32(cur + refl + 4)
            base = (ptr - self.magic) & 0xFFFFFFFF
            idx = index if i == n - 1 else 0
            size = block_sizes[i] if block_sizes else 0
            cur = base + idx * size
        return cur

    def follow_all(self, meta_off, block_offsets, block_sizes=None, index=0):
        """Like `follow`, but returns EVERY leaf struct selected by `index`
        (see normalize_index_spec). `index` may be an int (legacy: innermost=i),
        'all' (enumerate every element at every level), or a per-level list such
        as [0, 'all']. Reads each reflexive's count and skips empty/short blocks,
        so it returns [] when nothing is populated (never fabricates offsets)."""
        n = len(block_offsets)
        if n == 0:
            return [meta_off]
        sel = normalize_index_spec(index, n)
        cur = [meta_off]
        for i, refl in enumerate(block_offsets):
            size = block_sizes[i] if block_sizes else 0
            nxt = []
            for c in cur:
                count = self.i32(c + refl)
                ptr = self.u32(c + refl + 4)
                if ptr == 0 or count <= 0:
                    continue
                arr = (ptr - self.magic) & 0xFFFFFFFF
                s = sel[i]
                idxs = range(count) if s == 'all' else ([s] if 0 <= s < count else [])
                for idx in idxs:
                    nxt.append(arr + idx * size)
            cur = nxt
        return cur

    def resolve(self, cls, path, field, plugin, block=None, index=0, nth=0):
        """Return (base_offset, field_dict) for a field, or None."""
        meta = self.get_tag_meta(cls, path)
        if meta is None:
            return None
        fld = plugin.find(field, block, nth)
        if not fld:
            return None
        base = self.follow(meta, fld['block_offsets'], fld.get('block_sizes'), index)
        return base, fld

    def read(self, cls, path, field, plugin, block=None, index=0, nth=0):
        r = self.resolve(cls, path, field, plugin, block, index, nth)
        if r is None:
            return None
        base, fld = r
        fmt, _ = TYPE_FMT[fld['type']]
        return raw_to_display(fld['type'], struct.unpack_from(fmt, self.data, base + fld['offset'])[0])

    def read_first(self, cls, path, field, plugin, block=None, index=0, nth=0):
        """Read a field from the first tag matching (cls, path); handles the
        variant '*' form. Returns None if unresolved."""
        tags = self.find_tags(cls, path)
        if not tags:
            return None
        fld = plugin.find(field, block, nth)
        if not fld:
            return None
        try:
            base = self.follow(tags[0][1], fld['block_offsets'], fld.get('block_sizes'), index)
            fmt, _ = TYPE_FMT[fld['type']]
            return raw_to_display(fld['type'], struct.unpack_from(fmt, self.data, base + fld['offset'])[0])
        except Exception:
            return None

    def read_all(self, cls, path, field, plugin, block=None, index=0, nth=0):
        """(tag_path, value) for every tag matching (cls, path) — one entry per
        variant. Skips any that don't resolve. Empty if the field is unknown."""
        fld = plugin.find(field, block, nth)
        if not fld:
            return []
        fmt, _ = TYPE_FMT[fld['type']]
        out = []
        for tpath, meta in self.find_tags(cls, path):
            try:
                base = self.follow(meta, fld['block_offsets'],
                                   fld.get('block_sizes'), index)
                raw = struct.unpack_from(fmt, self.data, base + fld['offset'])[0]
                out.append((tpath, raw_to_display(fld['type'], raw)))
            except Exception:
                pass
        return out

    def read_all_leaves(self, cls, path, field, plugin, block=None, index=0, nth=0):
        """Like read_all, but returns (tag_path, [value per selected leaf]) — every
        element the index spec picks (e.g. index='all' across a multi-element block),
        per variant tag. Variants whose block is empty are omitted. Used to show a
        collapsed effect's full vanilla spread (H1-style per-variant listing extended
        to H2's per-index blocks)."""
        fld = plugin.find(field, block, nth)
        if not fld:
            return []
        fmt, _ = TYPE_FMT[fld['type']]
        out = []
        for tpath, meta in self.find_tags(cls, path):
            vals = []
            for base in self.follow_all(meta, fld['block_offsets'], fld.get('block_sizes'), index):
                try:
                    vals.append(raw_to_display(fld['type'],
                                struct.unpack_from(fmt, self.data, base + fld['offset'])[0]))
                except Exception:
                    pass
            if vals:
                out.append((tpath, vals))
        return out

    def read_tag_field(self, tag_base, field, plugin, block=None, index=0, nth=0):
        """Read a field from a tag by its meta-offset base (mirrors Halo2Map's
        signature so per-tag code can work across both parsers)."""
        fld = plugin.find(field, block, nth)
        if not fld:
            return None
        try:
            base = self.follow(tag_base, fld['block_offsets'], fld.get('block_sizes'), index)
            fmt, _ = TYPE_FMT[fld['type']]
            return raw_to_display(fld['type'], struct.unpack_from(fmt, self.data, base + fld['offset'])[0])
        except Exception:
            return None

    def write_tag_field(self, tag_base, field, value, plugin, block=None, index=0, nth=0):
        """Write a field by meta-offset base (mirrors Halo2Map). Returns old value."""
        fld = plugin.find(field, block, nth)
        if not fld:
            return None
        try:
            base = self.follow(tag_base, fld['block_offsets'], fld.get('block_sizes'), index)
            fmt, _ = TYPE_FMT[fld['type']]
            ftype = fld['type']
            off = base + fld['offset']
            old = raw_to_display(ftype, struct.unpack_from(fmt, self.data, off)[0])
            value = float(value) if (ftype in FLOAT_TYPES or ftype in ANGLE_TYPES) else int(round(value))
            struct.pack_into(fmt, self.data, off, display_to_raw(ftype, value))
            return old
        except Exception:
            return None

    def write(self, cls, path, field, plugin, value, block=None, index=0, nth=0):
        """Write a value into the in-memory buffer (call save() to persist).
        Returns the previous value, or None if unresolved."""
        r = self.resolve(cls, path, field, plugin, block, index, nth)
        if r is None:
            return None
        base, fld = r
        fmt, _ = TYPE_FMT[fld['type']]
        ftype = fld['type']
        off = base + fld['offset']
        old = raw_to_display(ftype, struct.unpack_from(fmt, self.data, off)[0])
        if ftype in FLOAT_TYPES or ftype in ANGLE_TYPES:
            value = float(value)
        else:
            value = int(value)
        struct.pack_into(fmt, self.data, off, display_to_raw(ftype, value))
        return old

    def grow_block(self, tag_base, block_offset, elem_size, new_elems):
        """Append `new_elems` (elem_size-byte blocks) to the reflexive at
        tag_base+block_offset, mirroring Halo2Map.grow_block but for the H1 cache.

        H1 addresses tag data by a magic-relative pointer (offset = ptr - magic) and
        the tag-data blob is the LAST region in the file (index_off + metaSize@0x14
        == EOF), so appending at EOF extends that blob in place: the block is
        relocated there (existing elements copied verbatim, new ones after), the
        reflexive repointed with the higher count, and the header meta size@0x14 and
        file size@0x08 grown. Every existing pointer is magic-relative and unmoved,
        so nothing else needs fixing; the old element bytes are orphaned. Element
        bytes are copied verbatim — embedded tagRefs keep their idents and any child
        reflexive pointers keep addressing the unmoved child data, so a caller
        copying a subtree must fix those pointers up itself. Returns the new block's
        file offset. save() must follow.

        H1 has no segment-alignment rule (unlike H2), but pointer targets are padded
        to 4 bytes. NOTE: restructures the map; verify MCC loads a grown map."""
        if any(len(e) != elem_size for e in new_elems):
            raise ValueError("every new element must be elem_size bytes")
        if not new_elems:
            raise ValueError("no elements to append")
        count = self.u32(tag_base + block_offset)
        old_ptr = self.u32(tag_base + block_offset + 4)
        existing = b'' if count == 0 else \
            bytes(self.data[(old_ptr - self.magic) & 0xFFFFFFFF:
                            ((old_ptr - self.magic) & 0xFFFFFFFF) + count * elem_size])
        blob = existing + b''.join(bytes(e) for e in new_elems)
        total = count + len(new_elems)
        delta = (len(blob) + 3) & ~3
        new_off = len(self.data)
        self.data += blob + bytearray(delta - len(blob))
        ptr = (new_off + self.magic) & 0xFFFFFFFF
        struct.pack_into('<I', self.data, tag_base + block_offset, total)      # count
        struct.pack_into('<I', self.data, tag_base + block_offset + 4, ptr)    # ptr
        meta_size = self.u32(0x14) + delta
        file_size = self.u32(0x08) + delta
        struct.pack_into('<I', self.data, 0x14, meta_size)
        struct.pack_into('<I', self.data, 0x08, file_size)
        return new_off

    def append_raw(self, blob):
        """Append raw bytes to the tag-data blob at EOF (4-aligned), growing the
        header meta size@0x14 and file size@0x08. Returns the new bytes' file
        offset; address them with a magic-relative pointer (off + magic). Used to
        relocate a child sub-block so a copied element can own its own copy instead
        of pointing into another tag. save() must follow."""
        delta = (len(blob) + 3) & ~3
        new_off = len(self.data)
        self.data += bytes(blob) + bytearray(delta - len(blob))
        struct.pack_into('<I', self.data, 0x14, self.u32(0x14) + delta)
        struct.pack_into('<I', self.data, 0x08, self.u32(0x08) + delta)
        return new_off

    def save(self, out_path):
        with open(out_path, 'wb') as f:
            f.write(self.data)


if __name__ == '__main__':
    import sys
    map_path = sys.argv[1] if len(sys.argv) > 1 else \
        r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\halo1\maps\a10.map"
    plugin_path = sys.argv[2] if len(sys.argv) > 2 else \
        r"F:\SteamLibrary\steamapps\common\HCEEK\Assembly-1-2023-11-29-1702446457\Plugins\Halo1\matg.xml"
    m = HaloMap(map_path)
    print(f"map={Path(map_path).name} version={m.version} tags={m.tag_count} magic={m.magic:#x}")
    pl = Plugin(plugin_path)
    print(f"plugin fields parsed: {len(pl.fields)}")
    for diff in ('Easy', 'Normal', 'Hard', 'Impossible'):
        v = m.read('matg', 'globals\\globals', f'{diff} Enemy Damage', pl, block='Difficulty')
        print(f"  {diff} Enemy Damage = {v}")
