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
import h3_kit                                              # noqa: E402
H3EK = h3_kit.EK
OUT_SUB = 'saw'          # folder under data/objects/weapons/rifle that holds render/

#: What the stock weapons call their one region, which is NOT the same in every kit:
#: Halo 3 and ODST say 'standard', Reach says 'default'. `tool render` writes 'default'
#: whatever the JMS declares -- which is exactly why Halo 3 needs h3_region_name.py
#: afterwards and Reach does not -- so this only makes the source say what it means.
REGION = h3_kit.per_kit(h3='standard', odst='standard', reach='default',
                        what='what the stock weapons call their region')
#: The two nodes the H4 SAW's skinned bones move. Reach prefixes every skeleton node
#: with `b_`, and a name that does not match falls back to node 0 SILENTLY -- which
#: would weld the magazine to the body and look like an animation problem.
GUN, MAG = h3_kit.per_kit(h3=('gun', 'magazine'), odst=('gun', 'magazine'),
                          reach=('b_gun', 'b_magazine'),
                          what='the skeleton nodes the H4 bones map onto')

#: TOOL RENDER STRIPS A LEADING `b_`, and Reach's skeleton is entirely b_-prefixed.
#: So a JMS that honestly declares `b_gun` produces a render model whose node is called
#: `gun`, and then NOTHING THAT ANIMATES THE WEAPON CAN FIND ITS NODES. The statically
#: placed weapon still draws at bind pose, which is what made this look like a
#: rendering fault instead of a naming one, while first person was EMPTY and a dropped
#: weapon VANISHED. Declaring `b_b_gun` leaves `b_gun` after the strip.
#:
#: Halo 3 and ODST have unprefixed skeletons, so there is nothing to protect there.
NODE_PREFIX = h3_kit.per_kit(h3='', odst='', reach='b_',
                             what='what tool render will strip off a node name')

#: AND IT SORTS WHAT IS LEFT, ALPHABETICALLY. Measured: `b_b_switch` comes out
#: `b_switch` while `a_b_gun` is untouched, so the strip is exactly a leading `b_`, and
#: the emitted order is alphabetical on the stripped name whatever the JMS declares.
#:
#: That matters because the WORLD animation graph carries its own 5-node skeleton and
#: its animation data indexes INTO it. The donor's order is gun, switch, safety,
#: magazine, ophandle; alphabetical is gun, magazine, ophandle, safety, switch. A held
#: or dropped weapon is posed through that graph, so the transforms land on the wrong
#: nodes. First person is unaffected because its graph is the 52-node ARMS skeleton and
#: the weapon hangs off it by MARKER, not by node index.
#:
#: So the order is steered with a one-character sort key that is renamed away in the
#: tag afterwards -- `b_a_gun` renders as `a_gun`, sorts first, and reach_node_names.py
#: renames it to `b_gun`. Every rename is one character for one character, so it is an
#: in-place byte swap with no chunk length to correct.
ORDER_KEYS = 'abcdefghijklmnopqrstuvwxyz'

#: THE SECOND MATERIAL LINE. A JMS material is two lines, and the shared converter writes
#: the Halo 1/2 convention: the shader name, then `<none>` for "no texture path". Reach
#: reads that second line as the MAX MATERIAL NAME, and `<` and `>` are both in its
#: material-flag character set (%#?!@*$^-&=.;)><|~({}[ -- next to portal, weatherpoly,
#: seamsealer, soft_kill, slip_surface). So every material came out as one called `none`
#: carrying two spurious STRUCTURE flags: tool says "material 'none' is not a portal, but
#: has flags that only make sense on portals" and files it as *unexpected material flags.
#: The stock model and a sidecar-imported one carry neither. Writing the shader name
#: again puts tool in its benign legacy mode ("identical material/shader names"), which
#: is where every JMS-built model already lives.
MATERIAL_SECOND_LINE = h3_kit.per_kit(h3=None, odst=None, reach='shader name',
                                      what="what a JMS material's second line holds")
UNITS = 100.0            # JMS units per world unit


def _fields(seg):
    return {m.group(1): m.group(2)
            for m in re.finditer(r'<field name="([^"]+)" value="([^"]*)"', seg)}


def _elements_flat(xml, block, start=0):
    r"""The <element> chunks of a REACH-style block.

    The two kits do not export the same XML. Halo 3 and ODST wrap a block's elements in
    a container:

        <block name="nodes" value="node,5">
            <element index="0" name="gun"> ... </element>

    Reach has NO <block> tag anywhere in the file. It declares the block as a
    SELF-CLOSING field and then lets the elements follow as siblings:

        <field name="nodes" value="5" type="block"/>
        <element index="0" name="b_gun"> ... </element>

    So there is no container to bound the run, and the count in `value` is the only thing
    that says where it stops. Read as Halo 3, this yields nothing at all -- which is how
    the Reach skeleton came back empty and every H4 bone would have been welded to node 0.
    """
    m = re.search(r'<field name="%s" value="(\d+)" type="block"\s*/>' % re.escape(block),
                  xml[start:])
    if not m:
        return []
    want = int(m.group(1))
    i = start + m.end()
    out, depth, cur = [], 0, None
    for t in re.finditer(r'<(/?)element[^>]*?(/?)>', xml[i:]):
        closing, selfclose = t.group(1), t.group(2)
        at = i + t.start()
        if closing:
            depth -= 1
            if depth == 0 and cur is not None:
                out.append(xml[cur:i + t.end()])
                cur = None
                if len(out) >= want:
                    break
        elif not selfclose:
            if depth == 0:
                cur = at
            depth += 1
    return out


