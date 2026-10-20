r"""Halo 2 CAPACITY + RESIDENCY test (H2_PORT_PLAN.md phase 0.1): stand-in ports, built into one level.

A STAND-IN is a full copy of the SAW port's OWN tag set -- weapon, model, three render models,
collision, bitmaps, shaders, projectile, damage effects, firing effect, HUD + its five bitmaps, both
species' FP animation graphs, its six sounds -- under its own paths, so tool builds it in as a
separate weapon exactly as big as a real port:

    objects\weapons\rifle\saw\...                -> objects\weapons\sz_NN\saw\...
    effects\objects\weapons\rifle\saw\...        -> effects\objects\weapons\sz_NN\saw\...
    objects\characters\<sp>\fp\weapons\rifle\fp_saw\fp_saw -> ...\weapons\sz_NN\fp_saw\fp_saw
    sound\weapons\saw_port\...                   -> sound\weapons\sNN_port\...
    ui\hud\saw                                   -> ui\hud\sNN
    ui\hud\bitmaps\new_hud\...\saw_<x>           -> ...\sNN_<x>

Every replacement keeps the path's LENGTH, so each copied tag is the original with its pooled
(null-terminated) path strings overwritten in place -- nothing in an H2 loose tag moves.

    python h2_size_test_map.py make --count 21          create sz_01..sz_21 in the kit (kept)
    python h2_size_test_map.py distinct --count 21      each stand-in its OWN geometry + bitmaps
                                                        (tool de-duplicates identical resources)
    python h2_size_test_map.py build --level 07a_highcharity --count 21 [--placements] [--control]
    python h2_size_test_map.py clean                    delete every stand-in (out\h2_size_test.json)

`build` (H2 kit lock held): the level's weapons RESOURCE gets one PALETTE entry per stand-in --
and, with --placements, one resident-only placement each (a copy of the SAW's, flags 0x101 = not
placed automatically + at rest) -- the level is built (tool build-cache-file, the h2_batch way),
the result is copied to H2EK\h2_maps_win64_dx11\size_test\<level>.map, and the kit is ALWAYS put
back: the weapons resource byte-identical and the kit's own <level>.map output restored from a
copy. Reported: which stand-ins are resident in the built map, tool's own size lines against a
--control build (the unchanged kit), the file size. `--control` builds the unchanged level only.

Placements are capped by tool at 128 per scenario (MAXIMUM_WEAPON_DATUMS_PER_SCENARIO, read from
tool.exe's block definition, palette 256): 01b_spacestation ships 128 already.
"""
import argparse
import json
import os
import re
import shutil
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import h2_batch  # noqa: E402
import h2_loosetag as L  # noqa: E402
import h2_tagref  # noqa: E402
import kit_lock  # noqa: E402

H2EK = h2_batch.H2EK
TAGS = os.path.join(H2EK, 'tags')
OUT = os.path.join(HERE, 'out')
MANIFEST = os.path.join(OUT, 'h2_size_test.json')
SIZE_DIR = os.path.join(h2_batch.MAPS_OUT, 'size_test')
B = '\\'
SAW_WEAPON = r'objects\weapons\rifle\saw\saw'

#: weapons-resource root blocks (decoded 2026-10-20 on all 13 campaign levels):
#: names 0x00 (0x24), ? 0x18 (0x54), PALETTE 0x24 (0x30: weap tagref + 32 zero bytes),
#: PLACEMENTS 0x30 (0x54: palette index @0, name @2, flags @4 (0x101 = not automatically + at rest))
W_PALETTE, W_PES = 0x24, 0x30
W_PLACE, W_IES = 0x30, 0x54
NOT_AUTOMATIC_AT_REST = 0x101

EXT = {'weap': 'weapon', 'hlmt': 'model', 'mode': 'render_model', 'coll': 'collision_model',
       'phmo': 'physics_model', 'jmad': 'model_animation_graph', 'proj': 'projectile',
       'jpt!': 'damage_effect', 'effe': 'effect', 'bitm': 'bitmap', 'shad': 'shader',
       'nhdt': 'new_hud_definition', 'snd!': 'sound', 'ligh': 'light'}


