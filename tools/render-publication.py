"""Render English source copy for GitHub, Steam, Nexus and Paradox. No upload API."""
import argparse
import html
import json
import re
from pathlib import Path

SLUGS = ('parley', 'marriage_calc_assistant', 'agot_marriage_calc_assistant')
LINK = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
TOKEN = re.compile(r'\{\{([A-Z0-9_]+)\}\}')
GUIDE_MARKERS = (
    '<!-- steam-guide-summary:start -->',
    '<!-- steam-guide-summary:end -->',
    '<!-- full-game-rules-guide:start -->',
    '<!-- full-game-rules-guide:end -->',
)
STEAM_BYTE_LIMIT = 8000
# Observed in the Paradox Mods description editor on 2026-10-04. Check both
# text and the compact rich-text projection; the form may count its HTML value.
PARADOX_CHARACTER_LIMIT = 10000
DONATION_TEXT = 'Want to support my work? Donate on Ko-fi 💛'

def platform_source(text, platform):
    """Select the approved short Steam/Paradox guide or full guide from one source.

    The four markers must be standalone lines, each occur once, and follow the
    order above. Without them, retain the legacy source exactly. Reject partial
    or malformed blocks instead of leaking editorial markers into public copy.
    """
    if not re.search(r'<!--\s*(?:steam-guide-summary|full-game-rules-guide)', text):
        return text
    lines = text.splitlines(keepends=True)
    positions = []
    for marker in GUIDE_MARKERS:
        found = [i for i, line in enumerate(lines) if line.strip() == marker]
        if len(found) != 1:
            raise ValueError(f'Guide marker must occur once on its own line: {marker}')
        positions.append(found[0])
    if positions != sorted(positions):
        raise ValueError('Guide marker blocks are reversed, overlapping or nested')
    marker_lines = set(positions)
    for i, line in enumerate(lines):
        if re.search(r'<!--\s*(?:steam-guide-summary|full-game-rules-guide)', line) and i not in marker_lines:
            raise ValueError('Malformed or duplicate guide marker')
    summary_start, summary_end, full_start, full_end = positions
    omit_start, omit_end = (full_start, full_end) if platform in ('steam', 'paradox') else (summary_start, summary_end)
    return ''.join(line for i, line in enumerate(lines)
                   if i not in marker_lines and not omit_start < i < omit_end)

def resolve(text, links, nexus=False):
    missing = sorted({key for key in TOKEN.findall(text) if not links.get(key)})
    lines = []
    for line in text.splitlines():
        # The platform selector is retained for callers. Nexus preserves the
        # owner's support link just like the other publication projections.
        tokens = TOKEN.findall(line)
        if tokens and not any(links.get(key) for key in tokens) and any(x in line for x in ('CONTACT_EMAIL', 'mailto:', 'DONATION_URL', 'Source and issue reports')):
            continue
        def replace_link(match):
            label, url = match.groups()
            keys = TOKEN.findall(url)
            if any(not links.get(key) for key in keys):
                return label
            return f'[{label}](' + TOKEN.sub(lambda m: links[m[1]], url) + ')'
        line = LINK.sub(replace_link, line)
        line = TOKEN.sub(lambda m: links.get(m[1]) or '', line)
        lines.append(line)
    return '\n'.join(lines).strip() + '\n', missing

def flatten_tables(text):
    """Use labelled rows consistently on sites without a portable table dialect."""
    out = []
    header = None
    for line in text.splitlines():
        if line.startswith('|'):
            cells = [c.strip() for c in line.strip('|').split('|')]
            if all(re.fullmatch(r':?-+:?', c) for c in cells):
                continue
            if header is None:
                header = cells
                continue
            out.append('- ' + '; '.join(f'{h}: {c}' for h, c in zip(header, cells)))
        else:
            header = None
            out.append(line)
    return '\n'.join(out) + '\n'

def plain(text):
    text = flatten_tables(text)
    text = LINK.sub(lambda m: f'{m[1]}: {m[2]}', text)
    text = re.sub(r'(?m)^#{1,6}\s+', '', text)
    text = text.replace('**', '').replace('`', '')
    return text

def paradox_html(text):
    """Rich editor fragment from resolved Markdown, preserving heading links.

    Never pass the lossy plain-text export here. Only the small authored
    Markdown dialect is supported; raw HTML is escaped, never executed.
    Paradox's native heading is h3, including the separate support heading.
    """
    def inline(value):
        escaped = html.escape(value)
        escaped = LINK.sub(lambda m: f'<a href="{m[2]}">{m[1]}</a>', escaped)
        escaped = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escaped)
        return re.sub(r'`([^`]+)`', r'<strong>\1</strong>', escaped)

    rows, paragraph, listing = [], [], None
    def flush():
        if paragraph:
            rows.append('<p>' + '<br>'.join(paragraph) + '</p>')
            paragraph.clear()
    def close_list():
        nonlocal listing
        if listing:
            rows.append(f'</{listing}>')
            listing = None
    for line in flatten_tables(text).splitlines():
        heading = re.match(r'^#{1,6}\s+(.+)', line)
        item = re.match(r'^(?:([-*])\s+|\d+\.\s+)(.*)', line)
        if heading:
            flush()
            close_list()
            rows.append('<h3>' + inline(heading[1]) + '</h3>')
        elif item:
            flush()
            kind = 'ul' if item[1] else 'ol'
            if kind != listing:
                close_list()
                rows.append(f'<{kind}>')
                listing = kind
            rows.append('<li>' + inline(item[2]) + '</li>')
        else:
            close_list()
            if not line.strip():
                flush()
            else:
                paragraph.append(inline(line))
    flush()
    close_list()
    return ''.join(rows)

