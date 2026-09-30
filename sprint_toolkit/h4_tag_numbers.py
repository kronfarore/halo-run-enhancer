r"""Halo 4 port, step 4: write the port's OWN numbers into its H4EK tags.

Same job as reach_saw_tag_numbers.py: the built map ships the ported weapon as it was in
its own game, and the patcher applies the suggested balance on top when the option is on.
For the Focus Rifle this is not cosmetic -- its beam is a copy of the Sentinel "friendly"
beam, which deals ZERO damage in Halo 4.

WHY MANAGEDBLAM HERE. HREK had no way to write a tag field, so the Reach port located
bytes by signature. H4EK's ManagedBlam CAN (Foundry writes material tags through it), so
this sets fields BY NAME, exactly as the tag names them, and reads every one back.

Run inside the portable Blender on F:, in the H4EK project (one kit per process):

    blender --background --python h4_tag_numbers.py            # dry run
    blender --background --python h4_tag_numbers.py -- --write

THE ROWS are the Halo 4 catalog entry's (make_port_catalog_h4.py), using each row's
`original` -- the weapon's own value -- and the balanced value only where there is no
original. Matching, measured on the port's weapon tag:
  * catalog field names are the tag's field names, case aside ("Heat Loss Per Second" is
    `heat loss per second`), found depth-first through structs;
  * a row's `block` ("Barrels", "Magazines") descends into that block, element `index`;
  * "X Max" is the second half of the RealBounds field X (`magnification range` = 3.5,9.5);
  * values go in DISPLAY units, as the tag shows them (angles in degrees).
A row whose field matches NOTHING or MORE THAN ONE place is reported and skipped, never
guessed (the patcher still writes it into the MAP by its plugin name). A tag is saved
only when every read-back so far agrees.
"""
import importlib
import json
import os
import sys

import bpy

KEY = 'bl_ext.user_default.io_scene_foundry'
HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(os.path.dirname(HERE), 'weapon_ports_catalog.json')
WEAPON = 'Focus Rifle'
H4EK_TAGS = r'F:\SteamLibrary\steamapps\common\H4EK\tags'
EXT = {'weap': 'weapon', 'proj': 'projectile', 'jpt!': 'damage_effect'}


def fields_named(fields, name, path=''):
    """Every (path, field) whose name is `name`, depth-first through structs only."""
    out = []
    for f in fields:
        ft = str(f.FieldType)
        if f.FieldName.lower() == name:
            out.append((path + f.FieldName, f))
        if ft == 'Struct':
            out += fields_named(f.Elements[0].Fields, name, path + f.FieldName + '/')
    return out


def block_named(fields, name):
    for f in fields:
        ft = str(f.FieldType)
        if ft == 'Block' and f.FieldName.lower() == name:
            return f
        if ft == 'Struct':
            got = block_named(f.Elements[0].Fields, name)
            if got is not None:
                return got
    return None


def locate(tag, row):
    """[(path, field, component)] for a row, or a string saying why not."""
    name = row['field'].lower()
    component = None
    scopes = [('', tag.Fields)]
    if row.get('block'):
        blk = block_named(tag.Fields, row['block'].lower())
        if blk is None:
            return 'no block %r' % row['block']
        idx = row.get('index', 0) or 0
        els = range(blk.Elements.Count) if idx == 'all' else [idx]
        scopes = [('%s[%d]/' % (blk.FieldName, i), blk.Elements[i].Fields) for i in els
                  if i < blk.Elements.Count]
    out = []
    for prefix, fields in scopes:
        hits = fields_named(fields, name, prefix)
        comp = None
        if not hits and name.endswith(' max'):
            hits, comp = fields_named(fields, name[:-4], prefix), 1
        elif hits and str(hits[0][1].FieldType).endswith('Bounds'):
            comp = 0
        if len(hits) != 1:
            return '%d matches for %r under %r' % (len(hits), row['field'], prefix or 'root')
        out.append((hits[0][0], hits[0][1], comp))
        component = comp
    return out


def read(field, comp=None):
    if not hasattr(field, 'GetStringData'):          # enums carry an index, not text
        return str(field.Value)
    v = field.GetStringData()
    return list(v)[comp] if comp is not None else v


def set_value(field, comp, value):
    # integer fields refuse "2.0" and keep their old value; the catalog stores 2.0
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if not hasattr(field, 'GetStringData'):
        field.Value = int(value)
        return str(field.Value)
    if comp is None:
        field.SetStringData(str(value))
        return field.GetStringData()
    parts = list(field.GetStringData())
    parts[comp] = str(value)
    field.SetStringData(parts)
    return list(field.GetStringData())[comp]


def main(write):
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

    cat = json.load(open(CATALOG, encoding='utf-8'))
    entry = next(e for e in cat['Halo 4'] if e['weapon'] == WEAPON)
    by_tag = {}
    for r in entry['balance']:
        by_tag.setdefault((r['class'], r['tag']), []).append(r)

    problems = skipped = 0
    for (cls, rel), rows in sorted(by_tag.items()):
        path = rel + '.' + EXT[cls]
        print('\n%s  (%d rows)' % (path, len(rows)))
        # absolute: binds H4EK's ManagedBlam whoever launched this (see h4_weapon_refs.py)
        with T(path=os.path.join(H4EK_TAGS, path)) as t:
            kit = str(getattr(mb, 'mb_path', '') or '')
            if 'h4ek' not in kit.lower():
                raise SystemExit('ManagedBlam is bound to %r, not H4EK' % kit)
            changed = False
            for r in rows:
                value = r['original'] if r.get('original') is not None else r['value']
                where = locate(t.tag, r)
                if isinstance(where, str):
                    print('   SKIP %-30s %s' % (r['field'], where))
                    skipped += 1
                    continue
                for p, f, comp in where:
                    before = read(f, comp)
                    got = set_value(f, comp, value)
                    ok = abs(float(got) - float(value)) < 1e-4 * max(1.0, abs(float(value)))
                    print('   %-4s %-44s %s -> %s' % ('ok' if ok else 'BAD', p + ('' if comp is None else '[%d]' % comp), before, got))
                    if not ok:
                        problems += 1
                    changed = True
            t.tag_has_changes = bool(write and changed and not problems)
    print('\n%d skipped (not in the tag by that name; the patcher still writes them into the '
          'map by plugin name)' % skipped)
    print('%d problem(s); %s' % (problems, 'SAVED' if write and not problems else
                                   'not saved' + ('' if write else ' (dry run -- pass --write)')))


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    main('--write' in argv)
