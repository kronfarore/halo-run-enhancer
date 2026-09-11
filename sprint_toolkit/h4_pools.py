# -*- coding: utf-8 -*-
r"""Halo 4 zone-set residency: why a weapon placed in Sapien does not spawn, and the fix.

The same mechanism as Reach (see reach_pools.py): the cache's `zone` tag keeps one tag
pool (a BIT ARRAY, one bit per tag index) and one raw-page pool per zone set, and an
object whose tags are not in a pool that is live where it is placed has nothing
resident to build. Halo 4 adds the level's DESIGNER zones to it: a mission starts in
scenario zone set 0, which switches on only the designer zones in its Designer Zone
Flags (Dawn: 0xF, designer zones 0-3).

Measured on the rebuilt Dawn (2026-09-11), matching the in-game result exactly:
  * needler, covenant carbine, concussion rifle, plasma pistol -- the whole tag chain
    is resident ONLY in later designer zones (4-14), because the Covenant squads that
    carry them live there. Placed at the start, they do not spawn.
  * beam rifle -- the same, and its first-person model and animations are late too:
    it spawns but the slot is empty.
  * everything the scenario only places (DMR, shotgun, LightRifle...) sits in
    Scenario[0] and spawns.
  * storm_sentinel_beam has NO model at all (world and first-person refs null on every
    map) -- it is the Sentinels' built-in beam and can never be a pickup.

!! WRITING POOL BITS CRASHES HALO 4 (in game, 2026-09-11) -- the audit is sound, the
!! fix is not. With the full fix on Dawn, spawning the Storm Rifle or the Beam Rifle --
!! placed or as a starting weapon -- crashed the game. Unlike Reach, every Halo 4 zone
!! set carries a precomputed MEMORY BUDGET: its Resource Types entries (+0x34, 0x1C
!! each) hold a byte size per resource type, and the set total at +0x1C is their exact
!! sum (Scenario[0]: 391,745,536). The fix added ~136 sound banks, ~6000 sounds, bitmaps
!! and models to 60 sets and left every budget as it was, so the resource cache runs out
!! the moment the weapon is built. Reach survived because its fix added 88 tag bits and
!! NO pages. So --write now needs --experimental.
!!
!! THE WORKING ROUTE is the Editing Kit: add the weapon to a designer zone that zone set 0
!! switches on (Dawn: designer zones 0-3) and rebuild -- the tool then computes the pools
!! AND the budgets together.

THE (experimental) FIX copies a DONOR's residency onto the target, as on Reach: for every zone set and
pool where the donor's weap tag bit is set, set the bits of the target's whole declared
tagRef closure (weap, model chain, first person, HUD screen, projectiles, effects...),
and its raw pages wherever the donor has pages. The default donor is the palette weapon
resident in the MOST zone sets -- the Assault Rifle on Dawn -- so the target stays
loaded through every later zone-set switch the player carries it into. Tags in no pool
at all are left alone; they are not loaded through pools.

The map is copied aside FIRST (sprint_toolkit/_pools_backup/) and --restore puts it
back. The vault baseline is not touched.

    python sprint_toolkit/h4_pools.py m10_crash                        # audit
    python sprint_toolkit/h4_pools.py m10_crash --fix storm_needler --write
    python sprint_toolkit/h4_pools.py m10_crash --fix-all --write
    python sprint_toolkit/h4_pools.py m10_crash --restore
    python sprint_toolkit/h4_pools.py --audit                          # every mission
"""
import argparse
import os
import shutil
import struct
import sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import assembly_plugins                                           # noqa: E402
import halo_patch as HP                                           # noqa: E402
import h4_census as hc                                            # noqa: E402
import tagrefs                                                    # noqa: E402

GAME = 'Halo 4'
SEP = chr(92)
BACKUP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_pools_backup')

# zone tag (Halo4MCC zone.xml): every zone-set block shares one 0x90 element
ZS_ELEM = 0x90
ZS_BLOCKS = [('Designer', 0x64), ('Global', 0x70), ('Unattached', 0x88),
             ('DiscForbid', 0x94), ('DiscAlways', 0xA0), ('BSP', 0xAC),
             ('BSP2', 0xB8), ('BSP3', 0xC4), ('Cine', 0xD0), ('ReqMapVar', 0xDC),
             ('SandboxMapVar', 0xE8), ('Scenario', 0xF4)]
