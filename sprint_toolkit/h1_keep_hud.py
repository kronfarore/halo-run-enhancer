r"""Keep the player's HUD up through Halo 1's story beats (the chapter title cards).

THE PATTERN
-----------
Halo 1 has an explicit HUD toggle -- `(show_hud 0|1)` -- where Halo 2 had the opaque
`hud_cinematic_fade`. The title card is the same seven lines either way:

    (script dormant title_training
        (cinematic_show_letterbox 1)
        (show_hud 0)
        (sleep 30)
        (cinematic_set_title training)
        (sleep 150)
        (show_hud 1)
        (cinematic_show_letterbox 0))

You keep control throughout; only the HUD goes. 28 such beats across the campaign.

WHY THIS IS SCOPED BY LINE, NOT BY SCRIPT BLOCK
-----------------------------------------------
The Halo 2 tool could work a whole `(script dormant ...)` block at a time because every
beat had its own script. Halo 1 does not: `mission_a30` and `mission_shaftA` are huge
mission scripts with a title card sitting inline among hundreds of other lines, and
those same scripts legitimately hide the HUD elsewhere. Neutering a whole block there
would take out HUD calls that have nothing to do with a title.

So this targets `(show_hud 0)` calls NEAR a `(cinematic_set_title ...)` -- within
WINDOW lines -- and only while not inside a real cutscene. "Inside a cutscene" is
tracked properly, by walking `cinematic_start` / `cinematic_stop` in text order rather
than asking whether the enclosing block mentions them anywhere: 9 title cards live
inside genuine cutscenes, where the HUD is supposed to be gone.

WHY ONLY THE `0` CALL
---------------------
Only the HIDING call is commented out; `(show_hud 1)` is left alone. Removing a restore
can strand the HUD off if it was already hidden on entry, while leaving one is harmless
because turning an already-visible HUD on does nothing. This is a strictly safer shape
than the Halo 2 tool's, which removes both halves of the pair.

Halo 2's answer was that the HUD verb alone is enough -- `--mode keep-title` there
leaves the letterbox and the title intact and works -- so `keep-title` is the default
here too.

    python h1_keep_hud.py                     # dry run
    python h1_keep_hud.py --apply             # rewrite (originals kept as *.keephud.bak)
    python h1_keep_hud.py --revert            # restore the originals
    python h1_keep_hud.py --status            # is the edit in the source AND in the map?
    python h1_keep_hud.py --apply --mode all  # also drop the bars and the title

REBUILD AND DEPLOY
------------------
Scripts are compiled into the .map, so an edit here does nothing until the level is
rebuilt. Per map, from the HCEEK folder:

    tool.exe build-cache-file levels\<map>\<map> remastered <resources> 1

`sprint_build.py <map> --build-only` already wraps exactly that and is the easier route.
Then copy `HCEEK\maps\<map>.map` into `halo1\maps\`, refresh `<map>.map.bak` (the Run
Enhancer patches FROM that baseline and would otherwise restore the pre-rebuild map),
and re-run `--status` before playing.
"""
import argparse
import glob
import os
import re

HCEEK = r"C:\Program Files (x86)\Steam\steamapps\common\HCEEK"
LEVELS_DIR = os.path.join(HCEEK, "data", "levels")
DEPLOYED = (r"C:\Program Files (x86)\Steam\steamapps\common"
            r"\Halo The Master Chief Collection\halo1\maps")
BAK_SUFFIX = ".keephud.bak"
MARK = ";[keep-hud] "

# How far from a title call a (show_hud 0) still counts as part of that beat. The
# shipped pattern puts them 1-3 lines apart; 8 absorbs the variants that add a sleep or
# a sound call without reaching the next unrelated HUD call.
WINDOW = 8

# Halo 1 spells its booleans BOTH ways and the campaign is split almost evenly:
# `show_hud false` 18 / `show_hud 0` 15, `cinematic_show_letterbox true` 19 / `1` 8
# (plus two `on`). Matching only the numeric form found 7 of the sites and silently
# missed the rest -- every c40 chapter title among them, which is what exposed it.
OFF = r"(?:0|false|off)"
ON = r"(?:1|true|on)"

TITLE = re.compile(r"\(cinematic_set_title\b", re.I)
HIDE_HUD = re.compile(r"^([ \t]*)(\(show_hud\s+" + OFF + r"\s*\))", re.I)
LETTERBOX_ON = re.compile(r"^([ \t]*)(\(cinematic_show_letterbox\s+" + ON + r"\s*\))", re.I)
TITLE_LINE = re.compile(r"^([ \t]*)(\(cinematic_set_title\b[^\n]*)$", re.I)
CINE_START = re.compile(r"\(cinematic_start\b", re.I)
CINE_STOP = re.compile(r"\(cinematic_stop\b", re.I)

MODES = {
    # Only the HUD call. Title and letterbox still play.
    # CONFIRMED in game on c40 (2026-08-19): the HUD stays up. The black bars stay too,
    # which is what 'keep-title-nobars' is for.
    'keep-title': (HIDE_HUD,),
    # HUD up and no black bars, title kept. The title is drawn into the letterbox
    # frame, so it may go with the frame -- that is the thing this mode finds out.
    'keep-title-nobars': (HIDE_HUD, LETTERBOX_ON),
    # Drop the bars and the title as well, matching the Halo 2 tool's 'all'.
    'all': (HIDE_HUD, LETTERBOX_ON, TITLE_LINE),
}
DEFAULT_MODE = 'keep-title'


