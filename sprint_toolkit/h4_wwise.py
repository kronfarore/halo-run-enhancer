r"""Read Halo 4's Wwise sound data (MCC: halo4\sound\pc\sfxbank.pck / sfxstream.pck).

RESEARCH TOOL for porting a weapon's sounds INTO Halo 4 (step: firing sound). Halo 4's
sound tags hold no audio: a .sound tag names a Wwise EVENT and a .soundbank tag naming a
BANK; the game hashes both names (Wwise FNV-1, lower case) and finds the bank in the AKPK
package by that id.

    python h4_wwise.py --bank sentinel                 bank entry + HIRC summary
    python h4_wwise.py --event play_wea_sentinel_friendly_beam_fire_in --bank sentinel
"""
import argparse
import os
import struct

MCC = r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection'
BANKS = os.path.join(MCC, 'halo4', 'sound', 'pc', 'sfxbank.pck')
STREAMS = os.path.join(MCC, 'halo4', 'sound', 'pc', 'sfxstream.pck')
HIRC_TYPES = {1: 'settings', 2: 'sound', 3: 'action', 4: 'event', 5: 'random/sequence',
              6: 'switch', 7: 'actor-mixer', 8: 'bus', 9: 'blend', 10: 'music segment',
              11: 'music track', 12: 'music switch', 13: 'music playlist', 14: 'attenuation',
              15: 'dialogue event', 16: 'motion bus', 17: 'motion fx', 18: 'effect',
              19: 'unknown19', 20: 'aux bus'}


def fnv(name):
    """Wwise short id: FNV-1 32 over the lower-case name."""
    h = 2166136261
    for c in name.lower().encode():
        h = (h * 16777619) & 0xFFFFFFFF
        h ^= c
    return h


def read_pck(path):
    """{'langs': {id: name}, 'banks': {id: (block, size, start, lang)}, 'streams': {...}}"""
    with open(path, 'rb') as f:
        hd = f.read(0x1C)
        magic, hsz, ver, lsz, bsz, ssz, xsz = struct.unpack('<4sIIIIII', hd)
        if magic != b'AKPK':
            raise SystemExit('%s is not an AKPK package' % path)
        body = f.read(hsz + 8 - 0x1C)
    lang = body[:lsz]
    langs = {}
    for i in range(struct.unpack_from('<I', lang, 0)[0]):
        off, lid = struct.unpack_from('<II', lang, 4 + i * 8)
        e = off
        while lang[e:e + 2] != b'\0\0':
            e += 2
        langs[lid] = lang[off:e].decode('utf-16-le')

    def lut(blob):
        out = {}
        if len(blob) < 4:
            return out
        for i in range(struct.unpack_from('<I', blob, 0)[0]):
            bid, blk, size, start, lg = struct.unpack_from('<IIIII', blob, 4 + i * 20)
            out[bid] = (blk, size, start, lg)
        return out
    return {'version': ver, 'header': hsz + 8, 'langs': langs,
            'banks': lut(body[lsz:lsz + bsz]), 'streams': lut(body[lsz + bsz:lsz + bsz + ssz])}


def bank_bytes(path, entry):
    blk, size, start, _lg = entry
    with open(path, 'rb') as f:
        f.seek(start * blk)
        return f.read(size)


def chunks(bank):
    out, i = {}, 0
    while i + 8 <= len(bank):
        tag, n = bank[i:i + 4].decode('latin-1'), struct.unpack_from('<I', bank, i + 4)[0]
        out[tag] = (i + 8, n)
        i += 8 + n
    return out


def hirc(bank):
    c = chunks(bank)
    if 'HIRC' not in c:
        return []
    at, _n = c['HIRC']
    count = struct.unpack_from('<I', bank, at)[0]
    i, objs = at + 4, []
    for _ in range(count):
        t = bank[i]
        size, oid = struct.unpack_from('<II', bank, i + 1)
        objs.append((t, oid, bank[i + 9:i + 5 + size]))
        i += 5 + size
    return objs


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bank')
    ap.add_argument('--event')
    a = ap.parse_args()
    p = read_pck(BANKS)
    s = read_pck(STREAMS)
    print('sfxbank.pck: version %d, %d banks, languages %s; sfxstream.pck: %d banks, %d streams'
          % (p['version'], len(p['banks']), p['langs'], len(s['banks']), len(s['streams'])))
    if not a.bank:
        return
    bid = fnv(a.bank)
    ent = p['banks'].get(bid)
    print('bank %r id %#010x -> %s' % (a.bank, bid, ent))
    if not ent:
        return
    b = bank_bytes(BANKS, ent)
    c = chunks(b)
    bkhd = struct.unpack_from('<II', b, c['BKHD'][0])
    print('chunks', {k: v[1] for k, v in c.items()}, 'BKHD version %d id %#x' % bkhd)
    objs = hirc(b)
    from collections import Counter
    print('HIRC', len(objs), dict(Counter(HIRC_TYPES.get(t, t) for t, _i, _d in objs)))
    if a.event:
        eid = fnv(a.event)
        byid = {oid: (t, d) for t, oid, d in objs}
        print('event %r id %#010x in bank: %s' % (a.event, eid, eid in byid))
        if eid in byid:
            _t, d = byid[eid]
            n = struct.unpack_from('<I', d, 0)[0]
            acts = struct.unpack_from('<%dI' % n, d, 4)
            for aid in acts:
                at, ad = byid.get(aid, (None, b''))
                atype = struct.unpack_from('<H', ad, 0)[0] if ad else None
                target = struct.unpack_from('<I', ad, 2)[0] if ad else None
                tt = byid.get(target, (None,))[0]
                print('  action %#x type %#06x -> target %#x (%s)' % (aid, atype or 0, target or 0,
                                                                     HIRC_TYPES.get(tt, tt)))


if __name__ == '__main__':
    main()