RAW_POOLS = (0x0, 0xC)
TAG_POOLS = (0x58, 0x64)
ZONE_RAW_PAGES, ZONE_SEGMENTS, ZONE_TAG_RESOURCES = 0x34, 0x4C, 0x58
ZTR_ELEM, ZTR_SEGMENT = 0x44, 0x1A
SEG_ELEM, SEG_PAGES = 0x18, (0xC, 0xE, 0x10)
# scnr: zone set 0's Designer Zone Flags say which designer zones are live at start
SCNR_ZONE_SETS, SCNR_ZS_ELEM, SCNR_DESIGNER_FLAGS = 0x100, 0x1A0, 0x11C
# classes the closure does not walk into: whole levels, units, AI
STOP = {'scnr', 'matg', 'sbsp', 'zone', 'play', 'bipd', 'vehi', 'char', 'sddt',
        'stli', 'gpdt', 'mulg', 'unic'}
KINDS = {'weapons': (0x1BC, 0x10), 'equipment': (0x1A4, 0x10)}
PREFERRED_DONORS = ('storm_assault_rifle', 'storm_magnum')


def zone_base(m):
    zt = next((t for t in m.tags if t.get('class') == 'zone'), None)
    if not zt or not zt.get('base'):
        raise SystemExit('map has no zone tag')
    return zt['base']


def zone_sets(m, zb):
    out = []
    for label, off in ZS_BLOCKS:
        b, n = HP._block_base(m, zb + off), max(0, m.i32(zb + off))
        for k in range(n) if b else []:
            out.append(('%s[%d]' % (label, k), b + k * ZS_ELEM))
    return out


def start_sets(m):
    """Labels of the zone sets live when the mission starts."""
    s = HP._scnr_base(m)
    zs = HP._block_base(m, s + SCNR_ZONE_SETS)
    flags = m.u32(zs + SCNR_DESIGNER_FLAGS) if zs else 0
    return {'Scenario[0]', 'Global[0]'} | {'Designer[%d]' % k for k in range(32)
                                           if flags & (1 << k)}


def _pool(m, elem, off):
    b, n = HP._block_base(m, elem + off), m.i32(elem + off)
    return (b, n * 4) if (b and n > 0) else (None, 0)


def getbit(m, b, size, i):
    return (i >> 3) < size and bool(m.data[b + (i >> 3)] & (1 << (i & 7)))


def setbit(m, b, size, i):
    if (i >> 3) >= size:
        return False
    m.data[b + (i >> 3)] |= (1 << (i & 7))
    return True


def tag_sets(m, sets, ti):
    """[(label, pool offset)] where tag index `ti` is resident."""
    hits = []
    for label, elem in sets:
        for off in TAG_POOLS:
            b, size = _pool(m, elem, off)
            if b and getbit(m, b, size, ti):
                hits.append((label, off))
    return hits


class Closure:
    """Declared-tagRef closure of a tag, and the raw pages behind it."""

    def __init__(self, m, zb):
        self.m = m
        self.by_ident = {t['ident']: t for t in m.tags if t.get('ident') is not None}
        self.specs = {}
        pd = assembly_plugins.plugins_dir()
        self._pd = pd
        res = {}
        b = HP._block_base(m, zb + ZONE_TAG_RESOURCES)
        for i in range(max(0, m.i32(zb + ZONE_TAG_RESOURCES))) if b else []:
            e = b + i * ZTR_ELEM
            res.setdefault(m.u32(e + 0xC) & 0xFFFF, []).append(
                struct.unpack_from('<h', m.data, e + ZTR_SEGMENT)[0])
        self.res = res
        self.seg_b = HP._block_base(m, zb + ZONE_SEGMENTS)
        self.seg_n = max(0, m.i32(zb + ZONE_SEGMENTS))

    def _spec(self, cls):
        if cls not in self.specs:
            self.specs[cls] = (tagrefs._spec(self._pd, 'Halo4MCC', cls)
                               or tagrefs._spec(self._pd, 'Halo4', cls))
        return self.specs[cls]

    def of(self, ident, max_tags=4000):
        root = self.by_ident.get(ident)
        if not root or root.get('base') is None:
            return [], set()
        seen, order, todo = {root['index']}, [root], [root]
        while todo and len(order) < max_tags:
            t = todo.pop()
            sp = self._spec(t['class'])
            if not sp:
                continue
            for _path, d in tagrefs.refs_of(self.m, t['base'], sp):
                c = self.by_ident.get(d)
                if (not c or c['index'] in seen or c.get('base') is None
                        or c['class'] in STOP):
                    continue
                seen.add(c['index'])
                order.append(c)
                todo.append(c)
        pages = set()
        for t in order:
            for sg in self.res.get(t['index'], []):
                if self.seg_b and 0 <= sg < self.seg_n:
                    for po in SEG_PAGES:
                        p = struct.unpack_from('<h', self.m.data,
                                               self.seg_b + sg * SEG_ELEM + po)[0]
                        if p >= 0:
                            pages.add(p)
        return order, pages


