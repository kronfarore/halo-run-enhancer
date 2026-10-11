r"""Halo 1: LIVE probe for the Grunt Birthday Party skull (diagnostic only, never the file).

Why: the Needle Rifle port's needle kills Grunts with headshots but Birthday Party never
fires; the pistol's does. halo1.dll's condition (PORTING.md "Grunt Birthday Party"):
  * +0xBA0CCA  the killing damage stores the hit collision NODE's body-part word
               (coll node +0x32; 2 = head/neck) in a global (+0x1B7BA7C);
  * +0x7FB9C   MCC's effect hook (every effect created goes through it) reads that global
               and RESETS it to -1; only if it read 2, the effect's object is a 'grunt'
               and flavour 11 (grunt_birthday_party) is on does it spawn sfx_konfetti +
               skull_laugh (+0x8039E..).
So the confetti needs the FIRST effect created after the kill to sit on the dead Grunt.
On paper the needle and the bullet take the same path; this probe records what happens.

It hooks five sites with jumps to a cave allocated next to halo1.dll and logs, in order:
  kind 1 KILL    body-part value written, killed object, causer        (+0xBA0CCA)
  kind 2 EFFECT  value the effect hook consumed, effect object, effect name (+0x7FB9C)
  kind 3 IMPACT  projectile impact damage: node, hit object, projectile   (+0xBC7ABF)
  kind 4 GBP?    the skull is on and the hook tests the value               (+0x803B0)
  kind 5 GBP!    the object was a grunt -> confetti is being created       (+0x80444)
Nothing is changed in behaviour (the hooked instructions are replayed in the cave).

    python sprint_toolkit/h1_gbp_probe.py --on      # install in the running MCC (a level loaded)
    python sprint_toolkit/h1_gbp_probe.py --dump    # print the log (since --on / --clear)
    python sprint_toolkit/h1_gbp_probe.py --clear   # empty the log
    python sprint_toolkit/h1_gbp_probe.py --off     # restore the five sites
    python sprint_toolkit/h1_gbp_probe.py --table ["impact grunt"]   # read-only, no hooks
The cave stays allocated after --off (harmless, freed when MCC exits). Results are also
appended to sprint_toolkit/reports/gbp_probe.jsonl (measured values + condition).
"""
import argparse
import ctypes
import json
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import death_penalty as dp  # noqa: E402

GLOBAL = 0x1B7BA7C                     # the body-part word of the last killing damage
TAG_ARRAY_PTR = 0x1C34FB0              # (h1_supercombine_count) tag array qword
VBASE_PTR, DBASE_PTR = 0x2EA3410, 0x2D9CE10
OBJ_HEADERS_PTR = 0x1C42248            # object data array (as at +0xBC7916)
OBJ_MEMORY_PTR = 0x2D9CDF8             # object memory base (as at +0xBC78F0)
FLAVOR_BYTE_GBP = 0x1C421C3            # debug_ice_cream_flavor_status_grunt_birthday_party
EFFECT_TABLE = 0x2B04F68               # qword entries (16 B: key str, value str), +8 count

SITES = {   # rva: (stock bytes, back rva)
    'kill':   (0xBA0CCA, bytes.fromhex('8905acadfd00'), 0xBA0CD0),
    'effect': (0x07FB9C, bytes.fromhex('8b05dabeaf01'), 0x07FBA2),
    'impact': (0xBC7ABF, bytes.fromhex('440fb74f3c488d4724'), 0xBC7AC8),
    'gbp_test': (0x0803B0, bytes.fromhex('837d8c020f8521020000'), 0x0803BA),
    'gbp_pass': (0x080444, bytes.fromhex('4c897c24684533c9'), 0x08044C),
}
GBP_SKIP = 0x0805DB                    # the jne target of the replayed test
CAVE_SIZE = 0x10000
LOG_OFF = 0x2000                       # log: dword count, then 32-byte entries
LOG_N = 0x7FFF + 1
LOG_SIZE = 0x100 + LOG_N * 32
REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports', 'gbp_probe.jsonl')
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports', 'gbp_probe.state.json')
KINDS = {1: 'KILL', 2: 'EFFECT', 3: 'IMPACT', 4: 'GBP?', 5: 'GBP!'}

