"""Where the Assembly plugin XMLs live.

The GUI stores this as the `assembly_plugins_dir` setting, so a user who moves
Assembly repoints it once and the Enhancer follows. The standalone CLI tools had no
such luck: each hardcoded the install path it was written against, and when Assembly
moved off the Steam drive they all pointed at nothing.

Mostly that fails loudly. `validate_halo_json.py` is the exception and the reason this
module exists -- it skips its resolution checks when the directory is missing and
still prints "0 problem(s)", so a stale path turns its most valuable pass into a
silent no-op that reads like a clean bill of health.

Resolution order, first hit wins:
    1. $ASSEMBLY_PLUGINS
    2. `assembly_plugins_dir` in settings.json beside this file (what the GUI writes)
    3. the known install locations
"""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))

# Known locations, most authoritative first. Assembly ships inside HCEEK, and the
# whole mod-tool set now lives on F: -- the loose E: copy is a leftover from the move
# and the C: path is where they used to be, so both stay only as fallbacks.
_ASSEMBLY = r"\Assembly-1-2023-11-29-1702446457\Plugins"
CANDIDATES = (
    r"F:\SteamLibrary\steamapps\common\HCEEK" + _ASSEMBLY,
    r"E:\Assembly-1-2023-11-29-1702446457\Plugins",
    r"C:\Program Files (x86)\Steam\steamapps\common\HCEEK" + _ASSEMBLY,
)


def _from_settings():
    try:
        with open(os.path.join(_HERE, 'settings.json'), encoding='utf-8') as f:
            v = json.load(f).get('assembly_plugins_dir')
        return v or None
    except Exception:
        return None


def plugins_dir(required=False):
    """The plugin directory, or the best guess when none of the candidates exist.

    `required=True` raises instead of guessing, for callers whose whole job depends
    on the plugins being there."""
    for p in (os.environ.get('ASSEMBLY_PLUGINS'), _from_settings()) + CANDIDATES:
        if p and os.path.isdir(p):
            return p
    if required:
        raise SystemExit(
            'Assembly plugins not found. Set ASSEMBLY_PLUGINS, or fix '
            'assembly_plugins_dir in settings.json. Tried:\n  '
            + '\n  '.join(str(p) for p in
                          (os.environ.get('ASSEMBLY_PLUGINS'), _from_settings())
                          + CANDIDATES if p))
    return CANDIDATES[-1]


PLUGINS = plugins_dir()
