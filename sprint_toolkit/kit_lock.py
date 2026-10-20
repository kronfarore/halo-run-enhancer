r"""ONE lock for the shared Halo 1 kit, so two port sessions can run in parallel (user,
2026-10-12; H1_PORT_PLAN.md "Running two ports in parallel").

Most of a port is the port's OWN files (its config, weapon / sound / data folders) and runs
in parallel freely. These steps touch what every port shares, and take the lock -- built into
the scripts, so a session cannot forget it:

    shared kit tags   h1_pickable_weapons --write (message list, cyborg labels, scenarios,
                      actor variants, effects), h1_hud_sheet.put (icon / reticle sheets + _r)
    kit builds        h1_rebuild_all, h1_port_test_map (temporary scenario edits + tool's ONE
                      temporary cache file), h1_enemy_test_map, h1_size_test_map
    proofs            port_tool_proof, port_sha_snapshot (snapshot / regen / restore)
    shared records    make_port_catalog_h1_ports, ai_firing_profile (writes), port_sounds.py
                      --write (the halo1 FMOD bank)

The lock is a file in the kit (`HCEEK\.port_kit.lock`: owner, what, pid, since). A process
that holds it passes a TOKEN to its children (environment KIT_LOCK_TOKEN), so a locked script
calling another locked script (h1_port_test_map -> h1_rebuild_all) does not wait on itself.
A lock whose process is gone is STALE and taken over. A waiting process says who holds it.

    with kit_lock.held('h1_port_test_map smg a30', owner='smg'): ...
    python kit_lock.py status
    python kit_lock.py run --owner dmr -- python h1_some_tool.py --write    (any command, locked)
    python kit_lock.py release --force                                     (a stuck lock, by hand)

HALO 2 (H2_PORT_PLAN.md, 2026-10-20): the same machinery, a SECOND lock in H2EK
(`H2EK\.port_kit.lock`), chosen with `kit='h2'` (`--kit h2` on the command line). Its token
travels in KIT_LOCK_TOKEN_H2, so an H2 holder's children re-enter the H2 lock only. The SHARED
RECORDS (weapon_ports_catalog.json, ai_firing_profiles.json, port_sounds) are one file for every
game: their writers keep taking the Halo 1 lock (the default), whichever game they write.

    with kit_lock.held('h2_port_test_map assault_rifle 03a', owner='assault_rifle', kit='h2'): ...
    with kit_lock.script('h2_rebuild_all', kit='h2'): ...
    python kit_lock.py --kit h2 status | run --owner X -- <command> | release --force
"""
import contextlib
import ctypes
import datetime
import json
import os
import socket
import subprocess
import sys
import time
import uuid

HCEEK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK')
H2EK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'H2EK')
LOCK = os.path.join(HCEEK, '.port_kit.lock')
ENV = 'KIT_LOCK_TOKEN'
POLL = 2.0
#: kit -> (lock file, token environment variable, the port configs owners are named from)
KITS = {'h1': (LOCK, ENV, 'ports_h1'),
        'h2': (os.path.join(H2EK, '.port_kit.lock'), ENV + '_H2', 'ports_h2')}


def _kit(kit):
    if kit not in KITS:
        raise SystemExit('kit_lock: unknown kit %r (have %s)' % (kit, ', '.join(sorted(KITS))))
    return KITS[kit]


def _alive(pid):
    """Is a process with this pid running (this machine)?"""
    if os.name != 'nt':
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, int(pid))          # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    ok = k.GetExitCodeProcess(h, ctypes.byref(code))
    k.CloseHandle(h)
    return bool(ok) and code.value == 259               # STILL_ACTIVE


def read(kit='h1'):
    try:
        return json.load(open(_kit(kit)[0], encoding='utf-8'))
    except (OSError, ValueError):
        return None


def _stale(info):
    return (info is not None and info.get('host') == socket.gethostname()
            and not _alive(info.get('pid', 0)))


def _try_create(info, kit='h1'):
    try:
        fd = os.open(_kit(kit)[0], os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=1)
    return True


