r"""Halo 2 AI firing data for a PORTED weapon: append (or replace) its entries in H2EK
`ai\generic.character` -- the Halo 2 half of the Armed cards (H2_PORT_PLAN.md 0.5 / 0.5b).

WHY THE TAG. A Halo 2 character finds its firing behaviour for a weapon by the weapon's tag
reference, in two blocks of the character (elite / grunt / brute / jackal / marine all name
`ai\generic` as parent; their own blocks are near-empty overrides):
  Weapons Properties         ranges, first-burst / surprise delays, special fire, drops,
                             accuracy bounds per difficulty
  Firing Pattern Properties  the weapon ref + TWO Firing Patterns ('inaccurate' -> 'really
                             accurate'; the accuracy bounds blend between them)
A weapon with no entry has no firing data at all (the SAW before this tool). Written into the
kit tag, every rebuilt level carries it and every character fires the port wherever a squad
hands it over -- no patch-time copy (Halo 1 needed one per actor variant).

THE VALUES (ai_firing_profile.h2_profile): a SAME-GAME DONOR's two entries are the base (a
stock Halo 2 weapon the port plays like, config `donor_weapon`), and every field the SOURCE
game's ai\generic entry has is copied over it BY NAME -- both patterns kept apart (no
averaging: Halo 2 has two, like the source). The field names are Halo 3's in all four source
games; Halo 2-only fields (timid / aggressive combat range from a Halo 4 source) stay the
donor's. Zeros ARE copied: in Halo 2 as in the sources a 0 rate of fire / damage modifier means
'the weapon's own' (37 of 38 stock pattern pairs carry WDM 0, the BR rate of fire 0). Flags and
enums stay the donor's unless the source is Halo 3 / ODST (same enum tables). Config `set`
rows ('<field name>[#pattern]=value') go on top.

LOOSE LAYOUT (decoded 2026-10-20 on generic.character; memory halo2-loose-tag-format):
  root +0x144 Weapons Properties count, chunk version 1, element 0xE0 (cache 0xCC):
      0x0 flags, 0x4 weapon tagref (16), cache fields 0xC..0xBC at +8, 0xC4 inner Firing
      Patterns block (12; empty in every stock entry -> no chunk), 0xD0 melee damage tagref.
      Children per element, in element order: the pooled ref paths (weapon, melee), then the
      inner patterns chunk if any.
  root +0x150 Firing Pattern Properties count, chunk version 0, element 0x1C: weapon tagref
      0x0, Firing Patterns block 0x10 (count). Children per element: the weapon path, then a
      'dfbt' chunk (version 0, n, 0x40) + n patterns (cache layout = loose layout).
Every write is checked by `tool export-tag-to-xml`: every OTHER element must export exactly as
before, and the port's two entries must print the values written (else the tag is put back).

    python h2_ai_firing.py --list                       the weapons with entries
    python h2_ai_firing.py --show <weapon tag>          one weapon's entries as tool prints them
    python h2_ai_firing.py --remove <weapon tag>        (H2 kit lock)
The write itself runs from the port's config:  python ai_firing_profile.py --h2-port saw
"""
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h2_tagfield  # noqa: E402

H2EK = h2_tagfield.H2EK
GENERIC = os.path.join(H2EK, 'tags', 'ai', 'generic.character')
# the STOCK tag, copied once before the first write (memory halo-backups-on-e-drive)
BACKUP = os.path.join('E:' + os.sep, 'HaloBackups', 'h2_ai_firing', 'generic.character.stock')
SIG = b'dfbt'
CHUNK = 0x10
ROOT = 0x50

PROPS_ROOT, PROPS_ES, PROPS_VER = 0x144, 0xE0, 1
PROPS_REFS = (0x4, 0xD0)            # weapon, weapon melee damage
PROPS_INNER = 0xC4                  # inner Firing Patterns block (count), cache +0xBC
FPP_ROOT, FPP_ES, FPP_VER = 0x150, 0x1C, 0
FPP_REF, FPP_PATTERNS = 0x0, 0x10
PAT_ES, PAT_VER = 0x40, 0


