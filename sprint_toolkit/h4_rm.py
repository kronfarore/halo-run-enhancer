"""Read an H4EK render_model XML export into plain Python: nodes (default pose), markers,
materials, parts (index ranges per material) and raw vertices/indices of every mesh."""
import re
import xml.etree.ElementTree as ET


def _f(el, name):
    f = el.find("field[@name='%s']" % name)
    return f.get('value') if f is not None else None


def _b(el, name):
    b = el.find("block[@name='%s']" % name)
    return list(b) if b is not None else []


def _vec(s):
    return tuple(float(x) for x in s.split(',')) if s else ()


def _int(s):
    return int(str(s).split(',')[-1]) if s not in (None, '') else -1


def load(path):
    txt = open(path, encoding='utf-8', errors='replace').read()
    txt = re.sub(r'value="<([^"<>]*)>"', 'value="[unavailable]"', txt)
    root = ET.fromstring(txt)
    out = {'nodes': [], 'markers': [], 'materials': [], 'meshes': []}
    for n in _b(root, 'nodes'):
        out['nodes'].append({'name': _f(n, 'name'), 'parent': _int(_f(n, 'parent node')),
                             'pos': _vec(_f(n, 'default translation')),
                             'rot': _vec(_f(n, 'default rotation'))})
    for g in _b(root, 'marker groups'):
        for m in _b(g, 'markers'):
            out['markers'].append({'name': _f(g, 'name'), 'node': _int(_f(m, 'node index')),
                                   'pos': _vec(_f(m, 'translation')),
                                   'rot': _vec(_f(m, 'rotation'))})
    for m in _b(root, 'materials'):
        rm = m.find("field[@name='render method']")
        out['materials'].append(rm.get('value').split(',')[0] if rm is not None else '')
    ci = _b(root, 'compression info')
    if ci:
        out['compression'] = {'pos0': _vec(_f(ci[0], 'position bounds 0')),
                              'pos1': _vec(_f(ci[0], 'position bounds 1')),
                              'uv0': _vec(_f(ci[0], 'texcoord bounds 0')),
                              'uv1': _vec(_f(ci[0], 'texcoord bounds 1'))}
    temps = _b(root, 'per mesh temporary')
    for mi, me in enumerate(_b(root, 'meshes')):
        parts = [{'material': _int(_f(p, 'render method index')),
                  'start': _int(_f(p, 'index start')), 'count': _int(_f(p, 'index count'))}
                 for p in _b(me, 'parts')]
        mesh = {'parts': parts, 'index_type': _f(me, 'index buffer type'),
                'verts': [], 'indices': []}
        if mi < len(temps):
            for v in _b(temps[mi], 'raw vertices'):
                ni = [_int(f.get('value')) for f in v.findall("field[@name='node index']")]
                nw = [float(f.get('value')) for f in v.findall("field[@name='node weight']")]
                mesh['verts'].append({'pos': _vec(_f(v, 'position')), 'uv': _vec(_f(v, 'texcoord')),
                                      'n': _vec(_f(v, 'normal')), 'nodes': ni, 'w': nw})
            mesh['indices'] = [_int(_f(i, 'word')) if _f(i, 'word') is not None else
                               _int(i.find('field').get('value'))
                               for i in _b(temps[mi], 'raw indices')]
        out['meshes'].append(mesh)
    return out


if __name__ == '__main__':
    import sys
    rm = load(sys.argv[1])
    for n in rm['nodes']:
        print('node', n)
    for m in rm['markers']:
        print('marker %-24s node %d pos %s' % (m['name'], m['node'], tuple(round(x * 100, 2) for x in m['pos'])))
    me = rm['meshes'][0]
    print('parts', me['parts'], 'index type', me['index_type'], 'idx', len(me['indices']), me['indices'][:12])
    for node in (0, 1):
        ps = [v['pos'] for v in me['verts'] if v['nodes'][0] == node]
        if ps:
            print('node %d verts %d bounds x100:' % (node, len(ps)),
                  [(round(min(p[k] for p in ps) * 100, 2), round(max(p[k] for p in ps) * 100, 2)) for k in range(3)])
