r"""reach_insert_block.py -- give an INHERITING Reach character its own tag block.

THE PROBLEM. Reach `char` tags inherit through `Parent Character`, and several
Hero-class enemies define nothing of their own: elite_story populates only Variants,
General Properties and Campaign Metagame Bucket, so its Vitality Properties reflexive
is count 0 / pointer null. A card pointed at it patches nothing, and a card pointed at
its parent buffs every sibling -- elite_ultra in this case. Repointing the parent to
elite_general is not a fix either: elite_general's OWN parent is elite_ultra, so the
Zealot would simply become the General (one card moving both) and swap its equipment.

THE APPROACH. Give the child its own block, so it can be tuned in isolation.
Growing a reflexive normally means relocating tag data and fixing up every pointer,
which halo3_map explicitly does not implement. This sidesteps that: a Reach map's tag
partitions carry a large run of trailing ZERO bytes (m10's P1 has 0x6CAA, P2 0xA4B4)
against a Vitality Properties element of only 0x64. Writing the new element into that
slack and pointing the empty reflexive at it moves NOTHING, so there are no fixups --
the only edits are the element itself plus the tag's own count and pointer.

The element is seeded with a byte-for-byte copy of the parent's, so the child starts
out behaving exactly as it did; only the fields explicitly overridden change.

WHAT IS AND IS NOT PROVEN. The tool verifies statically that the file now reads back
the new block and the intended values, and that the checksum is consistent. It CANNOT
show that the engine honours a child's own block rather than resolving inheritance
some other way, nor that the slack is truly unclaimed. Those need one in-game look.

    python sprint_toolkit/reach_insert_block.py --map m10 \
        --tag objects/characters/elite/ai/elite_story \
        --block "Vitality Properties" \
        --set "Normal Body Vitality=5000" --set "Legendary Body Vitality=5000"

    # make the subject impossible to miss, for that in-game look
    python sprint_toolkit/reach_insert_block.py --map m10 --repoint-elites
    python sprint_toolkit/reach_insert_block.py --map m10 --restore
"""

import argparse
import os
import struct
import sys
import shutil
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import halo_patch                                    # noqa: E402
import reach_census as rc                            # noqa: E402

SEP = chr(92)
BACKUP_SUFFIX = '.preinsert'
# Keep clear of the very end of the partition and stay 16-byte aligned; only carve
# from a zero run far larger than the request, so a short run that happens to be real
# data is never touched.
SLACK_MARGIN = 0x40
MIN_RUN = 0x400


def plugin_block(group, block_name):
    for sub in rc.PLUGIN_SUBDIRS:
        p = os.path.join(rc.PLUGINS, sub, group + '.xml')
        if not os.path.isfile(p):
            continue
        for ch in ET.parse(p).getroot():
            if ch.get('name') == block_name and ch.get('offset'):
                fields = {}
                for f in ch:
                    if f.get('name') and f.get('offset'):
                        fields[f.get('name')] = (f.tag.lower(), int(f.get('offset'), 16))
                return int(ch.get('offset'), 16), int(ch.get('elementSize', '0'), 16), fields
    raise SystemExit('block %r not found in %s plugin' % (block_name, group))


def char_base(m, path):
    for t in m.tags:
        if t.get('class') == 'char' and t.get('name') == path:
            return t['base']
    return None


def parent_of(m, base):
    ident = m.u32(base + 0x4 + 0xC)
    if ident == 0xFFFFFFFF:
        return None
    t = m.tag(ident & 0xFFFF)
    return t if t and t.get('base') is not None else None


def partition_of(m, off):
    for i, (la, sz, fb) in enumerate(m.partitions):
        if fb is not None and sz and fb <= off < fb + sz:
            return i
    return None


def find_slack(m, size, prefer=None):
    """Carve `size` bytes from the tail of a zero run in a tag partition.

    `prefer` is the partition holding the tag being edited, and it wins outright: on
    Reach every char tag and the scenario itself live in the last partition, so the
    new element belongs beside them rather than in whichever partition happens to have
    the longest zero run. Falls back to the largest run elsewhere.

    Returns a file offset whose address round-trips through off2data, or None --
    the reflexive pointer has to be expressible in the >>2 biased space."""
    best = None
    for i, (la, sz, fb) in enumerate(m.partitions):
        if not sz or fb is None:
            continue
        end = fb + sz
        run = 0
        while run < sz and m.data[end - 1 - run] == 0:
            run += 1
            if run > 0x40000:
                break
        if run < MIN_RUN or run < size + SLACK_MARGIN:
            continue
        off = (end - SLACK_MARGIN - size) & ~0xF
        if m.off2data(off) is None or m.data2off(m.off2data(off)) != off:
            continue
        cand = (off, run, i)
        if i == prefer:
            return cand
        if best is None or run > best[1]:
            best = cand
    return best


