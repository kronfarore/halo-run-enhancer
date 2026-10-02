r"""Halo 1: clone actor variants (actv) so a SHARE of an enemy's spawns carries another
weapon (2026-10-02).

Proven before this: the actv Weapon tagref (+0x64) alone decides an H1 AI's weapon,
and a weapon the biped's animations lack falls back to the biped default unless the
antr is taught the label (h1_teach_weapon.py). Changing a variant in place is 100%;
a share needs a NEW variant, which needs a new TAG -- nothing here could add one.

ADDING A TAG. H1 loads the tag-data region at 0x50000000 (index header at its start,
tag array normally right after at +0x28). The array is relocated to the end of the
file with the new entries appended, and the header's array pointer (+0x0) and count
(+0xC) updated; every other pointer is magic-relative and unmoved. A new entry is
0x20 bytes: class fourcc x3 (reversed), tag id ((salt << 16) | index), name pointer,
meta pointer, 8 zero bytes. halo_map.HaloMap derives its magic from the fixed base
for that reason (a relocated array would otherwise skew it).

CLONING. The 0x238-byte actv struct is copied, its Change Colors block (+0x22C,
elem 0x20) deep-copied so the clone owns it (enemy colours write per variant), the
Weapon ref repointed, the firing behaviour overwritten from a DONOR, and the clone
of the minor variant linked (Major Variant +0x24) to the clone of the major.

DONORS (user, 2026-10-02): every actv in the WHOLE GAME (all ten levels) that already
carries the target weapon is a candidate; the one most similar to the character being
taught wins -- same biped first, then the smallest relative difference over the
actv's non-weapon numbers (vitality, perception, movement, grenades). Its minor gives
the clone minor's firing block, its major (or minor again) the clone major's.
Firing block = 0x74-0x15F (ranges, rate, error, bursts, special fire) and
0x1D8-0x1E3 (dropped-weapon ammo); neither holds a reference.

NAMING. A clone is '<source path> with <weapon name>', e.g.
'characters\grunt\grunt minor plasma pistol with assault rifle'. General cards on
'characters\grunt\*' reach it; weapon-specific ones ('*plasma pistol') rightly do not.

SPAWNS. The minor clone is appended to the scenario Actor Palette (+0x420, elem 0x10)
and a share of the source's starting locations (Encounters +0x42C/0xB0 > Squads
+0x80/0xE8, Actor Type +0x20 > Starting Locations +0xD0/0x1C, Actor Type override
+0x18) is pointed at it, spread evenly.

    python h1_variants.py donors --weapon "weapons\assault rifle\assault rifle" --like "characters\grunt\grunt minor plasma pistol"
    python h1_variants.py build --map b30.map --out test.map --source "characters\grunt\grunt minor plasma pistol" --weapon "weapons\assault rifle\assault rifle" --share 0.5 [--teach pr]
"""
import argparse
import glob
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import halo_patch as hp  # noqa: E402

MAPS = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'halo1', 'maps')
LEVELS = ('a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40')

ACTV_SIZE = 0x238
REF_ACTOR, REF_UNIT, REF_MAJOR, REF_WEAPON = 0x04, 0x14, 0x24, 0x64
CHANGE_COLORS, CC_SZ = 0x22C, 0x20
FIRING = [(0x74, 0x160), (0x1D8, 0x1E4)]
# numbers that describe the CHARACTER rather than its weapon (similarity measure)
TRAITS = [(0x28, 0x64), (0x160, 0x1C0), (0x1D0, 0x1D8), (0x1E4, 0x22C)]

S_PALETTE, S_PAL_SZ = 0x420, 0x10
S_ENC, S_ENC_SZ = 0x42C, 0xB0
SQ, SQ_SZ, SQ_TYPE = 0x80, 0xE8, 0x20
SL, SL_SZ, SL_TYPE = 0xD0, 0x1C, 0x18
CLONE_SEP = ' with '    # was '~' until 2026-10-02: avoided as an untested character


# ----------------------------------------------------------------------------- tags
def _ref_name(m, base, off):
    d = m.u32(base + off + 0xC)
    if d in (0, 0xFFFFFFFF):
        return None
    return m.tag_name_by_id(d)


