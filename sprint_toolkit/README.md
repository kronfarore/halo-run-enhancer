# Sprint Toolkit (Halo 1) — **experimental**

A complementary, self-contained toolchain that adds a **sprint** ability to the
Halo: Combat Evolved campaign, plus optionally every weapon/equipment, and builds
the resulting maps — **no Guerilla, no manual tag editing**. It drives the HCEEK
`tool.exe` build and patches the loose scenario tags directly in Python.

> Status: **experimental / for tinkerers.** This produces modded `.map` files you
> deploy yourself. It is not a packaged, shippable mod — that's shelved until all
> maps are play-tested with all weapons. Use at your own risk; keep backups.

## How sprint works (the trick)

There is no Halo-script call that sets player speed, so speed comes from tag data:
the global run speed is raised to the *sprint* speed, and every real weapon carries
a movement penalty that scales you back to normal. Holding an invisible, penalty-free
**sprint weapon** = sprinting. A small script (`sprint.hsc`, compiled into every
level via `global_scripts.hsc`) watches the **flashlight** key and swaps you to that
weapon; it's a real toggle with duration + cooldown, and works in co-op. Speed,
duration, cooldown, and on/off are all tunable **after** the build, by byte-patching
the built map (`sprint_tune.py`, or the Enhancer's "Apply Sprint to maps" button).

## Prerequisites

- **HCEEK** — the Halo CE MCC Editing Kit (has `tool.exe`, `tags\`, `data\`,
  `maps\`). Its `Assembly\...\Plugins` folder supplies the tag definitions.
- **Halo: MCC** installed (to play the built maps).
- Python 3.8+. (Reuses `halo_patch.py` / `halo_map.py` from the parent Enhancer repo.)

## One-time setup

1. **Edit `paths.py`** — set `HCEEK`, `MCC`, and `PLUGINS` for your machine.
2. **Install the sprint weapon tag:** copy `assets/sprint.weapon` to
   `HCEEK\tags\weapons\sprint\sprint.weapon`.
3. **Install the sprint script:** *automatic.* Every build (`sprint_build.py` /
   `batch_build.py`) syncs `sprint.hsc` into `HCEEK\data\global_scripts.hsc` first,
   wrapped in `;>>> SPRINT TOOLKIT` markers, so the built maps always carry the
   current script and re-running never duplicates it. The first sync backs the file
   up to `global_scripts.hsc.presprint`. To install it by hand without building, run
   `python install_script.py`. It compiles into every level and stays inert until a
   map is tuned to enable it.

   > If you followed an older version of this README and pasted `sprint.hsc` into
   > `global_scripts.hsc` by hand, delete that block once — the installer refuses to
   > run while an unmarked copy is present, so it can't create a duplicate.

## Usage

Build + deploy + tune **one map** (for testing):

```
python sprint_build.py b30                                   # sprint only, remastered
python sprint_build.py b40 --graphics classic --weapons all --equipment all
python sprint_build.py d40 --weapons alien --equipment all   # remastered, alien weapons
```

Build **all 10 campaign maps**, both versions, into `out\<version>\`:

```
python batch_build.py                    # both versions, all maps
python batch_build.py --version classic_all
python batch_build.py --maps b30,b40 --speed 160
```

Re-tune an already-built/deployed map without rebuilding:

```
python sprint_tune.py <map.map> --mult 1.5 --enable      # speed 150%, sprint on
python sprint_tune.py <map.map> --duration 75 --cooldown 45   # in ticks (30/sec)
python sprint_tune.py <map.map> --restore                # undo (from the .bak baseline)
```

Inspect a scenario's tag layout (debug): `python h1_loosetag.py show <map>`.

## The two versions (an H1 graphics constraint)

Adding a **human** weapon to a map forces a **classic**-graphics build (a remastered
map crashes when you equip a human weapon). So there are two sets, both built
**self-contained** (`--resources none`, which also avoids a shared-`bitmaps.map`
mismatch that corrupts graphics):

- **`classic_all`** — every weapon + equipment, **classic** graphics.
- **`remastered_alien`** — Covenant weapons + equipment, **remastered** (renders
  correctly in *both* in-game graphics views).

Only weapons the player can normally use are added (the Enhancer's H1 pool).

## Files

| File | What it does |
|---|---|
| `paths.py` | Your install paths — **edit this**. |
| `h1_loosetag.py` | Depth-first H1 loose-tag walker + inserter (sprint profile, palette weapons/equipment). The core. |
| `sprint_build.py` | One map: insert → build → deploy to `halo1\maps` → tune. |
| `batch_build.py` | All 10 maps × both versions → `out\`. |
| `sprint_tune.py` | Byte-patch speed / duration / cooldown / enable on a built map. |
| `sprint.hsc` | The sprint script (append to `global_scripts.hsc`). |
| `assets/sprint.weapon` | The invisible sprint weapon tag. |

## Caveats

- Deploy overwrites `halo1\maps\<map>.map` (a one-time `.presprint.bak` is kept).
- Modified maps need MCC's anti-cheat **off** (play offline / campaign).
- Self-contained maps are large (~40–275 MB each). Both full versions ≈ 4 GB.
- Every built map must be **tuned with `--enable`** before it will sprint.

## Credits

Inspired by **Sprint Evolved** (`https://steamcommunity.com/sharedfiles/filedetails/?id=3594880812`) — this Halo 1 mod
first demonstrated sprint is achievable in H1 purely from tag data to me: an
invisible weapon plus per-weapon movement penalties, driven by a flashlight-key
script. This toolkit re-derives that technique independently, with its own assets
and scripts (no files taken from the mod), and adds a tunable duration/cooldown
model and a self-sufficient Python build pipeline. Full credit to Sprint Evolved's
author for the original idea that made this possible.

