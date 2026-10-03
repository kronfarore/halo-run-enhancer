r"""A ported weapon's sound VOLUME, set at patch time (Halo 3, ODST, Reach).

WHERE A SOUND'S VOLUME LIVES: not in the sound tag. A compiled sound (snd!) holds an
INDEX into the map's sound gestalt (ugh!) "Playbacks" block, and the gain is that
entry's Gain Base (dB). The cache builder POOLS identical entries: before this tool, the
SAW's firing sound shared its entry with 4598 stock sounds in Halo 3's 010_jungle, 285
in ODST's sc150 and 2083 in Reach's m20 -- writing it would have changed all of them.

THE BUILD-TIME MARKER (saw_port_sounds.py): each port's sounds are built MARKER_DB below
their as-built gain (the SAW: -0.01 dB, inaudible). No stock sound carries such a value,
so the builder cannot pool them with anything else: the port OWNS its entries, one per
distinct as-built gain. This tool finds them through the port's sound tags and shifts
their Gain Base by the knob. It REFUSES when an entry is also used by a sound outside the
port (a map built before the marker) -- nothing is written then.

THE KNOB is relative, in dB, to the as-built level, so it must be applied to the
BASELINE map (the patcher's fresh copy), never twice to the same file.

    import port_volume
    rows = port_volume.apply(m, 'Halo 3', 'SAW', -3.0)     # m: an open map, saved by the caller

COMMAND LINE (cmd.exe):
    python port_volume.py --game "Halo 3" --map 010_jungle             report
    python port_volume.py --game "Halo 3" --map 010_jungle --shift 6 --write
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

B = chr(92)
#: port -> the folder its own sound tags live in (every game that has them)
PORT_SOUNDS = {'SAW': B.join(['sound', 'weapons', 'saw_port'])}
#: the build-time marker: each port's sounds sit this far below their as-built gain. One
#: value PER PORT, so two ports in one map can never pool with each other.
MARKER_DB = {'SAW': 0.01}
#: game -> (snd! playback index offset, ugh! Playbacks block offset, element size,
#:          Gain Base offset) -- Assembly's MCC plugins
LAYOUT = {'Halo 3': (0x0C, 0x10, 0x44, 0x1C),
          'Halo 3: ODST': (0x0C, 0x10, 0x44, 0x1C),
          'Halo Reach': (0x0E, 0x10, 0x54, 0x2C)}
FOLDER = {'Halo 3': 'halo3', 'Halo 3: ODST': 'halo3odst', 'Halo Reach': 'haloreach'}


def _f32(m, o):
    return struct.unpack_from('<f', m.data, o)[0]


def entries(m, game, weapon):
    """{playback index: [port sound names]}, {playback index: [OTHER sounds using it]},
    and the Playbacks element offsets. Empty dicts when the map has no such port."""
    snd_off, blk, esz, _g = LAYOUT[game]
    folder = PORT_SOUNDS[weapon].lower() + B
    ugh = m.find_tags('ugh!', '*')
    if not ugh:
        return {}, {}, []
    pbs = m.follow_all(ugh[0][1], [blk], [esz], 'all')
    own, users = {}, {}
    for name, base in m.find_tags('snd!', '*'):
        i = struct.unpack_from('<h', m.data, base + snd_off)[0]
        if i < 0 or i >= len(pbs):
            continue
        n = str(name)
        (own if n.lower().startswith(folder) else users).setdefault(i, []).append(n)
    shared = {i: users[i] for i in own if i in users}
    return own, shared, pbs


def apply(m, game, weapon, db):
    """Shift the port's own Playbacks entries by `db` dB. Returns [(index, old, new,
    sounds)]. Raises ValueError (nothing written) when an entry is shared."""
    if game not in LAYOUT or weapon not in PORT_SOUNDS:
        return []
    own, shared, pbs = entries(m, game, weapon)
    if shared:
        i = sorted(shared)[0]
        raise ValueError('%s %s: playback entry %d is shared with %d other sounds (e.g. %s) -- '
                         'the map was built without the volume marker'
                         % (game, weapon, i, len(shared[i]), shared[i][0]))
    gain_off = LAYOUT[game][3]
    rows = []
    for i in sorted(own):
        o = pbs[i] + gain_off
        old = _f32(m, o)
        struct.pack_into('<f', m.data, o, old + db)
        rows.append((i, old, old + db, own[i]))
    return rows


def main():
    import halo_patch as hp
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', required=True, choices=sorted(LAYOUT))
    ap.add_argument('--map', required=True, help='mission name, e.g. 010_jungle, or a .map path')
    ap.add_argument('--weapon', default='SAW', choices=sorted(PORT_SOUNDS))
    ap.add_argument('--mcc', default=os.path.dirname(HERE))
    ap.add_argument('--shift', type=float, help='dB relative to what the map holds now')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    path = a.map if a.map.lower().endswith('.map') else \
        os.path.join(a.mcc, FOLDER[a.game], 'maps', a.map + '.map')
    m = hp.open_map(path, a.game)
    own, shared, pbs = entries(m, a.game, a.weapon)
    gain_off = LAYOUT[a.game][3]
    print('%s  %s: %d playback entries' % (os.path.basename(path), a.weapon, len(own)))
    for i in sorted(own):
        print('   #%-4d gain %+7.3f dB  %s%s' % (
            i, _f32(m, pbs[i] + gain_off), ', '.join(n.rsplit(B, 1)[-1] for n in own[i]),
            '   SHARED with %d other sounds' % len(shared[i]) if i in shared else ''))
    if a.shift is None:
        return
    rows = apply(m, a.game, a.weapon, a.shift)
    for i, old, new, _n in rows:
        print('   #%-4d %+7.3f -> %+7.3f dB' % (i, old, new))
    if a.write:
        m.save()
        print('written %s' % path)
    else:
        print('(dry run -- pass --write)')


if __name__ == '__main__':
    main()
