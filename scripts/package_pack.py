#!/usr/bin/env python3
"""Validate final PNGs and create a new portable preview and image ZIP. Requires Pillow."""
import argparse
import html
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--count', type=int, default=6)
    parser.add_argument('--width', type=int, default=1024)
    parser.add_argument('--height', type=int, default=1024)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source, output = args.directory.resolve(), args.output.resolve()
    if output.exists() or output == source or source in output.parents:
        parser.error('output must be a new directory outside the final image directory')
    result = subprocess.run([
        sys.executable, str(Path(__file__).with_name('validate_pack.py')), str(source),
        '--count', str(args.count), '--width', str(args.width), '--height', str(args.height),
    ], capture_output=True, text=True)
    if result.returncode:
        print(result.stdout or result.stderr, file=sys.stderr)
        return 1
    report = json.loads(result.stdout)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.pack-', dir=output.parent) as temp:
        stage = Path(temp) / 'delivery'
        final = stage / 'final'
        final.mkdir(parents=True)
        cards = []
        from urllib.parse import quote
        for row in report['images']:
            name = row['file']
            shutil.copy2(source / name, final / name)
            cards.append(f'<figure><img src="final/{quote(name)}" alt="{html.escape(name, quote=True)}"><figcaption>{html.escape(name)}</figcaption></figure>')
        page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>文件夹皮肤预览</title>
<style>body{font:16px system-ui;background:#f5f5f5;color:#222;margin:24px}body.dark{background:#242424;color:#eee}header{display:flex;gap:16px;align-items:center;flex-wrap:wrap}main{display:flex;flex-wrap:wrap;gap:24px;margin-top:24px}figure{margin:0;text-align:center}img{width:var(--size,256px);height:var(--size,256px);object-fit:contain}figcaption{max-width:256px;overflow-wrap:anywhere;font-size:13px}</style>
<header><h1>整套预览</h1><button onclick="document.body.classList.toggle('dark')">浅色 / 深色背景</button><label>显示尺寸 <select onchange="document.documentElement.style.setProperty('--size',this.value+'px')"><option>64</option><option>128</option><option selected>256</option></select></label></header>
<p>统一显示尺寸，图片比例保持不变。程序已检查数量、像素尺寸和透明性；主体大小、风格及透明边缘仍需视觉验收。</p><main>'''+''.join(cards)+'</main></html>'
        (stage / 'preview.html').write_text(page, encoding='utf-8')
        (stage / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        with zipfile.ZipFile(stage / 'skins.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(final.iterdir()):
                archive.write(path, path.name)
        stage.rename(output)
    print(json.dumps({'delivery':str(output), 'count':len(report['images']), 'visual_review':'not assessed by this script'}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