def sources():
    out = []
    for p in glob.glob(os.path.join(LEVELS_DIR, "*", "scripts", "*.hsc")):
        if p.endswith(BAK_SUFFIX):
            continue
        out.append(p)
    return sorted(out)


SCRIPT_HEAD = re.compile(r"^\(script\b", re.I)


def _title_lines(lines):
    """Indices of lines holding a cinematic_set_title that is NOT inside a cutscene.

    Depth is walked in text order but RESET AT EACH `(script ...)` boundary, because
    Halo 1 does not balance the pair within a file: mission_a30.hsc has five
    `cinematic_start` and two `cinematic_stop`, the partners living in other blocks or
    other files. A running whole-file counter therefore never returns to zero and
    silently declares everything after the first cutscene to be inside one -- which hid
    a30's own `reunion` title card from this tool. Within a single block the pair does
    balance, which is the level the question is actually asked at.
    """
    out, depth = [], 0
    for i, ln in enumerate(lines):
        if SCRIPT_HEAD.match(ln):
            depth = 0
        # Bungie commented several beats out rather than deleting them -- all four of
        # a50's titles and d40's chapter_d40_1 (whose show_hud pair is commented too).
        # A dead title must not open a window around live HUD calls next to it.
        if ln.lstrip().startswith(";"):
            continue
        if CINE_START.search(ln):
            depth += 1
        if CINE_STOP.search(ln):
            depth = max(0, depth - 1)
        if depth == 0 and TITLE.search(ln):
            out.append(i)
    return out


def transform(text, mode=DEFAULT_MODE):
    """Comment out the chosen calls within WINDOW lines of a standalone title card."""
    lines = text.split("\n")
    titles = _title_lines(lines)
    if not titles:
        return text, []
    near = set()
    for t in titles:
        near.update(range(max(0, t - WINDOW), min(len(lines), t + WINDOW + 1)))
    pats = MODES[mode]
    changed, hits = [], 0
    for i in sorted(near):
        if lines[i].lstrip().startswith(";"):
            continue
        for pat in pats:
            m = pat.match(lines[i])
            if m:
                lines[i] = m.group(1) + MARK + m.group(2)
                hits += 1
                changed.append(i)
                break
    return "\n".join(lines), changed


def _level_of(p):
    return os.path.basename(os.path.dirname(os.path.dirname(p)))


def status():
    import datetime

    def when(p):
        return datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime('%Y-%m-%d %H:%M')

    print("%-8s %-26s %-8s %-17s %-17s %s"
          % ("level", "script", "marked", "source edited", "map built", "verdict"))
    for p in sources():
        with open(p, "r", encoding="latin-1") as f:
            text = f.read()
        marked = MARK in text
        if not marked and not _title_lines(text.split("\n")):
            continue
        lvl = _level_of(p)
        mp = os.path.join(DEPLOYED, lvl + ".map")
        if not os.path.exists(mp):
            print("%-8s %-26s %-8s %-17s %-17s %s"
                  % (lvl, os.path.basename(p), "yes" if marked else "no",
                     when(p), "-", "no deployed map"))
            continue
        if not marked:
            verdict = "source is VANILLA"
        elif os.path.getmtime(mp) >= os.path.getmtime(p):
            verdict = "edit is in the deployed map"
        else:
            verdict = "MAP IS OLDER THAN THE EDIT - rebuild needed"
        print("%-8s %-26s %-8s %-17s %-17s %s"
              % (lvl, os.path.basename(p), "yes" if marked else "no",
                 when(p), when(mp), verdict))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--revert", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--mode", choices=sorted(MODES), default=DEFAULT_MODE)
    a = ap.parse_args()

    if not os.path.isdir(LEVELS_DIR):
        print("HCEEK levels not found: %s" % LEVELS_DIR)
        return 1
    if a.status:
        return status()
    if a.revert:
        n = 0
        for p in sources():
            b = p + BAK_SUFFIX
            if os.path.exists(b):
                with open(b, "rb") as f:
                    data = f.read()
                with open(p, "wb") as f:
                    f.write(data)
                os.remove(b)
                n += 1
        print("restored %d file(s)" % n)
        return 0

    print("mode: %s\n" % a.mode)
    files = hits = 0
    for p in sources():
        bak = p + BAK_SUFFIX
        src = bak if os.path.exists(bak) else p     # always transform the ORIGINAL
        with open(src, "r", encoding="latin-1") as f:
            original = f.read()
        new, changed = transform(original, a.mode)
        if not changed:
            continue
        files += 1
        hits += len(changed)
        print("  %-6s %-28s %d call(s)"
              % (_level_of(p), os.path.basename(p), len(changed)))
        if a.apply:
            if not os.path.exists(bak):
                with open(bak, "w", encoding="latin-1") as f:
                    f.write(original)
            with open(p, "w", encoding="latin-1") as f:
                f.write(new)
    print("\n%d call(s) across %d file(s)" % (hits, files))
    print("rewritten; backups are *%s" % BAK_SUFFIX if a.apply
          else "dry run - nothing written. Pass --apply to rewrite the sources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
