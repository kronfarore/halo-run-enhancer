r"""insert_block.py -- give an INHERITING character its own tag block.

THE PROBLEM. Character tags inherit through `Parent Character` (tagRef at +0x4 in
Halo 2, Halo 3, ODST and Reach alike), and several Hero-class enemies define nothing
of their own -- Halo 2's elite_honor_guard and Halo 3/ODST's elite_specops_commander
populate NO blocks at all, and Reach's elite_story populates only three. Their
Vitality Properties reflexive is count 0 / pointer null. A card pointed at such a
variant patches nothing; a card pointed at its parent buffs every sibling. See
ModifierDatabase.get_boss_modifiers_filtered, which states that rule.

TWO STRATEGIES, chosen per parser rather than per game:

  * SLACK (Halo 3, ODST, Reach -- anything with `partitions`). Growing a reflexive
    normally means relocating tag data and fixing up every pointer, which halo3_map
    does not implement. This sidesteps that: the tag-data partition carries a long run
    of trailing ZERO bytes (Reach m10 0xD62E, Halo 3 050 0xD18C, ODST sc110 0xE8EC)
    against a Vitality Properties element of 0x64-0x80. The element is written into
    that slack and the empty reflexive pointed at it. Nothing moves, so there is
    nothing to fix up. CONFIRMED IN GAME on Reach m10: elite_story given 5000/5000
    with every Elite palette slot repointed at him made every Elite unkillable, so the
    engine does honour a child's own block and the slack is genuinely free.

  * APPEND (Halo 2 -- anything with `append_block_element`). halo2_map already
    implements proper growth: it relocates the block to end-of-image, pads to the
    0x1000 segment alignment MCC requires, and grows file_size/meta_size/
    tag_data_size. That is strictly better than slack, so it is preferred where it
    exists. NOTE halo2_map's own docstring flags that a grown map has not been
    verified to load in MCC -- unlike the slack path, the Halo 2 route is still
    untested in game.

The new element is seeded with a byte-for-byte copy of the PARENT's, so the child
starts out behaving exactly as it did and only the overridden fields change. An
element built from zeroes would silently be a different character.

    python sprint_toolkit/insert_block.py --game "Halo 2" --map 06a \
        --tag objects/characters/elite/ai/elite_honor_guard \
        --block "Vitality Properties" --set "Legendary Body Vitality=500"

    python sprint_toolkit/insert_block.py --game "Halo Reach" --map m10 \
        --tag objects/characters/elite/ai/elite_story --repoint-family elite
    python sprint_toolkit/insert_block.py --game "Halo Reach" --map m10 --restore
"""

import argparse
import os
import shutil
import struct
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import halo_patch                                    # noqa: E402
import map_vault as V                                # noqa: E402

PLUGINS = os.environ.get(
    'ASSEMBLY_PLUGINS',
    r"C:\Program Files (x86)\Steam\steamapps\common\HCEEK"
    r"\Assembly-1-2023-11-29-1702446457\Plugins")
SEP = chr(92)
BACKUP_SUFFIX = '.preinsert'
PARENT_REF = 0x4            # the tagRef itself; same offset in every game's char tag
# ...but the DATUM INSIDE a tagRef is not. Halo 2's tagRefs are 8 bytes with the datum
# at +0x4; Halo 3, ODST and Reach use 16 bytes with it at +0xC. Reading Halo 2 with the
# Halo 3 offset silently picks a wrong parent and seeds the new element from garbage,
# which is exactly what it did before this was pinned down.
TAGREF_DATUM = {'Halo 2': 0x4}
DEFAULT_TAGREF_DATUM = 0xC

# Only carve from a zero run far larger than the request, and stay clear of the very
# end of the partition, so a short run that happens to be real data is never touched.
SLACK_MARGIN = 0x40
MIN_RUN = 0x400

SUBDIRS = {'Halo 2': ['Halo2MCC', 'Halo2'], 'Halo 3': ['Halo3MCC', 'Halo3'],
           'Halo 3: ODST': ['ODSTMCC', 'ODST'], 'Halo Reach': ['ReachMCC', 'Reach']}


