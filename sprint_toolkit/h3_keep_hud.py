r"""Keep the player's HUD up through Halo 3's chapter title cards.

ONE LINE, ONE FILE -- unlike Halo 1 and Halo 2
----------------------------------------------
Halo 1 and Halo 2 spell the beat out at all 44 / 21 call sites, so their tools have to
walk every level script. Halo 3 factors it into a shared helper in
`H3EK\data\globals\global_scripts.hsc`:

    (script static void chapter_start
        (chud_cinematic_fade 0 0.5)          <- the HUD hide, H2's verb renamed
        (cinematic_show_letterbox TRUE)
            (sleep 30))
    (script static void chapter_stop
        (cinematic_show_letterbox FALSE)
            (sleep 15)
        (chud_cinematic_fade 1 0.5)
        (game_save))

Commenting out those two calls keeps the HUD up and the black bars away for every
chapter title in the game, and it rides along with any level rebuild because
global_scripts is compiled into each cache. Only the hiding half is touched;
`chapter_stop`'s restores are left alone, so the HUD can never be stranded off and a
stray letterbox can always be cleared.

Halo 1 settled the shape on c40: dropping the HUD fade alone keeps the HUD but leaves
the bars, and dropping the letterbox with it removes the bars while the title still
draws.

WHAT IS DELIBERATELY NOT TOUCHED
--------------------------------
Surveying all 28 title-bearing script blocks across the nine campaign levels:

  12  call `chapter_start` / `chapter_stop`            <- fixed by this edit
   3  call `cinematic_fade_to_title` / `_slow`         <- left alone, see below
  21  call `cinematic_title_to_gameplay` (the EXIT)    <- nothing to do
   1  is a bare `cinematic_set_title` with no wrapper  <- nothing to hide it

`cinematic_fade_to_title` and `_slow` open with `(cinematic_stop)` and
`(camera_control OFF)`: they are the tail of a real CUTSCENE, where the HUD is already
off and is supposed to be. Same rule as the Halo 1 and Halo 2 tools -- cutscenes are
not our business.

None of the level scripts call `chud_cinematic_fade` for a title at all; every one that
hides the HUD does it through `chapter_start`.

    python h3_keep_hud.py            # dry run
    python h3_keep_hud.py --apply    # comment the hide out (backup kept)
    python h3_keep_hud.py --revert   # restore
    python h3_keep_hud.py --status   # is the edit in the source, and in the maps?

REBUILD
-------
global_scripts.hsc is compiled into every cache, so each level picks the change up the
next time it is built:

    cd H3EK && tool.exe build-cache-file levels\solo\<lvl>\<lvl> pc

then copy `H3EK\maps\<lvl>.map` into `halo3\maps\` and refresh `<lvl>.map.bak` (the Run
Enhancer patches FROM that baseline). If you are already rebuilding for the weapon
imports, apply this first and it comes along for free.
"""
import argparse
import os
import re

H3EK = r"F:\SteamLibrary\steamapps\common\H3EK"
GLOBALS = os.path.join(H3EK, "data", "globals", "global_scripts.hsc")
# WHAT HALO 3 ACTUALLY COMPILES. Editing the .hsc above does NOTHING: tool.exe reads
# the scenario_hs_source_file TAG, and dumps whatever it used into the
# H3EK reports folder, one global_scripts.hsc per level.
# Two builds were wasted before those dumps showed 0 keep-hud marks while the .hsc had 2.
GLOBALS_TAG = os.path.join(H3EK, "tags", "globals",
                           "global_scripts.scenario_hs_source_file")
REPORTS = os.path.join(H3EK, "reports")
DEPLOYED = (r"C:\Program Files (x86)\Steam\steamapps\common"
            r"\Halo The Master Chief Collection\halo3\maps")
BAK_SUFFIX = ".keephud.bak"
MARK = ";[keep-hud] "
# In the TAG the comment is made by overwriting "(" with ";", so the marker to
# look for is the commented call itself rather than a inserted label.
MARK_TAG = b";chud_cinematic_fade 0 0.5)"

LEVELS = ["010_jungle", "020_base", "030_outskirts", "040_voi", "050_floodvoi",
          "070_waste", "100_citadel", "110_hc", "120_halo"]

# Both live inside `chapter_start`; `chapter_stop`'s restores are left alone, so the
# HUD can never be stranded off and a stray letterbox can always be cleared.
CHAPTER_START = re.compile(r"\(script\s+static\s+void\s+chapter_start\b", re.I)
HIDE_HUD = re.compile(r"^([ \t]*)(\(chud_cinematic_fade\s+0(?:\.0*)?\s+[0-9.]+\s*\))", re.I)
LETTERBOX_ON = re.compile(r"^([ \t]*)(\(cinematic_show_letterbox\s+(?:1|true|on)\s*\))", re.I)

# Halo 1 proved out this exact pairing on c40: dropping the HUD fade alone keeps the
# HUD but leaves the black bars, and dropping the letterbox with it removes the bars
# while the title still draws. So both go by default here.
PATTERNS = (HIDE_HUD, LETTERBOX_ON)


