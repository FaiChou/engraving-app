#!/usr/bin/env python3
"""Rebuild added font assets from the pinned, hash-verified original font files.

Usage: python3 fonts/build-assets.py [--source-directory /path/to/fonts]

Without a source directory, originals are fetched from the official Google Fonts
repository. With one, each original is read from <id>.ttf. Requires only Python's
standard library. Never modifies the six pre-existing font assets or index.html.
"""

import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-directory", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "sources.json").read_text())

    for entry in manifest["fonts"]:
        if args.source_directory:
            data = (args.source_directory / (entry["id"] + ".ttf")).read_bytes()
        else:
            url = entry["source"].replace(
                "https://github.com/google/fonts/blob/",
                "https://raw.githubusercontent.com/google/fonts/",
            )
            url = urllib.parse.quote(url, safe=":/%")
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read()
        if hashlib.sha256(data).hexdigest() != entry["sourceSha256"]:
            raise ValueError("Source checksum mismatch: " + entry["id"])

        # Explicit mtime keeps the output independent of the build's clock.
        packed = bytearray(gzip.compress(data, compresslevel=9, mtime=0))
        packed[9] = 255  # Normalize gzip's OS header across Python versions.
        encoded = base64.b64encode(packed).decode("ascii")
        script = (
            "window.ENGRAVING_FONT_DATA=window.ENGRAVING_FONT_DATA||{};"
            "window.ENGRAVING_FONT_DATA[" + json.dumps(entry["id"]) + "]="
            + json.dumps(encoded) + ";\n"
        ).encode("utf-8")
        destination = root / entry["script"]
        destination.write_bytes(script)
        # zlib releases may produce different compressed bytes, but the decoded
        # original is always verified above and remains byte-for-byte identical.
        print(entry["id"], len(script), "bytes")


if __name__ == "__main__":
    main()
