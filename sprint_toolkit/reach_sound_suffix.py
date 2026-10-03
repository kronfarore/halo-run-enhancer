r"""Set the `fmod bank suffix` of Reach sound tags (HREK ManagedBlam, in Blender).

`tool reimport-sounds` rewrites a sound's encodings but CLEARS its bank suffix, even with
-bank:<suffix> (measured 2026-10-03, PC-only test); this puts it back.

    blender --background --python reach_sound_suffix.py -- <suffix> <sound tag> [...]
(tag paths relative to HREK\tags, with or without .sound; suffix '' clears it)
"""
import importlib
import os
import sys

import bpy  # noqa: F401

KEY = 'bl_ext.user_default.io_scene_foundry'
TAGS = r'F:\SteamLibrary\steamapps\common\HREK\tags'


def main(argv):
    suffix, tags = argv[0], argv[1:]
    mb = importlib.import_module(KEY + '.managed_blam')
    if not mb.mb_active:
        mb.mb_init(os.path.join(TAGS, 'globals', 'globals.globals'))
    if 'hrek' not in str(mb.mb_path).lower():
        raise SystemExit('ManagedBlam is bound to %r, not HREK' % mb.mb_path)

    class T(mb.Tag):
        pass
    ok = True
    for rel in tags:
        rel = rel if rel.endswith('.sound') else rel + '.sound'
        with T(path=os.path.join(TAGS, rel)) as t:
            f = t.tag.SelectField('fmod bank suffix')
            was = f.GetStringData()
            f.SetStringData(suffix)
            now = f.GetStringData()
            t.tag_has_changes = True
            ok &= now == suffix
            print('   %-50s fmod bank suffix %r -> %r' % (rel, was, now))
    print('SUFFIX OK' if ok else 'SUFFIX FAILED')


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1:])
