r"""Which tags in the ODST maps actually USE a block or field?

The plugin says a block exists on every tag of a class; it does not say which tags
populate it. "ODST added Kungfu Properties" is only interesting if something has
one. This reads the shipped maps and answers that.

    python odst_tagfield.py char "Kungfu Properties"                # block users
    python odst_tagfield.py char "Engage Properties" "Default Combat Range"
    python odst_tagfield.py weap "New Triggers" "Target Tracking Lock Time"
"""
import argparse
import collections
import os
import struct
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MAPS = (r"C:\Program Files (x86)\Steam\steamapps\common"
        r"\Halo The Master Chief Collection\halo3odst\maps")
LEVELS = ['h100', 'sc100', 'sc110', 'sc120', 'sc130', 'sc140', 'sc150', 'l200', 'l300']
BLOCKS = ('reflexive', 'tagblock', 'block', 'struct')


def _int(s):
    if not s:
        return None
    return int(s, 16) if s.lower().startswith('0x') else int(s)


def locate(cls, block, field=None):
    """(block_offset, entry_size, field_offset, field_type) from the ODST plugin."""
    import odst_fielddiff as F
    root = ET.parse(F._plugin(F.ODST_DIRS, cls)).getroot()
    for node in root.iter():
        if node.tag.lower() not in BLOCKS:
            continue
        if (node.get('name') or '').strip().lower() != block.lower():
            continue
        boff = _int(node.get('offset'))
        esz = _int(node.get('entrySize') or node.get('elementSize') or 0)
        if field is None:
            return boff, esz, None, None
        for ch in node:
            if (ch.get('name') or '').strip().lower() == field.lower():
                return boff, esz, _int(ch.get('offset')), ch.tag.lower()
        return boff, esz, None, None
    return None, None, None, None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cls')
    ap.add_argument('block')
    ap.add_argument('field', nargs='?')
    ap.add_argument('--levels', nargs='*', default=LEVELS)
    a = ap.parse_args(argv)

    from halo3_map import Halo3Map
    boff, esz, foff, ftype = locate(a.cls, a.block, a.field)
    if boff is None:
        raise SystemExit('block %r not found in the ODST %s plugin' % (a.block, a.cls))
    print('%s > %s @0x%X entry 0x%X%s\n'
          % (a.cls, a.block, boff, esz,
             ('  field %s @0x%X %s' % (a.field, foff, ftype)) if foff is not None else ''))

    users = collections.defaultdict(set)      # tag name -> {values or 'n entries'}
    for lvl in a.levels:
        path = os.path.join(MAPS, lvl + '.map')
        if not os.path.exists(path):
            continue
        m = Halo3Map(path)
        for t in m.tags:
            if t['class'] != a.cls or not t.get('name'):
                continue
            try:
                entries = list(m.follow_all(t['base'], [boff], [esz], 'all'))
            except Exception:
                continue
            if not entries:
                continue
            if foff is None:
                users[t['name']].add('%d entry(ies)' % len(entries))
                continue
            for el in entries:
                try:
                    v = struct.unpack_from('<f', m.data, el + foff)[0]
                except Exception:
                    continue
                if v == v and v != 0.0:       # skip NaN and unset zeros
                    users[t['name']].add(round(v, 4))

    if not users:
        print('nothing in the ODST campaign populates it.')
        return 0
    print('%d tag(s) use it:' % len(users))
    for name in sorted(users):
        vals = sorted(users[name], key=str)
        print('  %-56s %s' % (name, ', '.join(str(v) for v in vals[:8])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