def props_loose(cache_off):
    """A Weapons Properties field's cache offset (Assembly plugin) -> its loose offset."""
    if cache_off < 0x4:
        return cache_off
    if 0xC <= cache_off < 0xBC:
        return cache_off + 8
    raise ValueError('Weapons Properties +0x%X is a reference / block, not a value' % cache_off)


# --- reading -------------------------------------------------------------------

def _count(data, root_off):
    return struct.unpack_from('<I', data, ROOT + root_off)[0]


def _chunk(data, root_off, es, after=0):
    """The block's chunk: the first 'dfbt' after `after` with this count and element size
    (both blocks have one unambiguous match in generic.character -- checked by blocks())."""
    n = _count(data, root_off)
    if not n:
        return None
    i = data.find(SIG, after)
    while i >= 0:
        cnt, size = struct.unpack_from('<II', data, i + 8)
        if cnt == n and size == es:
            return i
        i = data.find(SIG, i + 4)
    raise ValueError('no chunk for root+0x%X (%d x 0x%X)' % (root_off, n, es))


def _ref_len(data, at):
    return struct.unpack_from('<I', data, at + 8)[0]


def _walk(data, chunk, n, es, refs, inner):
    """[(element offset, [ref paths], children start, children end)] and the block's end.
    Children per element = its pooled paths in field order, then its inner block's chunk."""
    out = []
    pos = chunk + CHUNK + n * es
    for i in range(n):
        e = chunk + CHUNK + i * es
        start = pos
        paths = []
        for r in refs:
            ln = _ref_len(data, e + r)
            paths.append(bytes(data[pos:pos + ln]).decode('latin-1') if ln else '')
            pos += ln + 1 if ln else 0
        k = struct.unpack_from('<I', data, e + inner)[0]
        if k:
            if bytes(data[pos:pos + 4]) != SIG:
                raise ValueError('element %d: expected its inner chunk at 0x%X' % (i, pos))
            ver, cnt, size = struct.unpack_from('<III', data, pos + 4)
            if cnt != k or size != PAT_ES:
                raise ValueError('element %d: inner chunk %d x 0x%X, element says %d'
                                 % (i, cnt, size, k))
            pos += CHUNK + cnt * size
        out.append((e, paths, start, pos))
    return out, pos


def blocks(data):
    """{'props': (chunk, [elements]), 'fpp': (chunk, [elements])}; FPP must start exactly
    where the props block ends (adjacent root fields, depth-first) -- the layout check."""
    pc = _chunk(data, PROPS_ROOT, PROPS_ES)
    pe, pend = _walk(data, pc, _count(data, PROPS_ROOT), PROPS_ES, PROPS_REFS, PROPS_INNER)
    fc = _chunk(data, FPP_ROOT, FPP_ES, pend)
    if fc != pend:
        raise ValueError('Firing Pattern Properties chunk at 0x%X, props end at 0x%X' % (fc, pend))
    fe, fend = _walk(data, fc, _count(data, FPP_ROOT), FPP_ES, (FPP_REF,), FPP_PATTERNS)
    return {'props': (pc, pe, pend), 'fpp': (fc, fe, fend)}


def entries(data):
    b = blocks(data)
    return ([p[0] for _e, p, _s, _t in b['props'][1]], [p[0] for _e, p, _s, _t in b['fpp'][1]])


def find(data, weapon):
    """(props element offset or None, fpp element offset or None, [pattern offsets])."""
    b = blocks(data)
    pe = next((e for e, p, _s, _t in b['props'][1] if p[0].lower() == weapon.lower()), None)
    fe, pats = None, []
    for e, p, s, t in b['fpp'][1]:
        if p[0].lower() == weapon.lower():
            fe = e
            k = struct.unpack_from('<I', data, e + FPP_PATTERNS)[0]
            first = t - k * PAT_ES
            pats = [first + j * PAT_ES for j in range(k)]
            break
    return pe, fe, pats


# --- writing -------------------------------------------------------------------

def _bump(data, chunk, root_off, delta):
    n = struct.unpack_from('<I', data, chunk + 8)[0] + delta
    struct.pack_into('<I', data, chunk + 8, n)
    struct.pack_into('<I', data, ROOT + root_off, n)


