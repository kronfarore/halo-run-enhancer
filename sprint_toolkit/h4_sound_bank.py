r"""Halo 4 port, sound: the Focus Rifle's OWN Wwise bank, built from the Sentinel bank.

Test 1 (h4_sound_test.py, boot 30) proved the chain in game: Reach's audio as PCM WEM in
a rebuilt v88 bank, read from sfxbank.pck, played by a looping sound attached to the
weapon. That test lived INSIDE the Sentinel's bank. This builds the port's own:

  * a full copy of the sentinel bank (43 HIRC objects, 15 media) with EVERY internal id
    renamed -- objects, media and the bank id -- so it never collides with the real
    sentinel bank when both are loaded. The two events the port uses get readable names:
        play_wea_port_focus_rifle_fire_in   start one-shot + loop   (was ..._sentinel_friendly_beam_fire_in)
        stop_wea_port_focus_rifle_fire      stop loop + tail        (was stop_wea_sentinel_friendly_beam_fire)
    every other id becomes fnv('port_focus_rifle/<old id>'). Ids from OUTSIDE the bank
    (buses, the mixer's parent, RTPCs) are left alone.
    Renaming is a byte replacement over the object bodies: v88 packs its fields, so ids
    sit at odd offsets; measured on the sentinel bank, every hit is a real reference.
  * the three media the events play replaced by Reach's 3p firing set (in / loop / out,
    sfx.fsb 10952-10954) as PCM, those sound objects switched to PCM.
Bank name `port_focus_rifle` (id 0xb4d927ce, free in sfxbank.pck).

Output: tool\port_sounds\halo4\port_focus_rifle.bnk -- installed into the live
sfxbank.pck by tool\port_sounds.py (patch time / by hand), the way port_glyphs.py
handles the icon fonts.

    python h4_sound_bank.py           build + verify, write the .bnk
"""
import json
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h4_sound_test as t                                          # noqa: E402
import h4_wwise as w                                               # noqa: E402

SOURCE_BANK = 'sentinel'
BANK = 'port_focus_rifle'
EVENTS = {'play_wea_sentinel_friendly_beam_fire_in': 'play_wea_port_focus_rifle_fire_in',
          'stop_wea_sentinel_friendly_beam_fire': 'stop_wea_port_focus_rifle_fire'}
#: OLD sentinel sound object -> Reach wav (as in test 1)
REPLACE = {0x090ac918: '10952_in.wav', 0x392e4cf5: '10953_loop.wav', 0x290e3e3c: '10954_out.wav'}
OUT_DIR = os.path.join(os.path.dirname(HERE), 'port_sounds', 'halo4')
#: the stock package, so a build never starts from an installed port bank
STOCK_PCK = r'F:\HaloPortBackups\h4_sound_stock\sfxbank.pck'


