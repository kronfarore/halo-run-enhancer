# Porting a weapon into another Halo game

The reusable recipe, written from the two ports that are finished: the Halo 4 **SAW**
into **Halo 1** and into **Halo 3**. Tool names still say `saw_` because it was the first
one; they take the weapon as an argument.

Source weapons come from **H4EK** (`F:\SteamLibrary\steamapps\common\H4EK`), which is the
only kit that ships real source tags for every weapon.

---

## Outlined ammo ticks: always the same cause

Recorded here because it has now cost a fix in two games, and the WRONG fix was tried
first in the second one. If spent ticks keep a lit rim that travels with the full/empty
boundary as the magazine drains:

**The threshold channel is a property of the CELL, not of the tick, and it must cover
every pixel.** Halo 1, 2 and 3 all light a meter pixel by comparing a channel of the art
against the ammo level (Halo 1 luminance, Halo 2 and 3 blue), and Bungie's own art carries
that value across the blank gaps too -- `battle_rifle_meter` has ZERO zero-blue pixels.
Paint it only where a tick is opaque and every gap reads 0, which means "still loaded";
the HUD samples filtered, so each tick's rim mixes its own threshold with the 0 beside it
and keeps drawing after the tick has emptied.

Lay the threshold field down FIRST as a continuous staircase over the whole bitmap, then
stamp the tick art over it without touching that channel.

**It is not an alpha problem, so do not hard-edge the art.** That was tried in Halo 2 and
changed nothing, because Bungie's ticks are softly antialiased (alpha 9..137) and always
were. Hard edges only throw the antialiasing away.

---

## What "ported" actually means

A port is not done when it appears in game. Nine things have to be true, and Halo 3
quietly shipped without the last three until the user caught it:

| # | step | H1 | H3 |
|---|------|----|----|
| 1 | geometry: first-person AND world model, on the target's skeleton | done | done |
| 2 | textures / shaders | done | done |
| 3 | its own projectile + damage effect AND the weapon names them (H1: its own melee too) -- `port_refs_audit.py` | done | done |
| 4 | numbers: the source game's values in the tags | done | done |
| 4b | the fields NO card covers: `port_field_audit.py` shows nothing left to port | done | done |
| 5 | balance rows, with per-game field coverage audited | done | done |
| 6 | ammo pickup: which item tops it up (a port has none of its own) | done | n/a |
| 7 | ammo meter / HUD readout sized for the port's magazine | done | done |
| 8 | pickup icon, and the HUD schematic beside the ammo | done | done |
| 9 | reload and swap animation timing | done | done |
| 10 | its OWN SOUNDS: fire, dry fire, reload, swap, melee, idle fidgets (+ first draw) -- see **Step 10** | done | done |
| 11 | ARMED card: enemies can be given the port -- it needs AI firing data (Halo 1 only) -- see **Step 11** | done | no Armed cards yet |

Step 10 was added 2026-10-05 after the SAW had shipped in five games on the donor's
sounds (the H3/ODST/Reach SAW fired through the REAL Assault Rifle's firing effect). It is
done for the SAW in all five games plus the Halo 4 Focus Rifle; the per-game recipe is in
**Step 10, the port's own sounds** below.

**When a port is done -- the closing steps (all games):**
0. `python port_refs_audit.py --game "<game>"` on the REBUILT map: the weapon fires its own
   projectile, names its own damage effects (Halo 1: its own melee too) -- see step 3 below.
1. If the port added a pickup/HUD glyph (Halo 3, ODST, Reach, Halo 4 -- the loose icon
   font packages): `python port_glyphs.py --capture` in the tool folder, then commit
   `port_glyphs.json`. Without it the glyph exists only on this machine, and the
   Enhancer cannot restore it after a Steam update or put it on a co-op partner's
   install. It refuses if any package does not rebuild from the stock backups on E:.
2. `python validate_halo_json.py` -- its GLYPHS section flags a live glyph the json
   lacks (step 1 forgotten) and a glyph the live packages are missing
   (`python port_glyphs.py --check` runs that section alone).
3. If the port added its own sound bank (Halo 4): commit `tool/port_sounds/<game>/*.bnk`;
   `python port_sounds.py --check` confirms it is in the live package.
4. `python port_backup.py --game <g>` -- the port's tags, data, scripts and shared files.
5. If the port has its OWN sound tags (Halo 3, ODST, Reach): the volume knob needs them
   built with the marker -- a NEW port gets its own value in port_volume.py (MARKER_DB +
   PORT_SOUNDS, e.g. 0.02, never one another port uses) and its sounds set to gain -3
   minus it before the build; `python port_volume.py --game "<game>" --map <map>` on the
   rebuilt map must list the entries with no SHARED and headroom 3.
6. Step 4b: `python port_field_audit.py --game <h1|h2|h3|odst|reach>` -- list 2 must say
   "0 to port"; lists 4/5 hold only what was KEPT on purpose (written down in the
   game's writer). Every tag write is proven with `kit_tag_diff.py <kit> snap|diff`.
7. Step 10 checks on the REBUILT map: `python port_sound_refs.py --game "<game>"` -- every
   fire / dry / animation sound names the port's own folder; Halo 3 / ODST / Reach: the
   installed `<game>\fmod\pc\sfx.<suffix>.fsb` equals the kit's and holds every hash the
   map names; Halo 1 / Halo 4: `python port_sounds.py --check`.
8. Step 11 (Halo 1): the port is in `h1_enemy_weapons.used_weapons()` and `best_donor` /
   `donor_for` names a firing donor for a Grunt and an Elite slot -- see **Step 11**.
9. THE HIT-EFFECT RULE (Halo 1, user 2026-10-08, Spike Rifle): the port's SHIELD-HIT effect
   on the player (its projectile's response effect for material #22, cyborg energy shield)
   keeps the donor's per-hit load up to the stock pistol's rate (3.5/s) and above it shrinks
   it by (3.5 / rate)^3.19 (size = the square root) -- `python h1_hit_effect_load.py` lists
   every weapon's scale; the port applies it with `bullet.impact_thin` {'materials': [22],
   'out': <own folder>, 'thin': {}, 'rate': max(default, balanced)}. See "Balance".
10. THE MUZZLE-FLASH RULE (Halo 1, user 2026-10-10, the DMR: 'if muzzle flash isn't part of
   the regular things to replicate, it should finally be'): the port's FIRST-PERSON flash is
   checked against the SOURCE weapon's, before boot 1 -- the template's flash sprites (count,
   radius, direction, offset: its `effe` events / particles) beside the source firing
   effect's first-person particles (Halo 3 / Reach: the particle systems with camera mode
   'first person', their location markers and emitter `bounding radius estimate`). A
   template's flash belongs to the TEMPLATE's muzzle: the DMR on the sniper inherited two
   sideways brake fans of 15-20 sprites up to 0.125 wu where Reach's flash is 0.06-0.11 wu at
   the bore ('too big and wide'). Fix with `sound_effects` `copy_from` a closer Halo 1 flash
   (the DMR: the BR port's pistol sprites + casing) and/or `match` / `drop_off_axis` / `scale`
   / `shift` (the SMG); record the source numbers beside the choice in the config.
   `python h1_effect_particles.py "<port fire effect>" "<template's>"` lists both sides' particles.

**Step 4 has a second half: the fields NO CARD covers (2026-10-05).** The balance table
only knows fields some card targets; every other field of a clone is its donor's. Run
`python port_field_audit.py --game h3|odst|reach|h2|h1` (read-only): per field it compares
the SOURCE pair (H4 SAW vs H4 AR) -- same there = the target donor's value is right;
different + the same numeric field in the target = port it by the ratio rule (writers:
h3_saw_tag_numbers / reach_saw_tag_numbers / saw_port_values EXTRA / h2_saw_numbers);
otherwise an engine difference to decide. Lists 4 and 5 catch a port cloned from ANOTHER
weapon than its yardstick (Halo 2: the GPMG + the Warthog turret's bullet ->
h2_saw_yardstick.py). It reads the CATALOG for what balance covers (derived rows
included). Done for all five SAW ports: nothing left to port.

**STEP 5b, MEASURING THE BALANCED VALUES** (made a heading of its own 2026-10-06 -- the user
could not find it): a balanced value is never a guess. Put the port beside the weapons whose
role it shares and read time to kill on the game's real enemies, then propose rows that move
it INTO that role -- and run the same check on the balanced numbers. Halo 4 / Reach:
`port_role_compare.py` + `port_ttk.py` (below). HALO 1: `h1_role_compare.py <set>
[--balanced]` (role table + time to kill at normal / legendary from HCEEK tags: per-material
damage modifiers, actor-variant vitality, globals difficulty scales). It found, on the
restored fuel rod, that its explosion does x0 to Hunters (Bungie's Grunt friendly-fire
guard) and that 'Charging Time 0' alone leaves it firing 10 rounds/s.

**STEP 11, THE ARMED CARD (Halo 1 only, 2026-10-06).** 'Armed: <weapon>' cards are not in
halo.json: the enhancer SYNTHESIZES them (`armed_card` / `armed_cards`) for every weapon a
player holds, per enemy type (Grunt, Jackal, Elite, Flood combat form, Sentinel; Marines
through the Ally pool; never the Hunter). Each pick moves 10% of that enemy's spawns onto
a variant carrying the weapon -- an existing one, or one of the level's 20 spare enemy
slots, filled with the source variant + the weapon + the FIRING BLOCK of a donor actor
variant (actv 0x74-0x15F, 0x1D8-0x1E3). A port only gets the card while ports are offered
on the level, and only if it is in `h1_enemy_weapons.used_weapons()`: weapons some
character SPAWNS with, plus every weapon with a FIRING PROFILE in
`tool\ai_firing_profiles.json`. Which case a port is:

  carried in game     Halo 1 restorations: the Energy Blade (Elite commander / stealth
                      Elite major) and the Flak Cannon (spec-ops Grunts) -- nothing to do;
                      the donor is the most similar carrier (`best_donor`)
  a foreign source    the SAW: `ai_firing_profile.py --from-map <source game's map>
                      --from-weapon <source tag> --to-weapon <port>` copies the source
                      game's ai\generic firing values (fields matched by NAME), laid over a
                      base donor found by the port's animation LABEL (the SAW is 'ar': an
                      AR carrier)
  a same-game stand-in  the Sentinel Beam: its label 'sb' is unique, so the label search
                      finds no base. `ai_firing_profile.py --to-weapon <port>
                      --donor-weapon <a Halo 1 weapon> [--set 0xOFF=VALUE:NAME ...]`:
                      fire like the characters carrying that weapon (the beam: Halo 1's
                      Sentinel gun, `characters\sentinel\sentinel`) -- `donor_for` reads
                      'donor_weapon'

THE TRAP in a donor's firing block: it carries the donor's OTHER behaviour too. The
Sentinel never drops a weapon (Drop Weapon Loaded +0x1D8/+0x1DC = 0/0), so a beam-armed
Grunt or Elite may have dropped it empty. `--set` writes explicit fields over the donor (the
beam: 0.7 / 0.9, the plasma-rifle Elite's). Read every field the copy carries (the
enhancer session's review found this one). The donor's Weapon Damage Modifier (+0xC4)
rides along too: the beam's 0.0 = Sentinel strength, matching its 4.64 calibration -- a
knob if beam-armed Elites prove too strong. Animation: `ensure_label` teaches the port's
label to each enemy from TEACH_DONORS ('pr' first); a melee-only weapon on a unit with no
melee (Energy Blade on Grunts/Jackals) gets a stand-in swing (enhancer side, 5dc3f23).

Check (closing step 8): the port is in `used_weapons()`, and the donor for a Grunt slot
and an Elite slot is the intended one. BALANCED DROP (2026-10-12, every port): the profile's
`balanced_set` holds Drop Weapon Loaded / Ammo by the ratio rule (see the Plasma Repeater).
THE SPECIES SKILL RULE (2026-10-14, user; C1 Storm Rifle the pilot, then every port; default AND
balanced): `h1_enemy_weapons.species_skill_rule` scales each Armed slot's error, tracking, leading,
surprise delay and first-burst delay (the pair by sums) by the slot's OWN stock variant over the
donor, tracking / leading capped at 1 -- a fixed donor (the Elite minor plasma rifle) had Grunts
aim like Elites, a per-slot similarity donor (a Marine, a Flood Elite) gave each species another
species' skill. Halo 4 (and the other sources' ai\generic) gives no species an own entry. Burst
shape and rate stay the weapon's (+ the Grunt half rate). Stock character: Grunt minor PP vs
Elite minor PR error x2, tracking x0.56, surprise x5; Jackal error x0.33, tracking x0.67. A
profile's `species_skill: False` opts out; `SPECIES_SKILL_HOLD` keeps in-progress ports out
(the Plasma Launcher was held until done; wired in on the user's go, 2026-10-14 -- its spec-ops
Grunt fuel rod donor: the Jackal / Elite slots now carry their own species' skill). Proof of the opt-in pilot: the Plasma Repeater's
Armed b30 build byte-identical. Back up `ai_firing_profiles.json`,
`ai_firing_profile.py` and `h1_enemy_weapons.py` (port_backup h1 carries them).

**And step 5 has a ROLE check (2026-10-05):** `python port_role_compare.py <set>
[--balanced]` puts the port beside the weapons whose role it shares -- damage per shot,
dps, shots/seconds to overheat, overheat recovery, battery, headshots, range, zoom, aim
assist -- built and balanced. Sets live in its SETS table (first: the H4 Focus Rifle
against the Beam Rifle, the Sentinel Beam and the Sniper Rifle bridge).
`python port_ttk.py <set> [--why]` turns that into TIME TO KILL on the game's real enemies:
character vitality (normal/legendary, parent chain), the model's shield/body materials, the
globals damage table (damage group x armor, printed per lookup), overheat pauses, shield
overflow into the body. Body shots only. HEAT DRAINS WHILE FIRING (user, 2026-10-13: Halo 2 /
3 / ODST / Reach / 4; the earlier "cools only while NOT firing -- confirmed" was WRONG, fixed in
a8d79b2). HEAT REVISIT (2026-10-14): the H4 Focus Rifle port = Reach exactly under drain (75
shots / 2.50 s, the user's Reach stopwatch; the old rule said 40 / 1.33 s) -- its tags were
right; its balanced option 2 (Overheated Heat Loss 0.375, recovery 2.4 s) still sits between
the Beam Rifle and the Sentinel Beam on every enemy -- no change. The Halo 1 Plasma Repeater
(B3) WAS refit: Reach full heat 14 rounds draining, not 12 (ea50476).

**Step 3 is TWO things, and the Halo 1 SAW shipped with only one of them** (found
2026-10-02). `saw_port_values.py` wrote the port's own numbers into
`weapons\saw\bullet` (proj + jpt!), but the weapon tag's trigger was a copy of the
Assault Rifle's and still named `weapons\assault rifle\bullet`. So the built SAW fired
the DONOR's bullet, the port's own bullet tags were orphans the cache never compiled,
every SAW projectile/damage balance row pointed at a tag that was not in the map, and
editing the AR's bullet moved the SAW with it. Cloning the tags is not enough: the
trigger has to name them (`saw_weapon.py` does it now). The MELEE had the same gap and
is wired too (2026-10-03): `weapons\saw\melee` holds the port's 70/70/70 where the AR's
stock tag is 40/50/60 -- which is exactly what the balance table brings the port down
to, so sharing the donor's tag shipped the port pre-balanced and left its Melee Damage
card nothing of its own to move. `player_response` stays the donor's: it is the effect
played on whoever is hit and carries no per-weapon damage.
After fixing the wiring the maps that carry the port must be REBUILT; until then the
deployed map still has the old reference.

**Step 3, checked in every game -- what the WEAPON must NAME (audited 2026-10-03):**
cloning the projectile and damage tags is half of step 3; the other half is that the
built weapon REFERENCES the clones. `python port_refs_audit.py` (sprint_toolkit) reads
the DEPLOYED map through the Assembly plugin -- tag edits without a rebuild do not count
-- and lists every projectile and damage effect the port and its projectile name, each
classified OWN / GLOBAL / DONOR'S (how many of the map's weapons and projectiles share
it). All six ports pass (H1/H2/H3/ODST/Reach SAW, H4 Focus Rifle).

| reference | Halo 1 | Halo 2 - Halo 4 |
|---|---|---|
| weapon -> projectile (trigger / barrel `Projectile`) | OWN | OWN |
| projectile -> `Impact Damage` | OWN | OWN |
| weapon -> melee DAMAGE | **OWN** -- every H1 weapon has its own melee damage tag (`weapons\assault rifle\melee`); clone it and point `Player Melee Damage` at the clone | **SHARED GLOBAL** -- `strike_melee` / `smash_melee` (13-38 users per map); keep it, and no catalog row may retune it (Reach dropped its three melee rows for exactly this) |
| weapon -> melee RESPONSE, firing damage (shake/rumble) | donor's is fine: feedback, no per-weapon damage numbers | global, or the port's own |

A DONOR'S damage tag in a damage-bearing field is the Halo 1 bug pattern: the audit
reports it as a PROBLEM and exits 1. Run it after every rebuild of a map that carries a
port (closing steps above).

Step 6 is a **port detail, not a general option**: a port inherits the donor's pickup
item, and the dropdown only re-points it when several weapons share one. Halo 4 has no
ammo pickups at all.

---

## Halo 1

Everything runs through `saw_build.py`, which does the whole thing and always restores
the scenario even when the build fails:

    python saw_build.py [--map a10] --scale 1.0 [--skip-bitmaps] [--no-deploy]

What it chains, and what each piece is for:

1. `tool bitmaps weapons\saw\bitmaps` — TIFs are already in the HCEEK data tree.
   Source pixels come from `h4_bitmap.py`, because **H4EK's own exporters fail**
   ("rasterizer\invalid"); decode the tag directly. The pixel blob follows its u32 size
   (= mip chain + 8) and that value also appears earlier in the chunk header — **take the
   last match**. Plain linear DXT, no byte swap.
2. `saw_shaders.py` — shader_model tags. **A Halo 1 shader needs a multipurpose map** or
   the weapon renders white: R = reflection mask, G = self-illum, B unused, A white. Take
   R from H4's control map.
3. `saw_to_jms.py <rm.xml> <out> [scale]` — H4 render_model to JMS on the **donor's
   skeleton**, so the donor's animations drive it. See *Reading H4 geometry* below.
4. `tool model weapons\saw\fp` and `weapons\saw` — gbxmodels.
5. `make_icon.py` + `add_msg_icon.py` + `saw_weapon.py` — see step 8 below.
   `h1_saw_sounds.py --write` runs BEFORE `saw_anims.py` (**step 10**: its own sounds; the
   animations only name them once the tags exist), and after the deploy
   `..\port_sounds.py --write` puts the audio into the FMOD bank MCC actually plays.
6. `saw_port_values.py --write` — **step 4** (its `EXTRA` list = step 4b, the fields no
   card covers): the port's own Halo 4 numbers into its
   Halo 1 tags, so the map ships the SAW and the patcher applies the balance on top.
   Both halves read the same `balance_SAW_Halo4_to_Halo1.json`, one taking `original`
   and the other `balanced`, so they cannot drift. **Assembly's units are not
   Reclaimer's**: angles are degrees in the table and RADIANS in the tag, velocities
   are units per tick in the table and per SECOND in the tag. The tool proves every
   path and factor against the Assault Rifle before it writes, and refuses if one
   stops reproducing the donor — which is how the velocity factor was caught
   inverted during its reconstruction.
7. `saw_scenario.py --map <map>` — puts the weapon in that map's spawn profiles (the SAW
   only; new ports use `h1_port_test_map.py`, see "the port tooling after phase 0").
   **Only the spawns.** a10 has six profiles and three of them drive mechanisms (the
   sprint mod's invisible weapon, the bridge pistols, a weapon insert); handing one
   the SAW breaks the level. That cannot be read off the tag, so it is recorded per
   map and an unknown map is REFUSED with its profiles printed.
8. `tool build-cache-file levels\<map>\<map> classic none 1` — **must be `classic`**;
   read_write/remastered corrupts, and a human weapon forces classic anyway.
9. `saw_scenario.py --restore` — always.
10. deploy; the original stays as `<map>.map.before_saw`.

**Step 7, the ammo meter.** `ammo_meter.py <N> <tag base>` renders the tick art for any
magazine. The readout is two `weapon_hud_interface` elements on loaded ammo: a STATIC
silhouette sheet and a METER sheet whose **luminance is the tick's threshold** and alpha
is the shape. The engine meter runs **0..255, not the AR art's 0..240** — threshold of
tick k is `step * k` with `step = 255 // N`, which is also the element's
`alpha_multiplier`. Getting that wrong fills two ticks per round and tops out early.

**Step 8, the pickup icon.** The icon is `weapon_hud_interface`
`messaging_information.sequence_index` into the **shared** sheet
`ui\hud\bitmaps\combined\hud_msg_icons`. `make_icon.py` renders one from the weapon's own
JMS in the stock style (outline 235 grey a~230 over fill 79 grey a~59); `add_msg_icon.py`
**appends** a new bitmap and sequence so stock indices are untouched, and is idempotent
from its own backup of the stock tag.

**Step 9, animation timing.** Multipliers are `balanced_frames / BUILT_frames`, not a raw
ratio. `port_anim_measure.py` measures frame counts and reproduces the table, which is
what makes it trustworthy for other games.

### Halo 1: enemy-only weapons made pickable, with HALO 3 first-person animations (2026-10-05)

Halo 1 ships the Elites' Energy Sword and the Grunts' Fuel Rod as enemy-only items: weapon
flag `detonates_when_dropped`, and no first-person model, animations or (fuel rod) HUD.
The user's call: pick up the ORIGINAL weapons, behaviour unchanged, FP animations ported
from Halo 3. Status: tags written and maps BUILD; **not yet seen in game**.

**The finding that makes it cheap: Halo 3's FP arm skeleton IS Halo 1's.**
`objects\characters\masterchief\fp\fp.render_model` (H3EK) and
`characters\cyborg\fp\fp.gbxmodel` (HCEEK) have the same 37 nodes, parents and bind
positions to two decimals (shoulders y +-9.40, elbow x 10.25, wrist 21.14, every knuckle).
`base` = `frame bone24`, `l_hand` = `frame l wriste`, `l_middle_low` = `frame l middlelow`,
the rest by name. Two conventions differ:
* **Quaternions**: Halo 1 tags (and its JMAs) store the INVERSE rotation, Halo 3 the
  rotation. H1 = conjugate(H3). Proven by `fp_render.py`: the H1 AR idle draws right only
  when its tag quaternions are conjugated.
* **Camera**: H3 animates `camera_control` and offsets `base` against it; Halo 1's camera
  is the animation origin. Every frame is re-expressed in camera_control's frame.
Halo 3 omits nodes at bind from an animation (the sword idle stores 5 of 40
translations) -- those come from the H3 render models' default transforms.

**Tools** (sprint_toolkit):
* `h3_fp_pose.py` -- full per-node poses from an H3 kit jmad (static default_data +
  animated tracks + node masks; builds on h3_anim_decode).
* `h1_fp_retarget.py <weapon> --list | --preview <anim> | --write` -- H3 -> H1 JMAs into
  `HCEEK\data\<weapon>\fp\animations`, then `tool animations "<weapon>\fp"`. Solved in world
  space; weapon nodes get a bind correction: `same_space` (sword: H1 and H3 models share a
  model space, only the `blades` pivot differs) or `node` (fuel rod: grip node to grip node).
* `fp_render.py` -- offline FP view (H1 hands + weapon, any frame of any H1 antr). Check
  every retarget with it before a build.
* `h1_scaled_model.py` -- a scaled gbxmodel copy (the fuel rod's FP model: its own world
  mesh x0.75 -- 0.57 long is alien-sized; H3's FP fuel rod is 0.43, H1's PC one 0.41).
* `h1_pickable_weapons.py --write` -- the kit tag edits (below). Rerun after every
  `tool animations`: recompiling resets the key frames and sounds it sets.

**JMA facts, from an exact roundtrip** (Oddball FP antr -> Reclaimer JMAs -> HCEEK tool
-> identical to 0.00003): JMA quaternions are the tag's; a BASE animation's JMA has one
frame more than the tag (the tool drops the last -- append frame 0 to a loop, repeat the
last frame of a one-shot); an OVERLAY's JMO has a reference frame first, and only its
ANIMATED tracks are deltas. Node order = depth, then name (the tool's own).

**What h1_pickable_weapons.py writes** (stock tags kept as `<tag>.before_pickable`):
sword -- flag cleared, FP model = its own world model, FP animations, no HUD/trigger
(the oddball's setup), melee key 5 + the Elite's sword-swing sound. Fuel rod -- flag
cleared, scaled FP model, FP animations from H3's flak_cannon (fire, both reloads), own
melee (`weapons\fuel rod gun\melee`, the PC fuel rod's), HUD = the PC fuel rod's with
the AR's magazine readout (`master rounds` child, 4-tick meter), keeps 4 rounds / 1.25 s
charge / rod projectile. Player biped `characters\cyborg\cyborg` taught `fr` (from `pc`)
and `fb` (from `b`) -- 15 weapon types.

**First dry test (a50, 2026-10-05):** both stay on the ground, FP models render, idle /
ready / melee right. Found: the fuel rod Grunts drop it EMPTY (actv drop_weapon_loaded and
drop_weapon_ammo 0..0 -- now 0.5-1.0 / 2-6); left hand clipped the fuel rod (now a 2-bone
IK offset in gun space, `left_hand_offset`); MCC has no localized line for message 8
("need string insert here": the sword now has its own appended pair, 49/50); icons too
small or missing (own icons from the models, 27/28 -- `add_msg_icon.py` now edits the
CURRENT sheet: it used to rebuild from stock and would have dropped the SAW's). Fuel rod HUD
is now the rocket launcher's, its two rockets redrawn as four (`h1_rocket_meter.py`).
Sword: plasma pistol HUD (crosshair + battery = energy) and an EXPERIMENTAL lunge on fire --
an invisible 1.5 wu strike with the sword's melee damage plus a firing damage with
instantaneous acceleration 3.0 on the wielder (direction not yet seen), 0.1 energy each.

**Second dry test (a50, 2026-10-06), and what changed:** the shove did nothing (strike hit)
-- its damage effect was the plasma pistol trigger's, 0 damage with every material
modifier 0; now 0.01 damage, modifiers 1. Both weapons carry Halo 3's aim assist (sword
autoaim 10 deg / 2.5 wu, magnetism 10 deg / 6 wu; fuel rod 4 / 25, 6 / 25) -- the AI-only
tags had none. The fuel rod fired with `rounds_per_shot 0` (never spent a round, never
reloaded): now 1; Grunts have NO fuel rod reload animation, so watch them. Fuel rod HUD =
the PC fuel rod's (its crosshair, the user's pick) + Halo 3's rod meter (ballistic_meters
#17, four rods, `h1_rocket_meter.py ... h3_rods`); sword reticle = Halo 3's
(hud_reticles #13, `h1_add_reticle.py`, scale x123/97 from the two fuel rod reticles).
H3 HUD sheets are read with `h3_hud_art.py` (largest tgda chunk; H3EK's exporter fails).
A PLACED weapon's ammo is the scenario placement's own Rounds Left/Loaded: 0/0 spawns it
empty (Bungie's placements all carry counts; a50's test row is 0/0).
The fuel rod's hold-to-fire is the stock AI trigger (1.25 s charge, discharge).

**Third round (2026-10-06):** EVERY Halo 1 HUD sheet a port writes has a 32-bit `_r` twin
(`hud_msg_icons_r`, `hud_reticles_r`; both compiled into each map, both shipped loose by
MCC) and a weapon HUD's sequence index must exist in BOTH -- the sword reticle written to
`hud_reticles` only drew as a BLUE SQUARE in game. `h1_hud_sheet.put_twins` writes both at
one index (pads with empty sequences); `add_msg_icon.py` and `h1_add_reticle.py` use it,
and the SAW's icon now has its `_r` twin too (#25). Lunge shove: positive acceleration
pushes the player BACK, negative forward; too much hurts (-2.0 now). Fuel rod charge: the
plasma pistol's charging loop as an attachment scaled by `primary_charged` -- Halo 1 has
no FP slot that plays during a charge. Rod meter in one row (`h3_rods_row`).

**Fourth round (2026-10-06), own sounds:** the sword cued the Elite's third-person swing,
silent for its first 0.45 s (timed to the Elite's wind-up), so the first-person slash and
lunge sounded 0.3 s late. `h1_port_sounds.py <weapon>` is the GENERIC Halo 1 own-sounds
tool (the SAW's h1_saw_sounds.py stays SAW-only): Halo 3 audio straight from MCC's
`halo3\fmod\pc\sfx.fsb` (its `.info` names every subsong's source file; vgmstream
decodes), several H3 sounds MIXED where H3 cues them on one frame (lunge = hum + cloth),
22 kHz mono at the stock level, stock-shaped ADPCM tags under `sound\weapons\<x>_port`,
and only its OWN files + manifest in port_sounds\halo1 (h1_saw_sounds' bank step wipes that
folder -- run port_sounds.py --write after either). Sword: melee, lunge, ready (ignition),
posing. Balanced build note (user): a small radius on the lunge strike's damage.

**Fifth round (2026-10-06): sounds complete, step 3, backups.** Fuel rod: Halo 3's own
fuel rod sounds (flak_cannon ready / reload / posing / melee / fire foley, all cued at frame
0 as Halo 3 does). Sword: Halo 3's IGNITION is not an animation cue -- the weapon's
blade_activate effect plays sword_ready with a 0.6 s DELAY, so the H1 ready cues it at
frame 18 (antr sound frame index); hit = the melee damage effect's sound (slash and lunge);
hum = a sound_looping (the plasma rifle charge loop's shape) attached unscaled at `flare`,
class weapon_idle. STEP 3 applied to a restored weapon: the Grunts' fuel rod fired the
HUNTERS' projectile + explosion, which the enhancer's Hunter cards tune -- it now owns a
same-valued chain (`grunt fuel rod` proj -> `effects\grunt explosion` -> `grunt explosion`
jpt), verified separate in the built map. `port_backup.py --game h1` now carries the restored
weapons' folders, sounds, every shared tag edited in place + its .before_pickable copy.
Manual steps that do NOT apply to a restored weapon: 1/2 (own geometry, original), 4/4b
(original numbers), 6 (no ammo item exists), glyphs (H1 has none). Still open: step 5 --
enhancer cards / pools / starting picks for both (enhancer side), and the per-weapon
balanced switch.

**Open for the first boot**: does the dropped sword/fuel rod stay; the FP pose and grip
(left hand vs the H1 fuel rod's front -- H3's hand is 13 cm ahead of the grip, the scaled
model's own `cyborg left hand` marker 20 cm); overlay deltas (`moving`, aim `overlays`:
composition order assumed); the fuel rod's 4-tick HUD; the sword's fire button (no trigger,
like the oddball). Not done: own sounds (step 10: reload silent, no sword ready sound),
pickup icons, enhancer cards, Sentinel Beam (H3 geometry reads with `h4_rm.load`).

### Halo 1: the Sentinel Beam, a full HALO 3 port (2026-10-06, 12 boots on c40)

Halo 1's Sentinels fire an AI weapon that has no model and is never dropped. The port is
Halo 3's beam, built from scratch. The DROP (the user's option B) is a `weapon` part on
the Sentinel's body-destroyed effect, `characters\sentinel\effects\death` (threshold 0, so
it plays on every kill). Tools, all generic per weapon:

  geometry + look   h3_rm_to_jms.py (H3 render model -> JMS on its OWN skeleton, nodes
                    `frame <name>`, quaternions conjugated, index buffers are TRIANGLE
                    STRIPS) + h1_h3_weapon_model.py (bitmaps from the largest tgda chunk;
                    multipurpose map R = H3 base alpha, G = illum; shader; `tool model`)
  FP animations     h1_fp_retarget.py (`view_offset` moves the whole rig in view space;
                    `holds` writes a still from a source's last frame)
  weapon            h1_pickable_weapons.py on a COPY of the plasma rifle (`template`), with
                    the ratio rule against the plasma rifle
  sounds            h1_port_sounds.py sentinel_beam (TUPLE folders = pieces played one after
                    another; `loop_len` = a short seamless loop, tail crossfaded into head)
  test map          h1_enemy_test_map.py --grunt/--elite "characters\sentinel\sentinel"

What Halo 1 did that the data did not say (each one cost a boot):

* RATE IS TICK-QUANTISED: a round every floor(30 / rate) + 1 ticks, so 30/s fires 15/s and
  15/s fires 10/s (measured from heat vs battery). The tag says 30 and every per-round value
  is doubled.
  CORRECTED by the SMG (2026-10-07, measured by magazine dumps): a 15/s tag fired 15/s and
  22.5/s fired 15/s -- "15 fires 10" does not hold; what holds so far is a 15/s CAP
  (SMG 22.5, beam 30). The beam's heat-based 10/s reading is the odd one out.
* A camera-facing CONTRAIL fired from the camera is seen END-ON and has no width: no beam in
  view, but one in the floor's reflection. Give the trigger a `first person offset` (the
  rocket launcher's is y -0.1). `rounds between tracers` must be 0, or only one round in four
  draws.
* EFFECT LIGHTS and lens flares spawn at the hidden THIRD-PERSON weapon (above the right arm);
  object attachments never show in first person at all. The visible muzzle glow is PARTICLES
  with `first person only`. A non-dynamic light (the Sentinel's gunlight) lights nothing.
* Additive flash sprites SATURATE: five `flash c generic` at 15/s (~20 alive) burn any tint
  to white. One sprite with an RGB tint (`tint as hsv` off) is red. The plasma pistol's green
  flash is the same sprite tinted.
* The template's `vent` markers: its overheat steam and misfire burst need own copies whose
  locations name a marker the new model has (`overheat`).
* Without `first-person overheated` (the stock plasma rifle's hold after `overheating`), the
  engine REPLAYS `overheating`, with its sound and a jump in the pose.
* A LOOPING SOUND ON A HELD TRIGGER. Weapon export inputs, as measured on this weapon:

    primary firing on   never moves (two wirings, one the flamethrower's exact layout)
    overheated          never moves
    ready               stays 1 through an overheat
    illumination        stays up while fire is HELD, even with nothing firing
    primary rate of fire  ramps with the trigger (accel / decel time); bounds must differ
                        (29..30) or the ramp is 0/0. Smooth: the hum's SOURCE
    age (inverted)      0 on an empty battery (the template's function 3)
    primary firing      0 while an overheat or an empty battery blocks the trigger: the
                        one that ends the hum

  A signal that drops between rounds makes the loop restart and QUEUE its start/end tracks
  (the tail grows with how long fire was held). Halo 1 also finishes a loop pass before the
  end track, so the loop is 0.5 s. What shipped: function 0 = 'one' x rate of fire, turning
  off with function 1 (= 'one' x primary firing), which turns off with function 3 (battery
  left). `turn off with` CHAINS. A per-shot sound in the firing effect instead was heard as
  static.

Catalogued as 'Sentinel Beam' (donor Plasma Rifle; balanced: 11.6 damage, ratio-rule aim, H3 battery; default damage 4.64 from the Sentinel yardstick); Armed card via a same-game firing profile (step 11). The enhancer
session wires cards/pools. A cyan layer under the muzzle glow while firing, probably the
beam's own start; kept (user).

### Halo 1: the port tooling after phase 0 (2026-10-07) -- per-weapon CONFIGS

H1_PORT_PLAN.md "Phase 0: DONE" is the full record; the short form:

* **A weapon is a config, not code:** `sprint_toolkit/ports_h1/<key>.py` (dict `PORT`).
  h1_h3_weapon_model / h1_fp_retarget / h1_pickable_weapons / h1_port_sounds /
  make_port_catalog_h1_ports / ai_firing_profile --port / h1_port_test_map / port_backup
  read its sections (`model`, `retarget`, `pickable`, `sounds`, `catalog`,
  `firing_profile`, `test`, `backup`). The old WEAPONS dicts moved there unchanged; the
  sword / fuel rod / Sentinel Beam regenerate byte-identical tags (only `tool bitmaps`'
  own run-to-run `base_address` garbage differs, with the old scripts too).
* **Reservations** (message pair, hud_msg_icons and hud_reticles sequence, label, sound and
  weapon folder) are in each config and in the plan's table; the writers put a port at ITS
  index (padding the message list / sheets), so ports done in any order never collide.
  Two sessions writing the same shared tag at once still race: one at a time.
* **Test map:** `h1_port_test_map.py <key> [--level] [--grunt/--elite <actv>] [--god]
  [--stage]` replaces the SAW-only saw_scenario.py: the port in every SPAWN profile (non-spawn
  profiles: `sprint_profile`, a10's bridge0/bridge1/weapon_insert), made resident if needed,
  enemies swapped on the copy, the live map backed up to E:\HaloBackups\h1_port_test;
  `--restore <level>`.
* **Catalog:** `make_port_catalog_h1_ports.py` derives `weap` / `fp_animations` /
  `requires` for a port and keeps the enhancer's keys.
* **Step 11:** `ai_firing_profile.py --port <key>`; source layouts now Halo 3 (+ODST),
  Reach and Halo 4 (Halo 3's Weapons Properties carry their own inner Firing Patterns, read
  as a fallback). The SAW's stored profile = m020's storm_lmg + Drop Weapon Loaded 0.4..0.8
  set over it.
* **Capacity** (MCC classic): tag space and vertex buffers are each 64 MiB (HCEEK tool's
  own checks), not CE's 23 MiB. The vertex buffer on a10 is the binding one; all 25 ports
  fit even at SAW size. d40's weapon placements reach 115 of 128. NO 384 MiB file cap: a
  458.8 MiB a10 with all tag data past 384 MiB loads and plays (h1_size_test_map.py, user's
  boot 2026-10-10).
* **Two ports in parallel (2026-10-12):** `kit_lock.py` -- one lock taken inside every script
  that touches what ports share (shared tags, kit builds + staging, proofs, catalog / firing
  profiles / the halo1 bank); proofs snapshot, regenerate and restore DONE ports only and run old
  tools from a temporary toolkit copy; `h1_port_test_map` records each staged level's owner
  port. H1_PORT_PLAN.md "Running two ports in parallel" has the rules and the pairs.
* OBSERVATION (Sentinel Beam only): `tool model` on today's JMS gives the beam's FP model
  LOD node counts 6, the shipped and tested one has 0 -- the tested copy was kept.

### Halo 1: the SMG, the wave-A pilot (2026-10-07, 4 boots on a30) -- a plain magazine gun

The whole weapon is `ports_h1/smg.py`; every number there carries its derivation. Order:
`h1_h3_weapon_model.py smg` -> `h1_fp_retarget.py smg --write` + `tool animations
weapons\smg\fp` -> `h1_port_sounds.py smg --write` -> `make_icon.py` + `add_msg_icon.py
<png> smg 30` -> `h1_pickable_weapons.py --only smg --write` (re-applies the FP sound cues:
run it after every `tool animations`) -> `make_port_catalog_h1_ports.py smg` ->
`ai_firing_profile.py --port smg` -> `..\port_sounds.py --write` -> `h1_port_test_map.py smg
[--balanced] [--armed grunt,elite] --stage`.

**Step 4a, the yardstick (user): the ASSAULT RIFLE.** `h1_role_compare.py smg` laid the
ratio rule out per candidate: AR 6.67 x 22.5/s = 150/s (Halo 3's SMG and AR both do 75/s,
so it IS the H1 AR's dps), pistol 175/s, plasma rifle 108/s with no magazine to scale.
DEFAULT = Halo 3's own numbers in the tags; BALANCED = the ratio rows (PORTING "Balance").
Two new balance rules came out of it (see "When the ratio breaks" under Balance): scale a
degenerate near-zero bound by its sibling's ratio (spread minimum 1.83), and the
DUAL-WIELD CARRY RULE (x1.5 on the carry ratio: 562). Ammo pickup, balanced: Halo 3's own
pickup : initial ratio (120/180) on the balanced initial 450 = 300 (user; Halo 1's ratio,
450, refilled almost the whole carry).

What the pilot found (each an OBSERVATION until a second port agrees):
* **TWO RESOURCE GROUPS.** A dual-wieldable weapon's Halo 3 FP graph splits its animation
  data into tag resource groups (fp_smg: 14 single-wield members, 17 dual), each numbering
  its members from 0. The decoder keyed by member alone, so every single-wield animation
  read DUAL data (frame counts gave it away: `ready` 4 frames where the tag says 19).
  h3_anim_decode.members_from_xml / h3_fp_pose now key by (group, member). Every dual graph
  in wave A has this (Spiker, Mauler...). h3_anim_retime / h3_saw_animations still key by
  index alone: fine for single-group graphs, check before using them on a dual one.
* **RATE CAP: Halo 1 fired the SMG at 15/s whatever above it** -- 60 rounds in 4.0 s at a
  15/s tag (15/s, so the beam's "15 fires 10" does NOT hold), 112 in 7.5 s at 22.5/s (15/s).
  With the beam's 30/s -> 15/s: every rate 15..30 has fired 15/s. User: accept the balanced
  100/s (6.67 x 15) rather than move damage. A faster port must be MEASURED (magazine dump).
* **FP placement.** The beam's tested view_offset (-0.0375, 0, -0.0425) as a start; the user
  moved it forward 1.5 / up 2 units (1 unit = 0.01 wu); Halo 3's own placement (0) showed
  nothing wrong but looked worse -> (-0.0225, 0, -0.0225). The beam's 'see into the arms'
  was the beam's own, not a general Halo 3 retarget problem.
* **FIRE SOUND from a LOOP.** Halo 3 automatics fire through in / loop / out; Halo 1 plays
  one sound per round, the AR's a whole shot + tail (0.6-0.8 s, 4 permutations, -13 dB).
  h1_port_sounds `shots`: shot k = the loop's k-th period (its own rate: 66 ms) + Halo 3's
  release tail. User: all sounds good. Stock H1 levels are measured from MCC's
  sounds_adpcm.fsb (the config lists them).
* **BALANCED TIMING.** The patcher retimes `anims` reload / swap (one swap multiplier for
  ready AND put-away: the ready's, x1.45) and then swaps in `anim_sounds` -- the reload's
  sound stretched for the retime: h1_port_sounds `stretch` moves every click to onset x1.5,
  unpitched, carried as an unused FP sound reference (`extra_sounds`). Confirmed in game.
* **MUZZLE FLASH** = the template's sprites (Halo 3 particles do not come across). Halo 3's
  SMG flash is on-axis only: the AR's muzzle-brake ring sprites dropped, the rest moved 1
  unit forward and 1 up, full size (user). `sound_effects` 4th element.
* **RETICLE** (Halo 3 hud_reticles #3, Halo 1 #19): Halo 1 draws the 256 px sheet at about
  half size and thin Halo 3 strokes broke up -- `reticle_thicken` 1 px a side (user: better;
  Halo 3's diagonal gaps kept).
* **SPREAD and the barrel climb** Halo 1 lacks (Halo 3: 0 -> 0.4 deg/shot, 'very late' over
  ~1.1 s): +1.6 deg on the full-bloom cone (4 shots between a player's corrections), through
  the ratio on the balanced side: default 2.75 -> 4.35, balanced 9.43 (user, option A).
  Halo 1's error ramp (1.2 s here, step 4b ratio) arrives when Halo 3's climb does.
* **STEP 11 needs a BASE when the label is the port's own:** donor_for finds a firing base by
  the port's animation label (the SAW is 'ar'); 'sm' has no carrier, so no Armed card.
  `firing_profile` 'source' now takes `donor_weapon` (the AR): Halo 3's 24 ai\generic fields
  over the AR carriers -- Grunts fire from a Marine AR major, Elites from a Flood combat
  Elite AR; 'sm' taught from 'pr'. Confirmed in game (a30, every Grunt and Elite armed).
* **Step 6:** the AR template's magazine item = Halo 1's AR ammo tops it up (confirmed).
* **Not reproduced:** dual wield (no second gun, dual reloads, the 0.9 dual damage scale) --
  deferred by the user; its only trace is the carry rule.

Tools generalized (wave A uses them as data): h1_pickable_weapons `--only`, `bullet`,
`magazine`, `error_deg`, `sound_effects` (+flash), `fields` (step 4b by dotted path),
`hud.ammo_meter`, `reticle_thicken`, `extra_sounds`; h1_port_sounds `shots`, `stretch`;
port_field_audit `--port <key>` (config `field_audit`); ai_firing_profile source +
`donor_weapon`; h1_port_test_map `--balanced` (the patcher's own apply_weapon_ports) and
`--armed` (the enhancer's h1_enemy_weapons.apply at 100%); h1_role_compare candidate rows
(`dmg`/`mag`/`reload`/`damage_tags`; the needle's damage is `detonation damage`);
h1_add_reticle `thicken`; make_port_catalog bullet; port_refs_audit cross-drive maps. New:
`h3_weapon_values.py` (step 4a's Halo 3 table, any H3EK weapons side by side) and
`h1_stock_sound_levels.py` (a stock Halo 1 sound's level as MCC plays it, from the bank).

### Halo 1: the Battle Rifle, wave A2 (2026-10-07, 7 boots on a30) -- burst, zoom scope, on-gun counter

The whole weapon is `ports_h1/battle_rifle.py`, on a copy of the Halo 1 PISTOL (the
yardstick: its zoom, magazine HUD and bullet materials). Same run order as the SMG, plus
`h1_h3_scope.py` (run by make_hud) and the model's `numeric` counter.

**Step 4a (user): the PISTOL.** `h1_role_compare.py battle_rifle` (now burst-aware:
`'burst': (rounds, spacing, cycle)`): the pistol ratio is the only candidate whose every
value scales -- AR ratio: 270 at pickup over a 225 maximum, spread 3.0 -> 1.08 inverted;
sniper ratio: Flood combat forms take 33 s (the sniper bullet's materials). Pistol ratio:
10 a round, 30 a burst, 102/s against the pistol's 88 (Halo 3: BR 44, magnum 38). Rows
per round AND per burst cycle; the burst's shape has no yardstick.

**THE BURST (option B, measured and tuned by the user).** Halo 1 has no burst trigger;
the kit's own precedent is `digsite\weapons\smg`'s second trigger: charge 1 tick,
overcharged action DISCHARGE, a SPEW time. Observations (this port; verify on the next):
* spew 0.2 s at 15/s fired FIVE rounds; held, bursts ran back to back (36 in 2.18 s = a
  5-round burst every 9 ticks: 1 charge tick + 4 gaps of 2). So rounds ~ spew ticks / 2 + 2.
* the CHARGE can stand in for Halo 3's recovery (0.28 s + 4 ticks = 0.41 s, Halo 3's
  0.413) but delays the FIRST round by the same -- tested (B1), not chosen.
* THE BR: charge 1 tick + `does_not_repeat_automatically` (one burst a pull), 10 rounds/s,
  spew 0.15 s = EXACTLY 3 rounds (user's own tuning, 'a similar feeling to the original').
  Not reproduced: Halo 3's 2-tick spacing (here 3) and the 0.28 s recovery (tapping is
  limited by the player only) -- so no burst-cycle balance row. 5b on the built port:
  balanced 73/s at Halo 3's tapping rhythm, more if tapped faster; user: combat good.
* two variants in ONE boot: `h1_port_test_map --secondary <tag>` (a test-only tag on every
  spawn profile's secondary).
* the fire sound: Halo 3 plays ONE fused burst sound (no separable onsets); `shots`
  slices it per round (period 1/15 s + the burst's own tail) -- user: 'pretty good'.

**THE ZOOM: Halo 3's scope as Halo 1's screen-effect mask (`h1_h3_scope.py`; user: the
STANDARD procedure for every zooming port).** Halo 1 draws a zoom vignette as the weapon
HUD's screen_effect mask: RGB = how dark (pistol: black lens, 131 outside, white ring),
ALPHA = where the convolution blurs (255 = blurred), radius = how much. Halo 3's scope
widgets are all drawn BLACK with the bitmap's alpha -- the same darkening -- so the chud's
zoom-only bitmap widgets bake into one mask (widget origin in half-extents, image y down;
origin offset y down; mirror = a copy reflected about the anchor; extend border). The
donor's zoom crosshairs are dropped; the HUD's reticle stays (as in Halo 3).
Observations: the mask is drawn in a centred 4:3 box ~1.09 px a TEXEL at 1080p (512 ->
558 px, 1024 -> ~1116) -- so `aspect` 4/3 and `span` set the size (BR: span 660 on 1024 =
Halo 3's 58% of the height); a convolution radius of 0 SMEARS the whole view (not 'off');
every stock zoom (pistol, rocket launcher, sniper) blurs OUTSIDE the lens only, and the
user keeps that: alpha 'outside' (flood fill of the vignette grey from the border, so
the black ruler bars touching the ring do not pull the blur in). `h3_hud_art` reads a8.

**THE ON-GUN AMMO COUNTER (model `numeric`).** Halo 1's AR display is a
shader_transparent_chicago with flag NUMERIC (its bitmap a 10-digit sequence, counter
limit = magazine), the digit PLACE = the gbxmodel shader entry's permutation (0 / 1). The
H3 digit quads each map one glyph, so the AR's numeric shader drives them. The value is
OUT A (measured: A illumination made it jump per shot; A empty kept 00). Out A comes
from the object FUNCTIONS (out N = function N, scaled by an export 'in'): the pistol has
ONE function, A <- illumination, which also scales the muzzle-flash LIGHT attachment --
moving A to the ammo made every armed Grunt / Elite (and the player) glow. Fixed with the
AR's layout (`obje_functions`, `attachment_scales`): exports A illumination / B ammo;
out A = ammo display, out B = muzzle flash. Balanced: counter limit rows on the two
`schi` tags (the patcher writes schi). Digits are Halo 1 AR style, not Halo 3's.

**Close-out checks the user asked for (now part of every port):** step 4b lists 2 AND 3
-- list 3 here gave the TRACER (Halo 3's BR bullet carries one every 2nd round; the
pistol's none: the AR bullet's contrail, `attachments_from`, rounds between tracers 2),
bounding offset, breaking effect, linear fade; not ported: jitter wobble at period 0,
the unshielded screen flash (Halo 1 has one: the shielded 0.5). A full field diff of
the port against its template (every difference traced to a decision); kit_tag_diff on
the close-out writes; `port_sound_refs --map <test copy>`: it caught three BORROWED pistol
sounds -- ammo pickup, weapon drop (item collision sound), casing eject -- now Halo 3's
(br_ammo / br_drop / br_eject). Armed test = balanced + god (`--armed` implies both).

Also: one resource group in the FP graph (not dual-wieldable, as expected); the graph has
no plain fire_1 / posing:var0 (var1 used); FP view_offset (-0.0225, 0, -0.0125) (user:
+2 then -1 unit); Halo 3's zoom sounds; the headshot reticle cross (#24) not reproduced
(Halo 1 has no such state); `port_sounds.retimed_anim_sound` takes a LIST of swaps (both
reloads stretched x1.34, confirmed in game).

### Halo 1: the Covenant Carbine, wave A3 (2026-10-07/08, 4 boots + 2 measurement runs on a30) -- collection-state scope, on-gun meters, the Armed WDM rule

The whole weapon is `ports_h1/covenant_carbine.py`, on a copy of the Halo 1 PISTOL (the
BR's shape). Same run order as the BR.

**Step 4a (user): the PISTOL.** `h1_role_compare.py covenant_carbine` (candidate rows on
the bullet AND the plasma-bolt materials): the pistol ratio is the only candidate whose
every value scales -- needler ratio: the needle's 65 wu/s and a degenerate error carry
over, no zoom; sniper ratio: zoom 2 x 2/4 = 1x, Flood combat forms 36 s. Pistol ratio:
16.7 x 8.24/s = 137/s against the pistol's 88 (Halo 3: carbine 59, magnum 38). Halo 3's
semi-auto rate = 1 / fire recovery (0.17 s). **Damage type:** Halo 3's carbine is
`plasma_fast`, which has NO shield bonus (energy_shield x1; `plasma_slow` x1.5) -- so the
user took the H1 pistol bullet's table with Halo 3's two differences Halo 1 has a material
for: Jackal shield 0 -> 0.5, Sentinel 0.2 -> 2.0.

**The scope from a COLLECTION-state chud** (`ui\chud\carbine`): `scope_bitmaps` carries
'zoom lvl 1', its eight widgets none -- `h1_h3_scope.widgets()` now inherits the
collection's state (BR mask byte-identical). New per-widget decisions (`per_widget`):
the four needle wedges are scale 0 and get 1.0 from an 'active' .chad (a small slide, not
reproduced), both 'blip's are static (baked), `carbine_distortion` (a 'distortion and
blur' refraction over the two SIDE cells, not the lens) became Halo 1 blur at half
strength in its hexes (`blur`, `bake_maps` -> the mask alpha), clipped to the dark cell
interior (`blur_inside`; test 2: its hexes are larger than the cells and smeared the
outlines). Negative widget scale = a flipped sprite. SIZE/SHAPE (tests 1-2): Halo 1 drew
it too big and too wide with the BR's settings; the user picked x squashed 0.8 (aspect
4/3 / 0.8) at 80% size (span 828) out of two variants in one boot (`--secondary`).
OBSERVATION: the BR's span/aspect were not general -- tune per chud in game.

**ON-GUN METERS** (test 1: 'a flat square on the gun'): Halo 3's `carbine_display` and
`carbine_switch` are METER shaders (`meter_map`, `meter_value` <- ammo), not glow --
`h1_h3_weapon_model` `meters` makes Halo 1 shader_transparent_meters (copied from the
plasma rifle's heat gauge). **The channels SWAP:** Halo 3 = shape in RGB, fill gradient
in alpha; Halo 1 = gradient in RGB, shape in alpha. The meter reads an object OUT (A: the
AR's function layout, as the BR's counter). **Halo 3's steps are GAMMA-spaced** (the
display: 17 values 223..1 = (k/18)^2.2) and Halo 1 compares linearly (lit while gradient
< value) -- test 2: 'drains only from the 3rd shot, irregular' -> `steps` remaps by rank
to (N-1-r+0.5)/N; confirmed smooth. The body's illum lines are 1-2 px (0.4% of the map):
Halo 3 blooms them, Halo 1 does not -> `illum_dilate` 1 + a set `glow` colour (confirmed).

**A Covenant look on a bullet template:** the plasma pistol's green `fire bolt` as the
fire effect (`sound_effects` `copy_from`; no casing, so no eject sound to borrow), its
bolt light (`attachments_from`) and impact effects (`material_responses_from`, the slug
'disappears' where the bullet overpenetrated), the plasma pistol's green muzzle light.
Screen flash (user via the screen-flash session, H1_SCREEN_FLASH.md): Halo 3's shielded
response (ARGB .25/0/.5/.75, intensity 0.5) instead of the pistol's white wash.

**Semi-automatic** (`does_not_repeat_automatically`, Halo 3's 5.88/s; balanced 8.24):
the player's tapping sets the rate (18 in ~4.5 s default, 27 in ~4 s balanced = ~6.5/s):
below both the tag and the tick-rule cap -- the 15/s observation is not tested by it.
**Step 6:** Halo 3 has NO carbine magazine item -> pistol ammo (user), 36 = Halo 3's
family pickup : initial 2/3 on 54 (balanced 67). Needler ammo exists in HCEEK but no
campaign scenario places it.

**THE ARMED WEAPON DAMAGE MODIFIER RULE (user, 2026-10-08)** -- see "Balance". The
Armed test felt too strong; Halo 3's profile carries no WDM, so the slots kept the AR
donors' 0.4 (the Grunt major slot 0.5). A tag estimate needs a hit fraction (the
carbine's AI aims to 0.35 deg with a 180 wu/s slug; plasma bolts at 25-50 wu/s with
1.5-5 deg mostly miss) -- so MEASURED: a30, every Grunt/Elite palette entry -> Elite
minor plasma rifle (`--grunt/--elite`), player mortal (`--armed elite --mortal`), stopwatch
time to die from the dropship group's first shot x5: stock 3.61 s, Armed carbine (0.40,
balanced) 2.04 s -> 0.23 measured; Rule B gives 0.26. `h1_vitality_live.py` (a live
shield/health logger) did NOT get through its moved-triple step in reasonable time -- the
first scan keeps too many candidates; fix before relying on it.

Close-out: list 2 = 0 (the damage effect's wobble period deliberately not written, as the
BR); lists 3/4/5 recorded line by line in the config (CLOSE-OUT RECORD); full field diff
`h1_port_template_diff.py covenant_carbine` (NEW: every pair from the config, 197
differences traced; it found an orphan `carbine_tint_map` shader, removed); port_refs_audit 0 problems; port_sound_refs 0 BORROW (the tool does not read
Halo 1 FP graphs: the writer's listing shows all five cues `cc_*`); 5b: default = Halo 3's
own row, balanced = the pistol-ratio row exactly. One resource group (not dual-wieldable).
Not reproduced: the wedges' slide, the refraction itself, the headshot cross.

### Halo 1: the Beam Rifle, wave A4 (2026-10-08, 9 boots on a30) -- a tapped heat weapon, a template that is NOT the yardstick, glow on a bloomless engine

The whole weapon is `ports_h1/beam_rifle.py` (CLOSE-OUT RECORD in it), on a copy of the Halo 1
PLASMA PISTOL, with the SNIPER RIFLE as the yardstick: the first port whose template is not its
yardstick.

**Step 4a (user): the SNIPER.** `h3_weapon_values.py` now prints heat (loss normal / overheated,
recovery / overheated thresholds), the CAMPAIGN battery and zoom; `h1_role_compare.py beam_rifle`
simulates overheat pauses for tapped weapons (`heat_sim`). Halo 3's beam = its sniper's 80 /
1200 wu/s / 500 / aim; rate 1 / 0.4 s vs 1 / 0.7 s; heat 0.7 a shot (2 quick shots overheat).
Plasma pistol ratio: 205.7 damage (degenerate: the pistol's 7); Sentinel Beam ratio: two
derivations, a 5-shot battery. Balanced = sniper ratio: 101, 3.5/s, zoom 1.75x / 8.44x, Halo 1
sniper aim; heat and battery Halo 3's (no sniper counterpart). **Battery: Halo 3 has a
CAMPAIGN age field** (0.05 = 20 shots) beside the multiplayer one (0.1) -- read it. **Materials
(user):** the sniper bullet's + the Carbine's plasma pair (Jackal shield 0.5, Sentinel 2.0);
Flood stays 0.05 (Halo 3's bullet_fast and plasma_fast treat Flood alike). **ONE heat loss in
Halo 1** where Halo 3 has two (cooling 0.575, overheated 0.3): Bungie's pair splits (H1 plasma
rifle = H3's overheated loss, plasma pistol = the cooling one); judged in one boot (0.3 / 0.575),
the user took the average 0.4375 (a 2.06 s vent).

**Template = role, not yardstick.** The heat/battery HUD (`master plasma`), overheat states and
`cannot_fire_at_maximum_age` came from the plasma pistol; the damage table, bullet, contrail and
zoom screen effect from the sniper. Costs: the charged trigger (`keep_triggers` 1), its two
charge attachments, the heat flares (`drop_attachments`), the low-battery misfire (Halo 3 has
none), and **STEP 4b must run BEFORE boot 1**: the sniper's `use error when unzoomed` was in
list 5 and the user found it in test 3 ('does not hit the crosshair'); list 4 also held the
pistol's weapon type, firing noise, camo ding, charged illumination; the template diff later
found the bolt's responses turning the sniper's 11 OVERPENETRATE materials into 'disappear'
(Halo 3's beam overpenetrates the same 11) -> `material_effects_from` (effects only), and the
sniper screen effect's night vision / green desaturation (`screen_effect_clear`).

**Scope (h1_h3_scope):** the chud's two widget sets are FULLSCREEN (window state 13) vs SPLIT
SCREEN (242) -- `widgets()` inherits the collection's window state and bakes fullscreen only;
`parent` anchors take the collection's placement. Meter fills (meter shaders: garbage as a
mask) and the hidden warning flashes dropped, the static meter frame baked (user); the
`distortion and blur` layer covers everything outside the lens = Halo 1's outside blur
(`blur` x1 -- the grey flood fill finds no vignette at ~90% dark). The Carbine's 80% /
x0.8 squash fitted again (2nd scope; the BR's 4/3 was the variant).

**What Halo 1 did (each an OBSERVATION, PORTING rule):**
* Halo 3's `*_first_person_fire` sound is only the FP LAYER (silent 0.3 s, then clicks): the
  shot is the third-person fire sound; mix both (`bm_fire`). Look first: `h3_sound_envelope.py
  <h3_dir> [--match fire]` prints every folder's subsongs with a 0.1 s envelope.
* Halo 3's overheat in+loop+out is 6.9 s against a 2-3 s vent: 'in' on the FP overheating
  animation, 'out' on o-h-exit, no loop.
* The sniper's trail rides SMOKE point physics and drifts with the wind (`contrail`
  `no_physics`). The trail is drawn from the camera unless the trigger's FP offset puts the
  round at the muzzle -- computed from the idle pose (fp_render: primary trigger marker in
  camera space, 0.58 / -0.067 / -0.045 wu).
* **Impact colour = the PROJECTILE's change colour A** (`c generic` particles): the bolt's runs
  magenta -> green; the sniper bullet has none -> own pink (`change_color`) + `impact_tint`.
* **The muzzle light as an attachment stayed lit** (illumination export) -> a light PART of
  the firing effect, 0.1 s (`fire_effect`, the Sentinel Beam's recipe).
* **Lights, lens flares and attachments draw at the hidden THIRD-PERSON gun in first person**
  (third time: Sentinel Beam, test 1 green dot, gem flares at `gem n` markers). No first-person
  or zoom switch on a Halo 1 lens flare. Do not use them for first-person looks.
* **GLOW without bloom:** Halo 3 colours greyscale illum masks through shader parameters in
  function data (unreadable) and BLOOMS; Halo 1 does neither. What worked, in order:
  (1) find which material really glows -- render the FP pose coloured by material
  (`fp_material_view.py <key> --illum <H3 illum bitmap>`;
  (`beam_rifle_glass` was an ADDITIVE Halo 3 template -- the gems, not glass; the illum-map
  lines all face down, hidden); (2) ADDITIVE chicago shaders (the needler's needles are the
  precedent) -- a FLAT colour reads as paint even additive; (3) a TEXTURE with falloff: the
  strips sample the bright band of Halo 3's own luminous mask (snowbound airlock_field_mask
  alpha), pink to white-hot, scrolled along v (`glow_shaders` `mask`, `v_scroll`); (4) small
  pieces (the gems, a few pixels) need a HALO: **glow cards** -- each piece copied 1.3x about
  its centre, lifted 0.05 along its normal, additive, falling to 0 at its UV box edge
  (`glow_cards`; the user picked 1.3 of 1.8 / 1.5 / 1.3). Halo 1 gbxmodels store UVs
  normalized with a model-wide `base_map_u/v_scale` -- multiply before sampling a texture.
* Tool rejects attachment elements APPENDED with Reclaimer ('reference name length
  mismatch'); re-point existing ones (`attachments_set`).

**Step 11 (user): the SNIPER's carriers** (the plan said none; the Flood combat Elite and the
armoured Marines carry it), the Flood Elite for EVERY slot via the profile's new
`donor_variant` (h1_enemy_weapons.donor_for reads it before a saved choice; the ranking gave
Grunts/Jackals the armoured Marine). WDM rule base 0.4: 0.40 default / 0.23 balanced. Armed
Grunt, Jackal (all Grunts swapped to Jackals: a30's dropship has none) and Elite confirmed.
**New user rule for every Armed card** (handed to the enhancer session): Grunts with a
two-handed weapon fire at half rate (heavy support excepted); Jackals with one lose the arm
shield (to test).

Final check (user): the weapon flags, decided by NAME (the audit lists the flags word under 'decide
by hand'): Halo 3's beam and sniper both magnetize only when zoomed -> the sniper's
`aim_assists_only_when_zoomed` (Halo 1's one flag also stops autoaim unzoomed). Close-out: list 2 = 0 (weapon, projectile; the damage effect's two = Halo 3's own breaking
effect), template diff 191 traced, kit_tag_diff no change on the final rebuild, refs 0
problems, sound refs 0 BORROW (the older ports' were closed 2026-10-08: own sounds or
user KEEPs, `sound_keeps`), 5b default = Halo 3's row, balanced = the sniper-ratio row. Not
reproduced: Halo 3's two losses, bloom, live scope meters, the headshot cross. Zoom-out on
overheat: the next section (halo1.dll, built and confirmed by its own session).

### Halo 1: the Beam Rifle, wave A4 -- leaving the zoom on overheat (research, 2026-10-08, nothing patched)

Test 3: zoomed + overheating, the player STAYS zoomed (Halo 2-4 drop the zoom). No stock
Halo 1 weapon both zooms and overheats, so the engine never had to handle it. Read-only
analysis of `halo1\halo1.dll` (sha256 `0a12dc56...6cd42e6c`, MCC build of 2026-06-22).

**Tag-only: none.** weap flags (Reclaimer hek `weap.py`): nothing about zoom except
`aim_assists_only_when_zoomed`; `must_be_readied` is unrelated; trigger flag
`use_error_when_unzoomed` is accuracy only. The heat block (recovery/overheated/detonation
thresholds, loss, illumination, overheated/detonation effects) has no zoom field; zoom is
`zoom_levels` + `zoom_ranges` only; wphi does not drive zoom state. The reload unzoom is
engine code (below), not a tag setting.

**Script: not usable.** Halo 1 HaloScript HAS `players_unzoom_all` (and
`player_action_test_zoom`), but no script function reads weapon heat, so a script cannot
know WHEN to call it.

**Where the engine keeps and clears zoom** (addresses at image base 0x180000000):
- Per local player control, 4 entries x 0x58 from the pointer at `0x182D8FE70`:
  +0x10 unit, +0x30/+0x31 weapon index / desired, +0x32 grenade, **+0x34 zoom level
  (int16, -1 = unzoomed)**, +0x5E zoom-button latch, +0x60/+0x62 zoom hold.
  `players_unzoom_all` = `0x180A9A22C` (writes +0x34 = -1, +0x5E = 0 for all four).
- Player control tick `0x180A9915C` unzooms on weapon switch (`0x180A993BD`, `0x180A993E1`)
  and with no weapon (`0x180A99619`); zoom input via next-zoom `0x180B770B8`, which refuses
  while `0x180B76A88` (weapon +0x280 == 1) says so.
- Melee / grenade / vehicle / death paths write +0x34 inline (`0x180AD5225`,
  `0x180AD5D17`, `0x180B00CD5`, `0x180B0A1CF`).
- **First-person weapon event handler `0x180B2A3F0(local player, event)`** (called through
  `0x180B27BA0(weapon, event)`). Its switch unzooms for events **9, 10, 0x12, 0x13 = the
  reloads** (sent from the reload start at `0x180B78330`). That is the "reload unzooms" rule.
- **The overheat:** weapon tick `0x180B74E6C` compares heat (weapon +0x204) with the tag's
  `overheated_threshold` (weap +0x350), sets the overheated bit (weapon +0x1F8 bit 0) once,
  and sends **event 0xF** (0x10 for one variant) to `0x180B27BA0`, then the tag's
  overheated effect (weap +0x380). The switch does nothing with 0xF/0x10 -> zoom stays.

**The patch site (option A, 6 bytes in place, no code cave):** the switch tail
```
0x180B2A462  8D 42 EE   lea eax,[rdx-0x12]   ->  8D 42 F1   lea eax,[rdx-0x0F]
0x180B2A465  41 3B C7   cmp eax,r15d (=1)    ->  83 F8 04   cmp eax,4
0x180B2A468  77 5D      ja  (skip unzoom)       unchanged
```
file offset `0xB29862`. The unzoom range becomes 0xF..0x13: adds exactly the two overheat
events (0x11 is taken by its own `je` before; 0x12/0x13 keep unzooming). Both paths end at
`0x180B2A4C7`, and the later code there branches on the ORIGINAL event, so nothing else
changes. Affects only a weapon held by a LOCAL player (the AI path exits at -1); stock heat
weapons (plasma pistol/rifle) are never zoomed, so for them it writes -1 over -1.
**Not covered:** re-zooming during the vent stays possible (the event fires once). Blocking it
would need a code cave in `0x180B76A88` (test weapon +0x1F8 bit 0) -- option B, only if the
user wants it after seeing A (check first what Halo 3 does in the vent).

**Risks / how to ship:** option A as a LIVE memory patch (iron_live.py pattern: no file
write, reverts on restart, MCC may stay open) is the low-risk route; as a dll file patch it
needs MCC closed, the user's go, a backup, and a byte-pattern check (the bytes above +
context) so an MCC update cannot misplace it. It is global (every map, co-op: each machine
needs it). Bit 0 of +0x1F8 = overheated is read from the code, unverified live.
**Recommendation:** A, live-patched, one boot on a30: zoom in, overheat -> must drop to
unzoomed; reload still unzooms; plasma pistol unchanged.

**BUILT 2026-10-08 (option A, untested in game):** `sprint_toolkit/h1_overheat_unzoom.py`, Options -> Patching -> Halo 1 -> "Overheating drops the zoom (halo1.dll)" (`h1_overheat_unzoom`, off by default, in the run's options snapshot so a co-op partner gets it too). Every patch (any game) syncs it: LIVE into a running MCC (verified live: the running dll held the stock bytes + context) AND into the file -- in place with MCC closed; with MCC running the loaded dll cannot be opened for writing but CAN be renamed, so the patched copy is swapped in and the original becomes `halo1.dll.inuse-<time>`, deleted by a later sync. First file write keeps `halo1.dll.prepatch.bak`. Unticked -> both halves back to stock. Engine-wide by construction (keyed on the overheat event), so every heat weapon a run gives zoom to is covered, not just the Beam Rifle. CLI: `python sprint_toolkit/h1_overheat_unzoom.py --show | --on | --off`.

**A CONFIRMED in game 2026-10-08** (the user: loads and works). **Option B BUILT and CONFIRMED in game the same day**, sub-option "...and no zooming back in while it vents" (`h1_overheat_no_rezoom`, on, only acts with A): the call to the can't-zoom check at `0x180B7710D` (inside next-zoom `0x180B770B8`) goes to a 76-byte cave in the .text slack at rva `0x1750180` (file `0x174F580`; VirtualSize ends at 0x1750171, raw at 0x1750200, so it is in the file and mapped RX; live it reads as zeros) that calls the original check and also says "can't" while weapon object +0x1F8 bit 0 is set. That bit is set at the overheated threshold and cleared below the RECOVERY threshold (weapon tick `0x180B750E7`), i.e. exactly the vent. Zooming out still works. Object resolution copies next-zoom's own (table ptr rva 0x1C42248, data base 0x2D9CDF8; object = data + entry offset, flags at +0x22C from that). Cave filled before the call points at it; call restored before the cave is cleared.

---

### Halo 1: the Spike Rifle, wave A5 (2026-10-08) -- a dual-wieldable arcing automatic

The whole weapon is `ports_h1/brute_spiker.py`.

**Step 4a, the yardstick (user): the ASSAULT RIFLE.** `h3_weapon_values.py` + `h1_role_compare.py
brute_spiker`. Halo 3's spiker is `bullet_slow` -- the AR's damage group, not the needler's
`plasma_slow` -- and does the AR's dps (9 x 8/s = 72 vs 7.5 x 10/s = 75). AR ratio: 12 x 12/s =
144/s (H1 AR 150), magazine 75, 300 / 375 (DUAL-WIELD CARRY RULE x1.5), reload 2.8 s, error
1.08 -> 2.71 (the minimum's own ratio is degenerate: the maximum's 6.5/3.0 on both, the SMG
rule), 101 -> 71 wu/s, range 70, aim 6/20 14.4/22.5, melee 56.6 (cut_melee 72 / strike_melee 70);
it kills like the H1 AR (Elite major 2.17 s vs 2.07). The needler ratio (180/s on the needle's
materials: Flood combat forms in 3 shots; its spread minimum 0/0) was rejected. No AR
counterpart, so Halo 3's own in BOTH versions: air gravity 0.2 (the H3 AR has 0) and the
spike's ricochet material responses (bounce at 0-60 deg off hard metal / terrain / glass).

DONE 2026-10-08 (13 boots on a30; ten-map rebuild BATCHED with the SMG, BR, Carbine, Beam
Rifle). The config's CLOSE-OUT RECORD lists every decision. What the Spike Rifle found (each an
OBSERVATION until a second port agrees, except the user RULES):
* **4b BEFORE BOOT 1 paid off:** the AR bullet starts its detonation timer ON FIRST BOUNCE
  with timer 0 -- every ricochet would have ended at the first bounce; Halo 3's spike: when at
  rest, 1 s, minimum velocity 12. Flags decided by NAME again (template diff + Halo 3 xml).
* **H3 export cache** keyed by basename returned another weapon's `fx\projectile.effect`:
  now keyed by path (h3_weapon_values, h1_fp_retarget). Check any cached H3 read whose name is
  generic.
* **The stuck spike (user: 'like the needler'):** Halo 3 spawns a MODEL PARTICLE at the impact
  (`fx\particles\models\weapons\brute_spike`, 4-5 s) -- Halo 1 has none, so the needle's
  recipe: response `attach` + the particle model as the projectile's MODEL
  (`h3_rm_to_jms.convert_particle_model`, `extra_models`), timer when at rest 4-5 s, then the
  needle's burst with no damage (user: 'detonate like the needles'; Halo 3's spike has no
  detonation effect at all -> silent), x0.5 (user). Attach did NOT cost the hit stagger (A/B).
* **Ricochet** = Halo 1 potential response `reflect` (skip fraction = 1 - Halo 3's chance;
  impact angle 0-60 deg; frictions). Confirmed on rock and metal, not on dirt or bodies.
* **Visible spike** = the AR tracer's contrail recoloured (Halo 3's light volume colour, BGRA
  in its function data), `rounds between tracers` 0 = EVERY round (confirmed).
* **GLOW, the third time (after the Carbine and the Beam Rifle):** Halo 3's illum colour lives
  per SHADER (self_illum_color, BGRA bytes) with an intensity (6!) Halo 1 cannot do -- a
  saturating colour stands in. fp_material_view's sampling MISSED thin lit lines (6x6 / 15%):
  now exact coverage + `--texels` (the lit texels drawn on the pose) -- use them FIRST. Tiny
  lights on edge-on faces are right but invisible without bloom: GLOW SPOTS (`glow_spots`: a
  radial halo card per lit-texel cluster, plus a camera-facing card), radial bore cards (the
  Beam Rifle's gems), a flat card for a lit window; flat cards over whole faces read as squares.
  FP glow geometry hides with the FP model when zoomed (tested).
* **The hit effect on the player:** a hit plays the projectile's response effect for the
  player's MATERIAL (#22 shielded) -- at a high rate the donor's 49 sparks flood the view.
  THE HIT-EFFECT RULE v2 (Balance; `h1_hit_effect_load.py`, closing check 9).
* **Armed test (user rule):** Jackals ride the FIRST dropship (`DROPSHIP_JACKALS`; a30 =
  lz_search's lz_cship, not first_wave's ship). One Jackal came out of an expected 2-3 (kept).
* Muzzle flash: the SMG's on-axis recipe, 0.5 units higher (user). Fire sound: a one-shot per
  round (no loop to slice). Dry fire = Halo 3's own reuse of the SMG's (own copy). Flashlight:
  the game's own, a standing user rule (port_sound_refs KEEP).
* Not reproduced: dual wield (carry rule x1.5 instead), the bounce speed window (20-30 wu/s:
  the balanced spike is 4x faster), Halo 3's 1 s impact glow decal.

### Halo 1: the Mauler, wave A6 (2026-10-08) -- a one-handed pellet weapon

* **Halo 3 keeps PELLETS on the projectile, not the barrel.** The barrel reads projectiles per
  shot 1 and error 0 (h3_weapon_values); the count and cone are the projectile's `conical
  spread` block: yaw count x pitch count (3 x 5 = 15), `spread` 7.5 deg, a fixed GRID. The
  mauler (`excavator_shard`) and the shotgun (`shotgun_bullet`) share it exactly. Distance
  falloff = flag 'damage scales based on distance' + `air damage range` (mauler 2.5 -> 5 wu,
  7 -> 1.5; shotgun 2 -> 4, 10 -> 3). Halo 1 has the same falloff fields (shotgun pellet
  18..25 -> 8 over 1.5 -> 3 wu) but a random cone (error angle 10, distribution 'point').
* **Step 4a (user, 2026-10-08): yardstick SHOTGUN** (ports_h1/brute_mauler.py yardstick). Same
  projectile family in Halo 3 (pellets, cone, bullet_slow, falloff): every value has a
  counterpart; the pistol has no pellets/cone/falloff (its lower bound 0 is degenerate).
  Balanced: 15 x 15.05 (lower 4.0 over 1.875 -> 3.75), 0.75 s, 10 (13 / 62 with the carry
  rule), 55 fr WHOLE-magazine reload (H1 shotgun's 12 shells 144 fr x 55 / H3 shotgun's empty
  -> full 144 fr), error 10, 140 -> 100 wu/s, range 53.3, aim 6/19.1 12/19.1, melee 56.6.
  Default (Halo 3's own) is weak in Halo 1: 105 a shot vs the shotgun's 322 (Elite major in 3
  vs 1 on normal) -- the wave-A rule, shown to the user. Damage table: the shotgun pellet's.
  Hit-effect rule with PELLETS (user, 2026-10-08): count SHOTS, not pellets -- 1.33/s is
  under 3.5/s, the pellet's shield-hit effect stays x1 (pellets x rate = 20/s would give x0.004).
* **Before boot 1 (4b + template diff + port_sound_refs), the Shotgun template's traps:** the
  magazine flag 'every round must be chambered' and weapon type 'shotgun' (Halo 3's mauler has
  neither, Halo 3's shotgun both: cleared, by name); the trigger's EMPTY field names the AR dry
  fire SOUND directly and `shotgun empty` sits on the MISFIRE field (a sound_effects copy of
  `shotgun empty` repointed nothing): empty = the port's own dry fire by `fields`, misfire
  cleared. The firing effect plays its fire sound in TWO identical events at 0 s (kept: the
  level matches the shotgun's; h1_pickable_weapons' swap check now counts sounds, not parts).
  Halo 3's pellet attachment (`fx\projectile`) is an EMPTY effect: nothing to port.
* Step 6 (user): no Halo 3 ammo item; Halo 1's shotgun ammo (60 a box) tops the Mauler up, kept.
* One-handed pose: `ml` taught from `hp` (Halo 1's pistol), not `sg` (two-handed).
* **DONE 2026-10-09, 7 boots on a30** (dry default, 2 fix boots, 3 balanced incl. glow, Armed):
  user-confirmed; the ten-map rebuild is batched (user's go). Close-out record in
  `ports_h1/brute_mauler.py`.
* **Ammo display = Halo 3's own round icons (user, test 1: 'the original pips').** `ammo_meter`
  `art` {'h3': (sheet, sequence)}: the chud's ballistic-meter sprite (the Mauler: `ballistic_
  meters` #13, read off `ui\chud\excavator`), its FIRST icon cut by alpha columns, drawn one a
  round in a row at Halo 3's spacing, native size at most, top-aligned (centred sat low under
  the counter). A full magazine lit 4 of 5: the value is capped at 255 and the compare is
  strict, so a tick threshold of exactly 255 never lights -- `plan` now keeps the top below
  255 (only magazines whose tick count divides 255 change: 5, 15, 17, 51, 85).
* **Glow in Halo 3's SHAPES (user, test 3: 'works well for shapes').** Radial spot cards read as
  'lights drawn onto the weapon'. What works: the lit triangles COPIED in place (scale 1.0, lift
  0.02, same UVs) as an additive chicago whose texture IS Halo 3's illum mask (`glow_shaders`
  `mask` + `mask_channel` 'rgb' + `dilate`; `glow_cards` with `lit`), on a saturated base illum
  (HOT, +1 px). `skip_normals` + `skip_dot` (glow_cards and glow_spots) leave out faces along an
  axis -- the barrel ends faced exactly +-x (dot 1.0), the drum windows tilted (0.84..0.99).
* **A thin lit line on a face edge-on to the FP camera stays OPEN** (user: 'very minor, move
  on'): the body slit (0.8 x 0.2 along the gun, a sideways face). Tried: a camera-facing radial
  card (`face` + `only_face`: a blob), a fin along the lit texels (`strip`: edge-on in the
  render), the face's own shaped card grown 3 px x2 gain (still not seen). OBSERVATION: Halo 3
  shows such lines by bloom alone; locate a user-circled light by rendering the lit texels
  (fp_material_view --illum) and matching THEIR screen position, not a guessed spot (test 3
  carded the wrong light).
* **Armed donor with split carrier bases (user):** Halo 1's shotgun carriers are Flood combat
  (WDM 0.15) and Marines (0.6) -- one donor pinned for every slot (`donor_variant`, the Flood
  combat Elite), base 0.15: WDM 0.345 default / 0.16 balanced. WDM sits at actv +0xC4 (big-
  endian in the tag file, after the 64-byte header).
* **Test rule (user, 2026-10-09):** the god shield on EVERY port test boot (h1_port_test_map
  default; `--mortal` opts out).
* **Tools from the Mauler** (sprint_toolkit, generic): `h1_weapon_values.py` (step 4a's Halo 1
  side, raw fields incl. falloff and the trigger's three effect fields), `h1_weapon_carriers.py`
  (step 11: carriers of a weapon + their WDM), `h1_port_write_proof.py <key> snap|diff`
  (closing check 6), `h1_tag_inspect.py effect|hud` (template effects / HUD elements),
  `h3_port_sources.py chud|sounds` (a chud's reticle + ammo sprites; Halo 3 bank folders),
  `glow_spot_list.py` (lit-texel spots: centre, normal, extent -- for the glow filters).
* 5b tool fix: `h1_role_compare` kept only the last Damage Upper Bound row (both bounds alike
  in earlier ports); it now keeps the range's two bounds (the Mauler's 12.6..17.5 -> 15.05).

### Halo 1: the Brute Shot, wave A7 (2026-10-09, 9 boots on a30) -- an explosive grenade launcher

The whole weapon is `ports_h1/brute_shot.py` (its CLOSE-OUT RECORD lists every decision).

* **Step 4a (user): yardstick ROCKET LAUNCHER.** The damage is the grenade's DETONATION damage
  effect (`shot_grenade_explosion` 26..73, radius 0.3 -> 1.1, `explosion_small`); h3_weapon_values
  prints none, so read the projectile's `detonation damage` (and the yardsticks': rocket 80..240
  over 0.9 -> 2, flak 30..60, frag 60..160). RL ratio: 95.8 every 0.75 s (128 dps vs the rocket's
  158 = Halo 3's 0.81 relation), 6 / 18 / 18, 3.4 s, 24 -> 4.4 wu/s, range 14.6, aim 0/21 7.2/28,
  melee 61.9. The Fuel Rod ratio (Hunter armour immune: Halo 1's Covenant explosion table) and
  the Frag ratio (damage only) were shown and rejected. Halo 3's damage table: explosion_small
  vs _large differ only on soft flood flesh (x1 vs x2) for Halo 1 -> flood_combat_form 1.0.
* **Halo 3's grenade does NOT bounce** (the plan assumed it): impact (detonate) on every
  material, its `attach` response at chance 0, timer 0, a mid-air burst at 20 wu. Kept in both
  versions; a bounce is a later enhancer option (user).
* **MINIMUM VELOCITY DETONATES in Halo 1.** Halo 3's 11 (an at-rest threshold there) burst the
  grenade after ~1 s (user's stopwatch) instead of Halo 3's ~2 s = its 20 wu range (16 -> 7 over
  6..15 wu = 1.9 s). Set 0; the range decides (confirmed ~2 s).
* **An explosive projectile is new tooling:** `bullet.damage` None + `explosion` (own copies of
  the detonation effect and its damage part; `part` when the effect is another weapon's -- by
  class, the frag effect names a LIGHT of the same path as its damage; `scale` an own scaled
  particle-system copy; `swaps`; `fields`), `keep_attachments`, `set_attachments` (+ `copy`
  scaled), `hum` on the projectile, `glow` (light + recoloured flare), `drop_widgets`;
  `sound_effects` `drop_event_parts`; h1_port_template_diff pairs the explosion.
* **What the rocket template carried along (each caught in game, not by 4b):** its contrail
  emits points at 0..5 wu/s along the marker plus smoke point physics (the trail left the arc
  -- replaced by Halo 1's frag smoke trail, which Halo 3's soft-smoke particles resemble); its
  LIGHT-VOLUME WIDGET (an exhaust streak turning with the shot angle); a one-sprite muzzle
  flash with the back-blast on `primary ejection` (-> the shotgun's flash family, its fire
  sound dropped from the second event); explosion screen flash duration 0 (-> Halo 3's 1 s,
  yellow by the user: blue reads as plasma). Template objects' WIDGETS and contrail physics
  belong on the 4b/template-diff checklist for any projectile port.
* **Halo 3 WORLD MODELS CAN BE AUTHORED TILTED.** The brute shot's root `gun` node rests ~55 deg
  rotated; the weapon frame is the `body` node (x forward, z up, primary_trigger 0.25 ahead).
  Halo 3 holds weapons by markers, Halo 1 by the object frame (the pickup icon came out
  diagonal; third person and drops sit in it). `h3_rm_to_jms.convert(frame=)` re-roots the
  model (vertices + root bind; markers stay node-relative); config `world_frame`. The vertices
  are in MODEL space even for `rigid` meshes (checked: markers land on the geometry). Check
  every Halo 3 world model's root rotation.
* **Glow on an INNER ring wall: fold it** (`glow_cards` `fold`, h1_h3_weapon_model.fold_cards).
  The chevrons sit on a wall facing the drum axis -- Halo 1 shows only the far half (Halo 3:
  bloom). Folded flat into the ring opening on both faces, chevron UVs kept. Four boots to get
  right: (1) a white half ring (gain x1.6 + 2 px -> x1.0, 1 px); (2) the circle fit pulled by
  stray lit triangles (drop short / off-circle ones); (3) the wall is +-0.74 tall on one half
  and +-0.42 on the other, Halo 3's UVs follow it -- map each vertex by its place across ITS
  OWN triangle's wall into the full strip (v); (4) the lit-texel test took 81 of the 96 strip
  triangles (half-quads) -- take the strip by UV (`v_range`); the mask texture at 512 (`size`).
  Check a fold with a TEXTURED render (mask sampled at the UVs) before a boot.
* **Armed test (user rules):** a30's first dropship 3 Jackals / 3 Grunts / the Elite squad
  (`DROPSHIP_JACKALS` per-squad counts) for every Armed test; `--actor-flags
  avoid_friends_line_of_fire,crouch_when_in_line_of_fire` (Halo 1's humans carry them, no
  Covenant actor does) made Grunts / Jackals / Elites 'more careful' with explosives -- a
  SPECIES flag, so an enhancer OPTION (handed off). Halo 1 actor variants have no minimum
  firing range.
* Explosion visuals vs radius cards: EXPLOSION_VISUAL_SCALE.md (parked by the user until every
  weapon is ported everywhere); the Brute Shot already has its own particle-system copy.
* Step 6 (user): Halo 3's brute shot has no ammo item; the rocket's box (the template's magazine
  item) tops it up RATIO-SCALED: 2 x carry 18/8 = 4.5 -> 4 a box (the weapon's own magazine item;
  the rocket keeps 2).
* Not reproduced: Halo 3's bloom (the fold stands in), its grenade light volume (a flare).
* **Tools from the Brute Shot** (sprint_toolkit, generic): `h3_tag_fields.py` (any H3EK tag's
  fields; a projectile's detonation / damage / responses summary -- what h3_weapon_values does
  not print), `h3_rm_info.py` (a Halo 3 render model's nodes, markers, vertex types and the
  TILTED-ROOT check; `--frame <node>`), `glow_fold_render.py` (a folded glow textured as Halo 1
  draws it, before a boot), `jms_side_view.py` (a JMS side-on, one material highlighted),
  `h1_model_markers.py` (gbxmodel markers live per permutation); `h1_port_test_map.py
  --actor-flags`, per-squad `DROPSHIP_JACKALS`.

### Halo 1: the Spartan Laser, wave A8 (2026-10-09/10, 19 boots on a30) -- a charge-up beam

The whole weapon is `ports_h1/spartan_laser.py` (its CLOSE-OUT RECORD lists every decision). On a
copy of the Halo 1 PLASMA PISTOL (heat + battery), yardstick the ROCKET LAUNCHER.

* **Step 4a (user): ROCKET LAUNCHER, with the AOE SPIKE BUMP counted (A/B in game).** What
  h3_weapon_values does not print: the trigger is `spew-charge` (2.5 s; while charging barrel 0
  fires a NO-damage tracer at 20/s, charged barrel 1 fires 5 beam rounds at 30/s with one firing
  effect); a round's damage is the projectile's DETONATION damage, 20 over 0..0.6 wu PLUS an
  `aoe spike damage bump` of 94 inside 0.15 wu -> 114 a direct hit, 570 a shot (the bump is what
  one-shots a Halo 3 Spartan: hard_metal_thin body + energy_shield_thin, both x0.5 to `laser`);
  battery = age 0.04 a round x 5 = 5 shots; heat 1 a round. Damage group `laser` = the rocket's
  `explosion_large` except hard_metal_solid (Hunter armour) 0.5 vs 1. **Halo 3's rocket has the
  bump too (240 + 200 = 440 direct):** the user's A/B picked 'with the bump' (A, 408 a shot vs B,
  131) -- and the BRUTE SHOT's rocket ratio, which had used 240, was corrected to 73/440 (balanced
  52.3, WDM 0.91). Read every Halo 3 damage effect's `aoe spike` fields before a ratio.
* **CHARGE in Halo 1: two mechanisms, only one the AI uses.** The plasma pistol's PAIR (trigger
  0 charges; a full charge -- or 'discharge' at the charge's end -- fires trigger 1; an early
  release fires trigger 0) worked for the player (a tap = Halo 3's harmless tracer) but Armed AI
  only ever TAPPED it -- with a longer burst, special fire 'overcharge' (Bungie's only charging
  AI: the plasma-pistol Jackals) and a charge hold. The FUEL ROD's ONE trigger (charge, then
  'discharge' its own projectile; rounds per second 10, 'does not repeat automatically') works:
  the player's early release fires NOTHING; the AI needs **Rate Of Fire 0** (actv 0x78: a rate
  makes it PULSE the trigger a round at a time -- the fuel rod Grunts run 0 and HOLD for the
  burst) and a **burst longer than the charge** (Halo 3's profile bursts 2.6 s for ITS 2.5 s;
  3.6 s here for the balanced 3.33 s). The tap-tracer is lost (no second trigger).
* **Halo 1 CHARGES DURING THE OVERHEAT** (no trigger flag prevents it; only the discharge waits):
  a held laser fires every max(charge, vent) = 2.5 s where Halo 3's cycle is charge + vent 4.75
  s -- the plasma pistol's charged shot overlaps the same way. A vent stretched to the whole
  cycle (boot 19) 'did not feel right': reverted, Halo 3's vent kept (user). h1_role_compare
  models a charged, overheating weapon as max(charge, vent) now.
* **OVERPENETRATION needs a projectile that does not cross its whole range in one tick:** at
  4000 wu/s over 120 wu (all in one 30 Hz tick) Halo 1 never overpenetrated; a test copy at the
  sniper's 1000 did (control: the stock sniper as `--secondary`, `--secondary-rounds`). An
  overpenetrated unit takes the IMPACT only -- the detonation happens where the beam stops -- so
  the impact carries the whole direct hit (570) and the splash serves near misses (Hunters, which
  stop it as Halo 3's 'not against giants', get both).
* **A CONTRAIL's first point is laid after the projectile's FIRST UPDATE:** a fast round's beam
  starts tens of wu out, so from the firing point it shows only side-on (the Sentinel Beam's 'end
  on' look, though the first-person offset was set). The beam starts SLOW and accelerates (60 ->
  1940 wu/s: Halo 1 changes a projectile's speed over its range) -- 2 wu out after one tick.
* **Contrail textures:** every stock contrail texture holds ONE sequence with NO sprites -- a
  contrail naming it with sequence count 1 draws NOTHING (0 = the whole bitmap); stock textures
  are short-bolt patterns, mostly dark along a long beam. Halo 3's beam = a beam PROFILE texture
  palette-mapped (fx\contrails\_bitmaps\beam x fx\particles\_gradients\laser_red_01, additive x
  alpha): baked into one texture (`baked_textures`), drawn additive + a narrower alpha-blended
  body (solid over bright scenery) + a second additive layer (luminance). Layers on one texture
  match; mixed textures did not (the Sentinel's beam texture read orange).
* **POINT PHYSICS WIND:** Halo 1's first-person smoke rides `warm smoke cloud`, which 'uses simple
  wind' -- the vent steam drifted with a30's wind whatever its direction; an own particle copy on
  `vacuum particle` physics (`overheated_effect` `own_particles`, `direction`, `offset`).
* **THE RETICLE: MCC draws the reticle sheet at ~0.5 with BILINEAR sampling** (a test chart of 1 /
  2 / 3 / 4 / 6 px line pairs: 2 px the first to resolve, unevenly) -- a 2 x 2 average, so a 2 px
  line is 1 px at 100 % or 2 px at 50 % by its phase and flickers along a curve: the 'fizzle'.
  Mips, pixel doubling, a registration change and a prefilter did nothing; Halo 3's size (art x0.78,
  overlay x2.1) was crisp but too big (user). The fix: EVERY STROKE AT LEAST 3 SHEET PX
  (`reticle_min_width` -> h1_add_reticle.grow_to: only the thinner strokes, +1 px at 4x
  supersampling, per layer keeping its brightness; ticks and gaps untouched) -- checked in a
  bilinear simulation at three scales and phases before booting. Halo 3 crosshairs can be SEVERAL
  widgets (`reticle_layers`: the laser's inner double circle `spartan_outerring`). A 1 px gap
  between two lines is the limit at Halo 1's size (brightness did not change it).
* **Halo 1's `charge` crosshair type does not draw in MCC** (an own bitmap + `_r` twin, small
  sprites in hud_reticles, whole frames: nothing, three boots). MCC remaps only the stock sheets
  listed in ui\hud\default.hud_globals to their `_r` copies. The charge cue is a MODEL glow
  instead: `glow_points` (a card star at a marker) on an additive chicago whose
  `framebuffer_fade_source` is D out (primary charged) -- confirmed in first person.
* **Halo 1's `tool model` DROPS A TRAILING DIGIT of a material name** when it finds the shader:
  `spartan_laser_decal2` drew with `spartan_laser_decal`'s (the Beam Rifle's `beam_rifle2` too,
  harmless there) -> `material_names`. Decals: an alpha-blended-decal shader_model on a DXT5 map
  (`decals`); `tool bitmaps` skips non-power-of-two maps (now resized up).
* **Battery rounding:** age 0.2 in float32 sums to 0.6000000238 after three shots (HUD 39 %); the
  float just under 0.2 shows 80 / 60 / 40 / 20 / 0 but leaves 0.99999994 after five, and a 6th
  fired ('can fire with partial ammo' off did not stop it) -> AGE MISFIRE: start 0.9999, chance 1.
* Smaller: a trigger's empty-effect slot can be SOUND- or EFFECT-class per trigger (a sound in an
  effect-class slot fails the build); the luminous indicator segments took the Beam Rifle's gem
  recipe; the impact = the rocket explosion's parts small and red (psys tint, own red light, the
  energy flare `flare h stealth cannon`, the grenade-char scorch); `h1_h3_scope` read a widget's
  mirror flags from an animation block's `flags` (fixed: the field before `bitmap`).
* **Armed:** Halo 3's own ai\generic laser entry over the rocket carriers (Flood combat Elite /
  human, WDM 0.4) + Rate Of Fire 0 + burst 3.6 s; `hands` heavy (Grunts full rate, Jackals
  shieldless -- confirmed). WDM rule on the held cycle: 0.28 default / 0.52 balanced.
  `ai_firing_profile` `set` takes shorts now (`0x154=h1`).
* Steps 6-10: 6 n/a (battery); 7 the plasma pistol's heat + battery meters; 8 icon 37, messages
  67/68; 9 no reload, BALANCED SWAP x0.85 (H1 rocket ready 22 x 31/26 over the built 31) --
  missed at close-out, caught by the final step check: a port with no reload still has step 9's
  swap (`anims` in the catalog entry); 10 own sounds (14).
* Not reproduced: the tap-tracer, the HUD charge triangle, Halo 3's bloom, the charge lock during
  the overheat. Tools: `h1_hud_sheet.put_frames` / mips / compaction, `h1_add_reticle` `layers`,
  `grow_to`, `simulate`, `orbit_frames`; `h1_h3_weapon_model` `decals`, `material_names`,
  `glow_points`, `fade_source`, `solid_textures`, `baked_textures`; `h1_pickable_weapons` `triggers`,
  `no_impact_damage`, `clear_response_effects`, contrail `bitmap` / `sequence` / `states` / `extra` /
  `blend`, explosion `drop_particles` / `particle_swaps` / `psys_tint` / `light`;
  `h1_port_test_map --secondary-rounds`.

### Halo 1: the Gravity Hammer, wave A9 (2026-10-10) -- a melee weapon with an area blast

The whole weapon is `ports_h1/gravity_hammer.py`.

* **Step 4a (user): the restored ENERGY SWORD, x1.007 -- BALANCED = DEFAULT in practice.** What
  h3_weapon_values does not print: a swing is TWO damages -- the shared `smash_melee` 80 (no
  radius; the same tag as Halo 3's rocket and flak melee) PLUS the hammer's own
  `gravity_hammer_explosion` 50..160 over 0.75 -> 1.5 wu, acceleration 3.5 -- the explosion set
  off by an ANIMATION EFFECT (FP strike / lunge frame 4, the primary keyframe; third person at
  marker `hammer_detonation`), on every swing, hit or not: 240 a direct swing every 38 fr (1.27
  s). Lunge `crush_melee` 150 + the explosion. No aoe spike on any of the four damage effects.
  Energy = campaign EXTERNAL AGING 0.05 a swing (20; multiplayer 0.0835). Aim 10 / 1.75, 10 / 6.
  The sword (151 vs dash_melee 150, Halo 3's aim) gives x1.007 everywhere; energy has no ratio
  (Halo 3's sword ages per kill). Shown and not picked: the heavy-weapon melee reading (Fuel Rod
  / RL, x0.69 -- Halo 3's hammer smash IS their smash_melee), AR (x0.79), Oddball (x0.53).
  `h1_role_compare.py` melee candidates take `parts` (Halo 1 damage tag, damage[, radius,
  materials]) + `interval` / `aim`.
* **FIRE = Halo 3's head SLAM, not its strike** (boot 1, user): melee_strike_1 / _2 are POMMEL
  JABS (the melee button); the RT attack is the lunge animation (`melee_lunge_unaimed`, 46 fr,
  head down at frame 5) -> a slam that lands is crush_melee 150 + the blast (310 / 1.53 s; the
  sword ratio unchanged). Find the frame by the weapon node's motion (h1_fp_retarget.retarget +
  fp_render.compose), not the graph's key frame.
* **AREA MELEE in Halo 1:** the sword's trigger recipe (make_lunge, `strike`/`push` optional now)
  fires an INVISIBLE strike (own_beam on a copy of the sword's `lunge` projectile) that detonates on
  every material and by a TIMER from launch (0.2 s = the slam's moment, 6 wu/s) into an own
  explosion (own_explosion: damage + knockback, owner and friends spared). Every swing blasts, hit
  or miss. The wielder's push back = the sword shove (firing damage 0.01, POSITIVE acceleration).
* **KNOCKBACK on LIVING units:** 4b's ratio (5.83, the H1 rocket's 6) moved only dead bodies --
  the user tuned 7.5 live (blast) and +5 (shove) in Assembly. The god shield does not stop it.
* **A dropped item rests on its world model's `ground point` MARKER** (found 2026-10-11 in the
  Plasma Repeater session: every stock Halo 1 weapon has one, on a side surface near the balance
  point). The hammer had none: it rested on its ORIGIN with model z vertical and stood / sank --
  boot 3's 'stand like the flag' (`always_maintains_z_up`) was a workaround, now REMOVED: the
  hammer has `ground_point: 'auto'` (h1_h3_weapon_model) and lies on its side. The collision hull
  does not decide it (h1_box_collision.py: no change). Check every port's world model for one.
* **Shockwave without mesh particles:** the Wraith mortar's `light ring expand` (additive, lies
  PERPENDICULAR to its location's direction). On the effect's `gravity` location (straight down) it
  lies flat; the stock particle lives 0.1-0.2 s (unseen) -> an own copy 0.5-0.6 s, drawn x4
  (brighter), three stacked 0.12 wu apart + one upright on location 0 (faces the strike's target).
  Ground hits clip flat rings (accepted). own_explosion `add_particles` (count / offset / delay /
  own `particle` copy) and `drop_classes`.
* **No fire during a melee:** Halo 1 blocks a trigger for only 3/4 of a player melee -> the
  h1-melee-gate session's halo1.dll patch (`h1_melee_blocks_fire.py`, enhancer option on by
  default, opt-in tag bit 31 via `melee_blocks_fire`). Padding the FP melee made it WORSE.
* **ARMED, four traps** (12 Armed tests): (1) h1_enemy_weapons clones the donor's WHOLE actv --
  the sword commander's flags 0x40 'cannot use ranged weapons' rode along: no carrier ever fired
  (every 'slam' was its melee; give the melee its OWN hit sound so tests can tell them apart) ->
  profile `set` '0x0=I0:Flags' (I<int> longs in ai_firing_profile). (2) Halo 1's AI moves between
  firing positions; only a CHARGE closes in: actor flag `always_charge_in_attacking_mode` (the
  Flood shotgun recipe, test-map `--actor-flags`) + berserk firing ranges (actv 0x168 / 0x16C);
  melee range 0x160 / abort 0x164 / berserk 0x170 / 0x174 (found in the tag by value). (3) The AI
  fires from the world model's `primary trigger` marker and judges reach by the projectile's
  MAXIMUM RANGE: the hammer had no markers (its blast went off on the carrier) and range 1.2 ->
  marker = Halo 3's `hammer_detonation`, range 5 (the timer still bursts it at 1.2). (4) The
  label's FIRE animation is the pose donor's recoil -> catalog `fire_anim` 'melee'
  (h1_enemy_weapons.ensure_fire_anim on a PRIVATE copy of the type's list: teach() shares the
  donor's; h1_pickable_weapons.third_person_fire_as_melee for the player). Stand-in swings:
  warn before signal-attack (the Jackal's signal-attack barely moves the weapon hand). Jackals'
  swing is still cut short by knockback (shieldless: every hit pings) -- accepted.
* Tools: `h1_box_collision.py`, `make_icon.py --z-forward`, `h1_add_reticle` `dry` + `split`,
  `h1_fp_retarget` `pad_end`, `h1_pickable_weapons` `melee_fields` / `fire_anim` / hit_sound on
  an own melee copy (it read the donor's backup), `port_refs_audit` takes the entry's `weap`,
  `port_field_audit` an `impact` pair (a second impact damage effect: the slam's crush).
* **Final step check (2026-10-10):** closing 0 refs 0 problems, 2 validate_halo_json 0
  problems, 6 4b (weapon / blast / melee / impact: list 2 only the recorded decisions) + write
  proof 34 tags / 723,618 fields 0 changed, 7 port_sound_refs 0 BORROW + port_sounds --check 0,
  8 Armed carriers built in every test, 9 hit effect x1; 1/3/5 n/a (Halo 1).

### Halo 1: no FIRE during a MELEE (melee weapons, 2026-10-10) -- halo1.dll patch, CONFIRMED

Gravity Hammer boots 8-9: melee (the pommel jab, 38 fr), then fire -> the slam's blast with no
swing (the FP fire waits for the jab); holding the jab's last pose 15 more frames made it WORSE.
The restored sword (lunge on fire) has the same gap. Analysis of `halo1.dll` (rva at image base
0x180000000, MCC build of 2026-06-22) + a LIVE probe (`h1_melee_fire_probe.py`, logs to
`out/melee_fire_probe.jsonl`).

* **The trigger gate.** Weapon tick `+0xB74E6C` reads the weapon's control word (weapon +0x1FA:
  bit 1 primary, bit 2 secondary trigger, bit 3 reload, **0x10 = cannot fire**: both triggers
  forced off). The unit update `+0xAFBE54` builds it from the unit control flags (unit +0x1D8:
  0x80 melee, 0x400 reload, 0x800 / 0x1000 the triggers) and hands it over at `+0xAFD693`
  (setter `+0xB768BC`). 0x10 comes from (a) the unit's animation STATE (+0x283) in the mask at
  `+0xB00F3C` (0x1E melee, 0x21 grenade, ...: the AI's full-body melee -- a PLAYER melee never
  sets it, measured) or (b) **unit +0x512 > 0** (not in a vehicle).
* **The player's melee** is the biped update `+0xBAF258`: on the melee flag with +0x512 == 0 it
  starts the REPLACEMENT animation 'melee' (unit +0x284 = 7), sends the FP melee event, and
  sets the timer **+0x512 = the FP melee's frame count minus a quarter** (+0x513 = when the
  damage lands, `+0xB0C388` at the key frame). The timer counts down a tick at a time; it blocks
  the trigger AND the next melee. So the last quarter of every melee can fire: measured, hammer
  blocked 30 of 36 ticks, sword 19 of 26. Stock weapons have it too (a fire in the recovery).
* **The fix: `h1_melee_blocks_fire.py`** (two 6-/8-byte call sites, 50 bytes of caves in the
  .text slack at `+0x17501CC`, right after the overheat-unzoom cave; --show / --on [--live] /
  --off = --restore; LIVE + FILE as h1_overheat_unzoom, rename swap while MCC runs).
  U `+0xAFD688` (`mov edx,[rbp+0x88]`, the word handed to the weapon): also bit **0x80** while
  unit +0x284 == 7 (the melee replacement animation plays; 0x80 is read nowhere in stock).
  W `+0xB7515A` (`movzx r8d,word [rbx+0x1FA]`, r15 = the weapon tag): 0x80 -> 0x10 when the
  tag has **weapon flags bit 31** (weap +0x308; byte +0x30B mask 0x80 -- only unreleased
  digsite tags use bits 16+, halo1.dll reads none of them). The timer is untouched, so melee
  spam is stock; the trigger waits for the melee ANIMATION's end instead.
* **That animation is the THIRD-person one** (the replacement anim on the cyborg, weapon type
  slot 8). `gh` was taught from the flag: `stand rifle f melee` 32 fr < the jab 38 -> the label
  gets its own `stand rifle gh melee` held to 38 fr (`third_person_melee_as_fp`; the flag's is
  shared with the sprint weapon). The sword's `stand pistol b melee` 28 fr (crouched 46) already
  outlasts the slash (24).
* **Opt-in = port key `'melee_blocks_fire': True`** (gravity_hammer, energy_sword):
  `h1_pickable_weapons.edit_weapon` sets weapon flags bit 31, `teach_cyborg` the 3P melee.
* **CONFIRMED in game 2026-10-10** (live patch, a30): melee then fire -> no slam / lunge until
  the swing ends, both weapons; the probe shows the word at 0x82 with fire held through the
  tail and the trigger going through on the tick the animation ends.
* **Enhancer:** Options -> Patching -> Halo 1 "No firing during a melee: Gravity Hammer, Energy
  Sword (halo1.dll)" (`h1_melee_blocks_fire`, ON by default -- user), synced on every patch like
  the overheat option, in the run's options snapshot (co-op: both machines).

### Halo 1: the DMR, the Reach pilot (wave B1, 2026-10-10, 3 boots + Armed on a30) -- Reach as a SOURCE

The whole weapon is `ports_h1/dmr.py`, on a copy of the Halo 1 SNIPER RIFLE. Wave B's question
was the ROUTE from Reach; the answer is that Reach goes through the SAME pipeline as Halo 3,
behind one path prefix.

**`reach:` paths (reach_tags.py).** A config names an HREK tag as `reach:objects\...`;
h1_fp_retarget.export_xml / rm_defaults / load, h3_rm_to_jms.convert, h3_hud_art.decode /
sheet / sprite and h1_h3_scope.widgets branch on it, and only on it (a path without the prefix
runs the old code: proven byte-identical, below). reach_tags reads HREK's export, which is
FLAT XML -- a block is `<field type="block"/>` followed by its elements as siblings, a struct's
fields follow it as siblings, a block index is the element's NAME, a tag reference is the
BASENAME only (`find_tag`: by name + extension, nearest the referencing tag's folder) -- into
the shapes the Halo 3 readers return. `export-tag-to-xml` needs absolute paths (cwd = the kit).

**Step 4a (user): the SNIPER RIFLE**, not the provisional pistol (`h3_weapon_values.py --kit
reach` + `h1_role_compare.py dmr`). Pistol ratio: every value scales (25 x 2.0/s = 50 dps, 22
rounds, 3x by ratio). Sniper ratio: 22.09 x 4.5/s = 99 dps, 15 / 45 / 75 (= Reach's own), the
spread INVERTS (Reach's sniper minimum 0.08 is near zero) -> the SIBLING RULE in Reach's shape
(user): 0.019 -> 0.25; zoom Reach's 3x in both (ratio 1.5x / 2.4x); bullet materials = the H1
sniper bullet's (user: Elite shields x2, Flood x0.05 -- Flood take ~26 s). Wave rule kept:
default = Reach's own numbers, balanced = the ratio rows. Reach's damage table: bullet_fast
(DMR) = bullet_slow (magnum) on flesh and thin shields, x2 on tough / thick / metal.

**Geometry:** Reach's ONE render model (world and first person; the FP graph moves it) through
h3_rm_to_jms -- no Foundry for a Halo 1 TARGET (Foundry was Reach-as-target's JMS trap). Not
tilted (b_gun root at identity, grip at the origin), `primary_trigger` present. Nodes come out
`frame b gun` etc. Scope GLASS (alpha blend over grey 50% + cubemap) dropped; UNSC stencils a
decal (Reach's alpha); the on-gun counter (ones / tens) = the BR's numeric recipe, limit 15.
**Textures:** every DMR shader has self-illumination OFF (the illum bitmaps they name are not
even in HREK) -> multipurpose R = the diffuse alpha, G 0. reach_tags.decode_bitmap = Halo 3's
method (the largest tgda, DDS header); a8 / dxt / dxn handled.

**FP animations, route (a) (user): Reach's own fp_dmr RETARGETED.** Reach's Spartan arms =
Halo 1's 37 nodes (names, parents, lengths to 0.001) + 10 helpers: pedestal / aim_pitch /
aim_yaw ABOVE base and humerus / radius / handguard twist nodes -- `drop_nodes`; h1_fp_retarget
now walks to the nearest KEPT ancestor (Halo 3's skipped nodes are leaves: unchanged). The
4.3 deg roll on r_hand was NOT corrected (user: 'right hand looks right'). view_offset = the
BR's minus 2.5 cm forward (Reach's arms sit further forward): user 'FP position good'. `look`
(9 fr overlay) = Halo 1's `overlays`. Melee primary keyframe 5. Routes (b) Halo 3 BR motion
and (c) the SAW donor-skeleton route were not needed; (b) stays the fallback for a Reach
weapon with no good graph.

**Sounds:** h1_port_sounds `bank: 'haloreach'` -- Reach's sfx.fsb + .info have Halo 3's
280-byte entries; numbered 1/2/3 and a/b/c files are permutations. Fire = marksman_rifle_fire
+ marksman_tail_ext MIXED (Halo 1 plays one sound a round); targets = the H1 sniper's levels.
**HUD:** Reach's chud (`reach_tags.chud_widgets`): zoom = the `zoom lvl N` conditions of a
widget / its collection, the FULLSCREEN placement = the element with no window state, and
Reach's 4K art is 'double / triple sized' (`more flags`: 2-3 px a chud unit) -> `px_per_unit`
in the bake, and sprites (reticles) come at Halo 3's density. SIZE (user, test 1 'shrink to
mirror the original'): Reach's 1152x640 HUD canvas = its 90% SAFE AREA of 1280x720 -> span /
0.9, the ring at 69% of the screen height (an OBSERVATION; Halo 3's scopes were read as full
screen and approved). The magnification ARC (scale 0, animated) at scale 1 and its SLIDER
static at 3.0x (user: 'as a static picture'). Reticle = Reach's circle (#14) at 28; the
`reticle_min_width` simulation showed it unbroken.
**The sniper template's HUD is not the pistol's** (4b template diff, before boot 1): its zoom
overlays are AIM-typed crosshairs with zoom-only overlays, its reticle draws from its OWN
sheet, `dont_scale_size` set, zoom angle ticks on `age`, distance / elevation numbers ->
make_hud opt-ins `drop_crosshairs`, `reticle_bitmap`, `reticle_scaling`, `drop_elements`.
The sniper trigger's `use error when unzoomed` cleared (Reach's DMR blooms zoomed); the
sniper's `aim assists only when zoomed` + night vision cleared (Reach's DMR has neither).
**Muzzle flash (test 1, now closing check 10):** the sniper's two sideways brake fans -> the
BR port's pistol sprites + casing (`copy_from`), Reach's at-the-bore flash.
**Step 6 (user):** Reach's DMR has no pickup count (ammo box 0) -> the YARDSTICK's pickup :
initial ratio (16 : 12) on 45 = 60.
**Step 9:** ONE reload multiplier for both reloads in the patcher (empty x1.094 and full
x1.153 wanted) -> x1.12 (user: keep); swap x1.38 (the H1 sniper's ready).
**Step 11:** donor = the Flood combat Elite sniper (WDM 0.4; flags harmless) for every slot;
WDM rule 1.54 / 0.81 -- the FIRST WDM above 1.0 (the DMR does a quarter of the sniper's dps),
applied as is (user). hands 'two' (enhancer).

**Proof (the pilot's job):** `port_sha_snapshot.py` -- snap, regen (the wave-A --write chain:
model -> retarget + tool animations -> sounds -> pickable, every non-Reach config), snap, diff.
Old tools vs generalized tools: 10,474 files, 0 changed (80 bitmap headers: `tool bitmaps`'
pointer noise, pixels identical). FINDING: the chain does NOT reproduce 12 tested files byte
for byte (FP animation tags, the SMG / Sentinel Beam gbxmodels, three sounds): content-equal
where checked (the sword's tag: every animation, key and sound identical), so they are tag
noise -- but a regen run must restore from backup to leave the tested kit exact.

### Halo 1: the supercombine count PER PROJECTILE (Needle Rifle, wave B2, 2026-10-10) -- halo1.dll patch, CONFIRMED 2026-10-11

Halo 2 on carry `Super Detonation Projectile Count` in the projectile tag; Halo 1 hardcodes 7
(the Needle Rifle wants Reach's 3, the stock needler keeps 7). Tool: `h1_supercombine_count.py`,
enhancer Options -> Patching -> Halo 1 "Supercombine needle count per projectile (halo1.dll)"
(`h1_supercombine_count`, OFF by default). CONFIRMED in game 2026-10-11 (a30): needler at 7 and
Needle Rifle at 3 in one level, and both supercombining on the player with `h1_supercombine_players`
(Armed copy, rifle count written into the map, god shield).

**Where the 7 lives.** Every read of proj flag bit 3 (`has super combining explosion`,
proj +0x17C, `test byte [reg+0x17C], 8`) leads to a loop over the PARENT object's attached
children (object +0xD0 = next sibling) counting the ones with the SAME tag index and without
object +0x1F8 bit 6 (already spent). The count is compared with the constant 6 (= six OTHERS,
or seven including the detonating one) at four places:

| rva (base 0x180000000) | stock | proj tag in | role |
|---|---|---|---|
| +0xBC72C5 | `cmp r8w,6 / jge` | rdi | attach (fn +0xBC7158): -> `bts [new proj +0x1F8],7` |
| +0xBC8442 | `cmp r10w,6 / jge` | r13 | attach on impact (projectile update): same bit 7 |
| +0xBC8EC4 | `cmp r8w,6 / jle` | rsi | detonation: >= 7 -> super_detonation (proj +0x198) |
| +0xBC8F4C | `cmp r8w,6 / jg` | rsi | detonation, per-sibling loop (zero timers vs bit 6) |

So the count is "needles of THIS tag stuck in THIS object", and the needler's 7 and another
projectile's N never mix (stock already keeps `needle` and `mp_needle` apart).

**The per-projectile field: proj +0x1F2, int16** = the HEK `pad(2)` after `detonation noise`
(Assembly Halo1MCC: hidden int16 `Unknown`). Zero in all 772 proj tags of the 29 Halo 1 maps in
halo1\maps (2026-10-10, ports included); nothing in halo1.dll reads +0x1F2. Semantics as Halo 2+:
TOTAL needles; 0 or less = the engine's 7, so with the patch on and nothing set the game is stock.
1 combines on the detonation path only (the attach loop needs a sibling) -- keep the card's
Halo 1 minimum at 2.

**Where the count comes from, NOT the tag file.** The field is a pad: reclaimer writes pads as
zero on save and tool's handling of pad bytes is untested, so do not put it in the loose tag.
Write it into the BUILT map (or at patch time): `h1_supercombine_count.map_count(HaloMap, proj,
n)` / `--map <file.map> --count <proj> <n>`. The enhancer rebuilds every patch from the
baseline, so a patch-time write (port catalog value, then the card on top) is the robust home.

**The patch.** Each 5-byte `cmp R,6` becomes `call cave`; a cave (20-21 bytes) is
`movsx eax, word [T+0x1F2] ; dec eax ; jns +4 ; mov ax,6 ; cmp R, ax ; ret` (flags survive the
ret, the stock jcc after the call is untouched). eax is dead at all four sites (written before
any read on every path), and the caves touch no stack, so they need no unwind data. The .text
section slack is FULL (overheat + melee caves), so the caves sit in int3 PADDING between
functions -- the first time: no int3 run in halo1.dll's .text is longer than 21 bytes (237 runs
>= 16, 17 of exactly 21). Picked: +0x139561B (rdi/r8w), +0x139576B (r13/r10w), +0x1397BAB
(rsi/r8w, shared by both detonation sites) -- each right after a `ret`, outside every .pdata
range and relocation, never a jump target. Verified offline: on -> disassembles as above,
off -> byte-identical to the stock dll, and it coexists with the overheat / melee patches.
The NEXT halo1.dll cave: 14 more 21-byte int3 runs remain (+0x1391621 .. +0x139B09B); vet
each the same way (prev byte C3 = after a ret, no .pdata cover, no reloc, not a jump target),
or chain shorter runs with a jmp.

**The PLAYER is never supercombined in campaign -- engine rule, MEASURED 2026-10-11.** The
detonation (+0xBC8E7A..+0xBC8EBE) gates on the stuck-in object before the count: word +0x70
must be 0, and if dword +0x1F8 is not -1 the game-engine pointer (qword +0x2E9F820, set by
game_engine_new +0xA9E3B0, NULL in campaign) must be set. `h1_supercombine_test.cmd gates`
on a loaded campaign level: every AI biped +0x1F8 = -1, the player's = 0xEC700000 (a player
handle, index 0) -- so +0x1F8 is the unit's player, and players are immune in campaign (in
multiplayer they are not). Stock needler included; the god shield plays no part (no count code
reads shields). LIFTED by option `h1_supercombine_players` (2026-10-11, user: test it):
`h1_supercombine_count.sync_players` / `h1_supercombine_test.cmd players on|off`, ONE byte --
+0xBC8EB5 `74 0D` (je to the count when +0x1F8 == -1) -> `EB 0D` (always), so every unit goes
on to the count; the attach path needs nothing (needles already stick to players). Test: god
shield on, let enemies with needlers / Needle Rifles stick 7 / 3 needles in you -> the
supercombine bursts on you (shield drop, the explosion effect).

**Live tag access (test helper).** halo1.dll's tag_get +0xA9B648: tag array = qword
[+0x1C34FB0] (32-byte entries: class, id +0xC, name +0x10, data +0x14), a tag pointer p is at
p - [+0x2EA3410] + [+0x2D9CE10] (the index header there: tag count +0xC). Tag data is loaded
once per level -- `--count <proj> <n>` changes a projectile's count in the running game.

**Test plan (one boot, any level with Elites and a needler, e.g. a30 / b30):** patch on (Options
tick + patch, or `h1_supercombine_test.cmd on`). (1) stock count: stick needles into one Elite
-- 6 do not combine, the 7th does. (2) `h1_supercombine_test.cmd 3` while in game: the 3rd
needle combines. (3) `h1_supercombine_test.cmd 0`: back to 7.
A 3-to-7 change in one boot proves the engine reads the projectile's own count; (1) proves 0 =
stock. Per weapon at once (needler 7 beside a port at 3) follows with the Needle Rifle's first
boot. If (2) still needs 7: the counts are not read where shown -- re-probe live before a second
boot.

### Halo 1: when the Grunt Birthday Party skull fires (Needle Rifle, 2026-10-11) -- research + live probe

User, boot 7 (a30): the port's needle headshots Grunts (jpt `can cause headshots`, like
`weapons\pistol\bullet`) but Birthday Party never fires; the pistol's does. rvas at image base
0x180000000, halo1.dll of 2026-06-22.

**RESOLVED, no needle bug (user, 2026-10-11):** the pistol report was an assumption. In CLASSIC
graphics, which every test uses (Anniversary graphics break the modded maps), the confetti is
not seen with the pistol either. What the skull spawns, `sfx_konfetti`, is an ANNIVERSARY
effect: it is defined only in `halo1\prebuild\paks\initial_ps.s3dpak`, not in any map. The
candidates and the probe below are kept for reference.

**CONFIRMED in game 2026-10-11 (a30, classic, pistol headshots: a small needle burst on the
Grunt) after a second route.** The first build (below) never fired in classic graphics. The
probe showed why: value 2 reached the skull test, but MCC's object-record lookup (`"id%x"`,
+0x2B3140) returns 0 in classic graphics (that list is the Anniversary mirror), so MCC leaves
at +0x803E2, before the name test and before +0x80444. Route 2 hooks the lookup result at
**+0x803DC** (`mov r14,rax ; test rax,rax` -> `call KA`). On a hit (Anniversary graphics) it
replays both instructions and returns to the stock path. On a miss it looks the effect's
object up with mask -1 (object_get +0xB389A4, which returns &object.tag), compares that tag
with `tag_loaded('bipd', 'characters\grunt\grunt')` (name at +0x1B745E0 in the .rdata slack),
then spawns the effect through route 1's C2/C3. Every miss leaves through C3's tail (+0x139A055:
`add rsp,0x28 ; xor r9d,r9d` -> ZF=1, so the stock `je` skips MCC's confetti code) and `ret`.
Caves: KA +0x1391621 (21), KB +0x1393D00 (16), KC +0x1394B8F (17), KD +0x13978BF (17),
KE +0x139689C (20), KF +0x1394990 (16), all unreferenced. More free int3 runs of 16-20 bytes
remain (+0x1393CBE, +0x1394AEE, +0x13952DC, +0x139537C, +0x1396A2C ...; scan in this section's
history). The effect is small: a bigger or real confetti effect only needs `--effect`, plus
its tag in the maps.

**The classic confetti (2026-10-11, untested in game): `effects\grunt birthday party.effect`**,
written by `h1_confetti_effect.py --write` into HCEEK\tags; the dll's preferred slot already
names it, so no dll change (since 3e50a85 it is the ONLY Birthday Party effect: vanilla
maps play nothing). v2 (same day), after in-game tests: on a dead Grunt at the object origin
the small spark effects (`charged bolt sparks`, `impact c shield`) showed NOTHING and `needle
detonate` only a tiny burst, while `weapons\plasma grenade\effects\explosion` DID show. So the
container is that explosion, with v3 (user, same day) removing EVERY part but its light (no
plasma fireball, no damage, no decal; the light an own warm copy = the flash). Event 0, the
LAUNCH: confetti and pink needle debris straight up (cone 0.35, 3-4.5 wu/s) from the origin +
0.3 wu, the needler's pop and the Grunt's own `celebration` line (unit_dialog, 14 permutations:
the dead Grunt cheers). Event 1, 0.3 s later, the AIR BURST at the origin + 1.2 wu (~3.6 m):
confetti in six colours and green / blue sparks in every direction, raining down. Confetti = an
own particle `effects\particles\solid\confetti` (a copy of `debris shirt`: a near-white
fluttering cloth sprite on light wind-damped point physics, so the tint gives clean colours;
4-6 s, fades over the last second, not killed at rest).
**The original cannot be copied** (checked 2026-10-11): `initial_ps.s3dpak` is 71 zlib chunks
(u32 count + u32 offsets); decompressed, `sfx_konfetti` is a Saber3D TEXT definition (an
`sfx_entity` playing `sfx_konfett` + `sfx_expl_flash_02` x0.5; `surface` emitters on
`sfx_source_ak`, `dir y+`, speedNorm 2, life 6 s, size 0.5, texture `konfetti_16x1` = a 4x4
animated sprite sheet, CDT friction 15 = pieces settle) drawn only by the Anniversary renderer
with a Saber `sfx` material. Classic reads Blam tags only, and there is no converter. Its numbers are mirrored
above; the texture's pixels were not found in a readable pak (porting its look would mean
extracting it and authoring an H1 sprite bitmap).
**How it gets into the maps:** a NEVER-CALLED static script at the end of sprint.hsc,
`gbp_confetti_ref` (`effect_new_on_object_marker "effects\grunt birthday party" (player0) ""`).
install_script puts sprint.hsc into data\global_scripts.hsc, which tool compiles into every
level, and the script compiler adds the tag to each scenario's references. That's the same
route the ability effects (`ab_fx0`) take, and no gameplay reference is touched.
`h1_rebuild_all.py` prints `confetti yes/no` per level. Unrebuilt maps play nothing.

**Built (opt-in, 2026-10-11): `h1_birthday_party.py`, route 1.** Enhancer option
`h1_birthday_party` (Options -> Patching -> Halo 1, off by default); `h1_birthday_party_test.cmd
on|show|off` for the user. Where the confetti code starts (+0x80444, reached only on a real
Birthday Party), a call into three chained 21-byte int3 caves (+0x1397EFB, +0x139865B,
+0x139A04B) does `tag_loaded('effe', NAME)` (+0xA9B35C) and the engine's effect-on-object
call (+0xBA1078, the one unit death uses) on the dead Grunt (r13d). NAME is in the .rdata
slack at +0x1B74520 (VirtualSize ends at +0x1B7451A; the slack is mapped, checked live).
Default effect: `weapons\needler\effects\needle detonate` (all ten campaign maps, no damage
parts); `--effect <path>` names another, and a path a level lacks spawns nothing. A real
confetti effect only needs its tag in the maps. The nested effect re-enters MCC's effect hook
with the head value already reset, so the skull code does not run twice.
**Test (a30, Birthday Party skull ON, classic graphics):** `h1_birthday_party_test.cmd on` in
game, headshot a Grunt with the pistol -> the needle burst + pop on the Grunt; a body-shot kill
-> nothing; skull off -> nothing. A crash at a Grunt headshot means the nested effect call is
not safe there (then: defer the spawn to the end of the effect call instead).

**The condition, three pieces (all in halo1.dll, nothing in any tag but the data they read):**
1. **Flavour index 11.** `debug_ice_cream_flavor_status_grunt_birthday_party` is the byte
   +0x1C421C3 = flavor(11) (base +0x1C421B8; the debug-global table at +0x1B89E80 names every
   flavour's byte -- the authoritative name->index map). Its ONLY consumer: `mov ecx,0xB; call
   flavor` at **+0x8039E**.
2. **The killing damage records WHERE it hit.** object damage (+0xB9EA28, args: node index
   r8w, region r9w, material 5th) looks the hit **collision node** up in the victim's coll tag
   (`coll +0x28C Nodes`, 64-byte elements) and keeps the node's **+0x32 word** (Assembly:
   `Unknown Name`; a body-part class). Grunt: 2 = `bip01 neck` + `bip01 head`; 0 pelvis/spine,
   1 spine1, 3/4 left arm, 6 left leg, 7/8 right arm, 10 right leg. No valid node -> -1.
   When that damage KILLS (flag bit 0 after unit kill +0xB9D9E0) and has a causer (damage data
   +0xC != -1), +0xBA07F4 stores the word in the global **+0x1B7BA7C** (`mov [g],eax` at
   **+0xBA0CCA**; its only writer).
3. **The next EFFECT consumes it.** +0x7FB20 is MCC's effect hook: every effect_new reaches it
   through +0xAB2040 (effect tag valid, 1-32 locations) with the effect's OBJECT (edx). It reads
   the global and **resets it to -1 at entry** (+0x7FB9C/+0x7FBA5), maps the effect tag path to
   an Anniversary effect name (table from `hcex_effect_names.ps`, qword +0x2B04F68 / count
   +0x2B04F70; paths not in it get a built `sfx_wpn_...` name) and **returns before the skull
   test if that name is EMPTY** (+0x7FF2A). Then: flavour 11 on AND value == 2 AND the effect's
   object exists AND MCC's object record (`"id%x"`, +0x2B3140) is named exactly `grunt` AND it
   has not celebrated yet (list +0x2B05050) -> `sfx_konfetti` + `skull_laugh` at the effect.
So: **Birthday Party = a HEAD-node kill whose very next effect sits on the dead Grunt** (in
practice the projectile's flesh impact effect, `weapons\...\effects\impact grunt`, created on
the hit object by +0xBC8638 right after the impact damage at +0xBC7AE2).

**Why the needle should NOT differ, and what is left.** Read statically, the bullet and the
needle take the same route: same impact-damage call (node = collision result +0x3E), the same
`impact grunt` response effect for material 11 on the hit object (the needle's is
`weapons\needler\effects\impact grunt`, ATTACH; the bullet's `weapons\pistol\...`, response 0),
nothing that creates an effect between the kill and that response effect (checked
transitively, 4 call levels deep from the hook: +0xBA07F4 after the write, +0xB9EA28's tail, +0xBC7880 up to +0xBC82A9), and the
attach code (+0xBC8317..) runs only after the effects. The headshot itself (+0xB9FD65) is a
different test -- coll MATERIAL `head` flag + jpt flag bit 1 -- so "headshots work" does not by
itself prove the node word was 2. Remaining candidates, in order of how cheaply they are told
apart:
  (b) `hcex_effect_names.ps` maps `weapons\needler\effects\impact grunt` to an EMPTY name: the
      hook consumes the 2 and leaves before the test. The table only exists in a loaded level
      (it is inside the Anniversary paks, not plain on disk) -- `h1_gbp_probe.cmd table`.
  (c) another effect lands between the kill and the impact effect (not visible statically).
  (a) the needle's kill reports a non-head node (value != 2).
  (d) the Grunt is not killed by the impact damage (no KILL record at all).

**The probe: `sprint_toolkit/h1_gbp_probe.py` / `h1_gbp_probe.cmd`** (live only, never the
file; jumps at five sites into a cave allocated within 2 GB of halo1.dll, the hooked
instructions replayed, so behaviour is unchanged): logs KILL (value, victim, model), IMPACT
(node, hit object, projectile), EFFECT (value consumed, object, effect name), GBP? (skull on and
tested) and GBP! (confetti). `dump` prints every kill with the effect that consumed it and
appends to `reports/gbp_probe.jsonl`; `table` reads the effect-name table (read-only).

**One-boot test (a30, Birthday Party ON, god shield as usual).** At the first Grunts:
`h1_gbp_probe.cmd table` -> `on`; then (1) pistol headshot a Grunt (confetti expected),
(2) Needle Rifle headshot a Grunt, (3) Needle Rifle body shot until it dies, (4) stock needler
kill; `h1_gbp_probe.cmd dump`, then `off`. Each outcome decides the fix:
  * (b) table shows `...needler\effects\impact grunt -> ''` and the needle's KILL 2 is consumed
    by that effect -> **tag-side fix**: give the port's material-11 (Grunt) response its OWN
    effect (a copy of the needler's under `weapons\needle rifle\effects\impact grunt`, which is
    not in the table and so gets a non-empty built name), or reuse the pistol's `impact grunt`.
    One boot confirms. (Check the Anniversary-graphics look of a path outside the table.)
  * (c) the dump names the intervening effect -> move/remove it on the port, or the dll fix.
  * (a) value != 2 with node 9/12 in IMPACT -> the needle hits a non-head node; check the
    IMPACT node against the Grunt node list above.
  * (d) no KILL -> the needle's kill comes from another damage (detonation): the dll fix.
  * dll fix (only if the tag route cannot): consume the head value only when the effect's object
    is the KILLED object and only at the skull test (+0x803B0), not at hook entry -- a cave in
    int3 padding (.text slack is full, see the supercombine count), option
    `h1_gbp_any_effect`, cmd/.cmd for the user. Not built: the probe decides whether it is needed.

### Halo 1: the Needle Rifle, wave B2 (2026-10-10/11, 9 boots on a30) -- a stuck needle, its own supercombine, a Reach scope with coloured glyphs

The whole weapon is `ports_h1/needle_rifle.py`, on a copy of the Halo 1 NEEDLER (the yardstick,
the user's pick at 4a: the needle family, Reach's `needle` damage group = Halo 1's needle
materials) and fired like a precision weapon (Reach's latch trigger, a straight unguided needle,
2x zoom). The Reach route is the DMR's unchanged (`reach:` paths, Reach's bank, route (a) with the
DMR's drop_nodes / view_offset -- the FP placement was right at boot 1).

**The supercombine (step 4a).** A Halo 1 projectile names its OWN `super_detonation` effect (the
needle: `weapons\needler\effects\explosion`, damage part `explosion`); only the needle COUNT is
the engine's (7, c20). The port carries own copies (`bullet.super_explosion`, h1_pickable_weapons:
`own_explosion(..., slot='super')`): Reach's attached 350 + area 40 = ONE damage 45 -> 390 over
Reach's radius 0.375-1.25 (default), the needler's 60 (balanced rows). TRAP: a Halo 1 needle bursts
0.75 s after it sticks -- at 4/s seven needles never coexist; the attached life must be >= (7 - 1) /
rate: Reach's 4 s (default), 0.75 x 6/2 shot intervals = 2.25 s (balanced, a 'Timer' row).
h1_role_compare models it (`super` (count, tag, damage), `timer` window, `delay` for the needler's
burst damage). Per-weapon counts: the dll session's `h1_supercombine_count` (built 6dd397a,
untested). **Halo 1 campaign never supercombines the PLAYER** (engine gate on unit +0x1F8 at
+0xBC8E7A..+0xBC8EBE, null game engine = campaign; live read 2026-10-11) -- not a port defect.

**Needle behaviour.** Damage ON IMPACT (Reach) on the needle's materials, `attached detonation
damage` cleared, guidance 0, minimum velocity 9 (Reach; the needler's 2 slipped through 4b once).
Material responses = REACH's TABLE per Halo 1 material (default: sticks to bodies; soft ground
bounce 0-30 else detonate; stone 0-75 / thick metal 0-85 at chance 0.9 else fizzle; glass passes):
`reflect` takes a LIST of angle groups, skip = 1 - chance. The bounce IS Reach's (user checked);
it read 'out of proportion' only because of the TRAIL (below). BALANCED bounce by the ratio
rule (H1 needler x Reach NR / Reach needler): soft ground none (the needler sticks there), thin
metal 19.1 deg, stone 25, thick metal 35, frictions 0.3 -- PER-ELEMENT catalog rows (block
'Material Responses' + `index`; halo_patch apply_field passes it; verified in the built map).
**Headshots:** Halo 1's jpt flag 'causes headshots' (+ 'multiplayer'); Halo 3 / Reach 'can cause
headshots' on the damage effect (+ the model's headshotable regions from Halo 2 on). Reach's needle
rifle has it, its needler not -> set. (The DMR config's note 'no Halo 1 jpt flag' is wrong; the DMR
has the flag from the sniper bullet.) Grunt Birthday Party: NOT a port issue -- its confetti
(`sfx_konfetti`) is Anniversary-graphics only and never shows in classic graphics with any weapon
(the earlier 'pistol works' was an assumption); a classic effect = the opt-in dll option
`h1_birthday_party` (the birthday-party session's section above, untested).

**The trail (boot 1-4).** The needler's needle brought a LIGHT-VOLUME widget (turns with a stuck
needle's surface -- the Brute Shot's trap again: `drop_widgets`) and a contrail at 30 points/s (one
every 50 wu at 1500 wu/s: invisible). The sniper's trail (`attachments_from` + `contrail`) from the
FP muzzle (`first_person_offset` = the FP primary_trigger in the idle pose, the DMR's method
reproduced exactly), additive, Reach's own PROFILE from projectile.contrail_system (ManagedBlam:
lifespan 0.15 s, 0.03 -> 0.01 wu, pink -> violet) -- the sniper's ~1.4 s / 0.087 wu streak made
every ricochet look huge. Read the source contrail's lifespan / size before borrowing a trail.

**On-gun look.** Reach meter shaders read: the screens' UVs land on `plasma_launcher_holo`'s
ring ICONS (not the ring gauge its illum map holds -- check where the UVs land on EACH map), a
shape with no gradient; every weapon OUT reads 0 until the first shot (the needler's 'needles
remaining' and an added constant alike) -> `meters` `static`: the colour baked, an additive chicago
(the needler's luminous) -- always lit. `shape` 'r' when a Reach map keeps the shape in one channel.
The blue indicator halogram = the same lit shape at the meter's OFF level the user approved.
**Draining needles:** Reach's `ammunition_needles` (a REPLACEMENT on 12 needle nodes, spent = SCALE
0.01) = Halo 1's `first-person ammunition` OVERLAY (the needler's; last frame = full = zero delta):
h1_fp_retarget `replacement_overlays` (reference = the full frame, node scale carried) -- Halo 1
plays node SCALE in an overlay (confirmed in game).

**HUD.** Reticle = Reach's ONE arc sprite on four widgets (h1_add_reticle per-layer `xform`:
offset / flip / rotate). Ammo meter = `ammo_meter` sizes (21, 18) + balanced rows (the needler's
20-tick meter showed 18/20 full). SCOPE SIZE FROM A SOURCE SCREENSHOT (user: 'a recurring problem,
make it part of zoom porting'): `h1_h3_scope.py <chud> --port <key> --fit W,H` (the lens px at
1080p) solves span / aspect -- Reach's lens here 865 x 590 = 55% of the height (the DMR's '90% safe
area' gave 1.27x too big). COLOURED scope glyphs (a mask only darkens): `zoom_glyphs` -- a ZOOM
crosshair whose sequence holds an EMPTY sprite 0 and the glyph as sprite 1 (Halo 1 draws sprite N
at zoom level N; an aim crosshair with 'show only when zoomed' overlays drew nothing), at reserved
hud_reticles 44 / 45 (put_frames, + _r), overlay colour WITH an alpha byte, the sprite = Reach's
faint alpha normalized ^1.6 in RGB + A (MCC drew any non-zero texel near-opaque), size / place
measured on the source screenshot then nudged onto the mask's cutouts (memory
h1-coloured-scope-glyphs). `--balanced` boots now exercise per-element rows too.

**Step 11.** Donor = the Elite minor needler (user; carriers 0.4 / 0.5 / 0.6, no actor flags),
Reach's profile (3.875/s bursts), WDM rule as is 2.08 / 1.50 (user, aware a default supercombine
x 2.08 one-shots -- but the player cannot be supercombined in campaign anyway). Grunts 1.94/s (the
two-handed half: actv 0x78 = trigger pulls per second, so x0.5 is slower), Jackals shieldless.

**Proof:** port_sha_snapshot, twice (reach_tags / pickable super + swaps + reticle_xform; then
model meters / retarget replacement / pickable glyphs + reflect list / scope fit): old vs new tools
0 changed of 10,637 / 10,806 files (bitmap headers only; one FP antr content-equal), h1_add_reticle
12 reticles identical, the kit restored exactly both times. Now TOOLS: `port_tool_proof.py --rev
<old> --tools ... --backup ... --tag ...` (the whole proof in one run), `h1_reticle_proof.py` (a
reticle-tool change, dry), `reach_function_data.py` (Blender: every function-data value of an HREK
tag -- shader colours / intensities, contrail profiles).
**Close-out re-check (user: 'check every step, especially 4b'):** 4b's material lines against
Reach's table found Reach's DEFAULT bounce frictions 0 / 0 (the terrain's 0.7 had been copied),
terrain / thick-metal noise 4 deg, and the template's glass glance (now skip 1); step 9's balanced
SWAP had been computed in a comment and never written (x1.05). Read lists 4/5 line by line against
the SOURCE table, not just list 2.

### Halo 1: the Plasma Repeater, wave B3 (2026-10-11/12, 8 boots + Armed on a30) -- heat that slows the gun, an overheat for a vent, a gauge that fills AND recolours

The whole weapon is `ports_h1/plasma_repeater.py`, on a copy of the Halo 1 PLASMA RIFLE (the
yardstick and template, the user's pick at 4a: heat + battery HUD, gauge, bolt, overheat states).
The Reach route is the DMR's / Needle Rifle's unchanged (FP placement right at boot 1).

**Where Reach's heat lives (step 4a).** NOT in the trigger fields (heat per round 0, loss 0.033):
in the weapon's FUNCTIONS (ManagedBlam `TagValueCustomFunctionEditor.Evaluate` + tool.exe's
tooltips): 0.03 heat a TICK while firing; rate = 15 + (3 - 15) x heat^1.5; it never overheats;
passive loss 0.25 -> 0.06/s by the heat_loss function (the 0.0333 field overridden); the manual
vent 2.5 s. **Approximation B (user):** OVERHEAT stands in for the vent; the rate decline follows
the heat -- Halo 1 ramps the rate over the HELD time, so the ramp is fitted to reach each heat's
rate when Reach would. What it lacks: venting part-way, firing on at 3/s while hot, Reach's slow
passive cooling.

**The Halo 1 trigger, MEASURED** (`h1_weapon_state_probe.py`, live, read-only, follows every held
or dropped weapon; values to reports\*.jsonl): per tick rate/30 is added; a shot when the sum
REACHES 1, then the sum RESETS to 0 (no carry) -> a rate a hair under 15 fires every 3 ticks (10/s),
exactly 3/s every 11 ticks (2.7/s). Heat (weapon +0x204) COOLS WHILE FIRING at the one loss.
Overheated = weapon +0x1F8 bit 0; leaving it needs heat BELOW the recovery threshold (0 never
exits: recovery 0.01). The template's AGE penalties (rate -20 %, heat +20 % at an empty battery)
kept it from ever overheating (Reach: 0 / 0 -> 0). Fit (h1_role_compare `heat_model`, `h1_ticks`):
DEFAULT start 20 (six shots every 2 ticks = 15/s), ramp 1.35 s to 3.05, decel 2.5, heat 0.12 a
round, loss 0.4 -> overheat on the 12th round at 1.03 s (Reach 12 / 1.0 s); BALANCED floor 3.4,
ramp 2.6, decel 2.9, heat 0.077, loss 1/2.9 -> 22 rounds / 1.97 s (Reach x the ratio 1.95 s).
Measured dps: default ~21.8 sustained (sim 23), balanced ~37.5 (sim 40); balanced overheat ~20
rounds in 1.55 s, vent 2.87 s.

**THE RUNTIME-RATE TRAP (every Halo 1 weapon):** the engine ramps by the trigger's RUNTIME 'Rate Of
Fire Acceleration / Deceleration Rate' (+0xF8 / +0xFC) = 1 / (time x 30), computed at MAP BUILD.
A balance row on Acceleration / Deceleration Time alone changes nothing (boot 7: the balanced gun
kept the default ramp and never overheated). The repeater's balanced rows write both; since
8b0c984 the enhancer's `halo_patch.sync_h1_trigger_rates` re-derives the rates from the times on
every Halo 1 patch (time 0 -> 1.0), so it is one rule for every weapon (user) -- the repeater is
the only port whose ramp was hand-fitted.

**The vent.** Reach's vent_enter / vent_loop / vent_exit = Halo 1's overheating / overheated /
o-h-exit; Halo 1 plays `overheated` ONCE -> h1_fp_retarget `repeat` (vent_loop x3 = 3 s; the
states run 3.7 s against the 2.5 s vent, as the stock plasma rifle's 3.6 / 2.5). Sounds: the
vent_enter cue + the manual vent's `in` mixed, the vent loop, the exit.

**DROPPED PORTS SANK -- SOLVED: the `ground point` marker.** Every stock Halo 1 weapon world
model has ONE `ground point` (on its side surface near the balance point, stored rotation 0.707,
0.707, 0, 0: its axis INTO the gun); a dropped item rests on it. Ports had none and rested on the
origin. Pathfinding spheres, the hull and the bounding radius had NO effect (tested). Now
`h1_h3_weapon_model` `'ground_point': 'auto'` places it (replacing an existing one; computed in the
node-0 frame, right for re-rooted models) and ALL ports carry it (smg, battle rifle, carbine, DMR,
needle rifle, beam rifle, brute shot, mauler, spiker, spartan laser, sentinel beam, gravity hammer
-- the hammer's forced z-up flag REMOVED, user); the SAW's is fitted in saw_to_jms.py. Reaches
the shipped maps with the batched rebuild.

**The heat lights (on-gun).** Reach's gauge FILLS with heat and the whole fill turns teal ->
yellow -> red; the lower display lights recolour. What failed: a change colour (Halo 1's = a
creation colour x a BRIGHTNESS: black), a meter's `gradient` SOURCE and its `flash` colour (no
effect: a meter colours lit texels by PLACE), a v-axis 'fill' lookup (no stock shader slides v by
a function). What works:
- DISPLAY (the lower lights; the user's BACKUP recipe, 'remember this setup'): an additive lit
  shape (the Needle Rifle's `static` chicago, white) x a colour RAMP sampled at one point (uv scale
  0.001, clamped) slid by an out (`meters` `ramp` + `ramp_source`: the map's u-animation source).
- GAUGE: the meter FILL (value = A out, `gradient_range` 0.02..0.95 -- Reach's alpha gradient is 0
  over its left half, lit half from cold -- lit WHITE, unlit = Reach's meter_color_off at half) +
  a copy of the gauge lifted 0.1 JMS units (`glow_cards`) with a MULTIPLY chicago (`tint`): the
  ramp ADDED to the inverted shape -> x1 outside the outline, x the heat colour inside.
- HOLD THE COLOUR THROUGH THE VENT: A out = heat + overheated (pickable `fields`: C in =
  overheated; function 0 'one' x A in + C in).
Every Halo 1 weapon out reads 0 until the first shot except B out (heat floored at 0.1, live from
spawn).

**Look and sound.** Reach's two staggered muzzles = the plasma rifle's two firing effects
(`primary trigger1` / `primary trigger`; h3_rm_to_jms names list entries per instance;
`sound_effects` '<field>@n' keys). Muzzle flash: the plasma rifle's vertical +-120 deg pair
dropped (`drop_off_axis` 0.012). Pilot flame = island glow. Own impact sound (user): every response
effect that plays plasmahit -> a copy playing rp_impact (`impact_tint` `sounds`, no particle
match); the hit-effect rule at 15/s. Reticle: Reach's faint ring (#3, four quarters at gain 0.5)
+ four wedges (#33 rotated +-45 / +-135 at +-17.3, k 0.56) -- h1_add_reticle `flip_y`, per-layer
`gain`, any-angle `rotate`; MCC's grow threshold 96 erased Reach's alpha-85 sprite until
`reticle_split` 1 + gain; overlay x1.5 (user: x1.15 then +30 %).

**Materials (user):** DEFAULT = the H1 plasma rifle bolt's table; BALANCED = that table x Reach's
plasma_fast / plasma_slow per armour class (h1_role_compare RP_FAST_SLOW: Elite shield x0.625,
Elite body x2.5, Hunter x2, Jackal shield x0.5, Marine armour x2, metal x2-2.5).

**Step 11.** Donor = the Elite minor plasma rifle (carriers 0.4-0.6, no actor flags); Reach's
ai\generic profile; WDM rule 0.5 x 130 / 96 (default), / 125 (balanced). Enhancer (8b0c984): hands
'two', tag_map, battery skips, 20 Halo 1 cards from the Plasma Rifle. Armed boot (built map read
back): WDM 0.677 / 0.52, Grunts 5.03/s vs 10.06, Jackals shieldless. THE DROP BATTERY (user):
MCC's SHIPPED Reach maps carry ~HALF of HREK's ai\generic 'drop weapon loaded' for every weapon
(m10: repeater 0.25-0.45, plasma rifle 0.35-0.45, AR 0.25-0.45, magnum 0.3-0.4; HREK 0.5-0.9 /
0.7-0.9 / 0.5-0.9 / 0.6-0.8) -- the source read is right; read drop values from the MAP, not
HREK. Default = Reach's 25-45 %; balanced by the ratio 50-90 % (ai_firing_profile
`balanced_set`).
**THE BALANCED DROP RULE (user 2026-10-12: 'same rule for every weapon'):** every Armed port's
firing profile carries balanced Drop Weapon Loaded / Ammo = the H1 yardstick's MOST COMMON carrier
value x source port / source yardstick (source values from the source MAP); a zero on one side =
no row. Applied to the SMG, BR, Carbine, Beam Rifle, Spiker, Mauler, Brute Shot (ammo only), DMR,
Needle Rifle, SAW, Plasma Repeater; none for the Gravity Hammer (the sword's carriers drop
nothing) and the Spartan Laser (the RL carriers drop it unloaded); the Sentinel Beam is its own
yardstick. Default fields unchanged (ai_firing_profiles.json diff: balanced_fields only).

**Traps on the way:** `--skip-bitmaps` REWRITES the glow shaders (caught by the proof diff; rebuild
fully); a glow bitmap missing under --skip-bitmaps fails the build; the pilot listed in both
`shaders` and `glow_shaders` drew twice.

**Proof:** port_tool_proof rp1-rp4 (reach_tags / pickable / reticle / retarget repeat / model
meters + ground point): 0 changed apart from bitmap headers, one brute-shot FP antr (known noise)
and -- rp4, by design -- every port's gbxmodel (its new ground point); h1_reticle_proof identical;
the kit restored each time. After rp4 the proof is NARROWED (user): only the steps whose scripts
import a changed tool are regenerated, 'NOT COMPARED' names ports whose later steps read a changed
output; `--full --rev <wave start>` at the end of every wave (wave B: d096b49).

**HEAT REVISIT (2026-10-14, after C1; ea50476, catalog 48bd3d1).** The user's rule (Reach drains heat
while firing) means Reach's passive loss (0.25 -> 0.06/s) runs under the 0.03 a tick: full heat after
14 rounds / ~1.25 s, not 12 / 1.0. Refit: default ramp 1.6 s (was 1.35), heat first 0.108 by the
model -- THE PROBE (b30) overheated it on the 13th: cooling is exact (0.4/30 every tick between
shots) but the ramp holds 15/s longer than `H1_RAMP` says (factor ~0.92 at a 1.6 s tag, 0.857 at
1.4: not a constant) -> heat 0.106, the middle of the measured window; PROBE 2: all three held
bursts overheat on the 14th round at 1.13-1.20 s (heat 0.97-0.98 after the 13th). Balanced
(plasma-rifle ratio, 24 rounds draining) ramp 2.9 s, heat 0.0714 = 24 rounds for any ramp factor
0.86-0.92 (not probed; was 2.6 / 0.077 / 22). Tags rebuilt (`h1_pickable_weapons --only
plasma_repeater --write`); the ten-map rebuild stays batched.

### Halo 1: the Grenade Launcher, wave B4 (2026-10-12, 19 boots + Armed x2 on a30) -- a bouncing grenade, a charged pair for Reach's EMP, a particle sprite of its own

The whole weapon is `ports_h1/grenade_launcher.py`, on a copy of the Halo 1 ROCKET LAUNCHER (weapon,
magazine, HUD, melee) firing grenades built on Halo 1's FRAG GRENADE projectile.

**Step 4a (user): the FRAG GRENADE as yardstick, its holes by the ROCKET LAUNCHER** (a thrown grenade
has no rate, magazine, reload, range, aim, melee or impact). Reach (HREK): impact 25 `collision` +
detonation 0..180 over 0.75 -> 2.25 (`explosion_small`, the frag's group too -> the frag table in both
versions, Hunter armour x0.25); balanced 135 (lower 90), 1.667 -> 2.5, recovery 1.25 s, impact 0 (the
rocket's 0: a zero on one side), aim / range by the rocket. h1_role_compare `grenade_launcher` (shot
rows take damage PARTS: impact + explosion + EMP). WDM: the usual dps column (user), 0.154 / 0.585.

**Reach's hold-to-detonate + EMP -> the plasma pistol's CHARGED PAIR** (`add_triggers` [0]: trigger 1 =
a copy of trigger 0; trigger 0 charges 0.5 s, hold 45 s, overcharged action none): a tap fires the
bouncing grenade, a full charge released fires `grenade release` -- every material detonates, Reach's
tethered blast 0..180 over 0.001 -> 1 (`projectiles` [1]) + the EMP (`add_damage`: 100 on Reach's emp
table -- elite / cyborg shields x0.5, jackal shield x0.25, everything else 0; balanced 35 by the plasma
pistol overcharge ratio). Lost: detonating a grenade already in flight, rolling while held, the
vehicle stall. Halo 1's AI never fires the charged shot (Jackals with special fire overcharge at
100 %, `--actv-set`, still only tapped -- user: leave it). Charge cue: the arm light (`fade_source` B
out; weapon B in = primary charged + the plasma pistol's `one x B in` function via `obje_functions`)
and Reach's landmine BEEP loop (`fire_loop` on B out, 0.3 s `lead` silence: a tap is silent). PENDING
(user): the GL joins the future 'no overcharge sound when empty' patch.

**The bounce and the fuse, MEASURED** (`h1_projectile_probe.py`, read-only, new): a weapon-fired
projectile's speed falls LINEARLY WITH DISTANCE from initial to final over its maximum range; a
FINAL VELOCITY above 0 is a SPEED FLOOR (boot 2: after its first bounce the grenade slid at 7.4 wu/s
for 12 s and burst at its 100 wu range -- never at rest); Halo 1's 'on first bounce' fuse runs from
REST (bursts ~0.45 s after settling); 'immediately' is exact. Final velocity 0. Three bounce boots
(Reach 0.42 -> 2.6-3.5 s bursts; the frag's 0.8 / 0.9 -> 'no bounce at all'; A/B) -> the user's pick:
Reach's friction 0.42 + a FUSE FROM LAUNCH 1.2 s (the typical first bounce ~0.7 s + Reach's 0.5;
balanced 1.1). Lost: a long lob bursts in the air. Units / steep fast hits detonate (Reach's rules as
per-material responses: `default_responses`, reflect `response` 'detonate'; Halo 1's angle
convention unverified). `clear_detonation_effects`: the frag's per-material DETONATION effects (a dirt
sound, an empty stone effect) REPLACED the grenade's own explosion on contact -- the rocket's are empty.

**The EMP look -- Reach's emp_pulse in Halo 1** (boots 7-19): Reach's release plays `emp_pulse` (a ring
of electric wisps, `fx\bitmaps\plasma\emp_mask`, coloured over its life by a cyan -> deep-blue
gradient). Found one fact a boot, by COLOUR, with the normal explosion off (user): added particles
draw at the effect location `normal` (the surface) with distribution 'start' (a 'buildup' over a 0 s
event makes none); a particle draws ONLY from a STOCK particle sheet's own tag layout -- every rebuilt
sheet (raw a8r8g8b8, DXT5, DXT1, stock headers copied, keyed or opaque) failed while a byte copy of
the stock sheet drew; Reach's mask SPLICED into the stock `flash h shield impact` sheet's pixels drew
(`h1_hud_sheet.sprite_bitmap` 'splice', HCEEK's DXT1, opaque on black); the 128 px `shield charge
rings` sheet failed as a container. Final: 6 rings, 2.0-2.5 wu (the EMP's damage radius), 0.8-1.0 s
growing x0.6 -> x1.1, tinted Reach mid -> deep blue (reads white-blue cyan, additive). Not reproduced:
the colour over life, the scrolling clouds, a sharper ring.

**Look:** Reach's one model (b_gun not tilted, primary_trigger present); the on-gun LCD STATIC (teal
14 / 152 / 193 x3: frame, ARM / READY, digits 000; the tether distance / skull count have no Halo 1
source -> skull dropped); the holo SIGHT = the diffuse's ALPHA (Reach paints the sight reticle there)
through `meters` `levels` (140, 235) + `floor` 0.12. Crosshair (from the user's Reach screenshot):
hud_reticles #12 + the falcon pitch ladder (`crop` rows +30..-10, `stretch` 0.642 x 0.281) + the AUTO
square, SUPERSAMPLED x2 (512 px cell, Reach art at native 4K density, scale 1.3, overlay 1.6 / 1.3 / 2,
`split` 100 for the dim frame) -- 'the best crosshair so far' (memory h1-reticle-supersample); a frame
touching the cell edge bled a stray pixel (margin). Muzzle flash: the shotgun family without sparks /
casing (Reach: round flash 0.053, glow 0.13, smoke). HUD meter for a 1-round magazine: ammo_meter caps
the signed-byte alpha multiplier at 127.

**Sounds:** Reach's bank; fire = grenade_launcher_fire + brute_shot_tails_ext mixed; explosion =
grenade_launcher_expl + frag_close_layer; bounces frag_bnc_dirt / metal (the frag's reflection effects
copied, `impact_tint` sounds, on both grenades); Reach's frag_armed LOOP is SILENT (decode a loop before
using it). Step 6: the rocket's box ratio-scaled 4 -> then (user test) the FRAG GRENADE equipment, 1
round: a pickup gives BOTH a grenade and a round (noted for later).

**Enhancer (hand-off):** hands 'two' (81aedf1), 19 cards from the rocket / frag / shotgun (d1a8e9e);
Triggers balance rows and cards reached trigger 0 ONLY -> `index: 'all'` rows + catalog
`trigger_index: 'all'` (0dcb713). 'Covenant avoid friendly fire' stays a global option (user).

**Proofs:** port_tool_proof gl1 (pickable), gl2 (model meters), gl3 (sounds + pickable), glF (every
chain tool changed since 9fb39f7); h1_reticle_proof (crop / stretch, supersample); ammo_meter.plan
unchanged for every n but 1 -- each 0 changed apart from bitmap-header noise, the kit restored exact.

### Halo 1: the Concussion Rifle, wave B5 (2026-10-12/13, 12 boots + Armed on a30, PARALLEL with B7) -- a knockback bolt, a Covenant look recoloured layer by layer

The whole weapon is `ports_h1/concussion_rifle.py`: a copy of the Halo 1 ROCKET LAUNCHER (user: 'if
it's easier') firing a bolt built on the restored FUEL ROD's projectile and explosion.

**Step 4a (user): yardstick the FUEL ROD; DEFAULT = Reach's own, BALANCED = the ratio per field;
materials: the fuel rod's table in default, x Reach's plasma_fast / explosion_large in balanced;
HUNTERS: Reach's values in both (the fuel rod's x0 has no ratio).** Reach: impact 21.5 (`collision`)
+ blast 0..21.5 over 1 -> 2 wu (core 0.8, `plasma_fast`) = 43 a hit at 3/s (129 dps = the Plasma
Rifle's 130); the knockback 2.5 = Reach's own GRAVITY HAMMER IMPULSE (2.5). Balanced: blast 26.9
(lower 14.3 by the sibling rule), impact 0 (the fuel rod has none), knockback 4 x 2.5/1.5 = 6.67,
1.04 s a shot, 5 / 11 / 24, magnetism 6 -- 26 dps against the fuel rod's 60. The user judged
Reach's raw 2.5 knockback 'decent enough' in default (the hammer's tuned 7.5 not needed). Step 6: the
rocket box ratio-scaled by the carry (7, balanced 6).

**Flight, MEASURED (h1_projectile_probe).** A Halo 1 projectile with final > initial did NOT speed
up along the range: the balanced bolt (11.2 -> 12.3) flew a constant 12.17-12.18 wu/s from its
first tick (observation; the GL's grenade slowed along the range). Two balanced traps, one boot
each: (1) Reach's MINIMUM VELOCITY 11 against an 11.2 wu/s bolt -- in Halo 1 it DETONATES (the
Brute Shot) -> balanced 0 (the fuel rod's zero); (2) MAXIMUM RANGE 0 copied from the fuel rod
destroyed the bolt on creation (probe: 0 projectiles over 5 shots) -- the fuel rod's 0 is UNSET (it
falls by gravity), not a value to carry: no row, Reach's 100 in both. Read a yardstick's zero as
'unset' before a ratio writes it.

**The look: every green layer of the fuel rod, found one by one (boots 2-9).** Muzzle flash: the
plasma pistol's `fire bolt` (user: 'a normal plasma release'; Reach's flash gradient is violet),
fins dropped, x0.7, tinted violet, an own violet muzzle light on the rocket's slot. The fuel rod's
green came from FIVE places, none of them visible to 4b or the template diff:
- the blast's particle system TYPE states `birth` / `death` carry a COLOUR MULTIPLIER (green) over
  every particle state -- recolouring the particle states alone changed nothing (`psys_tint`
  `@<type state>`, h1_pickable_weapons);
- `c` particles (sparks, `c fire`) are coloured by the creating object's CHANGE COLOUR -- the fuel rod
  copy has none (`change_color` violet, the Beam Rifle's finding);
- a solid glow shader_model on the plasma rifle template draws its green REFLECTION tint over the
  diffuse -> ADDITIVE glow shaders for the bolt model (Reach's own `concussion_rifle_grenade`);
- each material response names its effect TWICE: the nested POTENTIAL response kept the fuel rod's
  impact effects (green burn, green flare) -> `impact_tint` `potential`, impact particles violet,
  the burn = Halo 1's plain plasma burn (user: blue is fine);
- the green ball in flight was the template's light-volume WIDGET (`hunter fuel rod`), no
  attachment at all -- a one-colour-per-element diagnostic boot (sparks red, light blue, model
  yellow / white) left it green and so pointed at it -> `widget_tint`. Its sprite sheet is CYAN and
  the volume draws ADDITIVELY in layers: a pink tint came out blue, then white (clipped) -> the tint
  per channel = target / sprite colour and alpha 0.45 so the layers stop clipping ('big success');
  final size x0.75 (user).
READ THE DEPLOYED MAP (port_refs_audit's plugin walker, colours by offset) before a look boot: it
proved each tag was right and moved the search to the next layer. Explosion visual ~0.75 wu (Reach's
flash 0.73), inside the 1 wu full-damage core; the outer damage edge has no visual, as in Reach.

**Look, the rest:** Reach's model (b_gun not tilted, left_hand + primary_trigger markers); the
INDICATOR / OVERHEAT panels lit blue from Reach's `plasma_launcher_holo` (static meters); every
material needs a shader before `tool model` -- an unmapped one makes tool ASK for a type and loop on
the empty input (50 minutes, 4 GB of prompts). Crosshair: hud_reticles #17 'mirror horizontal' =
the sprite (one crescent + three HALF triangles) with its RIGHT edge on the centre and its mirror
on the other side, its registration (box centre) moved onto the crescent, sized from the user's
screenshot (88 x 38 px), supersampled x2. Ammo: 6 / 5 ticks (Reach's pips are a shader bar).

**MCC's Halo 1 plugin:** `Instantaneous Acceleration` is a vector3 (`... i / j / k`; Halo 1 reads
`i`) -- a knockback balance row must name `Instantaneous Acceleration i`.

**Step 11:** donor the fuel rod (grunt specops fuel rod, WDM 0.5, no actor flags), Reach m10's
ai\generic entry; WDM rule 0.233 / 1.15; balanced drop 0.25-0.875 / 6-13. Enhancer: hands 'two'
(Reach files it as a rifle: Grunts half rate, Jackals shieldless; e86e829), 16 cards from the rocket
(e49524a; knockback uncarded). Armed: all three species fire it (user).

**Tools from the Concussion Rifle** (h1_pickable_weapons, each opt-in, narrowed proofs cr1-cr4 0
changed): `set_attachments` copy `tint`, `psys_tint` `@<type state>`, `impact_tint` `potential`,
`widget_tint`; h1_role_compare `concussion_rifle` set.
**Final step check (2026-10-13, user):** 4b list 3 line by line found `active camo ding` (Reach 0.75,
the H1 fuel rod 0 -> the source value) left at the rocket's 1.0 -- applied; write proof 29 port tags /
3,489 fields, exactly that one changed. Closing 0 refs 0 problems, 2 validate_halo_json 0 problems, 6
4b list 2 = recorded decisions only (knockback default Reach's, impact knockback moot with balanced
impact 0), 7 port_sound_refs all OWN + port_sounds --check 0, 8 Armed fires (user), 9 hit effect x1,
10 muzzle flash compared; 1/3/5 n/a (Halo 1).

### Halo 1: the Focus Rifle, wave B7 (2026-10-12/13, 13 boots + Armed on b30, PARALLEL with B5) -- a continuous beam at 30/s, an animated Reach-colour beam, a heat-ramp display

The whole weapon is `ports_h1/focus_rifle.py` (CLOSE-OUT RECORD in it), on a copy of the Halo 1 PLASMA
RIFLE (the yardstick, user) wired as the SENTINEL BEAM (the hum on the rate of fire, an own one-sprite
firing effect, a copy of Halo 1's Sentinel beam projectile with the plasma bolt's damage table).

**Step 4a (user): the PLASMA RIFLE.** Reach: 3 a round (plasma_fast) x 30/s, heat 0.025, loss 0.35 /
0.23 overheated, recovery 0.1, battery 0.0016125 (620), zoom 3.5 / 9.5, 4000 wu/s, range 120. **Reach
COOLS WHILE FIRING:** the user's stopwatch ~2.5 s = 0.75 heat/s - 0.35 (no cooling would be 1.33 s;
the meter never visibly falls). Halo 1 has ONE loss: the mean 0.29 (the Beam Rifle's precedent).
Balanced = the plasma-rifle ratio by TIME TO OVERHEAT (both games cool while firing: H1 PR 2.67 s x
2.47 / Reach PR 2.17 = 3.0 s), 130 dps, battery by time (9.3 s). Materials: the bolt's table default, x
Reach's plasma_fast / plasma_slow balanced (the repeater's rule). The Halo 4 port of the same weapon was
the reference (Reach's own values; heat cards from the Sentinel Beam there).

**THE RATE, MEASURED (boot 2, `h1_weapon_state_probe`):** a 29..30 tag fires **30 rounds a second**
in Halo 1 -- 29 rounds in 0.97 s, shots 33 ms apart. The "15/s cap" (SMG 22.5, Sentinel Beam 30)
did NOT hold here: the repeater's rule (rate/30 a tick, a shot when the sum reaches 1, reset) gives
one round EVERY tick at a full 30 and two ticks at 15..29.9. The per-round values doubled for 15/s
overheated the gun in ~1 s (user: 'under 2 s'). **THE SENTINEL BEAM, PROBED (c40, 2026-10-13): it
fires 15/s** (shots 67 ms apart; 38 rounds to the 0.9 overheat in 2.47 s; 84 rounds a battery) -- its
doubled per-round values are RIGHT, no change. The SAME 29..30 tag, accel 0.05: 30/s on the Focus
Rifle, 15/s on the Sentinel Beam. A field diff of the two weapons: the ONLY rate-relevant difference
is the AGE penalty -- the Sentinel Beam kept the plasma rifle template's rate-of-fire penalty 0.2 (the
Focus Rifle: Reach's 0, which Reach's plasma rifle shares). It scales with the battery used, which is
> 0 after the FIRST round: 30 x (1 - 0.2 x 0.012) = 29.9 < 30 -> two ticks from the second shot on
(the probe's first gap is already 67 ms). Not isolated by a boot. So a 30/s port needs age rate-of-fire
penalty 0 in BOTH versions (the Focus Rifle's balanced fit assumes 30/s; no row or card touches it).
Measure every port's rate. Halo 1 cools while firing
(confirmed again: heat 0.045 -> 1.0 over 29 rounds at 0.29/s); vent 3.07 s as fitted.

**THE BEAM -- the best so far (user):** Reach's 1p `beam_system` = a `center` ribbon on energy_trail
+ a 12-gon `pulse` tube, both through the palette `sentinel_beam` (MISSING from HREK; Halo 3's
fx\contrails\_gradients\sentinel_beam is it: black -> gold -> white). Baked (the Spartan Laser's
route) onto an own copy of the Sentinel contrail. Then, step by step in game:
- **Motion:** the contrail's own `texture animation u` drew STATIC (every 30/s beam is new and starts
  at the same phase). A contrail **SECONDARY MAP** -- a greyscale knot map from Reach's pulse (floor
  0.35), u animation source `none`, function `slide`, period 0.4 s -- runs on GAME TIME and MOVES
  (boot 8; pickable contrail `secondary`).
- **Reach's colour** (the user's firing screenshot: white-hot core, warm orange-peach edges, a
  blue-violet haze): an ADDED violet contrail on the same marker drew nothing from boot 8 on (it had
  drawn as a gold pulse in boot 4, without a secondary map -- not isolated further); boot 11's
  diagnostic put the violet on the CORE texture and it drew at once. Final: ONE contrail 0.2 wu whose
  texture SUMS a narrow white-orange centre (energy_trail ^ 2.2, colour stops) and hollow blue-violet
  bands (energy_trail ^ 0.45, gain 1.6) -- `baked_textures` `components` (boot 12-13, user 'looks
  right'). Test tool: `h1_beam_variant.py <port> <name> --spec layers.json` (a weapon copy on the
  test secondary; `--clean`).
- **Applied to the Spartan Laser** (user: 'looks better like this -- copy it into the build'): its
  core on energy_trail and its glow on Reach's pulse through laser_red_01 (57b5e67; the batched rebuild).

**Look, the rest:** the display tiles = Reach's heat meter (user: 'a heat tracking meter as well'):
weapon input B = heat (was illumination; the muzzle-light attachment dropped -- its light is in the
firing effect), function 2 = the heat out C, the repeater's colour RAMP slid by it (blue -> orange);
indicator / plasma strip static lit shapes in Reach's colours. Scope: Reach's chud fitted to the user's
screenshot (lens 1293 x 707 -> span 931.1, aspect 1.2506). Crosshair #22 supersampled -- the cell art
includes h1_add_reticle.SCALE (1.268): scale 2.0, overlay 0.155 (2.4 overflowed the cell). The beam
starts at the FP muzzle (`h1_fp_muzzle.py`, the lost marker_dir.py as a tool) minus 1 unit (user).

**Step 11.** Donor = the Elite minor plasma rifle (15 carriers 0.4-0.6, no actor flags); Reach's m10
profile (drop 37.5-47.5 %); WDM 0.5 x 130 / 90 = 0.722, balanced 0.5; balanced drop 0.75-0.95.
Enhancer (2721d29, 5b81e9a): hands 'two', heat + battery cards from the plasma rifle itself, Salvo
Shooting skipped (30/s already a round a tick), Error Angle muted (user, card-level). Armed boot: all
three species fire it.

**PARALLEL (the first pair, with B5):** a test copy of a DONE port under its own folder was deleted by
the other session's proof restore (`h1_beam_variant --out`: put it under the in-progress port); a
by-path commit of a shared file swept the other session's hunk in (20200bf); a port turning DONE during
a proof shows its folders as ADDED in the restore check (fo3: 196, the Concussion Rifle's -- untouched);
a level fails to build while the other session's tags in its palette are broken (b30, B5's bolt).
Heredocs ate backslashes in a config once more (every port config failed to load for a minute): configs
through the Edit tool only.

**Proofs:** fo1 (bake size), fo2 (stops / gain / grey + contrail secondary), fo3 (components) -- 0
changed apart from bitmap headers, the kit restored exact; the scroll keys rode in B5's cr proofs.

### Halo 1: the Plasma Launcher, wave B6 (2026-10-13/14, 16 boots + balanced + Armed x2 on a30, PARALLEL with C1) -- a multi-bolt charge as a charged pair, a homing volley, a sticky bolt, a Reach hex scope

The whole weapon is `ports_h1/plasma_launcher.py`: a copy of the Halo 1 PLASMA PISTOL (its charged
trigger pair, heat, battery) firing bolts built on the Halo 1 PLASMA GRENADE's projectile and explosion.

**Step 4a (user): yardstick the PLASMA GRENADE, Reach's charge KEPT, holes by the ROCKET ratio;
the grenade's table in both versions.** The grenade is the bolt's own family (Reach explosion_small,
175 / 300 against 250 / 350) and the only candidate with a free AND a stuck burst in both games. No
Reach yardstick charges: the 0.75 s hold and the 3.0 s charge stay Reach's, only recovery / spacing
take the time ratio (times by ratio made a 7.5-9.4 s volley charge). Autoaim ANGLE kept Reach's in
balanced (user): the rocket's 0 would switch off the homing. h1_role_compare `plasma_launcher`.

**Reach's charge in Halo 1, MEASURED (h1_projectile_probe, h1_weapon_state_probe):**
- the pair: a tap fires trigger 0 at once (Reach needs a 0.75 s hold: lost; the tap paced at Reach's
  0.95 s single-bolt cycle -- 1.0526/s fired every 31 ticks, 1.13/s every 28-29: Halo 1 rounds ~2
  ticks up); a full charge released, or held past the 2 s hold ('discharge'), fires trigger 1.
- THE SPEW NEVER RUNS from the pair's trigger 1 -- its own spew time, or its own 1-tick charge +
  discharge + spew (a test secondary): ONE bolt each time. The volley = 4 PROJECTILES PER SHOT with
  each its own error (1.5 -> 2.5 deg; a 4 deg horizontal fan read as 'two pairs of two'). Lost: Reach's
  0.21 s spacing, the 2- and 3-bolt levels. Heat 1.6 / battery 4 bolts on the one round.
- A volley fires from ONE bolt of battery left: Halo 1 checks only that the battery is not empty (user:
  accept). Battery 12 = age 0.0833333 + the Spartan Laser's misfire 0.9999 / 1.0.
- The exported PRIMARY CHARGED runs over charge + HOLD (5 s: 0.50 at 3.0 s, 1.0 at the auto-discharge;
  a second word, +0xE4, reaches 1.0 at 3.0 s and is not exported).

**Homing:** trigger 1's bolt guided at Reach's 45 deg/s -- Halo 1 steers at the autoaim target at
release ('visibly tracks', user); the tap unguided (Halo 1's AI only taps a pair: Reach's AI bolts are
unguided too). Lost: the lock time / grace / decay, the lock rings.

**Sticking:** the needle's DEFAULT `attach` on every material (the grenade's own `attach` is a
potential response with empty conditions), the Jackal shield and force fields reflect, water passes;
fuse 'when at rest' 0.25..2.5 s (stuck = at rest), 'detonation max time if attached' off. Halo 1 deals
ATTACHED detonation damage AT THE STICK (boot 1: 'kills before the explosion') -> none: the burst alone
(Reach's stuck 300 lost). Stick beep: a response effect's sound was never heard; the projectile's
DETONATION STARTED effect (`started_effect`, the fuse start) plays it.

**The full-charge cue (user: 'another fully charged identification'):** Reach turns the rear display
red at full charge. A colour RAMP read against the charge drifted (Halo 1's sampling of a tiny ramp is
not linear: +0.22 on the ramp moved the lights ~0.35 s, not 1.1). Fixed by a STEP: the unused object
function 0 (A out) = primary charged clip-and-normalised to a narrow band (0.884..0.894 after tuning by
eye; the probe's 0.50 at 3 s showed at ~2.25 s), the ramp read on A out (blue < 0.3, red > 0.7).
The muzzle charge glow: the Spartan Laser's radial cards faded by D out.

**Look / HUD:** Reach's model -- the rear holo ring / screen / emitter lit (static, Reach blue); the
bolt Reach's model, a pale-blue additive core + a blue glow flare (pure white at first). Muzzle: the
pistol's `fire bolt` copied (both events), fins dropped, x1.5, Reach blue, a muzzle light part
(`sound_effects` `light`). Crosshair: hud_reticles #31 is ONE QUADRANT (two pointer halves + a tick),
drawn four times with Reach's widget origin 0.945 (the halves overlap 5.5 %; h1_add_reticle applies a
layer's `stretch` to its offset TOO -- offsets in sprite px). The 3x SCOPE: Reach's chud state data did
not decode (every widget zoom 0) -> per_widget `zoom`; its side cells are the top cell turned +-120 deg
by the chud animation (`rotate`); its small cells mirror about their OWN offset (`mirror_local`); the
central lens animated (scale 0) fitted to the user's screenshot (aspect 1.25, the Focus Rifle's). The
coloured symbols as zoom glyphs: the two rings (52 / 53, art turned 180 deg: `flip`, a 7 px cell margin
or the edge bleeds) and the four bolt pips in ONE glyph (58, `mirror4` with per-row x). Halo 1 centres a
glyph overlay on its sprite CELL, not its registration: a non-square glyph needs its anchor offset
measured off a screenshot. hud_reticles 59 was granted but NOT needed (the scope's charge bar is a live
meter). Pickup icon x1.3 (a heavy weapon).

**Sounds:** Reach's bank. Reach's charge LOOP decodes SILENT (the GL's frag_armed lesson again): the
loop = the 'in''s full-charge sustain 3.0-4.5 s (`slice` + `loop_len`), no start sound (a
sound_looping's start plays when it is attached, on ready). Water splash KEPT (user). Screen flash on
the player (Armed boot): the grenade's 1 s / 0.7 green flash on BOTH damage tags -> impact none, burst
0.25 s at 0.25 in Reach blue.

**Step 11:** donor the fuel rod (grunt specops fuel rod, WDM 0.5), Reach m10's ai\generic entry (#14);
WDM rule base 0.5 x the grenade's 120 dps / the TAP dps (the AI taps): 0.33 / 0.89; balanced drop
0.4-1.0 loaded. Enhancer (its keys): hands 'heavy', trigger_index 'all', the plasma pistol's charged-
shot cards skipped. Armed: all three species fire it (user).

**Close-out pass (user: 'check every ported step'):** 5b on the BUILT port (h1_role_compare rows:
tap 186 dps / balanced 67-71, volley 236 / 112 -- the WDM rule's numbers held); step 9's balanced
SWAP had been missed -- the RL ratio (H1 rocket ready 22 fr x Reach 26/26) = `anims` swap x0.846, no
reload (a battery); 4b list 2 / list 3 flags decided by name and written into the config.

**Tool changes (each opt-in, narrowed proofs pl1-pl7 0 changed):** reach_tags 96-bit node masks
(the first Reach FP graph above 64 nodes) + a bare `&` in chud names; h3_anim_decode.blobs keeps only
tgda-proven chunks (an outer chunk the size of a member shifted the rest); h1_pickable_weapons
`attached`, `started_effect`, sound_effects `light`, zoom_glyphs `overlay` / `flip` / `mirror4`;
h1_h3_scope per_widget `zoom` / `rotate` / `mirror_local`; h1_port_sounds `slice`.

### Halo 1: the Storm Rifle, the Halo 4 pilot (wave C1, 2026-10-13/14, 7 boots + Armed on b30, PARALLEL with B6) -- Halo 4 as a SOURCE, its compressed FP graph decoded and the arms re-solved, Wwise sounds, a CUI HUD

The whole weapon is `ports_h1/storm_rifle.py`, on a copy of the Halo 1 PLASMA RIFLE (heat / battery HUD,
gauge, overheat states). Halo 4 enters wave A's pipeline behind `h4:` paths, as Reach did behind
`reach:` (B1); the SAW's Halo 4 tools (saw_to_jms etc.) were not needed.

**THE h4: SOURCE (`h4_tags.py`).** `tool export-tag-to-xml` of H4EK (absolute paths, cwd = the kit)
writes Halo 3-SHAPED XML: the Halo 3 readers run unchanged (`h3_weapon_values --kit h4`, h1_h3_weapon_model,
h3_hud_art). Bitmaps: a multi-image tag (the 10 Covenant digits, the 7 heat stages) is ONE pixel blob
after a u32 total size, ending at the next `lbgt` chunk (`bitmap_images` / `decode_bitmap`). Halo 4's
render model = world AND first person (like Reach): 4 nodes (b_gun root not tilted, cannister, two vents).

**THE FP GRAPH IS COMPRESSED-ONLY** (no float copy, unlike Reach). `h4_fp_dump.py` (Blender + Foundry,
reusing `h4_fp_jump.build_rig`) decodes it and dumps rest + every frame's armature matrices to
`out\h4_fp\<graph>.json`; h4_tags.load_graph reads that. Blender space = G(-90 deg about z) x Halo x
3.048; the per-bone convention is identity. Foundry samples N+1 frames: keep N. OVERLAYS import as full
poses stacked on idle frame 0 -> deltas from frame 0 (`overlay_deltas`). Foundry leaves a stray
`<folder><basename>` copy of the graph / render model in H4EK: removed (h4_fp_dump does it itself).

**THE ARMS ARE RE-SOLVED** (`h1_fp_retarget._resolve_arms`; storm_fp is NOT Halo 1's skeleton: 84 nodes,
other proportions). Per frame: base re-axed (h4_tags.ARM_AXES per side), two-bone IK on HALO 1's bone
lengths to Halo 4's wrists with the elbow in Halo 4's arm plane; a wrist out of Halo 1's reach moves the
SHOULDER toward it by the shortfall (Halo 4's melee stretches the left arm ~4 cm past it -- clamped, the
hand stopped inside the gun). FINGERS BY DIRECTION: each Halo 1 segment rigid on its solved parent, then
the smallest rotation onto Halo 4's segment (joint -> next joint, the tip along Halo 4's bone axis) --
absolute axes (100-170 deg off: Halo 4's finger bones have their own conventions) and deviation-from-bind
(Halo 4's bind hand is curled, Halo 1's flat) both failed in game. Quaternions kept in the previous
frame's hemisphere per node (`_continuous`): w >= 0 locals flipped near 180 deg and MCC's frame blend
spun through each flip (melee, the fidget). `hand_offset` / `hand_offset_anims` (gun-space, per side,
per source animation): Halo 1's chunkier glove sinks into a grip Halo 4's slim hand wraps -- applied to
the FIDGET only (user: idle fine without, the melee grip lost with it). Reference: Halo 4's own arms
rendered from b_camera_control in Blender (`h4_fp_reference.py`) against fp_render, same frames;
hand-in-gun counts per animation: `h1_fp_hand_clip.py`.
Halo 1 plays `overheated` once; Halo 4's `overheated` is not between overheating and o_h_exit (a 19 cm
jump) -> `holds`: overheating's last frame held 31 frames (40 too long, user). User verdict after 5 dry
boots: idle and overheat good, the fidget acceptable, the melee grip approximate ("That settles the
animation work").

**SOUNDS: WWISE** (`h1_port_sounds` bank 'halo4'). First-person events live in the bank `<x>_player`
(here `assault_carbine_player`); the fire event has 6 layers; `<event>@<bank>` names another bank's event
(the flyby in proj_cov_whizby, the impact in plasma_impact_generic); 'offsets' trims per folder. The
projectile loop events are EMPTY in MCC. All own, under sound\weapons\storm_rifle_port.

**HUD: CUI** (.cui_screen, 1280x720 canvas, art 3 px a widget unit: h4_tags.px_per_unit). The crosshair
from ac_tick + layers + ac_circle, scale 2.3, supersampled (512 px cell). The on-gun HEAT panel = 7
stage images -> one Halo 1 meter (`meters` 'stages', a texel's threshold = the first stage it is lit in);
`value_floor` 0.1 (Halo 1's heat out B is floored at 0.1: stage 1 lit from cold, boot 2). The battery
counter (10 Covenant digits) was built (`numeric` 'digits', glyph in RGB too: the numeric chicago ADDS
its map -- white quads otherwise) and then DROPPED (user: Halo 4 shows no counter on the gun). The
overheat chevron on function 0 (= overheated): the template's function 3 carries INVERT (lit at rest).

**HALO 1 TRAPS (new):** `tool` keeps 31 characters of a shader name (`material_names` st_*); `tool model`
loops on a prompt for a material without a shader; the template's collision hull hid the world model
(an own hull: h1_box_collision boxes).

**Step 4a (user): the PLASMA PISTOL** (Halo 4 has no plasma rifle; the only heat plasma weapon in both).
Halo 4: 8 a bolt (plasma_fast) x 10/s, heat 0.09, loss 0.55 / 0.3 overheated, recovery 0.1, battery
0.006 (167), 50 wu/s, range 100. **HEAT DRAINS WHILE FIRING in Halo 2 / 3 / ODST / Reach / 4** (user,
relayed mid-port: the old 'cools only while not firing' reading was wrong) -> 27 bolts / 2.6 s, 3.0 s
vent. Halo 1 also cools while firing but with ONE loss: approximation A' -- loss 0.3 (the overheated one,
the 3 s lockout kept), heat fitted 0.0665 (the 27th bolt). Balanced (ratio): 10.29, heat 0.0639 on 0.433,
recovery 0.25 -> 47 bolts, 1.73 s vent; 62.5 wu/s, range 125, aim 6.25 / 15; PP bolt table x Halo 4's
plasma_fast / slow; battery = Halo 4's own (the ratio degenerate). PROBES (h1_weapon_state_probe): a
10.0 tag fires 10.0/s; A' = 27 bolts in 2.61 s + 3.00 s vent. The user: balanced is "very hard to
overheat". The shared tools' old heat rule was fixed in passing (port_ttk, port_role_compare: a8d79b2);
B3 Plasma Repeater and the H4-kit Focus Rifle were reported affected (revisit after C1, user).

**Step 11.** Halo 4 m020 ai\generic Storm Rifle entry over the Elite minor plasma rifle (one donor for
every slot, B3's choice); WDM 0.5 x 90 / 80 (default), / 103 (balanced); balanced drop 0.5-0.9. Enhancer
(bd7646c, 1f2385b): hands 'two', own bolt + melee tag_map, skip Ammo / Reload / Ramp Up / Misfire, 18
cards from the plasma rifle. Armed boot: Grunts (x0.5, two-handed), Jackals (shieldless), Elites.

**Proofs:** st1-st7 narrowed (model / retarget / sounds / pickable of the done ports): 0 changed apart
from bitmap headers, restore 0 each.

### Halo 1: the Suppressor, wave C2 (2026-10-14/15, 8 dry boots + balanced + Armed on a30, PARALLEL with C3) -- a Halo 4 magazine automatic, a shader with no colour map, the 32 MiB model-buffer cap

The whole weapon is `ports_h1/suppressor.py`, on a copy of the Halo 1 ASSAULT RIFLE (also the yardstick):
the Halo 4 route of the Storm Rifle (h4: paths, Foundry FP decode, arms re-solved, Wwise sounds, CUI
crosshair) on the magazine shape of the SMG / Spike Rifle (a slow visible projectile on every round).

**Step 4a (user): the ASSAULT RIFLE.** Halo 4: shard 6.25 (plasma_fast) x 15/s, 48 (192 / 336), reload
59 / 68 fr, error 0.5 -> 3, aim (mode block) 7.5/15 10/20. The shard flies 60 -> 15 wu/s over its FIRST
2.5 wu (`acceleration range` 0..2.5), then 15; Halo 1 slows a projectile over its WHOLE range (the final
velocity a floor) -> 15 -> 15 (within ~0.1 s at every distance). Halo 4's shard has NO damage falloff:
its damage effect's 'scales based on distance' flag is unset, the 0..60 air damage range inert. Balanced
(AR ratio): 8.33, 22.5 tag (Halo 1 fires 15..29.9 at 15/s: 125 dps), 90 (288 / 787: no dual wield, no
x1.5), 2.9 s, error 2.5 (the maximum's ratio; the minimum's own gave 6.7) -> 8.13, range 40, aim 9/23.4
12/31.25. The rate was NOT probed on this port (the SMG's 15 / 22.5 -> 15/s measurements carried).

**THE DIFFUSE THAT DOES NOT EXIST.** H4EK's `_default_metal.material` names a colour map
(storm_forerunner_smg_default_diff) shipped NOWHERE (not H4EK, not MCC's maps). The SHIPPED default
material (m020.map: bitmaps normal / SHATTER control / cube / detail spec; specular 100, mix 0.9, reflection
gamma 0.42, fresnel power 0.5936) = H4EK's `_shatter_metal.material`: `srf_char_forerunner_andrew` takes its
diffuse from the control map's df channel (`control_map_spdfgl`: G, by the slot name) x albedo tint 0.494.
`h4_standin_diffuse.py` (channel mode) bakes grey = tint x G, the specular channel R into the base map's
alpha (Halo 1's reflection mask). Read a Halo 4 cache tag's references: scan its data for tag-reference
structs (group magic, datum @0xC) and match parameter floats against the H4EK materials.

**THE 32 MiB MODEL-BUFFER CAP** (found here; memory h1-model-buffer-32mib-cap): `tool build-cache-file`
crashes with a bare access violation after 'streaming model vertex and index buffers' once a map's MODEL
vertices x 68 + indices x 2 pass 32 MiB (crash registers: EBP = total model vertices). Bisect: build the
level with the port's tag references swapped one group at a time, then its parts, vertices, attributes --
everything above ~1000 vertices crashed, a finished port dropped instead built. Fixes (user): world = FP
model tag (one gbxmodel, -0.8 MB here), the 8 Reach / Halo 4 ports reworked and decimated (h1_decimate.py,
another session); this port decimated to 60 % (40 / 50 lumpy on the side).

**FP.** The graph's 93 nodes = the C1 DROP list + 13 gun bones: no new drop. Left hand: Halo 4's fingers
curl over the front-left of the gun, ours sat behind the drum. The hand-in-gun COUNT pointed DOWN (fewer
intersections); the look pointed UP -- rendered through Halo 4's reference camera (FOV 70, a pinhole of the
FP space), (0, +1, +1) cm matched (the count doubles: the chunkier palm inside the gun, unseen). Idle /
posing / fire only. View 2 units lower (user); the FP muzzle re-measured for the shard's first-person offset.

**LOOK.** Glow = the shipped look from the user's Halo 4 screenshot (strip edges 214 / 161 / 29 -> rgb
1 / 0.75 / 0.13); the strips are long thin UV islands: an islands glow lit their middles -> `strip`
(falls off across the long axis), a narrow `core` (power 3) in `hot_rgb` pale yellow (white read 'pure
white'), plus HALO CARDS (glow_cards: each strip copied, widened 2.2 in its own plane, `along` 1.05, rings
`round_scale` 1.4, `skip_piece_normals` for pieces facing along the barrel and the tilted top plate --
x2.2 in 3D ran a strip through the gun, floated a square, tilted the rings). The shard: the AR tracer
contrail recoloured, brighter (1 / 0.88 / 0.45), wider 0.07, + the fuel rod exhaust light / flare as a
shard glow. Muzzle: Halo 4's FP flash is a LIGHT only (+ plate sparkles) -> the AR's centre flash kept,
tinted, 3 units up (user); off-axis flashes, FP smoke, casing dropped.

**SOUNDS** (bank forerunner_smg_player): fire = play_forerunner_smg_player_fire_single, 3 LAYERS (`event:k`
entries layered; several wavs in one entry = permutations); the drop's event lives in the BOLTSHOT's
player bank (found by scanning all 578 banks for the event id, bank names by FNV of H4EK soundbank tag
names); impact = plasma_impact_generic + forerunner_impact_sweetener over the AR's hard-surface hits
(impact_tint `sounds`). Pickup sound: the AR's (user: KEEP).

**Step 11.** Halo 4 m020 ai\generic Suppressor entry over the AR (donor_weapon); WDM 0.4 x 150 / 93.75 =
0.64, balanced / 125 = 0.48; balanced drop 0.3 x 0.7/0.5 = 0.42 - 0.9 (Halo 4's own sets no rounds: no
row); species skill. Enhancer (75b11d1): hands 'two', own shard + melee tag_map, no rate skips. Armed
boot: Grunts (x0.5), Jackals (shieldless), Elites -- passed.

**Tools new / generalized (each committed with its proof):** h3_hud_art.decode local images,
h4_standin_diffuse.py, h1_h3_weapon_model islands `strip` / `core` / `hot_rgb` (proof su1 0 changed) and
glow_cards `along` / `skip_piece_normals` / `round_scale` (su2 caught a key-name clash with the Mauler's
`skip_normals`: renamed, su3 0 changed), h1_role_compare 'suppressor'. Read-only tools promoted at
close-out: `h1_fp_camera_render.py` (the FP retarget through Halo 4's reference camera, trial hand
offsets), `h1_gbxmodel_render.py` (a built gbxmodel side / top, glow geometry highlighted),
`h1_model_buffer.py map|ports` (the 32 MiB cap), `h4_cache_refs.py` (a shipped Halo 4 tag's references
+ which H4EK material's values it holds), `h1_tag_writes_proof.py <key> snap|diff` (closing check 6 for
Halo 1: flatten, re-run the writers, 0 changed). Trap: `ai_firing_profile.build()`
WRITES by default (write=True) -- pass write=False to read a source entry.

### Halo 1: the Boltshot, wave C3 (2026-10-14/15, 6 dry boots + balanced + Armed on b30, PARALLEL with C2) -- a Halo 4 sidearm with a charged pellet blast that overheats, a charged pair on a magazine template

The whole weapon is `ports_h1/boltshot.py`, on a copy of the Halo 1 PISTOL with a second trigger
(`add_triggers`, the Grenade Launcher's charged pair): a tap fires the bolt (trigger 0), a 0.6 s charge
the blast (trigger 1).

**Step 4a (user): a ratio PER MODE.** The bolt by the PISTOL (bullet_slow both sides), the blast by the
SHOTGUN -- Halo 4's own shotgun is a near-twin. Halo 4's blast is ONE projectile whose `conical spread`
(yaw 5 x pitch 3) makes 15 pellets: read the PROJECTILE, not the barrel ('projectiles per shot 1'). The
charge kept (no yardstick charges; Halo 1's plasma pistol charges 0.6 s too); the bolt's range kept 40 (the
ratio 6.4 is degenerate: the Magnum's 250); balanced 7 rounds a blast (two a magazine).

**Step 4b found the overheat:** barrel 1 generates 1.0 heat a shot at threshold 1 -- every blast
OVERHEATS for 1.8 s (loss 0.5 overheated; Halo 1's one loss = that one, the Storm Rifle's A'). The leftover
`overheated` / `o_h_exit` / `*_overheated` animations were the clue. Halo 1 adds trigger heat per SHOT,
not per round (the plugin's tooltip), and charges DURING the overheat (h1_role_compare: cycle = max).
Halo 4 holds fire_2's last frame through the lockout (fire_2's end = o_h_exit's start; `overheated` is
another pose) -> Halo 1 overheating = fire_2 (`also_as`), overheated = its last frame held 32 fr, o-h-exit.

**Halo 1 limits found (recorded in `lacks`):** Halo 1 AUTO-RELOADS once fewer rounds are loaded than ANY
trigger costs -- 6 bolts of 10 (balanced 9 of 15); the user kept Halo 4's 5 a blast. The fixed 5 x 3 grid
(Halo 1: random in the cone). The AI only taps the pair. Halo 4 opens the plates by a charge-driven
OVERLAY (`flaps`) Halo 1 cannot play -> fire_2's open plates baked into `overcharged` (`node_from`).

**The look (user, boots 1-5):** the gun drew WHITE: Halo 4's colour map has a solid alpha, so the
reflection mask (multipurpose R) was 255 -- base maps from the colour map x albedo tint + the CONTROL map's
specular (R) as the alpha, the AR's gun shader. The glow islands' default white-hot centre saturates tiny
islands white (`hot: False`). The charge cue: Halo 4 lights plates / vents / a core with effects; Halo 1
draws weapon attachments at the hidden third-person gun -> radial cards built into the model at Halo 4's
own effect markers, faded by the charge (`glow_points`, now rotation-aware + `index`); the sight display one
card in its own plane (`at` + `normal`). Pellets invisible at 5.5 wu: the AR's tracer contrail recoloured,
a burst at range end AND on contact (`default_responses` detonate). Halo 4's pip strip read at its own
density (`ammo_meter` `native`: scaled to Halo 3 units the ten pips merged into one). FP down 2 units / back
1, the MELEE alone 2 more (`view_offset_anims`, ramped); muzzle flash 4.0 up, 2.0 forward (the
Suppressor's start), its life 0.075 -> 0.12 s (`own_particles`: the lifespan is in the shared particle).

**Hands:** a 2 cm right-hand offset that halved the hand-in-gun count on `overcharged` moved the hand OFF
Halo 4's grip (the count fell because the hand left the gun -- the user's video caught it); a ramped
offset reads as a slide. Final: 1 cm on fire_2 (the post-blast hold), set at once, the exit ramping out
(`hand_offset_anims` `ramp`). Halo 1 snaps between FP animations: any per-animation offset needs a ramp
where it meets another animation, or a recoil to hide in.

**Step 11:** donor the Jackal minor plasma pistol (Halo 1's Covenant sidearm), Halo 4 m020 ai\generic
#21, WDM 0.5 x 88 / 75 = 0.587 (balanced 0.503), drop 0.7 - 0.9 both; species skill on. Enhancer (its
keys): hands 'one', the bolt / charged card split of the plasma pistol (charged cards on the pellet /
trigger 1). Armed: Grunts, Jackals, Elites (user: works).

**Closing:** refs audit 0 problems; sound refs all own but the ammo pickup (KEEP: Halo 4's pickup tag is
empty); check 6 (`h1_tag_writes_proof`) 69 tags 0 changed; step 5b h1_role_compare `boltshot` (built rows:
`rounds_per_shot` / `reserve` model the auto-reload). **Tool changes (each opt-in, narrowed proofs
bo1-bo5 0 changed):** h1_fp_retarget `also_as`, `node_from`, hand_offset_anims `ramp`,
`view_offset_anims`; h1_h3_weapon_model glow_points rotations / `index` / `at` / `normal`; ammo_meter
`native`; h1_pickable_weapons sound_effects `own_particles`; h1_fp_hand_clip (read-only) absent-key fix.

### Halo 1: the LightRifle, wave C4 (2026-10-15, 7 dry boots + balanced + Armed on a30, PARALLEL with C5) -- a Halo 4 burst rifle whose zoom switches the shot, a polyart scope as coloured overlays

The whole weapon is `ports_h1/lightrifle.py`, on a copy of the Halo 1 PISTOL (also the yardstick): the Halo 4
route of the Suppressor on the burst + zoom shape of the Battle Rifle.

**Step 4a (user): the PISTOL.** Halo 4: ONE trigger, `latch-zoom` -- barrel 0 unzoomed = a 3-round burst
(5.33 plasma_fast a round at 30/s, recovery 0.3), barrel 1 zoomed = ONE `_combined` shot of 23.5 for 3
ROUNDS (2.5/s, its own projectile + large fly-by). Read the barrels, not the table (h3_weapon_values shows
barrel 0 only). Balanced = the pistol ratio per mode (burst 8.89 x 3, the cycle 0.524 s; scoped 39.2);
the Sniper ratio put Flood combat forms at 35 s (the sniper bullet's table).

**THE MODE SWITCH IS NOT PORTABLE.** Halo 1's zoom does not switch triggers. Option C (user's first
choice): the scoped shot on the GRENADE key -- weapon flag `secondary trigger overrides grenades` (Bungie's
own `digsite\weapons\smg` sets it with `prevents grenade throwing`, its spew burst on trigger 1). FAILED
(boot 1): the burst is a 1-tick CHARGE on trigger 0, and Halo 1 hands a charged trigger 0 to trigger 1
when a weapon has two (the plasma pistol, the Boltshot) -- the right trigger fired nothing, the grenade key
fired the single shot. Option A kept: the burst on both zoom levels, the scoped shot recorded as lost.
(The digsite layout -- single shot on the trigger, burst on the grenade key -- would work but inverts
Halo 4.)

**THE BURST'S ROUND COUNT FOLLOWS THE SPEW TIME (observation):** at 30/s a spew of 1 tick fired 1 round,
2 ticks 1, 3 ticks 2; the user tuned 0.15 s = exactly 3 (the Battle Rifle's 0.15 s at 10/s gave 3 too).
A rate card changes only the spacing inside the burst.

**THE FIRE SOUND WAS THE WRONG ONE (boot 1).** The event walk (h4_wwise.extract) follows an event's actions
one level into containers; the LightRifle fire event's real sounds sit behind a SWITCH of two blends of
layered randoms -- the walk reached only a quiet detail container (5 x 0.45 s at -25 dB rms). Eleven of the
event's 14 targets exist in no MCC bank. `obj_<hex id>` sound specs (h4_wwise.extract_object: every sound
under one container, children by the DirectParentID -- the first container id in a body, offset 6 in a
container / 31 in an embedded sound -- media by the bank's DIDX source id) took blend A's three layers + the
crack; blend B (2.2-3.2 s, heavier) left as the scoped shot's. Listen-check every Halo 4 fire event that
resolves to fewer / shorter sounds than expected.

**THE SCOPE IS POLYART.** Halo 4's forerunner_rifle_scope draws 3D vector meshes (polyart_asset: half-float
x / y / z / alpha + triangles + a camera), no bitmaps. `h4_polyart.py` rasterizes them through their camera;
`h4_polyart_scope.py` fits the frame to the user's zoomed screenshot (the CUI's parallax / zoom-in moves it:
scale x 1.05 / y 0.975, 112 px up, by maximising overlap with the screenshot's saturated orange), splits it
into four quadrant PNGs (a sheet px = 2 screen px). Drawn as coloured ZOOM GLYPHS (the Needle Rifle's
recipe, `zoom_glyphs` `image`) at hud_reticles 68-71 over a CLEAR mask (`scope` with no chud). Lessons:
- MCC draws a zoom overlay CENTRED ON ITS SPRITE -- the registration point is ignored (boot 3: all four
  quadrants stacked in the middle). Pin each crop to its full size (corner pixels) and place by `offset`:
  quadrant corner / 1.11 px a HUD unit - (2 - 256) x units a sheet px.
- `normalize` (alpha ^ gamma into RGB) kills faint texels: the 1/255 corner pins vanished, the top
  sprites shrank to 256 px and drew 250 px low (boot 5); 10/255 survives and stays invisible.
- Solid opaque panels / hard edges (boot 4) = MCC's near-opaque non-zero texels: `normalize` + gamma 1.6,
  x 0.6, the holo panels 0.45 (user: 'much better').
- The H1 blur outside the lens: `blur_outside` (an ellipse in mask texels: 1.09 px a texel tall, the 4:3
  box 1.453 wide); the top / bottom shade: `dark_bands`. An orange band fill in the glyphs (`--band`) was
  tried and reverted (user).

**The rest:** body = the colour map (grey, solid alpha) in the Boltshot's colour mode with the control
map's specular as alpha; the shipped glow material names a camo `sku_diff` -- drawn as additive islands
anyway. The scope hexagon = a display card (the Boltshot's); the FIRING LIGHT-UP (user: 'every Forerunner
weapon lights up') = glow cards + a flare faded by `A_out` (the pistol template's firing illumination,
0.08 s recovery); keep firing cards off pieces facing along the barrel (a 2.6x card on the hexagon reached
under the plate above it). The ammo HUD = Halo 4's three segment strips (`ammo_meter` `rows`: a column = one
3-round shot). Decimated 60 % (0.53 MiB with the cards, budget 0.6). FP: 2 units down; hands as built.

**Step 11:** donor the AR carriers (the Battle Rifle's precedent; the pistol's carriers are crewmen /
Flood / the suicidal Marine), Halo 4 m020 ai\generic #16, WDM 0.4 x 88 / 43.6 = 0.81 (balanced / 72.7 =
0.48), balanced drop 0.3 - 1.0 (the Magnum 0.6 - 0.8 on m020), species skill. Trap:
`ai_firing_profile.py` WITHOUT `--port` writes even with `--dry`. Enhancer (5d4e87c): hands 'two', tag_map
bolt + melee, no skips (a rate card moves only the spacing inside the burst), 18 cards from the Pistol.

**The Armed boot found three things the player never sees** (fixed, Armed 2 passed): NO third-person
muzzle flash on enemies (the FP `drop_off_axis` had dropped the pistol's 3P side flashes too ->
`keep_3p_off_axis`, `scale_3p` 1.5); the pistol template's grey-white full-screen HIT FLASH (not Halo 4's:
its impact_bullet_forerifle response is a 0.2 s 'early' ORANGE directional flash -> that colour / timing at a
15 % wash x 0.3); an INVISIBLE incoming bolt at 3000 wu/s (the AR tracer contrail recoloured, every round).
Check these three before any port's Armed boot.

**Closing:** refs audit 0; sound refs 0 BORROW (pickup KEEP: Halo 4's pickup event is in no bank); check 6
60 tags 0 changed; 5b h1_role_compare `lightrifle` (44 / 73 dps). **Tool changes (opt-in, narrowed proofs
lr1-lr5 0 changed):** h4_wwise.extract_object + h1_port_sounds `obj_`; ammo_meter `rows`; h1_pickable_weapons
zoom_glyphs `image` (+ a cell that grows), chud-less `scope` (+ `blur_outside`, `dark_bands`), sound_effects
`keep_3p_off_axis` / `scale_3p`; new h4_polyart.py / h4_polyart_scope.py (read-only art tools).

## Halo 3

Halo 3 has no single orchestrator; the order is:

    h3_make_saw.py          clone the donor weapon, projectile, effects
    h3_saw_wire_model.py    fp model
    h3_saw_world_model.py   world model      (h3_saw_world_revert.py undoes it)
    h3_saw_textures.py      bitmaps + shaders
    h3_saw_chud.py          clone the donor chud and repoint the weapon at it
    h3_meter_art.py         the ammo meter art          (step 7)
    h3_chud_sequence.py     which sprite that chud draws (step 7)
    h3_weapon_glyph.py      the pickup icon glyph        (step 8)
    h3_weapon_schematic.py  the HUD schematic            (step 8)
    h3_saw_pickup_icon.py   the weapon's five message string ids (step 8)
    h3_mcc_localization.py  the strings the game ACTUALLY shows  (step 8)
    h3_saw_animations.py    retime reload / ready         (step 9)
    saw_port_sounds.py --game h3 --write   own sounds + graphs + bank  (step 10)
    h3_build_map.py         build
    h3_saw_deploy.py        install + baseline, and --check
    h3_apply_saw_numbers.py balance rows onto the map
    h3_saw_tag_numbers.py   the port's own H4 numbers + step 4b fields (PORT_EK=h3)
    port_field_audit.py --game h3   nothing left to port            (step 4b)

### The traps, each of which cost a build

* **`tool build-cache-file` exits 0 when it crashes.** Two arguments, scenario and `pc`,
  and **backslashes** in the scenario path. Always build through `h3_build_map.py`, which
  demands the success string *and* an advanced mtime. See `h3-build-cache-file-trap`.
* **The cache builder deduplicates identical blocks.** A byte-identical clone shares its
  donor's blocks, so the clone must DIFFER before the build. `h3_saw_deploy.py --check`
  proves ownership from map data — run it after every build.
* **Run the tag tools for real.** `h3_saw_chud.py` had only ever been run dry once, so
  the weapon still pointed at the AR's chud.
* **`h3_apply_saw_numbers.py` restores from the baseline first.** Animation scaling is not
  idempotent; without the restore, "originals" silently keeps the balanced frame count.
* **`apply_field`'s `index` addresses the OUTERMOST block.** For chud Sequence Index that
  means index 0 silently rewrites a different widget. Use `h3_chud_sequence.py`.

### Step 7, the ammo meter

`ui\chud\bitmaps\ballistic_meters` is a sheet of sprites, each a **grid of ticks whose
cols x rows equals the magazine**, and the **blue channel is the tick's threshold**. The
largest Halo 3 ships is 60, so a bigger magazine needs a sprite drawn. Two rules, both
learned from in-game artefacts:

* **Blue is a property of the CELL, not the tick.** It runs as an unbroken staircase
  across the whole sprite; a gap left at 0 means "still loaded" and leaves an outline on
  spent ticks. Fill the field first, stamp the art over it without touching blue.
* **Pad downward and rightward**, the way Bungie does: the band boundary is the next
  tick's first row.

### Step 8, the icons

Read `mcc-localization-overrides-tags` **first**. The prompt's icon is a **character
inside the message string**, and MCC takes that string from
`data\UI\Localization\<LANG>_Halo3.bin`, a loose file — not from the map. The weapon tag's
**five** string ids (`pickup`, `swap`, `picked up`, `switch-to`, `switch-to from ai`)
choose which entry; the localization file supplies its text and glyph. Patch both.

Glyph and schematic are drawn from the port's **own geometry**, not by hand — see
`h3_weapon_glyph.py`, which documents the model-XML traps. The glyph box **is** the
on-screen size; borrow a shipped glyph's exact dimensions.

**THE TEXT RULE BELOW IS SUPERSEDED for Halo 3 and ODST** -- both ports now bring
their own lines (see **Step 8, the text**), so nothing is borrowed and nothing has to
be blanked. It still describes Halo 2 and Halo 1, which have not been converted, and
it remains the right rule for any line a port does NOT own.

**The rule for the TEXT: blank it, do not rename it.** A port has no lines of its own, so
rewording one means taking a live weapon's — and that weapon is then wrong for the rest of
the game. The lines that matter carry a SYMBOL rather than a name (the pickup prompt is
`<button> to pick up <glyph>`), and those are already right for any weapon, because they
never say what it is. So:

* a line that would have to be **borrowed** is blanked — filled with SPACES, which keeps
  the entry, its offset and the file's length, and shows as nothing;
* a line that carries only a symbol is **left alone**;
* a line the port genuinely OWNS may be reworded. That is the Halo 2 case below: the cut
  donor came with its own three lines and nothing else uses them.

Blanking by terminating the string early does NOT work — the freed bytes become new
entries and renumber every string after them. That is the "CARNAGE REPORT" failure.

### Step 9, animation timing

`h3_saw_animations.py` retimes by NAME and clones **both** graphs the weapon references
(masterchief and dervish — fixing one leaves the other shared). Build at the **longest**
timing needed, because the patcher can only shorten. See `h3-animation-format` for the
format and its three traps.

---

## Halo 3: ODST

ODST is the same engine and measures out almost identically to Halo 3: the Assault
Rifle's first-person and world **skeletons are byte-identical** between the two kits
(node list, default transforms, every marker), its projectile and damage effect tags are
byte-identical files, and its reload is the same 58 frames. So the whole Halo 3 pipeline
runs against it — `h3_kit.py` selects the kit from `PORT_EK`, and every tool asks it:

    set PORT_EK=odst

and the balance comes out the same to the last decimal (velocity 75, magazine 72,
reload ×0.851562). That is not a copy: ODST is measured from its own tags and lands
there because its Assault Rifle is Halo 3's.

### The pipeline, end to end

Every tool takes the kit from `PORT_EK`, so set it once:

    set PORT_EK=odst

    h3_make_saw.py          clone the weapon, projectile, damage effect   (step 3)
    saw_to_jms_h3.py        the JMS, from ODST's OWN skeleton XML x2      (step 1)
    tool render <dir> final both models -- fp and saw_3p
    h3_saw_textures.py      bitmaps + shaders, BOTH model folders         (step 2)
    tool render <dir> final AGAIN: a shader that arrives after a render is not in it
    h3_saw_world_model.py   world model, hlmt, weapon -> hlmt             (step 1)
    h3_saw_wire_model.py    fp model                                      (step 1)
    h3_region_name.py       'default' -> 'standard' on all FOUR models -- LAST, because
                            the two wiring steps re-render
    h3_saw_tag_numbers.py   the port's own H4 numbers into its tags       (step 4, 4b)
    port_field_audit.py --game odst   nothing left to port              (step 4b)
    h3_saw_chud.py          clone the chud, low-ammo 18                   (step 7)
    h3_sprite_box.py        give a spare sprite a REAL box on blank canvas (steps 7, 8)
    h3_meter_art.py         the 72-tick meter, sprite 1                   (step 7)
    h3_chud_sequence.py     point the chud at meter 1 and schematic 10
    h3_weapon_schematic.py  the schematic, sprite 10                      (step 8)
    h3_weapon_glyph.py      the pickup glyph, 0xE04A                      (step 8)
    h3_port_messages.py     its own messages, all languages, --repoint    (step 8)
    h3_saw_animations.py    retime reload/ready on the odst_recon graph   (step 9)
    saw_port_sounds.py --game odst --write  own sounds + graph + bank    (step 10)
    make_port_catalog_odst.py --write                                     (step 5)
    <place it in Sapien AND give it a starting profile>
    odst_ek_build.py --build sc150
    h3_chunk_check.py       NINE chunks, all backed -- before any launch
    h3_saw_deploy.py --install [--baseline]

Scale is **1.0**, and the two skeleton XMLs come from ODST's own Assault Rifle
(`fp_assault_rifle.render_model` and `assault_rifle.render_model`) -- byte-identical to
Halo 3's, but export them from the kit you are building in.

### THE STEP THAT GETS IT INTO THE MAP

**Place the weapon in Sapien AND give it a Player Starting Profile. The placement alone
is not enough — confirmed in game.** The first rebuild, with a Sapien placement only,
produced no geometry; adding the profile produced all of it.

This is the single most expensive thing to rediscover, because **a build that gathers no
geometry still produces every tag and reads as success**: the weapon, both render models,
the animation graph, the projectile and the HUD are all present and correct in the map,
and there is simply nothing to draw. `tool` says nothing about it — no error, no warning,
not one mention of the tag in a 134 KB log.

So always, before spending a launch:

    h3_chunk_check.py sc150 --game "Halo 3: ODST" "rifle\saw"

Nine rows, all backed (fp model, world model, animation graph, 2 bitmaps, 4 shaders).
No rows means the scenario edit did not reach the build, whatever the build reported.

Residency then needs nothing: `tool` marks the port `X` in GLOBAL by itself, exactly as
it does for a stock weapon, so there is no `--load-always` fold.

### Editing the scenario by hand does NOT work, and here is why

Three headless routes were tried and all three produced tags with zero geometry — a
profile slot, a real weapon-palette entry, and a real placement pointed at it. Each was a
valid edit that parsed and read back. What Sapien and Guerilla write is evidently more
than a path: the equipment work reached the same conclusion in its own words, that a
hand-made entry lacks "the position, BSP attachment, folder and unique ID" Sapien writes.

**And the scenario tag's weapon palette is not the one that counts.** `tool` states it:

    WARNING (group_postprocessing 'levels\atlas\sc150\sc150.scenario')
    'scenario_weapon_block' referenced by resource
    'levels\atlas\sc150\resources\sc150.scenario_weapons_resource'
    that is about to be stomped over isn't empty!

Fifteen blocks — weapons, vehicles, equipment, scenery, decals, trigger volumes and more
— live in `resources\<level>.scenario_*_resource` and STOMP the copy inside the
`.scenario` at build time. sc150's scenario tag lists 23 weapons; the resource lists the
17 the map really has. This is very likely what `h3-import-weapon-recipe` recorded as a
Guerilla palette entry getting "neither geometry nor residency": the edit was discarded
before it could do anything. `odst_saw_place.py` reads the real palette and placements.

### What ODST does NOT share with Halo 3

* **One animation graph, not two.** Halo 3's Assault Rifle names the Master Chief's and
  the Dervish's; ODST's names `odst_recon` twice, so there is one graph to clone and the
  repoint rewrites both references to it.
* **The HUD sheets have no free slots.** `ballistic_meters` has 18 sequences with one
  free (a two-row box) and `weapon_scematics` has 27 whose three spare ones are 8x8
  stubs. Halo 3 took the automag's schematic, which is free there because the automag
  never appears in Halo 3 — in ODST it is the starting pistol.
  Both sheets stop using canvas around y=400 and no sequence covers the ~100 blank rows
  below, so `h3_sprite_box.py` gives a spare sequence a REAL box down there. Nothing is
  taken from a weapon that is in the game. Two traps: the sprite records are **not
  4-aligned**, and while an edge is a pixel count over the sheet size and can be rebuilt
  exactly, a **registration point can be a half pixel**, so it must be read from the tag.
* **Five fonts, not four.** ODST inserted `fixedsys-pda13`, so its HUD font is index 3
  where Halo 3's is 2 (both have 144 glyphs, which is how to tell). Its packages are also
  ~50 KB larger and packed differently, so Halo 3's codepoint sorts into a full ODST
  block. The port takes **0xE04A**, one of only six that fit.
* **Assembly's ODST `chdt` plugin renames things.** `Low Ammo Loaded Threshold` is
  `Low Clip Cutoff` (same offset), and `Widget Collections` is `HUD Widgets`. Asking for
  the Halo 3 name returns None for both weapons, and `None == None` reads as "the clone
  owns its blocks" — a deduplication check that silently always passes.
* **ODST has ammo pickups** where Halo 3 has none: its Assault Rifle references
  `objects\powerups\assault_rifle_ammo`, so the port inherits one as built.

### Step 6, the ammo pickup: DONE, and it is the second game to have it

ODST HAS ammo pickups where Halo 3 has none, so the port gets the same dropdown Halo 1
has. The layout was MEASURED rather than assumed: a magazine element is 20 bytes --
`Rounds` i16 at +0, then the equipment tag reference at **+4** (its group 4CC reads
`piqe`, eqip backwards), whose datum sits at +0x10. So `ref_offset` is 4 and the patcher
writes at `ref_offset + 0xC` as it does everywhere.

Eight items, read off a built map: assault rifle, battle rifle, needler, pistol, rocket
launcher, shotgun, SMG and sniper rifle ammo. Each records which of the 11 missions
carries it, because pickup items are PER MAP; a mission that lacks one is not an error,
the patcher falls back to the item the port was built with.

**One patcher bug had to be fixed for this to work anywhere but Halo 1.**
`_tag_id_by_name` walked Halo 1's tag index and reached for `m.tag_count`, which no
Halo 3-era map object has -- so it raised AttributeError rather than returning a datum,
and the ammo step was quietly Halo-1-only. Halo 3 and later already carry each tag's
`ident` in the parsed tag table, so it asks that first.

### Step 8 in ODST: DONE, and it owns its lines

The port brings its own five messages rather than taking a weapon's -- see
**Step 8, the text** below, which is the general method for every game. Confirmed in
game: its own glyph on three prompts and "Picked up a SAW" on the confirmation, in all
twelve languages.

Its GLYPH is its own too, at **0xE04A**. ODST needs a different codepoint AND a
different font index from Halo 3: its packages hold FIVE fonts (it inserted
`fixedsys-pda13`), so the HUD font is index 3 rather than 2, and they are ~50 KB larger
and packed differently, so Halo 3's 0xE06A sorts into a full block. Six codepoints fit;
this takes the first.

---

## Halo 2

The donor is `objects\weapons\rifle\gpmg`, a **cut** Bungie LMG that is in no scenario's
palette but still owns its own first-person model, HUD and the full set of pickup message
string ids. Nothing live has to be hijacked -- the ceiling the Halo 3 port ran into does not
exist here. See `halo2-weapon-port-donor`.

Halo 2 is the easiest of the three to READ (the kit hands back Bungie's own source for
geometry and collision) and the hardest to WRITE: there is no XML importer, so every tag
edit is a byte edit, and the animation format had to be decoded before the reload could be
retimed.

### The pipeline, end to end

Each of these is one script, and each proves its own work before it keeps it.

    saw_to_jms_h2.py <storm_lmg_rm.xml>            1. geometry onto the donor's skeleton
    tool render objects\weapons\rifle\saw          and \saw\fp_saw
    h2_saw_textures.py                             2. skin, bump maps, shaders
    h2_saw_weapon.py                               3. its own weapon, projectile, effects
    h2_saw_numbers.py                              4. the balance numbers
    h2_saw_collision.py --write                    5. its own collision hull
    h2_saw_meter.py                                7. a 72-round ammo meter
    h2_saw_hud_plate.py --write                       the HUD's weapon symbol
    h2_saw_reticle.py --write                         the crosshair, ported from H4
    h2_saw_scope.py --write                           blank the scope widgets
    h2_saw_glyph.py --write                        8. a pickup icon of its own
    h2_saw_messages.py                                the pickup prompts
    h2_saw_animations.py --force                   9. its own animation graphs
    h2_anim_retime.py <graph> reloads 128 --write     and its own reload length
    h2_saw_yardstick.py --write                    4b. GPMG / turret leftovers -> the SMG (then
                                                      h2_saw_numbers.py again)
    h2_saw_sounds.py --write                      10. its own sounds (classic), graphs repointed
    h2_saw_place.py --level <name> --build --deploy   put it in the player's hands

Two tools underneath all of it:

    h2_tagref.py   <tag> --set <class> <old> <new>   repoint a reference
    h2_tagfield.py <tag> --set "<field>" <value>     change a number

### Step 1, geometry

`tool extract-render-data <render_model>` unzips Bungie's ORIGINAL .jms out of the tag, so
the skeleton, rest pose, markers and material strings are the authored file rather than
something reconstructed from a tag dump. (H4's `extract-import-info` finds nothing, which is
why the other two ports work harder here.)

* **JMS 8210 is not JMS 8200.** Reclaimer writes Halo 1's and only that, so `write_jms`
  cannot be aimed at Halo 2: nodes carry a parent index instead of child/sibling links,
  triangles name only a material, and there is **no REGIONS section at all** -- region and
  permutation are parsed out of the material's second line, `(1) base gun`. `h2_jms.py`
  implements it and proves it by writing all four extracted files back byte for byte.
* **Node translations are absolute**, not parent-relative as in Halo 1.
* **JMS v is 1 - the tag's v**, measured against the donor rather than assumed.
* Anchor the mesh on the donor's `right_hand` marker: the H4 weapons are authored with the
  root bone ON the grip, so the two grips coincide and the hand the animation drives is
  right by construction. Scale is settled by the grip-to-foregrip span; for the SAW into the
  GPMG that came out at 1.0, with the left hand landing within half a unit unaided.
* **Halo 2 fires from the barrel marker the weapon tag names**, and for the GPMG that is
  `primary_trigger`, not a `muzzle_flash` -- there is no muzzle marker in the file at all.
  It sits 32 units out, past the end of a shorter gun, so it has to be moved.

**Check the dump before you trust it.** The H4 render model can be exported more than once
and the exports are NOT interchangeable: the SAW's full dump is 10736 vertices in four parts,
a sparser one is 7916 in two, and the render method indices mean different things in each --
part 0 is a twelve-index decal sheet in one and the entire gun in the other. Feed the wrong
one in and the part map drops the body, keeps a seven-index scrap, and builds a
**two-triangle weapon** without a single error from any tool in the chain. The converter now
refuses anything under a thousand triangles. Keep the dump somewhere durable: this one was
living in `%TEMP%`.

`tool render` reports far fewer triangles than it was given (13836 -> 8361 for the SAW). That
is welding, not loss: the surface area is 98.4% of what went in. Check the area, not the
count.

### Step 2, textures and shaders

`h2_saw_textures.py` decodes the Halo 4 maps, imports them and repoints the shaders.

* **A Halo 2 bump map is a HEIGHT map**, not a normal map (`usage = height map`, bump height
  4.0). Halo 4's is tangent-space normals, so it has to be integrated back into heights --
  Poisson/FFT, then a high pass, then a gain fitted against Bungie's own slope statistics.
* The p8-bump format is gone in MCC; x8r8g8b8 is what imports.
* **h4_bitmap's pixel offset depends on the format**: the marker is chain+8 for dxt1,
  chain+0 for a single-mip dxt5, and **chain+16 for dxn**. Score the result for roughness
  rather than trusting the first offset that decodes.

### Step 3, what the port must OWN

A port that shares a tag with a live weapon changes that weapon when it is tuned. Clone and
repoint: the projectile, both damage effects, the firing effect, and the animation graphs.

**Borrowed effects bring their own conventions, and their own owners.** Two caught here:

* the GPMG fires the WARTHOG CHAINGUN's muzzle flash, smoke and casings, with the turret's
  muzzle light, at 20 rounds a second. The port takes the SMG's firing effect instead;
* the projectile kept `effects\materials\objects\weapons\warthog_chaingun`, the turret's
  IMPACT set, which reads in game as an uncharacteristic fireball on every wall hit. That is
  a separate reference from the firing effect and has to be repointed separately.

**A borrowed effect is authored around its donor's marker.** The port's muzzle flash sat
above the muzzle and the marker was not at fault -- it measured 0.07 units off the centre of
the barrel opening. Bungie's SMG carries its barrel marker **1.40 units BELOW its own bore**,
so the effect is drawn that far above where it is emitted. Measure the donor's marker against
the donor's bore and adopt the difference (the GPMG's own is 3.72, so the number is per
weapon, not per game).

### Step 4, the numbers

`h2_tagfield.py`. The Assembly plugins cannot be used: they give offsets in the CACHE layout
and a loose tag is laid out differently (the weapon's root struct is 0x31C in a cache and
0x5F4 on disk, and no arithmetic gets from one to the other). So the offset is FOUND and the
finding is PROVED -- read what tool.exe reports, list every place in the tag whose bytes
decode to that, probe each **into a copy**, and keep the one where that field changed and
nothing else did. Results cache in `h2_tagfield_offsets.json`.

* **Angles are RADIANS in the file and DEGREES in the export.** Searching for the 1.0 that
  tool prints for a minimum error finds nothing; 0.0174533 finds it on the nose.
* **A field reading zero cannot be found this way** -- padding reads zero too. Locate it in a
  tag of the same group that has a non-zero one, and apply the same offset WITHIN the block
  element. (The element layout is shared; the absolute offset is not.)
* Probe into a copy, never the tag. An interrupted probe once left `saw.weapon` unloadable.

### Step 5, collision

`tool collision` on the render mesh asserts in `reduce_collision_geometry.cpp`
(`next_edge_index != edge_index`): a Halo 2 hull has to be closed, convex-ish and simple, and
a weapon's render mesh is none of those. **Do not try to build one from the port's geometry.**

What works is `tool extract-collision-data <donor>`, which unzips Bungie's own authored hull
out of the donor tag exactly as `extract-render-data` unzips the render source, and then
scaling it. Every property that makes it compile is kept and only the size changes. Scale it
**per axis**, each axis's ratio of the two render meshes clamped to [1.0, 1.25], about the
hull's own centre so it does not drift off the grip: one factor big enough for the port's
width would otherwise stretch the hull a third of a gun past the muzzle. The SAW came out
[1.0, 1.25, 1.11] -- wider and taller than the GPMG, but shorter.

### Steps 6 and 7, ammo and the HUD

**Step 6 is n/a in Halo 2**, as in Halo 3: there are no ammo items, you top up from dropped
weapons. A weapon's nested `magazines` block is the physical magazine thrown out during a
reload, not a pickup.

**The ammo meter.** Halo 2 draws the readout as ONE bitmap of tick art, revealed as the
magazine empties, so the tick count is purely a property of the art. Bungie's, measured:

    battle_rifle_meter  197x34   2 rows of 18 = 36   tick 6px wide, row pitch 17
    smg_meter           198x42   3 rows of 20 = 60   tick 6px wide, row pitch 14

The tick is 6 pixels wide in both; the magazine changes the rows and their spacing. Keep the
donor's canvas so the widget does not move. **And blue is the threshold, and a property of
the CELL** -- see the rule at the top of this file, which cost a fix in two games.

**The HUD's own weapon symbol** is not a glyph, and not the `backpack` widget (that is the
small stowed icon at the left of the group). The big symbol beside the ammo is painted into
`ui\hud\bitmaps\new_hud\backgrounds\<weapon>_bkd`, a 206x38 plate per weapon, which is why a
port wearing the donor's plate shows the donor's gun whatever else is fixed.

There is no empty plate, so rebuild one: the silhouette sits in x 105..190, y 5..33, and the
background behind it is a smooth gradient, so interpolate each row between the pixels either
side of the box. (Averaging other weapons' plates together instead leaves the seams of
whatever each one covered.) Then draw the port's weapon the way Bungie draws theirs:

* the symbol is **flat**, a hard bright cyan silhouette, not a shaded picture of the gun.
  Shading it by its own geometry gives a dim mottled shape that sinks into the plate;
* **the gradient belongs to the SYMBOL, not the plate**, and this is the part that makes it
  look drawn rather than pasted. It runs from about 225 at whatever row the weapon starts on
  to about 7 at the row it ends on, with blue near constant at 215. The shotgun proves it:
  its drawing spans rows 4..24 and ramps 218..14 over exactly that, while the plate underneath
  runs 189..22. Take the two ENDS of the donor's ramp and stretch them over the port's own
  extent. Do NOT sample the donor row by row -- the plate's own green is 222 at the top, so
  every background pixel there passes for symbol and the port's top comes out plate coloured,
  a symbol that fades exactly where it should be brightest;
* **alpha tells you nothing** about what is symbol and what is plate -- it is 190 or above
  across the whole image. Green plus blue separates them, the plate being flat dark green;
* every shipped symbol **fills the box top to bottom**, so fit the width and then stretch
  vertically to fill;
* close the one-pixel holes: a 13836-triangle gun at 29 rows breaks into slivers, and a sliver
  reads as a scratch, not a gun.

Write only image 0. Stacking all four of the donor's images into one colour plate makes tool
import a single 206x152 bitmap, and the widget asks for sequence 0 at every screen size anyway.

**The crosshair ports across from Halo 4.** The port otherwise wears the donor's, and a donor
picked for its skeleton has no reason to have a suitable one -- the SAW came out with the cut
GPMG's broken circle and tick marks, which reads as a scope sight. H4EK specifies the real one
exactly: `ui\hud\weapons\<race>\<weapon>\<weapon>.cui_screen` names each widget's bitmap and
carries `prop_left/top/width/height`, `prop_bitmap_flipx/y` and `prop_opacity`. The SAW's is
four mirrored copies of `img_saw_quarter` (an L bracket, 32x32 at +-4 / +-36) plus four 8x8
ticks at 55% opacity. Decode with `h4_bitmap.py`, mirror and place at Halo 4's own offsets.

Keep the TARGET game's colour convention: Halo 2 reticles are flat blue with the shape in the
alpha and the widget's shader tints them (green for a friendly, grey for an invincible
target), so the H4 art supplies coverage only. Give the port its **own one-image bitmap**
rather than a sequence in the shared sheet, so no other weapon's reticle can move -- which
changes the widget's sequence index to 0 on three widgets x three screen sizes.

Size it against the donor's SHAPE, not its box: the donor is a circle inscribed in its image,
and a bracket frame drawn to the same footprint reaches into corners the circle never touches.
0.6 of the footprint was right for the SAW.

**The scope widgets DO draw, whatever the flags say.** A HUD cloned from a zooming weapon
carries `scope_mask`, four bracket crosshairs, `2x` and `distance_meter`, all gated on
`[Y] unit flags` = *unit is zoomed* while the port's `magnification levels` is 0 -- so by the
tag's own logic none can appear, and in game they did. Do not argue with it: give them a blank
bitmap (one transparent image) and set all three sequence indices on each to 0.

### Step 8, the icons and the text

See "The icon supply" below for the general rule. In Halo 2 specifically:

* `tool replace-font-char <font> <tiff> <utf16>` writes the glyph, so the codec never has to
  be cracked -- but **the codepoint argument is DECIMAL**. Hex is read as 0 and silently
  rewrites the notdef glyph, which turns every unmapped character in the game into a SAW;
* the tool will not ADD a codepoint, so `h2_font_add.py` creates the entry first;
* eight English fonts draw HUD text and all eight need the glyph;
* **MCC reads `data\UI\Localization\<LANG>_Halo2.bin`, not the map.** The index is (hash,
  offset) pairs, NOT ordinal like Halo 3, so patch by CONTENT: find the line, pad with SPACES
  never NUL, and keep the length, entry count and offsets invariant;
* the prompt sets are INTERLEAVED, not one set per weapon. Getting "picked up" right does not
  mean "take from ally" is right; check each.

### Step 9, ANIMATION

The long one. A port inherits the donor's animation graph, which means it inherits the
donor's reload -- the SAW reloaded at the sniper rifle's 2.4 seconds instead of its own 4.3 --
and, until Halo 2's animation format was decoded, that could not be changed. It can now.

#### Own the graphs, and fix the sounds

Clone **both** graphs (a weapon names one per player species) and repoint the weapon, so
retiming the port cannot retime the weapon it was cloned from. Then fix the `snd!` references:
they are the donor's, so the port reloads with the donor's noises. Point them at the balance
donor's equivalents one for one -- the SAW took the SMG's reload, ready, melee and posing.

#### The format, codec 3

Verified to the byte on **355 animations across every character graph H2EK ships**, so it is
a rule rather than a sample.

Finding the data: the blob is NOT pointed at from the element. It sits in the child data
immediately after the animation's pooled NAME, which has no terminator, so find the name and
step past it; the element's `+0x34` gives its length.

    element   +0x13 node count   +0x14 frame count   +0x34 frame data size
              +0x50 tail size    +0x54 B

    blob      32-byte header: (1, b, c, 1), then X = 32 + 8b and Y = X + 12c
              table A   b packed i16 quaternions   STATIC rotations
              table B   c float3                   STATIC translations
              52-byte sub-header:
                  +0x04 codec, +0x05 R, +0x06 T   R/T = nodes with an ANIMATED rotation
                  +0x10 A = 32 + R*f*8            or translation
                  +0x14 B = A + T*f*12
                  +0x18 f*8, +0x1C f*12, +0x20 f*4
              [0,A)   R x f packed i16 quaternions
              [A,B)   T x f float3 translations, then a 32-byte TRAILER
              [B,end) a 32-byte HEADER (codec 2, R, T, its own A, B, strides), then
                      R x f FLOAT quaternions and T x f float3 translations

Both halves are node-major: all of one node's frames, then the next node's.

**Size does not track frame count, it tracks how many nodes MOVE** -- b swings from 1 to 33
between animations. Believing otherwise is what made this look keyframe-compressed for a
while; it is not, it is full frame.

**The 32 bytes are at the END of the compressed half and the START of the uncompressed one.**
Getting that backwards shifts every quaternion by four frames and `build-cache-file` asserts
in `uncompressed_static_data_codec.h` on `node < header->total_rotated_nodes`. Two
measurements settle it: the packed quaternions read as unit-length more often from offset 0
than from 32, and -- decisively, since both halves hold the same rotations -- comparing them
node by node gives a mean error three times lower at 0.

Codecs 4, 6 and 8 (`put_away`, `sprint`, `throw_grenade`, `pitch_and_turn`) are undecoded. No
reload uses them.

#### What recompression does, and why it is needed

`tool model-animation-reset-compression` rebuilds the compressed half from the uncompressed
one -- but only for the animations it judges worth recompressing. Three in-game results pin
it down, after two wrong readings on the way:

    resampled data, not recompressed   the reload jerked at its start and its end
    the same, recompressed             smooth and correct
    ZEROS, recompressed                FROZEN: the hands held one pose throughout

Zeros surviving says tool did not replace them; the same data going jerky-to-smooth says it
did. So the compressed half is a PLACEHOLDER that this side need not understand, but it must
not be degenerate or it will be kept. Write a quantisation of the resampled uncompressed data
and let Bungie's compressor do the compressing.

**It TRUNCATES THE TAG IT IS GIVEN TO 64 BYTES WHEN IT ASSERTS**, and leaves a `tool.exe`
running that holds the file open -- later writes fail with "Device or resource busy", further
runs return nothing, and on the user's desktop a crash dialog waits to be dismissed. It
destroyed two graphs before that was understood. **Never point it at a real tag**: write to a
scratch tag, run there, copy back only a whole result, and kill the hung process on failure.
Keep failing attempts few; each one costs the person at the keyboard a dialog.

#### Retiming

`h2_anim_retime.py <graph> reloads <frames> --write`. Rewrite the uncompressed half, fill the
compressed half, hand it to tool.exe, and write only what comes back whole. Resample with the
ENDS PINNED -- new frame t reads old position `t*(f-1)/(new-1)` -- so the first and last poses
are the animator's exactly. Align the sign of each quaternion pair before blending.

**Nodes that do not move are sampled, not blended.** Interpolating a node made of nothing but
float noise is wrong on its own terms: `_qlerp` normalises, which erases the noise. The
threshold is measured, not picked -- across the two reload graphs the nodes fall into two
populations with nothing between them (Dervish: seven at ~1e-7 and one at 1.2e-4; Chief:
nothing below 1.1e-2), so 1e-3 sits in the gap with two orders of magnitude of margin.

**Not every graph accepts interpolated TRANSLATIONS.** The Chief's retimes with everything
interpolated; the Dervish's asserts, and it is the translations it objects to -- hold the
rotations and interpolate the translations and it asserts, do the reverse and it recompresses.
It is not the translation data, which is numerically identical in the two graphs. What differs
is how the whole animation scores once they are interpolated. So **ask rather than guess**:
build the best version, offer it, fall back to held translations only if refused, and report
which was used.

Ruled out on the way, one run each, so none of it is repeated:

    the graph itself        untouched recompresses, and so does an identity retime
    the length              96, 128 and 144 assert, and 36 does too -- not per-frame deltas
    the trailer             clearing it instead of copying it asserts
    the placeholder         tiling the original compressed bytes asserts; only ZEROS pass,
                            and they pass by being SKIPPED, which is the frozen weapon
    one of a pair           retiming both byte-identical reloads asserts
    still nodes             holding all eight of the Dervish's non-moving rotations asserts
    per-axis                holding a node's still axes and blending its moving one is
                            refused on BOTH graphs, including the one that takes plain
                            blending -- a mixture is worse than either
    per-node                blending only the nodes that visibly move is refused as well

**Held translations step, and every species' graph must still be the same length.** Sampling
means the position advances in steps, and a fractional ratio steps raggedly: 72 to 128
alternates one- and two-frame holds, which in game reads as the weapon jittering rather than
settling at the end of the reload. A whole multiple (72 to 144) evens it out -- and costs that
species a different reload duration, which is worse than the jitter. Nor can the reload card
even them up afterwards: `halo3_reload.scale_reload` rewrites the FRAME COUNT and never the
data, so shortening 144 to 128 plays 128 of 144 frames and truncates the tail, which is where
the weapon settles.

**Event frames are not scaled yet.** The sound and effect keys live in child blocks and
matching each chunk to its animation in a loose tag has not been done. It does not bite on a
reload whose only key is at frame 1, which is frame 1 at any length.

#### How long the reload should be

Measured from each kit's own first-person graphs (frames at 30fps):

    H4 SAW 128   H4 AR 68   H3 AR 58   H3 SMG 50   H2 SMG 50

    H4 -> H3 via the assault rifle   58/68 = 0.853
    H3 -> H2 via the SMG             50/50 = 1.000
    balanced Halo 2 reload           109 frames, 3.64s

Build the tag at the SAW's **own 128** (4.27s), because the card can only shorten, and let the
Reload Time card take it to 109 -- the same multiplier the Halo 3 port arrived at
independently, which is a good check on the chain.

#### A weapon has one first-person MODEL per species

Not just one set of animations: the `first person` block holds an element for each, and each
names its own model. A port starts with both pointing at the same one, so two rigs that hold
the weapon differently -- 42-node Spartan, 36-node Elite -- get the same position in the view.
Build a second model at its own offset (`saw_to_jms_h2.py --fp-sub=NAME --fp-nudge=x,y,z`),
clone the `.model` tag, point it at the new render model, and retarget that ONE entry, which
needs an `nth=` aware reference edit because the two paths are identical until one changes.

The two graphs are NOT interchangeable, so a species whose graph will not retime keeps the
donor's length; it cannot borrow the other's.

### Editing tags

There is no XML importer, so tag edits are byte edits. A tag reference is 16 bytes with the
class 4CC REVERSED, and the path is pooled elsewhere -- and since the file is laid out in
strict FIELD order, a struct's paths are interleaved with its child blocks, so which record
owns which string cannot be recovered from the bytes alone. `h2_tagref.py` therefore edits
**by class and current path**, refuses anything ambiguous, and re-exports with tool.exe
afterwards to prove the list changed in exactly one place, restoring the file if it did not.

**Write the length field BEFORE the string.** A record is not necessarily before the string it
names -- in a HUD the last scope widget's record sits two kilobytes past the first pooled path
-- so replacing a path with a shorter one moves that record out from under its own offset. Do
the lengths first, which cannot move anything, then the strings from the end backwards.

`tool verify-tag-load` proves nothing: it is silent for a good tag AND for one that does not
exist.

---

## Halo Reach

**COMPLETE 2026-09-30 -- all nine steps built and confirmed in game** on m20: world model
held, dropped and ally-held; first person; own HUD icon and 72-tick meter with the low-ammo
flash at 18; pickup icon on the ground and on trade; reload and ready retimed with their
events; muzzle flash on the barrel. The status table and what stays open are at the end of
the Reach sections ("Reach port status").

*Scoped 2026-09-29:* Reach was expected to be ODST-adjacent. It is
not: it is the *Halo 2* shape of first person laid over a Halo 3 era toolchain, and the
two halves of the port that usually cost the most -- the models and the icon -- move in
opposite directions. Everything below is measured from HREK and the live game, not
assumed from the other kits.

### The kit

    set PORT_EK=reach

`h3_kit.py` knows HREK, so the Halo 3 tools resolve against it -- tags, data, tool,
the `haloreach` game folder for the live font packages, and the HUD font index. Anything
that genuinely DIFFERS per kit now goes through `h3_kit.per_kit()`, which **refuses** for
a kit whose value has not been measured instead of quietly handing back Halo 3's. That is
deliberate: a silent fallback is how the ODST balance table returned nothing, how the
ammo step became Halo 1 only, and how a HUD check passed by comparing None to None.

`F:\SteamLibrary\steamapps\common\HREK` is a full kit: `tool.exe`, `sapien.exe`,
`Foundation.exe` (Guerilla's replacement), 305 verbs. It already has a build/install
pipeline in `reach_ek_build.py`, and `reach_place.py` already knows how to append
placements and grow a palette -- both confirmed in game on m20.

Two verb signatures differ from Halo 3 and will silently do the wrong thing:

    build-cache-file <scenario> <platform> <target-language> ...   (Halo 3: two args)
    render <source-directory> <final-or-draft>                     (Halo 3: one arg)

Missions are `m10 m20 m30 m35 m45 m50 m52 m60 m70 m70_bonus`. The kit also carries `m05`
and `m70_a`, which the game does not run -- the same trap `reach_ek_build.py` already
avoids by taking its list from halo.json.

### What is CHEAPER than ODST

**One render model, not two.** Reach has no per-weapon first-person render model. There
is a single shared arms model, `objects\characters\spartans\fp\fp.render_model`, and the
weapon's `first person` block pairs the weapon's OWN WORLD MODEL with a per-species
animation graph. Read straight out of the Assault Rifle's tag references:

    model  objects\weapons\rifle\assault_rifle\assault_rifle
    jmad   objects\characters\spartans\fp\weapons\rifle\fp_assault_rifle
    model  objects\weapons\rifle\assault_rifle\assault_rifle      <- the SAME model
    jmad   objects\characters\elite\fp\weapons\rifle\fp_assault_rifle

So step 1 builds one model instead of fp + world, and the whole `h3_saw_wire_model.py` /
`h3_saw_world_model.py` split collapses. It also means the region-name trap
(`'default'` vs `'standard'`) applies to ONE model, not four.

**The icon is nearly free, and that is the surprise.** Step 8's glyph half cost Halo 3 a
cracked codec. Reach needs none of it:

* `haloreach\maps\fonts\font_package_icon*.bin` ships LOOSE in the game folder, exactly
  as Halo 3's does -- so a glyph shows up with **no map rebuild**;
* the format is identical. `h3_font_package.py`'s block reader parses all four 0xC000
  regions of Reach's package with every bound sane, and **`h3_font_codec.decode` decodes
  all 353 Reach glyphs with zero failures** (Halo 3: 291, also zero). The opcode stream is
  the same one.
* there is room: **24,208 free bytes** in the last block and **229 unused private-use
  codepoints** below 0xE160 (Reach uses 0xE006..0xE143 across 6 fonts).

So `h3_weapon_glyph.py` should reach Reach on a kit switch rather than a rewrite.

**The HUD font is index 3 -- measured, not deduced.** The package header NAMES its fonts,
which settles a question that cost time in Halo 3 and ODST. Reach's six, in order:

    0  icon\fixedsys-9            3  icon\fixedsys_hud-15     <- the HUD font
    1  icon\fixedsys_ui-title     4  icon\fixedsys_ui-15
    2  icon\fixedsys_hud-number   5  icon\fixedsys_ui-16

Halo 3's four are `fixedsys-9`, `fixedsys-ui`, `fixedsys-hud`, `fixedsys-term`, so its HUD
font is 2 -- and Reach's index 2 is `hud-number`, a SEPARATE face for the ammo counter that
Halo 3 does not have. Carrying Halo 3's 2 across would put the glyph in the digits font.

**Step 8's text half ports outright.** HREK has the same three verbs as H3EK and H3ODSTEK
-- `extract-unicode-strings`, `strings`, `strings-localized` -- and the same string list
at the same path, `tags\ui\hud\hud_messages.multilingual_unicode_string_list`. So
`h3_port_messages.py` applies, **including the CRLF trap**, which will empty every other
pickup prompt in the game if the source is read in text mode. Read it with `newline=''`.

### What is MORE EXPENSIVE than ODST

**Step 9 doubles -- against ODST, not against Halo 3.** Reach names TWO first-person
animation graphs, Spartan and Elite, and they are not interchangeable: a species whose
graph will not retime keeps the donor's length and cannot borrow the other's. Both must
be retimed or the Elite rig (Firefight, and m70_bonus) holds a differently-timed weapon.

Halo 3 is the same shape -- it names the Master Chief's and the Dervish's -- so this is
ODST, naming `odst_recon` twice and needing one clone, that is the outlier. **All three
games keep these graphs in the CHARACTER tree**, at
`objects\characters\<who>\fp\weapons\rifle\fp_assault_rifle`; that is not a Reach
difference. What Reach does not have is the per-weapon fp RENDER MODEL that sits beside
the world one in Halo 3 and ODST.

**The kit ships no model or icon SOURCE.** `data\objects\weapons\` is empty, and the
`data\ui\font_icons\*` folders the font settings name are empty too. So
`build_fonts_icon.bat` would rebuild the icon package as BLANKS -- never run it. Edit the
package in place the way `h3_weapon_glyph.py` does, which moves no offsets.

### Step 1, the model: JMS WORKS, and it is the Halo 3 JMS

**Resolved 2026-09-29 by rendering one.** Reach's `tool render` accepts a **version 8200
JMS** -- the exact file the Halo 3 port already produces. The Halo 3 SAW's own
`saw\render\saw.jms` was dropped into HREK unchanged and rendered, and it produced a
1,199,333-byte `jmstest.render_model` with 5 nodes, 5 marker groups, compression info and
real geometry. The only complaints were `unable to find shader 'saw_body'`, because the
shaders were not copied with it.

So step 1 is a KIT SWITCH, not a new importer. FBX and the `import <sidecar-file>` route
exist -- seven `*.sidecar.xml` tests ship under `data\objects\test` -- and are not needed.

Three things about the Reach toolchain that the test turned up:

* **`tool.exe` wants ABSOLUTE paths** for `export-tag-to-xml`, and says
  "Input tag path is not located in the tags directory structure" for the relative path
  H3EK accepts. `render` takes the relative source directory as usual.
* **Reach's skeleton nodes are prefixed `b_`** -- `b_gun`, `b_magazine`, `b_ophandle`,
  `b_safety`, `b_switch` where Halo 3 has `gun`, `magazine`, `ophandle`, `safety`,
  `switch`. Same five, same shape. The JMS template is built FROM the exported skeleton,
  so the names come along on their own; this matters only if one is ever hardcoded.
* **Sixteen marker groups, and the hands are per species**: `left_hand_spartan_fp`,
  `left_hand_elite_fp`, `left_hand_spartan`, `left_hand_elite`, `left_hand_marine`, and
  the right-hand set. The port's model must carry all of them or a Marine or an Elite
  holds it wrong. Halo 3's AR has five marker groups.

#### The region-name trap does NOT apply to Reach

`h3_region_name.py` exists because `tool render` names the region and permutation
**'default'** while every Halo 3 stock weapon says **'standard'**, and the mismatch makes
the world model render as thin air. Measured, both ends of that comparison:

    Halo 3   assault_rifle.render_model   region 'standard' / permutation 'standard'
    Reach    assault_rifle.render_model   region 'default'  / permutation 'default'

Reach's stock convention is the one `tool render` already writes, so the names match and
the rename step drops out. (Variant COUNT is not the mechanism and is not the check --
both games' AR models carry zero variants. The check is the stock region NAME.) Worth
one look the first time a SAW is dropped in front of an ally, but there is nothing to do
up front.

### The pipeline so far

    set PORT_EK=reach

    h3_make_saw.py --write        weapon, projectile, damage effect      (step 3)
    tool export-tag-to-xml        the AR's render_model, ABSOLUTE paths
    saw_to_jms_h3.py <xml> <lmg_rm.xml> 1.0     ONE JMS, the world skeleton  (step 1)
    tool render objects\weapons\rifle\saw final
    <clone two shaders>           saw_body, saw_display                   (step 2, part)
    tool render ... final         AGAIN: a shader that arrives after a render is not in it
    reach_saw_wire_model.py --write   hlmt + BOTH mode refs               (step 1)
    reach_saw_textures.py --write     the H4 skin into both shaders       (step 2)
    tool render ... final             a THIRD time, for the same reason
    balance_port.py SAW "Assault Rifle" "Halo 4" "Halo Reach"           (the table)
    reach_saw_tag_numbers.py --write  the H4 numbers into the tags        (step 4, 4b)
    port_field_audit.py --game reach  nothing left to port              (step 4b)
    saw_port_sounds.py --game reach --write  own sounds + graphs + bank   (step 10, later)

Six tags, every chunk tree spanning its file, every reference resolving:

    saw.weapon       37051 bytes, 24 refs      saw.model         23789, 10 refs
    ...bullet.projectile 24411, 10 refs        ...damage_effect   6850,  4 refs
    saw_body.shader  13596, 7 refs             saw_display.shader 9293,  4 refs

**Steps 1, 2, 3 and 4 are done.** The port has its own geometry, its own skin, its own
bullet and damage effect, and its own numbers: magazine 72, 216 carried, velocity 300,
damage 7.5, against the Assault Rifle's 32 / 160 / 3000 / 5.834.

The balance table came straight out of `balance_port.py` on ONE hop, because the Assault
Rifle exists in both games -- 53 rows, 47 balanced, only 2 with no target. Reach's
Assault Rifle is exactly TWICE Halo 4's on velocity (3000 against 1500), a clean game
scale, so Reach needs no `_mgvel` anchor the way Halo 3 did.

There is no XML IMPORTER -- HREK exports tags and cannot read them back -- so step 4 is
byte edits found by a signature of adjacent values that must match exactly once. What
makes that safe is that `export-tag-to-xml` names every field, so each tag is exported
again afterwards and the named fields read back. Two things it caught immediately: a
rounded float literal (6.788) packs to different bytes than the stored one and matched
NOTHING, and `damage upper bound` is a `real bounds` field that exports as one value,
`7.5,7.5`, so its halves are read by index.

THREE THINGS THE HALO 3 TOOLS DID NOT SURVIVE UNCHANGED, all now handled:

* **`h3tag` reads Reach tags as they are.** The chunk format is identical -- the
  Assault Rifle's weapon parses 37111 of 37111 bytes and decodes all 24 references. That
  is the whole tag-editing layer carried over for free.
* **The XML export is a DIFFERENT SCHEMA.** Halo 3 wraps a block's elements in
  `<block name="nodes" value="node,5">`; Reach has no `<block>` tag anywhere in the
  file and instead writes a self-closing `<field name="nodes" value="5" type="block"/>`
  with the elements following as SIBLINGS. Read as Halo 3 this yields nothing, and the
  skeleton comes back empty.
* **Block indices are NAMES.** Halo 3 writes `node,3`, Reach writes `b_ophandle`, and
  `NONE` for no link -- so an index has to be resolved against the names already read.

And one that would have been silent: Reach's nodes are `b_`-prefixed, so the H4 bone map
keyed on `gun` and `magazine` matched nothing and fell back to node 0, welding the
magazine to the body. It raises now instead.

All 16 marker groups come across, per-species hands included. 10736 verts, 13836 tris.

### A dangling reference that is REACH'S, not the port's

`saw_body.shader` points at `objects\weapons\boneyard\battle_rifle\bitmaps\battle_rifle_illum`,
which does not exist. So does the STOCK `assault_rifle_composite.shader` it was cloned
from -- HREK ships no `objects\weapons\boneyard` folder at all. `tool render` does not
complain and the model builds. Inherited, not introduced; do not go looking for it
twice.

### Step 5, the catalog: the simplest of the four

`make_port_catalog_reach.py` -- 45 balance rows, none of them pointing at a donor or a
shared tag. Reach needs less special handling than any other game:

* **no Machine Gun detour.** Bullet speed is measured against the Assault Rifle, which
  Reach runs at exactly twice Halo 4's, so there is no `_mgvel` table.
* **no `MEASURED` step.** ODST needs six rows read straight off the donor's tags for
  fields no card can reach there; all six are card-reachable in Reach.
* **one PORT_TAGS entry serves two classes**, because the damage effect shares the
  projectile's path.

Dropped: the three MELEE rows, which point at `globals\damage_effects\strike_melee` and
would retune the whole sandbox. `anims` ships ABSENT, as Halo 3's does and unlike
ODST's -- the port shares the Assault Rifle's graphs, so retiming would retime the
Assault Rifle for both species.

**The 320 / 288 question is answered, and it was arithmetic.** The tag's `rounds total
maximum` is the RESERVE PLUS THE MAGAZINE: Reach's Assault Rifle reads 320 in the tag,
288 through the plugin's "Rounds Inventory Maximum" and 32 loaded, and 288 + 32 = 320.
So the port's is 216 + 72 = 288 -- which is the number `h3_saw_tag_numbers.py` writes
for Halo 3, reached from the other end. The catalog derives the balanced total the
same way, because nothing in Reach recomputes it.

### Step 6, the ammo pickup: DONE, and Reach has THREE where ODST has eight

MEASURED on a built m20, not assumed: the Magazines/Magazines element is 20 bytes with
`Rounds` i16 at +0 and the equipment reference's 4CC ('piqe') at +4, so `ref_offset` is
4 and the patcher writes the datum at +0xC from there -- identical to ODST.

Reach consolidated its pickups. Reading every eqip tag off all ten missions gives one
generic `ammo_box` plus `rocket_launcher_ammo` and `sniper_rifle_ammo`, and all three are
on ALL TEN missions -- so unlike Halo 1 and ODST there is no per-map `maps` key to carry.
Everything else in Reach's eqip list is an armour ability, a grenade or a health pack.

### Step 9: the graphs are UN-SHARED, the retiming is not done

`h3_saw_animations.py --write --clone-only` clones both species graphs to
`objects\weapons\rifle\saw\fp\fp_saw_{spartans,elite}` and repoints the weapon. The path
shape is identical to Halo 3's, so `_graph()` builds them unchanged.

**Retiming fails, and this is the real cost of Reach's step 9.** `h3_anim_decode` reads
Reach's frame data past the end of the buffer:

    struct.error: unpack_from requires a buffer of at least 7784 bytes ...
                  (actual buffer size is 7704)

So Reach's animation layout is NOT Halo 3's, and decoding it is its own job -- the same
size as the Halo 3 and Halo 2 codec work. `--clone-only` exists for exactly this: the
port keeps the Assault Rifle's timing but no longer SHARES it, so whenever the format is
cracked the retime cannot reach a live weapon.

### Step 7, the HUD: DONE, and it CANNOT wait for the rebuild

Reach's chud has no meter -- it draws ammo as a NUMBER -- so step 7 is only the
`low ammo loaded threshold`, 8 of 32 on the Assault Rifle, which a port holding 72 would
inherit and cry low at a ninth of its magazine. A quarter of 72 is **18**.

**It must happen BEFORE the build, not after.** The cache builder deduplicates identical
block data, so a byte-identical chud clone comes out of the build SHARING the Assault
Rifle's blocks -- Halo 3 measured exactly that, and writing one moved the other. Writing
the threshold into the TAG is what makes the two differ and keeps them apart. Deferring
it until after a rebuild does not work: it would need another rebuild.

`h3_saw_chud.py` already had the locator and it works on Reach unchanged: the chud's root
struct is the FIRST `bdat`, and the threshold triple sits at its `tgbl` payload + 0x14.
A raw byte search does not work (8 appears 85 times as a long; `(8,0,0)` still matches 45
times, and no `tgst` chunk starts with those longs) -- which is why the chunk-tree route
is the answer and not a nicety.

Validated across Reach's own weapons, and the last two are the proof:

    assault_rifle (8,0,0)   dmr (3,0,0)     magnum (3,0,0)    shotgun (2,0,0)
    sniper_rifle  (1,0,0)   needle_rifle (5,0,0)   spike_rifle (10,0,0)
    plasma_rifle  (0,0,20)  focus_rifle  (0,0,20)   <- BATTERY weapons

The third member is `low battery threshold` and only the energy weapons use it, which is
what confirms the triple is (loaded, reserve, battery) rather than a coincidence.

Done: `ui\chud\saw` holds 18, the Assault Rifle still holds 8, and the weapon is repointed.

### Step 8: DONE -- the glyph is in, and the port has its own lines

The icon renders from the port's own mesh at all three resolutions (155x44, 310x88,
465x132) and the codec is Halo 3's, unchanged. It did not FIT anywhere, which is what
`h3_font_grow.py` exists for; see the glyph-ceiling section. Reach's codepoint is
**0xE150**, above the 0xE143 its HUD font tops out at in all three packages, because an
appended block goes at the END of the file.

**The glyph is LIVE.** The packages are loose files in `haloreach\maps\fonts`, so it is
already there with no rebuild. The MESSAGES are in the map's string list and are not.

`h3_port_messages.py` ran against HREK unchanged -- same three verbs, same list path.
**Reach has SEVEN lines where Halo 3 and ODST have five**, adding `saw_switch_to` ("Out
of ammo / Press ... to switch to") and `saw_swap_ai` (taking an ally's weapon). All
eleven non-English languages got them, 4 localized and 3 English fallback each -- the
same split as ODST, because the prompts carry only an icon while the confirmation and the
two ammo lines name the weapon.

The list went 298,702 -> 319,253 bytes and the weapon's five message ids are repointed.
**The CRLF trap did not fire**, and the proof is two numbers: `tool` reported 702 english
strings rather than a small delta, and the count of unpointed (-1) words came out at TWO,
below the THREE the shipped list already carries.
### What is NOT done

Step 7 (above), step 8's glyph placement and its messages, and step 9's retiming. The
messages themselves are untried: `h3_port_messages.py` refuses until the glyph codepoint
is settled, which is correct -- a message pointing at a codepoint with no glyph is a
blank box.

### The unknown still worth measuring

1. residency. Reach is the one game where a placed weapon can be inert because its tag's
   bit is clear in the first zone set's pool. A fresh EK build pools what the scenario
   references, so this should be a no-op for a built map -- but it is the standing HALF /
   LATE audit in `reach_pools.py`, and it is the first thing to check if the SAW spawns
   as nothing.

### Where it goes in

Reach has no equivalent of ODST's "placement alone is not enough" finding yet, because
the ODST result came from a starting profile and Reach's starting profiles are a
different shape -- named per difficulty, per co-op and per area, with the armor-ability
reference at +0x54 marking a player profile. Expect to place it in Sapien AND wire a
profile, and expect that to be the step that costs a rebuild to learn.

---

## Step 8, the text: A PORT BRINGS ITS OWN LINES

**This replaces every borrow, and it is the general answer.** Read it before the
per-game notes below, which now only record what each game still needs.

The old method took a live weapon's five message ids and edited its text. It never
generalised: the donor has to be a weapon that never appears, Halo 3 only had one
(the automag, which is ODST's STARTING PISTOL), and every remaining candidate is itself
a future port. Hijacking also reaches OUTSIDE the map, into a localization file shared
by every install of that game.

The Editing Kits could do this all along. The verbs, per kit:

| game | extract | import | tool |
|---|---|---|---|
| Halo 3, ODST | `extract-unicode-strings <list>` | `strings <dir>` **+** `strings-localized <dir>` | `h3_port_messages.py` |
| Halo 2 | `extract-unicode-strings <list>` | `new-strings <dir>` (all languages at once) | `h2_port_messages.py` |
| Halo 1 | — (Reclaimer reads the tag) | — (Reclaimer writes it) | `h1_port_messages.py` |

The source is UTF-16, a `[Strings]` header and one `name = "text"` per line, with icons
as NAMED MACROS (`&assault_rifle`, `&button_action_weapon_primary`). There are 39 macros
and no `&saw`, because the table lives inside `tool` rather than in a tag -- which does
not matter, because a **literal private-use character** works in its place.

So: clone the donor's lines, rename the prefix, swap its icon macro for the port's own
codepoint, re-import. `h3_port_messages.py` does it, and `--repoint` renames whichever
donor prefix the weapon actually carries, so one command converts a hijacking port into
an owning one.

### THE THREE TRAPS, all of which bit

* **CRLF.** The extracted source is CRLF and reading it in TEXT mode collapses that to
  LF. Written back, `tool` reads the whole vanilla body as ONE malformed entry, imports
  only the lines you appended, and leaves every pre-existing string with **english offset
  -1** -- text still in the blob, no pointer to it. In game that is every weapon's pickup
  prompt showing NO TEXT AT ALL, while the port's shows correctly. Measured: 479 of 487.
  Read with `newline=''`.
* **`extract-unicode-strings` reports only the DELTA after an import.** Re-extracting
  returns 8 entries and looks exactly like catastrophic data loss. It is not.
* **Do not delete the tag first.** It does make every string "new", and it discards the
  eleven other languages. It was only ever a workaround for the CRLF bug.

### Languages

`--languages` clones the port's lines into each `data_XX` source. The split is the icon
and it falls out of the data: the four PROMPT lines carry the icon macro and name no
weapon, so the localized text is cloned verbatim with only the icon swapped -- right in
every language, no translation. `picked_up` and the two ammo lines DO name the weapon,
and a name cannot be substituted into a translated sentence safely (the differing span
between two weapons' lines comes out as `'assau`, `n Assault`, half a Chinese word), so
those three take the English line. Result on both Halo 3 and ODST: no missing offset in
any of the twelve languages.

### Where each game stands

**All four now own their lines.** None takes anything from a live weapon, and the two
edits that reached OUTSIDE the map -- into localization files shared by every install of
their game -- have both been undone.

* **Halo 3: ODST** — done and confirmed in game. 487 entries, all twelve languages.
* **Halo 3** — done in the tags, needs a map rebuild. 475 entries, all twelve languages;
  repointed `am_*` → `saw_*`, and `h3_mcc_localization --restore` gave the automag its
  glyph back.
* **Halo 2** — done in the tags, needs a map rebuild. 332 → 339 entries in all NINE
  languages (its `new-strings` does every language in one pass); repointed `gpmg_*` →
  `saw2_*`, and `h2_saw_messages --restore` gave the cut GPMG its three lines back.
  **The prefix is four characters because H2 POOLS these ids with no terminators**, so a
  rename must not change length — the same trap `h2_tagref` documents for tag paths. The
  weapon comes out at exactly 3971 bytes, unchanged.
* **Halo 1** — done in the tags, needs a map rebuild. Its ICON was always owned (a new
  sequence appended to the shared sheet); the text was not. The engine reads the index
  AND the one after it, so a port needs a PAIR: appended at 47/48, weapon repointed from
  4. **Halo 1 is the only one where appending is trivially safe** — its list is addressed
  BY POSITION, so nothing before a new entry can move.

Each needs its map rebuilt before the change shows, ODST excepted.

### The localization .bin, for the record

It is no longer on the critical path -- the map's strings win once the list changes --
but it is not the black box the ODST notes first called it. **Its index is a table of
(hash, offset) pairs**, 7506 in Halo 2's English file, offsets monotonic; that is how
`h2_saw_messages.py` edits it safely. Its length must never change: shortened lines are
padded back with SPACES, never NULs, because a NUL ends the string early and everything
after it becomes a new entry -- which is how 21 phantom entries once turned Halo 3's
assault rifle pickup line into "CARNAGE REPORT".


---

## The icon supply, and why it has to grow

A port needs a pickup glyph, and taking a shipped weapon's is only tolerable once. There
are a limited number of icons and a great many more weapons to port, so the list has to be
extensible or the whole pipeline has a ceiling built into it. This should have been
settled at the end of the Halo 3 port and was not.

What is established, for Halo 3:

* **The official build path cannot add one.** `tool font-package` takes codepoints from a
  name table compiled into tool.exe — alphabetical from 0xE112 — and a tif whose name is
  not in that table aborts the run. The set of names is fixed at the tool.
* **The container is not fixed.** `font_package_icon.bin` is four fonts and four character
  map tables, each an array of 8-byte entries (u16 codepoint, u16 font index, u32 glyph
  offset), at 0xC000-spaced blocks holding 92, 64, 69 and 66 entries — in blocks with room
  for thousands. The glyph payload is a codec `h3_font_codec.py` reads and writes exactly,
  in both directions, across all 73895 shipped glyphs.
* **Bungie grew it themselves.** The alphabetical block starts at 0xE112, and `automag`
  (0xE144) and `golf_club` (0xE145) sit past its end, out of alphabetical order — appended
  after the fact. The highest codepoint any font declares is 0xE151.

**The tables are bounded** — `h3_font_package.py --bounds` proves it and exits non-zero if
it ever stops adding up. The file is five regions of 0xC000: region 0 is the package and
font headers, and each of the other four opens with two u32s that bound everything in it.

    +0x00   (entry count << 16) | table offset in the block, always 8
    +0x04   (glyph data size << 16) | glyph data offset in the block

So the character map is exactly `count` entries at `block + 8`, and the payloads follow at
`block + data offset`. A glyph's own offset is relative to the BLOCK, not to the data —
the first one equals the data offset exactly, which is what gives it away — and the last
ends at data offset + data size.

Within a table the entries form per-font RUNS, each ascending by codepoint, and one font's
runs may span blocks: fixedsys-hud's 144 glyphs are 34 + 69 + 41 across blocks 2, 3 and 4.
Summed per font they come to exactly the counts the font headers declare — 24, 98, 144, 24,
290 in all. Nothing is scattered and nothing needs a heuristic.

### Adding a glyph

Everything needed is now known:

1. append the payload in a block that has room — used extent is data offset + data size,
   and against the 0xC000 block that leaves **288, 32, 1088 and 5688 bytes** free in blocks
   1 to 4, so block 4 will take several icons as it stands;
2. insert an 8-byte entry into that block's table, inside the right font's run and in
   ascending codepoint order;
3. that insertion pushes the glyph data along by 8, so **every offset in that block moves
   by 8**, and the block's own two u32s move with it;
4. bump the font header's glyph count at +0x13C, and its highest codepoint at +0x138 if the
   new one is higher.

`h3_font_add.py` does it, and `h3_weapon_glyph.py` calls it whenever the codepoint it is
asked for does not exist yet. The SAW now owns **0xE06A** in all three resolutions, and
0xE128, which it used to borrow, is byte-identical to Bungie's again.

**The rule, which cost two goes to get right: a new entry goes in its SORTED position.**
A font's entries are not one run — `fixedsys-hud`'s live in a dozen blocks — but they must
read as ONE ascending list across the package. Inserting after whichever run had room keeps
that run ascending and breaks the font: 0xE151 after the run ending 0xE069 made the font
read `... 0xE069, 0xE151, 0xE070 ...`, and a lookup that assumes a sorted list stops
finding things. The x1 package was fine because there it landed above the font's highest,
so one package of three was right and two were not — and the pickup and ally-trade prompts
drew no icon at all while the player's inventory icon, which is not a font glyph, kept
working. That is the shape of the bug to expect here.

So: insert sorted, and when the block a codepoint sorts into has no room, change the
CODEPOINT rather than the place. `h3_font_add.add()` refuses to return a package whose font
no longer ascends. 0xE06A was chosen because it is free in all three packages AND sorts
into a block with room in all three — confirmed in game.

### Halo 2 is easier, and needs no codec at all

H2EK ships **`tool replace-font-char <font> <tiff> <utf16>`**, so Bungie's own encoder
draws the pixels and the payload format never has to be understood — which matters,
because the SHIPPED payloads do not decode with the Halo 3 codec even though that tool
writes with it. The 2004 data is in some older form; what the tool writes today is what
the engine reads today.

What it will NOT do is add a codepoint. An unmapped one resolves to the font's notdef
glyph and `replace-font-char` replaces THAT — one command and every unmapped character in
the game becomes a SAW. So `h2_font_add.py` creates the entry first: append a 16-byte
record to the glyph table, push every payload along by 16 and bump every absolute offset
with it, point the codepoint's slot in the character map at the new index, and raise the
glyph count. The character map being indexed by codepoint is what makes this easier than
Halo 3 — no table to insert into, no order to keep.

Two traps, one run each:

* **the codepoint argument is DECIMAL.** `0xE13D` is read as 0, and the tool silently
  rewrites the notdef glyph while reporting "replaced char 0" and the notdef's size — the
  only sign anything went wrong;
* the font has to be edited where tool.exe can reach it, so copy it into H2EK, edit, copy
  back.

`h2_saw_glyph.py` drives the pair over all eight English fonts and refuses any font where
a shipped glyph moved. The SAW owns **0xE13D**, free in all of them, with 195 more above
it for the ports after this one.

---

## Reading H4 source data

    tool export-tag-to-xml <ABSOLUTE tag path> <out.xml>

Relative paths fail with "not located in the tags directory structure". Three things
about the render_model XML cost time every time they are rediscovered:

* positions are **compressed to 0..1** and need expanding through the compression bounds;
* `position bounds 0` and `1` are **six floats paired per axis**, not min then max — the
  tell is that the middle pair comes out symmetric, which is the weapon's width;
* `raw indices` is a triangle **STRIP**; read as a list it draws a discus.

`extract-import-info` fails on H4 tags — there are no original source files to recover.

**The source tag is `objects\weapons\rifle\storm_lmg\storm_lmg.render_model` in H4EK.**
The SAW is called the storm_lmg there, which is not guessable, and every port's geometry
comes out of it — all four converters take that export as `lmg_rm.xml`, and it has been
living in `%TEMP%`, one cleanup away from being the next thing rescued out of a
scratchpad. It is reproducible in one command:

    tool export-tag-to-xml <H4EK>\tags\objects\weapons\rifle\storm_lmg\storm_lmg.render_model %TEMP%\lmg_rm.xml

---

## Open, and deliberately so

* **The port's non-English confirmation lines are English.** The four prompt lines are
  properly localized in all twelve languages; `picked_up` and the two ammo lines fall back
  to English, because a weapon name cannot be substituted into a translated sentence
  safely. Fixing it needs a real translation per language, which is a content job.
* **The crosshair is not ported in Halo 1 or Halo 3 yet.** Only Halo 2's is. The method is
  game-agnostic -- H4EK specifies the layout, so the same read applies -- but both earlier
  ports still wear their donor's reticle. ODST inherits Halo 3's, so it is in the same
  position.
* **Codecs 4, 6 and 8 of the Halo 2 animation format** are undecoded, so `ready`,
  `put_away`, `sprint` and `throw_grenade` cannot be retimed. Codec 3, which every reload
  uses, is done.
* **Halo 2 animation EVENT frames are not scaled** when an animation is retimed. It does
  not bite on a reload whose only key is at frame 1, but a weapon with a mid-reload key
  needs this first.
* **Whether shortening truncates.** `scale_reload` rewrites the frame count and not the
  data, so a shortened animation should play the first N frames and cut the tail -- where a
  reload settles. Read from the code, never seen in game, and it applies to the Halo 3 port
  as much as to Halo 2. One look with a Reload Time card applied would settle it.
* **Halo 2 collision is the donor's hull, scaled.** Good enough for a similar weapon; a port
  whose shape differs a lot from its donor's would want a real hull, and `tool collision`
  will not build one from a render mesh.

---

## Balance

    balance_compare.py "<weapon>" "<source game>" "<target game>"

Reads every card-reachable field from the **pristine baselines** in both games and gives
the ratio per field; `balance_port.py` turns that into the port's balance rows.
`port_coverage.py`, `port_field_matrix.py` and `port_gap_check.py` audit which fields a
game actually exposes, so a missing row is a known gap rather than an oversight.

Ports carry their ORIGINAL numbers by default; the balance option swaps in the derived
values, and damage moves by the same ratio. (Exception: fields NO card covers -- step 4b --
have no row to switch, so the port takes the ratio value outright.)

**When the ratio breaks (user, 2026-10-07, SMG):** the ratio rule needs the source
yardstick's number to be a normal reference. Two failure shapes so far:
- a near-ZERO source value (H3 AR spread minimum 0.1 deg: 1.25/0.1 gave the H1 SMG a 25 deg
  first shot, wider than its 5.96 maximum) -> scale by the sibling bound's ratio instead
  (the maximum's 2.75/3.0: 2 x 0.917 = 1.83 deg);
- related fields scaling in opposite directions (H3 AR carries 12 magazines, the SMG 4:
  pickup x1.875 but carry limit x0.625 -> starts with more than it can hold).
**DUAL-WIELD CARRY RULE:** a port its source game let you DUAL WIELD gets x1.5 on its
carry-limit ratio (dual wield doubles output and carry; x2 is too much for a one-handed
port): SMG 600 x 0.625 x 1.5 = 562.5 -> 562 (Halo 1 stores a short). Applies to the next
dual-wieldable ports too (Brute Spiker, Plasma Rifle-class) when their carry looks odd.
**AMMO PICKUP (balanced):** the source game's own pickup : initial ratio on the balanced
initial (SMG: 120/180 x 450 = 300; user, 2026-10-07).
**THE HIT-EFFECT RULE, Halo 1 (user, 2026-10-08, the Spike Rifle's Armed test):** 'the higher
the fire rate, the smaller the effect'. A projectile hitting the player plays the projectile's
own response effect for the player's material -- the same table it uses on walls; shielded =
#22 `cyborg energy shield`. Stock Halo 1 never scales it (the AR's 49-particle shield hit at
15/s) and ports inherit their donor's, so high-rate ports wash the view out with sparks. Load
per hit = sum of created count x radius^2 over the effect's particles; x rate x projectiles
per shot = load per second. RULE v2 (the user's pick after v1, below, kept it 'too big --
a steeper curve'): the donor's per-hit load is KEPT up to the stock pistol's rate (3.5/s);
above it x (3.5 / rate)^K, K = 3.19 FITTED to the approved Spike Rifle effect (every 4th spark
at x0.25 = 2% of the AR's load at 12/s). Size only (scale = sqrt), at max(default, balanced)
rate (one tag serves both). Spike Rifle x0.14 (the approved load, all 49 sparks smaller).
APPLIED 2026-10-08 (tags written, untested in game): SMG x0.098 (15/s: balanced 22.5 is capped
at the measured 15/s), SAW x0.098 (15/s; its own writer saw_port_values.py reads
ports_h1/saw.py `impact_thin`, whose `from` names the donor's effect so a rerun does not shrink
the own copy twice), Battle Rifle x0.187 (the TAG rate 10/s: a burst's 3 rounds land 0.1 s
apart and stack; the sustained tap rate ~5-6/s would give ~x0.5), Covenant Carbine x0.255
(balanced 8.24/s; x0.44 at the default 5.88 alone). The shared code is
h1_hit_effect_load.thin_effect; h1_pickable_weapons runs it LAST in the bullet step (after
material_responses_from -- the Carbine's plasma responses). Beam Rifle, Sword unchanged.
FUEL ROD: NOT applied -- the table's x0.19 is an artifact of the tag's 10/s, which nobody
fires (default: one rod per 1.25 s charge = 0.8/s; balanced 2.5/s; Grunts ~0.4/s): every real
rate is under 3.5/s, so the rule keeps x1.0; its #22 response is a DETONATION (`impact
generic`, the explosion itself, 81 particles), not shield sparks. USER: leave it unchanged
for now. Armed tests on a30: SMG, Battle Rifle, Carbine size CONFIRMED by the user (keep as is); the Carbine's then
recoloured GREEN (user: 'change color to green if possible' -- impact_thin `tint`, the plasma
pistol bolt light's .23/1/.13 on the sparks + flash; not re-tested, the user's call: 'the size
was the important part'); SAW CONFIRMED (keep). All four DONE; they reach the shipped maps with
the batched ten-map rebuild (user's go). v1 = a
load-per-second budget equal to the stock pistol's (4.36/s): Spike x0.78, too big (user).
The way there: a -30% screen flash first (reverted: not the complaint), then thinned + x0.25
(approved), v1, v2. Unshielded hits (#21 cyborg armor: sparks, smoke, blood) are left alone.

**ARMED WEAPON DAMAGE MODIFIER, Halo 1 ("Rule B", user 2026-10-08):** an enemy carrying a
port gets actor_variant Weapon Damage Modifier (0xC4) = base x (yardstick player dps /
port player dps), base = the WDM of the carriers it fires from (the AR donors: 0.4), dps
from h1_role_compare 5b; once for the default numbers, once for the balanced rows
(`firing_profile['wdm_rule']` -> ai_firing_profiles.json `fields` + `balanced_fields`;
h1_enemy_weapons uses the latter for ports in its spec's `balanced`). A stronger port gets
a gentler AI. Beam Rifle 0.40 / 0.23 (base 0.4: the Flood Elite sniper; yardstick Sniper 202), Carbine 0.60 / 0.26, SMG 0.80 / 0.60, BR 0.80 / 0.48, SAW 0.53 / 0.40 (the
rule replaced Halo 4's own 0.75; dps at the 15/s cap observation). Checked by stopwatch on
the Carbine (0.23 measured vs 0.26). A source profile's own WDM (Halo 4 has one) is
replaced by the rule; every Halo 1 port carries a rule now.

---

## Dependencies

`port_env.py` puts the vendored Reclaimer stack under `pylibs/` on `sys.path` — pure
Python, no compiler. Import it before anything from `reclaimer`.

Step 10 (sounds) also needs **numpy** and **vgmstream-cli** at
`F:\Tools\vgmstream\vgmstream-cli.exe` (h4_wwise.py --extract, port_sound_levels.py) --
outside the repo, so reinstall it on a new machine.

---

## What deploys, and what the toolkit is missing

Audited 2026-09-29, after a build died on a script that had never been in the repo.

### Only Halo 1 deploys on its own

    saw_build.py          DEPLOYS BY DEFAULT      --no-deploy to stop it
    h2_saw_place.py       only with --deploy
    h3_saw_deploy.py      only with --install     (Halo 3 and ODST, kit-switched)
    odst_ek_build.py      only with --install
    reach_ek_build.py     only with --install

Halo 1 is the odd one out: it is the oldest chain and predates the others. Everything
that writes a live map elsewhere -- the H4 test tools, `reach_place.py`,
`reach_keep_hud.py`, `h1_weapon_ring.py`, `h2_saw_glyph.py` -- backs the file up first
and is gated behind `--write`, `--deploy` or `--install`.

### Nine tools were lost with a scratchpad; one mattered

`port_backup.py`'s `SCRIPTS` list is the manifest of what a port's tooling consists of,
and it is the only record of what the session scratchpad held before df48675 promoted
21 tools out of it. It ran NINE names short and said so only as a count:

    saw_port_values.py      REBUILT -- it was step 4, and saw_build.py called it
    ammo_pickups_scan.py    h3_weapon_census.py     h3_tagtable_probe.py
    check_families.py       h3_verify_magazine.py   jms_add_colour.py
    saw_h3_bench.py         tagvals.py

Every one of the remaining eight is referenced by **nothing but the manifest** -- no
build chain calls any of them, so they were surveys, probes and benchmarks rather than
steps, and the four chains are complete without them. They are left in the manifest on
purpose: it is the record that they existed.

`port_backup.py` now NAMES a shortfall instead of printing `31 of 39`, which is the
thing that would have caught this the day it happened.

**RECOVERED 2026-09-30.** All eight were in the 2026-09-21 backups under
`F:\HaloPortBackups\*\scripts\` (one version each across every backup) and are back in
the toolkit. The manifest now checks complete for h1, h2 and reach.

---

## SCALE: it is 140 ports, and the pipeline is built for one

Counted 2026-09-29 with `port_matrix.py`, off the weapon spreadsheet, whose answer is in
the cell COLOURS and not in its text.

    56 weapons in the sheet
    45 SOURCEABLE -- they exist in at least one MCC game
    11 exist in no MCC game at all (Halo 5 / Infinite) and cannot be ported from anywhere

    Halo: CE       12 has, 33 missing      Halo 3: ODST   22 has, 23 missing
    Halo 2         18 has, 27 missing      Halo: Reach    23 has, 22 missing
    Halo 3         26 has, 19 missing      Halo 4         29 has, 16 missing

    140 port jobs to fill every gap.

**"MP only" counts as HAS IT.** If the tags are already in the game, a campaign
appearance is a placement and residency problem -- no geometry, no shaders, no
animations. Lumping those in with real ports overstates the work, so the matrix keeps
them apart.

### What the SAW cost, and why that does not multiply

One weapon into four games took the whole of this document. At that rate 140 is not a
project, it is a decade. But most of what it cost was PER GAME, not per weapon, and that
half is now done and amortises across every future port in that game:

* the kit selector, and `per_kit` refusing to guess;
* the tag format -- `h3tag` reads H3, ODST and Reach unchanged;
* the JMS version, and the two XML schemas the exporters use;
* the string verbs and the CRLF trap;
* the font package format, its codec, and the block-occupancy rule;
* the chud threshold locator;
* the balance machinery -- `balance_port.py` already derives a table for ANY weapon pair
  from the games' own tags, which is the one part that was general from the start.

### What actually multiplies, and therefore what has to become DATA

**77 of the 215 tools mention `saw` by name.** That is the whole problem in one number:
there is a SAW pipeline, not a port pipeline. Everything below is per WEAPON and is
currently a constant in a script:

    the donor            which weapon's skeleton and animations it inherits
    the source geometry  which H4/H3/H2 render_model, and its bone -> node map
    the markers          which of the donor's the port keeps and which it moves
    the tag names        saw, saw_bullet_h4_original_numbers, fp_saw_<species>
    the numbers          magazine, reserve, velocity, damage
    the icon             its codepoint, per game, per package
    the messages         its prefix and its lines

So the next step is a **port manifest**: one file per (weapon, target game) carrying
exactly those, and tools that read it instead of holding constants. Nothing about the
method changes -- the nine steps are right, and each one has now been proven in three
engines -- it is the same steps driven by data.

### The leverage, which is not evenly spread

    in 1 game: 16 weapons   <- 5 targets each, 80 of the 140 jobs
    in 2 games: 8      in 3: 5      in 4: 6      in 5: 1      in 6: 9

**Sixteen weapons account for more than half the work**, because a weapon that exists in
one game is missing from five. Extracting ONE of those well -- geometry, textures,
numbers -- pays off five times, and the Halo 4 set is most of them. That is the opposite
of the SAW's shape, which was one source and four targets, and it is the argument for
making the SOURCE side of the pipeline data-driven first.

The other end is nearly free: the nine weapons already in all six games need no ports at
all, and the H3 to ODST direction is byte-identical territory where a port is mostly a
copy.

---

## Port glyphs on EVERY machine: port_glyphs.py (2026-10-03)

The pictograms of Halo 3 / ODST / Reach / Halo 4 live in LOOSE packages beside the maps
(`<game>\maps\fonts\font_package_icon*.bin`): no map rebuild carries them, a Steam
update or verify restores the stock ones, and a co-op partner's install never had them.
`tool\port_glyphs.py` + `tool\port_glyphs.json` (35 KB) carry the finished glyph records
and put them back: `ensure(game, mcc_root)` for the Enhancer at patch time, or
`python port_glyphs.py [--game G] --write` by hand. Standard library + h3_font_repack.py
only -- no kit, Blender or source art at run time.
* Proven on a stock install copy: all 13 packages written, glyph sets identical to the
  in-game-proven live ones; a second run is a no-op. Halo 4 rebuilds byte for byte; the
  older Halo 3-family placements come out with the same glyphs and headers in the
  repacker's block order (the layout of the in-game growth test).
* **After adding a new port glyph** (h3_weapon_glyph.py, h4_weapon_glyph.py, ...): run
  `python port_glyphs.py --capture` on the dev machine (needs the stock backups on E:)
  and commit the json. It refuses if any package does not rebuild from stock.
* A frozen Enhancer build needs in halo_enhancer.spec: pathex=['sprint_toolkit'],
  hiddenimports=['h3_font_repack', 'port_glyphs'], datas += [('port_glyphs.json', '.')].

## THE GLYPH CEILING: the first hard limit on how many weapons a game can take

Measured with `glyph_capacity.py`. A ported weapon needs a pickup icon, and from Halo 3
on that icon goes into `maps\fonts\font_package_icon*.bin`, which are FIXED SIZE. So
"how many weapons can this game accept" has a hard answer, and it is far below the
number of weapons there are to port:

    game        icons that still fit      weapons missing (port_matrix.py)
    Halo 3              4                         19
    Halo 3: ODST        1                         23
    Halo Reach          1                         22

**The space is not where it looks.** A package is a series of 0xC000 blocks, and each
font's glyphs are spread across them as ascending RUNS. A new glyph sorts into the run
its codepoint extends, so the only free space it can use is the tail of THAT block --
not the package's total. Reach's x1 has 25,616 free bytes and exactly 1,408 of them are
reachable by the HUD font. That is the difference between twelve more icons and one.

And **all three resolutions must take it**, so the ceiling is the smallest of them. x1 is
usually the binding one because it is the smallest file.

### Halo 1 has no ceiling, and that is the shape to copy

Halo 1 has no font package at all. Its pickup icon is a sequence in the shared
`hud_msg_icons` BITMAP, and `add_msg_icon.py` APPENDS a bitmap and a sequence, growing
the tag. Unbounded, and already proven. The later games' packages are the exception, not
the rule.

### Four ways out, cheapest and least risky first

1. **ONE SHARED GLYPH for every port.** A single "ported weapon" icon costs one slot in
   total instead of one per weapon, works today in every game, and needs no new format
   understanding. It is the only option that is free right now. The cost is that every
   port shows the same picture in its prompt.
2. **REPACK THE BLOCKS.** Redistribute each font's runs so the free space is reachable.
   Uses only the format already decoded and proven, no engine assumptions. Takes
   Halo 3 to 8, ODST to 22, Reach to 12.
3. **SMALLER ICON ART.** The SAW costs 726 bytes at x1 for 155x44. Halving that takes
   Halo 3 to 17 repacked, ODST to 19, Reach to 14 -- and it composes with (2).
4. **GROW THE PACKAGE.** The block count is not stored anywhere: every reader derives it
   from the FILE SIZE, and the shipped packages already vary from 4 blocks to 22. So
   appending a block is plausible and would remove the ceiling entirely. It is also the
   only option that needs an in-game test to trust, because nothing proves the engine
   sizes it the same way.

(2) and (3) together look sufficient for ODST and Reach and marginal for Halo 3; (4) is
the one that actually ends the problem. (1) is the fallback that unblocks porting
immediately if the others take time.

### (4) IS BUILT: `h3_font_grow.py`, and the ceiling is gone

Appending a block works. Done to all three of Reach's live packages, each gaining exactly
one block and exactly one codepoint:

    x1   245,760 -> 294,912 bytes    4 -> 5 blocks
    x2   589,824 -> 638,976         11 -> 12
    x3 1,130,496 -> 1,179,648       22 -> 23

    353 -> 354 entries in each, all 354 decode, nothing lost, font 3 still ascending.

**The best evidence is not that test -- it is ODST.** Halo 3 ships a FOUR-block,
245,760-byte x1; ODST ships a FIVE-block, 294,912-byte one. Same engine, same format,
and a grown Reach x1 is byte-for-byte that shape. The block count is stored nowhere: every
reader derives it by walking the file in 0xC000 steps and accepting what validates as a
block header. The walk IS the format.

**A new block goes at the END of the file**, and a font is one ascending list read across
the blocks in file order, so it can only carry codepoints above that font's highest.
Reach's HUD font tops out at 0xE143 in all three packages, so Reach's glyph is **0xE150**.
`grow()` refuses anything lower and `ordered()` proves the result.

Still needs ONE BOOT to trust: nothing in the bytes proves the ENGINE sizes the package
the way the readers do. If it does, there is no glyph ceiling in any of these games and
a port costs 48 KB of font package.

### The two bugs that were damaging packages, both fixed

The write path **wrote the file and then checked it**, so a failed check left the damage
on disk and only said "restore it". And it checked `fp.bounds`, which is FALSE on Reach's
SHIPPED package -- its `ui-16` header claims 98 glyphs where the tables hold 96 -- so
every Reach write wrote and then raised. That is what emptied x1 earlier, not the
insertion.

`h3_weapon_glyph.verify()` now runs BEFORE the write: nothing lost, exactly one codepoint
gained, and every glyph in the result decodes. A global "adds up" check cannot do that on
a file whose shipped header disagrees with its own tables -- diff against a pristine copy
instead.

### Two games still unmeasured

* **Halo 2** edits eight fonts in place under `h2_fonts` rather than using a package
  (`h2_font_add.py`), so its ceiling is a different measurement.
* **Halo 4's packages are not 0xC000-blocked** -- 327,680 is not a multiple of it, and
  the x3 tables do not sit where the others' do. It has FOUR resolution tiers rather than
  three. It needs its own reader before its ceiling can be stated, and it is a port
  target for 16 weapons.

**This is a restrictor, not a detail.** Nine steps can be automated and a manifest can
make the pipeline generic, and none of that matters if the eleventh weapon in a game has
nowhere to put its icon.

---

## GLYPH CAPACITY, ALL FIVE GAMES: NO CEILING (2026-09-30)

    Halo 1   the icon is a sequence in the hud_msg_icons BITMAP; add_msg_icon.py appends
    Halo 2   one font per file; h2_font_add.py appends a record + payload (+2,288 bytes per
             icon per font, 8 fonts). halo2.dll opens each font with CreateFileA (random
             access, 0x6f41e1) and reads glyphs by offset on demand -- no whole-file
             buffer, so no size cap. The only limit is 12 font FILES (the scan at
             0x6f3f70); ports add none. Already past the largest shipped size
             (handel_gothic-24 644,684 > 642,396) with the SAW drawing.
    Halo 3 / ODST / Reach   h3_font_repack.add_glyph: packages grow by whole blocks,
             confirmed in game on Reach (the section below).

## THE BLOCK INDEX -- and why "native range" was the wrong rule (2026-09-30)

**Supersedes the section below.** Right after the font headers, in the header region,
every icon package carries one pair of u32 keys PER BLOCK -- the first and last entry the
block holds -- with key = `font << 16 | codepoint`. It matches every block of all nine
shipped packages (Halo 3, ODST, Reach x x1/x2/x3) exactly, and nothing follows it. The
package is ONE list ascending by that key, cut first-fit into 0xC000 blocks; the index is
how the engine picks the block to search.

`h3_font_repack.py --selftest` rebuilds all nine shipped packages from their glyphs,
first-fit, and gets every file back BYTE FOR BYTE -- so this is exactly what the kits'
`tool font-package` does, and a package rebuilt with a new glyph sorted in is what the
official tool would have written.

What it re-explains:
  * Reach 0xE150 in an APPENDED block: the index did not list the block -> box.
  * Reach 0xE150 placed in block 4: block 4's range is font 5 only -> box. The "above
    the font's native top" explanation below was a coincidence of both.
  * Halo 3's 0xE06A and ODST's 0xE04A each became the LAST entry of an x2 block with the
    index left one codepoint short, so they could not draw at x2. FIXED with
    `h3_font_repack.py --fix-index --write`; all nine live indices now check.
  * h3_font_add / place / grow never touched the index. `h3_font_repack.add_glyph` is
    their replacement: rebuild around the new glyph, grow by whole blocks, rewrite the
    index. The capacity question then becomes the index's room in the header region
    (thousands of blocks) and free codepoints -- not bytes.

**Growth test, Reach, written to the live packages:** fonts 0-2 spread over the SHIPPED
block count, so the ENTIRE HUD font (every weapon icon, the SAW's included) sits in
blocks the package never had -- x1 4->7, x2 11->21, x3 22->41, every record identical.
FIRST BOOT: every weapon icon broke -- the test had left each font's OWN block range alone: the third u32 of a font's header triple is (blocks spanned << 16) | first block (all fonts, all nine packages). assemble() now rewrites it; test rewritten. SECOND BOOT: most icons GONE; a same-count --shift test then DREW -- so a count cap. The count is IN the file: header +0x410 = index offset, +0x414 = block count (all nine packages), read by haloreach.dll's glyph lookup at 0xcca68, which bsearches that many 8-byte index entries (blocks are then paged through an 8-slot cache). assemble() now writes +0x414. Third test: the real growth again, counts 7/21/41. **THIRD BOOT: ALL ICONS DRAW -- GROWTH CONFIRMED.** h3_weapon_glyph now calls h3_font_repack.add_glyph (any free codepoint, grows by whole blocks); add/place/grow and glyph_capacity are superseded. Checked in memory: 40 heavy icons took Reach x1 from 4 to 24 blocks, verify() clean. Icons normal = the engine reads grown packages. Every weapon icon broken = it caps at the
shipped count. Undo: `h3_font_repack.py --undo-growth-test haloreach`.

## THE CODEPOINT MUST BE INSIDE THE FONT'S NATIVE RANGE

Measured in game, Reach, 2026-09-29, and it corrects the glyph-ceiling plan.

The port's prompt drew a BOX while **"Picked up a SAW" on the same screen was correct**.
That one detail settles a lot: the string list, the weapon's message ids, the import and
the twelve languages all work, and ONLY the glyph lookup failed.

It failed at 0xE150 in an APPENDED block, and it failed at 0xE150 in an EXISTING block
that the engine was already reading. **So the block was never the problem.** What is wrong
with 0xE150 is that it is above 0xE143, where Reach's HUD font natively stops:

    halo3      HUD font 0xE006..0xE150 natively   added 0xE06A   INSIDE   works
    halo3odst  HUD font 0xE006..0xE150 natively   added 0xE04A   INSIDE   works
    haloreach  HUD font 0xE008..0xE143 natively   added 0xE150   ABOVE    box

Both precedents agree and neither was chosen on purpose -- they happened to be free in a
range that also happened to be inside. The font header's top-codepoint bound updates
correctly (0xE144 -> 0xE151) and the entry decodes, so nothing in the FILE is wrong. The
engine simply does not resolve an icon above the font's shipped top.

Reach's glyph is now **0xE052**: free, inside the range, and sorting into a block with
room in all three packages, whose boundaries differ completely. The packages are back to
their shipped sizes and block counts, 354 of 354 entries decode, and the messages were
re-imported so the tag holds 48 occurrences of U+E052 and none of U+E150.

### What this does to the ceiling

**A naive append cannot add a usable icon.** A font is one ascending list read across the
blocks in file order, so an appended block can only carry codepoints ABOVE the font's top
-- and those are exactly the ones the engine will not resolve. Growing the file is safe
(the text was undisturbed) and useless on its own.

What growth needs is a REPACK: rebuild the package with N+1 blocks and redistribute every
run, so the new block holds a mid-range slice and the ascending order still reads. Then
the binding constraint stops being bytes and becomes free IN-RANGE codepoints -- of which
Reach has 103 free in 0xE093..0xE143 alone and 229 below 0xE160.

So the ceiling is not 1, and it is not unbounded either:

    today, no repack        Halo 3 4, ODST 1, Reach 1
    repacked in place       Halo 3 8, ODST 22, Reach 12
    repacked AND grown      limited by free in-range codepoints, which is ~100+

The middle row needs no new format understanding. The bottom row needs a real repacker
and is the one that reaches 140.

---

## `tool render` STRIPS A LEADING `b_` FROM NODE NAMES

Reach only, and it is the whole of the empty first-person model and the weapon that
vanished when dropped.

Reach's skeleton is entirely b_-prefixed -- `b_gun`, `b_magazine`, `b_ophandle`,
`b_safety`, `b_switch`. The JMS declared exactly those, because the converter reads them
out of the Assault Rifle's own export. `tool render` then wrote a render model whose
nodes are called `gun`, `magazine`, `ophandle`, `safety`, `switch`.

    assault_rifle   parent node  NONE, b_gun, b_gun     first child  b_ophandle
    saw (before)    parent node  NONE, gun, gun         first child  magazine

**So nothing that ANIMATES the weapon could find its nodes.** The statically placed
weapon still drew, because bind pose needs no graph -- which is exactly what made this
look like a rendering fault rather than a naming one. First person was empty and a
dropped weapon vanished, and residency, the region name, the model wiring, the geometry
chunks and the compression bounds were all checked and all innocent.

The fix is to declare `b_b_gun` and let the strip leave `b_gun`. Confirmed: the render
model now reads b_gun / b_magazine / b_ophandle / b_safety / b_switch, all parented to
b_gun with a valid sibling chain. `saw_to_jms_h3.py` carries it as `NODE_PREFIX`, per
kit, because Halo 3 and ODST have unprefixed skeletons and there is nothing to protect.

This is the same shape as the region-name trap in Halo 3: `tool` rewrites a NAME on the
way in, the tag is otherwise perfect, and only the thing that looks the name up notices.
Whenever a ported model is silently wrong, compare its node and region names against the
donor's FIRST -- it is one export and a diff, and it is the cheapest check there is.

---

## `tool render` ALSO SORTS THE NODES, and the world graph indexes into them

The second half of the same trap, and it is what the eliminations below were closing in
on. Measured: `b_b_switch` comes out `b_switch` while `a_b_gun` is left alone, so the
strip is exactly a leading `b_` -- and the order that comes out is ALPHABETICAL on the
stripped name, whatever the JMS declares.

    donor        b_gun, b_switch, b_safety, b_magazine, b_ophandle
    alphabetical b_gun, b_magazine, b_ophandle, b_safety, b_switch

**The world animation graph carries its own 5-node skeleton and its animation data
indexes INTO it**, so a port whose nodes came out sorted has indices 1..4 permuted
against the graph that poses it. That is the whole of it:

    placed by the scenario   bind pose, no graph          DRAWS
    first person             the 52-node ARMS graph, and the weapon hangs off it by
                             MARKER rather than by node index               DRAWS
    held by an ally, dropped posed through the world graph                  NOTHING

Order cannot be asked for, so it is bought with a sort key and the key is renamed away.
`saw_to_jms_h3.py` emits `b_a_gun`, `b_b_switch`, `b_c_safety`, `b_d_magazine`,
`b_e_ophandle`; `tool` strips the `b_` and sorts on `a_gun`, `b_switch`, ... which IS the
donor's order; `reach_node_names.py` then renames `a_gun` to `b_gun` and so on. Every
rename is one character for one character, so each is an in-place byte swap with no chunk
length to propagate -- unlike Halo 3's region rename, which grows the file.

Run it after EVERY `tool render`, like the region rename in Halo 3. The port's nodes now
read b_gun, b_switch, b_safety, b_magazine, b_ophandle -- the donor's names in the
donor's order.

---
## THE WORLD MODEL: what has been ELIMINATED

After the `b_` fix, first person works and its animations look right. The WORLD model
still draws nothing -- on the ground and in an ally's hands. Both go through the same
render model, and the only thing between them is the model tag, so the search space is
small and most of it is now closed. Recorded so none of it is checked twice:

* **residency** -- `reach_pools.py m20 --audit`: 34 palette entries, 0 HALF-loaded, 0 not
  resident at start. The FULL CLOSURE is live, not just the weapon;
* **the geometry in the map** -- `h3_chunk_check`: `mode saw` 1 chunk, 1 backed, same as
  the Assault Rifle, plus both bitmaps and `saw_body`;
* **the model tag** -- `saw.model` exported to XML is IDENTICAL to the Assault Rifle's in
  all 99 fields except the render-model reference. Not the LOD distances, not the
  imposter policy, not the checksums;
* **the region and permutation names** -- both `default`/`default`, and every other field
  of the regions block matches: mesh index, mesh count, all four instance masks, the L1
  and L2 section group indices. This is where Halo 3's identical symptom lived, and it is
  not where Reach's does. `default` is universal across Reach's stock weapons;
* **the mesh format** -- same vertex type (skinned), same rigid node index (-1), same
  index buffer type (triangle strip), same mesh count, same runtime flags;
* **the compression bounds** -- same axis convention, comparable scale (1.05 m).

One real difference remains and its significance is unknown: **`tool render` emits the
nodes in a different ORDER than the donor's.** The Assault Rifle reads b_gun, b_switch,
b_safety, b_magazine, b_ophandle; the port reads b_gun, b_magazine, b_ophandle, b_safety,
b_switch -- alphabetical after the prefix strip. The hierarchy is equivalent (every node
is a child of b_gun, with a valid sibling chain) and the JMS declares the donor's own
links, so this is tool's own traversal, not lost data. It would matter only if a graph
addressed nodes by INDEX -- and the first-person graph is a clone of the donor's and
animates correctly, which argues it resolves by name.

The next step is the bisect Halo 3 used: point `saw.model`'s `mode` back at the Assault
Rifle's render model and rebuild. If a dropped weapon then draws as an Assault Rifle the
fault is inside the port's render model; if it still draws nothing the fault is in the
weapon or the model tag, and neither of those differs from the donor.

---

## THE BISECT ANSWERED: the fault is INSIDE the port's render model

With `saw.model` pointed at the DONOR's render model and everything else the port's own,
the result in game was:

    in your hands      the SAW      (first person reads the weapon's own `first person
                                    model`, which still points at the port's)
    dropped, on allies the ASSAULT RIFLE

So **the world path works and renders** -- it just will not render THIS render model,
while the first-person path renders the same tag happily. That halves the problem and
rules out the weapon tag, the model tag and how the object is built.

### What tool itself says about it

The port's render model carries three entries in its `errors` block that the donor's does
not. The first is the interesting one:

    no region/permutation found in material names, model will be a single region

and the string it comes from spells out why:

    'identical material/shader names found - assuming legacy parsing mode
     (single default region/permutation)'

Our materials are `saw_body` and `saw_display`, and the shaders are called `saw_body` and
`saw_display`, so `tool` decides this is an OLD JMS, gives up on parsing regions out of
the material names, and synthesises one. The donor gets no such comment: Bungie's models
came through the FBX/SIDECAR pipeline, where regions are a face collection -- the sample
sidecar in `data\objects\test` carries exactly that, a `regions` FaceCollection whose one
entry is `default`.

Both end up with one region called `default`, so it is not yet proven that legacy parsing
is the FAULT -- but it is the only difference `tool` itself flags, and it is the only
thing left that distinguishes how the two models were built.

### What the material syntax is NOT

`(default default) saw_body`, by analogy with the marker format that tool does document
(`marker '%s' has bad format - must be '(permutation region) name'`), is WRONG for
materials: the shader then fails to resolve entirely, the material comes out `invalid`,
and the legacy comment stays. Tried and reverted.

The other strings around it are the map to the real syntax, and they say a MAX material
name yields a `region_name` and a `permutation_name`, that a material name may contain a
material TYPE which can override one found in the shader name, and that the punctuation
set in play is `%#?!@*$^-&=.;)><|~({}[`. Reading those out properly is the next move,
and the alternative is to stop fighting the JMS path and use the sidecar importer the
donor was built with.

---

## THE LEGACY-REGION LEAD IS A RED HERRING

`no region/permutation found in material names` is what `tool` says about ANY JMS-built
model, including Halo 3's SAW, whose world model works. So it is a property of the JMS
path, not a fault -- and switching to the FBX/sidecar importer is therefore not
guaranteed to fix anything. Correcting the earlier recommendation.

Three material-name syntaxes were tried and all fail. `(default default) saw_body`, by
analogy with the marker format tool documents, and `saw_body default` both stop the
shader resolving; `default saw_body` and `default default saw_body` keep it resolving
(tool takes the LAST token as the shader) but the legacy comment stays. Whatever a
"multi-part material" is, it is not space- or paren-separated region and permutation.

## EVERY FIELD OF THE RENDER MODEL MATCHES THE DONOR

The bisect proved the fault is inside the port's render model. Every field that
`export-tag-to-xml` can show has now been compared against the Assault Rifle's and
agrees: regions and permutations and their names, every field of the permutation block,
node names, node order, node list checksum, marker groups and marker count, mesh count,
vertex type, rigid node index, index buffer type and index, vertex buffer index, PRT
vertex type, lighting policy, runtime flags, compression bounds, and the presence and
absence of every block in the tag. The counts that differ follow from having 2 materials
where the donor has 10.

So the difference is in the DATA, not the shape of the tag, and the XML cannot show it.

### The experiment that splits THAT in half

`tool export-render-model-mesh <render-model> <out>` writes the donor's own geometry as a
binary DirectX `.x` (2 MB for the Assault Rifle, plus its textures as DDS). Converting
that into a JMS and rendering it AS THE PORT'S MODEL separates the two remaining
suspects in one build:

    the donor's geometry, through our JMS pipeline, still does not draw in the world
      -> the JMS PIPELINE is the fault, and the FBX/sidecar importer is the answer

    it draws
      -> the pipeline is fine and OUR H4 GEOMETRY DATA is the fault -- tangents, normals
         or the skinning -- and the fix is in the converter, not the importer

That is worth doing before writing an FBX exporter, because it says whether the FBX
exporter is needed at all. The `.x` is binary (`xof 0303bin`), so it needs a reader; that
is a contained job against a documented format, unlike authoring binary FBX plus Bungie's
per-node property JSON, which is what the sidecar route actually requires.

---

## THE CONTROL FAILED, AND THAT FOUND IT: `<none>` IS TWO MATERIAL FLAGS IN REACH

The donor's OWN geometry, exported with `tool export-render-model-mesh` and wrapped on the
port's skeleton by `reach_donor_mesh.py`, drew nothing in the world either. So the fault
was never our H4 data: it was in how a JMS becomes a render model.

Comparing three render models side by side -- stock, a sidecar import of the kit's FBX
sample, and the JMS control -- one error appeared on BOTH JMS-built models and on
NEITHER of the others: `*unexpected material flags`, with tool's own explanation
`material 'none' is not a portal, but has flags that only make sense on portals`.

A JMS material is two lines. The shared converter writes the Halo 1/2 convention: the
shader name, then `<none>` for "no texture path". **Reach reads the second line as the MAX
material name**, and `<` and `>` are both in its flag character set
(`%#?!@*$^-&=.;)><|~({}[`, sitting next to portal, weatherpoly, seamsealer, soft_kill,
slip_surface). So every material came out named `none` and carrying two spurious
STRUCTURE flags.

`saw_to_jms_h3.py` now writes the shader name on both lines for Reach
(`MATERIAL_SECOND_LINE`), which is tool's benign legacy mode. Halo 1 keeps `<none>` --
correct there -- and Halo 3 and ODST are unchanged. The port's render model now carries
one error, a tangent warning of the same class as the stock model's; the flag errors AND
the legacy-region comment are gone.

### The sidecar route, measured on the way

`tool import <sidecar>` works in this kit: the shipped FBX sample imported in 15 s and
built a render model. It reads the GRANNY intermediate (.gr2), not the FBX directly. It is
not usable as a control as shipped, because its skeleton and markers content objects
point at .max/.gr2 files that do not ship, so the importer invents a skeleton from the
mesh objects and writes no markers. Re-running it overwrote the kit's own
`test_fbx_assault_rifle.render_model` with that degraded version; it is a test asset no
map references, and HREK.7z holds the original.

---

## WHERE THE REACH WORLD MODEL STANDS

The material-flag fix removed every error tool reports on a JMS-built model except a
tangent warning the stock model shares -- and the dropped / ally-held SAW still draws
nothing. That was the last difference the XML could show. The JMS path itself produces
something the world path rejects, and nothing visible says what.

### The sidecar route needs a Granny file, and the kit cannot make one

Measured: with the sample's `.gr2` removed, `tool import` reports "asset does not contain
any render geometry" and writes nothing. It does NOT convert FBX itself; the FBX is only
the artist's source, and the `.gr2` came from Bungie's Max/Maya exporter plugin, which
does not ship. `bin\tools\bonobo` is Foundation's plugin system, not an exporter.

What DOES ship is `granny2_x64.dll` with its full writer API (GrannyBeginMesh,
GrannyBeginSkeleton, GrannyBeginFileDataTreeWriting, ...), so a `.gr2` can in principle be
authored through ctypes. The importer also reads Bungie's per-node extended properties
(`bungie_face_region`, `bungie_object_type`, ...) -- the `.json` beside the sample mirrors
them -- so the file has to carry those too.

Three ways forward, recorded so the choice is not re-derived:

* author the `.gr2` ourselves against the kit's Granny DLL -- fully in the toolkit,
  largest and least certain;
* use the community Blender exporter that already writes Reach sidecar `.gr2` through that
  same DLL -- proven route, but an outside install and a manual export step;
* a hybrid inside the tag: keep the donor's Bungie-built render model and swap only its
  geometry for ours -- small if the cache builder rebuilds from the per-mesh raw blocks,
  and unproven that it does.

---

## REACH STEP 1, THE PROPER WAY: Foundry and the sidecar importer

The JMS path was ruled out by a control: the Assault Rifle's own geometry, pushed through
`tool render` from a JMS, draws nothing in the world either. Bungie's assets came through
FBX -> Granny `.gr2` -> sidecar -> `tool import`, and `tool` cannot make a `.gr2` itself --
with the sample's removed it finds no geometry at all. Foundry is the community exporter
that writes one.

### The install, on F:, with nothing on C:

    F:\Tools\blender-5.2.2-windows-x64\            portable Blender 5.2.2 LTS, 913 MB
        portable\                                settings live HERE, not in %APPDATA%
        portable\extensions\user_default\io_scene_foundry    Foundry 1.9.19
    F:\Tools\downloads\                           the two zips, both SHA-256 verified

Foundry needs Blender 5.2 or newer. It found HREK by itself. **Its `allow_tool_patches`
ships ON, which lets it modify HREK's tool.exe; it is switched OFF here**, and the export
refuses to run if it finds it back on.

### The pipeline

    blender --background --python reach_foundry_saw.py -- --build --export

Foundry imports the Assault Rifle's own MODEL TAG natively, which gives a scaffold it
built itself: the armature with the five b_ bones in the donor's order, a mesh object
carrying the region/permutation properties, all 20 markers, the scene set up as a model
asset. The script keeps all of that and swaps ONLY the mesh data for the SAW's, read from
the JMS `saw_to_jms_h3.py` already builds, then moves the four markers the SAW carries
elsewhere. The scale is Blender metres, 3.048 x world units, so a JMS coordinate goes in
x 0.03048.

(Foundry's own JMS import hands off to a second community add-on that is not installed.
Going through the donor's TAG avoids it, and gives a scaffold Foundry set up itself.)

The result: nodes `b_gun, b_switch, b_safety, b_magazine, b_ophandle` NATIVELY, in the
donor's order -- no strip, no sort, no rename trick -- region `default`, 16 marker groups,
and a single cosmetic `degenerate triangle` error from zero-area triangles already in the
source mesh.

### Foundry rewrites the MODEL tag -- and must not

Its export regenerates `saw.model` from what the scene holds, so it DROPS the collision,
physics and world-animation references the port borrows from the Assault Rifle and points
the imposter at a SAW imposter that does not exist. A dropped weapon on that model has no
physics body. It also writes an unreferenced `saw.scenery`. The script keeps `saw.model`
aside and puts it back after every export, and removes the scenery. What we take from
Foundry is the render model only.

The `.blend`, sidecar and `.gr2` files live in the kit beside the port's data:
`data\objects\weapons\rifle\saw\saw.blend`, `saw.sidecar.xml`, `export\models\*.gr2`.
Pre-Foundry tags are backed up at `E:\HaloBackups\reach_saw_prefoundry_20260930_0721`.

---

## CONFIRMED IN GAME, 2026-09-30: the Foundry render model fixes the world model

First person still works, and the SAW now draws when dropped AND in an ally's hands. So
the JMS importer really was the cause, and **for Reach, `tool render` from a JMS is dead as
a route for any weapon that can be dropped or carried** -- which is every weapon.

What that retires, kept in the repo only as the record of how it was found:

* `reach_node_names.py` and the `b_<key>_` sort key in `saw_to_jms_h3.py` -- workarounds
  for the JMS importer stripping `b_` and sorting nodes. Foundry emits the donor's names in
  the donor's order natively.
* `MATERIAL_SECOND_LINE` -- the `<none>` flag fix. Real, but not the cause.
* `reach_saw_bisect.py` and `reach_donor_mesh.py` -- the two controls. The bisect proved
  the fault was inside the render model; the donor-mesh control proved it was the JMS
  PIPELINE rather than our data. Both are reusable the next time a port model misbehaves.

`saw_to_jms_h3.py` still matters: it is how the H4 geometry gets out of Halo 4, and
`reach_foundry_saw.py` reads its JMS. Only the `tool render` step is replaced.

### Reach port status

**COMPLETE -- every step confirmed in game (2026-09-30).**

    1 geometry        DONE   through Foundry; first person, dropped and ally-held.
                             Markers: subtract the parent bone's length (see step 9 notes)
    2 textures        DONE
    3 own tags        DONE
    4 numbers         DONE
    5 catalog         DONE   45 rows, 3 ammo choices, fp_animations saw\fp_saw_* with
                             reload x1.0 (Reach AR = H4 AR = 68 frames, so built = balanced)
    6 ammo pickup     DONE
    7 HUD             DONE   own icon (text widget -> saw string), own 72-tick meter, low 18
    8 icon + text     DONE   glyph 0xE052 inside the font's native range, 7 lines x 12
    9 animations      DONE   reach_foundry_fp_retime.py: reload 128, ready 24, events scaled

**Still open for Reach, as scaling work rather than SAW work:**
  * ~~Glyph capacity~~ SOLVED 2026-09-30: packages grow (h3_font_repack.py, confirmed in
    game); see THE BLOCK INDEX.
  * **The Foundry scripts are SAW-specific** (paths, moved markers, frame targets). They
    are generalised with the NEXT port, which needs its own marker placement anyway.
  * **Starting profiles** never gave a Reach weapon; a non-issue, weapons are SPAWNED now.

---

## REACH STEP 7, THE REST: the HUD icon is TEXT, and the meter gets its own sheet

### The weapon icon

Reach's chud does not draw the weapon schematic from a bitmap. The `shematic` and
`shematic_backpack` widgets are TEXT widgets in the full-screen HUD message font, with
input string `assault_rifle` -- which is a line in `hud_messages`,
`assault_rifle = "&assault_rifle"`, expanded by tool to the Assault Rifle's glyph. So
`h3_port_messages.py` adds `saw = "<U+E052>"` (the same glyph the pickup prompt already
draws), to all twelve languages since it carries no words, and `h3_saw_chud.py` renames
both input strings to `saw`. The HUD and the backpack icon are then the SAW's.

### The ammo meter

The `meter` bitmap widget reads the raw `weapon ammo loaded` and draws
`ui\chud\bitmaps\ballistic_meters_2_rows`: ONE 320x48 a8r8g8b8 image plus a 160x24
mip, no sequences, Halo 3's encoding exactly -- blue is the per-tick threshold counting
down column by column (40/39, 38/37, ...), red 48 and green 2 on every tick, alpha the
shape. It is a 40-round meter: the Spike Rifle uses it whole, the Assault Rifle crops it
with manual texture coordinates 0,34,24,160. The shipped TGA exporter fails on it
(`rasterizer\invalid`); the pixels are RAW in the tag's 76,800-byte `tgda`, level 0
then the mip.

`reach_meter_art.py` writes a NEW tag, `saw_ballistic_meter`, cloned from the sheet so
format and mip chain are the shipped ones, and redraws its pixels in place: 72 ticks as
24 columns of 3, thresholds 72 -> 1 in the same column order, the shipped tick shape
scaled to the smaller cell. It points ONLY the SAW's meter widget at it and sets its
texture coordinates to 0,0,0,0 like the Spike Rifle's. The shared sheet and every other
chud are untouched.

---

## REACH STEP 9: the animations are COMPRESSED, and Foundry decodes them

**CORRECTED 2026-10-10 (the Halo 1 DMR, wave B1): they are NOT compressed-only.** The export
mislabels the member's `data sizes`: in label order they are the blob's sections shifted by
one -- `static_node_flags` = the default data, `animated_node_flags` = a codec-3 compressed
copy, `movement_data` / `pill_offset_data` = the static / animated node masks (24 bytes each),
`uncompressed_data` = 12 bytes a frame (zero in fp_dmr), `compressed_data` = a FULL codec-2
float copy in Halo 3's uncompressed layout. So a Reach pose decodes like Halo 3's, in Python,
no Foundry: `reach_tags.load_graph` (all 25 fp_dmr animations: masks = header counts, unit
quaternions, codec 3 and 2 agree within 0.042 deg). Foundry stays the route for WRITING a
Reach graph (Reach as the target); the text below is the original record.

Why `h3_anim_decode` over-read: Halo 3 stores first-person frames RAW in the uncompressed
block (16-byte quaternions), which is what made retiming arithmetic. Reach does not.
Across all 23 members of the SAW's graph `default_data` is 0, the bulk is in the
COMPRESSED block, and the uncompressed block is a flat 12 bytes per frame (108/9, 60/5,
1200/100) -- probably root motion. So every Halo 3 invariant fails and the decoder was
reading the wrong block. Retiming needs Reach's codec decoded.

**Foundry already decodes it**, through the kit's own ManagedBlam. Importing the Spartan
first-person arms (`objects\characters\spartans\fp\fp.render_model`) and then the graph
onto that armature (`reach_foundry_fp_probe.py`) loads 25 actions -- reload_full 0..60,
reload_empty 0..69, ready 0..21, put_away 0..6. So step 9 is a keyframe-scaling job in
Blender plus a sidecar export, like step 1, and needs no codec work.

What does NOT work, and why: importing the graph with no armature in the scene imports
nothing ("No armature found"); importing the WEAPON tag crashes in Foundry's material
node layout (`arrange`), which appears to need a live UI.

**DONE -- `reach_foundry_fp_retime.py`** (run inside the F: Blender, once per species,
`-- spartans --write` / `-- elite --write`). It imports the arms, adds the five weapon
b_ bones read from the graph's own skeleton (b_gun under r_hand), imports the graph onto
that rig, scales keys + handles about frame_start (reload_full/empty 128, ready 24), and
exports ALL animations -- the export rebuilds the graph from the scene, so exporting
one leaves a graph of one.

Three traps, all measured:
  * Foundry names the asset after the .blend's FOLDER: two species saved side by side in
    `saw\fp` both came out as `saw\fp\fp`. Each species gets its own folder,
    `saw\fp_saw_<sp>\fp_saw_<sp>`, and the weapon's jmad refs are repointed there.
  * Exported into NOTHING, the graph comes out with 0 sound references and its events in
    a separate frame_event_list. So the new path is SEEDED with the original graph first;
    the export then merges and keeps sounds/effects inline.
  * ...but the merge ALSO keeps the seed's inline event FRAMES: reload_full was 128 frames
    with its primary keyframe still at 34. `fix_events()` (also `--events` alone) sets
    them through Foundry's ManagedBlam AnimationTag, computed from the ORIGINAL graph so
    reruns cannot compound. Result, both species: reload_full 34/52/fx40 -> 74/113/87,
    reload_empty 34/62/fx30,48 -> 64/117/56,90. Sound events sit at 0 and stay there.
The originals stay in `saw\fp\` (plus `.before_retime` copies of them and of saw.weapon).

---

## Step 10, the port's own sounds -- THE RECIPE (2026-10-05)

The history and every trap are in the next section; this is the run order. All of it is
in git (sprint_toolkit + the tool-root modules) and in `port_backup.py --game <g>`.

**Source, once per source weapon (Halo 4 here):**

    h4_wwise.py --extract <bank> <out dir> <event> ...   the events' audio (vgmstream);
                                    the SAW: bank light_machine_gun_player -> H4EK\temp\saw_sounds,
                                    events play_wea_lmg_player_fire_in / _fire_out,
                                    play_weapons_storm_light_machine_gun_player_dryfire,
                                    play_wea_lmg_ready_fly / _mech / _initial,
                                    play_wea_lmg_reload_fly_a.._c, _mech_a.._d,
                                    play_wea_lmg_pose_var_1_a.._c, _2_a.._c,
                                    play_wea_lmg1_foley_melee_player, play_wea_lmg2_foley_melee_player
                                    (event names: the H4EK sound tags)
    saw_port_audio.py               per-shot fire mixes, tails, dry fire -> H4EK\temp\saw_port_audio
    graph_sound_events.py <kit> <graph>   which sound each target animation cues, at which
                                    frame (a target graph cues ONE sound per animation)
    saw_port_foley.py               the source's foley cue lists by FRAME, mixed into one
                                    sound per animation (stretch for a retimed animation)
    port_sound_levels.py --game <g> <donor sounds>   the donor's active RMS + tag gain =
                                    the level targets (`--foley`: the mixes' own)

**Per game** (each script repoints the port's effects AND first-person graphs at its own
sounds, builds them with the volume marker, and refuses on a failed import):

| game | sounds | then | where MCC plays it from |
|------|--------|------|-------------------------|
| Halo 1 | `h1_saw_sounds.py --write` (in saw_build.py; then saw_anims.py) | rebuild; `..\port_sounds.py --write` | classic FMOD bank sounds_adpcm.fsb, BY TAG PATH (22 kHz XBOX ADPCM, never under sound\sfx) |
| Halo 2 | `h2_saw_sounds.py --write` | rebuild (03a; 01b reserved) | the map (Opus, classic) |
| Halo 3 | `saw_port_sounds.py --game h3 --write` | rebuild + `h3_saw_deploy.py --install --baseline` | `halo3\fmod\pc\sfx.saw.fsb` (installed by --write; MONO foley; per-sound banks merged -- the H3EK FSBank trap) |
| ODST | `saw_port_sounds.py --game odst --write` | `odst_ek_build.py`, `h3_chunk_check.py`, deploy | `halo3odst\fmod\pc\sfx.saw.fsb` (MONO foley) |
| Reach | `saw_port_sounds.py --game reach --write` | `reach_ek_build.py --maps m20` | `haloreach\fmod\pc\sfx.saw.fsb` -- NEEDED, despite an early test that seemed to say not |
| Halo 4 | `h4_sound_bank.py` | `..\port_sounds.py --write` (no rebuild) | its own Wwise bank in sfxbank.pck |

**Level changes without a rebuild:** H3/ODST/Reach foley targets / `--boost` and H1
`--bank-only` change only the bank (the map's subsound hashes come from the wav paths), so
re-run the sound script and load the map again. Gains (tag) need a rebuild.

**The patcher's side:** `port_volume.py` (the knob, needs the marker), `port_sounds.ensure`
(Halo 1 / Halo 4 banks on any machine), `port_sounds.retimed_anim_sound` (Halo 1: a
retimed animation swaps to the sound stretched for it; catalog `anim_sounds`).

**On every machine (2026-10-05):** `saw_port_sounds.py --write` also copies the bank to
`tool\port_sounds\<game>\` -- COMMIT IT after every bank change -- and
`port_sounds.ensure('<game>')` (fmod_ensure) copies it into `<game>\fmod\pc` when missing
or different; a bank MCC holds open (a map of that game loaded) is reported, not forced.
The enhancer calls it for the folders in its PORT_SOUND_FOLDERS. Patch time needs nothing
outside the frozen app: plain file copies here, numpy (bundled) only for Halo 1's ADPCM;
vgmstream is a BUILD-time tool.

**Checks** (closing step 6): `port_sound_refs.py --game "<game>"` on the built map;
bank live == kit and every map hash in it; `port_volume.py` headroom 3.

## The SAW ports' OWN SOUNDS (started 2026-10-03)

**What they play today** (`port_sound_refs.py`, read from the deployed maps): every SAW
port borrows ALL its sounds -- fire, distant fire, tails, dry fire, reload, ready, melee,
pose, zoom, pickup -- from its donor (H1/H3/ODST/Reach: the Assault Rifle, the Battle
Rifle's dry fire, the Sniper's zoom; H2: the SMG, the chaingun's ammo rattle). In
H3/ODST/Reach the SAW even fires through the ASSAULT RIFLE's own firing / empty EFFECTS,
shared with the real AR -- the sounds cannot be changed there without owning the effects.

**The source: Halo 4's SAW** (`storm_lmg`, player bank `light_machine_gun_player` in
sfxbank.pck). Wwise banks keep only name HASHES; the event names come from H4EK's sound
tags (export-tag-to-xml), 21 of the bank's 26 named that way. `h4_wwise.py --extract
<bank> <out> <event...>` follows event -> actions -> containers -> sounds -> media
(embedded or in sfxstream.pck) and decodes with vgmstream. The player fire is LAYERED:
6 stereo cracks (~84 ms) + 11 mono bodies (0.645 s) played together per shot; release
plays one of 3 tails (2.4-2.7 s). `saw_port_audio.py` makes the older engines' per-shot
sound from that: 6 permutations of crack + body, the 3 tails, the dry fire (48 kHz stereo).

**Reach: the kit's FMOD route** (`reach_saw_sounds.py`, HREK):
* `tool sounds-single-layer <data folder> <sound class> -bank:<suffix>` = one sound tag
  per folder, one permutation per wav, the audio in `fmod\pc\sfx.<suffix>.fsb` (+ .info)
  beside the stock sfx.fsb. The type argument is a SOUND CLASS (weapon_fire,
  weapon_empty, first_person_outside, ...; `tool` lists them on a wrong one).
* a compiled Reach sound tag carries `FMod Bank Suffix` (snd! +0x30): stock '' (sfx.fsb),
  the port's 'saw' -- so MCC is expected to open `haloreach\fmod\pc\sfx.saw.fsb`.
* the AR's tails are two tags by class (ar_tail_ext first_person_outside, ar_tail_int
  first_person_inside); the SAW's tail is imported twice with those classes.
* the SAW gets OWN copies of the AR's firing / empty effects (saw\fx), sounds repointed;
  the weapon names them. The distant-fire LOD sound stays the AR's for now.
* **First boot: the SAW was SILENT.** The map was right (own effects, own sounds, suffix
  'saw'), and the game does build `fmod\pc\sfx.<suffix>.fsb` (haloreach.dll strings). The
  difference was the ENCODING: stock Reach sound tags carry `xma2,ms_adpcm` (two raw-data
  entries); the import wrote xma2 only, so the map compiled the sound with an XMA v2 codec
  (ugh! codec compression 7) where every stock sound uses compression 8 -- the PC one,
  MS-ADPCM, embedded in the map. `tool reimport-sounds <dir> adpcm no no
  compression-append` adds it (the script does, and checks every tag). The saw bank and
  suffix stay, so either playback path finds the audio. Second boot pending.
  Observation from one game: whether PC Reach plays the map's MS-ADPCM or the FMOD bank
  is not isolated yet.
* **Second boot (2026-10-03): THE REACH SAW PLAYS ITS OWN SOUNDS** (Halo 4 SAW fire, tails,
  dry fire). Working state: tags `xma2,ms_adpcm`, bank suffix 'saw', sfx.saw.fsb installed.
* **Planned tests, one at a time now that sound works (user):**
  1. PC ONLY -- drop the Xbox (XMA2) encoding, keep MS-ADPCM: the ports only run on PC,
     and the XMA2 data only adds size. Reimport with the adpcm compressor WITHOUT
     compression-append and confirm in game.
     SET UP (2026-10-03): `reach_saw_sounds.py --write --pc-only --install`. Found on the
     way: `reimport-sounds <dir> adpcm no no <filter>` REPLACES the encodings when the
     filter is not compression-append, and the filter must match every tag (`weapons`
     misses the first_person_* tails; `stereo` takes all four). It also CLEARS the bank
     suffix, even with -bank:<suffix> -- `reach_sound_suffix.py` (ManagedBlam) sets it
     back, so this test changes the encoding only.
     **CONFIRMED in game (2026-10-03): PC-only sounds the same.** Now the default of
     reach_saw_sounds.py (`--both` keeps XMA2). Import ports' sounds PC-only from here on.
     **Test 2 CONFIRMED (2026-10-03): the FMOD bank is NOT needed.** With sfx.saw.fsb +
     .info moved out of haloreach\fmod\pc the SAW still plays its sounds, before and after
     an MCC restart: PC Reach plays the MS-ADPCM audio compiled INTO THE MAP. So a Reach
     port's sounds need nothing outside the map -- no loose file, no restore step, nothing
     a Steam verify can delete. The kit still writes the bank into HREK (part of the
     import); the tags keep suffix 'saw' (the tested state; an empty suffix is untested).
     Observation from Reach; Halo 3 / ODST use the same kit route and are expected to
     behave alike -- confirm on their first port.
     **WITHDRAWN 2026-10-04: Test 2 was misheard.** The SAW's firing effect also plays the
     AR's distant-fire layer (assault_rifle_lod_far) and the projectile has sounds of its
     own; with the bank out of the folder those were what played. Installing sfx.saw.fsb
     in haloreach\fmod\pc for the first time (2026-10-04) made the SAW's fire, reload and
     ready audible. **Reach plays port sounds from the FMOD bank, like Halo 3 / ODST** --
     saw_port_sounds.py now installs it on every route. Lesson: a "still plays" test
     needs a sound that cannot be confused with another layer (a test tone).
**Halo 3 / ODST (2026-10-03, built, first boot pending)** -- `saw_port_sounds.py --game h3|odst
--write` (one script for all three kits now; reach_saw_sounds.py is a wrapper):
* both SAWs fired through the AR's firing effect, the dry fire through the BATTLE RIFLE's
  empty effect; Halo 3's AR firing effect has NO tails (fire + distant fire), ODST's has
  the two like Reach. Own copies, repointed, as for Reach.
* the encoding differs from Reach: stock H3 / ODST sound tags carry xma v2.0 ONLY -- PC
  must play them from FMOD (sfx.fsb) -- and the H3 kits' `reimport-sounds ... adpcm`
  gives uncompressed PCM ("none (little endian)") and clears the bank suffix. So the
  first test mirrors STOCK: the import's XMA2, suffix 'saw', and sfx.saw.fsb installed in
  halo3\fmod\pc / halo3odst\fmod\pc (both dlls build `fmod\pc\sfx.<suffix>.fsb` too).
  Banks: Vorbis 48 kHz stereo ~70 kbps (H3 7 streams, ODST 13).
* the ports live in ONE map each: Halo 3 010_jungle, ODST sc150.
* if it plays: the same follow-up as Reach -- is the bank needed? (no rebuild).
* **CONFIRMED in game (2026-10-03): Halo 3 and ODST play the SAW's own sounds** (stock
  route). Lessons: h3_build_map.py only BUILDS -- install with `h3_saw_deploy.py --install
  --baseline`; ODST levels are levels\atlas (h3_build_map fixed); h3_chunk_check.py takes
  the map NAME, not a path (sc150: every SAW chunk backed, the four sounds included).
* **"More oomph" (user):** the per-shot mix left out Halo 4's 0.35 s PUNCH layer (fire_in
  #9: the loudest, most low end, 16% below 150 Hz), and its level already matched the
  Reach AR (-16 vs -17 dBFS RMS) -- the gap is low end (11.6% vs the AR's 13.9%).
  Candidates for listening: sprint_toolkit\sound_compare\oomph (A current, B + punch,
  C + punch + 4 dB below 150 Hz, level-matched; the AR shot for reference).
  User: the sound itself is fine (A stays).
* **ODST felt "noticeably quieter" (user) -- it is the MIX, not the audio.** The SAW shot
  measures the same in every game (-12 dBFS over the first 0.25 s; tag gain -3 = -15
  effective). Effective level of each game's own guns (shot RMS + tag gain): Halo 3 AR
  -22.2, Carbine -24.7 -> the H3 SAW stands ~7 dB above; ODST AR -14.6, Carbine -13.0 ->
  the ODST SAW sat level with them. Fix with the SAME sounds, ODST only, ~+6 dB:
  * the tag's GAIN BASE IS CAPPED AT 0 dB (`tool process-sounds <dir> <spec> gain= 4`
    stays 0; gain+ stops at 0): -3 -> 0 = +3 dB (saw_port_sounds.py `gain`);
  * the other +3 dB in the AUDIO: a soft limiter searched to raise the shot's RMS by
    exactly 3 dB, peaks capped (-12.0 -> -9.0 dBFS, peak -1.2) (`boost`, fire + tails).
  * +6 was TOO LOUD in game (user); now +4.5 (boost 1.5, shot -10.5 dBFS). **Retuning
    the boost needs NO REBUILD on the stock route:** the boost lives only in the loose
    bank; `saw_port_sounds.py --game odst --write --boost DB` re-imports and installs it,
    the .info (the keys the map looks up) comes out byte-identical and the sample counts
    unchanged -- restart MCC and listen. Only a GAIN change (in the tag, so in the map)
    needs a rebuild. The +6 bank: F:\HaloPortBackups\odst_saw_bank_plus6.
    +4.5 CONFIRMED good (user); a bank swap took effect WITHOUT an MCC restart.
* **Per-port VOLUME at patch time (port_volume.py, tool root).** A compiled sound's gain
  is NOT in its snd!: the snd! holds an index (+0xC H3/ODST, +0xE Reach) into the sound
  gestalt (ugh!) Playbacks block (+0x10; element 0x44 / Reach 0x54; Gain Base +0x1C /
  Reach +0x2C), and the cache builder POOLS identical entries. The SAW's entry was shared
  with 4596 stock sounds (010), 282 + 2646 (sc150), 2079 (m20) -- never write it in
  place. **The build-time marker:** every port sound is built MARKER_DB (SAW 0.01 dB,
  one value per port) below its gain (`saw_port_sounds.py --game X --gain-only`, then
  rebuild). No stock gain is fractional like that (pools read: whole and half dB, a few
  x.4988), so the port owns its entries and port_volume.apply() shifts them; it refuses
  an entry used by any other sound. Relative to the as-built level, so applied to the
  baseline copy. **Every map carrying a port must be rebuilt with the marker** before
  the knob works there.
* **The engine CLAMPS Gain Base at 0 dB** (boots 2026-10-03: H3 SAW -6 "quieter", -20
  near silent; ODST SAW +6 and +12 unmoved; Reach with only the marker: unchanged). A port
  can be turned DOWN freely, UP only to 0. **Headroom rule:** every port ships at the
  import gain -3 with its AUDIO set so that -3 is the right level -- the knob gets +3 dB
  up. Halo 3 / Reach SAW: plain audio at -3. ODST SAW: -3 gain + 4.5 dB soft-limited
  audio (= the confirmed +4.5; limiter: 0.05% of samples near the ceiling, at +6 0.6%).
  port_volume.headroom() reports it, apply() caps at 0.
* **Halo 4: volume is in the port's OWN Wwise bank** (not the map; no pooling, no marker).
  port_volume.bank_volume() shifts the Volume property (v88 prop id 0x00, dB float) of the
  bank's ROOT actor-mixer, which every sound of the bank plays through (checked: all 15
  sounds); the patcher passes `port_sounds.ensure('halo4', root, volume={port: dB})`.
  Focus Rifle mixer ships at -6 dB -> +6 headroom (capped at 0 until a boot shows Wwise
  plays a mixer above 0 louder). Boot 32: installed at -20 -> the beam "basically
  silent", the OVERHEAT NOT -- it was never the weapon's sound:
* **The Focus Rifle's overheat sound came from the FP GRAPH**, not the weapon: the port's
  graph is a byte copy of the Beam Rifle's and cues the Beam Rifle's foley on
  `overheating` (event-list sound reference 54) and `o_h_exit` (58), from the stock
  beam_rifle_player bank. (The weapon's own overheat attachments -- Reach-era
  fr_overheat lsnd, the Sentinel's overheated.effect -> bishop_beam -- name events no
  installed bank has: silent.) Now: h4_sound_bank.py IMPORTS those two events WHOLE into
  port_focus_rifle (event, actions, container + sounds, Vorbis media, their root
  actor-mixers trimmed to the copied children, the attenuation share-set they name),
  every id renamed, each copied root given a Volume property (0 dB) -- port_volume shifts
  EVERY root. h4_make_port_weapon.make_sound_tags: own overheat sound tags on the new
  events, the own event list's references 54/58 -> them, and the own graph's `imported
  events` -> its OWN event list (it still named the Beam Rifle's: the copied list was
  unused). Tag paths in an H4 tag file: a `frgt` chunk, group `!dns`, path WITHOUT
  extension. Headroom is now 0 (the copied roots sit at 0 dB) until a boot shows Wwise
  plays a mixer above 0 louder -- boot 33 tests overheat roots at +12, fire as built.
* **Boot 33: WWISE PLAYS A MIXER ABOVE 0 dB LOUDER** (overheat at +12 "definitely
  louder"; the exact amount not judged by ear) -- unlike the maps' Gain Base. Banks are
  capped at port_volume.BANK_CEILING_DB = +12 (the highest value tested), so the Focus
  Rifle's knob has +12 up (the overheat roots at 0) and the headroom rule is not needed
  for Halo 4. The overheat plays from the port's own bank (imports confirmed); the
  stronger fade (blue_haze curve) is good (user). As-built bank reinstalled.
  2. is the FMOD bank needed at all -- or does PC Reach play the map's MS-ADPCM? (the
     bank is a loose file a Steam verify removes; without it, nothing to restore).

**Halo 2 and Halo 1 (2026-10-03), CLASSIC ONLY** (user: every H1/H2 rebuild is classic):
* **Halo 2** -- `h2_saw_sounds.py --write`. Classic H2 in MCC plays the map's sounds as
  OPUS 48 kHz (4039 of 4456 on 03a), so: `sounds-single-layer <dir> <class>` then
  `reimport-sounds-to-opus <dir>`. The SAW's own saw_fire effect named the SMG's fire
  (its remastered-only fire_lod part is left: classic never plays it); the weapon names
  its dry fire SOUND directly (the Battle Rifle's). H2's gestalt pools gains like H3's
  (the SMG fire's entry: 871 sounds) -> the volume marker (-3.01), port_volume knows
  Halo 2 (snd! +0x6, ugh! Playback Parameters 0x38, Gain Base +0x10). H2EK's
  export-tag-to-xml needs ABSOLUTE paths (a relative output comes out empty) and writes
  `<field name="gain base" ...>-3.000000</field>`. The SAW is on 01b and 03a only; 03a
  rebuilt (`h2_batch.py --maps 03a --stage build`) + shipped (live + E:\HaloBaselines);
  01b is reserved for another test -- rebuild it when that is done.
* **Halo 1** -- `h1_saw_sounds.py --write`. Classic H1 plays Xbox ADPCM from the map (AR
  fire 22 kHz mono); the SAW audio is resampled to 44.1 kHz mono (numpy FFT, no scipy)
  and imported with `tool sounds <dir> xbox`, its playback fields copied from the AR's
  sound. The SAW fired through the AR's SHARED `fire bullet` / `empty` effects -> own
  copies in weapons\saw\effects (the casing eject kept), the weapon repointed in place
  AND in saw_weapon.py (which regenerates the weapon from the AR). No gestalt in H1: the
  knob scales the own tags' permutation GAINS (linear; a 0 in a tag plays as 1.0), built
  at 0.708 with the audio +3 dB soft-limited (headroom rule). All ten maps carry the SAW;
  a10 rebuilt + shipped (`h1_rebuild_all.py --maps a10`), the other nine still play the
  AR's sounds until rebuilt.
* **HALO 1 PLAYS FROM FMOD BANKS, NOT THE MAP (2026-10-04).** The first H1 builds were
  silent ("a Pea Shooter" = the casing click left in the effect), first because `tool
  sounds ... xbox` needs a Windows ACM codec missing here (it prints "MM: couldn't open
  stream" and still writes EMPTY permutations -- now `wav` + a samples check), then
  because MCC never plays a Halo 1 map's sound data at all: it plays
  halo1\sound\pc\sounds_adpcm.fsb (classic view: 3106 XBOX IMA ADPCM subsongs, the
  classic tags' own audio sample for sample) found by TAG PATH through
  lst\sounds_adpcm.lst.bin (`sound\old_sfx\...` for the maps' `sound\sfx\...`; the
  Anniversary view uses sounds_debug, CELT). Formats in tool\h1_fsb.py. The port's audio
  ships in tool\port_sounds\halo1 (h1_saw_sounds.py: tone D at the AR's level, 22 kHz
  mono) and tool\port_sounds.py appends it as `port_*` tail subsongs + index entries
  (the plain path AND an `old_` form, until a boot shows which lookup applies), with
  the stock files backed up (F:\HaloPortBackups\sound_stock). Volume = re-encoding at
  install (ensure(volume=...)); the map's tag gains do nothing. A Steam verify restores
  the stock bank: run `python port_sounds.py --write` (or patch) again.
* **CONFIRMED (test 5, 2026-10-04): the bank lookup works for a port sound OUTSIDE
  sound\sfx** -- the beep placed in the bank under `sound\weapons\saw_port\saw_fire`
  played. Two conditions, both learned the hard way:
  * the tag must be STOCK-SHAPED: 22 kHz XBOX ADPCM (h1_saw_sounds writes h1_fsb's
    encoder output into the permutations). With 44 kHz uncompressed tags (tests 0-1) the
    game never asked the bank -- only the effect's casing click played;
  * the tag must NOT live under sound\sfx: a new tag there CRASHED the game the moment
    the SAW became active (halo1.dll+0xB3605D, a garbage tag pointer) -- with the stock
    bank, with classic + Anniversary index entries, and with stock-shaped tags alike
    (tests 2-4). Presumably MCC pairs every sfx tag with an Anniversary counterpart.
  The index carries the plain path and an `old_` form (which one hits: not isolated).
* **FSB5 sample headers (the 'pea shooter' + AR 'clipping', 2026-10-04):** bits 5-6 are
  the CHANNEL count (0 mono, 1 stereo, 2 = 6, 3 = 8) and the data offset is bits 7-33 in
  32-BYTE units; every sample must start 32-aligned (stock: all). h1_fsb.py first wrote
  16-byte offsets -- a sample on an odd 16 read as 6-channel, 16 bytes early. The
  2-entry build only worked because each fire permutation was 8032 bytes (a multiple
  of 32). Also: halo1.dll SORTS the .lst entries itself after reading (file order is
  irrelevant) and keys them by path; one entry per path (an alias pair on the same
  subsongs made the summed count disagree with the bank). Bisect rule that found it:
  old working map + new bank still broken => the bank.
* **Halo 1 SAW reload + ready (2026-10-04):** the fp animation set (saw_anims.py, the
  AR's retimed) named the AR's reload / weapon ready. Halo 4 cues its SAW foley by FRAME
  (storm_fp_lmg.frame_event_list: reload fly_a@0 mech_a@15 mech_b@30 fly_b@54 mech_c@66
  fly_c@90 mech_d@90 of 128; ready fly+mech@0 of 35); a Halo 1 animation plays ONE sound,
  so saw_port_foley.py MIXES the cues at their frames (variation set k = recording k of
  each event -> permutations), stretched for a retimed animation. The H1 SAW's reload is
  128 frames like Halo 4's, so the cues land 1:1. Levelled to the H1 AR's own (active
  RMS: ar_reload -20.9, weapon ready -13.1 dBFS). saw_anims.py points both animation
  sets at the own sounds (the balanced set at a 164/128-stretched reload -- that set is
  not in the built maps today). Melee keeps the AR's.
* **Reload + ready, Halo 2 / 3 / ODST / Reach (2026-10-04):** every SAW graph cues ONE
  sound per animation at frame 0 (H2: frame 1), so the same saw_port_foley mixdown fits;
  every port's reload is 128 frames = Halo 4's (cues 1:1). saw_port_sounds.py (h3/odst/
  reach) and h2_saw_sounds.py import saw_reload / saw_ready (Reach: saw_reload_empty +
  _full) and repoint the graphs. Levels = each game's OWN donor (active RMS of the AR's
  reload/ready in its sfx.fsb + that tag's gain: H3 reload -38 dB effective, ODST -21,
  Reach -26), the volume marker kept. TRAP (Reach): repoint the graphs the WEAPON names
  (saw.weapon jmad refs: saw\fp_saw_*\fp_saw_*, which keep their sounds in a
  .frame_event_list too); saw\fp\fp_saw_*.model_animation_graph are unused leftovers --
  a first build edited those and m20 kept the AR's. Verify on the BUILT map
  (port_sound_refs.sounds_of, frms refs), not the kit.
* **The H3-engine chunk-size trap (Halo 3 / ODST, 2026-10-04):** with the reload in
  sfx.saw.fsb as dual-mono STEREO (917 KB, over the 0xC0000 = 768 KB chunk size the
  halo3.dll .info parser splits entries by) NO SAW sound played in either game --
  the fire neither (bisect: the same bank cut to the entries under 768 KB played; the
  structurally identical Reach bank with the same long entries plays). Foley is MONO
  there now (reload 459 KB) and check_bank_entries refuses entries over the size.
  MCC LOCKS a loaded game's sfx.saw.fsb -- install banks with that game closed.
* **Second batch (2026-10-04): melee, idle fidgets, Reach's first draw** -- same mixdown
  (saw_port_foley MELEE1/2, POSE1/2, READY_INITIAL). H4 has no SAW zoom audio in any MCC
  bank, so the ports keep their zoom. Halo 1: melee via the bank; the BALANCED reload
  (the patcher retimes the reload x1.28125 in the map) swaps to a mix stretched for it
  -- saw_anims.py ships it as an unused sound reference, the catalog's `anim_sounds`
  names the swap, port_sounds.retimed_anim_sound does it at patch time.
* **The H3EK FSBank trap (2026-10-04):** ONE `sounds-single-layer` call that puts 6+
  permutations into a NON-EMPTY bank fails -- `FSBank error! (7) An operating system
  based file error` -- for any sound (fire too), re-imported permutations count, 1-3 work,
  any count into an EMPTY bank works; one core or NUMBER_OF_PROCESSORS=1 change nothing.
  The tool STILL WRITES THE TAG, so the build carries on and the map names hashes the bank
  lacks (the H3 melee shipped silent). The ODST and Reach kits have no such limit. Fix:
  every sound into its own fresh bank, merged by fsb5_merge.py (byte-identical to a
  kit-built bank but for the per-build hash); every import fails on `-ERROR-`, and
  check_bank_complete wants one bank entry per imported wav. A bank-only fix needs no
  rebuild: the map's subsound hashes come from the wav paths.

## Halo 4 as the TARGET -- the H4 port kit (started 2026-09-30)

Every earlier port carried the Halo 4 SAW OUT of Halo 4. This kit ports INTO it. First
weapon: **Reach's Focus Rifle**, chosen as an easy one. The master list of what each game
lacks is the user's spreadsheet (`Halo Weapons Spreadsheet (CE - Infinite).ods`, Sheet2).

### What H4EK is, measured

* **Import is sidecar/Granny only**: `tool import <sidecar>` -- no JMS verb at all. So the
  Foundry route the Reach SAW proved is not a workaround here, it is THE route.
* **No legacy shaders**: H4EK has no .shader tags and no shader.render_method_definition.
  Surfaces are `.material` tags on material shaders (`shaders\material_shaders\...`).
* **Leftovers are not a weapon**: H4EK carries `rifle\focus_rifle` -- but only feedback and
  impact effects, no weapon, model or graph. The same goes for other Reach-era folders
  (needle_rifle, plasma_repeater, plasma_rifle, spike_rifle). Check before assuming.
* **Weapons have no chud** (see halo4 scoping): the HUD is a `cusc` screen referenced from
  weap 0x4E0. First-person graphs live at
  `objects\characters\storm_fp\weapons\<cat>\fp_<name>\storm_fp_<name>`.
* **Residency is designer zones**: a port must be in the map's `dz_enhancer`, ticked in
  every zone set (Foundation), and an EK rebuild must be copied into
  `E:\HaloBaselines\halo4\maps` or the next enhancer patch discards it.

### The donors (first pass)

    geometry            the Focus Rifle's own, from HREK, through Foundry
    materials           the Beam Rifle's (Covenant, same family), bitmaps repointed
    behaviour + fx      storm_sentinel_beam -- a continuous plasma beam with heat, like the
                        Focus Rifle; H4EK ships its weapon, projectiles and fx, and only its
                        MODELS are null (why it can never be a pickup today)
    fp animation, HUD   the Beam Rifle (fp_beam_rifle, its cusc screen and scope). Reach's
                        own fp graph is built on Reach's arm skeleton and does not carry over

### Status

    1 geometry        DONE   h4_foundry_port.py --import (HREK) / --export (H4EK): render,
                             collision, physics, model; 14 nodes; 0 errors
    2 materials       DONE   h4_port_materials.py: metal/shell/rubber on the port's own
                             diffuse + normal + a control map built from Reach's diffuse
                             alpha; the glowing surfaces borrow the Beam Rifle's scope
                             material as a first pass. All 8 resolve in the render model.
    3 own tags        DONE   h4_make_port_weapon.py, v2 on the SENTINEL BEAM (first boot
                             of the Beam-Rifle-based tag: model fine, the weapon DID NOT
                             FIRE -- a single-shot sniper barrel fed a continuous beam).
                             Barrels -> the port's own beam copy; model, fp model, fp
                             graph and HUD set BY FIELD NAME through ManagedBlam
                             (h4_weapon_refs.py). The Sentinel Beam's tag actually names
                             the Focus Rifle's Reach paths -- in Halo 4 it IS the Focus
                             Rifle's weapon tag, missing its model.
    4 numbers         DONE   balance_port.py via the SNIPER RIFLE (user: a sniper that is a
                             laser); h4_tag_numbers.py bakes them by name, read back. The
                             copied friendly beam dealt ZERO damage: now 3.
    5 catalog         DONE   make_port_catalog_h4.py: 36 rows; heat + battery carried as the
                             port's own (the sniper has neither); Beam Damage MEASURED x1.0
                             (sniper round 80 in both); Shots Per Fire dropped (Reach 0 =
                             H4 minimum 1)
    6 ammo pickup     n/a    energy weapon
    7 HUD             DONE   own cui_screen (a Plasma Pistol copy: battery % in the weapon
                             panel, heat under the reticle) + OWN Reach scope template (h4_reach_scope*.py, boots
                             21-25). Side meters hidden (empty in game; layout unsettled)
    8 icon + text     DONE   own glyph U+E1F6 in the live icon packages, fr_* pickup lines,
                             HUD icon line (boot 20). OPEN: non-English lines --
                             `strings-localized` imported 0, unchecked in game
    9 animations      DONE   own graph = byte copy of the Beam Rifle's + overheating loop
                             frame (boot 26); ready playback 24/22 = Reach's swap timing
    fx                DONE   beam (Sentinel tracer look, n-gon, Reach palette), orange muzzle
                             flash (own Storm Rifle copy, boot 22). Firing sound: see sound
    aim               DONE   Beam Rifle aim assist + strict deviation + hidden gun when zoomed
    sound             DONE   own Wwise bank (Reach in/loop/out as PCM) via tool/port_sounds.py,
                             firing loop as a weapon attachment, Beam Rifle zoom sounds (boot 31)
    ** COMPLETE 2026-10-03 (boot 31): every step confirmed in game; backup
       F:\HaloPortBackups\2026-10-03_focus-rifle-h4. Open only: non-English pickup
       lines unchecked in a non-English client. **

**First test: m30_cryptum** (user's choice). Add the Focus Rifle to m30's `dz_enhancer`,
tick that zone in the zone sets where it is tested (m30 has it in only 4 of 24), place it,
rebuild, install -- and copy the build to `E:\HaloBaselines\halo4\maps` or the next
enhancer patch rebuilds from the old one.

### Run order (every rebuild of the port)

    blender --background --python h4_foundry_port.py -- --import    (HREK)
    python h4_port_materials.py --write
    blender --background --python h4_foundry_port.py -- --export    (H4EK)
    python h4_reach_scope_art.py --write         scope bitmaps (once; boot 21)
    python h4_muzzle_recolor.py --write          own orange muzzle effect (boot 21)
    blender --background --python h4_beam_look.py -- --write   own beam tracer (+ fade)
    python h4_sound_bank.py                      own Wwise bank -> tool/port_sounds/halo4
    python ..\port_sounds.py --write            bank into the live sfxbank.pck (no rebuild)
    blender --background --python h4_fp_graph.py -- --write   own fp graph = byte copy + loop fix
    python h4_make_port_weapon.py --write        re-copies the donor weapon every time
                                                 (and the HUD: icon + Reach scope)
    blender --background --python h4_tag_numbers.py -- --write      so this comes LAST

**Second boot (2026-09-30):** ground model good, heat/overheat and battery WORK on the
Sentinel base; first-person model invisible but casting a SHADOW; no beam seen. Measured
against the Beam Rifle's render model: the port's parts carried part flag 16 "Draw Cull
Distance Medium" -- Reach's per-face "Draw Distance Mid", kept through Foundry. Halo 4
applies it to the first-person weapon; the Beam Rifle's body has none. --export now
resets it (all part flags 0). The beam's firing effect hangs off the fp model's markers,
so "no beam" may be the same cull -- the next boot separates that from a projectile fault.

**Third boot (2026-10-01):** unchanged -- fp invisible, no beam -- but DAMAGE LANDS, so the
projectile is fine and only drawing fails. The cull flag was not it. Diffing the .model
against the Beam Rifle's: Foundry wrote **zero variants** where every Bungie weapon has
one (`default` -> region `default` -> permutation `default`). The ground object draws its
render model directly; the first-person weapon and the effects on its markers go through
the variant. --export now adds it (add_default_variant, ManagedBlam).

**Fourth boot:** still invisible, still no beam -- the variant was not it either (kept: it
matches every Bungie weapon). Diffing the WEAPON tags flag by flag (ManagedBlam flags by
name) against the Beam Rifle's: the Sentinel Beam carries object flag **"extension of
parent"** -- its gun was part of the Sentinel's body. Held by the player, it draws as part
of the player, whose body first person never draws: invisible, shadow cast, beam effects
on its markers hidden, damage landing. h4_make_port_weapon.py clears it (h4_weapon_refs.py
`clear-flag:`). Lesson for every donor that was an NPC's built-in gun: diff the FLAGS.

**Fifth boot:** unchanged. A FULL field diff of the two weapon tags (not just flags) shows
more NPC-gun leftovers, now set to the Beam Rifle's by h4_make_port_weapon.py (`set:`):
object bounding radius 0 / offset 0 (Beam Rifle 0.3 / 0.215 -- the gun used its parent's
bounds), weapon ready 1st person animation playback scale 0 (1), weapon name `bb` and
class `pistol` (the fp graph is the Beam Rifle's `csr`, a rifle). If the sixth boot is
still invisible, the next test swaps the BEAM RIFLE's render model in as the fp model:
model fault vs weapon-tag fault in one boot.

**Boots 6-7 WITHOUT rebuilds** (h4_map_poke.py writes the built map in place): the
leftovers changed nothing; then the SWAP TEST -- the Beam Rifle's render model as the fp
model on the port's weapon -- DREW. So the weapon tag was fine and the model was not.
Ruled out at the desk, no boot: render-model geometry flags (the build sets 39 on both).

**THE TWO REAL CAUSES, found by data:**
  * **First person: the skeleton must map into the fp graph.** The port is animated by the
    DONOR's fp graph. All 14 of the Beam Rifle's render-model nodes are in fp_beam_rifle;
    of the Focus Rifle's 14 only b_gun is -- and Halo 4 does not draw a first-person model
    whose nodes do not map. --export now collapses the armature to b_gun (vertices to
    b_gun, markers re-parented at their world positions). Recipe rule: **a port borrowing
    an fp graph must use only node names that graph contains.**
  * **The beam: first person draws no third-person effect.** The right trigger fires
    barrel 0, the Sentinel's "enemy" barrel, whose firing effect bsh_firing has ONLY a 3p
    tracer -- an NPC gun is never seen from inside. Its damage landed, nothing showed.
    Repointed to the friendly firing effect (1p + 3p tracers).
Both need the eighth boot after a real rebuild.

**Boot 8 (rebuild): the FIRST-PERSON MODEL DRAWS** -- the skeleton was it. The beam still
did not. **Boot 9, poked (--beam-test): the port firing the Beam Rifle's projectile DREW
a beam.** So the weapon and model can show one, and the Sentinel's first-person tracer is
what never draws. Why: Halo 4 draws a player's beam from the PROJECTILE -- the Beam
Rifle's firing effect is a sound and a light, and its projectile carries the beam as an
object ATTACHMENT (fx\projectile). The Sentinel draws its beam as a 1p tracer in the
firing effect, a path no player ever exercised. h4_make_port_weapon.py now gives the
port's own projectile that attachment (h4_weapon_refs.py `add-attachment`). Recipe rule:
**a donor's visuals must be the kind the PLAYER path draws.**

**Boots 10-11:** the beam DRAWS (thin, end-on: it leaves the camera). Muzzle start: the
gun-origin barrel flag fires from the gun's WORLD position, which first person draws
elsewhere -- no visible help; not kept. "Draw in first person pass" on the Sentinel's
point-to-point tracer: no change. **The look:** H4 has NO beam_system tags; Bungie
converted the Focus Rifle's beam into the Sentinel's tracers -- a "cross" (two ribbons,
double-sided) where the Beam Rifle's streak is one thin "aligned ribbon". The port now
owns a copy of that tracer with point-to-point CLEARED, riding the projectile inside its
own copy of the Beam Rifle's projectile effect (fx\beam, fx\beam_projectile).

**The overheat jerk** (user's slow-motion video: the whole fp view shifts right ~2 frames
at the end of overheating). h4_fp_jump.py measured the Beam Rifle's graph, hands + gun
against the camera: overheating->o_h_exit 0.0010 (authored to join), but overheating->
overheated 0.0353 and overheated->o_h_exit 0.0350 -- the `overheated` hold is DISPLACED,
all base animations (not an overlay artifact), and no o_h_exit frame matches it (closest
0.031), so trimming frames could not fix it. h4_fp_graph.py writes the port's OWN graph
(storm_fp\weapons\rifle\fp_focus_rifle) with `overheated` as a still hold of
overheating's last frame (both hand-offs <=0.001), keeping the SHIPPED frame_event_list
(Foundry's round trip lost events: 25,224 vs 32,491 bytes). The Beam Rifle never
overheats in normal play, so nobody saw this.

**TRAP: Foundry's graph IMPORT rewrites the source graph's frame_event_list** -- it
changed the Beam Rifle's shipped one (32,491 -> 30,376 bytes). Restored from H4EK.7z
(bin\x64\7zr.exe e H4EK.7z <path>); h4_fp_jump.build_rig now keeps it byte for byte.
H4EK.7z is the clean source for ANY shipped H4 tag.

**Boot 12, both WRONG:** the unpinned Sentinel tracer drew NOTHING (its length runs along
the point-to-point profile; without two points it has none) -- back to the Beam Rifle's
streak. And the jerk STAYED with the `overheated` hold made still, followed by a FREEZE
(that still hold): so the jerk is BEFORE the hold, inside `overheating`. **The jolt:**
--detail overheating -> frame 44 kicks 0.0205 (~10x its neighbours), 45-49 drift back;
frames 27-37 are a deliberate fine shake. h4_fp_graph.py now smooths ONLY frames 44-46
(a line from 43 to 47; worst spike 0.0144 -> 0.0035) and leaves every other frame,
`overheated` included, as Bungie made it. Verified on the exported graph itself.
Method note: an animation glitch the user sees as "a jerk" can be a mismatched
HAND-OFF or a SPIKE inside one animation -- measure both, and use the user's ordering
(jerk-then-freeze) to tell which.

**User correction (boot 13): the jerk is "within the overheated animation when the heat
is vented".** `overheated` is internally clean (loop seam 0.0009) and `vent_*` too; the
jerk is the 0.035 hand-off overheated -> o_h_exit, which starts while heat still drains.
The still-hold of boot 12 froze the motion; the fix SHIFTS `overheated` as a whole (every
channel + overheating's last minus overheated's first), keeping its motion: joins
0.0000 / 0.0009, verified on the exported graph. The frame-44 jolt smoothing stays (a real
spike). Lesson: ask WHEN in the game state a glitch happens before choosing which seam.

**Boot 14: jerk still felt.** Not the overheat camera shake either (weap 0x330 nulled,
`--no-overheat-shake`: unchanged). The user's second video, frame-differenced: ONE frame
(56 of 124, ~52% heat) with BOTH hands and the rifle shifted -- not in the animation data
(the frame-44 jolt was right hand only; every hand-off <=0.001; b_camera_control never
moves). Diagnostic poke `--graph-pp`: the Plasma Pistol's fp graph, whose overheat chain is
used in normal play (it has b_gun, so the port's model still draws).

**The beam look, solved on paper:** the Sentinel's 3p tracer IS the Focus Rifle's beam
(center on energy_trail + two plasma layers: plasma_trail_a/b noise through a palette --
Reach's own textures, all present in H4 under fx\reach). Unpinning failed because its
LENGTH functions run on "profile position"; the Beam Rifle streak's run on "profile age".
h4_beam_look.py: own copy of the Sentinel tracer, the streak's length/offset/lifespan/
self-acceleration functions copied in field by field, palette -> Reach's
focus_rifle_plasma, point-to-point cleared; in an own copy of the streak's effect, attached
to the port's projectile. Z-510 (storm_anti_infantry_turret) = the same "bsh" point-to-point
mechanism, not usable for a player weapon.

**Beam FADE-OUT (2026-10-03, user):** the Sentinel tracers keep a constant profile alpha
(1.0 on profile position), so each segment stays opaque until its lifespan ends. Most stock
H4 trails fade by PROFILE AGE (curve functions, type 08); the Beam Rifle streak core:
(0,1) (0.27,1) (0.863,0.321) (1,0). h4_beam_look.py now copies that `profile alpha` onto
all three tracers (FADE), peak kept at 1.0 (the streak's is 0.9). Both blend
add_src_times_srcalpha, so alpha dims the glow. ManagedBlam's TagValueCustomFunctionEditor
(`st.SelectField('Mapping').Value`) EVALUATES and edits these curves: Evaluate(x, range),
Get/SetControlPoint(graph, i) -- use it to read a function's shape instead of decoding
the blob. Boot 32: fade visible, "could be stronger" -> the streak's SECOND tracer's
curve (blue_haze: (0,1) (0.2,0.747) (0.877,0) (1,0)), FADE_FROM = 1 (boot 33).

**Boot 15 (rebuild):** the Plasma Pistol graph has NO pop -> the Beam Rifle chain. Its VENT
set (vent_enter/loop/exit, absent from the Plasma Pistol's; vent_enter steps 0.058) is now
LEFT OUT of the port graph (37 animations). The overheat shake (frames 27-37, +-0.005
alternating -- the Beam Rifle's, not the Focus Rifle's) damped by a 5-frame moving average:
0.0096 -> 0.0018. The beam: drew, "2-dimensional" and too long-lived -> n-gon tube, 6
sides (Reach's own 1p beam was an n-gon), profile lifespan 0.35..1.0 -> 0.175..0.5 s
(function data floats at +4/+8). Spawn point: each barrel's FIRST PERSON OFFSET (+x
forward, +y left, +z up) -- first-person only, unlike the gun-origin flag; starting guess
0.13,-0.05,-0.05, tuned without rebuilds via `h4_map_poke.py --fp-offset x,y,z`.

**Boot 16:** the pop SURVIVED dropping the vent set; the Plasma Pistol's overheat set also
lacks `o_h_exit` (overheated goes straight back to idle), so that is left out too. The
overheat damping is reverted (the user meant the shake WHILE FIRING). Offset tuned in game:
**0.03,-0.08,0.00**. Firing shake + muzzle flash tested by poke first: the per-shot
"Firing Damage" (barrel firing effect +0x54: camera shake + rumble + simulated input --
Reach's Focus Rifle had all three too) nulled, and the Suppressor's muzzle-flash-only
effect (storm_forerunner_smg\fx\fr_smg_firing_muzzle_flash, no shot sound) in each
barrel's "Optional Secondary Firing Effect" (+0x44).

**Boot 17:** pop still there. Dropping o_h_exit was a MISTAKE -- the Plasma Pistol HAS one
(an earlier name filter on heat/vent/overh missed it); restored. A full name diff of the
port graph against the Plasma Pistol's leaves three OVERLAYS only the Beam Rifle has:
flaps (1 frame), barrel_spin (21), accelration_screens (9), blended by weapon functions --
and the port's weapon exports `heat` as blend_weight / blend_weight_barrel. Heat crossing
a threshold mid-vent on a one-frame overlay = a one-frame pop at ~half heat. All three are
left out (34 animations). Lesson: compare graphs by the FULL name set, never a filtered one.

**THE POP, SOLVED (boot 19) -- by in-map bisection, no rebuilds** (h4_map_poke.py
--action-anim / --anim-flags / --loop-frame on the compiled graph, layout =
halo3_reload.LAYOUTS['Halo 4']). Steps: o_h_exit -> overheated: pop stays; overheated ->
idle: pop stays, but now visibly "right before the idle" = the END of `overheating`; the
"Disable Weapon Aim/1st Person" flag (0x18 vs the Plasma Pistol's 0x08): not it.
**Cause: `overheating`'s LOOP FRAME INDEX was 0** -- at its end the engine wraps to the
loop frame for ONE frame before the next state, and frame 0 is the pre-overheat pose.
The Plasma Pistol's is 16. Set to the last frame (58): pop gone. h4_fp_graph.py sets it
after export (set_loop_frames). The earlier removals (vent set, overlays) are harmless to
the Focus Rifle and kept; o_h_exit and Bungie's motion are intact.
**Method lesson:** when two graphs differ in behaviour, diff their COMPILED per-animation
fields (loop frame, playback flags, frame counts) in the built map -- not only names and
poses -- and bisect by poking one field per boot.

**Firing feedback + muzzle (kit):** per-shot response = the Assault Rifle's
(storm_assault_rifle_firing; the Sentinel's was too strong at 30/s, the Storm Rifle's too
weak); muzzle flash = the Storm Rifle's firing effect in the optional secondary slot
(needs primary_trigger + fx_vent, both on the model) until the Focus Rifle's own Reach
muzzle particles are ported.

### Step 7 / 8 in Halo 4: the HUD scope, the pickup lines, the pictogram (2026-10-02)

* **Scope:** the port's OWN copy of the Plasma Pistol's cui_screen (in a built map a screen
  is one shared tag -- grafting the shared one would scope the real Plasma Pistol), then
  AFTER EACH BUILD `h4_map_poke.py --scope`: the enhancer's in-game-proven
  `_apply_h4_scope` with the Beam Rifle's screen as donor.
* **Lines:** they live in `ui\strings\ingame` (not a hud_messages list), five ids like
  Halo 3's; the Sentinel base carried the Beam Rifle's `be_*`. `h4_port_messages.py`
  clones them as `fr_*` ("Focus Rifle"), English in every language (Halo 4's prompts NAME
  the weapon, so a translated line cannot be cloned safely); `tool strings` imports
  English, `strings-localized` reported 0 for the others (fallback). Only ingame.txt may
  sit in data\ui\strings when importing (the verb takes every .txt).
* **Pictogram:** Halo 4's icon packages are the Halo 3 container with **0x10000 blocks**
  (h3_font_repack rebuilds all four byte for byte with BLOCK = 0x10000); a glyph record
  has a **12-byte header** (u16 advance, size, width, height, 0, 12*res) over Halo 3's
  codec (408/408 decode exactly); x2-x4 are exact multiples; pickup pictograms are font 2
  (icon\fixedsys-hud). `h4_mesh_dump.py` + `h4_weapon_glyph.py` draw the port's side
  silhouette and add it at U+E1F6 (no Focus Rifle macro exists); the lines carry the
  literal character. Packages are loose: no rebuild for the glyph, one for the lines.

**Boot 20:** pickup prompt IN. Player-HUD icon NOT: the screen's `weapon_icon_text`
names a string id from `ui\strings\weapons` (`plasma_pistol_icon = "&plasma_pistol"` on the
copied screen) -> `focus_rifle_icon` (the port's glyph) added there and the screen
repointed (h4_hud_icon.py, run by h4_make_port_weapon.py after every screen copy).
Muzzle: the re-enabled Reach particles drew NOTHING (Bungie disabled them for a reason) --
back to the Storm Rifle's flash. Scope: the graft is the H4 BEAM RIFLE's (vector polyart,
19 assets); Reach's Focus Rifle scope is BITMAPS (scopes\beam_rifle_scope + meters +
overheat border) -- recreating it means a new H4 scope template on imported Reach bitmaps.

**Boot 21 -> the port's OWN Reach scope and an orange muzzle (kit, needs a rebuild):**

* **Reticle drift = the Beam Rifle scope's PARALLAX** (user: "always moves to the right
  ... returns to the centre when I don't move"). That template parks its art in four
  parallax containers driven by parallax listener -> expression `0+(a*10)` ->
  container prop_left/prop_top bindings. The port's own template has none of them.
  (`h4_map_poke.py --fp-offset 0,0,0` was poked into the boot-21 map as a control test:
  if the drift went with the old scope, the 0.03,-0.08,0 offset is innocent and stays.)
* **Reach's scope, read from its chud definition** (HREK ui\chud\focus_rifle):
  scope mask (a8, double sized, origin -1,-1, scale 1.2, mirrored both ways = the
  lower-right QUADRANT of a 2:1 mask, black at the bitmap's alpha); heat meter right
  (+435), battery meter left (-435), scale 1.19; meter frames (triple sized, origin 6.8,
  mirrored); reticle hud_reticles sequence 22. Units: 1152x640 chud, centred; double
  sized = 2 px a unit; ORIGIN is in half-extents of the bitmap. The meter bitmaps are
  horizontal arcs but stand upright in the frames: a quarter turn.
* **h4_reach_scope_art.py**: exports the Reach bitmaps (HREK `tool export-bitmap-tga`
  works off its "save directly" fallback), bakes mask + frames + reticle into ONE
  1920x1080 picture for the 1280x720 HUD, and turns the meters into Halo 4 meter bitmaps.
  **Halo 4's hud_meter reads R = A = shape, G = B = fill threshold (255 top -> 0 bottom)**,
  measured on the Beam Rifle's heat_bar/ammo_bar; Reach keeps the shape in A. Bitmap tags
  start as copies of the Beam Rifle's (import settings kept by `tool bitmaps`).
* **h4_reach_scope.py** (run by h4_make_port_weapon.py after each HUD copy): template =
  the Beam Rifle's minus every parallax binding, polyart hidden (prop_visible 0), its
  three bitmap widgets repointed (frame full screen, meters in the frames); then wires it
  into the port's HUD the way the Beam Rifle's HUD carries its own: a `template
  instantiations` row, one HUD component per template component (ti = that row) under an
  own transformation container in scope_container, zoom_decision/zoom_on_off + their two
  bindings + the "> 0" long comparison, the three sniper_zoom animations, and meter
  bindings weapon_data_reader.prop_charge -> ammo_animator, prop_heat -> shader_heat_bar.
  The HUD's own reticle fades out while zoomed (the Reach reticle is in the art).
  **`component indices` is SORTED BY STRING ID NUMBER** (ManagedBlam GetRawData of the
  name) and rebuilt. Cross-tag copies go field by field -- ManagedBlam's
  CopyElement/PasteAppendElement use the Windows clipboard and failed once in a kit run.
  The in-map graft (`--scope`) is no longer needed; it refuses an already-scoped HUD.
* **Muzzle colour:** REACH'S FOCUS RIFLE MUZZLE IS ORANGE (its effect's particle tints,
  read through HREK's ManagedBlam: (255,98,42) -> (255,92,0), sparks (255,200,72) ->
  (238,83,31); the firing light stays blue-violet). `h4_muzzle_recolor.py` copies the
  Storm Rifle flash and its 10 parts to focus_rifle\fx\muzzle, drops the Storm Rifle's
  fire SOUND part, moves every colour to Reach's orange (colour functions: byte 2 = colour
  count, a two-colour function's colours in u32 slots 0 and 3 -- Reach uses the same
  layout) and gives the six palette bitmaps own recoloured copies.

**Boot 22 (rebuild):** muzzle flash GOOD. Control test before it: barrel offset 0,0,0 in
the old map still drifted ("when looking around") -> the offset is innocent, the drift was
the Beam Rifle scope's parallax. Three faults, all mine:
* **No zoom, wrong heat:** h4_make_port_weapon.py re-copies the Sentinel Beam, and
  h4_tag_numbers.py (magnification levels 0 -> 2, heat values) was not run after it.
  h4_make_port_weapon.py now runs it as its LAST step.
* **Scope drawn all the time (side bars + a second reticle):** in a HUD, a TEMPLATE
  INSTANCE row's `type` is the template component's NAME (Bungie's Beam Rifle HUD,
  compiled: type sid == name sid on every ti=1 row), not its widget class. Written as
  the class, the rows were never tied to the zoom-faded container.
* **No dark lens mask:** prop_alpha_blend_mode 1 is ADDITIVE (the Beam Rifle's glowing
  polyart); its dark vignette leaves it UNSET.

**Boots 23-24:** zoom back, unzoomed fine; the user keeps the HUD's OWN reticle zoomed too
(Reach reticle out of the art, no fade -- the heat readout under it shows when zoomed).
* **Black block:** an EXPLICIT prop_alpha_blend_mode 0 drew the whole frame opaque.
  Bungie leaves the property UNSET on 1707 of 1727 HUD widgets sampled; unset != 0.
* **THE RETICLE DRIFT, found by a field diff of the weapon against the Beam Rifle and
  Plasma Pistol:** the Sentinel Beam (an ENEMY gun) carries aim assist modes with a 20 deg
  autoaim cone and a **20 deg DEVIATION ANGLE** -- how far Halo 4 lets the aim, and the
  reticle with it, leave the screen centre (Beam Rifle 0.4, Plasma Pistol 4). Not the
  scope's parallax (gone, drift unchanged), not the barrel offset (zeroed, unchanged).
  Both modes -> the Beam Rifle's; top-level deviation 0; zoomed aim speed 0.5 -> 1.
  LESSON: a weapon based on an AI gun inherits AI aim assist -- diff ALL of it.
* **Side meters stayed empty** with heat and battery (weapon_data_reader.prop_battery --
  prop_charge is the Plasma Pistol's OVERCHARGE) bound; hidden for a while. **SETTLED
  2026-10-03:** an imported bitmap tag stores the SOURCE TIFF beside the PROCESSED pixels,
  and the byte reads of boot 24 hit the source copy, so the "fix" swapped the layout the
  wrong way. Read through ManagedBlam ('processed pixel data'), Bungie's heat_bar is
  B,G,R,A = threshold, threshold, shape, shape -- R = A = shape, G = B = threshold, the
  ORIGINAL layout -- and `tool bitmaps` stores a TIFF's RGBA exactly so. In-game control
  (`--meters-br-bitmap`): Bungie's bitmap in both widgets filled with battery and heat,
  so the bindings were right. Boot 23's "empty" was the overcharge binding plus no
  firing. Meters shown again.

**Boot 25:** zoomed view visible. Three findings:
* **Scope art short of the screen edges:** Halo 4's HUD area is inset; Bungie's own dark
  vignette in the Beam Rifle scope is drawn 15% larger (scale 1.15 at -96,-54). The Reach
  art is now scaled 1.15 on a canvas 1.5x the HUD area, padded with the mask's dark edge
  (frame widget -320,-180 1920x1080).
* **Drift left (slight unzoomed, more with zoom):** without the weapon flag **strict
  deviation angle** Halo 4 raises the deviation to the AUTOAIM angle (plugin tooltip) --
  2 deg unzoomed, 1 in the modes; the Beam Rifle sets it. Set.
* **Gun still drawn when zoomed** (the pistol hides it): flag **hide FP weapon when in
  iron sights** ("for scoped weapons"), set like the Beam Rifle. h4_weapon_refs.py now
  takes '/name' for a TOP-LEVEL field ('/flags' = the weapon's own; a bare 'flags' finds
  item/object/flags first).
* Projectile origin when zoomed: the tag has ONE first-person offset per barrel, nothing
  per zoom level -- the beam starts at camera + offset in both states.

**Boot 26 -> THE RETICLE DRIFT, SOLVED (no rebuild, by poke bisection):**
* Unchanged by the deviation fixes. In the HUD nothing binds the reticle's position: it
  sits in a `reticule_offset_container`, which the ENGINE moves. Pokes, cumulative:
  acceleration scales 0 -> 1 (`--accel-scale`): no change; the port pointed at Bungie's
  own fp graph (`--graph-back`): **drift gone**; that graph with only the overheating
  loop-frame fix (`--on-beam-graph --loop-frame 16=58`): no pop, no jerk, no drift.
* **Cause, in THIS port: the port's re-exported fp graph** (Foundry round trip plus the
  smoothing/shift/drops of the pop hunt). Every per-animation flag, loop frame and frame
  count matched Bungie's (compiled diff), but the animation DATA differs, and with
  Bungie's own graph the drift is gone. Which part did it (the round trip itself, or one
  of the edits) is NOT isolated. h4_fp_graph.py now makes the Focus Rifle's graph a BYTE
  COPY of the shipped one plus the loop-frame fix; `--foundry` keeps the old route.
  **For other ports, an observation, not a rule (one port so far):** if a re-exported
  fp graph shows reticle drift, compare against the shipped graph by poke
  (`--graph-back`) first, and prefer copy-and-edit-the-field when only a field needs to
  change. A Foundry export may well work for another weapon -- verify on more H4 ports
  before ruling it out.
* **Zoomed beam origin -- not achieved on the Focus Rifle.** The Light Rifle
  (storm_forerunner_rifle) splits by zoom with trigger behavior **latch-zoom** (primary
  barrel 0 unzoomed, secondary barrel 1 zoomed). On this port `--zoom-barrel` (latch-zoom,
  nothing else changed) fired ONE shot per press, zoomed or not. Among the shipped H4
  weapons only per-press ones use it (BR, Light Rifle); the automatics use spew. Untried:
  other trigger settings alongside it (autofire time, a second trigger), and per-press
  ports, where it may work as it does on the Light Rifle. The Focus Rifle keeps
  0.03,-0.08,0 in both views (user accepted).
* **Seen in the m30 build: identical blocks MERGED.** Both barrels' first-person offsets
  (equal in the kit) were ONE block in the map, so poking one moved both. Check block
  pointers before poking a per-barrel block; `--zoom-barrel` gives barrel 1 its own 12
  bytes (halo_patch._h3_reserve) when they are shared.

**2026-10-03, measured without a boot:**
* **Swap timing (step 9):** both graphs 30 fps. Reach's Focus Rifle: ready 22 frames,
  put_away 6, ready_initial 29, ready_overheated 22. The Beam Rifle graph: 24 / 5 / 29 /
  19. No ready time on either weapon. Halo 4's lever is the weapon's ready playback scale:
  24/22 = 1.0909 (kit) makes the ordinary ready Reach's; put_away (1 frame) has no field.
* **Languages:** the `strings-localized` "imported 0" was misleading -- the built tag has
  all 17 language offsets for every fr_* line and focus_rifle_icon, each the English text
  (by design). Unconfirmed in a non-English client.
* **Firing sound -- the audio is in neither kit.** Reach: the HREK sound tags hold only
  metadata ("sound data resource <unavailable>"); the audio is in MCC's FMOD bank
  `haloreach\fmod\pc\sfx.fsb` (FSB5, Vorbis, 16162 samples; names in sfx.fsb.info).
  Halo 4: a sound tag is a WWISE EVENT NAME + a .soundbank tag naming a bank inside
  `halo4\sound\pc\sfxbank.pck` (AKPK, bank version 88); H4EK has no Wwise project and no
  audio import verb. A port needs: extract (an FSB5 Vorbis decoder) -> author a v88 bank
  + event -> add it to the package (or reuse an existing event's audio, which is
  hijacking). Research below.

**Halo 4 sound, mapped 2026-10-03 (h4_wwise.py, no boot):**
* `halo4\sound\pc\sfxbank.pck` = AKPK v1: header 0x1C (magic, header size, version,
  language-map / bank-LUT / stream-LUT / externals sizes), language map (1: "sfx"), bank
  LUT of 577 entries (id, block size 1, size, start = BYTE offset, language). Bank id =
  Wwise FNV-1 of the soundbank tag's name, lower case ("sentinel" -> 0xfb27dc31).
  sfxstream.pck holds 2085 streamed media. sfxbank_dlc.pck / sfxstream_dlc.pck are
  4-byte "Stub" files; whether the game mounts them is unknown (names not in halo4.dll
  as plain strings).
* Banks are version 88 (BKHD, DIDX, DATA, HIRC). The .sound tag's event name hashes to
  the HIRC event. Sentinel friendly beam: `play_..._fire_in` = play a start one-shot
  (2.55 s, in a random container) + play a LOOPING sound (4.6 s);
  `stop_..._fire` = stop the loop + play a tail (1.6 s). Reach's Focus Rifle has the
  same three: in / loop / out (sfx.fsb subsongs 10952-10954).
* Codecs in all banks: Wwise custom Vorbis 12706 embedded + 1217 streamed, **PCM 450
  embedded + 189 streamed**, a few others. Custom Vorbis needs Wwise's encoder; **PCM
  is writable by hand**: RIFF/WAVE, fmt 24 bytes (tag 0xFFFE, 16-bit, cbSize 6, u16 0,
  u32 channel mask), JUNK 4, data. A sound object's first fields: codec plugin
  (0x00010001 PCM, 0x00040001 Vorbis), stream type (0 embedded), media id, bank id,
  in-bank offset (DIDX offset + start of DATA payload), size.
* Plan, test 1 (no map rebuild): rebuild the sentinel bank with those three media as
  Reach's audio in PCM, the three sound objects switched to PCM; append it to the end of
  sfxbank.pck and repoint its LUT entry (20 bytes, in place; restore = put the entry
  back and truncate). The port fires the Sentinel friendly beam effect, so it would sound
  like Reach's Focus Rifle -- and so would friendly Sentinels' beams, for the test only.
  Then the real thing: an OWN bank and own event names, own .sound / .sound_looping /
  .soundbank tags in H4EK, a new LUT entry (or the DLC package), map rebuild.
* **Boot 29:** firing SILENT with the test bank, and again after `--restore`, with the
  port's Player Sound Bank poked to the sentinel bank -- while the OVERHEAT loop plays.
  The overheat loop is an OBJECT ATTACHMENT on the weapon (weap 0x118: lsnd, primary
  scale `overheated`); the Sentinel's firing loop sits in its firing EFFECT's "looping
  sounds" block (alive only as long as the per-shot effect), and its one-shot
  (bishop_beam_fire, bishop_beam bank) is first-person-only and its bank is not in m30's
  list. Next test (`--firing-loop`): the Sentinel loop as attachment 0, scaled by
  `primary_firing` -- the way the overheat sound already works on this port.
* **Boot 30 -- REACH'S FIRING SOUND PLAYS IN HALO 4.** `--firing-loop` made firing
  audible (start sound + loop; overheat still plays); with the rebuilt sentinel bank
  installed (`h4_sound_test.py --install`; the first retest was void because `--restore`
  had left its record and `--install` refused -- fixed) the port plays Reach's Focus Rifle
  audio, before and after an MCC restart. The chain holds on this port: Reach audio from
  sfx.fsb (vgmstream) -> hand-written PCM WEM -> rebuilt v88 bank -> appended to
  sfxbank.pck with its LUT entry repointed -> a weapon object attachment (lsnd) scaled by
  primary_firing. Still a TEST: it lives in the Sentinel's bank and on map pokes.
* **Zoom sounds:** the Sentinel base named the bishop beam's NONPLAYER zoom events (bank
  bishop_beam, not in m30) -- silent. Reach's Focus Rifle used the Beam Rifle's zoom
  sounds; Halo 4's Beam Rifle has its own (weapons_covenant/beam_rifle bank, in m30).
  Kit (h4_make_port_weapon.py) + poke `--zoom-sounds`.
* **Next:** the port's OWN bank (own event names, Reach in/loop/out as PCM), own
  .sound / .sound_looping / .soundbank tags in H4EK, the lsnd as a kit attachment on
  primary_firing, the bank added to sfxbank.pck as a NEW LUT entry (the header grows by
  20 bytes, so every bank start shifts) or in the DLC stub package; a restore path like
  port_glyphs (Steam verify restores sfxbank.pck).
* **The finished version (2026-10-03, needs a rebuild):**
  - `h4_sound_bank.py`: the port's OWN bank `port_focus_rifle` (0xb4d927ce) = a full copy
    of the stock sentinel bank with all 59 owned ids renamed (objects, media, bank id;
    122 references, exactly the count measured before) -- no collision with the real
    sentinel bank -- events `play_wea_port_focus_rifle_fire_in` /
    `stop_wea_port_focus_rifle_fire`, Reach's in/loop/out as PCM. Written to
    `tool/port_sounds/halo4/port_focus_rifle.bnk` (committed, 1.5 MB).
  - `tool/port_sounds.py` (sound twin of port_glyphs.py): inserts every port bank into the
    live sfxbank.pck as a NEW table entry in id order (header +20 bytes, every bank offset
    shifted), the bank appended; temp file + swap, read back. Proven on a stock copy: all
    577 original banks byte-identical at their new offsets, the port bank reads back,
    second run a no-op. `--write`, `--check`; SOUNDS section in validate_halo_json.py.
  - Kit (`h4_make_port_weapon.make_sound_tags`): own .soundbank (bank list name
    port_focus_rifle), .sound in/out (the two events), .sound_looping (tracks[0]
    in/out) under sound\weapons\focus_rifle\port; the weapon gets the loop as a NEW
    attachment scaled by primary_firing (the overheat loop keeps its own) and the bank as
    its Player Sound Bank. h4_weapon_refs add-attachment takes `path|scale|marker`.
  - The sentinel bank is STOCK again (h4_sound_test.py --restore, sha1 c63d37be checked).
  - Closing step for a sound port: commit the .bnk under tool/port_sounds/<game>/; the
    Enhancer's patch-time `port_sounds.ensure('halo4', mcc_root())` reinstalls it after a
    Steam update/verify (spec: datas += [('port_sounds', 'port_sounds')]).
* **Scope meters, in-map test pokes:** `--meters-visible`, `--meters-br-bitmap` (the Beam
  Rifle's heat_bar as a control). UI property names are in a string namespace the map
  reader does not resolve -- the poke matches by structure.

### CHECKLIST for a port that OVERHEATS (battery / heat weapons only)

The overheat pop is a **heat-weapon problem only**: it lives in a borrowed fp graph's
OVERHEAT chain (overheating -> overheated -> o_h_exit), which plays only on a weapon with
heat. Ballistic ports (the SAW in every game) never enter it. For any battery/heat port
that borrows a donor's fp graph -- above all a donor that does NOT overheat in normal
play (the Beam Rifle), whose overheat animations nobody ever saw:

1. Read each overheat-chain animation's **Loop Frame Index** in the compiled graph
   (`h4_map_poke.py` reads/pokes it: jmad Animations element +0x8). A NON-looping entry
   animation (overheating) with loop frame 0 shows its FIRST frame for one frame when it
   ends: a whole-rig pop. Set it to the last frame (h4_fp_graph.set_loop_frames).
2. Compare against a donor whose overheat chain IS used in play (the Plasma Pistol: loop
   frame 16, no pop) -- every compiled per-animation field, not just names and poses.
3. Bisect in the built map, one field per boot, before any rebuild.
4. Per-shot feedback at a heat weapon's fire rate (30/s for the Focus Rifle) multiplies:
   pick a firing damage response built for automatic fire (the Assault Rifle's here).

### Diagnostic tools of the H4 kit (promoted from scratch scripts, 2026-10-03)

    h4_weapon_diff.py      field-by-field diff of weapon tags (+ flag names): finds what
                           a donor-based port inherited -- the drift's AI aim assist,
                           the missing strict-deviation / hide-when-zoomed flags
    h4_cusc_dump.py        a HUD screen's templates, components, overlay properties and
                           bindings (mapping the scope templates)
    reach_effect_tints.py  a Reach effect's particle colours via HREK ManagedBlam (the
                           orange muzzle); export-tag-to-xml shows them only as sizes
    port_refs_audit.py     step 3 in the built map, every game (see the top of this file)
    h4_map_poke.py         every no-rebuild test of this port (--help lists them)
    h4_wwise.py            Halo 4 sound package / bank / event reader

### Foundry across kits: the traps

* **The Microsoft Store Python virtualises %APPDATA%** for itself and every child. A
  Blender launched from it reads a DIFFERENT copy of Foundry's project list -- one without
  H4EK -- so ManagedBlam silently binds HREK, parses H4 tags with Reach's definitions
  (Reach paths as 'before' values, `hud screen reference` not found) and fails with "not
  rooted under the current directory". h4_weapon_refs.py / h4_tag_numbers.py register
  H4EK in whatever list their process sees, bind through an ABSOLUTE H4EK path, and
  refuse unless ManagedBlam is H4EK's.
* **Integer fields refuse "2.0"** and silently keep their value: whole numbers go in as
  integers.

* **One kit per Blender PROCESS.** Foundry binds one kit's ManagedBlam and needs a restart
  to switch, so import runs in the source kit and export in H4EK -- two processes.
  `foundry_setup.py -- --add <kit>` registers a kit (Foundry's own operator needs a UI).
* **Background mode divides by zero** laying out material node trees (UI scale 0). The
  scripts replace `arrange` with a no-op at runtime; Foundry's files are untouched.
* **`nwo.shader_to_material` cannot help**: it copies the Reach shaders into
  `tags\_temp` and fails to load the first one (H4EK cannot read them). The copies must be
  deleted afterwards -- they were.
