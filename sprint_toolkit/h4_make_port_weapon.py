r"""Halo 4 port, step 3: the port's OWN weapon tag, in H4EK.

DONOR: THE SENTINEL BEAM (user's call after the first boot, 2026-09-30). The first build
copied the Beam Rifle's weapon tag because it was fully wired -- and in game the weapon
did NOT FIRE: a single-shot sniper trigger and barrel fed a continuous beam. The Sentinel
Beam is the Focus Rifle's functional twin -- a continuous plasma beam with heat, and it
is itself Focus-Rifle-derived (it names fx\reach\material_effects\weapons\focus_rifle
and the Focus Rifle's overheat sound) -- so its trigger, barrels and heat are the right
ones. What it lacks is exactly why it is never a pickup in Halo 4: its model, first-person
model and HUD references are NULL.

TWO KINDS OF EDIT:
  * references the donor HAS are repointed in bytes (h3tag): both barrels' projectiles
    -> the port's OWN copy of the Sentinel "friendly" beam + damage effect (so step 4's
    numbers never retune the Sentinel Beam), and the model's dangling imposter reference
    is cleared (an H4 null reference is an empty `tgrf` chunk);
  * references the donor has as NULL have no bytes to repoint, so they are SET BY FIELD
    NAME through H4EK's ManagedBlam, in a Blender process (h4_weapon_refs.py, run from
    here): `model`, `first person`[0] `first person model` + `first person animations`,
    `hud screen reference`. Field names read from the Beam Rifle's XML.

First-person animations stay the Beam Rifle's: a rifle hold (the Sentinel Beam's is the
plasma pistol's). The HUD is the Plasma Pistol's (battery percentage + heat).

RUN h4_tag_numbers.py AFTER THIS: the weapon is re-copied from the donor every time.

    python h4_make_port_weapon.py [--write]
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                   # noqa: E402

H4EK = r'F:\SteamLibrary\steamapps\common\H4EK'
BLENDER = r'F:\Tools\blender-5.2.2-windows-x64\blender.exe'
TAGS = os.path.join(H4EK, 'tags')
PORT = 'objects\\weapons\\rifle\\focus_rifle\\focus_rifle'
SB = 'objects\\weapons\\pistol\\storm_sentinel_beam\\'
DONOR = SB + 'storm_sentinel_beam'
BR = 'objects\\weapons\\rifle\\storm_beam_rifle\\'

#: The port's OWN beam: a copy of the Sentinel Beam's friendly projectile and its damage
#: effect. Step 4 writes the Focus Rifle's numbers into these; writing them into the
#: Sentinel Beam's own would retune that weapon too -- the shared-tag trap.
SB_BEAM = SB + 'projectiles\\storm_sentinel_beam_beam_friendly'
OWN_PROJ = 'objects\\weapons\\rifle\\focus_rifle\\projectiles\\focus_rifle_beam'

#: (group, donor path, port path): references the donor HAS
REPOINT = [
    ('proj', SB_BEAM, OWN_PROJ),
    ('proj', SB + 'projectiles\\storm_sentinel_beam_beam_enemy', OWN_PROJ),
    # The RIGHT trigger fires barrel 0 -- the Sentinel's "enemy" barrel, whose firing
    # effect bsh_firing carries only a THIRD-person tracer (bsh_projectile_3p): an NPC
    # gun is never seen from inside. First person draws no 3p effect, so the beam was
    # invisible while its damage landed (boots 2-7). The friendly firing effect has a
    # 1p AND a 3p tracer.
    ('effe', SB + 'fx\\bsh_firing', SB + 'fx\\friendly_beam\\firing'),
]

#: (field path, tag path WITH extension): references the donor has as NULL
FP_OFFSET = '0.03,-0.08,0.00'      # tuned in game by the user (boot 16)

SET_REFS = [
    ('model', PORT + '.model'),
    ('first person[0]/first person model', PORT + '.render_model'),
    ('first person[0]/first person animations',
     # the port's OWN copy of fp_beam_rifle (h4_fp_graph.py: the overheat jerk fixed)
     'objects\\characters\\storm_fp\\weapons\\rifle\\fp_focus_rifle\\'
     'fp_focus_rifle.model_animation_graph'),
    # the PLASMA PISTOL's HUD: battery as a percentage + overheat. The Beam Rifle's (first
    # boot) counts 10 shots, which a 620-round battery cannot show. No scope overlay: zoom
    # itself is the weapon's, and the enhancer grafts the scope UI at patch time.
    ('hud screen reference', 'ui\\hud\\weapons\\covenant\\plasma_pistol\\plasma_pistol.cui_screen'),
    # NOT A REFERENCE: the Sentinel Beam is flagged "extension of parent" -- its gun was
    # part of the Sentinel's body. Held by the player, the weapon then draws as part of
    # the player, whose body first person never draws: invisible, shadow still cast, and
    # the beam on its markers hidden too, while the damage landed (boots 2-4). The Beam
    # Rifle does not carry it.
    ('clear-flag:item/object/flags', 'extension of parent'),
    # NPC-gun leftovers, set to the Beam Rifle's (boot 5 found them by a full field diff):
    # bounding radius 0 -- as part of its parent the gun used the Sentinel's bounds --
    # can cull the held weapon and the effects on its markers; the ready animation at
    # playback scale 0 freezes on its first, off-screen frame; and the weapon labels
    # its animations as a pistol 'bb' where the fp graph is the Beam Rifle's 'csr'.
    ('set:item/object/bounding radius', '0.3'),
    ('set:item/object/bounding offset', '0.215,0,0'),
    ('set:weapon ready 1st person animation playback scale', '1'),
    ('set:weapon name', 'csr'),
    ('set:weapon class', 'rifle'),
    # WHERE THE BEAM STARTS (boot 15: "appears in the centre of the screen"). Projectiles
    # leave the first-person camera; a barrel's "first person offset" (+x forward, +z up,
    # +y left) moves that spawn in FIRST PERSON only. The gun-origin flag used the gun's
    # WORLD position instead and did not help. Starting guess for the Focus Rifle's
    # muzzle; tune in a built map with h4_map_poke.py --fp-offset, then copy here.
    ('set-point:barrels[0]/first person offset', FP_OFFSET),
    ('set-point:barrels[1]/first person offset', FP_OFFSET),
]


#: The VISIBLE BEAM. Halo 4 draws a player's beam from the PROJECTILE: the Beam Rifle's
#: firing effect is only a sound and a light, and its projectile carries the beam as an
#: object attachment (fx\projectile). The Sentinel's beam is a first-person TRACER in its
#: firing effect instead -- a path no player ever exercised -- and it never drew: damage
#: landed, nothing showed (boots 2-8). Boot 9, poked: the port firing the Beam Rifle's
#: projectile DREW its beam. So the port's own projectile gets that attachment (the Beam
#: Rifle's pink-purple plasma; a Focus Rifle look can replace it later).
#
#: THE LOOK, TRIED AND RETIRED (boot 12): the Beam Rifle's streak is an "aligned ribbon",
#: one-sided and thin.
#: The Focus Rifle's own beam survives in Halo 4 only as the Sentinel's tracers -- Bungie
#: converted it there, H4 has no beam_system tags at all -- a "cross" (two ribbons),
#: double-sided: thick from any angle. But as a POINT-TO-POINT tracer in the firing effect
#: it never draws from the player's view (boots 2-8; "draw in first person pass" did not
#: change that, boot 11). So the port gets its OWN copy of that tracer with point-to-point
#: cleared -- it then trails its projectile like the Beam Rifle's -- inside its OWN copy
#: of the Beam Rifle's projectile effect, attached to the port's projectile -- and it drew
#: NOTHING: unpinned, a tracer whose length runs along the point-to-point profile has no
#: length. Back to the Beam Rifle's own streak (it draws); a thicker look will come from
#: widening a copy of THAT streak.
OWN_FX = 'objects\\weapons\\rifle\\focus_rifle\\fx\\'
OWN_TRACER = OWN_FX + 'beam'
OWN_PROJ_FX = OWN_FX + 'beam_projectile'
SB_TRACER = SB + 'fx\\friendly_beam\\projectile_3p'
BR_PROJ_FX = BR + 'fx\\projectile'
PROJ_REFS = [
    # the Focus Rifle's own beam look -- h4_beam_look.py builds it (run that FIRST): the
    # Sentinel's tracer (= the Focus Rifle's converted beam) with the Beam Rifle streak's
    # trail behaviour and Reach's focus_rifle_plasma palette
    ('add-attachment', OWN_FX + 'beam_projectile.effect'),
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
    print('model: imposter reference cleared %d time(s)' % clear_ref(model, 'impo', PORT))

    weap = h3tag.Tag(os.path.join(TAGS, DONOR + '.weapon'))
    for group, old, new in REPOINT:
        n = weap.repoint(old, new, group)
        print('weapon: %-4s %-66s x%d' % (group, new, n))
        if n < 1:
            raise SystemExit('the donor has no %s reference to %s' % (group, old))
    for field, path in SET_REFS:
        if field.startswith(('clear-flag:', 'set:', 'set-point:')):
            continue
        if not os.path.exists(os.path.join(TAGS, path)):
            raise SystemExit('%s -> %s does not exist' % (field, path))

    # the port's own beam, copied fresh from the donor's
    if a.write:
        for ext in ('projectile', 'damage_effect'):
            dst = os.path.join(TAGS, OWN_PROJ + '.' + ext)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(TAGS, SB_BEAM + '.' + ext), dst)
        proj = h3tag.Tag(os.path.join(TAGS, OWN_PROJ + '.projectile'))
        if proj.repoint(SB_BEAM, OWN_PROJ, 'jpt!') != 1:
            raise SystemExit('the beam projectile does not name its damage effect once')
        proj.save()
        print('own beam: %s.{projectile,damage_effect}' % OWN_PROJ)

    bad = [b for b in unresolved(model) + unresolved(weap) if a.write or b[1] != OWN_PROJ]
    if bad:
        raise SystemExit('unresolved references, nothing written:\n  ' +
                         '\n  '.join('%s %s' % b for b in bad))
    print('every existing reference resolves (%d in the weapon)' % len(weap.references()))
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

    # the NULL references, by field name, in an H4EK Blender process
    by_name(PORT + '.weapon', SET_REFS)
    by_name(OWN_PROJ + '.projectile', PROJ_REFS)


def by_name(tag, pairs):
    """Run h4_weapon_refs.py on one tag with (field, value) pairs; refuse on failure."""
    args = [BLENDER, '--background', '--python', os.path.join(HERE, 'h4_weapon_refs.py'),
            '--', tag]
    for field, value in pairs:
        args += [field, value]
    r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace')
    lines = [l for l in r.stdout.splitlines() if l.startswith(('   ', 'REFS'))]
    print('%s:' % tag.rsplit('\\', 1)[-1])
    print('\n'.join(lines) or r.stdout[-2000:])
    if not any(l.startswith('REFS OK') for l in lines):
        print(r.stdout[-1500:], r.stderr[-1500:])
        raise SystemExit('setting fields by name failed on %s' % tag)


if __name__ == '__main__':
    main()
