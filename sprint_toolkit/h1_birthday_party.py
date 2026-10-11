r"""Halo 1: Grunt Birthday Party in CLASSIC graphics (halo1.dll patch, opt-in).

The skull (flavour 11) only ever spawns `sfx_konfetti` + `skull_laugh`, Anniversary effects
that classic graphics never draw (user, 2026-10-11: no confetti in classic with any weapon).
The test itself runs in classic too (PORTING.md "when the Grunt Birthday Party skull fires"):
a HEAD-node kill whose next effect sits on a dead `grunt` reaches +0x80444, the start of the
confetti code. This patch adds a CLASSIC effect there, on the dead Grunt:

    +0x80444  mov [rsp+0x68],r15 ; xor r9d,r9d   ->  call C1 ; nop x3
    C1 +0x1397EFB  mov [rsp+0x70],r15 (replayed) ; sub rsp,0x28 ; lea rdx,[NAME] ; jmp C2
    C2 +0x139865B  mov ecx,'effe' ; call tag_loaded +0xA9B35C ; mov ecx,eax ;
                   mov edx,r13d (the grunt) ; jmp C3
    C3 +0x139A04B  cmp ecx,-1 ; je +5 ; call effect_new_on_object +0xBA1078 ;
                   add rsp,0x28 ; xor r9d,r9d (replayed) ; ret
    NAME +0x1B74520  the effect's tag path, in the .rdata slack (VirtualSize ends at
                   +0x1B7451A, raw data at +0x1B74600; zero in the stock file)

(rva at image base 0x180000000; MCC halo1.dll of 2026-06-22.) C1-C3 are 21-byte int3 runs
after a `ret`, outside every .pdata range and relocation and unreferenced (checked
2026-10-11; the supercombine count uses +0x139561B / +0x139576B / +0x1397BAB). +0xBA1078 is
the engine's own effect-on-object call (unit death uses it); tag_loaded returns -1 for a
path the level does not hold, and then nothing is spawned. The Anniversary confetti still
runs as before. The new effect re-enters MCC's effect hook, which is harmless: the head value
is already reset, so the skull code does not run again.

Effects, chosen PER LEVEL by the dll (caves E1-E5): `effects\grunt birthday party` when the
loaded map holds it (a rebuilt map's own confetti), else the fallback slots. Those are EMPTY
by default (user, 2026-10-11): a vanilla map plays nothing. No stock effect worked well. The
needler's `needle detonate` shows a tiny burst; the plasma rifle's `charged bolt sparks` and
`impact c shield` show nothing on a dead Grunt. `--effect "preferred;fallback1;fallback2"`
fills them (64-byte slots in the .rdata slack at +0x1B74520 / +0x1B74560 / +0x1B745A0).

Same LIVE / FILE handling as h1_supercombine_count.py (verified sites, caves first, rename
swap while MCC runs, .prepatch.bak). In co-op BOTH machines need it.

    python sprint_toolkit/h1_birthday_party.py --show
    python sprint_toolkit/h1_birthday_party.py --on [--effect "<effe path>"]   # live + file
    python sprint_toolkit/h1_birthday_party.py --on --live
    python sprint_toolkit/h1_birthday_party.py --off
"""
import argparse
import os
import shutil
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import death_penalty as dp  # noqa: E402
from h1_melee_blocks_fire import _live  # noqa: E402
from h1_overheat_unzoom import DLL, _classify, _cleanup_inuse  # noqa: E402

H = bytes.fromhex
NAME = 'Grunt Birthday Party in classic graphics'
# Three name slots, ';'-separated: the PREFERRED effect (a rebuilt map's own confetti tag),
# else BOTH fallbacks (in every stock campaign map, no damage parts): the needler's pink
# needle burst + pop, and the plasma rifle's green overcharge sparks. The choice is made per
# LEVEL by the dll (tag_loaded), so rebuilt and vanilla maps can be mixed freely.
CONFETTI = r'effects\grunt birthday party'
# User 2026-10-11: REBUILT MAPS ONLY. No stock effect looked right (the needle burst is tiny; the
# plasma rifle's charged bolt sparks and impact c shield showed nothing on a dead Grunt), so the
# fallback slots stay empty and a vanilla map plays nothing. The slots still work if wanted.
DEFAULT_EFFECT = CONFETTI

