r"""Dump a Halo 4 HUD screen (.cui_screen): template instantiations, components (type,
name, parent, template index), one overlay's component properties, and the property
bindings. Used to map the Beam Rifle scope before the Focus Rifle port's own Reach scope
template was built (h4_reach_scope.py, 2026-10-02).

    python h4_cusc_dump.py <screen.cui_screen> [--overlay N] [--component NAME]

Path relative to H4EK\tags. `tool export-tag-to-xml`, no Blender. Reading notes:
  * in a weapon HUD, a TEMPLATE-INSTANCE component row's `type` is the template
    component's NAME, not its widget class (boot 22);
  * an unset property is not the same as 0 (prop_alpha_blend_mode, boot 24);
  * `component indices` is sorted by string id number.
"""
import argparse
import os
import re
import subprocess

H4EK = r'F:\SteamLibrary\steamapps\common\H4EK'


def export(tag):
    out = os.path.join(os.environ.get('TEMP', '.'), '_h4_cusc_dump.xml')
    if os.path.exists(out):
        os.remove(out)
    subprocess.run([os.path.join(H4EK, 'tool.exe'), 'export-tag-to-xml',
                    os.path.join(H4EK, 'tags', tag), out], cwd=H4EK, capture_output=True)
    if not os.path.exists(out) or not os.path.getsize(out):
        raise SystemExit('could not export %s' % tag)
    return open(out, encoding='utf-8', errors='replace').read()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('screen')
    ap.add_argument('--overlay', type=int, default=0)
    ap.add_argument('--component', help='only this component in the overlay listing')
    a = ap.parse_args()
    s = export(a.screen)
    print('templates:', re.findall(r'name="screen reference" value="([^"]*)"', s))
    i, j = s.find('<block name="components"'), s.find('<block name="component indices"')
    rows = re.findall(r'<field name="type" value="([^"]*)"[^>]*/>\s*<field name="name" value="([^"]*)"'
                      r'[^>]*/>\s*<field name="parent" value="([^"]*)"[^>]*/>\s*<field name="flags"'
                      r' value="([^"]*)"[^>]*/>\s*<field name="template instantiation index" value="([^"]*)"',
                      s[i:j])
    print('components (%d):' % len(rows))
    for n, (t, nm, p, _f, ti) in enumerate(rows):
        print('  %3d %-34s %-34s parent %-30s ti %s' % (n, t[:34], nm[:34], p[:30], ti.strip(',')))
    o = s.find('<block name="overlays"')
    parts = re.split(r'<field name="resolution" value="([^"]*)"', s[o:])
    if len(parts) > 2 * a.overlay + 1:
        res, body = parts[2 * a.overlay + 1], parts[2 * a.overlay + 2]
        print('overlay %d (%s):' % (a.overlay, res))
        a_ = body.find('<block name="animations"')
        body = body[:a_]
        # a component element and its own `name` field share an indentation step; its
        # property elements sit deeper, so split on the component indentation only
        heads = list(re.finditer(r'^( +)<element index="\d+" name="([^"]+)">\n\1    <field name="name" '
                                 r'value="\2"', body, re.M))
        heads = [h for h in heads if len(h.group(1)) == len(heads[0].group(1))] if heads else []
        for k, h in enumerate(heads):
            nm = h.group(2)
            if a.component and nm != a.component:
                continue
            el = body[h.start():heads[k + 1].start() if k + 1 < len(heads) else len(body)]
            props = re.findall(r'name="name" value="(prop_[a-z_]+|_auto_[a-z_]+)"[^>]*/>\s*'
                               r'<field name="value" value="([^"]*)"', el)
            print('  %-34s %s' % (nm[:34], ', '.join('%s=%s' % (k2, v[:40]) for k2, v in props)))
    b = s.find('<block name="property bindings"')
    binds = re.findall(r'source component name" value="([^"]*)".*?\n.*?source property name" value="([^"]*)"'
                       r'.*?\n.*?target component name" value="([^"]*)".*?\n.*?target property name" value="([^"]*)"',
                       s[b:])
    print('bindings (%d):' % len(binds))
    for sc, sp, tc, tp in binds:
        print('  %s.%s -> %s.%s' % (sc, sp, tc, tp))


if __name__ == '__main__':
    main()
