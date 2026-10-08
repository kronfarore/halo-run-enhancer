r"""The close-out FULL FIELD DIFF of a Halo 1 port against what it was copied from (the BR's
rule, 2026-10-07: every difference must trace to a decision written in the config).

Every pair comes from the port's config (ports_h1/<key>.py):
  pickable  weapon vs template; bullet projectile / damage (own vs source); melee;
            sound_effects (own effect vs `copy_from`, else the template's); hud (vs donor)
  model     every shader vs `template`; meters vs their `from`
Read through port_field_audit.flatten (Reclaimer). Halo 1 has no XML export, so this is
also kit_tag_diff's Halo 1 form: run it after the last writes.

    python h1_port_template_diff.py covenant_carbine [--only weapon,hud]
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_field_audit as pfa  # noqa: E402
import ports_h1  # noqa: E402

B = '\\'
TAGS = os.path.join(pfa.STEAM, 'HCEEK', 'tags')


def pairs(p):
    w = p['pickable']
    out = [('weapon', w['weapon'] + '.weapon', w['template'] + '.weapon')]
    for kind, ext in (('projectile', '.projectile'), ('damage', '.damage_effect')):
        src, own = (w.get('bullet') or {}).get(kind, (None, None))
        if own:
            out.append(('bullet ' + kind, own + ext, src + ext))
    if w.get('melee'):
        out.append(('melee', w['melee'][1] + '.damage_effect', w['melee'][0] + '.damage_effect'))
    for field, (src, own, _swaps, *opt) in (w.get('sound_effects') or {}).items():
        base = (opt[0] if opt else {}).get('copy_from', src)
        out.append((field, own + '.effect', base + '.effect'))
    h = w.get('hud') or {}
    if h.get('out'):
        out.append(('hud', h['out'] + '.weapon_hud_interface', h['donor'] + '.weapon_hud_interface'))
    m = p.get('model') or {}
    for name in m.get('shaders', {}):
        out.append(('shader ' + name, m['dir'] + B + 'shaders' + B + name + '.shader_model',
                    m['template'] + '.shader_model'))
    for name, M in (m.get('meters') or {}).items():
        out.append(('meter ' + name, m['dir'] + B + 'shaders' + B + name + '.shader_transparent_meter',
                    M['from'] + '.shader_transparent_meter'))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('port', help='ports_h1 config key')
    ap.add_argument('--only', help='comma list of pair labels (prefix match)')
    a = ap.parse_args()
    only = [x.strip() for x in (a.only or '').split(',') if x.strip()]
    total = 0
    for label, port, src in pairs(ports_h1.load(a.port)):
        if only and not any(label.startswith(o) for o in only):
            continue
        if not os.path.exists(os.path.join(TAGS, port)):
            print('== %s: %s MISSING' % (label, port))
            continue
        x, y = pfa.flatten('HCEEK', port), pfa.flatten('HCEEK', src)
        keys = sorted(set(x) | set(y))
        diff = [(k, y.get(k, ('', '-'))[1], x.get(k, ('', '-'))[1]) for k in keys if x.get(k) != y.get(k)]
        total += len(diff)
        print('== %-24s %s  vs  %s  (%d of %d differ)' % (label, port, src, len(diff), len(keys)))
        for k, was, now in diff:
            print('   %-66s %-30s -> %s' % (k[:66], str(was)[:30], str(now)[:70]))
    print('\n%d difference(s): trace each to a decision in the config' % total)


if __name__ == '__main__':
    main()