def standin_path(path, n):
    """The SAW-owned tag path -> stand-in n's (same length, or None when not SAW-owned)."""
    p = path
    for a, b in ((r'weapons\rifle\saw' + B, r'weapons\sz_%02d' % n + B + 'saw' + B),
                 (r'weapons\rifle\fp_saw' + B, r'weapons\sz_%02d' % n + B + 'fp_saw' + B),
                 (r'sound\weapons\saw_port' + B, r'sound\weapons\s%02d_port' % n + B)):
        if a in p:
            p = p.replace(a, b)
    if p.lower() == r'ui\hud\saw':
        p = r'ui\hud\s%02d' % n
    if p.lower().startswith('ui\\hud\\bitmaps\\') and p.rsplit(B, 1)[-1].startswith('saw_'):
        head, tail = p.rsplit(B, 1)
        p = head + B + 's%02d_' % n + tail[4:]
    if p == path:
        return None
    assert len(p) == len(path), (path, p)
    return p


def tag_file(cls, path):
    """The kit file of a reference (class, path)."""
    ext = EXT.get(cls)
    if ext:
        f = os.path.join(TAGS, path + '.' + ext)
        if os.path.exists(f):
            return f
    import glob
    hits = [f for f in glob.glob(os.path.join(TAGS, path + '.*'))
            if '.before' not in f and not f.endswith(('.bak', '._anchor'))]
    return hits[0] if len(hits) == 1 else None


def closure(start=SAW_WEAPON):
    """Every SAW-owned tag reachable from the weapon: [(class, path, file)]."""
    seen, todo, out = set(), [('weap', start)], []
    while todo:
        cls, path = todo.pop()
        if (cls, path.lower()) in seen:
            continue
        seen.add((cls, path.lower()))
        f = tag_file(cls, path)
        if f is None:
            raise SystemExit('no kit file for %s %s' % (cls, path))
        out.append((cls, path, f))
        for c2, p2 in h2_tagref.references(f):
            if standin_path(p2, 1) is not None and (c2, p2.lower()) not in seen:
                todo.append((c2, p2))
    return out


def make(count):
    owned = closure()
    print('the SAW owns %d tags (%.1f MB):' % (len(owned), sum(os.path.getsize(f) for _c, _p, f in owned) / 1e6))
    for cls, path, f in sorted(owned, key=lambda t: t[1]):
        print('   %-5s %s' % (cls, path))
    made = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {'files': []}
    files = set(made['files'])
    for n in range(1, count + 1):
        pairs = [(p, standin_path(p, n)) for _c, p, _f in owned]
        for cls, path, f in owned:
            data = open(f, 'rb').read()
            for old, new in pairs:
                data = data.replace(old.encode('latin-1') + b'\0', new.encode('latin-1') + b'\0')
            dest = os.path.join(TAGS, standin_path(path, n) + os.path.splitext(f)[1])
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, 'wb').write(data)
            files.add(dest)
        print('   stand-in %02d: %d tags' % (n, len(owned)))
    json.dump({'files': sorted(files)}, open(MANIFEST, 'w'), indent=1)
    # PROVE stand-in 01: every reference that was the SAW's is now the stand-in's, nothing else moved
    bad = 0
    for cls, path, f in owned:
        dest = os.path.join(TAGS, standin_path(path, 1) + os.path.splitext(f)[1])
        want = [(c, standin_path(p, 1) or p) for c, p in h2_tagref.references(f)]
        got = h2_tagref.references(dest)
        if want != got:
            bad += 1
            print('   MISMATCH %s: %s' % (dest, [x for x in got if x not in want][:3]))
    print('stand-in 01 references checked against the SAW\'s through tool: %s'
          % ('all %d tags correct' % len(owned) if not bad else '%d WRONG' % bad))
    return not bad


