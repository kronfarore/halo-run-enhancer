r"""The Arbiter's flashlight (2026-10-24 co-op request): an OPTION, default off.

Halo 2's flashlight key already drives the Arbiter: it toggles the same unit float the
Chief's does (unit+0x278, 1.0 = on) -- which is what the per-player abilities read
(halo2-per-player-input-hunt) -- and natively it also cloaks him, which the halo2.dll
patches `no-camo-grant` + `no-arbiter-camo` switch off (h2_dll_patch.py; they must stay on).
What dervish.biped lacks is everything VISIBLE. masterchief.biped carries three things:

  integrated light toggle   effe  objects\characters\masterchief\flashlight  (the click)
  attachments [1], [2]      ligh  objects\characters\masterchief\flashlight_1p / _3p
                            marker `flashlight`, primary scale `integrated_light_power`

`integrated_light_power` is an engine-exported unit function (no Functions-block row on
the Chief either), so the lights fade with the flashlight state on any unit. The Arbiter's
render model has no `flashlight` marker. The kit hung his lights on `head` (on the Chief
both markers share the head node), but the Elite head sways with every idle and step, and the
beam with it (user 2026-10-27: 'the anchor point is not that great'). His only other marker
off the limbs is `body` on spine1, chest height; in the bind pose both point straight ahead
(+x, same as the Chief's `flashlight`), and the lights are `no shadow` + `ignore parent
object`, so starting inside the chest costs nothing. The patch side moves both lights onto
`body` (MARKER); a map built with `head` needs no rebuild.

KIT SIDE (this script, under the H2 kit lock): the three pieces are copied onto
H2EK\tags\objects\characters\dervish\dervish.biped, every write proved by tool.exe
(h2_tagref.fill_reference / append_attachment). So every built Halo 2 level that has the
Arbiter carries the light ON.

PATCH SIDE (`apply(m, on)`, for halo_patch -- the option): the patcher works from the
baseline, which has it on. OFF lowers the bipd's Attachments count (+0x94) to drop the
two trailing flashlight lights and nulls the Integrated Light Toggle datum (+0xC4 / +0xC8);
ON puts both back (the light elements stay in place past the count, so ON after OFF on the
same image works too) and points their marker at MARKER. Marker string ids in the cache are
(length << 24) | string-table index (04b: head 0x04000095, body 0x040000BD). A map without dervish.biped, or one built before this, is reported
and left alone. Cache layout from the Halo2MCC bipd plugin: Attachments elem 0x18, type
tagref at +0x0 (class, datum).

    python h2_arbiter_flashlight.py                kit edit (idempotent) + report
    python h2_arbiter_flashlight.py --check <map>  what a built map carries
    python h2_arbiter_flashlight.py --map <in> --off|--on [--out <out>]
"""
import argparse
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

H2EK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'H2EK')
DERVISH = r'objects\characters\dervish\dervish'
TAG = os.path.join(H2EK, 'tags', DERVISH + '.biped')
TOGGLE = r'objects\characters\masterchief\flashlight'
LIGHTS = (r'objects\characters\masterchief\flashlight_1p',
          r'objects\characters\masterchief\flashlight_3p')
MARKER = 'body'                         # spine1: steadier than 'head' (see above)
SCALE = 'integrated_light_power'

ATTACH, ATTACH_SZ = 0x94, 0x18          # bipd Attachments (cache)
TOGGLE_REF = 0xC4                       # bipd Integrated Light Toggle tagref (class, datum)
NULL = 0xFFFFFFFF


# --- kit side ------------------------------------------------------------------------
def _fill_toggle():
    """The toggle path, placed where masterchief.biped has it. h2_tagref.fill_reference tries
    every byte after a null as the place, and the right one is ~800 bytes in (tool asserted on
    the earlier candidates, 2026-10-25), so it is placed directly instead: the record is the
    root offset at which the Chief's root holds this reference (both roots are 988 bytes), the
    path goes in FIELD order -- after the change-colors chunks, just before the unit's `scnu`
    descriptor chunk, as on the Chief. tool.exe checks it: the field must read the path and
    every other field as before, or the file is restored."""
    import h2_tagfield as tf
    chief = open(os.path.join(H2EK, 'tags', r'objects\characters\masterchief\masterchief.biped'),
                 'rb').read()
    original = open(TAG, 'rb').read()
    d = bytearray(original)
    rs, size = 0x50, struct.unpack_from('<I', d, 0x4C)[0]
    recs = [i for i in range(rs, rs + size, 4) if chief[i:i + 4] == b'effe'
            and struct.unpack_from('<I', chief, i + 8)[0] == len(TOGGLE)]
    spot = d.find(b'scnu', rs + size)
    if size != struct.unpack_from('<I', chief, 0x4C)[0] or len(recs) != 1 or spot < 0 \
            or d[recs[0]:recs[0] + 4] != b'effe' or struct.unpack_from('<I', d, recs[0] + 8)[0]:
        raise ValueError('dervish.biped does not match the layout this was worked out on')
    rows0 = [r[4] for r in tf.read_all(tf.export(TAG))]
    struct.pack_into('<I', d, recs[0] + 8, len(TOGGLE))
    d[spot:spot] = TOGGLE.encode('latin-1') + b'\0'
    open(TAG, 'wb').write(bytes(d))
    x = tf.export(TAG)
    if not x or ('<tag_reference name="integrated light toggle" type="effe">%s<' % TOGGLE) not in x \
            or [r[4] for r in tf.read_all(x)] != rows0:
        open(TAG, 'wb').write(original)
        raise ValueError('the toggle edit did not read back as intended; restored')
    print('dervish.biped: integrated light toggle -> %s (record 0x%X, path at 0x%X)'
          % (TOGGLE, recs[0], spot))