def plugin_block(game, group, block_name):
    """(block offset, element size, {field: (kind, offset)}) from the game's plugin."""
    for sub in SUBDIRS[game]:
        p = os.path.join(PLUGINS, sub, group + '.xml')
        if not os.path.isfile(p):
            continue
        for ch in ET.parse(p).getroot():
            if ch.get('name') == block_name and ch.get('offset'):
                fields = {f.get('name'): (f.tag.lower(), int(f.get('offset'), 16))
                          for f in ch if f.get('name') and f.get('offset') is not None}
                return (int(ch.get('offset'), 16),
                        int(ch.get('elementSize', '0'), 16), fields)
    raise SystemExit('block %r not found in the %s %s plugin' % (block_name, game, group))


def tag_base(m, group, path):
    if isinstance(m.tags, dict):                       # Halo 1 shape
        return m.tags.get((group, path))
    for t in m.tags:
        if t.get('class') == group and t.get('name') == path:
            return t['base']
    return None


def tag_row(m, group, path):
    if isinstance(m.tags, dict):
        return None
    for t in m.tags:
        if t.get('class') == group and t.get('name') == path:
            return t
    return None


def parent_tag(m, base, datum=DEFAULT_TAGREF_DATUM):
    ident = m.u32(base + PARENT_REF + datum)
    if ident == 0xFFFFFFFF:
        return None
    t = m.tag(ident & 0xFFFF)
    return t if t and t.get('base') is not None else None


def seed_ancestor(m, base, blk_off, datum=DEFAULT_TAGREF_DATUM):
    """Nearest ancestor that actually POPULATES the block.

    One hop is not enough: Halo 3's elite_specops_commander inherits from
    elite_specops, which is itself empty, and the values only appear further up at
    `elite`. Walking to the nearest populated ancestor is also the semantically right
    seed -- it is exactly what the engine resolves for this character today."""
    seen, cur = set(), parent_tag(m, base, datum)
    while cur is not None and cur['name'] not in seen:
        seen.add(cur['name'])
        if m.i32(cur['base'] + blk_off) > 0:
            return cur
        cur = parent_tag(m, cur['base'], datum)
    return None


def block_data_off(m, base, blk_off):
    """File offset of a block's first element, across both pointer models."""
    ptr = m.u32(base + blk_off + 4)
    return m.data2off(ptr) if hasattr(m, 'data2off') else m.p2o(ptr)


def partition_of(m, off):
    for i, (la, sz, fb) in enumerate(m.partitions):
        if fb is not None and sz and fb <= off < fb + sz:
            return i
    return None


def find_slack(m, size, prefer=None):
    """Carve `size` bytes from the tail of a zero run. `prefer` (the partition holding
    the tag) wins outright -- on Reach and Halo 3 alike every char tag lives in the
    last partition, so the element belongs beside them."""
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


def insert(m, base, blk_off, esz, seed):
    """Give an empty reflexive one element seeded with `seed`. Returns
    (element file offset, strategy name)."""
    if hasattr(m, 'append_block_element'):             # Halo 2: proper growth
        off = m.append_block_element(base, blk_off, esz, seed)
        return off, 'append (end-of-image, segments grown)'
    spot = find_slack(m, esz, prefer=partition_of(m, base))
    if spot is None:
        raise SystemExit('no usable slack for %d bytes' % esz)
    off, run, part = spot
    m.data[off:off + esz] = seed
    struct.pack_into('<i', m.data, base + blk_off, 1)
    struct.pack_into('<I', m.data, base + blk_off + 4, m.off2data(off))
    return off, 'slack (P%d, zero run 0x%X)' % (part, run)


