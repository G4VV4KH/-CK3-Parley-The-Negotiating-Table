# Verify the downloaded Workshop copy

`verify_workshop.py` compares an existing Steam download with the exact `game`
inventory in a schema-1 `build_game.py` manifest. It uses Python 3.10+ and only
the standard library. It reads files and prints JSON to stdout; it does not
download, upload, change Steam subscriptions or write into any mod directory.

First validate the game build with `build_game.py --verify`. This delivery check
uses the supplied manifest as its authority and separately verifies that the
local game payload still matches its recorded sizes and SHA-256 hashes. It does
not independently recreate the source projection or replace its engine smoke.

After Steam assigns real IDs and downloads the uploaded mods, pass each mapping
explicitly. The following IDs are placeholders in documentation only; replace
them with the real assigned IDs before running:

```powershell
python ./verify_workshop.py --build-dir './path/to/game/build-id' --workshop-root './workshop/content/1158310' --mod 'parley=REAL_STEAM_ID' --mod 'marriage_calc_assistant=REAL_STEAM_ID' --mod 'agot_marriage_calc_assistant=REAL_STEAM_ID'
```

Only mapped mods are checked. The report lists any unselected manifest mods so
a partial comparison cannot be mistaken for a family verdict. Each mapped mod
must have its own positive numeric Workshop ID.

## Comparison policy

Every expected payload file must be present, with its exact name and bytes.
All extra files inside a mapped mod folder are reported, including documents
and unexpected runtime files; there is no extension-based exclusion. Files in
other Workshop mod directories and Steam's app-level metadata are outside the
comparison. Empty directories carry no payload and are not compared. Links,
Windows reparse points and nonregular files inside a mod payload are rejected.

`descriptor.mod` is byte-exact by default. If Steam or its uploader adds
`remote_file_id` or `path`, rerun with `--allow-descriptor-metadata` to opt into
this narrow exception. Only complete, quoted, top-level assignment lines for
those two keys may differ. Every other byte, including the descriptor's BOM,
other line endings, name, version, dependencies and supported game version,
must remain identical. A downloaded `remote_file_id`, when present, must equal
the explicitly mapped ID. Duplicate metadata assignments are rejected.

The exception does not claim the descriptor files are identical. The result is
`PASS_WITH_DESCRIPTOR_METADATA`, with the before/after metadata values, sizes
and hashes recorded. Changes to the formatting or position of those permitted
metadata lines are also explicitly reported as a metadata-only exception even
when their parsed values are the same. Inline, nested, multiline or otherwise
unsupported metadata forms fail the exact comparison and require inspection;
the tool does not normalize them broadly.

```powershell
python ./verify_workshop.py --build-dir './path/to/game/build-id' --workshop-root './workshop/content/1158310' --mod 'parley=REAL_STEAM_ID' --allow-descriptor-metadata
```

Exit codes: **0** for successful mapped comparisons, **1** for a mismatch or
unreadable/missing mapped payload, **2** for invalid arguments or an unreadable
manifest/configuration. Exact matches receive `PASS_EXACT`; a successful
metadata exception remains visibly distinct. Save the JSON outside the game
and Workshop payloads if a permanent delivery record is needed.

No real Workshop IDs were known when this utility was prepared. Fixture tests
demonstrate its comparison behavior; they do not establish that an uploaded
release has been delivered or runtime-tested.
