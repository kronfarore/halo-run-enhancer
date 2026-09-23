r"""Read and write the Halo 2 JMS (version 8210), the format `tool render` imports.

Reclaimer writes JMS 8200 (Halo 1) and only that: nodes carry first-child/sibling links,
there is a REGIONS section, and every triangle names a region. Halo 2's 8210 is a
different file -- nodes carry a PARENT index, there is no region section at all, and a
triangle names only its material. So the Halo 1 converter's writer cannot be pointed at
Halo 2, and the format is implemented here instead.

Nothing here was guessed. `tool extract-render-data <render_model>` hands back the
ORIGINAL Bungie .jms that built the tag -- the H2EK tags still carry the zipped source,
unlike H4's, where `extract-import-info` finds nothing. So the spec below is Bungie's own
file, and `--selftest` proves it: parse each extracted JMS and write it back BYTE FOR
BYTE, all four of them, before any of it is trusted to build a port.

    ;### VERSION ###        8210
    ;### NODES ###          name, parent index, rotation i j k w, translation x y z
    ;### MATERIALS ###      shader name, then "(LOD) permutation region"
    ;### MARKERS ###        name, node index, rotation, translation, radius
    ;### VERTICES ###       position, normal, influence count, (node, weight)*, uv count, uv*
    ;### TRIANGLES ###      material index, v0 v1 v2
    plus thirteen physics/instancing sections a weapon render mesh leaves empty.

Two traps worth naming, because both are silent:

* **There is no REGIONS section.** A Halo 2 region and permutation are parsed out of the
  MATERIAL's second line: `(1) base gun` is LOD 1, permutation `base`, region `gun`. Get
  that string wrong and the geometry lands in a region the model tag never asks for,
  which in Halo 3 was exactly the bug that made a dropped weapon render as thin air.
* **Node translations are ABSOLUTE**, not parent-relative as in Halo 1 -- Reclaimer's own
  (admittedly incomplete) 8210 reader says so, and `frame bullet` bears it out: it hangs
  off `frame magazine` yet its translation is nowhere near its parent's.
"""
import os
import sys

VERSION = '8210'
NL = '\r\n'

#: section header, its record keyword, and the comment lines Bungie writes under the count
SECTIONS = [
    ('NODES', 'NODE', ['<name>', '<parent node index>',
                       '<default rotation <i,j,k,w>>', '<default translation <x,y,z>>']),
    ('MATERIALS', 'MATERIAL', ['<name>', '<material name>']),
    ('MARKERS', 'MARKER', ['<name>', '<node index>', '<rotation <i,j,k,w>>',
                           '<translation <x,y,z>>', '<radius>']),
    ('INSTANCE XREF PATHS', None, ['<path>', '<name>']),
    ('INSTANCE MARKERS', None, ['<name>', '<unique identifier>', '<path index>',
                                '<rotation <i,j,k,w>>', '<translation <x,y,z>>']),
    ('VERTICES', 'VERTEX', ['<position>', '<normal>', '<node influences count>',
                            '\t<node influences <index, weight>>', '\t<...>',
                            '<texture coordinate count>',
                            '\t<texture coordinates <u,v>>', '\t<...>']),
    ('TRIANGLES', 'TRIANGLE', ['<material index>', '<vertex indices <v0,v1,v2>>']),
    ('SPHERES', None, ['<name>', '<parent>', '<material>', '<rotation <i,j,k,w>>',
                       '<translation <x,y,z>>', '<radius>']),
    ('BOXES', None, ['<name>', '<parent>', '<material>', '<rotation <i,j,k,w>>',
                     '<translation <x,y,z>>', '<width (x)>', '<length (y)>',
                     '<height (z)>']),
    ('CAPSULES', None, ['<name>', '<parent>', '<material>', '<rotation <i,j,k,w>>',
                        '<translation <x,y,z>>', '<height>', '<radius>']),
    ('CONVEX SHAPES', None, ['<name>', '<parent>', '<material>',
                             '<rotation <i,j,k,w>>', '<translation <x,y,z>>',
                             '<vertex count>', '<...vertices>']),
    ('RAGDOLLS', None, ['<name>', '<attached index>', '<referenced index>',
                        '<attached transform>', '<reference transform>', '<min twist>',
                        '<max twist>', '<min cone>', '<max cone>', '<min plane>',
                        '<max plane>']),
    ('HINGES', None, ['<name>', '<body A index>', '<body B index>',
                      '<body A transform>', '<body B transform>', '<is limited>',
                      '<friction limit>', '<min angle>', '<max angle']),
    ('CAR_WHEEL', None, ['<name>', '<chassis index>', '<wheel index>',
                         '<chassis transform>', '<wheel transform>',
                         '<suspension transform>', '<suspension min limit>',
                         '<suspension max limit>', '<friction limit>', '<velocity>',
                         '<gain>']),
    ('POINT_TO_POINT', None, ['<name>', '<body A index>', '<body B index>',
                              '<body A transform>', '<body B transform>',
                              '<constraint type>', '<x min limit>', '<x max limit>',
                              '<y min limit>', '<y max limit>', '<z min limit>',
                              '<z max limit>', '<spring length>']),
    ('PRISMATIC', None, ['<name>', '<body A index>', '<body B index>',
                         '<body A transform>', '<body B transform>', '<is limited>',
                         '<friction limit>', '<min limit>', '<max limit>']),
    ('BOUNDING SPHERE', None, ['<translation <x,y,z>>', '<radius>']),
]