k32 = dp.k32
k32.VirtualAllocEx.restype = ctypes.c_void_p
k32.VirtualAllocEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                               ctypes.c_ulong, ctypes.c_ulong]
MEM_COMMIT_RESERVE = 0x3000


def _rel32(src_next, dst):
    d = dst - src_next
    if not -2**31 <= d < 2**31:
        raise ValueError('cave out of rel32 range')
    return struct.pack('<i', d)


def _st32(reg, disp):          # mov [r10+disp8], reg32
    return bytes([0x41 | (4 if reg >= 8 else 0), 0x89, 0x40 | ((reg & 7) << 3) | 2, disp])


def _st64(reg, disp):          # mov [r10+disp8], reg64
    return bytes([0x49 | (4 if reg >= 8 else 0), 0x89, 0x40 | ((reg & 7) << 3) | 2, disp])


def _prologue(log, kind):
    return (b'\x9c\x41\x52\x41\x53'                       # pushfq; push r10; push r11
            + b'\x49\xba' + struct.pack('<Q', log)        # mov r10, log
            + b'\x41\xbb\x01\x00\x00\x00'                 # mov r11d, 1
            + b'\xf0\x45\x0f\xc1\x1a'                     # lock xadd [r10], r11d
            + b'\x41\x81\xe3' + struct.pack('<I', LOG_N - 1)  # and r11d, N-1
            + b'\x49\xc1\xe3\x05'                         # shl r11, 5
            + b'\x4f\x8d\x94\x1a\x00\x01\x00\x00'         # lea r10, [r10+r11+0x100]
            + b'\x41\xc7\x02' + struct.pack('<I', kind))  # mov dword [r10], kind


EPILOGUE = b'\x41\x5b\x41\x5a\x9d'                        # pop r11; pop r10; popfq
RAX, RDX, RDI, R8, R12, R13, R14, R11 = 0, 2, 7, 8, 12, 13, 14, 11


def _caves(base, cave):
    """{site: (cave address, code)} -- every cave ends in a jmp back to its site."""
    log = cave + LOG_OFF
    g = base + GLOBAL
    out, at = {}, cave

    def put(name, body, tail):
        nonlocal at
        code = bytearray(body)
        for kind, arg in tail:
            if kind == 'jmp':
                code += b'\xe9' + _rel32(at + len(code) + 5, arg)
            elif kind == 'jne':
                code += b'\x0f\x85' + _rel32(at + len(code) + 6, arg)
        out[name] = (at, bytes(code))
        at += (len(code) + 0x3F) & ~0x3F

    put('kill', b'\xa3' + struct.pack('<Q', g)               # mov [G], eax (the stock store)
        + _prologue(log, 1) + _st32(RAX, 4) + _st32(R14, 8) + _st32(R12, 0xC)
        + _st64(RDI, 0x10) + EPILOGUE, [('jmp', base + SITES['kill'][2])])
    put('effect', b'\xa1' + struct.pack('<Q', g)             # mov eax, [G] (the stock load)
        + _prologue(log, 2) + _st32(RAX, 4) + _st32(RDX, 8) + _st32(R8, 0xC)
        + _st64(R13, 0x10) + EPILOGUE, [('jmp', base + SITES['effect'][2])])
    put('impact', _prologue(log, 3)
        + b'\x44\x0f\xb7\x5f\x3e' + _st32(R11, 4)            # node  = word [rdi+0x3e]
        + b'\x44\x8b\x5f\x38' + _st32(R11, 8)                # hit object = [rdi+0x38]
        + _st32(R12, 0xC)                                    # the projectile
        + b'\x4c\x8b\x5f\x3c' + _st64(R11, 0x10)             # raw words +0x3c..+0x43
        + EPILOGUE + SITES['impact'][1], [('jmp', base + SITES['impact'][2])])
    put('gbp_test', _prologue(log, 4)
        + b'\x44\x8b\x5d\x8c' + _st32(R11, 4)                # value read = [rbp-0x74]
        + _st32(R13, 8) + EPILOGUE + b'\x83\x7d\x8c\x02',    # replay cmp [rbp-0x74], 2
        [('jne', base + GBP_SKIP), ('jmp', base + SITES['gbp_test'][2])])
    put('gbp_pass', _prologue(log, 5) + _st32(R13, 8) + EPILOGUE + SITES['gbp_pass'][1],
        [('jmp', base + SITES['gbp_pass'][2])])
    return out