def distinct(count):
    """Give every stand-in its OWN geometry and bitmap data. tool de-duplicates identical
    resources (byte-copied stand-ins added 20 MiB of geometry + 34 MiB of bitmaps to tool's
    counts but 0.3 MiB to the file), so each stand-in's three JMS (one vertex moved by
    n/1000 of a JMS unit) and its three source TIFFs (one corner pixel set to n) are written
    under data/objects/weapons/sz_NN/saw (every vertex / pixel) and re-imported with tool render / tool bitmaps
    into the stand-in's own tags -- the size of a real port, with nothing shared."""
    import subprocess
    import h2_jms
    from PIL import Image
    data = os.path.join(H2EK, 'data')
    src = os.path.join(data, 'objects', 'weapons', 'rifle', 'saw')
    made = json.load(open(MANIFEST))
    files = set(made['files'])
    jms = [('render', 'saw'), (os.path.join('fp_saw', 'render'), 'fp_saw'),
           (os.path.join('fp_saw_dervish', 'render'), 'fp_saw_dervish')]
    tifs = ('saw_gun', 'saw_gun_bump', 'saw_display')

    def tool(*args):
        p = subprocess.run([os.path.join(H2EK, 'tool.exe')] + list(args), cwd=H2EK,
                           capture_output=True, text=True, errors='replace')
        return (p.stdout or '') + (p.stderr or '')

    for n in range(1, count + 1):
        rel = os.path.join('objects', 'weapons', 'sz_%02d' % n, 'saw')
        dst = os.path.join(data, rel)
        for sub, name in jms:
            m = h2_jms.read(os.path.join(src, sub, name + '.jms'))
            # EVERY vertex moves (n/1000 of a JMS unit): one moved vertex left most of the
            # geometry shared (07a: +17 MiB in the file against tool's +54 MiB counted)
            m.verts = [h2_jms.Vertex((v.pos[0] + n / 1000.0, v.pos[1], v.pos[2]), v.normal,
                                     v.influences, v.uvs) for v in m.verts]
            out = os.path.join(dst, sub, name + '.jms')
            os.makedirs(os.path.dirname(out), exist_ok=True)
            h2_jms.write(out, m)
            files.add(out)
        for name in tifs:
            # EVERY pixel's low bits carry n, so no mip level can be shared either
            import numpy as np
            im = Image.open(os.path.join(src, 'bitmaps', name + '.tif'))
            a = np.asarray(im).copy()
            a[..., 0] = (a[..., 0] & 0xE0) | (n & 0x1F)
            im = Image.fromarray(a, im.mode)
            out = os.path.join(dst, 'bitmaps', name + '.tif')
            os.makedirs(os.path.dirname(out), exist_ok=True)
            im.save(out, compression=None)
            files.add(out)
        t0 = time.time()
        for sub in ('', 'fp_saw', 'fp_saw_dervish'):
            before = os.path.getmtime(os.path.join(TAGS, rel, sub, (sub or 'saw') + '.render_model'))
            tool('render', os.path.join(rel, sub) if sub else rel)
            after = os.path.getmtime(os.path.join(TAGS, rel, sub, (sub or 'saw') + '.render_model'))
            if after == before:
                raise SystemExit('tool render wrote no %s render model for stand-in %02d' % (sub or 'world', n))
        tool('bitmaps', os.path.join(rel, 'bitmaps'))
        json.dump({'files': sorted(files)}, open(MANIFEST, 'w'), indent=1)
        print('   stand-in %02d: own geometry + bitmaps (%.0f s)' % (n, time.time() - t0), flush=True)


def clean():
    if not os.path.exists(MANIFEST):
        print('nothing to clean')
        return
    files = json.load(open(MANIFEST))['files']
    for f in files:
        if os.path.exists(f):
            os.remove(f)
    for f in sorted({os.path.dirname(f) for f in files}, key=len, reverse=True):
        try:
            os.removedirs(f)
        except OSError:
            pass
    os.remove(MANIFEST)
    print('removed %d stand-in files' % len(files))