def publication_metadata(source, mod_version=None, target_game_version=None):
    """Separate the mod's file version from its approved CK3 compatibility target."""
    version_match = re.search(r'\bVersion\s+(\d+(?:\.\d+)+)', source)
    target_match = re.search(r'\bTargets CK3\s+\*{0,2}(\d+(?:\.\d+)+)', source)
    canonical_version = version_match[1] if version_match else None
    canonical_target = target_match[1] if target_match else None
    if mod_version and canonical_version and mod_version != canonical_version:
        raise ValueError('Explicit mod version differs from canonical description')
    if target_game_version and canonical_target and target_game_version != canonical_target:
        raise ValueError('Explicit CK3 target differs from canonical description')
    version = mod_version or canonical_version
    target = target_game_version or canonical_target
    return {'mod_version': version, 'target_game_version': target,
            'nexus_file_version': version,
            'nexus_file_description': f'For CK3 {target}' if target else None}

def validate_support(source, files, donation_url):
    """Require the approved heading once in every supported rich projection."""
    if not donation_url:
        return 'NOT_VERIFIED'
    link = f'[{DONATION_TEXT}]({donation_url})'
    required = {
        'canonical': f'### {link}',
        'github.md': f'### {link}',
        'steam.bbcode': f'[h1][url={donation_url}]{DONATION_TEXT}[/url][/h1]',
        'nexus.bbcode': f'[size=5][b][url={donation_url}]{DONATION_TEXT}[/url][/b][/size]',
        'paradox.html': f'<h3><a href="{html.escape(donation_url)}">{DONATION_TEXT}</a></h3>',
    }
    for name, heading in required.items():
        content = source if name == 'canonical' else files[name]
        if content.count(heading) != 1 or content.count(DONATION_TEXT) != 1:
            raise ValueError(f'{name}: missing, duplicate or incorrectly formatted support heading')
    return 'PASS'

def paradox_character_count(text):
    # Browser validators count JavaScript UTF-16 code units, not UTF-8 bytes or
    # Python Unicode code points. Astral symbols such as status bullets count 2.
    return len(text.encode('utf-16-le')) // 2

def bbcode(text, platform):
    text = flatten_tables(text)
    text = LINK.sub(lambda m: f'[url={m[2]}]{m[1]}[/url]', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'[b]\1[/b]', text)
    text = re.sub(r'`([^`]+)`', r'[b]\1[/b]', text)
    out, listing = [], None
    def close():
        nonlocal listing
        if listing:
            out.append('[/olist]' if listing == 'ordered' and platform == 'steam' else '[/list]')
            listing = None
    for line in text.splitlines():
        match = re.match(r'^(?:([-*])\s+|\d+\.\s+)(.*)', line)
        if match:
            kind = 'unordered' if match[1] else 'ordered'
            if listing != kind:
                close()
                out.append('[olist]' if kind == 'ordered' and platform == 'steam' else '[list=1]' if kind == 'ordered' else '[list]')
                listing = kind
            out.append('[*]' + match[2])
            continue
        close()
        heading = re.match(r'^#{1,6}\s+(.+)', line)
        if heading:
            out.append('[h1]' + heading[1] + '[/h1]' if platform == 'steam' else '[size=5][b]' + heading[1] + '[/b][/size]')
        else:
            out.append(line)
    close()
    return '\n'.join(out).strip() + '\n'

def preview_html(text):
    # Deliberately simple semantic preview; platform-native layout must be checked on upload.
    rows = []
    for line in flatten_tables(text).splitlines():
        escaped = html.escape(line)
        escaped = LINK.sub(lambda m: f'<a href="{m[2]}">{m[1]}</a>', escaped)
        escaped = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escaped)
        escaped = re.sub(r'`([^`]+)`', r'<code>\1</code>', escaped)
        h = re.match(r'^(#{1,6}) (.+)', escaped)
        rows.append(f'<h{len(h[1])}>{h[2]}</h{len(h[1])}>' if h else '<p>' + escaped + '</p>' if escaped else '')
    return '<!doctype html><meta charset="utf-8"><title>Publication copy preview</title><style>body{max-width:900px;margin:48px auto;padding:0 24px;background:#14181f;color:#e6e8ed;font:17px/1.55 system-ui}h1,h2{color:#e9c880}a{color:#9bc5ff}code{background:#252c36;padding:2px 5px}p{margin:8px 0}</style><main>' + '\n'.join(rows) + '</main>'