def add_tags(m, entries):
    """Append tags to the map's tag array. `entries` = [(cls, name, meta_bytes)].
    Returns [(tag id, meta file offset)]. The array moves to EOF; save() must follow."""
    io = m.index_off
    count = m.u32(io + 0xC)
    old = bytes(m.data[m.tag_array_off:m.tag_array_off + count * 0x20])
    last_salt = max(m.u32(m.tag_array_off + i * 0x20 + 0xC) >> 16 for i in range(count))
    new, out = [], []
    for k, (cls, name, meta) in enumerate(entries):
        idx = count + k
        salt = (last_salt + 1 + k) & 0xFFFF
        if salt == 0xFFFF:
            salt = 0xE174
        tid = (salt << 16) | idx
        name_off = m.append_raw(name.encode('latin-1') + b'\0')
        meta_off = m.append_raw(bytes(meta))
        four = cls.encode('latin-1')[::-1]
        e = bytearray(0x20)
        e[0:4] = four
        e[4:8] = b'\xff\xff\xff\xff'
        e[8:12] = b'\xff\xff\xff\xff'
        struct.pack_into('<IIII', e, 0xC, tid, (name_off + m.magic) & 0xFFFFFFFF,
                         (meta_off + m.magic) & 0xFFFFFFFF, 0)
        new.append(bytes(e))
        out.append((tid, meta_off))
    arr = m.append_raw(old + b''.join(new))
    struct.pack_into('<I', m.data, io, (arr + m.magic) & 0xFFFFFFFF)
    struct.pack_into('<I', m.data, io + 0xC, count + len(entries))
    m._parse_index()
    return out


# ----------------------------------------------------------------------------- donors
def _floats(m, base, spans):
    out = []
    for a, b in spans:
        for o in range(a, b, 4):
            v = struct.unpack_from('<f', m.data, base + o)[0]
            out.append(v if math.isfinite(v) and abs(v) < 1e6 else 0.0)
    return out


def _distance(a, b):
    tot = 0.0
    for x, y in zip(a, b):
        tot += abs(x - y) / (abs(x) + abs(y) + 1e-6)
    return tot / max(1, len(a))


def find_donors(weapon, like_unit, like_traits, maps=None):
    """Every actv in the game carrying `weapon`, ranked most-similar first.
    -> [(score, level, actv name, unit, major name or None, minor bytes, major bytes)]"""
    seen, out = set(), []
    for lvl in maps or LEVELS:
        p = os.path.join(MAPS, lvl + '.map')
        if not os.path.exists(p):
            continue
        m = hp.open_map(p, 'Halo 1')
        tags = dict(m.find_tags('actv', '*'))
        majors = {_ref_name(m, b, REF_MAJOR) for b in tags.values()} - {None}
        for name, b in tags.items():
            if CLONE_SEP in name or name in majors or _ref_name(m, b, REF_WEAPON) != weapon:
                continue
            if name in seen:
                continue
            seen.add(name)
            # scripted set-pieces (a wounded marine sitting against a wall) are not
            # combatants and make poor firing donors, however close their numbers
            if any(k in name.lower() for k in ('wounded', 'sitting', 'cinematic')):
                continue
            unit = _ref_name(m, b, REF_UNIT)
            score = 0.0 if unit == like_unit else 1.0
            score += _distance(_floats(m, b, TRAITS), like_traits)
            maj = _ref_name(m, b, REF_MAJOR)
            if not maj:
                score += 0.1                 # a minor+major pair gives both clones a donor
            mb = tags.get(maj)
            out.append((score, lvl, name, unit, maj,
                        bytes(m.data[b:b + ACTV_SIZE]),
                        bytes(m.data[mb:mb + ACTV_SIZE]) if mb is not None else None))
    out.sort(key=lambda r: r[0])
    return out


