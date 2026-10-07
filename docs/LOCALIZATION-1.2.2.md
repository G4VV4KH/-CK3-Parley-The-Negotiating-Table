# Parley 1.2.2 localization candidate

Prepared 2026-10-07 for CK3 1.20.0.4 from published Parley 1.2.1.

The runtime change is limited to 13 translated values: German (1), Japanese (7), Polish (1) and Spanish (4), plus the descriptor version. The source contains 662 localization keys per language; GAME retains 652, excluding the same ten developer-only diagnostic keys as 1.2.1. Gameplay scripts, GUI, assets, English strings and the remaining language files are unchanged.

## Exact scope

- German: `tnt_item_usehook_desc`.
- Japanese: `tnt_item_hook_desc`, `tnt_bd_hook_p`, `tnt_bd_hook_r`, `tnt_ai_offer_row_hook_p`, `tnt_ai_offer_row_usehook_r`, `tnt_ai_msg_tt_hook`, `setting_tnt_ai_treaties_rare_desc`.
- Polish: `tnt_item_hostage_desc`.
- Spanish: `tnt_item_marriage_desc`, `tnt_ai_offer_desc_a14`, `tnt_ai_offer_desc_a20`, `tnt_ai_goal_poor`.

## Release boundary

The reviewed build profile preserves the 83-file developer tree and projects the exact 82-file candidate. The release guard replays the approved translation delta against the verified 1.2.1 delivery and requires candidate-byte equality. Package preparation additionally requires an exact-source acceptance report for all nine target languages, current publication-copy validation and a clean reviewed source commit. Missing native localization evidence blocks packaging.

The complete localization gate, public-page updates and newly delivered archive verification remain pending. Static projection success is not native or visual acceptance. Historical 1.2.1 native evidence on CK3 1.20.0.3 retains its original scenario coverage; it does not establish current all-language or visual acceptance.

## Publication source

`publishing/description.en.md` remains canonical. Its 1.2.2 copy targets CK3 1.20.0.4, preserves the AGOT hold and includes the six other maintained mods with their assigned Steam links, including Tax Collection Automation. Nexus file version is 1.2.2; its separate file description is `For CK3 1.20.0.4`. The square cover, separate 16:9 Paradox cover and existing reviewed gallery are reused; this update does not introduce new artwork.
