r"""Add a tag to a Halo 4 scenario's `dz_enhancer` designer zone, headless (ManagedBlam).

The Halo 4 counterpart of odst_dz_enhancer.py, for one item at a time. Written for the
Sprint equipment (user, 2026-11-27: "Sprint should be made available in all H4 maps"):
`objects\equipment\sprint\sprint` is in H4EK and in Dawn's dz_enhancer, and in no other
mission's. Halo 4 has no patch-time residency fix (writing its pool bits crashes the
game, h4_pools.py), so the Editing Kit zone is the whole mechanism.

HOW TOOL BUILDS A ZONE (measured against all eight built baselines, 2026-11-27)
  * The cache's palette of a kind is the scenario TREE's palettes merged depth-first:
    the main scenario's palette as it is, then each child scenario (child order,
    recursing into its own children) adding the entries no EARLIER scenario had --
    repeats inside one scenario are kept (Midnight's m90_coldant lists the energy-drain
    grenade twice, and so does the build). This reproduces all eight built equipment
    palettes in exact order; breadth-first does not (Forerunner, Delta).
  * A designer zone's per-kind lists (`equipment`, `weapon`, ...) are indices into that
    merged palette, and are what the build keeps; an index past the end is dropped.
    `references` is the Sapien-side list of the same tags -- a reference with no palette
    entry did NOT reach the m020 build.
So an item is added in three parts, each only if missing:
  1. a palette entry in the LAST scenario of the depth-first walk (follow the last child
     down to a leaf), which puts it at the end of the merged palette and shifts no
     existing index -- the main palette is left alone, appending there would;
  2. a `references` entry in dz_enhancer;
  3. dz_enhancer's index for it (= the merged palette's size before it). Infinity,
     Shutdown, Liftoff and Midnight already list exactly that index: an entry past their
     old palette that their builds dropped.
If dz_enhancer is later edited in Sapien, run this again; it reports "already holds it"
or adds what is missing. The proof is the built map (halo_patch.h4_enhancer_items).

Run inside the portable Blender (Foundry's ManagedBlam, H4EK bound first):

    blender --background --python h4_dz_add.py                     # dry run, all eight
    blender --background --python h4_dz_add.py -- --write          # write (backs up first)
    blender --background --python h4_dz_add.py -- --maps m020,m60_rescue
    blender --background --python h4_dz_add.py -- --tag <rel path with extension> --kind weapon

Then rebuild each changed map (tool build-cache-file environments\solo\<m>\<m> pc) and
install the build as the patch baseline, E:\HaloBaselines\halo4\maps\<m>.map.
Refuses to write while Sapien / Foundation / tool / Guerilla run (they hold the tags).
Output goes to sprint_toolkit/reports/h4_dz_add.txt as well as stdout.
"""
import datetime
import importlib
import os
import shutil
import subprocess
import sys

KEY = 'bl_ext.user_default.io_scene_foundry'
HERE = os.path.dirname(os.path.abspath(__file__))
H4EK = r'F:\SteamLibrary\steamapps\common\H4EK'
TAGS = os.path.join(H4EK, 'tags')
MAPS = ('m10_crash', 'm020', 'm30_cryptum', 'm40_invasion', 'm60_rescue', 'm70_liftoff',
        'm80_delta', 'm90_sacrifice')
ZONE = 'dz_enhancer'
DEFAULT_TAG = r'objects\equipment\sprint\sprint.equipment'
PALETTE = {'equipment': 'equipment palette', 'weapon': 'weapon palette'}
BACKUP_ROOT = r'E:\HaloBackups\h4_dz_add'
REPORT = os.path.join(HERE, 'reports', 'h4_dz_add.txt')
BUSY = ('sapien.exe', 'foundation.exe', 'tool.exe', 'tool_fast.exe', 'guerilla.exe')
_out = []