def resource(level):
    return os.path.join(TAGS, 'scenarios', 'solo', level, 'resources',
                        level + '.scenario_weapons_resource')


def weapon_palette(data):
    """(chunk offset, [paths]) of a weapons resource's palette."""
    n = L.root_count(data, W_PALETTE)
    hits = [c for c, _v, cnt, es in L.chunks(data)
            if cnt == n and es == W_PES and bytes(data[c + 16:c + 20]) == b'paew']
    if len(hits) != 1:
        raise SystemExit('weapons palette: %d candidate chunks' % len(hits))
    c = hits[0]
    pool, out = c + 16 + n * W_PES, []
    for i in range(n):
        ln = struct.unpack_from('<I', data, c + 16 + i * W_PES + 8)[0]
        out.append(bytes(data[pool:pool + ln]).decode('latin-1') if ln else '')
        pool += ln + 1 if ln else 0
    return c, out


def weapon_placements(data):
    n = L.root_count(data, W_PLACE)
    hits = [c for c, _v, cnt, es in L.chunks(data) if cnt == n and es == W_IES]
    if n and len(hits) < 1:
        raise SystemExit('weapon placements: no chunk')
    return (hits[-1] if n else None), n


def add_weapons(data, paths, placements=False):
    """Append palette entries (and optionally one resident-only placement each)."""
    added = []
    for p in paths:
        c, have = weapon_palette(data)
        if p in have:
            continue
        idx = L.insert_element(data, W_PALETTE, W_PES, L.make_palette(p, b'weap'), paths=(p,),
                               tagref_offsets=(0x0,), chunk=c)
        added.append((p, idx))
    if placements:
        _c, have = weapon_palette(data)
        saw = have.index(SAW_WEAPON)
        for p, idx in added:
            c, n = weapon_placements(data)
            if n >= 128:
                raise SystemExit('weapon placements already at tool\'s cap (128)')
            src = None
            for i in range(n):
                e = c + 16 + i * W_IES
                if struct.unpack_from('<h', data, e)[0] == saw:
                    src = bytearray(data[e:e + W_IES])
            if src is None:
                raise SystemExit('no SAW placement to copy')
            struct.pack_into('<h', src, 0, idx)
            top = max(struct.unpack_from('<I', data, c + 16 + i * W_IES + 0x28)[0] & 0xFFFF
                      for i in range(n))
            high = struct.unpack_from('<I', src, 0x28)[0] & 0xFFFF0000
            struct.pack_into('<I', src, 0x28, high | ((top + 1) & 0xFFFF))
            L.insert_element(data, W_PLACE, W_IES, bytes(src), chunk=c)
    return added


PATS = {'tags MiB': r'total tag size is\s+([\d.]+)M', 'geometry MiB': r'adding geometry\.\.\.\s*added \d+ for ([\d.]+)M',
        'bitmaps MiB': r'adding bitmaps\.\.\.added \d+ for ([\d.]+)M',
        'sounds MiB': r'adding sounds done \(\d+ sound permutations for ([\d.]+)M',
        'tag count': r'done \((\d+) tags for', 'final MiB': r'final size is ([\d.]+)M',
        'anim bytes': r'cached animation tag data (\d+) bytes', 'seconds': r'total time ([\d.]+)'}


def log_stats(log):
    t = open(log, encoding='latin-1').read().replace('\r', '\n')
    out = {}
    for k, p in PATS.items():
        m = re.findall(p, t)
        out[k] = float(m[-1]) if m else None
    return out


def resident(map_path, names):
    import halo_patch
    m = halo_patch.open_map(map_path, 'Halo 2')
    weaps = {t.get('name') for t in m.tags if t.get('class') == 'weap'}
    return [n for n in names if n in weaps], len(m.tags)


