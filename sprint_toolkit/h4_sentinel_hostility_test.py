r"""h4_sentinel_hostility_test.py -- do Halo 4's Sentinels fight the player at all?

The Sentinel keeps a Halo 4 card set, but the Halo 4 Sentinel is not a campaign enemy
in the usual sense, and the question that decides whether its cards stay, change or go
is simply: put a lot of them in front of the player -- do they attack?

The Sentinel IS fielded by squads -- Requiem 29 spawns, Midnight 16 -- so presence is not
the question; hostility is. Requiem is the test map: `storm_sentinel` is resident and in
its character palette, and it fields 82 Grunts, the most plentiful thing to repoint.
Grunts are ground spawns and the Sentinel flies, so a Sentinel dropped on a Grunt point
simply lifts off; there is none of the body-size risk that ruled out Crawler -> Knight.

Only the CHARACTER index of each Grunt spawn changes. Squad team, objectives and
everything else are untouched, so the result reads cleanly:

  * Sentinels shoot the player      -> hostile under an enemy squad; the cards can stay.
  * Sentinels idle / ignore you     -> the Halo 4 Sentinel does not engage; its cards
                                       need adjusting or leaving out.
  * Sentinels fight the Covenant    -> they carry their own allegiance regardless of
                                       squad, which is its own answer.

A baseline is made FIRST if Requiem has none -- restoring is then a straight copy.

    python sprint_toolkit/h4_sentinel_hostility_test.py            # dry run
    python sprint_toolkit/h4_sentinel_hostility_test.py --apply
    python sprint_toolkit/h4_sentinel_hostility_test.py --restore
"""
import argparse
import os
import shutil
import struct
import sys
import xml.etree.ElementTree as ET

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import assembly_plugins                                           # noqa: E402
import halo_patch as hp                                           # noqa: E402
import h4_census as hc                                            # noqa: E402
import map_vault as V                                             # noqa: E402

S = chr(92)
MAP = 'm020'
FROM_LEAF, TO_LEAF = 'storm_grunt', 'storm_sentinel'


def _layout():
    rs = ET.parse(os.path.join(assembly_plugins.plugins_dir(), 'Halo4MCC',
                               'scnr.xml')).getroot()
    sq = next(c for c in rs if c.tag.lower() == 'tagblock' and c.get('name') == 'Squads')
    cp = next(c for c in rs if c.tag.lower() == 'tagblock'
              and c.get('name') == 'Character Palette')
    return (int(sq.get('offset'), 16), int(sq.get('elementSize'), 16),
            int(cp.get('offset'), 16), int(cp.get('elementSize'), 16))


def _at(m, b, o):
    c = m.i32(b + o)
    return (m.data2off(m.u32(b + o + 4)), c) if c > 0 else (0, 0)


def plan(m):
    """(from slot, to slot, [entry offsets]) -- every Spawn Point AND every cell that
    names an ordinary Grunt, read with h4_census's offsets (never hand-rolled ones)."""
    SQO, SQS, CPO, CPS = _layout()
    idx = {t['index']: t for t in m.tags}
    sb = m.find_tags('scnr', '*')[0][1]
    pe, npal = _at(m, sb, CPO)
    slot = {}
    for i in range(npal):
        d = struct.unpack_from('<I', m.data, pe + i * CPS + 0xC)[0]
        tt = idx.get(d & 0xFFFF)
        slot[((tt or {}).get('name') or '?').rsplit(S, 1)[-1]] = i
    src, dst = slot.get(FROM_LEAF), slot.get(TO_LEAF)
    hits = []
    se, nsq = _at(m, sb, SQO)
    for s in range(nsq):
        sq = se + s * SQS
        sp, spn = _at(m, sq, hc.SPAWN_POINTS[0])
        for j in range(spn):
            e = sp + j * hc.SPAWN_POINTS[1] + hc.SPAWN_FIELDS['character']
            if m.i16(e) == src:
                hits.append(e)
        for co, csize in hc.CELL_BLOCKS:
            ca, cn = _at(m, sq, co)
            for j in range(cn):
                bo, bsize = hc.CELL_SUB['character']
                ba, bn = _at(m, ca + j * csize, bo)
                for k in range(bn):
                    e = ba + k * bsize + hc.CELL_SUB_INDEX
                    if m.i16(e) == src:
                        hits.append(e)
    return src, dst, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args()
    live = os.path.join(hc.MAPS, MAP + '.map')
    base = V.baseline_for('Halo 4', live)
    print('live     %s' % live)
    print('baseline %s  (exists: %s)' % (base, os.path.exists(base)))
    if a.restore:
        if not os.path.exists(base):
            raise SystemExit('no baseline to restore from')
        shutil.copyfile(base, live)
        print('restored Requiem from the baseline')
        return
    m = hp.open_map(live, 'Halo 4')
    src, dst, hits = plan(m)
    print('%s = palette slot %s ; %s = slot %s ; %d spawn/cell entr(ies) to repoint'
          % (FROM_LEAF, src, TO_LEAF, dst, len(hits)))
    if src is None or dst is None:
        raise SystemExit('both characters must already be in the palette')
    if not a.apply:
        print('(dry run -- pass --apply)')
        return
    if not os.path.exists(base):
        os.makedirs(os.path.dirname(base), exist_ok=True)
        del m
        shutil.copyfile(live, base)
        print('baseline CREATED first')
        m = hp.open_map(live, 'Halo 4')
        src, dst, hits = plan(m)
    for e in hits:
        struct.pack_into('<h', m.data, e, dst)
    m.save()
    del m
    m2 = hp.open_map(live, 'Halo 4')
    _s, _d, left = plan(m2)
    print('after save: %d ordinary Grunt entries left ; tags=%d ; checksum reproduces: %s'
          % (len(left), len(m2.tags), m2.u32(m2.CHECKSUM_OFF) == m2.update_checksum()))


if __name__ == '__main__':
    main()
