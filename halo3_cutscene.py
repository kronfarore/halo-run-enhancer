# halo3_cutscene.py — remove the Halo 3 flood-"vision" cutscenes (Cortana flicker +
# Gravemind screen effects) from STOCK campaign maps in place, reproducing
# TacoUpgrade's "Cortana Begone".
#
# The mod deletes the HSC statements that play those effects (the
# `cinematic_scripting_play/destroy_cortana_effect...` calls with their paired
# sleep/start_dialogue, and the `set g_cortana_*` / `set g_gravemind_*` state
# statements) and relinks + recompiles the whole scenario — not reproducible as a
# byte patch. We do the equivalent IN PLACE: HSC statements in a (begin …) block are
# a Next-linked sibling list; repointing every live predecessor of a removed span
# past it orphans those statements (never executed), with ZERO change to expression
# count, links outside the edit, or the Script Strings blob.
#
# `Next Expression @0x8` is a datum `(target_salt<<16)|target_index` (target's salt
# @0x0), little-endian; a null link is 0xFFFFFFFF. The per-map removed spans are the
# exact expression indices the mod deleted, derived by aligning stock vs mod Script
# Expressions on a rebuild-stable key and taking the pure 'delete' blocks (which sum
# to the exact expr-count delta). See scratchpad/recipe_gen.py.
#
# apply is verified + idempotent: each span must be in range and hold a vision token
# ('cortana'/'gravemind') or the map is left untouched; re-running finds nothing to
# redirect. Only maps in CORTANA_RUNS are patchable (the 7 stock cutscene maps).

import struct

SCNR_EXPR_OFF = 0x49C          # Script Expressions tagblock: [count i32][ptr u32]
EXPR_SIZE = 0x18
F_SALT = 0x0                   # u16
F_NEXT = 0x8                   # u32 datum
F_STR = 0xC                    # u32 String Address (into Script Strings blob)
NEXT_TERMINATOR = 0xFFFFFFFF

VISION_TOKENS = ('cortana', 'gravemind')   # flood-vision effects the mod removes

# Removed expression spans [start, end) per map internal name, from the mod oracle.
CORTANA_RUNS = {
    '010_jungle': [(26951, 26967), (27030, 27034), (27041, 27051)],
    '020_base': [(47694, 47710), (47773, 47777), (47784, 47788), (47835, 47851),
                 (47914, 47918), (47925, 47929), (47976, 47992), (48055, 48059),
                 (48066, 48070), (48117, 48135), (48198, 48202), (48209, 48213),
                 (48260, 48276), (48339, 48343), (48350, 48354)],
    '040_voi': [(32857, 32873), (32936, 32940), (32947, 32951), (32998, 33014),
                (33077, 33081), (33088, 33092), (33139, 33155), (33218, 33222),
                (33229, 33233)],
    '050_floodvoi': [(32051, 32073), (32125, 32134), (32141, 32150), (32186, 32205),
                     (32258, 32267), (32274, 32283), (32330, 32346), (32409, 32413),
                     (32420, 32424)],
    '100_citadel': [(58115, 58131), (58194, 58198), (58205, 58209), (58256, 58272),
                    (58335, 58339), (58346, 58350), (58397, 58413), (58476, 58480),
                    (58487, 58491)],
    '110_hc': [(20907, 20923), (20986, 20990), (20997, 21001), (21048, 21064),
               (21127, 21131), (21138, 21142), (21189, 21205), (21268, 21277),
               (21284, 21294), (21341, 21359), (21422, 21431), (21438, 21442),
               (21489, 21514), (21577, 21581), (21588, 21592), (21752, 21774),
               (21826, 21835), (21842, 21851), (21888, 21910), (21962, 21971),
               (21978, 21987), (22024, 22046), (22098, 22107), (22114, 22123),
               (22160, 22182), (22234, 22243), (22250, 22259), (22296, 22318),
               (22370, 22379), (22386, 22399), (22436, 22458), (22510, 22514),
               (22521, 22530)],
    '120_halo': [(53867, 53889), (53941, 53950), (53957, 53966)],
}


