r"""Read the finished level's SCORE and TIME out of the running MCC (the post-game screen).

WHY
---
The enhancer's Next level box records each level's summary-screen score and time for
the par-time analysis. Typing them is the only step of a run that still needs the
player to copy numbers off the screen. No file holds them -- `%USERPROFILE%\AppData\
LocalLow\MCC` has nothing, and the online-stats keys (`BestMissionTimeMS.DifficultyId.
%u.MapId.%u.Coop.%u`) are only names the wrapper builds to query the service -- so this
reads them where the post-game report itself gets them: MCC's campaign metagame object.

WHERE THEY LIVE (MCC-Win64-Shipping.exe, desk work 2026-10-18)
--------------------------------------------------------------
One heap object behind a static pointer is the campaign metagame. Every site that
scores reads it the same way -- the player-death site (+437EB2) loads it into rbx,
`inc [rbx+0x148]`, and calls ApplyPenalty (+44B764), which adds to a float at +0x30 of
an entry in a list at +0x98 (see death_penalty.py). The function that fills the
carnage-report record from it (+331E2C) spells the whole layout out:

    +331ECF  mov rbp, [rip+G]                 ; G = the metagame object pointer
             lea rcx, [rbp+0x98]              ; score list: sentinel, first = [+0x10],
             ...walk: entry+0x10 = next,      ;   entry+0x00 == 0 picks the entry
             mov eax, [entry+0x30] -> rec+0   ; PENALTIES (float; ApplyPenalty adds here)
             mov eax, [rbp+0x138]  -> rec+8   ; KILL POINTS (float; a copy of the
                                              ;   +0x60 list's entry, +4380AC)
             mov eax, [rbp+0x144]  -> rec+0x8C
             mov eax, [rbp+0x148]  -> rec+4   ; deaths
             call +44B8C8          -> rec+0xC ; ELAPSED TIME (float)

and +44B8C8 is

    cmp byte [rip+F], 0 ; xorps xmm0,xmm0 ; je done
    mov rax, [rip+P] ; test rax,rax ; je done ; cmp dword [rax+0x64], 1 ; ja done
    movss xmm0, [rip+SEG]                     ; the segment still running
  done:
    addss xmm0, [rcx+0x1B8]                   ; + the banked time
    ret

The same sum is what +366894 converts to an integer for the mission-time stat.

WHAT THE SUMMARY SCREEN SHOWS (calibration boot 2026-10-19, reports/pgcr_live.jsonl)
-----------------------------------------------------------------------------------
Screen: score 21917, time 0:05:55, time multiplier 3.00. The object read
    +0x138 kill points 7439    +0x158 time multiplier 3.0    +0x98 entry -400
    elapsed 355.90 (SECONDS; +0x13C holds the 355.87 snapshot)
and 7439 * 3 - 400 = 21917: the multiplier scales the kill points only, penalties
(here two reverts at -50 x Legendary 4) are added after it. The process also holds the
score-over-time graph -- a vector of 0x14-byte records {?, index, kills+penalties,
score, time} whose last record read (21917, 355.90) -- which confirms the formula but
has no cheap path from a static yet, so the score is computed from the object.

HOW THIS FINDS IT
-----------------
No RVA is trusted: both code sequences above are located by byte signature in the
running image (wildcards on every displacement), and the globals and field offsets are
decoded out of the matched instructions. An MCC update that moves code keeps working as
long as these two little sequences survive; one that changes them is refused with a
reason, never misread. The decoded addresses are cached per pid
(out/pgcr_live_addrs.json), so after the first read a press costs a few hundred bytes.

    python pgcr_live.py                       # read and print (and log)
    python pgcr_live.py --note "a10 Legendary, post-game screen"
    python pgcr_live.py --calibrate --score 25840 --time 0:23:41 --note "..."

`--calibrate` also dumps the object and scans the whole process for the values the
user typed (int / float / double; time as s, ms, 30 / 60 Hz ticks), so the unit of the
time field and the score entry can be confirmed against what the screen shows. Every
reading is appended, with its condition, to reports/pgcr_live.jsonl.

Read-only: it never opens the process for writing.
"""
import argparse
import ctypes
import json
import os
import re
import struct
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import death_penalty as dp                       # pid / module base / read helpers