def f(v):
    """Bungie writes every float with ten decimals and no exponent."""
    return '%.10f' % v


class Node(object):
    __slots__ = ('name', 'parent', 'rot', 'pos')

    def __init__(self, name, parent, rot, pos):
        self.name, self.parent = name, parent
        self.rot, self.pos = tuple(rot), tuple(pos)


class Material(object):
    """`name` is the shader; `spec` is Bungie's "(LOD) permutation region"."""
    __slots__ = ('name', 'spec')

    def __init__(self, name, spec):
        self.name, self.spec = name, spec

    @property
    def region(self):
        return self.spec.split()[-1]

    @property
    def permutation(self):
        return self.spec.split()[-2]


class Marker(object):
    __slots__ = ('name', 'node', 'rot', 'pos', 'radius')

    def __init__(self, name, node, rot, pos, radius=-1.0):
        self.name, self.node = name, node
        self.rot, self.pos, self.radius = tuple(rot), tuple(pos), radius


class Vertex(object):
    __slots__ = ('pos', 'normal', 'influences', 'uvs')

    def __init__(self, pos, normal, influences, uvs):
        self.pos, self.normal = tuple(pos), tuple(normal)
        self.influences = list(influences)          # [(node index, weight)]
        self.uvs = [tuple(uv) for uv in uvs]


class Model(object):
    def __init__(self):
        self.nodes, self.materials, self.markers = [], [], []
        self.verts, self.tris = [], []


def _tokens(text):
    """Every meaningful line, comments and blanks dropped -- the file is line oriented."""
    out = []
    for line in text.split('\n'):
        line = line.strip('\r').strip()
        if line and not line.startswith(';'):
            out.append(line)
    return out


def _floats(tok):
    return [float(x) for x in tok.split()]


def read(path):
    t = _tokens(open(path, encoding='latin-1').read())
    if t[0] != VERSION:
        raise ValueError('%s is JMS version %s, not %s' % (path, t[0], VERSION))
    i = 1
    m = Model()

    n = int(t[i]); i += 1
    for _ in range(n):
        m.nodes.append(Node(t[i], int(t[i + 1]), _floats(t[i + 2]), _floats(t[i + 3])))
        i += 4

    n = int(t[i]); i += 1
    for _ in range(n):
        m.materials.append(Material(t[i], t[i + 1]))
        i += 2

    n = int(t[i]); i += 1
    for _ in range(n):
        m.markers.append(Marker(t[i], int(t[i + 1]), _floats(t[i + 2]),
                                _floats(t[i + 3]), float(t[i + 4])))
        i += 5

    n = int(t[i]); i += 1
    i += n * 2                              # instance xref paths
    n = int(t[i]); i += 1
    i += n * 5                              # instance markers

    n = int(t[i]); i += 1
    for _ in range(n):
        pos, normal = _floats(t[i]), _floats(t[i + 1])
        i += 2
        influences = []
        for _k in range(int(t[i])):
            influences.append((int(t[i + 1]), float(t[i + 2])))
            i += 2
        i += 1
        uvs = []
        for _k in range(int(t[i])):
            uvs.append(_floats(t[i + 1]))
            i += 1
        i += 1
        m.verts.append(Vertex(pos, normal, influences, uvs))

    n = int(t[i]); i += 1
    for _ in range(n):
        m.tris.append((int(t[i]), tuple(int(x) for x in t[i + 1].split())))
        i += 2
    return m