def github_gallery(repo):
    manifest = repo / 'publishing/gallery.json'
    if not manifest.exists():
        return ''
    items = json.loads(manifest.read_text(encoding='utf-8'))['items']
    allowed = (repo / 'publishing/screenshots').resolve()
    rows = ['\n## Screenshots\n']
    for item in items:
        path = (repo / item['file']).resolve()
        if not path.is_relative_to(allowed) or not path.is_file():
            raise ValueError(f'Invalid gallery image: {item["file"]}')
        caption = item['caption_en']
        rows.append(f'![{caption}]({item["file"]})\n\n{caption}\n')
    return '\n'.join(rows)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dev-root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--config', type=Path)
    parser.add_argument('--source-dir', type=Path, help='Exact selected repository; requires a single scoped mod')
    parser.add_argument('--mod-version')
    parser.add_argument('--target-game-version')
    parser.add_argument('--require-all-links', action='store_true')
    args = parser.parse_args()
    if args.source_dir and len(SLUGS) != 1:
        parser.error('--source-dir requires the single-mod wrapper')
    config = args.config or args.dev_root / 'parley/publishing/family-links.json'
    links = json.loads(config.read_text(encoding='utf-8'))['links']
    for key, value in links.items():
        if not value:
            continue
        if key.endswith('_URL') and not re.fullmatch(r'https://[^\s\[\]{}<>]+', value):
            raise ValueError(f'Invalid HTTPS URL: {key}')
        if key == 'CONTACT_EMAIL' and not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', value):
            raise ValueError('Invalid public contact email')
    reports = []
    for slug in SLUGS:
        repo = args.source_dir or args.dev_root / slug
        source = (repo / 'publishing/description.en.md').read_text(encoding='utf-8')
        full_source = platform_source(source, 'github')
        steam_source = platform_source(source, 'steam')
        paradox_source = platform_source(source, 'paradox')
        resolved, missing = resolve(full_source, links)
        steam, steam_missing = resolve(steam_source, links)
        paradox, paradox_missing = resolve(paradox_source, links)
        missing = sorted(set(missing) | set(steam_missing) | set(paradox_missing))
        if args.require_all_links and missing:
            raise ValueError(f'{slug}: missing metadata: {missing}')
        nexus, _ = resolve(full_source, links, nexus=True)
        github = resolved + github_gallery(repo)
        metadata = publication_metadata(resolved, args.mod_version, args.target_game_version)
        files = {'steam.bbcode':bbcode(steam,'steam'),'nexus.bbcode':bbcode(nexus,'nexus'),'paradox.txt':plain(paradox),'paradox.html':paradox_html(paradox),'github.md':github,'preview.html':preview_html(resolved),
                 'metadata.json':json.dumps(metadata, ensure_ascii=False, indent=2) + '\n'}
        steam_bytes = len(files['steam.bbcode'].encode('utf-8'))
        if steam_bytes > STEAM_BYTE_LIMIT:
            raise ValueError(f'{slug}: Steam description is {steam_bytes} UTF-8 bytes; limit is {STEAM_BYTE_LIMIT}')
        paradox_characters = paradox_character_count(files['paradox.txt'])
        paradox_html_characters = paradox_character_count(files['paradox.html'])
        if max(paradox_characters, paradox_html_characters) > PARADOX_CHARACTER_LIMIT:
            raise ValueError(f'{slug}: Paradox description is {paradox_characters} text / {paradox_html_characters} HTML characters; limit is {PARADOX_CHARACTER_LIMIT}')
        # Validate the complete selected-mod render before touching any output.
        for name, content in files.items():
            if '{{' in content or '}}' in content:
                raise ValueError('Unresolved placeholder in output')
        support_status = validate_support(resolved, files, links.get('DONATION_URL'))
        target = repo / 'publishing/generated'
        target.mkdir(exist_ok=True)
        for name, content in files.items():
            (target / name).write_text(content, encoding='utf-8', newline='\n')
        (repo / 'README.md').write_text(github + '\n## Contributing\n\nSee [dev.md](dev.md) for the source layout, checks and pull-request workflow.\n', encoding='utf-8', newline='\n')
        report = {'mod':slug,'missing_metadata':missing,'steam_characters':len(files['steam.bbcode']),'steam_under_8000':len(files['steam.bbcode'])<=8000,'steam_bytes':steam_bytes,'steam_under_8000_bytes':steam_bytes<=STEAM_BYTE_LIMIT,'status':'PREVIEW_METADATA_PENDING' if missing else 'COPY_RENDERED','paradox_format':'paradox.html: native rich-text fragment with linked h3 headings; paradox.txt is reference text only. Verify public rendering after saving.','paradox_characters':paradox_characters,'paradox_html_characters':paradox_html_characters,'paradox_under_10000':max(paradox_characters,paradox_html_characters)<=PARADOX_CHARACTER_LIMIT,'required_support_local':support_status,'required_support_public':'NOT_VERIFIED','nexus_donation_link':'Preserved as the approved size=5 bold linked heading.',**metadata}
        (target / 'render-status.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
        reports.append(report)
    print(json.dumps(reports,indent=2))

if __name__ == '__main__':
    main()
