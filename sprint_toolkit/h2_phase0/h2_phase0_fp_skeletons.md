# H2 phase 0, deliverable 0.4 -- first-person skeletons (H2 vs H3 / Reach / H4)

Measured 2026-10-20, read-only. Units: JMS units (100 per world unit). No tag under any kit's
`tags\` was written; no build-cache-file; nothing committed.

## Bottom line

| source | onto H2 masterchief (37 arm nodes) | onto H2 dervish (31 arm nodes) |
|---|---|---|
| **Halo 3** | **IDENTICAL skeleton** (37/37 names, same parents, same graph order, max position delta 0.0002). Copy node-for-node. | **IDENTICAL skeleton**: H3 `dervish\fp\fp` and `elite\fp_arms\fp_arms` = H2 dervish (31/31, delta 0.0000). H3 ships a dervish FP graph for 24 of 25 FP weapons (all but fp_smg_silenced). Copy node-for-node. |
| **Reach** | Same 37 arm nodes, same parent-relative bind (bone lengths 0.0%), PLUS 10 extra nodes (pedestal, aim_pitch, aim_yaw, l/r_humerus, l/r_radius, l/r_handguard; camera_control is under base). Model frame rotated 90 deg about z via pedestal/base binds. Right-hand fingers differ by 0.08-0.30 units (left hand exact). Copy by name below `base`; drop helpers; convert `base`'s root transform. | Reach `elite\fp\fp` = H2 dervish + the same 10 helpers, residual 0.0000 after the root rotation. Reach ships elite FP graphs for every Reach FP weapon. Copy by name, same as left. |
| **Halo 4** | Different rig: 80 nodes, `b_` prefix, fingers numbered 0-3, 43 helper/fixup bones, bent rest pose, bone-axis convention differs. All 37 H2 names map (b_x -> x, finger 1/2/3 -> low/mid/tip; pinky0 extra) but lengths differ: shoulders -25.0%, upper arm -10.7%, forearm +7.1%. Re-solve (IK on hand targets) -- no copy. | Halo 4 has NO elite FP arms or graphs (storm_fp only). Dervish must get an IK re-solve onto 4-digit hands, or keep a donor's H2 dervish graph retimed (the SAW's route). |

## 1. Halo 2 FP arms (H2EK, original Bungie JMS)

Render models: `objects\characters\masterchief\fp\fp.render_model` -> `fp_arms.jms` (JMS 8210),
`objects\characters\dervish\fp\fp.render_model` -> `dervish_fp_arms.jms` (**JMS 8209**, not 8210;
h2_jms.read refuses it unless VERSION is overridden -- the layout up to triangles is the same).

JMS node names carry `b_` (b_base, b_l_upperarm, ...); the animation graphs drop it (base, l_upperarm).
Weapon JMS nodes carry `frame ` (frame gun); graphs drop it (gun). Translations are ABSOLUTE (confirmed:
b_l_forearm sits at y=9.399 = its parent's y).

### masterchief: 37 nodes, 4980 verts
b_base; per side: upperarm > forearm > hand > {index, middle, ring, pinky, thumb} x {low, mid, tip} = 18 per side.

| node | absolute rest pos (x y z) |
|---|---|
| base | 0 0 0 |
| l_upperarm / r_upperarm | 0 +-9.399 0 |
| l_forearm / r_forearm | 10.251 / 10.258, +-9.399, 0 |
| l_hand / r_hand | 21.144 / 21.145, +-9.399, 0 |
| l_index_low | 24.610 9.834 1.515 |
| l_middle_low | 24.784 10.121 0.326 |
| l_ring_low | 24.821 10.040 -0.889 |
| l_pinky_low | 24.389 9.792 -1.817 |
| l_thumb_low | 21.998 8.995 1.468 |
(right side mirrored in y; full table: scratch `h2_dump.txt`)

Shoulder spread 18.798; upper arm L 10.251 / R 10.258; forearm L 10.894 / R 10.886.
Rest pose: arms straight along +x (T-pose forward), identity rotations on the chain.
Markers: `right_hand` on b_r_hand local (2.275 1.152 0.040); `left hand` on b_l_hand (2.275 -0.856 0.040); flashlight on base.
**These are exactly Halo 1's numbers** (memory h1-parallel-ports: H1 shoulders +-9.40, upper 10.25, forearm 10.89).

### dervish: 31 nodes, 5508 verts
Same chain, NO middle finger: per side upperarm > forearm > hand > {thumb, index, ring, pinky} x {low, mid, tip} = 15 per side.
Node order in the JMS is RIGHT side first (the graph re-sorts it to the same order as the Chief's).

| | value |
|---|---|
| shoulders | 0 +-9.399 0 (same as Chief) |
| forearm | 10.251 (both sides) |
| hand | 21.144 (both sides) |
| upper arm / forearm length | 10.251 / 10.893 (Chief R 10.258 / 10.886: 0.1% apart) |
| finger chain | index_low 25.644 +-10.482 0.862, ring_low 25.646 +-10.482 -0.826, pinky_low 22.499 +-9.322 -0.856 (a second thumb, below), thumb_low 22.510 +-9.340 0.918 |

So the Elite ARM chain is the Chief's; only the hands differ (4 digits, longer: index 4.7+2.5+2.3).
Up to 2.9 units of finger-node difference vs the Chief under the SAME names (index/ring/pinky/thumb mean
different digits) -- finger animation is NOT transferable between species.
Marker: `left hand elite` on b_l_hand (3.309 -0.931 0.044).

### H2 FP animation graphs (tool export-tag-to-xml)
| graph | nodes | arms | weapon | other |
|---|---|---|---|---|
| masterchief fp_smg | 42 | 37 (0-36) | gun<r_hand, charging_handle, magazine, stock (37-40) | camera_control<base (41) |
| dervish fp_smg | 36 | 31 (0-30) | gun<r_hand, charging_handle, magazine, stock (31-34) | camera_control (35) |
| masterchief fp_battle_rifle | 42 | 37 | gun, magazine, ophandle, safety | camera_control |
| dervish fp_battle_rifle | 36 | 31 | gun, magazine, ophandle, safety | camera_control |

Flags: base = local root + primary model; arms = primary model (left side "left arm member");
l_hand "left hand", r_hand "right hand"; **gun = local root + secondary model, parent r_hand**.
So the weapon attaches through the GRAPH: its root node `gun` is a child of `r_hand` and is
animated per frame (the arms' `right_hand` marker is not what places it in first person).

### H2 FP weapon render models (JMS 8210, absolute)
| model | nodes |
|---|---|
| fp_smg | frame gun (-0.073 0 0.780), frame stock, frame charging_handle, frame magazine |
| fp_battle_rifle | frame gun (0 0 0), frame magazine (-5.248 0 0.812), frame OpHandle (1.582 0.425 5.220), frame safety (1.089 0.808 3.406) |
| fp_gpmg (cut donor) | frame gun, frame magazine, frame bullet<magazine, frame OpHandle; markers right_hand / right_hand_elite / left_hand / left_hand_elite |

## 2. Halo 3 FP arms

| render model | nodes | vs H2 |
|---|---|---|
| masterchief\fp\fp | 37 | = H2 masterchief: 37/37 names, same parents, max delta 0.0002, lengths +0.0% |
| dervish\fp\fp | 31 | = H2 dervish: 31/31, delta 0.0000 |
| elite\fp_arms\fp_arms | 31 | = H2 dervish: 31/31, delta 0.0000 |

H3 markers add fx_left/right_hand, fx_left/right_forearm; `right_hand` / `left_hand` are the H2 values.
H3 graphs: masterchief fp_assault_rifle 43 nodes (37 arms + gun, magazine, ophandle, safety, switch + camera_control),
fp_battle_rifle 42 and fp_smg 42 -- **node-for-node identical to H2's graphs** (same order, same weapon
node names for the BR and SMG). dervish fp_assault_rifle 37, fp_battle_rifle 36 (= H2 dervish BR),
fp_brute_shot 43 (31 arms + gun<r_hand, body, ammo01-04, ammo_feeder, barrel, slide, ammo_cap, handle).
H3 dervish FP graphs exist for every masterchief one except fp_smg_silenced.

## 3. Reach and Halo 4 (brief)

**Reach** `spartans\fp\fp` 47 nodes: pedestal (root), base<pedestal, aim_pitch, aim_yaw, camera_control<base,
37 H2 nodes, + l/r_humerus (upperarm, at mid-bone), l/r_radius (forearm, mid-bone), l/r_handguard (hand).
Parent-relative locals of the arm chain are identical to H3 (l_upperarm (0, 9.399, 0), r_forearm (10.2583, 0, 0) ...);
the pedestal (0.5,0.5,0.5,0.5) and base (-0.707,0,0,0.707) binds put the model frame 90 deg about z from H2's
(rigid alignment R = [[0,1,0],[-1,0,0],[0,0,1]], residual 0 on the chain). Right-hand fingers 0.08-0.30 off H2 (re-posed), left exact.
**Reach** `elite\fp\fp` 41 nodes = H2 dervish 31 + the same 10, residual 0.0000.
Reach FP graphs: spartans fp_dmr 51 (47 + b_gun<r_hand, b_magazine, b_ophandle, b_safety), elite fp_dmr 45.
Weapon nodes are `b_`-prefixed (b_gun) -> rename to gun / frame gun. Reach has elite FP graphs for all its FP weapons.

**Halo 4** `storm_fp` 80 nodes (graph storm_fp_br 84 = 80 + b_gun<b_r_hand, b_magazine, b_safety, b_ophandle).
Shoulders +-7.047 (spread 14.093), base offset -0.941 x from pedestal, upper arm 9.153, forearm 11.666, rest pose bent
(hands at x 5.0, z -11.2), local bone axis along y (marker fx_left_forearm at (0, -11.666, 0)). Helpers: shoulder_helper1-4,
upperarm_fixup, shoulder_fixup, elbow_fixup, elbow_armor, forearm_helper1-4, forearm_fixup, hand_twist, wrist_fixup,
hand_helper1-4 (right), grip, hand_marker_offset, pinky0. No elite FP model or graphs in H4EK.

## 4. Weapon side
| | root | children |
|---|---|---|
| H2 FP (JMS) | `frame gun` | `frame magazine`, `frame OpHandle`, `frame safety`, `frame stock`, `frame charging_handle`, `frame bullet` |
| H2 graph | `gun` <r_hand | magazine, ophandle, safety, stock, charging_handle |
| H3 fp_assault_rifle | `gun` | magazine (-4.801 0 1.435), ophandle, safety, switch |
| H3 fp_battle_rifle | `gun` | magazine (-7.620 0.002 1.324), ophandle (0.362 0.387 5.561), safety (2.395 0.444 3.662) |
| Reach dmr (one model, no fp_ copy) | `b_gun` | b_magazine, b_safety, b_ophandle |
| H4 storm_br | `b_gun` | b_safety, b_magazine, b_ophandle (same rest values as Reach's DMR) |

Naming maps 1:1 (H3 `gun` -> H2 JMS `frame gun`; `b_` stripped for Reach/H4). Rest positions differ between
games' models of "the same" weapon (H2 BR magazine -5.25 vs H3 -7.62), which is irrelevant when model AND
animations come from the same source. Note H2 graphs are per-weapon node sets: a port graph must list the
source's weapon nodes (e.g. H3 AR adds `switch`).

## 5. Conclusions per source game
* **Halo 3 -> H2 masterchief: copy node-for-node.** All 37 arm nodes + camera_control map by name, order and
  rest pose (bone-length difference 0.0%). Weapon nodes carry over by name. H3 is effectively the H2 rig.
* **Halo 3 -> H2 dervish: copy node-for-node** from H3's own `dervish\fp\weapons\...` graph (31/31, 0.0%).
  This removes the SAW route's limitation for H3 sources: each species gets its own source animation.
* **Reach -> both: copy by name** for the 37 / 31 shared nodes (0.0% bone lengths); drop pedestal, aim_pitch,
  aim_yaw, humerus, radius, handguard (twist/cosmetic helpers -- the armour they skin is not in H2's mesh);
  re-express `base` out of the pedestal frame (camera_control is a child of base in both, so it follows) (the constant 90 deg z rotation). Not a re-solve. Right-hand fingers' tiny rest offsets
  (<=0.30) mean finger TRANSLATIONS should come from the H2 bind, rotations from Reach.
* **Halo 4 -> masterchief: IK re-solve required** (names map, lengths do not: -25% / -10.7% / +7.1%, posed rest,
  different bone axes) -- same conclusion as the H1 Storm Rifle check.
* **Halo 4 -> dervish: no source exists**; IK re-solve onto the Elite hand, or the SAW route (a donor H2 dervish
  graph retimed with h2_anim_retime.py).

Not measured / open: (a) whether H3/Reach animation STREAMS use H2's quaternion sign convention (H2 JMS and
H3 tag binds both store w = -1 rotations; the codec mapping onto H2 codec 3 is phase 1 work); (b) how H2's
`tool` imports source animations (JMA/JMM import path untested here) -- the toolkit today edits graphs in place
(h2_anim.py codec 3); (c) whether a graph with extra weapon nodes (`switch`) needs the FP weapon model to carry
the same nodes (it should, as in H2's own graphs).

## Commands run
```
cd F:\SteamLibrary\steamapps\common\H2EK
tool.exe extract-render-data objects\characters\masterchief\fp\fp        -> data\!extracted\fp\render\fp_arms.jms (moved to scratch)
tool.exe extract-render-data objects\characters\dervish\fp\fp            -> data\!extracted\fp\render\dervish_fp_arms.jms (moved to scratch)
tool.exe extract-render-data objects\weapons\rifle\battle_rifle\fp_battle_rifle\fp_battle_rifle   (left in data\!extracted\fp_battle_rifle)
(fp_smg / fp_gpmg JMS were already in data\!extracted; copied)
tool.exe export-tag-to-xml <ABS ...\masterchief|dervish\fp\weapons\rifle\fp_smg|fp_battle_rifle\*.model_animation_graph> C:\Users\kron1\AppData\Local\Temp\h2fp_*.xml
  (trap: a long output path -- the scratchpad -- produced EMPTY files; a short %TEMP% path works)