def _records(m, keyword):
    """The lines of every record in a section, in Bungie's order."""
    if keyword == 'NODE':
        for nd in m.nodes:
            yield [nd.name, str(nd.parent), '\t'.join(f(x) for x in nd.rot),
                   '\t'.join(f(x) for x in nd.pos)]
    elif keyword == 'MATERIAL':
        for mt in m.materials:
            yield [mt.name, mt.spec]
    elif keyword == 'MARKER':
        # the blank line before the radius is Bungie's own: an empty field sits between
        # the translation and the radius on every marker in every shipped file.
        for mk in m.markers:
            yield [mk.name, str(mk.node), '\t'.join(f(x) for x in mk.rot),
                   '\t'.join(f(x) for x in mk.pos), '', f(mk.radius)]
    elif keyword == 'VERTEX':
        for v in m.verts:
            rec = ['\t'.join(f(x) for x in v.pos),
                   '\t'.join(f(x) for x in v.normal), str(len(v.influences))]
            for node, weight in v.influences:
                rec += [str(node), f(weight)]
            rec.append(str(len(v.uvs)))
            for uv in v.uvs:
                rec.append('\t'.join(f(x) for x in uv))
            yield rec
    elif keyword == 'TRIANGLE':
        for mat, (a, b, c) in m.tris:
            yield [str(mat), '%d\t%d\t%d' % (a, b, c)]


def _count(m, name):
    return {'NODES': len(m.nodes), 'MATERIALS': len(m.materials),
            'MARKERS': len(m.markers), 'VERTICES': len(m.verts),
            'TRIANGLES': len(m.tris)}.get(name, 0)


def dumps(m):
    out = [';### VERSION ###', VERSION, '']
    for name, keyword, comments in SECTIONS:
        out.append(';### %s ###' % name)
        out.append(str(_count(m, name)))
        out += [';\t' + c for c in comments]
        out.append('')
        if keyword is None:
            continue
        for k, rec in enumerate(_records(m, keyword)):
            out.append(';%s %d' % (keyword, k))
            out += rec
            # a marker's record ends ON its radius; every other kind is followed by a
            # blank line.
            if keyword != 'MARKER':
                out.append('')
    return NL.join(out) + NL


def write(path, m):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='latin-1', newline='') as fh:
        fh.write(dumps(m))


def selftest(paths):
    ok = True
    for p in paths:
        want = open(p, 'rb').read()
        got = dumps(read(p)).encode('latin-1')
        same = got == want
        ok &= same
        print('%-6s %-24s %7d bytes%s'
              % ('OK' if same else 'DIFFER', os.path.basename(p), len(want),
                 '' if same else '   -> produced %d' % len(got)))
        if not same:
            for a, b in zip(want.split(b'\r\n'), got.split(b'\r\n')):
                if a != b:
                    print('       first difference: %r != %r' % (a[:70], b[:70]))
                    break
    return ok


if __name__ == '__main__':
    args = sys.argv[1:]
    if args and args[0] == '--selftest':
        sys.exit(0 if selftest(args[1:]) else 1)
    for p in args:
        m = read(p)
        print('%s: %d nodes, %d materials, %d markers, %d verts, %d tris'
              % (os.path.basename(p), len(m.nodes), len(m.materials), len(m.markers),
                 len(m.verts), len(m.tris)))
        print('   nodes  : %s' % [(n.name, n.parent) for n in m.nodes])
        print('   mats   : %s' % [(mt.name, mt.spec) for mt in m.materials])
        print('   markers: %s' % [(mk.name, mk.node) for mk in m.markers])