k32 = dp.k32
ACCESS_READ = dp.PROCESS_QUERY_INFORMATION | dp.PROCESS_VM_READ
CACHE = os.path.join(_HERE, 'out', 'pgcr_live_addrs.json')
LOG = os.path.join(_HERE, 'reports', 'pgcr_live.jsonl')
DUMP_DIR = os.path.join(_HERE, 'out', 'pgcr_live')

# The carnage-report fill (+331ECF): mov rbp,[rip+G] ; lea rcx,[rbp+LIST] ;
# mov rax,[rcx+0x10] ; jmp ; cmp [rax],rbx ; jbe ; mov rax,[rax+0x10] ; ... ;
# mov eax,[rax+SCORE] ; mov [rsi],eax ; mov eax,[rbp+X] ; mov rcx,rbp ;
# mov [rsi+8],eax ; mov eax,[rbp+Y] ; mov [rsi+0x8C],eax ; mov eax,[rbp+DEATHS]
SIG_REPORT = re.compile(
    rb'\x48\x8B\x2D(.{4})\x48\x8D\x8D(.{4})\x48\x8B\x41\x10\xEB.\x48\x39\x18\x76.'
    rb'\x48\x8B\x40\x10\x48\x3B\xC1\x75.\x48\x8B\xC3\x48\x85\xC0\x74.\x8B\x40(.)'
    rb'\x89\x06\x8B\x85(.{4})\x48\x8B\xCD\x89\x46\x08\x8B\x85(.{4})'
    rb'\x89\x86\x8C\x00\x00\x00\x8B\x85(.{4})', re.S)
# The elapsed-time getter (+44B8C8), described in the docstring.
SIG_ELAPSED = re.compile(
    rb'\x80\x3D(.{4})\x00\x0F\x57\xC0\x74\x1A\x48\x8B\x05(.{4})\x48\x85\xC0\x74\x0E'
    rb'\x83\x78\x64\x01\x77\x08\xF3\x0F\x10\x05(.{4})\xF3\x0F\x58\x81(.{4})\xC3', re.S)

# What the time float counts: seconds (calibration boot 2026-10-19: 355.90 -> 0:05:55).
TIME_SCALE = 1.0
TIME_UNIT_NOTE = 'seconds'
# The time multiplier the summary screen shows (read by +36648E / +456DA1). A field
# offset, not a signature: it is checked for a plausible value before it is used.
TIME_MULT_OFF = 0x158


# --- process plumbing ----------------------------------------------------------

def _open(pid):
    return k32.OpenProcess(ACCESS_READ, False, pid)


def _u32(b, o=0):
    return struct.unpack_from('<I', b, o)[0]


def _i32(b, o=0):
    return struct.unpack_from('<i', b, o)[0]


def _u64(b, o=0):
    return struct.unpack_from('<Q', b, o)[0]


def _f32(b, o=0):
    return struct.unpack_from('<f', b, o)[0]


def _text_section(h, base):
    """(rva, size) of .text, from the PE headers in memory."""
    hdr = dp.read(h, base, 0x1000)
    if not hdr or hdr[:2] != b'MZ':
        return None
    pe = _u32(hdr, 0x3C)
    nsec = struct.unpack_from('<H', hdr, pe + 6)[0]
    opt = struct.unpack_from('<H', hdr, pe + 20)[0]
    sec = pe + 24 + opt
    for i in range(nsec):
        s = sec + 40 * i
        if hdr[s:s + 5] == b'.text':
            return _u32(hdr, s + 12), _u32(hdr, s + 8)
    return None


def _read_big(h, addr, size, chunk=4 << 20):
    out = bytearray()
    for off in range(0, size, chunk):
        part = dp.read(h, addr + off, min(chunk, size - off))
        if part is None:
            part = b'\0' * min(chunk, size - off)
        out += part
    return bytes(out)


