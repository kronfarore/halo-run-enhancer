r"""Which Editing Kit the port tools work in -- Halo 3's, ODST's, or Reach's.

Halo 3 and Halo 3: ODST are the same engine, and the port measures out nearly the same:
the Assault Rifle's first-person and world skeletons are byte-identical between the two
kits (node list, default transforms, every marker), and so are its projectile and damage
effect tags. So the whole Halo 3 pipeline runs against either kit, and the only thing
that has to change per run is which one.

    set PORT_EK=odst        (cmd)         -- everything after this targets H3ODSTEK
    set PORT_EK=reach                     -- HREK
    set PORT_EK=h3                        -- back to Halo 3, which is also the default

A full directory path works too, for a kit somewhere else.

REACH IS A THIRD KIT, NOT A SECOND ODST. It shares the toolchain -- same version 8200
JMS, same three string verbs, same font package format and codec -- and differs in ways
that are recorded next to the tool that cares. The two that bite hardest:

  * a weapon has NO first-person render model. The `first person` block pairs the
    weapon's OWN WORLD MODEL with a per-species animation graph, so a port builds one
    model, not two, and retimes two graphs (Spartan and Elite), not one.
  * `tool.exe` wants ABSOLUTE tag paths where H3EK takes relative ones.

WHAT IS NOT THE SAME between kits, and therefore lives with the tool that cares:

  * the first-person ANIMATION GRAPH. Halo 3's Assault Rifle names two, the Master
    Chief's and the Dervish's; ODST's names `odst_recon` twice; Reach's names one per
    species and keeps them in the CHARACTER tree.
  * the HUD SHEETS. `ballistic_meters` is 20 sprites in Halo 3 and 18 in ODST, and the
    free slots differ; `weapon_scematics` is 26 against 27, and ODST's three spare
    sequences are 8x8 stubs rather than full-size art.
  * the LOCALIZATION file, which is named per game.

Nothing here reads a map: this is about tag SOURCE, so it stays out of the patcher.

USE `per_kit()` FOR ANYTHING THAT DIFFERS. A plain `X if IS_ODST else Y` silently hands
a third kit the Halo 3 answer, which is the shape of several bugs this project has
already paid for -- a vacuous HUD check that compared None to None, a balance table that
returned nothing for ODST, an ammo step that was Halo 1 only. `per_kit` raises instead.
"""
import os

B = os.sep
COMMON = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common')
KITS = {'h3': 'H3EK', 'halo3': 'H3EK', 'halo 3': 'H3EK',
        'odst': 'H3ODSTEK', 'h3odst': 'H3ODSTEK', 'halo 3: odst': 'H3ODSTEK',
        'reach': 'HREK', 'hr': 'HREK', 'haloreach': 'HREK', 'halo reach': 'HREK'}
GAMES = {'H3EK': 'Halo 3', 'H3ODSTEK': 'Halo 3: ODST', 'HREK': 'Halo Reach'}
#: short tag per kit, for anything that keeps per-game copies on disk
SHORTS = {'H3EK': 'h3', 'H3ODSTEK': 'odst', 'HREK': 'reach'}
#: The installed game folder under the MCC root, which is where the LIVE font packages
#: and the localization files live. Each game has its OWN, and they are not the same
#: files: ODST's font_package_icon.bin is 294912 bytes against Halo 3's and Reach's
#: 245760, and a glyph added to one is not in the others.
MCC_GAMES = {'H3EK': 'halo3', 'H3ODSTEK': 'halo3odst', 'HREK': 'haloreach'}


def kit_dir(name=None):
    """The Editing Kit directory `name` asks for -- a short name, or a path."""
    name = (name or os.environ.get('PORT_EK') or 'h3').strip()
    if os.sep in name or ':' in name[1:]:
        if not os.path.isdir(name):
            raise SystemExit('no such Editing Kit: %s' % name)
        return name
    folder = KITS.get(name.lower())
    if folder is None:
        raise SystemExit('unknown kit %r -- one of %s, or a path'
                         % (name, sorted(set(KITS))))
    return os.path.join(COMMON, folder)


EK = kit_dir()
KIT = os.path.basename(EK)
TAGS = os.path.join(EK, 'tags')
DATA = os.path.join(EK, 'data')
TOOL = os.path.join(EK, 'tool.exe')
GAME = GAMES.get(KIT, 'Halo 3')
IS_H3 = GAME == 'Halo 3'
IS_ODST = GAME == 'Halo 3: ODST'
IS_REACH = GAME == 'Halo Reach'
MCC_GAME = MCC_GAMES.get(KIT, 'halo3')
SHORT = SHORTS.get(KIT, 'h3')

#: The port's weapon tag, the same path in all three games.
#:
#: It was briefly PADDED in ODST to 61 characters, to fit an in-place overwrite of a
#: weapon palette entry. That route is abandoned: it puts the tag in the map and gathers
#: none of its geometry (see odst_saw_place.py), so the padding bought nothing and the
#: name is back to matching Halo 3's.
SAW_WEAPON = os.sep.join(['objects', 'weapons', 'rifle', 'saw', 'saw'])


def banner():
    """One line naming the kit, so a run can never be ambiguous about which it hit."""
    return '%s  (%s)' % (KIT, GAME)


_UNSET = object()


def per_kit(h3=_UNSET, odst=_UNSET, reach=_UNSET, what='this value'):
    """Pick a per-kit value, and REFUSE to guess for a kit that has none.

    The point is the refusal. A kit whose value has not been measured raises here, at
    the one place that knows the kit, rather than quietly receiving Halo 3's answer and
    producing a build that looks right and is not.
    """
    value = {'h3': h3, 'odst': odst, 'reach': reach}[SHORT]
    if value is _UNSET:
        raise SystemExit(
            '%s is not established for %s.\n'
            'It has NOT been defaulted to another kit, because that is how a port ends '
            'up\nlooking correct and being wrong. Measure it, then add it at the '
            'per_kit() call.' % (what[0].upper() + what[1:], banner()))
    return value


#: The font in maps/fonts/font_package_icon*.bin that draws the pickup prompt.
#:
#: Halo 3's packages hold four fonts and the HUD one is index 2; ODST's hold FIVE, having
#: inserted fixedsys-pda13, so its HUD font is index 3. Reach's hold SIX and its HUD font
#: is index 3 as well -- but for a different reason, and Halo 3's 2 would be wrong there
#: in a way that is easy to miss: Reach's index 2 is fixedsys_hud-number, a separate face
#: for the ammo counter that Halo 3 does not have. Reach's package NAMES its fonts in the
#: header, so this one was read rather than inferred:
#:
#:     0 fixedsys-9   1 fixedsys_ui-title   2 fixedsys_hud-number
#:     3 fixedsys_hud-15   4 fixedsys_ui-15   5 fixedsys_ui-16
HUD_FONT = per_kit(h3=2, odst=3, reach=3, what='the HUD font index')


if __name__ == '__main__':
    print(banner())
    print('  tags %s' % TAGS)
    print('  tool %s  %s' % (TOOL, 'present' if os.path.exists(TOOL) else 'MISSING'))
    print('  mcc game folder %s, short %s, HUD font %d' % (MCC_GAME, SHORT, HUD_FONT))
