r"""Stage Master Chief's first-person animation graphs into the ODST Editing Kit.

WHY
---
ODST's own fp graphs do not contain the dual-wield animations (confirmed by frame-count
matching -- see `odst_dualwield.py`). The reference mod does not copy animations either:
it points each ODST fp graph at Chief's through the jmad **Inheritance List**, and the
dual class's actions carry a **Graph Index** selecting that inherited graph.

The ODST kit ships only 7 of Chief's fp graphs and none of the ones that matter, so the
tags have to come across from the Halo 3 kit first. That is all this does -- copy tag
files between the two kits' `tags` trees. It changes nothing in the game and builds
nothing.

WHAT HAPPENS AFTER THIS (the part this script cannot do)
--------------------------------------------------------
A tag only enters a built map if something REFERENCES it, and the reference we need is
the Inheritance List entry inside ODST's own fp graph. That is a tag edit, so it happens
in Guerilla -- but it is a small one, because **the Node Map is empty**: the mod's
inheritance entries have 0 node-map entries and 0 flag dwords, just the tagRef. Measured
on its fp_plasma_rifle / fp_magnum / fp_smg.

Per graph, once:

    open  tags\objects\characters\odst_recon\fp\weapons\<...>\fp_<w>.model_animation_graph
    Inheritance List -> add one element
    Inherited Graph  -> objects\characters\masterchief\fp\weapons\<...>\fp_<w>
    leave Node Map and Node Map Flags EMPTY
    save

Then rebuild the level, and the `dual` weapon class and the weapon flag go in as an
ordinary map patch (`odst_dualwield.py`), which needs no Guerilla at all.

    python odst_import_fp.py                  # report what is missing
    python odst_import_fp.py --copy           # copy the dual-wield set
    python odst_import_fp.py --copy --all     # every fp weapon graph ODST lacks
    python odst_import_fp.py --undo           # remove what this script copied

Every copy is logged to `out/odst_import_fp.json` so --undo removes exactly what was
added and never touches a tag the kit shipped.
"""
import argparse
import json
import os
import shutil

H3EK = r"F:\SteamLibrary\steamapps\common\H3EK"
ODSTEK = r"F:\SteamLibrary\steamapps\common\H3ODSTEK"
CHIEF_FP = os.path.join('objects', 'characters', 'masterchief', 'fp')
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out',
                   'odst_import_fp.json')

# The nine one-handed weapons share eight graphs -- plasma_rifle_red has no fp graph of
# its own and uses the plasma rifle's.
DUAL_SET = ['fp_magnum', 'fp_smg', 'fp_smg_silenced', 'fp_plasma_pistol',
            'fp_plasma_rifle', 'fp_spike_rifle', 'fp_excavator', 'fp_needler']


def graphs(root):
    """{basename: full path} for every fp weapon animation graph under a kit."""
    out = {}
    base = os.path.join(root, 'tags', CHIEF_FP)
    for dirpath, _dirs, files in os.walk(base):
        for f in files:
            if f.endswith('.model_animation_graph'):
                out[f[:-len('.model_animation_graph')]] = os.path.join(dirpath, f)
    return out


def rel_of(path, root):
    return os.path.relpath(path, os.path.join(root, 'tags'))


def plan(want_all):
    src, dst = graphs(H3EK), graphs(ODSTEK)
    names = sorted(src) if want_all else [n for n in DUAL_SET]
    rows = []
    for n in names:
        if n not in src:
            rows.append((n, None, 'NOT IN THE HALO 3 KIT'))
            continue
        if n in dst:
            rows.append((n, src[n], 'already in the ODST kit'))
            continue
        rows.append((n, src[n], 'to copy'))
    return rows


def pairs(want_all):
    """[(ODST graph tag, Chief graph tag)] -- the exact Guerilla edit list.

    Paired by basename, which is safe here because the two kits use the same fp weapon
    names; the FOLDERS differ (Chief files the brute shot under support_low, ODST under
    its own tree), so the Chief path is printed in full rather than derived.
    """
    src = graphs(H3EK)
    odst = {}
    base = os.path.join(ODSTEK, 'tags', 'objects', 'characters', 'odst_recon', 'fp')
    for dirpath, _dirs, files in os.walk(base):
        for f in files:
            if f.endswith('.model_animation_graph'):
                odst[f[:-len('.model_animation_graph')]] = os.path.join(dirpath, f)
    names = sorted(odst) if want_all else DUAL_SET
    out = []
    for n in names:
        if n in odst and n in src:
            out.append((rel_of(odst[n], ODSTEK)[:-len('.model_animation_graph')],
                        rel_of(src[n], H3EK)[:-len('.model_animation_graph')]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--copy', action='store_true', help='actually copy the tag files')
    ap.add_argument('--all', action='store_true',
                    help='every fp weapon graph, not just the dual-wield set')
    ap.add_argument('--undo', action='store_true',
                    help='delete the files this script copied, per its log')
    ap.add_argument('--pairs', action='store_true',
                    help='print the exact Guerilla edit list (ODST graph -> Chief graph)')
    a = ap.parse_args(argv)

    if a.pairs:
        rows = pairs(a.all)
        print('Open each ODST graph in Guerilla, add ONE Inheritance List element, set')
        print('Inherited Graph to the tag on the right, leave Node Map and Node Map')
        print('Flags EMPTY, save. %d graph(s):\n' % len(rows))
        for od, ch in rows:
            print('   %s' % od)
            print('      -> %s' % ch)
        return 0

    if a.undo:
        if not os.path.exists(LOG):
            print('nothing logged at %s' % LOG)
            return 1
        with open(LOG, encoding='utf-8') as f:
            copied = json.load(f)
        gone = 0
        for rel in copied:
            p = os.path.join(ODSTEK, 'tags', rel)
            if os.path.exists(p):
                os.remove(p)
                gone += 1
        os.remove(LOG)
        print('removed %d of %d copied tag(s)' % (gone, len(copied)))
        return 0

    rows = plan(a.all)
    todo = [r for r in rows if r[2] == 'to copy']
    for n, src, why in rows:
        print('   %-22s %s%s' % (n, why, '' if not src else
                                 '   <- ' + rel_of(src, H3EK)))
    print('\n%d graph(s) to copy, %d already present, %d missing from the Halo 3 kit'
          % (len(todo), sum(1 for r in rows if r[2].startswith('already')),
             sum(1 for r in rows if r[1] is None)))
    if not a.copy:
        print('\ndry run \u2014 nothing written. Pass --copy to stage them.')
        return 0

    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    already = json.load(open(LOG, encoding='utf-8')) if os.path.exists(LOG) else []
    copied = list(already)
    for n, src, why in todo:
        rel = rel_of(src, H3EK)
        dst = os.path.join(ODSTEK, 'tags', rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        copied.append(rel)
        print('   copied %s' % rel)
    with open(LOG, 'w', encoding='utf-8') as f:
        json.dump(copied, f, indent=1)
    print('\n%d file(s) staged; log: %s' % (len(todo), LOG))
    print('NOTE: a copied tag is inert until an ODST fp graph REFERENCES it \u2014 see the '
          'Guerilla step in this file\'s docstring.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
