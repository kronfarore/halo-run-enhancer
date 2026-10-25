r"""Halo 2: dropped weapons/equipment stay longer, and the flashlight stays on longer --
halo2.dll VALUE patches (user, 2026-10-24 co-op; dll route chosen). All default OFF (stock).

No tag field holds either (globals has only 'Havok Cleanup Resources'). Found through the
script functions garbage_collect_now (+0x784180 -> +0x8D0E50: garbage globals +1) and
game_can_use_flashlights (+0x789A80 -> +0x8DE090). rva at image base 0x180000000.

DROPPED ITEMS -- a grace TIME, then a count (unlike Halo 1, which has only the count)
  object_set_garbage(obj, on, ticks) +0x8D9E10 sets object +4 bit 14, counts it (garbage
  globals *(+0x18B7350) +4, a word) and stamps object +0x20 = now + ticks, the earliest
  time it may be deleted. A dropped item gets 30 s (+0x91E83E movss xmm0, [30.0] -> seconds
  to ticks +0x706710). The collector +0x8DCD20 runs the object pass +0x8D04F0, which deletes
  only garbage whose +0x20 has passed and that no player sees (+0x8DC360):
    count >= 50  (+0x8DCD74 cmp word [rax+4], 0x32)  -> delete while count > 30 (+0x8DCE1F)
    object memory <= 0xCCCC free or <= 102 free object slots -> engine pressure, left stock
    a script's garbage_collect_now (03a x18, 03b, 05a/05b, 08a) -- left stock
  'drop_limit' moves the 50 (1..127, an imm8) and the 30 with it (3/5); 0 = no count limit
  (+0x8DCD79 jl -> jmp: only the engine's memory / slot pressure collects).
  'drop_grace_seconds' repoints that ONE movss at a private float (30.0 is shared by 69
  instructions): +0xDF71C0, in the .rdata raw slack (VirtualSize ends at +0xDF713C, raw at
  +0xDF7200), so the FILE carries it too. sword_energy_live.py's live slot is +0xDF7FC0.

FLASHLIGHT -- not a battery: a timer that switches it OFF (unit update +0x8FF9C0)
  The button toggles unit +0x138 bit 29 and arms unit +0x27C = 4.0 s (+0x8FFAA6, an imm32
  in the code). The timer counts down in seconds; at 0 the light goes off UNLESS the level
  script has set game_can_use_flashlights (the byte +0x8DE080 returns; dark areas) -- so
  outside those areas Halo 2's light lasts 4 s. A vehicle seat (+0x14 parent) or unit +0x10A
  bit 2 still switch it off. unit +0x278 is the light level (ramps to 1.0; the per-player
  ability predicate reads it). 'flashlight_seconds' writes the imm32; 0 = forever (1e9 s).
  Applies to the Arbiter too (his light, h2_arbiter_flashlight.py, rides the same state).

    python sprint_toolkit/h2_drops_flashlight.py --show
    python sprint_toolkit/h2_drops_flashlight.py --drop-limit 127 --grace 120 --flashlight 120
    python sprint_toolkit/h2_drops_flashlight.py --flashlight 0          # never switches off
    python sprint_toolkit/h2_drops_flashlight.py --off                   # all stock (--restore)
    python sprint_toolkit/h2_drops_flashlight.py --probe --watch 10 --note "03a, light on"
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

MODULE = 'halo2.dll'
DLL = dt.find_dll('halo2', MODULE)
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports', 'drops_flashlight.jsonl')

GC_TRIGGER = 0x8DCD78            # imm8 of cmp word [rax+4], 0x32
GC_LOW = 0x8DCE23                # imm8 of cmp word [rax+4], 0x1e
GC_JL = 0x8DCD79                 # jl +0x8DCEC6 (fewer than 50: no collection)
GRACE_INSN = 0x91E83E            # movss xmm0, [rip+0x31425a] -> 30.0 at +0xC32AA0
GRACE_SLOT = 0xDF71C0            # private float, .rdata raw slack
FLASH_IMM = 0x8FFAAC             # imm32 of mov dword [rbx+0x27c], 4.0
FOREVER = 1e9
GARBAGE_GLOBALS = 0x18B7350      # qword -> +1 script request, +4 garbage count (word)
PLAYERS_PTR = 0xE80A28           # h2_memscan.resolve_unit
OBJ_TABLE_PTR = 0x18B7398
OBJ_DATA_PTR = 0x18B7360


def _low(n):
    return n * 3 // 5


def _enc_limit(n):
    n = int(n)
    if n == 0:
        return [H('32'), H('1e'), H('90e947010000')]
    if not 1 <= n <= 127:
        raise ValueError('drop limit: 1..127, or 0 for no count limit')
    return [bytes([n]), bytes([_low(n)]), H('0f8c47010000')]


def _dec_limit(cur):
    if cur[2] == H('90e947010000'):
        return 0
    return cur[0][0] if cur[2] == H('0f8c47010000') else None


GRACE_REPOINTED = H('f30f1005') + struct.pack('<i', GRACE_SLOT - (GRACE_INSN + 8))


def _enc_grace(s):
    s = float(s)
    if not 0 < s <= 3600:
        raise ValueError('grace: 0 < seconds <= 3600')
    return [f32(s), GRACE_REPOINTED]


def _dec_grace(cur):
    return unf32(cur[0]) if cur[1] == GRACE_REPOINTED else None


def _enc_flash(s):
    s = float(s)
    if s < 0:
        raise ValueError('flashlight: seconds >= 0 (0 = forever)')
    return [f32(s or FOREVER)]


def _dec_flash(cur):
    v = unf32(cur[0])
    return 0 if v >= FOREVER / 10 else v


TUNABLES = [
    dt.Tunable('drop_limit', 'Halo 2 garbage count before cleanup', 'objects', 50, [
        (GC_TRIGGER, H('66837804'), H('32'), b''),
        (GC_LOW, H('66837804'), H('1e'), H('0f9fc1')),
        (GC_JL, b'', H('0f8c47010000'), H('bb02000000')),
    ], _enc_limit, _dec_limit),
    dt.Tunable('drop_grace_seconds', 'Halo 2 dropped-item grace time', 's', 30.0, [
        (GRACE_SLOT, H('00000000'), H('00000000'), H('00000000')),
        (GRACE_INSN, b'', H('f30f10055a423100'), H('e8c57edeff')),
    ], _enc_grace, _dec_grace),
    dt.Tunable('flashlight_seconds', 'Halo 2 flashlight on-time', 's', 4.0, [
        (FLASH_IMM, H('c7837c020000'), H('00008040'), H('8b8338010000')),
    ], _enc_flash, _dec_flash),
]


def sync(drop_limit=None, drop_grace_seconds=None, flashlight_seconds=None,
         path=DLL, quiet=True, live_only=False, keys=None):
    """The enhancer's call: each value or None (= stock) in the running MCC AND halo2.dll.
    keys limits what is touched (default: all three). Result rows; never raises."""
    vals = {'drop_limit': drop_limit, 'drop_grace_seconds': drop_grace_seconds,
            'flashlight_seconds': flashlight_seconds}
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


def _unit(h, base, entry=0):
    """h2_memscan.resolve_unit's chain: the players array -> unit handle -> object."""
    players = _u64(h, base + PLAYERS_PTR)
    if not players:
        return None
    el = players + _u64(h, players + 0x48) + entry * 0x224
    datum = struct.unpack('<I', dp.read(h, el + 0x2C, 4))[0]
    if datum in (0, 0xFFFFFFFF):
        return None
    tbl = _u64(h, base + OBJ_TABLE_PTR)
    off = struct.unpack('<i', dp.read(h, tbl + _u64(h, tbl + 0x48) + (datum & 0xFFFF) * 12 + 8,
                                      4))[0]
    return None if off == -1 else ((_u64(h, base + OBJ_DATA_PTR) + 0x57) & ~0xF) + off