def build(level, count, placements, control):
    level = h2_batch.BY_SHORT.get(level, level)
    res = resource(level)
    kit_map = os.path.join(h2_batch.MAPS_OUT, level + '.map')
    keep_res = res + '.size_test_keep'
    keep_map = kit_map + '.size_test_keep'
    logdir = os.path.join(OUT, 'h2logs_size_test', 'control' if control else 'test')
    os.makedirs(logdir, exist_ok=True)
    names = [standin_path(SAW_WEAPON, n) for n in range(1, count + 1)]
    with kit_lock.held('h2_size_test_map %s %s' % (level, 'control' if control else count),
                       owner='phase0', kit='h2'):
        shutil.copy2(res, keep_res)
        if os.path.exists(kit_map):
            shutil.copy2(kit_map, keep_map)
        try:
            if not control:
                for nm in names:
                    if not os.path.exists(os.path.join(TAGS, nm + '.weapon')):
                        raise SystemExit('%s missing -- run make --count %d first' % (nm, count))
                data = bytearray(open(res, 'rb').read())
                added = add_weapons(data, names, placements)
                open(res, 'wb').write(bytes(data))
                _c, pal = weapon_palette(data)
                print('%s: +%d palette entries (now %d)%s' % (level, len(added), len(pal),
                      ', +%d placements (now %d)' % (len(added), weapon_placements(data)[1])
                      if placements else ', NO placements'))
            t0 = time.time()
            ok, msg = h2_batch.build_cache(level, logdir)
            print('build: %s %s (%.0f s)' % ('ok' if ok else 'FAILED', msg, time.time() - t0))
            if ok:
                os.makedirs(SIZE_DIR, exist_ok=True)
                dest = os.path.join(SIZE_DIR, '%s%s.map' % (level, '.control' if control else ''))
                shutil.copy2(kit_map, dest)
        finally:
            shutil.copy2(keep_res, res)
            os.remove(keep_res)
            if os.path.exists(keep_map):
                shutil.copy2(keep_map, kit_map)
                os.remove(keep_map)
            print('kit restored: weapons resource + the kit\'s %s.map output put back' % level)
    if not ok:
        raise SystemExit(1)
    stats = log_stats(os.path.join(logdir, level + '.build.log'))
    have, ntags = resident(dest, names + [SAW_WEAPON])
    rec = {'level': level, 'count': 0 if control else count, 'placements': placements,
           'stats': stats, 'file_bytes': os.path.getsize(dest), 'resident': have,
           'when': time.strftime('%Y-%m-%d %H:%M')}
    runs = os.path.join(OUT, 'h2_size_test_runs.json')
    allr = json.load(open(runs)) if os.path.exists(runs) else []
    allr.append(rec)
    json.dump(allr, open(runs, 'w'), indent=1)
    print('built map %s: %.1f MiB, %d tags' % (dest, os.path.getsize(dest) / 2**20, ntags))
    print('resident: SAW %s; stand-ins %d of %d' % ('yes' if SAW_WEAPON in have else 'NO',
                                                     len([h for h in have if h != SAW_WEAPON]),
                                                     0 if control else count))
    for k, v in stats.items():
        print('   %-14s %s' % (k, v))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('verb', choices=('make', 'distinct', 'build', 'clean', 'closure'))
    ap.add_argument('--count', type=int, default=21)
    ap.add_argument('--level', default='07a_highcharity')
    ap.add_argument('--placements', action='store_true')
    ap.add_argument('--control', action='store_true')
    a = ap.parse_args()
    if a.verb == 'closure':
        for cls, path, f in closure():
            print('%-5s %-70s %d' % (cls, path, os.path.getsize(f)))
    elif a.verb == 'make':
        sys.exit(0 if make(a.count) else 1)
    elif a.verb == 'distinct':
        import kit_lock
        with kit_lock.held('h2_size_test_map distinct %d' % a.count, owner='phase0', kit='h2'):
            distinct(a.count)
    elif a.verb == 'clean':
        clean()
    else:
        build(a.level, a.count, a.placements, a.control)


if __name__ == '__main__':
    main()
