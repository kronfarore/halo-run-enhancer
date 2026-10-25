r"""Halo 1: dropped weapons/equipment stay longer, and a longer flashlight battery --
halo1.dll VALUE patches (user, 2026-10-24 co-op; dll route chosen). Both default OFF (stock).

No tag field holds either (globals / items have no lifetime; Reach and Halo 4 are the first
with a 'Garbage Collection' block). Found through the script functions garbage_collect_now
(+0xB1A3A4: sets garbage-globals +2) and unit_get_current_flashlight_state (+0xB1B4FC ->
+0xB07A60: unit +0x1D4 bit 16). rva at image base 0x180000000, MCC halo1.dll of 2026-06-22.

DROPPED ITEMS -- there is NO timer in Halo 1, only a count
  An item that comes to rest with no parent becomes 'garbage' (item physics +0xBDC9DC ->
  object_set_garbage +0xB391F0, object flags +0x10 bit 16; campaign only). A dead unit does
  too (+0xB045D7). The object update counts garbage every tick (+0xB3A0E8 -> garbage
  globals *(+0x2D9CDF0) +4, a word). The collector +0xB3C818 runs after every object
  update and deletes garbage the players cannot see (+0xB394F8, the PVS test):
    count >= 50   (+0xB3C8DA cmp word [rbx+4], 0x32)  -> delete down to 30 (+0xB3C986)
    object memory or free object slots low (2 MiB pool; <= 102 free slots) -> delete
                  until >= 204 free slots and >= 0x33333 bytes free -- left stock
    a script's garbage_collect_now (c10, d20, b40)  -- left stock
  Bodies and dropped weapons share the 50. 'drop_limit' moves the 50 (1..127: the cmp is
  an imm8) and the 30 with it (3/5); 0 = no count limit at all (+0xB3C8DF jl -> jmp): only
  the engine's own memory / slot pressure collects, which keeps the game safe.

FLASHLIGHT -- a battery, unit +0x328 (1.0 full), in the unit update
  on:  -= [+0x194EFA4] per tick (+0xAFDD2C), 1/3600 = 120 s at 30 ticks/s, skipped when
       the unit tag has 'Integrated Light Lasts Forever' (unit flags +0x17C bit 24)
  off: += [+0x194EFE0] per tick (+0xAFDDCF), 1/900 = 30 s from empty to full
  It cannot be switched on again below 0.2 (+0xAFDC6B). Both constants are read by that ONE
  instruction each (every rip reference in .text checked), so the float is changed in
  place. 'flashlight_seconds' 0 = never drains.

    python sprint_toolkit/h1_drops_flashlight.py --show
    python sprint_toolkit/h1_drops_flashlight.py --drop-limit 127 --flashlight 360
    python sprint_toolkit/h1_drops_flashlight.py --drop-limit 0          # no count limit
    python sprint_toolkit/h1_drops_flashlight.py --flashlight 0          # never drains
    python sprint_toolkit/h1_drops_flashlight.py --off                   # all stock (--restore)
    python sprint_toolkit/h1_drops_flashlight.py --live ...              # the running MCC only
    python sprint_toolkit/h1_drops_flashlight.py --probe --note "a10, 3 rifles dropped"
"""
import argparse
import json
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import death_penalty as dp  # noqa: E402
import dll_tunables as dt  # noqa: E402
from dll_tunables import H, f32, unf32  # noqa: E402

MODULE = 'halo1.dll'
DLL = dt.find_dll('halo1', MODULE)
TICKS = 30                       # Halo 1 game ticks per second
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports', 'drops_flashlight.jsonl')

GC_TRIGGER = 0xB3C8DE            # imm8 of cmp word [rbx+4], 0x32
GC_LOW = 0xB3C98A                # imm8 of cmp word [rbx+4], 0x1e
GC_JL = 0xB3C8DF                 # jl +0xB3CCF2 (fewer than 50: no collection)
DRAIN = 0x194EFA4                # 1/3600
RECHARGE = 0x194EFE0             # 1/900
GARBAGE_GLOBALS = 0x2D9CDF0      # qword -> +2 script request, +4 garbage count (word)
PLAYER_CONTROL_PTR = 0x2D8FE70   # +0x10 player 1's unit handle (h1_melee_fire_probe)
OBJ_TABLE_PTR = 0x1C42248
OBJ_DATA_PTR = 0x2D9CDF8


def _low(n):
    return n * 3 // 5


def _enc_limit(n):
    n = int(n)
    if n == 0:
        return [H('32'), H('1e'), H('90e90d040000')]
    if not 1 <= n <= 127:
        raise ValueError('drop limit: 1..127, or 0 for no count limit')
    return [bytes([n]), bytes([_low(n)]), H('0f8c0d040000')]


def _dec_limit(cur):
    if cur[2] == H('90e90d040000'):
        return 0
    return cur[0][0] if cur[2] == H('0f8c0d040000') else None


def _rate(seconds):
    return f32(1.0 / (TICKS * seconds)) if seconds else f32(0.0)


def _seconds(blob):
    r = unf32(blob)
    return 0 if r == 0 else (1.0 / (TICKS * r) if r > 0 else None)


