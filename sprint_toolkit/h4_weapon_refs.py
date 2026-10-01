r"""Set tag REFERENCE fields by name in an H4EK tag, through ManagedBlam -- for references
that are NULL in a donor, where there are no bytes to repoint.

Run inside the portable Blender on F: (h4_make_port_weapon.py calls it):

    blender --background --python h4_weapon_refs.py -- <tag path> <field> <value> [<field> <value> ...]

`field` is a path of field names as the tag names them, case aside: `model`, or
`first person[0]/first person model` (block name, element index, field). Plain names
are found depth-first through structs. `value` is a tag path WITH its extension.
Every reference is read back; the tag is saved only when all of them match.
Prints `REFS OK` on success.
"""
import importlib
import os
import re
import sys

import bpy

KEY = 'bl_ext.user_default.io_scene_foundry'
H4EK_TAGS = r'F:\SteamLibrary\steamapps\common\H4EK\tags'


def find(fields, name):
    """(field) named `name` depth-first through structs, or None."""
    for f in fields:
        if f.FieldName.lower() == name:
            return f
        if str(f.FieldType) == 'Struct':
            got = find(f.Elements[0].Fields, name)
            if got is not None:
                return got
    return None


def resolve(tag, path):
    fields = tag.Fields
    parts = path.lower().split('/')
    for part in parts[:-1]:
        m = re.match(r'(.+)\[(\d+)\]$', part)
        blk = find(fields, m.group(1)) if m else None
        if blk is None or str(blk.FieldType) != 'Block' or blk.Elements.Count <= int(m.group(2)):
            raise SystemExit('no block element %r' % part)
        fields = blk.Elements[int(m.group(2))].Fields
    f = find(fields, parts[-1])
    if f is None or str(f.FieldType) != 'Reference':
        raise SystemExit('no reference field %r' % path)
    return f


def same_value(got, want):
    """'0.3' == '0.3', '0.215,0,0' == '0.215,0,0' numerically, names exactly."""
    a, b = [x.strip() for x in got.split(',')], [x.strip() for x in want.split(',')]
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        try:
            if abs(float(x) - float(y)) > 1e-5:
                return False
        except ValueError:
            if x != y:
                return False
    return True


def resolve_any(tag, path):
    """Like resolve(), for a field of any type (a flags field here)."""
    fields = tag.Fields
    parts = path.lower().split('/')
    for part in parts[:-1]:
        f = find(fields, part)
        if f is None or str(f.FieldType) != 'Struct':
            raise SystemExit('no struct %r' % part)
        fields = f.Elements[0].Fields
    f = find(fields, parts[-1])
    if f is None:
        raise SystemExit('no field %r' % path)
    return f


def main(argv):
    rel, pairs = argv[0], list(zip(argv[1::2], argv[2::2]))
    mb = importlib.import_module(KEY + '.managed_blam')
    # BIND H4EK FIRST, from an absolute path inside it: mb_init switches the scene to the
    # project that owns the file. Setting scene_project by hand started ManagedBlam for
    # the PREVIOUS project (HREK) when launched from another process, and ManagedBlam
    # cannot change kits within a process.
    # AND MAKE SURE THIS PROCESS KNOWS H4EK. Launched from the Microsoft Store Python,
    # Blender sees a VIRTUALISED %APPDATA% -- a different copy of Foundry's project list,
    # one without H4EK -- so the switch above silently stays on HREK. Registering it here
    # is harmless when it is already listed.
    u = importlib.import_module(KEY + '.utils')
    kit = os.path.dirname(H4EK_TAGS)
    have = u.read_projects_list() or []
    if kit.lower() not in [h.rstrip('\/').lower() for h in have]:
        u.write_projects_list(have + [kit])
        u.setup_projects_list()
    if not mb.mb_active:
        mb.mb_init(os.path.join(H4EK_TAGS, 'globals', 'globals.globals'))

    class T(mb.Tag):
        pass

    # ABSOLUTE path: mb_init switches to the project that owns the file. A relative one
    # binds whatever project the context resolves first -- HREK, when launched from
    # another process -- and the scene_project set above does not reliably win.
    with T(path=os.path.join(H4EK_TAGS, rel)) as t:
        # ONE KIT PER PROCESS, and it must be H4EK. Launched from another process,
        # Foundry once bound HREK's ManagedBlam instead -- it then parses the H4 tag with
        # Reach's definitions, shows Reach paths as the 'before' values and cannot find
        # `hud screen reference`. Refuse rather than edit through the wrong kit.
        kit = str(getattr(mb, 'mb_path', '') or '')
        print('   kit %s' % kit)
        if 'h4ek' not in kit.lower():
            raise SystemExit('ManagedBlam is bound to %r, not H4EK' % kit)
        ok = True
        for field, value in pairs:
            if field == 'add-attachment':
                # an object ATTACHMENT (block `attachments`, element field `type`) -- how
                # a Halo 4 projectile carries its visible beam (the Beam Rifle's
                # projectile: one attachment, its fx\projectile effect)
                att = resolve_any(t.tag, 'attachments')
                have = [t.get_path_str(att.Elements[i].SelectField('type').Path).lower()
                        for i in range(att.Elements.Count)]
                if value.lower() in have:
                    print('   ok   add-attachment %s (already there)' % value)
                    continue
                e = att.AddElement()
                e.SelectField('type').Path = t._TagPath_from_string(value)
                got = t.get_path_str(e.SelectField('type').Path)
                good = got.lower() == value.lower()
                ok &= good
                print('   %-4s add-attachment %s' % ('ok' if good else 'BAD', got))
                continue
            if field.startswith('set:'):
                # 'set:<field path>' <value>: a plain field -- number, string id or enum
                f = resolve_any(t.tag, field[len('set:'):])
                ft = str(f.FieldType)
                if 'Enum' in ft:
                    names = [i.EnumName for i in f.Items]
                    was = names[f.Value] if 0 <= f.Value < len(names) else f.Value
                    f.Value = names.index(value)
                    now = names[f.Value]
                else:
                    was = f.GetStringData()
                    parts = value.split(',')
                    f.SetStringData(parts if len(parts) > 1 else value)
                    now = f.GetStringData()
                now_s = now if isinstance(now, str) else ','.join(now)
                was_s = was if isinstance(was, str) else (','.join(was) if hasattr(was, '__iter__') else str(was))
                good = same_value(now_s, value)
                ok &= bool(good)
                print('   %-4s %-44s %s -> %s' % ('ok' if good else 'BAD', field, was_s, now_s))
                continue
            if field.startswith('clear-flag:'):
                # 'clear-flag:<flags field path>' <flag name>: clear one bit by name
                f = resolve_any(t.tag, field[len('clear-flag:'):])
                was = f.TestBit(value)
                f.SetBit(value, False)
                good = not f.TestBit(value)
                ok &= good
                print('   %-4s %-44s %s: %s -> %s' % ('ok' if good else 'BAD', field, value,
                                                    was, f.TestBit(value)))
                continue
            f = resolve(t.tag, field)
            before = t.get_path_str(f.Path)
            f.Path = t._TagPath_from_string(value)
            after = t.get_path_str(f.Path)
            good = after.lower() == value.lower()
            ok &= good
            print('   %-4s %-44s %s -> %s' % ('ok' if good else 'BAD', field, before or '(null)', after))
        t.tag_has_changes = ok
    print('REFS OK' if ok else 'REFS FAILED -- not saved')


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1:])
