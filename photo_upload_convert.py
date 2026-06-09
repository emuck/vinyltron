#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
from pathlib import Path

from PIL import Image, ImageOps


def center_crop_square(img):
    width, height = img.size
    side = min(width, height)
    if side <= 0:
        raise ValueError("image has invalid dimensions")
    left = int((width - side) / 2)
    top = int((height - side) / 2)
    return img.crop((left, top, left + side, top + side))


def safe_stem(name):
    stem = Path(name or "photo").stem.lower()
    stem = re.sub(r"[^a-z0-9_-]+", "-", stem).strip("-_")
    return stem or "photo"


def unique_destination(destination, source_name, digest):
    base = "%s-%s" % (safe_stem(source_name), digest[:8])
    path = destination / ("%s.png" % base)
    if not path.exists():
        return path

    for index in range(2, 1000):
        candidate = destination / ("%s-%d.png" % (base, index))
        if not candidate.exists():
            return candidate
    raise RuntimeError("could not allocate unique destination filename")


def convert_image(source, destination, source_name, size):
    data = source.read_bytes()
    digest = hashlib.sha1(data).hexdigest()
    output = unique_destination(destination, source_name or source.name, digest)

    with Image.open(source) as img:
        original_size = img.size
        img = ImageOps.exif_transpose(img).convert("RGB")
        img = center_crop_square(img)
        img = img.resize((size, size), Image.LANCZOS)
        destination.mkdir(parents=True, exist_ok=True)
        img.save(output, format="PNG", optimize=True)

    return {
        "filename": output.name,
        "path": str(output),
        "source_name": source_name or source.name,
        "source_size": list(original_size),
        "size": [size, size],
        "sha1": digest,
    }


def main():
    parser = argparse.ArgumentParser(description="Convert one uploaded Vinyltron idle photo.")
    parser.add_argument("source", help="Temporary uploaded source image")
    parser.add_argument("destination", help="Idle image destination folder")
    parser.add_argument("--source-name", default="", help="Original upload filename")
    parser.add_argument("--size", type=int, default=64, help="Output square size in pixels")
    args = parser.parse_args()

    if args.size <= 0:
        raise SystemExit("--size must be greater than zero")

    result = convert_image(
        Path(args.source).expanduser().resolve(),
        Path(args.destination).expanduser().resolve(),
        args.source_name,
        args.size,
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
