r"""H4 SAW geometry -> a Halo 3 JMS on the Halo 3 Assault Rifle's skeleton.

The Halo 1 converter takes its skeleton, rest pose and markers from Reclaimer's
extraction of the Halo 1 Assault Rifle. Reclaimer cannot read Halo 3 tags, but
`tool.exe export-tag-to-xml` dumps a render_model with everything a JMS node needs --
name, first child, next sibling, default translation and rotation -- plus the marker
groups. So the template is built from that XML instead, and the geometry half is the
Halo 1 converter's own `convert()`, unchanged.

Halo 3's first-person rifle skeleton is `gun` (root) with `magazine`, `ophandle`,
`safety` and `switch` hanging off it -- the same shape as Halo 1's, without the
"frame " prefix.

    python saw_to_jms_h3.py <render_model.xml> <lmg_rm.xml> [scale] [out subdir]

The third-person skeleton is the same minus `switch`, so the same converter builds the
world model: point it at assault_rifle.render_model's XML and give it its own subdir.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
import env  # noqa
import h4_rm
import saw_to_jms as h1
from reclaimer.model.jms import JmsModel, JmsNode, JmsMarker
from reclaimer.model.jms.file import write_jms

B = os.sep
H3EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK')
OUT_SUB = 'saw'          # folder under data/objects/weapons/rifle that holds render/
UNITS = 100.0            # JMS units per world unit


def _fields(seg):
    return {m.group(1): m.group(2)
            for m in re.finditer(r'<field name="([^"]+)" value="([^"]*)"', seg)}


def _elements(xml, block, start=0):
    """The <element> chunks of the first <block name="..."> at or after `start`."""
    i = xml.find('<block name="%s"' % block, start)
    if i < 0:
        return []
    depth, j, out, cur = 0, i, [], None
    for m in re.finditer(r'<(/?)(block|element)[^>]*>', xml[i:]):
        tag, closing = m.group(2), m.group(1)
        at = i + m.start()
        if tag == 'block':
            depth += -1 if closing else 1
            if depth == 0:
                if cur is not None:
                    out.append(xml[cur:at])
                break
        elif tag == 'element' and depth == 1:
            if closing:
                if cur is not None:
                    out.append(xml[cur:at])
                cur = None
            else:
                cur = at
    return out


def template_from_xml(path):
    """A JmsModel carrying the Halo 3 weapon's skeleton and markers, no geometry."""
    xml = open(path, encoding='utf-8', errors='replace').read()
    nodes = []
    for el in _elements(xml, 'nodes'):
        f = _fields(el)
        rot = [float(x) for x in f.get('default rotation', '0,0,0,1').split(',')]
        pos = [float(x) for x in f.get('default translation', '0,0,0').split(',')]
        idx = lambda key: int(f.get(key, ',-1').split(',')[-1])
        nodes.append(JmsNode(f.get('name', ''), idx('first child node'),
                             idx('next sibling node'),
                             rot[0], rot[1], rot[2], rot[3],
                             pos[0] * UNITS, pos[1] * UNITS, pos[2] * UNITS,
                             idx('parent node')))
    by_name = {n.name: i for i, n in enumerate(nodes)}
    markers = []
    for grp in _elements(xml, 'marker groups'):
        name = (_fields(grp[:grp.find('<block')] if '<block' in grp else grp)
                .get('name', ''))
        for el in _elements(grp, 'markers'):
            f = _fields(el)
            rot = [float(x) for x in f.get('rotation', '0,0,0,1').split(',')]
            pos = [float(x) for x in f.get('translation', '0,0,0').split(',')]
            node = f.get('node index', '0')
            node = int(node.split(',')[-1]) if ',' in node else int(node or 0)
            markers.append(JmsMarker(name, '', 0, node,
                                     rot[0], rot[1], rot[2], rot[3],
                                     pos[0] * UNITS, pos[1] * UNITS, pos[2] * UNITS,
                                     float(f.get('radius', 0) or 0)))
    # The REGION name matters: Halo 3 draws a world model through the model tag's
    # variant system, which looks for the permutation by name. The Assault Rifle uses
    # 'standard'; an unnamed JMS region becomes 'default', the variant finds nothing and
    # the weapon renders as thin air -- while first person, which references the render
    # model directly, looks fine. That was the vanishing dropped SAW.
    jm = JmsModel('saw', 0, nodes, [], markers, ['standard'], [], [])
    return jm, by_name


def main():
    global OUT_SUB
    xml_rm = sys.argv[1]
    lmg = sys.argv[2]
    if len(sys.argv) > 3:
        h1.SCALE = float(sys.argv[3])
    if len(sys.argv) > 4:
        OUT_SUB = sys.argv[4]
    out_dir = os.path.join(H3EK, 'data', 'objects', 'weapons', 'rifle', OUT_SUB, 'render')
    print('scale %s' % h1.SCALE)
    tmpl, by_name = template_from_xml(xml_rm)
    print('skeleton: %s' % [n.name for n in tmpl.nodes])
    print('markers : %s' % sorted({m.name for m in tmpl.markers}))
    rm = h4_rm.load(lmg)
    # Halo 3 and Halo 4 spell these markers the same way, so each moves to the SAW's own
    # position. `left_hand` is deliberately NOT in the list: the animation places the hand,
    # and moving the marker would fight it -- the same reason the Halo 1 port picked its
    # scale to suit the Assault Rifle's hand rather than moving markers.
    h1.MARKER_FROM = {'muzzle_flash': 'muzzle_flash', 'primary_trigger': 'primary_trigger',
                      'primary_ejection': 'primary_ejection', 'flashlight': 'flashlight'}
    # the H4 SAW's two skinned bones -> the Halo 3 nodes that move the same parts
    node_map = {0: by_name.get('gun', 0), 1: by_name.get('magazine', by_name.get('gun', 0))}
    jm = h1.convert(rm, tmpl, node_map)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, 'standard.jms')
    write_jms(out, jm)
    xs = [v.pos_x for v in jm.verts]
    print('wrote %s\n   verts %d, tris %d, x %.1f..%.1f'
          % (out, len(jm.verts), len(jm.tris), min(xs), max(xs)))


if __name__ == '__main__':
    main()