def _alloc_near(h, base):
    for step in range(1, 0x400):
        for want in (base - step * 0x100000, base + 0x4000000 + step * 0x100000):
            p = k32.VirtualAllocEx(h, ctypes.c_void_p(want), CAVE_SIZE + LOG_SIZE,
                                   MEM_COMMIT_RESERVE, dp.PAGE_EXECUTE_READWRITE)
            if p:
                return p
    return None


def _open():
    pid = dp.find_pid()
    if not pid:
        raise SystemExit('MCC is not running.')
    h = k32.OpenProcess(dp.ACCESS, False, pid)
    if not h:
        raise SystemExit('OpenProcess failed -- run elevated.')
    base = dp.module_base(pid, b'halo1.dll')
    if not base:
        raise SystemExit('halo1.dll is not loaded (start a Halo 1 level first).')
    return pid, h, base


def _state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def install():
    pid, h, base = _open()
    st = _state()
    for name, (rva, stock, _back) in SITES.items():
        cur = dp.read(h, base + rva, len(stock))
        if cur != stock:
            if st.get('pid') == pid and cur and cur[0] == 0xE9:
                raise SystemExit('already installed (use --dump / --off).')
            raise SystemExit('%s: unexpected bytes at +%X (%s) -- different halo1.dll build?'
                             % (name, rva, cur.hex() if cur else None))
    cave = _alloc_near(h, base)
    if not cave:
        raise SystemExit('could not allocate a cave within 2 GB of halo1.dll')
    caves = _caves(base, cave)
    for name, (at, code) in caves.items():
        ok, err = dp.write(h, at, code)
        if not ok:
            raise SystemExit(err)
    for name, (at, _code) in caves.items():         # sites last, caves already in place
        rva, stock, _back = SITES[name]
        patch = b'\xe9' + _rel32(base + rva + 5, at)
        ok, err = dp.write(h, base + rva, patch + b'\x90' * (len(stock) - 5))
        if not ok:
            raise SystemExit(err)
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, 'w') as f:
        json.dump({'pid': pid, 'cave': cave, 'base': base}, f)
    gbp = dp.read(h, base + FLAVOR_BYTE_GBP, 1)
    print('probe ON (cave %#x). Birthday Party skull flag in this level: %s'
          % (cave, 'ON' if gbp and gbp[0] else 'OFF -- turn the skull on, or kinds 4/5 never log'))


def uninstall():
    pid, h, base = _open()
    for name, (rva, stock, _back) in SITES.items():
        cur = dp.read(h, base + rva, len(stock))
        if cur == stock:
            continue
        ok, err = dp.write(h, base + rva, stock)
        print('%s: %s' % (name, 'restored' if ok else err))
    print('probe OFF')


def _q(h, a):
    b = dp.read(h, a, 8)
    return struct.unpack('<Q', b)[0] if b and len(b) == 8 else 0


def _tag_name(h, base, tid):
    arr, vb, db = (_q(h, base + o) for o in (TAG_ARRAY_PTR, VBASE_PTR, DBASE_PTR))
    e = dp.read(h, arr + 32 * (tid & 0xFFFF), 32) if arr else None
    if not e or len(e) < 32:
        return None
    cls = e[:4][::-1].decode('latin1')
    name_p = struct.unpack_from('<i', e, 0x10)[0]
    raw = dp.read(h, name_p - vb + db, 200) or b''
    return '%s %s' % (cls, raw.split(b'\0')[0].decode('latin1'))


def _object_tag(h, base, obj):
    if obj in (0xFFFFFFFF, -1):
        return '-'
    try:
        arr = _q(h, base + OBJ_HEADERS_PTR)
        first = struct.unpack('<i', dp.read(h, arr + 0x34, 4))[0]
        off = struct.unpack('<i', dp.read(h, arr + first + (obj & 0xFFFF) * 12 + 8, 4))[0]
        mem = _q(h, base + OBJ_MEMORY_PTR)
        tid = struct.unpack('<I', dp.read(h, mem + 0x34 + off, 4))[0]
        return _tag_name(h, base, tid) or '?'
    except (TypeError, struct.error):
        return '?'


def _cstr(h, p):
    raw = dp.read(h, p, 160) if p else None
    return raw.split(b'\0')[0].decode('latin1') if raw else '?'


