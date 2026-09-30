r"""Check (and fix) the Foundry settings every Reach Foundry script relies on.

Run inside the portable Blender on F: (Foundry 1.9.19 needs Blender 5.2+):

    blender --background --python foundry_setup.py            # report
    blender --background --python foundry_setup.py -- --fix   # switch tool patches OFF
    blender --background --python foundry_setup.py -- --add F:\SteamLibrary\steamapps\common\H4EK

What must hold:
  * a Foundry PROJECT pointing at HREK (F:\SteamLibrary\steamapps\common\HREK), current;
  * `allow_tool_patches` OFF. Foundry ships with it ON, which lets it modify HREK's
    tool.exe. The build scripts refuse to export when it is on; this is how it goes off.

The portable install keeps its preferences in its own `portable` folder, so a fresh
Blender unzip needs this run once (after adding the HREK project in Foundry's prefs).
"""
import sys

import bpy

KEY = 'bl_ext.user_default.io_scene_foundry'
EK = r'F:\SteamLibrary\steamapps\common\HREK'

p = bpy.context.preferences.addons[KEY].preferences

# ADD A KIT. Foundry's own operator ends in a UI redraw that has no area in background
# mode, so its two list helpers are called directly. One kit per Blender PROCESS: Foundry
# loads that kit's ManagedBlam and needs a restart to switch -- which is why a
# cross-game port runs one process per kit (import in one, export in the other).
if '--add' in sys.argv:
    import importlib
    prefs_mod = importlib.import_module(KEY + '.utils')
    new = sys.argv[sys.argv.index('--add') + 1].rstrip('\/')
    have = prefs_mod.read_projects_list() or []
    if new.lower() not in [h.lower() for h in have]:
        prefs_mod.write_projects_list(have + [new])
        prefs_mod.setup_projects_list()
        bpy.ops.wm.save_userpref()
        print('added project', new)
    else:
        print('project already listed', new)
found = False
for i, pr in enumerate(p.projects):
    fields = {a: getattr(pr, a) for a in dir(pr)
              if not a.startswith(('_', 'bl_', 'rna'))
              and isinstance(getattr(pr, a), (str, int, float, bool))}
    print('project %d: %s' % (i, fields))
    found |= any(isinstance(v, str) and v.rstrip('\/').lower() == EK.lower()
                 for v in fields.values())
print('current project: %r' % p.current_project)
print('HREK project present: %s' % found)
print('allow_tool_patches: %s' % p.allow_tool_patches)

if '--fix' in sys.argv and p.allow_tool_patches:
    p.allow_tool_patches = False
    bpy.ops.wm.save_userpref()
    print('allow_tool_patches -> False (saved)')
if not found:
    print('ADD the HREK project in Foundry preferences before running any Reach Foundry script')
