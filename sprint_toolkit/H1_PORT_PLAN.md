# Halo 1: every missing weapon (plan, 2026-10-06)

The user's master list (`tool\Halo Weapons Spreadsheet (CE - Infinite).ods`, Sheet2) marks
25 weapons missing from Halo 1. The aim is to attempt all of them, Halo 1 first. Rules:

- **One weapon per session**, handed over with the prompt at the end of this file.
- **Sequential at the start.** The next weapon starts only when the previous one is DONE
  (definition below). Parallel sessions come later, once phase 0's reservations and
  per-weapon configs make them safe.
- A finding from one port is an OBSERVATION until a second port confirms it
  (memory port-findings-are-observations). Each session writes what it found into PORTING.md.

Done so far: SAW (from Halo 4), Energy Sword, Fuel Rod and Sentinel Beam (restored, the
last a full Halo 3 port). Their recipes are in PORTING.md.

## Phase 0: setup, before the first weapon (one session)

1. **Capacity.** Every port is made resident in all ten maps (palette entry plus one
   resident-only placement; memory h1-weapon-into-map). Measure each map's tag/meta size
   against Halo 1's limits, and the growth per port (the Sentinel Beam's delta from today's
   rebuild is a sample). Decide whether all 25 can be resident everywhere, or whether some
   are only resident where the enhancer can offer them.
2. **Reservations** (a table in this file), so sessions never collide and can later run in
   parallel:
   - pickup message indices in `ui\hud\hud_item_messages`;
   - `hud_msg_icons` sequence;
   - `hud_reticles` sequence;
   - the two-letter cyborg animation label (taught from the closest stock label);
   - the sound folder `sound\weapons\<x>_port`;
   - the catalog name (halo.json's name for the weapon).
3. **Per-weapon configs.** Today the H3-source pipeline keeps each weapon in a WEAPONS dict
   inside five scripts: h1_h3_weapon_model, h1_fp_retarget, h1_pickable_weapons,
   h1_port_sounds and make_port_catalog_h1_restored. Move each weapon into its own file
   (`ports_h1/<weapon>.py` or `.json`) that the scripts load, so sessions stop editing
   shared code.
4. **A generic test-staging tool.** It puts the weapon in the player's hands at the start
   of a chosen test map, plus the enemies that matter for it (h1_enemy_test_map.py
   already swaps the enemies). This replaces the SAW-only saw_scenario.py.
5. **A catalog writer for ports** (the restored entries' writer, generalized), plus the
   Armed-card firing-profile step (PORTING step 11).
6. **Backup:** port_backup.py --game h1 lists each new weapon's folders from its config,
   automatically.

## The order

The pipeline decides the order. Halo 3's first-person arm skeleton IS Halo 1's, so
`h1_fp_retarget.py` brings Halo 3 animations across whole, and Halo 3 also has the
cleanest geometry, bitmap and sound extraction (h3_rm_to_jms, h1_h3_weapon_model,
h1_port_sounds). Every weapon that exists in Halo 3 comes FROM Halo 3, Halo 2's included.
Reach and Halo 4 arms differ: those weapons go the SAW way (the source mesh on a Halo 1
donor's skeleton, the donor's animations retimed) until a session proves a retarget.

Each wave starts with a PILOT: the weapon that exercises the most of the pipeline in its
simplest form, used to fix and generalize the tools before the rest of the wave.

### Wave A: Halo 3 source, retarget pipeline (9)

| # | weapon | new things it tests |
|---|---|---|
| A1 | **SMG** (pilot) | the first plain magazine gun on this pipeline: reload, ammo pickup (step 6), magazine HUD meter |
| A2 | Battle Rifle | burst fire, zoom + scope HUD (memory halo-zoom-ui) |
| A3 | Covenant Carbine | zoom on a Covenant weapon, its own projectile |
| A4 | Beam Rifle | heat + zoom (Sentinel Beam heat lessons, tick-quantised rate) |
| A5 | Brute Spiker | the blades' melee, a slow projectile |
| A6 | Brute Mauler | a pellet spread (the shotgun as yardstick) |
| A7 | Brute Shot | a bouncing grenade projectile + its explosion (step 3: own chain) |
| A8 | Spartan Laser | a charge-up shot (the fuel rod's charge lessons), a beam visual (the Sentinel Beam's contrail lessons) |
| A9 | Gravity Hammer | a melee weapon with energy (the Energy Sword's recipe; aging per swing) |

### Wave B: Reach source, SAW route (7)

The pilot first PROVES the route from Reach (geometry: the Foundry route, memory
reach-port-foundry-render-model; animations: a Halo 1 donor's).

| # | weapon | new things it tests |
|---|---|---|
| B1 | **DMR** (pilot) | the Reach pipeline end to end; scope zoom |
| B2 | Needle Rifle | needles + supercombine (the needler as yardstick) |
| B3 | Plasma Repeater | heat with venting |
| B4 | Grenade Launcher | an arcing grenade; the EMP alt-fire approximated |
| B5 | Concussion Rifle | a splash push projectile |
| B6 | Plasma Launcher | a charge; lock-on approximated (guidance) |
| B7 | Focus Rifle | a beam + zoom (the H4 kit's Focus Rifle and the Sentinel Beam) |

### Wave C: Halo 4 source, the SAW's own route (9)

The SAW proved Halo 4 to Halo 1 (saw_to_jms.py, saw_port_values.py, h1_saw_sounds.py), but
those tools are SAW-hardwired: the pilot generalizes them.

| # | weapon | new things it tests |
|---|---|---|
| C1 | **Storm Rifle** (pilot) | generalizing the SAW tools; heat |
| C2 | Suppressor | an automatic, a fast projectile |
| C3 | Boltshot | a charged secondary shot, approximated |
| C4 | LightRifle | burst + zoom |
| C5 | Scattershot | bouncing pellets |
| C6 | Binary Rifle | a charge + zoom, one-shot balance |
| C7 | Railgun | a charge shot |
| C8 | Sticky Detonator | remote detonation approximated |
| C9 | Incineration Cannon | a cluster explosion |

A mechanic Halo 1 does not have (lock-on, remote detonation, EMP, bouncing projectiles...)
is APPROXIMATED as closely as the engine allows, never skipped (user, 2026-10-07). E.g.
lock-on -> strong projectile guidance/magnetism; remote detonation -> a sticky projectile on
a long fuse or a detonation triggered by a second shot. The session records the
approximation and what it does not reproduce.

## Definition of done, per weapon

All of PORTING.md's "What ported actually means", steps 1-11, plus:

- **step 5b:** the h1_role_compare.py set, with balanced values the user picked;
- **in every map:** palette entry plus resident-only placement in all ten scenarios,
  checked on the BUILT maps;
- **tested in game:** a dry test map first, then enemy behaviour (Armed card);
- **records:** catalog entry plus a hand-off to the enhancer session (cards, skip_cards,
  tag_map); PORTING notes; memory; port_backup --game h1.

The full ten-map rebuild + ship happens at the END of each weapon, on the user's go.

## Hand-off prompt for a weapon session

> Port the <WEAPON> into Halo 1 (H1_PORT_PLAN.md, wave <X>, #<n>). Source: <game>.
> Read sprint_toolkit/H1_PORT_PLAN.md, PORTING.md (Halo 1 sections + steps 0-11) and
> memory h1-pickable-sword-fuelrod / h1-weapon-into-map first. Use the reserved message /
> icon / reticle / label / sound-folder values from the plan's table. Test on a single map
> first (no full rebuild until I say so). When done: catalog entry, enhancer hand-off,
> PORTING notes, memory, backup -- and add what this weapon taught to the plan.
