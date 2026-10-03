r"""A ported weapon's sound VOLUME, set at patch time (Halo 3, ODST, Reach; Halo 4 through
its own sound bank).

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

THE ENGINE CLAMPS GAIN BASE AT 0 dB (boot 2026-10-03: the ODST SAW at +12 sounded
unmoved; the Halo 3 SAW at -20 was near silent). So a port can only be turned UP as far
as its entries sit below 0 -- HEADROOM RULE: every port ships at gain -3 (the import's
own default), its AUDIO set so that -3 is the right level (ODST's SAW: +4.5 dB soft-
limited), giving the knob +3 dB up and anything down. headroom() reports it; apply()
caps every entry at 0 and says so.

THE KNOB is relative, in dB, to the as-built level, so it must be applied to the
BASELINE map (the patcher's fresh copy), never twice to the same file.

    import port_volume
    rows = port_volume.apply(m, 'Halo 3', 'SAW', -3.0)     # m: an open map, saved by the caller

HALO 4 is not map data -- see bank_volume() below; the patcher passes the knob to
port_sounds.ensure(..., volume={port: dB}).

COMMAND LINE (cmd.exe):
    python port_volume.py --game "Halo 3" --map 010_jungle             report
    python port_volume.py --game "Halo 3" --map 010_jungle --shift 6 --write
    python port_volume.py --game "Halo 4" --weapon "Focus Rifle" --shift -3 --write
                                          (Halo 4: relative to the bank AS BUILT)
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


#: the engine's ceiling for a Playbacks entry's Gain Base (measured, see above)
CEILING_DB = 0.0


def headroom(m, game, weapon):
    """How far (dB) the knob can turn this port UP in this map before the engine's 0 dB
    clamp: the smallest distance of its entries below CEILING_DB. None without a port."""
    if game not in LAYOUT or weapon not in PORT_SOUNDS:
        return None
    own, _shared, pbs = entries(m, game, weapon)
    if not own:
        return None
    return round(min(CEILING_DB - _f32(m, pbs[i] + LAYOUT[game][3]) for i in own), 2)


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
        new = min(old + db, CEILING_DB)     # louder than 0 dB is not played louder
        struct.pack_into('<f', m.data, o, new)
        rows.append((i, old, new, own[i]))
    return rows


# ---- Halo 4: the port's OWN Wwise bank ---------------------------------------------
# Halo 4 sounds are Wwise (v88 banks in sound\pc\sfxbank.pck, installed by port_sounds.py),
# not map data. A port's bank is its own (every id renamed, h4_sound_bank.py), so nothing
# is pooled and no marker is needed: the knob shifts the Volume property (v88 prop id 0x00,
# dB float) of the bank's ROOT actor-mixer, which every sound of the bank plays through
# (Wwise volumes add down the hierarchy). The Focus Rifle's mixer ships at -6 dB, so it
# has +6 up before 0 -- capped at CEILING_DB like the maps, until a boot shows Wwise plays
# a mixer above 0 louder.
#: port -> (game folder, bank file under tool\port_sounds\<game>)
PORT_BANKS = {'Focus Rifle': ('halo4', 'port_focus_rifle.bnk')}
BANK_GAMES = {'Halo 4': 'halo4'}
HIRC_SOUND, HIRC_CONTAINER, HIRC_MIXER = 2, 5, 7
PROP_VOLUME = 0x00


def _hirc(bank):
    """[(type, id, body offset in bank, body length)] -- chunk walk as h4_wwise.py."""
    i = 0
    while i + 8 <= len(bank):
        tag, n = bank[i:i + 4], struct.unpack_from('<I', bank, i + 4)[0]
        if tag == b'HIRC':
            count = struct.unpack_from('<I', bank, i + 8)[0]
            j, out = i + 12, []
            for _ in range(count):
                t = bank[j]
                size, oid = struct.unpack_from('<II', bank, j + 1)
                out.append((t, oid, j + 9, size - 4))
                j += 5 + size
            return out
        i += 8 + n
    return []


def _node_base(bank, t, at):
    """Offset of a node's (bus id, parent id) pair, or None for a layout not handled.
    Sound: 24 bytes of embedded source data + source bits, then override-FX, FX count.
    Container / mixer: override-FX, FX count first. Only FX count 0 is handled."""
    if t == HIRC_SOUND:
        stype = struct.unpack_from('<I', bank, at + 4)[0]
        p = at + (24 if stype == 0 else 16) + 1
    elif t in (HIRC_CONTAINER, HIRC_MIXER):
        p = at
    else:
        return None
    if bank[p + 1] != 0:
        return None
    return p + 2


def _root_mixer(bank):
    """(mixer id, offset of its Volume float) of the FIRST root (reports)."""
    return _root_mixers(bank)[0]


def _root_mixers(bank):
    """[(mixer id, offset of its Volume float)] -- the actor-mixers at the top of the bank
    (parent outside it); every sound must descend from one, and every root must carry a
    Volume property (h4_sound_bank.py gives imported roots one). ValueError otherwise."""
    objs = _hirc(bank)
    parent, ours = {}, {oid for _t, oid, _a, _n in objs}
    mixers = []
    for t, oid, at, _n in objs:
        p = _node_base(bank, t, at)
        if p is None:
            if t in (HIRC_SOUND, HIRC_CONTAINER, HIRC_MIXER):
                raise ValueError('object %#x: layout not handled' % oid)
            continue
        parent[oid] = struct.unpack_from('<I', bank, p + 4)[0]
        if t == HIRC_MIXER and parent[oid] not in ours:
            mixers.append((oid, p + 8))
    if not mixers:
        raise ValueError('no root actor-mixer')
    roots = {r for r, _p in mixers}
    for t, oid, _a, _n in objs:
        if t != HIRC_SOUND:
            continue
        o, seen = oid, set()
        while o in parent and o not in roots and o not in seen:
            seen.add(o)
            o = parent[o]
        if o not in roots:
            raise ValueError('sound %#x does not play through a root mixer' % oid)
    out = []
    for root, p in mixers:
        # two flag bytes, then the prop bundle: count, ids, 4-byte values
        n = bank[p + 2]
        ids = list(bank[p + 3:p + 3 + n])
        if PROP_VOLUME not in ids:
            raise ValueError('mixer %#x carries no Volume property' % root)
        out.append((root, p + 3 + n + 4 * ids.index(PROP_VOLUME)))
    return out


def bank_volume(bank, db, cap=True):
    """The bank with EVERY root mixer's Volume shifted by `db` (each capped at
    CEILING_DB unless cap=False -- a test). Same length; returns (new bytes, old dB, new
    dB) of the first root."""
    out = bytearray(bank)
    first = None
    for _root, o in _root_mixers(bank):
        old = struct.unpack_from('<f', bank, o)[0]
        new = old + db if not cap else min(old + db, CEILING_DB)
        struct.pack_into('<f', out, o, new)
        first = first or (old, new)
    return bytes(out), first[0], first[1]


def bank_headroom(bank):
    """How far the knob can go UP: the smallest distance of any root below CEILING_DB."""
    return round(min(CEILING_DB - struct.unpack_from('<f', bank, o)[0]
                     for _r, o in _root_mixers(bank)), 2)


def main():
    import halo_patch as hp
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', required=True, choices=sorted(LAYOUT) + sorted(BANK_GAMES))
    ap.add_argument('--map', help='mission name, e.g. 010_jungle, or a .map path (not Halo 4)')
    ap.add_argument('--weapon', default='SAW', choices=sorted(PORT_SOUNDS) + sorted(PORT_BANKS))
    ap.add_argument('--mcc', default=os.path.dirname(HERE))
    ap.add_argument('--shift', type=float, help='dB relative to what the map holds now')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    if a.game in BANK_GAMES:
        return main_bank(a)
    if not a.map:
        ap.error('--map is needed for %s' % a.game)
    path = a.map if a.map.lower().endswith('.map') else \
        os.path.join(a.mcc, FOLDER[a.game], 'maps', a.map + '.map')
    m = hp.open_map(path, a.game)
    own, shared, pbs = entries(m, a.game, a.weapon)
    gain_off = LAYOUT[a.game][3]
    print('%s  %s: %d playback entries, headroom %s dB' % (
        os.path.basename(path), a.weapon, len(own), headroom(m, a.game, a.weapon)))
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


def main_bank(a):
    """Halo 4: report the live bank's mixer; --shift DB --write installs the bank at that
    volume RELATIVE TO THE BANK AS BUILT (not to what is live)."""
    import port_sounds
    folder, name = PORT_BANKS[a.weapon]
    built = open(os.path.join(port_sounds._data_dir(), folder, name), 'rb').read()
    bid = struct.unpack_from('<I', built, 12)[0]
    _r, o = _root_mixer(built)
    print('%s %s: as built, mixer volume %+.2f dB, headroom %s dB'
          % (name, a.weapon, struct.unpack_from('<f', built, o)[0], bank_headroom(built)))
    pck = os.path.join(a.mcc, port_sounds.PACKAGES[folder])
    with open(pck, 'rb') as f:
        _h, _fl, table = port_sounds.read_header(f)
        ent = next((e for e in table if e[0] == bid), None)
        live = port_sounds._bank_at(f, ent) if ent else None
    if live is None:
        print('   live package: bank NOT installed')
    else:
        _r, lo = _root_mixer(live)
        print('   live package: mixer volume %+.2f dB' % struct.unpack_from('<f', live, lo)[0])
    if a.shift is None:
        return
    for r in port_sounds.ensure(folder, a.mcc, write=a.write, volume={a.weapon: a.shift}):
        print('   %-5s %s  %s' % ('skip' if r.get('skip') else 'ok' if r['ok'] else 'FAIL', r['field'],
                                  r.get('reason') or '%s -> %s' % (r.get('old'), r.get('new'))))
    if not a.write:
        print('(dry run -- pass --write)')


if __name__ == '__main__':
    main()