def transform(data):
    """Comment the HUD hide and the letterbox inside chapter_start, IN PLACE.

    `data` is the raw bytes of the scenario_hs_source_file tag, which stores the script
    text verbatim. The comment is made by overwriting the opening `(` with a `;` rather
    than inserting one, so the tag's byte length never changes and no length field or
    offset inside it has to be understood. `;` comments to end of line in HaloScript, so
    `;chud_cinematic_fade 0 0.5)` is inert.

    Bounded to the chapter_start block: the same two calls appear in `perspective_start`
    and all over the cutscene helpers, where the HUD is meant to go.
    """
    out = bytearray(data)
    k = out.find(b"(script static void chapter_start")
    if k < 0:
        return bytes(out), []
    end = out.find(b"(script ", k + 10)
    if end < 0:
        end = len(out)
    changed = []
    for call in (b"(chud_cinematic_fade 0 0.5)", b"(cinematic_show_letterbox TRUE)"):
        at = out.find(call, k, end)
        if at >= 0:
            out[at:at + 1] = b";"
            changed.append((at, call.decode("latin-1")))
    return bytes(out), changed


# --- the second patch: bring the HUD back EARLY ---------------------------------
# 16 of the 28 title blocks never hide the HUD themselves -- it is already off from a
# cutscene or an insertion transition, and `cinematic_title_to_gameplay` is what
# restores it. But that script restores it LAST:
#
#     (sleep 30) ... gaze/weapons (~12) ... (sleep 110) letterbox off (sleep 15)
#     (chud_cinematic_fade 1 1)        <- ~167 ticks, about 5.5s in
#
# so the title card plays out with no HUD. Moving the fade to the top brings it back
# while the title is still on screen, which is the whole ask.
#
# Done by overwriting the blank line and the "; unlock the players gaze" comment that
# sit between the opening (sleep 30) and the first real call -- 38 bytes of slack,
# enough for the 25-byte call plus a shortened comment. Byte length is unchanged, so
# nothing inside the tag has to be re-lengthed. The ORIGINAL late fade is deliberately
# left in place: fading an already-visible HUD in is a no-op, and keeping it means the
# restore still happens even if this early one is ever removed.
TITLE_TO_GAMEPLAY = b"(script static void cinematic_title_to_gameplay"
EARLY_ANCHOR = (b"\r\n\t\t\r\n\t\t; unlock the players gaze \r\n\t\t")
EARLY_CALL = b"(chud_cinematic_fade 1 1)"


def _early_replacement():
    """The anchor's bytes rewritten to run the fade first, at IDENTICAL length.

    The anchor is 38 bytes: CRLF + tabs + the blank line + "; unlock the players gaze "
    + CRLF + tabs. The replacement keeps the same opening and closing CRLF+tabs so the
    following call still starts on its own indented line, and pads the fade's line with
    spaces to make up the difference. Asserts the length rather than trusting it -- a
    tag whose length shifted would corrupt everything after this point.
    """
    head = tail = bytes([13, 10, 9, 9])   # CRLF + two tabs
    pad = len(EARLY_ANCHOR) - len(head) - len(EARLY_CALL) - len(tail)
    if pad < 0:
        return None
    rep = head + EARLY_CALL + b" " * pad + tail
    assert len(rep) == len(EARLY_ANCHOR), (len(rep), len(EARLY_ANCHOR))
    return rep


def transform_early(data):
    """Insert the early HUD fade into cinematic_title_to_gameplay, in place."""
    out = bytearray(data)
    k = out.find(TITLE_TO_GAMEPLAY)
    if k < 0:
        return bytes(out), []
    end = out.find(b"(script ", k + 10)
    if end < 0:
        end = len(out)
    # NOT a check for EARLY_CALL: the script's own LATE fade is the same call text, so
    # that guard matched on a pristine tag and skipped the patch every time. The anchor
    # disappearing is the real "already done" signal.
    at = out.find(EARLY_ANCHOR, k, end)
    rep = _early_replacement()
    if at < 0 or rep is None:
        return bytes(out), []
    out[at:at + len(EARLY_ANCHOR)] = rep
    return bytes(out), [(at, "early HUD fade in cinematic_title_to_gameplay")]


# --- the third patch: drop the black bars early too -----------------------------
# With the fade moved to the top the HUD comes back at once, but the LETTERBOX still
# does not: `cinematic_title_to_gameplay` waits `(sleep 110)` before
# `(cinematic_show_letterbox FALSE)`, so the bars sit there for ~3.7s more. Shrinking
# that one sleep pulls the bars off with the HUD. Same-length edit: "(sleep 110)" is
# 11 bytes and "(sleep 1)" plus two spaces is 11 too, so nothing shifts.
#
# Only the sleep that GATES the letterbox removal is touched -- it occurs exactly once
# in this script -- and the (sleep 15) after it is left, so the tail keeps its pacing.
SLEEP_BEFORE_LETTERBOX = b"(sleep 110)"
SLEEP_REPLACEMENT = b"(sleep 1)  "