def remove(data, weapon):
    """Drop the weapon's element (and its children) from both blocks. True if any was there."""
    hit = False
    for key, root_off, es in (('fpp', FPP_ROOT, FPP_ES), ('props', PROPS_ROOT, PROPS_ES)):
        chunk, els, _end = blocks(data)[key]
        for e, paths, s, t in els:
            if paths[0].lower() == weapon.lower():
                if len(els) == 1:
                    raise ValueError('refusing to empty the %s block' % key)
                del data[s:t]               # children first (higher offset)
                del data[e:e + es]
                _bump(data, chunk, root_off, -1)
                hit = True
                break
    return hit


def append(data, weapon, props_elem, melee_path, patterns):
    """Append the weapon's Weapons Properties element (0xE0 bytes; its tagref lengths are set
    here) and its Firing Pattern Properties element with `patterns` (each 0x40 bytes)."""
    if any(p.lower() == weapon.lower() for lst in entries(data) for p in lst):
        raise ValueError('%s already has an entry -- remove it first' % weapon)
    w = weapon.encode('latin-1')
    b = blocks(data)
    # FPP first: it sits after the props block, so its splices leave the props offsets alone
    fc, fe, fend = b['fpp']
    pe = bytearray(FPP_ES)
    pe[0:16] = b'paew' + b'\0' * 4 + struct.pack('<I', len(w)) + b'\xff' * 4
    struct.pack_into('<I', pe, FPP_PATTERNS, len(patterns))
    kids = w + b'\0'
    if patterns:
        kids += SIG + struct.pack('<III', PAT_VER, len(patterns), PAT_ES) + b''.join(patterns)
    data[fend:fend] = kids
    data[fc + CHUNK + len(fe) * FPP_ES:fc + CHUNK + len(fe) * FPP_ES] = bytes(pe)
    _bump(data, fc, FPP_ROOT, +1)
    # then Weapons Properties
    pc, pels, pend = b['props']
    e = bytearray(props_elem)
    m = (melee_path or '').encode('latin-1')
    e[0x4:0x14] = b'paew' + b'\0' * 4 + struct.pack('<I', len(w)) + b'\xff' * 4
    e[0xD0:0xE0] = b'!tpj' + b'\0' * 4 + struct.pack('<I', len(m)) + b'\xff' * 4
    struct.pack_into('<I', e, PROPS_INNER, 0)          # the patterns live in the FPP block
    data[pend:pend] = w + b'\0' + (m + b'\0' if m else b'')
    data[pc + CHUNK + len(pels) * PROPS_ES:pc + CHUNK + len(pels) * PROPS_ES] = bytes(e)
    _bump(data, pc, PROPS_ROOT, +1)
    blocks(data)                                        # re-walk: the layout must still parse


# --- the export check ------------------------------------------------------------

def export_rows(path=GENERIC):
    xml = h2_tagfield.export(path)
    if not xml:
        raise RuntimeError('tool export-tag-to-xml failed on %s' % path)
    return _rows(xml)


def _rows(xml):
    """[(block, element ordinal, weapon of that element, field, text)] for the two blocks.
    Each element is labelled by its weapon so a list before/after an append compares."""
    import re
    out = []
    for blk in ('weapons properties', 'firing pattern properties'):
        i = xml.find('<block name="%s">' % blk)
        if i < 0:
            continue
        # the block ends at the matching close: count nested opens
        depth, j = 0, i
        tok = re.compile(r'<(/?)block\b')
        for m in tok.finditer(xml, i):
            depth += -1 if m.group(1) else 1
            if depth == 0:
                j = m.end()
                break
        seg = xml[i:j]
        for n, el in enumerate(re.split(r'\n\t\t<element index="\d+">', seg)[1:]):
            wm = re.search(r'<tag_reference name="weapon" type="weap">([^<]*)<', el)
            weap = wm.group(1) if wm else ''
            pat = -1
            for m in re.finditer(r'<element index="(\d+)"[^>]*>|<field name="([^"]+)" type="[^"]+">([^<]*)<'
                                 r'|<tag_reference name="([^"]+)"(?: type="[^"]+">([^<]*)<| />)', el):
                if m.group(1) is not None:
                    pat = int(m.group(1))
                elif m.group(2):
                    out.append((blk, n, weap, '%s%s' % (m.group(2), '' if pat < 0 else '#%d' % pat),
                                m.group(3).strip()))
                elif m.group(4):
                    out.append((blk, n, weap, m.group(4), (m.group(5) or '').strip()))
    return out


