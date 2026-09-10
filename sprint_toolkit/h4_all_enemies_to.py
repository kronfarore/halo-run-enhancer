r"""h4_all_enemies_to.py -- replace EVERY enemy on a Halo 4 map with one character.

A test rig. The Sentinel test on Requiem answered the first question (they do attack the
player, but they are not planned as an enemy, so they do not roam -- they hold where they
spawn). This is the tool for the follow-up tests: every enemy spawn on a level becomes
the chosen character, so its behaviour can be watched at scale.

"Enemy" means every character-palette slot that is not an ally. Allies are recognised by
name -- the UNSC and civilian families Halo 4 ships -- and are left exactly as they are,
so the Marines still fight alongside you and the test reads cleanly. The target
character itself is skipped too.

Only each spawn's CHARACTER index changes: every Spawn Point and every Designer /
Templated Cell entry, read with h4_census's offsets. Squad teams, objectives, weapons
and vehicles are untouched. The target must already be in the map's character palette
(for the Sentinel: Requiem, Reclaimer and Midnight).

A baseline is made FIRST if the map has none, so --restore is always a straight copy.

    python sprint_toolkit/h4_all_enemies_to.py --map m020                 # dry run
    python sprint_toolkit/h4_all_enemies_to.py --map m020 --apply
    python sprint_toolkit/h4_all_enemies_to.py --map m020 --to storm_knight --apply
    python sprint_toolkit/h4_all_enemies_to.py --map m020 --restore
"""
import argparse
import collections
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
# Name fragments of the characters that fight WITH the player. Measured off the eight
# campaign maps: every Marine variant, the Spartan AI, the fleet officers, Lasky,
# Palmer, Cortana and the scientists.
ALLY = ('marine', 'spartan', 'odst', 'cortana', 'lasky', 'palmer', 'scientist',
        'fleet_officer', 'crew', 'civilian', 'pilot', 'masterchief', 'infinity')


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


def plan(m, to_leaf):
    """(target slot, {slot: leaf} of the enemy slots, [(entry offset, slot)])."""
    SQO, SQS, CPO, CPS = _layout()
    idx = {t['index']: t for t in m.tags}
    sb = m.find_tags('scnr', '*')[0][1]
    pe, npal = _at(m, sb, CPO)
    leaf = {}
    for i in range(npal):
        d = struct.unpack_from('<I', m.data, pe + i * CPS + 0xC)[0]
        tt = idx.get(d & 0xFFFF)
        leaf[i] = ((tt or {}).get('name') or '').rsplit(S, 1)[-1]
    target = next((i for i, n in leaf.items() if n == to_leaf), None)
    enemies = {i: n for i, n in leaf.items()
               if n and n != to_leaf and not any(a in n for a in ALLY)}
    hits = []
    se, nsq = _at(m, sb, SQO)
    for s in range(nsq):
        sq = se + s * SQS
        sp, spn = _at(m, sq, hc.SPAWN_POINTS[0])
        for j in range(spn):
            e = sp + j * hc.SPAWN_POINTS[1] + hc.SPAWN_FIELDS['character']
            v = m.i16(e)
            if v in enemies:
                hits.append((e, v))
        for co, csize in hc.CELL_BLOCKS:
            ca, cn = _at(m, sq, co)
            for j in range(cn):
                bo, bsize = hc.CELL_SUB['character']
                ba, bn = _at(m, ca + j * csize, bo)
                for k in range(bn):
                    e = ba + k * bsize + hc.CELL_SUB_INDEX
                    v = m.i16(e)
                    if v in enemies:
                        hits.append((e, v))
    return target, enemies, hits


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--map', required=True, help='campaign map basename, e.g. m020')
    ap.add_argument('--to', default='storm_sentinel',
                    help='character leaf name to put everywhere (default storm_sentinel)')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args()
    live = os.path.join(hc.MAPS, a.map + '.map')
    base = V.baseline_for('Halo 4', live)
    print('live     %s' % live)
    print('baseline %s  (exists: %s)' % (base, os.path.exists(base)))
    if a.restore:
        if not os.path.exists(base):
            raise SystemExit('no baseline to restore from')
        shutil.copyfile(base, live)
        print('restored %s from the baseline' % a.map)
        return
    m = hp.open_map(live, 'Halo 4')
    target, enemies, hits = plan(m, a.to)
    if target is None:
        raise SystemExit('%s is not in %s\'s character palette -- a swap can only use '
                         'a character the map already carries' % (a.to, a.map))
    per = collections.Counter(enemies[v] for _e, v in hits)
    print('target %s = palette slot %d ; %d enemy slot(s) ; %d spawn/cell entr(ies)'
          % (a.to, target, len(enemies), len(hits)))
    for n, c in per.most_common():
        print('   %-40s %4d -> %s' % (n, c, a.to))
    if not a.apply:
        print('(dry run -- pass --apply)')
        return
    if not os.path.exists(base):
        del m
        os.makedirs(os.path.dirname(base), exist_ok=True)
        shutil.copyfile(live, base)
        print('baseline CREATED first')
        m = hp.open_map(live, 'Halo 4')
        target, enemies, hits = plan(m, a.to)
    for e, _v in hits:
        struct.pack_into('<h', m.data, e, target)
    m.save()
    del m
    m2 = hp.open_map(live, 'Halo 4')
    _t, _en, left = plan(m2, a.to)
    print('after save: %d enemy entr(ies) left un-swapped ; tags=%d ; checksum '
          'reproduces: %s' % (len(left), len(m2.tags),
                              m2.u32(m2.CHECKSUM_OFF) == m2.update_checksum()))


if __name__ == '__main__':
    main()
