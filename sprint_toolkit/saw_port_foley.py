r"""The SAW ports' RELOAD and READY sounds, from Halo 4's own SAW foley (2026-10-04, user:
the Halo 1 SAW "still holds the AR swap and reload sounds").

HALO 4 CUES THEM BY FRAME (storm_fp_lmg.frame_event_list, frames at 30 fps):
    reload_full / reload_empty   fly_a @0, mech_a @15, mech_b @30, fly_b @54, mech_c @66,
                                 fly_c @90, mech_d @90                (128 frames long)
    ready                        ready_fly @0, ready_mech @0           (35 frames)
each event a random container of 2-3 recordings (H4EK\temp\saw_sounds\<event>\*.wav).

A game whose animation plays ONE sound (Halo 1: a sound + sound frame per animation)
gets a MIXDOWN: every cue placed at its frame, `stretch` scaling the positions for an
animation retimed to another length (Halo 1's balanced reload: 164/128). Variation set
k takes recording k (mod its count) of every event, so the port keeps H4's variety as
permutations. Mono, 48 kHz, levels as recorded (the game levels them).

    from saw_port_foley import mix, RELOAD, READY
    x = mix(RELOAD, k=0, stretch=1.0)             # float mono, RATE
"""
import glob
import os
import wave

import numpy as np

SRC = r'F:\SteamLibrary\steamapps\common\H4EK\temp\saw_sounds'
RATE = 48000
FPS = 30.0
RELOAD = [('play_wea_lmg_reload_fly_a', 0), ('play_wea_lmg_reload_mech_a', 15),
          ('play_wea_lmg_reload_mech_b', 30), ('play_wea_lmg_reload_fly_b', 54),
          ('play_wea_lmg_reload_mech_c', 66), ('play_wea_lmg_reload_fly_c', 90),
          ('play_wea_lmg_reload_mech_d', 90)]
READY = [('play_wea_lmg_ready_fly', 0), ('play_wea_lmg_ready_mech', 0)]
RELOAD_FRAMES, READY_FRAMES = 128, 35
# second batch (2026-10-04): melee (one random recording of 8 / 6), the idle fidgets
# (posing var1 / var2: three pieces at frames 0, 40, 80 of 90 / 106 frames) and the
# first draw (ready_initial: THREE LAYERS played together -- 'all' sums every recording).
# The SAW's zoom-in/out tags name events no Halo 4 bank in MCC contains: nothing to port.
MELEE1 = [('play_wea_lmg1_foley_melee_player', 0)]
MELEE2 = [('play_wea_lmg2_foley_melee_player', 0)]
POSE1 = [('play_wea_lmg_pose_var_1_a', 0), ('play_wea_lmg_pose_var_1_b', 40),
         ('play_wea_lmg_pose_var_1_c', 80)]
POSE2 = [('play_wea_lmg_pose_var_2_a', 0), ('play_wea_lmg_pose_var_2_b', 40),
         ('play_wea_lmg_pose_var_2_c', 80)]
READY_INITIAL = [('play_wea_lmg_ready_initial', 0, 'all')]
POSE1_FRAMES, POSE2_FRAMES, READY_INITIAL_FRAMES = 90, 106, 35


def _read(p):
    with wave.open(p, 'rb') as r:
        ch, rate = r.getnchannels(), r.getframerate()
        a = np.frombuffer(r.readframes(r.getnframes()), dtype=np.int16).astype(np.float64)
    if rate != RATE:
        raise ValueError('%s: %d Hz, want %d' % (p, rate, RATE))
    return a.reshape(-1, ch).mean(1) / 32768.0


def variations(event):
    return sorted(glob.glob(os.path.join(SRC, event, '*.wav')))


def mix(cues, k=0, stretch=1.0):
    """The cues mixed at their frames (x stretch), recording k of each event."""
    parts = []
    for cue in cues:
        event, frame = cue[0], cue[1]
        files = variations(event)
        if not files:
            raise SystemExit('no recordings for %s in %s' % (event, SRC))
        at = int(round(frame / FPS * stretch * RATE))
        if len(cue) > 2 and cue[2] == 'all':            # layers, all played together
            parts += [(at, _read(f)) for f in files]
        else:
            parts.append((at, _read(files[k % len(files)])))
    n = max(at + len(x) for at, x in parts)
    out = np.zeros(n)
    for at, x in parts:
        out[at:at + len(x)] += x
    return out


def count(cues):
    """How many distinct variation sets the cues offer (the largest container)."""
    return max(1 if len(c) > 2 and c[2] == 'all' else len(variations(c[0])) for c in cues)