def set_field(m, elem_off, fields, name, value):
    if name not in fields:
        raise SystemExit('field %r not in block; have: %s'
                         % (name, ', '.join(sorted(fields))))
    kind, off = fields[name]
    if kind.startswith('float'):
        struct.pack_into('<f', m.data, elem_off + off, float(value))
    elif kind in ('int16', 'enum16', 'short'):
        struct.pack_into('<h', m.data, elem_off + off, int(float(value)))
    elif kind in ('int8', 'enum8', 'flags8'):
        struct.pack_into('<b', m.data, elem_off + off, int(float(value)))
    else:
        struct.pack_into('<i', m.data, elem_off + off, int(float(value)))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--map', required=True)
    ap.add_argument('--tag', help='char tag path, forward or back slashes')
    ap.add_argument('--block', default='Vitality Properties')
    ap.add_argument('--set', action='append', default=[], metavar='FIELD=VALUE')
    ap.add_argument('--repoint-elites', action='store_true',
                    help="point every elite\\ai\\* character-palette slot at --tag, so "
                         "the subject cannot be missed in game")
    ap.add_argument('--restore', action='store_true',
                    help='put back the %s backup' % BACKUP_SUFFIX)
    a = ap.parse_args()

    path = os.path.join(rc.MAPS, a.map + '.map')
    backup = path + BACKUP_SUFFIX
    if a.restore:
        if not os.path.exists(backup):
            raise SystemExit('no backup at %s' % backup)
        shutil.copyfile(backup, path)
        os.remove(backup)
        print('restored %s' % path)
        return
    if not os.path.exists(backup):
        shutil.copyfile(path, backup)
        print('backed up -> %s' % backup)

    m = halo_patch.open_map(path, rc.GAME)
    tag_path = (a.tag or '').replace('/', SEP)

    if a.tag:
        base = char_base(m, tag_path)
        if base is None:
            raise SystemExit('%s not in %s' % (a.tag, a.map))
        blk_off, esz, fields = plugin_block('char', a.block)
        count = m.i32(base + blk_off)
        print('%s: %s count=%d' % (a.tag.rsplit('/', 1)[-1], a.block, count))
        if count == 0:
            par = parent_of(m, base)
            if par is None:
                raise SystemExit('no parent to copy the block from')
            pcount = m.i32(par['base'] + blk_off)
            if pcount < 1:
                raise SystemExit('parent %s has no %s either'
                                 % (par['name'], a.block))
            psrc = m.data2off(m.u32(par['base'] + blk_off + 4))
            spot = find_slack(m, esz, prefer=partition_of(m, base))
            if spot is None:
                raise SystemExit('no usable slack for %d bytes' % esz)
            off, run, part = spot
            print('  parent %s supplies the template (%d element(s))'
                  % (par['name'].rsplit(SEP, 1)[-1], pcount))
            print('  slack: partition P%d, zero run 0x%X, taking 0x%X at file 0x%X'
                  % (part, run, esz, off))
            m.data[off:off + esz] = m.data[psrc:psrc + esz]
            struct.pack_into('<i', m.data, base + blk_off, 1)
            struct.pack_into('<I', m.data, base + blk_off + 4, m.off2data(off))
            elem = off
        else:
            elem = m.data2off(m.u32(base + blk_off + 4))
            print('  already has its own block; editing in place')
        for kv in a.set:
            k, _, v = kv.partition('=')
            set_field(m, elem, fields, k.strip(), v.strip())
            print('  set %s = %s' % (k.strip(), v.strip()))

    if a.repoint_elites:
        c = rc.Census(a.map)
        pal_off, pal_esz = c.blocks['Character Palette']
        n = m.i32(c.base + pal_off)
        arr = m.data2off(m.u32(c.base + pal_off + 4))
        target = None
        for t in m.tags:
            if t.get('class') == 'char' and t.get('name') == tag_path:
                target = t
        if target is None:
            raise SystemExit('--repoint-elites needs a valid --tag')
        ident = m.u32(arr + 0 * pal_esz + 0xC)
        newid = (ident & 0xFFFF0000) | (target['index'] & 0xFFFF)
        hit = 0
        for i in range(n):
            e = arr + i * pal_esz
            cur = m.u32(e + 0xC)
            t = m.tag(cur & 0xFFFF) if cur != 0xFFFFFFFF else None
            nm = (t or {}).get('name') or ''
            if (SEP + 'elite' + SEP) in nm and nm != tag_path:
                struct.pack_into('<I', m.data, e + 0xC,
                                 (cur & 0xFFFF0000) | (target['index'] & 0xFFFF))
                hit += 1
        print('repointed %d elite palette slots at %s'
              % (hit, tag_path.rsplit(SEP, 1)[-1]))

    m.save()

    # --- static verification, on a freshly reopened file ---
    m2 = halo_patch.open_map(path, rc.GAME)
    print('\nverify:')
    if a.tag:
        base2 = char_base(m2, tag_path)
        blk_off, esz, fields = plugin_block('char', a.block)
        print('  %s count is now %d' % (a.block, m2.i32(base2 + blk_off)))
        reg = halo_patch.PluginRegistry(rc.PLUGINS, list(rc.PLUGIN_SUBDIRS))
        pl = reg.get('char')
        for k in ('Normal Body Vitality', 'Legendary Body Vitality',
                  'Normal Shield Vitality', 'Legendary Shield Vitality'):
            if k in fields:
                v = m2.read_all('char', tag_path, k, pl, block=a.block, index='all')
                print('     %-28s %s' % (k, [x for _, x in v]))
    print('  checksum self-consistent: %s'
          % (m2.u32(m2.CHECKSUM_OFF) == m2.update_checksum()))


if __name__ == '__main__':
    main()
