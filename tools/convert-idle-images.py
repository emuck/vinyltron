#!/usr/bin/env python3
import argparse
import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageOps


IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.heic', '.heif'}


def center_crop_square(img):
    width, height = img.size
    side = min(width, height)
    if side <= 0:
        return img
    left = int((width - side) / 2)
    top = int((height - side) / 2)
    return img.crop((left, top, left + side, top + side))


def output_name(path, source_root):
    relative = path.relative_to(source_root)
    stem = '__'.join(relative.with_suffix('').parts)
    digest = hashlib.sha1(str(relative).encode('utf-8')).hexdigest()[:8]
    safe = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in stem)
    return f'{safe}-{digest}.png'


def open_source_image(src):
    try:
        img = Image.open(src)
        img = ImageOps.exif_transpose(img).convert('RGB')
        return img
    except Exception:
        if src.suffix.lower() not in ('.heic', '.heif'):
            raise
        return open_heic_with_external_tool(src)


def open_heic_with_external_tool(src):
    magick = shutil.which('magick')
    if magick:
        return open_heic_with_magick(src, magick)

    sips = shutil.which('sips')
    if not sips:
        raise RuntimeError('HEIC/HEIF input requires Pillow HEIF support, ImageMagick, or macOS sips')

    return open_heic_with_sips(src, sips)


def open_heic_with_magick(src, magick):
    with tempfile.TemporaryDirectory(prefix='vinyltron-heic-') as tmp:
        converted = Path(tmp) / (src.stem + '.png')
        subprocess.run(
            [magick, str(src), '-auto-orient', str(converted)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        with Image.open(converted) as img:
            img = ImageOps.exif_transpose(img).convert('RGB')
            return img.copy()


def open_heic_with_sips(src, sips):
    with tempfile.TemporaryDirectory(prefix='vinyltron-heic-') as tmp:
        converted = Path(tmp) / (src.stem + '.jpg')
        subprocess.run(
            [sips, '-s', 'format', 'jpeg', str(src), '--out', str(converted)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        with Image.open(converted) as img:
            img = ImageOps.exif_transpose(img).convert('RGB')
            return img.copy()


def convert_image(src, dst, size):
    with open_source_image(src) as img:
        img = center_crop_square(img)
        img = img.resize((size, size), Image.LANCZOS)
        dst.parent.mkdir(parents=True, exist_ok=True)
        img.save(dst, format='PNG', optimize=True)


def iter_images(source, recursive):
    if source.is_file():
        if source.suffix.lower() in IMAGE_EXTENSIONS:
            yield source
        return

    pattern = '**/*' if recursive else '*'
    for path in sorted(source.glob(pattern)):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            yield path


def main():
    parser = argparse.ArgumentParser(
        description='Convert source photos into matrix-ready Vinyltron idle PNGs.'
    )
    parser.add_argument('source', help='Source image file or folder')
    parser.add_argument('destination', help='Destination folder for converted PNGs')
    parser.add_argument('--size', type=int, default=64, help='Output square size in pixels (default: 64)')
    parser.add_argument('--recursive', action='store_true', help='Scan source folders recursively')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing converted files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be converted without writing files')
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    destination = Path(args.destination).expanduser().resolve()
    if args.size <= 0:
        raise SystemExit('--size must be greater than zero')
    if not source.exists():
        raise SystemExit(f'source does not exist: {source}')

    source_root = source.parent if source.is_file() else source
    converted = 0
    skipped = 0
    failed = 0

    for src in iter_images(source, args.recursive):
        dst = destination / output_name(src, source_root)
        if dst.exists() and not args.overwrite:
            print(f'skip existing: {dst.name}')
            skipped += 1
            continue
        print(f'convert: {src} -> {dst}')
        if args.dry_run:
            converted += 1
            continue
        try:
            convert_image(src, dst, args.size)
            converted += 1
        except Exception as e:
            print(f'error: {src}: {e}')
            failed += 1

    print(f'done: converted={converted} skipped={skipped} failed={failed}')
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