def write_checked(weapon, props_elem, melee_path, patterns, expect, path=GENERIC):
    """Replace the weapon's entries in the kit tag and PROVE it with an export: every other
    element unchanged, the weapon's rows = `expect` ({(block, field): text predicate}).
    The tag is put back if anything fails. Caller holds the H2 kit lock."""
    if path == GENERIC and not os.path.exists(BACKUP):
        os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
        shutil.copy2(path, BACKUP)
        print('stock ai\\generic backed up -> %s' % BACKUP)
    before = export_rows(path)
    keep = path + '.h2_ai_firing_keep'
    shutil.copy2(path, keep)
    try:
        d = bytearray(open(path, 'rb').read())
        removed = remove(d, weapon)
        append(d, weapon, props_elem, melee_path, patterns)
        open(path, 'wb').write(bytes(d))
        after = export_rows(path)
        others_b = [r[0:1] + r[2:] for r in before if r[2].lower() != weapon.lower()]
        others_a = [r[0:1] + r[2:] for r in after if r[2].lower() != weapon.lower()]
        if others_a != others_b:
            diff = [x for x in others_a if x not in others_b][:5]
            raise RuntimeError('other elements changed in the export: %s' % diff)
        mine = {(r[0], r[3].lower()): r[4] for r in after if r[2].lower() == weapon.lower()}
        bad = []
        for k, ok in expect.items():
            if k not in mine or not ok(mine[k]):
                bad.append((k, mine.get(k)))
        if bad:
            raise RuntimeError('written values do not export as expected: %s' % bad[:8])
        n_p = sum(1 for r in after if r[0] == 'weapons properties' and r[2].lower() == weapon.lower()
                  and r[3] == 'weapon')
        n_f = sum(1 for r in after if r[0] == 'firing pattern properties'
                  and r[2].lower() == weapon.lower() and r[3] == 'weapon')
        if (n_p, n_f) != (1, 1):
            raise RuntimeError('expected one entry per block, export shows %d / %d' % (n_p, n_f))
    except BaseException:
        shutil.copy2(keep, path)
        os.remove(keep)
        raise
    os.remove(keep)
    return {'replaced': removed, 'rows': len(mine), 'others': len(others_a)}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--show')
    ap.add_argument('--remove')
    ap.add_argument('--tag', default=GENERIC)
    a = ap.parse_args()
    if a.list:
        p, f = entries(open(a.tag, 'rb').read())
        print('Weapons Properties (%d):' % len(p))
        for i, w in enumerate(p):
            print('  %2d %s' % (i, w))
        print('Firing Pattern Properties (%d):' % len(f))
        for i, w in enumerate(f):
            print('  %2d %s' % (i, w))
    elif a.show:
        for r in export_rows(a.tag):
            if r[2].lower() == a.show.lower():
                print('%-26s %-36s %s' % (r[0], r[3], r[4]))
    elif a.remove:
        import kit_lock
        with kit_lock.held('h2_ai_firing --remove %s' % a.remove, kit='h2'):
            before = export_rows(a.tag)
            d = bytearray(open(a.tag, 'rb').read())
            if not remove(d, a.remove):
                raise SystemExit('%s has no entry' % a.remove)
            keep = a.tag + '.h2_ai_firing_keep'
            shutil.copy2(a.tag, keep)
            open(a.tag, 'wb').write(bytes(d))
            after = export_rows(a.tag)
            if [r[0:1] + r[2:] for r in before if r[2].lower() != a.remove.lower()] != \
                    [r[0:1] + r[2:] for r in after]:
                shutil.copy2(keep, a.tag)
                os.remove(keep)
                raise SystemExit('export changed beyond the removed entry -- tag put back')
            os.remove(keep)
            print('removed %s (export-checked)' % a.remove)
    else:
        ap.print_help()


if __name__ == '__main__':
    main()
