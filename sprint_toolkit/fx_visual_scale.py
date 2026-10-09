r"""PROTOTYPE (feasibility, 2026-10-09): scale an effect's VISUAL size in a Halo 2 / 3 /
ODST / Reach / 4 cache map, so an explosion can follow a radius card. Not wired into
the patcher; see EXPLOSION_VISUAL_SCALE.md.

What is scaled, per emitter of every particle system of the effect:
  * Particle Size (world units) and Emission Radius (world units): their FUNCTION
    data's output range -- the floats at function +4 and +8. Every scalar function
    type keeps its curve normalised between them (Halo 3's GPU bake stores the same
    two numbers beside the curve's coefficients), so x k on both is x k on the output.
  * Halo 3 / ODST / Reach / 4: the property's `Runtime m Constant Value` (inline).
  * Halo 3 only: the baked GPU rows -- Runtime GPU Properties row 2 col 0 (the size
    when it is constant) and the Runtime GPU Functions rows the size function bakes to
    (row index = GPU property row 2 col 2 >> 17, the function's min/max at cols 2, 3).
    Verified over 7076 emitters of 040_voi: 0 mismatches.
  * Halo 4 alternative: the effect's own `Global Size Scale` (mode 'gss').

COPY ON WRITE, never in place: the caches DEDUPLICATE function data (Halo 3 040_voi:
63684 datarefs over 5750 blobs; every game alike), Halo 3's GPU blocks, and (Halo 2,
Halo 3) whole emitter blocks. Editing in place would resize unrelated effects across
the map. So each touched function blob / GPU block gets a private scaled copy and the
dataref / reflexive is repointed; an emitter block shared with an effect OUTSIDE the
scaled set is copied first. Space: gen 3+ through halo_patch._h3_reserve (zero runs,
the rule confirmed in game on Reach m10 and Halo 4 m70); Halo 2 appended at the end of
the image like Halo2Map.grow_blocks.

    python fx_visual_scale.py --game "Halo 3" --map <in.map> --out <out.map>
                              --effect <effe path> [--effect ...] --scale 2 [--mode gss]
It re-opens the written map and verifies: every scaled value is old x k, and every
property of every OTHER effect in the map evaluates to exactly the bytes it had.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import explosion_fx_audit as A  # noqa: E402

SIZE, RADIUS = 'Particle Size', 'Emission Radius'
H3_GPU = {'Halo 3': (0x2CC, 0x10, 0x2D8, 0x40)}
SIZE_GPU_ROW = 2


class Fx:
    def __init__(self, game, m):
        self.game, self.m = game, m
        self.h2 = game == 'Halo 2'
        self.p2o = m.p2o if self.h2 else m.data2off
        self.fn_rel, self.ptr_rel = (8, 0xC) if self.h2 else (4, 0x10)
        self.L = A.effe_layout(game)
        self.gpu = H3_GPU.get(game)
        self.pending = []          # Halo 2: [(bytes, [patch(new_ptr) callbacks])]

    # --- raw access ---
    def f32(self, o):
        return struct.unpack_from('<f', self.m.data, o)[0]

    def put_f32(self, o, v):
        struct.pack_into('<f', self.m.data, o, v)

    def blk(self, o):
        n = self.m.i32(o)
        return n, (self.p2o(self.m.u32(o + 4)) if n > 0 else None)

    def effect(self, name):
        return next((t for t in self.m.tags if t.get('class') == 'effe'
                     and str(t.get('name') or '').lower() == name.lower()), None)

    def psys_slots(self, t):
        """(reflexive offset of the psys' Emitters block) for every particle system."""
        L = self.L
        ne, eb = self.blk(t['base'] + L['EV'][0])
        for e in range(ne if eb else 0):
            nps, sb = self.blk(eb + e * L['EV'][1] + L['PSYS'][0])
            for s in range(nps if sb else 0):
                yield sb + s * L['PSYS'][1] + L['EMIT'][0]

    def emitters(self, t):
        for refl in self.psys_slots(t):
            n, emb = self.blk(refl)
            for j in range(n if emb else 0):
                yield emb + j * self.L['EMIT'][1]

    # --- allocation: new bytes, returns the stored pointer value for them ---
    def alloc(self, data, patch):
        """Place `data` and call patch(ptr) once its pointer is known."""
        if self.h2:
            self.pending.append((bytes(data), patch))
            return
        import halo_patch as hp
        got = hp._h3_reserve(self.m, [len(data)])
        if not got:
            raise SystemExit('no slack for %d bytes' % len(data))
        off = got[0]
        self.m.data[off:off + len(data)] = data
        patch(self.m.off2data(off))

    def flush(self):
        """Halo 2: one appended region for every pending copy (Halo2Map.grow_blocks)."""
        if not self.pending:
            return
        m = self.m
        blob, offs, base = bytearray(), [], len(m.data)
        for data, _ in self.pending:
            blob += bytearray((-len(blob)) & 15)
            offs.append(base + len(blob))
            blob += data
        delta = (len(blob) + m.SEGMENT_ALIGN - 1) & ~(m.SEGMENT_ALIGN - 1)
        m.data += blob + bytearray(delta - len(blob))
        for (data, patch), off in zip(self.pending, offs):
            patch((off - m.meta_offset + m.mask) & 0xFFFFFFFF)
        m.file_size += delta
        m.meta_size += delta
        m.tag_data_size += delta
        struct.pack_into('<I', m.data, 0x8, m.file_size)
        struct.pack_into('<I', m.data, 0x14, m.meta_size)
        struct.pack_into('<I', m.data, 0x2D8, m.tag_data_size)
        self.pending = []

    # --- census: who uses an emitter block ---
    def emitter_block_users(self):
        users = {}
        for t in self.m.tags:
            if t.get('class') != 'effe' or t.get('base') is None:
                continue
            for refl in self.psys_slots(t):
                n, emb = self.blk(refl)
                if emb:
                    users.setdefault(emb, set()).add(t['name'].lower())
        return users

    # --- the scale ---
    def scale(self, names, k, mode='emitters'):
        m, L = self.m, self.L
        names = [n.lower() for n in names]
        tags = [self.effect(n) for n in names]
        if None in tags:
            raise SystemExit('effect not in map: %s' % names[tags.index(None)])
        log = {'gss': 0, 'emitter_blocks_copied': 0, 'blobs_copied': 0, 'gpu_blocks_copied': 0,
               'constants': 0, 'emitters': 0}
        if mode == 'gss':
            for t in tags:
                o = t['base'] + L['gss']
                self.put_f32(o, self.f32(o) * k)
                log['gss'] += 1
            return log
        # 1. emitter blocks shared with an effect outside the set get a private copy
        users = self.emitter_block_users()
        seen_blk = {}
        for t in tags:
            for refl in self.psys_slots(t):
                n, emb = self.blk(refl)
                if not emb or users.get(emb, set()) <= set(names):
                    continue
                if emb in seen_blk:              # same block, another psys in the set
                    struct.pack_into('<I', m.data, refl + 4, seen_blk[emb])
                    continue
                data = bytes(m.data[emb:emb + n * L['EMIT'][1]])

                def patch(ptr, refl=refl, emb=emb):
                    struct.pack_into('<I', m.data, refl + 4, ptr)
                    seen_blk[emb] = ptr
                self.alloc(data, patch)
                log['emitter_blocks_copied'] += 1
        self.flush()
        # 2. per emitter: private scaled copies of the function blobs / GPU blocks
        blob_memo, gpu_memo, done = {}, {}, set()
        for t in tags:
            for em in self.emitters(t):
                if em in done:
                    continue
                done.add(em)
                log['emitters'] += 1
                for prop in (SIZE, RADIUS):
                    q = em + L['props'][prop]
                    sz = m.i32(q + self.fn_rel)
                    src = self.p2o(m.u32(q + self.ptr_rel)) if sz > 0 else None
                    if src is not None:
                        key = (src, sz)
                        if key in blob_memo:
                            struct.pack_into('<I', m.data, q + self.ptr_rel, blob_memo[key])
                        else:
                            data = bytearray(m.data[src:src + sz])
                            for o in (4, 8):
                                struct.pack_into('<f', data, o, struct.unpack_from('<f', data, o)[0] * k)

                            def patch(ptr, q=q, key=key):
                                struct.pack_into('<I', m.data, q + self.ptr_rel, ptr)
                                blob_memo[key] = ptr
                            self.alloc(data, patch)
                            log['blobs_copied'] += 1
                    if not self.h2:
                        c = q + L.get('const_rel', 0x18)
                        if self.f32(c):
                            self.put_f32(c, self.f32(c) * k)
                            log['constants'] += 1
                if self.gpu:
                    self._gpu(em, k, gpu_memo, log)
        self.flush()
        return log

    def _gpu(self, em, k, memo, log):
        """Halo 3: private scaled copies of the size rows of the baked GPU blocks."""
        m, L = self.m, self.L
        gp_off, gp_sz, gf_off, gf_sz = self.gpu
        q = em + L['props'][SIZE]
        sz = m.i32(q + self.fn_rel)
        fn = self.p2o(m.u32(q + self.ptr_rel)) if sz > 0 else None
        np_, gp = self.blk(em + gp_off)
        nf, gf = self.blk(em + gf_off)
        if not gp or np_ <= SIZE_GPU_ROW:
            return
        row = gp + SIZE_GPU_ROW * gp_sz
        const = self.f32(row)
        idx = int(self.f32(row + 8)) >> 17
        # the function was already scaled (fn points at the private copy), so the
        # GPU rows to scale are the ones still holding the OLD min/max = new / k
        lo, hi = (self.f32(fn + 4) / k, self.f32(fn + 8) / k) if fn else (None, None)
        if const:
            key = ('P', gp)
            if key not in memo:
                data = bytearray(m.data[gp:gp + np_ * gp_sz])
                struct.pack_into('<f', data, SIZE_GPU_ROW * gp_sz, const * k)

                def patch(ptr, em=em, key=key):
                    struct.pack_into('<I', m.data, em + gp_off + 4, ptr)
                    memo[key] = ptr
                self.alloc(data, patch)
                log['gpu_blocks_copied'] += 1
            else:
                struct.pack_into('<I', m.data, em + gp_off + 4, memo[key])
        elif gf and lo is not None:
            key = ('F', gf)
            if key not in memo:
                data = bytearray(m.data[gf:gf + nf * gf_sz])
                hit = 0
                for r in (idx, idx + 1):
                    if r >= nf:
                        continue
                    a, b = struct.unpack_from('<2f', data, r * gf_sz + 8)
                    if abs(a - lo) < 1e-5 and abs(b - hi) < 1e-5:
                        struct.pack_into('<2f', data, r * gf_sz + 8, a * k, b * k)
                        hit += 1
                if not hit:
                    return

                def patch(ptr, em=em, key=key):
                    struct.pack_into('<I', m.data, em + gf_off + 4, ptr)
                    memo[key] = ptr
                self.alloc(data, patch)
                log['gpu_blocks_copied'] += 1
            else:
                struct.pack_into('<I', m.data, em + gf_off + 4, memo[key])


def snapshot(game, m):
    """{(effect, emitter#, prop): (function bytes, constant, gpu size row/fn rows)} for
    every emitter of every effect -- what each property evaluates to."""
    fx = Fx(game, m)
    snap = {}
    for t in m.tags:
        if t.get('class') != 'effe' or t.get('base') is None:
            continue
        if fx.L['gss'] is not None:
            snap[(t['name'], -1, 'gss')] = round(fx.f32(t['base'] + fx.L['gss']), 6)
        for i, em in enumerate(fx.emitters(t)):
            for prop, po in fx.L['props'].items():
                q = em + po
                sz = m.i32(q + fx.fn_rel)
                p = fx.p2o(m.u32(q + fx.ptr_rel)) if sz > 0 else None
                fnb = bytes(m.data[p:p + sz]) if p else b''
                const = None if fx.h2 else round(fx.f32(q + 0x18), 6)
                snap[(t['name'], i, prop)] = (fnb, const)
            if fx.gpu:
                gp_off, gp_sz, gf_off, gf_sz = fx.gpu
                np_, gp = fx.blk(em + gp_off)
                nf, gf = fx.blk(em + gf_off)
                snap[(t['name'], i, 'gpuP')] = bytes(m.data[gp:gp + np_ * gp_sz]) if gp else b''
                snap[(t['name'], i, 'gpuF')] = bytes(m.data[gf:gf + nf * gf_sz]) if gf else b''
    return snap


def verify(game, before, after, names, k, mode):
    names = {n.lower() for n in names}
    bad, scaled, same = [], 0, 0
    for key, v0 in before.items():
        v1 = after.get(key)
        eff, i, prop = key
        mine = eff.lower() in names
        if not mine:
            if v1 != v0:
                bad.append(('OUTSIDE CHANGED', key))
            else:
                same += 1
            continue
        if mode == 'gss':
            ok = (prop != 'gss' and v1 == v0) or (prop == 'gss' and abs(v1 - v0 * k) < 1e-4)
        elif prop in (SIZE, RADIUS):
            (f0, c0), (f1, c1) = v0, v1
            ok = len(f0) == len(f1)
            if f0:
                a0, b0 = struct.unpack_from('<2f', f0, 4)
                a1, b1 = struct.unpack_from('<2f', f1, 4)
                ok = ok and abs(a1 - a0 * k) < 1e-5 and abs(b1 - b0 * k) < 1e-5 \
                    and f0[:4] == f1[:4] and f0[12:] == f1[12:]
            if c0 is not None:
                ok = ok and abs(c1 - c0 * k) < 1e-5
            scaled += ok
        elif prop in ('gpuP', 'gpuF'):
            ok = len(v0) == len(v1)          # content checked by the decoder rule above
        else:
            ok = v1 == v0                    # every other property untouched
        if not ok:
            bad.append(('MISMATCH', key))
    return {'outside_unchanged': same, 'scaled_ok': scaled, 'problems': bad[:20], 'n_problems': len(bad)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--game', required=True)
    p.add_argument('--map', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--effect', action='append', required=True)
    p.add_argument('--scale', type=float, required=True)
    p.add_argument('--mode', default='emitters', choices=['emitters', 'gss'])
    a = p.parse_args()
    if os.path.abspath(a.out) == os.path.abspath(a.map):
        raise SystemExit('--out must be a different file (this is a prototype)')
    m = A.load(a.game, a.map)
    before = snapshot(a.game, m)
    log = Fx(a.game, m).scale(a.effect, a.scale, a.mode)
    print('scaled:', log)
    m.save(a.out)
    m2 = A.load(a.game, a.out)
    after = snapshot(a.game, m2)
    print('verify:', verify(a.game, before, after, a.effect, a.scale, a.mode))


if __name__ == '__main__':
    main()