def kit():
    import h2_tagref
    import kit_lock
    with kit_lock.held('arbiter flashlight kit edit', kit='h2'):
        bak = TAG + '.preflashlight'
        if not os.path.exists(bak):
            shutil.copy2(TAG, bak)
            print('backed up -> %s' % os.path.basename(bak))
        refs = h2_tagref.references(TAG)
        if ('effe', TOGGLE) not in refs:
            _fill_toggle()
        for light in LIGHTS:
            if ('ligh', light) not in h2_tagref.references(TAG):
                h2_tagref.append_attachment(TAG, 'ligh', light, MARKER, 'effe', primary_scale=SCALE)
        print('dervish.biped references: %s' % ', '.join(
            '%s %s' % r for r in h2_tagref.references(TAG)))


# --- patch side ----------------------------------------------------------------------
def _resolve(m, datum):
    t = m.tag(datum & 0xFFFF) if datum != NULL else None
    return t['name'] if t and t['datum'] == datum else None


def _find(m, cls, name):
    return next((t for t in m.tags if t['class'] == cls and t['name'] == name), None)


def state(m):
    """None when the map has no Arbiter (or no flashlight lights in it); else a dict:
    base, count (current), lights [element indices of our lights, counted or not], toggle."""
    b = _find(m, 'bipd', DERVISH)
    if not b or b['base'] is None:
        return None
    base = b['base']
    n, ptr = m.i32(base + ATTACH), m.u32(base + ATTACH + 4)
    if not ptr:
        return None
    arr = m.p2o(ptr)
    lights = []
    for i in range(n + len(LIGHTS)):              # past the count too: an earlier OFF
        name = _resolve(m, m.u32(arr + i * ATTACH_SZ + 4))
        if name in LIGHTS:
            lights.append(i)
        elif i >= n:
            break
    if not lights:
        return None
    return {'base': base, 'count': n, 'lights': lights,
            'toggle': _resolve(m, m.u32(base + TOGGLE_REF + 4))}


def _sid(m, name):
    """The cache string id of `name` ((length << 24) | index), or None when not in the map."""
    for i in range(m.u32(0x30)):
        if m.resolve_stringid(i) == name:
            return (len(name) << 24) | i
    return None


def apply(m, on):
    """Switch the Arbiter's flashlight on/off in an open Halo2Map. Returns a report line,
    or None when the map has nothing to switch (no Arbiter, or built before the kit edit)."""
    s = state(m)
    if s is None:
        return None
    base, lights = s['base'], s['lights']
    if lights != list(range(lights[0], lights[0] + len(lights))) or lights[0] + len(lights) < s['count']:
        raise ValueError('dervish attachments: the flashlight lights are not the trailing elements')
    want = lights[0] + len(lights) if on else lights[0]
    struct.pack_into('<i', m.data, base + ATTACH, want)
    eff = _find(m, 'effe', TOGGLE)
    if on and not eff:
        raise ValueError('the flashlight toggle effect is not in this map')
    struct.pack_into('<I', m.data, base + TOGGLE_REF + 4, eff['datum'] if on else NULL)
    marker = ''
    if on:
        sid = _sid(m, MARKER)
        if sid is None:
            raise ValueError('marker %r is not in this map' % MARKER)
        arr = m.p2o(m.u32(base + ATTACH + 4))
        for i in lights:
            struct.pack_into('<I', m.data, arr + i * ATTACH_SZ + 8, sid)
        marker = ', marker %s' % MARKER
    return 'Arbiter flashlight %s (attachments %d -> %d, toggle effect %s%s)' % (
        'ON' if on else 'OFF', s['count'], want, 'set' if on else 'cleared', marker)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', metavar='MAP')
    ap.add_argument('--map')
    ap.add_argument('--out')
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--on', action='store_true')
    g.add_argument('--off', action='store_true')
    a = ap.parse_args()
    if not (a.check or a.map):
        return kit()
    import halo2_map
    m = halo2_map.Halo2Map(a.check or a.map)
    if a.check:
        s = state(m)
        if s is None:
            print('%s: no Arbiter flashlight (no dervish biped, or built before the kit edit)'
                  % os.path.basename(a.check))
            return 1
        on = s['count'] > s['lights'][0]
        arr = m.p2o(m.u32(s['base'] + ATTACH + 4))
        print('%s: Arbiter flashlight %s -- attachments %d, lights at %s, toggle %s, marker %s'
              % (os.path.basename(a.check), 'ON' if on else 'OFF', s['count'], s['lights'],
                 s['toggle'], '/'.join(sorted({m.resolve_stringid(m.u32(arr + i * ATTACH_SZ + 8))
                                               for i in s['lights']}))))
        return 0
    if not (a.on or a.off):
        sys.exit('--map needs --on or --off')
    print(apply(m, a.on) or 'nothing to switch')
    m.save(a.out or a.map)


if __name__ == '__main__':
    sys.exit(main() or 0)
