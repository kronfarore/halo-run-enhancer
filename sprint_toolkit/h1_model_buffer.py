r"""Halo 1's 32 MiB MODEL-BUFFER CAP (found 2026-10-14, the C2 Suppressor; memory h1-model-buffer-32mib-cap):
`tool build-cache-file` crashes with a bare EXCEPTION_ACCESS_VIOLATION right after "streaming model
vertex and index buffers..." once a map's MODEL vertices x 68 + strip indices x 2 pass 32 MiB (the
crash registers: EBP = the total model vertex count). tool's own "vbuf" line does not show it.
Read-only.

    python h1_model_buffer.py map <built .map>       the map's model buffer: total, margin, largest models
    python h1_model_buffer.py ports                  each port's world + FP gbxmodel cost (HCEEK tags),
                                                     and what world = FP sharing would save

`map` names the map's gbxmodels from its own tag table and sums their HCEEK tags (every geometry's
parts) -- the kit tags must be the ones the map was built from.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.mod2 import mod2_def  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
CAP = 32 * 1024 * 1024


def cost(rel):
    """(vertices, indices) of an HCEEK gbxmodel, or None."""
    if not rel:
        return None
    p = os.path.join(TAGS, rel + '.gbxmodel')
    if not os.path.exists(p):
        return None
    d = mod2_def.build(filepath=p).data.tagdata
    v = sum(len(x.uncompressed_vertices.STEPTREE) for g in d.geometries.STEPTREE for x in g.parts.STEPTREE)
    i = sum(len(x.triangles.STEPTREE) * 3 for g in d.geometries.STEPTREE for x in g.parts.STEPTREE)
    return v, i


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    m = sub.add_parser('map')
    m.add_argument('map')
    sub.add_parser('ports')
    a = ap.parse_args()
    if a.cmd == 'map':
        import halo_patch
        mp = halo_patch.open_map(a.map, 'Halo 1')
        rows = []
        for name, _b in mp.find_tags('mod2', '*'):
            c = cost(name)
            if c:
                rows.append((c[0] * 68 + c[1] * 2, c[0], c[1], name))
        tv, ti = sum(r[1] for r in rows), sum(r[2] for r in rows)
        b = tv * 68 + ti * 2
        print('%d models: %d vertices, %d indices = %.2f MiB of 32 (%.2f MiB left)'
              % (len(rows), tv, ti, b / 2 ** 20, (CAP - b) / 2 ** 20))
        for r in sorted(rows, reverse=True)[:10]:
            print('   %6.3f MiB  %6d v  %6d i  %s' % (r[0] / 2 ** 20, r[1], r[2], r[3]))
        return
    import ports_h1
    tot = save = 0
    for key, P in ports_h1.all_ports():
        pk = P.get('pickable') or {}
        w, f = pk.get('world_model'), pk.get('fp_model')
        cw, cf = cost(w), (None if f == w else cost(f))
        if cw is None and cf is None:
            continue
        bw = cw[0] * 68 + cw[1] * 2 if cw else 0
        bf = cf[0] * 68 + cf[1] * 2 if cf else 0
        one = (P.get('model') or {}).get('world') == (P.get('model') or {}).get('fp')
        sv = min(bw, bf) if (one and cf) else 0
        tot += bw + bf
        save += sv
        print('%-18s %-12s world %.2f MiB  fp %s%s' % (
            key, P.get('status'), bw / 2 ** 20,
            'shared' if f == w else '%.2f MiB' % (bf / 2 ** 20),
            '  (sharing would save %.2f)' % (sv / 2 ** 20) if sv else ''))
    print('ALL PORTS %.2f MiB in every map they are resident in; sharing world = FP would save %.2f MiB'
          % (tot / 2 ** 20, save / 2 ** 20))


if __name__ == '__main__':
    main()
