r"""Which Editing Kit the Halo 3 port tools work in -- Halo 3's, or ODST's.

Halo 3 and Halo 3: ODST are the same engine, and the port measures out nearly the same:
the Assault Rifle's first-person and world skeletons are byte-identical between the two
kits (node list, default transforms, every marker), and so are its projectile and damage
effect tags. So the whole Halo 3 pipeline runs against either kit, and the only thing
that has to change per run is which one.

    set PORT_EK=odst        (cmd)         -- everything after this targets H3ODSTEK
    set PORT_EK=h3                        -- back to Halo 3, which is also the default

A full directory path works too, for a kit somewhere else.

WHAT IS NOT THE SAME, and therefore lives with the tool that cares rather than here:

  * the first-person ANIMATION GRAPH. Halo 3's Assault Rifle names two, the Master
    Chief's and the Dervish's; ODST's names `odst_recon` twice. So a port clones two
    graphs in one game and one in the other.
  * the HUD SHEETS. `ballistic_meters` is 20 sprites in Halo 3 and 18 in ODST, and the
    free slots differ; `weapon_scematics` is 26 against 27, and ODST's three spare
    sequences are 8x8 stubs rather than full-size art.
  * the LOCALIZATION file, which is named per game.

Nothing here reads a map: this is about tag SOURCE, so it stays out of the patcher.
"""
import os

B = os.sep
COMMON = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common')
KITS = {'h3': 'H3EK', 'halo3': 'H3EK', 'halo 3': 'H3EK',
        'odst': 'H3ODSTEK', 'h3odst': 'H3ODSTEK', 'halo 3: odst': 'H3ODSTEK'}
GAMES = {'H3EK': 'Halo 3', 'H3ODSTEK': 'Halo 3: ODST'}


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
TAGS = os.path.join(EK, 'tags')
DATA = os.path.join(EK, 'data')
TOOL = os.path.join(EK, 'tool.exe')
GAME = GAMES.get(os.path.basename(EK), 'Halo 3')
IS_ODST = GAME == 'Halo 3: ODST'
#: The installed game folder under the MCC root, which is where the LIVE font packages
#: and the localization files live. ODST has its own, and they are NOT the same files:
#: its font_package_icon.bin is 294912 bytes against Halo 3's 245760.
MCC_GAME = 'halo3odst' if IS_ODST else 'halo3'
#: Halo 3's short tag, for anything that keeps per-game copies on disk.
SHORT = 'odst' if IS_ODST else 'h3'


def banner():
    """One line naming the kit, so a run can never be ambiguous about which it hit."""
    return '%s  (%s)' % (os.path.basename(EK), GAME)


if __name__ == '__main__':
    print(banner())
    print('  tags %s' % TAGS)
    print('  tool %s  %s' % (TOOL, 'present' if os.path.exists(TOOL) else 'MISSING'))