class _Exprs:
    """Accessor over a map's Script Expressions block + Script Strings blob."""

    def __init__(self, m):
        self.m = m
        d = m.data
        s = m.scenario_tag()['base']
        self.count = struct.unpack_from('<i', d, s + SCNR_EXPR_OFF)[0]
        self.base = m.data2off(struct.unpack_from('<I', d, s + SCNR_EXPR_OFF + 4)[0])
        ss_size = struct.unpack_from('<i', d, s + 0x3D8)[0]
        ss_ptr = struct.unpack_from('<I', d, s + 0x3D8 + 0xC)[0]
        so = m.data2off(ss_ptr)
        self.strblob = bytes(d[so:so + ss_size]) if so else b''

    def off(self, i):
        return self.base + i * EXPR_SIZE

    def salt(self, i):
        return struct.unpack_from('<H', self.m.data, self.off(i) + F_SALT)[0]

    def next_index(self, i):
        v = struct.unpack_from('<I', self.m.data, self.off(i) + F_NEXT)[0]
        return None if v in (0, 0xFFFFFFFF) else (v & 0xFFFF)

    def str_at(self, i):
        addr = struct.unpack_from('<I', self.m.data, self.off(i) + F_STR)[0]
        if addr == 0 or addr >= len(self.strblob):
            return ''
        s = self.strblob.rfind(b'\0', 0, addr) + 1
        e = self.strblob.find(b'\0', addr)
        return self.strblob[s:(e if e >= 0 else len(self.strblob))].decode('latin1', 'replace')

    def set_next(self, i, target):
        if target is None:
            datum = NEXT_TERMINATOR
        else:
            datum = (self.salt(target) << 16) | (target & 0xFFFF)
        struct.pack_into('<I', self.m.data, self.off(i) + F_NEXT, datum)


def remove_cortana_flicker(m):
    """Neutralise the flood-vision cutscenes (Cortana + Gravemind) in an open
    Halo3Map (in memory; call m.save() to persist). Returns a report dict.

    Every live expression whose Next points into a removed span is repointed to the
    first surviving statement past it (following the original chain through removed
    nodes). Idempotent and self-verifying: if the map's internal name has no recipe,
    a span is out of range, or a span lacks a vision token, nothing is written."""
    name = m.internal_name
    runs = CORTANA_RUNS.get(name)
    report = {'map': name, 'ok': False, 'edits': 0, 'removed_exprs': 0}
    if not runs:
        report['reason'] = 'no cutscene recipe for this map'
        return report
    ex = _Exprs(m)
    for a, b in runs:
        if b > ex.count:
            report['reason'] = 'span out of range (build mismatch?)'
            return report
        if not any(any(t in ex.str_at(i).lower() for t in VISION_TOKENS)
                   for i in range(a, b)):
            report['reason'] = f'span [{a}:{b}] has no vision token (build mismatch?)'
            return report
    removed = set(i for a, b in runs for i in range(a, b))

    def first_kept_after(n):
        seen = 0
        while n is not None and n in removed and seen <= ex.count:
            n = ex.next_index(n)
            seen += 1
        return n

    edits = 0
    for p in range(ex.count):
        if p in removed:
            continue
        n = ex.next_index(p)
        if n is not None and n in removed:
            ex.set_next(p, first_kept_after(n))
            edits += 1
    report.update(ok=True, edits=edits, removed_exprs=len(removed))
    return report


def orphaned_ok(m):
    """True if every removed expression is unreachable. HSC statements execute along
    the Next sibling chain (entered from a script root or a parent's Next); a call
    node's Value->function_name pointer is only followed once the call node itself is
    reached via Next. So a removed statement is dead iff no live expression's Next
    points into a removed span and no script root lands there. (A literal's Value can
    coincidentally alias a removed index — that is NOT an execution edge.)"""
    runs = CORTANA_RUNS.get(m.internal_name)
    if not runs:
        return True
    ex = _Exprs(m)
    removed = set(i for a, b in runs for i in range(a, b))
    for p in range(ex.count):
        if p not in removed and ex.next_index(p) in removed:
            return False
    # no live script Root Expression may land inside a removed span
    d = m.data
    s = m.scenario_tag()['base']
    scnt = struct.unpack_from('<i', d, s + 0x3EC)[0]
    soff = m.data2off(struct.unpack_from('<I', d, s + 0x3EC + 4)[0])
    for i in range(scnt):
        datum = struct.unpack_from('<I', d, soff + i * 0x34 + 0x24)[0]
        if datum not in (0, 0xFFFFFFFF) and (datum & 0xFFFF) in removed:
            return False
    return True


if __name__ == '__main__':
    import sys
    import halo3_map
    m = halo3_map.Halo3Map(sys.argv[1])
    rep = remove_cortana_flicker(m)
    print(rep)
    if rep['ok'] and len(sys.argv) > 2:
        m.save(sys.argv[2])
        print("saved", sys.argv[2])