def locate(h, base):
    """Decode the globals and offsets from the two signatures. (dict, None) or
    (None, reason)."""
    sec = _text_section(h, base)
    if not sec:
        return None, 'could not read the PE headers of the MCC module'
    rva, size = sec
    code = _read_big(h, base + rva, size)
    rep = list(SIG_REPORT.finditer(code))
    ela = list(SIG_ELAPSED.finditer(code))
    if len(rep) != 1 or len(ela) != 1:
        return None, ('signature match counts report=%d elapsed=%d (want 1 / 1) -- this '
                      'MCC build differs, nothing read' % (len(rep), len(ela)))
    m, e = rep[0], ela[0]
    at = rva + m.start()
    g = at + 7 + _i32(m.group(1))                 # mov rbp,[rip+d] is 7 bytes
    ea = rva + e.start()
    flag = ea + 7 + _i32(e.group(1))              # cmp byte [rip+d],0 : 7 bytes
    ptr = ea + 7 + 3 + 2 + 7 + _i32(e.group(2))   # mov rax,[rip+d] ends at +0x13
    seg_end = ea + 0x26
    seg = seg_end + _i32(e.group(3))
    return {
        'g_rva': g, 'list_off': _i32(m.group(2)), 'score_off': m.group(3)[0],
        'x138_off': _i32(m.group(4)), 'x144_off': _i32(m.group(5)),
        'deaths_off': _i32(m.group(6)),
        'flag_rva': flag, 'ptr_rva': ptr, 'seg_rva': seg,
        'banked_off': _i32(e.group(4)),
        'report_rva': at, 'elapsed_rva': ea,
    }, None


def _cached(pid, base):
    try:
        with open(CACHE, encoding='utf-8') as f:
            blob = json.load(f)
    except Exception:
        return None
    if blob.get('pid') == pid and blob.get('base') == base:
        return blob.get('addrs')
    return None


def _save(pid, base, addrs):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, 'w', encoding='utf-8') as f:
        json.dump({'pid': pid, 'base': base, 'addrs': addrs}, f, indent=1)


def _score_entries(h, g, list_off, score_off, limit=16):
    """[(entry address, key qword, score float)] along the score list."""
    head = g + list_off
    blob = dp.read(h, head, 0x18)
    if not blob:
        return []
    cur, out = _u64(blob, 0x10), []
    while cur and cur != head and len(out) < limit:
        e = dp.read(h, cur, 0x40)
        if not e:
            break
        out.append((cur, _u64(e, 0), _f32(e, score_off)))
        cur = _u64(e, 0x10)
    return out


def _elapsed(h, base, g, a):
    """The getter's sum: banked + (the running segment when the game says so)."""
    banked = dp.read(h, g + a['banked_off'], 4)
    if not banked:
        return None, None, None
    banked = _f32(banked)
    seg = 0.0
    flag = dp.read(h, base + a['flag_rva'], 1)
    if flag and flag[0]:
        p = dp.read(h, base + a['ptr_rva'], 8)
        p = _u64(p) if p else 0
        st = dp.read(h, p + 0x64, 4) if p else None
        if st is not None and _u32(st) <= 1:
            s = dp.read(h, base + a['seg_rva'], 4)
            seg = _f32(s) if s else 0.0
    return banked + seg, banked, seg


