r"""Give the Halo 1 port its OWN pickup text, instead of the Assault Rifle's.

Halo 1 is the easiest of the four, and it was already half right: its ICON is owned --
`add_msg_icon.py` appends a NEW sequence (25) to the shared `hud_msg_icons` sheet with
every stock index untouched -- but its TEXT was never fixed. The weapon's
`item_attrs.message_index` is **4**, which is `ui\hud\hud_item_messages` entry 4,
"Picked up an assault rifle". The port says it is an Assault Rifle.

    [ 4] Picked up an assault rifle
    [ 5] Picked up %d rounds for assault rifle

The engine reads the index AND the one after it -- 4 is the pickup line and 5 the ammo
line -- so a port needs a PAIR, and it appends them:

    [47] Picked up a SAW
    [48] Picked up %d rounds for SAW

**Appending is safe in a way it is not in the other games.** A Halo 1
`unicode_string_list` is addressed BY POSITION, so new entries at the end cannot move an
existing one: no offset table, no pooled strings, no length bookkeeping, nothing to
desynchronise. The other three games all needed care here (see `PORTING.md`, "Step 8,
the text"); Halo 1 needs none.

HCEEK has no `extract-unicode-strings`, and does not need one: Reclaimer reads and writes
the tag directly, which is how the rest of the Halo 1 pipeline already works.

    python h1_port_messages.py                 # show what it would add
    python h1_port_messages.py --write

STILL TO CONFIRM IN GAME, as in every other game: MCC reads HUD text from
`data\UI\Localization\<LANG>_Halo1.bin` rather than the map. Adding entries is what made
ODST fall back to the map's copy, and the port's own text then showed correctly; whether
Halo 1 behaves the same way is one look at a picked-up SAW.
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.ustr import ustr_def                    # noqa: E402
from reclaimer.hek.defs.weap import weap_def                    # noqa: E402

B = os.sep
EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'HCEEK')
MESSAGES = os.path.join(EK, 'tags', 'ui', 'hud', 'hud_item_messages.unicode_string_list')
WEAPON = os.path.join(EK, 'tags', 'weapons', 'saw', 'saw.weapon')
DONOR_INDEX = 4                      # the Assault Rifle's pair, 4 and 5
LINES = ['Picked up a SAW', 'Picked up %d rounds for SAW']


def text(e):
    d = e.data
    if isinstance(d, str):
        return d
    try:
        b = bytes(d)
    except TypeError:
        b = bytes(d.STEPTREE)
    return b.decode('utf-16-le', 'replace').replace('\x00', '')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    for p in (MESSAGES, WEAPON):
        if not os.path.exists(p):
            raise SystemExit('missing %s' % p)

    t = ustr_def.build(filepath=MESSAGES)
    sl = t.data.tagdata.strings.STEPTREE
    w = weap_def.build(filepath=WEAPON)
    have = w.data.tagdata.item_attrs.message_index

    print('%s: %d strings' % (os.path.basename(MESSAGES), len(sl)))
    print('   the port currently points at [%d] %r' % (have, text(sl[have])))
    print('   and the engine reads [%d] %r for ammo' % (have + 1, text(sl[have + 1])))

    mine = [i for i, e in enumerate(sl) if text(e) == LINES[0]]
    if mine:
        print('\n   its own pair is already at [%d]' % mine[0])
        index = mine[0]
    else:
        index = len(sl)
        print('\n   would append:')
        for k, l in enumerate(LINES):
            print('      [%d] %r' % (index + k, l))

    if not a.write:
        print('\n(dry run -- pass --write)')
        return

    if not mine:
        if not os.path.exists(MESSAGES + '.before_saw'):
            shutil.copy2(MESSAGES, MESSAGES + '.before_saw')
        for l in LINES:
            sl.append()
            sl[-1].data = l
        t.serialize(temp=False, backup=False)
        back = ustr_def.build(filepath=MESSAGES)
        bl = back.data.tagdata.strings.STEPTREE
        print('   %d -> %d strings' % (len(sl) - len(LINES), len(bl)))
        for k in range(len(LINES)):
            print('      [%d] %r' % (index + k, text(bl[index + k])))
        # every pre-existing entry must still read what it did: appending is only safe
        # because nothing before it moves, and that is worth proving rather than assuming
        if text(bl[DONOR_INDEX]) != 'Picked up an assault rifle':
            raise SystemExit('entry %d changed -- the append was not safe' % DONOR_INDEX)
        print('   entry %d still reads %r' % (DONOR_INDEX, text(bl[DONOR_INDEX])))

    if have != index:
        if not os.path.exists(WEAPON + '.before_messages'):
            shutil.copy2(WEAPON, WEAPON + '.before_messages')
        w.data.tagdata.item_attrs.message_index = index
        w.serialize(temp=False, backup=False)
        print('   weapon message index %d -> %d' % (have, index))
    else:
        print('   weapon already points at %d' % index)


if __name__ == '__main__':
    main()