def _elements(xml, block, start=0):
    """The <element> chunks of the first <block name="..."> at or after `start`."""
    i = xml.find('<block name="%s"' % block, start)
    if i < 0:
        return _elements_flat(xml, block, start)
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


def _block_index(value, names, default=-1):
    r"""Resolve a "short block index" field, in either kit's spelling.

    Halo 3 and ODST write the block type and the ordinal, `node,3`. Reach writes the
    NAME of the thing pointed at, `b_ophandle`, and `NONE` for no link. So the index has
    to be looked up against the names already read -- which is why the nodes are
    collected in two passes.
    """
    value = (value or '').strip()
    if not value or value == 'NONE':
        return default
    if ',' in value:
        value = value.rsplit(',', 1)[-1]
    try:
        return int(value)
    except ValueError:
        return names.index(value) if value in names else default


def template_from_xml(path):
    """A JmsModel carrying the weapon's skeleton and markers, no geometry."""
    xml = open(path, encoding='utf-8', errors='replace').read()
    raw = [_fields(el) for el in _elements(xml, 'nodes')]
    names = [f.get('name', '') for f in raw]
    nodes = []
    for f in raw:
        rot = [float(x) for x in f.get('default rotation', '0,0,0,1').split(',')]
        pos = [float(x) for x in f.get('default translation', '0,0,0').split(',')]
        base = f.get('name', '')
        if NODE_PREFIX and base.startswith('b_'):
            # b_gun -> b_<key>_gun, so the strip leaves <key>_gun and the sort obeys
            base = 'b_%s_%s' % (ORDER_KEYS[len(nodes)], base[2:])
        else:
            base = NODE_PREFIX + base
        nodes.append(JmsNode(base,
                             _block_index(f.get('first child node'), names),
                             _block_index(f.get('next sibling node'), names),
                             rot[0], rot[1], rot[2], rot[3],
                             pos[0] * UNITS, pos[1] * UNITS, pos[2] * UNITS,
                             _block_index(f.get('parent node'), names)))
    by_name = {n.name: i for i, n in enumerate(nodes)}
    markers = []
    for grp in _elements(xml, 'marker groups'):
        # The group's own name is whatever comes BEFORE its children. Halo 3 opens them
        # with <block>, Reach with a bare <element>, and reading the whole chunk would
        # let a child's `name` overwrite the group's.
        cut = min((i for i in (grp.find('<block'), grp.find('<element', 1)) if i > 0),
                  default=len(grp))
        name = _fields(grp[:cut]).get('name', '')
        for el in _elements(grp, 'markers'):
            f = _fields(el)
            rot = [float(x) for x in f.get('rotation', '0,0,0,1').split(',')]
            pos = [float(x) for x in f.get('translation', '0,0,0').split(',')]
            node = _block_index(f.get('node index'), names, default=0)
            markers.append(JmsMarker(name, '', 0, node,
                                     rot[0], rot[1], rot[2], rot[3],
                                     pos[0] * UNITS, pos[1] * UNITS, pos[2] * UNITS,
                                     float(f.get('radius', 0) or 0)))
    # The REGION name matters: Halo 3 draws a world model through the model tag's
    # variant system, which looks for the permutation by name. The Assault Rifle uses
    # 'standard'; an unnamed JMS region becomes 'default', the variant finds nothing and
    # the weapon renders as thin air -- while first person, which references the render
    # model directly, looks fine. That was the vanishing dropped SAW.
    jm = JmsModel('saw', 0, nodes, [], markers, [REGION], [], [])
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
    # The names now carry a sort key (b_a_gun), so a lookup on the donor's own name has
    # to match on the STEM. Getting this wrong falls back to node 0 and welds the bones.
    def node_of(want):
        if want in by_name:
            return by_name[want]
        stem = want[2:] if want.startswith('b_') else want
        for k, v in by_name.items():
            if k == stem or k.endswith('_' + stem):
                return v
        return None
    gi, mi = node_of(GUN), node_of(MAG)
    if gi is None:
        raise SystemExit('this skeleton has no node for %r -- it has %s.'
                         % (GUN, sorted(by_name)))
    node_map = {0: gi, 1: mi if mi is not None else gi}
    jm = h1.convert(rm, tmpl, node_map)
    if MATERIAL_SECOND_LINE == 'shader name':
        for mat in jm.materials:
            mat.tiff_path = mat.name
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, REGION + '.jms')
    write_jms(out, jm)
    xs = [v.pos_x for v in jm.verts]
    print('wrote %s\n   verts %d, tris %d, x %.1f..%.1f'
          % (out, len(jm.verts), len(jm.tris), min(xs), max(xs)))


if __name__ == '__main__':
    main()