SITE = 0x80444
C1, C2, C3 = 0x1397EFB, 0x139865B, 0x139A04B
NAME_RVA = 0x1B74520
NAME_MAX = 0xC0                       # bytes reserved (to +0x1B745E0; slack ends +0x1B74600)
SLOT = 0x40                           # three 64-byte name slots: preferred, fallback 1, 2
FB1_RVA, FB2_RVA = NAME_RVA + SLOT, NAME_RVA + 2 * SLOT
E1, E2, E3, E4, E5 = 0x1394AEE, 0x1395B0E, 0x139537C, 0x1396E0D, 0x1396A2C
TAG_LOADED = 0xA9B35C
EFFECT_ON_OBJECT = 0xBA1078
OBJECT_GET = 0xB389A4                 # (object, type mask) -> &object.tag (or 0)
# CLASSIC graphics: MCC's object-record lookup ("id%x", +0x2B3140) finds nothing, so its code
# leaves at +0x803E2 before the name test and before +0x80444 (measured 2026-10-11 with the
# probe: value 2 reached the test, the lookup returned 0). This second route hooks the lookup
# result: lookup failed -> the effect's object is the Grunt biped -> the effect.
SITE2 = 0x803DC                       # mov r14,rax ; test rax,rax   (then je +0x805DB)
KA, KB, KC, KD, KE, KF = 0x1391621, 0x1393D00, 0x1394B8F, 0x13978BF, 0x139689C, 0x1394990
GRUNT_RVA = 0x1B745E0                 # r'characters\grunt\grunt' in the .rdata slack
GRUNT = b'characters\\grunt\\grunt\x00'
DONE = C3 + 10                        # add rsp,0x28 ; xor r9d,r9d (ZF=1: je taken) ; ret
SECTIONS = [(0x1000, 0x174F200, 0xC00),      # .text  (rva start, raw size, rva - file offset)
            (0x1751000, 0x423600, 0x1A00)]   # .rdata


def _rel(next_ip, target):
    return struct.pack('<i', target - next_ip)


CODE1 = (H('4c897c2470') + H('4883ec28') + H('488d15') + _rel(C1 + 16, NAME_RVA)
         + H('e9') + _rel(C1 + 21, E1))
CODE2 = (H('b965666665') + H('e8') + _rel(C2 + 10, TAG_LOADED) + H('89c1') + H('4489ea')
         + H('e9') + _rel(C2 + 20, C3))
CODE3 = (H('83f9ff') + H('7405') + H('e8') + _rel(C3 + 10, EFFECT_ON_OBJECT)
         + H('4883c428') + H('4533c9') + H('c3'))
assert len(CODE1) <= 21 and len(CODE2) <= 21 and len(CODE3) <= 21
CODE_KA = (H('4c8bf0') + H('4885c0') + H('7401') + H('c3')     # registry hit: stock path
           + H('4883ec28') + H('4489e9') + H('e9') + _rel(KA + 21, KB))
CODE_KB = H('83caff') + H('e8') + _rel(KB + 8, OBJECT_GET) + H('4885c0') + H('e9') + _rel(KB + 16, KC)
CODE_KC = (H('0f84') + _rel(KC + 6, DONE) + H('8b00') + H('89442420')
           + H('e9') + _rel(KC + 17, KD))
CODE_KD = (H('488d15') + _rel(KD + 7, GRUNT_RVA) + H('b964706962')   # mov ecx,'bipd'
           + H('e9') + _rel(KD + 17, KE))
CODE_KE = (H('e8') + _rel(KE + 5, TAG_LOADED) + H('3b442420') + H('0f85') + _rel(KE + 15, DONE)
           + H('e9') + _rel(KE + 20, KF))
