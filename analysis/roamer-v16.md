# V16-candidate role-assignment scope

`main.SoccerSimAgent.play` calls `field_logic.run` for active non-keepers;
normal play dispatches `_act_normal`. Its selector previously applied the
0.3 m `field_params` margin. The separate `tactics.select_roles` 0.65 m margin
does not control final normal roamer actions: its result is overwritten by
`run_fields`. V16 supplies a 1.0 m margin only to `_act_normal`'s selector.
Kickoff selection retains its existing default and locking behavior.

Unit coverage exercises initial choice/actions, exact boundary retention,
clear-margin switches, unavailable incumbent, empty roster, missing ball,
phase reset and unchanged kickoff default. Match-switch frequency cannot be
derived from result/event logs, which contain no per-tick attacker assignments.
Historical raw V14 telemetry is not present on this machine; no switches per
match are claimed. See `../match-results/roamers-v16/REPORT.md` for blockers.
