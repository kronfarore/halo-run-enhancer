r"""Keep the player's HUD up through Halo 2's story beats (the mission title cards).

WHAT THESE BEATS ARE
--------------------
Forty-four `dormant` scripts across the thirteen solo missions look like this:

    (script dormant 05a_title1
        (hud_cinematic_fade 0 0.5)
        (cinematic_show_letterbox TRUE)
        (sleep 30)
        (cinematic_set_title title_2)
        (sleep 150)
        (hud_cinematic_fade 1 0.5)
        (cinematic_show_letterbox FALSE))

You keep control throughout; only the HUD goes away. Real cutscenes are
`(cinematic_start)`/`(cinematic_stop)` and are NOT touched here.

WHAT THIS DOES
--------------
It comments the HIDING calls out, inside these 44 scripts only. The sleeps stay, so
every downstream `wake` and timing is unchanged.

**Only the hiding half.** `(hud_cinematic_fade 1 ...)` and
`(cinematic_show_letterbox FALSE)` are RESTORES and are always left alone. An earlier
version matched the verb by name and took the restores with it; on 08a_deltacliffs,
which opens with a cutscene, that restore was the only thing that ever brought the HUD
back, so the level ended up with no HUD at all. Halo 1's tool never had this bug and
Halo 3's leaves `chapter_stop` alone -- this is Halo 2 catching up.

USAGE
-----
Edits the H2EK SOURCE .hsc files, which is what h2_batch.py compiles from. It does NOT
rebuild or deploy -- see the REBUILD section below.

    python h2_keep_hud.py                            # dry run
    python h2_keep_hud.py --apply                    # mode 'keep-title-nobars'
    python h2_keep_hud.py --apply --mode keep-title  # keep the title card
    python h2_keep_hud.py --revert                   # restore the originals
    python h2_keep_hud.py --status                   # is the edit IN THE BUILT MAP?

MODES
-----
  keep-title          drop only the HUD fade; title and its black bars still play.
  keep-title-nobars   drop the fade and the bars. The title STILL DRAWS without its
                      frame -- confirmed in game on Halo 1's c40. This is the default.
  all                 also drop the title.

Re-running --apply with a different mode always starts from the pristine backup, so
switching modes is safe and never stacks.

REBUILD AND DEPLOY (the part that is easy to forget)
----------------------------------------------------
The scripts are COMPILED INTO the .map, so an edit here does nothing until the level is
rebuilt and redeployed. Per level, e.g. 01b:

    python h2_batch.py --maps 01b                 # builds into H2EK\h2_maps_win64_dx11
    copy the built .map over halo2\h2_maps_win64_dx11    copy it over <level>.map.bak TOO             # see below
    python h2_keep_hud.py --status                # verify before playing

The .bak matters: the Run Enhancer patches FROM `<level>.map.bak`, so if that still
holds a pre-rebuild map the next patch silently restores it and the HUD fix disappears.

This is a ONE-TIME cost per source change, not per play session -- the built map keeps
the edit until you rebuild again.
"""
import argparse
import glob
import os
import re

H2EK = r"C:\Program Files (x86)\Steam\steamapps\common\H2EK"
SOLO = os.path.join(H2EK, "data", "scenarios", "solo")
BAK_SUFFIX = ".keephud.bak"

# CONFIRMED IN GAME (01b, rebuilt 2026-08-19): commenting all three keeps the HUD up
# through the beat. Which ONE of them hides it is still unknown -- all three went at
# once -- so the modes below walk it back a verb at a time.
# Halo 2 writes its booleans both ways (`TRUE` on 05a, `true` on 08a) and the fade
# takes a number, so every pattern accepts both spellings.
OFF = r"(?:0(?:\.0*)?|false|off)"
ON = r"(?:1(?:\.0*)?|true|on)"

# ONLY THE HIDING HALF. Matching `hud_cinematic_fade` by name commented out the
# RESTORE as well -- and on a level that opens with a cutscene (08a_deltacliffs) that
# restore is the only thing that ever brings the HUD back, so the level was left with
# no HUD at all. Halo 1 and Halo 3 never had this bug; this is Halo 2 catching up.
HIDE_HUD = r"\(hud_cinematic_fade\s+" + OFF + r"\s+[0-9.]+\s*\)"
LETTERBOX_ON = r"\(cinematic_show_letterbox\s+" + ON + r"\s*\)"
SET_TITLE = r"\(cinematic_set_title\b[^\n]*"

MODES = {
    # HUD stays up; the title card and its black bars still play.
    'keep-title': (HIDE_HUD,),
    # ...and no black bars either. The title still draws without its frame -- confirmed
    # in game on Halo 1's c40, which is what settled the shape for all three games.
    'keep-title-nobars': (HIDE_HUD, LETTERBOX_ON),
    # Also drop the title itself.
    'all': (HIDE_HUD, LETTERBOX_ON, SET_TITLE),
}
DEFAULT_MODE = 'keep-title-nobars'


def _neuter_re(mode):
    return re.compile(r"^([ \t]*)(" + "|".join(MODES[mode]) + r")",
                      re.M | re.I)


MARK = ";[keep-hud] "


def sources():
    out = []
    for p in glob.glob(os.path.join(SOLO, "*", "scripts", "*.hsc")):
        if p.endswith(".preability") or p.endswith(BAK_SUFFIX):
            continue
        out.append(p)
    return sorted(out)


