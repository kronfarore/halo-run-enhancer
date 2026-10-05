r"""WHERE A FIRST-PERSON GRAPH CUES ITS SOUNDS -- the frames a port's own mix must be
built around (saw_port_foley.py). Lists animation name, frame count and sound events (sound ref, frame) from a kit's XML
export of a model_animation_graph (H3 / ODST / Reach kits). Regex, not an XML parser:
the kits' exports are not always well-formed. Halo 2: h2_tagref.references; Halo 1:
the antr's sound index + sound frame (saw_anims.py prints them).

    python graph_sound_events.py h3|odst|reach <tag path under tags\, with extension>

Promoted from a scratch script (graph_sounds.py), 2026-10-05."""
import os
import re
import subprocess
import sys

KITS = {'h3': r'F:\SteamLibrary\steamapps\common\H3EK', 'odst': r'F:\SteamLibrary\steamapps\common\H3ODSTEK',
        'reach': r'F:\SteamLibrary\steamapps\common\HREK'}


def export(kit, rel):
    ek = KITS[kit]
    out = os.path.join(ek, 'temp', '_graph.xml')
    if os.path.exists(out):
        os.remove(out)
    subprocess.run([os.path.join(ek, 'tool.exe'), 'export-tag-to-xml', os.path.join(ek, 'tags', rel), out],
                   cwd=ek, capture_output=True)
    return open(out, encoding='utf-8', errors='replace').read().splitlines()


def read(kit, rel):
    lines = export(kit, rel)
    refs, anims = [], []
    sect = None
    cur = None
    in_sound_events = False
    for l in lines:
        m = re.search(r'<block name="([^"]+)"', l) or re.search(r'<field name="([^"]+)" value="[^"]*" type="block"', l)
        if m:
            b = m.group(1)
            if b in ('sound references', 'animations'):
                sect = b
            in_sound_events = (b == 'sound events')
            continue
        f = re.search(r'<field name="([^"]+)" value="([^"]*)"', l)
        if not f:
            continue
        name, val = f.group(1), f.group(2)
        if sect == 'sound references' and name == 'sound':
            refs.append(val.split(',')[0])
        elif sect == 'animations':
            if name == 'name' and not in_sound_events and val and not val.startswith(','):
                cur = [val, None, []]
                anims.append(cur)
            elif name == 'frame count' and cur and cur[1] is None:
                cur[1] = val
            elif in_sound_events and cur is not None:
                if name == 'sound':
                    cur[2].append([val.split(',')[-1], None])
                elif name in ('frame', 'frame offset') and cur[2]:
                    cur[2][-1][1] = val
    return refs, anims


if __name__ == '__main__':
    kit, rel = sys.argv[1], sys.argv[2]
    refs, anims = read(kit, rel)
    for i, r in enumerate(refs):
        print('ref %d  %s' % (i, r))
    for name, fc, evs in anims:
        if evs or any(k in name for k in ('reload', 'ready')):
            print('%-44s frames %-4s events %s' % (name, fc, [(refs[int(i)].rsplit(chr(92), 1)[-1] if i.isdigit() and int(i) < len(refs) else i, fr) for i, fr in evs]))