def renaming(bank):
    """old id -> new id for every id the bank OWNS."""
    objs = t.objects(bank)
    c = w.chunks(bank)
    di, dn = c['DIDX']
    old = [oid for _t, oid, _a, _e in objs]
    old += [struct.unpack_from('<I', bank, di + k * 12)[0] for k in range(dn // 12)]
    m = {w.fnv(SOURCE_BANK): w.fnv(BANK)}
    named = {w.fnv(a): w.fnv(b) for a, b in EVENTS.items()}
    for o in old:
        m[o] = named.get(o, w.fnv('%s/%08x' % (BANK, o)))
    if len(set(m.values())) != len(m):
        raise SystemExit('renaming collides with itself')
    return m


def rename(bank, m):
    """The bank with every owned id replaced: BKHD bank id, DIDX media ids, HIRC object
    ids (headers) and every reference inside the object bodies."""
    out = bytearray(bank)
    c = w.chunks(bank)
    bk = c['BKHD'][0]
    struct.pack_into('<I', out, bk + 4, m[struct.unpack_from('<I', bank, bk + 4)[0]])
    di, dn = c['DIDX']
    for k in range(dn // 12):
        at = di + k * 12
        struct.pack_into('<I', out, at, m[struct.unpack_from('<I', bank, at)[0]])
    hits = 0
    for _ty, oid, a, e in t.objects(bank):
        struct.pack_into('<I', out, a - 4, m[oid])            # the header id
        i = a
        while i + 4 <= e:
            v = struct.unpack_from('<I', bank, i)[0]
            if v in m:
                struct.pack_into('<I', out, i, m[v])
                hits += 1
                i += 4
            else:
                i += 1
    return bytes(out), hits


def check_events(bank):
    """Each named event must reach PCM sound objects whose media sit in this bank."""
    objs = {oid: (ty, a, e) for ty, oid, a, e in t.objects(bank)}
    c = w.chunks(bank)
    di, dn = c['DIDX']
    media = {struct.unpack_from('<I', bank, di + k * 12)[0] for k in range(dn // 12)}
    ok = True
    for name in EVENTS.values():
        eid = w.fnv(name)
        if eid not in objs:
            print('   MISSING event %s' % name)
            ok = False
            continue
        _ty, a, _e = objs[eid]
        n = struct.unpack_from('<I', bank, a)[0]
        for aid in struct.unpack_from('<%dI' % n, bank, a + 4):
            _aty, aa, _ae = objs[aid]
            kind, tgt = struct.unpack_from('<HI', bank, aa)
            ty, ta, _te = objs.get(tgt, (None, 0, 0))
            desc = w.HIRC_TYPES.get(ty, ty)
            if ty == 2:
                plug, _st, src = struct.unpack_from('<III', bank, ta)
                desc += ' %s media %s' % ('PCM' if plug == t.PCM else hex(plug),
                                          'in bank' if src in media else 'MISSING')
                ok &= src in media
            print('   %-36s action %#06x -> %#010x %s' % (name, kind, tgt, desc))
    return ok


# ---- events IMPORTED from other stock banks (2026-10-03) ----------------------------
# The OVERHEAT sound the player hears is not the weapon's: the port's first-person graph
# (a byte copy of the Beam Rifle's) cues the Beam Rifle's foley on its `overheating` and
# `o_h_exit` animations, from the stock beam_rifle_player bank. To turn it with the
# port's volume knob it has to live in the port's bank, so those two events are copied in
# WHOLE: event, actions, the target subtree (container + sounds), the media, and the
# target's ancestors up to its root actor-mixer (children trimmed to what was copied).
# Every id is renamed fnv('port_focus_rifle/<bank>/<old id>'), the bank id in the actions
# and the sounds becomes ours; the roots keep their own bus, positioning and RTPCs, so the
# sound is unchanged -- and each gets a Volume property (0 dB) for port_volume.bank_volume.
IMPORTS = {'beam_rifle_player': {
    'play_wea_beam_rifle_oh_foley_enter_player': 'play_wea_port_focus_rifle_overheat',
    'play_cov_beam_first_person_o_h_exit_player_01': 'play_wea_port_focus_rifle_overheat_exit'}}
HIRC_SOUND, HIRC_ACTION, HIRC_EVENT, HIRC_MIXER = 2, 3, 4, 7
FX = -1
SHARESETS = (14,)               # attenuation


def parse(bank):
    """(BKHD chunk bytes, [[media id, bytes]], [[type, id, body]]) -- body = after the id."""
    c = w.chunks(bank)
    if list(c) != ['BKHD', 'DIDX', 'DATA', 'HIRC']:
        raise SystemExit('unexpected chunk order %s' % list(c))
    da, _dn = c['DATA']
    di, dn = c['DIDX']
    media = [[mid, bank[da + off:da + off + size]]
             for mid, off, size in (struct.unpack_from('<III', bank, di + k * 12)
                                    for k in range(dn // 12))]
    objs = [[ty, oid, bank[a:e]] for ty, oid, a, e in t.objects(bank)]
    return bank[c['BKHD'][0] - 8:c['BKHD'][0] + c['BKHD'][1]], media, objs


def assemble(bkhd, media, objs):
    """The bank from its parts: DATA 16-aligned as shipped, every embedded sound's
    offset/size pointed at its media (absolute offsets, as the shipped banks carry)."""
    data, didx, pos = bytearray(), bytearray(), 0
    for mid, blob in media:
        pos += -pos % 16
        data += b'\0' * (pos - len(data))
        didx += struct.pack('<III', mid, pos, len(blob))
        data += blob
        pos = len(data)
    head = len(bkhd) + 8 + len(didx) + 8
    where = {mid: (off, size) for mid, off, size in struct.iter_unpack('<III', bytes(didx))}
    hirc = bytearray(struct.pack('<I', len(objs)))
    for ty, oid, body in objs:
        body = bytearray(body)
        if ty == HIRC_SOUND:
            stype, src = struct.unpack_from('<II', body, 4)
            if stype == 0:
                off, size = where[src]
                struct.pack_into('<II', body, 16, head + off, size)
        hirc += struct.pack('<BII', ty, len(body) + 4, oid) + body
    return bytes(bkhd) + b'DIDX' + struct.pack('<I', len(didx)) + bytes(didx) + \
        b'DATA' + struct.pack('<I', len(data)) + bytes(data) + \
        b'HIRC' + struct.pack('<I', len(hirc)) + bytes(hirc)


def _parent(ty, body):
    """Parent id of a sound / container / mixer body (FX count 0 only), else None."""
    if ty == HIRC_SOUND:
        p = (24 if struct.unpack_from('<I', body, 4)[0] == 0 else 16) + 1
    elif ty in (5, HIRC_MIXER):
        p = 0
    else:
        return None
    if body[p + 1] != 0:
        return FX                # an FX chain moves the parent field; refused if copied
    return struct.unpack_from('<I', body, p + 6)[0]


def _with_volume(body):
    """A mixer body with a Volume property (0 dB) added to its prop bundle, if absent."""
    p = 12                       # override-FX, FX count 0, bus, parent, 2 flag bytes
    n = body[p]
    ids = list(body[p + 1:p + 1 + n])
    if 0 in ids:
        return body
    vals = body[p + 1 + n:p + 1 + 5 * n]
    return body[:p] + bytes([n + 1]) + bytes(ids + [0]) + vals + struct.pack('<f', 0.0) + \
        body[p + 1 + 5 * n:]


def import_events(bank, src_name, events):
    """`bank` with `events` {old name: new name} of stock bank `src_name` copied in."""
    src = w.bank_bytes(STOCK_PCK, w.read_pck(STOCK_PCK)['banks'][w.fnv(src_name)])
    bkhd, media, objs = parse(bank)
    _sb, smedia, sobjs = parse(src)
    byid = {oid: (ty, body) for ty, oid, body in sobjs}
    parent = {oid: _parent(ty, body) for ty, oid, body in sobjs}
    take = []
    for old in events:
        eid = w.fnv(old)
        if eid not in byid:
            raise SystemExit('%s has no event %s' % (src_name, old))
        body = byid[eid][1]
        acts = struct.unpack_from('<%dI' % struct.unpack_from('<I', body, 0)[0], body, 4)
        take += [eid] + list(acts)
        for a in acts:
            tgt = struct.unpack_from('<I', byid[a][1], 2)[0]
            # the target, everything under it, and its ancestors
            take += [o for o in byid if _under(o, tgt, parent)]
            o = parent.get(tgt)
            while o in byid:
                take.append(o)
                o = parent.get(o)
    take = set(take)
    # share-sets the copied nodes NAME (attenuation): copied too, or they would dangle
    # once the source bank is not loaded. Children lists are trimmed below, so a mixer's
    # other children are not followed.
    for o in list(take):
        ty, body = byid[o]
        end = len(body)
        if ty == HIRC_MIXER:
            end -= 4 * sum(1 for x in parent.values() if x == o) + 4
        for i in range(end - 3):
            v = struct.unpack_from('<I', body, i)[0]
            if v in byid and v not in take and byid[v][0] in SHARESETS:
                take.add(v)
    bad = [o for o in take if parent.get(o) == FX]
    if bad:
        raise SystemExit('copied objects with an FX chain (not handled): %s' % [hex(o) for o in bad])
    fx_any = [o for o, pp in parent.items() if pp == FX]
    if any(_under(o, top, parent) for o in fx_any for top in take):
        raise SystemExit('an FX object may sit under a copied node')
    m = {w.fnv(src_name): w.fnv(BANK)}
    for o in take:
        m[o] = w.fnv('%s/%s/%08x' % (BANK, src_name, o))
    m.update({w.fnv(a): w.fnv(b) for a, b in events.items()})
    used_media = {struct.unpack_from('<I', byid[o][1], 8)[0] for o in take
                  if byid[o][0] == HIRC_SOUND and struct.unpack_from('<I', byid[o][1], 4)[0] == 0}
    for mid in used_media:
        m[mid] = w.fnv('%s/%s/media/%08x' % (BANK, src_name, mid))
    have = {oid for _t, oid, _b in objs} | {mid for mid, _x in media}
    if set(m.values()) & have or len(set(m.values())) != len(m):
        raise SystemExit('imported ids collide')
    added = []
    for ty, oid, body in sobjs:
        if oid not in take:
            continue
        body = bytearray(body)
        if ty == HIRC_MIXER:
            kids = [k for k in take if parent.get(k) == oid]
            n = struct.unpack_from('<I', body, len(body) - 4 * len([x for x in parent.values() if x == oid]) - 4)[0]
            cut = len(body) - 4 * n - 4
            body = body[:cut] + struct.pack('<I', len(kids)) + b''.join(struct.pack('<I', k) for k in sorted(kids))
            if parent.get(oid) not in byid:
                body = bytearray(_with_volume(bytes(body)))
        hits, i = 0, 0
        while i + 4 <= len(body):
            v = struct.unpack_from('<I', body, i)[0]
            if v in m:
                struct.pack_into('<I', body, i, m[v])
                hits += 1
                i += 4
            else:
                i += 1
        added.append([ty, m[oid], bytes(body)])
        print('   + %-15s %#010x -> %#010x  %d bytes, %d references renamed'
              % (w.HIRC_TYPES.get(ty, ty), oid, m[oid], len(body), hits))
    for mid, blob in smedia:
        if mid in used_media:
            media.append([m[mid], blob])
            print('   + media %#010x -> %#010x  %d bytes' % (mid, m[mid], len(blob)))
    return assemble(bkhd, media, objs + added)


def check_imports(bank):
    """Each imported event reaches sounds whose media are in this bank and DECODE
    (vgmstream), and every sound plays through a root mixer with a Volume property."""
    sys.path.insert(0, os.path.dirname(HERE))
    import port_volume
    roots = port_volume._root_mixers(bank)
    print('   root mixers: %s, knob headroom %s dB'
          % (', '.join('%#010x' % r for r, _o in roots), port_volume.bank_headroom(bank)))
    objs = w.hirc(bank)
    byid = {oid: d for _t, oid, d in objs}
    ok = True
    for name in (n for e in IMPORTS.values() for n in e.values()):
        sounds = w.event_sounds(bank, objs, w.fnv(name))
        if not sounds:
            print('   MISSING sounds for %s' % name)
            ok = False
        for verb, sid in sounds:
            plug, stype, src, fid, off, size = struct.unpack_from('<IIIIII', byid[sid], 0)
            f = os.path.join(t.OUT, '%08x.wem' % sid)
            os.makedirs(t.OUT, exist_ok=True)
            open(f, 'wb').write(bank[off:off + size])
            r = subprocess.run([t.VGM, '-m', f], capture_output=True, text=True).stdout
            dur = [l.strip() for l in r.splitlines() if 'play duration' in l]
            good = stype == 0 and fid == w.fnv(BANK) and bool(dur)
            ok &= good
            print('   %-42s %s sound %#010x codec %#x: %s' % (name, verb, sid, plug,
                                                           dur[0] if dur else 'DOES NOT DECODE'))
    return ok


def _under(o, top, parent):
    seen = set()
    while o is not None and o not in seen:
        if o == top:
            return True
        seen.add(o)
        o = parent.get(o)
    return False


def main():
    stock = w.bank_bytes(STOCK_PCK, w.read_pck(STOCK_PCK)['banks'][w.fnv(SOURCE_BANK)])
    m = renaming(stock)
    renamed, hits = rename(stock, m)
    print('renamed %d ids (%d references in object bodies); bank %#x -> %#x'
          % (len(m), hits, w.fnv(SOURCE_BANK), w.fnv(BANK)))
    # the media swap of test 1, on the renamed sound objects
    t.REPLACE = {m[k]: v for k, v in REPLACE.items()}
    bank, report = t.build(renamed)
    for oid, wav, was, now in report:
        print('   sound %#010x: %d bytes Vorbis -> %d bytes PCM (%s)' % (oid, was, now, wav))
    if not t.verify(bank):
        raise SystemExit('media verification failed')
    if not check_events(bank):
        raise SystemExit('event check failed')
    # nothing of the sentinel's own ids may survive in the new bank's HIRC/DIDX headers
    left = [o for o in m if any(struct.pack('<I', o) in bank[a - 4:e]
                                for _t, _o, a, e in t.objects(bank))]
    if left:
        raise SystemExit('old ids still referenced: %s' % [hex(x) for x in left[:8]])
    for src_name, events in IMPORTS.items():
        print('importing from %s: %s' % (src_name, ', '.join(events.values())))
        bank = import_events(bank, src_name, events)
    if not check_imports(bank):
        raise SystemExit('imported events check failed')
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, BANK + '.bnk')
    open(path, 'wb').write(bank)
    json.dump({'bank': BANK, 'bank_id': w.fnv(BANK),
               'events': list(EVENTS.values()) + [n for e in IMPORTS.values() for n in e.values()],
               'source': 'Reach focus_rifle 3p firing set (sfx.fsb 10952-10954) as PCM, in a '
                         'renamed copy of the Halo 4 sentinel bank; the Beam Rifle overheat '
                         'foley events imported from beam_rifle_player',
               'bytes': len(bank)},
              open(os.path.join(OUT_DIR, BANK + '.json'), 'w'), indent=1)
    print('wrote %s (%d bytes)' % (path, len(bank)))


if __name__ == '__main__':
    main()
