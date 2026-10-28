r"""LIVE test of where the Arbiter's flashlight hangs (user 2026-10-28: 'head' sways, 'body'
sways too -- 'new anchor on his model'). Which bone of the Elite skeleton stays steadiest
cannot be read from the tags (his 3P graph is the recompressed 124-byte layout, codecs not
decoded, h2_anim.py), so it is judged by eye, in one boot, by moving the light live.

HOW. The two flashlight lights (h2_arbiter_flashlight.py) hang on one marker of
dervish.render_model ('head' or 'body', read from the map's bipd attachments). This finds
that marker's 36-byte element (region, permutation, node, pad, translation, rotation,
scale) in the running MCC by its bytes plus their neighbours from the map file, and
rewrites node + translation + rotation from CANDIDATES. Every candidate puts the light at
the SAME bind-pose spot (the head marker, his face) facing model forward, so only how the
bone moves differs. Memory only: a level load puts the map's own marker back.

KEYS (global, the game keeps focus):
    F7  next anchor       F8  previous anchor
    F9  'this one' -- logged as the pick
    F11 quit (the light stays where it is until the level is reloaded)

Every switch and pick goes to reports/h2_arbiter_anchor.jsonl (halo-log-measured-values).
If the light does not move on a switch, revert to the last checkpoint once (the attachment
may have cached the marker) and say so -- that is a finding too.

    python h2_arbiter_anchor_live.py [--map <the level's .map>]     (run elevated)
"""
import argparse
import ctypes
import json
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import death_penalty as dp                                       # noqa: E402
import h2_memscan as ms                                          # noqa: E402

MAPS = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'halo2', 'h2_maps_win64_dx11')
LOG = os.path.join(HERE, 'reports', 'h2_arbiter_anchor.jsonl')
MODE = r'objects\characters\dervish\dervish'
GROUPS = 0x58                       # mode: marker groups block (count, ptr); element 12 bytes
GROUP_SZ, MARKER_SZ = 12, 36
CONTEXT = 48                        # bytes either side used to make the pattern unique
#: read-only, read/write, write-copy and their execute twins: the tag data may sit in a
#: read-only mapping (dp.write lifts the protection for the write and puts it back)
READABLE = (0x02, 0x04, 0x08, 0x20, 0x40, 0x80)

#: (bone, node index, marker translation, marker rotation x y z w). Computed from the
#: dervish.render_model bind pose (H2EK export): light origin = the head marker's spot
#: (0.1712, 0, 0.6636), facing model forward. 'head' is exactly the shipped head marker.
CANDIDATES = [
    ('head', 19, (0.020651, 0.042705, 0.0), (0.674381, 0.212631, 0.212631, 0.674379)),
    ('neck1', 16, (0.093632, 0.020578, 0.0), (0.706781, -0.021491, -0.021492, 0.706779)),
    ('neck', 11, (0.102945, 0.082244, 0.0), (0.657372, 0.260507, 0.260506, 0.657370)),
    ('spine1', 7, (0.151506, 0.129864, 0.0), (0.521525, 0.477507, 0.477507, 0.521524)),
    ('spine', 4, (0.197668, 0.129761, 0.0), (0.521525, 0.477507, 0.477507, 0.521524)),
    ('pelvis', 0, (0.223542, 0.156561, 0.0), (0.499999, 0.500000, 0.499999, 0.500001)),
    ('physics_control', 2, (0.171176, 0.000001, 0.663566), (0.0, 0.0, 0.0, 1.0)),
    ('r_hand', 38, (-0.150372, 0.010584, 0.256293), (0.312895, -0.266492, -0.124921, 0.903036)),
]
VK = {'F7': 0x76, 'F8': 0x77, 'F9': 0x78, 'F11': 0x7A}


def light_marker(path):
    """(marker name, its element offset in the map data, the map data) for the marker the
    Arbiter's flashlight lights hang on."""
    import halo2_map
    import h2_arbiter_flashlight as af
    m = halo2_map.Halo2Map(path)
    s = af.state(m)
    if s is None:
        raise SystemExit('%s: no Arbiter flashlight in this map' % os.path.basename(path))
    arr = m.p2o(m.u32(s['base'] + af.ATTACH + 4))
    sid = m.u32(arr + s['lights'][0] * af.ATTACH_SZ + 8)
    name = m.resolve_stringid(sid)
    mode = af._find(m, 'mode', MODE)
    n, ptr = m.i32(mode['base'] + GROUPS), m.u32(mode['base'] + GROUPS + 4)
    g = m.p2o(ptr)
    for k in range(n):
        e = g + k * GROUP_SZ
        if m.resolve_stringid(m.u32(e)) == name:
            cnt = m.i32(e + 4)
            if cnt != 1:
                raise SystemExit('marker group %r has %d markers, expected 1' % (name, cnt))
            return name, m.p2o(m.u32(e + 8)), bytes(m.data)
    raise SystemExit('marker group %r not in dervish.render_model' % name)


