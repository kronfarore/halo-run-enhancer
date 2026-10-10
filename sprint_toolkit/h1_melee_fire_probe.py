r"""Halo 1 live probe: what the player's unit and held weapon do around a melee + fire.

Logs every CHANGE (polled far faster than the 30 Hz tick) of the fields halo1.dll uses to
gate a trigger, to out/melee_fire_probe.jsonl (one row per change, with the condition):
  unit  +0x283 animation state (0x1E melee, 0x1F airborne melee, 0x21 grenade)
        +0x269 melee/throw progress byte, +0x1D8 control flags (0x80 melee, 0x800 fire)
        +0x1F0 / +0x1F4 (the 'may fire anyway' exception in the unit update at +0xAFD419)
        +0x8C / +0x8E animation index / frame
  weap  +0x1FA control word from the unit (bit 1 fire, bit 4 = cannot fire)
        +0x202 ready timer, +0x280.. trigger 0 (state word, timer)
  global byte rva 0x2EAB8D0 (when set, the unit update skips the weapon control block)
(rva at image base 0x180000000, MCC halo1.dll of 2026-06-22; research in PORTING.md,
"no FIRE during a MELEE".)

    python sprint_toolkit/h1_melee_fire_probe.py --seconds 60 --note "hammer: melee then fire"
    python sprint_toolkit/h1_melee_fire_probe.py --once
"""
import argparse
import json
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import death_penalty as dp  # noqa: E402

PLAYER_CONTROL_PTR = 0x2D8FE70    # 4 x 0x58, +0x10 unit handle (h1_overheat_unzoom research)
OBJ_TABLE_PTR = 0x1C42248
OBJ_DATA_PTR = 0x2D9CDF8
SKIP_BYTE = 0x2EAB8D0
# tag index -> tag data, as +0xA9B648 does: instances (32 bytes) +0x14 = address, rebased
TAG_TABLE_PTR = 0x1C34FB0
TAG_ADDR_BASE = 0x2EA3410
TAG_DATA_BASE = 0x2D9CE10
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'melee_fire_probe.jsonl')


def u64(h, a):
    b = dp.read(h, a, 8)
    return struct.unpack('<Q', b)[0] if b else 0


def obj(h, base, handle):
    """Object address (the code's own resolution: data + 0x34 + entry offset)."""
    if handle in (None, 0xFFFFFFFF):
        return None
    table = u64(h, base + OBJ_TABLE_PTR)
    if not table:
        return None
    first = struct.unpack('<i', dp.read(h, table + 0x34, 4))[0]
    off = struct.unpack('<i', dp.read(h, table + first + (handle & 0xFFFF) * 12 + 8, 4))[0]
    if off == -1:
        return None
    return u64(h, base + OBJ_DATA_PTR) + 0x34 + off


def tag(h, base, index):
    inst = u64(h, base + TAG_TABLE_PTR)
    a = struct.unpack('<i', dp.read(h, inst + (index & 0xFFFF) * 32 + 0x14, 4))[0]
    return a - u64(h, base + TAG_ADDR_BASE) + u64(h, base + TAG_DATA_BASE) if a else None


def snapshot(h, base):
    try:
        return _snapshot(h, base)
    except (TypeError, struct.error):          # a read failed: the mission is (un)loading
        return None


def _snapshot(h, base):
    pc = u64(h, base + PLAYER_CONTROL_PTR)
    if not pc:
        return None
    unit_h = struct.unpack('<I', dp.read(h, pc + 0x10, 4))[0]
    u = obj(h, base, unit_h)
    if not u:
        return None
    ub = dp.read(h, u, 0x2E0)
    if not ub:
        return None
    idx = struct.unpack_from('<b', ub, 0x2D3)[0]
    wh = struct.unpack_from('<I', ub, 0x2D8 + 4 * idx)[0] if 0 <= idx < 4 else 0xFFFFFFFF
    w = obj(h, base, wh)
    wb = dp.read(h, w, 0x2A0) if w else None
    s = {
        'skip': dp.read(h, base + SKIP_BYTE, 1)[0],
        'state': ub[0x283], 'b284': ub[0x284], 'b285': ub[0x285], 'b269': ub[0x269],
        'b26d': ub[0x26D],
        'ctrl': '%08x' % struct.unpack_from('<I', ub, 0x1D8)[0],
        'u1f0': struct.unpack_from('<i', ub, 0x1F0)[0],
        'u1f4': '%08x' % struct.unpack_from('<I', ub, 0x1F4)[0],
        'anim': struct.unpack_from('<hh', ub, 0x8C),
        'widx': idx, 'weapon': '%08x' % wh,
    }
    if wb:
        s['w1fa'] = '%04x' % struct.unpack_from('<H', wb, 0x1FA)[0]
        s['w202'] = struct.unpack_from('<h', wb, 0x202)[0]
        s['trig0'] = struct.unpack_from('<hh', wb, 0x280)
        t = tag(h, base, struct.unpack_from('<I', wb, 0)[0])
        s['wflags'] = '%08x' % struct.unpack('<I', dp.read(h, t + 0x308, 4))[0] if t else None
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--seconds', type=float, default=60.0)
    ap.add_argument('--note', default='')
    ap.add_argument('--once', action='store_true')
    ap.add_argument('--wait', type=float, default=1800.0,
                    help='seconds to wait for a mission to be loaded')
    a = ap.parse_args(argv)
    pid = dp.find_pid()
    if not pid:
        raise SystemExit('MCC is not running')
    h = dp.k32.OpenProcess(dp.ACCESS, False, pid)
    base = dp.module_base(pid, b'halo1.dll')
    if not base:
        raise SystemExit('halo1.dll not loaded')
    if a.once:
        print(snapshot(h, base))
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    print('waiting for a mission ...')
    t0 = time.perf_counter()
    while snapshot(h, base) is None:
        if time.perf_counter() - t0 > a.wait:
            raise SystemExit('no mission loaded within %d s' % a.wait)
        time.sleep(0.5)
    print('in a mission: logging %d s -- do the test now' % a.seconds)
    t0 = time.perf_counter()
    last = None
    rows = 0
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(json.dumps({'start': time.strftime('%Y-%m-%d %H:%M:%S'), 'note': a.note}) + '\n')
        while time.perf_counter() - t0 < a.seconds:
            s = snapshot(h, base)
            if s != last:
                row = {'ms': round((time.perf_counter() - t0) * 1000, 1)}
                row.update(s or {'snapshot': None})
                f.write(json.dumps(row) + '\n')
                rows += 1
                last = s
            time.sleep(0.002)
    print('%d change(s) logged to %s' % (rows, OUT))


if __name__ == '__main__':
    main()
