# hud_titles.py -- keep the player's HUD up through chapter/cinematic titles, by
# editing the COMPILED script tree in the map. No editing kit and no rebuild.
#
# h1/h2/h3_keep_hud.py do this by editing the kit's script SOURCE and rebuilding the
# cache, which is fine for a modder and useless as a run option: the Enhancer patches
# shipped .map files in place. This does the same job the way halo3_cutscene.py does
# its work -- statements in a block are a Next-linked sibling list, so repointing a
# statement's predecessor past it orphans the statement. Nothing is deleted, the
# expression count never changes, and the Script Strings blob is untouched.
#
# THE RECORD (0x18 bytes, all three third/fourth-gen games):
#     0x00 u16 salt    0x02 u16 opcode   0x04 u16 value type   0x06 u16 flags
#     0x08 u32 next    0x0C u32 string   0x10 u32 value
#
# A call is TWO records: the function NAME has value type 2 and its `next` chains the
# ARGUMENTS, while its parent is the GROUP whose `value & 0xFFFF` points at the name.
# The group is the statement, and the group is what has a predecessor and gets skipped.
#
# ONLY THE HIDING HALF OF EACH PAIR IS REMOVED. Both verbs are called in matched
# pairs and stranding the HUD off forever is the one way this edit can ruin a level:
#
#     chud_cinematic_fade 0 <t>      hides the HUD     removed
#     chud_cinematic_fade 1 <t>      restores it       kept
#     cinematic_show_letterbox true  bars on           removed
#     cinematic_show_letterbox false bars off          kept
#
# That is the rule h3_keep_hud settled on Halo 1's c40: dropping the fade alone keeps
# the HUD but leaves the bars, and dropping the letterbox with it removes the bars
# while the title still draws. The title verbs themselves are never touched, so
# chapter titles still appear.
#
# HALO 1 AND HALO 2 ARE ALREADY DONE, by a different route. h1_keep_hud.py and
# h2_keep_hud.py edit the editing kit's script SOURCES and the rebuilt map carries the
# edit; both are applied to every deployed map today. So this module skips those two
# games on purpose -- there is nothing left to fix there, and a patch-time edit would
# be a second, conflicting copy of the same change.
#
# For the record, since it was worth establishing and is easy to get wrong: Halo 2's
# scenario IS readable by this code's layout (Script Expressions 0x238, element 0x14 --
# the same record 4 bytes narrower). What stops a name-based search is that Halo 1 and
# Halo 2 store function names as OPCODES, not strings; their string blob holds only
# literals and script names. The Halo 2 opcodes are 0x0274 hud_cinematic_fade,
# 0x0230 cinematic_show_letterbox, 0x0232 cinematic_set_title, 0x0013 sleep, identical
# across all 13 maps. Halo 1 has no expression tagblock at all -- a Script Syntax Data
# blob at 0x474 instead (56-byte header, 20-byte nodes).

import struct

# game -> (Script Expressions tagblock offset, Script Strings dataRef offset).
# Measured, not assumed: each was confirmed by checking that the strings blob parses
# and contains the verbs below.
SCRIPT_BLOCKS = {
    'Halo 3':       (0x49C, 0x3D8),
    'Halo 3: ODST': (0x4DC, 0x418),
    'Halo Reach':   (0x504, 0x41C),
}
EXPR_SIZE = 0x18
F_NEXT, F_STR, F_VALUE = 0x8, 0xC, 0x10
TERMINATOR = 0xFFFFFFFF
T_FUNCNAME = 2
T_BOOL, T_REAL, T_SHORT, T_LONG = 5, 6, 7, 8

# verb -> predicate on the first argument that means "this call HIDES the HUD"
HIDERS = {
    'chud_cinematic_fade': lambda v: v == 0.0,
    'cinematic_show_letterbox': lambda v: v == 1.0,
}


class Tree:
    """The compiled script tree of one scenario."""

    def __init__(self, m, game, block_base, scnr_base):
        self.m = m
        self.game = str(game).strip()
        eoff, soff = SCRIPT_BLOCKS[self.game]
        self.n = max(0, m.i32(scnr_base + eoff))
        self.base = block_base(m, scnr_base + eoff)
        ptr = m.u32(scnr_base + soff + 0xC)
        sb = m.data2off(ptr) if ptr else None
        ss = max(0, m.i32(scnr_base + soff))
        self.blob = bytes(m.data[sb:sb + ss]) if sb else b''

    def ok(self):
        return bool(self.base) and self.n > 0 and bool(self.blob)

    def string(self, off):
        if not (0 <= off < len(self.blob)):
            return None
        e = self.blob.find(b'\0', off)
        return self.blob[off:e if e >= 0 else len(self.blob)].decode('latin-1')

    def at(self, i):
        if not self.base or not (0 <= i < self.n):
            return None
        e = self.base + i * EXPR_SIZE
        d = self.m.data
        salt, opcode, vtype, flags = struct.unpack_from('<HHHH', d, e)
        nxt, soff = struct.unpack_from('<II', d, e + F_NEXT)
        val = struct.unpack_from('<I', d, e + F_VALUE)[0]
        return dict(i=i, salt=salt, opcode=opcode, vtype=vtype, flags=flags,
                    next=nxt, string=self.string(soff), value=val,
                    child=val & 0xFFFF)

    def number(self, r):
        """The first argument as a float, whatever width it is stored in."""
        if r is None:
            return None
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
        struct.pack_into('<I', self.m.data, self.base + i * EXPR_SIZE + F_NEXT, datum)

    def set_value(self, i, val):
        struct.pack_into('<I', self.m.data, self.base + i * EXPR_SIZE + F_VALUE, val)


