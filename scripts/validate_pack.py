#!/usr/bin/env python3
"""Read-only checks for selected final PNGs; requires Pillow. No visual-style claims."""
import argparse
import json
import sys
from pathlib import Path
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, help='Directory containing only selected final PNGs')
    parser.add_argument('--count', type=int, default=6)
    parser.add_argument('--width', type=int, default=1024)
    parser.add_argument('--height', type=int, default=1024)
    parser.add_argument('--output', type=Path, help='Optional JSON report, outside the image directory')
    args = parser.parse_args()
    if min(args.count, args.width, args.height) <= 0:
        parser.error('count, width, height must be positive')
    if not args.directory.is_dir():
        parser.error('image directory does not exist')
    files = sorted(p for p in args.directory.iterdir() if p.is_file() and p.suffix.lower() == '.png')
    errors = []
    if len(files) != args.count:
        errors.append(f'Expected {args.count} PNGs, found {len(files)}')
    results = []
    for path in files:
        row = {'file': path.name, 'errors': []}
        try:
            with Image.open(path) as im:
                im.load()
                row['size'] = list(im.size)
                if im.format != 'PNG':
                    row['errors'].append('Not a PNG image')
                if im.size != (args.width, args.height):
                    row['errors'].append('Canvas size differs from target')
                # Conversion preserves PNG palette transparency as well as RGBA alpha.
                alpha = im.convert('RGBA').getchannel('A')
                low, high = alpha.getextrema()
                row['alpha_range'] = [low, high]
                if low == 255:
                    row['errors'].append('No transparent pixels')
                if high == 0:
                    row['errors'].append('Image is completely transparent')
                bbox = alpha.point(lambda x: 255 if x > 8 else 0).getbbox()
                row['visible_bounds_auxiliary_only'] = list(bbox) if bbox else None
                row['warnings'] = []
                if bbox and (bbox[0] == 0 or bbox[1] == 0 or bbox[2] == im.width or bbox[3] == im.height):
                    row['warnings'].append('Visible content touches canvas edge; inspect cropping')
        except Exception as exc:
            row['errors'].append(f'Cannot read image: {exc}')
        results.append(row)
    report = {
        'passed': not errors and all(not r['errors'] for r in results),
        'expected': {'count': args.count, 'size': [args.width, args.height]},
        'errors': errors, 'images': results,
        'visual_review': 'not assessed by this script',
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + '\n', encoding='utf-8')
    print(payload)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
