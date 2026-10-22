r"""Closing check 10 for HALO 2 ports, THE MUZZLE-FLASH RULE (PORTING "When a port is done"; Halo 1's
h1_effect_particles.py): the port's FIRST-PERSON flash beside its SOURCE weapon's and the DONOR's it
was cloned from, before boot 1. Read-only (tool export-tag-to-xml through ttk_common.flatten).

    python h2_effect_particles.py <key> [--all]          the port, its donor, its source (config)
    python h2_effect_particles.py --effect H2EK:<path.effect> --effect H3EK:<path.effect> ...

Per particle system (first person only unless --all): the particle tag, camera mode, the location
MARKER, and per emitter:
  HALO 2   count, lifespan, SIZE, emission radius / angle (the emitter's function constants: Halo 2
           stores each property as a function; byte 0 = its type, the two floats at +4 / +8 its
           range), translational offset (wu, along the marker), relative direction, shape.
           SIZE IS NOT IN WORLD UNITS: the particle tag scales it again (Bungie's SMG first-person
           flash reads 1.5-2.0, the BR's 0.05-0.08) -- compare a port with its DONOR and with
           Bungie's stock flashes, not with the source's number.
  HALO 3 / ODST / REACH / HALO 4   the emitter's `bounding radius estimate` (wu) -- the source
           side's size, as h4_effect_particles.py reads it.
  HALO 1   h1_effect_particles.particles (count, radius, offset, direction).
Reading it: the port's systems should sit at the source's markers in the same NUMBER and
direction; a donor's off-axis sprites the source lacks are dropped (the Halo 1 DMR rule), and
the size judged against the donor's / Bungie's flashes of the same role.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ttk_common as tc  # noqa: E402

KITS = {'Halo 3': 'H3EK', 'Halo 3: ODST': 'H3ODSTEK', 'Halo Reach': 'HREK', 'Halo 4': 'H4EK'}
H2_PROPS = ('count', 'lifespan', 'velocity', 'angular velocity', 'size', 'tint', 'alpha',
            'emission radius', 'emission angle')
SHOW = (0, 1, 4, 7, 8)


def _fn(v, key, prime):
    """(type, lo, hi) of a Halo 2 function property: its data bytes."""
    b, i = [], 0
    while (key + 'data/[%d]/value' % i + prime) in v:
        b.append(int(v[key + 'data/[%d]/value' % i + prime][1]) & 255)
        i += 1
    b = bytes(b)
    if len(b) < 12:
        return None
    return (b[0],) + struct.unpack_from('<2f', b, 4)


def h2_systems(path):
    v = tc.flatten('H2EK', path)
    locs = [v[k][1] for k in sorted(k for k in v if k.startswith('locations/') and k.endswith('marker name'))]
    out = []
    for ev in range(int(v.get('events/#count', ('', '0'))[1])):
        for s in range(int(v.get('events/[%d]/particle systems/#count' % ev, ('', '0'))[1])):
            p = 'events/[%d]/particle systems/[%d]/' % (ev, s)
            loc = v.get(p + 'location', ('', ''))[1]
            loc = locs[int(loc)] if loc.lstrip('-').isdigit() and 0 <= int(loc) < len(locs) else \
                (locs[0] if len(locs) == 1 else (loc or '?'))
            ems = []
            for e in range(int(v.get(p + 'emitters/#count', ('', '0'))[1])):
                q = p + 'emitters/[%d]/' % e
                fns = [_fn(v, q, "'" * k) for k in range(len(H2_PROPS))]
                ems.append(dict(fns=fns, shape=v.get(q + 'emission shape', ('', ''))[1],
                                offset=v.get(q + 'translational offset', ('', ''))[1],
                                direction=v.get(q + 'relative direction', ('', ''))[1]))
            out.append(dict(event=ev, particle=v[p + 'particle'][1].split('\\')[-1], marker=loc,
                            camera=v.get(p + 'camera mode', ('', ''))[1], emitters=ems))
    return locs, out


def xml_systems(kit, path):
    v = tc.flatten(kit, path)
    locs = [v[k][1] for k in sorted(k for k in v if k.startswith('locations/') and k.endswith('marker name'))]
    out = []
    for ev in range(int(v.get('events/#count', ('', '0'))[1])):
        for s in range(int(v.get('events/[%d]/particle systems/#count' % ev, ('', '0'))[1])):
            p = 'events/[%d]/particle systems/[%d]/' % (ev, s)
            li = v.get(p + 'location', ('', ',-1'))[1].split(',')[-1]
            loc = locs[int(li)] if li.lstrip('-').isdigit() and 0 <= int(li) < len(locs) else li
            radii = [float(v[p + 'emitters/[%d]/bounding radius estimate' % e][1])
                     for e in range(int(v.get(p + 'emitters/#count', ('', '0'))[1]))
                     if (p + 'emitters/[%d]/bounding radius estimate' % e) in v]
            out.append(dict(event=ev, particle=v[p + 'particle'][1].split(',')[0].split('\\')[-1],
                            marker=loc, camera=v.get(p + 'camera mode', ('', ''))[1], radii=radii))
    return locs, out


def first_person(cam):
    return 'third' not in cam or 'first' in cam


def show(label, kit, path, everything):
    print('== %s  [%s] %s' % (label, kit, path))
    if kit == 'HCEEK':
        import h1_effect_particles as H1
        for ev, tag, loc, cnt, rad, d, off, cone, cam in H1.particles(path):
            if everything or first_person(cam.replace('_', ' ')):
                print('  ev%d %-30s %-16s count %-10s radius %.3f-%.3f dir %+.2f/%+.2f off %+.3f/%+.3f/%+.3f %s'
                      % (ev, tag, loc, cnt, rad[0], rad[1], d[0], d[1], off[0], off[1], off[2], cam))
        return
    if kit == 'H2EK':
        locs, systems = h2_systems(path)
    else:
        locs, systems = xml_systems(kit, path)
    print('   markers %s' % locs)
    for s in systems:
        if not everything and not first_person(s['camera']):
            continue
        print('  ev%d %-30s %-16s %s' % (s['event'], s['particle'][:30], s['marker'], s['camera']))
        if kit != 'H2EK':
            print('      bounding radius estimate %s wu' % [round(r, 3) for r in s['radii']])
            continue
        for k, e in enumerate(s['emitters']):
            vals = ['%s %s' % (H2_PROPS[i], '%.3g-%.3g' % e['fns'][i][1:] if e['fns'][i] else '-')
                    for i in SHOW]
            print('      e%d %s; offset %s dir %s %s' % (k, ', '.join(vals), e['offset'], e['direction'], e['shape']))


def weapon_effects(kit, weapon):
    """The firing effects a weapon's barrels name."""
    v = tc.flatten(kit, weapon + '.weapon')
    out = []
    for k, (typ, val) in v.items():
        if typ == 'tag reference' and val and k.split('/')[-1].rstrip("'") == 'firing effect':
            p = val.split(',')[0]
            if p and p not in out:
                out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key', nargs='?')
    ap.add_argument('--effect', action='append', default=[], help='KIT:path.effect (H2EK / H3EK / HREK / H4EK / HCEEK)')
    ap.add_argument('--all', action='store_true', help='third-person systems too')
    a = ap.parse_args()
    if a.key:
        import ports_h2
        cfg = ports_h2.load(a.key)
        wtag = (cfg.get('catalog') or {}).get('weapon_tag') or ''
        if not wtag:
            import json
            sys.path.insert(1, os.path.dirname(HERE))
            import weapon_ports as W
            cat = {p['weapon']: p for p in json.load(open(os.path.join(os.path.dirname(HERE),
                                                                       'weapon_ports_catalog.json'))).get('Halo 2') or ()}
            wtag = W.weap_path(cat[cfg['name']]) if cfg.get('name') in cat else ''
        donor = (cfg.get('donor') or {}).get('weapon')
        for label, kit, weap in (('PORT %s' % cfg.get('name'), 'H2EK', wtag), ('DONOR', 'H2EK', donor)):
            for fx in weapon_effects(kit, weap) if weap else ():
                show(label, kit, fx + '.effect', a.all)
        src, stag = cfg.get('source'), cfg.get('source_tag')
        if src == 'Halo 1' and stag:
            import h1_effect_particles as H1
            from reclaimer.hek.defs.weap import weap_def
            w = weap_def.build(filepath=os.path.join(H1.TAGS, stag + '.weapon')).data.tagdata.weap_attrs
            for t in w.triggers.STEPTREE:
                for f in t.firing_effects.STEPTREE:
                    if f.firing_effect.filepath:
                        show('SOURCE %s' % src, 'HCEEK', f.firing_effect.filepath, a.all)
        elif src in KITS and stag:
            for fx in weapon_effects(KITS[src], stag):
                show('SOURCE %s' % src, KITS[src], fx + '.effect', a.all)
        else:
            print('(no source effect: source %r, source_tag %r)' % (src, stag))
    for spec in a.effect:
        kit, path = spec.split(':', 1)
        show('EFFECT', kit, path, a.all)


if __name__ == '__main__':
    main()
