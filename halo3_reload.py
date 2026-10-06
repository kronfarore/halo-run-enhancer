"""Reload-speed patching via first-person animation graphs (jmad), for the weapons
whose reload has no tag-side timer — the reload duration is the length of the
first-person reload ANIMATION. This module scales those animations in place. Supports
Halo 3 and Halo 2 (the two share the jmad approach but differ in block offsets).

Identification is robust, not frame-count guesswork: every fp graph's `Modes` tree
maps action Labels (stringIDs like `reload_empty`, `reload_full`, and the shotgun's
`reload_enter`/`reload_continue_*`/`reload_exit`) to an Animation Index. We resolve
each Action label to its name and take every animation targeted by a `reload*`
action, then scale that animation's Frame Count and every keyed event frame by the
multiplier, so the mag-refill keyframe and sounds stay in sync.

Two dedup traps handled: several actions point at the same animation index, and
several animations share one physical event block — each animation and each event
element is scaled exactly once.

Layouts (see Assembly Halo3/Halo2/ODST jmad.xml):
  Halo 3: Animations @0x50 el0x88 (Frame Count i16@0x10); event blocks 0x2C/0x38/0x44/0x50
          (frame i16@+0x2); Modes @0x5C el0x28 -> WClass @0x4 el0x1C -> WType @0x4 el0x34
          -> Actions @0x4 el0x08 (Label sid@0, Anim Index i16@6).
  ODST:   Halo 3's, except Effect Events is el0xC (not 0x8) -- the ONLY divergence.
  Halo 2: Animations @0x2C el0x60 (Frame Count i16@0x14); event blocks 0x40/0x48/0x50
          (frame i16@+0x2); Modes @0x34 el0x14 -> WClass @0x4 el0x14 -> WType @0x4 el0x34
          -> Actions @0x4 el0x08 (Label sid@0, Anim Index i16@6).
"""
import struct