def transform_bars(data):
    """Pull the letterbox removal forward inside cinematic_title_to_gameplay."""
    out = bytearray(data)
    k = out.find(TITLE_TO_GAMEPLAY)
    if k < 0:
        return bytes(out), []
    end = out.find(b"(script ", k + 10)
    if end < 0:
        end = len(out)
    at = out.find(SLEEP_BEFORE_LETTERBOX, k, end)
    if at < 0:
        return bytes(out), []
    assert len(SLEEP_REPLACEMENT) == len(SLEEP_BEFORE_LETTERBOX)
    out[at:at + len(SLEEP_BEFORE_LETTERBOX)] = SLEEP_REPLACEMENT
    return bytes(out), [(at, "letterbox removed early (sleep 110 -> 1)")]


def status():
    """Is the edit in the TAG, and did each build actually compile it?

    The second half is the part that matters and the part that was missing: tool.exe
    dumps the scripts it really used into H3EK\\reports\\<level>\\global_scripts.hsc, so
    that dump is proof rather than inference. Two builds were interpreted as failures
    before anyone looked at it.
    """
    import datetime

    def when(p):
        return datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime('%Y-%m-%d %H:%M')

    if not os.path.exists(GLOBALS_TAG):
        print("script tag not found: %s" % GLOBALS_TAG)
        return 1
    with open(GLOBALS_TAG, "rb") as f:
        _tag = f.read()
    marked = MARK_TAG in _tag
    _k = _tag.find(TITLE_TO_GAMEPLAY)
    _blk = _tag[_k:_k + 2000] if _k >= 0 else b""
    # The early fade must be near the TOP of the block -- the script's own late fade is
    # the same text, so a whole-block search would always say "patched".
    early = EARLY_CALL in _blk[:200]
    # The bars patch is the ABSENCE of the long sleep that gated the letterbox removal.
    bars = bool(_blk) and SLEEP_BEFORE_LETTERBOX not in _blk
    print("global_scripts TAG : chapter_start %s | early-HUD %s | early-bars %s  (%s)"
          % ("MARKED" if marked else "vanilla",
             "MARKED" if early else "vanilla",
             "MARKED" if bars else "vanilla", when(GLOBALS_TAG)))
    if os.path.exists(GLOBALS):
        with open(GLOBALS, "rb") as f:
            hsc_marked = b";[keep-hud]" in f.read()
        print("global_scripts.hsc : %s  <- NOT compiled; the tag above is"
              % ("marked" if hsc_marked else "vanilla"))
    print()
    print("%-16s %-17s %-12s %s" % ("level", "map built", "compiled?", "verdict"))
    for lvl in LEVELS:
        mp = os.path.join(DEPLOYED, lvl + ".map")
        rep = os.path.join(REPORTS, lvl, "global_scripts.hsc")
        compiled = "-"
        if os.path.exists(rep):
            with open(rep, "rb") as f:
                compiled = "EDIT" if MARK_TAG in f.read() else "vanilla"
        if not os.path.exists(mp):
            print("%-16s %-17s %-12s %s" % (lvl, "-", compiled, "no deployed map"))
            continue
        if not marked:
            verdict = "tag is vanilla"
        elif compiled == "vanilla":
            verdict = "REBUILD NEEDED (last build used vanilla scripts)"
        elif compiled == "EDIT" and os.path.getmtime(mp) >= os.path.getmtime(rep):
            verdict = "edit is in the deployed map"
        else:
            verdict = "REBUILD NEEDED"
        print("%-16s %-17s %-12s %s" % (lvl, when(mp), compiled, verdict))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--revert", action="store_true")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(GLOBALS_TAG):
        print("script tag not found: %s" % GLOBALS_TAG)
        return 1
    if a.status:
        return status()

    bak = GLOBALS_TAG + BAK_SUFFIX
    if a.revert:
        if not os.path.exists(bak):
            print("no backup to restore")
            return 1
        with open(bak, "rb") as f:
            data = f.read()
        with open(GLOBALS_TAG, "wb") as f:
            f.write(data)
        os.remove(bak)
        print("restored the global_scripts tag")
        return 0

    src = bak if os.path.exists(bak) else GLOBALS_TAG
    with open(src, "rb") as f:
        original = f.read()
    new, changed = transform(original)
    new, changed2 = transform_early(new)
    new, changed3 = transform_bars(new)
    changed = changed + changed2 + changed3
    if not changed:
        print("nothing to change (already patched, or the anchors moved)")
        return 0
    for at, call in changed:
        print("  tag offset 0x%X: %s -> ;%s" % (at, call, call[1:]))
    print("\n%d call(s) -- covers every chapter title in all 9 campaign levels"
          % len(changed))
    print("byte length unchanged: %s" % (len(new) == len(original)))
    if a.apply:
        if not os.path.exists(bak):
            with open(bak, "wb") as f:
                f.write(original)
        with open(GLOBALS_TAG, "wb") as f:
            f.write(new)
        print("applied to the TAG; backup is %s" % os.path.basename(bak))
        print("rebuild each level, then check --status: the 'compiled?' column reads "
              "the dump tool.exe leaves in H3EK\\reports\\<level>\\ and is the only "
              "real proof the edit was used.")
    else:
        print("dry run - nothing written. Pass --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