def palette(m, kind):
    s = HP._scnr_base(m)
    off, es = KINDS[kind]
    b, n = HP._block_base(m, s + off), max(0, m.i32(s + off))
    out = []
    for i in range(n) if b else []:
        ident = m.u32(b + i * es + 0xC)
        nm = HP._tag_name_by_id(m, ident)
        if nm:
            out.append((str(nm).rsplit(SEP, 1)[-1], ident))
    return out


#: placement block per palette kind: (scnr offset, element size)
PLACEMENTS = {'weapons': (0x1B0, 0x170), 'equipment': (0x198, 0x154)}


def placed_names(m):
    """Palette entry names that have at least one placement in the scenario."""
    s = HP._scnr_base(m)
    out = set()
    for kind, (off, esz) in PLACEMENTS.items():
        pal = palette(m, kind)
        b = HP._block_base(m, s + off)
        for i in range(max(0, m.i32(s + off))) if b else []:
            pi = struct.unpack_from('<h', m.data, b + i * esz)[0]
            if 0 <= pi < len(pal):
                out.add(pal[pi][0])
    return out


def survey(m, zb, sets, clo):
    """[(kind, name, ident, weap tag index, start?, closure tags late)]"""
    live = start_sets(m)
    rows = []
    for kind in KINDS:
        for nm, ident in palette(m, kind):
            t = clo.by_ident.get(ident)
            if not t:
                continue
            tags, _pages = clo.of(ident)
            late = []
            for c in tags:
                where = {lab for lab, _o in tag_sets(m, sets, c['index'])}
                if where and not (where & live):
                    late.append(c)
            here = {lab for lab, _o in tag_sets(m, sets, t['index'])}
            rows.append((kind, nm, ident, t['index'], bool(here & live), late,
                         len(here)))
    return rows


def pick_donor(rows, kind, name=None):
    cands = [r for r in rows if r[0] == kind and r[4] and not r[5]]
    if name:
        cands = [r for r in cands if r[1] == name]
    for pref in PREFERRED_DONORS if not name else ():
        for r in cands:
            if r[1] == pref:
                return max((x for x in cands if x[1] == pref), key=lambda x: x[6])
    return max(cands, key=lambda r: r[6]) if cands else None


#: The pools a player actually moves through: the scenario zone sets, the designer
#: zones they switch on, and the global set. BSP / cinematic / map-variant sets are
#: left alone -- copying into all 138 of Dawn's sets put tens of thousands of bits on
#: one weapon where Reach's proven fix needed 88.
FIX_BLOCKS = ('Scenario', 'Designer', 'Global')


def apply_fix(m, sets, clo, target_ident, donor_ident, start_only=False):
    """Give the target's LATE closure the residency the donor has, in the scenario,
    designer and global pools -- or, with start_only, only in the pools live when the
    mission starts. Returns (tag bits, page bits) written."""
    live = start_sets(m)
    all_sets = sets
    ttags, _tpages = clo.of(target_ident)
    _dtags, dpages = clo.of(donor_ident)
    donor_ti = clo.by_ident[donor_ident]['index']
    # Only what is NOT already live at the start. A tag in no pool at all is loaded
    # another way and is left alone; one already live at start needs nothing.
    late = []
    for t in ttags:
        # judged against EVERY zone set -- narrowing first made nothing look late
        where = {lab for lab, _o in tag_sets(m, all_sets, t['index'])}
        if where and not (where & live):
            late.append(t)
    lidx = {t['index'] for t in late}
    tpages = set()
    for t in late:
        for sg in clo.res.get(t['index'], []):
            if clo.seg_b and 0 <= sg < clo.seg_n:
                for po in SEG_PAGES:
                    p = struct.unpack_from('<h', m.data, clo.seg_b + sg * SEG_ELEM + po)[0]
                    if p >= 0:
                        tpages.add(p)
    sets = [(lab, e) for lab, e in all_sets if lab.split('[')[0] in FIX_BLOCKS
            and (not start_only or lab in live)]
    ttags = [t for t in ttags if t['index'] in lidx]
    nt = npg = 0
    for _label, elem in sets:
        for off in TAG_POOLS:
            b, size = _pool(m, elem, off)
            if not b or not getbit(m, b, size, donor_ti):
                continue
            for t in ttags:
                if not getbit(m, b, size, t['index']) and setbit(m, b, size, t['index']):
                    nt += 1
        for off in RAW_POOLS:
            b, size = _pool(m, elem, off)
            if not b or not any(getbit(m, b, size, p) for p in dpages):
                continue
            for p in tpages:
                if not getbit(m, b, size, p) and setbit(m, b, size, p):
                    npg += 1
    return nt, npg


