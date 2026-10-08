"""Add an explicitly authorized text-only overlay; preserve all other pixels.

Requires Pillow and an explicitly supplied readable font (--font). No font is
bundled. Use the exact original font bytes to reproduce an accepted annotation;
a different font creates a different media result and requires its own review.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('--font', required=True, type=Path,
                        help='Explicit readable font file; font bytes are not bundled.')
    args = parser.parse_args()
    if args.output.exists() or args.receipt.exists():
        raise ValueError('Output and receipt must be new files')
    font_path = args.font.expanduser().resolve()
    if not font_path.is_file():
        raise ValueError('Font must be a readable regular file')
    font_bytes = font_path.read_bytes()
    original = Image.open(args.source).convert('RGB')
    if original.size != (1920, 1080):
        raise ValueError('Expected the approved 1920x1080 capture')
    annotated = original.copy()
    draw = ImageDraw.Draw(annotated)
    title_font = ImageFont.truetype(str(font_path), 28)
    subtitle_font = ImageFont.truetype(str(font_path), 26)
    # Empty center of the deal ledger; never cover an existing UI label.
    bounds = (756, 656, 1180, 741)
    gold, ivory = (147, 117, 65), (232, 215, 173)
    draw.line((786, 658, 1148, 658), fill=gold, width=1)
    for line, y, font in [('Negotiation interests', 670, title_font), ('preview', 707, subtitle_font)]:
        draw.text((967, y), line, font=font, fill=ivory, anchor='mt',
                  stroke_width=1, stroke_fill=(27, 29, 31))
    draw.line((786, 740, 1148, 740), fill=gold, width=1)
    diff = ImageChops.difference(original, annotated)
    outside = diff.copy()
    ImageDraw.Draw(outside).rectangle((bounds[0], bounds[1], bounds[2]-1, bounds[3]-1), fill=(0, 0, 0))
    if outside.getbbox() is not None:
        raise ValueError('Unexpected changes outside caption rectangle')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    annotated.save(args.output, format='PNG', optimize=True)
    restored = Image.open(args.output).convert('RGB')
    if ImageChops.difference(restored, annotated).getbbox() is not None:
        raise ValueError('Saved image differs from lossless annotation')
    record = {
        'status': 'PASS_TEXT_ONLY_OVERLAY',
        'authorization': 'User explicitly approved deterministic text layer without image generation.',
        'caption': 'Negotiation interests preview',
        'source': str(args.source),
        'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'output': str(args.output),
        'output_sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
        'size': original.size,
        'allowed_overlay_rectangle': bounds,
        'actual_changed_rectangle': diff.getbbox(),
        'outside_overlay_pixels_changed': 0,
        'font': str(font_path),
        'font_sha256': hashlib.sha256(font_bytes).hexdigest(),
        'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_provenance': 'User supplied authentic gameplay capture; exact loaded runtime hash not established by screenshot.',
        'generated_image_attempt': 'Rejected because it redrew the gameplay screenshot; not used for publication.'
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.receipt.open('x', encoding='utf-8') as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
