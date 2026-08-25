"""Install-specific paths for the sprint toolkit — EDIT THESE for your machine.

The only things that vary per setup are your HCEEK (Halo CE MCC Editing Kit) and
Halo: MCC install folders, and where the Assembly plugin XMLs live. `TOOL` is
auto-detected as the Enhancer repo this toolkit sits in, so you normally don't
touch it. Everything else in the toolkit imports its paths from here.
"""
import os

# --- edit these ---------------------------------------------------------------
# Your Halo CE MCC Editing Kit (HCEEK): contains tool.exe, tags\, data\, maps\.
HCEEK = r'F:\SteamLibrary\steamapps\common\HCEEK'

# Your Halo: The Master Chief Collection install: deploy writes to halo1\maps here.
MCC = r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection'

# The Assembly plugin XMLs (ship with Assembly / HCEEK): scnr.xml, matg.xml, weap.xml.
PLUGINS = HCEEK + r'\Assembly-1-2023-11-29-1702446457\Plugins'

# --- derived (usually leave alone) --------------------------------------------
# Halo 1 plugin subdir order (MCC override first) for resolving tag fields.
HALO1_SUBDIRS = ['Halo1MCC', 'Halo1']

# The Enhancer repo (for halo_patch / halo_map) — parent of this toolkit folder.
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCNR_XML = os.path.join(PLUGINS, 'Halo1', 'scnr.xml')
TOOL_EXE = os.path.join(HCEEK, 'tool.exe')

# The compiled-into-every-level script file. sprint.hsc is (re)installed into this
# by install_script.py before each build, so the built maps always carry the
# current sprint logic. tool.exe reads it from data\ at build time.
GLOBAL_SCRIPTS = os.path.join(HCEEK, 'data', 'global_scripts.hsc')