def dump(clear=False):
    pid, h, base = _open()
    st = _state()
    if st.get('pid') != pid:
        raise SystemExit('no probe in this MCC session (run --on first).')
    log = st['cave'] + LOG_OFF
    if clear:
        dp.write(h, log, b'\0' * 4)
        print('log cleared')
        return
    n = struct.unpack('<I', dp.read(h, log, 4))[0]
    first = max(0, n - LOG_N)
    rows, names = [], {}
    for i in range(first, n):
        e = dp.read(h, log + 0x100 + (i % LOG_N) * 32, 32)
        kind, val, obj, extra, ptr = struct.unpack('<IiIIQ', e[:24])
        rows.append((i, kind, val, obj, extra, ptr))
    # print every KILL with its impact before and the effects right after it
    out = []
    for j, (i, kind, val, obj, extra, ptr) in enumerate(rows):
        if kind not in (1, 3, 4, 5):
            continue
        if kind == 3:
            node = val & 0xFFFF
            line = 'IMPACT  node %d  hit %s  by %s  raw %016x' % (
                node if node < 0x8000 else node - 0x10000, _object_tag(h, base, obj),
                _object_tag(h, base, extra), ptr)
        elif kind == 1:
            line = 'KILL    body part %d  object %s  model %s' % (
                val, _object_tag(h, base, obj), _cstr(h, ptr))
        elif kind == 4:
            line = 'GBP?    value %d  effect object %s' % (val, _object_tag(h, base, obj))
        else:
            line = 'GBP!    confetti on %s' % _object_tag(h, base, obj)
        out.append(('#%d ' % i) + line)
        if kind == 1:
            for k in rows[j + 1:]:
                if k[1] == 2:
                    eff = _cstr(h, k[5])
                    out.append('#%d   -> next EFFECT consumed %d  on %s  effect %s'
                               % (k[0], k[2], _object_tag(h, base, k[3]), eff))
                    rec = {'when': time.strftime('%Y-%m-%d %H:%M:%S'), 'kill_value': val,
                           'killed': _object_tag(h, base, obj), 'consumed': k[2],
                           'effect_object': _object_tag(h, base, k[3]), 'effect': eff,
                           'condition': 'h1_gbp_probe live, Birthday Party test'}
                    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
                    with open(REPORT, 'a') as f:
                        f.write(json.dumps(rec) + '\n')
                    break
    print('%d log entries (%d effects)' % (n, sum(1 for r in rows if r[1] == 2)))
    print('\n'.join(out) if out else 'no kills / impacts logged yet')


def _mstr(h, p):
    """An MCC refcounted string (+4 length, chars at +0xC)."""
    hdr = dp.read(h, p, 12) if p else None
    if not hdr or len(hdr) < 12:
        return None
    n = struct.unpack_from('<i', hdr, 4)[0]
    return (dp.read(h, p + 12, max(0, min(n, 300))) or b'').decode('latin1')


def table(sub):
    """The effect hook's name table (hcex_effect_names.ps, loaded with the level): effect
    tag path -> Anniversary effect name. An EMPTY name makes the hook return before the
    Birthday Party test (+0x7FF2A), after it has already reset the head value."""
    pid, h, base = _open()
    tab = _q(h, base + EFFECT_TABLE)
    n = struct.unpack('<i', dp.read(h, base + EFFECT_TABLE + 8, 4))[0]
    if not tab or n <= 0:
        raise SystemExit('effect name table is empty (load a Halo 1 level first).')
    shown = 0
    for i in range(n):
        k, v = struct.unpack('<QQ', dp.read(h, tab + 16 * i, 16))
        key, val = _mstr(h, k), _mstr(h, v)
        if sub.lower() in (key or '').lower():
            print('%-60s -> %r' % (key, val))
            shown += 1
    print('%d of %d entries match %r (paths NOT in the table get a built name, never empty)'
          % (shown, n, sub))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--on', action='store_true')
    g.add_argument('--off', action='store_true')
    g.add_argument('--dump', action='store_true')
    g.add_argument('--clear', action='store_true')
    g.add_argument('--table', metavar='SUBSTRING', nargs='?', const='impact grunt')
    a = ap.parse_args(argv)
    if a.on:
        install()
    elif a.off:
        uninstall()
    elif a.table is not None:
        table(a.table)
    else:
        dump(clear=a.clear)


if __name__ == '__main__':
    main()