# ----------------------------------------------------------------------------- clone
def _weapon_ref(m, weapon):
    """A 16-byte tagref to `weapon` that this map resolves: copied from any tag
    already referencing it (an actv's Weapon, else the weap tag's own id)."""
    for _n, b in m.find_tags('actv', '*'):
        if _ref_name(m, b, REF_WEAPON) == weapon:
            return bytes(m.data[b + REF_WEAPON:b + REF_WEAPON + 16])
    tid = m.tag_id(('weap', weapon))
    if tid is None:
        return None
    ref = bytearray(16)
    ref[0:4] = b'paew'
    struct.pack_into('<I', ref, 4, m.tag_name_ptr(('weap', weapon)))
    struct.pack_into('<I', ref, 0xC, tid)
    return bytes(ref)


def _clone_bytes(m, src_base, weref, donor):
    b = bytearray(m.data[src_base:src_base + ACTV_SIZE])
    b[REF_WEAPON:REF_WEAPON + 16] = weref
    if donor is not None:
        for lo, hi in FIRING:
            b[lo:hi] = donor[lo:hi]
    # own Change Colors copy
    n = m.u32(src_base + CHANGE_COLORS)
    if n:
        src = (m.u32(src_base + CHANGE_COLORS + 4) - m.magic) & 0xFFFFFFFF
        off = m.append_raw(bytes(m.data[src:src + n * CC_SZ]))
        struct.pack_into('<I', b, CHANGE_COLORS + 4, (off + m.magic) & 0xFFFFFFFF)
    return b


def clone_variant(m, source, weapon, donor_minor=None, donor_major=None):
    """Clone `source` (and its Major Variant) to carry `weapon`. Returns the new
    minor tag id and name."""
    tags = dict(m.find_tags('actv', '*'))
    sb = tags[source]
    weref = _weapon_ref(m, weapon)
    if weref is None:
        raise SystemExit('this level has no %s' % weapon)
    wshort = weapon.rsplit(chr(92), 1)[-1]
    entries = []
    major = _ref_name(m, sb, REF_MAJOR)
    if major and major in tags:
        entries.append(('actv', major + CLONE_SEP + wshort,
                        _clone_bytes(m, tags[major], weref, donor_major or donor_minor)))
    entries.append(('actv', source + CLONE_SEP + wshort,
                    _clone_bytes(m, sb, weref, donor_minor)))
    ids = add_tags(m, entries)
    if len(ids) == 2:                      # minor -> its cloned major
        (maj_id, _mo), (_min_id, min_off) = ids
        name_ptr = m.tag_name_ptr(('actv', entries[0][1]))
        ref = bytearray(m.data[min_off + REF_MAJOR:min_off + REF_MAJOR + 16])
        struct.pack_into('<I', ref, 4, name_ptr)
        struct.pack_into('<I', ref, 0xC, maj_id)
        m.data[min_off + REF_MAJOR:min_off + REF_MAJOR + 16] = ref
    return ids[-1][0], entries[-1][1]


# ----------------------------------------------------------------------------- spawns
def _elems(m, at, size):
    n = m.u32(at)
    if not n or n > 100000:
        return []
    base = (m.u32(at + 4) - m.magic) & 0xFFFFFFFF
    return [base + i * size for i in range(n)]


def repoint_share(m, source, clone_id, clone_name, share):
    """Add the clone to the Actor Palette and point `share` of the source's starting
    locations at it, evenly spread. Returns (moved, of)."""
    s = hp._scnr_base(m)
    pal = _elems(m, s + S_PALETTE, S_PAL_SZ)
    names = [m.tag_name_by_id(m.u32(p + 0xC)) for p in pal]
    src_idx = {i for i, n in enumerate(names) if n == source}
    if not src_idx:
        return 0, 0
    if clone_name in names:                  # built in (Sapien): reuse its entry
        new_idx = names.index(clone_name)
    else:
        ref = bytearray(m.data[pal[min(src_idx)]:pal[min(src_idx)] + 16])
        struct.pack_into('<I', ref, 4, m.tag_name_ptr(('actv', clone_name)))
        struct.pack_into('<I', ref, 0xC, clone_id)
        new_idx = len(pal)
        m.grow_block(s, S_PALETTE, S_PAL_SZ, [bytes(ref)])
    spawns = []
    for enc in _elems(m, s + S_ENC, S_ENC_SZ):
        for sq in _elems(m, enc + SQ, SQ_SZ):
            sq_type = struct.unpack_from('<h', m.data, sq + SQ_TYPE)[0]
            for sl in _elems(m, sq + SL, SL_SZ):
                ov = struct.unpack_from('<h', m.data, sl + SL_TYPE)[0]
                if (ov if ov >= 0 else sq_type) in src_idx:
                    spawns.append(sl)
    want = int(round(share * len(spawns)))
    moved = 0
    for k, sl in enumerate(spawns):          # even spread: k-th spawn when the quota rises
        if int((k + 1) * want / max(1, len(spawns))) > int(k * want / max(1, len(spawns))):
            struct.pack_into('<h', m.data, sl + SL_TYPE, new_idx)
            moved += 1
    return moved, len(spawns)


