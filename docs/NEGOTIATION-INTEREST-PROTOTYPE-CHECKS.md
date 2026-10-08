# Negotiation interest prototype checks

Design checkpoint, 8 October 2026. This covers the illustrative interface and
pure arithmetic in `NEGOTIATION-INTEREST-DESIGN.md`, not production CK3 behavior.

Run `node tools/design/check_interest_prototype.cjs` with the absolute path to
the task's `parley-negotiation-interests.html` fragment as its first argument.
The prototype fragment is an external test input, not bundled in this repository; supply its absolute path explicitly.

- Pure model arithmetic: PASS, 2237 assertions. Coverage includes three example
  scores, Off bypass, finite zero-willingness handling, percentage bounds,
  stronger-mode ordering, penalty reconciliation and zero usefulness without
  an opinion-derived benefit.
- Event binding with a minimal DOM stub: PASS. Covers unique element IDs,
  resolved selectors, Off and Strict switches, detail buttons, all three
  scenario results and tooltip text. This is not a browser rendering check.
- Browser visual and actual hover rendering: NOT_VERIFIED. A single headless
  Chrome attempt was stopped by the system policy disallowing remote debugging.
  No policy was changed or bypassed. The isolated browser process exited.
- Native CK3 feature behavior: NOT_RUN. No gameplay implementation or native
  harness was added in this design step.
- Production runtime: all 83 files have identical SHA-256 entries before and
  after this turn. Existing dirty authoring changes are preserved.
- Existing tracked diff whitespace check: PASS. Publication, normal CK3 profile,
  launcher settings and frozen release files were not changed.

Not covered: live native personality and budget extraction, amount-band and
cross-resource integration, Auto-balance, atomic settlement, cache invalidation,
AI execution, native tooltip/layout, multiplayer or long-campaign balance.
