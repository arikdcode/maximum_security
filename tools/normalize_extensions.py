#!/usr/bin/env python3
"""
Extension normalization, driven by tools/inventory.yaml.

Adds a real extension to every extensionless file. Binary lumps get an honest
extension (png/ogg/.../lmp); text lumps (with --text) get .txt.

Reference handling (the subtle part)
------------------------------------
GZDoom resolves a reference two different ways:
  * BARE NAME (no '/') -> short-name lookup, which is case- AND extension-
    INSENSITIVE. Appending an extension to the file does NOT break these, so we
    leave them alone.
  * PATH (contains '/') -> full-path lookup, which is case-INSENSITIVE but
    extension-SENSITIVE (verified empirically: "graphics/X" will NOT find
    graphics/X.png). So every quoted path reference to a renamed file must gain
    the new extension.

We therefore rewrite quoted path references case-insensitively, editing the file
as BYTES so line endings / encoding are preserved exactly. If any source path
appears UNQUOTED (can't be safely auto-rewritten), we refuse to apply and list
them for manual handling.

Usage
-----
    python3 tools/normalize_extensions.py            # dry-run, binaries only
    python3 tools/normalize_extensions.py --apply
    python3 tools/normalize_extensions.py --text --apply   # include text lumps
"""
import argparse
import os
import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
INVENTORY = REPO / "tools" / "inventory.yaml"
GAME = REPO / "game"

BINARY_EXT = {
    "png": ".png", "ogg": ".ogg", "mp3": ".mp3",
    "wav": ".wav", "flac": ".flac", "pcx": ".pcx",
    "doom_patch": ".lmp", "dmx_sound": ".lmp", "unknown": ".lmp",
    "fon": ".lmp", "wad": ".wad", "md3": ".md3",
}
TEXT_EXT = {"text": ".txt"}

# Characters that may appear inside a Doom asset path; used for token boundaries
# so we match whole paths, not substrings of longer ones.
_PATHCH = r"A-Za-z0-9_/.\- "


def load_inventory():
    inv = yaml.safe_load(INVENTORY.read_text())
    files = inv["files"]
    all_paths = {f["path"] for f in files}
    text_paths = [f["path"] for f in files
                  if f["type"] == "text" and not os.path.basename(f["path"]).startswith(".")]
    return files, all_paths, text_paths


def build_plan(files, all_paths, type_ext):
    renames, collisions = [], []
    for f in files:
        ext = type_ext.get(f["type"])
        if not ext:
            continue
        src = f["path"]
        if os.path.splitext(src)[1]:
            continue
        dst = src + ext
        if dst in all_paths or (GAME / dst).exists():
            collisions.append((src, dst))
        else:
            renames.append((src, dst, ext))
    return renames, collisions


def scan_references(text_paths, rename_index):
    """Find every whole-token occurrence (case-insensitive) of a renamed source
    path inside text lumps. Returns (quoted, unquoted):
      quoted   = {text_file: [(insert_offset, ext), ...]}  (ext goes after token)
      unquoted = [(text_file, token)]  (needs manual review)
    """
    low = {src.lower(): ext for src, ext in rename_index.items()}
    if not low:
        return {}, []
    # one alternation, longest-first so e.g. a/bc wins over a/b
    alt = b"|".join(re.escape(s.encode()) for s in sorted(low, key=len, reverse=True))
    pat = re.compile(rb"(?<![" + _PATHCH.encode() + rb"])(" + alt
                     + rb")(?![" + _PATHCH.encode() + rb"])", re.IGNORECASE)
    quoted, unquoted = {}, []
    for tp in text_paths:
        try:
            data = (GAME / tp).read_bytes()
        except OSError:
            continue
        for m in pat.finditer(data):
            tok = m.group(1).decode("ascii", "replace")
            ext = low[tok.lower()]
            before = data[m.start(1) - 1:m.start(1)]
            after = data[m.end(1):m.end(1) + 1]
            if before == b'"' and after == b'"':
                quoted.setdefault(tp, []).append((m.end(1), ext))
            else:
                unquoted.append((tp, tok))
    return quoted, unquoted


def main():
    ap = argparse.ArgumentParser(description="Normalize extensions from inventory.yaml")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--text", action="store_true",
                    help="also rename text lumps to .txt (default: binaries only)")
    args = ap.parse_args()

    type_ext = dict(BINARY_EXT)
    if args.text:
        type_ext.update(TEXT_EXT)

    files, all_paths, text_paths = load_inventory()
    renames, collisions = build_plan(files, all_paths, type_ext)
    rename_index = {src: ext for src, _dst, ext in renames}
    quoted, unquoted = scan_references(text_paths, rename_index)

    by_ext = {}
    for _s, _d, e in renames:
        by_ext[e] = by_ext.get(e, 0) + 1
    mode = "binaries + text" if args.text else "binaries only"
    print(f"RENAME PLAN ({mode})  total: {len(renames)}")
    for e, c in sorted(by_ext.items(), key=lambda kv: -kv[1]):
        print(f"  {e:6} {c}")
    print(f"\nCollisions (NOT renamed): {len(collisions)}")
    for s, d in collisions:
        print(f"  {s}  ->  {d}  (target exists)")

    n_quoted = sum(len(v) for v in quoted.values())
    print(f"\nQuoted path references to rewrite: {n_quoted} in {len(quoted)} lumps")
    for tp, lst in sorted(quoted.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(lst):4}  {tp}")
    print(f"\nUNQUOTED references (manual review, block apply): {len(unquoted)}")
    for tp, tok in unquoted[:40]:
        print(f"    {tp}  ->  {tok}")

    if not args.apply:
        print("\n(dry-run; pass --apply to perform renames + reference rewrites)")
        return
    if unquoted:
        print("\nREFUSING to apply: resolve unquoted references first.")
        raise SystemExit(2)

    # 1) rewrite references as bytes (right-to-left so offsets stay valid)
    for tp, inserts in quoted.items():
        p = GAME / tp
        data = p.read_bytes()
        for off, ext in sorted(inserts, key=lambda x: -x[0]):
            data = data[:off] + ext.encode() + data[off:]
        p.write_bytes(data)
    print(f"\nRewrote {sum(len(v) for v in quoted.values())} references in {len(quoted)} lumps "
          f"(byte-preserving).")

    # 2) rename files
    for src, dst, _e in renames:
        (GAME / src).rename(GAME / dst)
    print(f"Renamed {len(renames)} files.")


if __name__ == "__main__":
    main()