def say(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    _out.append(s)


def busy():
    try:
        txt = subprocess.run(['tasklist', '/fo', 'csv', '/nh'], capture_output=True,
                             text=True).stdout.lower()
    except Exception:
        return []
    return [p for p in BUSY if '"%s"' % p in txt]


def bind():
    mb = importlib.import_module(KEY + '.managed_blam')
    u = importlib.import_module(KEY + '.utils')
    have = u.read_projects_list() or []
    if H4EK.lower() not in [h.rstrip('\\/').lower() for h in have]:
        u.write_projects_list(have + [H4EK])
        u.setup_projects_list()
    if not mb.mb_active:
        mb.mb_init(os.path.join(TAGS, 'globals', 'globals.globals'))
    if 'h4ek' not in str(getattr(mb, 'mb_path', '') or '').lower():
        raise SystemExit('ManagedBlam is bound to %r, not H4EK' % getattr(mb, 'mb_path', ''))

    class T(mb.Tag):
        pass
    return mb, T


def _block(fields, name):
    return next((f for f in fields if str(f.FieldType) == 'Block' and f.FieldName == name), None)


def _norm(p):
    return str(p or '').replace('/', '\\').lower()


def _refs(block):
    """The first Reference field of every element, normalised (None for an empty one)."""
    out = []
    for i in range(block.Elements.Count if block is not None else 0):
        r = next((s for s in block.Elements[i].Fields if str(s.FieldType) == 'Reference'), None)
        out.append(_norm(r.Path.RelativePathWithExtension) if r is not None and r.Path else None)
    return out


def _sid(field):
    try:
        return field.GetStringData()
    except Exception:
        return str(getattr(field, 'Data', '') or '')


def walk(T, root, kind):
    """(depth-first [(rel, palette)], leaf): the scenario tree under `root`, and the
    scenario visited LAST -- the one whose palette end is the merged palette's end."""
    order = []

    def go(rel):
        with T(path=os.path.join(TAGS, rel)) as t:
            f = t.tag.Fields
            pal = _refs(_block(f, PALETTE[kind]))
            kids = [k for k in _refs(_block(f, 'child scenarios')) if k]
        order.append((rel.lower(), pal))
        for k in kids:
            go(k)
    go(root)
    return order, order[-1][0]


def merged(order):
    """The cache palette tool builds from the tree (see the module docstring)."""
    out = []
    for _rel, pal in order:
        before = set(out)
        out += [x for x in pal if x and x not in before]
    return out


def inspect(t, T, root, tag, kind):
    f = t.tag.Fields
    dzs = _block(f, 'designer zones')
    if dzs is None:
        return {'error': 'no designer zones block'}
    el = di = None
    for i in range(dzs.Elements.Count):
        e = dzs.Elements[i]
        if _sid(next(s for s in e.Fields if s.FieldName == 'name')) == ZONE:
            el, di = e, i
    if el is None:
        return {'error': 'no %s designer zone' % ZONE}
    refs_b, kind_b = _block(el.Fields, 'references'), _block(el.Fields, kind)
    idx = [int(next(s for s in kind_b.Elements[j].Fields).Value)
           for j in range(kind_b.Elements.Count)]
    order, leaf = walk(T, root, kind)
    pal = merged(order)
    want = _norm(tag)
    in_pal = want in pal
    index = pal.index(want) if in_pal else len(pal)
    return {'zone_index': di, 'refs_b': refs_b, 'kind_b': kind_b, 'idx': idx,
            'refs': _refs(refs_b), 'in_refs': want in _refs(refs_b), 'merged': len(pal),
            'in_palette': in_pal, 'index': index, 'in_idx': index in idx, 'leaf': leaf,
            'scenarios': len(order)}


def main(argv):
    write = '--write' in argv
    maps = list(MAPS)
    tag, kind = DEFAULT_TAG, 'equipment'
    if '--maps' in argv:
        maps = [x.strip() for x in argv[argv.index('--maps') + 1].split(',') if x.strip()]
    if '--tag' in argv:
        tag = argv[argv.index('--tag') + 1]
    if '--kind' in argv:
        kind = argv[argv.index('--kind') + 1]
    if not os.path.exists(os.path.join(TAGS, tag)):
        raise SystemExit('no such tag in H4EK: %s' % tag)
    if write:
        b = busy()
        if b:
            raise SystemExit('refusing to write while %s run(s) -- close it first' % ', '.join(b))
    mb, T = bind()
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = os.path.join(BACKUP_ROOT, stamp)
    say('h4_dz_add %s: %s -> %s.%s on %s (%s)' % (stamp, tag, ZONE, kind, ', '.join(maps),
                                                 'WRITE' if write else 'dry run'))
    changed = []
    for name in maps:
        root = os.path.join('environments', 'solo', name, name + '.scenario')
        path = os.path.join(TAGS, root)
        if not os.path.exists(path):
            say('%-14s no scenario %s' % (name, path))
            continue
        with T(path=path) as t:
            info = inspect(t, T, root, tag, kind)
        if info.get('error'):
            say('%-14s SKIP: %s' % (name, info['error']))
            continue
        need = [x for x, n in (('palette entry in %s' % info['leaf'].rsplit('\\', 1)[-1],
                                not info['in_palette']),
                               ('reference', not info['in_refs']),
                               ('index %d' % info['index'], not info['in_idx'])) if n]
        say('%-14s %d scenarios, merged %s palette %d; %s index %d; %s'
            % (name, info['scenarios'], kind, info['merged'], ZONE, info['index'],
               'already holds it' if not need else
               '%s %s' % ('adding' if write else 'would add', ' + '.join(need))))
        if not write or not need:
            continue
        os.makedirs(dest, exist_ok=True)
        if not info['in_palette']:
            lp = os.path.join(TAGS, info['leaf'])
            shutil.copy2(lp, os.path.join(dest, os.path.basename(lp)))
            with T(path=lp) as lt:
                pb = _block(lt.tag.Fields, PALETTE[kind])
                e = pb.AddElement()
                r = next(s for s in e.Fields if str(s.FieldType) == 'Reference')
                r.Path = lt._TagPath_from_string(os.path.join(TAGS, tag))
                lt.tag.Save()                # explicitly: Tag.__exit__ swallows save errors
                lt.tag_has_changes = False
        if not info['in_refs'] or not info['in_idx']:
            if not os.path.exists(os.path.join(dest, os.path.basename(path))):
                shutil.copy2(path, os.path.join(dest, os.path.basename(path)))
            with T(path=path) as t:
                again = inspect(t, T, root, tag, kind)
                if not again['in_refs']:
                    e = again['refs_b'].AddElement()
                    r = next(s for s in e.Fields if str(s.FieldType) == 'Reference')
                    r.Path = t._TagPath_from_string(os.path.join(TAGS, tag))
                if not again['in_idx']:
                    e = again['kind_b'].AddElement()
                    next(s for s in e.Fields).Value = again['index']
                t.tag.Save()
                t.tag_has_changes = False
        changed.append(name)
        with T(path=path) as t:
            back = inspect(t, T, root, tag, kind)
        ok = back['in_palette'] and back['in_refs'] and back['in_idx']
        say('%-14s   read back: %s (merged palette %d, index %d)'
            % (name, 'OK' if ok else 'NOT THERE', back['merged'], back['index']))
    if write:
        say('changed: %s; backups in %s' % (', '.join(changed) or 'none', dest))


def _finish():
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, 'a', encoding='utf-8') as f:
        f.write('\n'.join(_out) + '\n\n')


if __name__ == '__main__':
    try:
        main(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    except SystemExit as e:
        say(str(e))
    except Exception:
        import traceback
        say(traceback.format_exc())
    _finish()