# (anim_blk, anim_el, frame_count_off, event_blocks[(blk,el)], frame_off_in_event,
#  modes_blk, modes_el, wclass_blk, wclass_el, wtype_blk, wtype_el, actions_blk,
#  actions_el, action_anim_idx_off)
LAYOUTS = {
    'Halo 3': dict(anim_blk=0x50, anim_el=0x88, fc_off=0x10,
                   events=((0x2C, 0x04), (0x38, 0x08), (0x44, 0x08), (0x50, 0x04)),
                   frame_off=0x2, modes_blk=0x5C, modes_el=0x28,
                   wclass_blk=0x04, wclass_el=0x1C, wtype_blk=0x04, wtype_el=0x34,
                   actions_blk=0x04, actions_el=0x08, act_anim_off=0x6),
    'Halo 2': dict(anim_blk=0x2C, anim_el=0x60, fc_off=0x14,
                   events=((0x40, 0x04), (0x48, 0x08), (0x50, 0x04)),
                   frame_off=0x2, modes_blk=0x34, modes_el=0x14,
                   wclass_blk=0x04, wclass_el=0x14, wtype_blk=0x04, wtype_el=0x34,
                   actions_blk=0x04, actions_el=0x08, act_anim_off=0x6),
    # ODST was missing entirely, so `scale_reload` bailed with "no reload layout for
    # Halo 3: ODST" on every ODST map and the reload cards -- inherited from Halo 3 like
    # the rest -- never did anything. Its jmad is Halo 3's with ONE difference: Effect
    # Events is 0xC per element, not 0x8. Striding it at 8 would walk the wrong frame
    # fields and corrupt the sound/effect timing of every reload it touched, so the
    # layout is copied out rather than aliased to Halo 3's.
    'Halo 3: ODST': dict(anim_blk=0x50, anim_el=0x88, fc_off=0x10,
                         events=((0x2C, 0x04), (0x38, 0x08), (0x44, 0x0C), (0x50, 0x04)),
                         frame_off=0x2, modes_blk=0x5C, modes_el=0x28,
                         wclass_blk=0x04, wclass_el=0x1C, wtype_blk=0x04, wtype_el=0x34,
                         actions_blk=0x04, actions_el=0x08, act_anim_off=0x6),
    # Reach restructured the graph in two ways, both found empirically -- the ReachMCC
    # plugin names neither the action Label nor its Animation Index, so there was
    # nothing to read them off.
    #   * The Modes tree gains a SETS level between Weapon Type and Actions, and the
    #     action's Animation Index sits at +0xA rather than +0x6.
    #   * An animation element is only a header now: Frame Count and all four event
    #     blocks moved into a nested Shared Animation Data block at +0x30 (0xD4 each).
    # Verified on fp_assault_rifle -- ready 20f, put_away 5f, reload_empty 68f,
    # reload_full 59f, plus the sprint_* actions no earlier game has.
    'Halo Reach': dict(anim_blk=0x94, anim_el=0x3C,
                       shared_blk=0x30, shared_el=0xD4, fc_off=0x2,
                       events=((0x38, 0x04), (0x44, 0x08), (0x50, 0x0C), (0x5C, 0x04)),
                       frame_off=0x2, modes_blk=0x104, modes_el=0x30,
                       wclass_blk=0x0C, wclass_el=0x38, wtype_blk=0x08, wtype_el=0x14,
                       sets_blk=0x08, sets_el=0x48,
                       actions_blk=0x0C, actions_el=0x0C, act_anim_off=0xA),
    # Halo 4 (Halo4 jmad plugin; there is no Halo4MCC one). Reach's tree with three
    # differences, all read off the plugin and checked on storm_elite_ai (Requiem):
    #   * Frame Count is at +0x0 of the Shared Animation Data, not Reach's +0x2.
    #   * Script Events keep their frame at +0x4, so an event block may name its own
    #     frame offset as a third tuple member.
    #   * An action carries a Graph Index (+0x8) beside its Animation Index (+0xA). -1 is
    #     this graph; anything else points into another graph, and scaling this graph's
    #     animation at that index would hit an unrelated animation -- such actions are
    #     skipped (none of the berserk actions measured so far use one).
    # The Elite's `go_berserk` actions (the label differs from Halo 3's `berserk`, the
    # substring match takes both) resolve to animations of 36-58 frames.
    # Halo 4 animation data lives in resources; only the header frame counts and event
    # frames are scaled here, exactly as for Reach -- untested in game.
    'Halo 4': dict(anim_blk=0x9C, anim_el=0x40,
                   shared_blk=0x34, shared_el=0xDC, fc_off=0x0,
                   events=((0x34, 0x04), (0x40, 0x08), (0x4C, 0x0C), (0x58, 0x04),
                           (0x64, 0x08, 0x4)),
                   frame_off=0x2, modes_blk=0x13C, modes_el=0x30,
                   wclass_blk=0x0C, wclass_el=0x38, wtype_blk=0x08, wtype_el=0x14,
                   sets_blk=0x08, sets_el=0x48,
                   actions_blk=0x0C, actions_el=0x0C, act_anim_off=0xA,
                   act_graph_off=0x8),
}


def _reload_anim_indices(m, base, L, match=('reload',)):
    """Animation indices driven by any action whose resolved label contains one of
    `match`. Deduped, order-preserving.

    `match` is a parameter because the swap is the same problem as the reload: weapon
    SWAP speed is the `ready` and `put_away` animations in this very graph, and no
    weap field drives it (Ready Time is non-zero on three weapons, ODST's Weapon Ready
    1st Person Animation Playback Scale on none at all).
    """
    out, seen = [], set()
    # `anim:<text>` entries match the ANIMATION's own name instead of an action label.
    # Some animations are never behind an action -- the Flood pure forms' transformation
    # plays `combat:to_tank` / `combat:from_stalker` as mode transitions -- so they can
    # only be found by name. Needs the dynamic stringID lookup (halo3_map, 2026-09-17).
    names = [k[5:] for k in match if k.startswith('anim:')]
    match = tuple(k for k in match if not k.startswith('anim:'))
    if names:
        for ai, el in enumerate(m.follow_all(base, [L['anim_blk']], [L['anim_el']], 'all')):
            nm = m.resolve_stringid(struct.unpack_from('<I', m.data, el)[0]) or ''
            if any(k in nm for k in names) and ai not in seen:
                seen.add(ai)
                out.append(ai)
    if not match:
        return out
    for mo in m.follow_all(base, [L['modes_blk']], [L['modes_el']], 'all'):
        for wc in m.follow_all(mo, [L['wclass_blk']], [L['wclass_el']], 'all'):
            for wt in m.follow_all(wc, [L['wtype_blk']], [L['wtype_el']], 'all'):
                # Reach inserts a Sets level between Weapon Type and Actions; the
                # earlier games go straight there, so an absent key means "no level".
                holders = ([wt] if not L.get('sets_blk') else
                           m.follow_all(wt, [L['sets_blk']], [L['sets_el']], 'all'))
                for holder in holders:
                 for a in m.follow_all(holder, [L['actions_blk']], [L['actions_el']], 'all'):
                    label = struct.unpack_from('<I', m.data, a)[0]
                    name = m.resolve_stringid(label)
                    if not _matches(name, match):
                        continue
                    if L.get('act_graph_off') is not None and struct.unpack_from(
                            '<h', m.data, a + L['act_graph_off'])[0] >= 0:
                        continue           # animation lives in another graph
                    ai = struct.unpack_from('<h', m.data, a + L['act_anim_off'])[0]
                    if ai >= 0 and ai not in seen:
                        seen.add(ai)
                        out.append(ai)
    return out