CODE_KF = H('488d15') + _rel(KF + 7, NAME_RVA) + H('e9') + _rel(KF + 12, E1)
# Both routes arrive at E1 with rdx = the preferred name, the 0x28 frame and r13d = the grunt:
#   E1  mov ecx,'effe' ; call tag_loaded ; cmp eax,-1 ; jmp E2
#   E2  jne C2+10 (found: mov ecx,eax ; mov edx,r13d ; C3 spawns it, done) ;
#       lea rdx,[fallback 1] ; jmp E3
#   E3  mov ecx,'effe' ; call tag_loaded ; mov ecx,eax ; mov edx,r13d ; jmp E4
#   E4  cmp ecx,-1 ; je +5 ; call effect_new_on_object ; jmp E5
#   E5  lea rdx,[fallback 2] ; jmp C2 (looked up and spawned by C2/C3, done)
CODE_E1 = (H('b965666665') + H('e8') + _rel(E1 + 10, TAG_LOADED) + H('83f8ff')
           + H('e9') + _rel(E1 + 18, E2))
CODE_E2 = (H('0f85') + _rel(E2 + 6, C2 + 10) + H('488d15') + _rel(E2 + 13, FB1_RVA)
           + H('e9') + _rel(E2 + 18, E3))
CODE_E3 = (H('b965666665') + H('e8') + _rel(E3 + 10, TAG_LOADED) + H('89c1') + H('4489ea')
           + H('e9') + _rel(E3 + 20, E4))
CODE_E4 = (H('83f9ff') + H('7405') + H('e8') + _rel(E4 + 10, EFFECT_ON_OBJECT)
           + H('e9') + _rel(E4 + 15, E5))
CODE_E5 = H('488d15') + _rel(E5 + 7, FB2_RVA) + H('e9') + _rel(E5 + 12, C2)
for _c, _room in ((CODE_KA, 21), (CODE_KB, 16), (CODE_KC, 17), (CODE_KD, 17), (CODE_KE, 20),
                  (CODE_KF, 16), (CODE_E1, 18), (CODE_E2, 18), (CODE_E3, 20), (CODE_E4, 19),
                  (CODE_E5, 20)):
    assert len(_c) <= _room

# (rva, context before, stock, patched, context after) -- in "on" order: caves first
SITES = [
    (C1, H('5ec3'), b'\xcc' * len(CODE1), CODE1, b''),
    (C2, H('5dc3'), b'\xcc' * len(CODE2), CODE2, b''),
    (C3, H('5bc3'), b'\xcc' * len(CODE3), CODE3, b''),
    (KA, H('5dc3'), b'\xcc' * len(CODE_KA), CODE_KA, b''),
    (KB, H('28c3'), b'\xcc' * len(CODE_KB), CODE_KB, b''),
    (KC, H('5fc3'), b'\xcc' * len(CODE_KC), CODE_KC, b''),
    (KD, H('5fc3'), b'\xcc' * len(CODE_KD), CODE_KD, b''),
    (KE, H('5bc3'), b'\xcc' * len(CODE_KE), CODE_KE, b''),
    (KF, H('f8c3'), b'\xcc' * len(CODE_KF), CODE_KF, b''),
    (E1, H('5bc3'), b'\xcc' * len(CODE_E1), CODE_E1, b''),
    (E2, H('5ec3'), b'\xcc' * len(CODE_E2), CODE_E2, b''),
    (E3, H('c0c3'), b'\xcc' * len(CODE_E3), CODE_E3, b''),
    (E4, H('5fc3'), b'\xcc' * len(CODE_E4), CODE_E4, b''),
    (E5, H('ffc3'), b'\xcc' * len(CODE_E5), CODE_E5, b''),
    (GRUNT_RVA, b'', b'\x00' * len(GRUNT), GRUNT, b''),
    (SITE, H('3bca7ced'), H('4c897c24684533c9'), H('e8') + _rel(SITE + 5, C1) + H('909090'),
     H('458d41ff')),
    (SITE2, H('642d2300'), H('4c8bf04885c0'), H('e8') + _rel(SITE2 + 5, KA) + H('90'),
     H('0f84f301')),
]


