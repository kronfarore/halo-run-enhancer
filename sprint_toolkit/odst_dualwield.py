r"""What ODST needs to dual-wield again, and what it already has.

FINDING (2026-08-20)
--------------------
ODST lost dual wield in two places, and only ONE of them is a byte patch.

  1. `weap` -> Flags -> **Can Be Dual Wielded** (bit 16, at 0x19C in ODST) is CLEAR on
     all nine one-handed weapons; the reference mod sets it on exactly those nine and
     changes nothing else in that dword. Trivially patchable.

  2. The first-person animation graph's Modes tree carries only the `any` weapon class.
     Halo 3's carries `any` AND `dual` (stringID 0x1F4 there, 0x1F6 in ODST's table),
     and the `dual` class is what tells the engine which animation each hand plays.
     Stock ODST has no `dual` class on any of them.

Flipping the flag alone therefore lets you PICK UP a second weapon and leaves the engine
with no dual animation set to play -- which is what a "sloppy restore" looks like.

WHY IT NEEDS AN IMPORT: GRAPH INHERITANCE
-----------------------------------------
The ODSTMCC jmad plugin says how the mod does it:

    Inheritance List  @0x80  el 0x30 (first field: tagRef to the Inherited Graph)
    Actions element   Label @0x0, GRAPH INDEX @0x4, Animation Index @0x6

    "To reference an inherited graph, set the Graph Index value of the animation(s)
     you want to the Inheritance List index that points to the graph."

So an action's animation index is not necessarily local. Measured on fp_plasma_rifle:

    stock ODST      inheritance list 0 entries, `any` actions graphIdx -1 (local)
    reference mod   inheritance list 1 entry -> Chief's fp_plasma_rifle,
                    dual actions graphIdx 0 (inherited)
    Halo 3 (Chief)  dual actions graphIdx -1, into its own 37 animations

The mod adds Chief's graph to the ODST graph's Inheritance List and copies Chief's dual
action table verbatim. Indices that look out of range locally (spike_rifle 16 of 13) are
valid in the INHERITED graph.

ODST's own graphs really do lack the animations. Confirmed by frame-count matching --
the way to compare animations here, since their names are stringIDs the toolkit's
resolver does not reach (above 0xF00). Of Chief's eight plasma_rifle dual animations,
three have no ODST animation of matching length at all and the rest match only ones the
`any` class already uses.

THE FLAG-ONLY TEST
------------------
The reasoning above says the flag alone should not be enough. It is worth SHOWING that
rather than arguing it, because the two failure modes look completely different in game
and each tells us something:

  * the weapon cannot be picked up as a second weapon at all  -> the flag is not the
    gate, and the analysis above is wrong somewhere;
  * it CAN be dual wielded but the hands are broken (T-pose, frozen, missing left
    weapon, wrong animation) -> the flag is the gate, and only the animation half is
    missing, which is exactly what the import would supply;
  * it works properly -> ODST's own graph had a usable dual set after all and no import
    is needed for THAT weapon.

`--patch <weapon>` sets bit 16 on one weapon in one map and nothing else. It writes the
map in place, keeping a `.dualwield.bak` beside it so the change is reversible without
re-patching from the enhancer's own baseline (which would take the flag with it).

    python odst_dualwield.py --map sc130 --patch magnum
    python odst_dualwield.py --map sc130 --revert

MCC MUST BE CLOSED: it holds the map files open and the write fails.

This module is otherwise the survey that establishes the above, and the source of the
action tables an implementation would need.

    python odst_dualwield.py                 # stock ODST, one map
    python odst_dualwield.py --mod           # ...beside the reference mod's maps
    python odst_dualwield.py --map sc130
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import halo_patch as HP                                          # noqa: E402
import halo3_reload as RL                                        # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import map_vault as V                                            # noqa: E402

GAME = 'Halo 3: ODST'
L = RL.LAYOUTS[GAME]
MOD_MAPS = (r"C:\Program Files (x86)\Steam\steamapps\workshop\content\976730"
            r"\3248662097\halo3odst\maps")

WEAP_FLAGS = 0x19C                 # ODST weap Flags dword
DUAL_BIT = 16                      # "Can Be Dual Wielded"
NO_MAX_BIT = 1                     # "Doesn't Count Toward Maximum" (the SOCOM slot)

# The one-handed set, as the reference mod defines it. `automag` is deliberately NOT
# here: the mod gives it the third-slot flag instead and its own notes record removing
# its dual wielding again ("Sad but needed to be done").
ONE_HANDED = ['magnum', 'smg', 'smg_silenced', 'plasma_pistol', 'plasma_rifle',
              'plasma_rifle_red', 'spike_rifle', 'excavator', 'needler']

# weapon short name -> the fp graph it uses, by the tail of the tag path
FP_OF = {'magnum': 'fp_magnum', 'smg': 'fp_smg', 'smg_silenced': 'fp_smg_silenced',
         'plasma_pistol': 'fp_plasma_pistol', 'plasma_rifle': 'fp_plasma_rifle',
         'plasma_rifle_red': 'fp_plasma_rifle', 'spike_rifle': 'fp_spike_rifle',
         'excavator': 'fp_excavator', 'needler': 'fp_needler'}


def weap_flags(m, short):
    for name, base in m.find_tags('weap', '*' + short):
        if name.rsplit(chr(92), 1)[-1] == short:
            return struct.unpack_from('<I', m.data, base + WEAP_FLAGS)[0]
    return None


def fp_graph(m, tail):
    """The PLAYER's graph for this weapon: the one under the odst_recon character.

    A map carries two graphs whose basename matches -- one under the weapon's own
    folder and one under the character -- and only the character's is the first-person
    set the player sees, so matching on basename alone picks the wrong tag half the time.
    """
    for name, base in m.find_tags('jmad', '*' + tail):
        if name.rsplit(chr(92), 1)[-1] == tail and 'odst_recon' in name:
            return name, base
    return None, None


def classes(m, base):
    """[(class stringID, [(action label, animation index)])] for mode `any`."""
    out = []
    for mo in m.follow_all(base, [L['modes_blk']], [L['modes_el']], 'all'):
        for wc in m.follow_all(mo, [L['wclass_blk']], [L['wclass_el']], 'all'):
            csid = struct.unpack_from('<I', m.data, wc)[0]
            acts = []
            for wt in m.follow_all(wc, [L['wtype_blk']], [L['wtype_el']], 'all'):
                for a in m.follow_all(wt, [L['actions_blk']], [L['actions_el']], 'all'):
                    lab = struct.unpack_from('<I', m.data, a)[0]
                    idx = struct.unpack_from('<h', m.data, a + L['act_anim_off'])[0]
                    acts.append((m.resolve_stringid(lab) or hex(lab), idx))
            out.append((m.resolve_stringid(csid) or hex(csid), acts))
    return out


def survey(m, label):
    print('== %s' % label)
    for w in ONE_HANDED:
        f = weap_flags(m, w)
        if f is None:
            print('   %-18s (weapon absent)' % w)
            continue
        name, base = fp_graph(m, FP_OF[w])
        if base is None:
            print('   %-18s flags=%08X dual=%-3s  (no player fp graph)'
                  % (w, f, 'yes' if f & (1 << DUAL_BIT) else 'no'))
            continue
        anims = m.follow_all(base, [L['anim_blk']], [L['anim_el']], 'all')
        cls = classes(m, base)
        used = {i for _c, acts in cls for _l, i in acts if i >= 0}
        spare = [i for i in range(len(anims)) if i not in used]
        print('   %-18s dual flag=%-3s  fp anims=%-3d  classes=%-22s  '
              'animations no class uses: %s'
              % (w, 'yes' if f & (1 << DUAL_BIT) else 'NO', len(anims),
                 ','.join(c for c, _a in cls), spare))
        for c, acts in cls:
            if c == 'any':
                continue
            print('        %-10s %s' % (c, acts))


DUAL_SID = 0x1F6                   # 'dual' in ODST's own string table
BLOCK_REF = 12                     # count i32, pointer u32, 4 unused


def _ref(m, off):
    return m.i32(off), HP._block_base(m, off)


def _set_ref(m, off, count, file_off):
    """Point a tagblock ref at a relocated element array."""
    ptr = m.off2data(file_off)
    if ptr is None:
        raise RuntimeError('offset 0x%X is outside every partition' % file_off)
    struct.pack_into('<II', m.data, off, count, ptr)


def add_dual_class(m, tail, actions, graph_index=-1):
    """Give the player's fp graph for `tail` a `dual` weapon class.

    `actions` is [(label stringID, animation index)]. `graph_index` selects which graph
    those indices address: -1 is this graph's own animations, and 0.. picks an entry of
    the Inheritance List. The local form needs nothing imported and is what makes a
    flag-only map testable; the inherited form is the real fix once Chief's graph is in.

    The three new arrays are placed in ONE partition zero-run via `_h3_reserve`, because
    H3 resolves tagblock pointers through the partition table -- appending at EOF gives a
    pointer the engine cannot map. Existing elements are COPIED, so every ref they carry
    (Weapon ik, Overlays, Transitions) keeps pointing at the data it already shared.
    """
    name, base = fp_graph(m, tail)
    if base is None:
        return 'no player fp graph for %s' % tail

    modes = m.follow_all(base, [L['modes_blk']], [L['modes_el']], 'all')
    if not modes:
        return '%s has no Modes' % tail
    mode = modes[0]
    wc_ref = mode + L['wclass_blk']
    n_wc, wc_base = _ref(m, wc_ref)
    if not wc_base or n_wc < 1:
        return '%s mode has no Weapon Class' % tail
    for i in range(n_wc):
        if struct.unpack_from('<I', m.data, wc_base + i * L['wclass_el'])[0] == DUAL_SID:
            return '%s already has a dual class' % tail

    # the template: weapon class 0 and its first weapon type
    wt_ref0 = wc_base + L['wtype_blk']
    n_wt, wt_base = _ref(m, wt_ref0)
    if not wt_base or n_wt < 1:
        return '%s weapon class 0 has no Weapon Type' % tail

    sz_wc = (n_wc + 1) * L['wclass_el']
    sz_wt = L['wtype_el']
    sz_ac = len(actions) * L['actions_el']
    got = HP._h3_reserve(m, [sz_wc, sz_wt, sz_ac])
    if not got:
        return 'no partition slack for %d bytes' % (sz_wc + sz_wt + sz_ac)
    off_wc, off_wt, off_ac = got

    # actions
    for i, (label, anim) in enumerate(actions):
        e = off_ac + i * L['actions_el']
        struct.pack_into('<Ihh', m.data, e, label, graph_index, anim)

    # weapon type: a copy of the existing one, with its Actions repointed at ours
    m.data[off_wt:off_wt + sz_wt] = m.data[wt_base:wt_base + sz_wt]
    _set_ref(m, off_wt + L['actions_blk'], len(actions), off_ac)

    # weapon class array: the existing elements verbatim, plus ours
    m.data[off_wc:off_wc + n_wc * L['wclass_el']] = \
        m.data[wc_base:wc_base + n_wc * L['wclass_el']]
    new_el = off_wc + n_wc * L['wclass_el']
    m.data[new_el:new_el + L['wclass_el']] = m.data[wc_base:wc_base + L['wclass_el']]
    struct.pack_into('<I', m.data, new_el, DUAL_SID)
    _set_ref(m, new_el + L['wtype_blk'], 1, off_wt)

    _set_ref(m, wc_ref, n_wc + 1, off_wc)
    return ('%s: dual class added (%d actions, graph index %d, %d bytes at 0x%X)'
            % (tail, len(actions), graph_index, sz_wc + sz_wt + sz_ac, off_wc))


INHERIT_BLK, INHERIT_EL = 0x80, 0x30
INH_NODEMAP, INH_FLAGS, INH_ROOTZ = 0x10, 0x1C, 0x28
CHIEF_UNIT = 'objects' + chr(92) + 'characters' + chr(92) + 'masterchief' + chr(92) + \
    'masterchief'

# Lifted verbatim from the reference mod's odst_recon graph. The node map is what makes
# a cross-skeleton borrow legal -- ODST's rig has 94 nodes, Chief's 88 -- and it is the
# reason a direct tagRef swap gets nulled by tool.exe while inheritance is accepted.
# 21 of Chief's nodes map onto ODST's; the rest are -1 (no counterpart), and the flag
# dwords mark exactly those 21. Root z offset compensates the height difference.
UNIT_NODE_MAP = [0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18,
                 38, 39, 42] + [-1] * 30
UNIT_NODE_FLAGS = [0x1FFFFF, 0x0]
UNIT_ROOT_Z = 0.9238440990447998

# (label stringID, animation index) per mode, indices into CHIEF's graph.
UNIT_DUAL_ACTIONS = {
    140: [(12, 83), (15, 118), (16, 119), (21, 88), (22, 87), (23, 89), (24, 90),
          (31, 60), (32, 85), (33, 84), (70, 86), (462, 121), (463, 120), (464, 122),
          (465, 123), (1011, 61)],
    143: [(12, 444), (15, 455), (16, 456), (21, 448), (22, 447), (23, 449), (24, 450),
          (31, 441), (32, 446), (33, 445), (462, 458), (463, 457), (464, 459),
          (465, 460), (1011, 442)],
}


PLAYER_GRAPH = ('objects' + chr(92) + 'characters' + chr(92) + 'odst_oni_op' +
                chr(92) + 'odst_oni_op_player')

# The player's hlmt points at odst_oni_op_player, NOT at odst_recon -- odst_recon is
# only inherited by it. Wiring odst_recon alone therefore changes nothing the engine
# reads for the player, which is why a map that looked correct still behaved as stock.
# This graph gets its own inheritance entry (index 2, after odst_recon and lipsync) and
# its own node map: 51 entries, all of them used, and a different root z from the
# odst_recon one. Values lifted from the reference mod.
PLAYER_NODE_MAP = [0, 1, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 71,
                   72, 94, 96, 97, 98, 99, 100, 109, 110, 111, 112, 113, 114, 115, 116,
                   117, 118, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 135, 136,
                   137, 138, 139]
PLAYER_NODE_FLAGS = [0xFFFFFFFF, 0x7FFFF]
PLAYER_ROOT_Z = 0.874493


def add_inheritance(m, graph_tag, target_tag, node_map=None, node_flags=None,
                    root_z=None):
    """Append an Inheritance List entry on `graph_tag` pointing at `target_tag`.

    Returns (index, message). The index is what an action's Graph Index must be set to.
    """
    base = None
    for n, b in m.find_tags('jmad', '*'):
        if n == graph_tag:
            base = b
            break
    if base is None:
        return None, 'no %s' % graph_tag
    tgt = HP._h3_tag_datum(m, 'jmad', target_tag)
    if tgt is None:
        return None, '%s is not in this map' % target_tag

    n_inh, inh_base = _ref(m, base + INHERIT_BLK)
    for i in range(max(0, n_inh)):
        if m.u32(inh_base + i * INHERIT_EL + 0xC) == tgt:
            return i, 'already inherits it at index %d' % i

    # The fp graphs need NO node map -- ODST's arm rig and Chief's are both 20 nodes,
    # which is why the mod's fp inheritance entries carry an empty one. The UNIT graphs
    # do (94 vs 88). Passing the map explicitly keeps that distinction visible instead
    # of hiding it behind a default that is right for only one of the two.
    node_map = UNIT_NODE_MAP if node_map is None else node_map
    node_flags = UNIT_NODE_FLAGS if node_flags is None else node_flags
    root_z = UNIT_ROOT_Z if root_z is None else root_z

    sz_inh = (n_inh + 1) * INHERIT_EL
    sz_map = max(1, len(node_map) * 2)
    sz_flg = max(1, len(node_flags) * 4)
    got = HP._h3_reserve(m, [sz_inh, sz_map, sz_flg])
    if not got:
        return None, 'no slack for %d bytes' % (sz_inh + sz_map + sz_flg)
    off_inh, off_map, off_flg = got

    for i, v in enumerate(node_map):
        struct.pack_into('<h', m.data, off_map + i * 2, v)
    for i, v in enumerate(node_flags):
        struct.pack_into('<I', m.data, off_flg + i * 4, v)

    if n_inh and inh_base:
        m.data[off_inh:off_inh + n_inh * INHERIT_EL] = \
            m.data[inh_base:inh_base + n_inh * INHERIT_EL]
    el = off_inh + n_inh * INHERIT_EL
    m.data[el:el + INHERIT_EL] = b'\0' * INHERIT_EL
    # the group magic, copied from a sibling rather than spelled out: it is stored
    # reversed ('damj') and copying cannot get the byte order wrong
    if n_inh and inh_base:
        m.data[el:el + 4] = m.data[inh_base:inh_base + 4]
    struct.pack_into('<I', m.data, el + 0xC, tgt)
    if node_map:
        _set_ref(m, el + INH_NODEMAP, len(node_map), off_map)
    if node_flags:
        _set_ref(m, el + INH_FLAGS, len(node_flags), off_flg)
    struct.pack_into('<f', m.data, el + INH_ROOTZ, root_z)
    _set_ref(m, base + INHERIT_BLK, n_inh + 1, off_inh)
    return n_inh, 'inheritance entry %d -> %s' % (n_inh, target_tag.rsplit(chr(92), 1)[-1])


# Chief's OWN dual table for fp_plasma_rifle, read from a Halo 3 map: (label, anim).
# Indices are local to CHIEF's graph, which is exactly what Graph Index selects.
FP_DUAL_ACTIONS = {
    'fp_plasma_rifle': [('fire_1', 0), ('idle', 2), ('ready', 15), ('put_away', 14),
                        ('posing', 10), ('misfire_1', 0), ('overheating', 7),
                        ('o_h_exit', 6)],
}
CHIEF_FP = {'fp_plasma_rifle': 'objects' + chr(92) + 'characters' + chr(92) +
            'masterchief' + chr(92) + 'fp' + chr(92) + 'weapons' + chr(92) + 'rifle' +
            chr(92) + 'fp_plasma_rifle' + chr(92) + 'fp_plasma_rifle'}


def wire_fp(m, tail):
    """Inheritance entry -> Chief's fp graph, plus a dual class addressing it.

    Unlike the unit graph this needs no node map (both arm rigs are 20 nodes), and the
    action labels are resolved to THIS map's stringIDs by name -- the ids differ between
    the two games' tables.
    """
    name, base = fp_graph(m, tail)
    if base is None:
        return 'no player fp graph for %s' % tail
    target = CHIEF_FP.get(tail)
    if not target:
        return 'no Chief fp graph recorded for %s' % tail
    idx, msg = add_inheritance(m, name, target, node_map=[], node_flags=[], root_z=1.0)
    if idx is None:
        return msg
    want = [n for n, _a in FP_DUAL_ACTIONS[tail]]
    by_name = {}
    for _c, acts in classes(m, base):
        for lab, _i in acts:
            by_name.setdefault(lab, None)
    sids = {}
    for mo in m.follow_all(base, [L['modes_blk']], [L['modes_el']], 'all'):
        for wc in m.follow_all(mo, [L['wclass_blk']], [L['wclass_el']], 'all'):
            for wt in m.follow_all(wc, [L['wtype_blk']], [L['wtype_el']], 'all'):
                for a in m.follow_all(wt, [L['actions_blk']], [L['actions_el']], 'all'):
                    sid = struct.unpack_from('<I', m.data, a)[0]
                    nm = m.resolve_stringid(sid)
                    if nm:
                        sids.setdefault(nm, sid)
    missing = [n for n in want if n not in sids]
    if missing:
        return '%s: no stringID for %s' % (tail, missing)
    acts = [(sids[n], anim) for n, anim in FP_DUAL_ACTIONS[tail]]
    rep = add_dual_class(m, tail, acts, graph_index=idx)
    return '%s; %s' % (msg, rep)


def add_unit_dual_inherited(m, graph_tag, graph_index):
    """Dual classes on combat/crouch whose actions address the INHERITED graph."""
    base = None
    for n, b in m.find_tags('jmad', '*'):
        if n == graph_tag:
            base = b
            break
    if base is None:
        return 'no %s' % graph_tag
    out = []
    for mode in m.follow_all(base, [L['modes_blk']], [L['modes_el']], 'all'):
        msid = struct.unpack_from('<I', m.data, mode)[0]
        acts = UNIT_DUAL_ACTIONS.get(msid)
        if not acts:
            continue
        wc_ref = mode + L['wclass_blk']
        n_wc, wc_base = _ref(m, wc_ref)
        if not wc_base:
            continue
        if any(struct.unpack_from('<I', m.data, wc_base + i * L['wclass_el'])[0]
               == DUAL_SID for i in range(n_wc)):
            out.append('mode %d already has dual' % msid)
            continue
        sz_wc = (n_wc + 1) * L['wclass_el']
        got = HP._h3_reserve(m, [sz_wc, L['wtype_el'], len(acts) * L['actions_el']])
        if not got:
            out.append('mode %d: no slack' % msid)
            continue
        off_wc, off_wt, off_ac = got
        for i, (label, anim) in enumerate(acts):
            struct.pack_into('<Ihh', m.data, off_ac + i * L['actions_el'],
                             label, graph_index, anim)
        m.data[off_wt:off_wt + L['wtype_el']] = \
            m.data[_ref(m, wc_base + L['wtype_blk'])[1]:
                   _ref(m, wc_base + L['wtype_blk'])[1] + L['wtype_el']]
        _set_ref(m, off_wt + L['actions_blk'], len(acts), off_ac)
        m.data[off_wc:off_wc + n_wc * L['wclass_el']] = \
            m.data[wc_base:wc_base + n_wc * L['wclass_el']]
        el = off_wc + n_wc * L['wclass_el']
        m.data[el:el + L['wclass_el']] = m.data[wc_base:wc_base + L['wclass_el']]
        struct.pack_into('<I', m.data, el, DUAL_SID)
        _set_ref(m, el + L['wtype_blk'], 1, off_wt)
        _set_ref(m, wc_ref, n_wc + 1, off_wc)
        out.append('mode %d: dual class, %d actions -> graph %d'
                   % (msid, len(acts), graph_index))
    return '; '.join(out) or 'no matching modes'


UNIT_GRAPHS = ('objects\\characters\\odst_recon\\odst_recon',
               'objects\\characters\\odst_oni_op\\odst_oni_op_player')
UNIT_MODES = (140, 143)            # 'combat' and 'crouch'
CLASS_PISTOL = 792                 # the one-handed class to copy poses from


def add_dual_to_unit(m, tag_path, mode_sids=UNIT_MODES, template=CLASS_PISTOL):
    """Give the UNIT animation graph a `dual` weapon class on the given modes.

    The fp graph is what the player SEES; this is the graph the engine consults for what
    the character can do, and stock ODST has no `dual` class on `combat` or `crouch` --
    only unarmed / any / missile / support / rifle / pistol / sword. The reference mod
    adds one to both, with 15-16 locomotion actions (idle, turn, move_*, airborne,
    land_*) inherited from Chief's unit graph.

    Here the class is built LOCALLY instead, by copying the one-handed `pistol` class's
    actions verbatim. The body will hold itself as if carrying one pistol rather than
    two weapons -- wrong, and deliberately so: this tests only whether the presence of a
    dual class on the unit graph is what gates the dual-wield state.
    """
    base = None
    for n, b in m.find_tags('jmad', '*'):
        if n == tag_path:
            base = b
            break
    if base is None:
        return 'no %s' % tag_path

    done = []
    for mode in m.follow_all(base, [L['modes_blk']], [L['modes_el']], 'all'):
        msid = struct.unpack_from('<I', m.data, mode)[0]
        if msid not in mode_sids:
            continue
        wc_ref = mode + L['wclass_blk']
        n_wc, wc_base = _ref(m, wc_ref)
        if not wc_base:
            continue
        tmpl = None
        for i in range(n_wc):
            sid = struct.unpack_from('<I', m.data, wc_base + i * L['wclass_el'])[0]
            if sid == DUAL_SID:
                tmpl = 'already'
                break
            if sid == template:
                tmpl = wc_base + i * L['wclass_el']
        if tmpl == 'already':
            done.append('mode %d already has dual' % msid)
            continue
        if tmpl is None:
            done.append('mode %d has no class %d to copy' % (msid, template))
            continue

        n_wt, wt_base = _ref(m, tmpl + L['wtype_blk'])
        if not wt_base or n_wt < 1:
            done.append('mode %d template has no Weapon Type' % msid)
            continue
        n_ac, ac_base = _ref(m, wt_base + L['actions_blk'])
        if not ac_base or n_ac < 1:
            done.append('mode %d template has no Actions' % msid)
            continue

        sz_wc = (n_wc + 1) * L['wclass_el']
        sz_wt = L['wtype_el']
        sz_ac = n_ac * L['actions_el']
        got = HP._h3_reserve(m, [sz_wc, sz_wt, sz_ac])
        if not got:
            done.append('mode %d: no slack for %d bytes' % (msid, sz_wc + sz_wt + sz_ac))
            continue
        off_wc, off_wt, off_ac = got

        m.data[off_ac:off_ac + sz_ac] = m.data[ac_base:ac_base + sz_ac]
        m.data[off_wt:off_wt + sz_wt] = m.data[wt_base:wt_base + sz_wt]
        _set_ref(m, off_wt + L['actions_blk'], n_ac, off_ac)
        m.data[off_wc:off_wc + n_wc * L['wclass_el']] = \
            m.data[wc_base:wc_base + n_wc * L['wclass_el']]
        new_el = off_wc + n_wc * L['wclass_el']
        m.data[new_el:new_el + L['wclass_el']] = m.data[tmpl:tmpl + L['wclass_el']]
        struct.pack_into('<I', m.data, new_el, DUAL_SID)
        _set_ref(m, new_el + L['wtype_blk'], 1, off_wt)
        _set_ref(m, wc_ref, n_wc + 1, off_wc)
        done.append('mode %d: dual class from class %d (%d actions)'
                    % (msid, template, n_ac))
    return '; '.join(done) or 'no matching modes'


def local_actions(m, tail, names):
    """Dual actions pointing at THIS graph's own animations, matched by action NAME.

    Each name reuses whatever animation the `any` class already plays for it -- so the
    dual state has something valid to play without importing anything. The animations are
    the single-wield ones and will not look right in two hands; that is the point of the
    test, not a defect to fix here.

    Matched by NAME, never by raw stringID: the id for a given name differs between the
    two games' string tables, and carrying Chief's ids across produced `aim_move_down`,
    `warn` and `sniff` where `misfire_1`, `overheating` and `o_h_exit` were meant.
    """
    _name, base = fp_graph(m, tail)
    if base is None:
        return []
    by_name = {}
    for mo in m.follow_all(base, [L['modes_blk']], [L['modes_el']], 'all'):
        for wc in m.follow_all(mo, [L['wclass_blk']], [L['wclass_el']], 'all'):
            for wt in m.follow_all(wc, [L['wtype_blk']], [L['wtype_el']], 'all'):
                for a in m.follow_all(wt, [L['actions_blk']], [L['actions_el']], 'all'):
                    sid = struct.unpack_from('<I', m.data, a)[0]
                    nm = m.resolve_stringid(sid)
                    if nm:
                        by_name.setdefault(nm, (sid,
                                                struct.unpack_from('<h', m.data,
                                                                   a + 6)[0]))
    return [by_name[n] for n in names if n in by_name]


# The action names Chief's dual class uses per weapon, from out/odst_dual_recipe.json.
DUAL_LABELS = {
    'fp_plasma_rifle': ['fire_1', 'idle', 'ready', 'put_away', 'posing', 'misfire_1',
                        'overheating', 'o_h_exit'],
    'fp_magnum': ['fire_1', 'idle', 'ready', 'put_away', 'posing', 'reload_empty',
                  'reload_full'],
    'fp_smg': ['fire_1', 'idle', 'ready', 'put_away', 'posing', 'reload_empty',
               'reload_full'],
    'fp_spike_rifle': ['fire_1', 'idle', 'ready', 'put_away', 'posing', 'reload_empty',
                       'reload_full'],
    'fp_excavator': ['fire_1', 'idle', 'ready', 'put_away', 'posing', 'reload_empty',
                     'reload_full'],
    'fp_plasma_pistol': ['fire_1', 'fire_2', 'idle', 'ready', 'put_away', 'posing',
                         'overheated', 'overcharged', 'overheating', 'o_h_exit'],
}


BAK_SUFFIX = '.dualwield.bak'


def targets_for(path):
    """The map files a flag has to be written to for the change to STICK.

    The enhancer patches FROM `<map>.map.bak` and rebuilds the live map from it every
    time, so flagging only the live map means the next ordinary patch silently undoes
    the test. The baseline gets the same edit, and --revert puts both back.
    """
    out = [path]
    bak = path + '.bak'
    if os.path.exists(bak):
        out.append(bak)
    return out


def patch_one(path, weapon):
    """Set Can Be Dual Wielded on one weapon, in place. Returns a report string."""
    import shutil
    m = HP.open_map(path, GAME)
    hit = None
    for name, base in m.find_tags('weap', '*' + weapon):
        if name.rsplit(chr(92), 1)[-1] == weapon:
            hit = (name, base)
            break
    if not hit:
        return 'no weapon %r in this map' % weapon
    name, base = hit
    off = base + WEAP_FLAGS
    old = struct.unpack_from('<I', m.data, off)[0]
    new = old | (1 << DUAL_BIT)
    if new == old:
        return '%s already has the flag (%08X)' % (weapon, old)
    bak = path + BAK_SUFFIX
    if not os.path.exists(bak):
        shutil.copyfile(path, bak)
    struct.pack_into('<I', m.data, off, new)
    m.save(path)
    return '%s: flags %08X -> %08X   (backup: %s)' % (weapon, old, new,
                                                      os.path.basename(bak))


def patch(path, weapon):
    return '; '.join('%s -> %s' % (os.path.basename(t), patch_one(t, weapon))
                     for t in targets_for(path))


def revert(path):
    import shutil
    done = []
    for t in targets_for(path):
        bak = t + BAK_SUFFIX
        if not os.path.exists(bak):
            continue
        shutil.copyfile(bak, t)
        os.remove(bak)
        done.append(os.path.basename(t))
    return ('restored ' + ', '.join(done)) if done else         'no %s beside this map' % BAK_SUFFIX


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--map', default='sc130')
    ap.add_argument('--mod', action='store_true',
                    help='also survey the reference mod\'s copy of the same map')
    ap.add_argument('--patch', metavar='WEAPON',
                    help='set Can Be Dual Wielded on this weapon, in place')
    ap.add_argument('--revert', action='store_true',
                    help='undo --patch from the .dualwield.bak beside the map')
    ap.add_argument('--add-dual', metavar='FP_GRAPH',
                    help='add a dual weapon class to this fp graph, in place')
    ap.add_argument('--add-dual-unit', action='store_true',
                    help='add a dual weapon class to the UNIT graph, in place')
    ap.add_argument('--wire-player', metavar='MAPFILE',
                    help='inheritance + dual classes on odst_oni_op_player, the graph '
                         'the player model actually uses')
    ap.add_argument('--wire-unit', metavar='MAPFILE',
                    help='inheritance entry + inherited dual classes on the unit graph '
                         'of a BUILT map file (needs Chief\'s unit graph present)')
    a = ap.parse_args(argv)

    p = V.resolve(GAME, a.map)
    if not p:
        print('map not found: %s' % a.map)
        return 1

    if a.revert:
        print('%s: %s' % (a.map, revert(p)))
        return 0
    if a.patch:
        print('%s: %s' % (a.map, patch(p, a.patch)))
        return 0
    if a.wire_player:
        import shutil
        for t in (a.wire_player, a.wire_player + '.bak'):
            if not os.path.exists(t):
                continue
            m = HP.open_map(t, GAME)
            idx, msg = add_inheritance(m, PLAYER_GRAPH, CHIEF_UNIT,
                                       node_map=PLAYER_NODE_MAP,
                                       node_flags=PLAYER_NODE_FLAGS,
                                       root_z=PLAYER_ROOT_Z)
            print('   %s: %s' % (os.path.basename(t), msg))
            if idx is None:
                continue
            print('   %s: %s' % (os.path.basename(t),
                                 add_unit_dual_inherited(m, PLAYER_GRAPH, idx)))
            bak = t + BAK_SUFFIX
            if not os.path.exists(bak):
                shutil.copyfile(t, bak)
            m.save(t)
        return 0

    if a.wire_unit:
        import shutil
        t = a.wire_unit
        m = HP.open_map(t, GAME)
        graph = 'objects' + chr(92) + 'characters' + chr(92) + 'odst_recon' + \
            chr(92) + 'odst_recon'
        idx, msg = add_inheritance(m, graph, CHIEF_UNIT)
        print('   %s' % msg)
        if idx is None:
            return 1
        print('   %s' % add_unit_dual_inherited(m, graph, idx))
        # and the first-person half, if Chief's fp graph made it into this build
        for tail in sorted(CHIEF_FP):
            print('   %s' % wire_fp(m, tail))
        bak = t + BAK_SUFFIX
        if not os.path.exists(bak):
            shutil.copyfile(t, bak)
        m.save(t)
        print('   saved %s' % t)
        return 0

    if a.add_dual_unit:
        import shutil
        for t in targets_for(p):
            m = HP.open_map(t, GAME)
            reps = [add_dual_to_unit(m, g) for g in UNIT_GRAPHS]
            if all(r.startswith('no ') for r in reps):
                print('   %s -> %s' % (os.path.basename(t), '; '.join(reps)))
                continue
            bak = t + BAK_SUFFIX
            if not os.path.exists(bak):
                shutil.copyfile(t, bak)
            m.save(t)
            for g, r in zip(UNIT_GRAPHS, reps):
                print('   %s  %s -> %s'
                      % (os.path.basename(t), g.rsplit(chr(92), 1)[-1], r))
        return 0

    if a.add_dual:
        import shutil
        tail = a.add_dual
        for t in targets_for(p):
            m = HP.open_map(t, GAME)
            labels = DUAL_LABELS.get(tail)
            if not labels:
                print('no dual action labels recorded for %s' % tail)
                return 1
            acts = local_actions(m, tail, labels)
            if len(acts) < len(labels):
                print('   %s: only %d of %d labels exist in the `any` class'
                      % (os.path.basename(t), len(acts), len(labels)))
            rep = add_dual_class(m, tail, acts)
            if rep.startswith('no ') or 'already' in rep or 'has no' in rep:
                print('   %s -> %s' % (os.path.basename(t), rep))
                continue
            bak = t + BAK_SUFFIX
            if not os.path.exists(bak):
                shutil.copyfile(t, bak)
            m.save(t)
            print('   %s -> %s' % (os.path.basename(t), rep))
        return 0

    survey(HP.open_map(p, GAME), 'STOCK %s' % a.map)
    if a.mod:
        mp = os.path.join(MOD_MAPS, a.map + '.map')
        if os.path.exists(mp):
            survey(HP.open_map(mp, GAME), 'REFERENCE MOD %s' % a.map)
        else:
            print('\n(no mod copy of %s)' % a.map)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
