r"""Halo 2 'Hunters drop a Fuel Rod' -- the H2EK half (2026-10-20). See hunter_drop.py.

No Halo 2 cache map has an effect to spare and halo2_map cannot add a tag, so the drop is
built in: a NEW effect `objects\characters\hunter\effects\death` (a copy of the Brute
helmet-headshot effect -- one location `head`, one event, one part -- whose part, a crate,
becomes the pickable flak_cannon) on the Hunter model's body death response (`new damage
info / damage sections[0] body / instant responses[0]`: threshold 0, destroyed), whose
Transition Effect ships EMPTY. Then the levels are rebuilt (h2_rebuild_all.py); the
patcher blanks the reference when the option is off.

Every write is checked by `tool export-tag-to-xml`: the reference must read the new path
and nothing else may change; otherwise the file is restored.

    python h2_hunter_drop.py            dry run: what would change
    python h2_hunter_drop.py --write
"""
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h2_tagfield as TF      # noqa: E402
import h2_loosetag as LT      # noqa: E402

H2EK = TF.H2EK
TAGS = os.path.join(H2EK, 'tags')
BS = chr(92)
TEMPLATE = r'effects\objects\characters\brute\helmet_headshot'
TEMPLATE_PART = r'objects\characters\brute\garbage\brute_helmet\brute_helmet'
EFFECT = r'objects\characters\hunter\effects\death'
ROD = r'objects\weapons\support_high\flak_cannon\flak_cannon'
MODEL = r'objects\characters\hunter\hunter'
REF = 16
TRANSITION_EFFECT = 0xC          # in the loose instant-response element
EMPTY_ID = 0xFFFFFFFF


def tag(rel, ext):
    return os.path.join(TAGS, rel + ext)


def records(data, cls, length):
    """Offsets of 16-byte tagRef records: reversed class, pointer, length, -1."""
    want, out, i = cls[::-1], [], data.find(cls[::-1])
    while i >= 0:
        if i + REF <= len(data):
            _p, ln, ident = struct.unpack_from('<III', data, i + 4)
            if ln == length and ident == EMPTY_ID:
                out.append(i)
        i = data.find(want, i + 1)
    return out


def checked(path, data, expect):
    """Write `data`, export, and keep it only if `expect(xml_before, xml_after)` holds."""
    before = TF.export(path)
    old = open(path, 'rb').read()
    open(path, 'wb').write(data)
    after = TF.export(path)
    if after is None or not expect(before, after):
        open(path, 'wb').write(old)
        return False
    return True


def make_effect(write):
    src, dst = tag(TEMPLATE, '.effect'), tag(EFFECT, '.effect')
    data = bytearray(open(src, 'rb').read())
    old, new = TEMPLATE_PART.encode(), ROD.encode()
    rec = records(data, b'bloc', len(old))
    pool = data.find(old + b'\0')
    if len(rec) != 1 or pool < 0:
        raise SystemExit('template effect: %d crate records, pool at %d' % (len(rec), pool))
    data[rec[0]:rec[0] + 4] = b'weap'[::-1]
    struct.pack_into('<I', data, rec[0] + 8, len(new))
    data[pool:pool + len(old)] = new
    print('effect %s: part crate %s -> weap %s' % (EFFECT, TEMPLATE_PART, ROD))
    if not write:
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    was = '<tag_reference name="type" type="bloc">%s</tag_reference>' % TEMPLATE_PART
    now = '<tag_reference name="type" type="weap">%s</tag_reference>' % ROD
    ok = checked(dst, bytes(data), lambda b, a: now in a and a.replace(now, was) == b)
    if not ok:
        os.remove(dst)
        raise SystemExit('effect edit did not verify -- removed')
    print('  verified by export')


def hook_model(write):
    path = tag(MODEL, '.model')
    data = bytearray(open(path, 'rb').read())
    if EFFECT.encode() + b'\0' in data:
        print('model: already hooked')
        return
    xml = TF.export(path)
    marker = '<tag_reference name="transition effect" />'
    if xml.count(marker) != 1:
        raise SystemExit('model: %d empty transition effects, expected 1' % xml.count(marker))
    # the instant responses chunk: the one whose elements hold the empty effe records;
    # its own refs pool right after the element array (they are the element's only
    # non-empty strings), and the transition effect is its FIRST effe reference
    for off, _ver, cnt, es in LT.chunks(data):
        body = off + REF
        recs = [r for r in records(data, b'effe', 0) if body <= r < body + cnt * es]
        # +0xC: Transition Effect, the response's first field after type / flags /
        # threshold (New Damage Info's own shield effects come earlier, at +0xB4..)
        if cnt == 1 and recs and recs[0] - body == TRANSITION_EFFECT:
            break
    else:
        raise SystemExit('model: no instant responses chunk found')
    new = EFFECT.encode()
    r = recs[0]
    struct.pack_into('<I', data, r + 8, len(new))
    at = body + cnt * es
    data[at:at] = new + b'\0'
    print('model %s: death response transition effect -> %s' % (MODEL, EFFECT))
    if not write:
        return
    want = '<tag_reference name="transition effect" type="effe">%s</tag_reference>' % EFFECT
    if not checked(path, bytes(data), lambda b, a: want in a and
                   a.replace(want, marker) == b):
        raise SystemExit('model edit did not verify -- restored')
    print('  verified by export')


def main():
    write = '--write' in sys.argv
    if write:
        for rel, ext in ((MODEL, '.model'),):
            p = tag(rel, ext)
            if not os.path.exists(p + '.before_hunter_drop'):
                shutil.copyfile(p, p + '.before_hunter_drop')
    make_effect(write)
    hook_model(write)
    if not write:
        print('(dry run -- --write to save)')


if __name__ == '__main__':
    main()
