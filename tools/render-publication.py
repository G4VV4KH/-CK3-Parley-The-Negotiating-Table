"""Render English source copy for GitHub, Steam, Nexus and Paradox. No upload API."""
import argparse
import html
import json
import re
from pathlib import Path

SLUGS = ('parley', 'marriage_calc_assistant', 'agot_marriage_calc_assistant')
LINK = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
TOKEN = re.compile(r'\{\{([A-Z0-9_]+)\}\}')

def resolve(text, links, nexus=False):
    missing = sorted({key for key in TOKEN.findall(text) if not links.get(key)})
    lines = []
    for line in text.splitlines():
        if nexus and '{{DONATION_URL}}' in line:
            continue  # Use Nexus's own donation field; no solicitation in page copy.
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
        h = re.match(r'^(#{1,3}) (.+)', escaped)
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
    parser.add_argument('--require-all-links', action='store_true')
    args = parser.parse_args()
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
        repo = args.dev_root / slug
        source = (repo / 'publishing/description.en.md').read_text(encoding='utf-8')
        resolved, missing = resolve(source, links)
        if args.require_all_links and missing:
            raise ValueError(f'{slug}: missing metadata: {missing}')
        target = repo / 'publishing/generated'
        target.mkdir(exist_ok=True)
        nexus, _ = resolve(source, links, nexus=True)
        github = resolved + github_gallery(repo)
        files = {'steam.bbcode':bbcode(resolved,'steam'),'nexus.bbcode':bbcode(nexus,'nexus'),'paradox.txt':plain(resolved),'github.md':github,'preview.html':preview_html(resolved)}
        for name, content in files.items():
            if '{{' in content or '}}' in content:
                raise ValueError('Unresolved placeholder in output')
            (target / name).write_text(content, encoding='utf-8', newline='\n')
        (repo / 'README.md').write_text(github + '\n## Contributing\n\nSee [dev.md](dev.md) for the source layout, checks and pull-request workflow.\n', encoding='utf-8', newline='\n')
        report = {'mod':slug,'missing_metadata':missing,'steam_characters':len(files['steam.bbcode']),'steam_under_8000':len(files['steam.bbcode'])<=8000,'status':'PREVIEW_METADATA_PENDING' if missing else 'COPY_RENDERED','paradox_format':'Plain text: verify final spacing in the actual upload editor.','nexus_donation_link':'Omitted; use platform donation field.'}
        (target / 'render-status.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
        reports.append(report)
    print(json.dumps(reports,indent=2))

if __name__ == '__main__':
    main()