# ----------------------------------------------------------------------------- cli
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    d = sub.add_parser('donors')
    d.add_argument('--weapon', required=True)
    d.add_argument('--like', required=True)
    d.add_argument('--map', default=os.path.join(MAPS, 'b30.map'))
    b = sub.add_parser('build')
    b.add_argument('--map', required=True)
    b.add_argument('--out', required=True)
    b.add_argument('--source', required=True)
    b.add_argument('--weapon', required=True)
    b.add_argument('--share', type=float, default=0.5)
    b.add_argument('--teach', metavar='DONOR_LABEL', help="also teach the biped's antr the weapon label from this donor label")
    sh = sub.add_parser('share', help='point a share of a variant spawns at a clone ALREADY in the map (kit-built)')
    sh.add_argument('--map', required=True)
    sh.add_argument('--out', required=True)
    sh.add_argument('--source', required=True)
    sh.add_argument('--clone', required=True)
    sh.add_argument('--share', type=float, default=0.5)
    a = ap.parse_args()
    if a.cmd == 'share':
        m = hp.open_map(a.map, 'Halo 1')
        tid = m.tag_id(('actv', a.clone))
        if tid is None:
            raise SystemExit('the clone is not in this map: ' + a.clone)
        moved, of = repoint_share(m, a.source, tid, a.clone, a.share)
        print('%d of %d %s spawns -> %s' % (moved, of, a.source.split(chr(92))[-1], a.clone.split(chr(92))[-1]))
        m.save(a.out)
        print('written:', a.out)
        return

    m = hp.open_map(a.map, 'Halo 1')
    like = a.like if a.cmd == 'donors' else a.source
    tags = dict(m.find_tags('actv', '*'))
    lb = tags[like]
    ranked = find_donors(a.weapon, _ref_name(m, lb, REF_UNIT), _floats(m, lb, TRAITS))
    for score, lvl, name, unit, maj, _mi, _ma in ranked[:8]:
        print('  %.3f  %-4s %-55s major=%s' % (score, lvl, name, (maj or '-').split(chr(92))[-1]))
    if a.cmd == 'donors':
        return
    if not ranked:
        raise SystemExit('no actv in the game carries %s' % a.weapon)
    _s, lvl, dname, _u, _maj, dmin, dmaj = ranked[0]
    print('donor: %s (%s)' % (dname, lvl))
    if a.teach:
        import h1_teach_weapon as tw
        unit = _ref_name(m, lb, REF_UNIT)
        bipd = dict(m.find_tags('bipd', '*')).get(unit)
        antr = _ref_name(m, bipd, 0x38) if bipd is not None else None  # obje Animation Graph
        label = m.weapon_label(a.weapon)
        for p, base in m.find_tags('antr', antr or '-'):
            print('  taught %r in %s: %d class(es)' % (label, p, tw.teach(m, base, a.teach, label)))
    cid, cname = clone_variant(m, a.source, a.weapon, dmin, dmaj)
    moved, of = repoint_share(m, a.source, cid, cname, a.share)
    print('clone %s id %#x; %d of %d spawns repointed' % (cname, cid, moved, of))
    m.save(a.out)
    print('written:', a.out)


if __name__ == '__main__':
    main()
