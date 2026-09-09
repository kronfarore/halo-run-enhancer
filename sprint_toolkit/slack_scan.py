"""Is there ANY usable free space inside Halo 4's tag partitions?

`find_slack` only inspects the TAIL of each partition, which on Halo 4 is 0-3 bytes.
But a cache is not necessarily packed solid: padding between tags, or between a tag's
data and the next, would show up as zero runs INSIDE a partition. If a long enough run
exists and its offset round-trips through the pointer model, the seeder can use it with
no restructuring at all -- which is enormously safer than growing the file.
"""
import os
import sys

TOOL = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection\tool"
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, 'sprint_toolkit'))
import halo_patch as hp
import h4_census as hc

ROOT = r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection"
NEED = 184          # the biggest element the hero cards need (Charge Properties)


def runs(m, lo, hi, need):
    """Every zero run of at least `need` bytes in [lo, hi), as (start, length)."""
    data = m.data
    out = []
    i = lo
    while i < hi:
        if data[i]:
            i += 1
            continue
        j = i
        while j < hi and not data[j]:
            j += 1
        if j - i >= need:
            out.append((i, j - i))
        i = j
    return out


for game, path in [('Halo Reach', os.path.join(ROOT, 'haloreach', 'maps', 'm30.map')),
                   ('Halo 4', os.path.join(hc.MAPS, 'm70_liftoff.map')),
                   ('Halo 4', os.path.join(hc.MAPS, 'm90_sacrifice.map'))]:
    m = hp.open_map(path, game)
    print('=== %s %s' % (game, os.path.basename(path)))
    tot = 0
    usable = 0
    biggest = (0, 0, -1)
    for i, (la, sz, fb) in enumerate(m.partitions):
        if not sz or fb is None:
            continue
        rs = runs(m, fb, fb + sz, NEED)
        tot += len(rs)
        for off, ln in rs:
            # must be addressable: the offset has to survive off2data -> data2off
            cand = (off + 0xF) & ~0xF
            if cand + NEED > off + ln:
                continue
            d = m.off2data(cand)
            if d is None or m.data2off(d) != cand:
                continue
            usable += 1
            if ln > biggest[1]:
                biggest = (cand, ln, i)
        if rs:
            print('   partition[%d] 0x%X..0x%X : %d run(s) >= %d bytes, longest %d'
                  % (i, fb, fb + sz, len(rs), NEED, max(l for _o, l in rs)))
    print('   TOTAL runs >= %d bytes: %d ; addressable: %d' % (NEED, tot, usable))
    if usable:
        print('   biggest addressable: offset 0x%X, %d bytes, partition %d'
              % (biggest[0], biggest[1], biggest[2]))