def survey(t):
    """[(verb, name index, group index, first arg, is_hide)] for every call site."""
    child_of = {}
    for i in range(t.n):
        child_of.setdefault(t.at(i)['child'], []).append(i)
    out = []
    for i in range(t.n):
        r = t.at(i)
        if r['vtype'] != T_FUNCNAME or r['string'] not in HIDERS:
            continue
        parents = [p for p in child_of.get(i, []) if p != i and t.at(p)['child'] == i]
        arg = t.number(t.at(r['next'] & 0xFFFF)) if r['next'] != TERMINATOR else None
        out.append((r['string'], i, parents[0] if parents else None, arg,
                    arg is not None and HIDERS[r['string']](arg)))
    return out


def _skip(t, group):
    """Orphan the statement at `group`; returns a description or None."""
    g = t.at(group)
    for i in range(t.n):
        r = t.at(i)
        if r['next'] != TERMINATOR and (r['next'] & 0xFFFF) == group and i != group:
            t.set_next(i, g['next'])
            return 'expr %d -> past %d' % (i, group)
    # first statement of its block: the PARENT's child pointer moves on instead
    for i in range(t.n):
        r = t.at(i)
        if r['child'] == group and i != group and r['vtype'] != T_FUNCNAME:
            if g['next'] == TERMINATOR:
                return None          # the only statement in the block; leave it
            t.set_value(i, (r['value'] & 0xFFFF0000) | (g['next'] & 0xFFFF))
            return 'parent %d enters at %d' % (i, g['next'] & 0xFFFF)
    return None


def remove_title_hud_hiding(m, game, block_base, scnr_base):
    """Orphan every call that hides the HUD for a title. Returns a result dict."""
    g = str(game).strip()
    if g not in SCRIPT_BLOCKS:
        # NOT a missing feature. Halo 1 and Halo 2 already have this, applied at BUILD
        # time by sprint_toolkit/h1_keep_hud.py and h2_keep_hud.py -- they edit the
        # editing kit's script sources and the rebuilt map carries the edit. Both are
        # currently applied to every deployed map (`--status` says "edit is in the
        # deployed map" on all 10 H1 levels and all 13 H2 missions), so there is
        # nothing for a patch-time edit to do here and doing one anyway would be a
        # second, conflicting copy of the same change.
        return {'ok': True, 'skip': True,
                'reason': '%s gets this at build time from %s_keep_hud.py; already '
                          'in the deployed maps' % (g, 'h1' if g == 'Halo 1' else 'h2')}
    if scnr_base is None:
        return {'ok': False, 'reason': 'no scnr'}
    t = Tree(m, g, block_base, scnr_base)
    if not t.ok():
        return {'ok': False, 'reason': 'script block unreadable'}
    rows = survey(t)
    kept = sum(1 for r in rows if not r[4])
    # ITERATE TO A FIXED POINT. Two hide statements can be adjacent siblings: skipping
    # the first repoints its predecessor onto the second, which puts the second back on
    # the live chain after it was already dealt with. One pass left exactly one call
    # still reachable on every Halo 3 and ODST map; re-surveying and repeating clears
    # it. The loop is bounded because each pass either unlinks something or stops.
    removed, failed, passes = 0, 0, 0
    while passes < 8:
        passes += 1
        live = []
        for _verb, _name, group, _arg, is_hide in survey(t):
            if not is_hide or group is None:
                continue
            if any(t.at(i)['next'] != TERMINATOR
                   and (t.at(i)['next'] & 0xFFFF) == group and i != group
                   for i in range(t.n)):
                live.append(group)
        if not live:
            break
        moved = 0
        for group in live:
            if _skip(t, group):
                removed += 1
                moved += 1
        if not moved:
            failed = len(live)
            break
    return {'ok': True, 'removed': removed, 'kept': kept, 'failed': failed,
            'sites': len(rows), 'passes': passes}