def set_field(m, elem, fields, name, value):
    if name not in fields:
        raise SystemExit('field %r not in block; have: %s'
                         % (name, ', '.join(sorted(fields))))
    kind, off = fields[name]
    if kind.startswith('float') or kind in ('degree', 'rangef'):
        struct.pack_into('<f', m.data, elem + off, float(value))
    elif kind in ('int16', 'enum16', 'short', 'range16'):
        struct.pack_into('<h', m.data, elem + off, int(float(value)))
    elif kind in ('int8', 'enum8', 'flags8'):
        struct.pack_into('<b', m.data, elem + off, int(float(value)))
    else:
        struct.pack_into('<i', m.data, elem + off, int(float(value)))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', required=True, choices=sorted(SUBDIRS))
    ap.add_argument('--map', required=True)
    ap.add_argument('--tag', help='char tag path, forward or back slashes')
    ap.add_argument('--block', default='Vitality Properties')
    ap.add_argument('--set', action='append', default=[], metavar='FIELD=VALUE')
    ap.add_argument('--repoint-family', metavar='SUBSTR',
                    help='point every character-palette slot whose path contains '
                         'SUBSTR at --tag, so the subject cannot be missed in game')
    ap.add_argument('--restore', action='store_true',
                    help='put back the %s backup' % BACKUP_SUFFIX)
    a = ap.parse_args()

    path = V.resolve(a.game, a.map)
    if not path:
        raise SystemExit('no map %r for %s' % (a.map, a.game))
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
        print('backed up -> %s' % os.path.basename(backup))

    m = halo_patch.open_map(path, a.game)
    datum = TAGREF_DATUM.get(a.game, DEFAULT_TAGREF_DATUM)
    tag_path = (a.tag or '').replace('/', SEP)

    if a.tag:
        base = tag_base(m, 'char', tag_path)
        if base is None:
            raise SystemExit('%s not in %s' % (a.tag, a.map))
        blk_off, esz, fields = plugin_block(a.game, 'char', a.block)
        count = m.i32(base + blk_off)
        print('%s: %s count=%d' % (a.tag.rsplit('/', 1)[-1], a.block, count))
        if count == 0:
            par = seed_ancestor(m, base, blk_off, datum)
            if par is None:
                raise SystemExit('no ancestor populates %s -- nothing to seed from'
                                 % a.block)
            psrc = block_data_off(m, par['base'], blk_off)
            seed = bytes(m.data[psrc:psrc + esz])
            elem, how = insert(m, base, blk_off, esz, seed)
            print('  seeded from nearest populated ancestor: %s'
                  % par['name'].rsplit(SEP, 1)[-1])
            print('  %s -> element at file 0x%X' % (how, elem))
        else:
            elem = block_data_off(m, base, blk_off)
            print('  already has its own block; editing in place')
        for kv in a.set:
            k, _, v = kv.partition('=')
            set_field(m, elem, fields, k.strip(), v.strip())
            print('  set %s = %s' % (k.strip(), v.strip()))

    if a.repoint_family:
        row = tag_row(m, 'char', tag_path)
        if row is None:
            raise SystemExit('--repoint-family needs a valid --tag')
        pal_off, pal_esz = None, None
        for sub in SUBDIRS[a.game]:
            p = os.path.join(PLUGINS, sub, 'scnr.xml')
            if not os.path.isfile(p):
                continue
            for ch in ET.parse(p).getroot():
                if ch.get('name') == 'Character Palette' and ch.get('offset'):
                    pal_off = int(ch.get('offset'), 16)
                    pal_esz = int(ch.get('elementSize', '0'), 16)
            if pal_off is not None:
                break
        scnr = m.scenario_tag()
        sbase = scnr['base'] if isinstance(scnr, dict) else None
        n = m.i32(sbase + pal_off)
        arr = block_data_off(m, sbase, pal_off)
        hit = 0
        for i in range(n):
            e = arr + i * pal_esz
            cur = m.u32(e + datum)
            t = m.tag(cur & 0xFFFF) if cur != 0xFFFFFFFF else None
            nm = (t or {}).get('name') or ''
            if a.repoint_family in nm and nm != tag_path:
                struct.pack_into('<I', m.data, e + datum,
                                 (cur & 0xFFFF0000) | (row['index'] & 0xFFFF))
                hit += 1
        print('repointed %d palette slots containing %r at %s'
              % (hit, a.repoint_family, tag_path.rsplit(SEP, 1)[-1]))

    m.save()

    # --- static verification, on a freshly reopened file ---
    m2 = halo_patch.open_map(path, a.game)
    print('\nverify:')
    if a.tag:
        base2 = tag_base(m2, 'char', tag_path)
        blk_off, esz, fields = plugin_block(a.game, 'char', a.block)
        print('  %s count is now %d' % (a.block, m2.i32(base2 + blk_off)))
        pl = halo_patch.PluginRegistry(PLUGINS, SUBDIRS[a.game]).get('char')
        for k in sorted(fields):
            if 'Vitality' in k or k in [x.split('=')[0].strip() for x in a.set]:
                v = m2.read_all('char', tag_path, k, pl, block=a.block, index='all')
                if v:
                    print('     %-30s %s' % (k, [x for _, x in v]))
    cs_off = getattr(m2, 'CHECKSUM_OFF', None)
    if cs_off is None:
        print('  saved (this parser exposes no checksum word to re-verify)')
    else:
        print('  checksum self-consistent: %s'
              % (m2.u32(cs_off) == m2.update_checksum()))


if __name__ == '__main__':
    main()
