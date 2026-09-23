"""Give the ported weapon its own first-person animation set, retimed to its identity.

The port borrows the donor's animations (Halo 1 AR), so its reload and weapon swap run at
the DONOR's speed. Here the donor's animation tag is cloned for the port and the relevant
animations are RESAMPLED to a new length -- Halo 1 animations are uncompressed, frame_data
is exactly frame_count * frame_size bytes, so a new frame simply takes the nearest source
frame. Key/loop/sound/foot frame indices scale with it.

Lengths (frames at 30 fps, measured from the pristine maps):
                     H4 AR   H4 SAW   H1 AR
    reload             68      128      87
    ready/put away     30       35      29

    original  the port keeps its own timing: donor_dst * (ported_src / donor_dst)
              = the port's own duration (reload 128 = 4.3s)
    balanced  the port keeps its RELATIVE timing: donor_dst * (ported_src / donor_src)
              (reload 87 * 128/68 = 164 = 5.5s, i.e. as much slower than the H1 AR as the
              H4 SAW is slower than the H4 AR)

    python saw_anims.py [original|balanced]
"""
import copy, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
import env  # noqa
from reclaimer.hek.defs.antr import antr_def

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
DONOR = os.path.join(TAGS, 'weapons', 'assault rifle', 'fp', 'fp.model_animations')
OUT = os.path.join(TAGS, 'weapons', 'saw', 'fp', 'fp.model_animations')
# the balanced timing ships as a SECOND tag: the patcher's balance option repoints the
# weapon at it (a tag reference), because it cannot resample animations in a built map
# measured frame counts: (ported in source game, donor in source game)
SRC = {'reload': (128, 68), 'swap': (35, 30)}
GROUPS = {'reload': ('reload',), 'swap': ('ready', 'put-away', 'put_away')}
FRAME_FIELDS = ('loop_frame_index', 'key_frame_index', 'second_key_frame_index',
                'sound_frame_index', 'left_foot_frame_index', 'right_foot_frame_index')


def factor(group, mode, donor_dst_frames):
    ported_src, donor_src = SRC[group]
    if mode == 'balanced':
        return ported_src / float(donor_src)
    return ported_src / float(donor_dst_frames)      # absolute: the port's own duration


def resample(anim, new_fc):
    """Stretch/shrink one uncompressed Halo 1 animation to new_fc frames."""
    old_fc, size = anim.frame_count, anim.frame_size
    data = bytes(anim.frame_data.data)
    if old_fc < 1 or size < 1 or len(data) < old_fc * size or new_fc == old_fc:
        return False
    out = bytearray()
    for i in range(new_fc):
        src = 0 if new_fc == 1 else int(round(i * (old_fc - 1) / float(new_fc - 1)))
        src = max(0, min(old_fc - 1, src))
        out += data[src * size:(src + 1) * size]
    anim.frame_data.data = bytes(out)
    mult = new_fc / float(old_fc)
    for f in FRAME_FIELDS:
        v = anim[f]
        if isinstance(v, int) and 0 < v < 0xFF:
            anim[f] = max(0, min(new_fc - 1, int(round(v * mult))))
    anim.frame_count = new_fc
    return True


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else 'original').lower()
    t = antr_def.build(filepath=DONOR)
    anims = t.data.tagdata.animations.STEPTREE
    # the donor's own lengths, read BEFORE anything is resampled
    donor_dst = {g: max([a.frame_count for a in anims
                         if any(k in a.name.lower() for k in keys)] or [1])
                 for g, keys in GROUPS.items()}
    rows = []
    for anim in anims:
        name = anim.name.lower()
        for group, keys in GROUPS.items():
            if not any(k in name for k in keys):
                continue
            old = anim.frame_count
            new = max(1, int(round(old * factor(group, mode, donor_dst[group]))))
            if resample(anim, new):
                rows.append('%-34s %s %3d -> %3d frames (%.2fs -> %.2fs)' % (
                    anim.name, group, old, new, old / 30.0, new / 30.0))
            break
    out = OUT if mode == 'original' else OUT.replace('fp.model_animations', 'fp_balanced.model_animations')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    t.filepath = out
    t.serialize(temp=False, backup=False)
    print('mode', mode)
    for r in rows:
        print(' ', r)
    print('wrote', out)


if __name__ == '__main__':
    main()
