"""Read-only, exact-lineage guard for the reviewed Parley 1.2.2 candidate.

This is not a native test or an acceptance report. A full localization acceptance
must be supplied by the engine owner before packaging; --check-candidate-only in
prepare_publication.py performs only the source/projection check.
"""
import hashlib
import json
import re
import zipfile
from pathlib import Path, PurePosixPath

VERSION = '1.2.2'
TARGET = '1.20.0.4'
CANDIDATE_SHA = '95a1b812b5f581ca5af13e2cd33296f62fb120db33a90412e24d30ec058f0ff7'
RECEIPT_SHA = '7be3be88255b026c85681b106b4420d7bcf96203da34a596c7a64a421d28f2ff'
PARENT_SHA = 'fcc1ca281567fc9f38684b3ba6be2612f90da6ab47d8cb29347cb8d8bf15bfe1'
PROPOSAL_SHA = 'ef1f3a4b6c6b15cd2b45fbd60c133776972a7eca8d86414c5d847cfac170c27a'
ARCHIVE_SHA = 'aeaf649f54204dc415e0c2782503a8082837c99adaac79864028305937690865'
LANGUAGES = {'english', 'french', 'german', 'japanese', 'korean', 'polish', 'russian', 'simp_chinese', 'spanish'}
BLANK_KEYS = {'tnt_ai_goal_blank', 'tnt_threat_cooldown_empty'}
ROOTS = {'common', 'data_binding', 'events', 'gui', 'localization'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def ref(path):
    path = Path(path)
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': sha(data)}


def referenced(record, expected_sha=None):
    actual = ref(record['path'])
    require(actual['sha256'] == record['sha256'], f"Referenced input changed: {record['path']}")
    if 'bytes' in record:
        require(actual['bytes'] == record['bytes'], 'Referenced input size differs')
    if expected_sha:
        require(actual['sha256'] == expected_sha, 'Unexpected reviewed input identity')
    return Path(record['path'])


def read_json(path, expected_sha=None):
    raw = Path(path).read_bytes()
    if expected_sha:
        require(sha(raw) == expected_sha, f'Unreviewed input: {path}')
    def unique(pairs):
        out = {}
        for key, value in pairs:
            require(key not in out, f'Duplicate JSON key: {key}')
            out[key] = value
        return out
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique)


def safe_name(name):
    p = PurePosixPath(name)
    require(bool(name) and p.as_posix() == name and not p.is_absolute()
            and ':' not in name and '\\' not in name and '..' not in p.parts, 'Unsafe runtime member')
    require(name in {'descriptor.mod', 'thumbnail.png'} or
            (len(p.parts) > 1 and p.parts[0] in ROOTS and p.suffix in {'.txt', '.gui', '.yml'}),
            f'Non-runtime member: {name}')


def inventory(files):
    return {name: {'bytes': len(data), 'sha256': sha(data)} for name, data in sorted(files.items())}


def manifest_files(manifest):
    expected = {}
    for item in manifest['files']:
        name = item['path']
        safe_name(name)
        require(name not in expected, 'Duplicate runtime member')
        require(type(item['bytes']) is int and item['bytes'] >= 0 and
                re.fullmatch('[0-9a-f]{64}', item['sha256']), 'Malformed runtime record')
        expected[name] = {key: item[key] for key in ('bytes', 'sha256')}
    return expected


def read_runtime(manifest):
    root = Path(manifest['runtime'])
    expected = manifest_files(manifest)
    require(root.is_dir(), 'Missing runtime')
    files = {}
    for path in root.rglob('*'):
        require(not path.is_symlink() and not (getattr(path.lstat(), 'st_file_attributes', 0) & 0x400),
                f'Runtime reparse point: {path}')
        if path.is_file():
            name = path.relative_to(root).as_posix()
            safe_name(name)
            files[name] = path.read_bytes()
    require(inventory(files) == expected, 'Runtime content/file set changed')
    return files


