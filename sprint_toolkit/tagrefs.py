"""Walk a tag's DECLARED tagRef fields, following tagblocks properly.

A raw scan of a tag header for 4-byte datum indices produces confident nonsense: any
float or count whose low word happens to index a real tag reads as a reference. That
is what put "weap storm_needler" on the Autosentry's projectile. This walks only
offsets the plugin declares as tagRef, through the block structure, so a hit is a hit.
"""
import os
import struct
import xml.etree.ElementTree as ET

_CACHE = {}


def _spec(plugin_dir, sub, cls):
    """[(path, offset)] tagRefs at the root, plus [(name, off, esz, children)] blocks."""
    key = (sub, cls)
    if key in _CACHE:
        return _CACHE[key]
    f = os.path.join(plugin_dir, sub, cls + '.xml')
    if not os.path.exists(f):
        _CACHE[key] = None
        return None

    def node(n, path):
        refs, blocks = [], []
        for c in n:
            nm = c.get('name')
            if not nm or c.get('offset') is None:
                continue
            off = int(c.get('offset'), 16)
            if c.tag.lower() == 'tagblock':
                sz = c.get('elementSize')
                blocks.append((nm, off, int(sz, 16) if sz else 0,
                               node(c, (path + '/' + nm).strip('/'))))
            elif c.tag.lower() == 'tagref':
                refs.append(((path + '/' + nm).strip('/'), off))
        return refs, blocks

    _CACHE[key] = node(ET.parse(f).getroot(), '')
    return _CACHE[key]


def refs_of(m, base, spec, want=None, limit=4096):
    """[(field path, datum)] for every declared tagRef reachable from `base`."""
    out = []

    def walk(b, sp, depth):
        if depth > 3:
            return
        refs, blocks = sp
        for path, off in refs:
            try:
                d = struct.unpack_from('<I', m.data, b + off + 0xC)[0]
            except Exception:
                continue
            if d not in (0, 0xFFFFFFFF):
                out.append((path, d))
        for nm, off, esz, sub in blocks:
            if not esz:
                continue
            try:
                cnt = m.i32(b + off)
                ptr = m.u32(b + off + 4)
            except Exception:
                continue
            if cnt <= 0 or cnt > limit or ptr == 0:
                continue
            arr = m.data2off(ptr) if hasattr(m, 'data2off') else None
            if arr is None:
                continue
            for i in range(min(cnt, 64)):
                walk(arr + i * esz, sub, depth + 1)

    walk(base, spec, 0)
    return out