def report(mid, rows):
    bad = [r for r in rows if not r[4] or r[5]]
    print('=== %s: %d palette entries, %d not fully resident at mission start'
          % (mid, len(rows), len(bad)))
    for kind, nm, _id, _ti, start, late, nsets in rows:
        if start and not late:
            continue
        what = ('weap tag NOT at start' if not start else 'weap tag at start')
        print('   %-9s %-36s %s; %d closure tag(s) late%s' % (
            kind, nm, what, len(late),
            (' e.g. ' + ', '.join(sorted({c['class'] for c in late}))) if late else ''))


def _live(mid):
    return os.path.join(hc.MAPS, mid + '.map')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map', nargs='?', help='campaign map basename, e.g. m10_crash')
    ap.add_argument('--audit', action='store_true', help='every campaign mission')
    ap.add_argument('--fix', action='append', default=[], help='palette entry name')
    ap.add_argument('--fix-all', action='store_true')
    ap.add_argument('--fix-placed', action='store_true',
                    help='every palette entry the scenario actually places (the usual '
                         'case after a Sapien pass)')
    ap.add_argument('--donor', help='donor palette entry (default: the widest resident)')
    ap.add_argument('--start-only', action='store_true',
                    help='only the pools live at mission start: the smallest fix, but a '
                         'weapon carried past a zone switch may unload')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--experimental', action='store_true',
                    help='required with --write: writing pool bits crashed Halo 4 on spawn '
                         '(zone-set memory budgets are not updated) -- see the docstring')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args(argv)
    if a.audit:
        for mid, _t in hc.CAMPAIGN:
            m = HP.open_map(_live(mid), GAME)
            zb = zone_base(m)
            report(mid, survey(m, zb, zone_sets(m, zb), Closure(m, zb)))
            del m
        return 0
    if not a.map:
        ap.error('name a map, or pass --audit')
    live, bak = _live(a.map), os.path.join(BACKUP, a.map + '.map')
    if a.restore:
        if not os.path.exists(bak):
            raise SystemExit('no backup to restore from: %s' % bak)
        shutil.copyfile(bak, live)
        os.remove(bak)
        print('restored %s from the side backup (backup removed)' % a.map)
        return 0
    if a.write and not a.experimental:
        raise SystemExit('refused: writing Halo 4 pool bits crashed the game on spawn '
                         '(2026-09-11). Add the weapon to a designer zone zone set 0 loads '
                         'and rebuild instead; --experimental overrides.')
    if a.write and not os.path.exists(bak):
        os.makedirs(BACKUP, exist_ok=True)
        shutil.copyfile(live, bak)
        print('backup CREATED: %s' % bak)
    m = HP.open_map(live, GAME)
    zb = zone_base(m)
    sets = zone_sets(m, zb)
    clo = Closure(m, zb)
    rows = survey(m, zb, sets, clo)
    print('start sets: %s' % ', '.join(sorted(start_sets(m))))
    report(a.map, rows)
    placed = placed_names(m) if a.fix_placed else set()
    targets = [r for r in rows if (not r[4] or r[5])
               and (a.fix_all or r[1] in a.fix or r[1] in placed)]
    unknown = set(a.fix) - {r[1] for r in rows}
    if unknown:
        print('not in the palette: %s' % ', '.join(sorted(unknown)))
    if not targets:
        return 0
    wrote = 0
    for r in targets:
        donor = pick_donor(rows, r[0], a.donor)
        if donor is None:
            print('   %-36s no resident %s donor' % (r[1], r[0]))
            continue
        nt, npg = apply_fix(m, sets, clo, r[2], donor[2], start_only=a.start_only)
        wrote += nt + npg
        print('   %-36s <- %-24s %d tag bit(s), %d page bit(s)' % (r[1], donor[1], nt, npg))
    if not a.write:
        print('(dry run -- pass --write; the bits above were computed, not saved)')
        return 0
    if not wrote:
        print('nothing to write')
        return 0
    m.save()
    del m
    m2 = HP.open_map(live, GAME)
    zb = zone_base(m2)
    rows2 = survey(m2, zb, zone_sets(m2, zb), Closure(m2, zb))
    left = [r[1] for r in rows2 if (not r[4] or r[5]) and r[1] in {t[1] for t in targets}]
    print('after save: still not resident: %s ; checksum reproduces: %s'
          % (left or 'none', m2.u32(m2.CHECKSUM_OFF) == m2.update_checksum()))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
