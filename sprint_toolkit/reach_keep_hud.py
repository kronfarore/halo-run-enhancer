r"""Keep the player's HUD up through Halo Reach's chapter titles -- in the .map.

Halo 1, 2 and 3 do this by editing the editing kit's script SOURCE and rebuilding the
cache (h1/h2/h3_keep_hud.py). Reach has no editing kit here, so this edits the
COMPILED script tree in the map instead, using the technique halo3_cutscene.py proved:
statements in a block are a Next-linked sibling list, so repointing a statement's
predecessor past it orphans the statement. Nothing is deleted, the expression count
does not change, and the Script Strings blob is untouched.

THE RECORD (Reach: Script Expressions @0x504, 0x18 bytes; Script Strings @0x41C)

    0x00 u16 salt        0x02 u16 opcode      0x04 u16 value type   0x06 u16 flags
    0x08 u32 next        0x0C u32 string off  0x10 u32 value

A call is TWO records. The function NAME is a record with value type 2, whose `next`
chains the arguments; its parent is the GROUP record whose `value & 0xFFFF` points at
the name. The group is the statement, and the group is what gets skipped.

WHAT IS REMOVED, AND WHAT DELIBERATELY IS NOT

Both verbs are called in matched pairs, and only the HIDING half may go -- removing a
restore stranding the HUD off forever is the one way this edit can ruin a level:

    chud_cinematic_fade 0 <time>     hides the HUD      REMOVED
    chud_cinematic_fade 1 <time>     restores it        KEPT
    cinematic_show_letterbox true    bars on            REMOVED
    cinematic_show_letterbox false   bars off           KEPT

That is the same rule h3_keep_hud settled on Halo 1's c40: dropping the fade alone
keeps the HUD but leaves the bars, and dropping the letterbox with it removes the
bars while the title still draws. The title verbs themselves
(chud_show_screen_chapter_title, chud_fade_chapter_title_for_player) are NOT touched,
so chapter titles still appear.

    python reach_keep_hud.py --map m20 --dry-run     # what would change
    python reach_keep_hud.py --map m20               # apply
    python reach_keep_hud.py --map m20 --verify      # is the edit in the map?
    python reach_keep_hud.py --map m20 --restore     # put the map back

Patches FROM <map>.bak and never writes it. MCC can stay open as long as that map is
not loaded.
"""
import argparse
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_patch as HP                                          # noqa: E402
import map_vault as V                                            # noqa: E402

GAME = 'Halo Reach'
EXPRS = (0x504, 0x18)
STRINGS = 0x41C
F_SALT, F_OPCODE, F_VTYPE, F_FLAGS = 0x0, 0x2, 0x4, 0x6
F_NEXT, F_STR, F_VALUE = 0x8, 0xC, 0x10
TERMINATOR = 0xFFFFFFFF
T_FUNCNAME = 2
T_BOOL, T_REAL, T_SHORT, T_LONG = 5, 6, 7, 8
# verb -> (name of the arg that means "hide", predicate on the first argument)
HIDERS = {
    'chud_cinematic_fade': ('fade to 0', lambda v: v == 0.0),
    'cinematic_show_letterbox': ('letterbox on', lambda v: v == 1.0),
}


class Tree:
    def __init__(self, m):
        self.m = m
        self.scnr = HP._scnr_base(m)
        self.n = max(0, m.i32(self.scnr + EXPRS[0]))
        self.base = HP._block_base(m, self.scnr + EXPRS[0])
        so = m.u32(self.scnr + STRINGS + 0xC)
        sb = m.data2off(so) if so else None
        ss = max(0, m.i32(self.scnr + STRINGS))
        self.blob = bytes(m.data[sb:sb + ss]) if sb else b''

    def string(self, off):
        if not (0 <= off < len(self.blob)):
            return None
        e = self.blob.find(b'\0', off)
        return self.blob[off:e if e >= 0 else len(self.blob)].decode('latin-1')

    def at(self, i):
        if not self.base or not (0 <= i < self.n):
            return None
        e = self.base + i * EXPRS[1]
        d = self.m.data
        salt, opcode, vtype, flags = struct.unpack_from('<HHHH', d, e)
        nxt, soff = struct.unpack_from('<II', d, e + F_NEXT)
        val = struct.unpack_from('<I', d, e + F_VALUE)[0]
        return dict(i=i, off=e, salt=salt, opcode=opcode, vtype=vtype, flags=flags,
                    next=nxt, string=self.string(soff), value=val, child=val & 0xFFFF)

    def number(self, r):
        """The first argument as a float, whatever integer width it is stored in."""
        t, v = r['vtype'], r['value']
        if t == T_BOOL:
            return 1.0 if (v & 0xFF) else 0.0
        if t == T_REAL:
            return struct.unpack('<f', struct.pack('<I', v))[0]
        if t == T_SHORT:
            return float(struct.unpack('<h', struct.pack('<H', v & 0xFFFF))[0])
        if t == T_LONG:
            return float(struct.unpack('<i', struct.pack('<I', v))[0])
        return None

    def set_next(self, i, datum):
        struct.pack_into('<I', self.m.data, self.base + i * EXPRS[1] + F_NEXT, datum)

    def set_value(self, i, val):
        struct.pack_into('<I', self.m.data, self.base + i * EXPRS[1] + F_VALUE, val)

    def datum(self, i):
        """The (salt<<16)|index datum that other records use to point AT `i`."""
        r = self.at(i)
        return ((r['salt'] << 16) | i) & 0xFFFFFFFF