def _names(effect):
    """'preferred;fallback1;fallback2' -> three normalised paths ('' = slot unused)."""
    parts = [p.strip().lower() for p in (effect or '').split(';')][:3]
    return parts + [''] * (3 - len(parts))


def _name_blob(effect):
    out = b''
    for p in _names(effect):
        raw = p.encode('latin1') + b'\0'
        if len(raw) > SLOT:
            raise ValueError('effect path longer than %d bytes: %s' % (SLOT - 1, p))
        out += raw + b'\0' * (SLOT - len(raw))
    return out


def _offset(rva):
    for start, size, delta in SECTIONS:
        if start <= rva < start + size:
            return rva - delta
    raise ValueError('rva +0x%X outside .text/.rdata' % rva)


def _file_reader(path):
    with open(path, 'rb') as f:
        data = f.read()
    return lambda rva, n: data[_offset(rva):_offset(rva) + n]


def _write_file(path, writes):
    with open(path, 'r+b') as f:
        for rva, blob in writes:
            f.seek(_offset(rva))
            f.write(blob)


def _writes(state, want, effect):
    if want:
        out = [(NAME_RVA, _name_blob(effect))]          # the name before any code reads it
        if state in ('off', 'partial'):
            out += [(r, pt) for r, _p, _st, pt, _po in SITES]
        return out
    out = []
    if state in ('on', 'partial'):
        out += [(r, st) for r, _p, st, _pt, _po in reversed(SITES)]
    return out + [(NAME_RVA, b'\0' * NAME_MAX)]


def _effect_of(read):
    raw = read(NAME_RVA, NAME_MAX) or b''
    names = [raw[i:i + SLOT].split(b'\0')[0].decode('latin1') for i in range(0, NAME_MAX, SLOT)]
    return ';'.join(names).rstrip(';')


def _wanted_names(effect, on):
    return ';'.join(_names(effect)).rstrip(';') if on else ''


# Earlier builds of this patch (one effect name: C1 and KF jumped straight to C2). Read as
# stock, so such a dll classifies 'partial' and the next write upgrades it in place.
LEGACY = {
    C1: CODE1[:-4] + _rel(C1 + 21, C2),
    KF: CODE_KF[:-4] + _rel(KF + 12, C2),
}


def _upgrading(read):
    def r(rva, n):
        b = read(rva, n)
        for at, old in LEGACY.items():
            if b and rva <= at and at + len(old) <= rva + n:
                i = at - rva
                if b[i:i + len(old)] == old:
                    b = b[:i] + b'\xcc' * len(old) + b[i + len(old):]
        return b
    return r


def file_state(path=DLL):
    return (_classify(_upgrading(_file_reader(path)), SITES) if os.path.exists(path)
            else 'missing')


def live_state(h, base):
    return _classify(_upgrading(lambda rva, n: dp.read(h, base + rva, n)), SITES)


def live_set(h, base, want, effect=DEFAULT_EFFECT):
    state = live_state(h, base)
    if state == 'unknown':
        return False, ('the running halo1.dll does not hold the expected bytes -- this MCC '
                       'build differs, refusing to write')
    for rva, blob in _writes(state, want, effect):
        if not want and rva == NAME_RVA and state == 'off':
            continue
        ok, err = dp.write(h, base + rva, blob)
        if not ok:
            return False, '+0x%X: %s' % (rva, err)
    return True, None