def fmt_time(seconds):
    s = int(seconds)
    return '%d:%02d:%02d' % (s // 3600, s % 3600 // 60, s % 60)


def read_results(pid=None):
    """The finished level's score and time. Never raises; always a dict with 'ok'.

    ok=True carries score (int), seconds (float), time ('h:mm:ss'), deaths, and the
    raw fields for the log."""
    try:
        pid = pid or dp.find_pid()
        if not pid:
            return {'ok': False, 'reason': 'MCC is not running'}
        base = dp.module_base(pid)
        if not base:
            return {'ok': False, 'reason': 'MCC module not found in pid %d' % pid}
        h = _open(pid)
        if not h:
            return {'ok': False, 'reason': 'OpenProcess failed (%d)'
                    % ctypes.get_last_error()}
        try:
            a = _cached(pid, base)
            cached = a is not None
            if not cached:
                a, err = locate(h, base)
                if err:
                    return {'ok': False, 'reason': err}
                _save(pid, base, a)
            gp = dp.read(h, base + a['g_rva'], 8)
            g = _u64(gp) if gp else 0
            if not g:
                return {'ok': False, 'reason': 'no campaign metagame object (no level '
                        'played since MCC started?)'}
            entries = _score_entries(h, g, a['list_off'], a['score_off'])
            pick = next((e for e in entries if e[1] == 0), None)
            elapsed, banked, seg = _elapsed(h, base, g, a)
            raw = dp.read(h, g + 0x130, 0x90) or b''
            if pick is None or elapsed is None or len(raw) < 0x90:
                return {'ok': False, 'reason': 'metagame object unreadable',
                        'entries': len(entries)}
            deaths = _u32(raw, a['deaths_off'] - 0x130)
            kills = _f32(raw, a['x138_off'] - 0x130)
            mult = _f32(raw, TIME_MULT_OFF - 0x130)
            if not (0.0 < mult <= 100.0):
                return {'ok': False, 'reason': 'time multiplier reads %r -- this MCC '
                        'build differs, nothing filled' % mult}
            penalties = pick[2]
            secs = elapsed * TIME_SCALE
            return {
                'ok': True, 'pid': pid, 'cached': cached,
                'score': int(round(kills * mult + penalties)),
                'kill_points': kills, 'time_multiplier': mult, 'penalties': penalties,
                'seconds': secs, 'time': fmt_time(secs),
                'time_raw': elapsed, 'time_banked': banked, 'time_segment': seg,
                'time_unit': TIME_UNIT_NOTE, 'deaths': deaths,
                'x144': _u32(raw, a['x144_off'] - 0x130),
                'x13c': _f32(raw, 0xC),
                'entries': [{'key': k, 'score': s} for _a, k, s in entries],
                'g': g,
            }
        finally:
            k32.CloseHandle(h)
    except Exception as e:                         # a convenience: never take the GUI down
        return {'ok': False, 'reason': '%s: %s' % (type(e).__name__, e)}


def log(row):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    row = dict(row, at=time.strftime('%Y-%m-%dT%H:%M:%S'))
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(row) + '\n')
    return LOG


# --- calibration -----------------------------------------------------------------

def _parse_time(t):
    parts = [int(p) for p in t.split(':')]
    s = 0
    for p in parts:
        s = s * 60 + p
    return s


def value_scan(h, score, secs):
    """Every private-memory location holding the typed values, by representation.

    The displayed time is whole seconds, so time hits are ranges: [T, T+1) s."""
    import numpy as np
    probes = {}
    if score is not None:
        probes['score_i32'] = ('<i4', score, score)
        probes['score_f32'] = ('<f4', score - 0.5, score + 0.5)
        probes['score_f64'] = ('<f8', score - 0.5, score + 0.5)
    if secs is not None:
        probes['time_s_i32'] = ('<i4', secs, secs)
        probes['time_s_f32'] = ('<f4', secs, secs + 1)
        probes['time_s_f64'] = ('<f8', secs, secs + 1)
        probes['time_ms_i32'] = ('<i4', secs * 1000, secs * 1000 + 999)
        probes['time_ms_i64'] = ('<i8', secs * 1000, secs * 1000 + 999)
        probes['time_ms_f32'] = ('<f4', secs * 1000, secs * 1000 + 1000)
        probes['time_t30_i32'] = ('<i4', secs * 30, secs * 30 + 29)
        probes['time_t60_i32'] = ('<i4', secs * 60, secs * 60 + 59)
    hits = {k: [] for k in probes}
    for rbase, size in _private_regions(h):
        if size > 256 << 20:
            continue
        data = _read_big(h, rbase, size)
        for name, (dt, lo, hi) in probes.items():
            width = np.dtype(dt).itemsize
            n = len(data) // width
            arr = np.frombuffer(data, dtype=dt, count=n)
            idx = np.nonzero((arr >= lo) & (arr <= hi) if lo != hi else arr == lo)[0]
            for i in idx[:2000]:
                hits[name].append((rbase + int(i) * width, arr[i].item()))
    return hits