H3/Reach/H4 exports via sprint_toolkit h1_fp_retarget.export_xml (caches in sprint_toolkit\out\h3_export, reach_export, h4_export; gitignored)
```
Scratch dir: `C:\Users\kron1\AppData\Local\Temp\claude\C--Program-Files--x86--Steam-steamapps-common-Halo-The-Master-Chief-Collection-tool\41a4cbce-2979-4afe-a789-be857f4ebf1c\scratchpad\fp0\`
* `dump_h2.py <jms...>` -- H2 JMS 8209/8210 node/marker dump (h2_dump.txt)
* `export_jmad.py <rel graph...>` -- H2 graph skeleton nodes + flags
* `skel.py <rel...>` -- H3/Reach/H4 render-model skeletons in model space vs H2 (h3_mc.txt, others.txt)
* `align.py` -- rigid alignment + name map (H4) + bone-length % (align.txt)
* `graphs.py graph|rm <rel...>` -- graph skeleton lists / weapon render-model nodes (graphs_h3.txt, graphs_reach_h4.txt, weapons_rm.txt)
* `peek.py` -- raw parent-relative binds
* JMS copies: h2_mc_fp_arms.jms, h2_dervish_fp_arms.jms, h2_fp_smg.jms, h2_fp_br.jms, h2_fp_gpmg.jms
