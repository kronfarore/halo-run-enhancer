;=============================================================================
; ABILITY PROTOTYPE -- Halo 1 (HCEEK) -- v7  (SPRINT + POWERUPS)  [SPRINT PROTOTYPE]
;
; Append to data\global_scripts.hsc (compiled into every level). The Sprint Toolkit
; installer keeps this block in sync automatically -- see install_script.py.
;
; ONE flashlight-key ability per player, chosen by the Enhancer per run and mutually
; exclusive: 0 none, 1 sprint, 2 overshield, 3 active camo, 4 medikit. The key press
; activates it; it runs for a duration, then goes on cooldown. Per-player for co-op
; (ability0/sa0/... = player 1, ability1/sa1/... = player 2).
;
; Powerup mechanics (hs_doc.txt), FOCUS = overshield right now:
;   overshield  object_set_shield <obj> os_shield -- set the CURRENT shield once, per-player
;               (the <obj> arg attributes it to player 1 vs 2). Depletes naturally; os_ticks
;               just gates re-use. object_set_shield only touches shield, NOT health (no
;               unwanted health refill). CLEAN TEST: does this alone give the purple umbrella
;               overshield? unit_set_maximum_vitality was REJECTED (in-game 2026-07-28): its
;               args are absolute (~100), it only grows the NORMAL shield, and it force-
;               refills health. os_body is retained but UNUSED for now.
;   camo        create -> attach -> DETACH a NAMED camo pickup (camo_abilityN, a "Not
;               Automatically" equipment placement inserted at build time). The player
;               then collects the REAL equipment and gets its genuine 45s duration,
;               tunable via the eqip Powerup Time field.
;               ALL THREE STEPS ARE REQUIRED, confirmed in-game: attach alone does
;               NOTHING because an attached object is parented to the unit and never
;               runs pickup collision; detaching drops it at the player's feet as a free
;               object, which is collected normally. cheat_active_camouflage_local_player
;               is deliberately NOT used -- it grants PERMANENT camo and H1 has no
;               camo-off function (verified against hs_doc + the engine DLL), which is
;               why camo never expired. ability_stop destroys the pickup if it somehow
;               went uncollected. There is ONE PICKUP PER PLAYER (camo_ability0/1) so
;               co-op camo doesn't contend over a shared object.
;   medikit     "REGENERATION" to the user; medi_*/ability 4 stay the internal names.
;               unit_set_current_vitality <unit> <body> <shield> -- HEAL OVER TIME. Its args
;               are ABSOLUTE vitality units (vit_max ~= 100 = full), NOT the [0,1] the
;               unit_get_health/_shield GETTERS return -- so every getter value must be
;               scaled by vit_max before being passed back. (Feeding the raw [0,1] shield
;               straight in is what drained the shield to ~1/100th.) Each tick while active
;               it adds medi_rate to current body and writes the CURRENT shield back
;               unchanged. medi_ticks=1 = instant full heal; larger = regen over time.
; Sprint (ability 1) is unchanged from the working build.
;
; COOLDOWNS ARE SET LOW (1s) FOR TESTING. The Enhancer/patcher will write real values.
;
; ability0/ability1 default 0, so a built map is vanilla until the Enhancer sets an
; ability per player. Globals below are patched by name (set_global / the patcher).
;=============================================================================

; ---- tuning: durations/cooldowns in ticks (30/sec); magnitudes as [0,1]-scale reals -
(global short sprint_ticks 90)        ; 3.0s sprint
(global short sprint_cooldown 30)     ; 1.0s (low for testing)
(global short os_ticks 150)           ; 5.0s active window before cooldown starts
(global short os_cooldown 30)         ; 1.0s
(global real  os_shield 3.0)          ; object_set_shield value (current shield); "any positive -> purple"?
(global real  os_body 1.0)            ; UNUSED (was unit_set_maximum_vitality body arg; rejected)
(global short camo_ticks 150)         ; 5.0s duration -- matches the tag's Powerup Time
(global short camo_cooldown 900)      ; 30.0s, begins when the 5s window ends
; camo_ticks is the camo DURATION and tracks the camo tag's Powerup Time; camo_cooldown
; is separate and starts once that window ends, so a full cycle is duration + cooldown.
; (Re-triggering mid-camo would drop a pickup that can't be collected and just lies
; there as an empty prop -- harmless, and the cooldown keeps it from happening anyway.)
(global short medi_ticks 150)         ; 5.0s heal-over-time window (1 = instant)
(global short medi_cooldown 30)       ; 1.0s
(global real  medi_heal 75.0)         ; TOTAL heal in vitality units (75 = a 100% heal; more
                                      ; is allowed and just heals past what one full bar is
                                      ; worth). Bookkeeping only -- the script uses medi_rate.
(global real  medi_rate 0.5)          ; PER-TICK heal, = medi_heal / medi_ticks. Computed by
                                      ; the tuner in Python: dividing a real by a short GLOBAL
                                      ; in HSC misbehaved (result overshot -> clamped to full
                                      ; every tick, so medi_heal appeared to do nothing).
(global real  vit_max 75.0)           ; absolute vitality scale: what unit_get_health/_shield
                                      ; [0,1] must be multiplied by. MEASURED IN-GAME = 75, and
                                      ; it must be EXACT: too high and the per-tick write-back
                                      ; rewrites body/shield higher than they were (ratchets
                                      ; both to full regardless of rate); too low and it drains
                                      ; them. 74 drains, 76 regenerates, 75 holds steady.

; ---- per-player selected ability (0 none,1 sprint,2 overshield,3 camo,4 medikit) ----
(global short ability0 0)
(global short ability1 0)

; ---- per-player runtime state ----
(global boolean sa0 false)            ; player 1: active
(global short   sl0 0)                ;           ticks left in the active window
(global short   sc0 0)                ;           cooldown ticks left
(global boolean fp0 false)            ;           flashlight state last tick
(global boolean sa1 false)            ; player 2
(global short   sl1 0)
(global short   sc1 0)
(global boolean fp1 false)

(global boolean ability_fired false)  ; primary trigger this tick (sprint + camo end)

;-----------------------------------------------------------------------------
; Activate / deactivate -- one pair per player, dispatching on that player's ability.
; (HSC can't take a unit by variable, so player 1 and player 2 are written out.)
;-----------------------------------------------------------------------------
(global short fx_kind 5)             ; effect id; see the table in ab_fx0
(global short fx_every 10)           ; ticks between pulses (30/sec)
(global short fxp0 0)
(global short fxp1 0)
(global short fx_ladder 0)           ; 1 = step to the next effect on each use
(global short fx_min 1)
(global short fx_max 30)

; Effect-hunting aid: with fx_ladder on, every activation advances fx_kind, so a
; single build can be walked through the whole candidate list in game instead of
; one rebuild (or one tune + relaunch) per effect.
(script static void ab_ladder
	(if (> fx_ladder 0)
		(begin
			(set fx_kind (+ fx_kind 1))
			(if (> fx_kind fx_max) (set fx_kind fx_min)))))

(script static void ability_start0
	(set sa0 true)
	(if (= ability0 1)
		(begin
			(set sl0 sprint_ticks)
			(player_add_equipment (player0) sprint_profile 0)))
	(if (= ability0 2)
		(begin
			(set sl0 os_ticks)
			(object_set_shield (player0) os_shield)))            ; overshield: set current shield once
	(if (= ability0 3)
		(begin
			(set sl0 camo_ticks)
			(object_create camo_ability0)
			(objects_attach (player0) "" camo_ability0 "")
			(objects_detach (player0) camo_ability0)))
	(if (= ability0 4)
		(begin (set sl0 medi_ticks) (set fxp0 0) (ab_ladder)))                                ; medikit heals per tick (medi_tick0)
	(player_action_test_reset))         ; clear any pending fire so sprint doesn't insta-cancel

(script static void ability_stop0
	(set sa0 false)
	(if (= ability0 1) (set sc0 sprint_cooldown))
	(if (= ability0 2) (set sc0 os_cooldown))
	(if (= ability0 3) (set sc0 camo_cooldown))
	(if (= ability0 4) (set sc0 medi_cooldown))
	(if (= ability0 3) (object_destroy camo_ability0))    ; clear it if it wasn't picked up
	(if (= ability0 1) (objects_delete_by_definition "weapons\sprint\sprint")))

(script static void ability_start1
	(set sa1 true)
	(if (= ability1 1)
		(begin
			(set sl1 sprint_ticks)
			(player_add_equipment (player1) sprint_profile 0)))
	(if (= ability1 2)
		(begin
			(set sl1 os_ticks)
			(object_set_shield (player1) os_shield)))            ; overshield: set current shield once
	(if (= ability1 3)
		(begin
			(set sl1 camo_ticks)
			(object_create camo_ability1)
			(objects_attach (player1) "" camo_ability1 "")
			(objects_detach (player1) camo_ability1)))
	(if (= ability1 4)
		(begin (set sl1 medi_ticks) (set fxp1 0)))                                ; medikit heals per tick (medi_tick1)
	(player_action_test_reset))

(script static void ability_stop1
	(set sa1 false)
	(if (= ability1 1) (set sc1 sprint_cooldown))
	(if (= ability1 2) (set sc1 os_cooldown))
	(if (= ability1 3) (set sc1 camo_cooldown))
	(if (= ability1 4) (set sc1 medi_cooldown))
	(if (= ability1 3) (object_destroy camo_ability1))    ; clear it if it wasn't picked up
	(if (= ability1 1) (objects_delete_by_definition "weapons\sprint\sprint")))

;-----------------------------------------------------------------------------
; Medikit heal tick -- one slice of the heal, shield written back untouched.
; Everything is in ABSOLUTE vitality units, so the [0,1] getters are scaled by
; vit_max on the way in. Body is clamped to vit_max so we never exceed the max.
;-----------------------------------------------------------------------------
(script static void medi_tick0
	(unit_set_current_vitality (player0)
		(min vit_max (+ (* (unit_get_health (player0)) vit_max)
						medi_rate))
		(* (unit_get_shield (player0)) vit_max)))

(script static void medi_tick1
	(unit_set_current_vitality (player1)
		(min vit_max (+ (* (unit_get_health (player1)) vit_max)
						medi_rate))
		(* (unit_get_shield (player1)) vit_max)))

;-----------------------------------------------------------------------------
; Regeneration feedback pulse. H2 needed this because it has no health bar at
; all; H1 has one, but a visible effect still reads better than a slowly moving
; bar -- and it is what makes the ability legible in co-op, where you cannot see
; your partner's health.
;
; Only SELF-CONTAINED effects work on a player. Anything material-driven
; (collision/impact/slip) resolves its particles against the surface it hit and
; silently draws nothing; weapon effects likewise want their own markers. That
; was measured in H2, where every impact\ and weapon effect failed and the
; gameplay teleports and character effects worked -- so these candidates are all
; teleports or character effects.
;-----------------------------------------------------------------------------

(script static void ab_fx0
	(if (= fx_kind 1) (effect_new_on_object_marker
		"effects\coop teleport" (player0) ""))
	(if (= fx_kind 2) (effect_new_on_object_marker
		"cinematics\effects\teleportation\teleportation" (player0) ""))
	(if (= fx_kind 3) (effect_new_on_object_marker
		"cinematics\effects\teleportation\teleportation short" (player0) ""))
	(if (= fx_kind 4) (effect_new_on_object_marker
		"cinematics\effects\teleportation\teleport light" (player0) ""))
	(if (= fx_kind 5) (effect_new_on_object_marker
		"characters\cyborg\cyborg shield depletion" (player0) ""))
	(if (= fx_kind 6) (effect_new_on_object_marker
		"characters\monitor\monitor glow rings" (player0) ""))
	(if (= fx_kind 7) (effect_new_on_object_marker
		"characters\elite\effects\elite shield depletion" (player0) ""))
	(if (= fx_kind 8) (effect_new_on_object_marker
		"characters\sentinel\effects\sentinel shield depletion" (player0) ""))
	(if (= fx_kind 9) (effect_new_on_object_marker
		"levels\a50\devices\grav_lift_particles\grav_lift_particles" (player0) ""))
	(if (= fx_kind 10) (effect_new_on_object_marker
		"effects\small explosion" (player0) ""))
	(if (= fx_kind 11) (effect_new_on_object_marker
		"levels\a10\devices\shield charge\effects\shield charge ring" (player0) ""))
	(if (= fx_kind 12) (effect_new_on_object_marker
		"effects\bursts\space beam" (player0) ""))
	(if (= fx_kind 13) (effect_new_on_object_marker
		"effects\bursts\space beam large" (player0) ""))
	(if (= fx_kind 14) (effect_new_on_object_marker
		"effects\burning large" (player0) ""))
	(if (= fx_kind 15) (effect_new_on_object_marker
		"effects\explosions\steam explosion no objects" (player0) ""))
	(if (= fx_kind 16) (effect_new_on_object_marker
		"effects\explosions\medium explosion no objects" (player0) ""))
	(if (= fx_kind 17) (effect_new_on_object_marker
		"effects\retro rockets" (player0) ""))
	(if (= fx_kind 18) (effect_new_on_object_marker
		"characters\sentinel\effects\burning" (player0) ""))
	(if (= fx_kind 19) (effect_new_on_object_marker
		"cinematics\effects\lights\covenant blast bolt\effects\explosion" (player0) ""))
	(if (= fx_kind 20) (effect_new_on_object_marker
		"characters\flood_infection\body depleted" (player0) ""))
	(if (= fx_kind 21) (effect_new_on_object_marker
		"levels\c20\devices\index platform\effects\lightning ring" (player0) ""))
	(if (= fx_kind 22) (effect_new_on_object_marker
		"levels\c20\devices\index platform\effects\lightning" (player0) ""))
	(if (= fx_kind 23) (effect_new_on_object_marker
		"levels\c20\devices\index platform\effects\light trail" (player0) ""))
	(if (= fx_kind 24) (effect_new_on_object_marker
		"levels\c10\scenery\mri lightning\mri light flash" (player0) ""))
	(if (= fx_kind 25) (effect_new_on_object_marker
		"levels\a30\devices\beam emitter\effects\beam" (player0) ""))
	(if (= fx_kind 26) (effect_new_on_object_marker
		"scenery\emitters\sparks\effects\sparks" (player0) ""))
	(if (= fx_kind 27) (effect_new_on_object_marker
		"scenery\emitters\sparks spurt\effects\sparks spurt" (player0) ""))
	(if (= fx_kind 28) (effect_new_on_object_marker
		"levels\a50\devices\interior tech objects\holo control\holo control scrambled" (player0) ""))
	(if (= fx_kind 29) (effect_new_on_object_marker
		"scenery\c_field_generator\effects\shield depletion" (player0) ""))
	(if (= fx_kind 30) (effect_new_on_object_marker
		"characters\jackal\effects\shield depletion" (player0) "")))

(script static void ab_fx1
	(if (= fx_kind 1) (effect_new_on_object_marker
		"effects\coop teleport" (player1) ""))
	(if (= fx_kind 2) (effect_new_on_object_marker
		"cinematics\effects\teleportation\teleportation" (player1) ""))
	(if (= fx_kind 3) (effect_new_on_object_marker
		"cinematics\effects\teleportation\teleportation short" (player1) ""))
	(if (= fx_kind 4) (effect_new_on_object_marker
		"cinematics\effects\teleportation\teleport light" (player1) ""))
	(if (= fx_kind 5) (effect_new_on_object_marker
		"characters\cyborg\cyborg shield depletion" (player1) ""))
	(if (= fx_kind 6) (effect_new_on_object_marker
		"characters\monitor\monitor glow rings" (player1) ""))
	(if (= fx_kind 7) (effect_new_on_object_marker
		"characters\elite\effects\elite shield depletion" (player1) ""))
	(if (= fx_kind 8) (effect_new_on_object_marker
		"characters\sentinel\effects\sentinel shield depletion" (player1) ""))
	(if (= fx_kind 9) (effect_new_on_object_marker
		"levels\a50\devices\grav_lift_particles\grav_lift_particles" (player1) ""))
	(if (= fx_kind 10) (effect_new_on_object_marker
		"effects\small explosion" (player1) ""))
	(if (= fx_kind 11) (effect_new_on_object_marker
		"levels\a10\devices\shield charge\effects\shield charge ring" (player1) ""))
	(if (= fx_kind 12) (effect_new_on_object_marker
		"effects\bursts\space beam" (player1) ""))
	(if (= fx_kind 13) (effect_new_on_object_marker
		"effects\bursts\space beam large" (player1) ""))
	(if (= fx_kind 14) (effect_new_on_object_marker
		"effects\burning large" (player1) ""))
	(if (= fx_kind 15) (effect_new_on_object_marker
		"effects\explosions\steam explosion no objects" (player1) ""))
	(if (= fx_kind 16) (effect_new_on_object_marker
		"effects\explosions\medium explosion no objects" (player1) ""))
	(if (= fx_kind 17) (effect_new_on_object_marker
		"effects\retro rockets" (player1) ""))
	(if (= fx_kind 18) (effect_new_on_object_marker
		"characters\sentinel\effects\burning" (player1) ""))
	(if (= fx_kind 19) (effect_new_on_object_marker
		"cinematics\effects\lights\covenant blast bolt\effects\explosion" (player1) ""))
	(if (= fx_kind 20) (effect_new_on_object_marker
		"characters\flood_infection\body depleted" (player1) ""))
	(if (= fx_kind 21) (effect_new_on_object_marker
		"levels\c20\devices\index platform\effects\lightning ring" (player1) ""))
	(if (= fx_kind 22) (effect_new_on_object_marker
		"levels\c20\devices\index platform\effects\lightning" (player1) ""))
	(if (= fx_kind 23) (effect_new_on_object_marker
		"levels\c20\devices\index platform\effects\light trail" (player1) ""))
	(if (= fx_kind 24) (effect_new_on_object_marker
		"levels\c10\scenery\mri lightning\mri light flash" (player1) ""))
	(if (= fx_kind 25) (effect_new_on_object_marker
		"levels\a30\devices\beam emitter\effects\beam" (player1) ""))
	(if (= fx_kind 26) (effect_new_on_object_marker
		"scenery\emitters\sparks\effects\sparks" (player1) ""))
	(if (= fx_kind 27) (effect_new_on_object_marker
		"scenery\emitters\sparks spurt\effects\sparks spurt" (player1) ""))
	(if (= fx_kind 28) (effect_new_on_object_marker
		"levels\a50\devices\interior tech objects\holo control\holo control scrambled" (player1) ""))
	(if (= fx_kind 29) (effect_new_on_object_marker
		"scenery\c_field_generator\effects\shield depletion" (player1) ""))
	(if (= fx_kind 30) (effect_new_on_object_marker
		"characters\jackal\effects\shield depletion" (player1) "")))

(script static void medi_pulse0
	(set fxp0 (- fxp0 1))
	(if (< fxp0 1)
		(begin
			(set fxp0 fx_every)
			(ab_fx0))))

(script static void medi_pulse1
	(set fxp1 (- fxp1 1))
	(if (< fxp1 1)
		(begin
			(set fxp1 fx_every)
			(ab_fx1))))

;-----------------------------------------------------------------------------
; "Ability ready" cue. Fires once, on the tick the cooldown reaches zero -- the
; moment the player most needs to know about and the one thing a cooldown number
; would otherwise be needed for.
;
; It reuses the ab_fx dispatcher by swapping fx_kind around the call instead of
; repeating the whole effect table: the table is already 20 entries x 2 players,
; and H1's script node pool is finite.
;-----------------------------------------------------------------------------
(global short fx_ready 30)            ; effect id for the ready cue; 0 = off
(global short fx_ready_n 3)           ; how many flashes the cue fires
(global short fx_ready_gap 5)         ; ticks between them
(global short rdy0 0)                 ; flashes still owed, per player
(global short rdyt0 0)                ; ticks until the next one
(global short rdy1 0)
(global short rdyt1 0)
(global short fx_swap 0)

(script static void ab_ready0
	(if (> fx_ready 0)
		(begin
			(set fx_swap fx_kind)
			(set fx_kind fx_ready)
			(ab_fx0)
			(set fx_kind fx_swap))))

(script static void ab_ready1
	(if (> fx_ready 0)
		(begin
			(set fx_swap fx_kind)
			(set fx_kind fx_ready)
			(ab_fx1)
			(set fx_kind fx_swap))))

;-----------------------------------------------------------------------------
; Per-tick control.
;-----------------------------------------------------------------------------
(script continuous ability_control
	; A trigger pull cancels sprint and ends camo. player_action_test_primary_trigger
	; is an ANY-player test (no unit arg), read once per tick only while an ability is up.
	(set ability_fired false)
	(if (or sa0 sa1)
		(begin
			(set ability_fired (player_action_test_primary_trigger))
			(player_action_test_reset)))

	; ---- player 1 ----
	(if (> sc0 0)
		(begin
			(set sc0 (- sc0 1))
			(if (= sc0 0) (begin (set rdy0 fx_ready_n) (set rdyt0 0)))))
	(if (> rdy0 0)
		(begin
			(set rdyt0 (- rdyt0 1))
			(if (< rdyt0 1)
				(begin
					(set rdy0 (- rdy0 1))
					(set rdyt0 fx_ready_gap)
					(ab_ready0)))))
	(if sa0
		(begin
			(set sl0 (- sl0 1))
			; Overshield is set once at activation; camo runs its natural duration;
			; the medikit heals a slice every tick of its window.
			(if (= ability0 4) (begin (medi_tick0) (medi_pulse0)))
			(if (or (<= sl0 0)
					(and (= ability0 1)
						 (or ability_fired
							 (not (unit_has_weapon_readied (player0) "weapons\sprint\sprint"))
							 (not (= (unit_get_current_flashlight_state (player0)) fp0)))))
				(ability_stop0)))
		(if (and (> ability0 0)
				 (not (= (unit_get_current_flashlight_state (player0)) fp0))
				 (= sc0 0))
			(ability_start0)))
	(set fp0 (unit_get_current_flashlight_state (player0)))

	; ---- player 2 (only if present) ----
	(if (> (player_count) 1)
		(begin
			(if (> sc1 0)
				(begin
					(set sc1 (- sc1 1))
					(if (= sc1 0) (begin (set rdy1 fx_ready_n) (set rdyt1 0)))))
			(if (> rdy1 0)
				(begin
					(set rdyt1 (- rdyt1 1))
					(if (< rdyt1 1)
						(begin
							(set rdy1 (- rdy1 1))
							(set rdyt1 fx_ready_gap)
							(ab_ready1)))))
			(if sa1
				(begin
					(set sl1 (- sl1 1))
					(if (= ability1 4) (begin (medi_tick1) (medi_pulse1)))
					(if (or (<= sl1 0)
							(and (= ability1 1)
								 (or ability_fired
									 (not (unit_has_weapon_readied (player1) "weapons\sprint\sprint"))
									 (not (= (unit_get_current_flashlight_state (player1)) fp1)))))
						(ability_stop1)))
				(if (and (> ability1 0)
						 (not (= (unit_get_current_flashlight_state (player1)) fp1))
						 (= sc1 0))
					(ability_start1)))
			(set fp1 (unit_get_current_flashlight_state (player1)))))

	(sleep 1))
