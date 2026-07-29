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
;   camo        cheat_active_camouflage_local_player -- granted ONCE; ends on its own
;               natural duration (firing does NOT break it), then cooldown.
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
(global short camo_ticks 150)         ; 5.0s cap (also ends when you fire)
(global short camo_cooldown 30)       ; 1.0s
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
			(cheat_active_camouflage_local_player 0)))           ; granted once; ends on fire
	(if (= ability0 4)
		(set sl0 medi_ticks))                                ; medikit heals per tick (medi_tick0)
	(player_action_test_reset))         ; clear any pending fire so sprint doesn't insta-cancel

(script static void ability_stop0
	(set sa0 false)
	(if (= ability0 1) (set sc0 sprint_cooldown))
	(if (= ability0 2) (set sc0 os_cooldown))
	(if (= ability0 3) (set sc0 camo_cooldown))
	(if (= ability0 4) (set sc0 medi_cooldown))
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
			(cheat_active_camouflage_local_player 1)))
	(if (= ability1 4)
		(set sl1 medi_ticks))                                ; medikit heals per tick (medi_tick1)
	(player_action_test_reset))

(script static void ability_stop1
	(set sa1 false)
	(if (= ability1 1) (set sc1 sprint_cooldown))
	(if (= ability1 2) (set sc1 os_cooldown))
	(if (= ability1 3) (set sc1 camo_cooldown))
	(if (= ability1 4) (set sc1 medi_cooldown))
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
		(set sc0 (- sc0 1)))
	(if sa0
		(begin
			(set sl0 (- sl0 1))
			; Overshield is set once at activation; camo runs its natural duration;
			; the medikit heals a slice every tick of its window.
			(if (= ability0 4) (medi_tick0))
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
				(set sc1 (- sc1 1)))
			(if sa1
				(begin
					(set sl1 (- sl1 1))
					(if (= ability1 4) (medi_tick1))
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