def snapshot(h, base):
    s = {'patch': {t.key: t.read(dt.live_reader(h, base))[1] for t in TUNABLES}}
    try:
        g = _u64(h, base + GARBAGE_GLOBALS)
        s['garbage_count'] = struct.unpack('<h', dp.read(h, g + 4, 2))[0] if g else None
        for i in (0, 1):
            u = _unit(h, base, i)
            if u:
                fl = struct.unpack('<I', dp.read(h, u + 0x138, 4))[0]
                s['p%d' % (i + 1)] = {
                    'flashlight_on': bool(fl & 0x20000000),
                    'light_level': round(unf32(dp.read(h, u + 0x278, 4)), 4),
                    'timer_s': round(unf32(dp.read(h, u + 0x27C, 4)), 3)}
    except (TypeError, struct.error):          # a mission is (un)loading
        s['level'] = 'not readable'
    return s


def probe(note='', seconds=0, every=1.0):
    """One reading (or one per `every` s for `seconds`), each appended to LOG."""
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    t_end = time.time() + seconds
    while True:
        r = dt.live(MODULE, snapshot)
        row = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'game': 'Halo 2', 'note': note,
               **(r if isinstance(r, dict) else {'error': 'MCC / halo2.dll not running'
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
    ap.add_argument('--grace', type=float, help='seconds a dropped item is safe (stock 30)')
    ap.add_argument('--flashlight', type=float, help='on-time seconds; 0 = forever')
    ap.add_argument('--off', '--restore', dest='off', action='store_true', help='all stock')
    ap.add_argument('--show', action='store_true')
    ap.add_argument('--live', action='store_true', help='the running MCC only, not the file')
    ap.add_argument('--dll', default=DLL, help='a halo2.dll to act on (default: MCC\'s)')
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
                                   ('drop_grace_seconds', a.grace),
                                   ('flashlight_seconds', a.flashlight)) if v is not None}
        if not given:
            return dt.show(TUNABLES, MODULE, a.dll)
        rows = sync(path=a.dll, quiet=False, live_only=a.live, keys=set(given), **given)
    for r in rows:
        print('%-34s %-16s %s %s' % (r['effect'], r['field'], 'OK  ' if r['ok'] else 'FAIL',
                                     r.get('note') or r.get('reason') or r.get('new')))


if __name__ == '__main__':
    main()