def script_blocks(text):
    """(name, start, end) for every top-level (script ...) block, by paren balance."""
    out = []
    for m in re.finditer(r"^\(script\b[^\n]*", text, re.M):
        head = m.group(0)
        depth, j = 0, m.start()
        while j < len(text):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        name = (head.split() + ["?", "?", "?"])[2].strip("()")
        out.append((name, m.start(), j + 1))
    return out


def transform(text, mode=DEFAULT_MODE):
    """Comment out the chosen calls inside every script block that uses the fade.

    Scoped to those blocks so a real cutscene's letterbox and title are untouched;
    all 44 blocks that call `hud_cinematic_fade` also call the other two.
    """
    neuter = _neuter_re(mode)
    changed = []
    pieces, last = [], 0
    for name, a, b in script_blocks(text):
        body = text[a:b]
        if "hud_cinematic_fade" not in body:
            continue
        new_body, n = neuter.subn(lambda m: m.group(1) + MARK + m.group(2), body)
        if n:
            pieces.append(text[last:a])
            pieces.append(new_body)
            last = b
            changed.append((name, n))
    pieces.append(text[last:])
    return "".join(pieces), changed


DEPLOYED = (r"C:\Program Files (x86)\Steam\steamapps\common"
            r"\Halo The Master Chief Collection\halo2\h2_maps_win64_dx11")

# h2_batch.py builds the thirteen MISSIONS. 00a_introduction (the opening cinematic)
# and 01a_tutorial (the armory walkthrough) are not missions, are not in halo.json, and
# are never rebuilt -- so their deployed maps are always older than any source edit.
# Reporting "rebuild needed" for them is a false alarm that costs a play session to
# chase, so they are named as skipped instead.
NOT_BUILT = ('00a_introduction', '01a_tutorial')


def status():
    """Per level: is the edit in the source, and was the deployed map built after it?

    The question that actually matters when a change "does not work" is whether the
    change reached the game at all. Comparing the deployed .map's mtime against the
    source .hsc's answers it without another play session.
    """
    import datetime

    def when(p):
        return datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime('%Y-%m-%d %H:%M')

    print("%-22s %-8s %-17s %-17s %s"
          % ("level", "marked", "source edited", "map built", "verdict"))
    for p in sources():
        lvl = os.path.basename(os.path.dirname(os.path.dirname(p)))
        with open(p, "r", encoding="latin-1") as f:
            text = f.read()
        marked = MARK in text
        # One row per LEVEL, not per .hsc: only the mission script carries these beats,
        # and listing the cinematics/prediction/boss files beside it buried the answer.
        if not marked and "hud_cinematic_fade" not in text:
            continue
        # the deployed map for this level
        mp = os.path.join(DEPLOYED, lvl + ".map")
        if not os.path.exists(mp):
            print("%-22s %-8s %-17s %-17s %s"
                  % (lvl, "yes" if marked else "no", when(p), "-", "no deployed map"))
            continue
        s_t, m_t = os.path.getmtime(p), os.path.getmtime(mp)
        if lvl in NOT_BUILT:
            verdict = "not a mission \u2014 never rebuilt, edit stays on the shelf"
        elif not marked:
            verdict = "source is VANILLA — nothing to see in game"
        elif m_t >= s_t:
            verdict = "edit is in the deployed map"
        else:
            verdict = "MAP IS OLDER THAN THE EDIT — rebuild needed"
        print("%-22s %-8s %-17s %-17s %s"
              % (lvl, "yes" if marked else "no", when(p), when(mp), verdict))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="rewrite the sources")
    ap.add_argument("--revert", action="store_true", help="restore the originals")
    ap.add_argument("--status", action="store_true",
                    help="report whether the edit is in the source AND in the built map")
    ap.add_argument("--mode", choices=sorted(MODES), default=DEFAULT_MODE,
                    help="which calls to comment out (default: %s)" % DEFAULT_MODE)
    a = ap.parse_args()

    if a.status:
        return status()

    if not os.path.isdir(SOLO):
        print("H2EK solo scenarios not found: %s" % SOLO)
        return 1

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

    print("mode: %s - commenting out %s" % (a.mode, ", ".join(MODES[a.mode])))

    files = calls = scripts = 0
    for p in sources():
        bak = p + BAK_SUFFIX
        # Always transform the ORIGINAL, so re-running never stacks edits.
        src = bak if os.path.exists(bak) else p
        with open(src, "r", encoding="latin-1") as f:
            original = f.read()
        new, changed = transform(original, a.mode)
        if not changed:
            continue
        files += 1
        scripts += len(changed)
        calls += sum(n for _nm, n in changed)
        print("  %-52s %2d script(s), %2d call(s): %s"
              % (os.path.relpath(p, SOLO), len(changed), sum(n for _n, n in changed),
                 ", ".join(nm for nm, _n in changed[:4])
                 + (" \u2026" if len(changed) > 4 else "")))
        if a.apply:
            if not os.path.exists(bak):
                with open(bak, "w", encoding="latin-1") as f:
                    f.write(original)
            with open(p, "w", encoding="latin-1") as f:
                f.write(new)

    print("\n%d call(s) in %d script(s) across %d file(s)" % (calls, scripts, files))
    if a.apply:
        print("rewritten from the originals. Backups are *%s.\n"
              "Rebuild with h2_batch.py when the deployed maps are free to be replaced."
              % BAK_SUFFIX)
    else:
        print("dry run \u2014 nothing written. Pass --apply to rewrite the sources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