def _matches(name, match):
    """Does this animation name name one of the actions we are after?

    Separators are normalised because the games do not agree: Halo 3 onward name the
    jmad action `put_away`, Halo 1's antr calls the same animation
    "first-person put-away". Matching on the raw string silently missed every Halo 1
    swap animation.
    """
    n = (name or '').lower().replace('-', '_')
    return any(k.replace('-', '_') in n for k in match)


FPS = 30.0     # jmad/antr animations play at 30 fps (NTSC); reload seconds = frames / FPS


def reload_frames(m, tag_pattern, game='Halo 3', match=('reload',)):
    """Reference read for the patcher: reload-animation frame counts per graph, as
    [(who, [frames...]), ...]. Abstracts the H1 antr vs H2/H3 jmad layouts. `who` is a
    friendly label (Master Chief / Arbiter / tag basename). Returns [] if none found."""
    g = str(game).strip()

    def who_of(name):
        if 'dervish' in name:
            return 'Arbiter'
        if 'masterchief' in name:
            return 'Master Chief'
        base = name.rsplit(chr(92), 1)[-1]
        return 'first-person' if base == 'fp' else base

    out = []
    if g == 'Halo 1':
        for name, base in m.find_tags('antr', tag_pattern):
            fcs = []
            for el in m.follow_all(base, [H1_ANIM_BLK], [H1_ANIM_EL], 'all'):
                nm = m.data[el:m.data.index(b'\x00', el)].decode('latin1', 'replace')
                if _matches(nm, match):
                    fcs.append(struct.unpack_from('<h', m.data, el + H1_FC)[0])
            if fcs:
                out.append((who_of(name), sorted(set(fcs))))
        return out
    L = LAYOUTS.get(g)
    if L is None or not hasattr(m, 'resolve_stringid'):
        return out
    for name, base in m.find_tags('jmad', tag_pattern):
        anims = m.follow_all(base, [L['anim_blk']], [L['anim_el']], 'all')
        fcs = set()
        for i in _reload_anim_indices(m, base, L, match):
            if not (0 <= i < len(anims)):
                continue
            el = anims[i]
            if L.get('shared_blk') is not None:
                # Reach keeps Frame Count in the Shared Animation Data, as scale_reload
                # already knew; reading it off the header showed a wrong length there.
                shared = m.follow_all(el, [L['shared_blk']], [L['shared_el']], 'all')
                if not shared:
                    continue
                el = shared[0]
            fcs.add(struct.unpack_from('<h', m.data, el + L['fc_off'])[0])
        if fcs:
            out.append((who_of(name), sorted(fcs)))
    return out


def _scale_frame(m, off, mult, cap):
    v = struct.unpack_from('<h', m.data, off)[0]
    nv = max(0, min(cap, int(round(v * mult))))
    struct.pack_into('<h', m.data, off, nv)
    return v, nv


# A frame count is a signed 16-bit value: the engine's own ceiling on how long an
# animation can get. An inverted (slowing) reload / swap card stacks without a cap of
# its own and is saturated only when every animation it scales sits here.
FRAME_LIMIT = 0x7FFF


