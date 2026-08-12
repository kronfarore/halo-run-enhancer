r"""Binary patches for halo3odst.dll, with verify-before-write and a backup.

Same contract as h2_dll_patch.py: every entry records the exact original bytes and
refuses to write unless it finds them, so a game update or a different install is
rejected rather than corrupted. --revert restores. MCC must be fully CLOSED to patch
and fully RESTARTED afterwards -- the dll is mapped at process start, so reloading a
level is not enough.

THE KIKOWANI STARTING-WEAPON FIX -- apply `allow-inactive-weapon`

Why the starting profile silently produced empty hands, found by disassembly rather
than by guessing at map data:

`unit_add_equipment <unit> <starting_profile> <boolean>` is the engine's own "apply a
starting profile", and the HaloScript table hands over its implementation --
0x18039C3F8. It walks the profile's two weapon slots (element size 0x58, slot stride
0x14 starting at the primary tagRef's datum, profile+0x34), and for each one does:

    object_placement_data_new(&data, ...)     0x18037C954
    handle = object_new(&data)                0x18037CF34
    if (handle == -1) continue                <-- the empty hand, no error, no log

Inside object_new, the third early bail-out is:

    mov  ecx, dword ptr [rsi]                 ; the weapon's tag datum
    call 0x18014D4C8                          ; tag_is_active(datum)
    test al, al
    je   fail                                 ; -> returns -1

and 0x18014D4C8 is a plain residency bitmap lookup:

    if (datum == -1) return false
    word = (datum >> 5) & 0x7FF
    return (table[word] >> (datum & 0x1F)) & 1     ; table at [rip+0x7E5374] + 0x2A2F8

0x800 dwords = one bit per tag row. That single bit explains every observation on
sc150 at once: assault_rifle / smg_silenced / automag are active at level start and
work; the carbine and shotgun are active only in the later zone, so they render as
world placements you walk up to but cannot be granted at the start; the rocket
launcher is never active anywhere, which is why it never appeared by any route.

`allow-inactive-weapon` NOPs the 6-byte bail-out in object_new only, leaving the
tag_is_active helper alone so nothing else in the engine changes behaviour.

IMPORTANT -- this lets the engine build an object whose resources it believed were not
resident. That is safe only for a weapon whose pages actually exist in the map. Check
first, per map:

    python h3_raw_residency.py sc150 --survey

On sc150 that clears 15 of 17 weapons; rocket_launcher and spartan_laser have no
pages at all and must never be offered there, patch or no patch.

Usage:
    python odst_dll_patch.py --list
    python odst_dll_patch.py --apply allow-inactive-weapon
    python odst_dll_patch.py --revert allow-inactive-weapon
"""
import argparse
import os
import shutil

DLL = (r'C:\Program Files (x86)\Steam\steamapps\common'
       r'\Halo The Master Chief Collection\halo3odst\halo3odst.dll')

PATCHES = {
    'allow-inactive-weapon': {
        'offset': 0x0037C380,          # VA 0x18037CF80, inside object_new
        # je fail -- taken when tag_is_active(weapon datum) says the tag is not
        # resident in the current zone set. Six bytes, so six NOPs keep every other
        # instruction at its address.
        'original': bytes.fromhex('0f84ef0c0000'),
        'patched': bytes.fromhex('909090909090'),
        'note': 'object_new stops refusing to build a tag the zone set has not '
                'marked active -- the Kikowani starting-weapon fix',
    },
    'tag-always-active': {
        'offset': 0x0014C8ED,          # VA 0x18014D4ED, inside tag_is_active
        # jae not_active -- the bitmap test itself. Blunter: EVERY caller in the
        # engine now believes every tag is resident. Kept as a fallback in case the
        # refusal turns out to have a second site, but prefer the surgical patch.
        'original': bytes.fromhex('7303'),
        'patched': bytes.fromhex('9090'),
        'note': 'DANGEROUS FALLBACK: tag_is_active returns true for every tag',
    },
}


def _verify(data, p):
    o, n = p['offset'], len(p['original'])
    return bytes(data[o:o + n])


def apply(name, revert=False, dll=DLL):
    p = PATCHES[name]
    want = p['patched'] if revert else p['original']
    give = p['original'] if revert else p['patched']
    with open(dll, 'rb') as f:
        data = bytearray(f.read())
    found = _verify(data, p)
    if found == give:
        print('  %s: already %s' % (name, 'reverted' if revert else 'applied'))
        return True
    if found != want:
        print('  %s: REFUSING -- expected %s at 0x%08X, found %s'
              % (name, want.hex(), p['offset'], found.hex()))
        return False
    bak = dll + '.bak'
    if not os.path.exists(bak):
        shutil.copy2(dll, bak)
        print('  backed up to %s' % os.path.basename(bak))
    data[p['offset']:p['offset'] + len(give)] = give
    with open(dll, 'wb') as f:
        f.write(data)
    print('  %s: %s at 0x%08X (%s -> %s)'
          % (name, 'reverted' if revert else 'applied', p['offset'],
             want.hex(), give.hex()))
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dll', default=DLL)
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--apply', action='append', default=[])
    ap.add_argument('--revert', action='append', default=[])
    a = ap.parse_args(argv)

    if not os.path.exists(a.dll):
        raise SystemExit('not found: %s' % a.dll)
    if a.list or not (a.apply or a.revert):
        with open(a.dll, 'rb') as f:
            data = f.read()
        print('halo3odst.dll (%d bytes)' % len(data))
        for name, p in PATCHES.items():
            found = _verify(data, p)
            state = ('APPLIED' if found == p['patched'] else
                     'clean' if found == p['original'] else 'UNKNOWN(%s)' % found.hex())
            print('  %-24s %-16s %s' % (name, state, p['note']))
        return 0
    ok = True
    for n in a.apply:
        ok &= apply(n, False, a.dll)
    for n in a.revert:
        ok &= apply(n, True, a.dll)
    print('\nMCC must be fully restarted for this to take effect.')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
