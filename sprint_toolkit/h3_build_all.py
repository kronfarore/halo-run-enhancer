# -*- coding: utf-8 -*-
"""Build every Halo 3 campaign level and report per level.

Driven from Python rather than a shell loop: the level name has to be interpolated into
a BACKSLASH path (`levels\\solo\\<lvl>\\<lvl>`) and two attempts at doing that in bash
produced the literal string `levels\\solo$l$l`, so all nine "builds" failed instantly
without touching a map. subprocess takes the argument as a list, with no quoting layer
to get wrong.

Serial on purpose: two concurrent tool.exe runs abort with
`ASSERTION FAILED cache_file_builder.cpp #1157 g_cache_file_loaded_tags_report_file_ready`,
which looks like tag corruption and is really just the two of them fighting over the
loaded-tags report.
"""
import os, subprocess, sys, time

H3EK = r"C:\Program Files (x86)\Steam\steamapps\common\H3EK"
GAME = (r"C:\Program Files (x86)\Steam\steamapps\common"
        r"\Halo The Master Chief Collection\halo3\maps")
LEVELS = ["010_jungle", "020_base", "030_outskirts", "040_voi", "050_floodvoi",
          "070_waste", "100_citadel", "110_hc", "120_halo"]
MARK = b";chud_cinematic_fade 0 0.5)"

only = sys.argv[1:] or LEVELS
ok, bad = [], []
for lvl in only:
    scen = os.path.join("levels", "solo", lvl, lvl)
    t0 = time.time()
    r = subprocess.run([os.path.join(H3EK, "tool.exe"), "build-cache-file", scen, "pc"],
                       cwd=H3EK, capture_output=True, text=True, errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    built = os.path.join(H3EK, "maps", lvl + ".map")
    good = "successfully built cache file" in out.lower() and os.path.exists(built)
    # the only real proof the edit was compiled: tool.exe's own dump
    rep = os.path.join(H3EK, "reports", lvl, "global_scripts.hsc")
    compiled = "?"
    if os.path.exists(rep):
        with open(rep, "rb") as f:
            compiled = "EDIT" if MARK in f.read() else "vanilla"
    print("%-16s %-5s %5.0fs  scripts=%-8s %s"
          % (lvl, "OK" if good else "FAIL", time.time() - t0, compiled,
             "" if good else next((l for l in out.splitlines()
                                   if "FATAL" in l), "")[:70]))
    sys.stdout.flush()
    (ok if good else bad).append(lvl)

print("\n%d built, %d failed" % (len(ok), len(bad)))
if bad:
    print("failed:", ", ".join(bad))
