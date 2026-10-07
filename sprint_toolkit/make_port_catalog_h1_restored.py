r"""weapon_ports_catalog.json entries for Halo 1's RESTORED weapons -- the Elites' Energy
Sword and the Grunts' fuel rod made pickable (h1_pickable_weapons.py, PORTING.md "Halo 1:
enemy-only weapons made pickable") -- and the Sentinel Beam.

Since phase 0 of H1_PORT_PLAN.md (2026-10-07) the entries live in the weapons' own configs
(ports_h1/energy_sword.py, fuel_rod.py, sentinel_beam.py, section 'catalog') and the writer
is make_port_catalog_h1_ports.py, generic for every Halo 1 port. This file stays as the
old command name for those three.

They are not carried from another game: 'source' is Halo 1, the weapon tags keep their
stock paths. The STOCK baselines carry the AI-only versions under those same paths, so
each entry names `requires` -- a tag only the player build has -- and the enhancer counts
the port as present on a level only when its weap AND every `requires` tag are in the map
(the enhancer session's rule, cb8413d). The fuel rod is catalogued as 'Flak Cannon' and the
sword as 'Energy Blade', the names halo.json uses in Halo 2-4, so a run carries them across
games.

    python make_port_catalog_h1_restored.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_port_catalog_h1_ports  # noqa: E402

RESTORED = ['energy_sword', 'fuel_rod', 'sentinel_beam']


if __name__ == '__main__':
    make_port_catalog_h1_ports.main(RESTORED)