# --- Halo 1: model_animations (antr) master Animations block ---
# elem 0xB4: Name ascii@0x0 (0x20), Frame Count i16@0x22, Loop Frame @0x2E,
# Key Frame @0x34, Second Key Frame @0x36, Sound Frame @0x3E, foot i8 @0x40/0x41.
H1_ANIM_BLK, H1_ANIM_EL, H1_FC = 0x74, 0xB4, 0x22
H1_I16_FRAMES = (0x2E, 0x34, 0x36, 0x3E)
H1_I8_FRAMES = (0x40, 0x41)
# Frame Size i16@0x24, Frame Info Type enum16@0x26, and three data refs (size i32@+0,
# pointer@+0xC, magic-relative): Frame Info @0x48, Default Data @0x8C, Frame Data @0xA0.
H1_FRAME_SIZE, H1_INFO_TYPE = 0x24, 0x26
H1_FRAME_INFO, H1_FRAME_DATA = 0x48, 0xA0
# Frame Info Type: none / dx,dy / dx,dy,dyaw / dx,dy,dz,dyaw -> bytes per frame. Measured
# on all ten campaign maps (5390 animations): size / frame count is exactly 0/8/12/16.
H1_INFO_SIZES = (0, 8, 12, 16)


def _h1_dataref(m, el, off):
    """(size, file offset) of an animation data ref, or (0, None)."""
    size = m.i32(el + off)
    ptr = m.u32(el + off + 0xC)
    if size <= 0 or not ptr:
        return 0, None
    return size, (ptr - m.magic) & 0xFFFFFFFF


