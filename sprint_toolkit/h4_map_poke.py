r"""Poke the H4 port's weapon fields straight into a BUILT Halo 4 map -- no rebuild.

A rebuild costs a build-cache-file run per experiment. The fields being tested sit at
fixed offsets in the built weapon tag (Assembly's Halo4MCC/weap.xml), so they can be
written into the installed map directly, tested, and only then made permanent in the
kit tags (h4_make_port_weapon.py) for the next real build.

    python h4_map_poke.py                 report: the port's fields beside the Beam Rifle's
    python h4_map_poke.py --fix           the NPC-gun leftovers -> the Beam Rifle's values
    python h4_map_poke.py --swap-fp       ALSO point the fp model at the Beam Rifle's
                                          render model (model fault vs weapon-tag fault)
    python h4_map_poke.py --map <path>    another map (default: installed m30_cryptum)

Offsets, weap (Halo4MCC/weap.xml):
    0x1C  object flags, bit 8 "Extension Of Parent" ("object uses parent's markers")
    0x20  bounding radius        0x24  bounding offset (3 floats)
    0x4B4 weapon class (string id)   0x4B8 weapon name (string id)
    0x4D4 First Person block (element 0x28): +0x00 fp model tagRef, +0x10 fp animations
    0x5EC weapon ready 1st person animation playback scale
Class and name are COPIED from the Beam Rifle's tag in the same map, so no string id has
to be looked up. Restore: copy the map back from H4EK\maps (the build output).
Uses the enhancer's map reader read-only; edits nothing of the enhancer.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import halo_patch                                              # noqa: E402

MAP = (r'C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection'
       r'\halo4\maps\m30_cryptum.map')
PORT = r'objects\weapons\rifle\focus_rifle\focus_rifle'
BEAM = r'objects\weapons\rifle\storm_beam_rifle\storm_beam_rifle'
PP_GRAPH = r'objects\characters\storm_fp\weapons\pistol\fp_plasma_pistol\storm_fp_plasma_pistol'
PORT_GRAPH = r'objects\characters\storm_fp\weapons\rifle\fp_focus_rifle\fp_focus_rifle'
BEAM_GRAPH = r'objects\characters\storm_fp\weapons\rifle\fp_beam_rifle\storm_fp_beam_rifle'
SENTINEL_LOOP = r'sound\storm\characters\sentinel\loops\npc_sentinel_friendly_beam_fire'
SCOPE = r'ui\hud\weapons\covenant\focus_rifle\focus_rifle_scope'
BR_HEAT_BAR = r'ui\hud\weapons\covenant\beam_rifle\bitmap\heat_bar'
PORT_BEAM = r'objects\weapons\rifle\focus_rifle\projectiles\focus_rifle_beam'
BR_PROJ_FX = r'objects\weapons\rifle\storm_beam_rifle\fx\projectile'
FP_TRACER = r'objects\weapons\pistol\storm_sentinel_beam\fx\friendly_beam\projectile_1p'

FLAGS, RADIUS, OFFSET = 0x1C, 0x20, 0x24
CLASS, NAME, FP, READY = 0x4B4, 0x4B8, 0x4D4, 0x5EC
EXT_OF_PARENT = 1 << 8


def fp_element(m, base):
    count, ptr = struct.unpack_from('<iI', m.data, base + FP)
    return m.data2off(ptr) if count else None


def report(m, base, label):
    d = m.data
    flags = struct.unpack_from('<I', d, base + FLAGS)[0]
    fp = fp_element(m, base)
    print('%-12s ext-of-parent %-5s radius %-6g offset %-22s ready %-4g class %08x name %08x'
          % (label, bool(flags & EXT_OF_PARENT), struct.unpack_from('<f', d, base + RADIUS)[0],
             ','.join('%g' % v for v in struct.unpack_from('<3f', d, base + OFFSET)),
             struct.unpack_from('<f', d, base + READY)[0],
             struct.unpack_from('<I', d, base + CLASS)[0],
             struct.unpack_from('<I', d, base + NAME)[0]))
    if fp is not None:
        print('%-12s fp model datum %08x  fp anims datum %08x'
              % ('', struct.unpack_from('<I', d, fp + 0xC)[0],
                 struct.unpack_from('<I', d, fp + 0x1C)[0]))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--map', default=MAP)
    ap.add_argument('--fix', action='store_true')
    ap.add_argument('--swap-fp', action='store_true')
    ap.add_argument('--scope', action='store_true',
                    help='graft the Beam Rifle scope onto the port HUD (after each build)')
    ap.add_argument('--loop-frame', metavar='N=F', action='append',
                    help='fp graph animation N loop frame index (repeatable)')
    ap.add_argument('--anim-flags', metavar='N=FLAGS', action='append',
                    help='fp graph animation N playback flags (repeatable)')
    ap.add_argument('--action-anim', metavar='A=B', action='append',
                    help='fp graph action A plays animation B (bisection; repeatable)')
    ap.add_argument('--secondary-fx', metavar='EFFECT',
                    help='a muzzle effect (tag name) in the secondary firing slot of each barrel')
    ap.add_argument('--firing-response', metavar='DRDF',
                    help='per-shot damage response (shake/rumble) from another weapon')
    ap.add_argument('--no-firing-shake', action='store_true',
                    help='null the per-shot firing damage response (shake/rumble/recoil)')
    ap.add_argument('--fp-offset', metavar='X,Y,Z',
                    help='first person projectile offset: +x forward, +y left, +z up')
    ap.add_argument('--no-overheat-shake', action='store_true',
                    help='null the overheated damage effect (camera shake + rumble)')
    ap.add_argument('--graph-pp', action='store_true',
                    help='fp animations -> the Plasma Pistol graph (diagnostic)')
    ap.add_argument('--graph-back', action='store_true',
                    help='fp animations back to the Beam Rifle graph')
    ap.add_argument('--streak-back', action='store_true',
                    help='projectile attachment back to the Beam Rifle streak')
    ap.add_argument('--fp-tracer', action='store_true',
                    help='the original beam tracer: set "draw in first person pass"')
    ap.add_argument('--weapon-origin', action='store_true',
                    help='barrel flag: projectiles come out of the gun, not the camera')
    ap.add_argument('--beam-test', action='store_true',
                    help='barrel 0 fires the Beam Rifle projectile + firing effect')
    ap.add_argument('--unswap', action='store_true',
                    help='point the fp model back at the own render model of the port')
    ap.add_argument('--model-flags', action='store_true',
                    help='render model 0x64 bit 5: do not use compressed vertex positions')
    ap.add_argument('--on-beam-graph', action='store_true',
                    help='--loop-frame / --anim-flags act on the BEAM RIFLE fp graph (the '
                         'one --graph-back points the port at)')
    ap.add_argument('--zoom-barrel', metavar='X,Y,Z', nargs='?', const='0,0,0',
                    help="the Light Rifle's split: trigger 0 -> latch-zoom (primary barrel "
                         "0 unzoomed, secondary barrel 1 zoomed); barrel 1 = a copy of "
                         "barrel 0 with this first person offset (default the centre)")
    ap.add_argument('--trigger-spew', action='store_true',
                    help='undo --zoom-barrel: trigger 0 back to spew, no secondary barrel '
                         '(boot 26: latch-zoom fires ONE shot per press, zoomed or not)')
    ap.add_argument('--meters-visible', action='store_true',
                    help='scope side meters: prop_visible 0 -> 1 in the built focus_rifle_scope')
    ap.add_argument('--meters-br-bitmap', action='store_true',
                    help="CONTROL: both scope meters draw the Beam Rifle's own heat_bar bitmap")
    ap.add_argument('--meter-rects', action='store_true',
                    help='scope side meters -> the rects scaled with the art (boot 28)')
    ap.add_argument('--player-bank', metavar='SBNK',
                    help="weap +0x608 'Player Sound Bank' -> this soundbank tag (the port's "
                         "is empty; the plugin: 'high quality player sound bank to be prefetched')")
    ap.add_argument('--firing-loop', metavar='LSND', nargs='?', const=SENTINEL_LOOP,
                    help='object attachment 0 (the overheat loop) -> this looping sound, '
                         'scaled by primary_firing (the scale attachment 1 uses)')
    ap.add_argument('--zoom-sounds', action='store_true',
                    help="weap Zoom-In/Out Sound (0x48C/0x49C) -> the Beam Rifle's (Reach's "
                         "Focus Rifle used the Beam Rifle's zoom sounds)")
    ap.add_argument('--accel-scale', action='store_true',
                    help="object horizontal/vertical/angular acceleration scale (weap "
                         "0x30/0x34/0x38) -> the Beam Rifle's (the Sentinel's are 0)")
    a = ap.parse_args()

    m = halo_patch.open_map(a.map, 'Halo 4')
    port = m.find_tags('weap', PORT)
    beam = m.find_tags('weap', BEAM)
    if not port or not beam:
        raise SystemExit('not in this map: %s' % ('the port' if not port else 'the Beam Rifle'))
    pb, bb = port[0][1], beam[0][1]
    report(m, pb, 'focus rifle')
    report(m, bb, 'beam rifle')
    if not (a.fix or a.swap_fp or a.unswap or a.model_flags or a.beam_test or
            a.weapon_origin or a.fp_tracer or a.graph_back or a.streak_back or
            a.no_overheat_shake or a.graph_pp or a.fp_offset or a.secondary_fx or
            a.no_firing_shake or a.action_anim or a.firing_response or a.anim_flags or
            a.loop_frame or a.scope or a.accel_scale or a.zoom_barrel or a.trigger_spew or
            a.meters_visible or a.meters_br_bitmap or a.meter_rects or a.player_bank or
            a.firing_loop or a.zoom_sounds):
        return

    d = m.data
    if a.zoom_barrel:
        # Boot 26 (user): one first-person offset per BARREL, so zoomed and unzoomed can
        # start the beam in different places -- the Light Rifle's trigger is latch-zoom,
        # primary barrel 0 unzoomed, secondary barrel 1 zoomed. weap.xml: New Triggers
        # 0x50C (0xAC each): Behavior +0x6 (5 = Latch-Zoom), Secondary Barrel +0xA.
        # Barrels 0x518 (0x190): First Person Offset tagblock +0x100 (12 bytes).
        # OPEN QUESTION this tests: latch-zoom is only used by per-press weapons (Battle
        # Rifle, Light Rifle); does a held 30/s beam keep firing?
        tc, tp = struct.unpack_from('<iI', d, pb + 0x50C)
        t0 = m.data2off(tp)
        bc, bp = struct.unpack_from('<iI', d, pb + 0x518)
        if bc < 2:
            raise SystemExit('the port has %d barrel(s); the zoom split needs 2' % bc)
        b0 = m.data2off(bp)
        b1 = b0 + 0x190
        keep = bytes(d[b1 + 0x100:b1 + 0x10C])
        d[b1:b1 + 0x190] = d[b0:b0 + 0x190]
        d[b1 + 0x100:b1 + 0x10C] = keep
        oc, op = struct.unpack_from('<iI', d, b1 + 0x100)
        if oc < 1:
            raise SystemExit('barrel 1 has no first person offset element to set')
        xyz = [float(v) for v in a.zoom_barrel.split(',')]
        # THE BUILD MERGES IDENTICAL BLOCKS: both barrels' offset blocks (both 0.03,-0.08,0
        # in the kit) are ONE block in the map, so writing barrel 1's in place moved barrel
        # 0's too. Barrel 1 gets its own 12 bytes in a zero run (halo_patch._h3_reserve,
        # >= 4 KB runs only -- see h4-scope-graft-residency-crash).
        if op == struct.unpack_from('<iI', d, b0 + 0x100)[1]:
            got = halo_patch._h3_reserve(m, [12])
            if got is None:
                raise SystemExit("no free run for barrel 1's own offset block")
            struct.pack_into('<3f', d, got[0], *xyz)
            struct.pack_into('<iI', d, b1 + 0x100, 1, m.off2data(got[0]))
            print("barrel 1: own first person offset block (it shared barrel 0's)")
        else:
            struct.pack_into('<3f', d, m.data2off(op), *xyz)
        was = struct.unpack_from('<hhh', d, t0 + 0x6)
        struct.pack_into('<h', d, t0 + 0x6, 5)
        struct.pack_into('<h', d, t0 + 0xA, 1)
        print('trigger 0 behavior/primary/secondary %s -> (5, %d, 1); barrel 1 = barrel 0, '
              'first person offset %s' % (was, was[1], xyz))
    if a.meters_visible or a.meters_br_bitmap:
        # The port's scope template, overlay 0 (widescreen): each overlay component =
        # name sid + 7 property blocks (long, real, string_id, component ptr, tag
        # reference, string, argb), 12 bytes each. Long = (name sid, value); tag reference
        # = (name sid, 16-byte tagref: group, ..., datum at +0xC of the ref).
        C = halo_patch._H4_CUSC
        sc = m.find_tags('cusc', SCOPE)[0][1]
        ov0 = halo_patch._h4_rows(m, sc, *C['overlays'])[0]
        cb = m.data2off(struct.unpack_from('<I', ov0, halo_patch._H4_OV_COMPS[0] + 4)[0])
        n = struct.unpack_from('<i', ov0, halo_patch._H4_OV_COMPS[0])[0]
        brbm = next(t for t in m.tags if t['class'] == 'bitm' and t['name'] == BR_HEAT_BAR)
        for i in range(n):
            e = cb + i * halo_patch._H4_OV_COMPS[1]
            nm = m.resolve_stringid(struct.unpack_from('<I', d, e)[0])
            if nm not in ('bitmap_heat_bar', 'bitmap_ammo_bar'):
                continue
            for k, (esz, want) in ((0, (8, 'prop_visible')), (4, (20, 'prop_bitmap_reference'))):
                cnt, ptr = struct.unpack_from('<iI', d, e + 4 + k * 12)
                a0 = m.data2off(ptr) if cnt > 0 else None
                for j in range(max(cnt, 0)):
                    at = a0 + j * esz
                    # UI property names sit in a string NAMESPACE the map reader does not
                    # resolve, so match by structure: the meters' long block is (blend 1,
                    # scale-to-bounds 1, visible 0) -- the 0 is prop_visible; the tag
                    # reference block holds one entry, the bitmap.
                    if k == 0 and struct.unpack_from('<i', d, at + 4)[0] != 0:
                        continue
                    if k == 0 and a.meters_visible:
                        was = struct.unpack_from('<i', d, at + 4)[0]
                        struct.pack_into('<i', d, at + 4, 1)
                        print('%s prop_visible %d -> 1' % (nm, was))
                    if k == 4 and a.meters_br_bitmap:
                        was = struct.unpack_from('<I', d, at + 4 + 0xC)[0]
                        struct.pack_into('<I', d, at + 4 + 0xC, brbm['ident'])
                        print('%s bitmap %#x -> %#x (Beam Rifle heat_bar)' % (nm, was, brbm['ident']))
    if a.meter_rects:
        # Each meter's REAL property block (overlay 0): name sid + float. The names do not
        # resolve here, so each value is matched: old rect -> new rect, per meter.
        C = halo_patch._H4_CUSC
        sc = m.find_tags('cusc', SCOPE)[0][1]
        ov0 = halo_patch._h4_rows(m, sc, *C['overlays'])[0]
        cb = m.data2off(struct.unpack_from('<I', ov0, halo_patch._H4_OV_COMPS[0] + 4)[0])
        n = struct.unpack_from('<i', ov0, halo_patch._H4_OV_COMPS[0])[0]
        want = {1070.4: 1138.7, 1135.0: 1138.7, 103.8: 23.3, 203.4: 179.9, 105.8: 121.6,
                313.3: 360.3}
        for i in range(n):
            e = cb + i * halo_patch._H4_OV_COMPS[1]
            nm = m.resolve_stringid(struct.unpack_from('<I', d, e)[0])
            if nm not in ('bitmap_heat_bar', 'bitmap_ammo_bar'):
                continue
            cnt, ptr = struct.unpack_from('<iI', d, e + 4 + 12)
            a0 = m.data2off(ptr)
            for j in range(cnt):
                v = struct.unpack_from('<f', d, a0 + j * 8 + 4)[0]
                for old_v, new_v in want.items():
                    if abs(v - old_v) < 0.05:
                        struct.pack_into('<f', d, a0 + j * 8 + 4, new_v)
                        print('%s %.1f -> %.1f' % (nm, v, new_v))
    if a.player_bank:
        # Boot 28 (user): the port makes NO sound. Its firing effect names the Sentinel
        # friendly-beam loop (sentinel bank), but m30 has no Sentinels, and the port's
        # Player Sound Bank is empty -- so the bank may never load. tagRef: group at +0,
        # datum at +0xC (the Beam Rifle's: knbs ... beam_rifle_player).
        t = next((t for t in m.tags if t['class'] == 'sbnk' and t['name'] == a.player_bank), None)
        if t is None:
            raise SystemExit('no soundbank %s in this map' % a.player_bank)
        was = struct.unpack_from('<I', d, pb + 0x608 + 0xC)[0]
        d[pb + 0x608:pb + 0x60C] = d[bb + 0x608:bb + 0x60C]
        struct.pack_into('<I', d, pb + 0x608 + 0xC, t['ident'])
        print('player sound bank %#x -> %#x (%s)' % (was, t['ident'], a.player_bank))
    if a.firing_loop:
        # Boot 29: firing is SILENT (with or without the sound test, with the player bank
        # set) while the overheat loop -- an OBJECT ATTACHMENT (weap 0x118, 0x20 each: type
        # tagRef +0, marker +0x10, primary scale +0x18) scaled by `overheated` -- plays.
        # The Sentinel's firing sound sits in its firing effect's "looping sounds", alive
        # only as long as a per-shot effect. Test: the same loop as an attachment, scaled
        # by primary_firing (attachment 1, the firing light, already uses that function).
        t = next((t for t in m.tags if t['class'] == 'lsnd' and t['name'] == a.firing_loop), None)
        if t is None:
            raise SystemExit('no looping sound %s in this map' % a.firing_loop)
        cnt, ptr = struct.unpack_from('<iI', d, pb + 0x118)
        a0 = m.data2off(ptr)
        was = struct.unpack_from('<I', d, a0 + 0xC)[0]
        struct.pack_into('<I', d, a0 + 0xC, t['ident'])
        sc = struct.unpack_from('<I', d, a0 + 0x20 + 0x18)[0]
        struct.pack_into('<I', d, a0 + 0x18, sc)
        print('attachment 0: %#x -> %#x (%s), primary scale -> %s'
              % (was, t['ident'], a.firing_loop, m.resolve_stringid(sc) or hex(sc)))
    if a.zoom_sounds:
        # Boot 30: no zoom sound. The Sentinel base names the bishop beam's NONPLAYER zoom
        # events (bishop_beam bank, not in m30); Reach's Focus Rifle used the Beam Rifle's.
        for off in (0x48C, 0x49C):
            was = struct.unpack_from('<I', d, pb + off + 0xC)[0]
            d[pb + off:pb + off + 0x10] = d[bb + off:bb + off + 0x10]
            print('zoom sound +%#x: %#x -> %#x' % (off, was, struct.unpack_from('<I', d, pb + off + 0xC)[0]))
    if a.trigger_spew:
        tc, tp = struct.unpack_from('<iI', d, pb + 0x50C)
        t0 = m.data2off(tp)
        was = struct.unpack_from('<hhh', d, t0 + 0x6)
        struct.pack_into('<h', d, t0 + 0x6, 0)
        struct.pack_into('<h', d, t0 + 0xA, -1)
        print('trigger 0 behavior/primary/secondary %s -> (0, %d, -1)' % (was, was[1]))
    if a.accel_scale:
        # Boot 26 drift hunt: the reticle drifts while turning and recentres when still --
        # motion-driven. The Sentinel Beam (part of an enemy's body) carries acceleration
        # scales of 0 where every player weapon has 1 (Beam Rifle) or 1.25 (Plasma Pistol).
        for off in (0x30, 0x34, 0x38):
            was = struct.unpack_from('<f', d, pb + off)[0]
            new = struct.unpack_from('<f', d, bb + off)[0]
            struct.pack_into('<f', d, pb + off, new)
            print('acceleration scale +%#x: %g -> %g' % (off, was, new))
    if a.fix:
        flags = struct.unpack_from('<I', d, pb + FLAGS)[0]
        struct.pack_into('<I', d, pb + FLAGS, flags & ~EXT_OF_PARENT)
        d[pb + RADIUS:pb + RADIUS + 16] = d[bb + RADIUS:bb + RADIUS + 16]   # radius + offset
        d[pb + CLASS:pb + CLASS + 8] = d[bb + CLASS:bb + CLASS + 8]         # class + name
        struct.pack_into('<f', d, pb + READY, struct.unpack_from('<f', d, bb + READY)[0])
    if a.swap_fp:
        pf, bf = fp_element(m, pb), fp_element(m, bb)
        d[pf:pf + 0x10] = d[bf:bf + 0x10]                                   # fp model tagRef
    if a.beam_test:
        # Barrel 0 (right trigger) fires the BEAM RIFLE's projectile with the Beam Rifle's
        # firing effect -- a beam known to draw from a player's weapon. Beam seen: the
        # port's weapon + model can show one, and the Sentinel's 1p tracer is the fault.
        # Not seen: something on the port blocks effects. weap.xml: Barrels 0x518
        # (0x190 each), Projectile +0x110, Firing Effects +0x184 (0xF4), effect +0x4.
        def barrel0(base):
            count, ptr = struct.unpack_from('<iI', d, base + 0x518)
            return m.data2off(ptr)
        pb0, bb0 = barrel0(pb), barrel0(bb)
        d[pb0 + 0x110:pb0 + 0x120] = d[bb0 + 0x110:bb0 + 0x120]
        pfx = m.data2off(struct.unpack_from('<I', d, pb0 + 0x184 + 4)[0])
        bfx = m.data2off(struct.unpack_from('<I', d, bb0 + 0x184 + 4)[0])
        d[pfx + 0x4:pfx + 0x14] = d[bfx + 0x4:bfx + 0x14]
        print('barrel 0: Beam Rifle projectile + firing effect')
    if a.action_anim:
        # BISECTION in the built map (boot 17): an action of the port's fp graph plays
        # another animation. Layout = halo3_reload.LAYOUTS['Halo 4'] (proven by the reload
        # and swap cards): modes -> weapon class -> weapon type -> sets -> actions (0xC),
        # animation index at +0xA. `--list-actions` prints the indices.
        import halo3_reload
        L = halo3_reload.LAYOUTS['Halo 4']
        g = m.find_tags('jmad', PORT_GRAPH)[0][1]
        acts = [ac for mo in m.follow_all(g, [L['modes_blk']], [L['modes_el']], 'all')
                for wc in m.follow_all(mo, [L['wclass_blk']], [L['wclass_el']], 'all')
                for wt in m.follow_all(wc, [L['wtype_blk']], [L['wtype_el']], 'all')
                for st in m.follow_all(wt, [L['sets_blk']], [L['sets_el']], 'all')
                for ac in m.follow_all(st, [L['actions_blk']], [L['actions_el']], 'all')]
        for pair in a.action_anim:
            ai, an = (int(v) for v in pair.split('='))
            was = struct.unpack_from('<h', d, acts[ai] + 0xA)[0]
            struct.pack_into('<h', d, acts[ai] + 0xA, an)
            print('action %d: animation %d -> %d' % (ai, was, an))
    if a.scope:
        # STEP 7: the zoom HUD. The enhancer's own, in-game-proven Halo 4 scope graft
        # (halo_patch._apply_h4_scope: template instance, zoom_decision/zoom_on_off,
        # bindings, sniper_zoom_* animations) onto the port's OWN screen copy, donor the
        # Beam Rifle's screen. Run after every build; the enhancer does the same at patch
        # time. Its residency check refuses a donor whose scope template is not loaded
        # where the port's HUD is.
        rows = halo_patch._apply_h4_scope(m, ['weap ' + PORT], donor_huds=['beam_rifle'])
        for r in rows:
            print('scope: %s' % {k: r[k] for k in r if k in ('field', 'ok', 'skip', 'new', 'reason')})
    if a.anim_flags:
        # Playback Flags (jmad Animations element +0xA): bit 3 Disable Weapon IK, bit 4
        # Disable Weapon Aim/1st Person. The port's (Beam Rifle) overheating + o_h_exit
        # carry 0x18; the Plasma Pistol's -- which do not pop -- 0x08. With bit 4 the fp
        # aim offset is OFF during overheating and snaps back ON at the hand-off: one
        # frame of the whole rig shifted, "right before the idle" (boot 18).
        import halo3_reload
        L = halo3_reload.LAYOUTS['Halo 4']
        g = m.find_tags('jmad', BEAM_GRAPH if a.on_beam_graph else PORT_GRAPH)[0][1]
        els = m.follow_all(g, [L['anim_blk']], [L['anim_el']], 'all')
        for pair in a.anim_flags:
            ai, v = pair.split('=')
            ai, v = int(ai), int(v, 0)
            was = struct.unpack_from('<H', d, els[ai] + 0xA)[0]
            struct.pack_into('<H', d, els[ai] + 0xA, v)
            print('animation %d playback flags %#06x -> %#06x' % (ai, was, v))
    if a.loop_frame:
        # Loop Frame Index (jmad Animations element +0x8): where a finished animation
        # wraps to. The port's overheating: 0 -- its PRE-overheat pose, both hands
        # elsewhere; the Plasma Pistol's (no pop): 16. A wrap shown for one frame at the
        # hand-off = the pop "right before the idle" (boot 18).
        import halo3_reload
        L = halo3_reload.LAYOUTS['Halo 4']
        g = m.find_tags('jmad', BEAM_GRAPH if a.on_beam_graph else PORT_GRAPH)[0][1]
        els = m.follow_all(g, [L['anim_blk']], [L['anim_el']], 'all')
        for pair in a.loop_frame:
            ai, v = (int(x) for x in pair.split('='))
            was = struct.unpack_from('<h', d, els[ai] + 0x8)[0]
            struct.pack_into('<h', d, els[ai] + 0x8, v)
            print('animation %d loop frame %d -> %d' % (ai, was, v))
    if a.secondary_fx or a.no_firing_shake or a.firing_response:
        # each barrel's firing-effects element 0 (barrel +0x184, 0xF4 each):
        #   +0x44 Optional Secondary Firing Effect -- a MUZZLE FLASH beside the Sentinel's
        #         firing effect (boot 16: "missing a muzzle firing effect")
        #   +0x54 Firing Damage -- the per-shot damage response: camera shake + rumble +
        #         simulated input at 30 shots a second (boot 16: "the shake while firing")
        fx = None
        if a.secondary_fx:
            fx = next((t for t in m.tags if t['class'] == 'effe' and t['name'] == a.secondary_fx), None)
            if fx is None:
                raise SystemExit('no effect %s in this map' % a.secondary_fx)
        resp = None
        if a.firing_response:
            # a GENTLER per-shot response (boot 17: shake "much better" without one, but
            # "add a little feedback back") -- e.g. the Storm Rifle's, built for a
            # sustained automatic plasma weapon
            resp = next((t for t in m.tags if t['class'] == 'drdf' and t['name'] == a.firing_response), None)
            if resp is None:
                raise SystemExit('no response %s in this map' % a.firing_response)
        count, ptr = struct.unpack_from('<iI', d, pb + 0x518)
        first = m.data2off(ptr)
        for i in range(count):
            n, p2 = struct.unpack_from('<iI', d, first + i * 0x190 + 0x184)
            el = m.data2off(p2)
            if fx is not None:
                d[el + 0x44:el + 0x48] = b'effe'[::-1]
                struct.pack_into('<I', d, el + 0x44 + 0xC, fx['ident'])
                print('barrel %d secondary firing effect -> %s' % (i, a.secondary_fx))
            if a.no_firing_shake:
                struct.pack_into('<I', d, el + 0x54 + 0xC, 0xFFFFFFFF)
                print('barrel %d firing damage response -> null' % i)
            if resp is not None:
                d[el + 0x54:el + 0x58] = b'drdf'[::-1]
                struct.pack_into('<I', d, el + 0x54 + 0xC, resp['ident'])
                print('barrel %d firing damage response -> %s' % (i, a.firing_response))
    if a.fp_offset:
        # each barrel's "First Person Offset" block (weap.xml: barrel +0x100, 0xC per
        # point, +x forward, +z up, +y left) -- where the beam spawns in first person.
        # The block needs an element already (the kit build adds one).
        x, y, z = (float(v) for v in a.fp_offset.split(','))
        count, ptr = struct.unpack_from('<iI', d, pb + 0x518)
        first = m.data2off(ptr)
        for i in range(count):
            n, p2 = struct.unpack_from('<iI', d, first + i * 0x190 + 0x100)
            if not n:
                raise SystemExit('barrel %d has no first person offset element -- rebuild first' % i)
            at = m.data2off(p2)
            was = struct.unpack_from('<3f', d, at)
            struct.pack_into('<3f', d, at, x, y, z)
            print('barrel %d first person offset %s -> %s' % (i, ','.join('%g' % v for v in was), a.fp_offset))
    if a.no_overheat_shake:
        # weap 0x330 "Overheated Damage Effect" tagRef -> null. The Sentinel base names
        # globals\damage_responses	rigger_overheat: a CAMERA SHAKE + rumble on overheat --
        # the whole-view jerk the user still felt (boot 13) after every animation seam was
        # closed. The Beam Rifle leaves this field empty.
        was = struct.unpack_from('<I', d, pb + 0x330 + 0xC)[0]
        struct.pack_into('<I', d, pb + 0x330 + 0xC, 0xFFFFFFFF)
        print('overheated damage effect datum %08x -> null' % was)
    if a.graph_pp:
        # fp animations -> the PLASMA PISTOL's graph: its overheat chain is used all the
        # time in normal play. One-frame pop at ~52%% heat gone -> the Beam Rifle chain's
        # state handling; still there -> something on the port's weapon tag (boot 14).
        g = next((t for t in m.tags if t['class'] == 'jmad' and t['name'] == PP_GRAPH), None)
        if g is None:
            raise SystemExit('the Plasma Pistol fp graph is not in this map')
        pf = fp_element(m, pb)
        struct.pack_into('<I', d, pf + 0x10 + 0xC, g['ident'])
        print('fp animations -> %s' % PP_GRAPH)
    if a.graph_back:
        # fp animations -> the Beam Rifle's own graph (First Person +0x10): does the
        # port's re-exported graph cause the freeze after the overheat jerk (boot 12)?
        pf, bf = fp_element(m, pb), fp_element(m, bb)
        d[pf + 0x10:pf + 0x20] = d[bf + 0x10:bf + 0x20]
        print('fp animations -> the Beam Rifle graph')
    if a.streak_back:
        # the port projectile's attachment (proj.xml Attachments 0x118, 0x20 each, Type
        # tagRef +0x0) -> the Beam Rifle's projectile effect, the thin streak that DREW
        # (boot 10). The unpinned Sentinel tracer drew nothing (boot 12).
        own = m.find_tags('proj', PORT_BEAM)[0][1]
        brfx = next(t for t in m.tags if t['class'] == 'effe' and t['name'] == BR_PROJ_FX)
        count, ptr = struct.unpack_from('<iI', d, own + 0x118)
        el = m.data2off(ptr)
        # pick the EFFECT attachment by its group -- element 0 of the port's projectile
        # is the Sentinel's looping fire SOUND (lsnd); a blind index once wrote an effect
        # datum under an lsnd group
        hits = [el + i * 0x20 for i in range(count) if bytes(d[el + i * 0x20:el + i * 0x20 + 4])[::-1] == b'effe']
        if len(hits) != 1:
            raise SystemExit('expected one effect attachment, found %d' % len(hits))
        struct.pack_into('<I', d, hits[0] + 0xC, brfx['ident'])
        print('projectile attachment -> %s (%d attachment(s))' % (BR_PROJ_FX, count))
    if a.fp_tracer:
        # The Sentinel's (= the Focus Rifle's converted) first-person beam tracer carries
        # only "point-to-point" (flags u32 at +0x0, bit 0; measured: 1 on both Sentinel
        # tracers, 0 on the Beam Rifle's streak). Bit 1 is "draw in first person pass
        # (dangerous)" -- without it a tracer is not drawn in first person at all, which
        # is why the original beam never showed for the player (boots 2-8).
        tr = m.find_tags('trac', FP_TRACER)
        if not tr:
            raise SystemExit('no %s in this map' % FP_TRACER)
        tb = tr[0][1]
        was = struct.unpack_from('<I', d, tb)[0]
        struct.pack_into('<I', d, tb, was | 0x2)
        print('fp tracer flags %#x -> %#x' % (was, was | 0x2))
    if a.weapon_origin:
        # Barrel flags (+0x0) bit 2 "Projectiles Use Weapon Origin": "instead of coming
        # out of the magic first person camera origin, the projectiles for this weapon
        # actually come out of the gun". From the camera, the beam's projectile streak
        # flies straight away from the eye -- seen end-on, "visible only when I move"
        # (boot 10). From the gun it is seen from the side.
        count, ptr = struct.unpack_from('<iI', d, pb + 0x518)
        first = m.data2off(ptr)
        for i in range(count):
            at = first + i * 0x190
            was = struct.unpack_from('<I', d, at)[0]
            struct.pack_into('<I', d, at, was | 0x4)
            print('barrel %d flags %#x -> %#x' % (i, was, was | 0x4))
    if a.unswap:
        own = next(t for t in m.tags if t['class'] == 'mode' and t['name'] == PORT)
        pf = fp_element(m, pb)
        struct.pack_into('<I', d, pf + 0xC, own['ident'])
    if a.model_flags:
        # The port's MESH stores raw positions (mesh flag 256 "doesn't use compressed
        # position") while its geometry flags (0x64) say nothing about it -- 4, budgets
        # only. The Beam Rifle's geometry carries 36 = budgets + bit 5 "Don't Use
        # Compressed Vertex Positions". Swap test (boot 7): the Beam Rifle's model DRAWS
        # in first person on the port's weapon, so the fault is in the port's model.
        mb = m.find_tags('mode', PORT)[0][1]
        was = struct.unpack_from('<I', d, mb + 0x64)[0]
        struct.pack_into('<I', d, mb + 0x64, was | 0x20)
        print('render model flags %d -> %d' % (was, was | 0x20))
    print('\nafter:')
    report(m, pb, 'focus rifle')
    m.save()
    print('saved %s' % a.map)


if __name__ == '__main__':
    main()
