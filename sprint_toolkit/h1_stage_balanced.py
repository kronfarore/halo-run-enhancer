r"""Write a Halo 1 port's catalog BALANCE rows into one built map -- a test stage of the
balanced setting without a full enhancer patch.

Each row (class / tag / field / block / value, weapon_ports_catalog.json) is resolved
through the Assembly Halo1 plugin by field NAME: at the tag's root, or in element 0 of
the named block (`index` when the row gives one). A `<field> Max` row is the second
float of a range field (rangef / ranged: +4). Degree fields are written in radians, as the
tag stores them (the catalog keeps degrees, like the plugin shows them). Every write is
printed before -> after.

    python h1_stage_balanced.py <map> "Energy Blade" "Flak Cannon" [--dry]
"""
import argparse
import json
import math
import os
import struct
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import paths              # noqa: E402
import halo_patch         # noqa: E402

PLUGINS = os.path.dirname(paths.SCNR_XML)
CATALOG = os.path.join(ROOT, 'weapon_ports_catalog.json')
RANGES = ('rangef', 'ranged')


def plugin_field(cls, field, block):
    """(offset, type, block offset, block element size) for a field name."""
    root = ET.parse(os.path.join(PLUGINS, cls + '.xml')).getroot()
    name, second = (field[:-4], True) if field.endswith(' Max') else (field, False)
    scope, boff, bsize = root, None, None
    if block:
        b = next(e for e in root.iter() if e.tag.lower() in ('tagblock', 'reflexive')
                 and e.get('name') == block)
        scope, boff, bsize = b, int(b.get('offset'), 16), int(b.get('elementSize'), 16)
    for e in scope:
        if e.get('name') == name and e.get('offset'):
            off = int(e.get('offset'), 16)
            if second:
                if e.tag.lower() not in RANGES:
                    continue
                off += 4
            return off, e.tag.lower(), boff, bsize
    raise SystemExit('%s: no field %r%s' % (cls, field, ' in ' + block if block else ''))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('map')
    ap.add_argument('ports', nargs='+')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    cat = json.load(open(CATALOG, encoding='utf-8'))
    m = halo_patch.open_map(a.map, 'Halo 1')
    d = m.data
    for port in a.ports:
        e = next(x for x in cat['Halo 1'] if x['weapon'] == port)
        print('== %s' % port)
        for r in e['balance']:
            meta = m.tags.get((r['class'], r['tag']))
            if meta is None:
                print('   MISSING tag %s %s' % (r['class'], r['tag']))
                continue
            off, typ, boff, bsize = plugin_field(r['class'], r['field'], r.get('block'))
            base = meta
            if boff is not None:
                count, ptr = struct.unpack_from('<II', d, meta + boff)
                idx = r.get('index') or 0
                if idx >= count:
                    print('   %s: block %s has %d element(s)' % (r['field'], r['block'], count))
                    continue
                base = ((ptr - m.magic) & 0xFFFFFFFF) + idx * bsize
            at = base + off
            value = r['value']
            if typ in ('degree', 'ranged'):
                value = math.radians(value)
            old = struct.unpack_from('<f', d, at)[0]
            if not a.dry:
                struct.pack_into('<f', d, at, value)
            shown = (lambda x: math.degrees(x)) if typ in ('degree', 'ranged') else (lambda x: x)
            print('   %-28s %-24s %10.4g -> %-10.4g %s' % (r['field'], r['tag'].rsplit('\\', 1)[-1],
                                                         shown(old), r['value'], typ))
    if not a.dry:
        open(a.map, 'r+b').write(bytes(d))
        print('wrote %s' % a.map)


if __name__ == '__main__':
    main()