def regions(h):
    """Every committed readable region, no size cap (the tag cache can be one big block)."""
    out, addr = [], 0
    mbi = ms.MEMORY_BASIC_INFORMATION64()
    while addr < 0x7FFFFFFFFFFF:
        if not ms.k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                                     ctypes.sizeof(mbi)):
            break
        size = int(mbi.RegionSize)
        if mbi.State == ms.MEM_COMMIT and mbi.Protect in READABLE:
            out.append((int(mbi.BaseAddress), size))
        addr = int(mbi.BaseAddress) + max(size, 0x1000)
    return out


def find(h, pattern, at):
    """Process addresses of the marker element: where `pattern` occurs, + `at`."""
    hits, chunk = [], 16 << 20
    for base, size in regions(h):
        off = 0
        while off < size:
            n = min(chunk + len(pattern), size - off)
            buf = dp.read(h, base + off, n)
            if buf:
                i = buf.find(pattern)
                while i >= 0:
                    hits.append(base + off + i + at)
                    i = buf.find(pattern, i + 1)
            off += chunk
    return sorted(set(hits))


def element(cand, original):
    _name, node, t, q = cand
    return original[:2] + bytes([node]) + original[3:4] + struct.pack('<3f4f', *t, *q) \
        + original[32:36]


def log(row):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps({'time': time.strftime('%Y-%m-%d %H:%M:%S'), **row}) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--map', default=os.path.join(MAPS, '04b_floodlab.map'))
    a = ap.parse_args()
    name, e, data = light_marker(a.map)
    original = data[e:e + MARKER_SZ]
    pattern = data[e - CONTEXT:e + MARKER_SZ + CONTEXT]
    print('%s: the lights hang on marker %r (node %d)' % (os.path.basename(a.map), name, original[2]))
    pid = dp.find_pid()
    if not pid:
        raise SystemExit('MCC is not running -- start the level first')
    h = ms.k32.OpenProcess(0x1F0FFF, False, pid)
    if not h:
        raise SystemExit('OpenProcess failed -- run elevated')
    print('searching MCC memory for the marker ...')
    addrs = find(h, pattern, CONTEXT)
    if not addrs:
        # the neighbours may differ in memory; the element alone, if it is unique
        addrs = find(h, original, 0)
    if not addrs:
        raise SystemExit('marker not found in MCC memory -- is %s the level being played?'
                         % os.path.basename(a.map))
    print('found at %s' % ', '.join(hex(x) for x in addrs))
    if len(addrs) > 4:
        raise SystemExit('too many matches to write safely')
    level = os.path.basename(a.map)
    k = next(i for i, c in enumerate(CANDIDATES) if c[1] == original[2]) \
        if any(c[1] == original[2] for c in CANDIDATES) else -1

    def show(i):
        c = CANDIDATES[i]
        for x in addrs:
            ok, err = dp.write(h, x, element(c, original))
            if not ok:
                print('  write failed: %s' % err)
        print('-> anchor %d/%d: %s' % (i + 1, len(CANDIDATES), c[0]))
        log({'map': level, 'marker': name, 'event': 'show', 'anchor': c[0]})
    k = max(k, 0)
    show(k)
    print('F7 next, F8 previous, F9 pick this one, F11 quit')
    down = {v: False for v in VK.values()}
    user32 = ctypes.WinDLL('user32')
    while True:
        time.sleep(0.03)
        for key, vk in VK.items():
            pressed = bool(user32.GetAsyncKeyState(vk) & 0x8000)
            if pressed and not down[vk]:
                if key == 'F7':
                    k = (k + 1) % len(CANDIDATES)
                    show(k)
                elif key == 'F8':
                    k = (k - 1) % len(CANDIDATES)
                    show(k)
                elif key == 'F9':
                    print('   picked: %s' % CANDIDATES[k][0])
                    log({'map': level, 'marker': name, 'event': 'pick', 'anchor': CANDIDATES[k][0]})
                elif key == 'F11':
                    print('quit (light stays on %s until the level reloads)' % CANDIDATES[k][0])
                    return 0
            down[vk] = pressed


if __name__ == '__main__':
    sys.exit(main() or 0)