def survey(t):
    """[(verb, name index, group index, first-arg value, is_hide)] for every call."""
    child_of = {}
    for i in range(t.n):
        r = t.at(i)
        child_of.setdefault(r['child'], []).append(i)
    out = []
    for i in range(t.n):
        r = t.at(i)
        if r['vtype'] != T_FUNCNAME or r['string'] not in HIDERS:
            continue
        parents = [p for p in child_of.get(i, []) if p != i and t.at(p)['child'] == i]
        arg = None
        if r['next'] != TERMINATOR:
            arg = t.number(t.at(r['next'] & 0xFFFF))
        _label, is_hide = HIDERS[r['string']]
        out.append((r['string'], i, parents[0] if parents else None, arg,
                    arg is not None and is_hide(arg)))
    return out


def skip(t, group):
    """Orphan the statement at `group`. Returns a description, or None if it cannot
    be done safely."""
    g = t.at(group)
    # the predecessor SIBLING, i.e. whoever links to this statement with Next
    for i in range(t.n):
        r = t.at(i)
        if r['next'] != TERMINATOR and (r['next'] & 0xFFFF) == group and i != group:
            t.set_next(i, g['next'])
            return 'expr %d now points past %d' % (i, group)
    # no sibling before it: it is the first statement of its block, so the PARENT's
    # child pointer is what has to move on instead
    for i in range(t.n):
        r = t.at(i)
        if r['child'] == group and i != group and r['vtype'] != T_FUNCNAME:
            if g['next'] == TERMINATOR:
                return None          # only statement in the block; leave it alone
            t.set_value(i, (r['value'] & 0xFFFF0000) | (g['next'] & 0xFFFF))
            return 'parent %d now enters the block at %d' % (i, g['next'] & 0xFFFF)
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--map', required=True)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args(argv)
    live = V.resolve(GAME, a.map)
    if not live:
        raise SystemExit('no such Reach map: %s' % a.map)
    bak = live + '.bak'
    if not os.path.isfile(bak):
        raise SystemExit('no pristine baseline at %s' % bak)

    if a.restore:
        try:
            shutil.copy2(bak, live)
        except PermissionError:
            raise SystemExit('map is loaded in MCC; leave the mission first')
        print('restored %s' % live)
        return 0

    if a.dry_run or a.verify:
        m = HP.open_map(bak if a.dry_run else live, GAME)
        t = Tree(m)
        rows = survey(t)
        print('%s: %d expressions, %d call site(s)'
              % (os.path.basename(bak if a.dry_run else live), t.n, len(rows)))
        for verb, name, group, arg, is_hide in rows:
            print('   %-26s name=%-6d group=%-8s arg=%-8s %s'
                  % (verb, name, group, arg,
                     'HIDE -> remove' if is_hide else 'restore -> keep'))
        if a.verify:
            live_hidden = [r for r in rows if r[4]]
            reachable = 0
            for _v, _n, group, _a, _h in live_hidden:
                if group is None:
                    continue
                if any(t.at(i)['next'] != TERMINATOR
                       and (t.at(i)['next'] & 0xFFFF) == group for i in range(t.n)):
                    reachable += 1
            print('   %d hide-call(s) still reachable by a Next link'
                  % reachable)
        return 0

    try:
        shutil.copy2(bak, live)
    except PermissionError:
        raise SystemExit('map is loaded in MCC; leave the mission first')
    m = HP.open_map(live, GAME)
    t = Tree(m)
    rows = survey(t)
    done, kept, failed = 0, 0, 0
    for verb, name, group, arg, is_hide in rows:
        if not is_hide:
            kept += 1
            continue
        if group is None:
            print('   SKIP %-26s name=%d has no group' % (verb, name))
            failed += 1
            continue
        how = skip(t, group)
        if how:
            print('   removed %-26s group=%-6d arg=%-6s  (%s)' % (verb, group, arg, how))
            done += 1
        else:
            print('   SKIP    %-26s group=%-6d could not be unlinked safely'
                  % (verb, group))
            failed += 1
    if not done:
        shutil.copy2(bak, live)
        print('nothing removed; map left at its baseline')
        return 1
    m.save(live)
    print()
    print('%s: removed %d hide call(s), kept %d restore(s), %d skipped'
          % (os.path.basename(live), done, kept, failed))
    return 0


if __name__ == '__main__':
    sys.exit(main())
