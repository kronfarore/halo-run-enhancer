r"""Build a Halo 3 map and REFUSE to believe it worked unless it says so.

`tool build-cache-file` exits 0 when it crashes. A run that dies in globals
postprocessing after twenty seconds and a run that writes a 549 MB cache file both come
back with status 0, and if the output is piped through `tail` the only difference is a
few lines of crash dump that look much like the warnings a healthy build also prints.

Two rebuilds were deployed and tested from a map that had never been rebuilt, because
the installer happily copied the previous one and every check it ran -- the port is
present, the clone owns its blocks, the frame counts are right -- was true of the OLD
map. The tell was a timestamp that had not moved.

So success is taken from the build's own words, "successfully built cache file", and
from the cache file's timestamp actually advancing. Anything else is a failure, and the
assertion is printed rather than buried.

    python h3_build_map.py                       # 010_jungle
    python h3_build_map.py --map 020_base
"""
import argparse, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

B = os.sep
EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK')
OK = 'successfully built cache file'


def build(name, log=None):
    # BACKSLASHES. tool derives the report directory from this string, and given forward
    # slashes it fails to open reports\<map>\cache_file_loaded_tags.txt and asserts
    # g_cache_file_loaded_tags_report_file_ready before it has built anything.
    scenario = os.path.join('levels', 'solo', name, name)
    out = os.path.join(EK, 'maps', name + '.map')
    before = os.path.getmtime(out) if os.path.exists(out) else 0
    t0 = time.time()
    # TWO arguments and no more. The usage line advertises optional audio, language and
    # compression arguments, but passing "default" for them kills the build instantly:
    # it asserts g_cache_file_loaded_tags_report_file_ready in globals postprocessing
    # about twenty seconds in, and still exits 0.
    p = subprocess.run([os.path.join(EK, 'tool.exe'), 'build-cache-file', scenario, 'pc'],
                       cwd=EK, capture_output=True, text=True, errors='replace')
    text = (p.stdout or '') + (p.stderr or '')
    if log:
        open(log, 'w', encoding='utf-8').write(text)
    took = time.time() - t0
    after = os.path.getmtime(out) if os.path.exists(out) else 0

    said_ok = OK in text
    moved = after > before
    print('build %s: %.0f s, exit %d, said "%s": %s, cache file rewritten: %s'
          % (name, took, p.returncode, OK, said_ok, moved))
    if said_ok and moved:
        return out

    for line in text.splitlines():
        if ('ASSERTION' in line or '-FATAL-' in line or 'ERROR' in line
                or 'crash:' in line):
            print('   %s' % line.strip())
    raise SystemExit('BUILD FAILED -- do not install this map, it is the previous one')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--map', default='010_jungle')
    ap.add_argument('--log', default=os.path.join(os.environ.get('TEMP', '.'),
                                                  'h3_build.log'))
    a = ap.parse_args()
    out = build(a.map, a.log)
    print('ok -> %s' % out)


if __name__ == '__main__':
    main()
