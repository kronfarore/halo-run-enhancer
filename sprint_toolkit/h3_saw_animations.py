r"""Give the Halo 3 SAW its own first-person animations, retimed to the Halo 4 weapon's.

Port checklist step 9. The port was cloned from the Assault Rifle and so shares its
animation graph, which means two things: it reloads at the Assault Rifle's speed, and
retiming it would retime the Assault Rifle too. Both are fixed here -- the graph is
cloned, the weapon repointed, and the animations rebuilt at the SAW's own frame counts.

Measured, not guessed (frames at 30fps):

    animation            Halo 3 AR    Halo 4 SAW
    first_person:reload_empty   58          128
    first_person:reload_full    58          128
    first_person:ready          20           24
    first_person:put_away        5            5     (unchanged, so left alone)

The graph is built at the SAW's OWN timing rather than the balanced timing, because the
patcher can only SHORTEN a jmad animation -- `halo3_reload.scale_reload` rewrites frame
counts and would read past the data if it stretched one. Built long, the run's balance
multiplier (109/128 for the reload) only ever shortens, so both the balanced and the
"Halo 4 originals" settings work from one build.

The weapon references TWO graphs, the Master Chief's and the Dervish's, and both are
cloned: a port that only fixed one would still be sharing the other.

    python h3_saw_animations.py            # show what it would do
    python h3_saw_animations.py --write
"""
import argparse, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                   # noqa: E402
import h3_anim_decode as dec                                   # noqa: E402
import h3_anim_retime as ret                                   # noqa: E402

B = os.sep
EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK')
TAGS = os.path.join(EK, 'tags')
TOOL = os.path.join(EK, 'tool.exe')
EXT = '.model_animation_graph'

SAW_WEAPON = B.join(['objects', 'weapons', 'rifle', 'saw', 'saw'])
GRAPHS = [
    (B.join(['objects', 'characters', 'masterchief', 'fp', 'weapons', 'rifle',
             'fp_assault_rifle', 'fp_assault_rifle']),
     B.join(['objects', 'weapons', 'rifle', 'saw', 'fp', 'fp_saw_masterchief'])),
    (B.join(['objects', 'characters', 'dervish', 'fp', 'weapons', 'rifle',
             'fp_assault_rifle', 'fp_assault_rifle']),
     B.join(['objects', 'weapons', 'rifle', 'saw', 'fp', 'fp_saw_dervish'])),
]
#: what each animation becomes, in frames -- the Halo 4 SAW's own counts
TARGET = {'first_person:reload_empty': 128,
          'first_person:reload_full': 128,
          'first_person:ready': 24}


def export_xml(tag_rel, out):
    """tool export-tag-to-xml, which is how the animation NAMES and section sizes are
    read -- they are not recoverable from the tag bytes alone."""
    subprocess.run([TOOL, 'export-tag-to-xml', os.path.join(TAGS, tag_rel + EXT), out],
                   cwd=EK, capture_output=True)
    return out if os.path.exists(out) else None


def names_from_xml(path):
    """{animation name: index} for the graph's animations."""
    s = open(path, encoding='utf-8', errors='replace').read()
    return {m.group(2): int(m.group(1)) for m in
            re.finditer(r'<element index="(\d+)" name="(first_person:[^"]*)">', s)}


def recompress(tag_rel):
    r = subprocess.run([TOOL, 'model-animation-reset-compression', tag_rel],
                       cwd=EK, capture_output=True, text=True)
    return (r.stdout or '') + (r.stderr or '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--scratch', default=os.environ.get('TEMP', '.'))
    a = ap.parse_args()

    print('retiming to the Halo 4 SAW\'s own frame counts:')
    for k, v in sorted(TARGET.items()):
        print('   %-32s -> %d frames' % (k, v))
    print()

    for src, dst in GRAPHS:
        sp, dp = os.path.join(TAGS, src + EXT), os.path.join(TAGS, dst + EXT)
        if not os.path.exists(sp):
            print('%s: MISSING' % src)
            continue
        print('== %s\n   -> %s' % (src, dst))
        if not a.write:
            xml = export_xml(src, os.path.join(a.scratch, 'probe_names.xml'))
            if xml:
                have = names_from_xml(xml)
                for k in sorted(TARGET):
                    print('      %-32s %s' % (k, 'index %d' % have[k] if k in have
                                              else 'NOT IN THIS GRAPH'))
            continue

        os.makedirs(os.path.dirname(dp), exist_ok=True)
        shutil.copyfile(sp, dp)
        xml = export_xml(dst, os.path.join(a.scratch, 'clone.xml'))
        if not xml:
            print('   could not export the clone -- skipped')
            continue
        have = names_from_xml(xml)
        for name, frames in sorted(TARGET.items()):
            if name not in have:
                print('      %-32s not in this graph, skipped' % name)
                continue
            # re-read each time: the sizes change as each animation is rebuilt
            mem = dec.members_from_xml(xml)
            tag = h3tag.Tag(dp)
            rep = ret.retime(tag, mem, have[name], frames, xml)
            ok, cov, tot = tag.check()
            if not ok:
                raise SystemExit('   %s: tree no longer spans the file' % name)
            tag.save(dp)
            (_mw, mm), (_rw, rm) = rep['smooth']
            print('      %-32s %d -> %d frames (%+d bytes)  motion %.2f -> %.2f deg/frame%s'
                  % (name, rep['old'], rep['new'], rep['bytes'], mm, rm,
                     '  events ' + ', '.join('%d->%d' % e for e in rep['events'])
                     if rep['events'] else ''))
            xml = export_xml(dst, os.path.join(a.scratch, 'clone.xml'))
        # NOT recompressed on purpose -- retime() stores the frames raw (codec 8), so
        # the engine reads exactly what was written. Running
        # model-animation-reset-compression here re-encodes them and swaps the codec
        # from "best accuracy" to "best score", and the animation still played wrong.

    if not a.write:
        print('\n(dry run -- pass --write)')
        return

    wp = os.path.join(TAGS, SAW_WEAPON + '.weapon')
    w = h3tag.Tag(wp)
    have = {p for _o, g, p in w.references() if g == 'jmad'}
    want = {dst for _src, dst in GRAPHS}
    if want <= have:
        # Re-running rebuilds the graphs from the donor, which is the point; there is
        # then nothing left to repoint and that is success, not failure.
        print('\nweapon already points at the port\'s graphs')
        return
    n = 0
    for src, dst in GRAPHS:
        n += w.repoint(src, dst, 'jmad')
    ok, cov, tot = w.check()
    print('\nweapon repointed %d reference(s); parses %s (%d/%d)' % (n, ok, cov, tot))
    if ok and n:
        w.save(wp)
        print('wrote %s' % wp)
    else:
        raise SystemExit('weapon NOT saved')


if __name__ == '__main__':
    main()
