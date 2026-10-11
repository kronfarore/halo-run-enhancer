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

Effect: `weapons\needler\effects\needle detonate` by default (in all ten campaign maps, no
damage parts: needle debris, flash, flare, smoke + the needle pop sound). `--effect <path>`
names another; a dedicated confetti effect only needs its tag in the maps.

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
DEFAULT_EFFECT = r'weapons\needler\effects\needle detonate'

SITE = 0x80444
C1, C2, C3 = 0x1397EFB, 0x139865B, 0x139A04B
NAME_RVA = 0x1B74520
NAME_MAX = 0xC0                       # bytes reserved (to +0x1B745E0; slack ends +0x1B74600)
TAG_LOADED = 0xA9B35C
EFFECT_ON_OBJECT = 0xBA1078
SECTIONS = [(0x1000, 0x174F200, 0xC00),      # .text  (rva start, raw size, rva - file offset)
            (0x1751000, 0x423600, 0x1A00)]   # .rdata


def _rel(next_ip, target):
    return struct.pack('<i', target - next_ip)


CODE1 = (H('4c897c2470') + H('4883ec28') + H('488d15') + _rel(C1 + 16, NAME_RVA)
         + H('e9') + _rel(C1 + 21, C2))
CODE2 = (H('b965666665') + H('e8') + _rel(C2 + 10, TAG_LOADED) + H('89c1') + H('4489ea')
         + H('e9') + _rel(C2 + 20, C3))
CODE3 = (H('83f9ff') + H('7405') + H('e8') + _rel(C3 + 10, EFFECT_ON_OBJECT)
         + H('4883c428') + H('4533c9') + H('c3'))
assert len(CODE1) <= 21 and len(CODE2) <= 21 and len(CODE3) <= 21

# (rva, context before, stock, patched, context after) -- in "on" order: caves first
SITES = [
    (C1, H('5ec3'), b'\xcc' * len(CODE1), CODE1, b''),
    (C2, H('5dc3'), b'\xcc' * len(CODE2), CODE2, b''),
    (C3, H('5bc3'), b'\xcc' * len(CODE3), CODE3, b''),
    (SITE, H('3bca7ced'), H('4c897c24684533c9'), H('e8') + _rel(SITE + 5, C1) + H('909090'),
     H('458d41ff')),
]


def _name_blob(effect):
    raw = effect.strip().lower().encode('latin1') + b'\0'
    if len(raw) > NAME_MAX:
        raise ValueError('effect path longer than %d bytes' % (NAME_MAX - 1))
    return raw + b'\0' * (NAME_MAX - len(raw))


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
    return raw.split(b'\0')[0].decode('latin1')


def file_state(path=DLL):
    return _classify(_file_reader(path), SITES) if os.path.exists(path) else 'missing'


def live_state(h, base):
    return _classify(lambda rva, n: dp.read(h, base + rva, n), SITES)


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
    if (state == ('on' if want else 'off')
            and current == (effect.strip().lower() if want else '')):
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
                == (effect.strip().lower() if on else '')):
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