def file_set(want, path=DLL, effect=DEFAULT_EFFECT):
    """(ok, message). In place, or the swap by rename while MCC holds the dll."""
    _cleanup_inuse(path)
    state = file_state(path)
    if state == 'missing':
        return False, '%s not found' % path
    if state == 'unknown':
        return False, ('halo1.dll does not hold the expected bytes -- this MCC build '
                       'differs, refusing to write')
    current = _effect_of(_file_reader(path))
    if state == ('on' if want else 'off') and current == _wanted_names(effect, want):
        return True, 'already as wanted'
    writes = _writes(state, want, effect)
    bak = path + '.prepatch.bak'
    if not os.path.exists(bak):
        shutil.copyfile(path, bak)
    try:
        _write_file(path, writes)
        return True, 'written in place'
    except PermissionError:
        pass                                    # loaded by MCC: swap instead
    new = path + '.new'
    shutil.copyfile(path, new)
    _write_file(new, writes)
    if file_state(new) != ('on' if want else 'off'):
        os.remove(new)
        return False, 'the patched copy did not verify'
    held = '%s.inuse-%d' % (path, int(time.time()))
    try:
        os.rename(path, held)
    except OSError as e:
        os.remove(new)
        return False, 'MCC holds halo1.dll and it could not be renamed: %s' % e
    try:
        os.rename(new, path)
    except OSError as e:
        os.rename(held, path)
        return False, 'could not put the patched halo1.dll in place: %s' % e
    return True, 'swapped in while MCC runs (applies at its next start)'


def sync(on, path=DLL, quiet=True, live_only=False, effect=DEFAULT_EFFECT):
    """One call for the GUI (h1_supercombine_count.sync's shape): the patch on (or back to
    stock) in the running MCC AND in halo1.dll on disk. Result rows; never raises."""
    target = 'on' if on else 'off'
    effect = effect or DEFAULT_EFFECT
    row = {'tag': 'halo1.dll', 'effect': NAME}
    out = []

    def add(field, ok, old, msg):
        if quiet and ok and old == target and (msg in (None, 'already as wanted')):
            return
        out.append({**row, 'field': field, 'ok': ok, 'old': old,
                    'new': target if ok else None,
                    'reason': None if ok else msg, **({'note': msg} if ok else {})})

    def live(h, base):
        old = live_state(h, base)
        if (old == target and _effect_of(lambda r, n: dp.read(h, base + r, n))
                == _wanted_names(effect, on)):
            return add('running MCC', True, old, None)
        ok, err = live_set(h, base, on, effect)
        add('running MCC', ok, old if old != target else old + ' (other effect)', err)
    try:
        r = (_live(live) if os.path.normcase(os.path.abspath(path)) == os.path.normcase(DLL)
             else None)
        if isinstance(r, tuple):
            add('running MCC', False, None, r[1])
    except Exception as e:                      # never fatal to a map patch
        add('running MCC', False, None, str(e))
    if not live_only:
        try:
            old = file_state(path)
            ok, msg = file_set(on, path, effect)
            add('halo1.dll file', ok, old, msg)
        except Exception as e:
            add('halo1.dll file', False, None, str(e))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--on', action='store_true')
    g.add_argument('--off', action='store_true')
    g.add_argument('--show', action='store_true')
    ap.add_argument('--live', action='store_true', help='the running MCC only')
    ap.add_argument('--effect', default=DEFAULT_EFFECT)
    ap.add_argument('--dll', default=DLL)
    a = ap.parse_args(argv)
    if a.show:
        print('file: %s  effect %r' % (file_state(a.dll), _effect_of(_file_reader(a.dll))
                                       if os.path.exists(a.dll) else ''))
        r = _live(lambda h, base: (live_state(h, base),
                                   _effect_of(lambda rv, n: dp.read(h, base + rv, n))))
        print('running MCC: %s' % ((r,) if r is not None else 'not running'))
        return
    rows = sync(a.on, a.dll, quiet=False, live_only=a.live, effect=a.effect)
    for r in rows:
        print('%-16s %s -> %s  %s' % (r['field'], r.get('old'), r.get('new'),
                                      r.get('reason') or r.get('note') or ''))


if __name__ == '__main__':
    main()
