;=============================================================================
; SPRINT PROTOTYPE -- Halo 1 (HCEEK)  -- v4  (CO-OP TEST)
;
; Append to data\global_scripts.hsc (compiled into every level).
;
; PURPOSE: find out whether player 2 can sprint independently in H1 co-op.
; The speed mechanism is inherently per-player (global run speed applies to
; everyone; each player's penalty comes from the weapon THEY hold). The open
; question is input attribution: does unit_get_current_flashlight_state (player1)
; read player 2's flashlight on its own? It takes a unit arg, so it should --
; this build is what confirms it.
;
; Symmetric per-player state (0 = player 1, 1 = player 2). player1 is only
; touched when (player_count) > 1, so this is safe in solo. player0/player1/
; player_count come from the stock global_scripts.hsc above.
;
; KNOWN TEST CAVEATS (fine for answering the attribution question):
;  * One sprint weapon definition is shared, and stop deletes it by definition,
;    so if BOTH players sprint at once, either one ending ends both. TEST BY
;    TAKING TURNS first; simultaneous sprint is a later problem (the mod solved
;    it with per-player weapon objects).
;  * Shoot-to-cancel is dropped here: player_action_test_primary_trigger is an
;    ANY-player test with no unit arg, so it would confound per-player results.
;    Cancel is timeout / flashlight re-press / manual weapon switch -- all
;    per-unit clean.
;=============================================================================

(global short sprint_ticks 90)        ; 3.0s max sprint (30 ticks/sec)
(global short sprint_cooldown 60)     ; 2.0s cooldown

(global boolean sa0 false)            ; player 1: active
(global short   sl0 0)                ;           ticks left
(global short   sc0 0)                ;           cooldown left
(global boolean fp0 false)            ;           flashlight state last tick

(global boolean sa1 false)            ; player 2
(global short   sl1 0)
(global short   sc1 0)
(global boolean fp1 false)

(global boolean sprint_fired false)   ; primary trigger pressed this tick

; Master gate. The map always ships this script, but sprint only works when the
; Enhancer flips this true per run -- true for "Start with Sprint", or once the
; Sprint equipment card is drafted. Default false = a built map behaves vanilla
; until the Enhancer enables it. Patched by name via set_short_global (the boolean
; stores as int16 at the same syntax-node offset as the short globals).
(global boolean sprint_enabled false)

(script static void sprint_start0
	(set sa0 true)
	(set sl0 sprint_ticks)
	(player_add_equipment (player0) sprint_profile 0)
	(player_action_test_reset))        ; clear any pending fire so we don't insta-cancel

(script static void sprint_stop0
	(set sa0 false)
	(set sc0 sprint_cooldown)
	(objects_delete_by_definition "weapons\sprint\sprint"))

(script static void sprint_start1
	(set sa1 true)
	(set sl1 sprint_ticks)
	(player_add_equipment (player1) sprint_profile 0)
	(player_action_test_reset))

(script static void sprint_stop1
	(set sa1 false)
	(set sc1 sprint_cooldown)
	(objects_delete_by_definition "weapons\sprint\sprint"))

(script continuous sprint_control
	; A trigger pull cancels sprint. player_action_test_primary_trigger is an
	; ANY-player test (no unit arg), so in co-op a shot by EITHER player cancels
	; active sprints -- read once per tick and reset, only while a sprint is up so
	; we don't disturb level scripts that poll the same test.
	(set sprint_fired false)
	(if (or sa0 sa1)
		(begin
			(set sprint_fired (player_action_test_primary_trigger))
			(player_action_test_reset)))

	; ---- player 1 ----
	(if (> sc0 0)
		(set sc0 (- sc0 1)))
	(if sa0
		(begin
			(set sl0 (- sl0 1))
			(if (or (<= sl0 0)
					sprint_fired
					(not (unit_has_weapon_readied (player0) "weapons\sprint\sprint"))
					(not (= (unit_get_current_flashlight_state (player0)) fp0)))
				(sprint_stop0)))
		(if (and sprint_enabled
				 (not (= (unit_get_current_flashlight_state (player0)) fp0))
				 (= sc0 0))
			(sprint_start0)))
	(set fp0 (unit_get_current_flashlight_state (player0)))

	; ---- player 2 (only if present) ----
	(if (> (player_count) 1)
		(begin
			(if (> sc1 0)
				(set sc1 (- sc1 1)))
			(if sa1
				(begin
					(set sl1 (- sl1 1))
					(if (or (<= sl1 0)
							sprint_fired
							(not (unit_has_weapon_readied (player1) "weapons\sprint\sprint"))
							(not (= (unit_get_current_flashlight_state (player1)) fp1)))
						(sprint_stop1)))
				(if (and sprint_enabled
						 (not (= (unit_get_current_flashlight_state (player1)) fp1))
						 (= sc1 0))
					(sprint_start1)))
			(set fp1 (unit_get_current_flashlight_state (player1)))))

	(sleep 1))