@contextlib.contextmanager
def held(what, owner=None, timeout=3 * 3600, kit='h1'):
    """Hold the kit lock for the block. Re-entrant through the environment token."""
    lock, env, _cfg = _kit(kit)
    mine = os.environ.get(env)
    cur = read(kit)
    if mine and cur and cur.get('token') == mine:        # a parent of ours holds it
        yield cur
        return
    info = {'owner': owner or os.environ.get('PORT_SESSION') or 'pid %d' % os.getpid(),
            'what': what, 'pid': os.getpid(), 'host': socket.gethostname(),
            'since': datetime.datetime.now().isoformat(timespec='seconds'),
            'token': uuid.uuid4().hex}
    t0, told = time.time(), False
    while not _try_create(info, kit):
        cur = read(kit)
        if _stale(cur):
            print('kit lock: taking over a STALE lock (%s: %s, pid %s gone)'
                  % (cur.get('owner'), cur.get('what'), cur.get('pid')), flush=True)
            with contextlib.suppress(OSError):
                os.remove(lock)
            continue
        if not told and cur:
            print('kit lock: WAITING -- held by %s (%s) since %s'
                  % (cur.get('owner'), cur.get('what'), cur.get('since')), flush=True)
            told = True
        if time.time() - t0 > timeout:
            raise SystemExit('kit lock: gave up after %d s -- %s (%s) still holds it; '
                             '`python kit_lock.py status`' % (timeout, cur and cur.get('owner'),
                                                             cur and cur.get('what')))
        time.sleep(POLL)
    if told:
        print('kit lock: acquired after %.0f s' % (time.time() - t0), flush=True)
    os.environ[env] = info['token']
    try:
        yield info
    finally:
        cur = read(kit)
        if cur and cur.get('token') == info['token']:
            with contextlib.suppress(OSError):
                os.remove(lock)
        if os.environ.get(env) == info['token']:
            del os.environ[env]


def main():
    args = sys.argv[1:]
    kit = 'h1'
    if args[:1] == ['--kit']:
        kit, args = args[1], args[2:]
    lock = _kit(kit)[0]
    if not args or args[0] == 'status':
        cur = read(kit)
        if not cur:
            print('kit lock: free')
        else:
            print('kit lock: held by %s (%s) since %s, pid %s%s'
                  % (cur.get('owner'), cur.get('what'), cur.get('since'), cur.get('pid'),
                     ' -- STALE (process gone)' if _stale(cur) else ''))
        return
    if args[0] == 'release':
        cur = read(kit)
        if not cur:
            print('kit lock: free')
        elif '--force' in args or _stale(cur):
            os.remove(lock)
            print('kit lock: released (%s: %s)' % (cur.get('owner'), cur.get('what')))
        else:
            raise SystemExit('kit lock: %s (%s) holds it and is running; --force to break it'
                             % (cur.get('owner'), cur.get('what')))
        return
    if args[0] == 'run':
        owner = None
        rest = args[1:]
        if rest[:1] == ['--owner']:
            owner, rest = rest[1], rest[2:]
        if rest[:1] == ['--']:
            rest = rest[1:]
        if not rest:
            raise SystemExit('kit_lock.py run [--owner X] -- <command ...>')
        with held(' '.join(rest)[:120], owner=owner, kit=kit):
            sys.exit(subprocess.call(rest))
    raise SystemExit(__doc__)


def owner_from_argv(argv=None, kit='h1'):
    """The port a command works on: the first argument naming a ports_h1 (ports_h2 for
    kit='h2') config (`smg`, `--only dmr`, `--port needle_rifle`), else PORT_SESSION, else
    None (-> the pid)."""
    here = os.path.dirname(os.path.abspath(__file__))
    cfg = os.path.join(here, _kit(kit)[2])
    keys = {f[:-3] for f in (os.listdir(cfg) if os.path.isdir(cfg) else ())
            if f.endswith('.py') and not f.startswith('_')}
    for a in (argv if argv is not None else sys.argv[1:]):
        if a in keys:
            return a
    return os.environ.get('PORT_SESSION')


def script(name, argv=None, kit='h1'):
    """`with kit_lock.script('h1_rebuild_all'):` -- a whole script run, owner from argv."""
    argv = sys.argv[1:] if argv is None else argv
    return held(('%s %s' % (name, ' '.join(argv)))[:160], owner=owner_from_argv(argv, kit),
                kit=kit)


if __name__ == '__main__':
    main()