def candidate_proof(manifest_path, receipt_path):
    manifest = read_json(manifest_path, CANDIDATE_SHA)
    receipt = read_json(receipt_path, RECEIPT_SHA)
    require(manifest['mod'] == 'parley' and manifest['version'] == VERSION and manifest['game_target'] == TARGET,
            'Candidate version/target differs')
    referenced(receipt['runtime_manifest'], CANDIDATE_SHA)
    require(receipt['runtime_manifest']['sha256'] == ref(manifest_path)['sha256'], 'Candidate receipt differs')
    parent_path = referenced(manifest['base_published_manifest'], PARENT_SHA)
    parent = read_json(parent_path)
    archive = referenced(parent['archive'], ARCHIVE_SHA)
    old = read_runtime(parent)
    with zipfile.ZipFile(archive) as z:
        require(len(z.namelist()) == len(set(z.namelist())) == 82, 'Published archive member count differs')
        require({name: z.read(name) for name in z.namelist()} == old, 'Parent differs from published archive')
    proposal_path = referenced(receipt['proposal'], PROPOSAL_SHA)
    proposal = read_json(proposal_path)
    linguistic = read_json(referenced(receipt['linguistic_delta_review']))
    require(linguistic['status'] == 'ACCEPTED_FOR_CANDIDATE_NATIVE_VERIFICATION', 'Delta review not accepted')
    require(proposal['changed_locale_key_entries'] == 13 and proposal['changed_language_files'] == 4,
            'Translation scope differs')
    replay = dict(old)
    for item in proposal['files']:
        require(ref(referenced(item['source']))['sha256'] == sha(old[item['relative_file']]), 'Proposal source differs')
        replay[item['relative_file']] = referenced(item['proposal']).read_bytes()
    require(replay['descriptor.mod'].count(b'version="1.2.1"') == 1, 'Parent descriptor differs')
    replay['descriptor.mod'] = replay['descriptor.mod'].replace(b'version="1.2.1"', b'version="1.2.2"', 1)
    candidate = read_runtime(manifest)
    require(len(candidate) == 82 and candidate == replay, 'Candidate is not the exact reviewed translation delta')
    return candidate, {'candidate_manifest': ref(manifest_path), 'preparation_receipt': ref(receipt_path),
                       'published_parent_manifest': ref(parent_path), 'published_parent_archive': ref(archive),
                       'proposal': ref(proposal_path), 'changed_keys': 13, 'changed_locale_files': 4,
                       'gameplay_and_gui_delta': False, 'status': 'PASS_EXACT_PUBLISHED_LINEAGE'}


def assert_projection(dev_runtime, candidate, builder):
    projected, transforms = builder.project({'parley': dev_runtime})
    require(projected['parley'] == candidate, 'Authoring projection does not equal accepted candidate')
    builder.validate_localizations(projected)
    builder.validate_no_diagnostics(projected)
    return {'source_files': len(dev_runtime), 'game_files': len(candidate),
            'source': inventory(dev_runtime), 'game': inventory(candidate),
            'transforms': transforms, 'status': 'PASS_SOURCE_TO_CANDIDATE_BYTE_PARITY'}


def acceptance(path, candidate_manifest_path):
    """Strict aggregate schema; root builds it only from real candidate evidence.

    native_resolution and translation_review status fields remain assertions of
    the engine/linguistic reviewers. All referenced receipts are byte-verified;
    this function does not fabricate or reinterpret their scenario results.
    """
    require(path is not None, 'Supply exact candidate localization acceptance; packaging is pending')
    gate = read_json(path)
    require(gate.get('schema') == 'parley-localization-release-gate-v1' and gate.get('status') == 'PASS',
            'Complete localization acceptance is required before packaging')
    require(gate.get('mod') == 'parley' and gate.get('version') == VERSION and gate.get('game_target') == TARGET,
            'Acceptance release identity differs')
    referenced(gate['runtime_manifest'], CANDIDATE_SHA)
    require(ref(candidate_manifest_path)['sha256'] == CANDIDATE_SHA, 'Acceptance candidate differs')
    inventory_path = referenced(gate['language_inventory'])
    installed = read_json(inventory_path)
    # The installed-language inventory schema is retained alongside this report;
    # reviewer explicitly carries the identical required set into the gate.
    require(installed['game_version'] == TARGET and set(installed['languages']) == LANGUAGES,
            'Installed target language inventory differs')
    for name in ('source', 'version_source', 'language_names'):
        referenced(installed[name])
    require(set(gate['required_languages']) == LANGUAGES
            and len(gate['required_languages']) == 9, 'Required language set differs')
    require(set(gate['languages']) == LANGUAGES, 'A required language is absent')
    for language, row in gate['languages'].items():
        require(row['status'] == row['translation_review'] == row['native_resolution'] == 'PASS',
                f'Incomplete localization acceptance: {language}')
        require(row['defined_keys'] == row['covered_keys'] == 652 and
                set(row['intentional_blank_keys']) == BLANK_KEYS, f'Wrong key coverage: {language}')
        require(row['remaining_required_gaps'] == [] and bool(row['evidence']), f'Required gaps: {language}')
        for evidence in row['evidence']:
            referenced(evidence)
    require(gate['remaining_required_gaps'] == [], 'Required release gaps remain')
    return {'status': 'PASS', 'report': ref(path), 'visual_status': gate.get('visual_status', 'NOT_VERIFIED')}