def _private_regions(h):
    class MBI(ctypes.Structure):
        _fields_ = [('BaseAddress', ctypes.c_ulonglong), ('AllocationBase', ctypes.c_ulonglong),
                    ('AllocationProtect', ctypes.c_ulong), ('a1', ctypes.c_ulong),
                    ('RegionSize', ctypes.c_ulonglong), ('State', ctypes.c_ulong),
                    ('Protect', ctypes.c_ulong), ('Type', ctypes.c_ulong),
                    ('a2', ctypes.c_ulong)]
    mbi, addr = MBI(), 0
    while addr < (1 << 47):
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                                  ctypes.sizeof(mbi)):
            break
        if (mbi.State == 0x1000 and mbi.Protect in (0x02, 0x04, 0x20, 0x40)
                and mbi.Type == 0x20000):
            yield mbi.BaseAddress, mbi.RegionSize
        if mbi.RegionSize == 0:
            break
        addr = mbi.BaseAddress + mbi.RegionSize


def calibrate(score, time_text, note):
    rep = read_results()
    print(json.dumps(rep, indent=1, default=str))
    secs = _parse_time(time_text) if time_text else None
    pid = dp.find_pid()
    if not pid:
        return 1
    h = _open(pid)
    try:
        os.makedirs(DUMP_DIR, exist_ok=True)
        stamp = time.strftime('%Y%m%d_%H%M%S')
        g = rep.get('g')
        inside = {}
        if g:
            blob = dp.read(h, g, 0x900) or b''
            with open(os.path.join(DUMP_DIR, 'metagame_%s.bin' % stamp), 'wb') as f:
                f.write(blob)
        t0 = time.time()
        hits = value_scan(h, score, secs)
        print('value scan %.1fs' % (time.time() - t0))
        for name, lst in hits.items():
            near = [(a, v) for a, v in lst if g and g <= a < g + 0x900]
            inside[name] = ['+0x%X=%r' % (a - g, v) for a, v in near]
            print('%-14s %5d hit(s)%s' % (name, len(lst),
                  ('   in the metagame object: ' + ', '.join(inside[name]))
                  if near else ''))
        with open(os.path.join(DUMP_DIR, 'hits_%s.json' % stamp), 'w') as f:
            json.dump({k: [[a, v] for a, v in lst] for k, lst in hits.items()}, f)
        print('log -> %s' % log({
            'mode': 'calibrate', 'note': note, 'typed_score': score,
            'typed_time': time_text, 'read': {k: v for k, v in rep.items() if k != 'g'},
            'hit_counts': {k: len(v) for k, v in hits.items()},
            'in_object': inside, 'dump_stamp': stamp}))
    finally:
        k32.CloseHandle(h)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--note', default='', help='the condition, for the log')
    ap.add_argument('--calibrate', action='store_true')
    ap.add_argument('--score', type=int, help='(calibrate) the score on screen')
    ap.add_argument('--time', help='(calibrate) the time on screen, h:mm:ss or m:ss')
    a = ap.parse_args(argv)
    if a.calibrate:
        return calibrate(a.score, a.time, a.note)
    rep = read_results()
    for k, v in rep.items():
        print('  %-13s %s' % (k, v))
    print('log -> %s' % log({'mode': 'read', 'note': a.note,
                             'read': {k: v for k, v in rep.items() if k != 'g'}}))
    return 0 if rep.get('ok') else 1


if __name__ == '__main__':
    raise SystemExit(main())
