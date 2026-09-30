r"""Append the vertex COLOUR field Halo 3 expects to a JMS written for Halo 1.

Every vertex of the ported SAW's render models carries `-nan,-nan,-nan` as its vertex
colour, while every stock Halo 3 model carries `-1,0,0`. Reclaimer's JmsVertex has no
colour field at all, so write_jms cannot emit one -- and because the colour is the LAST
field of the record, leaving it out does not misalign anything: the geometry, normals and
UVs all come through correctly and only the colour reads as uninitialised memory.

This walks the written JMS and inserts one colour line per vertex. The record is
  node0 / position / normal / node1 / weight / u / v / w
so the colour goes after `w`, and the count of inserted lines has to match the vertex
count exactly or nothing is written.

    python jms_add_colour.py <file.jms> <vertex count> [--colour -1,0,0]
"""
import argparse, io, re, sys

FIELDS = 8                       # lines per vertex before the colour


def find_vertex_count(lines, n_verts):
    """The line index holding the vertex count: it must say n_verts and be followed by a
    plausible first vertex (an integer node index, then a three-float position)."""
    want = str(n_verts)
    for i, line in enumerate(lines):
        if line.strip() != want:
            continue
        a = lines[i + 1].strip() if i + 1 < len(lines) else ''
        b = lines[i + 2].strip() if i + 2 < len(lines) else ''
        if re.match(r'^-?\d+$', a) and len(b.split('\t')) == 3:
            return i
    return -1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('count', type=int)
    ap.add_argument('--colour', default='-1,0,0')
    a = ap.parse_args()
    raw = io.open(a.path, encoding='latin1', newline='').read()
    nl = '\r\n' if '\r\n' in raw[:400] else '\n'
    lines = raw.split(nl)
    at = find_vertex_count(lines, a.count)
    if at < 0:
        raise SystemExit('could not find the vertex count %d in %s' % (a.count, a.path))
    colour = '\t'.join(a.colour.split(','))
    out = lines[:at + 1]
    i = at + 1
    for _v in range(a.count):
        out.extend(lines[i:i + FIELDS])
        out.append(colour)
        i += FIELDS
    out.extend(lines[i:])
    io.open(a.path, 'w', encoding='latin1', newline='').write(nl.join(out))
    print('%s: %d vertices, colour %s inserted after every %d-line record'
          % (a.path.rsplit('\\', 1)[-1], a.count, a.colour, FIELDS))


if __name__ == '__main__':
    main()