def _h1_resample(m, el, old_fc, new_fc, off, per_frame):
    """Rebuild one of an animation's per-frame buffers for a new frame count: each new
    frame takes the nearest old one. Halo 1 animations are uncompressed, so this is a
    straight copy. Written in place when it fits, else appended to the tag data at EOF
    (append_raw) and the ref repointed -- which is what lets an animation grow LONGER;
    rewriting the frame count alone would read past the stored frames."""
    size, src = _h1_dataref(m, el, off)
    if not size or per_frame <= 0 or old_fc < 1:
        return False
    have = min(old_fc, size // per_frame)
    if have < 1:
        return False
    out = bytearray()
    for i in range(new_fc):
        k = 0 if new_fc == 1 else int(round(i * (have - 1) / float(new_fc - 1)))
        k = max(0, min(have - 1, k))
        out += bytes(m.data[src + k * per_frame:src + (k + 1) * per_frame])
    if len(out) <= size:
        m.data[src:src + len(out)] = out
    else:
        new_off = m.append_raw(bytes(out))
        struct.pack_into('<I', m.data, el + off + 0xC, (new_off + m.magic) & 0xFFFFFFFF)
    struct.pack_into('<i', m.data, el + off, len(out))
    return True


def _scale_reload_h1(m, tag_pattern, mult, match=('reload',)):
    tags = m.find_tags('antr', tag_pattern)
    if not tags:
        return {'ok': False, 'reason': f'no antr tags match {tag_pattern!r}'}
    graphs = anims_scaled = edits = capped = 0
    for _, base in tags:
        anims = m.follow_all(base, [H1_ANIM_BLK], [H1_ANIM_EL], 'all')
        hit = False
        for el in anims:
            nm = m.data[el:m.data.index(b'\x00', el)].decode('latin1', 'replace')
            if not _matches(nm, match):
                continue
            hit = True
            old_fc = struct.unpack_from('<h', m.data, el + H1_FC)[0]
            _, new_fc = _scale_frame(m, el + H1_FC, mult, FRAME_LIMIT)
            capped += new_fc >= FRAME_LIMIT
            if new_fc < 1:
                new_fc = 1
                struct.pack_into('<h', m.data, el + H1_FC, 1)
            # The frames themselves, so the motion plays whole at its new length (and so
            # a LONGER animation has frames to play).
            if new_fc != old_fc and hasattr(m, 'append_raw'):
                frame_size = struct.unpack_from('<h', m.data, el + H1_FRAME_SIZE)[0]
                _h1_resample(m, el, old_fc, new_fc, H1_FRAME_DATA, frame_size)
                itype = struct.unpack_from('<h', m.data, el + H1_INFO_TYPE)[0]
                if 0 <= itype < len(H1_INFO_SIZES) and H1_INFO_SIZES[itype]:
                    _h1_resample(m, el, old_fc, new_fc, H1_FRAME_INFO, H1_INFO_SIZES[itype])
            anims_scaled += 1
            edits += 1
            cap = new_fc - 1
            for off in H1_I16_FRAMES:
                _scale_frame(m, el + off, mult, cap)          # 0 stays 0
                edits += 1
            for off in H1_I8_FRAMES:
                v = m.data[el + off]
                if v not in (0, 0xFF):                        # 0xFF = unset
                    m.data[el + off] = max(0, min(cap, int(round(v * mult))))
        if hit:
            graphs += 1
    if anims_scaled == 0:
        return {'ok': True, 'skip': True, 'reason': 'no reload animations found',
                'graphs': graphs, 'animations': 0, 'edits': 0}
    return {'ok': True, 'graphs': graphs, 'animations': anims_scaled, 'edits': edits,
            'capped': capped}


# --- Halo 1 enemy ground speed: the ROOT MOTION of the move-* animations ---
# AI ground speed has no tag field in Halo 1: the engine moves an AI biped by the
# per-frame dx,dy of its move-* animation's Frame Info (confirmed in game on b30,
# 2026-10-03: x2 data, everybody moved twice as fast, legs looked fine). Speed in wu/s
# = sum(dx, dy) / frames * FPS; Elite stand move-front ships 2.25 wu over 26 frames.
# Covers every stance (stand / crouch / alert / flee / flaming) and direction.

def h1_move_anims(m, antr_base):
    """[(name, frame count, info type, info size, info file offset)] -- move-* only
    ('aim-move' is an aiming overlay with no root motion and does not match)."""
    out = []
    for el in m.follow_all(antr_base, [H1_ANIM_BLK], [H1_ANIM_EL], 'all'):
        nm = m.data[el:m.data.index(b'\x00', el)].decode('latin1', 'replace')
        if 'move-' not in nm:
            continue
        fc = struct.unpack_from('<h', m.data, el + H1_FC)[0]
        it = struct.unpack_from('<h', m.data, el + H1_INFO_TYPE)[0]
        size, off = _h1_dataref(m, el, H1_FRAME_INFO)
        out.append((nm, fc, it, size, off))
    return out


def h1_move_speed(m, fc, it, size, off):
    """(sum dx, sum dy, wu/s) of one move animation's root motion."""
    per = H1_INFO_SIZES[it] if 0 <= it < len(H1_INFO_SIZES) else 0
    if not per or off is None or fc < 1:
        return 0.0, 0.0, 0.0
    sx = sy = 0.0
    for i in range(min(fc, size // per)):
        dx, dy = struct.unpack_from('<2f', m.data, off + i * per)
        sx += dx
        sy += dy
    return sx, sy, (sx * sx + sy * sy) ** 0.5 / fc * FPS


# --- Halo 2: the same root motion, OUTSIDE the codec data, in the built map ---
# jmad Animations +0x2C, element 0x60: Name stringId +0x0, Frame Info Type u8 +0x11,
# Frame Count i16 +0x14, Resource dataref +0x28 (size i32, pointer -> p2o), data sizes
# +0x30: u8 static flags, u8 animated flags, i16 movement, i16 pill, i16 default,
# i32 uncompressed (0 once built), i32 compressed. The blob is [default][compressed]
# [static flags][animated flags][MOVEMENT][pill][uncompressed], the movement section
# plain dx,dy(,dz)(,dyaw) floats. The sizes sum to the dataref size on every
# root-motion animation of all 14 campaign maps. Confirmed in game on 03a (2026-10-03):
# x2 made every Covenant twice as fast on foot.
H2_ANIM_BLK, H2_ANIM_EL = 0x2C, 0x60


def h2_move_anims(m, jmad_base):
    """[(name, frame count, info type, info size, info file offset)] for every animation
    with root motion whose name holds `move_` -- runs, strafes, the idle<->move
    transitions and flight moves ('aim_move' overlays carry none). An element whose
    sizes do not add up is left out rather than written blind."""
    out = []
    for el in m.follow_all(jmad_base, [H2_ANIM_BLK], [H2_ANIM_EL], 'all'):
        it = m.data[el + 0x11]
        if not (0 < it < len(H1_INFO_SIZES)):
            continue
        nm = m.resolve_stringid(m.u32(el)) or ''
        if 'move_' not in nm or 'aim_move' in nm:
            continue
        fc = struct.unpack_from('<h', m.data, el + 0x14)[0]
        rsize, rptr = struct.unpack_from('<iI', m.data, el + 0x28)
        sf, af, mv, pill, dflt, unc, cmp = struct.unpack_from('<BBhhhii', m.data, el + 0x30)
        if (fc < 1 or mv != H1_INFO_SIZES[it] * fc or rsize <= 0
                or sf + af + mv + pill + dflt + unc + cmp != rsize):
            continue
        out.append((nm, fc, it, mv, m.p2o(rptr) + dflt + cmp + sf + af))
    return out


_MOVE_GAMES = {'Halo 1': ('antr', h1_move_anims), 'Halo 2': ('jmad', h2_move_anims)}


# Halo Reach shares Halo 3's zone and pages (its own 0x64-byte member record and Shared
# Animation Data path are handled inside h3_move_speed). Confirmed in game on m45.
# Halo 4 too: its own zone layout and 0x68 member, also inside h3_move_speed. Confirmed
# in game on m10 (Covenant) and m30 (Forerunner).
_H3_GAMES = ('Halo 3', 'Halo 3: ODST', 'Halo Reach', 'Halo 4')


def _is_run(game, name):
    """The plain run: Halo 1 `stand ... move-front`; from Halo 2 on `combat:<weapon>:
    move_front` and its `:varN` permutations (the Halo 3 Hunter's is `any:any:
    move_front`), never a transition."""
    if game == 'Halo 1':
        return name.startswith('stand ') and 'move-front' in name
    # Halo 4 calls it `locomote_run_front`
    return (name.startswith(('combat:', 'any:'))
            and (':move_front' in name or ':locomote_run_front' in name)
            and ':2:' not in name)


def _h3_pages():
    """Halo 3 / ODST keep the frames in compressed resource pages; that reader and writer
    live in sprint_toolkit/h3_move_speed.py (zone control data, raw-page fixups, deflate,
    page checksums)."""
    import os
    import sys
    tk = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sprint_toolkit')
    if tk not in sys.path:
        sys.path.insert(0, tk)
    import h3_move_speed
    return h3_move_speed


def _h3_move_speeds(m, tag_pattern, game):
    ms = _h3_pages()
    pages = ms.Pages(m)
    out = []
    for name, base in m.find_tags('jmad', tag_pattern):
        runs = []
        for nm, it, fc, pi, off in ms.move_anims(m, pages, base):
            if _is_run(game, nm) and pages.local(pi):
                runs.append(ms.speed(pages.get(pi), it, fc, off))
        if runs:
            out.append((name.rsplit(chr(92), 1)[-1], max(runs)))
    return out


def _h3_scale_move_speed(m, tag_pattern, mult):
    ms = _h3_pages()
    tags = m.find_tags('jmad', tag_pattern)
    if not tags:
        return {'ok': False, 'reason': 'not present in this map'}
    pages = ms.Pages(m)
    done, outside = set(), 0
    graphs = 0
    for _, base in tags:
        hit = False
        for _nm, it, fc, pi, off in ms.move_anims(m, pages, base):
            if not pages.local(pi):
                outside += 1          # a vanilla map keeps them in campaign/shared.map
                continue
            if (pi, off) in done:
                continue
            per = H1_INFO_SIZES[it]
            pg = pages.get(pi)
            for i in range(fc):
                dx, dy = struct.unpack_from('<2f', pg, off + i * per)
                struct.pack_into('<2f', pg, off + i * per, dx * mult, dy * mult)
            done.add((pi, off))
            pages.dirty.add(pi)
            hit = True
        graphs += hit
    pages.write_back()
    if not done:
        reason = ('animation pages live outside this map (vanilla map: campaign/shared.map)'
                  if outside else 'no move animations with root motion')
        return {'ok': True, 'skip': True, 'reason': reason, 'graphs': 0, 'animations': 0}
    return {'ok': True, 'graphs': graphs, 'animations': len(done), 'pages': len(pages.dirty),
            'outside': outside}


def move_speeds(m, tag_pattern, game='Halo 1'):
    """Reference read for the patcher: [(who, run wu/s)] per graph -- the fastest plain
    run. [] if none, or for a game whose root motion is not reachable."""
    g = str(game).strip()
    if g in _H3_GAMES:
        return _h3_move_speeds(m, tag_pattern, g)
    if g not in _MOVE_GAMES:
        return []
    cls, reader = _MOVE_GAMES[g]
    out = []
    for name, base in m.find_tags(cls, tag_pattern):
        runs = [h1_move_speed(m, *a[1:])[2] for a in reader(m, base) if _is_run(g, a[0])]
        if runs:
            out.append((name.rsplit(chr(92), 1)[-1], max(runs)))
    return out


def scale_move_speed(m, tag_pattern, mult, game='Halo 1'):
    """Multiply the dx,dy root motion of every move animation on every graph matching
    `tag_pattern` (antr in Halo 1, jmad from Halo 2; dz and dyaw untouched, frame counts
    untouched). A buffer two animations share is scaled once. Halo 3 / ODST hold the
    frames in compressed resource pages: edited pages are recompressed in place with
    fresh checksums (confirmed in game on 010, 2026-10-03); Halo Reach the same way
    (m45) and Halo 4 (m10, m30)."""
    g = str(game).strip()
    if mult is None or mult <= 0:
        return {'ok': False, 'reason': 'invalid movement multiplier'}
    if g in _H3_GAMES:
        return _h3_scale_move_speed(m, tag_pattern, mult)
    if g not in _MOVE_GAMES:
        return {'ok': False, 'reason': f'movement speed is not reachable in {game}'}
    cls, reader = _MOVE_GAMES[g]
    tags = m.find_tags(cls, tag_pattern)
    if not tags:
        # apply_run's exact wording for an absent tag: an enemy card turns it into
        # "not on this level" (absent_is_skip) instead of a failure
        return {'ok': False, 'reason': 'not present in this map'}
    done = set()
    graphs = 0
    for _, base in tags:
        hit = False
        for _nm, fc, it, size, off in reader(m, base):
            per = H1_INFO_SIZES[it] if 0 <= it < len(H1_INFO_SIZES) else 0
            if not per or off is None or off in done:
                continue
            done.add(off)
            hit = True
            for i in range(min(fc, size // per)):
                dx, dy = struct.unpack_from('<2f', m.data, off + i * per)
                struct.pack_into('<2f', m.data, off + i * per, dx * mult, dy * mult)
        graphs += hit
    if not done:
        return {'ok': True, 'skip': True, 'reason': 'no move animations with root motion',
                'graphs': 0, 'animations': 0}
    return {'ok': True, 'graphs': graphs, 'animations': len(done)}


def scale_reload(m, tag_pattern, mult, game='Halo 3', match=('reload',)):
    """Scale animation length by `mult` (0.5 = half duration = faster) on every jmad
    tag matching `tag_pattern`. `match` picks WHICH actions: ('reload',) for reload
    speed, ('ready', 'put_away') for weapon swap speed.

    Scale reload animation length by `mult` on every jmad tag matching `tag_pattern`. Idempotency is the caller's job: like every op it
    runs from the pristine .bak baseline, so re-patching re-scales the original frame
    counts rather than compounding. Returns a report dict."""
    if mult is None or mult <= 0:
        return {'ok': False, 'reason': 'invalid reload multiplier'}
    if str(game).strip() == 'Halo 1':
        return _scale_reload_h1(m, tag_pattern, mult, match)  # antr, ascii-named, no stringID
    L = LAYOUTS.get(str(game).strip())
    if L is None:
        return {'ok': False, 'reason': f'no reload layout for {game}'}
    if mult > 1 and str(game).strip() not in ('Halo 3', 'Halo 3: ODST'):
        # Only the Frame Count could be raised here, and the engine would then read past
        # the stored frames (memory h3-animation-format). Halo 1 resamples and Halo 3 /
        # ODST rebuild them (h3_anim_lengthen); the other games' codecs are not done yet.
        return {'ok': True, 'skip': True,
                'reason': f'animations cannot be made longer in {game} yet'}
    if not hasattr(m, 'resolve_stringid'):
        return {'ok': False, 'reason': f'{game} map has no stringID resolver'}
    tags = m.find_tags('jmad', tag_pattern)
    if not tags:
        return {'ok': False, 'reason': f'no jmad tags match {tag_pattern!r}'}
    graphs = anims_scaled = edits = capped = 0
    seen_events = set()          # (frame_field_addr) — event blocks are shared between anims
    fo = L['frame_off']
    # LONGER (an inverted card): Halo 3 / ODST rebuild the frames themselves
    # (h3_anim_lengthen); raising the Frame Count alone reads past the stored frames.
    # An animation that cannot be rebuilt keeps its length rather than break.
    grow = mult > 1 and str(game).strip() in ('Halo 3', 'Halo 3: ODST')
    lg = _H3Lengthener(m) if grow else None
    not_longer = {}
    for _, base in tags:
        idxs = _reload_anim_indices(m, base, L, match)
        if not idxs:
            continue
        anims = m.follow_all(base, [L['anim_blk']], [L['anim_el']], 'all')
        graphs += 1
        for ai in idxs:
            if not (0 <= ai < len(anims)):
                continue
            el = anims[ai]
            if grow:
                why = lg.lengthen(base, el, mult)
                if why:
                    not_longer[why] = not_longer.get(why, 0) + 1
                    continue
            if L.get('shared_blk') is not None:
                # Reach: the element is a header; Frame Count and every event block
                # live in the Shared Animation Data it points at.
                shared = m.follow_all(el, [L['shared_blk']], [L['shared_el']], 'all')
                if not shared:
                    continue
                el = shared[0]
            _, new_fc = _scale_frame(m, el + L['fc_off'], mult, FRAME_LIMIT)
            capped += new_fc >= FRAME_LIMIT
            if new_fc < 1:
                new_fc = 1
                struct.pack_into('<h', m.data, el + L['fc_off'], 1)
            anims_scaled += 1
            edits += 1
            cap = new_fc - 1
            for ev in L['events']:
                blk_off, elem_sz = ev[0], ev[1]
                efo = ev[2] if len(ev) > 2 else fo      # Halo 4 Script Events: +0x4
                for e in m.follow_all(el, [blk_off], [elem_sz], 'all'):
                    key = e + efo
                    if key in seen_events:
                        continue
                    seen_events.add(key)
                    _scale_frame(m, e + efo, mult, cap)
                    edits += 1
    moved = lg.finish() if grow else []
    if anims_scaled == 0:
        return {'ok': True, 'skip': True,
                'reason': ('not made longer: ' + '; '.join(
                    '%d %s' % (n, w) for w, n in not_longer.items())
                    if not_longer else 'no reload animations found'),
                'graphs': graphs, 'animations': 0, 'edits': 0}
    out = {'ok': True, 'graphs': graphs, 'animations': anims_scaled, 'edits': edits,
           'capped': capped}
    if grow:
        out['pages_moved'] = len([x for x in moved if x[0] != 'in place'])
        if not_longer:
            out['not_longer'] = not_longer
    return out


class _H3Lengthener:
    """Per map: rebuild Halo 3 / ODST animations at a new length (h3_anim_lengthen),
    each (resource, member) once, and write the touched pages back at the end."""

    def __init__(self, m):
        ms = _h3_pages()                       # puts sprint_toolkit on the path
        import h3_anim_lengthen as hl
        self.m, self.hl = m, hl
        self.pages = ms.Pages(m)
        self.res = {}
        self.done = {}

    def lengthen(self, base, el, mult):
        """None when animation `el` was rebuilt (the caller then scales its Frame Count
        and events by the same rounding), else why it was not."""
        m = self.m
        groups = m.follow_all(base, [0xF8], [0xC], 'all')
        g, k = struct.unpack_from('<hh', m.data, el + 0x28)
        if not (0 <= g < len(groups)):
            return 'animation borrowed from another graph'
        rid = m.u32(groups[g] + 4) & 0xFFFF
        if rid not in self.res:
            self.res[rid] = self.hl.Resource(m, self.pages, rid)
        r = self.res[rid]
        if not r.usable():
            return 'frames stored outside this map'
        if not (0 <= k < len(r.members)):
            return 'no such resource member'
        if (rid, k) not in self.done:
            fc = struct.unpack_from('<h', m.data, el + 0x10)[0]
            new_fc = max(1, min(FRAME_LIMIT, int(round(fc * mult))))
            got = r.lengthen(k, new_fc)
            self.done[(rid, k)] = got if isinstance(got, str) else None
        return self.done[(rid, k)]

    def finish(self):
        for r in self.res.values():
            if any(x.get('data') for x in r.members):
                r.relayout()
        return self.hl.write_back(self.pages)
