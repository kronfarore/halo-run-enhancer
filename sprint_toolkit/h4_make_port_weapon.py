r"""Halo 4 port, step 3: the port's OWN weapon tag, in H4EK.

Built the way the SAW was built in every other game: copy a DONOR that is already fully
wired, then repoint. The donor is the Beam Rifle, not the Sentinel Beam, measured:

    storm_sentinel_beam.weapon   NO model reference at all (hlmt null), first-person graph
                                 fp_plasma_pistol, no HUD screen, no soundbank -- the
                                 reason it can never be a pickup in Halo 4
    storm_beam_rifle.weapon      model, first-person model, fp_beam_rifle, its cusc HUD
                                 screen, its soundbank: everything a pickup needs

What the port takes from each:
    Focus Rifle (this port)   hlmt + first-person render model -> the Foundry export
    Sentinel Beam             the beam PROJECTILE and its firing effect -- the Sentinel Beam
                              is itself Focus-Rifle-derived: it still names
                              fx\reach\material_effects\weapons\focus_rifle and the Focus
                              Rifle's overheat sound, and so does the port
    Beam Rifle                everything else: fp graph, HUD, scope, soundbank, feedback
The firing NUMBERS (rate, heat, damage) are step 4's, from Reach's Focus Rifle.

THE MODEL TAG too: Foundry's export names an imposter model that it never builds, and a
dangling reference is a build error waiting. It is CLEARED -- an H4 null reference is a
`tgrf` chunk with an empty payload (93 of them in the Sentinel Beam's weapon tag).

Nothing is written unless every reference the new tags hold resolves to a file in H4EK.

    python h4_make_port_weapon.py [--write]
"""
import argparse
import glob
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                   # noqa: E402

H4EK = r'F:\SteamLibrary\steamapps\common\H4EK'
TAGS = os.path.join(H4EK, 'tags')
PORT = 'objects\\weapons\\rifle\\focus_rifle\\focus_rifle'
DONOR = 'objects\\weapons\\rifle\\storm_beam_rifle\\storm_beam_rifle'
SB = 'objects\\weapons\\pistol\\storm_sentinel_beam\\'

#: (group, donor path, port path) on the copied weapon
REPOINT = [
    ('hlmt', DONOR, PORT),
    ('mode', DONOR, PORT),                                    # the first-person model
    ('proj', 'objects\\weapons\\rifle\\storm_beam_rifle\\projectiles\\storm_beam_rifle_beam',
     SB + 'projectiles\\storm_sentinel_beam_beam_friendly'),
    ('effe', 'objects\\weapons\\rifle\\storm_beam_rifle\\fx\\firing',
     SB + 'fx\\friendly_beam\\firing'),
    ('foot', 'fx\\material_effects\\weapons\\sniper_rifle',
     'fx\\reach\\material_effects\\weapons\\focus_rifle'),
]


def resolves(path):
    return bool(glob.glob(os.path.join(TAGS, glob.escape(path) + '.*')))


def clear_ref(t, group, path):
    """Empty every reference to (group, path). Returns how many."""
    n = 0
    while True:
        hit = next((node for node in t.nodes() if node.marker == 'tgrf' and node.length >= 4
                    and bytes(t.data[node.payload_at:node.payload_at + 4])[::-1]
                    .decode('latin1').strip() == group
                    and bytes(t.data[node.payload_at + 4:node.payload_at + node.length])
                    .decode('latin1') == path), None)
        if hit is None:
            return n
        t.replace_payload(hit, b'')
        n += 1


def unresolved(t):
    return [(g, p) for _o, g, p in t.references() if not resolves(p)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    model = h3tag.Tag(os.path.join(TAGS, PORT + '.model'))
    cleared = clear_ref(model, 'impo', PORT)
    print('model: imposter reference cleared %d time(s)' % cleared)

    weap = h3tag.Tag(os.path.join(TAGS, DONOR + '.weapon'))
    for group, old, new in REPOINT:
        n = weap.repoint(old, new, group)
        print('weapon: %-4s %-70s x%d' % (group, new, n))
        if n < 1:
            raise SystemExit('the donor has no %s reference to %s' % (group, old))

    bad = unresolved(model) + unresolved(weap)
    if bad:
        raise SystemExit('unresolved references, nothing written:\n  ' +
                         '\n  '.join('%s %s' % b for b in bad))
    print('every reference resolves (%d in the weapon)' % len(weap.references()))
    if not a.write:
        print('(dry run -- pass --write)')
        return
    model.save()
    out = os.path.join(TAGS, PORT + '.weapon')
    weap.save(out)
    for f in (os.path.join(TAGS, PORT + '.model'), out):
        if not h3tag.Tag(f).check()[0]:
            raise SystemExit('%s no longer spans its file' % f)
    print('wrote', out)


if __name__ == '__main__':
    main()
