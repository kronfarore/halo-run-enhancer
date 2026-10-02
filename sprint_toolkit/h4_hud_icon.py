r"""Point the port's own HUD screen's weapon icon at the port's own icon string.

The player HUD draws its weapon icon with a TEXT component, `weapon_icon_text`, whose
string id names a line in ui\strings\weapons -- the Plasma Pistol screen the port copies
said `plasma_pistol_icon` ("&plasma_pistol"), so the HUD showed the Plasma Pistol's
icon (boot 20). Every resolution overlay carries its own copy of the component; all are
repointed to `focus_rifle_icon` (h4_port_messages.py adds it, with the port's glyph).

    blender --background --python h4_hud_icon.py -- <screen tag path> <string id>
"""
import importlib
import os
import sys

import bpy

KEY = 'bl_ext.user_default.io_scene_foundry'
H4EK_TAGS = r'F:\SteamLibrary\steamapps\common\H4EK\tags'
COMPONENT = 'weapon_icon_text'


def main(rel, sid):
    mb = importlib.import_module(KEY + '.managed_blam')
    if not mb.mb_active:
        mb.mb_init(os.path.join(H4EK_TAGS, 'globals', 'globals.globals'))
    if 'h4ek' not in str(mb.mb_path).lower():
        raise SystemExit('ManagedBlam is bound to %r, not H4EK' % mb.mb_path)

    class T(mb.Tag):
        pass

    n = 0
    with T(path=os.path.join(H4EK_TAGS, rel)) as t:
        system = t.tag.SelectField('system').Elements[0]
        overlays = system.SelectField('overlays')
        for i in range(overlays.Elements.Count):
            comps = overlays.Elements[i].SelectField('components')
            for j in range(comps.Elements.Count):
                c = comps.Elements[j]
                if c.SelectField('name').GetStringData() != COMPONENT:
                    continue
                props = c.SelectField('property values').Elements[0].SelectField('string_id properties')
                for k in range(props.Elements.Count):
                    v = props.Elements[k].SelectField('value')
                    was = v.GetStringData()
                    v.SetStringData(sid)
                    print('   overlay %d %s: %s -> %s' % (i, COMPONENT, was, v.GetStringData()))
                    n += 1
        t.tag_has_changes = n > 0
    print('HUDICON OK %d' % n if n else 'HUDICON NONE')


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:]
    main(argv[0], argv[1])