TUNABLES = [
    dt.Tunable('drop_limit', 'Halo 1 garbage count before cleanup', 'objects', 50, [
        (GC_TRIGGER, H('66837b04'), H('32'), b''),
        (GC_LOW, H('66837b04'), H('1e'), H('410f9ec6')),
        (GC_JL, b'', H('0f8c0d040000'), H('450fb7e3')),
    ], _enc_limit, _dec_limit),
    dt.Tunable('flashlight_seconds', 'Halo 1 flashlight battery', 's', 120.0, [
        (0xAFDD2C, b'', H('f30f5c057012e500'), H('f30f1100')),     # guard: the reader
        (DRAIN, H('6e128339'), H('b4a29139'), H('b5a29139')),
    ], lambda s: [H('f30f5c057012e500'), _rate(float(s))],
        lambda cur: _seconds(cur[1])),
    dt.Tunable('flashlight_recharge_seconds', 'Halo 1 flashlight recharge', 's', 30.0, [
        (0xAFDDCF, b'', H('f30f58050912e500'), b''),               # guard: the reader
        (RECHARGE, H('6f12833a'), H('b4a2913a'), H('b5a2913a')),
    ], lambda s: [H('f30f58050912e500'), _rate(float(s) or 1e-6)],
        lambda cur: _seconds(cur[1])),
]


def sync(drop_limit=None, flashlight_seconds=None, flashlight_recharge_seconds=None,
         path=DLL, quiet=True, live_only=False, keys=None):
    """The enhancer's call: each value or None (= stock) in the running MCC AND halo1.dll.
    keys limits what is touched (default: all three). Result rows; never raises."""
    vals = {'drop_limit': drop_limit, 'flashlight_seconds': flashlight_seconds,
            'flashlight_recharge_seconds': flashlight_recharge_seconds}
    if keys is not None:
        vals = {k: v for k, v in vals.items() if k in keys}
    return dt.sync(TUNABLES, MODULE, vals, path, DLL, quiet=quiet, live_only=live_only)


def status(path=DLL):
    """{key: (file state, file value, live state, live value)} -- for a GUI label."""
    rd = dt.file_reader(path) if os.path.exists(path) else None
    lv = dt.live(MODULE, lambda h, base: {t.key: t.read(dt.live_reader(h, base))
                                          for t in TUNABLES})
    out = {}
    for t in TUNABLES:
        f = t.read(rd) if rd else ('missing', None)
        l = lv.get(t.key) if isinstance(lv, dict) else (None, None)
        out[t.key] = (f[0], f[1], l[0], l[1])
    return out


# ---- live probe (logged) ----------------------------------------------------------------

def _u64(h, a):
    b = dp.read(h, a, 8)
    return struct.unpack('<Q', b)[0] if b else 0


def _obj(h, base, handle):
    if handle in (None, 0xFFFFFFFF):
        return None
    table = _u64(h, base + OBJ_TABLE_PTR)
    if not table:
        return None
    first = struct.unpack('<i', dp.read(h, table + 0x34, 4))[0]
    off = struct.unpack('<i', dp.read(h, table + first + (handle & 0xFFFF) * 12 + 8, 4))[0]
    return None if off == -1 else _u64(h, base + OBJ_DATA_PTR) + 0x34 + off


def snapshot(h, base):
    s = {'patch': {t.key: t.read(dt.live_reader(h, base))[1] for t in TUNABLES}}
    try:
        g = _u64(h, base + GARBAGE_GLOBALS)
        s['garbage_count'] = struct.unpack('<h', dp.read(h, g + 4, 2))[0] if g else None
        pc = _u64(h, base + PLAYER_CONTROL_PTR)
        u = _obj(h, base, struct.unpack('<I', dp.read(h, pc + 0x10, 4))[0]) if pc else None
        if u:
            s['p1_flashlight_on'] = bool(struct.unpack('<I', dp.read(h, u + 0x1D4, 4))[0]
                                         & 0x10000)
            s['p1_flashlight_energy'] = round(unf32(dp.read(h, u + 0x328, 4)), 5)
    except (TypeError, struct.error):          # a mission is (un)loading
        s['level'] = 'not readable'
    return s


def probe(note='', seconds=0, every=1.0):
    """One reading (or one per `every` s for `seconds`), each appended to LOG."""
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    t_end = time.time() + seconds
    while True:
        r = dt.live(MODULE, snapshot)
        row = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'game': 'Halo 1', 'note': note,
               **(r if isinstance(r, dict) else {'error': 'MCC / halo1.dll not running'
                                                 if r is None else r[1]})}
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(row) + '\n')
        print(json.dumps(row))
        if time.time() >= t_end:
            break
        time.sleep(every)
    print('logged to %s' % LOG)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--drop-limit', type=int, help='garbage before cleanup, 1..127; 0 = none')
    ap.add_argument('--flashlight', type=float, help='battery seconds; 0 = never drains')
    ap.add_argument('--recharge', type=float, help='seconds from empty to full')
    ap.add_argument('--off', '--restore', dest='off', action='store_true', help='all stock')
    ap.add_argument('--show', action='store_true')
    ap.add_argument('--live', action='store_true', help='the running MCC only, not the file')
    ap.add_argument('--dll', default=DLL, help='a halo1.dll to act on (default: MCC\'s)')
    ap.add_argument('--probe', action='store_true', help='read + log live values')
    ap.add_argument('--watch', type=float, default=0, help='with --probe: seconds to sample')
    ap.add_argument('--note', default='', help='with --probe: the condition, for the log')
    a = ap.parse_args(argv)
    if a.probe:
        return probe(a.note, a.watch)
    if a.off:
        rows = sync(path=a.dll, quiet=False, live_only=a.live)
    else:
        given = {k: v for k, v in (('drop_limit', a.drop_limit),
                                   ('flashlight_seconds', a.flashlight),
                                   ('flashlight_recharge_seconds', a.recharge))
                 if v is not None}
        if not given:
            return dt.show(TUNABLES, MODULE, a.dll)
        rows = sync(path=a.dll, quiet=False, live_only=a.live, keys=set(given), **given)
    for r in rows:
        print('%-34s %-16s %s %s' % (r['effect'], r['field'], 'OK  ' if r['ok'] else 'FAIL',
                                     r.get('note') or r.get('reason') or r.get('new')))


if __name__ == '__main__':
    main()
